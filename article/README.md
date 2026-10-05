# Warp and cell: two worlds that were never separate

Draft, October 2026. The short version; a longer one with the history
done properly is planned for hypertidy.org. The pages this refers to
are at https://mdsumner.github.io/sidebyside/.

## Two globes

Open two browser tabs. In one, gridlook draws a month of EERIE model
precipitation on a globe: 196,608 HEALPix cells, each placed on the
sphere and coloured, spinning under the mouse. In the other,
ortho-cog-viewer draws a Sentinel-2 scene of eastern Tasmania on an
oblique Mercator centred wherever the screen centre happens to be,
rewarping as you pan. Both are static HTML on a free host, both read
their bytes straight from a public bucket with range requests, neither
has a server. They look like the same kind of thing and they are built
on opposite assumptions about what a picture of data is made of.

gridlook's assumption: the grid is the primitive. A dataset is a list
of cells with values, and the job is to put each cell where it belongs.
There is no image, only geometry carrying colour.

ortho-cog-viewer's assumption: the image is the primitive. A dataset is
a raster with a coordinate system and a geotransform, and the job is to
move that raster into the view. Values never move; the mesh under them
does.

Call them cell and warp. The sidebyside pages put one dataset in front
of both, name the gap, and propose the bridge. This article is about
why the gaps fall where they do, and why the two were never really
separate.

## Geometry is a recipe either way

The first thing to notice is that neither side stores coordinates.

A HEALPix cell has no stored position. Its id, together with the
refinement level and the indexing scheme, is enough to compute its
centre, its corners, its neighbours, its parent, all by arithmetic.
When rangefinder tried to open the EERIE store it went looking for a
coordinate array named after the cell dimension and got three 404s,
because there is none: the dimension is nameless on purpose.

A raster with a geotransform has no stored positions either. Six
numbers and a CRS generate the position of every pixel on demand.
Nobody writes down where pixel (4000, 2000) is; the recipe says.

So warp and cell are siblings. Both derive geometry late from a small
description, and they differ only in what the description indexes: a
regular lattice in a projected plane, or a hierarchical partition of
the sphere. The odd one out is the third stance, the explicit one,
where coordinates are stored and shipped: Simple Features, GeoArrow,
a GeoParquet of polygons. That is the materialised answer to a question
someone already asked, and it has its place, but it is not where the
viewers live.

This is the recipe-not-payload principle showing up as a rendering
taxonomy. The question to ask of any viewer is: how small a description
generates how much geometry, and how late?

## Drape is not warp

The second thing to notice is that "warp" names two different
operations, and conflating them hides the most useful distinction in
the whole comparison.

A materialised warp resamples the source into a target grid. The output
is a new array with its own CRS and geotransform. You can read values
from it, write it to a file, cache it, hand it to the next step. GDAL's
warper does this; rwarp does this; a MUR day published with 2x, 4x and
8x coarser siblings is this. New numbers come out.

A visual warp leaves the values alone and moves the geometry under them.
The source stays a texture; the mesh carries target-CRS positions and
the UVs point back into untouched pixels; the GPU samples at draw time
and nothing is ever written down. ortho-cog-viewer does this. You can
pick a value on screen, but you get it by inverting the mapping and
reading the source, not by reading the picture.

The second is a drape, and a drape is exactly what gridlook does with
cells: values as read, geometry derived late, picture as a side effect.
So within the sidebyside suite, ortho-cog-viewer and gridlook are closer
to each other than ortho-cog-viewer is to rwarp. rwarp is the only
thing in the suite that produces data rather than a view.

That matters for the bridges. "Publish coarser siblings so gridlook can
show a 650-million-cell field" is a materialised warp, done once by the
data owner. "Sample HEALPix cells into a projected view" is a drape,
done every frame by the viewer. The GPU interpolation in a drape is
still a resampling; it is just one nobody can audit or reuse. A
materialised warp costs a decision up front (kernel, nodata, alignment)
and what comes out is a thing. A drape is cheap and honest and you
cannot hand it to anyone.

## Where the gaps fall

With those two distinctions in hand, the suite's gaps stop looking like
a feature list and start looking like consequences.

