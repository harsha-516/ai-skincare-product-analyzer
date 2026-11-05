"""
Hand-built reference lists used by the ingredient module (report section 4.3.3).

These lists say which ingredient a product contains and what that ingredient is commonly
used for. They are associations for matching and explanation, not proof that a product
works for a person (gap G6 in the report).
"""

import re

CONCERNS = {
    "acne": "Breakouts and blemishes",
    "oiliness": "Oiliness and shine",
    "pores": "Visible pores",
    "dryness": "Dryness and dehydration",
    "redness": "Redness and sensitivity",
    "dark_spots": "Dark spots and pigmentation",
    "dullness": "Dullness and uneven texture",
    "ageing": "Fine lines and firmness",
    "dark_circles": "Dark circles and puffiness",
    "sun": "Sun protection",
}

# Ingredient families a user can choose to avoid (hard filter in module 4).
FAMILIES = {
    "fragrance": "Added fragrance (parfum)",
    "fragrance_allergens": "EU-listed fragrance allergens",
    "essential_oils": "Essential oils",
    "drying_alcohol": "Drying alcohols",
    "sulfates": "Sulfate surfactants (SLS, SLES)",
    "parabens": "Parabens",
    "silicones": "Silicones",
    "comedogenic": "Highly comedogenic (rating 3 or more)",
    "fungal_acne": "Fungal-acne (Malassezia) triggers",
    "pregnancy_caution": "Pregnancy caution",
    "chemical_filters": "Chemical (organic) UV filters",
    "strong_actives": "Strong actives (retinoids, AHA/BHA, benzoyl peroxide)",
}

# Actives that commonly irritate when started too fast. Lactic acid is left out because it
# is mostly used as a pH adjuster at low levels.
STRONG_ACTIVES = re.compile(
    r"^retinol$|^retinal$|^retinyl retinoate$|^hydroxypinacolone retinoate$|^adapalene$|"
    r"^glycolic acid$|^mandelic acid$|^salicylic acid$|^benzoyl peroxide$")

# Regex on the canonical (lower-case INCI) name -> concerns it is commonly used for, and a
# strength: 1.0 for a targeted active, 0.5 for a supporting ingredient (humectants, soothing
# plant extracts, emollients) that appears in most formulas and so should count for less.
ACTIVES = [
    (r"^salicylic acid$|^betaine salicylate$", ["acne", "oiliness", "pores"], 1.0),
    (r"salix alba.*bark extract", ["acne", "pores"], 0.5),
    (r"^niacinamide$", ["acne", "oiliness", "pores", "redness", "dark_spots"], 1.0),
    (r"^azelaic acid$|potassium azeloyl diglycinate", ["acne", "redness", "dark_spots"], 1.0),
    (r"^benzoyl peroxide$|^sulfur$|^sulphur$", ["acne"], 1.0),
    (r"melaleuca alternifolia", ["acne"], 0.5),
    (r"^zinc pca$|^zinc gluconate$", ["oiliness", "acne"], 1.0),
    (r"^kaolin$|^bentonite$|charcoal powder|^montmorillonite$", ["oiliness", "pores"], 1.0),
    (r"^retinol$|^retinal$|^retinyl retinoate$|^hydroxypinacolone retinoate$|^adapalene$",
     ["ageing", "acne", "dullness"], 1.0),
    (r"^retinyl palmitate$|^bakuchiol$", ["ageing", "dullness"], 0.5),
    (r"^ascorbic acid$|ascorbyl glucoside|ascorbyl phosphate|tetrahexyldecyl ascorbate|"
     r"ethyl ascorbic acid|ascorbyl tetraisopalmitate", ["dark_spots", "dullness"], 1.0),
    (r"^alpha-arbutin$|^arbutin$|^tranexamic acid$|^kojic acid$|^hexylresorcinol$",
     ["dark_spots"], 1.0),
    (r"glycyrrhiza glabra.*root extract", ["dark_spots", "redness"], 0.5),
    (r"^glycolic acid$|^lactic acid$|^mandelic acid$|^gluconolactone$|^lactobionic acid$",
     ["dullness", "pores"], 1.0),
    (r"^sodium hyaluronate$|^hyaluronic acid$|hydrolyzed hyaluronic acid|"
     r"sodium acetylated hyaluronate|^urea$|^polyglutamic acid$|^sodium polyglutamate$",
     ["dryness"], 1.0),
    (r"^glycerin$|^sodium pca$|^betaine$|^trehalose$|^propanediol$|^butylene glycol$",
     ["dryness"], 0.5),
    (r"^ceramide|^phytosphingosine$", ["dryness", "redness"], 1.0),
    (r"^cholesterol$|^squalane$|butyrospermum parkii", ["dryness"], 0.5),
    (r"centella asiatica|^madecassoside$|^asiaticoside$|^colloidal oatmeal$|"
     r"avena sativa.*kernel (flour|extract)", ["redness"], 1.0),
    (r"^panthenol$|^allantoin$|^bisabolol$|^beta-glucan$|camellia sinensis leaf extract|"
     r"^dipotassium glycyrrhizate$|aloe barbadensis", ["redness"], 0.5),
    (r"^palmitoyl (tripeptide|tetrapeptide|pentapeptide|hexapeptide)|acetyl hexapeptide|"
     r"copper tripeptide|^acetyl octapeptide", ["ageing"], 1.0),
    (r"^adenosine$|peptide", ["ageing"], 0.5),
    (r"^caffeine$|^phytonadione$", ["dark_circles"], 1.0),
    (r"^zinc oxide$|^titanium dioxide$|^butyl methoxydibenzoylmethane$|^homosalate$|"
     r"^ethylhexyl salicylate$|^octocrylene$|^ethylhexyl methoxycinnamate$|^benzophenone-3$|"
     r"bis-ethylhexyloxyphenol methoxyphenyl triazine|^ethylhexyl triazone$|"
     r"^diethylamino hydroxybenzoyl hexyl benzoate$|methylene bis-benzotriazolyl|"
     r"^drometrizole trisiloxane$|^terephthalylidene dicamphor sulfonic acid$|"
     r"^polysilicone-15$|^diethylhexyl butamido triazone$", ["sun"], 1.0),
]

