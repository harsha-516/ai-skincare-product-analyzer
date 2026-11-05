import { api, mountChrome, hydrateIcons, productVisual, icon, esc, num, money,
  retailerLink, CONCERN_SHORT, FAMILY_SHORT, $, $$, toast } from "./ui.js";
import { loadImage, checkPhoto } from "./image-check.js";

mountChrome();
hydrateIcons();

const STEPS = [["Your skin", "Type and sensitivity"], ["Concerns", "Up to four"], ["Product & budget", "Type and price"],
  ["Ingredients", "Avoid and prefer"], ["Photo check", "Optional"]];
const SKIN = [["oily", "Oily", "Shiny by midday, visible pores"], ["dry", "Dry", "Tight, flaky or rough"],
  ["combination", "Combination", "Oily T-zone, drier cheeks"], ["normal", "Normal", "Comfortable, rarely shiny"],
  ["unsure", "Not sure", "We won't use skin-type labels"]];
const SENS = [["low", "Rarely reacts", "Most products feel fine"], ["high", "Highly sensitive", "Stings, redness or rashes are common"]];
const CONCERN_DESC = {
  acne: "Spots, blackheads, clogged pores", oiliness: "Shine and excess sebum", pores: "Enlarged or visible pores",
  dryness: "Tightness, flaking, dehydration", redness: "Flushing, irritation, reactivity", dark_spots: "Marks, pigmentation, uneven tone",
  dullness: "Rough texture, lack of glow", ageing: "Fine lines, loss of firmness", dark_circles: "Under-eye shadows, puffiness",
  sun: "Daily UV protection",
};
const FAMILY_ORDER = ["fragrance", "essential_oils", "drying_alcohol", "fragrance_allergens", "sulfates", "parabens",
  "silicones", "comedogenic", "fungal_acne", "pregnancy_caution", "chemical_filters", "strong_actives"];
const PRESETS = [["Under $20", 0, 20], ["$20 – $50", 20, 50], ["$50 – $100", 50, 100], ["Any price", 0, 1000]];
const SENSITIVE_DEFAULT = ["fragrance", "essential_oils", "drying_alcohol"];

const meta = await api.meta();
let step = 0;

// ----------------------------------------------------------------------- render options
const opt = (type, name, value, title, desc = "", extra = "") => `<label class="option">
  <input type="${type}" name="${name}" value="${esc(value)}"${extra}><span class="mark">${icon("check")}</span>
  <span><strong>${esc(title)}</strong>${desc ? `<span class="desc">${esc(desc)}</span>` : ""}</span></label>`;

$("#skin").innerHTML = SKIN.map(([v, t, d]) => opt("radio", "skin", v, t, d)).join("");
$("#sens").innerHTML = SENS.map(([v, t, d]) => opt("radio", "sens", v, t, d, v === "low" ? " checked" : "")).join("");
$("#concerns").innerHTML = Object.keys(meta.concerns).map((c) => opt("checkbox", "concern", c, CONCERN_SHORT[c], CONCERN_DESC[c])).join("");
$("#category").innerHTML = opt("radio", "category", "any", "Any type", "Show the best overall", " checked") +
  Object.entries(meta.categories).map(([c, n]) => opt("radio", "category", c, c, `${num(n)} products`)).join("");
$("#families").innerHTML = FAMILY_ORDER.map((f) => opt("checkbox", "family", f, FAMILY_SHORT[f], meta.families[f])).join("");
$("#presets").innerHTML = PRESETS.map(([l, a, b]) => `<button type="button" class="chip" data-min="${a}" data-max="${b}">${l}</button>`).join("");
$("#stepper").innerHTML = STEPS.map(([t, s], i) => `<button type="button" data-i="${i}"><span class="dot">${i + 1}</span><span>${t}<small>${s}</small></span></button>`).join("");

