// Modules 1, 4 and 5 — profile validation, constraint filtering, scoring and explanations.
// Pure functions with no DOM access, so the website and eval/run_eval.mjs run the same code.
//
//   S(p,u) = w_c·C + w_i·I + w_k·K + w_b·B      (report section 4.3.4)
//
// Hard rules (budget, category, restricted ingredients) remove a product before scoring and
// are never overridden by a high score. A component with no user input (no concerns, no
// preferred ingredients) is left out and the remaining weights are renormalised.

export const DEFAULT_WEIGHTS = { c: 0.35, i: 0.25, k: 0.2, b: 0.2 };

export const SKIN_TYPES = ["oily", "dry", "combination", "normal", "unsure"];

// Families pre-selected for avoidance when a user marks their skin as highly sensitive.
export const SENSITIVE_DEFAULT_AVOID = ["fragrance", "essential_oils", "drying_alcohol"];

export function effectivePrice(p) {
  return p.sp != null && p.sp > 0 && p.sp < p.p ? p.sp : p.p;
}

export function validateProfile(u) {
  const errors = [];
  if (!u || typeof u !== "object") return ["Profile is missing."];
  if (!SKIN_TYPES.includes(u.skinType)) errors.push("Choose a skin type, or pick “Not sure”.");
  const min = Number(u.budgetMin);
  const max = Number(u.budgetMax);
  if (!Number.isFinite(min) || !Number.isFinite(max)) errors.push("Enter a budget range.");
  else {
    if (min < 0 || max < 0) errors.push("Budget cannot be negative.");
    if (min > max) errors.push("The minimum budget is above the maximum.");
  }
  if ((u.concerns || []).length > 4) errors.push("Pick up to four concerns so results stay focused.");
  const clash = (u.preferIngredients || []).filter((k) => (u.avoidIngredients || []).includes(k));
  if (clash.length) errors.push(`An ingredient cannot be both preferred and avoided: ${clash.join(", ")}.`);
  return errors;
}

// Hard eligibility filters. Returns null when eligible, otherwise the reason it was removed.
export function exclusionReason(p, u, ingIndex) {
  if (u.category && u.category !== "any" && p.c !== u.category) return "category";
  const price = effectivePrice(p);
  if (price < Number(u.budgetMin) || price > Number(u.budgetMax)) return "budget";
  const avoidF = u.avoidFamilies || [];
  const avoidI = u.avoidIngredients || [];
  if (avoidF.length || avoidI.length) {
    // A restriction cannot be checked on a missing ingredient list.
    if (p.cp === "missing") return "incomplete";
    if (avoidF.some((f) => p.f.includes(f))) return "restricted";
    if (avoidI.length) {
      const keys = new Set(p.i.map((ix) => ingIndex[ix].k));
      if (avoidI.some((k) => keys.has(k))) return "restricted";
    }
  }
  return null;
}

export function componentScores(p, u, ingIndex) {
  const parts = {};
  const concerns = u.concerns || [];
  if (concerns.length) {
    parts.c = concerns.reduce((s, c) => s + (p.cs[c] || 0), 0) / concerns.length;
  }
  const prefer = u.preferIngredients || [];
  if (prefer.length) {
    const keys = new Set(p.i.map((ix) => ingIndex[ix].k));
    parts.i = prefer.filter((k) => keys.has(k)).length / prefer.length;
  }
  if (!p.st.length || u.skinType === "unsure") parts.k = 0.5;
  else parts.k = p.st.includes(u.skinType) ? 1 : 0.2;
  const min = Number(u.budgetMin);
  const max = Number(u.budgetMax);
  const price = effectivePrice(p);
  parts.b = max > min ? 1 - (0.6 * (price - min)) / (max - min) : 1;
  return parts;
}

export function combine(parts, weights = DEFAULT_WEIGHTS) {
  let s = 0;
  let w = 0;
  for (const key of Object.keys(parts)) {
    s += weights[key] * parts[key];
    w += weights[key];
  }
  return w > 0 ? s / w : 0;
}

function popularity(p) {
  return (p.r || 0) * Math.log10((p.rv || 0) + 1);
}

