# Configuring and compiling on Windows

The September 8 room-navigation follow-up makes a room-button right-click fly
the camera to the corresponding owned room and cycle multiple rooms of the same
type in stable map order. The focused room-component probe passes 17 checks,
including ownership, removal, irregular rooms and wooden/stone bridges. Clean
Release compilation and runtime preparation pass. The normal executable is dated
2026-09-08 19:03:04, is 4,490,240 bytes, SHA-256
`C0D0C7FC4D7DEB7AEB3E5EE7FB3DD5C447592A28DBD5CACBA9406E49F83806B0`.
Logs use `build/windows/room-navigation-` and `map-focus-probe-results.log`.
README documents the control; version 0.7.1 remains unchanged because no release
was requested and the project has no changelog. The user accepted the gameplay
result on September 8, 2026.

The final September 8 navigation-label adjustment increases only the category
font from 12 to 13 points using the existing bundled typeface. Release/runtime
preparation, 42,521 installed UI checks and 1,370 combined hand/render checks
pass; the rendered result was inspected. The normal executable is dated
2026-09-08 14:17:17, is 4,485,120 bytes, SHA-256
`7C1371C296F7DD14D329507996E997DFAAF10477FEE36D9163FA309D8F032BB7`.
Build/runtime logs use `build/windows/navigation-tooltip-final-`; the same
navigation-tooltip probes below now verify the 13-point font and its frame.
README remains accurate and no release/version change is needed. The scoped
tooltip task is closed under the user's final small-increase instruction;
no manual game was launched and this does not close the broader roadmap.

The September 8 navigation-tooltip follow-up on `fix/tooltip-hand-occlusion`
uses the existing larger font for the four main HUD category buttons. Tooltip
frames resize with the font, and ordinary targets restore default inheritance.
Release compilation and runtime preparation pass. The normal executable is
dated 2026-09-08 13:52:54, is 4,485,120 bytes, SHA-256
`B7505C8F0652A348AB5399A42F0CA158CB56F33408C90F21ABD4FBAE60432AAD`.
Build/runtime logs: `build/windows/navigation-tooltip-build.log` and
`build/windows/navigation-tooltip-runtime.log`.
The installed UI probe passes 42,521 checks, including all four category fonts,
frame fit, hand exclusion, screen edges and restoring ordinary tooltip fonts
across the existing resolution/scale matrix. The combined real-hand/font render
passes 1,370 checks and was visually inspected. Reproduce with the generators
and matching build scripts named `navigation-tooltip-preview` and
`navigation-tooltip-hand-preview` in `build/windows`.
User visual acceptance remains open; no game was launched. README reflects the
larger category labels; this unreleased correction needs no version bump.

The September 8 pointing-contour follow-up on `fix/tooltip-hand-occlusion`
removes empty mesh-box padding from the tooltip exclusion area while preserving
other hand poses and the existing pointer alignment. It requests software-skinned
positions only while measuring the pointing pose and releases the request before
returning. Release compilation and runtime preparation pass. The normal executable
is dated 2026-09-08 13:44:25, is 4,484,608 bytes, SHA-256
`7163BE0D32D0CDAF8A27BBA000E1ED6A9BC545526C336DE5D80863F50A0892A2`.
Logs: `build/windows/tooltip-contour-build.log` and
`build/windows/tooltip-contour-runtime.log`.
The extracted production contour and installed CEGUI render pass 1,368 checks,
including independent world-view projection under three camera transforms,
five resolutions and three fields of view, temporary-request release and the
previous tip/row/transition checks. The combined rendered preview was inspected.
Generate with `generate-tooltip-hand-combined.py` followed by
`generate-tooltip-contour-verification.py`, then run
`build/windows/build-tooltip-contour-verification.ps1` (generators also live in
`build/windows`). This supersedes the older box-equality oracle for the pointing
pose; the unchanged UI placement retains its previously recorded edge tests.
User comparison of the closer tooltip placement remains open. No game was launched.
README still accurately describes side placement and fallback; this unreleased
correction needs neither a version change nor a new control description.

The September 8 camera-relative tooltip correction on `fix/tooltip-hand-occlusion`
supersedes the initial clearance verification below: actual game captures still
showed overlap because the hand envelope included the overlay's world-camera
transform. Camera-local composition now keeps help to the right of the visible
hand, with screen-edge fallback. The movement handler also uses the correct
CEGUI element-event payload. The accepted list-pointer correction is preserved.
Release compilation and runtime preparation pass. The normal executable is
dated 2026-09-08 13:05:28, is 4,482,048 bytes, SHA-256
`B5D46298A04B7ED72F96B88A484943812F83AF137924E2F10C20838891103040`.
Build/runtime logs use `build/windows/tooltip-camera-`.
The installed UI probe passes 23,621 checks. The real-mesh camera regression
passes 917 checks (150 failed before), comparing all envelope edges against an
independent world-view projection under three camera transforms. The combined
real-hand/CEGUI render passes 918 checks and was visually inspected.
Reproduce with `build/windows/build-tooltip-clearance-preview.ps1`,
`build/windows/build-tooltip-camera-alignment.ps1` and
`build/windows/build-tooltip-hand-combined.ps1`. These are isolated probes;
user gameplay acceptance remains open. No game was launched or stopped.
README describes the placement; no version bump is needed for this unreleased fix.

The September 8 pointing-tip alignment on `fix/pointing-hand-list-alignment`
retains the tooltip-clearance correction below and passes Release compilation
and runtime preparation. The normal executable is dated 2026-09-08 12:47:27,
is 4,482,048 bytes, SHA-256
`06C7BB3807C4E77DA0AAD389D3F571FD29898BF18FE9AD75DFEDA8E3BB165871`.
Build/runtime logs use `build/windows/pointing-tip-`.
The real Ogre mesh/projection audit passes 242 checks across five resolutions,
three vertical fields of view and centre/corner positions: measured distal
fingertip error stays below 0.02 pixel, the same 20-pixel row is identified,
tooltip exclusion still contains the translated tip, six other poses retain
their original origin and the existing transition reaches both correct endpoints.
Run `build/windows/build-pointing-tip-alignment.ps1`; the tip measurement is
derived independently from mesh vertices, not the calibration constant.
The rendered fingertip/cursor-cross preview was inspected after increasing the
fixture camera's far clip to include its cursor plane. These are isolated tests,
not live list interaction or user acceptance. No game was launched or stopped.
README and version remain accurate: this restores existing pointing behavior,
adds no control and is not a release. Only build evidence needs updating.

