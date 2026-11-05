"""
Collect real Indian skincare products from brands' official online stores.

Most Indian direct-to-consumer skincare brands run on Shopify, which publishes each store's
catalogue at /products.json (names, INR prices, MRP, sizes, images, product URLs, descriptions).
This script checks each store's robots.txt, then downloads only that feed (a few requests per
brand) with a delay between requests and backoff when rate limited. Everything is saved under
data/raw/brands/ with the fetch date, so the pipeline never needs the network.

Product pages are not downloaded: the stores protect them with a bot check, and this collector
does not try to get around it. Ingredient lists come from the feed description when the brand
includes one there, or from data/manual/ingredients.csv (typed in from the pack).

Run from the repository root:  python pipeline/fetch_brands.py [--only domain ...]
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "brands"
UA = ("Mozilla/5.0 (compatible; SkinAnalyzerResearch/1.0; "
      "+https://github.com/harsha-516/ai-skincare-product-analyzer)")
DELAY = 2.0  # seconds between requests to the same store

# Brand name -> official store domain.
BRANDS = {
    "Minimalist": "beminimalist.co",
    "The Derma Co": "thedermaco.com",
    "Dr. Sheth's": "drsheths.com",
    "Plum": "plumgoodness.com",
    "Dot & Key": "dotandkey.com",
    "Deconstruct": "thedeconstruct.in",
    "Re'equil": "reequil.com",
    "Pilgrim": "discoverpilgrim.com",
    "mCaffeine": "mcaffeine.com",
    "Foxtale": "foxtale.in",
    "Aqualogica": "aqualogica.in",
    "Chemist at Play": "chemistatplay.com",
    "The Conscious Chemist": "theconsciouschemist.com",
    "Bare Anatomy": "bareanatomy.com",
    "Hyphen": "letshyphen.com",
    "Suganda": "suganda.co",
    "Earth Rhythm": "earthrhythm.com",
    "Fixderma": "fixderma.com",
}


def get(url: str, timeout: int = 30, retries: int = 4) -> tuple[int, bytes]:
    """GET with backoff: a 429 (rate limited) or 5xx waits as the store asks, then retries."""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return r.status, body
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                wait = e.headers.get("Retry-After")
                time.sleep(float(wait) if wait and wait.isdigit() else 10 * (attempt + 1))
                continue
            return e.code, b""
        except Exception:
            time.sleep(5 * (attempt + 1))
    return 0, b""


def robots_for(domain: str) -> urllib.robotparser.RobotFileParser:
    rp = urllib.robotparser.RobotFileParser()
    status, body = get(f"https://{domain}/robots.txt")
    rp.parse(body.decode("utf-8", "ignore").splitlines() if status == 200 else [])
    return rp


def fetch_feed(domain: str, rp) -> list[dict]:
    if not rp.can_fetch(UA, f"https://{domain}/products.json"):
        print(f"  robots.txt disallows the feed on {domain}; skipped")
        return []
    products = []
    for page in range(1, 21):
        status, body = get(f"https://{domain}/products.json?limit=250&page={page}")
        time.sleep(DELAY)
        if status != 200:
            break
        try:
            batch = json.loads(body)["products"]
        except (ValueError, KeyError):
            break
        if not batch:
            break
        products += batch
    return products


# Rough filter for face/lip skincare, used when inspecting feeds.
SKIN_WORDS = re.compile(
    r"serum|cleanser|face ?wash|moisturi[sz]er|cream|gel|sunscreen|spf|toner|essence|mask|"
    r"peel|exfoliat|scrub|eye|lip|balm|oil|lotion|mist|patch|treatment", re.I)
NOT_SKIN = re.compile(r"hair|shampoo|conditioner|body|baby|combo|kit|set of|bundle|gift|bag|"
                      r"tote|perfume|deo|roll on|underarm|foot|hand cream|nail|razor", re.I)


def wanted(p: dict) -> bool:
    text = f"{p.get('title', '')} {p.get('product_type', '')}"
    return bool(SKIN_WORDS.search(text)) and not NOT_SKIN.search(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="limit to these domains")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    summary_path = OUT / "_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    for brand, domain in BRANDS.items():
        if args.only and domain not in args.only:
            continue
        print(f"{brand} ({domain})")
        rp = robots_for(domain)
        products = fetch_feed(domain, rp)
        if not products:
            print("  no public feed")
            summary[brand] = {"domain": domain, "products": 0}
            continue
        record = {"brand": brand, "domain": domain, "fetched": date.today().isoformat(),
                  "products": products}
        path = OUT / f"{domain}.json.gz"
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(record, f)
        summary[brand] = {"domain": domain, "products": len(products)}
        print(f"  {len(products)} products", flush=True)
    summary_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- description parsing
TAG = re.compile(r"<[^>]+>")
HEAD = re.compile(r"(?i)(full\s+ingredients?(\s+list)?|ingredients?\s+list|all\s+ingredients|"
                  r"ingredients|inci)\s*[:\-]?")


def text_of(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|tr|span)>", "\n", html)
    t = TAG.sub(" ", html)
    t = re.sub(r"&nbsp;|&#160;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"&#?\w+;", " ", t)
    return re.sub(r"[ \t]+", " ", t)


def extract_ingredient_blocks(html: str) -> list[str]:
    """Candidate INCI lists: text right after an 'Ingredients' heading that reads like a
    comma-separated list. Kept as raw strings; the pipeline picks and cleans the best one."""
    t = text_of(html)
    out = []
    for m in HEAD.finditer(t):
        chunk = t[m.end(): m.end() + 2500].strip()
        # Stop at the next obvious section heading.
        chunk = re.split(r"\n\s*(how to use|directions|benefits|key benefits|who is it for|"
                         r"faq|frequently asked|reviews|disclaimer|caution|net (vol|qty|wt))",
                         chunk, flags=re.I)[0]
        chunk = re.sub(r"\s*\n\s*", " ", chunk).strip()
        if chunk.count(",") >= 5 and chunk not in out:
            out.append(chunk[:2500])
    # Lists without a heading: almost every INCI list starts with water.
    water = r"(?i)\b(aqua|water|purified water|deionized water)\b\s*(\([^)]*\))?\s*,"
    for m in re.finditer(water, t):
        run = re.split(r"\n\s*\n|\.\s+(?=[A-Z][a-z]+ )", t[m.start(): m.start() + 2500])[0]
        run = re.sub(r"\s*\n\s*", " ", run).strip()
        if run.count(",") >= 8 and run not in out:
            out.append(run)
    return out[:15]


if __name__ == "__main__":
    sys.exit(main())
