// Renders one comparison page from ./page.json, or the index from pages/index.json.
// No build step, no dependencies. ASCII only.

const ROOT = new URL("./", document.currentScript.src);

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(url + " " + r.status);
  return r.json();
}

async function config() {
  try {
    const cfg = await getJSON(new URL("config.json", ROOT));
    cfg.gridlookBase = new URL(cfg.gridlookBase, ROOT).href;
    return cfg;
  } catch (e) {
    return { gridlookBase: "https://gridlook.pages.dev/", pinned: null };
  }
}

function el(tag, attrs, children) {
  const n = document.createElement(tag);
  for (const k in attrs || {}) {
    if (k === "text") n.textContent = attrs[k];
    else n.setAttribute(k, attrs[k]);
  }
  for (const c of children || []) n.appendChild(c);
  return n;
}

const HOSTED = "https://gridlook.pages.dev/";

// Columns are stances, not owners. warp: the image is the primitive (raster +
// CRS + geotransform, warped to the view). cell: the grid is the primitive
// (cells placed on the sphere, no warp step).
function badgeText(status) {
  return { "warp-gap": "gap: warp side", "cell-gap": "gap: cell side", "shared": "shared" }[status] || status;
}

// side.gridlook: "vendored" (default, the pinned build on this site) or
// "hosted" (gridlook.pages.dev, for data whose CORS allow-list names that origin).
function resolve(side, cfg) {
  if (!side.url) return null;
  const base = side.gridlook === "hosted" ? HOSTED : cfg.gridlookBase;
  return side.url.replace("{GRIDLOOK}", base);
}

function panel(side, cfg) {
  const url = resolve(side, cfg);
  let text = side.label;
  if (url && side.url.indexOf("{GRIDLOOK}") !== -1) {
    text += side.gridlook === "hosted" ? " [gridlook.pages.dev]" : " [pinned build]";
  }
  const label = el("div", { class: "label", title: url || "" }, [
    document.createTextNode(text + (url ? "  " : "")),
  ]);
  if (url) label.appendChild(el("a", { href: url, target: "_blank", text: "open" }));
  const body = url
    ? el("iframe", { src: url, loading: "lazy", allow: "fullscreen" })
    : el("div", { class: "empty", text: side.note || "nothing to show" });
  return el("div", { class: "panel" }, [label, body]);
}

async function renderPage() {
  const cfg = await config();
  const p = await getJSON(new URL("page.json", location.href));
  document.title = p.title + " - sidebyside";
  const main = document.getElementById("sbs");

  const head = el("header", {}, [
    el("div", { class: "crumb" }, [
      el("a", { href: ROOT.href, text: "sidebyside" }),
      document.createTextNode(" / " + location.pathname.split("/").filter(Boolean).slice(-1)[0]),
    ]),
    el("h1", {}, [
      document.createTextNode(p.title),
      el("span", { class: "badge " + p.status, text: badgeText(p.status) }),
    ]),
  ]);

  const lines = el("div", { class: "lines" });
  const ds = el("p", {}, [el("b", { text: "dataset" })]);
  if (p.dataset.url) {
    ds.appendChild(el("a", { href: p.dataset.url, target: "_blank", text: p.dataset.name }));
  } else {
    ds.appendChild(document.createTextNode(p.dataset.name));
  }
  if (p.dataset.cors === false) ds.appendChild(document.createTextNode("  (no CORS yet)"));
  lines.appendChild(ds);
  lines.appendChild(el("p", {}, [el("b", { text: "gap" }), document.createTextNode(p.gap)]));
  lines.appendChild(el("p", {}, [el("b", { text: "bridge" }), document.createTextNode(p.bridge)]));

  const panels = el("div", { class: "panels" }, [panel(p.left, cfg), panel(p.right, cfg)]);

  main.appendChild(head);
  main.appendChild(lines);
  main.appendChild(panels);

  if (p.todo && p.todo.length) {
    const ul = el("ul", {}, p.todo.map((t) => el("li", { text: t })));
    main.appendChild(el("div", { class: "todo" }, [el("b", { text: "todo" }), ul]));
  }
  if (cfg.pinned) {
    main.appendChild(el("div", { class: "todo", text: "gridlook pinned at " + cfg.pinned }));
  }
}

async function renderIndex() {
  const cfg = await config();
  const slugs = await getJSON(new URL("pages/index.json", ROOT));
  const pages = await Promise.all(
    slugs.map((s) => getJSON(new URL("pages/" + s + "/page.json", ROOT)).then((p) => ({ slug: s, p })))
  );
  const rows = pages.map(({ slug, p }) =>
    el("tr", {}, [
      el("td", {}, [el("a", { href: "pages/" + slug + "/", text: slug })]),
      el("td", { text: p.dataset.name }),
      el("td", {}, [el("span", { class: "badge " + p.status, text: badgeText(p.status) })]),
      el("td", { text: p.gap }),
      el("td", { text: p.bridge }),
    ])
  );
  const table = el("table", {}, [
    el("thead", {}, [
      el("tr", {}, ["page", "dataset", "gap on", "gap", "bridge"].map((t) => el("th", { text: t }))),
    ]),
    el("tbody", {}, rows),
  ]);
  const main = document.getElementById("sbs");
  main.appendChild(table);
  const foot = el("p", { class: "todo" });
  foot.textContent = cfg.pinned
    ? "gridlook vendored at " + cfg.pinned
    : "gridlook panels point at gridlook.pages.dev (no vendored build in this preview)";
  main.appendChild(foot);
}

if (document.body.dataset.sbs === "index") renderIndex();
else renderPage();