The September 8 tooltip-clearance correction on `fix/tooltip-hand-occlusion`
passes Release compilation and runtime preparation. The normal executable is
dated 2026-09-08 12:40:26, is 4,481,024 bytes, SHA-256
`5C1A27FEED9A596B7EADA21370886950787B2CFA084E0EA6B90BB4C1E1C99421`.
Logs use `build/windows/tooltip-clearance-`.
The installed Ogre/CEGUI probe passes 23,621 checks, including 2,700 added
screen-bound, hand-envelope clearance and text-preservation assertions across
five resolutions and repeated scale changes. The UI fixture supplies a hand
envelope; a separate real-asset projection check confirms the visible fingertip
lies inside the production projected bounds. The room-label preview was inspected.
The old settings probe required adapting to current action-layout bindings;
its failures were fixture drift, not gameplay failures. No manual game was run.
Reproduction: `build/windows/build-tooltip-clearance-preview.ps1` and
`build/windows/build-hand-tip-audit.ps1`. User appearance acceptance remains open.
README is updated; no version bump is required for this unreleased correction.

The September 8 context-help correction on `fix/context-help-duplication`
retains the complete fork and separates concise pointer labels from detailed
upper-strip descriptions. Release compilation and runtime preparation succeeded.
The normal executable is dated 2026-09-08 12:20:14, is 4,478,976 bytes and has
SHA-256 `8D9BF5846AF6DA15AB1ECE96EB1928314B0B03C680A19822EEC4DCE500834336`.
Logs: `build/windows/context-help-build.log` and
`build/windows/context-help-runtime.log`.

The installed Ogre/CEGUI probe passes 20,921 checks, including all 27 action
labels, preserved descriptions/prices, dynamic worker prices, nonduplicated
dialog help, multiline context normalization and existing scaling/click checks.
Reproduce with `build/windows/build-context-help-preview.ps1`; production cost,
title and context-routing methods are extracted while game services are
simulated. Three rendered `build/reference-audit/context-help-*.png` category
previews were inspected. This does not replace user gameplay acceptance of
dynamic help surfaces. No game was launched; the normal executable is ready.
README usage is updated; no release/version change is required for this fix.
Private reference and acceptance notes remain outside the contribution.

The September 8 action-cost tooltip build on `feature/action-cost-tooltips`
retains the complete fork and adds hover prices to all 27 building, workshop
and spell actions. Release compilation and runtime preparation succeeded.
The normal executable is dated 2026-09-08 11:42:42, is 4,475,392 bytes and has
SHA-256 `B7BB407ADBF91B072BB3A91BEE00D3531DC2111A543B86684DD7E2A956A10B56`.
Logs: `build/windows/action-cost-tooltips-build.log` and
`build/windows/action-cost-tooltips-runtime.log`. Runtime staging was repeated
successfully after the isolated UI probe released its DLLs.

The installed Ogre/CEGUI action-panel probe passes 20,856 checks, including
119 added tooltip checks and the existing scaling/click regressions.
Reproduce with `build/windows/build-action-cost-preview.ps1`; the generator
extracts the production cost formatting and hover-update methods. Price-service
responses and game entities are simulated; spell expectations come from the
existing handlers and configuration. Worker price refresh is checked against
changing helper responses, not a live population simulation.
Three rendered category previews were inspected under
`build/reference-audit/action-cost-*.png`. Parentheses preserve the price in
CEGUI's parsed tooltip text; square brackets were observed to hide it as markup.
The normal executable is ready for user hover testing; no game was launched.
README usage was updated; the version remains unchanged because this is not a
release operation. Private acceptance notes remain outside the contribution.

The hand-price scaling correction is now in the normal executable. After the
previously observed user game exited, the normal Release link and runtime
preparation succeeded at 2026-09-08 11:20:07. The executable
`build/windows/opendungeons-plus.exe` is 4,470,784 bytes, SHA-256
`D73C84E18D066AD281A883B0A2FB7F159F1F4BB45EB974486431E28D65FC25BD`.
Logs: `build/windows/hand-price-scale-final-build.log` and
`build/windows/hand-price-scale-runtime.log`. This supersedes the pending
replacement statement in the historical candidate record below. The assistant
did not launch or terminate the game; final price readability remains user QA.

The September 8 hand-price scaling correction on `feature/hand-price-scaling`
passes 30 focused checks using the installed Ogre text overlay (four failures
before), including scale increases/decreases, unchanged other text, long price
captions and clearing. Before/after renders were inspected. The game retains
the existing 16-pixel design height and applies the action icon's effective
scale; leaving game mode restores the shared text's original height.

The normal Release link could not replace the executable because user game
process 3100 was running, started at 11:15:58. The same generated project was
successfully linked with an alternate target name, without stopping that process:
`build/windows/opendungeons-plus-hand-price-scale.exe`, dated 2026-09-08 11:18:12,
4,470,784 bytes, SHA-256
`293E5DAFAA1DC28269BFB5C157F0440E21AC43071AE6C9DC8DBD10115CBD321A`.
The normal executable still has the 10:58:41 workshop-build hash below and
does not yet include this correction. Replace it only after the game exits;
no DLL/configuration changes are required. Logs use `build/windows/hand-price-scale-`.
The isolated probe does not establish readability against the game world or
complete feedback acceptance; the user's visual retest remains open.

