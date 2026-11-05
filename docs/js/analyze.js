import { mountChrome, loadAll, esc, money, stars, sephoraSearch, ingredientListHTML } from "./common.js";
import { recommend, explain, validateProfile, searchIngredients, effectivePrice, SENSITIVE_DEFAULT_AVOID } from "./recommender.js";
import { loadImage, checkPhoto } from "./image-check.js";

mountChrome();
const { products, ingredients, stats } = await loadAll();
const byKey = new Map(ingredients.map((i) => [i.k, i]));

const SKIN = [["oily", "Oily"], ["dry", "Dry"], ["combination", "Combination"], ["normal", "Normal"], ["unsure", "Not sure"]];
// Families shown in the form, most commonly avoided first.
const FAMILY_ORDER = ["fragrance", "essential_oils", "drying_alcohol", "fragrance_allergens", "sulfates", "parabens",
  "silicones", "comedogenic", "fungal_acne", "pregnancy_caution", "chemical_filters", "strong_actives"];

const $ = (id) => document.getElementById(id);
$("skin").innerHTML = SKIN.map(([v, l]) => `<label class="choice"><input type="radio" name="skin" value="${v}"> ${l}</label>`).join("");
$("concerns").innerHTML = Object.entries(stats.concerns)
  .map(([k, v]) => `<label class="choice"><input type="checkbox" name="concern" value="${k}"> ${esc(v)}</label>`).join("");
$("families").innerHTML = FAMILY_ORDER
  .map((k) => `<label class="choice"><input type="checkbox" name="family" value="${k}"> ${esc(stats.families[k])}</label>`).join("");
$("category").innerHTML = `<option value="any">Any category</option>` +
  Object.keys(stats.categories).map((c) => `<option>${esc(c)}</option>`).join("");

// Up to four concerns.
$("concerns").addEventListener("change", () => {
  const boxes = [...document.querySelectorAll('input[name="concern"]')];
  const n = boxes.filter((b) => b.checked).length;
  boxes.forEach((b) => (b.disabled = !b.checked && n >= 4));
});

// Sensitivity pre-selects the usual irritant families.
document.querySelectorAll('input[name="sens"]').forEach((r) => r.addEventListener("change", () => {
  if (r.value === "high" && r.checked) {
    document.querySelectorAll('input[name="family"]').forEach((b) => {
      if (SENSITIVE_DEFAULT_AVOID.includes(b.value)) b.checked = true;
    });
  }
}));

// ---------------- ingredient pickers ----------------
function picker(prefix) {
  const input = $(`${prefix}-input`);
  const box = $(`${prefix}-suggest`);
  const picked = $(`${prefix}-picked`);
  const keys = [];
  let options = [];
  let active = -1;

  const draw = () => {
    picked.innerHTML = keys.map((k) => `<span class="tag">${esc(byKey.get(k)?.n ?? k)}<button type="button" data-k="${esc(k)}" aria-label="Remove ${esc(byKey.get(k)?.n ?? k)}">×</button></span>`).join("");
  };
  const close = () => { box.hidden = true; input.setAttribute("aria-expanded", "false"); active = -1; };
  const add = (k) => { if (!keys.includes(k)) keys.push(k); input.value = ""; close(); draw(); };

  input.addEventListener("input", () => {
    options = searchIngredients(ingredients, input.value).filter((i) => !keys.includes(i.k));
    if (!options.length) return close();
    box.innerHTML = options.map((o, ix) => `<button type="button" role="option" data-ix="${ix}"><span>${esc(o.n)}</span><span class="muted small">${o.pc} products</span></button>`).join("");
    box.hidden = false;
    input.setAttribute("aria-expanded", "true");
  });
  input.addEventListener("keydown", (e) => {
    if (box.hidden) return;
    const btns = [...box.querySelectorAll("button")];
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      active = (active + (e.key === "ArrowDown" ? 1 : -1) + btns.length) % btns.length;
      btns.forEach((b, i) => b.classList.toggle("active", i === active));
    } else if (e.key === "Enter") {
      e.preventDefault();
      add(options[Math.max(0, active)].k);
    } else if (e.key === "Escape") close();
  });
  box.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) add(options[Number(b.dataset.ix)].k); });
  picked.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    keys.splice(keys.indexOf(b.dataset.k), 1);
    draw();
  });
  input.addEventListener("blur", () => setTimeout(close, 150));
  return { keys, reset: () => { keys.length = 0; draw(); } };
}
const avoid = picker("avoid");
const prefer = picker("prefer");

