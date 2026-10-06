# Notes for the long version: what the 2011 thesis already said

Source: Sumner, M. D. (2011). The tag location problem. PhD thesis,
IMAS, University of Tasmania. Submitted May 2011; the work began in
2002, in earnest from 2003; Chapter 3 is Sumner, Wotherspoon and
Hindell (2009), PLoS ONE 4(10):e7324, after a long review history.
Built with R 2.12.0, sp, rgdal, maptools, spatstat. Page numbers are
the thesis's own.

Dating matters for the long version: the representation arguments in
Chapters 2, 5 and 6 were formed across 2003-2009, which is the whole
sp era (sp 0.7 appeared in 2005), so they are a contemporary reaction
to that type system, not hindsight.

These are the passages that map onto the warp / cell / drape vocabulary
of article/README.md, with the mapping stated. For the hypertidy long
version, which will do the sp/rgdal history properly.

## 1. Discrete versus continuous, in the data or in the rendering (p. 25)

> "The trip package provides tools to produce simple and KDE grids with
> line or point interpretations. The distinction here is one between
> discrete and continuous representations which can be represented in
> the data itself, or in the visualization technique or analysis used.
> The lack of clarity for these distinctions in spatial software is one
> of the problems faced in tracking research."

This is the drape-versus-materialise distinction in 2009 words: the
same continuity can live in the stored data (a materialised surface) or
in the technique that draws it (a drape), and the software of the day
did not let you say which you meant. The article's section "Drape is
not warp" is this paragraph, seventeen years later, with GPUs.

## 2. The mesh, named and set aside (p. 21)

> "Regular or irregular 'wireframe' representations give a smoother
> result and have continuous analytical and visualization counterparts
> via interpolation, but these data structures are more complicated to
> calculate and are much less widely supported."

And p. 18, in parentheses:

> "(Regular grids are historically easy to store and to compute, and so
> are applied most commonly -- irregular grids and meshes are not
> considered here)."

The mesh was already the right answer and already too hard to reach
from the available tools. anglr, and later the cell stance, are the
return to this parenthesis. Worth quoting exactly because it shows the
choice was made consciously, on cost, not on principle.

## 3. Time as attribute versus time as a continuous axis (p. 22)

> "GIS can be used to perform these calculations, but as discussed in
> Section 2.2.3 working with time in GIS is not well supported and this
> must be done as an attribute on line objects, rather than on
> inherently continuous lines that vary through time or other
> dimensions as well as space."

The earliest form of "Simple Features is a rendering format": a line
object with time as an attribute is a picture of a track, not the
track. Section 2.2.3 ("Joining the dots") is the place to mine for the
long version's account of what the sp/GIS model could not hold.

## 4. The parent grid with child windows (pp. 91-95)

> "A 'parent' grid encompassing the entire region is defined with a
> given grain size and offset. This is then treated as a virtual 3D
> array, without requiring that the parent matrix be duplicated for
> every time step. [...] A spatial 'child' window of each time step is
> stored to encompass only the samples for each estimate."

> "This is in effect a three-dimensional sparse array, where the X and Y
> dimensions are regularly spaced and the third dimension corresponds
> to the times t_i [...]. Only the smallest required subset is stored,
> and so the binning is fast as we are not handling redundant empty
> cells."

