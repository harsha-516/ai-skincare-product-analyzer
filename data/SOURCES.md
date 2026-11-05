# Data sources

All files in `raw/` are unchanged copies of the public datasets below, downloaded on 2026-11-04.

| File | Dataset | Downloaded from | Licence / terms |
|---|---|---|---|
| `raw/sephora_product_info.csv` | Sephora Products and Skincare Reviews: product_info.csv (8,494 products, scraped March 2023 by Kaggle user nadyinky) | https://huggingface.co/datasets/eyachawechi/my-sephora-data/resolve/main/product_info.csv | Check the original Kaggle listing for licence terms before any commercial use |
| `raw/cosing_ingredients.csv` | EU CosIng Ingredients and Fragrance Inventory | https://huggingface.co/datasets/nad949/CosIng (mirror of https://ec.europa.eu/growth/tools-databases/cosing/) | European Commission; reuse authorised under Commission Decision 2011/833/EU |
| `raw/cureskin_ingredient_flags.csv` | Indian Skincare Ingredient Flags, CureSkin Indian Skincare Decoder (2026) | https://huggingface.co/datasets/cureskin/indian-skincare-ingredient-flags | CC BY 4.0. Blank cells mean "not assessed", never "safe" |

## SHA-256

```
e414d9b336ee8117b0853991d9d75f8b0075372512b3550255a962b959acf02f *cosing_ingredients.csv
15642499736ebae58c571ac8538a84dac757e68fc678e53193f6c702f720a13d *cureskin_ingredient_flags.csv
d5ddb391be522e7bfcecbba93dd61129217c1381bf14a7580c0f6097ac8da063 *sephora_product_info.csv
```

## Evaluated and not used

* **Open Beauty Facts (India)**, https://world.openbeautyfacts.org (ODbL). 1,871 products tagged India, but only 42 of the
  first 100 had an ingredient list, many were toothpaste, shampoo or make-up, and there are no prices.
* **Image datasets for Module 2** (ACNE04, SCIN, Fitzpatrick17k) are still under licence and label review. None is included yet.
