"""
Evaluation of the recommender on the predefined personas (report section 4.5).

Relevance labels: a product counts as relevant for a persona when the retailer's own
"Good for: …" tags include at least one of the persona's concerns. These are marketing tags,
so they are weak labels (gap G1); the scorer never reads them, which keeps the comparison
fair. Manually labelled relevance sets can replace them later.

Run from the repository root:  python eval/run_eval.py
Writes report/evaluation.md and report/evaluation.json.
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import date
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.catalogue import get_catalogue  # noqa: E402
from backend.app.recommender import (DEFAULT_WEIGHTS, Profile, exclusion_reason,  # noqa: E402
                                     recommend)

K = 5


def load_personas() -> list[tuple[dict, Profile]]:
    raw = json.loads((ROOT / "eval" / "personas.json").read_text(encoding="utf-8"))
    return [(r, Profile(skin_type=r["skinType"], sensitivity=r["sensitivity"],
                        concerns=r["concerns"], category=r["category"],
                        budget_min=r["budgetMin"], budget_max=r["budgetMax"],
                        avoid_families=r["avoidFamilies"],
                        avoid_ingredients=r["avoidIngredients"],
                        prefer_ingredients=r["preferIngredients"])) for r in raw]


def is_relevant(p, u: Profile) -> bool:
    return any(c in u.concerns for c in p.retailer_good_for)


def violations(p, u: Profile, cat) -> list[str]:
    """Independent check: recompute families from each ingredient, not from p.families."""
    v = []
    if u.category != "any" and p.category != u.category:
        v.append("category")
    if not (u.budget_min <= p.effective_price <= u.budget_max):
        v.append("budget")
    if u.avoid_families or u.avoid_ingredients:
        if p.completeness == "missing":
            v.append("unverifiable")
        ings = [cat.ingredients[i] for i in p.ingredient_ids]
        if any(f in u.avoid_families for i in ings for f in i.families):
            v.append("family")
        if any(i.key in u.avoid_ingredients for i in ings):
            v.append("ingredient")
    return v


def metrics(ranked: list, u: Profile, total_relevant: int) -> dict:
    rel = [1 if is_relevant(p, u) else 0 for p in ranked[:K]]
    hits = sum(rel)
    dcg = sum(r / math.log2(i + 2) for i, r in enumerate(rel))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(K, total_relevant)))
    return {"p": hits / K if ranked else 0.0,
            "r": hits / min(K, total_relevant) if total_relevant else 0.0,
            "ndcg": dcg / ideal if ideal else 0.0}


def avg(ms: list[dict]) -> dict:
    return {k: mean(m[k] for m in ms) for k in ("p", "r", "ndcg")}


def main():
    cat = get_catalogue()
    personas = load_personas()
    methods = {k: [] for k in ("ours", "popularity", "cheapest", "random",
                               "noC", "noI", "noK", "noB")}
    per_persona, jaccards = [], []
    checked = viol = checked_naive = viol_naive = explained = with_three = 0

    for raw, u in personas:
        eligible = [p for p in cat.products.values() if not exclusion_reason(p, u, cat)]
        total_relevant = sum(is_relevant(p, u) for p in eligible)
        res = recommend(cat, u, explain_top=K)
        ours = [s.product for s in res.ranked[:K]]
        m = metrics(ours, u, total_relevant)
        methods["ours"].append(m)

        for s in res.ranked[:K]:
            checked += 1
            viol += bool(violations(s.product, u, cat))
            explained += 1
            with_three += len(s.reasons) >= 3

        naive = sorted((p for p in cat.products.values()
                        if u.category == "any" or p.category == u.category),
                       key=lambda p: -p.loves)[:K]
        for p in naive:
            checked_naive += 1
            viol_naive += bool(violations(p, u, cat))

        methods["popularity"].append(metrics(sorted(eligible, key=lambda p: -p.loves), u,
                                             total_relevant))
        methods["cheapest"].append(metrics(sorted(eligible, key=lambda p: p.effective_price), u,
                                           total_relevant))
        rnd = []
        for seed in range(1, 31):
            shuffled = eligible[:]
            random.Random(seed).shuffle(shuffled)
            rnd.append(metrics(shuffled, u, total_relevant))
        methods["random"].append(avg(rnd))

        for name, key in (("noC", "c"), ("noI", "i"), ("noK", "k"), ("noB", "b")):
            w = {**DEFAULT_WEIGHTS, key: 0}
            methods[name].append(metrics([s.product for s in recommend(cat, u, weights=w)
                                          .ranked[:K]], u, total_relevant))

        base = {p.id for p in ours}
        for key in DEFAULT_WEIGHTS:
            for d in (-0.1, 0.1):
                w = {**DEFAULT_WEIGHTS, key: max(0.0, DEFAULT_WEIGHTS[key] + d)}
                ids = {s.product.id for s in recommend(cat, u, weights=w).ranked[:K]}
                union = ids | base
                jaccards.append(len(ids & base) / len(union) if union else 1.0)

        per_persona.append({"id": raw["id"], "label": raw["label"], "eligible": len(eligible),
                            "relevant": total_relevant, **m,
                            "top": [f"{p.brand} — {p.name}" for p in ours]})

    summary = {k: avg(v) for k, v in methods.items()}
    out = {
        "generated": date.today().isoformat(), "personas": len(personas), "k": K,
        "summary": summary, "violation_rate": viol / checked,
        "naive_violation_rate": viol_naive / checked_naive,
        "explanation_coverage": with_three / explained,
        "weight_sensitivity_jaccard": mean(jaccards), "per_persona": per_persona,
    }
    (ROOT / "report" / "evaluation.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    names = {
        "ours": "Constraints first + weighted score (this project)",
        "popularity": "Most-loved among eligible products",
        "cheapest": "Cheapest among eligible products",
        "random": "Random among eligible products (mean of 30 seeds)",
        "noC": "Ablation: without concern match C",
        "noI": "Ablation: without preferred-ingredient match I",
        "noK": "Ablation: without skin-type fit K",
        "noB": "Ablation: without budget fit B",
    }
    pct = lambda x: f"{100 * x:.1f}%"  # noqa: E731
    md = [
        "# Evaluation — recommender on predefined personas", "",
        f"Generated by `eval/run_eval.py` on {out['generated']}. {len(personas)} personas, "
        f"K = {K}.", "",
        "Relevance labels are the retailer's own \"Good for\" tags. They are marketing tags, so",
        "treat these as weak labels. The scorer never reads them. Swap in manually labelled",
        "relevance sets when the team has them (objective O5).", "",
        "## Constraint filtering (O4)", "",
        "| Check | Result |", "|---|---|",
        f"| Constraint violation rate, this project (top {K}) | **{pct(out['violation_rate'])}** "
        f"({viol} of {checked}) |",
        f"| Violation rate, naive most-loved list without filters | "
        f"{pct(out['naive_violation_rate'])} ({viol_naive} of {checked_naive}) |", "",
        "Violations are rechecked independently from the ingredient table: category, budget,",
        "avoided ingredient families, avoided ingredients, and lists that are missing and so",
        "cannot be checked.", "",
        "## Ranking quality (O5)", "",
        f"| Method | Precision@{K} | Recall@{K} | NDCG@{K} |", "|---|---|---|---|",
        *[f"| {names[k]} | {summary[k]['p']:.3f} | {summary[k]['r']:.3f} | "
          f"{summary[k]['ndcg']:.3f} |" for k in names], "",
        f"Weight sensitivity: moving any one weight by ±0.1 keeps a mean top-{K} Jaccard overlap",
        f"of **{out['weight_sensitivity_jaccard']:.3f}** with the default ranking.", "",
        "## Explanations (O6)", "",
        f"{pct(out['explanation_coverage'])} of recommended products show at least three "
        "plain-language reasons.", "",
        "## Per persona", "",
        f"| ID | Persona | Eligible | Relevant | P@{K} | NDCG@{K} | Top result |",
        "|---|---|---|---|---|---|---|",
        *[f"| {r['id']} | {r['label']} | {r['eligible']} | {r['relevant']} | {r['p']:.3f} | "
          f"{r['ndcg']:.3f} | {(r['top'][0] if r['top'] else '—').replace('|', '/')} |"
          for r in per_persona], "",
    ]
    (ROOT / "report" / "evaluation.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"summary": {k: {m: round(v, 3) for m, v in s.items()}
                                  for k, s in summary.items()},
                      "violation_rate": out["violation_rate"],
                      "naive": out["naive_violation_rate"],
                      "explanations": out["explanation_coverage"],
                      "jaccard": round(out["weight_sensitivity_jaccard"], 3)}, indent=1))


if __name__ == "__main__":
    main()
