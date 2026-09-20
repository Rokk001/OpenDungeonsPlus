# Configuring and compiling on Windows

## Depleted health segments: September 20 asset update

Missing health now leaves transparent gaps instead of dark segments and borders.
The normal build reads the regenerated textures through its existing materials
junction; restart the game to reload them. The executable below is unchanged.
The focused asset regression passes 200 checks (96 failures before), and the
hidden-window OGRE overlay probe passes 234 checks; its colour/state matrix was
inspected. No game was launched; user visual acceptance remains pending.
See [health indicator transparency](CREATURE-HEALTH-AND-NEEDS.md).

## Hammer head-axis correction: current September 20 executable

The normal Release executable aligns the hammer's actual striking-face axis
with the pickaxe while retaining left-end pointer alignment and strike motion:
September 20 10:48:12 Europe/Warsaw, 4,873,728 bytes, SHA-256
`42494EF1450B2E9EF3F086C8A1B30960ED1B72C3099B0589AF702B0D88641C5C`.
All 4,189 real-asset checks, Release compilation, runtime preparation and 32
resource checks pass; staged and normal executable hashes match.
No game was launched by the assistant; the user accepted the hammer angle and
preceding yo-yo correction on September 20 and confirmed the overall goal complete.
See [hammer correction](CONSTRUCTION-HAMMER.md).

## Yo-yo finger pull: current September 20 executable

The normal Release executable adds synchronized finger flex/release to all three
yo-yo cycles without changing the accepted wrist angle or tool cursor hotspots:
September 20 09:29:35 Europe/Warsaw, 4,873,728 bytes, SHA-256
`07125307B5F0DEC495101EF0AF23E708E54A3B086DE56676410D2D53B0DA2D91`.
All 4,026 real-asset checks, Release compilation, runtime preparation and 32
resource checks pass; no game was launched. See [yo-yo follow-up](IDLE-HAND-ANIMATION.md).
The user accepted the preceding left tool cursor correction; yo-yo retest is pending.

## Left tool-end cursors: current September 20 executable

Both hammer and pickaxe now align their ready-pose left striking end with the
mouse pointer, preserving accepted angles and strikes: September 20 09:16:01
Europe/Warsaw, 4,872,704 bytes, SHA-256
`FA118F4310C661BBE1CC2E27794FD1D544D1E0972C3C9A1D043E47F03B716853`.
All 4,020 real-asset checks, Release compilation, runtime preparation and 32
resource checks pass. The normal executable is updated; no game was launched.
See [tool cursor alignment](CONSTRUCTION-HAMMER.md); user retest is pending.

## Empty-hand angle for idle effects: current September 20 executable

The normal Release executable now retains the empty-hand angle during both
watch and yo-yo effects, including the separate hammer-impact alignment below:
September 20 08:38:12 Europe/Warsaw, 4,871,680 bytes, SHA-256
`8474DC7A481512096AB6CD3A7C9FB990449FCB9092BBADA1BF06A942286AA1CD`.
Normal and staged hashes match; 3,690 real-asset checks, Release compilation,
runtime preparation and 32 resource checks pass.
See [idle-hand angle](IDLE-HAND-ANIMATION.md) and [hammer contact](CONSTRUCTION-HAMMER.md).
The game was closed during deployment; no game was launched and both corrections
await user visual acceptance.

## Construction impact alignment: current September 20 executable

The normal Release executable preserves the accepted hammer angle and movement
while aligning its actual impact with the selected pointer: September 20 08:30:00
Europe/Warsaw, 4,872,192 bytes, SHA-256
`D8EB7D35D25F54B44B102554652D3AD882164FFF12B75F918EDCBA0F9722C65E`.
All 3,668 real-asset checks, Release compilation, runtime preparation and 32
resource checks pass; see [construction hammer](CONSTRUCTION-HAMMER.md).
The game was closed during deployment; no game was launched and user retest
of the selected field remains pending.

## Shared digging/construction strike: current September 20 executable

The normal and staged Release executables now give the hammer the same hand movement,
duration and tool orientation as digging: September 20 02:38:45, 4,872,192 bytes,
SHA-256 `19A4241D70D4BFC9ABDC17A119D0D2B4BBEE2E7D89233B7E44012516594FE630`.
Compilation and 3,454 real-asset renderer checks pass; the separate input fixture
was blocked by Windows before execution. See [construction strike](CONSTRUCTION-HAMMER.md).
After the game closed, deployment and runtime preparation succeeded; both
executables match the hash above and all 32 normal-runtime resource checks pass.
The September 20 02:38:53/56/58 screenshots predate this deployment; at intake
the normal executable still had the rejected September 19 21:21 hash below.
No game was launched or stopped; user visual acceptance is pending.

## Left-facing construction strike: current September 19 executable

The normal and staged Release executables correct the hammer to strike left with its flat
face: September 19 21:21:00, 4,874,752 bytes, SHA-256
`0FACCAAE930C88DDE6F9C7662B850CAD74FC7AE05B383C7696A5E741630E1288`.
Compilation and 434 real hand/asset checks pass; 32 normal-runtime resource
checks also pass. See [construction strike](CONSTRUCTION-HAMMER.md).
After the user closed the game, deployment and runtime preparation succeeded;
the normal executable now matches the staged hash above, superseding the
rejected forward-pitch build below. No game was launched or stopped; visual
acceptance awaits the user's retest.

## Forward construction strike: current September 19 executable

