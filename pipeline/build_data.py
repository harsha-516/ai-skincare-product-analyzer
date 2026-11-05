"""
Module 3 — ingredient and product data processing.

Reads the three raw datasets in data/raw/, cleans and standardises them, and writes:
  data/processed/products.csv        clean product table (one row per product)
  data/processed/ingredients.csv     ingredient vocabulary with functions and flags
  data/skincare.db                   SQLite database read by the backend
  report/data_audit.md               data-quality audit (objectives O2 and O3)
  report/manual_check_sample.csv     50 random products for the manual matching check

Run from the repository root:  python pipeline/build_data.py
"""

from __future__ import annotations

import ast
import json
import random
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import write_database
from reference import (ACTIVES, CONCERNS, FAMILIES, SYNONYMS, family_of_name)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "skincare.db"
REPORT = ROOT / "report"

FUZZY_CUTOFF = 93  # RapidFuzz similarity (0–100) needed to accept a fuzzy match

# --------------------------------------------------------------------------- categories
# Sephora tertiary category -> app category. Anything not listed is out of scope
# (tools, supplements, self tanners, body products, gift sets).
CATEGORY_MAP = {
    "Face Wash & Cleansers": "Cleanser",
    "Makeup Removers": "Cleanser",
    "Face Wipes": "Cleanser",
    "Toners": "Toner",
    "Mists & Essences": "Toner",
    "Face Serums": "Serum",
    "Blemish & Acne Treatments": "Serum",
    "Anti-Aging": "Serum",
    "Facial Peels": "Exfoliator",
    "Exfoliators": "Exfoliator",
    "Moisturizers": "Moisturiser",
    "Night Creams": "Moisturiser",
    "Decollete & Neck Creams": "Moisturiser",
    "BB & CC Creams": "Moisturiser",
    "Face Oils": "Face oil",
    "Face Sunscreen": "Sunscreen",
    "Eye Creams & Treatments": "Eye care",
    "Eye Masks": "Eye care",
    "Face Masks": "Mask",
    "Sheet Masks": "Mask",
    "Lip Balm & Treatment": "Lip care",
}

# Mini-size and lip products often have no tertiary category; infer from the name.
NAME_RULES = [
    (r"\b(spf|sunscreen|sun screen|uv)\b", "Sunscreen"),
    (r"\b(cleanser|cleansing|face wash|wash|micellar|makeup remover)\b", "Cleanser"),
    (r"\b(eye)\b", "Eye care"),
    (r"\b(lip)\b", "Lip care"),
    (r"\b(peel|exfoliat\w*|scrub)\b", "Exfoliator"),
    (r"\b(mask|masque)\b", "Mask"),
    (r"\b(toner|essence|mist|tonic)\b", "Toner"),
    (r"\b(serum|treatment|ampoule|booster|drops)\b", "Serum"),
    (r"\b(oil)\b", "Face oil"),
    (r"\b(moisturi[sz]er|cream|lotion|gel cream|balm|hydrator)\b", "Moisturiser"),
]


def app_category(row) -> str | None:
    if row.secondary_category in ("Value & Gift Sets", "High Tech Tools", "Wellness",
                                  "Self Tanners", "Shop by Concern"):
        return None
    # Face products only: drop body, hand, foot, hair and nail products listed under skincare.
    if re.search(r"\b(body|foot|feet|hand|hands|hair|scalp|nail|nails|butt|bum|legs?)\b",
                 str(row.product_name).lower()):
        return None
    if isinstance(row.tertiary_category, str):
        return CATEGORY_MAP.get(row.tertiary_category)
    if row.secondary_category == "Lip Balms & Treatments":
        return "Lip care"
    name = str(row.product_name).lower()
    for pattern, cat in NAME_RULES:
        if re.search(pattern, name):
            return cat
    return None


# --------------------------------------------------------------------------- highlights
SKIN_TYPE_WORDS = {"oily": "oily", "dry": "dry", "combo": "combination",
                   "combination": "combination", "normal": "normal"}
