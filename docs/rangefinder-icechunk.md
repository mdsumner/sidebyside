# Icechunk as a rangefinder source: design and plan

Status: plan, ready to implement. Drop into hypertidy/rangefinder as
docs/icechunk.md. Written against rangefinder main as of 2026-10-06
(lib/sources/zarr.js at 1076 lines) and icechunk-js 0.6.0.

## 0. Why this is small

rangefinder already treats "a Zarr store" as an interface: openDataset()
in lib/sources/zarr.js takes a URL, picks a store object with get() and
getRange(), wraps it in a byte-counting shim, hands it to zarrita, and
everything downstream (describe, readZarrWarped, readCurvilinear,
zarrProfile, the chunk cache, the inspector) works on zarrita arrays.
There are already three store kinds behind that seam:

- FetchStore for a plain Zarr directory (zarrita's own)
- referenceStore() for Kerchunk JSON references
- parquetRefStore() for Kerchunk Parquet references

icechunk-js exports IcechunkStore, whose open() returns an object that
implements zarrita's AsyncReadable with both get() and getRange()
(getRange is needed for sharded arrays). So Icechunk is a fourth store
kind behind the same seam, not a new source. Nothing in layers 1, 2 or
4 changes.

What Icechunk brings that the other three do not: the manifests are
native, so a repo can hold virtual chunks pointing into NetCDF, HDF5,
GRIB or TIFF archives (the VirtualiZarr / blocklist / gdal mdim get-refs
story) and native chunks it wrote itself, with snapshots, branches and
tags. For rangefinder that means an ACCESS-NRI or AAD virtualized
collection reads the same as a plain store, and a version can be pinned
in the URL.

## 1. Detection

An Icechunk repo is a directory with refs/ and snapshots/ (v1) or a
config and a refs manifest (v2). icechunk-js auto-detects the format.
rangefinder needs to decide "this URL is an Icechunk repo, not a Zarr
directory" before opening, cheaply and without a listing (buckets rarely
allow ListBucket, see docs/design.md "OPEN DOOR").

Rule, in order:

1. URL scheme hint: icechunk+https://... or icechunk://... selects
   Icechunk explicitly. Strip the prefix, pass the https URL on. This is
   the documented way and the one the catalogue should write.
2. Fragment or query hint, for URLs that come from elsewhere:
   ?icechunk=1, or #icechunk. Same effect.
3. Sniff: GET <url>/refs/branch.main/ref.json (v1) and, failing that,
   <url>/config.yaml or the v2 ref location. A 200 on either means
   Icechunk. Do the sniff only when the URL has no .zmetadata and no
   zarr.json at its root (one extra 404 on a plain store is already
   being paid for .zmetadata today, so this adds at most two).