// ----------------------------------------------------------------------- ingredient pickers
function picker(prefix) {
  const input = $(`#${prefix}-input`);
  const box = $(`#${prefix}-suggest`);
  const picked = $(`#${prefix}-picked`);
  const items = new Map();
  let options = [];
  let active = -1;
  let t;
  const draw = () => {
    picked.innerHTML = [...items].map(([k, n]) => `<span class="tag tag-line">${esc(n)}<button type="button" data-k="${esc(k)}" aria-label="Remove ${esc(n)}">${icon("x")}</button></span>`).join("");
  };
  const close = () => { box.classList.add("hidden"); input.setAttribute("aria-expanded", "false"); active = -1; };
  const add = (o) => { items.set(o.key, o.name); input.value = ""; close(); draw(); onChange(); };
  input.addEventListener("input", () => {
    clearTimeout(t);
    const q = input.value.trim();
    if (q.length < 2) return close();
    t = setTimeout(async () => {
      const r = await api.ingredients({ q, limit: 8 });
      options = r.items.filter((o) => !items.has(o.key));
      if (!options.length || input.value.trim() !== q) return close();
      box.innerHTML = options.map((o, i) => `<button type="button" role="option" data-i="${i}"><span>${esc(o.name)}</span><span class="xs subtle">in ${num(o.product_count)} products</span></button>`).join("");
      box.classList.remove("hidden");
      input.setAttribute("aria-expanded", "true");
    }, 160);
  });
  input.addEventListener("keydown", (e) => {
    if (box.classList.contains("hidden")) { if (e.key === "Enter") e.preventDefault(); return; }
    const btns = $$("button", box);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      active = (active + (e.key === "ArrowDown" ? 1 : -1) + btns.length) % btns.length;
      btns.forEach((b, i) => b.classList.toggle("active", i === active));
    } else if (e.key === "Enter") { e.preventDefault(); add(options[Math.max(0, active)]); }
    else if (e.key === "Escape") close();
  });
  box.addEventListener("mousedown", (e) => { const b = e.target.closest("button"); if (b) { e.preventDefault(); add(options[Number(b.dataset.i)]); } });
  picked.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { items.delete(b.dataset.k); draw(); onChange(); } });
  input.addEventListener("blur", () => setTimeout(close, 120));
  return { items, set: (list) => { items.clear(); list.forEach(([k, n]) => items.set(k, n)); draw(); } };
}
const avoid = picker("avoid");
const prefer = picker("prefer");

// ----------------------------------------------------------------------- state
const val = (name) => $(`input[name="${name}"]:checked`)?.value;
const all = (name) => $$(`input[name="${name}"]:checked`).map((b) => b.value);
function profile() {
  return {
    skin_type: val("skin"), sensitivity: val("sens") || "low", concerns: all("concern"),
    category: val("category") || "any", budget_min: Number($("#bmin").value || 0), budget_max: Number($("#bmax").value || 0),
    avoid_families: all("family"), avoid_ingredients: [...avoid.items.keys()], prefer_ingredients: [...prefer.items.keys()],
  };
}
const STORE = "skinanalyzer.answers";
function onChange() {
  try { sessionStorage.setItem(STORE, JSON.stringify({ ...profile(), avoidNames: [...avoid.items], preferNames: [...prefer.items] })); } catch {}
}
function restore() {
  let s;
  try { s = JSON.parse(sessionStorage.getItem(STORE)); } catch {}
  if (!s) return;
  const check = (name, v) => { const el = $(`input[name="${name}"][value="${CSS.escape(v)}"]`); if (el) el.checked = true; };
  if (s.skin_type) check("skin", s.skin_type);
  check("sens", s.sensitivity);
  s.concerns.forEach((c) => check("concern", c));
  check("category", s.category);
  s.avoid_families.forEach((f) => check("family", f));
  $("#bmin").value = s.budget_min; $("#bmax").value = s.budget_max;
  avoid.set(s.avoidNames || []); prefer.set(s.preferNames || []);
}

function stepErrors(i) {
  const u = profile();
  if (i === 0 && !u.skin_type) return ["Choose a skin type, or pick “Not sure”."];
  if (i === 2) {
    if ($("#bmin").value === "" || $("#bmax").value === "") return ["Enter a minimum and maximum budget."];
    if (u.budget_min < 0 || u.budget_max < 0) return ["Budget cannot be negative."];
    if (u.budget_min > u.budget_max) return ["The minimum budget is above the maximum."];
  }
  if (i === 3) {
    const clash = u.prefer_ingredients.filter((k) => u.avoid_ingredients.includes(k));
    if (clash.length) return [`${clash.map((k) => avoid.items.get(k)).join(", ")} is both preferred and avoided.`];
  }
  return [];
}
const showErrors = (errs) => { $("#errors").innerHTML = errs.map((e) => `${icon("alert")}<span>${esc(e)}</span>`).join(""); };

function go(i) {
  step = i;
  $$(".panel").forEach((p) => p.classList.toggle("active", Number(p.dataset.step) === i));
  $$("#stepper button").forEach((b, j) => { b.classList.toggle("current", j === i); b.classList.toggle("done", j < i); });
  $("#progress").style.width = `${((i + 1) / STEPS.length) * 100}%`;
  $("#back").style.visibility = i === 0 ? "hidden" : "visible";
  $("#next").innerHTML = i === STEPS.length - 1 ? `See my results ${icon("arrow")}` : `Continue ${icon("arrow")}`;
  showErrors([]);
}

