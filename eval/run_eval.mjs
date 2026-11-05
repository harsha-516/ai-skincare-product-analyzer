// Evaluation of the recommender on the predefined personas (report section 4.5).
//
// Relevance labels: a product counts as relevant for a persona when the retailer's own
// "Good for: …" tags include at least one of the persona's concerns. These are marketing
// tags, so they are weak labels (gap G1); the scorer never reads them, which keeps the
// comparison fair. Manually labelled relevance sets can replace them later.
//
// Run from the repository root:  node eval/run_eval.mjs

import { readFileSync, writeFileSync } from "node:fs";
import { recommend, exclusionReason, effectivePrice, DEFAULT_WEIGHTS, explain } from "../docs/js/recommender.js";

const products = JSON.parse(readFileSync("docs/data/products.json", "utf8"));
const ingIndex = JSON.parse(readFileSync("docs/data/ingredients.json", "utf8"));
const stats = JSON.parse(readFileSync("docs/data/stats.json", "utf8"));
const personas = JSON.parse(readFileSync("eval/personas.json", "utf8"));
const K = 5;

const ctx = {
  ingIndex,
  concernLabels: stats.concerns,
  familyLabels: stats.families,
  nameOf: (k) => ingIndex.find((x) => x.k === k)?.n ?? k,
};

const isRelevant = (p, u) => p.gf.some((c) => u.concerns.includes(c));

// Independent constraint check: recompute families from the ingredient table, not p.f.
function violates(p, u) {
  const v = [];
  if (u.category !== "any" && p.c !== u.category) v.push("category");
  const price = effectivePrice(p);
  if (price < u.budgetMin || price > u.budgetMax) v.push("budget");
  if (u.avoidFamilies.length || u.avoidIngredients.length) {
    if (p.cp === "missing") v.push("unverifiable");
    const ings = p.i.map((ix) => ingIndex[ix]);
    if (ings.some((ing) => ing.f.some((f) => u.avoidFamilies.includes(f)))) v.push("family");
    if (ings.some((ing) => u.avoidIngredients.includes(ing.k))) v.push("ingredient");
  }
  return v;
}

function metrics(list, u, totalRelevant) {
  const top = list.slice(0, K);
  const rel = top.map((p) => (isRelevant(p, u) ? 1 : 0));
  const hits = rel.reduce((a, b) => a + b, 0);
  const dcg = rel.reduce((s, r, i) => s + r / Math.log2(i + 2), 0);
  const ideal = Array.from({ length: Math.min(K, totalRelevant) }, (_, i) => 1 / Math.log2(i + 2)).reduce((a, b) => a + b, 0);
  return {
    p: top.length ? hits / K : 0,
    r: totalRelevant ? hits / Math.min(K, totalRelevant) : 0,
    ndcg: ideal ? dcg / ideal : 0,
  };
}

