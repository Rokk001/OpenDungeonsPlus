# Main-menu atmosphere

The supplied main-menu artwork remains the source image. Ten lightweight
screen-space layers add slow fog, flickering firelight, pulsing green acid and
an intermittent two-stage lightning glow at matching locations in that image.

Each layer is positioned in normalized artwork coordinates and recalculated
from the same aspect-preserving rectangle as the background. This keeps every
effect aligned when the viewport is letterboxed or pillarboxed. The layers use
existing flare and smoke textures and are created only while the main menu is
active.

## Verification

- The production Ogre material parser and render fixture pass 280 checks across
  five resolutions and three interface scales.
- The fixture verifies all ten layers remain inside the authored image and
  saves real rendered frames; the 1920x1080 frame was visually inspected.
- Release compilation and Windows runtime preparation pass.
- CTest has no registered tests in this build tree.

The implementation agent did not launch the game. Motion and timing still need
an in-game acceptance check.
