import { api, mountChrome, productCard, skeletonCards, errorState, icon, esc, num, money,
  CONCERN_SHORT, FAMILY_SHORT, $, $$, params } from "./ui.js";

mountChrome();

const PAGE_SIZE = 24;
const SKIN = { oily: "Oily", dry: "Dry", combination: "Combination", normal: "Normal" };
const AVOID = ["fragrance", "essential_oils", "drying_alcohol", "sulfates", "parabens", "silicones", "comedogenic", "fungal_acne"];

const p = params();
const state = {
  q: p.get("q") || "", category: p.get("category") || "", concern: p.get("concern") || "",
  skin_type: p.get("skin_type") || "", max_price: p.get("max_price") || "",
  brand: p.getAll("brand"), avoid: p.getAll("avoid"), sort: p.get("sort") || "featured",
  page: Number(p.get("page")) || 1,
};

const radio = (name, value, label, extra = "") =>
  `<label><input type="radio" name="${name}" value="${esc(value)}"${state[name] === value ? " checked" : ""}> ${esc(label)}${extra}</label>`;

async function buildFilters() {
  const m = await api.meta();
  $("#f-brand").innerHTML = Object.entries(m.brand_counts).map(([b, n]) =>
    `<label><input type="checkbox" name="brand" value="${esc(b)}"${state.brand.includes(b) ? " checked" : ""}> ${esc(b)}<span class="count">${num(n)}</span></label>`).join("");
  $("#f-category").innerHTML = radio("category", "", "All categories", `<span class="count">${num(m.products)}</span>`) +
    Object.entries(m.categories).map(([c, n]) => radio("category", c, c, `<span class="count">${num(n)}</span>`)).join("");
  $("#f-concern").innerHTML = radio("concern", "", "Any concern") +
    Object.keys(m.concerns).map((c) => radio("concern", c, CONCERN_SHORT[c] || m.concerns[c])).join("");
  $("#f-skin").innerHTML = radio("skin_type", "", "Any skin type") +
    Object.entries(SKIN).map(([k, l]) => radio("skin_type", k, l)).join("");
  $("#f-avoid").innerHTML = AVOID.map((f) =>
    `<label><input type="checkbox" name="avoid" value="${f}"${state.avoid.includes(f) ? " checked" : ""}> ${esc(FAMILY_SHORT[f])}</label>`).join("");
  $("#f-price").value = state.max_price || 3000;
  $("#price-out").textContent = state.max_price ? money(state.max_price) : "any price";
  $("#q").value = state.q;
  $("#sort").value = state.sort;
}

function syncUrl() {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(state)) {
    if (Array.isArray(v)) v.forEach((x) => u.append(k, x));
    else if (v && !(k === "sort" && v === "featured") && !(k === "page" && v === 1)) u.set(k, v);
  }
  history.replaceState(null, "", u.toString() ? `?${u}` : location.pathname);
}

function activeChips(meta) {
  const chips = [];
  state.brand.forEach((b) => chips.push([`brand:${b}`, b]));
  if (state.category) chips.push(["category", state.category]);
  if (state.concern) chips.push(["concern", CONCERN_SHORT[state.concern]]);
  if (state.skin_type) chips.push(["skin_type", `${SKIN[state.skin_type]} skin`]);
  if (state.max_price) chips.push(["max_price", `Under ${money(state.max_price)}`]);
  state.avoid.forEach((f) => chips.push([`avoid:${f}`, `No ${FAMILY_SHORT[f].toLowerCase()}`]));
  $("#active-filters").innerHTML = chips.map(([k, l]) =>
    `<span class="tag tag-line" style="height:30px;padding-right:4px">${esc(l)}<button class="btn-ghost" data-k="${esc(k)}" aria-label="Remove ${esc(l)}" style="border:0;background:none;display:grid;place-items:center;width:22px;height:22px">${icon("x")}</button></span>`).join("");
  const title = state.brand.length === 1 ? state.brand[0] : state.concern ? `For ${CONCERN_SHORT[state.concern].toLowerCase()}`
    : state.category ? `${state.category}s` : "Every product, decoded";
  $("#page-title").textContent = title;
}

