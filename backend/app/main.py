"""
SkinAnalyzer API.

Run from the repository root:
    uvicorn backend.app.main:app --reload

The API lives under /api; everything else is the frontend in frontend/.
Interactive docs: /api/docs
"""

from __future__ import annotations

import math
import os
import re
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from urllib.parse import quote, quote_plus

from pydantic import BaseModel, Field

from collections import Counter

from .catalogue import ROOT, Catalogue, Product, get_catalogue
from .recommender import Profile, recommend, validate

FRONTEND = ROOT / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_catalogue()  # load the database once at startup
    yield


app = FastAPI(title="SkinAnalyzer API", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")

@app.middleware("http")
async def revalidate_frontend(request, call_next):
    # Browsers revalidate frontend files (cheap 304 via ETag) so updates show up immediately.
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


# Only needed when the frontend is hosted on a different origin than the API.
origins = [o for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])


# --------------------------------------------------------------------------- serialisers
def key_actives(p: Product, cat: Catalogue) -> list[dict]:
    """Strongest ingredient behind each fully matched concern, grouped by ingredient."""
    by_ing: dict[str, list[str]] = {}
    for c, strength in p.concern_strength.items():
        if strength == 1 and p.concern_evidence.get(c):
            by_ing.setdefault(p.concern_evidence[c][0], []).append(c)
    return [{"ingredient": k, "concerns": v} for k, v in by_ing.items()]


def shop_links(p: Product) -> list[dict]:
    """The exact product on the brand's own store, then a search for it on marketplaces.
    Marketplace prices are not shown: their terms do not allow automated price collection."""
    q = re.sub(r"\s*[-|]\s*\d+(\.\d+)?\s?(ml|g|gm)\b.*$", "", p.name, flags=re.I)
    q = q.split(" | ")[0].strip()  # drop marketing tails such as "| with 10% Niacinamide"
    q = f"{p.brand} {q}".strip()
    slug = re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")
    return [
        {"store": "official", "label": f"{p.brand} official store", "url": p.url, "exact": True},
        {"store": "amazon", "label": "Amazon", "url": f"https://www.amazon.in/s?k={quote_plus(q)}", "exact": False},
        {"store": "flipkart", "label": "Flipkart", "url": f"https://www.flipkart.com/search?q={quote_plus(q)}", "exact": False},
        {"store": "nykaa", "label": "Nykaa", "url": f"https://www.nykaa.com/search/result/?q={quote_plus(q)}", "exact": False},
        {"store": "myntra", "label": "Myntra", "url": f"https://www.myntra.com/{quote(slug)}", "exact": False},
        {"store": "meesho", "label": "Meesho", "url": f"https://www.meesho.com/search?q={quote_plus(q)}", "exact": False},
        {"store": "purplle", "label": "Purplle", "url": f"https://www.purplle.com/search?q={quote_plus(q)}", "exact": False},
    ]


def product_summary(p: Product, cat: Catalogue) -> dict:
    return {
        "id": p.id, "name": p.name, "brand": p.brand, "category": p.category,
        "price": p.price, "mrp": p.mrp, "effective_price": p.effective_price,
        "discount_pct": round(100 * (1 - p.price / p.mrp)) if p.mrp else 0,
        "size": p.size, "url": p.url, "image": p.image_url, "store": p.store,
        "in_stock": p.in_stock, "rating": p.rating, "reviews": p.reviews,
        "skin_types": p.skin_types, "families": sorted(p.families),
        "completeness": p.completeness, "has_full_list": p.has_full_list,
        "ingredient_count": len(p.ingredient_ids), "key_actives": key_actives(p, cat),
        "fragrance_free": p.has_full_list and "fragrance" not in p.families,
    }


def ingredient_summary(i) -> dict:
    return {"key": i.key, "name": i.name, "function": i.function,
            "cureskin_function": i.cureskin_function, "eu_restriction": i.eu_restriction,
            "comedogenic": i.comedogenic, "families": i.families, "concerns": i.concerns,
            "product_count": i.product_count}


# --------------------------------------------------------------------------- routes
@app.get("/api/health")
def health():
    return {"status": "ok", "products": len(get_catalogue().products)}


@app.get("/api/meta")
def meta():
    cat = get_catalogue()
    m = cat.meta
    return {
        "products": m["products"], "brands": m["brands"], "ingredients": m["ingredients"],
        "token_match_rate": m["token_match_rate"], "built": m["built"],
        "price_min": m["price_min"], "price_max": m["price_max"], "price_median": m.get("price_median"),
        "currency": "INR", "stores": m.get("stores", {}),
        "brand_counts": dict(sorted(Counter(p.brand for p in cat.products.values()).items())),
        "categories": dict(cat.categories.most_common()),
        "concerns": cat.concerns, "families": cat.families,
        # Products with a targeted active for each concern (strength 1.0).
        "concern_counts": {c: sum(p.concern_strength.get(c) == 1 for p in cat.products.values())
                           for c in cat.concerns},
    }


SORTS = {
    # Each brand store's own order, interleaved, with out-of-stock products last.
    "featured": lambda p: (not p.in_stock, p.featured_rank, p.brand),
    "price_asc": lambda p: p.effective_price,
    "price_desc": lambda p: -p.effective_price,
    "discount": lambda p: -(1 - p.price / p.mrp if p.mrp else 0),
}