// ---------------- photo ----------------
const drop = $("drop");
const photo = $("photo");
async function handleFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  $("photo-out").innerHTML = `<p class="muted small" style="margin-top:10px">Checking photo…</p>`;
  try {
    const img = await loadImage(file);
    const res = await checkPhoto(img);
    const out = $("photo-out");
    out.innerHTML = `<div class="photo-result">
      <div id="photo-canvas"></div>
      <div class="stack">
        <ul class="checks">${res.checks.map((c) => `<li><span class="dot ${c.ok === null ? "na" : c.ok ? "ok" : "bad"}"></span>${esc(c.label)}</li>`).join("")}</ul>
        <p class="small ${res.usable ? "" : "muted"}"><strong>${res.usable ? "This photo is usable." : "Please try another photo."}</strong></p>
        <p class="note">Skin-characteristic estimates from photos (the CNN in Module 2) are still being trained and
          evaluated, so we don't show any guesses yet. Your results below use your answers only.</p>
        <button class="btn btn-sm" type="button" id="photo-clear">Remove photo</button>
      </div></div>`;
    $("photo-canvas").append(res.canvas);
    $("photo-clear").addEventListener("click", () => { out.innerHTML = ""; photo.value = ""; });
  } catch (err) {
    $("photo-out").innerHTML = `<p class="errors" style="margin-top:10px">That file could not be read as an image.</p>`;
  }
}
photo.addEventListener("change", () => handleFile(photo.files[0]));
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("drag"); handleFile(e.dataTransfer.files[0]); });

