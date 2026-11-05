"""
Module 3 — ingredient and product data processing.

Reads the saved brand-store catalogues (data/raw/brands/, collected by fetch_brands.py) and
the two ingredient references in data/raw/, cleans and standardises them, and writes:
  data/skincare.db                   SQLite database read by the backend
  data/processed/products.csv        clean product table (one row per product)
  data/processed/ingredients.csv     ingredient vocabulary with functions and flags
  report/data_audit.md               data-quality audit (objectives O2 and O3)
  report/manual_check_sample.csv     50 random products for the manual matching check

Run from the repository root:  python pipeline/build_data.py
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

sys.path.insert(0, str(Path(__file__).resolve().parent))
from database import write_database  # noqa: E402
from reference import (ACTIVES, CONCERNS, FAMILIES, SYNONYMS, family_of_name)  # noqa: E402
from sources import load_brand_products  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
DB_PATH = Path(os.environ.get("SKINCARE_DB", ROOT / "data" / "skincare.db"))
REPORT = ROOT / "report"

FUZZY_CUTOFF = 93  # RapidFuzz similarity (0–100) needed to accept a fuzzy match

# Key actives named in a product's title or description, used only when the brand does not
# publish a full ingredient list. (pattern, name shown to users, reference INCI key)
NAMED_ACTIVES = [
    (r"niacinamide", "Niacinamide", "niacinamide"),
    (r"salicylic", "Salicylic Acid", "salicylic acid"),
    (r"vitamin\s*c\b|ascorb", "Vitamin C", "ascorbic acid"),
    (r"hyaluronic", "Hyaluronic Acid", "sodium hyaluronate"),
    (r"\bretinol\b", "Retinol", "retinol"),
    (r"\bretinal(dehyde)?\b", "Retinal", "retinal"),
    (r"ceramide", "Ceramides", "ceramide np"),
    (r"azelaic", "Azelaic Acid", "azelaic acid"),
    (r"arbutin", "Alpha Arbutin", "alpha-arbutin"),
    (r"tranexamic", "Tranexamic Acid", "tranexamic acid"),
    (r"kojic", "Kojic Acid", "kojic acid"),
    (r"glycolic", "Glycolic Acid", "glycolic acid"),
    (r"lactic", "Lactic Acid", "lactic acid"),
    (r"mandelic", "Mandelic Acid", "mandelic acid"),
    (r"centella|\bcica\b", "Centella Asiatica", "centella asiatica extract"),
    (r"peptide", "Peptides", "palmitoyl tripeptide-1"),
    (r"caffeine|coffee", "Caffeine", "caffeine"),
    (r"benzoyl peroxide", "Benzoyl Peroxide", "benzoyl peroxide"),
    (r"squalane", "Squalane", "squalane"),
    (r"panthenol|vitamin\s*b5", "Panthenol", "panthenol"),
    (r"bakuchiol", "Bakuchiol", "bakuchiol"),
    (r"\bsulph?ur\b", "Sulfur", "sulfur"),
    (r"zinc (pca|gluconate)", "Zinc", "zinc pca"),
    (r"\bclay\b|kaolin|bentonite", "Clay", "kaolin"),
]


def named_actives(text: str) -> list[tuple[str, str]]:
    t = text.lower()
    return [(name, key) for pat, name, key in NAMED_ACTIVES if re.search(pat, t)]


def concerns_of_key(key: str) -> dict[str, float]:
    out = {}
    for pat, cs, strength in ACTIVES:
        if re.search(pat, key):
            for c in cs:
                out[c] = max(out.get(c, 0), strength)
    return out


# --------------------------------------------------------------------------- ingredient text
NOISE_PATTERNS = [
    r"\bmay contain\b\s*(\(\+/-\))?:?", r"\(\+/-\)", r"\+/-", r"\b\d+(\.\d+)?\s?%",
    r"\bcertified organic\b", r"\borganic\b", r"\bnano\b", r"\(nano\)", r"[*†‡^®™]",
    r"\bsunscreen\b", r"\bactive ingredients?:?", r"\binactive ingredients?:?",
    r"\bother ingredients:?", r"\bingredients:?",
]


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

    source, audit = load_brand_products()
    # Featured order: each product's position in its brand store, so brands interleave.
    position = Counter()
    for p in source:
        p["featured_rank"] = position[p["brand"]]
        position[p["brand"]] += 1

    method_counts = Counter()
    unmatched_counter = Counter()
    ingredient_usage = Counter()
    rows = []
    for p in source:
        tokens, keys = [], []
        if p["ingredients_text"]:
            for piece in split_top_level(p["ingredients_text"]):
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
        actives = []
        if n >= 5 and n_unmatched / n <= 0.2:
            completeness = "complete"
        elif n >= 5:
            completeness = "partial"
        else:
            tokens = []
            actives = named_actives(f"{p['name']} {p['description']}")
            completeness = "actives" if actives else "missing"
        for k, m in tokens:
            if m != "unmatched":
                ingredient_usage[k] += 1
        rows.append({**p, "ingredients": [k for k, _ in tokens],
                     "unmatched": [k for k, m in tokens if m == "unmatched"],
                     "named_actives": actives, "completeness": completeness})

    products = pd.DataFrame(rows)

    # ------------------------------------------------------------- ingredient vocabulary
    # Every ingredient found in a product list, plus CureSkin's India-relevant flagged list, so
    # users can avoid an ingredient (e.g. linalool) even before any product lists it.
    vocab_keys = sorted({k for p in rows for k in p["ingredients"] if k not in set(p["unmatched"])}
                        | set(cureskin))
    ing_rows = []
    for k in vocab_keys:
        cs = cosing.get(k, {})
        cu = cureskin.get(k, {})
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
            "families": family_of_name(k, cs.get("function", ""), cu),
            "concerns": concerns_of_key(k),
            "product_count": ingredient_usage[k],
        })
    ingredients = pd.DataFrame(ing_rows)
    ing_lookup = {r["key"]: r for r in ing_rows}

    # Product-level families and concern evidence. From the full ingredient list when there is
    # one, otherwise from the actives named on the product (concerns only: families cannot be
    # checked without a full list). UV filters count for sun protection only in sunscreens or
    # products named SPF, because zinc oxide and titanium dioxide are also used as pigments.
    fams, evid, strengths = [], [], []
    for p in rows:
        f, e, cs = set(), {}, {}
        is_spf = p["category"] == "Sunscreen" or re.search(r"\bspf\b", p["name"].lower())
        sources = [(ing_lookup[k]["name"], ing_lookup[k]["concerns"], ing_lookup[k]["families"])
                   for k in p["ingredients"] if k in ing_lookup]
        sources += [(name, concerns_of_key(key), []) for name, key in p["named_actives"]]
        if is_spf and not p["ingredients"]:
            sources.append(("SPF", {"sun": 1.0}, []))
        for name, concerns, families in sources:
            f.update(families)
            for c, strength in concerns.items():
                if c == "sun" and not is_spf:
                    continue
                e.setdefault(c, []).append((strength, name))
                cs[c] = max(cs.get(c, 0), strength)
        fams.append(sorted(f))
        evid.append({c: [n for _, n in sorted(v, key=lambda x: -x[0])] for c, v in e.items()})
        strengths.append(cs)
    products["families"] = fams
    products["concern_evidence"] = evid
    products["concern_strength"] = strengths

    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)

    csv = products.drop(columns=["ingredients_text", "description"]).copy()
    for col in ["skin_types", "retailer_good_for", "claims", "ingredients", "unmatched",
                "families"]:
        csv[col] = csv[col].apply(lambda v: "; ".join(v))
    for col in ["concern_evidence", "concern_strength", "variants", "named_actives"]:
        csv[col] = csv[col].apply(json.dumps)
    csv.to_csv(OUT / "products.csv", index=False)
    ing_csv = ingredients.copy()
    ing_csv["families"] = ing_csv["families"].apply(lambda v: "; ".join(v))
    ing_csv["concerns"] = ing_csv["concerns"].apply(json.dumps)
    ing_csv.to_csv(OUT / "ingredients.csv", index=False)

    total_tokens = max(sum(method_counts.values()), 1)
    matched = total_tokens - method_counts["unmatched"]
    comp = products.completeness.value_counts().to_dict()
    with_list = comp.get("complete", 0) + comp.get("partial", 0)
    stats = {
        "built": date.today().isoformat(),
        "products": len(products),
        "brands": int(products.brand.nunique()),
        "ingredients": len(vocab_keys),
        "cosing_entries": len(cosing),
        "cureskin_entries": len(cureskin),
        "token_match_rate": round(100 * matched / total_tokens, 2),
        "with_ingredients_pct": round(100 * with_list / len(products), 2),
        "categories": products.category.value_counts().to_dict(),
        "price_min": float(products.price.min()), "price_max": float(products.price.max()),
        "price_median": float(products.price.median()),
        "stores": audit["stores"],
        "currency": "INR",
    }
    write_database(DB_PATH, rows, fams, evid, strengths, ing_rows, CONCERNS, FAMILIES, stats)

    # ------------------------------------------------------------- audit + manual sample
    listed = products[products.completeness.isin(["complete", "partial"])]
    sample = listed.sample(min(50, len(listed)), random_state=7)
    pd.DataFrame([{
        "id": p.id, "brand": p.brand, "name": p.name, "url": p.url,
        "n_ingredients": len(p.ingredients), "n_unmatched": len(p.unmatched),
        "unmatched_tokens": " | ".join(p.unmatched),
        "reviewer_errors_found": "", "reviewer_notes": ""} for p in sample.itertuples()
    ]).to_csv(REPORT / "manual_check_sample.csv", index=False)
    sample_tokens = int(sample.ingredients.apply(len).sum())
    sample_unmatched = int(sample.unmatched.apply(len).sum())

    pct = lambda v: f"{100 * v / len(products):.1f}%"  # noqa: E731
    lines = [
        "# Data audit — product and ingredient data (objectives O2 and O3)", "",
        f"Generated by `pipeline/build_data.py` on {date.today().isoformat()}.", "",
        "## Sources", "",
        "Products are read from each brand's official Indian online store (public Shopify "
        "catalogue feed plus the product page for the ingredient list), after checking "
        "robots.txt. Prices are the store's INR selling price on the fetch date.", "",
        "| Brand | Store | Fetched | Products in store | Kept |", "|---|---|---|---|---|",
        *[f"| {b} | {s['domain']} | {s['fetched']} | {s['raw']:,} | {s['kept']:,} |"
          for b, s in sorted(audit["stores"].items())], "",
        "## Product table (O2)", "",
        "| Step | Rows |", "|---|---|",
        f"| Products in all brand stores | {audit['raw_products']:,} |",
        f"| Removed: not a single face-care product (bundles, gifts, hair, body, make-up) | "
        f"{audit['out_of_scope']:,} |",
        f"| Removed: no price | {audit['no_price']:,} |",
        f"| Removed: duplicates (same brand + normalised name) | {audit['duplicates_removed']:,} |",
        f"| **Retained products** | **{len(products):,}** |", "",
        f"Target: at least 1,000 products retained → **{'met' if len(products) >= 1000 else 'not met'}** "
        f"({len(products):,}). Indian brand stores list far fewer face-care products than a "
        "multi-brand retailer; more brands can be added in `pipeline/fetch_brands.py`.", "",
        "| Ingredient information | Products | Share |", "|---|---|---|",
        f"| Full INCI list, complete | {comp.get('complete', 0):,} | {pct(comp.get('complete', 0))} |",
        f"| Full INCI list, partly matched | {comp.get('partial', 0):,} | {pct(comp.get('partial', 0))} |",
        f"| Key actives from name/description only | {comp.get('actives', 0):,} | {pct(comp.get('actives', 0))} |",
        f"| No ingredient information | {comp.get('missing', 0):,} | {pct(comp.get('missing', 0))} |", "",
        f"Target: ingredient list present for at least 95% of retained products → "
        f"**{100 * with_list / len(products):.1f}%, {'met' if with_list / len(products) >= .95 else 'not met'}**. "
        "Many brands do not publish the full INCI list online. Products without one are still "
        "matched to concerns through the actives they name, but are excluded whenever a user "
        "sets an ingredient restriction, because the restriction cannot be checked.", "",
        "| Category | Products |", "|---|---|",
        *[f"| {k} | {v:,} |" for k, v in products.category.value_counts().items()], "",
        "## Ingredient matching (O3)", "",
        f"Reference vocabulary: {len(cosing):,} EU CosIng INCI entries plus "
        f"{len(cureskin):,} CureSkin flagged ingredients.", "",
        "| Match method | Tokens | Share |", "|---|---|---|",
        *[f"| {k} | {method_counts[k]:,} | {100 * method_counts[k] / total_tokens:.2f}% |"
          for k in ["exact", "variant", "fuzzy", "unmatched"]], "",
        f"Tokens mapped to a reference entry: **{100 * matched / total_tokens:.2f}%**.", "",
        "*variant* = matched after a synonym (e.g. water → aqua) or after dropping bracketed "
        f"common names. *fuzzy* = RapidFuzz ratio ≥ {FUZZY_CUTOFF}.", "",
        f"Manual-check sample: {len(sample)} random products with a list, {sample_tokens:,} "
        f"tokens, {sample_unmatched} unmatched. See `report/manual_check_sample.csv`.", "",
        "### Most frequent unmatched tokens", "",
        "| Token | Count |", "|---|---|",
        *[f"| {t.replace('|', '/')} | {v} |" for t, v in unmatched_counter.most_common(25)], "",
        "## Sources considered and rejected", "",
        "- **Sephora US catalogue** (used in the mid-term prototype): real data, but not sold in "
        "India and priced in USD.",
        "- **Amazon, Flipkart, Myntra, Meesho, Nykaa prices**: their terms prohibit automated "
        "collection. The site links to a search for each product on these stores instead. Live "
        "prices need their official partner APIs (Amazon PA-API, Flipkart Affiliate API).",
        "- **Open Beauty Facts (India)**: few products with ingredient lists, no prices.", "",
    ]
    (REPORT / "data_audit.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"products={len(products)} brands={products.brand.nunique()} "
          f"ingredients={len(vocab_keys)} match={100 * matched / total_tokens:.2f}%")
    print("completeness", comp)
    print("categories", products.category.value_counts().to_dict())


if __name__ == "__main__":
    main()