let seq = 0;
async function load() {
  const mine = ++seq;
  syncUrl();
  activeChips();
  $("#grid").innerHTML = skeletonCards(8);
  try {
    const r = await api.products({ ...state, page_size: PAGE_SIZE });
    if (mine !== seq) return;
    $("#count").innerHTML = `${num(r.total)} product${r.total === 1 ? "" : "s"}` +
      (r.corrected_to ? ` · no exact match for “${esc(state.q)}”, showing <b>${esc(r.corrected_to)}</b>` : "");
    $("#grid").innerHTML = r.items.length ? r.items.map((x) => productCard(x)).join("")
      : `<div class="card empty" style="grid-column:1/-1"><div class="icon-badge">${icon("search")}</div><h3>No products match</h3><p class="muted small" style="margin-top:6px">Try removing a filter or searching for something broader.</p></div>`;
    renderPagination(r.total);
  } catch (err) {
    $("#grid").innerHTML = errorState(err);
  }
}

function renderPagination(total) {
  const pages = Math.ceil(total / PAGE_SIZE);
  if (pages <= 1) { $("#pagination").innerHTML = ""; return; }
  const cur = state.page;
  const nums = [...new Set([1, cur - 1, cur, cur + 1, pages])].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  let html = `<button class="btn btn-sm btn-icon" data-p="${cur - 1}" ${cur === 1 ? "disabled" : ""} aria-label="Previous page">${icon("back")}</button>`;
  let last = 0;
  for (const n of nums) {
    if (n - last > 1) html += `<span class="subtle">…</span>`;
    html += `<button class="btn btn-sm ${n === cur ? "btn-primary" : ""}" data-p="${n}" style="min-width:40px">${n}</button>`;
    last = n;
  }
  html += `<button class="btn btn-sm btn-icon" data-p="${cur + 1}" ${cur === pages ? "disabled" : ""} aria-label="Next page">${icon("arrow")}</button>`;
  $("#pagination").innerHTML = html;
}

// ----------------------------------------------------------------------- events
$("#filters").addEventListener("change", (e) => {
  const t = e.target;
  if (t.name === "avoid") state.avoid = $$('input[name="avoid"]:checked').map((x) => x.value);
  else if (t.name === "brand") state.brand = $$('input[name="brand"]:checked').map((x) => x.value);
  else if (t.type === "radio") state[t.name] = t.value;
  state.page = 1;
  load();
});
$("#f-price").addEventListener("input", (e) => {
  const v = Number(e.target.value);
  $("#price-out").textContent = v >= 3000 ? "any price" : money(v);
});
$("#f-price").addEventListener("change", (e) => {
  state.max_price = Number(e.target.value) >= 3000 ? "" : e.target.value;
  state.page = 1;
  load();
});
let t;
$("#q").addEventListener("input", (e) => {
  clearTimeout(t);
  t = setTimeout(() => {
    state.q = e.target.value.trim();
    if (state.q && state.sort === "featured") { state.sort = "relevance"; $("#sort").value = "relevance"; }
    state.page = 1;
    load();
  }, 220);
});
$("#sort").addEventListener("change", (e) => { state.sort = e.target.value; state.page = 1; load(); });
$("#pagination").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-p]");
  if (!b) return;
  state.page = Number(b.dataset.p);
  load();
  scrollTo({ top: $(".catalogue").offsetTop - 90, behavior: "smooth" });
});
$("#active-filters").addEventListener("click", async (e) => {
  const b = e.target.closest("button[data-k]");
  if (!b) return;
  const k = b.dataset.k;
  if (k.startsWith("avoid:")) state.avoid = state.avoid.filter((f) => f !== k.slice(6));
  else if (k.startsWith("brand:")) state.brand = state.brand.filter((b) => b !== k.slice(6));
  else state[k] = "";
  state.page = 1;
  await buildFilters();
  load();
});
$("#clear").addEventListener("click", async () => {
  Object.assign(state, { q: "", category: "", concern: "", skin_type: "", max_price: "", brand: [], avoid: [], sort: "featured", page: 1 });
  await buildFilters();
  load();
});
$("#open-filters").addEventListener("click", () => $("#filters").classList.add("open"));
$("#close-filters").addEventListener("click", () => $("#filters").classList.remove("open"));

await buildFilters();
load();
