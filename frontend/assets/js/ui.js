// Shared UI: icons, header/footer, API client, product visuals and cards.

// ----------------------------------------------------------------------- icons
const PATHS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  back: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
  chevron: '<path d="m9 6 6 6-6 6"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  alert: '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/>',
  drop: '<path d="M12 2.7c3.5 4 6 7.3 6 10.3a6 6 0 0 1-12 0c0-3 2.5-6.3 6-10.3Z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  leaf: '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/><path d="M2 21c0-3 1.9-5.4 5.2-6"/>',
  flask: '<path d="M9 3h6M10 3v6L4.5 18.5A2 2 0 0 0 6.2 21.5h11.6a2 2 0 0 0 1.7-3L14 9V3"/><path d="M7 15h10"/>',
  camera: '<path d="M14.5 4h-5L7.5 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3.5Z"/><circle cx="12" cy="13" r="3.5"/>',
  filter: '<path d="M3 5h18M6 12h12M10 19h4"/>',
  star: '<path d="m12 2.5 2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5L2.5 9.4l6.6-.9Z"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  external: '<path d="M14 4h6v6M20 4 10 14M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
  dot: '<circle cx="12" cy="12" r="4"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  wave: '<path d="M2 12c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/><path d="M2 17c2-3 4-3 6 0s4 3 6 0 4-3 6 0"/>',
  circle: '<circle cx="12" cy="12" r="8"/>',
  heart: '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 12 5.5 5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
};
export const icon = (name, cls = "") =>
  `<svg class="icon ${cls}" viewBox="0 0 24 24" aria-hidden="true">${PATHS[name] || PATHS.dot}</svg>`;

export const CONCERN_ICON = {
  acne: "target", oiliness: "drop", pores: "grid", dryness: "wave", redness: "heart",
  dark_spots: "circle", dullness: "sparkle", ageing: "layers", dark_circles: "moon", sun: "sun",
};
export const CONCERN_SHORT = {
  acne: "Breakouts", oiliness: "Oiliness", pores: "Visible pores", dryness: "Dryness",
  redness: "Redness", dark_spots: "Dark spots", dullness: "Dullness", ageing: "Fine lines",
  dark_circles: "Dark circles", sun: "Sun protection",
};
export const FAMILY_SHORT = {
  fragrance: "Fragrance", fragrance_allergens: "Fragrance allergens", essential_oils: "Essential oils",
  drying_alcohol: "Drying alcohol", sulfates: "Sulfates", parabens: "Parabens", silicones: "Silicones",
  comedogenic: "Pore-clogging", fungal_acne: "Fungal-acne triggers", pregnancy_caution: "Pregnancy caution",
  chemical_filters: "Chemical UV filters", strong_actives: "Strong actives",
};
const WARN_FAMILIES = new Set(["fragrance", "fragrance_allergens", "drying_alcohol", "essential_oils", "pregnancy_caution"]);
export const familyTag = (f) => `<span class="tag ${WARN_FAMILIES.has(f) ? "tag-amber" : "tag-line"}">${esc(FAMILY_SHORT[f] || f)}</span>`;

// ----------------------------------------------------------------------- helpers
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const money = (v) => `₹${Math.round(Number(v)).toLocaleString("en-IN")}`;
export const num = (v) => Number(v).toLocaleString("en-US");
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
export const retailerLink = (p) => p.url;
// Shopify CDN images accept a width parameter, so cards never download full-size photos.
export const sized = (src, w) => (src ? `${src}${src.includes("?") ? "&" : "?"}width=${w}` : "");
export const params = () => new URLSearchParams(location.search);

export function toast(text) {
  let el = $(".toast");
  if (!el) { el = document.createElement("div"); el.className = "toast"; document.body.append(el); }
  el.textContent = text;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 2600);
}

