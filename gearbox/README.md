# Gearbox

One raster reader, two sets of defaults.

Gearbox is a single HTML file with no build step. It reads three kinds of
source in the browser, with no server in between:

- **tile servers**: XYZ in Web Mercator, and WMTS tile matrices in other CRSs
  (NASA GIBS polar layers);
- **COGs**: any Cloud-Optimized GeoTIFF with an EPSG code and CORS;
- **VRT mosaics**: GDAL VRT files that list COGs by URL, including
  `<Overview>` entries that add a whole-mosaic pyramid by reference.

It draws the same view twice, side by side. Both panels run the same code.
They differ only in policy: the left panel uses deck.gl-raster's defaults,
the right panel uses the rules of a recipe reader (the REMA explorer's
policy), and a third preset copies gdalwarp. Every request and byte is
counted per panel, and each settled view adds a row to the log, so the
difference between policies is measured rather than claimed.

The left panel is an emulation of deck.gl-raster's defaults inside this
reader. It is not deck.gl, and it does not run deck.gl-raster code.

## Run it

Open `index.html` from any static host (GitHub Pages works). Locally:

```sh
python3 -m http.server 8000
# then open http://localhost:8000/?src=rema
```

Query parameters:

- `src`: a preset id (`rema`, `rema32`, `gebco`, `eox`, `nasa3031`, `s2`,
  `osm`, `esri`, `gibs3031`, `gibs3413`) or a URL. A URL containing `{z}` is
  a tile template, one ending `.vrt` is a VRT, anything else is a COG. A tile
  template can carry its zoom range: `.../{z}/{x}/{y}.png#maxz=12`.
- `display`: `EPSG:3857`, `EPSG:4326`, `EPSG:3031`, `EPSG:3413`,
  `EPSG:8857`, `source`, any other EPSG code, or a PROJ string such as
  `+proj=laea +lat_0=-90 +lon_0=140 +datum=WGS84` (URL-encoded). The display
  menu takes the same through "PROJ string or EPSG code...".

Sources need CORS. The REMA levels at 2 m, 10 m and 32 m live on the data
provider's bucket, the coarse levels in Git LFS beside the VRT.

## The pipeline

A screen tile is a 256 x 256 grid in the display CRS. For each one:

1. **Map** the grid into the source CRS on a 17 x 17 lattice of exact
   transforms (display to lon/lat to source, with a round-trip check).
2. **Measure** the size of a screen pixel in source units from the lattice:
   the tile's footprint, not a ground-metres formula.
3. **Pick a level**: the coarsest whose pixel is no larger than
   `factor x pixel`, by the panel's policy.
4. **Find the files**: a tile index for tile servers, the internal images for
   a COG, the VRT's source list (bucket-indexed) for a mosaic level.
5. **Read only the window** each file needs, then pick an image inside each
   file by the same rule.
6. **Sample** into the tile. Lattice cells whose interpolation error exceeds
   0.125 pixels are transformed per pixel, so domain edges, poles and the
   antimeridian are exact.

Tiles hold values; colour is applied at draw time. Hover shows the value and
the level that answered in both panels.

## The policy knobs

| Knob | deck.gl-raster defaults | recipe reader | gdalwarp rules |
|---|---|---|---|
| level: source px <= | 1 device px | 1.5 CSS px | 1 CSS px |
| mosaic pyramid | per-file (MosaicLayer) | VRT overviews | VRT overviews |
| overview extent | n/a | each file's own | base extent |
| mesh error measured in | source px | output px | source px |

All three load from the centre outwards with six concurrent requests per
host.

"gdalwarp rules" copies gdalwarp's choices, not its process. gdalwarp picks
one overview for the whole output from the ratio across the window,
approximates the transform along scanlines, and resamples nearest by
default. Gearbox picks a level per screen tile, approximates on a lattice,
and uses bilinear when upsampling, for every preset.

## What is on screen

- **machinery**: each screen tile's outline and a label: the level that
  answered, how many files and blocks it read, and how many lattice cells
  needed exact transforms.
- **file footprints**: the VRT's source files, in the display CRS.
- **View log**: per settled view and panel, the levels drawn (with tile
  counts), new headers opened, requests, bytes, time to settle, and
  projection calls.
- **This view as a recipe**: a `gdalwarp` command for the same grid.

## Tests

`test/` builds small fixtures (COGs, a 4 x 4 VRT mosaic with an offset
external overview, a global RGB COG, an XYZ pyramid), serves them with a
range-capable server, and drives the page headless with Playwright.
`test/results-2026-10-15.txt` holds one run at device pixel ratios 1 and 2.

```sh
python3 test/make_fixtures.py /tmp/fx
mkdir -p /tmp/site && cp index.html /tmp/site/ && ln -s /tmp/fx /tmp/site/fx
python3 test/serve.py /tmp/site 8765 &
python3 test/drive.py http://127.0.0.1:8765/index.html /tmp/shots \
  "src=http://127.0.0.1:8765/fx/mosaic.vrt&display=EPSG:3031"
```

`drive.py` routes the CDN scripts to local npm copies; edit `LIB` at its
top.

## Limits

- Top-down, no rotation. One band (coloured) or 8-bit RGB(A).
- The VRT reader uses each source file's own georeferencing and the
  `DstRect` only as a footprint. It ignores `SrcRect` scaling, per-source
  nodata and band mapping beyond the first band or the first three.
- CRS definitions are built in for common codes and fetched from epsg.io for
  others; proj4js does the transforms. So a display CRS can be any PROJ
  string in a family proj4js implements (stere, laea, aeqd, ortho, eqearth,
  merc, tmerc/utm, lcc, aea, cea, eqc, moll, robin, sinu, omerc and a few
  more), with no datum grids and no pipelines. Its drawable area is found by
  round-tripping a lon/lat grid, so hemispheres and lobes need no bounds.
- A COG must carry an EPSG code in its GeoKeys. A VRT can carry any WKT1
  that proj4js parses.
- Rendering is on the CPU into canvas tiles. That keeps the planner and the
  sampler in plain sight; it is not the fast path.

See `GUIDE.md` for what this suggests for deck.gl-raster.
