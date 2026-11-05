"""
Turn the saved brand-store feeds (data/raw/brands/*.json.gz) into clean product records.

Each record is one real product sold in India, with its INR price and MRP from the brand's own
store, the exact product URL and image, the brand's own skin-type and concern labels (from its
store tags), and the best ingredient list found on the product page or in its description.
"""

from __future__ import annotations

import gzip
import html
import json
import re
from pathlib import Path

from fetch_brands import extract_ingredient_blocks  # same parser as the collector

ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = ROOT / "data" / "raw" / "brands"
# Ingredient lists typed in from the product pack, for products whose brand does not publish one
# in its store feed. Columns: url, ingredients, checked_by, checked_on.
MANUAL_INGREDIENTS = ROOT / "data" / "manual" / "ingredients.csv"


def load_manual_ingredients() -> dict[str, str]:
    import csv

    if not MANUAL_INGREDIENTS.exists():
        return {}
    with MANUAL_INGREDIENTS.open(encoding="utf-8", newline="") as f:
        return {r["url"].strip(): r["ingredients"].strip() for r in csv.DictReader(f)
                if r.get("url") and r.get("ingredients")}

# --------------------------------------------------------------------------- scope
# Not single face-care products: bundles, gifts, samples, merchandise, hair, body, make-up.
EXCLUDE = re.compile(
    r"\b(combo|kit|duo|trio|set|sets|regime|regimen|routine|bundle|pack of \d+|\d+ ?packs?|gift|"
    r"hamper|box|sample|trial|mini[s]? set|tote|bag|pouch|vanity|merch|card|voucher|"
    r"hair|shampoo|conditioner|scalp|beard|body|bath|soap|baby|kid|underarm|roll[- ]?on|"
    r"deo|perfume|fragrance mist|foot|feet|hand ?cream|hand ?wash|nail|razor|"
    r"lipstick|kajal|kohl|eyeliner|mascara|foundation|concealer|compact|blush|"
    r"highlighter|primer|nail paint|tint stick)\b", re.I)
EXCLUDE_TYPES = re.compile(r"combo|free|gift|kit|bundle|hair|body|shampoo|make ?up|merch|"
                           r"tryplum|sample|lipstick|perfume|deo", re.I)

CATEGORY_RULES = [
    (r"\b(spf|sunscreen|sun ?screen|sun ?stick|sun ?gel|sunblock|uv)\b", "Sunscreen"),
    (r"\b(eye|under[- ]?eye)\b", "Eye care"),
    (r"\b(lip)\b", "Lip care"),
    (r"\b(face ?wash|cleanser|cleansing|foaming wash|wash|micellar|cleansing balm)\b", "Cleanser"),
    (r"\b(peel|exfoliat\w*|scrub|aha|bha)\b(?!.*\bserum\b)", "Exfoliator"),
    (r"\b(patch|patches|spot (treatment|corrector|gel)|pimple)\b", "Spot treatment"),
    (r"\b(mask|masque|clay)\b", "Mask"),
    (r"\b(toner|essence|mist|tonic)\b", "Toner"),
    (r"\b(serum|ampoule|booster|drops|elixir|concentrate|solution)\b", "Serum"),
    (r"\b(moisturi[sz]er|moisturi[sz]ing|cream|creme|lotion|gel|balm|emulsion|hydrator)\b",
     "Moisturiser"),
    (r"\b(face oil|facial oil|oil)\b(?![- ]free)", "Face oil"),
]


def category_of(title: str, product_type: str) -> str | None:
    text = f"{title} {product_type}".lower()
    for pattern, cat in CATEGORY_RULES:
        if re.search(pattern, text):
            return cat
    return None


# --------------------------------------------------------------------------- store tags
SKIN_TAGS = {
    "oily": r"\boily\b", "dry": r"\bdry\b(?! ?(hair|frizzy|scalp))", "combination": r"combination|\bcombo skin",
    "normal": r"\bnormal\b", "sensitive": r"sensitive",
}
CONCERN_TAGS = {
    "acne": r"acne|pimple|breakout|blemish", "oiliness": r"oil[- ]?control|oiliness|excess oil|sebum",
    "pores": r"pore", "dryness": r"dryness|dry skin|dehydrat|hydrat|moistur",
    "redness": r"redness|sensitiv|irritat|calm|sooth", "dark_spots": r"pigment|dark spot|acne mark|blemish|uneven|tan\b|tan[- ]removal|melasma",
    "dullness": r"dull|glow|bright|radian", "ageing": r"ageing|aging|wrinkle|fine line|firm|collagen|photoag",
    "dark_circles": r"dark circle|puff", "sun": r"\bspf\b|sun ?protect|sunscreen|uv",
}
CLAIM_TAGS = {
    "Fragrance Free": r"fragrance[- ]free|no fragrance", "Paraben Free": r"paraben[- ]free",
    "Sulphate Free": r"sulph?ate[- ]free", "Vegan": r"\bvegan\b", "Cruelty Free": r"cruelty[- ]free",
    "Non-comedogenic": r"non[- ]comedogenic", "Dermatologist Tested": r"dermatologist[- ]tested",
}


def tags_of(p: dict) -> list[str]:
    t = p.get("tags") or []
    return [x.strip().lower() for x in (t if isinstance(t, list) else t.split(",")) if x.strip()]