The normal executable includes the corrected forward hammer pitch and approach,
while retaining the user's accepted fork features: September 19 21:11:36,
4,874,752 bytes, SHA-256
`F210CC584F9C943946FB98E9A7148D0AA191E1B751712FAC0E921F16DED5AD3A`.
It matches the staged Release build. Compilation, runtime preparation and 32
resource checks pass; the real hand/asset fixture passes 418 checks, including
the impact-direction assertion that failed before correction. Settled rendered
previews were inspected; see [construction strike](CONSTRUCTION-HAMMER.md).
The game was closed during deployment and was not launched by the agent;
user acceptance of this direction correction remains pending.

## Idle hand effects: current September 19 executable

The normal executable now includes interruptible, randomly selected watch/yo-yo
effects after thirty seconds without input, retaining all previous fork work.
It matches the staged executable: September 19 20:58:18, 4,874,752 bytes, SHA-256
`837A0A66FCBA05B1CAE09FF490D8628C580BD913CA9F0F2A8C5E8E073AA0D82F`.
A clean Release build in `build/review-followups`, a subsequent up-to-date build
and normal runtime preparation succeed. Timer/input checks pass 2,125, real hand
rendering 415, menu restoration 100, Alt 128, construction input 560 and resource
generation 32. See [idle effects](IDLE-HAND-ANIMATION.md) for coverage and manual
acceptance. The game was closed during deployment; no game session was started.

## Pickaxe screenshot follow-up: current September 19 executable

The normal executable matches `build/review-followups/opendungeons-plus.exe`:
September 19 20:28:25, 4,859,904 bytes, SHA-256
`0756E281C9572A739478F2AEBEFB903E4C0795801CCEE7F834D1C2256FA40326`.
It retains the hammer strike, Alt toggle and dormitory resource corrections,
and includes the revised pickaxe shaft roll. Release compilation and runtime
preparation pass; the corrected real-model fixture passes 280 checks, Alt input
128 and generated resources 32. The orientation preview was inspected; game
acceptance remains with the user. The hash supersedes older entries below;
file timestamps alone do not establish build ordering on this machine.

## Dormitory floor resources: September 19 follow-up

The normal runtime's existing source junctions now provide corrected carpet and
border materials for all dormitory layouts. The actual Ogre mesh/material/shader
fixture passes 96 checks over sixteen neighbour masks, with full-pipeline
previews; see [floor continuity](DORMITORY-FLOOR-BORDER.md). Restart the game to
reload the resources; no C++ rebuild is needed, and the executable metadata
below is unchanged. User visual acceptance remains pending.

## Construction strike and Alt toggle: normal September 19 executable

The normal executable is September 19 20:58:12, 4,859,904 bytes, SHA-256
`FC8115365FAC3471C011237608D8AA517E339D380464954164E4A34FEBD7DFF0`.
It includes the separate Alt-toggle correction and pointer-aligned construction
strike. Release compilation, runtime preparation and 32 resource checks pass;
hammer rendering/input fixtures pass 838 checks and Alt input/lifetime 128.
The game was closed at deployment and was not launched by the agent; user
gameplay/visual acceptance remains pending. The earlier staged-only restriction
below is superseded by this deployment. Continue using the current staged build
tree, not stale objects in the normal tree.

## Alt-toggle correction: staged September 19 executable

Release compilation succeeds in `build/review-followups`: September 19 19:36:22,
4,855,296 bytes; the production input/lifetime fixture passes 128 checks.
The user explicitly clarified press-to-toggle rather than hold-to-show.
The game was running at deployment, so the normal executable was not replaced;
close the game before copying and preparing this staged executable for retest.
No game was launched or stopped by the agent, and no version or protocol changed.

## Food-lane search follow-up: normal September 19 executable

The normal executable contains the food-lane search correction, construction
hammer, pickaxe alignment and hold-Alt indicators: September 19 18:59:47,
4,855,296 bytes, SHA-256
`FDC2F21F750614AC4590603A164A54FF31C63E5809B9D5C85A0B62285AC25BB6`.
Release compilation, runtime preparation and 32 resource checks pass. Navigation
passes 6,751 room/layout, 7,277 path and 5,205 saved-food checks; the full packed
suite still has 140 known large-body failures among 7,315 checks. Saved-food
search reaches 336/382 targets, worst 78.594 ms, total 5,286.78 ms; aggregate
cost remains above the earlier 297-target baseline, so gameplay responsiveness
is not claimed fixed. See [navigation evidence](ROOM-OBJECT-NAVIGATION.md).
The game was closed during deployment and was not launched by the agent.
User gameplay acceptance and the large-body passage decision remain pending.
Continue incremental builds in `build/review-followups`, or clean-build the
normal tree before reusing its older object files.

## Hold-Alt indicators: normal September 19 executable

The normal executable includes hold-Alt health/needs visibility and all earlier
fork work: September 19 18:07:39, 4,854,272 bytes, SHA-256
`CD65DC8235ACF5E33C44140B34E2994B8D1F227954871677A01FE3963ED24103`.
Release compilation, normal runtime preparation, 70 production lifetime/modifier
checks (both input backends), 32 resource checks and eight compiler-flag checks
pass. The game was closed during deployment and was not launched by the agent;
user gameplay acceptance is pending. Incremental work continues in the staged
build tree; clean-build the normal tree before reusing its older object files.

## Pickaxe alignment: normal September 19 executable

Release compilation, normal runtime preparation and 32 resource checks pass.
The executable is September 19 17:49:15, 4,854,272 bytes, SHA-256
`404F344FB79BA27AEFB6FDA67CCFDA704E8B6671B93E96DA72E9BAAAAE421FE2`.
It retains the construction hammer and food-lane corrections. The blade roll
passes 124 real-model/controller checks; user visual acceptance remains pending.
The build-tree and old-object precautions below still apply.

