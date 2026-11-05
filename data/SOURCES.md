# Data sources

## Products: brands' official Indian online stores

`raw/brands/<store>.json.gz` holds one snapshot per brand, collected by `pipeline/fetch_brands.py`:
the store's public Shopify catalogue feed (`/products.json`), plus the ingredient sections of each
face-care product page. The fetch date is stored in each file and shown on the website.

How it's collected:
* Each store's `robots.txt` is read first, and any path it disallows is skipped.
* The collector identifies itself with a user agent that links to this repository.
* It waits 2 seconds between requests and backs off when a store answers 429 (rate limited).
* Only public catalogue data is read: names, prices, sizes, images, product URLs and the
  ingredient lists the brand publishes. No accounts, carts or personal data.

Prices are the brand store's INR selling price on the fetch date. The MRP is the store's
"compare at" price when it is higher.

### Not collected

Amazon, Flipkart, Myntra, Meesho and Nykaa do not permit automated collection of their listings
or prices, so the site links to a search for each product on those stores instead of showing
their prices. Showing their live prices would need their official partner APIs (Amazon Product
Advertising API, Flipkart Affiliate API), which need an approved account.

## Ingredient references

| File | Dataset | Downloaded from | Licence / terms |
|---|---|---|---|
| `raw/cosing_ingredients.csv` | EU CosIng Ingredients and Fragrance Inventory | https://huggingface.co/datasets/nad949/CosIng (mirror of https://ec.europa.eu/growth/tools-databases/cosing/) | European Commission; reuse authorised under Commission Decision 2011/833/EU |
| `raw/cureskin_ingredient_flags.csv` | Indian Skincare Ingredient Flags, CureSkin Indian Skincare Decoder (2026) | https://huggingface.co/datasets/cureskin/indian-skincare-ingredient-flags | CC BY 4.0. Blank cells mean "not assessed", never "safe" |

## Earlier sources, no longer used

* **Sephora Products and Skincare Reviews** (Kaggle, user nadyinky): used in the mid-term
  prototype. Removed because its products are US listings priced in USD, not sold in India.
* **Open Beauty Facts (India)**: few products with ingredient lists, and no prices.
