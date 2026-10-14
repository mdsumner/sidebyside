# Data recipes for Gearbox

`dep_ls_geomad_red_antimeridian.vrt`: a GDAL VRT mosaic of the red band of
the Digital Earth Pacific Landsat GeoMAD 2025 test tiles (a 4 x 3 grid of
96 km tiles in EPSG:3832, columns 064-067, rows 020-022), referenced by URL
from the public staging bucket. Column 066 crosses the antimeridian. The
same tiles are the test case in developmentseed/deck.gl-raster#673. The
grid was written from the items' `proj:transform` (checked against 064/020,
066/021 and 067/022: row numbers increase northward); Gearbox reads each file's own georeferencing, so the
`DstRect` values only steer which files a view touches.

Check it with GDAL:

    gdalinfo /vsicurl/https://mdsumner.github.io/sidebyside/gearbox/data/dep_ls_geomad_red_antimeridian.vrt
