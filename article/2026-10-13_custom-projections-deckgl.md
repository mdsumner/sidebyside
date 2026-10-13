# Custom projections in deck.gl: notes from the warp side

Draft, 13 October 2026. A position piece for
[visgl/deck.gl#10739](https://github.com/visgl/deck.gl/issues/10739)
(Tracker: Custom projection), written from the experience of building
browser viewers that already do most of what that tracker is reaching
for, outside deck.gl. The pages this refers to are at
https://mdsumner.github.io/sidebyside/ ; the viewers are
[ortho-cog-viewer](https://mdsumner.github.io/ortho-cog-viewer/),
[rangefinder](https://hypertidy.github.io/rangefinder/) and the rwarp
wasm slippy map.

## Where things stand

deck.gl merged an experimental `_CustomProjectionView` on 6 October 2026
(visgl/deck.gl#10741, second of a six-PR stack). Applications hand the
view a converter with `forward` and `inverse` in the shape of
`proj4(from, to)`, plus `fromCrs`, `toCrs`, an optional `fromBounds`
and `toBounds`, and a `resolution` for subdividing curved geometry.
Positions are preprojected on the CPU into map metres and drawn in
cartesian mode; a `projectionSignature` built from the CRS identifiers
and resolution tells layers when to rebuild. The reviewer's list of
what is still open: seam and domain clipping, spatially varying
distortion, polar computations, per-layer source CRS, and reusable
subdivision primitives in math.gl. The v10 ambition is GPU fp64
preprojection at attribute upload, keyed by named projections
(equal-earth, stereographic, albers, lambert).

The day after, deck.gl-raster merged an experimental
`custom-projection` example (developmentseed/deck.gl-raster#694): a
stand-in for the upstream view on deck.gl 9.4, a `ProjectedCOGLayer`
that selects tiles in the map CRS and draws each tile's mesh in map
metres, with presets for EPSG:3031, EPSG:3413, Equal Earth and Web
Mercator. Its README lists the limits plainly: top-down only, `fromCrs`
must be WGS84, polar-native rasters that contain a pole render only in
their own polar projection, domain trimming is exact only for grids
whose rows are parallels, mesh error is measured in source pixels, and
each projection is a separate tile layer.

That README is the most useful document in this whole thread, because
every line of it is a thing we hit and worked through in the last year,
and it is the list that decides whether deck.gl's custom projections
end up general or end up as "Equal Earth and polar stereo, top-down,
one layer per projection". What follows is what we would put on the
record, in the order it matters.

## 1. The converter contract is right; say that it is engine-agnostic

`forward`/`inverse` with `fromCrs`/`toCrs` is exactly the seam a
viewer needs, and it is the seam ortho-cog-viewer and rwarp already
use. Two things are worth stating in the docs rather than leaving
implicit.

First, the engine is not proj4js. A PROJ-in-wasm converter satisfies
the contract unchanged. ortho-cog-viewer keeps proj4js as the fast
path and one definition authority (`crsDefinition`, shared with
rwarp), and loads a PROJ wasm build on an unknown-code miss. That is
how it gets EPSG codes proj4js does not ship, and it is how it will get
datum grids when it needs them. rwarp's `CrsTransform` trait does the
same thing in Rust with libproj or proj4rs behind it. If the view's
docs say "proj4-shaped", people will read "proj4-limited".

Second, the identity of a projection is its definition, not its name.
`projectionSignature` built from `fromCrs`/`toCrs` strings is fine as
long as the strings are the definitions (a PROJ string or an
authority:code), and is a trap if they are labels, because two
converters can share a label and differ in parameters. This matters
for point 4 below.

Page 07 (projection vocabularies) is the comparison: d3-geo's named
list on one side, PROJ strings with a resolver on the other, and
proj-wasm as the bridge.

## 2. Domain is geometry, not a lon/lat box

This is the central argument and the one nobody in the thread has made
yet.

`fromBounds` as a box in source lon/lat works for Equal Earth and
Mercator. It does not describe a hemisphere in orthographic or tilted
perspective, an interrupted projection (Goode homolosine's lobes), or
the situation deck.gl-raster's README names: a polar-native raster
drawn in a world projection, where the pole becomes a line and the
tiles that touch it straddle the antimeridian, "which one mesh per tile
can't represent". A lon/lat box cannot say where a projection is
valid; only the target plane can.

The proposal: the view carries a domain defined in the target plane (a
polygon, or a predicate, or in the common case a half-period and a
boundary polyline), and preprojected geometry is clipped against that
boundary as one generic operation on positions and their attributes.
Three consequences follow.

The antimeridian stops being a special case. In Mercator the world-copy
boundary at x = k * 512 is just one domain edge; a tile that crosses
it is clipped there and each part shifted into its copy. This is
precisely what deck.gl-raster's `clipMeshToWorld` does in
developmentseed/deck.gl-raster#673 (unwrap in the reprojector, clip at
every multiple of the period, interpolate uv along the cut), and it
already has fixtures for a vertical 4326 seam, a rotated 4326 grid,
EPSG:3832, UTM 60N and a 360-degree-wide image. The vertical-line case
is done and tested; the generalisation to a boundary polyline is small.

Polar-native rasters become drawable in world projections, because the
tiles that wrap the pole are clipped along the domain edge rather than
folded.

Projections whose valid area is not a lon/lat box become drawable at
all. ortho-cog-viewer's tilted perspective (`+proj=tpers`) is a globe
by projection; its centred orthographic and omerc modes move the
boundary with the view centre; its interrupted Goode cuts along the
lobes. In every one of those the cut is a clip in the target plane,
and it follows the cursor because the domain is recomputed from the
projection parameters, not stored with the data.

The seam-unwrapping half of this also generalises: #673 snaps each
refined vertex's exact x to the copy nearest its parent triangle's
interpolated x, and unwraps seed vertices by bisection along the uv
path from the previous seed. That is standard phase unwrapping against
a local reference, which is why it works where the earlier attempts
(unwrap before proj4, a global `+over`) did not: proj4 normalises
whatever it is given, so the fix has to act on the transform output,
and it has to use references that are local enough to stay inside half
a period. The one stated limit, a seed triangle spanning a wildly
nonlinear region such as polar stereographic over the pole, is a
density problem, not a design problem.

## 3. Refinement error belongs in the output space

deck.gl-raster's reprojector measures mesh error in source pixels, as
if they were square. Lon/lat pixels near a pole are slivers on a polar
map, so a view straight over the pole needed over half a million
triangles until the example stretched each tile's pixel grid by its
aspect ratio on the map before meshing (`columnErrorScale`). The README
says the library should measure error in the output projection
instead; it should, and the view is the natural place to own that
metric, because `resolution` is already a subdivision parameter for
curved geometry and the raster meshers should use the same one.

There are two legitimate ways to build the mesh, and the choice
interacts with the metric. deck.gl-raster meshes in source uv and
projects the vertex positions (Delatin on the source grid, positions
moved). ortho-cog-viewer meshes in the target plane and carries the
warp in the texture coordinates (a regular grid in display CRS, uv
computed by the inverse transform). The first is the right shape when
the projection is static and the source is the thing being refined;
the second is the right shape when the projection changes every frame,
because the mesh never changes, only its uv. Both measure error best in
the target plane. Stating the trade-off in the tracker would save the
next library the year it took us.

## 4. Name the dynamic case as a non-goal, or own it

`projectionSignature` driving layer rebuilds assumes projection
parameters change rarely: a user picks Equal Earth, layers rebuild
once. Centred projections do not work that way. ortho-cog-viewer's
centred mode recomputes `+lon_0`/`+lat_0` (and the domain) from the
screen centre on every pan; orthographic, tilted perspective and
oblique Mercator all rewarp as you move. rwarp's wasm slippy map does
the materialised version of the same thing, warping tile-server
imagery into a local LAEA or polar stereo chosen per view.

deck.gl probably should not do this in v10. Preprojecting attributes
at upload, and especially fp64 preprojection on the GPU at upload, is
built on the assumption that upload is rare. That is a reasonable
non-goal. What would help downstream is for the tracker to say so, so
that libraries built on the view know whether "projection follows the
view" is theirs to build (it is), and so that the signature's contract
is explicit: a parameter change is a new projection, with the rebuild
cost that implies. The target-plane mesh with warp-in-uv (point 3) is
the shape that makes the dynamic case cheap; if the view ever wants
it, that is the route.

## 5. On the GPU registry

Keying named projections for a GPU fp64 fast path is fine. The key
should be a projection family with parameters, which is what `+proj=`
already is, rather than a label. Stereographic with parameters covers
EPSG:3031, 3413, 3995 and every local polar stereo without a registry
entry each; Lambert conformal conic with parameters covers every state
plane and national grid in that family. And the registry should fall
back to the converter on a miss rather than fail, so a PROJ string that
happens to be stereographic goes fast and one that is `tpers` still
draws.

## What we did instead, and why it matters here

The allonboard project arrived at the same stand-in as #694 on its own:
one `SimpleMeshLayer` per tile, mesh in the view CRS, an
`OrthographicView` of EPSG:3031 metres (allboa decision 0010). Two
groups converging on the same workaround in the same month is decent
evidence that the view is the missing piece and that the raster layer
on top is not the hard part.

So the division we would argue for:

- The projection contract, the engine seam, domain-as-geometry and the
  clip operation, and the error metric belong in deck.gl core and
  math.gl. They are properties of the view, and every layer needs them.
- Tile selection in the map CRS, mesh construction per tile, and the
  fixtures that prove it belong in deck.gl-raster, where Kyle has
  already written the first version.
- Projection-follows-the-view, globe-by-projection, interrupted
  projections rotating under the cursor stay in viewers built for
  them. deck.gl's model is one static planar space per view; nothing in
  the tracker moves toward re-meshing as the centre moves, and it does
  not need to.

What we can contribute cheaply, and will: fixtures. A pole-containing
EPSG:3031 tile, a UTM 60 scene, a 360-degree image, a tilted
perspective hemisphere and an interrupted projection are the inputs
that surface the half-period and lon/lat-box limits, and a failing test
is the contribution form that gets merged. The data is already in
their example (the GEBCO in #694 is `ausantarctic/gebco` on Source
Cooperative).

## Pages

- 04 polar: GIBS EPSG:3031 and LIST WMTS draped on polar stereographic
  in the browser; the CRS vocabulary gap.
- 07 projections: proj4js plus proj-wasm against d3-geo's list; Goode,
  tpers and centred omerc on the warp side.
- A page for the deck.gl stand-ins (deck.gl-raster#694 and allonboard's
  SimpleMeshLayer-per-tile) against ortho-cog-viewer on the same
  EPSG:3031 dataset is the obvious next one: one dataset, two warp
  shells, the gap being domain and dynamic projection.

## References

- visgl/deck.gl#10739 Tracker: Custom projection
- visgl/deck.gl#10741 feat(core): add experimental CustomProjectionView
  (merged 2026-10-06)
- developmentseed/deck.gl-raster#694 experimental custom projection
  example with polar stereographic COGs (merged 2026-10-07)
- developmentseed/deck.gl-raster#673 antimeridian support (unwrap in
  the reprojector, clip at the world boundary; on the
  kyle/antimeridian-crossing branch)
- developmentseed/deck.gl-raster dev-docs/specs/2026-05-27-antimeridian-crossing-tile-design.md
- mdsumner/ortho-cog-viewer ; hypertidy/rangefinder ; rwarp wasm demo
