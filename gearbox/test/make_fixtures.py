"""Build small fixtures for Gearbox: COGs, a VRT mosaic with an external
overview, and an XYZ tile pyramid. Run: python3 make_fixtures.py OUTDIR"""
import os, sys, math
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.enums import Resampling

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

def dome(xx, yy):
    r = np.hypot(xx, yy)
    return (3000 * np.exp(-(r / 900e3) ** 2) + 200 * np.sin(xx / 40e3) * np.cos(yy / 55e3)).astype("float32")

def write_cog(path, arr, transform, crs, nodata=None, dtype=None):
    tmp = path + ".tmp.tif"
    count = 1 if arr.ndim == 2 else arr.shape[0]
    dtype = dtype or arr.dtype
    with rasterio.open(tmp, "w", driver="GTiff", width=arr.shape[-1], height=arr.shape[-2], count=count,
                       dtype=dtype, crs=crs, transform=transform, nodata=nodata, tiled=True,
                       blockxsize=256, blockysize=256, compress="deflate") as d:
        d.write(arr if arr.ndim == 3 else arr[None])
        d.build_overviews([2, 4, 8, 16], Resampling.average)
    with rasterio.open(tmp) as s:
        prof = s.profile
        prof.update(driver="COG", compress="deflate", blocksize=256)
        prof.pop("blockxsize", None); prof.pop("blockysize", None); prof.pop("tiled", None)
        prof.pop("interleave", None)
        with rasterio.open(path, "w", **prof) as d:
            d.write(s.read())
    os.remove(tmp)

# 1. single COG in EPSG:3031, 1 km
res = 1000.0
x0, y0 = -1500e3, 1500e3
n = 3000
xs = x0 + (np.arange(n) + 0.5) * res
ys = y0 - (np.arange(n) + 0.5) * res
xx, yy = np.meshgrid(xs, ys)
write_cog(os.path.join(out, "dome_3031.tif"), dome(xx, yy), from_origin(x0, y0, res, res), "EPSG:3031", nodata=-9999)

# 2. VRT mosaic: 4 x 4 tiles at 250 m, each 800 px + 20 px overlap (like REMA)
tres = 250.0
tpx = 800
ov = 20
srcs = []
mx0, my0 = -800e3, 800e3
for j in range(4):
    for i in range(4):
        tx0 = mx0 + i * tpx * tres
        ty0 = my0 - j * tpx * tres
        w = tpx + ov
        xs = tx0 + (np.arange(w) + 0.5) * tres
        ys = ty0 - (np.arange(w) + 0.5) * tres
        a = dome(*np.meshgrid(xs, ys))
        fn = "tile_%d_%d.tif" % (j, i)
        write_cog(os.path.join(out, fn), a, from_origin(tx0, ty0, tres, tres), "EPSG:3031", nodata=-9999)
        srcs.append((fn, tx0, ty0, w))
W = H = 4 * tpx + ov
# whole-mosaic overview at 2 km that starts 900 m outside the mosaic, like REMA's 1 km
ores = 2000.0
ox0, oy0 = mx0 - 900, my0 + 900
on = int(math.ceil((W * tres + 1800) / ores))
xs = ox0 + (np.arange(on) + 0.5) * ores
ys = oy0 - (np.arange(on) + 0.5) * ores
write_cog(os.path.join(out, "mosaic_ovr_2km.tif"), dome(*np.meshgrid(xs, ys)), from_origin(ox0, oy0, ores, ores), "EPSG:3031", nodata=-9999)
with rasterio.open(os.path.join(out, "dome_3031.tif")) as d:
    wkt = d.crs.to_wkt()
lines = ['<VRTDataset rasterXSize="%d" rasterYSize="%d">' % (W, H),
         '  <SRS>%s</SRS>' % wkt.replace("&", "&amp;").replace("<", "&lt;"),
         '  <GeoTransform>%r, %r, 0, %r, 0, %r</GeoTransform>' % (mx0, tres, my0, -tres),
         '  <VRTRasterBand dataType="Float32" band="1">',
         '    <NoDataValue>-9999</NoDataValue>']
for fn, tx0, ty0, w in srcs:
    xo = int(round((tx0 - mx0) / tres)); yo = int(round((my0 - ty0) / tres))
    lines += ['    <ComplexSource>',
              '      <SourceFilename relativeToVRT="1">%s</SourceFilename>' % fn,
              '      <SourceBand>1</SourceBand>',
              '      <SrcRect xOff="0" yOff="0" xSize="%d" ySize="%d"/>' % (w, w),
              '      <DstRect xOff="%d" yOff="%d" xSize="%d" ySize="%d"/>' % (xo, yo, w, w),
              '      <NODATA>-9999</NODATA>',
              '    </ComplexSource>']
lines += ['    <Overview>',
          '      <SourceFilename relativeToVRT="1">mosaic_ovr_2km.tif</SourceFilename>',
          '      <SourceBand>1</SourceBand>',
          '    </Overview>',
          '  </VRTRasterBand>', '</VRTDataset>']
open(os.path.join(out, "mosaic.vrt"), "w").write("\n".join(lines) + "\n")

# 3. RGB COG in EPSG:4326, global, 0.1 degree
gres = 0.1
gw, gh = 3600, 1800
lon = -180 + (np.arange(gw) + 0.5) * gres
lat = 90 - (np.arange(gh) + 0.5) * gres
LON, LAT = np.meshgrid(lon, lat)
r = ((np.sin(LON * math.pi / 30) * 0.5 + 0.5) * 255).astype("uint8")
g = ((np.cos(LAT * math.pi / 20) * 0.5 + 0.5) * 255).astype("uint8")
b = (((LAT + 90) / 180) * 255).astype("uint8")
write_cog(os.path.join(out, "stripes_4326.tif"), np.stack([r, g, b]), from_origin(-180, 90, gres, gres), "EPSG:4326")

# 4. XYZ tiles z0..3 in EPSG:3857: checkerboard with the tile address drawn as colour
from PIL import Image, ImageDraw
for z in range(4):
    for x in range(2 ** z):
        for y in range(2 ** z):
            im = Image.new("RGB", (256, 256), ((x * 70) % 256, (y * 70) % 256, 60 + z * 60))
            dr = ImageDraw.Draw(im)
            dr.rectangle([0, 0, 255, 255], outline=(255, 255, 255))
            dr.text((10, 10), "%d/%d/%d" % (z, x, y), fill=(255, 255, 255))
            os.makedirs(os.path.join(out, "xyz", str(z), str(x)), exist_ok=True)
            im.save(os.path.join(out, "xyz", str(z), str(x), "%d.png" % y))
print("fixtures in", out)
