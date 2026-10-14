"""A kerchunk-Parquet virtual Zarr fixture: chunk bytes (shuffle + zlib, like
netCDF4/HDF5) concatenated into one 'netCDF-like' blob with padding, a
.zmetadata with record_size, and refs.N.parq tables per variable.
Run: python3 make_refs_fixture.py OUTDIR"""
import os, sys, json
import numpy as np
import pyarrow as pa, pyarrow.parquet as pq
from numcodecs import Shuffle, Zlib

out = sys.argv[1]
root = os.path.join(out, "virtual.parq")
os.makedirs(root, exist_ok=True)
lat = np.arange(-89.7, 90, 0.6)          # 300, ascending
lon = np.arange(-179.7, 180, 0.6)        # 600
LON, LAT = np.meshgrid(lon, lat)
ssh = np.stack([np.sin(np.radians(LAT) * 3) * np.cos(np.radians(LON)) + 0.1 * k for k in range(2)]).astype("<f4")
ssh[:, (LAT > 70)] = 9.969209968386869e36                      # fill, like netCDF
chunks = (1, 150, 300)
sh, zl = Shuffle(elementsize=4), Zlib(level=1)
blob = bytearray(os.urandom(4096))                               # a header to skip
rows = []
for t in range(2):
    for j in range(2):
        for i in range(2):
            a = np.ascontiguousarray(ssh[t, j * 150:(j + 1) * 150, i * 300:(i + 1) * 300])
            enc = zl.encode(sh.encode(a.tobytes()))
            rows.append((len(blob), len(enc)))
            blob += enc + os.urandom(123)
open(os.path.join(out, "virtual_blob.nc"), "wb").write(blob)
target = "http://127.0.0.1:8765/fx/virtual_blob.nc"
rs = 5
def write_refs(var, recs):
    os.makedirs(os.path.join(root, var), exist_ok=True)
    for f in range(0, len(recs), rs):
        part = recs[f:f + rs]
        tbl = pa.table({"path": pa.array([r[0] for r in part], pa.string()),
                        "offset": pa.array([r[1] for r in part], pa.int32()),
                        "size": pa.array([r[2] for r in part], pa.int32()),
                        "raw": pa.array([r[3] for r in part], pa.binary())})
        pq.write_table(tbl, os.path.join(root, var, "refs.%d.parq" % (f // rs)))
write_refs("ssh", [(target, o, n, None) for o, n in rows])
write_refs("yt_ocean", [(None, 0, 0, lat.astype("<f8").tobytes())])
write_refs("xt_ocean", [(None, 0, 0, lon.astype("<f8").tobytes())])
meta = {
    ".zgroup": {"zarr_format": 2}, ".zattrs": {"title": "virtual fixture"},
    "ssh/.zarray": {"shape": list(ssh.shape), "chunks": list(chunks), "dtype": "<f4", "fill_value": 9.969209968386869e36,
                    "order": "C", "filters": [{"id": "shuffle", "elementsize": 4}, {"id": "zlib", "level": 1}],
                    "compressor": None, "dimension_separator": ".", "zarr_format": 2},
    "ssh/.zattrs": {"_ARRAY_DIMENSIONS": ["Time", "yt_ocean", "xt_ocean"], "nan_attr": float("nan"), "_FillValue": "AAAAgB2vFcQ=", "valid_range": [-1000.0, 1000.0]},
    "yt_ocean/.zarray": {"shape": [300], "chunks": [300], "dtype": "<f8", "fill_value": None, "order": "C", "filters": None, "compressor": None, "zarr_format": 2},
    "yt_ocean/.zattrs": {"_ARRAY_DIMENSIONS": ["yt_ocean"]},
    "xt_ocean/.zarray": {"shape": [600], "chunks": [600], "dtype": "<f8", "fill_value": None, "order": "C", "filters": None, "compressor": None, "zarr_format": 2},
    "xt_ocean/.zattrs": {"_ARRAY_DIMENSIONS": ["xt_ocean"]},
}
json.dump({"metadata": meta, "record_size": rs}, open(os.path.join(root, ".zmetadata"), "w"))
print("virtual zarr fixture in", root)
