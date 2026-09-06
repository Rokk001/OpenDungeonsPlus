# Wall hover outline

## Scope and existing implementation

Work branch: `fix/wall-hover-outline`, based on the accepted HUD checkpoint
`c450a6cc`. The user reported that hovering a diggable wall does not visibly
highlight it and authorized a correction. Existing hover targeting, drag
selection, digging requests and the blue outline presentation are reused.

The preview already creates a twelve-edge wall box, but its top was hardcoded
at Z=1.02. The actual loaded wall mesh reaches Z=1.375. Since the outline
material enables depth testing, the wall can obscure lines drawn inside it.
The source-derived asset check reproduces this mismatch: 101 checks, one failure
in the local `build/windows/hand-wall-height-before.log` diagnostic.

The correction must use the actual rendered wall's world bounds, including the
existing fog wall representation when the tile has not been revealed. Keep the
small surface clearance, ground previews and input behavior unchanged; do not
replace the height constant with another guessed wall height or disable depth
testing for the whole world.

## Correction and verification

The preview now finds the wall entity already created by the tile renderer,
falling back to the existing fog wall when unrevealed. It places the top outline
0.02 units above that object's current world bounding box. Translations, tile
rotations and model scaling are therefore reflected in the preview. A wall
without a rendered visual produces no invented box; floor previews remain at
their existing height. The selection and digging command paths are unchanged.

The focused OGRE geometry probe loads seven real wall/fog meshes and exercises
revealed/unrevealed lookup paths, three scales, rotation and translation, mixed
wall/floor previews, missing visuals and cancellation. It reports 85 failures
in 187 checks against `c450a6cc` and zero failures after the fix. The unrevealed
path uses the actual fog mesh on a regular OGRE entity to exercise the shared
bounding-box API; it does not render GPU instancing or a live game.

Local evidence:

- `build/windows/wall-outline-before.log` and `wall-outline-after.log`.
- `build/windows/generate-wall-outline-probe.py` extracts the production function.
- Release compilation: `build/windows/wall-outline-build.log`.
- Runtime preparation: `build/windows/wall-outline-runtime.log`.

Open `build/windows/opendungeons-plus.exe` directly. The user must still verify
the visible outline while hovering, dragging over walls, cancelling and changing
display scale/resolution; no game was launched by the assistant. The earlier
HUD fixes remain part of this executable and retain the user's acceptance.

Version stays 0.7.1 because this is a development correction, not a release.
README and the build/development notes describe the affected behavior; no
changelog exists in the checkout. The separate object-name finding is outside
this correction. Internal planning documents and the user's ignore-rule change
are not part of the functional contribution.