def labels_from_tags(tags: list[str]) -> tuple[list[str], list[str], list[str]]:
    # Only tags that talk about skin; ignore hair tags such as "dry & frizzy hair".
    skin_tags = [t for t in tags if "hair" not in t and "scalp" not in t and "body" not in t]
    joined = " | ".join(skin_tags)
    skin = sorted(k for k, pat in SKIN_TAGS.items()
                  if any(re.search(pat, t) for t in skin_tags if "skin" in t or "type" in t))
    concerns = sorted(k for k, pat in CONCERN_TAGS.items()
                      if any(re.search(pat, t) for t in skin_tags if "concern" in t or "skin" in t
                             or re.search(pat, t) and len(t) < 40))
    claims = sorted(k for k, pat in CLAIM_TAGS.items() if re.search(pat, joined))
    return skin, concerns, claims


# --------------------------------------------------------------------------- text
TAG = re.compile(r"<[^>]+>")


def plain(text: str | None) -> str:
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text or "")
    t = TAG.sub(" ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


INCI_HINT = re.compile(r"(?i)\b(aqua|water|glycerin|propanediol|butylene glycol|phenoxyethanol|"
                       r"sodium|acid|extract|oil|alcohol|xanthan|tocopher|dimethicone|peg-?\d|"
                       r"ethylhexylglycerin|disodium|carbomer|ceteareth|cetearyl)\b")


def best_ingredient_list(blocks: list[str]) -> str | None:
    """The candidate that most looks like a real INCI list (many commas, INCI vocabulary)."""
    scored = []
    for b in blocks:
        b = html.unescape(b)
        b = re.sub(r"(?i)^(full|complete|all)?\s*ingredients?\s*(list)?\s*[:\-]?\s*", "", b).strip()
        commas = b.count(",")
        hints = len(INCI_HINT.findall(b))
        if commas >= 5 and hints >= 3:
            # Cut trailing prose after the list ends (a sentence with a full stop and capital).
            b = re.split(r"\.\s+(?=[A-Z][a-z]+\s+[a-z]+\s+[a-z]+)", b)[0]
            scored.append((hints + commas, b))
    return max(scored)[1] if scored else None


def size_of(title: str, variant_title: str) -> str:
    for text in (variant_title, title):
        m = re.search(r"(\d+(?:\.\d+)?\s?(?:ml|mL|ML|g|gm|gms|G|GM|pcs|patches|N))\b", text or "")
        if m:
            return m.group(1).replace(" ", "").lower().replace("gms", "g").replace("gm", "g")
    return ""


def norm_name(s: str) -> str:
    s = re.sub(r"[^a-z0-9%]+", " ", s.lower())
    s = re.sub(r"\b(\d+(\.\d+)?\s?(ml|g|gm|gms))\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------- loader
def load_brand_products() -> tuple[list[dict], dict]:
    products, audit = [], {"stores": {}, "raw_products": 0, "out_of_scope": 0,
                           "no_price": 0, "duplicates_removed": 0, "manual_lists": 0}
    manual = load_manual_ingredients()
    for path in sorted(BRANDS_DIR.glob("*.json.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as f:
            store = json.load(f)
        brand, domain = store["brand"], store["domain"]
        kept = 0
        seen = {}
        for p in store["products"]:
            audit["raw_products"] += 1
            title = html.unescape(p.get("title", "")).strip()
            ptype = p.get("product_type") or ""
            if EXCLUDE.search(title) or EXCLUDE_TYPES.search(ptype):
                audit["out_of_scope"] += 1
                continue
            cat = category_of(title, ptype)
            if not cat:
                audit["out_of_scope"] += 1
                continue
            variants = [v for v in p.get("variants", []) if v.get("price")]
            available = [v for v in variants if v.get("available", True)] or variants
            if not available:
                audit["no_price"] += 1
                continue
            v = min(available, key=lambda x: float(x["price"]))
            price = float(v["price"])
            if price <= 0:
                audit["no_price"] += 1
                continue
            mrp = float(v["compare_at_price"]) if v.get("compare_at_price") else None
            if mrp is not None and mrp <= price:
                mrp = None
            key = norm_name(title)
            if key in seen:
                audit["duplicates_removed"] += 1
                continue
            seen[key] = True
            tags = tags_of(p)
            skin, concerns, claims = labels_from_tags(tags)
            body = plain(p.get("body_html"))
            url = f"https://{domain}/products/{p['handle']}"
            if url in manual:
                blocks = [manual[url]]
                audit["manual_lists"] += 1
            else:
                blocks = extract_ingredient_blocks(p.get("body_html") or "")
            images = p.get("images") or []
            products.append({
                "id": f"{domain.split('.')[0]}-{p['id']}",
                "name": title, "brand": brand, "category": cat, "source_category": ptype,
                "price": price, "mrp": mrp, "size": size_of(title, v.get("title", "")),
                "url": url,
                "image": images[0]["src"] if images else "",
                "store": domain, "in_stock": any(x.get("available", True) for x in variants),
                "variants": [{"title": x.get("title"), "price": float(x["price"])} for x in variants][:8],
                "skin_types": [s for s in skin if s != "sensitive"],
                "sensitive_ok": "sensitive" in skin,
                "retailer_good_for": concerns, "claims": claims,
                "ingredients_text": best_ingredient_list(blocks),
                "description": body[:600],
                "fetched": store["fetched"],
            })
            kept += 1
        audit["stores"][brand] = {"domain": domain, "raw": len(store["products"]), "kept": kept,
                                  "fetched": store["fetched"]}
    return products, audit
