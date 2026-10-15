"""Zarr fixtures for Gearbox: a GeoZarr multiscale group (v3, EPSG:3031),
a CF-style v2 store with time/lat/lon (ascending lat, scale/offset, fill),
and a sharded v3 CF array. Run: python3 make_zarr_fixtures.py OUTDIR"""
import os, sys
import numpy as np
import zarr

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

def dome(xx, yy):
    r = np.hypot(xx, yy)
    return (3000 * np.exp(-(r / 900e3) ** 2) + 200 * np.sin(xx / 40e3) * np.cos(yy / 55e3)).astype("float32")

# 1. GeoZarr multiscale, v3, three levels
g = zarr.open_group(os.path.join(out, "geozarr_3031.zarr"), mode="w", zarr_format=3)
x0, y0, res0, n0 = -1500e3, 1500e3, 500.0, 6000
layout = []
for i in range(3):
    res = res0 * 2 ** i
    n = n0 // 2 ** i
    xs = x0 + (np.arange(n) + 0.5) * res
    ys = y0 - (np.arange(n) + 0.5) * res
    a = g.create_array(str(i), shape=(n, n), chunks=(512, 512), dtype="float32",
                       fill_value=np.nan, dimension_names=["y", "x"])
    a[:] = dome(*np.meshgrid(xs, ys))
    layout.append({"asset": str(i), "spatial:transform": [res, 0, x0, 0, -res, y0], "spatial:shape": [n, n]})
g.attrs.update({
    "spatial:dimensions": ["y", "x"],
    "proj:code": "EPSG:3031",
    "multiscales": {"layout": layout, "resampling_method": "average"},
})
zarr.consolidate_metadata(os.path.join(out, "geozarr_3031.zarr"))

# 2. CF v2: time, lat (ascending), lon; int16 packed with scale/offset and _FillValue
lat = np.arange(-89.875, 90, 0.25)
lon = np.arange(-179.875, 180, 0.25)
g2 = zarr.open_group(os.path.join(out, "cf_sst.zarr"), mode="w", zarr_format=2)
t = g2.create_array("time", shape=(2,), dtype="int32"); t[:] = [0, 1]; t.attrs["_ARRAY_DIMENSIONS"] = ["time"]
t.attrs.update({"units": "days since 2026-10-13", "calendar": "standard"})
la = g2.create_array("lat", shape=lat.shape, dtype="float64"); la[:] = lat; la.attrs["_ARRAY_DIMENSIONS"] = ["lat"]
lo = g2.create_array("lon", shape=lon.shape, dtype="float64"); lo[:] = lon; lo.attrs["_ARRAY_DIMENSIONS"] = ["lon"]
LON, LAT = np.meshgrid(lon, lat)
sst = 28 * np.cos(np.radians(LAT)) - 1.8 + 2 * np.sin(np.radians(LON * 3))
packed = np.round((sst - 20) / 0.01).astype("int16")
packed[(LAT > 60) & (LON > 0)] = -32768  # a land-like hole
v = g2.create_array("analysed_sst", shape=(2,) + sst.shape, chunks=(1, 240, 480), dtype="int16", fill_value=-32768)
v[0] = packed; v[1] = packed + 100  # the latest step is 1 degree warmer
v.attrs.update({"_ARRAY_DIMENSIONS": ["time", "lat", "lon"], "scale_factor": 0.01, "add_offset": 20.0, "_FillValue": -32768})
zarr.consolidate_metadata(os.path.join(out, "cf_sst.zarr"))

# 3. sharded v3 CF array with latitude/longitude names, descending latitude
g3 = zarr.open_group(os.path.join(out, "sharded.zarr"), mode="w", zarr_format=3)
lat3 = np.arange(89.75, -90, -0.5)
lon3 = np.arange(-180, 180, 0.5)
a = g3.create_array("latitude", shape=lat3.shape, dtype="float64", dimension_names=["latitude"]); a[:] = lat3
a = g3.create_array("longitude", shape=lon3.shape, dtype="float64", dimension_names=["longitude"]); a[:] = lon3
a = g3.create_array("init_time", shape=(3,), dtype="int64", dimension_names=["init_time"])
a[:] = [1791158400 + 86400 * i for i in range(3)]  # 2026-10-05, 06, 07 00 UTC
a.attrs.update({"units": "seconds since 1970-01-01", "calendar": "proleptic_gregorian"})
a = g3.create_array("ensemble_member", shape=(2,), dtype="int16", dimension_names=["ensemble_member"]); a[:] = [0, 1]
L3, A3 = np.meshgrid(lon3, lat3)
temp = (30 * np.cos(np.radians(A3)) - 10 + 5 * np.sin(np.radians(L3 * 2))).astype("float32")
a = g3.create_array("temperature_2m", shape=(3, 2) + temp.shape, chunks=(1, 1, 120, 180), shards=(1, 1, 360, 720),
                    dtype="float32", fill_value=np.nan, dimension_names=["init_time", "ensemble_member", "latitude", "longitude"])
for i in range(3):
    a[i, 0] = temp + i; a[i, 1] = temp - i
zarr.consolidate_metadata(os.path.join(out, "sharded.zarr"))
print("zarr fixtures in", out)