The September 8 workshop action-order build on `feature/workshop-action-order`
retains complete fork `902f240d` and moves the existing wooden-door button before
the traps. The existing installed Ogre/CEGUI action-panel probe passes 20,737
checks at five resolutions and 80/100/120 percent scale; its updated order
expectation failed against the preceding source at check 2,262. The rendered
workshop preview was inspected. These isolated checks use simulated game entities
and command endpoints; final game acceptance remains with the user.
Release compilation and runtime preparation pass. The executable is dated
2026-09-08 10:58:41, is 4,470,272 bytes and has SHA-256
`AF0CF24E2091087703711594E887A80D1A3E14F799894865D0C71B45582AFD6A`.
Logs use `build/windows/workshop-action-order-`; reproduce the interface check
with `build/windows/build-action-panel-preview.ps1`. No game launch or push.

The September 8 idle-terrain context build on `feature/idle-terrain-context`
passes 12 focused context checks (nine failures before), Release compilation and
runtime preparation. It retains complete fork `0eb801e3`, including trap costs
and workshop scheduling, and adds existing terrain names and ownership guidance
to the top context strip without making terrain an actionable hand target.
The executable is dated 2026-09-08 10:42:36, is 4,470,272 bytes and has SHA-256
`77E63E48A4B147512CBDBF9F17511E2D28E6B286C451FA9D9DDAF9F228AD8F25`.
Logs use `build/windows/idle-terrain-`; the generator is
`build/windows/generate-idle-terrain-probe.py`. Tile predicates are simulated in
this focused check; the user still needs to inspect in-game text and hand pose.

The September 8 trap-cost feedback build on `feature/trap-placement-cost-feedback`
passes 141 focused trap/door checks (81 failures before), 496 existing action
checks, Release compilation and runtime preparation. It retains complete fork
`08610de8`, including workshop scheduling, and adds numeric placement costs beside
the hand for traps and doors. The executable is dated 2026-09-08 10:35:28,
is 4,469,760 bytes and has SHA-256
`B7A8170DA48C63779B4CC490642F1C80C9A88B732408D705391BDE974AC73114`.
Logs use `build/windows/trap-cost-`; the focused generator is
`build/windows/generate-trap-cost-probe.py`, reusing the existing action fixture.
These tests simulate world/network inputs and do not establish visual or gameplay
acceptance; the user still needs to check price placement/readability, invalid
targets, GUI entry and cancellation. No game was launched or branch pushed.

The September 8 workshop-order build on `feature/workshop-order-scheduling`
passes 13 focused scheduling/save-block checks, Release compilation and runtime
preparation. The executable is dated 2026-09-08 10:24:53, is 4,469,248 bytes,
and has SHA-256
`96D274A9C8A3ABBC73625440E1067F706423E10FE4ED3AC9E40923370C128219`.
It includes the complete `8f5a80d4` fork and the pending order/save correction;
mixed-type production and save/load gameplay acceptance remain with the user.
See [workshop scheduling](WORKSHOP-ORDER-SCHEDULING.md) for reproduction and
verification limits; the earlier build records below are historical.

The save-request correction adds the two existing optional string fields to
three default-save callers. All 58 focused packet checks pass (six failures
before), as do Release compilation, runtime preparation on retry and the
headless OGRE resource check. The executable is dated September 6 at 23:33:45,
is 4,202,496 bytes and has SHA-256
`a0a0adee1a8dbcb33723839900c3d40316d0e0c6097f89c0a4d89c418e2078a5`.
It retains the complete navigation checkpoint `11949bc2` and earlier fork work.
Logs use `save-request-`; see [save request payload](SAVE-REQUEST-PAYLOAD.md).
The game was not launched; actual saving and loading remain user QA.

The navigation appearance update adds a four-layer circular minimap frame,
reuses the removal symbol for Sell and replaces the text zoom label with a
generated magnifier while preserving all existing controls. The map, overlay,
click-target and camera-dialog probes pass 3,986 checks, and the full interface
matrix passes at five representative resolutions and 80%, 100% and 120% user
scale. Release compilation and runtime preparation pass. The executable is dated
September 6 at 23:05:49, is 4,201,984 bytes and has SHA-256
`a72e1ef155a17c76e0bf517947980480ee1b00aa890e72844cb4b6bca864071e`.
Logs use `navigation-appearance-`; see [navigation appearance](NAVIGATION-APPEARANCE.md).
No game was launched by the assistant. The user already accepted the underlying
map controls; the new frame and symbols still require visual acceptance.

The main-menu camera now preserves its authored horizontal framing across 4:3,
widescreen and ultrawide viewports, and restores the prior gameplay field of view
on exit. All 339 real Ogre camera checks pass, as do the Release build and runtime
preparation. The executable is dated September 6 at 22:50:03, is 4,197,888 bytes
and has SHA-256
`f9ef830a6eeb858db7e4abc667488f27f437a0b1504b60b8db84f3aca10f2350`.
Logs use `main-menu-framing-`; see [main-menu scene framing](MAIN-MENU-FRAMING.md).
No game was launched; user visual acceptance remains pending.

The hand-animation correction also plays the accepted downward strike when
removing digging marks. All 781 release/selection checks pass, with two reproduced
failures before the correction, as do Release/runtime/resource checks. The
executable is dated September 6 at 22:31:33, 4,197,376 bytes, SHA-256
`c41af657e9a8891fdaac306cff05e379a306977123a9d1c476718a43dc7a021d`.
Logs use `hand-unmark-`; see [hand animation](HAND-DIG-ANIMATION.md).
The user accepted marking; the unmarking retest remains pending. No game was launched.

