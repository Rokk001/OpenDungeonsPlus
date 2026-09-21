# Crypt corpse presentation

September 21: the user accepted the lying pose, but rejected the missing visible
decomposition and flies; pose acceptance does not cover that remaining effect.

The actual client update advances the decay animation, and an isolated hidden
Ogre render confirms eight live particles and root scales 1, 0.91 and 0.82 at
the start, middle and end. The gap is presentation: the corpse keeps its intact
texture and only shrinks 18%, while 0.025-unit dark flare particles are barely
visible at dungeon-camera scale. This reproduces the weak presentation without
running the game. Extend the existing decay state with per-corpse mottling and
gradual surface breakup plus readable winged flies, preserving the accepted
pose, living-creature materials, transport cleanup and server economy.

The correction now passes 12,595 production pose/delivery/particle checks and
24 installed-OpenGL render/cleanup checks, including 746 visible fly pixels,
changing swarm images, three distinct surface stages, unchanged shared living
materials, restoration of original appearance and removal of private materials
and particle systems. An early preview read the previous front buffer; the
fixture now reads the just-rendered back buffer and measures pixels, not merely
particle counts. The current preview was inspected without launching the game.

The clean Windows Release build passed (header layout changed); logs are
`build/review-followups/crypt-visible-build.log`, `crypt-visible-render.log` and
`crypt-visible-decay.log`. The new executable is built but deployment is waiting
for the user to close the game; do not mark it ready in the normal start file.
The original pose and 18% skeletal settling remain unchanged. The visible
material effect follows the existing base-duration animation; research still
controls removal independently, so it can remove an already visibly decaying
corpse before the base-duration surface breakup finishes.

September 21 verification follow-up: the previously execution-blocked fixture
now starts but stops while creating its first entity because its headless setup
never initialized the material manager. The game performs that initialization
through renderer startup; this is a fixture error, not evidence of a game crash.
Initialize the same default materials before creating test entities, following
the existing isolated asset probes; do not alter corpse behavior or assertions.
The particle manager also needed its normal billboard-factory initialization.
Once initialization succeeded, the angular quaternion comparison reported 711
failures even for quaternions compared with themselves: float dot-product
rounding was amplified by acos. Compare quaternion components up to sign with
squared error at most 1e-10 instead, retaining a negative control that rejects
a genuine 0.001-radian difference. No production code or asset was changed.

The final September 21 run passes all 12,584 checks, including all configured
creature meshes, delivery/interruption, removal, final skeletal poses, settling,
animation reuse and the actual fly particle script. This supersedes the blocked
fixture status below; visual game acceptance remains with the user.

The crypt accepts only dead creatures and starts a server-side rotting counter
after transport, but never requests a lying/decay animation at that transition.
The client release handler only reattaches the scene node and changes position;
it does not establish a final corpse pose. Mesh creation defaults to Idle, while
animation restoration depends on the transported entity's prior state.

Request a dedicated decay state on successful crypt placement, reusing the
existing animation packet and final death/drop poses, including meshes with no
usable death pose. Add slow corpse settling and an animated fly swarm; neither
room capacity, decay reward, vampire spawning nor research timing changes.
Removing a crypt spot returns the corpse to its ordinary death state and removes
the decay presentation. Destruction, pickup and animation replacement clean up
the swarm. Existing save behaviour (corpses are collected again) is retained.

The server animation is updated explicitly: `clearDestinations` alone only sends
the requested end state to existing clients. Visibility restoration applies the
heading before the corpse tilt and preserves its ground height when position is
restored. The effect follows position updates and is removed on pickup as well.

The settling animation uses the base configured decay duration; research still
controls the server's actual corpse-removal time without changing its rewards.

Initial September 20 validation: the focused production-code fixture compiles, but Windows application
control blocks its executable with error 4551 before any checks run. Consequently
there is no runtime or visual pass. The fixture covers crypt delivery/interruption,
spot removal, every configured skeleton's final pose and settling keys, shared
animation reuse and particle-template parsing. Game appearance remains for the
user to test after deployment; release compilation is recorded separately below.

Windows Release compilation passed on September 20 in `build/review-followups`
(`crypt-final-build.log`). The complete implementation has since been deployed
in the normal executable recorded at the top of BUILDING.md; the September 21
test-only correction requires no game rebuild or redeployment.

This is a local feature, not a release: the development index is updated without
a version bump or release changelog entry; the top-level README needs no change.