That is a tile scheme (grout, vaster's TileScheme) and a chunked array
with offsets, described without either word because neither existed in
the vocabulary of the tools. Figure 5.3 ("Indexing scheme", p. 95) is a
chunk index diagram. The recipe-not-payload principle is already here:
the parent grid is six numbers, the children are offsets into it.

## 5. Primary and intermediate locations (pp. 91-94)

> "No existing study has made an explicit distinction between primary
> locations that represent purpose-measured data and intermediate times
> between these. [...] The intermediate locations are truly continuous
> in that each individual element represents the entire interval between
> each subsequent primary location."

The measured point is discrete and the interval between is continuous;
the representation must hold both. For the long version this is the
same shape as "the value is at the cell, the geometry is between the
cells" and is the reason a track is a mesh problem, not a point
problem. Figures 5.1 and 5.2 (pp. 93-94) are the pictures.

## 6. The divide in data representation, named as the cause (p. 90)

> "The limited support for continuous variables in GIS vector was
> discussed in Chapter 2. The crossover of these research domains is
> rare partly because of this divide in data representation, but is
> increasingly relevant due to multi-disciplinary studies."

This is the article's "modal thinking" claim in its original form: a
divide in representation produces a divide in communities. In 2011 the
two domains were tracking ecology and oceanography; in 2026 they are
ESM visualisation and imagery. Same mechanism.

## 7. Slabs versus points (pp. 104-106)

> "Data interfaces generally use one of two types: direct manipulation
> of 'slabs' of array data, or database-like lookup of exact samples
> queried by 3D or 4D track coordinates."

> "Point samples provide a direct overlay of single coordinates with an
> arrayed data set. In its own right this is very simple, but include
> requirements for interpolation to exact coordinates and dynamic
> interaction and the common slab implementations are lacking. This is
> analogous to the deficiencies of topological data identified in
> Chapter 2 -- decisions or habits established at one level have serious
> ramifications for the simplest next level of generalization."

Slab access is the warp stance (read a window, resample it); point
lookup is the cell stance (invert position to index, read one value).
The thesis wanted both and had neither in a usable form; "decisions or
habits established at one level have serious ramifications" is modal
thinking stated as a mechanism. The three access types listed on p. 105
(slab in memory, compressed masks, database) are a 2009 sketch of
chunked object storage, bitmask overviews, and a query engine. xyt,
planned-extraction and the Icechunk work are the point-lookup side of
this finally being built; rangefinder's windowed reads are the slab
side.

## 8. Projections (p. 26)

> "Despite the wide availability of software tools for working with map
> projections their use is still virtually non-existent in modern
> tracking studies."

Footnote 7 lists PROJ, rgdal, Manifold, GMT. For the long version's
projection section (sidebyside page 07), the point is that the tools
existed and the habit did not; the same is true of the cell side's
d3-geo list today.

## 9. The tools acknowledged (acknowledgements, p. vii)

> "To build the document figures and displayed code I have used R 2.12.0
> with the following packages: MASS, mgcv, deldir, spatstat, lattice,
> sp, rgdal, maptools, geosphere, zoo, maps, mapdata, RODBC and ff."

deldir and spatstat are the mesh and the pixellation; sp, rgdal and
maptools are the modal type system; ff is memory-mapped arrays, the
2009 answer to the slab problem (Section 6.5, "Large data set
example"). The tripGrid code on pp. 42-45 is a worked example of the
SpatialGridDataFrame era: a grid is a data frame of cells with a
GridTopology, exactly the "raster that is secretly a table" the article
describes.

## 10. Two diagnoses from memory, not from the thesis (Oct 2026)

Stated in conversation from memory, close to but not verified against
the record. Before either goes into the long version, look up the
specifics (Dropbox or svn cache from the sp era): for SpatialPixels, the
class definition and points2grid's handling of gaps, and whatever
thread prompted the realisation; for the generics, one concrete method
that could not be made to dispatch. Sharper than the article's current
sp paragraph and should replace it once checked.

- SpatialPixels conflated non-regularity with sparsity. Whether cells
  lie on a regular lattice and whether all cells are present are
  independent properties; a type that fuses them can represent neither
  cleanly. The same conflation is why rangefinder could not see a
  HEALPix store in 2026: its geometry types fuse "regular" with "has
  coordinate arrays", and a HEALPix grid is regular with none.
- sp could not be extended despite its S4 foundation: the generics were
  written for the shipped classes, so a new representation could not
  join the dispatch. sf repeated this with S3: print, plot and the st_*
  generics are hardcoded to the shipped sfc types. A type system that
  cannot be extended turns a representation choice into a community
  boundary. That is the mechanism behind "modal thinking": not that
  people chose a model, but that the tools made the model
  unextendable, so disagreement had to become a separate package
  ecosystem.

  One independent verification for sf: r-spatial/sf issue 2430,
  "plot() not anticipating subclasses" (31 Aug 2024). Subclassing an
  sfc object and calling plot() failed inside st_is_empty() with
  "Not compatible with STRSXP: [type=NULL]"; the reporter: "This makes
  it difficult to write extensions to the sf package." Closed in
  September 2025 as no longer reproducible, "solved as a byproduct" of
  commit 436c293, mechanism unclear. The exact form of the claim is
  therefore: extension failed in practice because internals checked
  shipped class names, and when it started working it was by accident,
  not design. That is a cleaner illustration of modal thinking than a
  flat "cannot": nobody decided to block extension, the code never
  considered it. A nine-year-old private gist holds the earlier sp
  version of the same complaint (does not mention 2430).

## 11. The 2017 gist (simple-frust-private.md; private, with 2020 and 2025 comments)

Nine years old, edited a few times. Many of its specific complaints were
later dealt with "because some motivated user pursued them". For the
long version, quote the structural sentences only; the 2020 comments
are heat, the gist is private for a reason, and the argument is
stronger without them. The Dec 2025 comment shows the heat cooled and
is the one to end on.

- Conflation, third instance: "The two issues of many features and
  many columns are completely independent but become completely
  confounded here." Same failure as SpatialPixels (regularity vs
  sparsity) and rangefinder's geometry types (regular vs has coordinate
  arrays): a type fusing two orthogonal properties so neither can be
  expressed alone. Candidate single technical thesis for the long
  version, with modal thinking as its social consequence.
- Topology vs geometry: "The relationship between topology and geometry
  is confused, while these are rightly decoupled and have dimension in
  ways that are independent they are usually conflated to mean the same
  thing." And: "Simple features are completely described as paths";
  PATH as "a stepping stone to the PRIMITIVES". The 2009 mesh
  parenthesis returning as a plan; recipe-not-payload in 2017 clothes.
- The seam, named: "'We use sf format but not sf itself' is itself an
  emerging standard." Exactly the shape sidebyside argues for: shared
  formats and readers, divergent renderers. "sf should import
  sfheaders" is the extension that did not happen; issue 2430 is the
  one that eventually did, by accident.
- Closing note (Dec 2025): "most of the bad choices by sf were unmade
  and made better by terra", with gdalraster + wk + geos as the
  development-grade path. Together with "many things have been dealt
  with because some motivated user pursued them", this lets the
  history end honestly: modal thinking is real, and it is eroded by
  individuals who refuse the mode, which is what the bridges in
  sidebyside are.

## What the long version should do with this

- Replace the article's one-paragraph sp/rgdal account with a section
  that quotes 1, 3, 6 and 7 and dates them: the divide was named in
  2009-2011, by someone inside the sp world, as a representation
  problem, and the mesh (2) was the known fix set aside for cost.
- Use 4 as the origin of the tile-scheme line (trip's parent/child
  grid -> raster/terra blocks -> grout -> vaster TileScheme -> aatgrid),
  which is the warp stance's own recipe-not-payload lineage.
- Use 5 to argue that tracks, meshes and DGGS cells are one family: a
  value at a sample, geometry derived between samples.
- Keep the 2017 post as the mid-point: sf arrived, the vector side got
  sharper, the divide got wider, the list of what sf could not hold
  (tracks, meshes, networks) is the list from 2011 unchanged.