Store the decision on the dataset object as ds.refs = "icechunk" so the
inspector and export.js can say so (the VRT export must decline, as it
does for Kerchunk: noVrt = "Icechunk repositories are not exported as a
source VRT; GDAL has no Icechunk driver").

Branch, tag and snapshot are carried in the URL too, as a query string
on the icechunk URL: ?branch=dev, ?tag=v1.0, ?snapshot=ABC123. Default
branch main. These are part of the dataset identity, so they are part of
the key in the datasets map.

## 2. Loading icechunk-js

Same on-demand pattern as zarrita() and hyparquet() in zarr.js: a lazy
import from a CDN list, memoised, reset on failure.

    var ICECHUNK = ["https://cdn.jsdelivr.net/npm/icechunk-js@0.6/+esm",
                    "https://esm.sh/icechunk-js@0.6"];

Dependencies are @msgpack/msgpack and flatbuffers, both pure JS, both
resolved by the CDN's ESM bundling. No wasm. Unpacked size is about
1 MB on npm; the bundled ESM will be a few hundred KB, loaded only when
an Icechunk URL is opened. Pin the major.minor as zarrita is pinned.

icechunk-js requires zarrita >= 0.7 for withRangeCoalescing; rangefinder
already loads zarrita@0.7. Opt into coalescing: it merges concurrent
range reads against the same backing object, which is exactly the
pattern when several chunks of one virtual NetCDF are read for one view.
Note the README caveat: one aborted read in a merged batch can reject
the others, so do not share one AbortController across reads that must
cancel independently. rangefinder's pool() already gives each read its
own signal from the caller; keep that.

## 3. The store branch in openDataset

Sketch, in the style of the existing code:

    async function icechunkStore(url, opts) {
      var ic = await icechunk();                  // lazy module, section 2
      var z = await zarrita();
      var raw = await ic.IcechunkStore.open(url, {
        branch: opts.branch || "main",
        tag: opts.tag, snapshot: opts.snapshot,
        withRangeCoalescing: z.withRangeCoalescing,
        signal: opts.signal
      });
      var bytes = new Map();
      var s = {
        bytes: bytes, refs: "icechunk", raw: raw,
        get: async function (key, o) {
          var b = await raw.get(key, o);
          if (b) bytes.set(key, b.byteLength);
          return b;
        },
        getRange: async function (key, range, o) {
          var b = await raw.getRange(key, range, o);
          if (b) bytes.set(key, (bytes.get(key) || 0) + b.byteLength);
          return b;
        }
      };
      // the hierarchy comes from the snapshot, not from a listing
      s.paths = raw.listNodes().filter(function (n) { return n.kind === "array" || n.nodeType === "array"; })
                               .map(function (n) { return n.path; });
      return s;
    }

Then in openDataset():

    var counting = isIcechunkUrl(url) ? await icechunkStore(stripIcechunk(url), icechunkOpts(url))
                 : isParquetRefs(url) ? await parquetRefStore(url)
                 : isReferenceUrl(url) ? await referenceStore(url) : null;

and, after withMaybeConsolidatedMetadata (which is a no-op for v3; keep
it, it is harmless):

    var paths = counting.paths || (store.contents ? ... : null);

That is the whole integration. Check the exact shape of listNodes()
output against the 0.6.0 typings when implementing; the README shows
listChildren("/"), listNodes() and getNode(path), and the array/group
discriminator may be named differently from the sketch.

## 4. Zarr v3 specifics

Icechunk repos are always Zarr v3. rangefinder's zarr.js was written
against v2 stores (.zarray, .zattrs, _ARRAY_DIMENSIONS) and zarrita
abstracts most of the difference, but three places read metadata
directly and need a v3 path:

- dimNames(arr): v2 puts names in attrs._ARRAY_DIMENSIONS; v3 puts them
  in the array metadata's dimension_names. zarrita exposes both on the
  opened array; read arr.meta.dimension_names first, fall back to the
  attribute.
- describe(): anything that inspects raw .zarray fields (chunks, dtype,
  fill_value, compressor) should go through the zarrita array object,
  which normalises v2 and v3. Audit for direct spec reads.
- Consolidated metadata: v3 stores may carry it in zarr.json under
  "consolidated_metadata"; Icechunk does not need it at all because the
  snapshot is the index. The paths list from section 3 replaces
  store.contents() for this store kind.

Sharded arrays (the v3 sharding codec) are what getRange exists for;
zarrita handles the inner-chunk index, the store only has to serve byte
ranges. The chunk cache key in chunks.js is (store url, array path,
chunk coords); for a sharded array that is still right because zarrita
asks for inner chunks by their logical coords.

## 5. Virtual chunks

A virtual chunk's bytes come from another object (s3://, gs://, https://
or az://). icechunk-js resolves the location and issues the range
request itself; rangefinder does not see the indirection, only the
bytes. Two things to carry over from the Kerchunk code:

- Public endpoint mapping: referenceStore() rewrites s3:// and gs://
  to their public https forms (httpsOf). icechunk-js does its own
  mapping for virtual chunk locations; check it agrees for the buckets
  in use (sentinel-cogs on us-west-2, NCI's and ACCESS-NRI's buckets)
  and, if a repo uses a region-specific endpoint, whether 0.6.0 exposes
  a hook. If not, this is the first upstream issue to file.
- CORS: every virtual chunk target must be CORS-open to the page's
  origin, independently of the repo's own bucket. The failure mode is
  that metadata loads and the first chunk read fails with a bare
  "Failed to fetch". Surface this in the inspector the same way a 403
  on a Kerchunk target is surfaced today, naming the target URL.

validateChecksums: leave off by default (extra headers per request);
expose as an opts flag.

## 6. Catalogue and UI

zarrCatalog(opts) already turns a Zarr URL into layer 1 + 2 entries
(variables, days, extents). An Icechunk URL goes through the same path.
The only UI additions:

- The source dialog accepts icechunk+https://... and shows branch / tag
  / snapshot fields when it sees one (free text, default main).
- The inspector's dataset line says "Icechunk (branch main, snapshot
  ABC123...)" next to the byte counts, so a shared permalink records
  which version was looked at. The snapshot id should be in the URL
  hash when the user picked a branch, resolved at open time, so the
  permalink is reproducible later even if the branch moves. That is the
  one piece of behaviour the other stores cannot offer, and it is worth
  making visible.

## 7. Test fixtures

Needed before any of this can be exercised: a public, CORS-open
Icechunk repo. Candidates in order of effort:

1. Write one. icechunk (Python) + xarray: one OISST or MUR day, two
   variables, native chunks, pushed to a bucket with CORS *. Ten lines.
   This is the fixture for sections 3, 4 and 6.
2. A virtual one over a NetCDF already on a public bucket, built with
   VirtualiZarr (or from blocklist output). This is the fixture for
   section 5 and the demo that matters for ACCESS-NRI.
3. Ask ACCESS-NRI (Charles Turner) whether one of the virtualized
   stores is, or can be, public with CORS. Also the dataset for
   sidebyside page 06.

A unit-style check in dev/: open the fixture, assert listNodes() finds
the variables, read one chunk through readZarrWarped at a coarse grid,
compare a few values against the same read through the plain-Zarr path
on a non-Icechunk copy of the same data.

## 8. Order of work

1. Fixture 1 (an hour, needs a bucket).
2. Section 2 + 3: loader and store branch; open the fixture, list it.
3. Section 4: dimNames and describe audit for v3; first image on screen.
4. Section 6: URL scheme, inspector line, snapshot in permalink.
5. Fixture 2 and section 5: virtual chunks, CORS failure surfacing.
6. Section 7 check in dev/, docs/sources-brainstorm.md updated, this
   file renamed to describe what was built.

Out of scope: writing, Icechunk's S3 credentials (anonymous only, as
everything else in rangefinder), az:// virtual chunks.

## 9. Relation to the rest

- sidebyside page 06 (hypertidy, mdsumner/sidebyside) is the public
  face of this: once fixture 3 exists the page gets a working warp
  panel and moves from warp-gap to shared.
- starc (hypertidy) remains the time index; Icechunk is a pixel-read
  (layer 3) concern only. A starc entry can point at an Icechunk URL
  with a snapshot, which is the reproducibility story for curated
  regions.
- gridlook reads Icechunk through the same icechunk-js, so the two
  viewers would share a reader and differ only in what they do with the
  array, which is the comparison the suite is trying to draw.