## Construction hammer and food lanes: normal September 19 executable

The normal `build/windows/opendungeons-plus.exe` now contains the separate
construction hammer and food-lane corrections: September 19 17:27:35,
4,853,760 bytes, SHA-256
`ABAFA35691BDCD04F6034F50F0A38C3977C34C6B6D38BD3987A531E2D7A12E62`.
It was built in the fresh `build/review-followups` build tree and copied while
the game was closed; runtime preparation succeeds. The old executable is kept
as `build/review-followups/previous-normal-20260919.exe`. No game was launched.
Use the staged build tree for subsequent incremental builds, or clean-build the
normal tree before using its old object files with the changed renderer layout.
The hammer passes 121 real-Ogre/controller checks; gameplay acceptance remains
with the user and the separate large-body bed passages are still unresolved.

## Food approaches through bed lanes: staged September 19 build

The separate `build/review-followups/opendungeons-plus.exe` compiles successfully:
September 19 17:13:13, 4,853,760 bytes, SHA-256
`8250829F818901B998794D84BB81003028B1CD48C051C1CEBCFC774DC050122C`.
It includes the preserved in-progress hand changes and the food approach fix;
it is not yet staged into the normal runtime or gameplay-tested. The normal
executable below is unchanged. The four reproduced food-lane failures are gone;
room/layout regression passes 6,751 and path geometry 7,270 checks. The separate
140 packed large-body failures remain open; see [navigation](ROOM-OBJECT-NAVIGATION.md).

## Food-route low-nest fallback: current binary and verification limit

Inspection on September 19 identifies the existing normal executable
`build/windows/opendungeons-plus.exe` as the September 14 00:54:09 build,
4,850,688 bytes, SHA-256
`DA857D8D84206FB303A20FC2AF95CBF9ACE322C14052CBDCA326A3C6A416B01E`.
The existing `bed-lanes-normal-build.log` records compilation of
`RoomObjectNavigation.cpp` and linking of this executable; the matching runtime
log records successful preparation. This supersedes the 00:40:50 binary below.

The uncommitted follow-up lets a food route use the existing low-nest crossing
permission when ground transit fails, without relaxing its interaction endpoint
or higher-bed collision. A September 19 rerun of the isolated room-layout and
benchmark test compiled, but Windows Code Integrity blocked its executable
before any assertions ran (WinError 4551, events 3033/3077). An approved execution
retry produced the same rejection. No policy was changed or game launched;
renewed test execution, the remaining packed-room failures and user gameplay
acceptance remain unresolved. See [navigation evidence](ROOM-OBJECT-NAVIGATION.md).

## Visible traversal over low nests

The normal `build/windows/opendungeons-plus.exe` is rebuilt and prepared:
2026-09-14 00:40:50, 4,849,152 bytes, SHA-256
`A451A4C3E843A8995D01887BEBE41048C9E44518CB1E1C0ECEBEFE68C7ADCE70`.
Creatures with feet too wide for the low nest's lane can visibly rise over it,
using their native Walk pose; ground routes remain preferred when less costly.
Server route validation and client elevation share the measured footprint and
minimum body height. Higher bed parts remain solid, and the accepted 70% sizing
and combat appearance/launch correction are preserved.
Release/runtime preparation and the new step geometry/lifecycle probe pass,
along with 39,699 native-pose, 10,136 existing renderer, 6,727 room-routing and
7,270 path checks. Eight more packed passages pass; 140 of 5,301 remain failing.
The native preview was inspected; full-game stepping and responsiveness still
require the user's retest. No game was launched/stopped or save/network version
changed. See [navigation scope and timing evidence](ROOM-OBJECT-NAVIGATION.md).

## Height-aware clearance beside low nests

The normal `build/windows/opendungeons-plus.exe` is rebuilt and prepared:
2026-09-14 00:17:30, 4,841,472 bytes, SHA-256
`86EA5A1D2F91D6B7CC5ABC3275AA06118ADB7B76DEE01DCE58429EB7501A9B98`.
Low-nest collision uses measured body triangles below the entire object instead
of projecting upper-body overhang into the walkway. Raised/taller objects retain
full-body collision; bed size and accepted combat presentation are unchanged.
Actual-mesh animation checks pass 39,699, furniture geometry 1,636, path geometry
7,270, room routing/benchmark 6,727 and saved-map fixtures 5,145. Eight previously
blocked packed-room cases now pass; 148 of 5,293 remain failing. Visible stepping
over higher bed parts and live navigation acceptance remain open.
Release compilation/runtime preparation, resource generation and Release flags
pass; no game was launched/stopped and no version or save/network format changed.
See [navigation evidence](ROOM-OBJECT-NAVIGATION.md).

## Usable strips between corner beds

The normal `build/windows/opendungeons-plus.exe` is rebuilt and prepared:
2026-09-13 23:59:51, 4,838,912 bytes, SHA-256
`45C078B5AED387496426A09F97A758DFBFE30546832D1CB1B6D91457AC776090`.
Navigation compares existing aligned routes instead of accepting an outside
detour immediately and refines once to the real endpoint. The accepted 70% beds
and immediate projectile visibility are preserved. Geometry passes 7,270 checks
and room-layout routing 6,673; packed large-body passage still fails 156 of 5,253
checks and requires the authorized visible low-bed stepping follow-up.
Release compilation/runtime preparation pass; no game was launched or stopped.
Live movement acceptance remains open. No version or save/network format change.
See [navigation evidence and timing limits](ROOM-OBJECT-NAVIGATION.md).

