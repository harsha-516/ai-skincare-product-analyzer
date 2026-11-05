import { api, mountChrome, revealOnScroll, icon, esc, num, money, productCard, productVisual, skeletonCards,
  CONCERN_ICON, CONCERN_SHORT, $, $$ } from "./ui.js";

mountChrome();

const TILE_TINTS = ["#f6e9e2", "#e9eee5", "#efe6ee", "#e5ebf1", "#f5ecd9"];

// The same sample profile shown in the hero card, answered live by the API.
const SAMPLE = {
  skin_type: "oily", sensitivity: "high", concerns: ["acne", "dark_spots"], category: "Serum",
  budget_min: 0, budget_max: 800, avoid_families: ["fragrance", "essential_oils", "drying_alcohol"], limit: 1,
};

async function hero() {
  try {
    const r = await api.recommend(SAMPLE);
    const top = r.results[0];
    if (!top) return;
    const p = top.product;
    $("#pv-match").innerHTML = `
      <div class="row" style="justify-content:space-between"><span class="rank-label">Best match</span><span class="tag tag-clay">Live result</span></div>
      <div style="display:grid;grid-template-columns:96px 1fr auto;gap:14px;align-items:center;margin-top:14px">
        ${productVisual(p)}
        <div><div class="xs subtle" style="text-transform:uppercase;letter-spacing:.08em;font-weight:600">${esc(p.brand)}</div>
          <div style="font-weight:600;line-height:1.3;margin-top:2px">${esc(p.name)}</div>
          <div class="small muted" style="margin-top:4px">${money(p.price)} on ${esc(p.brand)}'s store</div></div>
        <div class="ring" style="--v:${Math.round(top.score * 100)}"><div><b>${Math.round(top.score * 100)}</b><small>match</small></div></div>
      </div>
      <ul class="check-list" style="margin-top:14px">${top.reasons.slice(1, 2).map((t) => `<li>${icon("check")}${esc(t)}</li>`).join("")}</ul>
      <p class="xs subtle" style="margin-top:12px">${num(r.total - r.eligible)} of ${num(r.total)} products filtered out by these rules</p>`;
  } catch {
    $("#pv-match").remove();
  }
}

async function concernsAndStats() {
  const m = await api.meta();
  $$('[data-meta="products"]').forEach((el) => (el.textContent = num(m.products)));
  $$('[data-meta="ingredients"]').forEach((el) => (el.textContent = num(m.ingredients)));
  $$('[data-meta="brands"]').forEach((el) => (el.textContent = num(m.brands)));
  $$('[data-meta="median"]').forEach((el) => (el.textContent = money(m.price_median ?? 449)));
  $("#brands").innerHTML = Object.entries(m.brand_counts).sort((a, b) => b[1] - a[1]).map(([b, n]) => `
    <a class="brand-tile reveal" href="products.html?brand=${encodeURIComponent(b)}"><span><strong>${esc(b)}</strong>
      <span class="xs subtle" style="display:block">${num(n)} products · ${esc(m.stores[b]?.domain || "")}</span></span>${icon("arrow")}</a>`).join("");
  $("#concerns").innerHTML = Object.entries(m.concerns).map(([k, label], i) => `
    <a class="tile reveal" href="products.html?concern=${k}" style="--tile:${TILE_TINTS[i % TILE_TINTS.length]}">
      <div class="icon-badge">${icon(CONCERN_ICON[k])}</div>
      <div><h3>${esc(CONCERN_SHORT[k] || label)}</h3><p class="small muted" style="margin-top:4px">${num(m.concern_counts[k])} products with a targeted active</p></div>
    </a>`).join("");
  revealOnScroll();
}

const FAV_CATS = ["Serum", "Sunscreen", "Moisturiser", "Cleanser"];
async function favourites(cat) {
  $$("#fav-tabs .chip").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.c === cat)));
  $("#favourites").innerHTML = skeletonCards(4);
  const r = await api.products({ category: cat, sort: "featured", page_size: 4 });
  $("#favourites").innerHTML = r.items.map((p) => productCard(p)).join("");
}
$("#fav-tabs").innerHTML = FAV_CATS.map((c) => `<button class="chip" role="tab" data-c="${c}">${c}</button>`).join("");
$("#fav-tabs").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) favourites(b.dataset.c); });

revealOnScroll();
hero();
concernsAndStats();
favourites("Serum");
