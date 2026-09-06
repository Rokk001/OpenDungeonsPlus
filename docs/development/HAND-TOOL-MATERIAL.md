# Textured hand tool

Work branch: `fix/hand-tool-material`, based on combined checkpoint `199e20ab`,
which retains `84f9eae3` and parallel documentation checkpoint `ba245257`.

## Existing implementation and reuse decision

The hand already has a procedural pickaxe attached to its existing skeleton.
Its prism helper emits positions and fixed vertex colours into `debug_draw`,
without texture coordinates. That material also draws world previews, so a
global material change would alter unrelated feedback. The separate hand
material and all existing pose/input transitions must remain intact.

The repository already contains diffuse wood and metal surfaces in
`BasicAxe.png` and `BasicHammer.png`, credited to YD under CC0 in CREDITS.
The original axe and hammer shapes are unsuitable replacements for the pickaxe.
Their object-space normal maps are specific to those meshes and cannot be
reused on this geometry. Reuse only the matching diffuse atlas regions through
isolated tool materials, retaining the existing silhouette, attachment, depth
behavior and face shading. Do not modify the shared debug or hand materials.

## Implemented correction

The prism helper now supplies texture coordinates for front, back and side
triangles. The head sections share a common mapping so the metal pattern stays
continuous across them; depth is mapped across each side instead of collapsing
its coordinates onto an edge. The shaft and head use separate tool-only
materials with interior wood/metal atlas regions. Existing side-face darkening
remains, while the textures supply wood grain and metal surface detail.

Both materials retain the previous depth and blending behavior. They are unlit
and do not receive world shadows; the result is textured shading, not a new
dynamic lighting model. Original positions, silhouette, attachment, animation
and input handling are unchanged. No texture, shared material or dependency
was added or altered; the new material script uses existing texture files.

## Verification

All 521 geometry/material checks pass using actual installed Ogre objects and
GPU buffers. The production helper and creation blocks are compared with
checkpoint `84f9eae3`: all 156 vertex positions and the full bounds match, all
52 triangles retain their topology, every front/back/side triangle has finite,
non-collapsed texture coordinates, and the material/texture/depth/shadow checks
pass. The probe also verifies cleanup. This is not a gameplay test.

Isolated GL3Plus renders of the actual hand, tool and material scripts pass
from three camera directions, with integrated shadows disabled and enabled.
Each shadow-on image exactly matches its shadow-off counterpart by SHA-256.
The before/after images visibly replace solid grey/brown faces with dark metal
and wood grain. Original mesh-format, bone-weight and engine shader warnings
remain; no new tool material parsing or shader error occurs. These previews
do not establish final grip, hand orientation, reference animation timing or
appearance under every live display setting.

Logs and local evidence:

- `build/windows/hand-tool-probe-results.log`: 521 checks, zero failures.
- `build/windows/hand-tool-preview-before.log` and
  `hand-tool-preview-textured.log`: rendered comparison and cleanup.
- `build/reference-audit/hand-tool-before-*.png` and
  `hand-tool-textured-*.png`: three views and corresponding shadow variants.
- `build/windows/hand-tool-build.log`: Release build staged separately while
  the user was playing; the game process was not stopped.
- `build/windows/hand-tool-runtime-build.log` and `hand-tool-runtime.log`:
  normal Release output and runtime preparation after the game closed.

The ready executable at `build/windows/opendungeons-plus.exe` is dated
September 6, 2026 at 18:58:11, SHA-256
`66d0f7d258b88525f892faa59c39fb43cb82314ee96fad54c6c244c72ee5e302`.
No game was launched. Manual appearance remains with the user; hover a diggable
wall, return to open ground and navigate across interface controls.

Version remains 0.7.1 because this is a development correction, not a release.
The README's controls remain accurate, the development index links this note,
and the checkout has no changelog. Existing YD/CC0 texture credits in CREDITS
remain valid. Private comparison evidence stays outside upstream contributions.
