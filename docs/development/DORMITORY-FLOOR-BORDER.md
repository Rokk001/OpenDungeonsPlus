# Dormitory floor continuity

The September 19 19:22:06 screenshot shows dark-red patches and interrupted
carpet borders in narrow parts of the dormitory. `GameMap::computeTileSetIndex`
encodes south/east/north/west neighbours in bits 0/1/2/3, and the default tile
set sends seven masks (isolated, one neighbour, opposite neighbours) to the old
`Dormitory.png` stone-like red texture. The nine complete edge/corner/interior
variants instead use the existing woven carpet textures. No actor, bed placement
or lighting change is needed for this material-selection defect.

Complete only the missing masks by composing the shipped carpet, straight-edge
and corner samples in the room shader's dormitory-only variant. Reuse the old
room lighting/shadow calculation; leave other room materials and the nine
existing dormitory variants unchanged. Native mesh UVs map U towards west and
V towards north, as established by the existing straight/corner tile mappings;
the render regression must verify all sixteen neighbourhood masks and rotations.

Branch: `fix/dormitory-floor-border`, from complete checkpoint `2bd8172c`.
The native Ogre regression passes 96 assertions across all sixteen masks,
including their actual tile rotations: exposed boundaries have stone edging,
connected boundaries retain carpet, and every centre is carpet. The pixel checks
use the production fragment/material and Room mesh with a flat diagnostic vertex
stage; a second render uses the full production vertex shader including world
deformation. All sixteen full-pipeline previews were generated; isolated, end,
passage and corner examples were inspected. No shader/material errors occurred.

No C++ rebuild or version/save/network change is required. The normal runtime's
config, material and shader junctions point at these updated source assets;
restart the game to reload them. The README's existing room description is
unchanged; this fixes only floor continuity, not room mechanics. User screenshot
acceptance remains pending and no game was launched by the agent.
