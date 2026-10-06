# The input data layer, seen from allonboard

Draft for the allboa org (allonboard, working name). October 2026.
Written to go with two pointers: hypertidy/rangefinder, which holds the
readers, and mdsumner/sidebyside, which characterises the cloud formats
by what it costs to draw them.

## 1. The claim

allonboard is a render layer. Its stance is explicit geometry: vectors
arrive as GeoArrow and are drawn as they are. That is the right thing to
build and the thing nothing else in R does well.

Everything that is not explicit geometry (rasters, tiles, Zarr and
Icechunk arrays, model grids, discrete global grids) should arrive at
allonboard the same way it arrives at rangefinder: as a catalogue entry
that names a footprint, a time axis and a read recipe, with the bytes
fetched in the browser from wherever they live. allonboard should not
write those readers. They exist, they are small, and they are the part
of rangefinder that was designed to be lifted out.

So the input data layer, from allonboard's side, is: a recipe comes in,
a drawable comes out, and R's job is to produce recipes.

## 2. What rangefinder already has

rangefinder's design (docs/design.md there) splits the job into four
layers: 1 space (what names a footprint), 2 time (what lists the days),
3 pixels (how bytes become arrays), 4 render. Layers 1 to 3 are
interfaces; the UI never knows which binding is behind them. The
bindings, as of 6 Oct 2026, all plain ES modules with lazy CDN imports
and no build step:

    lib/sources/cog.js         76   files named directly (one or more COG URLs)
    lib/sources/tiles.js      109   XYZ templates, WMTS GetCapabilities
    lib/sources/vrt.js        208   a GDAL VRT mosaic as a catalogue
    lib/sources/wildtiles.js  230   the per-tile Sentinel cube contract
    lib/sources/stac.js       264   a live STAC API (earth-search etc.)
    lib/sources/starc.js      439   a published starc reference store
    lib/sources/zarr.js      1342   Zarr v2/v3, Kerchunk JSON and Parquet refs,
                                    Icechunk (icechunk-js), CF grids
    lib/dggs.js               442   HEALPix: view pixels to cell ids, inverse sampling
    lib/curvilinear.js        272   2D lon/lat grids: corners, footprints, rasterise
    lib/cog.js                387   layer 3: windowed COG reads warped to an output grid
    lib/tiles.js              395   layer 3: tile fetch and warp
    lib/chunks.js             106   one cache for every source's native pieces
    lib/geo.js                350   CRS, footprints, the output grid (proj4 from the page)

Every layer-3 read has the same shape: given an asset and an OutputGrid
(CRS, extent, size), return a typed array in that grid. That one
function signature is the input layer. A render layer that can take a
typed array plus an OutputGrid as a texture or a sampled raster can draw
anything the sources know how to read.

Lifting these into a package (say @hypertidy/sources, or a subpath of
rangefinder's own npm publish) is mostly moving files; they already
import nothing from the UI.

## 3. What R produces

R does not render and does not fetch pixels. R produces the recipe,
which is small, from objects the user already has:

- a URL (or a list of them, or a STAC query, or a starc store id)
- a CRS and, for rasters, a tile scheme or extent (vaster, grout)
- a variable name, a time selection, an Icechunk snapshot id
- for vectors, the GeoArrow buffer itself (the one payload in the system)
- for cells, a scheme name and level and a column of ids (S2 from
  trend.sst, HEALPix from a Zarr store)

sds (DSN helpers), starc (STAC reference cache), grout and vaster (tile
schemes) and gdalraster (what the data actually is) are the R side of
this. None of them needs to know about allonboard; they produce
descriptions, and allonboard's R package turns a description into a
layer spec the browser understands.

The asymmetry is the design. For vectors the recipe is a payload, but a
bounded one that the user chose to send. For rasters and grids the
recipe is a few hundred bytes and the payload never leaves the bucket.
That is what makes R relevant to a browser viewer without R doing any
of the drawing, and it is what keeps the R package thin.

## 4. Three primitives, one shell

The stances from sidebyside's article, as they land in allonboard:

- arrow (explicit geometry): allonboard's own layers, GeoArrow in,
  drawn as given. Native.
- warp (image is the primitive): a source read through rangefinder's
  layer 3 into an OutputGrid, handed to allonboard as a texture draped
  on the view's mesh, or as a sampled raster layer. This is where COGs,
  tiles, Zarr arrays, Icechunk repos and curvilinear model grids arrive.
- cell (grid is the primitive): a column of cell ids plus a scheme.
  deck.gl already has S2Layer and H3HexagonLayer that take ids and
  expand them client-side; a HEALPix layer would be the same shape.
  rangefinder's v.dggs object (cellsOf, cornersOf, a detector from
  attributes) is the interface, and a lib-level DGGS abstraction across
  schemes is the piece still to build.

allonboard does not need to choose among these. It needs a layer type
for each, and the input layer delivers each as a recipe.

## 5. What sidebyside contributes

sidebyside is the menu with prices. For each cloud format it shows which
stance the format naturally lands in, which readers exist on each side,
and where a gap is a consequence of the stance versus just a reader not
yet written. Read as a program document for allonboard it says:

- COG, tiles, big single arrays: warp, readers exist, cheap.
- Icechunk, plain Zarr, Kerchunk refs: warp, readers exist, cheap;
  Icechunk brings snapshot pinning, which the recipe should carry.
- curvilinear model grids: warp via cell rasterisation, exists.
- HEALPix: cell, or warp via inverse sampling; both exist as of this
  week. Other DGGS (S2, H3): the abstraction is the open work.
- projected and polar CRSs: warp side only; the recipe must carry a CRS
  the browser can resolve (proj4js now, proj-wasm as the fallback).

## 6. Open questions for the render side

These depend on allonboard's choices, which is why this document waits
on Tim's reply:

- deck.gl views and non-Mercator CRSs: can the warp primitive be drawn
  in a polar or oblique view without fighting the framework, or does the
  warp side need its own WebGL context alongside deck.gl (as
  ortho-cog-viewer has)?
- texture versus sampled raster: does allonboard want layer-3 output as
  an image (drape, cheap, un-auditable) or as values (materialised,
  pickable, exportable)? rangefinder does both; the answer decides the
  interface.
- cells: id columns straight from Arrow into an S2/H3/HEALPix layer is
  the cleanest path and keeps the cell stance inside the arrow transport.
  Worth deciding whether that is the only cell path or whether
  rangefinder's inverse-sampling route is wanted too.

## 7. Suggested first step

One allonboard layer that takes a rangefinder catalogue entry (a plain
JSON object: source kind, URL, variable, CRS) and draws it as a draped
texture in the current view. Everything in sections 2 to 5 is then a
matter of adding entries to the catalogue, not code to allonboard.