// ----------------------------------------------------------------------- events
$("#form").addEventListener("change", (e) => {
  if (e.target.name === "concern") {
    const n = all("concern").length;
    $$('input[name="concern"]').forEach((b) => (b.disabled = !b.checked && n >= 4));
    $("#concern-count").textContent = `${n} of 4 selected`;
  }
  if (e.target.name === "sens" && e.target.value === "high") {
    SENSITIVE_DEFAULT.forEach((f) => { $(`input[name="family"][value="${f}"]`).checked = true; });
    toast("Fragrance, essential oils and drying alcohols will be avoided");
  }
  onChange();
});
$("#presets").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  $("#bmin").value = b.dataset.min; $("#bmax").value = b.dataset.max;
  onChange();
});
$("#next").addEventListener("click", () => {
  const errs = stepErrors(step);
  if (errs.length) return showErrors(errs);
  if (step < STEPS.length - 1) { go(step + 1); scrollTo({ top: 0, behavior: "smooth" }); } else submit();
});
$("#back").addEventListener("click", () => go(Math.max(0, step - 1)));
$("#stepper").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  const target = Number(b.dataset.i);
  for (let i = 0; i < target; i++) { const errs = stepErrors(i); if (errs.length) { go(i); return showErrors(errs); } }
  go(target);
});

// ----------------------------------------------------------------------- photo
async function handleFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  const out = $("#photo-out");
  out.innerHTML = `<div class="notice">${icon("camera")}<span>Checking your photo…</span></div>`;
  try {
    const res = await checkPhoto(await loadImage(file));
    out.innerHTML = `<div class="card card-soft photo-result" style="padding:18px"><div id="photo-canvas"></div><div class="stack">
      <h3>${res.usable ? "Your photo looks good" : "Try a different photo"}</h3>
      <ul class="checks">${res.checks.map((c) => `<li>${icon(c.ok === null ? "info" : c.ok ? "check" : "x", c.ok === null ? "na" : c.ok ? "ok" : "bad")}<span>${esc(c.label)}</span></li>`).join("")}</ul>
      <button type="button" class="btn btn-sm" id="photo-clear">${icon("x")} Remove photo</button></div></div>`;
    $("#photo-canvas").append(res.canvas);
    $("#photo-clear").addEventListener("click", () => { out.innerHTML = ""; $("#photo").value = ""; });
  } catch {
    out.innerHTML = `<div class="alert">${icon("alert")}<span>That file could not be read as an image.</span></div>`;
  }
}
$("#photo").addEventListener("change", (e) => handleFile(e.target.files[0]));
const drop = $("#drop");
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("drag"); handleFile(e.dataTransfer.files[0]); });

// ----------------------------------------------------------------------- results
const PART = { c: ["Concern match", "35%"], i: ["Preferred ingredients", "25%"], k: ["Skin-type fit", "20%"], b: ["Budget fit", "20%"] };
const FUNNEL = [["category", "Other categories", "#d8ccbf"], ["budget", "Outside budget", "#c7b6a6"],
  ["restricted", "Contain something you avoid", "#a85a3f"], ["incomplete", "No ingredient list to check", "#e2c1b1"]];
let limit = 5;
let lastProfile;

