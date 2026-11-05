import { api, mountChrome, familyTag, errorState, icon, esc, num, CONCERN_ICON, CONCERN_SHORT, FAMILY_SHORT, $, $$ } from "./ui.js";
import { GUIDES } from "./guides.js";

mountChrome();

const meta = await api.meta();
$$('[data-meta="ingredients"]').forEach((el) => (el.textContent = num(meta.ingredients)));

// ----------------------------------------------------------------------- guides
let guideFilter = "all";
const counts = new Map();
async function guideCounts() {
  await Promise.all(GUIDES.map(async (g) => {
    try { counts.set(g.key, (await api.ingredient(g.key)).product_count); } catch { counts.set(g.key, 0); }
  }));
  renderGuides();
}
function renderGuides() {
  const list = GUIDES.filter((g) => guideFilter === "all" || g.concerns.includes(guideFilter));
  $("#guides").innerHTML = list.map((g) => `
    <article class="card stack" style="--gap:12px">
      <div class="row" style="justify-content:space-between;align-items:flex-start">
        <div class="icon-badge" style="${g.warn ? "background:var(--amber-50);color:var(--amber)" : ""}">${icon(g.warn ? "alert" : CONCERN_ICON[g.concerns[0]] || "flask")}</div>
        ${counts.has(g.key) ? `<span class="xs subtle">in ${num(counts.get(g.key))} products</span>` : ""}
      </div>
      <div><h3 style="font-size:1.12rem">${esc(g.name)}</h3><p class="small muted" style="margin-top:2px">${esc(g.sub)}</p></div>
      <div class="tags">${g.concerns.map((c) => `<span class="tag">${esc(CONCERN_SHORT[c])}</span>`).join("")}${g.warn ? '<span class="tag tag-amber">Common irritant</span>' : ""}</div>
      <p class="small"><b>Suits:</b> <span class="muted">${esc(g.suits)}</span></p>
      <p class="small muted">${esc(g.body)}</p>
      <p class="small muted">${esc(g.how)}</p>
      <a class="link small" href="ingredient.html?key=${encodeURIComponent(g.key)}">Products with ${esc(g.name.split(" (")[0].toLowerCase())} ${icon("arrow")}</a>
    </article>`).join("");
}
const FILTERS = ["all", "acne", "dark_spots", "dryness", "redness", "ageing"];
$("#guide-filter").innerHTML = FILTERS.map((f) => `<button class="chip" data-f="${f}" aria-pressed="${f === guideFilter}">${f === "all" ? "All" : esc(CONCERN_SHORT[f])}</button>`).join("");
$("#guide-filter").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  guideFilter = b.dataset.f;
  $$("#guide-filter .chip").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  renderGuides();
});
renderGuides();
guideCounts();

// ----------------------------------------------------------------------- lookup table
$("#family").innerHTML += Object.keys(meta.families).map((f) => `<option value="${f}">Flagged: ${esc(FAMILY_SHORT[f])}</option>`).join("");
export function meter(v) {
  if (v == null) return '<span class="xs subtle">Not rated</span>';
  const cls = v <= 1 ? "low" : v <= 2 ? "mid" : "";
  return `<span class="row" style="gap:8px"><span class="meter ${cls}" aria-label="${v} out of 5">${[1, 2, 3, 4, 5].map((n) => `<i class="${n <= v ? "on" : ""}"></i>`).join("")}</span><span class="xs subtle">${v}/5</span></span>`;
}
const LIMIT = 30;
let offset = 0;
let seq = 0;
async function load(append = false) {
  const mine = ++seq;
  if (!append) offset = 0;
  try {
    const r = await api.ingredients({ q: $("#q").value.trim(), family: $("#family").value, limit: LIMIT, offset });
    if (mine !== seq) return;
    const rows = r.items.map((i) => `<tr>
      <td><a href="ingredient.html?key=${encodeURIComponent(i.key)}"><b>${esc(i.name)}</b></a>${i.eu_restriction ? `<div class="xs subtle">EU restricted · Annex ${esc(i.eu_restriction)}</div>` : ""}</td>
      <td class="small muted">${esc(i.cureskin_function || i.function || "—")}</td>
      <td><div class="tags">${i.families.map(familyTag).join("") || '<span class="subtle small">—</span>'}</div></td>
      <td>${meter(i.comedogenic)}</td>
      <td style="text-align:right"><a class="link small" href="products.html?q=${encodeURIComponent(i.name)}">${num(i.product_count)}</a></td></tr>`).join("");
    $("#rows").innerHTML = append ? $("#rows").innerHTML + rows : rows || `<tr><td colspan="5" class="empty">No ingredient matches your search.</td></tr>`;
    offset += r.items.length;
    $("#icount").textContent = `Showing ${num(Math.min(offset, r.total))} of ${num(r.total)}`;
    $("#imore").classList.toggle("hidden", offset >= r.total);
  } catch (err) {
    $("#rows").innerHTML = `<tr><td colspan="5">${errorState(err)}</td></tr>`;
  }
}
let t;
$("#q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => load(), 180); });
$("#family").addEventListener("change", () => load());
$("#imore").addEventListener("click", () => load(true));
load();