The minimap stacking correction passes all 680 installed-CEGUI click checks
(640 failures before), Release build and runtime preparation. The changed layout
is available through the existing runtime GUI junction; this fix changes no C++
source. The prepared executable is dated September 6 at 22:31:33,
SHA-256 `c41af657e9a8891fdaac306cff05e379a306977123a9d1c476718a43dc7a021d`. Runtime layout
SHA-256: `1080be29fea54a34a428dc9cc9fcc646130a32f9c8931b5955d2427b0c65cd5b`.
Logs: `minimap-layer-build.log` and `minimap-layer-runtime.log`; see
[minimap navigation stacking](MINIMAP-NAVIGATION-LAYER.md).
The complete hand/map fork at `468cb98e` is retained. No game was launched;
the user's click retest and broader navigation appearance work remain open.

The downward hand-strike follow-up passes Release compilation, runtime
preparation, 876 renderer checks, 781 release/selection checks and the headless
resource check. The executable is dated September 6 at 22:21:21, 4,197,376 bytes,
SHA-256 `60a29defc506b4940cb9699d407715c705b7c84596c2af36800a4ca1aab54f17`.
It retains the full map/held-creature fork at `a4d1b0f5` and current local work.
Logs use `hand-dig-` under `build/windows/`; see
[the implementation note](HAND-DIG-ANIMATION.md). No game was launched;
the new strike's gameplay/visual acceptance remains with the user.

The map viewport follow-up draws a thin white camera outline on the minimap
and full map without overwriting terrain colours. All 1,028 viewport checks,
667 direction regressions and 11 composed map/detail checks pass. Release build
and runtime preparation pass in `map-viewport-build.log` and
`map-viewport-runtime.log`. The executable is dated September 6 at 22:12:09,
size 4,195,840 bytes, SHA-256 `8ca8dca9d95822a214036a2dd6825446742e384a912864a671f39624e6c49e61`.
It retains the complete map/held-creature fork at `32c6d4d3`; the shared checkout
and normal Git index are preserved. No game was launched. User gameplay/visual
acceptance and measured reference transitions remain open; see
[map navigation](MAP-NAVIGATION.md).

The map follow-up adds the clipped dotted heart direction at overview zoom and
uses the existing drawn minimap by default, retaining saved renderer preferences.
All 667 image/renderer direction checks and 11 composed map/detail checks pass;
Release build and runtime preparation pass in `map-direction-build.log` and
`map-direction-runtime.log`. The executable is dated September 6 at 21:49:44,
size 4,197,888 bytes, SHA-256 `5c122c3e3adcfa9ceff877a48a96eef2b867173b1355cf8d229b83f6a6ca1649`.
It retains the complete held-creature and portrait-clipping work at `6b248742`.
No game was launched. User gameplay/visual acceptance and measured reference
transitions remain open; see [map navigation](MAP-NAVIGATION.md).

The map-navigation checkpoint adds a full map, pointer detail, immediate map
relocation, minimap zoom and owned-room/fight focus. Release build and runtime
preparation pass in `map-navigation-build.log` and `map-navigation-runtime.log`.
The executable is dated September 6 at 21:33:40, size 4,193,280 bytes,
SHA-256 `3c939f6cc5eb005ee376be4828dc0a5ef149b20b5209330f3790ce9bb5a3fec1`. The installed GUI, map-renderer, camera, culling,
palette and detail-lighting checks pass; see [map navigation](MAP-NAVIGATION.md)
for exact counts and verification boundaries. The shared executable includes
parallel held-creature work, which is excluded from the map contribution.
Direction markers and further navigation acceptance remain open; no game was
launched and user startup/visual acceptance is still required.

The held-creature presentation and separate portrait-clipping correction pass
the Windows Release build and runtime preparation. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 21:30:54,
size 4,193,280 bytes, SHA-256
`26919b405f7cd92a5861d17e28a84f516cddfe5ba35e44d80c36553ecdaabb87`.
It retains the complete camera/hand fork and newer parallel map-navigation work.
All 77 renderer, 3,535 interface and 227 rotation/protocol checks pass, as do
33 portrait renders, twelve grip-layer comparisons and the headless resource
check. Logs use `held-display-` and `held-icon-` under `build/windows/`.
No game was launched; user gameplay acceptance remains open. See
[held-creature display](HELD-CREATURE-DISPLAY.md) and
[portrait clipping](CREATURE-PORTRAIT-CLIPPING.md).

The camera follow-up fixes native wheel units so each notch retains intermediate
zoom levels, and stops inherited gameplay movement before scripted menu shots.
All 540 native and 539 SFML camera/input checks pass, including the 286 camera
regression checks; 118 native checks fail before the wheel fix. Release build
and runtime preparation pass in `camera-wheel-game-build.log` and
`camera-wheel-runtime.log`. The executable is dated September 6 at 20:39:04,
size 4,171,264 bytes, SHA-256 `a7610e0c328461afe32f7584883ce227d781b84cd1fa4ae240cc58435139b1db`.
User gameplay and visual acceptance remain pending; see
[camera controls](CAMERA-CONTROLS.md).

The latest Release build corrects the incompatible virtual-call layouts found
after the user's 20:06 crash: event notices now reach the correct handler in
both game and editor modes. MSVC minimal rebuild is disabled, all 248 translation
units were rebuilt, and both linked-binary dispatch checks pass (the preceding
game-mode check fails). Runtime preparation and the headless shader-resource
checks pass. Logs: `build/windows/windows-incremental-full-build.log`,
`windows-incremental-runtime.log`, `windows-incremental-resources.log` and
`windows-dispatch-{before,after}.log`. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 20:30:04,
size 4,170,752 bytes, SHA-256
`1a19b114ccf0967f42508ce25d6717a4eb49c8e3041baee18246a110dfbd68cc`.
It retains the full hand/camera work and the newer local camera-reset correction.
No game was launched; user startup and gameplay acceptance remain pending. See
[Windows build consistency](WINDOWS-INCREMENTAL-BUILD.md) for the traced cause
and exact verification boundaries.