GOOD_FOR_MAP = {
    "Acne/Blemishes": "acne", "Dryness": "dryness", "Redness": "redness",
    "Dark spots": "dark_spots", "Dullness/Uneven Texture": "dullness", "Pores": "pores",
    "Anti-Aging": "ageing", "Loss of firmness": "ageing", "Dark Circles": "dark_circles",
}
CLAIM_TAGS = {"Fragrance Free", "Without Parabens", "Without Sulfates SLS & SLES",
              "Alcohol Free", "Oil Free", "Without Silicones", "Vegan", "Cruelty-Free",
              "Hypoallergenic", "Reef Safe SPF", "Clean at Sephora"}


def parse_highlights(text):
    tags = ast.literal_eval(text) if isinstance(text, str) else []
    skin, good_for, claims = set(), set(), []
    for t in tags:
        if t.startswith("Best for"):
            for w in re.findall(r"[A-Za-z]+", t.replace("Best for", "").replace("Skin", "")):
                if w.lower() in SKIN_TYPE_WORDS:
                    skin.add(SKIN_TYPE_WORDS[w.lower()])
        elif t.startswith("Good for:"):
            c = GOOD_FOR_MAP.get(t.split(":", 1)[1].strip())
            if c:
                good_for.add(c)
        elif t in ("SPF", "UV Protection"):
            good_for.add("sun")
        if t in CLAIM_TAGS:
            claims.append(t)
    return sorted(skin), sorted(good_for), claims


# --------------------------------------------------------------------------- ingredient text
NOISE_PATTERNS = [
    r"\bmay contain\b\s*(\(\+/-\))?:?", r"\(\+/-\)", r"\+/-", r"\b\d+(\.\d+)?\s?%",
    r"\bcertified organic\b", r"\borganic\b", r"\bnano\b", r"\(nano\)", r"[*†‡^®™]",
    r"\bsunscreen\b", r"\bactive ingredients?:?", r"\binactive ingredients?:?",
    r"\bother ingredients:?", r"\bingredients:?",
]


def pick_full_list(raw: str) -> str | None:
    """Sephora stores ingredients as a list of strings: marketing bullets ('-Niacinamide: ...'),
    disclaimers, and the full INCI list. Keep the part(s) that look like an INCI list."""
    if not isinstance(raw, str):
        return None
    try:
        parts = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        parts = [raw]
    lists = [p for p in parts if isinstance(p, str) and not p.strip().startswith("-")
             and p.count(",") >= 3 and "please be aware" not in p.lower()
             and "clean at sephora" not in p.lower()]
    return ", ".join(lists) if lists else None


def split_top_level(text: str) -> list[str]:
    """Split on commas/semicolons/bullets that are not inside brackets."""
    out, buf, depth = [], [], 0
    for i, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        # keep commas inside chemical locants such as 1,2-hexanediol
        in_number = (ch == "," and 0 < i < len(text) - 1 and text[i - 1].isdigit()
                     and text[i + 1].isdigit())
        if ch in ",;•" and depth == 0 and not in_number:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return out


def clean_token(tok: str) -> str:
    t = tok.lower().strip()
    for p in NOISE_PATTERNS:
        t = re.sub(p, " ", t)
    t = t.replace(" ", " ")
    t = re.sub(r"\s+", " ", t).strip(" .:-")
    return t