const money = (v) => `$${v % 1 === 0 ? v.toFixed(0) : v.toFixed(2)}`;
const list = (xs) => (xs.length <= 1 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}`);

export function explain(p, u, parts, ctx) {
  const { ingIndex, concernLabels, familyLabels } = ctx;
  const reasons = [];
  const warnings = [];
  const price = effectivePrice(p);
  const catText = u.category && u.category !== "any" ? `A ${p.c.toLowerCase()}, as you asked, ` : `A ${p.c.toLowerCase()} `;
  reasons.push(`${catText}at ${money(price)}, inside your ${money(Number(u.budgetMin))}–${money(Number(u.budgetMax))} budget.`);

  for (const c of u.concerns || []) {
    const ev = p.e[c];
    const label = (concernLabels[c] || c).toLowerCase();
    if (ev && ev.length) reasons.push(`For ${label}: contains ${list(ev.slice(0, 3))}.`);
    else warnings.push(`Nothing in the ingredient list is matched to ${label}.`);
  }
  const prefer = u.preferIngredients || [];
  if (prefer.length) {
    const byKey = new Map(p.i.map((ix) => [ingIndex[ix].k, ingIndex[ix].n]));
    const hit = prefer.filter((k) => byKey.has(k)).map((k) => byKey.get(k));
    if (hit.length) reasons.push(`Contains ${list(hit)}, which you said you prefer.`);
  }
  const avoided = [...(u.avoidFamilies || []).map((f) => (familyLabels[f] || f).toLowerCase()),
    ...(u.avoidIngredients || []).map((k) => ctx.nameOf(k))];
  if (avoided.length) {
    reasons.push(`Free of what you asked to avoid: ${list(avoided)}.`);
    if (p.cp === "partial") warnings.push("Part of this ingredient list could not be matched, so double-check the label.");
  }
  if (p.st.length && u.skinType !== "unsure") {
    if (p.st.includes(u.skinType)) reasons.push(`The retailer lists it for ${list(p.st)} skin, which includes yours.`);
    else warnings.push(`The retailer lists it for ${list(p.st)} skin, not ${u.skinType}.`);
  }
  if (p.r && p.rv >= 20) reasons.push(`Rated ${p.r.toFixed(1)} out of 5 from ${p.rv.toLocaleString("en-US")} reviews.`);
  if (!(u.avoidFamilies || []).includes("pregnancy_caution") && p.f.includes("pregnancy_caution")) {
    warnings.push("Contains an ingredient flagged for pregnancy caution.");
  }
  if (u.sensitivity === "high" && p.f.includes("strong_actives")) {
    warnings.push("Has a strong active. Patch-test it first and introduce it slowly.");
  }
  return { reasons, warnings };
}

export function recommend(products, ingIndex, u, opts = {}) {
  const k = opts.k ?? 5;
  const weights = opts.weights ?? DEFAULT_WEIGHTS;
  const excluded = { category: 0, budget: 0, restricted: 0, incomplete: 0 };
  const eligible = [];
  for (const p of products) {
    const why = exclusionReason(p, u, ingIndex);
    if (why) excluded[why]++;
    else eligible.push(p);
  }
  const scored = eligible.map((p) => {
    const parts = componentScores(p, u, ingIndex);
    return { product: p, parts, score: combine(parts, weights) };
  });
  scored.sort((a, b) => b.score - a.score || popularity(b.product) - popularity(a.product));
  const top = scored.slice(0, k).map((r) => ({
    ...r,
    ...(opts.ctx ? explain(r.product, u, r.parts, opts.ctx) : {}),
  }));
  return { results: top, eligibleCount: eligible.length, excluded, ranked: scored };
}

// Module 3 helper for the site: map typed text to the closest ingredient keys.
export function searchIngredients(ingIndex, text, limit = 8) {
  const q = text.trim().toLowerCase();
  if (q.length < 2) return [];
  const starts = [];
  const contains = [];
  for (const ing of ingIndex) {
    const n = ing.n.toLowerCase();
    if (n.startsWith(q) || ing.k.startsWith(q)) starts.push(ing);
    else if (n.includes(q) || ing.k.includes(q)) contains.push(ing);
  }
  const byUse = (a, b) => b.pc - a.pc;
  return [...starts.sort(byUse), ...contains.sort(byUse)].slice(0, limit);
}
