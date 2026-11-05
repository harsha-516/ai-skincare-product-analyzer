// Shared header, footer and data loading for every page.

export const REPO_URL = "https://github.com/harsha-516/ai-skincare-product-analyzer";

const NAV = [
  ["index.html", "Home"],
  ["analyze.html", "Analyse my skin"],
  ["products.html", "Products"],
  ["ingredients.html", "Ingredients"],
  ["project.html", "The project"],
];

export function mountChrome() {
  const here = location.pathname.split("/").pop() || "index.html";
  const header = document.createElement("header");
  header.className = "site-header";
  header.innerHTML = `
    <div class="wrap">
      <a class="brand" href="index.html">Skin<span>Analyzer</span></a>
      <nav class="nav" id="nav">
        ${NAV.map(([href, label]) => `<a href="${href}"${href === here ? ' aria-current="page"' : ""}>${label}</a>`).join("")}
      </nav>
      <a class="btn btn-primary btn-sm header-cta" href="analyze.html">Start analysis</a>
      <button class="btn btn-sm menu-btn" aria-expanded="false" aria-controls="nav">Menu</button>
    </div>`;
  document.body.prepend(header);
  const btn = header.querySelector(".menu-btn");
  btn.addEventListener("click", () => {
    const open = header.querySelector(".nav").classList.toggle("open");
    btn.setAttribute("aria-expanded", String(open));
  });

  const footer = document.createElement("footer");
  footer.className = "site-footer";
  footer.innerHTML = `
    <div class="wrap">
      <div>AI Skincare Product Analyzer · PRJ1 student project · Keerthana, Prateek, Harsha, Karthik</div>
      <div class="row">
        <a href="project.html#data">Data sources</a>
        <a href="${REPO_URL}">Source code</a>
      </div>
    </div>`;
  document.body.append(footer);
}

const cache = {};
export async function loadJSON(name) {
  if (!cache[name]) {
    cache[name] = fetch(`data/${name}.json`).then((r) => {
      if (!r.ok) throw new Error(`Could not load ${name}.json (${r.status})`);
      return r.json();
    });
  }
  return cache[name];
}

export async function loadAll() {
  const [products, ingredients, stats] = await Promise.all([
    loadJSON("products"), loadJSON("ingredients"), loadJSON("stats"),
  ]);
  return { products, ingredients, stats };
}

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

export const money = (v) => `$${Number(v) % 1 === 0 ? Number(v).toFixed(0) : Number(v).toFixed(2)}`;

export function stars(r) {
  if (r == null) return "";
  const full = Math.round(r);
  return `<span class="stars" aria-label="${r.toFixed(1)} out of 5">${"★".repeat(full)}${"☆".repeat(5 - full)}</span>`;
}

export const sephoraSearch = (p) =>
  `https://www.sephora.com/search?keyword=${encodeURIComponent(`${p.b} ${p.n}`)}`;

// Ingredient list with avoided families marked and matched actives in bold.
export function ingredientListHTML(p, ingredients, { avoid = [], highlight = [] } = {}) {
  const items = p.i.map((ix) => {
    const ing = ingredients[ix];
    const name = esc(ing.n);
    if (ing.f.some((f) => avoid.includes(f))) return `<mark title="${esc(ing.f.join(", "))}">${name}</mark>`;
    if (highlight.includes(ing.n)) return `<b>${name}</b>`;
    return name;
  });
  let html = items.join(", ");
  if (p.u) html += ` <span class="tag tag-warn">${p.u} unmatched</span>`;
  if (p.cp === "missing") html = "<em>No ingredient list in the source data.</em>";
  return html;
}