## Immediate missile visibility at the caster

The normal `build/windows/opendungeons-plus.exe` is rebuilt and prepared:
2026-09-13 23:38:07, 4,837,376 bytes, SHA-256
`A40BBBA85F5ACA22CF09B97A8AA90ECD50EF04D9D76E69BE786309A4543CA9BE`.
New creature missiles are now announced to the launch tile's visible players
before their first flight path, at the caster's actual XY position, rather than
after movement in the following server turn. The user-accepted fireball
appearance, arrow visibility, combat facing and 70% beds remain unchanged.

Release compilation/runtime preparation and 17 production launch/vision checks
pass (four failures before), together with 75 missile-collision, 180 fireball GPU
and 19 attack-dispatch checks. The client-visible launch timing remains for user
retest; no game was launched or stopped by the agent. No version, packet/save
format or additional README change is required. See [combat feedback](CREATURE-COMBAT-FEEDBACK.md).

## Fireballs, readable arrows and combat-facing correction

The normal `build/windows/opendungeons-plus.exe` is rebuilt and prepared after
the user closed the game: 2026-09-13 23:29:21, 4,837,376 bytes, SHA-256
`215E882C27CD61B854FA98236EEE3D596E983700BF944B67B89BF315E90D79F4`.
This retains the 70% corner beds and movement fixes, and adds the combat-facing
ordering correction, actual creature target positions, visible arrow shafts
and the warm fireball shader/trail. Release compilation and runtime preparation
pass; no game was launched or stopped by the agent.

Focused checks pass: arrival facing 82 (eight failed before), attack dispatch
19, fireball GPU frames at the configured flight speed 180, arrow GPU directions
eight (four failed before), missile collision 75, real-model renderer 10,136,
bed geometry 1,635 and generated resources 32. Rendered projectile previews were
inspected. Full live combat appearance remains for the user's retest; bedroom
passage/visible stepping is still unfinished. See [combat feedback](CREATURE-COMBAT-FEEDBACK.md).
No save, packet, damage or version change is needed; the development index now
describes the requested projectile presentation.

## Seventy-percent corner-bed correction in the normal executable

The September 13 23:05 screenshot shows small centered beds. The then-running
normal executable was the 18:41:04 build below and did not include the later
corner placement, walkable landmarks or failed-idle-retry correction. Its
22:56-23:00 log has repeated twenty-action-loop exits and 2-4-second upkeep;
the latest idle handler passes 24 checks while the older source fails two.

Beds now fit 70% of their allocation width and depth after rotation, anchored
at the top-left, with 30% clear strips at the right and bottom. This preserves
the existing small stable angle variation and applies to restored beds too.
The real-mesh regression fails 576 checks before and passes all 1,635 after;
default navigation passes 4,737, geometry 3,283 and Release flags eight checks.
Packed-room passage still fails 156 of 5,343 checks; this is not a claim that
all creatures can use a 30% lane or that the reported live stalls are resolved.

Release compilation succeeds to `build/windows/opendungeons-plus-pending.exe`,
dated 2026-09-13 23:11:59, 4,837,376 bytes, SHA-256
`9B709C4D1E5FEEA09149F1BD603C1738F52ABBEA469890D90ED5CC4E135D5AB0`.
After the user closed the game, Release linking and runtime preparation also
succeeded for the normal `build/windows/opendungeons-plus.exe`, dated
2026-09-13 23:14:48, 4,837,376 bytes, SHA-256
`5BE751264D758875751CDE775E4BAD379A7DF6F74A1508DAB085BA5DE6A5539F`.
All 32 generated-resource checks and eight effective Release-flag checks pass
after preparation. This is now the normal executable for user retesting and
supersedes the older normal/pending checkpoints below. No game was launched or
stopped by the agent. Visible low-bed stepping and live movement acceptance
remain open. No additional version bump or README entry is needed for this
build update; save and network formats remain unchanged.

## Startup resource regeneration correction

The September 13 21:23 startup failure came from CMake overwriting the shared
resource configuration with nonexistent installation-prefix media paths.
Windows generation now uses the already discovered OGRE media and includes
only installed shader directories. The regenerated configuration is shared by
both the normal and pending executables; neither binary needed to change.
The pending executable retains its 19:12:45 timestamp and SHA-256 below.

Release regeneration/build passes, as do 32 generation/configuration checks;
the native shader-resource probe fails before and passes after, resolving all
four internal shadow programs without a renderer or game window. DLL/Python
runtime preparation remains required for a fresh build directory, but another
CMake regeneration no longer undoes the media paths. User startup retest is
pending; bed stepping is authorized but not implemented in this executable.
See [startup verification](WINDOWS-STARTUP-FIXES.md); no gameplay, version or
README feature change is part of this configuration-only fix.

## Corner-bed and walkable-landmark checkpoint (partial)

The separate `build/windows/opendungeons-plus-pending.exe` is dated
2026-09-13 19:12:45, 4,837,376 bytes, SHA-256
`AE593D7E913A9C97315F1444A7A71AFE3E4854DD02DE38FF8AE54AF11A789F7A`.
Release compilation passes with optimized flags. This checkpoint makes portals
and dungeon hearts walkable and gives real beds 75% of their allocated native
dimensions, corner placement and stable creature-specific angles within four
degrees. Per-instance bed scale requires network version 0.7.3; unchanged map
records still load from 0.7.1 and 0.7.2. The normal 18:41 executable remains
unchanged, with the hash below; no game was launched or stopped.