The preceding Release build adds the camera controls in
[the camera note](CAMERA-CONTROLS.md), retaining the complete room-lighting fork.
Built on September 6 at 20:08:51, its SHA-256 is
`06a56d3703419cfd5a83e5a52be110f6d14ebb093ea715746f175b2f476383ee`.
The Release build, runtime preparation, 278 camera checks, 84 GUI checks,
63 Escape checks and 227 hand-rotation checks pass. Manual gameplay and Linux
remain unverified. Logs use the `camera-controls`, `camera-probe` and
`camera-gui-probe` prefixes in `build/windows/`.

The latest Release executable includes the corrected hand orientation and tool
grip, picker counts and current parallel room/camera work. All 94 focused grip
checks pass with shadows off and on; six rendered layer comparisons verify
finger/shaft occlusion, and 11 other-pose images remain unchanged. The separate
orientation probe passes 39 checks; the earlier picker probe passes 911 checks.
After the parallel task corrected its camera compilation error, Release build
and runtime preparation pass in `build/windows/hand-grip-release-rebuild.log`
and `hand-grip-runtime.log`. The executable at `build/windows/opendungeons-plus.exe`
is dated September 6, 2026 at 20:04:49, size 4,170,752 bytes, SHA-256
`5c0a25e0fdff21d906bcb5e60a6e6c83b5d21513bbb6e74c39b02d2b3218a2ed`.
No game was launched; manual visual acceptance remains with the user. See
[hand orientation](HAND-ORIENTATION.md), [tool grip](HAND-TOOL-GRIP.md) and
[picker counts](CREATURE-PICKER-COUNTS.md) for scope and verification limits.

The preceding Release build adds local lighting to visible rooms and restores
overlapping light contributions and ambient colour on custom world materials.
All 18 focused room-lighting checks, 60 ambient/falloff checks, 73 shadow-receiver
cases, 146 settings checks and the instanced-fog/wall renders pass. Release
compilation and runtime preparation pass in `build/windows/room-lighting-build.log`
and `room-lighting-runtime.log`. The prepared executable is dated September 6,
2026 at 19:38:14, SHA-256
`26b63a78da44873fe3eb27c9dd843bb2305db2084bee434052a7da143ec0b187`.
It retains the complete hand-tool/navigation and shadow baseline. No game was
launched; manual appearance and Linux runtime remain unverified. See
[room lighting](ROOM-LIGHTING.md) for evidence and test boundaries.

The latest Release build adds texture mapping and separate wood/metal materials
to the existing hand tool. All 521 geometry/material checks and six isolated
GL3Plus render views pass; corresponding shadow-on/off images are identical.
Release compilation first used `build/windows/hand-tool-stage` while the user
was playing, then rebuilt the normal executable after the game closed.
Logs: `build/windows/hand-tool-build.log`, `hand-tool-runtime-build.log` and
`hand-tool-runtime.log`. The prepared executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 18:58:11;
SHA-256 `66d0f7d258b88525f892faa59c39fb43cb82314ee96fad54c6c244c72ee5e302`.
It preserves the full navigation/selling/query/hand and parallel shadow baseline.
No game was launched; manual visual acceptance remains open. See
[textured hand tool](HAND-TOOL-MATERIAL.md) for exact verification boundaries.

The preceding Release build requests the existing pointing hand over interface
controls and restores the world pose on exit. All 178 focused controller checks
pass, including 24 previously failing navigation scenarios; Release compilation
and runtime preparation pass in `build/windows/navigation-hand-build.log` and
`navigation-hand-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 18:39:33;
SHA-256 `2590b059ff405e0eba52b6b1d455112933f7481142605824876ac69bd1176226`.
It preserves the complete selling/query/hand and parallel shadow baseline. No
game was launched; visual acceptance remains with the user. See
[navigation hand feedback](NAVIGATION-HAND-FEEDBACK.md) for test boundaries.

The preceding Release build adds a common minimap Sell toggle for the pointed room
tile, trap or door. All 70 focused sale/packet checks, 3,643 installed CEGUI/Ogre
layout checks and 56 creature-query regression checks pass. Release compilation
and runtime preparation pass in `build/windows/contextual-selling-build.log`
and `contextual-selling-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 18:16:46;
SHA-256 `f09479c82a868637aa55a7978fdfdf66fd263036ce3a41d4e7c79090b192ead3`.
It preserves the full creature-query, hand and parallel lighting baseline.
No game was launched. See [selling from the minimap](CONTEXTUAL-SELLING.md) for
the manual check and verification limits; live sale/refund acceptance is open.

The preceding Release build adds selectable creature inspection beside the minimap,
reusing the existing statistics windows. All 56 behavior checks and 3,563 installed
CEGUI/Ogre layout checks pass, as do Release compilation and runtime preparation.
Logs: `build/windows/entity-query-build.log` and `entity-query-runtime.log`.
The executable at `build/windows/opendungeons-plus.exe` is dated September 6, 2026
at 17:57:58; SHA-256
`c28f1b651dad76f4b848440d1b49964350bac75c108b996f8fbf7aa149ac6fb9`.
It preserves the complete hand-rotation and parallel lighting baseline. No game
was launched. See [entity information selection](ENTITY-QUERY.md) for the manual
check, test boundaries and the outstanding trap-range part of this tool.

