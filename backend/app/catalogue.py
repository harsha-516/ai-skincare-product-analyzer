"""Read-only access to data/skincare.db, plus an in-memory catalogue for the recommender."""

from __future__ import annotations

import json
import math
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("SKINCARE_DB", ROOT / "data" / "skincare.db"))


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Build it with:  python pipeline/build_data.py")
    # Read-only, so a running server can never modify the database.
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


@dataclass
class Ingredient:
    id: int
    key: str
    name: str
    function: str
    cureskin_function: str
    eu_restriction: str
    comedogenic: int | None
    product_count: int
    families: list[str] = field(default_factory=list)
    concerns: dict[str, float] = field(default_factory=dict)


@dataclass
class Product:
    id: str
    name: str
    brand: str
    category: str
    price: float
    sale_price: float | None
    effective_price: float
    size: str
    rating: float | None
    reviews: int
    loves: int
    completeness: str
    unmatched_count: int
    skin_types: list[str]
    retailer_good_for: list[str]
    claims: list[str]
    ingredient_ids: list[int] = field(default_factory=list)
    families: set[str] = field(default_factory=set)
    concern_strength: dict[str, float] = field(default_factory=dict)
    concern_evidence: dict[str, list[str]] = field(default_factory=dict)

    @cached_property
    def ingredient_id_set(self) -> frozenset[int]:
        return frozenset(self.ingredient_ids)


class Catalogue:
    def __init__(self, con: sqlite3.Connection):
        self.con = con
        self.meta = {r["key"]: json.loads(r["value"]) for r in con.execute("SELECT * FROM meta")}
        self.concerns = {r["id"]: r["label"] for r in con.execute("SELECT * FROM concerns")}
        self.families = {r["id"]: r["label"] for r in con.execute("SELECT * FROM families")}

        self.ingredients: dict[int, Ingredient] = {}
        for r in con.execute("SELECT * FROM ingredients"):
            self.ingredients[r["id"]] = Ingredient(
                r["id"], r["key"], r["name"], r["function"], r["cureskin_function"],
                r["eu_restriction"], r["comedogenic"], r["product_count"])
        for r in con.execute("SELECT * FROM ingredient_families"):
            self.ingredients[r["ingredient_id"]].families.append(r["family"])
        for r in con.execute("SELECT * FROM ingredient_concerns"):
            self.ingredients[r["ingredient_id"]].concerns[r["concern"]] = r["strength"]
        self.by_key = {i.key: i for i in self.ingredients.values()}

        self.products: dict[str, Product] = {}
        for r in con.execute("SELECT * FROM products"):
            self.products[r["id"]] = Product(
                r["id"], r["name"], r["brand"], r["category"], r["price_usd"],
                r["sale_price_usd"], r["effective_price"], r["size"], r["rating"], r["reviews"],
                r["loves"], r["completeness"], r["unmatched_count"], json.loads(r["skin_types"]),
                json.loads(r["retailer_good_for"]), json.loads(r["claims"]))
        for r in con.execute("SELECT * FROM product_ingredients ORDER BY product_id, position"):
            self.products[r["product_id"]].ingredient_ids.append(r["ingredient_id"])
        for r in con.execute("SELECT * FROM product_families"):
            self.products[r["product_id"]].families.add(r["family"])
        for r in con.execute("SELECT * FROM product_concerns"):
            p = self.products[r["product_id"]]
            p.concern_strength[r["concern"]] = r["strength"]
            p.concern_evidence[r["concern"]] = json.loads(r["evidence"])

        self.categories = Counter(p.category for p in self.products.values())
        # IDF weights for "similar products" (TF-IDF cosine over ingredient sets).
        n = len(self.products)
        df = Counter(i for p in self.products.values() for i in p.ingredient_id_set)
        self.idf = {i: math.log((1 + n) / (1 + c)) + 1 for i, c in df.items()}
        self._norm = {pid: math.sqrt(sum(self.idf[i] ** 2 for i in p.ingredient_id_set))
                      for pid, p in self.products.items()}

    def ingredient_by_key(self, key: str) -> Ingredient | None:
        return self.by_key.get(key)

    def similar(self, product: Product, k: int = 4) -> list[tuple[Product, float]]:
        """Products in the same category with the most similar ingredient lists."""
        a = product.ingredient_id_set
        if not a:
            return []
        na = self._norm[product.id]
        out = []
        for p in self.products.values():
            if p.id == product.id or p.category != product.category or not p.ingredient_ids:
                continue
            dot = sum(self.idf[i] ** 2 for i in a & p.ingredient_id_set)
            if dot:
                out.append((p, dot / (na * self._norm[p.id])))
        out.sort(key=lambda x: -x[1])
        return out[:k]

    def search_ids(self, q: str) -> list[str]:
        """Full-text search over name, brand and ingredient names (prefix match per word)."""
        words = [w for w in "".join(ch if ch.isalnum() else " " for ch in q.lower()).split() if w]
        if not words:
            return []
        expr = " ".join(f'"{w}"*' for w in words)
        rows = self.con.execute(
            "SELECT product_id FROM products_fts WHERE products_fts MATCH ? ORDER BY rank",
            (expr,)).fetchall()
        return [r["product_id"] for r in rows]


_catalogue: Catalogue | None = None


def get_catalogue() -> Catalogue:
    global _catalogue
    if _catalogue is None:
        _catalogue = Catalogue(connect())
    return _catalogue