The updated checkpoint also ends failed idle-wandering attempts for the current
tick instead of repeating them up to twenty times. The extracted production
retry probe reproduces two failures before and passes all 24 checks after this
correction; default navigation still passes all 4,737 checks. Actual in-game
turn duration remains unverified, and gameplay cooldowns are unchanged.

Verification passes 4,737 default navigation checks (including all creature
models/levels through both landmarks), 1,071 real-mesh/bed-placement checks,
seven real scale-packet checks, 27 save-header checks and 10,136 existing
renderer/animation checks with actual corner-bed placement. The new packed-bed
fixture still fails 176 of 5,243 checks: the existing full-body envelope cannot
pass every 75%-sized bed layout. These failures are not suppressed; the whole
room-navigation task is not ready for acceptance. The separate executable can
exercise the landmark/visual changes only, not certify bedroom passability.
Multi-second turns reported after the optimized 18:41 build also remain open.
See [the navigation note](ROOM-OBJECT-NAVIGATION.md) for implementation scope;
there is no additional README feature change beyond the existing navigation
entry, and the necessary protocol version bump is included in this checkpoint.

## Release optimization correction ready for load retest

The fully rebuilt and prepared normal `build/windows/opendungeons-plus.exe` is
dated 2026-09-13 18:41:04, 4,834,304 bytes, SHA-256
`97DD5D76CD37E3F19197FBF01CC0BE1D601071B659B85658DBE6A89D60C7A8A8`.
Release compilation, runtime preparation and eight effective-project-flag
checks pass; the flag probe fails against the preceding generated project.
With the corrected `/O2 /fp:fast /Zi` settings, 3,283 geometry checks, 20 action
retry checks and 8,052 navigation/layout/saved-food checks pass. The 362 food
searches reach the same 263 destinations in 1,571.44 ms total, 27.058 ms worst.
All 411 research/save/packet checks also pass with the existing approved values.
No game was launched or stopped. The reported load hang needs a user retest;
the requested 75%-sized corner beds with small angular variation are not in
this build and remain on the separate navigation task pending passage policy.
This normal executable supersedes the older build metadata below.

The generated MSVC Release project used `/Od` and Edit-and-Continue debugging:
the common platform flags overwrote CMake's optimized Release defaults. With
the September 6 save terrain, 27 saved beds and 50 source-oriented room objects,
362 isolated food searches reached the same 263 destinations with both flag
sets, but took 17,161.9 ms with `/Od /fp:fast` versus 1,676.67 ms with `/O2`.
The unoptimized run failed the existing 100-ms per-search regression ceiling;
the optimized run passed. These are isolated measurements, not a game-load test.

The separate `fix/windows-release-optimization` branch moves optimization and
debug-information choices out of the common flags: Release uses `/O2 /Zi`,
while Debug keeps `/Od /ZI`. This retains symbols without disabling Release
optimization. No save, protocol or gameplay values change, so no version bump
or README feature change is needed. The reported hang and larger-bed passage
decision remain open pending user retest and clarification respectively.

The September 13 visible furniture-footprint correction is built and prepared
for the normal `build/windows/opendungeons-plus.exe`, dated 2026-09-13 18:08:45,
4,795,904 bytes, SHA-256
`AA60D4F611BE659A27DA741E5B391A6734F040A1D87AE24B655C4D1AECF2DA1E`.
Release compilation and runtime preparation pass; no game was running when the
normal executable was replaced, and none was launched or stopped. Geometry
3,283, real furniture bounds 459, room navigation/layouts 7,630, walking poses
3,993, saved-terrain/food 3,617, renderer/animation 10,136, feeding limb 109 and
action retry 12 checks pass. See [navigation](ROOM-OBJECT-NAVIGATION.md) for scope
and measurement limits; user gameplay/visual acceptance remains pending.
The earlier pending executable and diagnostics below are superseded by this
normal build for testing the furniture changes.

The September 13 circular route-geometry extension passes Release compilation
to `build/windows/opendungeons-plus-pending.exe`, dated 2026-09-13 16:54:27,
4,791,296 bytes, SHA-256
`51B69E5A35A5FD055BB087E58087215BAD5B1F8592982786802058619E305223`.
Geometry 3,280 and navigation/benchmark 2,975 checks pass. The packed-dormitory
integration gate still reports four failures: the circular geometry is not yet
assigned to game furniture, and the navigation task is not ready for acceptance.
The normal 16:22:15 executable and its prepared runtime remain unchanged;
no game was launched or stopped. See [navigation](ROOM-OBJECT-NAVIGATION.md).

The September 13 combat-test stall follow-up is built to the normal executable
on `fix/solid-room-object-navigation`, dated 2026-09-13 16:22:15, 4,790,784 bytes,
SHA-256 `D5AF01DABB91D77158C65942FA1DC5FDBDFFC6ECC7F0E7FFB3B596B4AACFFBC0`.
Release linking and runtime preparation pass; no game was launched or stopped.
Geometry/shared-search 3,187, navigation/saved-food/benchmark 3,385, action retry
12, feeding 109, projectile 75, ranged dispatch 15, workshop 13 and shutdown 31
checks pass. The same 375 food cases retain 277 reachable targets; the final
isolated run takes 820.368 ms total, worst 5.684 ms, versus 1,482.060/642.864 ms
before. See [navigation](ROOM-OBJECT-NAVIGATION.md); live-game responsiveness,
combat acceptance and packed-bed collision policy remain unverified/open.