Cell-side gaps: no COG as data, no spatial windowing, no tile services,
no projected CRS beyond what d3-geo offers. Every one of these follows
from "the grid is the primitive". A COG in UTM is an image, not a cell
list. A tile service is images. Windowing is an image operation. If
your primitive is cells on a sphere, level of detail has to come from
the data owner, as a hierarchy of stores, because there is nothing to
window.

Warp-side gaps: no HEALPix, no ICON, no cells of any kind. Every one
follows from "the image is the primitive". A list of cells is not an
image, and until something turns it into one (a mesh, or an inverse
mapping from view pixels to cell ids) the warp renderers cannot see it.

Then there are the gaps that do not follow from either stance. Icechunk
in rangefinder was one: not a consequence of anything, just a reader
not yet written, and it landed in a day once named. Those are the cheap
bridges, and the suite exists partly to make them stand out from the
expensive ones.

The one dataset both sides draw today is a CMIP6 tripolar ocean grid.
gridlook places each cell on the sphere from its 2D longitude and
latitude arrays. rangefinder takes the same arrays, computes cell
corners, rasterises the cells into an affine view grid, and warps that.
Same field, same month, two routes. That page is the clearest
illustration in the suite: the stances are not two worlds, they are two
ends of one road, and a curvilinear grid happens to be reachable from
both.

## Modal thinking, and a 2017 post

Why does it feel like two worlds? Because tools carry models, and a
community organises its thinking around the model its tools hold.

In 2017 I wrote a summary of R spatial that said, in effect: sf is here,
it replaces sp and rgdal and rgeos, and this is good. It was. But the
thing sp had done to us is worth naming now. sp made the vector/raster
split a type system: SpatialPoints, SpatialLines, SpatialPolygons on one
side, SpatialGrid and SpatialPixels on the other. SpatialPixels was the
attempt to have it both ways, a raster that was secretly a table of
cells with coordinates, and it was slow and awkward and nobody loved it.
The lesson the community drew was "rasters and vectors are different
things", when the lesson available was "SpatialPixels was a bad
implementation of a correct idea". sf then sharpened the vector side
and left the raster side to raster and later terra, and the split
became two package ecosystems with different maintainers, different
idioms and a conversion function between them.

That is modal thinking: not wrong, just a habit of mind inherited from
a data structure. The same thing is visible today in the two viewer
worlds. The ESM community's tools say the grid is the data, and so its
people see images as a lossy export. The imagery community's tools say
the image is the data, and so its people see cells as an exotic grid
type. Neither is a position anyone argued for. Each is what the tools
made obvious.

The 2017 post ended with what sf could not represent: tracks, indexed
meshes, networks. Nine years on, the list has a new entry, and it is
the same entry in a new coat: a DGGS is an indexed mesh whose indices
are so good you never need to store the mesh.

## What this is not

It is not an argument that one stance should win. The cell side is
faster to a picture and more honest about what a cell is; the warp side
degrades gracefully across data shapes the cell side cannot touch, and
it can produce outputs rather than views. A national data function
needs both, and will get both whether or not anyone plans it, because
the model centres will build cell viewers and the imagery centres will
build warp viewers.

What it is: an argument for keeping the seam visible. Both sides now
use the same libraries underneath (zarrita for chunks, icechunk-js for
repositories, healpix-geo for cell geometry), so the difference is not
in the reading, it is in what happens after. A viewer that lets you see
which stance it is taking, and switch, is more useful than one that
hides it. The sidebyside pages are a small way of insisting on that.

## Sources

- https://mdsumner.github.io/sidebyside/ (the pages)
- https://github.com/d70-t/gridlook (DKRZ / MPI-M; Fast, Koelling,
  Wachsmann, Kluft)
- https://github.com/hypertidy/rangefinder,
  https://github.com/mdsumner/ortho-cog-viewer, rwarp (hypertidy)
- https://www.hypertidy.org/posts/2017-01-10_r-spatial-2017/
- docs/rangefinder-icechunk.md and docs/rangefinder-healpix.md in this
  repository, for the two bridges in detail
