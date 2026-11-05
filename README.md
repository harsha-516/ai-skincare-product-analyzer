# AI Skincare Product Analyzer

A constraints-first, explainable skincare recommender built on real, public product and ingredient data.
This is the PRJ1 project of Keerthana, Prateek, Harsha and Karthik.

You give it your skin type, sensitivity, concerns, budget, the category you want and the ingredients you avoid.
Products that break any of your rules are removed **before** scoring. The rest are ranked with a weighted
compatibility score, and every result explains in plain language why it was chosen.

> Informational decision support only. It is not a medical diagnosis and does not promise that a product will suit you.

**Live site:** `https://harsha-516.github.io/ai-skincare-product-analyzer/` (after GitHub Pages is enabled, see below)

| | |
|---|---|
| Products | **1,829** face-care products from 127 brands, with prices, ratings and full ingredient lists |
| Ingredients | **3,626** distinct ingredients, **98.4%** of ingredient tokens matched to the EU CosIng database |
| Constraint violations | **0%** across 20 test personas (a naive "most-loved" list breaks the rules 48% of the time) |
| Ranking | Precision@5 **0.61**, against 0.40 for popularity and 0.37 for random |
| Explanations | **100%** of results show at least three plain-language reasons |

## The website

| Page | What it does |
|---|---|
| `index.html` | Overview and live dataset numbers |
| `analyze.html` | Questionnaire → hard filters → ranked shortlist with reasons, score breakdown, warnings and full ingredient list. Optional selfie quality check |
| `products.html` | Browse and search all products by category, price, fragrance, brand or ingredient |
| `ingredients.html` | Common actives in plain English, plus a searchable table of every ingredient with its CosIng function and CureSkin flags |
| `project.html` | Problem, objectives and their status, methodology, datasets, results, literature review, research gap, work plan and references |

The site is static (HTML, CSS and vanilla JavaScript). It runs on GitHub Pages with no server, and nothing a user enters leaves their browser.

## How it works (report section 4)

```
Face photo (optional)        Questionnaire profile           Product + ingredient data
        │                            │                                  │
M2 Image quality gate        M1 Profile validation            M3 Ingredient module
(face, focus, light, size)   (budget, category, allergies)    (clean, standardise, match)
        └────────────────────────────┼──────────────────────────────────┘
                     M4 Eligibility filters: hard rules first
                 budget range · category · restricted ingredients
                                     │
                     M4 Weighted score  S = 0.35·C + 0.25·I + 0.20·K + 0.20·B
                                     │
                     M5 Ranked products with plain-language reasons
```

* **C, concern match.** For each chosen concern, take the strongest matching ingredient: 1.0 for a targeted
  active (for example niacinamide or salicylic acid), 0.5 for a supporting ingredient (for example glycerin or aloe). Then average over concerns.
* **I, preferred ingredients.** The share of the user's preferred ingredients that the product contains.
* **K, skin-type fit.** The retailer's "Best for … skin" label: 1 if it matches, 0.2 if it doesn't, 0.5 if there is no label or the user is unsure.
* **B, budget fit.** `1 − 0.6 × (price − min) / (max − min)`, so cheaper products inside the range score higher.
* A component the user gave no input for is dropped, and the remaining weights are renormalised.

**Image module status.** The browser runs MediaPipe BlazeFace face detection and three quality checks:
resolution of at least 300 px on the short side, mean brightness between 60 and 200, and a Laplacian-variance focus score of at least 40.
The focus threshold was calibrated on MediaPipe's sample portrait: sharp scores about 1,900, a 2 px blur 87, and a 3 px blur 32.
The transfer-learning CNN for visible skin characteristics (Phase 3) is **not trained yet**. Until it has been
evaluated, the site shows no skin estimates from photos.

## Data (all real and public)

| Dataset | Used for | Source and licence |
|---|---|---|
| Sephora Products and Skincare Reviews (Kaggle, user nadyinky, scraped March 2023) | Products, prices, ratings, highlights, ingredient lists | [Hugging Face mirror](https://huggingface.co/datasets/eyachawechi/my-sephora-data). Check the Kaggle page for the original licence |
| EU CosIng ingredient inventory | INCI names, functions, Annex restrictions | European Commission; reuse permitted under Decision 2011/833/EU. [Hugging Face mirror](https://huggingface.co/datasets/nad949/CosIng) |
| Indian Skincare Ingredient Flags (CureSkin, 2026) | Comedogenic rating, fungal-acne triggers, fragrance and EU allergens, alcohol type, pregnancy caution | [CC BY 4.0](https://huggingface.co/datasets/cureskin/indian-skincare-ingredient-flags) |

The raw files are kept unchanged in `data/raw/`. See [`data/SOURCES.md`](data/SOURCES.md) for checksums and notes.
Open Beauty Facts (India) was checked and not used: few of its products have ingredient lists, and none have prices.

## Repository layout

```
data/raw/           unchanged source datasets
data/processed/     clean product and ingredient tables (CSV)
pipeline/           Module 3: build_data.py (cleaning, matching, tagging), reference.py (synonyms, actives, families)
docs/               the website (served by GitHub Pages); docs/data/*.json is generated
docs/js/recommender.js   Modules 1, 4, 5: validation, hard filters, scoring, explanations (shared with eval)
docs/js/image-check.js   Module 2: face detection and image quality gate
eval/               20 test personas and the evaluation script
report/             mid-term report (PDF), data audit, evaluation results, 50-product manual-check sample
```

## Run it locally

Requires Python 3.10+ and Node 18+.

```bash
pip install -r requirements.txt
python pipeline/build_data.py      # rebuild data/processed, docs/data and report/data_audit.md
node eval/run_eval.mjs             # rebuild report/evaluation.md and docs/data/evaluation.json
python -m http.server 8000 --directory docs
```

Then open http://localhost:8000.

## Publish with GitHub Pages

In the repository, go to **Settings → Pages**. Set **Source** to *Deploy from a branch*, **Branch** to `main`, and the folder to `/docs`.

## Results

* [`report/data_audit.md`](report/data_audit.md): product table and ingredient matching (objectives O2 and O3)
* [`report/evaluation.md`](report/evaluation.md): constraint violations, Precision/Recall/NDCG@5, baselines, ablations, weight sensitivity (O4–O6)
* [`report/PRJ1-mid-term-report.pdf`](report/PRJ1-mid-term-report.pdf): literature review, research gap, objectives, methodology

**Known limitations.** The relevance labels used in evaluation are the retailer's own "Good for" tags, so
they are weak labels. Manually labelled relevance sets are the next step. Prices are 2023 Sephora US list prices in USD, not live prices.
Ingredient presence shows what a product contains, not that it will work for a particular person.

## Next steps

1. Phase 3: train the image module (baseline HOG/colour features with an SVM, then a MobileNetV2 or EfficientNet-B0 transfer model)
   on a licensed dataset such as ACNE04, and report macro-F1 by lighting and skin-tone group.
2. Have the team manually label relevance for the 20 personas, and fill in `report/manual_check_sample.csv`.
3. Run a usability study (SUS plus explanation clarity ratings) with at least 10 volunteers.
4. Add Indian retailer data (Nykaa, Amazon.in) where the terms permit.

## Licence

Code: MIT (see `LICENSE`). Datasets keep their original licences, listed above.