After the user closed the old run, the same server shutdown fix was rebuilt to
the normal `build/windows/opendungeons-plus.exe` and runtime preparation passed.
The normal executable is dated 2026-09-13 15:49:08, 4,785,152 bytes, SHA-256
`2A7E3CA18B6114B714F62F882B81DB816A8B1FFB77EC6515DD25CD237A48F30C`.
The 15:41 Windows hang report and log ending at the exit notification came from
the preceding 15:26 executable, without this fix; no new native crash dump exists.
Navigation clearance/performance remains open and is not covered by this fix.

The September 13 server self-wait fix passes 31 isolated real-SFML lifecycle
checks, two source guards, the existing 60 menu-cursor checks and Release linking.
The user's game is running, so the new output is
`build/windows/opendungeons-plus-pending.exe`, dated 2026-09-13 15:42:10,
4,785,152 bytes, SHA-256
`64F970762E0076AC2B17D78B9A45D1F5BD4EEB8A54BCAFF9F7041128E01118ED`.
It reuses the already prepared runtime; no running executable or DLL was replaced.
See [server shutdown](SERVER-SHUTDOWN.md). The normal 15:26 executable remains
unchanged; its latest user run still shows slow upkeep, under continued diagnosis.

The September 13 room-object navigation checkpoint passes Release compilation
and runtime preparation; the normal executable is dated 2026-09-13 15:26:05,
4,785,152 bytes, SHA-256
`4A508911681160E626E1050C4C67E44F1CFC565461EAF8BF1941BC6ECEFBD9A2`.
It includes the slow failed-search correction, body-sized food/work approaches,
rotated furniture and prison-fence clearance, and preserves the accepted feature
stack; see [room-object navigation](ROOM-OBJECT-NAVIGATION.md) for tests and limits.
Geometry 3,199, asset bounds 166, walking poses 3,993 and navigation integration
2,950 checks pass; dense-room and saved-terrain probes also pass. This does not
claim a complete live-game performance measurement or a resolved native crash.
The user's requested next step is diagnosis of the reported crash after this
checkpoint; no game was launched/stopped and no push was made.

The September 13 ranged-combat presentation follow-up passes Release compilation
and runtime preparation; the normal executable is dated 2026-09-13 13:50:39,
4,737,536 bytes, and includes the preceding projectile collision correction.
Dispatch 15, moving-projectile GPU 120 and real-model renderer 10,136 isolated
checks pass; see [combat feedback](CREATURE-COMBAT-FEEDBACK.md) for limits.
The user's game was not launched or stopped. Solid room-object navigation is
the remaining implementation task; research and feeding were accepted by the user.

The September 13 projectile collision correction passes 75 isolated production-
code checks (28 failures on the preceding implementation) and Release linking.
The normal executable was locked by the user's running game, so the verified
output is `build/windows/opendungeons-plus-pending.exe`, dated 2026-09-13 13:34:05,
4,720,128 bytes, SHA-256
`375A4912AD3CF1ECCB93AD00D2B8FBB1A5D793AFF9366C167CD6F65E349FF539`.
It uses the previously prepared runtime in that directory; no runtime DLLs were
replaced while the game was running. The normal executable remains the 12:47:51
build below. No game was launched/stopped or pushed; ranged presentation and
the newly requested solid room-object navigation are still in progress.

The September 13 cuff/grip and worker-tool feeding correction passes a clean
Release rebuild and runtime preparation after the animation-state layout change.
The executable is dated 2026-09-13 12:47:51, is 4,720,640 bytes, SHA-256
`35EE3E672F9999E3A01712BB9FA1FF4403A2290BB7022DE698AA3B42FE2465AA`.
The real-model renderer passes 10,124 checks (32 failures on the preceding
feeding implementation), and the committed finger/limb solver passes 109 checks.
Research 411, production 41, workshop 13, menu-cursor 60, feather/blood GPU
10 each and legacy map-header 26 checks also pass. The preceding exclusive-window
fix and its 624-check navigation result are retained. No game was launched or
pushed; the newly reported ranged-combat presentation remains under investigation.

The September 13 general window-navigation correction passes 624 isolated CEGUI
checks, Release compilation and runtime preparation. Opening options, objectives,
help, player information, cameras or settings now closes preceding dialogs through
their existing callbacks; see [exclusive windows](GAME-WINDOW-NAVIGATION.md).
The executable is dated 2026-09-13 12:31:56, is 4,718,592 bytes, SHA-256
`0E1D6B7EE3F64C77896DEE6CD66D3D4FF33914961AAFD23DAA7B98296173EA24`.
No game was launched; feeding and combat screenshot follow-ups remain open.

The September 13 follow-up fixes repeated-click closure and exclusive research/
production navigation, the culled sleeping-creature crash, and grounded chicken
pickup by all hand-equipped bipeds. Release compilation passes, along with
10,114 isolated renderer checks, 504 real-mouse CEGUI navigation checks and
64 committed limb-solver checks. The executable is dated 2026-09-13 09:04:25,
is 4,718,592 bytes, SHA-256
`0B193A99E5F113358294A8DA125F469B6A44BC14F0E680702C54EA630921DBE8`.
The complete feature stack is retained; the live game was not launched and user
gameplay acceptance remains pending. See the linked feeding, sleep, research
and production notes for the reproduced failures and verification scope.
Runtime preparation and the final 411 research, 41 production, 13 workshop,
60 menu-cursor, ten feather-GPU and 26 map-header checks also pass; the latter
include both supplied older saves, not a complete live-game deserialization.

