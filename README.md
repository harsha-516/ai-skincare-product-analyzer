# SkinAnalyzer: AI Skincare Product Analyzer

An ingredient-aware skincare recommender for India. You give it your skin type, sensitivity,
concerns, budget in rupees, the product type you want and the ingredients you avoid. Products
that break any of your rules are removed **before** scoring. The rest are ranked with a weighted
compatibility score, and every recommendation explains in plain language why it was chosen, with
a link to the exact product on the brand's official store and buttons to compare it on Amazon,
Flipkart, Nykaa, Myntra, Meesho and Purplle.

> Informational guidance only. It is not a medical diagnosis and does not promise that a product will suit you.

**Products:** real face-care products from Indian brands' official online stores (Minimalist,
The Derma Co, Dr. Sheth's, Dot & Key, Pilgrim, Plum, Foxtale, Re'equil, Deconstruct, mCaffeine,
Hyphen and more), with INR prices, MRP, sizes, photos and product links. See
[`report/data_audit.md`](report/data_audit.md) for the current counts and
[`data/SOURCES.md`](data/SOURCES.md) for how the data is collected.

## Architecture

```
 Browser (frontend/)                    Backend (backend/app/)                      Database
 ───────────────────                    ──────────────────────                      ────────
 index · analyze · products     HTTP    FastAPI  /api/meta                         data/skincare.db
 product · ingredients    ───────────►           /api/products  /api/products/{id}  (SQLite, read-only)
 ingredient                     JSON             /api/ingredients /api/ingredients/{key}
                                                 /api/recommend   (POST)        ◄── built by
 image-check.js: face detection and                │                                 pipeline/build_data.py
 photo quality check, in the browser only          └─ recommender.py: hard filters → weighted score → reasons
```

* **Database:** `data/skincare.db` is a SQLite database. Tables: `products`, `ingredients`, `product_ingredients`
  (label order), `product_families`, `product_concerns`, `ingredient_families`, `ingredient_concerns`, plus a full-text
  search index `products_fts`. The schema is in [`pipeline/database.py`](pipeline/database.py). The pipeline is the
  only writer; the backend opens the database read-only.
* **Backend:** FastAPI, in [`backend/app/`](backend/app). `catalogue.py` loads the database once at startup.
  `recommender.py` validates the profile, applies the hard filters, scores and explains. `main.py` defines the routes and
  serves the frontend. Interactive API docs are at `/api/docs`.
* **Frontend:** plain HTML, CSS and JavaScript modules in [`frontend/`](frontend), with no build step. It calls the API
  for all data. A selfie is checked on the user's own device (MediaPipe face detection plus focus, light and
  resolution checks) and is never uploaded.

### The score (Module 4)

`S = 0.35·C + 0.25·I + 0.20·K + 0.20·B`, applied only to products that pass every hard rule.

* **C, concern match:** for each chosen concern, the strongest matching ingredient. 1.0 for a targeted active
  (for example niacinamide or salicylic acid), 0.5 for a supporting ingredient (for example glycerin or aloe).
  Uses the full ingredient list when the brand publishes one, otherwise the actives named on the product.
* **I, preferred ingredients:** the share of the user's preferred ingredients that the product contains.
* **K, skin-type fit:** the brand's own skin-type tag on its store. 1 if it matches, 0.2 if not, 0.5 if there is no tag.
* **B, budget fit:** `1 − 0.6 × (price − min) / (max − min)`.
* A component the user left blank is dropped, and the other weights are renormalised.

## Run it

Requires Python 3.10+.

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open http://localhost:8000. The API docs are at http://localhost:8000/api/docs.

### Refresh prices, rebuild the data, evaluation and tests

```bash
pip install -r requirements-dev.txt
python pipeline/fetch_brands.py # brand stores → data/raw/brands/ (polite, takes a while)
python pipeline/build_data.py   # raw data → data/skincare.db, data/processed/*.csv, report/data_audit.md
python eval/run_eval.py         # 20 personas → report/evaluation.md, report/evaluation.json
python -m pytest                # API and recommender tests
```

`requirements.txt` holds only what the website server needs. `requirements-dev.txt` adds the
data pipeline and test tools.

## Deploying (Render, free plan)

The repository includes [`render.yaml`](render.yaml), so Render can set everything up.

1. Sign in at https://render.com with your GitHub account.
2. Click **New +**, then **Blueprint**, and pick this repository.
3. Click **Apply**. Render installs `requirements.txt` and starts
   `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
4. When the deploy shows **Live**, the site is at `https://skinanalyzer.onrender.com` (or a similar
   name Render assigns). Every push to `main` redeploys automatically.

On the free plan the server sleeps after about 15 minutes without visitors; the first visit after
that takes up to a minute to wake it. To host the frontend on a different domain from the API, set
`ALLOWED_ORIGINS` (comma-separated) on the backend.

## Data (all real and public)

| Data | Used for | Source |
|---|---|---|
| Brands' official Indian stores | Products, ₹ prices, MRP, sizes, photos, product links, skin-type and concern tags, published ingredient lists | Public Shopify catalogue feeds and product pages, collected politely after checking robots.txt (`pipeline/fetch_brands.py`) |
| EU CosIng ingredient inventory | INCI names, functions, Annex restrictions | European Commission; reuse permitted under Decision 2011/833/EU. [Mirror](https://huggingface.co/datasets/nad949/CosIng) |
| Indian Skincare Ingredient Flags (CureSkin, 2026) | Pore-clogging ratings, fungal-acne triggers, fragrance allergens, alcohol type, pregnancy caution | [CC BY 4.0](https://huggingface.co/datasets/cureskin/indian-skincare-ingredient-flags) |

**Marketplace prices.** Amazon, Flipkart, Myntra, Meesho and Nykaa don't permit automated
collection of their prices, so the site links to a search for each product on those stores instead.
Real cross-store price comparison needs their official partner APIs (Amazon Product Advertising
API, Flipkart Affiliate API), which need an approved affiliate account.

## Repository layout

```
backend/app/        FastAPI app: catalogue.py, recommender.py, main.py
backend/tests/      API and recommender tests (pytest)
frontend/           website: HTML pages, assets/css/app.css, assets/js/*.js
pipeline/           fetch_brands.py (collect), sources.py (brand data), build_data.py (clean, match, tag),
                    reference.py (synonyms, actives, families), database.py (schema)
data/raw/           brand-store snapshots (brands/) and the two ingredient references
data/processed/     clean product and ingredient tables (CSV)
data/skincare.db    SQLite database used by the backend
eval/               20 test personas and the evaluation script
report/             mid-term report (PDF), data audit, evaluation results, 50-product manual-check sample
```

## Project documents

* [`report/PRJ1-mid-term-report.pdf`](report/PRJ1-mid-term-report.pdf): literature review, research gap, objectives, methodology
* [`report/data_audit.md`](report/data_audit.md): product table and ingredient matching (objectives O2 and O3)
* [`report/evaluation.md`](report/evaluation.md): rule violations, Precision/Recall/NDCG@5, baselines, ablations, weight sensitivity (O4–O6)

**Known limitations.** Many Indian brands don't publish full ingredient lists online. Those products are matched to
concerns through the actives they name, and are left out whenever you set an ingredient restriction. Prices are a
snapshot from each brand's store on the fetch date. The relevance labels used in evaluation are the brands' own
store tags, so they are weak labels. Skin estimates from photos (the CNN in Module 2) are not trained yet.

## Licence

Code: MIT (see `LICENSE`). Datasets keep their original licences, listed above.
