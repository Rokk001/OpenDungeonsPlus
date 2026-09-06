# Camera controls

## Existing path and scope

The implementation starts from the complete fork's room-lighting checkpoint
`0c7d6234`, on the separate `fix/camera-controls` branch. The shared checkout
and normal Git index remain untouched by branch assembly.

GameMode routes keyboard and pointer events to CameraManager. The existing
camera already keeps wheel zoom centred on the ground target, clamps that
target to the map and prevents stalled minimap flights. These changes also
cover the corresponding camera commits reviewed in upstream PR 16; reuse
them. Progressive edge scrolling and the live pan-speed setting already exist.

The remaining gaps are the default shortcuts, three persistent user views and
their menu-based editing, held-key zoom, modifier transitions, top-down pan
orientation, and movement depending on frame rate or OS key repeat. F1-F5
currently open help, player information, objectives, research and save; those
actions remain in Options when F1-F6 select camera views. The user approved
the reference bindings taking precedence on September 6, 2026. Detailed
reference evidence stays in the private planning area.

Extend the existing camera, input and configuration paths. User camera angles
use the existing Input section of the user configuration and its save routine;
they do not store map positions. Preserve the existing numbered bookmarks,
wheel/hand rotation, GUI input ownership, map bounds and centred zoom.
Full-map navigation and minimap zoom belong to a subsequent functional branch.

Exact original timing and numerical camera parameters have not been measured;
retain the fork's existing view angles and bounds, and express its nominal
60 Hz pan speed in elapsed time. Manual comparison remains required.

## Verification

The shared CameraManager now accepts continuous pan/zoom/swivel input and
separate pointer distances. Game input is sampled once in ModeManager's update
after device capture; the existing frame-start callbacks also run during the
render callback, so using them for angular integration would apply it twice.
The attached camera's child transform is refreshed before ground projection,
avoiding a one-frame offset after rotation. Presets retain their ground target.

F1-F3 select isometric, top-down and oblique views; F4-F6 recall three user
orientations. Options contains Define user cameras, slot selection and Store.
While that panel is open, Ctrl+Insert/Delete, Ctrl+Page Up/Down and Ctrl+Home/End
adjust roll, yaw and pitch. Normal play supports arrow panning, Shift acceleration,
Home/End and Ctrl+Up/Down zoom, Delete/Page Down and Ctrl+Left/Right rotation,
X+horizontal pointer rotation, and Z+vertical pointer zoom. Existing WASD/Q/E,
middle-button orbit, V view cycling and numbered bookmarks remain available.
H shares the existing dungeon-heart focus action with T.

On September 6, 2026, the Windows Release build and runtime preparation pass.
The executable was built at 20:08:51. No manual game test was run.

- 278 focused checks use the production camera methods and binding resolver
  with real Ogre camera/scene nodes. They cover held/modifier/opposing keys,
  zero-pitch and rotated panning, wheel and held zoom, rotation/preset ground
  anchors, user-view serialization and map-bound flight. At 30/60/144 Hz,
  two-second pan distances differ by less than 2%; Shift doubles them.
- 84 real CEGUI checks cover dialog/chat/console/focus blocking, three slot
  callbacks, failed Store feedback, closing, and four resolutions at three
  live GUI scales. Configuration I/O is adapted in these isolated probes;
  saving uses the existing production ConfigManager routine in the game.
- All 63 existing Escape/navigation checks pass.

Evidence: `build/windows/camera-probe-results.log`,
`camera-gui-probe-results.log`, `escape-navigation-probe-results.log`,
`camera-controls-build.log` and `camera-controls-runtime.log`.
Manual gameplay/reference comparison and Linux remain unverified.
