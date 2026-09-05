# Interface scaling, live settings and camera controls

## Interface scale

The interface combines automatic resolution scaling with a user-selected scale
from 80% through 120% in 10% steps, available on the Video settings page.
Selecting a value previews it immediately; Apply saves it and Cancel restores
the saved value. Resolution and fullscreen changes recalculate the interface
scale without restarting the game.

Window geometry, skin images and hit targets use a 1024 x 768 design area and
the shorter display axis. Fonts retain the existing 800 x 600 reference so that
their text-to-control ratio is preserved. Scaling always starts from the stored
original dimensions, avoiding accumulated rounding drift. Mouse input remains in
display pixels and uses the actual scaled control rectangles.

Font and skin metrics update before window geometry so generated combobox fields
and arrows use the current font size. Formatted label image sizes and tab heights
scale as well. The settings title, tab strip, rows and footer are separated, and
the scrollable pages require the CEGUI clipping patch described in
[Windows development](WINDOWS.md). The two-row room/spell layout incorporates
[PR #29](https://github.com/tomluchowski/OpenDungeonsPlus/pull/29), by Francesco
Bonazzi; the wave portal is also kept inside the room grid at the supported
size/scale limits.

Layouts loaded at GUI initialization are registered automatically. Code that
creates additional controls must register the containing tree after assigning
their areas with `Gui::registerWindowHierarchy`; destroyed windows are removed
from the scaling registry. This includes dynamic renderer options and seat rows.

## Applying settings while playing

Resolution and fullscreen changes resize/restyle the active render window and
refresh the camera, CEGUI display size and input dimensions. The Windows manifest
keeps these dimensions in physical pixels under display scaling. VSync reads its
own checkbox and applies to the active window. Repeated renderer choices are
removed while preserving the selected value.

Creation-time options such as FSAA and framebuffer gamma use a replacement window
after the current input callback finishes. The camera, GUI and input transfer
before the previous active window is hidden; the primary OpenGL context remains
alive. Failures restore the previous window and saved configuration. The
version-specific OGRE patch is required for this path.

Dynamic shadows retain the custom fragment shader passes through integrated
additive texture shadows. The resource template exposes internal shadow programs
in OGRE's internal group while retaining access for game shader includes.

Mouse/keyboard capture changes recreate input devices before the next capture;
minimap selection refreshes the minimap at the next frame. Existing volume,
ambient-light and camera-speed previews are retained. A nickname change updates
the existing player through an optional negotiated message extension; older peers
keep their session nickname and the configured name applies on the next
connection. New message identifiers are appended, and replay playback does not
send nickname-change requests.

The tested Windows installation uses the OGRE-owned GL3Plus window path.
Switching the render backend in process and replacing an SFML-owned window are
not implemented by this work. The installed plugin set offers GL3Plus only.

## Progressive mouse-edge scrolling

The existing outer 2% activation area is retained. With Autoscroll enabled, camera
movement increases linearly towards each screen edge and reaches the configured
pan speed at the edge. Horizontal and vertical intensities combine at corners.
Keyboard movement and the existing Pan Speed setting keep their prior behavior.
Hovering an in-game GUI widget stops edge scrolling, including movement that
started before the pointer entered the widget.

## Issue and pull-request coordination

Reviewed against the original project's default branch on September 6, 2026:

- [Issue #6](https://github.com/tomluchowski/OpenDungeonsPlus/issues/6): addresses
  tiny widgets at high resolutions and the Windows pointer/display mismatch
  after live changes. The issue also reports Linux-specific capture/cursor and
  discoverability problems that this Windows verification does not resolve.
- [Issue #11](https://github.com/tomluchowski/OpenDungeonsPlus/issues/11): improves
  mouse-edge panning precision and prevents movement while using the HUD; this
  does not establish completion of its full camera/character checklist. Adjustable
  keyboard pan speed and centred zoom already landed in
  [PR #40](https://github.com/tomluchowski/OpenDungeonsPlus/pull/40).
- [PR #29](https://github.com/tomluchowski/OpenDungeonsPlus/pull/29): its two-row
  layout is included as a dependency, with the additional scale-related layout
  correction noted above; it must not be treated as newly authored work.
- [PR #21](https://github.com/tomluchowski/OpenDungeonsPlus/pull/21): independently
  overlaps the Windows icon-handle and absolute-resource-path corrections; its
  remaining macOS, CRLF, editor and URL changes are not included here.
- [PR #16](https://github.com/tomluchowski/OpenDungeonsPlus/pull/16): includes the
  same split layout/portability work along with unrelated changes; it is not
  included wholesale.
- [PR #15](https://github.com/tomluchowski/OpenDungeonsPlus/pull/15): the OGRE 14
  port overlaps rendering and settings files, but this contribution retains
  OGRE 13.6.5 and its explicitly supplied patches.
- [PR #41](https://github.com/tomluchowski/OpenDungeonsPlus/pull/41) and
  [PR #45](https://github.com/tomluchowski/OpenDungeonsPlus/pull/45): fog and room
  ownership visuals remain separate; only file-level overlap exists in the render
  manager.

No currently open issue is claimed fully resolved by this contribution, so the
pull request should use related/partial references rather than closing keywords.
The runtime crashes and duplicate renderer choices reported during Windows
development had no separate matching open issue in this repository snapshot.

## Verification

The user accepted the Windows Release behavior and the completed GUI-scaling
step. The recorded automated evidence has these narrower scopes:

- ODPacket tests: two cases, 15 assertions covering legacy and extended packet
  boundaries; this does not simulate a mixed-version multiplayer session.
- Isolated OGRE checks: shadow program lookup and shader-pass preservation;
  GL3Plus replacement-window creation/destruction with separable and monolithic
  shader modes; in-place resize/VSync; fullscreen client/viewport dimensions.
- Isolated CEGUI checks: real settings layout and generated renderer-option rows
  at 800 x 660, 1920 x 1080, 3440 x 1440 and 3840 x 2160 through
  100% -> 120% -> 80% -> 100%; no failed assertions for nested control geometry,
  text heights, dragging, slider/scrollbar tracking and click targets after the
  fixes. The NullRenderer checks do not prove GPU output.
- All 39 CEGUI layout files parse as XML; static outer-bounds checks cover
  representative menus/HUD/dialogs at small, Full HD and 4K sizes with
  80%, 100% and 120% scale.

The local diagnostics were development evidence rather than a new checked-in
test framework. The packet regression remains in `source/tests/test_ODPacket.cpp`.
For further platform testing, open all main-menu pages, HUD tabs, settings pages,
tooltips, Help, Objectives, Skill Tree and exit dialogs at those representative
sizes/scales, including a live resolution change while settings are open.
Check readability, clipping, overlap and clicks near each edge.
