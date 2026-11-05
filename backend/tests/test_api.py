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
        "category": "Serum", "budget_min": 0, "budget_max": 40,
        "avoid_families": ["fragrance", "essential_oils", "drying_alcohol"],
        "avoid_ingredients": ["linalool"], "prefer_ingredients": ["niacinamide"]}


def test_health_and_meta(client):
    assert client.get("/api/health").json()["status"] == "ok"
    m = client.get("/api/meta").json()
    assert m["products"] >= 1000
    assert "Serum" in m["categories"] and "acne" in m["concerns"]


def test_recommend_respects_every_hard_rule(client):
    cat = get_catalogue()
    r = client.post("/api/recommend", json={**BASE, "limit": 20}).json()
    assert r["results"]
    for item in r["results"]:
        p = cat.products[item["product"]["id"]]
        assert p.category == "Serum"
        assert 0 <= p.effective_price <= 40
        assert p.completeness != "missing"
        for i in p.ingredient_ids:
            ing = cat.ingredients[i]
            assert ing.key != "linalool"
            assert not set(ing.families) & set(BASE["avoid_families"])
        assert len(item["reasons"]) >= 3


def test_funnel_adds_up(client):
    r = client.post("/api/recommend", json=BASE).json()
    assert r["eligible"] + sum(r["excluded"].values()) == r["total"]


def test_results_are_sorted_by_score(client):
    scores = [x["score"] for x in client.post("/api/recommend", json={**BASE, "limit": 30})
              .json()["results"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("patch, message", [
    ({"budget_min": 60}, "minimum budget is above the maximum"),
    ({"skin_type": "purple"}, "skin type"),
    ({"concerns": ["acne", "dryness", "redness", "pores", "ageing"]}, "up to four"),
    ({"prefer_ingredients": ["linalool"]}, "both preferred and avoided"),
    ({"avoid_ingredients": ["not-an-ingredient"]}, "Unknown ingredient"),
])
def test_invalid_profiles_are_rejected(client, patch, message):
    r = client.post("/api/recommend", json={**BASE, **patch})
    assert r.status_code == 422
    assert any(message in e for e in r.json()["detail"]["errors"])


def test_unused_components_are_left_out():
    cat = get_catalogue()
    res = recommend(cat, Profile(skin_type="dry", budget_min=0, budget_max=30), explain_top=1)
    assert set(res.ranked[0].parts) == {"k", "b"}


def test_product_search_and_detail(client):
    r = client.get("/api/products", params={"q": "niacinamide", "category": "Serum"}).json()
    assert r["total"] > 10
    d = client.get(f"/api/products/{r['items'][0]['id']}").json()
    assert d["ingredients"] and all(s["category"] == "Serum" for s in d["similar"])
    assert client.get("/api/products/does-not-exist").status_code == 404


def test_product_filters(client):
    r = client.get("/api/products", params={"max_price": 15, "avoid": ["fragrance"],
                                            "page_size": 100}).json()
    assert all(p["effective_price"] <= 15 and "fragrance" not in p["families"]
               for p in r["items"])


def test_ingredients(client):
    r = client.get("/api/ingredients", params={"q": "linal"}).json()
    assert r["items"][0]["key"] == "linalool"
    d = client.get("/api/ingredients/niacinamide").json()
    assert d["product_count"] > 100 and d["top_products"]
