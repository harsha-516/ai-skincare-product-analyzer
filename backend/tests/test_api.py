"""API and recommender tests. Run from the repository root:  python -m pytest"""

import pytest
from fastapi.testclient import TestClient

from backend.app.catalogue import get_catalogue
from backend.app.main import app
from backend.app.recommender import Profile, recommend


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


BASE = {"skin_type": "oily", "sensitivity": "high", "concerns": ["acne", "dark_spots"],
        "category": "Serum", "budget_min": 0, "budget_max": 1200,
        "avoid_families": ["fragrance", "essential_oils", "drying_alcohol"],
        "avoid_ingredients": [], "prefer_ingredients": []}


def test_health_and_meta(client):
    assert client.get("/api/health").json()["status"] == "ok"
    m = client.get("/api/meta").json()
    assert m["currency"] == "INR"
    assert m["products"] >= 300 and m["brands"] >= 8
    assert "Serum" in m["categories"] and "acne" in m["concerns"]


def test_every_product_links_to_its_own_page_on_an_indian_brand_store():
    for p in get_catalogue().products.values():
        assert p.url == f"https://{p.store}/products/{p.url.rsplit('/', 1)[1]}"
        assert p.price > 0
        assert "sephora" not in p.url


@pytest.mark.parametrize("q, brand", [("minimalist", "Minimalist"), ("derma co", "The Derma Co"),
                                      ("dr sheth", "Dr. Sheth's")])
def test_search_finds_indian_brands(client, q, brand):
    r = client.get("/api/products", params={"q": q, "page_size": 100}).json()
    assert r["total"] > 0
    assert sum(p["brand"] == brand for p in r["items"]) >= len(r["items"]) // 2


@pytest.mark.parametrize("q", ["dermaco", "domaco"])
def test_brand_aliases_and_misspellings(client, q):
    r = client.get("/api/products", params={"q": q, "page_size": 100}).json()
    assert r["total"] > 0 and all(p["brand"] == "The Derma Co" for p in r["items"])


def test_recommend_respects_every_hard_rule(client):
    cat = get_catalogue()
    r = client.post("/api/recommend", json={**BASE, "limit": 20}).json()
    assert r["results"], "expected at least one eligible serum"
    for item in r["results"]:
        p = cat.products[item["product"]["id"]]
        assert p.category == "Serum"
        assert 0 <= p.effective_price <= 1200
        assert p.has_full_list, "restrictions can only be checked against a full ingredient list"
        for i in p.ingredient_ids:
            assert not set(cat.ingredients[i].families) & set(BASE["avoid_families"])
        assert len(item["reasons"]) >= 2  # budget fit + confirmation of what was avoided
        assert item["product"]["shop_links"][0]["url"] == p.url


def test_without_restrictions_products_without_full_lists_are_eligible(client):
    r = client.post("/api/recommend", json={**BASE, "avoid_families": [], "limit": 50}).json()
    cat = get_catalogue()
    assert any(not cat.products[x["product"]["id"]].has_full_list for x in r["results"])


def test_funnel_adds_up(client):
    r = client.post("/api/recommend", json=BASE).json()
    assert r["eligible"] + sum(r["excluded"].values()) == r["total"]


def test_results_are_sorted_by_score(client):
    scores = [x["score"] for x in client.post("/api/recommend", json={**BASE, "avoid_families": [],
                                                                       "limit": 30}).json()["results"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("patch, message", [
    ({"budget_min": 2000}, "minimum budget is above the maximum"),
    ({"skin_type": "purple"}, "skin type"),
    ({"concerns": ["acne", "dryness", "redness", "pores", "ageing"]}, "up to four"),
    ({"prefer_ingredients": ["niacinamide"], "avoid_ingredients": ["niacinamide"]},
     "both preferred and avoided"),
    ({"avoid_ingredients": ["not-an-ingredient"]}, "Unknown ingredient"),
])
def test_invalid_profiles_are_rejected(client, patch, message):
    r = client.post("/api/recommend", json={**BASE, **patch})
    assert r.status_code == 422
    assert any(message in e for e in r.json()["detail"]["errors"])


def test_unused_components_are_left_out():
    cat = get_catalogue()
    res = recommend(cat, Profile(skin_type="dry", budget_min=0, budget_max=800), explain_top=1)
    assert set(res.ranked[0].parts) == {"k", "b"}


def test_prices_in_explanations_are_rupees(client):
    r = client.post("/api/recommend", json={**BASE, "avoid_families": []}).json()
    assert "₹" in r["results"][0]["reasons"][0] and "$" not in r["results"][0]["reasons"][0]


def test_product_detail_has_store_and_marketplace_links(client):
    r = client.get("/api/products", params={"category": "Serum"}).json()
    d = client.get(f"/api/products/{r['items'][0]['id']}").json()
    stores = [x["store"] for x in d["shop_links"]]
    assert stores[0] == "official" and d["shop_links"][0]["exact"]
    assert {"amazon", "flipkart", "nykaa", "myntra", "meesho"} <= set(stores)
    assert all(s["category"] == "Serum" for s in d["similar"])
    assert client.get("/api/products/does-not-exist").status_code == 404


def test_product_filters(client):
    r = client.get("/api/products", params={"max_price": 500, "avoid": ["fragrance"],
                                            "page_size": 100}).json()
    assert all(p["effective_price"] <= 500 and p["has_full_list"] and "fragrance" not in p["families"]
               for p in r["items"])
    b = client.get("/api/products", params={"brand": ["Minimalist"], "page_size": 100}).json()
    assert b["total"] > 0 and all(p["brand"] == "Minimalist" for p in b["items"])


def test_ingredients(client):
    d = client.get("/api/ingredients/niacinamide").json()
    assert d["product_count"] >= 1
    # Common allergens can be avoided even if no published list contains them yet.
    assert client.get("/api/ingredients", params={"q": "linalool"}).json()["total"] >= 1
