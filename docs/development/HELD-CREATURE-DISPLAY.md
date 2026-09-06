# Held-creature display

Implemented on `feature/held-creature-display`, continuing from the complete
map-navigation checkpoint `6310df83` (retaining camera checkpoint `abc19866`)
and the separate portrait-clipping prerequisite, with newer parallel work
preserved in the shared checkout. Focused checks, Windows Release
compilation and runtime preparation pass; user gameplay acceptance remains open.

## Existing path and required correction

Pickup already inserts the entity at the front of the player's hand; rotation
changes that same list, and drop requests identify the chosen entity. Rendering
previously placed every model beside the hand in six columns. Reuse this ordered
list, the existing hand rig and cached creature portraits; do not create a
second inventory or change pickup eligibility, capacity or network messages.

The correction presents the first held creature between finger and thumb and
represents held creatures with square images in four columns. Other held object
types retain their existing model display. The existing GUI pointing priority,
input guards and one-shot animation durations remain unchanged. The occupied
resting pose samples the existing pickup's thumb/index tracks, while retaining
the other fingers' original resting positions.

The grip renderer must preserve each original entity node's orientation, scale,
children and world attachment rules. Additional held creature nodes can remain
detached from the rendered scene until selected; dropping must restore the
normal world parent and rendering queue. The editor retains its current display.

## Implementation

The renderer attaches the first list entry, when it is a creature, to a wrapper
at the animated index/thumb grip. It preserves the original entity node's
orientation, scale, children and attachment flags; the wrapper supplies the
held-view orientation. Additional creatures remain in an unattached storage
node until selected. Pickup, rotation, dropping and mode exit reuse the existing
ordered list and restore the existing world or editor display.

Each held creature has a square image in list order, with four columns and
32 design pixels per cell. Images share the existing cached portrait texture
through a square crop. Dynamic cells follow the existing hand-interface scale,
pass mouse input through, and clear the action/prohibition icon area. Surplus
cells are hidden, and mode teardown destroys the windows. There is no new
inventory limit, pickup rule, packet or dependency.

An interleaved portrait/interface render exposed a pre-existing scissor-state
leak; [the separate portrait correction](CREATURE-PORTRAIT-CLIPPING.md) resets
that state before rendering each portrait.

## Verification

- The source-derived real Ogre lifecycle probe passes 77 checks: selection,
  rotation, hidden-hand transitions, GUI pointing priority, drop transforms and
  culling flags, storage/grip destruction, mixed objects and editor restoration.
- The installed CEGUI layout probe passes 3,535 checks across 800x600, 1920x1080
  and 3440x1440 at 80%, 100% and 120% interface scale, with 0, 1, 2, 4, 5, 6 and
  13 held creatures. It verifies square cells, ordering, rows and input passthrough.
- The existing rotation/drop protocol regression passes 227 checks. Domain
  fixtures exercise the production methods; this is not a live multiplayer run.
- The actual GPU portrait probe passes all 33 configured meshes, including
  cached square-image drawing between portrait renders.
- Twelve combined/hand/creature layer comparisons across four meshes and three
  scales pass: fingers obscure 78 to 562 overlapping creature pixels. Selected
  rendered images were visually inspected; this is isolated asset verification.

Logs use `held-display-probe-current`, `held-display-ui-probe-results`,
`held-display-rotation-probe-results`, `held-display-image-results` and
`held-icon-preview-results` under `build/windows/`. Rendered layers use
`build/reference-audit/held-display-*`. The Release build, runtime preparation
and resource checks pass in `held-display-release-build.log`,
`held-display-runtime.log` and `held-display-resources.log`. The executable's
timestamp and hash are recorded in [BUILDING.md](BUILDING.md); it also retains
newer parallel camera/map work. The assistant did not launch the game.

## Remaining acceptance

The user should check pickup from the world and creature panel, several held
types, order rotation and dropping, movement over navigation, and leaving a game.
Live multiplayer, fullscreen transitions and the full visual comparison remain
unverified. Icon artwork uses the existing cropped portraits; exact offsets and
every species' grip have not been individually accepted. The additional suggested
wall-click swing is a separate follow-up and is not part of this display change.

Version remains 0.7.1 because no release was requested. README now describes the
held-creature presentation; no changelog exists. Public documentation uses
neutral functional descriptions, and detailed comparisons remain internal.
