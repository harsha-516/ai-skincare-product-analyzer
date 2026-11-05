# SkinAnalyzer: AI Skincare Product Analyzer

An ingredient-aware skincare recommender. You give it your skin type, sensitivity, concerns, budget, the product type
you want and the ingredients you avoid. Products that break any of your rules are removed **before** scoring. The rest
are ranked with a weighted compatibility score, and every recommendation explains in plain language why it was chosen.

> Informational guidance only. It is not a medical diagnosis and does not promise that a product will suit you.

| | |
|---|---|
| Products | **1,829** face-care products from 127 brands, with prices, ratings and full ingredient lists |
| Ingredients | **3,626** distinct ingredients, **98.4%** of ingredient tokens matched to the EU CosIng database |
| Rule violations | **0%** across 20 test personas (a plain "most loved" list breaks the rules 48% of the time) |
| Ranking | Precision@5 **0.61**, against 0.40 for popularity and 0.37 for random |
| Explanations | **100%** of results show at least three plain-language reasons |

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
* **I, preferred ingredients:** the share of the user's preferred ingredients that the product contains.
* **K, skin-type fit:** the retailer's "Best for … skin" label. 1 if it matches, 0.2 if not, 0.5 if there is no label.
* **B, budget fit:** `1 − 0.6 × (price − min) / (max − min)`.
* A component the user left blank is dropped, and the other weights are renormalised.

## Run it

Requires Python 3.10+.

```bash
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open http://localhost:8000. The API docs are at http://localhost:8000/api/docs.

### Rebuild the data, evaluation and tests

```bash
python pipeline/build_data.py   # raw CSVs → data/skincare.db, data/processed/*.csv, report/data_audit.md
python eval/run_eval.py         # 20 personas → report/evaluation.md, report/evaluation.json
python -m pytest                # API and recommender tests
```

## Deploying

The site needs a server for the API, so GitHub Pages alone can't host it. Any Python host works. The start command is:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

To host the frontend on a different domain from the API, set `ALLOWED_ORIGINS` (comma-separated) on the backend.

## Data (all real and public)

| Dataset | Used for | Source and licence |
|---|---|---|
| Sephora Products and Skincare Reviews (Kaggle, user nadyinky, scraped March 2023) | Products, prices, ratings, labels, ingredient lists | [Hugging Face mirror](https://huggingface.co/datasets/eyachawechi/my-sephora-data). Check the Kaggle page for the original licence |
| EU CosIng ingredient inventory | INCI names, functions, Annex restrictions | European Commission; reuse permitted under Decision 2011/833/EU. [Mirror](https://huggingface.co/datasets/nad949/CosIng) |
| Indian Skincare Ingredient Flags (CureSkin, 2026) | Pore-clogging ratings, fungal-acne triggers, fragrance allergens, alcohol type, pregnancy caution | [CC BY 4.0](https://huggingface.co/datasets/cureskin/indian-skincare-ingredient-flags) |

The raw files are kept unchanged in `data/raw/`. See [`data/SOURCES.md`](data/SOURCES.md) for checksums.

## Repository layout

```
backend/app/        FastAPI app: catalogue.py, recommender.py, main.py
backend/tests/      API and recommender tests (pytest)
frontend/           website: HTML pages, assets/css/app.css, assets/js/*.js
pipeline/           build_data.py (clean, match, tag), reference.py (synonyms, actives, families), database.py (schema)
data/raw/           unchanged source datasets
data/processed/     clean product and ingredient tables (CSV)
data/skincare.db    SQLite database used by the backend
eval/               20 test personas and the evaluation script
report/             mid-term report (PDF), data audit, evaluation results, 50-product manual-check sample
```

## Project documents

* [`report/PRJ1-mid-term-report.pdf`](report/PRJ1-mid-term-report.pdf): literature review, research gap, objectives, methodology
* [`report/data_audit.md`](report/data_audit.md): product table and ingredient matching (objectives O2 and O3)
* [`report/evaluation.md`](report/evaluation.md): rule violations, Precision/Recall/NDCG@5, baselines, ablations, weight sensitivity (O4–O6)

**Known limitations.** The relevance labels used in evaluation are the retailer's "Good for" tags, so they are weak
labels. Prices are 2023 Sephora US list prices in USD, not live prices. Skin estimates from photos (the CNN in
Module 2) are not trained yet, so recommendations use the questionnaire only.

## Licence

Code: MIT (see `LICENSE`). Datasets keep their original licences, listed above.