function resultCard(r, i, u) {
  const p = r.product;
  const score = Math.round(r.score * 100);
  return `<article class="result">
    <a href="product.html?id=${encodeURIComponent(p.id)}">${productVisual(p)}</a>
    <div>
      <div class="result-top">
        <div><span class="rank-label">${i === 0 ? "Best match" : `Match #${i + 1}`}</span>
          <h3><a href="product.html?id=${encodeURIComponent(p.id)}">${esc(p.name)}</a></h3>
          <div class="row small muted" style="margin-top:6px;gap:10px">${esc(p.brand)} · ${money(p.effective_price)}${p.rating ? ` · <span class="rating">${icon("star")}<b>${p.rating.toFixed(1)}</b></span>` : ""}</div></div>
        <div class="ring" style="--v:${score};--size:72px"><div><b>${score}</b><small>match</small></div></div>
      </div>
      <ul class="reasons">${r.reasons.map((t) => `<li>${icon("check")}<span>${esc(t)}</span></li>`).join("")}
        ${r.warnings.map((t) => `<li class="warn">${icon("alert")}<span>${esc(t)}</span></li>`).join("")}</ul>
      <div class="bars">${Object.entries(r.parts).map(([k, v]) => `<div><div class="bar-label"><span>${PART[k][0]}</span><b>${Math.round(v * 100)}%</b></div><div class="bar"><i style="width:${v * 100}%"></i></div></div>`).join("")}</div>
      <div class="row" style="margin-top:18px">
        <a class="btn btn-sm btn-primary" href="product.html?id=${encodeURIComponent(p.id)}">View ingredients</a>
        <a class="btn btn-sm" href="${retailerLink(p)}" target="_blank" rel="noopener">Find at retailer ${icon("external")}</a>
      </div>
    </div></article>`;
}

function summaryTags(u) {
  const t = [`${SKIN.find((s) => s[0] === u.skin_type)[1]} skin`, u.sensitivity === "high" ? "Highly sensitive" : null,
    ...u.concerns.map((c) => CONCERN_SHORT[c]), u.category === "any" ? "Any product type" : u.category,
    u.budget_max >= 1000 ? "Any price" : `${money(u.budget_min)}–${money(u.budget_max)}`,
    ...u.avoid_families.map((f) => `No ${FAMILY_SHORT[f].toLowerCase()}`), ...[...avoid.items.values()].map((n) => `No ${n}`)].filter(Boolean);
  return t.map((x) => `<span class="tag tag-line">${esc(x)}</span>`).join("");
}

async function submit(more = false) {
  const u = more ? lastProfile : profile();
  lastProfile = u;
  if (!more) limit = 5;
  const btn = $("#next");
  btn.disabled = true;
  try {
    const r = await api.recommend({ ...u, limit });
    $("#wizard").classList.add("hidden");
    $("#intro").classList.add("hidden");
    const res = $("#results");
    res.classList.remove("hidden");
    const removed = r.total - r.eligible;
    res.innerHTML = `
      <div class="results-head">
        <div><span class="eyebrow">Your shortlist</span><h1 style="font-size:clamp(2.2rem,4.5vw,3.4rem);margin-top:12px">${r.eligible ? `${num(r.eligible)} products fit your rules` : "Nothing fits every rule yet"}</h1>
          <div class="tags" style="margin-top:16px">${summaryTags(u)}</div></div>
        <button class="btn" id="edit">${icon("back")} Edit answers</button>
      </div>
      <div class="card funnel" style="margin-bottom:28px">
        <div class="row" style="justify-content:space-between"><h4>From ${num(r.total)} products to your shortlist</h4><span class="small muted">${num(removed)} removed by your rules</span></div>
        <div class="funnel-bar">${FUNNEL.map(([k, , c]) => r.excluded[k] ? `<span style="width:${(r.excluded[k] / r.total) * 100}%;background:${c}" title="${num(r.excluded[k])}"></span>` : "").join("")}
          <span style="width:${(r.eligible / r.total) * 100}%;background:var(--sage)"></span></div>
        <div class="funnel-legend">${FUNNEL.filter(([k]) => r.excluded[k]).map(([k, l, c]) => `<span><i style="background:${c}"></i>${num(r.excluded[k])} ${l.toLowerCase()}</span>`).join("")}
          <span><i style="background:var(--sage)"></i>${num(r.eligible)} eligible</span></div>
      </div>
      ${r.eligible === 0 ? `<div class="card empty"><div class="icon-badge">${icon("filter")}</div><h3>Try loosening a rule</h3><p class="muted small" style="margin-top:6px">Widen your budget, choose “Any type”, or avoid fewer ingredient groups.</p></div>` : ""}
      <div id="result-list">${r.results.map((x, i) => resultCard(x, i, u)).join("")}</div>
      ${r.eligible > r.results.length ? `<div class="row" style="justify-content:center;margin-top:28px"><button class="btn" id="more">Show 5 more matches</button></div>` : ""}
      <div class="notice" style="margin-top:32px">${icon("info")}<span>Results are informational guidance based on ingredient lists, retailer labels and your answers, not a diagnosis.
        Patch-test new products, and see a dermatologist if your skin is painful, infected or not improving.</span></div>`;
    $("#edit").addEventListener("click", () => { res.classList.add("hidden"); $("#wizard").classList.remove("hidden"); $("#intro").classList.remove("hidden"); go(0); scrollTo({ top: 0 }); });
    $("#more")?.addEventListener("click", () => { limit += 5; submit(true); });
    if (!more) scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    if (err.status === 422 && err.detail?.errors) showErrors(err.detail.errors);
    else showErrors([err.message || "Something went wrong. Please try again."]);
  } finally {
    btn.disabled = false;
  }
}

restore();
const restored = all("concern").length;
$$('input[name="concern"]').forEach((b) => (b.disabled = !b.checked && restored >= 4));
$("#concern-count").textContent = `${restored} of 4 selected`;
go(0);
