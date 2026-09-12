# Main-menu atmosphere

## September 12 motion correction

The user rejected the three visibly isolated clouds and their stepped motion.
The old renderer explicitly selected one smoke-atlas frame at three frames per
second, with no interpolation; material diffuse colour also did not reliably
control the unlit layers' final opacity. The correction replaces atlas playback
with continuous procedural mist, controls tint and opacity in the fragment
shader, keeps mist below or beside the navigation, and adds small rising embers
anchored to the painted braziers. The background and navigation remain intact.

The supplied main-menu artwork remains the source image. Ten atmospheric layers
add mist, firelight, green acid glow and intermittent lightning; 24 tiny embers
rise from the four painted fires with independent lifetimes and smooth fades.

Each layer is positioned in normalized artwork coordinates and recalculated
from the same aspect-preserving rectangle as the background. This keeps every
effect aligned when the viewport is letterboxed or pillarboxed. Dedicated unlit
shaders control colour, alpha and continuous mist motion without a flipbook or
additional image assets; layers exist only while the main menu is active.

## Verification

- The production Ogre material/shader parser and render fixture pass 640 checks
  over five requested window sizes and three interface scales; the headless
  desktop clamps larger windows, so this is not native 4K rendering evidence.
- The fixture verifies all 34 layers remain inside the authored image and
  renders a 180-frame motion sequence at 1/60-second simulation steps.
- The actual 1284x781 frames were inspected; sampling only the left mist region
  finds 434 changed pixels between consecutive frames, and 6,408 after one
  second, with much smaller consecutive-frame changes than the one-second
  difference, confirming motion rather than three-frame-per-second holds.
- CTest has no registered tests in this build tree.
- Release compilation and Windows runtime preparation pass after the correction.

The implementation agent did not launch the game. Motion and timing still need
an in-game acceptance check.

Version 0.7.1 is unchanged because this is a correction, not a release;
README wording is updated to include the added embers.