function seeded(seed) {
  let s = seed;
  return () => ((s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296);
}

const mean = (xs) => xs.reduce((a, b) => a + b, 0) / (xs.length || 1);
const pct = (x) => `${(100 * x).toFixed(1)}%`;
const f3 = (x) => x.toFixed(3);

const methods = { ours: [], popularity: [], cheapest: [], random: [], noC: [], noK: [], noB: [], noI: [] };
const perPersona = [];
let violationsOurs = 0;
let violationsNaive = 0;
let checked = 0;
let checkedNaive = 0;
let explained = 0;
let withThree = 0;
const jaccards = [];

for (const u of personas) {
  const eligible = products.filter((p) => !exclusionReason(p, u, ingIndex));
  const totalRelevant = eligible.filter((p) => isRelevant(p, u)).length;
  const run = recommend(products, ingIndex, u, { k: K, ctx });
  const ours = run.results.map((r) => r.product);
  const m = metrics(ours, u, totalRelevant);
  methods.ours.push(m);

  for (const p of ours) {
    checked++;
    if (violates(p, u).length) violationsOurs++;
  }
  for (const r of run.results) {
    explained++;
    if (r.reasons.length >= 3) withThree++;
  }

  // Naive baseline without hard filters: most-loved products in the category.
  const naive = products.filter((p) => u.category === "any" || p.c === u.category)
    .sort((a, b) => b.lv - a.lv).slice(0, K);
  for (const p of naive) {
    checkedNaive++;
    if (violates(p, u).length) violationsNaive++;
  }

  methods.popularity.push(metrics([...eligible].sort((a, b) => b.lv - a.lv), u, totalRelevant));
  methods.cheapest.push(metrics([...eligible].sort((a, b) => effectivePrice(a) - effectivePrice(b)), u, totalRelevant));
  const rnd = [];
  for (let s = 1; s <= 30; s++) {
    const r = seeded(s);
    rnd.push(metrics([...eligible].map((p) => [r(), p]).sort((a, b) => a[0] - b[0]).map((x) => x[1]), u, totalRelevant));
  }
  methods.random.push({ p: mean(rnd.map((x) => x.p)), r: mean(rnd.map((x) => x.r)), ndcg: mean(rnd.map((x) => x.ndcg)) });

  for (const [name, key] of [["noC", "c"], ["noK", "k"], ["noB", "b"], ["noI", "i"]]) {
    const w = { ...DEFAULT_WEIGHTS, [key]: 0 };
    methods[name].push(metrics(recommend(products, ingIndex, u, { k: K, weights: w }).results.map((r) => r.product), u, totalRelevant));
  }

  // Weight sensitivity: move each weight by ±0.1 and compare the top-5 sets.
  const base = new Set(ours.map((p) => p.id));
  for (const key of Object.keys(DEFAULT_WEIGHTS)) {
    for (const d of [-0.1, 0.1]) {
      const w = { ...DEFAULT_WEIGHTS, [key]: Math.max(0, DEFAULT_WEIGHTS[key] + d) };
      const ids = recommend(products, ingIndex, u, { k: K, weights: w }).results.map((r) => r.product.id);
      const inter = ids.filter((id) => base.has(id)).length;
      const uni = new Set([...ids, ...base]).size;
      jaccards.push(uni ? inter / uni : 1);
    }
  }

  perPersona.push({ id: u.id, label: u.label, eligible: eligible.length, relevant: totalRelevant, ...m,
    top: ours.map((p) => `${p.b} — ${p.n}`) });
}

const summary = Object.fromEntries(Object.entries(methods).map(([k, v]) => [k, {
  p: mean(v.map((x) => x.p)), r: mean(v.map((x) => x.r)), ndcg: mean(v.map((x) => x.ndcg)),
}]));

const out = {
  generated: new Date().toISOString().slice(0, 10),
  personas: personas.length,
  k: K,
  summary,
  violationRate: violationsOurs / checked,
  naiveViolationRate: violationsNaive / checkedNaive,
  explanationCoverage: withThree / explained,
  weightSensitivityJaccard: mean(jaccards),
  perPersona,
};
writeFileSync("docs/data/evaluation.json", JSON.stringify(out, null, 1));

const names = {
  ours: "Constraints first + weighted score (this project)",
  popularity: "Most-loved among eligible products",
  cheapest: "Cheapest among eligible products",
  random: "Random among eligible products (mean of 30 seeds)",
  noC: "Ablation: without concern match C",
  noI: "Ablation: without preferred-ingredient match I",
  noK: "Ablation: without skin-type fit K",
  noB: "Ablation: without budget fit B",
};
const md = [
  "# Evaluation — recommender on predefined personas",
  "",
  `Generated by \`eval/run_eval.mjs\` on ${out.generated}. ${personas.length} personas, K = ${K}.`,
  "",
  "Relevance labels are the retailer's own \"Good for\" tags. They are marketing tags, so treat",
  "these as weak labels. The scorer never reads them. Swap in manually labelled relevance sets",
  "when the team has them (objective O5).",
  "",
  "## Constraint filtering (O4)",
  "",
  "| Check | Result |", "|---|---|",
  `| Constraint violation rate, this project (top ${K}) | **${pct(out.violationRate)}** (${violationsOurs} of ${checked}) |`,
  `| Violation rate, naive most-loved list without filters | ${pct(out.naiveViolationRate)} (${violationsNaive} of ${checkedNaive}) |`,
  "",
  "Violations are rechecked independently from the ingredient table: category, budget,",
  "avoided ingredient families, avoided ingredients, and lists that are missing and so cannot",
  "be checked.",
  "",
  "## Ranking quality (O5)",
  "",
  `| Method | Precision@${K} | Recall@${K} | NDCG@${K} |`, "|---|---|---|---|",
  ...Object.keys(names).map((k) => `| ${names[k]} | ${f3(summary[k].p)} | ${f3(summary[k].r)} | ${f3(summary[k].ndcg)} |`),
  "",
  `Weight sensitivity: moving any one weight by ±0.1 keeps a mean top-${K} Jaccard overlap of`,
  `**${f3(out.weightSensitivityJaccard)}** with the default ranking.`,
  "",
  "## Explanations (O6)",
  "",
  `${pct(out.explanationCoverage)} of recommended products show at least three plain-language reasons.`,
  "",
  "## Per persona",
  "",
  `| ID | Persona | Eligible | Relevant | P@${K} | NDCG@${K} | Top result |`, "|---|---|---|---|---|---|---|",
  ...perPersona.map((r) => `| ${r.id} | ${r.label} | ${r.eligible} | ${r.relevant} | ${f3(r.p)} | ${f3(r.ndcg)} | ${(r.top[0] || "—").replace(/\|/g, "/")} |`),
  "",
];
writeFileSync("report/evaluation.md", md.join("\n"));
console.log(JSON.stringify({ summary, violationRate: out.violationRate, naive: out.naiveViolationRate, expl: out.explanationCoverage, jac: out.weightSensitivityJaccard }, null, 1));
for (const r of perPersona) console.log(r.id, r.eligible, r.relevant, f3(r.p), r.top[0]);
