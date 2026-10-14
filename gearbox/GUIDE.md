# Reading rasters the warper's way: a practical guide for deck.gl-raster

Draft, 15 October 2026.

This is for anyone building or extending a browser raster reader, with
deck.gl-raster as the worked example because its design is documented in
the open and its custom-projection work (#695) is under way now. It sits
beside [Gearbox](index.html), a single-file, no-build page that reads
tile servers, COGs and VRT mosaics in the browser under deck.gl-raster's
defaults and under a warper's, and counts what each view costs. Code
references are to deck.gl-raster at commit a8616fc.

The short version: deck.gl-raster already has nearly every part a warper
has. The differences are in a few defaults and in where the seams fall
between planning and rendering. Some of those are one-prop changes that do
not wait on deck.gl v10. One of them, a mosaic-level pyramid, is a new
capability that would change what a browser map can show. The hardest one,
where the mesh lives, is the one #695 is already circling.

## 1. One model, four layers

The [REMA explorer](https://mdsumner.github.io/rema-ovr/) work
([post](https://www.hypertidy.org/posts/2026-10-14_recipe-is-the-dataset/))
fell into four layers, each of which can change without the others:

| Layer | What it answers | In deck.gl-raster today |
|---|---|---|
| Storage | where the bytes are | `@developmentseed/geotiff`, Zarr stores, a tile server |
| Index | which files and blocks exist, at which levels | GeoTIFF IFDs; `TileMatrixSet`; `MosaicLayer`'s source list in Flatbush |
| Planning | for this view, which level, which files, which blocks | `RasterTileset2D` traversal and the LOD test |
| Rendering | arrays to pixels | `RasterLayer`, `MeshTextureLayer`, the GPU modules |

The unit that passes between them is a grid: a CRS, an extent and a size.
Every request in Gearbox is one: a 256 px screen tile in the display CRS.
GDAL, R, Python and a browser all understand that unit, which is why the
page can print a `gdalwarp` command for whatever is on screen.

deck.gl-raster's planning layer is fused to deck.gl's tile machinery: tile
selection runs over source tiles in Web Mercator common space, and the LOD
test uses ground metres at a latitude. Most of the work #695 lists is
unfusing that so planning can happen in another plane. The sections below
take the differences one at a time, cheapest first.

## 2. Level of detail: a factor and a footprint

**What deck.gl-raster does.** The coarsest level whose source pixel is no
larger than one device pixel
(`devicePixelsPerSourcePixel <= 1`, `raster-tile-traversal.ts`, documented in
`dev-docs/lod-and-pixel-matching.md`). Both sides are ground metres: the
level's metres per pixel against `40075016.686 * cos(lat) / 2^(zoom + 8)`.

**What a warper does.** gdalwarp's `-ovr AUTO` picks the overview whose
resolution is closest to the target's but not coarser, from a ratio
measured across the output window in source pixels (threshold 1.0,
`GDALWARP_OVERSAMPLING_THRESHOLD`), and uses that one level for the whole
output. Plain RasterIO allows 1.2 for nearest
neighbour. The REMA explorer uses 1.5 CSS pixels. None of them knows about
device pixels.

**What Gearbox shows.** Measuring per screen tile from its footprint in the
source CRS, the threshold alone moves whole levels. From
`test/results-2026-10-15.txt`:

- A single EPSG:3031 COG on a Web Mercator map at a 2x pixel ratio:
  deck.gl-raster's rule, 27 requests and 14.4 MB; the recipe rule, 9
  requests and 4.1 MB, for the same picture at the same CSS size.
- An XYZ pyramid drawn on EPSG:3031 at 1x: z3 and 32 requests against z2 and
  8 requests.

The device-pixel rule is defensible (#64 made it deliberately), but it is a
policy, and it costs four times the bytes for one level on every HiDPI
screen. Users should be able to choose.

**Pathway, easy.** A prop on `RasterTileLayer` that scales the criterion:
`lodScale` (or `pixelRatio` override) with today's behaviour as default.
It is a single multiplication in the traversal and touches nothing else.

**Pathway, medium: adopt option (D).** The LOD notes already sketch it:
measure the tile's footprint on screen rather than ground metres at a
latitude. Gearbox does exactly this, in the source CRS rather than in
screen space, from the same lattice it uses to warp. It removes gaps (B)
and (C) in the notes, it is the measure the #694 prototype had to invent
for custom projections, and it is the same in Mercator, globe and any
custom view. Doing (D) once in the main traversal, rather than as a third
mode, means the custom-projection traversal in #695 is mostly culling and
domain, not a second LOD.

## 3. A pyramid for the mosaic, by reference

This is the largest difference and the one with no equivalent today.

**What deck.gl-raster does.** `MosaicLayer` opens each source in view as its
own COG and uses that file's internal overviews. Overviews stop at the file
edge. A continent of REMA tiles is 5800 files; at small scale every one of
them costs a header read before a pixel is drawn, which is why the NAIP
example sets `minZoom={4}`.

**What a VRT does.** A VRT can declare `<Overview>` entries that cover the
whole mosaic. `REMA-2m_dem_ovr.vrt` lists the 5800 2 m COGs, then points at
the provider's own 10 m and 32 m VRTs and three coarse COGs (100 m, 500 m, 1 km). The
fine data never moves; the only new payload is the cheap end of the pyramid,
and it can be added to data you do not own.

**What Gearbox shows.** With the real REMA VRT, the whole continent in the
recipe panel is 7 requests and 3.4 MB, from the 1 km overview. The
per-file panel refuses the same view: its screen tiles would each open
hundreds of files, and the page says how many (it will open them if asked,
to measure what that costs). Zooming in moves the recipe panel through the
finer overviews toward the 2 m mosaic, each level's files found through its
own index. The runs here reached only the coarse levels hosted alongside
the VRT; the 10 m, 32 m and 2 m files are on the provider's bucket, which
the REMA explorer already reads from a browser. The fixtures repeat this offline: a 4 x 4 mosaic in EPSG:3031 is refused under
per-file pyramids at 5.4 km per pixel and drawn from a 2 km overview with no
new requests under the recipe.

**Pathway, medium.** Let a tileset's levels be heterogeneous. Today a
`TilesetDescriptor` level is a tile matrix of one array. A mosaic level
could be any of:

- a single COG (with its own internal overviews as sub-levels);
- a list of sources with footprints (what `MosaicLayer` takes now);
- a tile matrix from a server.

Level choice runs first, by the same LOD rule; then the planner finds the
files at that level, then the image inside each file. That is three calls of
one function. In Gearbox it is `pickLevel` used three times in `buildTile`.

A VRT reader is the obvious first producer of such a descriptor, and it is
small: Gearbox parses `SRS`, `GeoTransform`, `SourceFilename`, `DstRect` and
`Overview` in about 80 lines, plus a bucket index over footprints. STAC
mosaics are the second producer: a collection of scenes plus a collection of
overview COGs is the same structure. Neither needs deck.gl v10.

**A note for #601 (best practices for data creators).** If you publish a
mosaic, publish its coarse levels as COGs and one VRT that lists the fine
files and points at the coarse ones. It costs a few megabytes and makes the
mosaic usable at every scale by GDAL, by R and Python, and by a browser that
honours the overviews.

## 4. Whose georeferencing an overview uses

**What deck.gl-raster does.** An overview's transform is the base transform
scaled by the size ratio (`Overview.transform` in `packages/geotiff`). That
is correct for internal overviews.

**What GDAL does.** The same: an overview is assumed to cover exactly the
base extent.

**Why it matters.** External overviews often do not. REMA's 1 km and 500 m
files start 900 m and 400 m outside the 2 m grid, and the 32 m VRT is offset
by up to 20 m, so GDAL misregisters those levels by up to about one of their
own pixels at the edges. The fixture overview is offset the same way.
Gearbox has a knob for it: "base extent (GDAL)" against "file's own".

**Pathway, easy, once section 3 exists.** A level that is its own file
carries its own transform. Use it.

## 5. Mesh error: you already match GDAL

deck.gl-raster's `maxError` default of 0.125 source pixels is gdalwarp's
`-et` default, in the same units. That is a good default when the level
read is close to the screen's resolution, which the LOD rule normally
guarantees.

It over-refines when the level is much finer than the screen. That happens
whenever the pyramid runs out at the coarse end: per-file pyramids zoomed
out past their smallest overview, or a polar view of a lon/lat grid. In the
fixture mosaic on Web Mercator at 61 km per pixel, the per-file panel made
1.45 million projection calls where the recipe panel, reading a 2 km
overview, made 26 thousand. Output-pixel error (the experimental
`_errorSpace: "output"` from #711) ties the cost to what is visible, but
over a polar lon/lat grid it can cost more than source pixels, because there
the source pixel is the larger one. The metric is a policy too.

**Pathway, small.** Keep source pixels as the default. Make output pixels
the default for custom projections when they land, since the polar
`columnErrorScale` stretch in #694 is a hand-made output-pixel metric.

## 6. Where the mesh lives

This is the hard one, and the one #695's "known limitations" all come back
to.

deck.gl-raster meshes in source space: a Delatin mesh over each source
tile's pixel grid, vertices projected into the map. Gearbox (and
ortho-cog-viewer on the GPU) work the other way: a lattice in the display
CRS, with source coordinates computed by the inverse transform. The
consequences:

- **The domain is per vertex, not per tile.** Where the inverse fails or
  leaves the source, the lattice cell is transformed per pixel and those
  pixels are simply empty. No `fromBounds` is needed. A pole-containing
  EPSG:3031 mosaic draws in Equal Earth, where the pole is a line, without
  folding (try `?src=rema&display=EPSG:8857`).
- **Poles are not holes.** A global lon/lat COG on a polar map draws all the
  way to the pole. The #694 example stops geographic grids half a degree
  short of each pole.
- **The antimeridian is a lattice cell like any other.** Cells whose corners
  span more than 180 degrees of longitude are transformed per pixel; no
  unwrapping.
- **The cost is a different traversal.** Screen tiles are display-grid tiles,
  so the tile index is not the source's. Fetching still happens in source
  blocks (Gearbox reads windows, geotiff.js reads blocks), but caching
  rendered results is keyed by display tile, and a projection change
  invalidates them.

**Pathway, hard but bounded.** Keep fetching by source tile, and change what
each source tile's mesh is built from: a lattice in the target plane over
the tile's footprint, clipped to the domain by the inverse, with UVs from
the inverse transform. That keeps `TileLayer`'s caching of fetched data and
replaces Delatin only for non-Mercator views. It is the same mesh
ortho-cog-viewer builds per frame. The domain handling the #694 README
calls approximate (rows that are not parallels, valid areas that are not
lon/lat boxes, pole-containing rasters in world projections) then falls out
of the inverse rather than being bookkept.

This is the one item that should wait for the v10 betas, as #695 says.

## 7. Tile servers in any CRS

Nothing to change in the architecture. `RasterTileLayer` with a
`TileMatrixSet` is already general, and the titiler `.npy` example shows the
data path. In Gearbox a tile server is a source whose levels are tile
matrices and whose blocks are URLs; NASA GIBS EPSG:3031 and EPSG:3413 WMTS
layers use the same planner as a COG.

**Pathway, easy.** An example that draws a GIBS polar WMTS layer through
`RasterTileLayer` in a custom projection once v10 lands. It is the cheapest
proof that the tile-matrix path generalises.

## 8. Count the bytes

Every number in this guide comes from Gearbox's per-panel ledger: a
geotiff.js custom client (`GeoTIFF.fromCustomClient`) that counts requests
and bytes, behind a six-per-host limiter like deck.gl-raster's
`DEFAULT_CONCURRENCY_LIMITER`. The log records each settled view.

**Pathway, easy, and the most useful for users.** A stats hook on the
concurrency limiter (requests, bytes, per layer), and an example that shows
it. It turns "this is fast" into "this view read 3.4 MB in 7 requests" and
it is the evidence #601 needs.

## Summary

| Change | Effort | Waits on v10 | Where | Unblocks |
|---|---|---|---|---|
| LOD scale prop | easy | no | `raster-tile-traversal.ts` | HiDPI bandwidth, matching GDAL |
| Request/byte stats hook | easy | no | concurrency limiter | cost on screen; #601 evidence |
| Overview uses its own transform | easy (after the next row) | no | level descriptors | external overviews, REMA-style |
| Heterogeneous levels; VRT and STAC producers | medium | no | `TilesetDescriptor`, `MosaicLayer` | continents and countries at small scale |
| LOD from footprint (option D) | medium | no | traversal | one LOD for Mercator, globe, custom |
| Output-pixel error as default for custom views | small | yes | `RasterReprojector` | polar views without `columnErrorScale` |
| Target-plane mesh per source tile | hard | yes | render branch of #695 | domains, poles, pole-containing rasters |
| GIBS polar WMTS custom-projection example | easy | yes | examples | proof for tile servers |

The first five do not need deck.gl v10 and would make the mainline better
for Web Mercator users today. They also make the custom-projection work
smaller when it starts: (D) removes a second LOD, heterogeneous levels give
it data worth looking at in polar views, and the stats hook measures it.

## Words that would help the docs

The vocabulary is close already. A table in the docs would let GDAL users
find their way in:

| deck.gl-raster | GDAL / warper |
|---|---|
| tileset level | overview level |
| `TileMatrixSet` of the source | the source's block layout and overviews |
| the view | the target grid (`-t_srs -te -ts`) |
| `MosaicLayer` | a VRT without `<Overview>` |
| `maxError` | `-et` (same default, same units) |
| LOD criterion | `-ovr AUTO` |

And two sentences that describe what the library already does: a raster is
read in its own CRS and drawn in the view's, and the display CRS is a
choice, not a property of the data.

## Running Gearbox

`?src=rema` opens the REMA VRT on EPSG:3031. Other presets: `gebco`, `eox`,
`nasa3031`, `s2` (COGs), `rema32` (a VRT with no overviews), `osm`, `esri`,
`gibs3031`, `gibs3413` (tile servers). `display=` takes `EPSG:3857`,
`EPSG:4326`, `EPSG:3031`, `EPSG:3413`, `EPSG:8857` or `source`. The panel
presets are "deck.gl-raster defaults", "recipe reader", "gdalwarp rules", and
every knob can be changed in place.