// ---------------- submit ----------------
function readProfile() {
  const val = (name) => document.querySelector(`input[name="${name}"]:checked`)?.value;
  const all = (name) => [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((b) => b.value);
  return {
    skinType: val("skin"),
    sensitivity: val("sens") || "low",
    concerns: all("concern"),
    category: $("category").value,
    budgetMin: $("bmin").value === "" ? NaN : Number($("bmin").value),
    budgetMax: $("bmax").value === "" ? NaN : Number($("bmax").value),
    avoidFamilies: all("family"),
    avoidIngredients: [...avoid.keys],
    preferIngredients: [...prefer.keys],
  };
}

const ctx = {
  ingIndex: ingredients, concernLabels: stats.concerns, familyLabels: stats.families,
  nameOf: (k) => byKey.get(k)?.n ?? k,
};
let lastRun = null;
let shown = 5;

function resultCard(r, rank, u) {
  const p = r.product;
  const price = effectivePrice(p);
  const pct = Math.round(r.score * 100);
  const partLabel = { c: "Concern match", i: "Preferred ingredients", k: "Skin-type fit", b: "Budget fit" };
  const highlight = [...new Set(Object.values(p.e).flat())];
  return `<article class="card result">
    <div class="row"><span class="rank">${rank}</span><div class="tags"><span class="tag">${esc(p.c)}</span>
      ${p.cp === "partial" ? '<span class="tag tag-warn">partial ingredient list</span>' : ""}</div>
      <span class="spacer"></span>
      <div class="score" title="Weighted compatibility score"><div class="score-bar"><i style="width:${pct}%"></i></div><strong>${pct}</strong><span class="muted small">/100</span></div>
    </div>
    <h3>${esc(p.n)}</h3>
    <div class="muted small">${esc(p.b)}${p.s ? ` · ${esc(p.s)}` : ""} · ${money(price)}${p.r ? ` · ${stars(p.r)} ${p.r.toFixed(1)}` : ""}</div>
    <ul class="reasons">
      ${r.reasons.map((t) => `<li>${esc(t)}</li>`).join("")}
      ${r.warnings.map((t) => `<li class="warn">${esc(t)}</li>`).join("")}
    </ul>
    <div class="parts">${Object.entries(r.parts).map(([k, v]) => `<div class="part">${partLabel[k]}<strong>${Math.round(v * 100)}%</strong></div>`).join("")}</div>
    <details class="ings"><summary>Full ingredient list (${p.i.length})</summary>
      <div class="ing-list">${ingredientListHTML(p, ingredients, { avoid: u.avoidFamilies, highlight })}</div>
    </details>
    <div class="row" style="margin-top:12px"><a class="btn btn-sm" href="${sephoraSearch(p)}" target="_blank" rel="noopener">Find at Sephora</a></div>
  </article>`;
}

function renderResults() {
  const { run, u } = lastRun;
  const ex = run.excluded;
  const removed = [
    ex.category && `${ex.category.toLocaleString("en-US")} other categories`,
    ex.budget && `${ex.budget.toLocaleString("en-US")} outside budget`,
    ex.restricted && `${ex.restricted.toLocaleString("en-US")} contain something you avoid`,
    ex.incomplete && `${ex.incomplete.toLocaleString("en-US")} have no ingredient list to check`,
  ].filter(Boolean);
  const top = run.ranked.slice(0, shown).map((r) => ({ ...r, ...explainFor(r, u) }));
  $("results").innerHTML = `
    <div class="card stack">
      <h2>Your shortlist</h2>
      <div class="funnel"><span class="tag">${products.length.toLocaleString("en-US")} products</span>
        ${removed.map((t) => `<span class="arrow">→</span><span class="tag tag-outline">− ${esc(t)}</span>`).join("")}
        <span class="arrow">→</span><span class="tag tag-accent">${run.eligibleCount.toLocaleString("en-US")} eligible</span></div>
      ${run.eligibleCount === 0 ? `<p class="errors">No product passes all your rules. Try widening the budget, choosing “Any category” or avoiding fewer families.</p>` : ""}
    </div>
    <div class="grid" style="margin-top:16px">${top.map((r, i) => resultCard(r, i + 1, u)).join("")}</div>
    ${run.eligibleCount > shown ? `<div class="row" style="justify-content:center;margin-top:16px"><button class="btn" id="more-results">Show 5 more</button></div>` : ""}
    <div class="note disclaimer">These results are informational and based on ingredient lists, retailer labels and your answers.
      They are not a diagnosis or a promise that a product will suit you. Patch-test new products, and see a dermatologist
      if your skin is painful, infected or not improving.</div>`;
  $("more-results")?.addEventListener("click", () => { shown += 5; renderResults(); });
}

// recommend() explains only the top k; reuse its explain logic for "show more".
const explainFor = (r, u) => explain(r.product, u, r.parts, ctx);

$("form").addEventListener("submit", (e) => {
  e.preventDefault();
  const u = readProfile();
  const errors = validateProfile(u);
  $("errors").innerHTML = errors.map((t) => `<div>${esc(t)}</div>`).join("");
  if (errors.length) { $("errors").scrollIntoView({ behavior: "smooth", block: "center" }); return; }
  const run = recommend(products, ingredients, u, { k: 5, ctx });
  lastRun = { run, u };
  shown = 5;
  renderResults();
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
});
$("reset").addEventListener("click", () => {
  avoid.reset(); prefer.reset();
  $("results").innerHTML = ""; $("errors").innerHTML = ""; $("photo-out").innerHTML = "";
  setTimeout(() => document.querySelectorAll('input[name="concern"]').forEach((b) => (b.disabled = false)));
});
