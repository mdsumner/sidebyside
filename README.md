# sidebyside

Illustration-only comparisons of browser-native raster/grid viewers:
the hypertidy/mdsumner set (ortho-cog-viewer, rangefinder, rwarp wasm)
on the left, [d70-t/gridlook](https://github.com/d70-t/gridlook) on the right.

Each page is one dataset, two viewers, one named gap, one proposed bridge.
There is no UI beyond that. The point is to show exactly where a gap can
be filled or a bridge built, not to be usable as a viewer.

Live site: https://mdsumner.github.io/sidebyside/ (once Pages is enabled,
see Deploying below).

## Pages

| # | Page | Dataset | Who is behind | Gap | Bridge |
|---|------|---------|---------------|-----|--------|
| 01 | healpix | DKRZ d3hp003 HEALPix z7 (Zarr); trend.sst S2 cells as a second source | ours | DGGS on our analysis side (trend.sst) and on their rendering side, never both | a (cell id, value) renderer with a cell-to-vertices function per DGGS; delaunay of HEALPix centres first |
| 02 | cog | Sentinel-2 L2A COG, tile 55GEN | theirs | gridlook reads GeoTIFF only as a WGS84 overlay texture, not as data | virtual Zarr/Icechunk view over the COG from `gdal mdim get-refs` / blocklist |
| 03 | big-array | GHRSST MUR 0.01 deg SST as Zarr, no hierarchy | theirs | whole-field reads at one dimension index; no spatial windowing | publish coarser siblings (LOD as a data product) the way DKRZ publishes z-levels, produced by grout |
| 04 | polar | GIBS EPSG:3031 / LIST WMTS tiles on polar stereo | theirs | no tile-service ingestion; projections limited to d3-geo | shared tile-source module; `crsDefinition` as a common CRS authority |
| 05 | curvilinear | BRAN / NEMO tripolar slice with 2D lon/lat | ours | no geolocation-array (2D lon/lat) path in the warp renderers | anglr-style cell mesh from geoloc arrays as a third pluggable renderer |
| 06 | icechunk | an Icechunk store (ACCESS-NRI) | ours | no Icechunk reader in our layer-3 reads | lift icechunk-js into the shared reads module |
| 07 | projections | the same global field in both | draw | d3-geo list vs proj4js + proj-wasm (interrupted Goode, tpers, omerc) | proj-wasm as a shared resolver on an unknown-code miss |

Pages 01, 05 and 06 are where we are behind; 02, 03 and 04 are where
gridlook is; 07 is a draw with different vocabularies. Keep it balanced.

## How a page works

```
pages/
  01-healpix/
    index.html   <- identical shim in every page, loads ../../sbs.js
    page.json    <- all the content
```

`page.json`:

```json
{
  "title": "HEALPix on both",
  "status": "ours-gap",
  "dataset": { "name": "...", "url": "https://...", "cors": true },
  "left":  { "label": "ours (ortho-cog-viewer)", "url": null, "note": "why there is nothing to show" },
  "right": { "label": "gridlook", "url": "{GRIDLOOK}#https://..." },
  "gap": "one sentence",
  "bridge": "one sentence",
  "todo": ["anything still to stage or confirm"]
}
```

`status` is one of `ours-gap`, `theirs-gap`, `draw`. A `url` of `null`
renders an empty panel with the `note`, which is the honest way to show
a gap. `{GRIDLOOK}` is replaced with the gridlook base from `config.json`:
the vendored build on the deployed site, `https://gridlook.pages.dev/`
when running locally without one. A side may set `"gridlook": "hosted"`
to force `gridlook.pages.dev` instead of the pinned build; this is for
datasets whose bucket CORS allow-lists that origin specifically (DKRZ
does). Data we host ourselves gets `*` and stays on the pin.

To add a page: copy a directory, edit `page.json`, add the slug to
`pages/index.json`.

## Vendored gridlook and tracking its development

gridlook is MIT, Vite-built with a relative base path, so the Pages
workflow checks out `d70-t/gridlook` at the tag in `gridlook.pin`, builds
it with Node 24, and serves it at `/sidebyside/gridlook/`. The pin is the
tracking mechanism:

- `.github/workflows/bump-gridlook.yml` runs weekly, compares the latest
  gridlook release tag with `gridlook.pin`, and opens a PR when they differ.
- Merging the PR rebuilds the site. A page that stops loading after a bump
  is the signal that a contract on their side moved.

Iframing `gridlook.pages.dev` directly is the fallback, not the plan: a
pinned local build means the comparison is reproducible and a diff of the
pin is a diff of what changed.

## Deploying

1. Repo settings, Pages, Source: GitHub Actions.
2. Push to `main`. `pages.yml` builds gridlook, assembles `_site/`, deploys.

## Data

Every panel loads straight from a CORS-enabled URL. Known-good hosts:
DKRZ (`s3.eu-dkrz-1.dkrz.cloud`), `sentinel-cogs.s3.us-west-2.amazonaws.com`.
Pawsey is not reachable from a browser; anything we stage for pages 03,
05 or 06 goes to source.coop or another open bucket. Each page lists what
is still to be staged under `todo`.

## Local preview

Any static server from the repo root, e.g. `python3 -m http.server 8000`,
then open `http://localhost:8000/`. Without a vendored build the right
panels point at `gridlook.pages.dev`.
