"""
Modules 1, 4 and 5 — profile validation, constraint filtering, scoring and explanations.

    S(p, u) = w_c·C + w_i·I + w_k·K + w_b·B        (report section 4.3.4)

Hard rules (budget, category, restricted ingredients) remove a product before scoring and are
never overridden by a high score. A component with no user input (no concerns, no preferred
ingredients) is left out and the remaining weights are renormalised.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .catalogue import Catalogue, Product

DEFAULT_WEIGHTS = {"c": 0.35, "i": 0.25, "k": 0.20, "b": 0.20}
SKIN_TYPES = ("oily", "dry", "combination", "normal", "unsure")
SENSITIVE_DEFAULT_AVOID = ("fragrance", "essential_oils", "drying_alcohol")
EXCLUSION_REASONS = ("category", "budget", "restricted", "incomplete")


@dataclass
class Profile:
    skin_type: str
    sensitivity: str = "low"
    concerns: list[str] = field(default_factory=list)
    category: str = "any"
    budget_min: float = 0
    budget_max: float = 50
    avoid_families: list[str] = field(default_factory=list)
    avoid_ingredients: list[str] = field(default_factory=list)   # ingredient keys
    prefer_ingredients: list[str] = field(default_factory=list)  # ingredient keys


@dataclass
class Scored:
    product: Product
    parts: dict[str, float]
    score: float
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Result:
    ranked: list[Scored]
    eligible_count: int
    excluded: dict[str, int]


def validate(u: Profile, cat: Catalogue) -> list[str]:
    errors = []
    if u.skin_type not in SKIN_TYPES:
        errors.append("Choose a skin type, or pick “Not sure”.")
    if u.sensitivity not in ("low", "high"):
        errors.append("Sensitivity must be low or high.")
    if not all(math.isfinite(v) for v in (u.budget_min, u.budget_max)):
        errors.append("Enter a budget range.")
    else:
        if u.budget_min < 0 or u.budget_max < 0:
            errors.append("Budget cannot be negative.")
        if u.budget_min > u.budget_max:
            errors.append("The minimum budget is above the maximum.")
    if len(u.concerns) > 4:
        errors.append("Pick up to four concerns so results stay focused.")
    unknown = [c for c in u.concerns if c not in cat.concerns]
    if unknown:
        errors.append(f"Unknown concern: {', '.join(unknown)}.")
    unknown = [f for f in u.avoid_families if f not in cat.families]
    if unknown:
        errors.append(f"Unknown ingredient family: {', '.join(unknown)}.")
    if u.category != "any" and u.category not in cat.categories:
        errors.append(f"Unknown category: {u.category}.")
    unknown = [k for k in u.avoid_ingredients + u.prefer_ingredients if k not in cat.by_key]
    if unknown:
        errors.append(f"Unknown ingredient: {', '.join(unknown)}.")
    clash = sorted(set(u.prefer_ingredients) & set(u.avoid_ingredients))
    if clash:
        errors.append(f"An ingredient cannot be both preferred and avoided: {', '.join(clash)}.")
    return errors


def exclusion_reason(p: Product, u: Profile, cat: Catalogue) -> str | None:
    if u.category != "any" and p.category != u.category:
        return "category"
    if not (u.budget_min <= p.effective_price <= u.budget_max):
        return "budget"
    if u.avoid_families or u.avoid_ingredients:
        # A restriction cannot be checked on a missing ingredient list.
        if p.completeness == "missing":
            return "incomplete"
        if p.families.intersection(u.avoid_families):
            return "restricted"
        avoid_ids = {cat.by_key[k].id for k in u.avoid_ingredients}
        if avoid_ids & p.ingredient_id_set:
            return "restricted"
    return None


def component_scores(p: Product, u: Profile, cat: Catalogue) -> dict[str, float]:
    parts = {}
    if u.concerns:
        parts["c"] = sum(p.concern_strength.get(c, 0) for c in u.concerns) / len(u.concerns)
    if u.prefer_ingredients:
        ids = p.ingredient_id_set
        parts["i"] = sum(cat.by_key[k].id in ids for k in u.prefer_ingredients) / len(
            u.prefer_ingredients)
    if not p.skin_types or u.skin_type == "unsure":
        parts["k"] = 0.5
    else:
        parts["k"] = 1.0 if u.skin_type in p.skin_types else 0.2
    span = u.budget_max - u.budget_min
    parts["b"] = 1 - 0.6 * (p.effective_price - u.budget_min) / span if span > 0 else 1.0
    return parts


def combine(parts: dict[str, float], weights: dict[str, float] = DEFAULT_WEIGHTS) -> float:
    w = sum(weights[k] for k in parts)
    return sum(weights[k] * v for k, v in parts.items()) / w if w > 0 else 0.0


def popularity(p: Product) -> float:
    return (p.rating or 0) * math.log10(p.reviews + 1)


def _money(v: float) -> str:
    return f"${v:.0f}" if float(v).is_integer() else f"${v:.2f}"


def _join(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else f"{', '.join(xs[:-1])} and {xs[-1]}"


def explain(p: Product, u: Profile, cat: Catalogue) -> tuple[list[str], list[str]]:
    reasons, warnings = [], []
    where = f"A {p.category.lower()}, as you asked," if u.category != "any" else \
        f"A {p.category.lower()}"
    reasons.append(f"{where} at {_money(p.effective_price)}, inside your "
                   f"{_money(u.budget_min)}–{_money(u.budget_max)} budget.")
    for c in u.concerns:
        label = cat.concerns[c].lower()
        ev = p.concern_evidence.get(c)
        if ev:
            reasons.append(f"For {label}: contains {_join(ev[:3])}.")
        else:
            warnings.append(f"Nothing in the ingredient list is matched to {label}.")
    if u.prefer_ingredients:
        ids = p.ingredient_id_set
        hit = [cat.by_key[k].name for k in u.prefer_ingredients if cat.by_key[k].id in ids]
        if hit:
            reasons.append(f"Contains {_join(hit)}, which you said you prefer.")
    avoided = [cat.families[f].lower() for f in u.avoid_families] + \
              [cat.by_key[k].name for k in u.avoid_ingredients]
    if avoided:
        reasons.append(f"Free of what you asked to avoid: {_join(avoided)}.")
        if p.completeness == "partial":
            warnings.append("Part of this ingredient list could not be matched, so double-check "
                            "the label.")
    if p.skin_types and u.skin_type != "unsure":
        if u.skin_type in p.skin_types:
            reasons.append(f"The retailer lists it for {_join(p.skin_types)} skin, "
                           "which includes yours.")
        else:
            warnings.append(f"The retailer lists it for {_join(p.skin_types)} skin, "
                            f"not {u.skin_type}.")
    if p.rating and p.reviews >= 20:
        reasons.append(f"Rated {p.rating:.1f} out of 5 from {p.reviews:,} reviews.")
    if "pregnancy_caution" not in u.avoid_families and "pregnancy_caution" in p.families:
        warnings.append("Contains an ingredient flagged for pregnancy caution.")
    if u.sensitivity == "high" and "strong_actives" in p.families:
        warnings.append("Has a strong active. Patch-test it first and introduce it slowly.")
    return reasons, warnings


def recommend(cat: Catalogue, u: Profile, *, weights: dict[str, float] = DEFAULT_WEIGHTS,
              explain_top: int = 0) -> Result:
    excluded = dict.fromkeys(EXCLUSION_REASONS, 0)
    scored = []
    for p in cat.products.values():
        why = exclusion_reason(p, u, cat)
        if why:
            excluded[why] += 1
            continue
        parts = component_scores(p, u, cat)
        scored.append(Scored(p, parts, combine(parts, weights)))
    scored.sort(key=lambda s: (-s.score, -popularity(s.product), s.product.id))
    for s in scored[:explain_top]:
        s.reasons, s.warnings = explain(s.product, u, cat)
    return Result(scored, len(scored), excluded)
