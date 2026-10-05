# sidebyside

Illustration-only comparisons of two stances on browser-native raster
and grid viewing. The columns are stances, not owners:

- **warp**: the image is the primitive. A raster with a CRS and a
  geotransform, warped to the view. ortho-cog-viewer, rangefinder, the
  rwarp wasm slippy map (hypertidy / mdsumner).
- **cell**: the grid is the primitive. Cells placed on the sphere, no
  warp step. [d70-t/gridlook](https://github.com/d70-t/gridlook) (DKRZ).

Each page is one dataset, both stances, one named gap, one proposed
bridge. There is no UI beyond that. The point is to show exactly where a
gap can be filled or a bridge built, not to be usable as a viewer. Most
gaps are consequences of the stance (no COG, no windowing, no tile
services follow from grid-first; no DGGS cells, no geolocation arrays
follow from image-first). The ones that are not, like a missing reader,
stand out for that reason.

Live site: https://mdsumner.github.io/sidebyside/ (once Pages is enabled,
see Deploying below).

## Article

`article/README.md`: warp and cell, two worlds that were never separate.
The short explainer the pages are evidence for.

## Pages

| # | Page | Dataset | Gap on | Gap | Bridge |
|---|------|---------|---------------|-----|--------|
| 01 | healpix | DKRZ EERIE HEALPix level 7 (Zarr); trend.sst S2 cells as a second source | warp | DGGS on the warp analysis side (trend.sst) and the cell rendering side, never both | invert the view: pixel centres to cell ids via healpix-geo, then index the chunk (docs/rangefinder-healpix.md) |
| 02 | cog | Sentinel-2 L2A COG, tile 55GEN | cell | gridlook reads GeoTIFF only as a WGS84 overlay texture, not as data | virtual Zarr/Icechunk view over the COG from `gdal mdim get-refs` / blocklist |
| 03 | big-array | GHRSST MUR 0.01 deg SST as Zarr, no hierarchy | cell | whole-field reads at one dimension index; no spatial windowing | publish coarser siblings (LOD as a data product) the way DKRZ publishes z-levels, produced by grout |
| 04 | polar | GIBS EPSG:3031 / LIST WMTS tiles on polar stereo | cell | no tile-service ingestion; projections limited to d3-geo | shared tile-source module; `crsDefinition` as a common CRS authority |
| 05 | curvilinear | CMIP6 GFDL-ESM4 tos, tripolar with 2D lon/lat (BRAN later) | shared | both draw it: cells on the sphere vs cells rasterised then warped; ortho-cog-viewer/rwarp cannot | lift rangefinder's curvilinear.js into the shared reads module |
| 06 | icechunk | an Icechunk store (ACCESS-NRI) | warp | no Icechunk reader on the warp side | icechunk-js as a fourth store kind in rangefinder; plan in docs/rangefinder-icechunk.md |
| 07 | projections | Blue Marble vs CMIP6 HadGEM3 tas | shared | d3-geo list vs proj4js + proj-wasm (interrupted Goode, tpers, omerc) | proj-wasm as a shared resolver on an unknown-code miss |

Pages 01 and 06 are gaps on the warp side; 02, 03 and 04 are gaps on
the cell side; 05 and 07 are shared ground reached by different routes.
Keep it balanced. Plans for closing a gap live in docs/.

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
  "status": "warp-gap",
  "dataset": { "name": "...", "url": "https://...", "cors": true },
  "left":  { "label": "warp: ortho-cog-viewer", "url": null, "note": "why there is nothing to show" },
  "right": { "label": "cell: gridlook", "url": "{GRIDLOOK}#https://..." },
  "gap": "one sentence",
  "bridge": "one sentence",
  "todo": ["anything still to stage or confirm"]
}
```

`status` is one of `warp-gap`, `cell-gap`, `shared`. A `url` of `null`
renders an empty panel with the `note`, which is the honest way to show
a gap. `{GRIDLOOK}` is replaced with the gridlook base from `config.json`:
the vendored build on the deployed site, `https://gridlook.pages.dev/`
when running locally without one. A side may set `"gridlook": "hosted"`
to force `gridlook.pages.dev` instead of the pinned build, for a dataset
not yet confirmed to load from this site's origin. Data staged for this
suite gets `*` and stays on the pin. gridlook's own shipped catalog
(`public/static/catalog.json` in their repo) is the reliable source of
known-good dataset URLs; the hackathon path in their README is dead.

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