@app.get("/api/products")
def list_products(
    q: str = "", category: str | None = None, max_price: float | None = Query(None, ge=0),
    concern: str | None = None, skin_type: str | None = None, brand: list[str] = Query(default=[]),
    avoid: list[str] = Query(default=[], description="Ingredient families to exclude"),
    sort: Literal["featured", "price_asc", "price_desc", "discount", "relevance"] = "featured",
    page: int = Query(1, ge=1), page_size: int = Query(24, ge=1, le=100),
):
    cat = get_catalogue()
    corrected = None
    if q.strip():
        ids = cat.search_ids(q)
        if not ids and (corrected := cat.closest_brand(q)):
            ids = [p.id for p in cat.products.values() if p.brand == corrected]
        items = [cat.products[i] for i in ids]
    else:
        items = list(cat.products.values())
    if category:
        items = [p for p in items if p.category == category]
    if brand:
        items = [p for p in items if p.brand in brand]
    if max_price is not None:
        items = [p for p in items if p.effective_price <= max_price]
    if concern:
        items = [p for p in items if p.concern_strength.get(concern) == 1]
    if skin_type:
        items = [p for p in items if skin_type in p.skin_types]
    if avoid:
        items = [p for p in items if p.has_full_list and not p.families.intersection(avoid)]
    if sort != "relevance" or not q.strip():
        items.sort(key=SORTS["featured" if sort == "relevance" else sort])
    start = (page - 1) * page_size
    return {"total": len(items), "page": page, "page_size": page_size, "corrected_to": corrected,
            "items": [product_summary(p, cat) for p in items[start:start + page_size]]}


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    cat = get_catalogue()
    p = cat.products.get(product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return {
        **product_summary(p, cat),
        "claims": p.claims, "unmatched_count": p.unmatched_count,
        "description": p.description, "variants": p.variants, "shop_links": shop_links(p),
        "concerns": [{"concern": c, "label": cat.concerns[c], "strength": s,
                      "evidence": p.concern_evidence.get(c, [])}
                     for c, s in sorted(p.concern_strength.items(), key=lambda x: -x[1])],
        "ingredients": [ingredient_summary(cat.ingredients[i]) for i in p.ingredient_ids],
        "similar": [{**product_summary(s, cat), "similarity": round(sim, 3)}
                    for s, sim in cat.similar(p)],
    }


@app.get("/api/ingredients")
def list_ingredients(q: str = "", family: str | None = None, concern: str | None = None,
                     limit: int = Query(40, ge=1, le=200), offset: int = Query(0, ge=0)):
    cat = get_catalogue()
    q = q.strip().lower()
    items = list(cat.ingredients.values())
    if q:
        items = [i for i in items if q in i.key or q in i.name.lower()]
        items.sort(key=lambda i: (not (i.key.startswith(q) or i.name.lower().startswith(q)),
                                  -i.product_count))
    else:
        items.sort(key=lambda i: -i.product_count)
    if family:
        items = [i for i in items if family in i.families]
    if concern:
        items = [i for i in items if concern in i.concerns]
    return {"total": len(items),
            "items": [ingredient_summary(i) for i in items[offset:offset + limit]]}


@app.get("/api/ingredients/{key}")
def get_ingredient(key: str):
    cat = get_catalogue()
    i = cat.ingredient_by_key(key.lower())
    if not i:
        raise HTTPException(404, "Ingredient not found")
    products = [p for p in cat.products.values() if i.id in p.ingredient_id_set]
    products.sort(key=SORTS["featured"])
    return {**ingredient_summary(i), "family_labels": {f: cat.families[f] for f in i.families},
            "top_products": [product_summary(p, cat) for p in products[:8]]}


class ProfileIn(BaseModel):
    skin_type: str
    sensitivity: Literal["low", "high"] = "low"
    concerns: list[str] = Field(default_factory=list)
    category: str = "any"
    budget_min: float = 0
    budget_max: float = 1000
    avoid_families: list[str] = Field(default_factory=list)
    avoid_ingredients: list[str] = Field(default_factory=list)
    prefer_ingredients: list[str] = Field(default_factory=list)
    limit: int = Field(5, ge=1, le=50)


@app.post("/api/recommend")
def post_recommend(body: ProfileIn):
    cat = get_catalogue()
    u = Profile(**body.model_dump(exclude={"limit"}))
    errors = validate(u, cat)
    if errors:
        raise HTTPException(422, {"errors": errors})
    res = recommend(cat, u, explain_top=body.limit)
    return {
        "total": len(cat.products), "eligible": res.eligible_count, "excluded": res.excluded,
        "results": [{"product": {**product_summary(s.product, cat), "shop_links": shop_links(s.product)},
                     "score": round(s.score, 4),
                     "parts": {k: round(v, 4) for k, v in s.parts.items()},
                     "reasons": s.reasons, "warnings": s.warnings}
                    for s in res.ranked[:body.limit]],
    }


@app.get("/api/{rest:path}", include_in_schema=False)
def api_not_found(rest: str):
    raise HTTPException(404, "Not found")


if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