The preceding Release build fixes held-object spacing after rotation and ensures
that drop requests/replies identify the selected object. All 227 focused checks
pass (164 failures before the correction), as do Release compilation and runtime
preparation. Logs: `build/windows/hand-rotation-build.log` and
`build/windows/hand-rotation-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 17:34:49;
SHA-256 `e5db5cf2eb7d38b077f219c6d20aa3b51e4b79d26a1b1b3e2d345673315462c9`.
It preserves the full event-message, creature-selection and lighting work. No
game was launched. See [the hand-rotation note](HAND-ROTATION.md) for the manual
check and older-endpoint limitation; live gameplay/multiplayer acceptance remains
with the user.

The preceding Release build corrects lost path separators/bracketed names in event
messages, retaining the full creature-selection and lighting baseline. All 504
focused CEGUI rendering checks pass (156 failures before the correction), along
with Release compilation and runtime preparation. Logs:
`build/windows/event-message-paths-build.log` and
`build/windows/event-message-paths-runtime.log`. The prepared executable is
`build/windows/opendungeons-plus.exe`, September 6, 2026 at 17:18:02; SHA-256:
`71000f94b27c1406e4be50193c6b4924be748d5e331c38969ceb83ef6b1363d0`.
No game was launched. See [the display correction](EVENT-MESSAGE-PATHS.md) for
the exact evidence and manual check; this does not certify save/load behavior.

The preceding Release build adds highest/lowest eligible creature selection through
the documented portrait/count shortcuts, preserving the complete dialog/panel
and lighting work. Compilation and runtime preparation pass in
`build/windows/creature-level-selection-build.log` and
`creature-level-selection-runtime.log`. The prepared executable timestamp is
September 6, 2026 at 17:02:57; SHA-256:
`4f3a6b35d625897dcb66662bad4bc9a2aa15636869ab1b64237447e2bdf026dc`.
The real panel probe passes 847 checks, keyboard OIS 21 and SFML 324, and the
production SFML wrapper compiles with the installed SDK. User gameplay acceptance
of these gestures is still pending; no game was launched. See
[the selection note](CREATURE-LEVEL-SELECTION.md).

The subsequent `fix/quit-dialog-layout` correction widens only the exit dialog
and replay checkbox to prevent clipped text. All 260 focused CEGUI checks and
the isolated rendered preview pass. The prepared executable below loads this
XML directly through the verified `build/windows/gui` junction on its next start;
no additional compile is needed. See [the correction note](QUIT-DIALOG-LAYOUT.md).

The completed September 6 cursor-light correction on `fix/shadow-coverage` preserves
ambient illumination inside shadows and applies the existing light falloff to
custom materials. The user's 16:36 captures rejected the earlier solid-black
furniture shadows. All 60 new lighting checks, 73 receiver cases, 146 shadow
toggles and the 33-creature portrait regression pass. Release compilation and
runtime preparation pass at 16:51 in `build/windows/cursor-light-build.log` and
`cursor-light-runtime.log`. The shader/material-only correction loads directly
through the prepared runtime's resource junctions; the executable is still the
16:39:18 build with SHA-256
`141f56e38665bfab44df3741f82cbc46213637978990a4d256f7316129759024`.
The user's 18:18-18:19 screenshots confirm that the solid-black room shadows
are gone; additional instanced-fog and vertical-wall checks also pass.
The user requested local branch closure and a separate room-lighting follow-up;
the exact named-map and Linux verification limits remain recorded in
[shadow coverage](SHADOW-COVERAGE.md), together with the PR update status.

The creature-panel integration now passes the Release build and runtime preparation
in `build/windows/creature-panel-verified-build.log` and
`creature-panel-verified-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` has timestamp September 6, 2026 at 16:39:18
and SHA-256 `141f56e38665bfab44df3741f82cbc46213637978990a4d256f7316129759024`.
It includes portraits, four population views, worker counts, pickup/focus controls,
and the final connection/knockout corrections, alongside the separate shadow
checkpoint `99e80b2d`. The data probe passes 77 checks, state/negotiation 1,117,
and actual Ogre/CEGUI controls/scaling 830. The user accepted the appearance in
earlier 16:22 captures; detailed gameplay/network and remaining visual comparison
are still open. No game was launched by the assistant. See
[the creature panel note](CREATURE-PANEL.md) and AGENTS.md for branch ownership.

The preceding tested creature-panel checkpoint was `3de2e020` on
`feature/creature-panel`, retaining accepted Escape
checkpoint `2d3e79dc` and the subsequent mood/activity prerequisites. Cached
portraits now reuse all 33 existing creature meshes; the isolated Ogre/CEGUI
preview verifies rendering, caching, material isolation and cleanup. Panel
controls are not connected yet. Release compilation and runtime preparation pass
in `build/windows/creature-portrait-build.log` and `creature-portrait-runtime.log`.
The prepared `build/windows/opendungeons-plus.exe` has timestamp September 6,
2026 at 15:43:01 and SHA-256
`cb9421b005d5ca84cc463b73ea8702b33207ce53a71e48278dc641591bc25e40`.
No game was launched. See [the creature panel note](CREATURE-PANEL.md).
During this build checkpoint another session changed the shared checkout to
`fix/shadow-coverage`. The portrait commit was created separately without
switching that checkout; see AGENTS.md before further Git operations.

At the preceding activity checkpoint, full mood and activity transmission were implemented
as prerequisites for the creature-panel views; the views remain incomplete.
The focused packet/negotiation/state probe passes 1,049 checks. The clean Release
build, final incremental build and runtime preparation succeeded in
`build/windows/creature-activity-clean-build.log`, `creature-activity-final-build.log`
and `creature-activity-runtime.log`.
The prepared executable is `build/windows/opendungeons-plus.exe`, timestamp
September 6, 2026 at 15:16:16,
SHA-256 `667e5f70ebe7d9822a67f53b526e8ee02adcf5065c394f2c86cf50be30be806f`.
It retains all accepted Escape and marking corrections. No game was launched;
network/replay runtime acceptance and the broader panel work remain open. See
[the creature panel note](CREATURE-PANEL.md).

The preceding complete fork was `fix/escape-navigation`, continuing directly from
the user-confirmed Options checkpoint `32550ad8`. All 63 focused headless
navigation checks pass (49 failures against the preceding checkpoint).
Windows Release compilation and runtime preparation succeeded in
`build/windows/escape-navigation-build.log` and `escape-navigation-runtime.log`.
The prepared executable SHA-256 is
`53e580c640ffa264e6a4756322cd0bb8dc0d542f3e730d78c5780ee39dc42156`.
Open `build/windows/opendungeons-plus.exe` directly to test Escape in settings,
front-end submenus and game dialogs; see [Escape navigation](ESCAPE-NAVIGATION.md).
On September 6, the user confirmed Escape is fixed and works everywhere;
the separate hand-feedback and visual/display-change checks remain open.

The preceding `fix/options-escape` build continued from pickup-label
checkpoint `9ae03c54`. The focused keyboard/window probe passes all 32 checks;
Release compilation and runtime preparation pass in
`build/windows/options-escape-build.log` and `options-escape-runtime.log`.
The executable SHA-256 is
`991829f9116aff7b7a5bb325ee49b1d193e6a174c46b0cf589ed8ecb7e2b3292`.
Open `build/windows/opendungeons-plus.exe` directly and test F10 followed by
Escape; see [the Options correction](OPTIONS-ESCAPE.md).

The preceding `fix/pickup-target-description` build continued from
wall-outline checkpoint `fcb9714c`. Release compilation and runtime preparation
succeeded in `build/windows/pickup-description-build.log` and
`pickup-description-runtime.log`. The executable SHA-256 is
`3c4989a48148e88f23b4ba2c3a6d1453c5fe3f139d36388c118ef6774ce6e4e8`.
Open `build/windows/opendungeons-plus.exe` directly. The user test of object
descriptions is pending; the user's 13:07 captures show visible wall-hover/drag
outlines, without establishing mark completion or cancellation; see
[pickup target descriptions](PICKUP-TARGET-DESCRIPTION.md).

The preceding `fix/wall-hover-outline` build started from the accepted
HUD checkpoint `c450a6cc`. Release compilation and runtime preparation succeeded
in `build/windows/wall-outline-build.log` and `wall-outline-runtime.log`.
The wall geometry probe passes all 187 checks. Open
`build/windows/opendungeons-plus.exe` directly. The later 13:07 user captures
show visible outlines during hover and dragging; complete gesture and display
change checks remain pending. See [wall hover outline](WALL-HOVER-OUTLINE.md).
That build's executable SHA-256 was
`53dda20bd04dc7548ccb4b8d79237359536dd321801e03bdfcc4d3d41a7e7f5a`.

The preceding `fix/hud-interaction-regressions` build started from
the full hand-feedback checkpoint `c6cbb259`. The September 6 clean Release
build, final incremental build and runtime preparation succeeded. This build
corrects HUD edge scrolling, save/message visibility and square buttons while
retaining all preceding fork features. Logs: `build/windows/hud-regressions-clean-build.log`,
`hud-regressions-final-build.log` and `hud-regressions-runtime.log`.
The CEGUI interaction probe passes 357 checks; the layout/scaling probe reports
zero failures. See [the HUD correction record](../internal/README.md).
Open `build/windows/opendungeons-plus.exe` directly. On September 6, the user
confirmed the reported HUD issues are fixed; see the scoped acceptance record
in the HUD note. No game was launched by the assistant.
The executable SHA-256 is
`09b145a07c1a7eb648e8294b58c6b1cc12ed0ce6f789c43efe5725cff1712462`.

Earlier interface build checkpoints are retained in the [local planning index](../internal/README.md).

For the preserved `feature/action-state-feedback` prototype, the September 6 Release
build and runtime preparation succeeded; see [action feedback](ACTION-STATE-FEEDBACK.md)
for the executable location, headless evidence and the prototype stopped by the
user pending a redesigned plan.

For the completed `feature/live-settings` work, see [LIVE-SETTINGS.md](LIVE-SETTINGS.md)
for its build and runtime evidence. The baseline startup verification below
predates those settings changes.

As of September 5, 2026. The [prerequisites](WINDOWS-DEV-SETUP.md) are installed
and CMake and the Windows x64 game builds in Release and Debug have
completed successfully; the user's startup attempts exposed a resource-path error,
which has been corrected and rebuilt; a subsequent run reached the main-menu scene
and shut down normally, and the user confirmed that Release starts without errors.
The four resolved build errors and their evidence are recorded in
[WINDOWS-BUILD-FIXES.md](WINDOWS-BUILD-FIXES.md).
The startup evidence and subsequent correction are recorded in
[WINDOWS-STARTUP-FIXES.md](WINDOWS-STARTUP-FIXES.md).

## 1. Prepare the PowerShell session

In a new PowerShell console:

```powershell
Set-Location -LiteralPath 'C:\Users\mario\GitHub\OpenDungeonsPlus'
. .\scripts\win32\Enter-OpenDungeonsPlus.ps1
```

The dot at the start loads the compiler and search paths into the same session;
then configure and build in this console. CMake 3.31.8,
Python 3.10.11 and the x64 compiler from Visual Studio 2022 Build Tools are expected.

Some automated shells provide both `PATH` and `Path`. MSBuild then fails before
starting `CL.exe` with `System.ArgumentException: An item with the same key has
already been added`. Normalize the process environment before loading the helper:

```powershell
$taskCurrentPath = $env:Path
[System.Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
[System.Environment]::SetEnvironmentVariable('Path', $taskCurrentPath, 'Process')
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\scripts\win32\Enter-OpenDungeonsPlus.ps1
```

This changes only the current build process. A normal PowerShell console with one
path variable does not need this step.
If needed, check without building:

```powershell
Get-Command cl.exe, cmake.exe, python.exe | Select-Object Name, Source
cmake --version
python --version
```

## 2. Configure CMake

```powershell
& .\scripts\win32\configure-windows-prereqs.ps1
```

The script also loads the environment helper itself and uses:

- Source: project root, derived from the script path.
- Build directory: `build\windows`.
- Generator: `Visual Studio 17 2022`, architecture `x64`.
- `OD_BUILD_TESTING=OFF` and `BUILD_TESTING=OFF`.
- Installation target: `build\windows\install`.
- Python under `C:\Users\mario\AppData\Local\Programs\Python\Python310`:
  `python.exe`, `include`, `libs\python310.lib`, `libs\python310_d.lib`.

The configuration log is replaced on every invocation:
`C:\Users\mario\od-deps\logs\opendungeons-configure.log`.
On errors, the script prints the last lines and aborts.
Reconfigure after changes to CMake files or source lists;
for ordinary changes to existing C++ files, use the existing build.

## 3. Build the game

Release from the same prepared console:

```powershell
cmake --build .\build\windows --config Release --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Release game build failed' }
& .\scripts\win32\prepare-windows-runtime.ps1
```

After changing a class layout in a header, or after an interrupted rebuild, create
the next test executable with a clean build so that no object file can retain the
previous layout:

```powershell
cmake --build .\build\windows --config Release --target opendungeons-plus --clean-first --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Clean Release game build failed' }
& .\scripts\win32\prepare-windows-runtime.ps1
```

Keep the game and its error dialogs closed while preparing the runtime. CMake
can regenerate `resources.cfg` during a build and restore paths that do not exist
in this local Windows installation. Run runtime preparation after the successful
Release build, including a clean build, before handing the executable to the user.
The September 5 GUI-scaling startup failure from this omitted step is recorded in
[startup fixes](WINDOWS-STARTUP-FIXES.md#resource-path-regression-after-the-gui-scaling-clean-build).

For Debug instead:

```powershell
cmake --build .\build\windows --config Debug --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Debug game build failed' }
```

The successfully generated output files are
`build\windows\opendungeons-plus.exe` and `build\windows\opendungeons-plus_d.exe`,
directly in the build directory. Both files were checked for their AMD64 PE signature and
the corresponding Python DLL without starting the game.
The build output appears in the console; if an error occurs, record the first specific
compiler/linker message and the configuration used.
The logged successful verification runs for this setup are located
under `build\windows\game-Release-pass3.log` and `game-Debug-pass3.log`.

## 4. Direct Release startup and manual verification

For the current local setup, double-click
`C:\Users\mario\GitHub\OpenDungeonsPlus\build\windows\opendungeons-plus.exe`
in File Explorer; no PowerShell session is needed to test the Release build.
Keep the executable in that directory with its DLLs, configuration and resource links.
The files have been prepared and checked, and the executable includes the fix for
absolute Windows resource paths. The 14:07 startup logs confirm main-menu scene
loading and normal shutdown without the earlier loading errors; the user then
confirmed an error-free direct startup on September 5, 2026.
That confirmation predates the dynamic-shadow startup failure. The resource
template now also registers OGRE's `Media/Main` in `OgreInternal`, while retaining
its `Graphics` entry for game shader includes; the user's subsequent run reached
the main menu with shadows enabled, as recorded in
[startup fixes](WINDOWS-STARTUP-FIXES.md).
The corrected configuration has been generated beside the executable and passed
the isolated OGRE resource test; no C++ rebuild is needed for this template change.
The user's later Legacy test-map reproduction identified a fragment shader removed
by OGRE's automatic illumination splitting. RenderManager now selects integrated
additive texture shadows, preserving the existing custom shader passes. Release
and Debug rebuilt successfully; the isolated OGRE pass test reproduces the missing
fragment programs with splitting and retains the original pass without it.
The Release executable is ready for the user to retest the same map with shadows
enabled; gameplay and shadow appearance have not yet been verified after this fix.
Build logs: `game-Release-integrated-shadows.log` and
`game-Debug-integrated-shadows.log` under `build/windows`.

The configuration script now calls
[prepare-windows-runtime.ps1](../../scripts/win32/prepare-windows-runtime.ps1).
It copies 20 installed Release library/plugin DLLs and the two Python runtime DLLs
next to the executable, and replaces the generated Unix-style OGRE media paths
with the existing Windows installation's `Media/RTShaderLib`,
`Media/RTShaderLib/GLSL` and `Media/Main` directories.
The missing HLSL, HLSL_Cg and materials subdirectories are not registered.
The other game resource entries and their existing junctions are preserved.

The generated `python310._pth` points to the existing Python installation, its
`Lib` and `DLLs` directories and the executable directory, with `import site` enabled;
Python documents this application-local module path mechanism in
[Finding modules on Windows](https://docs.python.org/3.10/using/windows.html#finding-modules).
This is a local development setup: OGRE media and the Python standard library
still reside outside the repository, and the installed Visual C++ runtime is used.
It is not a standalone distribution package.

If dependencies change or CMake regenerates the resource configuration outside
the configuration script, refresh the prepared files with:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\win32\prepare-windows-runtime.ps1
```

The execution-policy option applies only to that process; it does not change the
system's policy. The setup has already been performed for the current Release executable.

As of September 5, 2026, static checks covered the executable and 22 DLLs,
all four configured OGRE plugins and all 14 resource directories, with no missing
DLL dependencies or incorrect CPU architectures; evidence is stored in
`build\windows\runtime-validation.json`. These checks do not start the game.

Debug still requires the prepared development environment; its direct-start
runtime files have not been staged. An optional console startup from the loaded
environment is:

```powershell
Push-Location -LiteralPath .\build\windows
try {
    & .\opendungeons-plus_d.exe
} finally {
    Pop-Location
}
```

The Debug startup command has not been verified in practice; its generated
`plugins_d.cfg` still names the Release variants of Codec_STBI and RenderSystem_GL3Plus,
so Debug plugin selection needs correction before its startup can be considered ready.
If a startup error occurs, record the actual message for diagnosis.
The user performs manual game tests and visual acceptance.

## Logs and resuming work

- Current installation and verification status: [WINDOWS-DEV-SETUP.md](WINDOWS-DEV-SETUP.md).
- Library logs: `C:\Users\mario\od-deps\logs\<name>-configure.log`,
  `<name>-Release.log`, `<name>-Debug.log`; Boost uses
  `boost-bootstrap.log` and `boost-build.log`.
- Rebuild dependencies only when actually needed, following
  [WINDOWS-PREREQUISITES.md](WINDOWS-PREREQUISITES.md).

`build` is excluded from Git and contains generated files;
`build\windows` also contains directory junctions to project resources.
Take these junctions into account when cleaning up and do not delete source directories through them.
After a new result, add the date, configuration used, error or success
and remaining checks to the Windows status document.
