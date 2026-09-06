# Hand model orientation

## Evidence and correction scope

The September 6 user captures at 19:17 and 19:19 show the pointing hand with
its forearm almost vertical beneath the pointer. The user reported the wrist
as twisted and requested correction. The existing keeper-hand mesh attaches
directly to the cursor-position node, with its authored upright orientation;
there is no presentation rotation between the mesh and that node.

Give the model its own child node, turn it 65 degrees in the screen plane and
tilt it 35 degrees around its longitudinal axis, bringing the wrist in from
the lower right and giving the hand the requested rightward depth inclination.
The user's clarification explicitly requires this spatial tilt; a rotation
within the screen plane alone is insufficient. Preserve the
cursor-position node, its origin, scale and visibility handling. The tool stays
attached to the hand bone and follows the model. Held objects remain children
of the original cursor node, so their positions and drop order do not rotate.
This uses a rotation, not a mirror, and does not alter the mesh, skinning, finger
poses, animation clips, timing, hit testing or input handling.

Work branch: `fix/hand-orientation`, based on picker correction `505cbf97` and
the preceding full fork. Unrelated concurrent lighting edits in RenderManager
belong to their own task and must not be staged in this correction.

## Verification

An isolated render comparison uses the current asset and pose-generation code;
the initial harness was corrected to advance Ogre's rendering-queued frame
event so consecutive images actually update skinned vertices. Before/after
rendering covers Idle, Point, Dig and three samples each of Pickup, Drop and
Slap. All 39 coordinate/visibility/handedness checks pass; the same probe fails
two orientation checks against the preceding attachment. Model rotation does
not change the 48 sampled bone transforms or held-object placement.

Logs are `build/windows/hand-orientation-preview-{before,current}.log` and
`hand-orientation-final-build.log`. Release compilation and runtime preparation
pass; the executable was rebuilt on September 6 at 19:52:53. The new user
captures at 19:46 predate this depth-tilt build and separately demonstrate the
incorrect tool grip, which requires its own correction. The assistant did not
launch the game; exact visual matching and user acceptance remain unverified.

Version remains 0.7.1; no release was requested. README describes the same hand
controls and no changelog exists; this task note records the visual correction.