The September 13 research save-compatibility correction passes 26 map-header
checks, including both reported 0.7.1 saves, plus 411 research/save/packet checks.
Release compilation and runtime preparation pass; see
[legacy save compatibility](LEGACY-SAVE-VERSION.md) for the verification boundary.
The executable is dated 2026-09-13 07:49:48, is 4,700,160 bytes, SHA-256
`A24CE41088F43DF999F825153012D06B43119C4B9451E2F1DDA30D766AE907DC`.
It retains the complete six-task feature stack; no game was launched.

The September 13 combat-animation follow-up passes 5,062 isolated real-Ogre
checks across all 33 models and ten GPU blood-transparency checks. Release
compilation and runtime preparation pass; see [combat feedback](CREATURE-COMBAT-FEEDBACK.md).
The combined executable contains the six queued research, production, cursor,
feeding, sleep and combat outcomes. It is dated 2026-09-13 01:06:16, is 4,699,648
bytes, SHA-256 `643304ABBBFDB3EBF6B9829C7DBD53DF55AEC0640137B7E492A4C5B17B5B5334`.
No game was launched; gameplay and visual acceptance remain with the user.

The September 13 sleep/bed-alignment correction passes 3,049 isolated Ogre
checks across all 33 creature models, both bed rotations and endpoint level
scales, plus Release compilation and runtime preparation; see
[sleep placement](CREATURE-SLEEP-ANIMATIONS.md) for the combined-bed evidence.

The September 13 feeding-material correction passes 2,455 isolated renderer
checks and ten real GPU transparency/fade checks, plus Release/runtime checks;
see [feeding animations](CREATURE-FEEDING-ANIMATIONS.md) for the reproduced black-quad defect.

The September 13 menu-hand correction passes 60 repeated-entry checks and
2,453 isolated Ogre hand/creature checks, plus Release compilation and runtime
preparation; see [menu hand cursor](MENU-HAND-CURSOR.md) for the reproduced case.

The September 13 production-priority correction passes 372 installed-CEGUI
checks (48 delayed-reply failures reproduced before the fix) and 41 actual
controller/reorder/packet checks, plus Release compilation and runtime staging.
The server still validates every requested move; see [production priority](TRAP-PRODUCTION-QUEUE.md).

The September 13 research-progression update implements all 27 three-level
entries, saved progress and versioned network selection. Release compilation,
runtime preparation, 411 research checks, 364 CEGUI checks, 35 production checks
and 13 workshop/save regressions pass; see [research progression](RESEARCH-PROGRESSION.md).
Gameplay and multiplayer acceptance remain with the user.

The sleep-arrival follow-up preserves the newly started sleep transition during
final bed positioning. All 2,451 isolated renderer checks pass, after reproducing
33 arrival failures before the correction. Release compilation (zero errors)
and runtime preparation pass; see [sleep transitions](CREATURE-SLEEP-ANIMATIONS.md).

The September 12 research-navigation checkpoint retains all four minimap corner
controls and adds the research button next to production. All 348 installed-CEGUI
checks pass, including the actual tree-toggle subscription; real 800x600 and
1280x720 views were inspected. Release compilation and runtime preparation pass.
This is not completion of the requested upgrade levels; see
[the remaining research scope](RESEARCH-PROGRESSION.md).

The September 12 production-queue update passes 35 actual reorder/packet checks,
13 existing workshop/save regressions and 288 installed-CEGUI layout/controller
checks. Real 800x600 and 1280x720 views were inspected. Release compilation and
runtime preparation pass using the maintained environment helper; reconfiguration
requires that helper's dependency paths. Manual production/network acceptance
remains with the user. See [production queue evidence](TRAP-PRODUCTION-QUEUE.md).

The September 12 sleep update adds authored sleep-entry playback or smooth
skeletal settling, followed by sustained rest and subtle breathing. All 2,385
isolated renderer checks pass across 33 meshes, including earlier animation
regressions. Release compilation and runtime preparation pass. User game and
bed-alignment acceptance remain pending; see [sleep transitions](CREATURE-SLEEP-ANIMATIONS.md).

The September 12 feeding update adds dedicated skeletal feeding clips for all
33 creature meshes, a consumed-chicken presentation and brief feather bursts.
The isolated real Ogre lifecycle probe passes 815 checks, including retained
hand/drop/get-up/combat regressions. Close-up renders were inspected and the
chicken pivot corrected. Release compilation and runtime preparation pass;
manual gameplay/network acceptance remains with the user. See
[feeding implementation and evidence](CREATURE-FEEDING-ANIMATIONS.md).

The September 12 atmosphere correction replaces stepped smoke-atlas playback
with continuous procedural mist and explicit shader tint/opacity, and adds 24
small rising embers at the four painted fire sources. The real Ogre/CEGUI probe
passes 640 checks and renders 180 consecutive frames; pixel comparisons verify
mist changes between consecutive frames, with much larger change over one second.
The headless desktop clamps larger requested windows (motion captures are
1284x781), so these renders do not prove native 4K coverage. Release compilation
and runtime preparation pass. Manual game acceptance remains with the user;
see [the correction and evidence](MAIN-MENU-ATMOSPHERE.md).

The September 12 main-menu atmosphere update keeps the supplied static artwork
and adds ten aligned screen-space layers for slow fog, flickering firelight,
pulsing green acid and intermittent lightning. The production Ogre material
parser and render fixture pass 280 checks across five resolutions and three UI
scales, and the 1920x1080 output was visually inspected. Release compilation
and runtime preparation pass; CTest has no registered tests. The executable is
dated 2026-09-12 18:44:37, is 4,598,272 bytes, SHA-256
`9DAC0D7F6EA72FABC2177C05B80FF6AC2054F826A6923F14D91F3D2A2B0C7D9D`.
No game was launched by the implementation agent; the in-game motion and timing
check remains pending. See [the main-menu atmosphere note](MAIN-MENU-ATMOSPHERE.md).