# --------------------------------------------------------------------------- reference data
def load_cosing():
    df = pd.read_csv(RAW / "cosing_ingredients.csv", dtype=str).fillna("")
    df["key"] = df["INCI name"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    df = df[df.key != ""].drop_duplicates("key")
    return {r["key"]: {"function": r["Function"].strip().title(),
                       "restriction": r["Restriction"].strip(),
                       "ref": r["COSING Ref No"].strip()} for _, r in df.iterrows()}


def load_cureskin():
    df = pd.read_csv(RAW / "cureskin_ingredient_flags.csv")
    df["key"] = df.inci_name.str.lower().str.strip()
    return {r.key: r._asdict() for r in df.itertuples()}


class Matcher:
    """Exact match first, then synonyms and bracket variants, then fuzzy matching."""

    def __init__(self, cosing: dict, cureskin: dict):
        self.cosing = cosing
        self.cureskin = cureskin
        self.vocab = set(cosing) | set(cureskin)
        self.vocab_list = sorted(self.vocab)
        self.cache: dict[str, tuple[str, str]] = {}

    def candidates(self, t: str):
        yield t
        if t in SYNONYMS:
            yield SYNONYMS[t]
        no_brackets = re.sub(r"\s*\([^)]*\)", "", t).strip()
        yield no_brackets
        for inner in re.findall(r"\(([^)]*)\)", t):
            yield inner.strip()
        for part in re.split(r"\s*[/\\]\s*", t):
            yield part
            if part in SYNONYMS:
                yield SYNONYMS[part]
        yield re.sub(r"[\(\)]", "", t).strip()

    def match(self, t: str) -> tuple[str, str]:
        """Return (canonical_key, method) where method is exact | variant | fuzzy | unmatched."""
        if t in self.cache:
            return self.cache[t]
        result = None
        for i, c in enumerate(self.candidates(t)):
            c = re.sub(r"\s+", " ", c).strip()
            c = SYNONYMS.get(c, c)
            if c in self.vocab:
                result = (c, "exact" if i == 0 else "variant")
                break
        if result is None and len(t) >= 5:
            hit = process.extractOne(t, self.vocab_list, scorer=fuzz.ratio,
                                     score_cutoff=FUZZY_CUTOFF)
            if hit:
                result = (hit[0], "fuzzy")
        if result is None:
            result = (t, "unmatched")
        self.cache[t] = result
        return result


# --------------------------------------------------------------------------- main
def main():
    random.seed(42)
    cosing = load_cosing()
    cureskin = load_cureskin()
    matcher = Matcher(cosing, cureskin)

    raw = pd.read_csv(RAW / "sephora_product_info.csv")
    audit = {"raw_rows": len(raw)}
    df = raw[raw.primary_category == "Skincare"].copy()
    audit["skincare_rows"] = len(df)

    df["category"] = df.apply(app_category, axis=1)
    audit["out_of_scope"] = int(df.category.isna().sum())
    df = df[df.category.notna()].copy()

    # Duplicates: same brand + same normalised name (minis, refills, re-listings).
    df["name_key"] = (df.brand_name.str.lower() + "|" +
                      df.product_name.str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True)
                      .str.replace(r"\b(mini|travel size|refill|jumbo|value size)\b", "", regex=True)
                      .str.strip())
    df = df.sort_values(["reviews", "loves_count"], ascending=False)
    before = len(df)
    df = df.drop_duplicates("name_key")
    audit["duplicates_removed"] = before - len(df)

    df = df[df.price_usd.notna() & (df.price_usd > 0)]

    method_counts = Counter()
    unmatched_counter = Counter()
    ingredient_usage = Counter()
    rows = []
    for r in df.itertuples():
        full = pick_full_list(r.ingredients)
        tokens, keys = [], []
        if full:
            for piece in split_top_level(full):
                t = clean_token(piece)
                if not t or len(t) > 120 or len(t) < 2:
                    continue
                key, method = matcher.match(t)
                method_counts[method] += 1
                if method == "unmatched":
                    unmatched_counter[t] += 1
                if key not in keys:
                    keys.append(key)
                    tokens.append((key, method))
        n = len(tokens)
        n_unmatched = sum(1 for _, m in tokens if m == "unmatched")
        if n == 0:
            completeness = "missing"
        elif n < 5 or n_unmatched / n > 0.2:
            completeness = "partial"
        else:
            completeness = "complete"
        for k, m in tokens:
            if m != "unmatched":
                ingredient_usage[k] += 1

        skin, good_for, claims = parse_highlights(r.highlights)
        rows.append({
            "id": r.product_id, "name": r.product_name, "brand": r.brand_name,
            "category": r.category, "source_category": r.tertiary_category if isinstance(
                r.tertiary_category, str) else r.secondary_category,
            "price_usd": float(r.price_usd),
            "sale_price_usd": float(r.sale_price_usd) if pd.notna(r.sale_price_usd) else None,
            "size": r.size if isinstance(r.size, str) else "",
            "rating": round(float(r.rating), 2) if pd.notna(r.rating) else None,
            "reviews": int(r.reviews) if pd.notna(r.reviews) else 0,
            "loves": int(r.loves_count),
            "skin_types": skin, "retailer_good_for": good_for, "claims": claims,
            "ingredients": [k for k, _ in tokens],
            "unmatched": [k for k, m in tokens if m == "unmatched"],
            "completeness": completeness,
        })

    products = pd.DataFrame(rows)

    # ------------------------------------------------------------- ingredient vocabulary
    vocab_keys = sorted({k for p in rows for k in p["ingredients"] if k not in set(p["unmatched"])})
    ing_rows = []
    for k in vocab_keys:
        cs = cosing.get(k, {})
        cu = cureskin.get(k, {})
        flags = family_of_name(k, cs.get("function", ""), cu)
        concerns = {}
        for pat, cs_, strength in ACTIVES:
            if re.search(pat, k):
                for c in cs_:
                    concerns[c] = max(concerns.get(c, 0), strength)
        ing_rows.append({
            "key": k,
            "name": (cu.get("display_name") if isinstance(cu.get("display_name"), str)
                     else k.title()),
            "function": cs.get("function") or (cu.get("function") if isinstance(
                cu.get("function"), str) else ""),
            "cureskin_function": cu.get("function") if isinstance(cu.get("function"), str) else "",
            "eu_restriction": cs.get("restriction", ""),
            "cosing_ref": cs.get("ref", ""),
            "comedogenic": None if pd.isna(cu.get("comedogenic", float("nan")))
            else int(cu["comedogenic"]),
            "families": flags,
            "concerns": concerns,
            "product_count": ingredient_usage[k],
        })
    ingredients = pd.DataFrame(ing_rows)
    ing_lookup = {r["key"]: r for r in ing_rows}

    # Product-level families and concern evidence, derived from ingredients only.
    # UV filters count for sun protection only in sunscreens or products named SPF, because
    # zinc oxide and titanium dioxide are also used as pigments.
    fams, evid, strengths = [], [], []
    for p in rows:
        f, e, cs = set(), {}, {}
        is_spf = p["category"] == "Sunscreen" or re.search(r"\bspf\b", p["name"].lower())
        for k in p["ingredients"]:
            info = ing_lookup.get(k)
            if not info:
                continue
            f.update(info["families"])
            for c, strength in info["concerns"].items():
                if c == "sun" and not is_spf:
                    continue
                e.setdefault(c, []).append((strength, info["name"]))
                cs[c] = max(cs.get(c, 0), strength)
        fams.append(sorted(f))
        evid.append({c: [n for _, n in sorted(v, key=lambda x: -x[0])] for c, v in e.items()})
        strengths.append(cs)
    products["families"] = fams
    products["concern_evidence"] = evid
    products["concern_strength"] = strengths

    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)

    csv = products.copy()
    for col in ["skin_types", "retailer_good_for", "claims", "ingredients", "unmatched",
                "families"]:
        csv[col] = csv[col].apply(lambda v: "; ".join(v))
    csv["concern_evidence"] = csv["concern_evidence"].apply(json.dumps)
    csv["concern_strength"] = csv["concern_strength"].apply(json.dumps)
    csv.to_csv(OUT / "products.csv", index=False)
    ing_csv = ingredients.copy()
    ing_csv["families"] = ing_csv["families"].apply(lambda v: "; ".join(v))
    ing_csv["concerns"] = ing_csv["concerns"].apply(json.dumps)
    ing_csv.to_csv(OUT / "ingredients.csv", index=False)

    total_tokens = sum(method_counts.values())
    matched = total_tokens - method_counts["unmatched"]
    comp = products.completeness.value_counts().to_dict()
    stats = {
        "built": date.today().isoformat(),
        "products": len(products),
        "brands": int(products.brand.nunique()),
        "ingredients": len(vocab_keys),
        "cosing_entries": len(cosing),
        "cureskin_entries": len(cureskin),
        "token_match_rate": round(100 * matched / total_tokens, 2),
        "with_ingredients_pct": round(100 * (1 - comp.get("missing", 0) / len(products)), 2),
        "categories": products.category.value_counts().to_dict(),
        "price_min": float(products.price_usd.min()), "price_max": float(products.price_usd.max()),
        "price_median": float(products.price_usd.median()),
    }
    write_database(DB_PATH, rows, fams, evid, strengths, ing_rows, CONCERNS, FAMILIES, stats)

    # ------------------------------------------------------------- audit + manual sample
    sample = products[products.completeness != "missing"].sample(50, random_state=7)
    sample_rows = []
    for p in sample.itertuples():
        sample_rows.append({"id": p.id, "brand": p.brand, "name": p.name,
                            "n_ingredients": len(p.ingredients),
                            "n_unmatched": len(p.unmatched),
                            "unmatched_tokens": " | ".join(p.unmatched),
                            "reviewer_errors_found": "", "reviewer_notes": ""})
    pd.DataFrame(sample_rows).to_csv(REPORT / "manual_check_sample.csv", index=False)
    sample_tokens = int(sample.ingredients.apply(len).sum())
    sample_unmatched = int(sample.unmatched.apply(len).sum())

    lines = [
        "# Data audit — product and ingredient data (objectives O2 and O3)",
        "",
        f"Generated by `pipeline/build_data.py` on {date.today().isoformat()}.",
        "",
        "## Product table (O2)",
        "",
        "| Step | Rows |", "|---|---|",
        f"| Raw Sephora catalogue | {audit['raw_rows']:,} |",
        f"| Skincare primary category | {audit['skincare_rows']:,} |",
        f"| Removed: out of scope (tools, supplements, self tanners, gift sets, body) | {audit['out_of_scope']:,} |",
        f"| Removed: duplicates (same brand + normalised name) | {audit['duplicates_removed']:,} |",
        f"| **Retained products** | **{len(products):,}** |",
        "",
        f"Target: at least 1,000 products retained → **{'met' if len(products) >= 1000 else 'not met'}**.",
        "",
        "| Ingredient list status | Products | Share |", "|---|---|---|",
    ]
    for k in ["complete", "partial", "missing"]:
        v = comp.get(k, 0)
        lines.append(f"| {k} | {v:,} | {100 * v / len(products):.1f}% |")
    present = 100 * (1 - comp.get("missing", 0) / len(products))
    lines += [
        "",
        f"Target: ingredient list present for at least 95% of retained products → "
        f"**{present:.1f}%, {'met' if present >= 95 else 'not met'}**.",
        "",
        "*complete* = at least 5 ingredients and no more than 20% unmatched tokens; "
        "*partial* = shorter list or more than 20% unmatched. When a user sets restrictions, "
        "products whose list is missing are excluded and partial lists are flagged.",
        "",
        "| Category | Products |", "|---|---|",
    ]
    for k, v in products.category.value_counts().items():
        lines.append(f"| {k} | {v:,} |")
    lines += [
        "",
        "## Ingredient matching (O3)",
        "",
        f"Reference vocabulary: {len(cosing):,} EU CosIng INCI entries plus "
        f"{len(cureskin):,} CureSkin flagged ingredients.",
        "",
        "| Match method | Tokens | Share |", "|---|---|---|",
    ]
    for k in ["exact", "variant", "fuzzy", "unmatched"]:
        v = method_counts[k]
        lines.append(f"| {k} | {v:,} | {100 * v / total_tokens:.2f}% |")
    lines += [
        "",
        f"Tokens mapped to a reference entry: **{100 * matched / total_tokens:.2f}%** "
        f"(target ≥ 95% mapped or flagged as unmatched → every token is one or the other, and "
        f"the mapped share is reported here).",
        "",
        "*variant* = matched after a synonym (e.g. water → aqua, parfum → fragrance) or after "
        "dropping bracketed common names. *fuzzy* = RapidFuzz ratio ≥ "
        f"{FUZZY_CUTOFF}.",
        "",
        f"Manual-check sample: 50 random products, {sample_tokens:,} ingredient tokens, "
        f"{sample_unmatched} unmatched ({100 * sample_unmatched / max(sample_tokens, 1):.2f}%). "
        "The sample is in `report/manual_check_sample.csv` with empty reviewer columns for the "
        "team to fill in.",
        "",
        "### Most frequent unmatched tokens",
        "",
        "| Token | Count |", "|---|---|",
    ]
    for t, v in unmatched_counter.most_common(25):
        lines.append(f"| {t.replace('|', '/')} | {v} |")
    lines += [
        "",
        "## Sources considered and rejected",
        "",
        "- **Open Beauty Facts (India)**: 1,871 products tagged India, but only 42 of the first "
        "100 had an ingredient list and many are toothpaste, shampoo or make-up, with no prices. "
        "Not used for this phase.",
        "",
    ]
    (REPORT / "data_audit.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"products={len(products)} ingredients={len(vocab_keys)} "
          f"match={100 * matched / total_tokens:.2f}% methods={dict(method_counts)}")
    print("completeness", comp)
    print("categories", products.category.value_counts().to_dict())


if __name__ == "__main__":
    main()
