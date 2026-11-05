import { api, mountChrome, productVisual, productCard, familyTag, errorState, icon, esc, num, money,
  retailerLink, CONCERN_SHORT, CONCERN_ICON, FAMILY_SHORT, $, params } from "./ui.js";

mountChrome();

const FLAG_NOTE = {
  fragrance: "Added fragrance is one of the most common causes of skin reactions.",
  fragrance_allergens: "Contains fragrance allergens that EU rules require to be named on the label.",
  essential_oils: "Essential oils can irritate reactive skin.",
  drying_alcohol: "Drying alcohols can leave dry or sensitive skin tight.",
  comedogenic: "Contains an ingredient rated 3 or more on the pore-clogging scale.",
  fungal_acne: "Contains ingredients that can feed Malassezia, linked to fungal acne.",
  pregnancy_caution: "Contains an ingredient flagged for caution during pregnancy. Ask your doctor.",
  strong_actives: "Contains a strong active. Introduce it slowly and patch-test first.",
  sulfates: "Contains sulfate surfactants, which can be stripping.",
  parabens: "Contains parabens.",
  silicones: "Contains silicones.",
  chemical_filters: "Uses chemical (organic) UV filters.",
};

async function main() {
  const id = params().get("id");
  if (!id) { location.replace("products.html"); return; }
  let p;
  try {
    p = await api.product(id);
  } catch (err) {
    $("#root").innerHTML = err.status === 404
      ? `<div class="card empty" style="margin-top:40px"><div class="icon-badge">${icon("search")}</div><h3>Product not found</h3><p class="muted small" style="margin-top:8px"><a class="link" href="products.html">Back to all products ${icon("arrow")}</a></p></div>`
      : errorState(err);
    return;
  }
  document.title = `${p.name} by ${p.brand} — SkinAnalyzer`;

  const flags = p.families.filter((f) => FLAG_NOTE[f]);
  const claims = p.claims.filter((c) => c !== "Clean at Sephora");
  const strongestFor = new Set(p.key_actives.map((a) => a.ingredient));

  $("#root").innerHTML = `
    <nav class="crumbs" aria-label="Breadcrumb"><a href="products.html">Products</a>${icon("chevron")}
      <a href="products.html?category=${encodeURIComponent(p.category)}">${esc(p.category)}</a>${icon("chevron")}<span>${esc(p.brand)}</span></nav>

    <section class="detail">
      ${productVisual(p, { badge: p.on_sale ? '<span class="tag tag-ink">On sale</span>' : "" })}
      <div>
        <span class="eyebrow">${esc(p.brand)}</span>
        <h1>${esc(p.name)}</h1>
        <div class="row">
          <span class="price" style="font-size:1.5rem">${money(p.effective_price)}${p.on_sale ? `<s>${money(p.price)}</s>` : ""}</span>
          ${p.rating ? `<span class="rating">${icon("star")}<b>${p.rating.toFixed(1)}</b><span class="subtle">· ${num(p.reviews)} reviews</span></span>` : ""}
        </div>
        <div class="tags" style="margin-top:16px">
          <span class="tag">${esc(p.category)}</span>
          ${p.fragrance_free ? '<span class="tag tag-sage">Fragrance-free</span>' : ""}
          ${p.skin_types.map((s) => `<span class="tag tag-line">${esc(s)} skin</span>`).join("")}
          ${claims.slice(0, 4).map((c) => `<span class="tag tag-line">${esc(c)}</span>`).join("")}
        </div>
        <div class="kv">
          <div><span>Size</span><b>${esc(p.size || "—")}</b></div>
          <div><span>Ingredients</span><b>${p.ingredient_count}</b></div>
          <div><span>List quality</span><b>${p.completeness === "complete" ? "Complete" : p.completeness === "partial" ? "Partial" : "Missing"}</b></div>
        </div>
        <div class="row">
          <a class="btn btn-primary" href="${retailerLink(p)}" target="_blank" rel="noopener">Find at retailer ${icon("external")}</a>
          <a class="btn" href="analyze.html">Check if it suits me</a>
        </div>
        ${flags.length ? `<div class="stack" style="margin-top:28px;--gap:8px"><h4>Worth knowing</h4>
          ${flags.map((f) => `<div class="notice" style="padding:12px 14px">${icon("alert")}<span><b style="color:var(--ink)">${esc(FAMILY_SHORT[f])}.</b> ${esc(FLAG_NOTE[f])}</span></div>`).join("")}</div>` : ""}
      </div>
    </section>

    ${p.concerns.length ? `<section class="section" style="padding:24px 0 48px">
      <div class="grid grid-2" style="align-items:start">
        <div><span class="eyebrow">What it targets</span><h2 style="margin-top:12px">Matched to concerns by its ingredients</h2>
          <p class="muted" style="margin-top:12px;max-width:440px">A full bar means a targeted active (for example niacinamide or salicylic acid). A half bar means a supporting ingredient such as glycerin or aloe.</p></div>
        <div class="card">${p.concerns.map((c) => `<div class="concern-row">
            <span class="row" style="gap:10px"><span class="icon-badge" style="width:32px;height:32px;border-radius:9px">${icon(CONCERN_ICON[c.concern])}</span>${esc(CONCERN_SHORT[c.concern] || c.label)}</span>
            <div class="bar"><i style="width:${c.strength * 100}%;background:${c.strength === 1 ? "var(--clay)" : "var(--line-2)"}"></i></div>
            <span class="small muted">${esc(c.evidence.slice(0, 2).join(", "))}</span></div>`).join("")}</div>
      </div></section>` : ""}

    <section style="padding-bottom:48px">
      <div class="section-head" style="margin-bottom:20px"><div><span class="eyebrow">Full ingredient list</span><h2 style="margin-top:12px">${p.ingredient_count} ingredients, decoded</h2></div>
        ${p.unmatched_count ? `<span class="tag tag-amber">${p.unmatched_count} could not be matched</span>` : ""}</div>
      ${p.ingredients.length ? `<div class="table-card"><div class="table-scroll"><table class="ing-table">
        <thead><tr><th>#</th><th>Ingredient</th><th>What it does</th><th>Flags</th></tr></thead>
        <tbody>${p.ingredients.map((i, ix) => `<tr>
          <td class="pos">${ix + 1}</td>
          <td><a href="ingredient.html?key=${encodeURIComponent(i.key)}"><b>${esc(i.name)}</b></a>${strongestFor.has(i.name) ? ' <span class="tag tag-clay">Key active</span>' : ""}</td>
          <td class="small muted">${esc(i.cureskin_function || i.function || "—")}</td>
          <td><div class="tags">${i.families.map(familyTag).join("") || '<span class="subtle small">—</span>'}</div></td></tr>`).join("")}</tbody></table></div></div>`
        : `<div class="notice">${icon("info")}<span>The source data has no ingredient list for this product.</span></div>`}
    </section>

    ${p.similar.length ? `<section style="padding-bottom:24px">
      <div class="section-head" style="margin-bottom:20px"><div><span class="eyebrow">Similar formulas</span><h2 style="margin-top:12px">Products with a similar ingredient list</h2></div></div>
      <div class="product-grid">${p.similar.map((s) => productCard(s, { extra: `<span class="xs subtle">${Math.round(s.similarity * 100)}% ingredient overlap</span>` })).join("")}</div>
    </section>` : ""}`;
}

main();