The September 12 creature-combat update varies and accelerates authored attack
clips, adds a short target reaction, displays sparks for armed clashes and subtle
blood for applied body damage, and adds a Game setting that disables blood.
Death playback is quicker, with model-based grounded fallbacks for Cultist and
Lich. The source-path probe passes 19 checks, the production particle scripts
pass 22 real Ogre checks, and the creature lifecycle probe passes 386 checks
across all 33 distinct creature meshes. The settings layout passes the existing
headless multi-resolution and UI-scale probe. The isolated impact render and both
fallback death renders were visually inspected. Release compilation and runtime
preparation pass; CTest has no registered tests. The executable is dated
2026-09-12 18:26:50, is 4,588,032 bytes, SHA-256
`C59E72017AAF1A428C1F1157ECABE0E8EADE5CB54A335F5A3F35555DA640DF7D`.
No game was launched by the implementation agent; the combined in-game check
remains pending. See [the creature combat note](CREATURE-COMBAT-FEEDBACK.md).

The September 12 creature hand-drop update preserves short right-click front-entry
drops and adds a 350-millisecond right-button hold for dropping every held
creature through one validated batch request. Confirmed creatures fall from hand
height and remain in a grounded lying pose until the server starts a smooth
350-millisecond get-up transition. The input and protocol regressions pass 10
and 233 checks respectively; the real Ogre
lifecycle probe passes 378 checks across all 34 configured creature definitions
(33 distinct meshes), including five concurrent falls. Its three-frame fall/ground
sequence and the get-up midpoint/final atlases were visually inspected. Release
compilation and runtime preparation pass; CTest has no registered tests. The
executable is dated 2026-09-12 17:57:10, is 4,552,192 bytes, SHA-256
`CBB2329AD8C348022927DEE68A51E6E73E926A211BAA3B4CD3D09F1C1A4127D4`.
No game was launched by the implementation agent; the combined in-game behavior
check remains pending. See [the creature hand-drop note](CREATURE-HAND-DROP.md).

The September 12 room-construction effect adds a short violet-blue spark burst
to each newly built gameplay room tile after the normal tile refresh. The
production particle and material scripts pass the 10-check headless OGRE probe,
and the notification/render-lifecycle source probe passes 12 checks. The real
OGRE render preview shows nine simultaneous tile effects with 324 live particles;
its output was visually inspected. Release compilation and runtime preparation
pass; CTest has no registered tests. The normal executable is dated
2026-09-12 15:45:25, is 4,496,896 bytes, SHA-256
`21A15287F86C5FFA8787B326D777B9E169C40E5966C943A8C62A005F9A5525E1`.
The user accepted the in-game result on September 12, 2026; no game was launched
by the implementation agent. See [the room-construction effect note](ROOM-CONSTRUCTION-EFFECT.md).

The September 8 community exit-page update replaces the loose recruitment text
with a centred, skinned panel and explicit Discord and Close actions. The real
Ogre/CEGUI render probe passes 150 layout, text-fit and hit-target checks across
five resolutions and three UI scales. Release compilation and runtime
preparation pass. The normal executable is dated 2026-09-08 22:54:32, is
4,490,752 bytes, SHA-256
`8F84BD5703D825E8F9D1327EFFE3768E5EBE3DC228E2E35DB4B411A080913773`.
The user confirmed the completed page and both actions in game on September 8,
2026; see [the community exit-page note](COMMUNITY-EXIT-PAGE.md).

The September 8 worker-creation effect adds a short turquoise-green spark burst
to workers created by the summon-worker spell without changing ordinary creature
spawning or worker behaviour. The production particle and material scripts pass
the 10-check headless OGRE probe. Release compilation and runtime preparation
pass, and the user accepted the visual result in game. The normal executable is
dated 2026-09-08 20:58:21, is 4,491,264 bytes, SHA-256
`CEA36C7510853B7129E3703F811F0DF5662367FFAB0797B2D3209DBA934D5C53`.

The final September 8 creature-readability follow-up continuously shows a
softened, segmented owner-coloured health ring above every visible creature. Its centre
alternates the level with the established hunger, tiredness, mood and activity
symbols, including the previously omitted unhappy state, while preserving the
existing autonomous food, sleep, work-refusal, conflict and departure paths.
The ordinary level caption is enlarged and optically centred inside the ring.
The unhappy display is derived from the negotiated allied mood value and does
not extend the legacy overlay packet. The source-path probe passes 25 checks,
the deterministic asset probe 26, the real OGRE overlay render 234, and the
serializer/mood/activity probe 1,117. Release compilation and runtime preparation
pass. A separate 27-check probe executes the production overlay cycle across
health states, needs, the level interval and visibility rules. The OGRE matrix
covers all eight health states in all eight configured player colours. The normal
executable is dated 2026-09-08 20:34:19, is 4,490,752 bytes,
SHA-256
`9221DF8E21452ED11010E228404492926872F458E9346F505C6F84678FEA7905`.
The initial build attempts were invalid before compilation because the calling
environment contained both `Path` and `PATH`; removing only the duplicate from
the temporary build process allowed the documented environment helper to run.
The user accepted the gameplay appearance on September 8, 2026.

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
