import { api, mountChrome, productCard, familyTag, errorState, icon, esc, num, CONCERN_ICON, CONCERN_SHORT, $, params } from "./ui.js";
import { GUIDES } from "./guides.js";

mountChrome();

const COMEDO = ["Won't clog pores", "Very unlikely to clog pores", "Unlikely to clog pores", "May clog pores for some", "Likely to clog pores", "Very likely to clog pores"];

async function main() {
  const key = params().get("key");
  if (!key) { location.replace("ingredients.html"); return; }
  let i;
  try {
    i = await api.ingredient(key);
  } catch (err) {
    $("#root").innerHTML = err.status === 404
      ? `<div class="card empty" style="margin-top:40px"><div class="icon-badge">${icon("search")}</div><h3>Ingredient not found</h3><p style="margin-top:8px"><a class="link" href="ingredients.html">Browse the dictionary ${icon("arrow")}</a></p></div>`
      : errorState(err);
    return;
  }
  document.title = `${i.name} — SkinAnalyzer`;
  const guide = GUIDES.find((g) => g.key === i.key || (g.also || []).includes(i.key));
  const concerns = Object.entries(i.concerns).sort((a, b) => b[1] - a[1]);

  $("#root").innerHTML = `
    <nav class="crumbs" aria-label="Breadcrumb"><a href="ingredients.html">Ingredients</a>${icon("chevron")}<span>${esc(i.name)}</span></nav>
    <section class="page-hero" style="padding-top:24px">
      <span class="eyebrow">Ingredient</span>
      <h1>${esc(i.name)}</h1>
      <p class="lead">${esc(guide ? guide.body : i.cureskin_function || i.function || "A cosmetic ingredient listed in the EU CosIng inventory.")}</p>
      <div class="tags" style="margin-top:18px">${i.families.map(familyTag).join("")}
        ${concerns.map(([c, s]) => `<span class="tag ${s === 1 ? "tag-clay" : ""}">${s === 1 ? "Targets" : "Supports"} ${esc(CONCERN_SHORT[c].toLowerCase())}</span>`).join("")}</div>
    </section>

    <section class="grid grid-3" style="padding-bottom:48px">
      <div class="card stack"><div class="icon-badge">${icon("flask")}</div><h3>What it does</h3>
        <p class="small muted">${esc(i.cureskin_function || "—")}</p>
        ${i.function ? `<p class="xs subtle">EU CosIng function: ${esc(i.function.toLowerCase())}</p>` : ""}</div>
      <div class="card stack"><div class="icon-badge">${icon("grid")}</div><h3>Pore-clogging rating</h3>
        ${i.comedogenic == null ? '<p class="small muted">Not rated in our reference data.</p>'
          : `<div class="row"><span class="display" style="font-size:2.6rem;line-height:1">${i.comedogenic}</span><span class="subtle">/ 5</span></div><p class="small muted">${COMEDO[i.comedogenic]}</p>`}</div>
      <div class="card stack"><div class="icon-badge">${icon("layers")}</div><h3>How common is it?</h3>
        <div class="row"><span class="display" style="font-size:2.6rem;line-height:1">${num(i.product_count)}</span></div>
        <p class="small muted">products in our catalogue list it${i.eu_restriction ? `. Its use is restricted in the EU (Annex ${esc(i.eu_restriction)}).` : "."}</p></div>
    </section>

    ${guide ? `<section class="card card-soft" style="margin-bottom:48px"><div class="grid grid-2">
      <div><span class="eyebrow">How to use it</span><h2 style="margin-top:10px;font-size:2rem">${esc(guide.name)}</h2><p class="muted" style="margin-top:8px">${esc(guide.sub)}</p></div>
      <div class="stack"><p><b>Suits:</b> <span class="muted">${esc(guide.suits)}</span></p><p class="muted">${esc(guide.how)}</p></div></div></section>` : ""}

    ${i.top_products.length ? `<section>
      <div class="section-head" style="margin-bottom:20px"><div><span class="eyebrow">Most loved products with ${esc(i.name)}</span><h2 style="margin-top:12px">Where you'll find it</h2></div>
        <a class="link" href="products.html?q=${encodeURIComponent(i.name)}">See all ${num(i.product_count)} ${icon("arrow")}</a></div>
      <div class="product-grid">${i.top_products.map((p) => productCard(p)).join("")}</div></section>` : ""}`;
}

main();