CHEMICAL_FILTERS = re.compile(
    r"^avobenzone$|^butyl methoxydibenzoylmethane$|^homosalate$|^octisalate$|"
    r"^ethylhexyl salicylate$|^octocrylene$|^octinoxate$|^ethylhexyl methoxycinnamate$|"
    r"^oxybenzone$|^benzophenone-3$|bis-ethylhexyloxyphenol methoxyphenyl triazine|"
    r"^ethylhexyl triazone$|^diethylamino hydroxybenzoyl hexyl benzoate$|"
    r"methylene bis-benzotriazolyl|^drometrizole trisiloxane$|"
    r"^terephthalylidene dicamphor sulfonic acid$|^polysilicone-15$")

# The 26 fragrance allergens listed in Annex III of EU Regulation 1223/2009.
EU_ALLERGENS = {
    "amyl cinnamal", "amylcinnamyl alcohol", "anise alcohol", "benzyl alcohol",
    "benzyl benzoate", "benzyl cinnamate", "benzyl salicylate", "cinnamal", "cinnamyl alcohol",
    "citral", "citronellol", "coumarin", "eugenol", "farnesol", "geraniol", "hexyl cinnamal",
    "hydroxycitronellal", "hydroxyisohexyl 3-cyclohexene carboxaldehyde", "isoeugenol",
    "alpha-isomethyl ionone", "butylphenyl methylpropional", "limonene", "linalool",
    "methyl 2-octynoate", "evernia prunastri extract", "evernia furfuracea extract",
}

DRYING_ALCOHOLS = {"alcohol", "alcohol denat", "alcohol denat.", "ethanol", "isopropyl alcohol",
                   "sd alcohol", "sd alcohol 40", "sd alcohol 40-b", "denatured alcohol",
                   "methanol"}

# Common spellings -> the name used in CosIng.
SYNONYMS = {
    "water": "aqua", "eau": "aqua", "purified water": "aqua", "deionized water": "aqua",
    "distilled water": "aqua", "fragrance": "parfum", "perfume": "parfum",
    "fragrance (parfum)": "parfum", "parfum (fragrance)": "parfum", "aroma": "parfum",
    "flavor": "aroma", "vitamin e": "tocopherol", "vitamin c": "ascorbic acid",
    "vitamin b3": "niacinamide", "vitamin b5": "panthenol", "pro-vitamin b5": "panthenol",
    "d-panthenol": "panthenol", "dl-panthenol": "panthenol", "hyaluronic acid": "hyaluronic acid",
    "alcohol denat": "alcohol denat.", "denatured alcohol": "alcohol denat.",
    "sd alcohol 40": "alcohol denat.", "sd alcohol 40-b": "alcohol denat.",
    "shea butter": "butyrospermum parkii butter", "aloe vera": "aloe barbadensis leaf juice",
    "glycerine": "glycerin", "vegetable glycerin": "glycerin",
    "tea tree oil": "melaleuca alternifolia leaf oil", "iron oxides": "ci 77491",
    "avobenzone": "butyl methoxydibenzoylmethane", "octisalate": "ethylhexyl salicylate",
    "octinoxate": "ethylhexyl methoxycinnamate", "oxybenzone": "benzophenone-3",
    "witch hazel": "hamamelis virginiana water",
    "ceramide 3": "ceramide np", "ceramide 6 ii": "ceramide ap", "ceramide 1": "ceramide eop",
}


def family_of_name(key: str, cosing_function: str, cureskin_row: dict) -> list[str]:
    """Ingredient families for one canonical ingredient name."""
    f = set()
    fn = (cosing_function or "").upper()
    if key in ("parfum", "aroma", "fragrance") or cureskin_row.get("fragrance") == 1:
        f.add("fragrance")
    if key in EU_ALLERGENS or cureskin_row.get("eu_allergen") == 1:
        f.add("fragrance_allergens")
    if re.search(r"\boil\b", key) and "PERFUMING" in fn and not re.search(
            r"seed oil|kernel oil|nut oil|fruit oil|butter", key):
        f.add("essential_oils")
    if key in DRYING_ALCOHOLS or cureskin_row.get("alcohol_type") == "drying":
        f.add("drying_alcohol")
    if re.search(r"(lauryl|laureth|myreth|coco|cetearyl|trideceth) sulfate$", key):
        f.add("sulfates")
    if "paraben" in key:
        f.add("parabens")
    if re.search(r"(methicone|siloxane|dimethiconol|silsesquioxane)\b", key) or key.endswith(
            "cone") and "silicone" not in key and key not in ("bone",):
        f.add("silicones")
    co = cureskin_row.get("comedogenic")
    if isinstance(co, (int, float)) and co == co and co >= 3:
        f.add("comedogenic")
    if cureskin_row.get("fa_trigger") == 1:
        f.add("fungal_acne")
    if cureskin_row.get("pregnancy_caution") == 1:
        f.add("pregnancy_caution")
    if CHEMICAL_FILTERS.search(key):
        f.add("chemical_filters")
    if STRONG_ACTIVES.search(key):
        f.add("strong_actives")
    return sorted(f)