// ----------------------------------------------------------------------- API
export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : "Request failed");
    this.status = status;
    this.detail = detail;
  }
}
async function request(path, opts = {}) {
  const r = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => null);
  if (!r.ok) throw new ApiError(r.status, body?.detail ?? r.statusText);
  return body;
}
const qs = (o) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(o)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => p.append(k, x));
    else p.set(k, v);
  }
  const s = p.toString();
  return s ? `?${s}` : "";
};
let metaPromise;
export const api = {
  meta: () => (metaPromise ??= request("/meta")),
  products: (o) => request(`/products${qs(o)}`),
  product: (id) => request(`/products/${encodeURIComponent(id)}`),
  ingredients: (o) => request(`/ingredients${qs(o)}`),
  ingredient: (key) => request(`/ingredients/${encodeURIComponent(key)}`),
  recommend: (profile) => request("/recommend", { method: "POST", body: JSON.stringify(profile) }),
};

// ----------------------------------------------------------------------- product visual
// A stylised pack shot drawn from the product's category and brand: there are no product
// photos in the open dataset, so this keeps the catalogue visual without inventing images.
const TINTS = ["#efe3d6", "#e7ece3", "#ece3e8", "#e5e9ee", "#f1e7d9", "#e9e4dc", "#f0e0d8", "#e2e8e4"];
const PACKS = ["#c97f62", "#8a9e7f", "#b58aa0", "#7f97ad", "#d1a66b", "#a89585", "#c4806f", "#7fa092", "#d9b8a6", "#e9ddd0"];
function hash(s) { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; }

const SHAPES = {
  dropper: (c, cap) => `<rect x="38" y="6" width="24" height="38" rx="7" fill="${cap}"/><rect x="33" y="38" width="34" height="12" rx="3" fill="${cap}" opacity=".85"/><rect x="22" y="48" width="56" height="102" rx="16" fill="${c}"/>`,
  jar: (c, cap) => `<rect x="14" y="62" width="72" height="22" rx="7" fill="${cap}"/><rect x="10" y="80" width="80" height="62" rx="16" fill="${c}"/>`,
  pump: (c, cap) => `<rect x="44" y="8" width="12" height="20" rx="3" fill="${cap}"/><rect x="34" y="6" width="30" height="8" rx="4" fill="${cap}"/><rect x="38" y="26" width="24" height="14" rx="4" fill="${cap}"/><rect x="24" y="38" width="52" height="112" rx="18" fill="${c}"/>`,
  tube: (c, cap) => `<path d="M26 30h48l-4 106H30Z" fill="${c}"/><rect x="34" y="134" width="32" height="16" rx="4" fill="${cap}"/><rect x="26" y="26" width="48" height="8" rx="2" fill="${c}" opacity=".75"/>`,
  tall: (c, cap) => `<rect x="38" y="8" width="24" height="26" rx="6" fill="${cap}"/><rect x="26" y="32" width="48" height="118" rx="14" fill="${c}"/>`,
  small: (c, cap) => `<rect x="40" y="40" width="20" height="22" rx="5" fill="${cap}"/><rect x="34" y="60" width="32" height="88" rx="12" fill="${c}"/>`,
};
const CATEGORY_SHAPE = { Serum: "dropper", "Face oil": "dropper", Moisturiser: "jar", Mask: "jar", Cleanser: "pump",
  Sunscreen: "tube", "Eye care": "small", "Lip care": "small", Toner: "tall", Exfoliator: "tall", "Spot treatment": "small" };

export function productVisual(p, { badge = "", width = 480 } = {}) {
  if (p.image) {
    return `<div class="pvis pvis-photo">${badge ? `<div class="badge-corner">${badge}</div>` : ""}
      <img src="${esc(sized(p.image, width))}" alt="${esc(p.name)} by ${esc(p.brand)}" loading="lazy" decoding="async"
        onerror="this.closest('.pvis').classList.add('img-failed');this.remove()"></div>`;
  }
  return drawnVisual(p, badge);
}

