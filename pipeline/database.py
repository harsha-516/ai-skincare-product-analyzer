"""
SQLite schema and writer for the product and ingredient database (data/skincare.db).

The backend reads this database; the pipeline is the only thing that writes it.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL              -- JSON
);

CREATE TABLE concerns (
    id    TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

CREATE TABLE families (
    id    TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

CREATE TABLE ingredients (
    id                INTEGER PRIMARY KEY,
    key               TEXT NOT NULL UNIQUE,   -- canonical lower-case INCI name
    name              TEXT NOT NULL,
    function          TEXT NOT NULL DEFAULT '',  -- EU CosIng function
    cureskin_function TEXT NOT NULL DEFAULT '',
    eu_restriction    TEXT NOT NULL DEFAULT '',  -- CosIng Annex reference, if restricted
    cosing_ref        TEXT NOT NULL DEFAULT '',
    comedogenic       INTEGER,                   -- 0–5, NULL = not rated
    product_count     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE ingredient_families (
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    family        TEXT    NOT NULL REFERENCES families(id),
    PRIMARY KEY (ingredient_id, family)
);

CREATE TABLE ingredient_concerns (
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    concern       TEXT    NOT NULL REFERENCES concerns(id),
    strength      REAL    NOT NULL,              -- 1.0 targeted active, 0.5 supporting
    PRIMARY KEY (ingredient_id, concern)
);

CREATE TABLE products (
    id               TEXT PRIMARY KEY,           -- <store>-<shopify product id>
    name             TEXT NOT NULL,
    brand            TEXT NOT NULL,
    category         TEXT NOT NULL,
    source_category  TEXT NOT NULL DEFAULT '',   -- the store's own product type
    price_inr        REAL NOT NULL,              -- lowest in-stock variant on the brand store
    mrp_inr          REAL,                       -- compare-at price, when higher than price
    effective_price  REAL NOT NULL,              -- = price_inr (kept for filters and sorting)
    size             TEXT NOT NULL DEFAULT '',
    url              TEXT NOT NULL,              -- exact product page on the brand store
    image_url        TEXT NOT NULL DEFAULT '',
    store            TEXT NOT NULL,              -- store domain
    in_stock         INTEGER NOT NULL DEFAULT 1,
    variants         TEXT NOT NULL DEFAULT '[]', -- JSON [{title, price}]
    description      TEXT NOT NULL DEFAULT '',
    featured_rank    INTEGER NOT NULL DEFAULT 0, -- position in the brand store's own listing
    rating           REAL,                       -- not published by brand stores yet
    reviews          INTEGER NOT NULL DEFAULT 0,
    completeness     TEXT NOT NULL CHECK (completeness IN ('complete', 'partial', 'actives', 'missing')),
    unmatched_count  INTEGER NOT NULL DEFAULT 0,
    skin_types       TEXT NOT NULL DEFAULT '[]', -- JSON, from the brand's store tags
    retailer_good_for TEXT NOT NULL DEFAULT '[]',-- JSON, concern tags from the brand's store
    claims           TEXT NOT NULL DEFAULT '[]', -- JSON, e.g. "Fragrance Free"
    fetched          TEXT NOT NULL DEFAULT ''    -- date the store was read
);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_price ON products(effective_price);

CREATE TABLE product_ingredients (
    product_id    TEXT    NOT NULL REFERENCES products(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id),
    position      INTEGER NOT NULL,              -- order on the label, 0 = first
    PRIMARY KEY (product_id, ingredient_id)
);
CREATE INDEX idx_pi_ingredient ON product_ingredients(ingredient_id);

CREATE TABLE product_families (
    product_id TEXT NOT NULL REFERENCES products(id),
    family     TEXT NOT NULL REFERENCES families(id),
    PRIMARY KEY (product_id, family)
);
CREATE INDEX idx_pf_family ON product_families(family);

CREATE TABLE product_concerns (
    product_id TEXT NOT NULL REFERENCES products(id),
    concern    TEXT NOT NULL REFERENCES concerns(id),
    strength   REAL NOT NULL,
    evidence   TEXT NOT NULL,                    -- JSON list of ingredient names, strongest first
    PRIMARY KEY (product_id, concern)
);

CREATE VIRTUAL TABLE products_fts USING fts5(
    product_id UNINDEXED, name, brand, ingredients, tokenize = 'unicode61 remove_diacritics 2'
);
"""


def write_database(path: Path, rows, families_per_product, evidence_per_product,
                   strength_per_product, ingredient_rows, concerns: dict, families: dict,
                   stats: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        con.executescript(SCHEMA)
        con.executemany("INSERT INTO meta VALUES (?, ?)",
                        [(k, json.dumps(v)) for k, v in stats.items()])
        con.executemany("INSERT INTO concerns VALUES (?, ?)", concerns.items())
        con.executemany("INSERT INTO families VALUES (?, ?)", families.items())

        ing_id = {}
        for i, r in enumerate(ingredient_rows, start=1):
            ing_id[r["key"]] = i
            con.execute(
                "INSERT INTO ingredients VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (i, r["key"], r["name"], r["function"] or "", r["cureskin_function"] or "",
                 r["eu_restriction"] or "", r["cosing_ref"] or "", r["comedogenic"],
                 r["product_count"]))
            con.executemany("INSERT INTO ingredient_families VALUES (?, ?)",
                            [(i, f) for f in r["families"]])
            con.executemany("INSERT INTO ingredient_concerns VALUES (?, ?, ?)",
                            [(i, c, s) for c, s in r["concerns"].items()])
        names = {r["key"]: r["name"] for r in ingredient_rows}

        for p, fams, ev, cs in zip(rows, families_per_product, evidence_per_product,
                                   strength_per_product):
            con.execute(
                "INSERT INTO products VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (p["id"], p["name"], p["brand"], p["category"], p["source_category"] or "",
                 p["price"], p["mrp"], p["price"], p["size"], p["url"], p["image"], p["store"],
                 int(p["in_stock"]), json.dumps(p["variants"]), p["description"],
                 p["featured_rank"], None, 0, p["completeness"], len(p["unmatched"]),
                 json.dumps(p["skin_types"]), json.dumps(p["retailer_good_for"]),
                 json.dumps(p["claims"]), p["fetched"]))
            matched = [k for k in p["ingredients"] if k in ing_id]
            con.executemany("INSERT INTO product_ingredients VALUES (?, ?, ?)",
                            [(p["id"], ing_id[k], pos) for pos, k in enumerate(matched)])
            con.executemany("INSERT INTO product_families VALUES (?, ?)",
                            [(p["id"], f) for f in fams])
            con.executemany(
                "INSERT INTO product_concerns VALUES (?, ?, ?, ?)",
                [(p["id"], c, cs[c], json.dumps(list(dict.fromkeys(ev[c]))[:4])) for c in cs])
            # Brand aliases so "dermaco", "thedermaco" or "drsheths" also match.
            compact = "".join(ch for ch in p["brand"].lower() if ch.isalnum())
            aliases = {compact, compact.removeprefix("the"), compact.removesuffix("s")}
            active_names = " ".join(n for n, _ in p.get("named_actives", []))
            con.execute("INSERT INTO products_fts VALUES (?, ?, ?, ?)",
                        (p["id"], p["name"], f"{p['brand']} {' '.join(sorted(aliases))}",
                         f"{' '.join(names[k] for k in matched)} {active_names}"))
        con.commit()
        con.execute("VACUUM")
    finally:
        con.close()
    tmp.replace(path)