// Fallback pack drawing for products without a photo.
function drawnVisual(p, badge) {
  const h = hash(p.brand + p.id);
  const tint = TINTS[h % TINTS.length];
  const pack = PACKS[(h >>> 3) % PACKS.length];
  const cap = "#2f2a26";
  const shape = SHAPES[CATEGORY_SHAPE[p.category] || "tall"](pack, cap);
  const light = pack === "#e9ddd0";
  const initials = esc(p.brand.replace(/[^A-Za-z0-9 ]/g, "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "•");
  const labelY = CATEGORY_SHAPE[p.category] === "jar" ? 116 : 104;
  return `<div class="pvis" style="--tint:${tint}">
    ${badge ? `<div class="badge-corner">${badge}</div>` : ""}
    <svg viewBox="0 0 100 156" role="img" aria-label="${esc(p.category)} by ${esc(p.brand)}">
      <ellipse cx="50" cy="152" rx="34" ry="4" fill="#000" opacity=".08"/>
      ${shape}
      <rect x="30" y="${labelY - 16}" width="40" height="30" rx="3" fill="#fff" opacity="${light ? ".7" : ".9"}"/>
      <text x="50" y="${labelY + 3}" text-anchor="middle" font-family="Inter, sans-serif" font-size="10" font-weight="700" fill="#2f2a26" letter-spacing=".5">${initials}</text>
      <rect x="40" y="${labelY + 7}" width="20" height="1.6" rx=".8" fill="#2f2a26" opacity=".35"/>
    </svg>
  </div>`;
}

export function stars(r) {
  if (r == null) return "";
  return `<span class="rating">${icon("star")}<b>${r.toFixed(1)}</b></span>`;
}

export const priceHTML = (p) =>
  `<span class="price">${money(p.price)}${p.mrp ? `<s>${money(p.mrp)}</s>` : ""}</span>${p.discount_pct ? `<span class="off">${p.discount_pct}% off</span>` : ""}`;

export function productCard(p, { extra = "" } = {}) {
  const badge = !p.in_stock ? `<span class="tag tag-ink">Out of stock</span>`
    : p.fragrance_free ? `<span class="tag tag-float">Fragrance-free</span>` : "";
  const actives = (p.key_actives || []).slice(0, 2).map((a) => a.ingredient).join(" · ");
  return `<a class="product-card" href="product.html?id=${encodeURIComponent(p.id)}">
    ${productVisual(p, { badge, width: 400 })}
    <div class="body">
      <span class="brand">${esc(p.brand)}</span>
      <h3>${esc(p.name)}</h3>
      ${actives ? `<span class="actives">${esc(actives)}</span>` : ""}
      ${extra}
      <div class="meta"><span class="row" style="gap:8px">${priceHTML(p)}</span>${p.size ? `<span class="xs subtle">${esc(p.size)}</span>` : ""}</div>
    </div>
  </a>`;
}

// Where to buy: the exact page on the brand's store, plus searches on the big marketplaces.
export function shopLinks(p, { compact = false } = {}) {
  const links = p.shop_links || [];
  const official = links.find((l) => l.exact);
  const others = links.filter((l) => !l.exact);
  return `<div class="shop">
    ${official ? `<a class="btn btn-primary${compact ? " btn-sm" : ""}" href="${esc(official.url)}" target="_blank" rel="noopener">Buy on ${esc(p.brand)} · ${money(p.price)} ${icon("external")}</a>` : ""}
    ${others.length ? `<div class="compare"><span class="xs subtle">Compare on</span>${others.map((l) =>
      `<a class="store-chip" href="${esc(l.url)}" target="_blank" rel="noopener" title="Search ${esc(l.label)} for this product">${esc(l.label)}</a>`).join("")}</div>` : ""}
  </div>`;
}

export const skeletonCards = (n = 8) => Array.from({ length: n }, () => `<div class="skeleton" style="height:360px"></div>`).join("");

// ----------------------------------------------------------------------- chrome
const NAV = [["analyze.html", "Skin analysis"], ["products.html", "Products"], ["ingredients.html", "Ingredients"]];
const LOGO = `<svg class="logo-mark" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#1d1916"/><path d="M16 7c4 4.6 6.5 8.2 6.5 11.4a6.5 6.5 0 0 1-13 0C9.5 15.2 12 11.6 16 7Z" fill="#e9b9a2"/><path d="M13.2 18.6a2.9 2.9 0 0 0 2.8 2.9" stroke="#1d1916" stroke-width="1.6" fill="none" stroke-linecap="round"/></svg>`;

export function mountChrome() {
  const here = location.pathname.split("/").pop() || "index.html";
  const active = (href) => href === here || (here === "product.html" && href === "products.html") || (here === "ingredient.html" && href === "ingredients.html");
  const header = document.createElement("header");
  header.className = "site-header";
  header.innerHTML = `<div class="container">
      <a class="logo" href="index.html">${LOGO}SkinAnalyzer</a>
      <nav class="nav" id="site-nav">${NAV.map(([h, l]) => `<a href="${h}"${active(h) ? ' aria-current="page"' : ""}>${l}</a>`).join("")}</nav>
      <div class="header-actions">
        <a class="btn btn-primary btn-sm" href="analyze.html">Start your analysis</a>
        <button class="btn btn-ghost btn-icon menu-toggle" aria-label="Menu" aria-expanded="false" aria-controls="site-nav">${icon("menu")}</button>
      </div></div>`;
  document.body.prepend(header);
  const toggle = header.querySelector(".menu-toggle");
  toggle.addEventListener("click", () => toggle.setAttribute("aria-expanded", String(header.querySelector(".nav").classList.toggle("open"))));
  const onScroll = () => header.classList.toggle("scrolled", scrollY > 8);
  addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const footer = document.createElement("footer");
  footer.className = "site-footer";
  footer.innerHTML = `<div class="container">
    <div class="footer-grid">
      <div class="stack" style="--gap:16px">
        <a class="logo" href="index.html">${LOGO}SkinAnalyzer</a>
        <p class="small" style="max-width:340px">Ingredient-aware skincare recommendations that respect your skin, your budget and the ingredients you avoid.</p>
      </div>
      <div><h4>Explore</h4><ul>
        <li><a href="analyze.html">Skin analysis</a></li><li><a href="products.html">Products</a></li><li><a href="ingredients.html">Ingredient dictionary</a></li></ul></div>
      <div><h4>Shop by concern</h4><ul>
        <li><a href="products.html?concern=acne">Breakouts</a></li><li><a href="products.html?concern=dark_spots">Dark spots</a></li>
        <li><a href="products.html?concern=dryness">Dryness</a></li><li><a href="products.html?concern=sun">Sun protection</a></li></ul></div>
      <div><h4>Information</h4><ul>
        <li><a href="index.html#how">How it works</a></li><li><a href="index.html#faq">FAQ</a></li>
        <li><a href="index.html#data">Data sources</a></li><li><a href="/api/docs">Developer API</a></li></ul></div>
    </div>
    <div class="footer-bottom">
      <span>© ${new Date().getFullYear()} SkinAnalyzer. Guidance only, not a medical diagnosis.</span>
      <span>Prices and products from brands' official Indian stores · Ingredient data: EU CosIng, CureSkin (CC BY 4.0)</span>
    </div></div>`;
  document.body.append(footer);
  hydrateIcons();
}

// Replace <span data-icon="name"></span> placeholders written in static HTML.
export function hydrateIcons(root = document) {
  $$("[data-icon]", root).forEach((el) => { el.outerHTML = icon(el.dataset.icon); });
}

export function revealOnScroll() {
  const io = new IntersectionObserver((entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -8% 0px" });
  $$(".reveal").forEach((el) => io.observe(el));
}

export function errorState(err) {
  return `<div class="card empty"><div class="icon-badge">${icon("alert")}</div><h3>Something went wrong</h3><p class="muted small" style="margin-top:6px">${esc(err.message || err)}. Please refresh the page.</p></div>`;
}
