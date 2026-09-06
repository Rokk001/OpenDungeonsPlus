# Creature panel

## Existing behavior and implementation scope

Work branch: `feature/creature-panel`, from the complete current fork at
`2d3e79dc`, including the accepted Escape correction and all local documentation.
At the baseline, the panel offered worker/fighter pickup buttons and eligible counts.
The approved local HUD specification requires per-type views and accurate
activity and mood data; those original controls alone did not cover those views.

## Current integration

The panel now displays cached per-type portraits with Total, Jobs, Fighting and
Moods views, horizontal type scrolling, and persistent worker Total/Idle/Working/
Fighting counts. Type order follows the map's creature definitions, including
custom types. The existing worker/fighter quick selectors remain at the right.
Left-clicking a count requests an eligible creature of that type and category
through the existing server-validated pickup command. Right-clicking a portrait
or count uses the existing camera navigation to an on-map creature of that type.

`CreaturePanelData` provides one shared category mapping for aggregate counts and
local pickup selection. The server sends an owner-only class/count snapshot after
entity refresh, with a separately negotiated capability. This counts living
owned creatures on the map, including those outside client vision, without
sending hidden entity names, positions or vision. Held and carried off-map
creatures are excluded; their class remains visible with zero when none remain
on the map. The local hand list is not added again. See the
[picker-count correction](CREATURE-PICKER-COUNTS.md) for the diagnosed pickup bug.
Old peers and recordings retain their existing packet layouts and quick controls.
Unknown activity is not idle; unknown mood is not happy. Active workshop/library
use counts as manufacturing; queued or interrupted room work does not. Friendly
arena combat appears in both training and fighting. Guarding remains zero because
the fork has no corresponding action; no AI jobs or mood thresholds were changed.

`CreaturePanel` owns its dynamic windows and event connections, reuses the current
GUI scaling registry, and renders only when the creature tab is visible. Portrait
textures now use 192x384 pixels for the 54x108 design columns. Pending pickup
requests are suppressed until the next aggregate snapshot; that guard does not
constitute a live network-latency test.

The integration review found two implementation defects and corrected them:

- Storing CEGUI scoped connections by value in a growing vector disconnected
  earlier controls when the vector relocated them. The panel now uses the
  project's existing connection-handle pattern with explicit teardown.
- Creature upkeep stops during knockout, but its retained action stack could
  still appear as work, fighting or idle. The existing knockout predicate now
  suppresses activity on both server and client while retaining living totals,
  the action stack and recovery behavior.

### Integration verification

- The production classification/aggregate packet probe passes 77 checks,
  including active versus queued work, arena membership, semantic mood groups,
  unknown state, held totals, packet boundaries and atomic malformed-input rejection.
- The production mood/activity/negotiation probe passes 1,117 checks. The expanded
  optional negotiation matrix covers the panel capability. Three knockout checks
  failed before the one-line activity correction and pass afterward; recovery is
  also covered. Before evidence is `build/windows/creature-panel-knockout-before.log`.
- The real Ogre/CEGUI panel probe passes 830 checks. It links the production panel,
  portrait renderer and category mapping and extracts current scaling methods.
  It injects mouse input for views, type/category pickup, camera focus and paging,
  and checks all visible type-count hit areas and column bounds at 800x600,
  1280x720, 1920x1080, 3440x1440 and 3840x2160 through 80/100/120/100% changes.
  Column aspect allows one pixel of the existing pixel-alignment rounding.
  Game entities, map storage and command endpoints are test doubles; this does
  not replace gameplay, multiplayer, replay or live display-switch acceptance.

The UI probe initially expected paging despite all fixture types fitting on screen;
additional custom fixture classes now establish real overflow. Its original ratio
tolerance also rejected 41x81 pixels from ordinary pixel alignment, so it now checks
the expected 2:1 column dimensions within one pixel. Neither harness correction
changed the game's layout or paging behavior.

Local commands and logs are `build/windows/build-creature-panel-data-probe.ps1`,
`build-creature-mood-probe.ps1`, `build-creature-panel-ui-probe.ps1` and their
corresponding `*-results.log` files. Generated panel images are under
`build/reference-audit/creature-panel-*.png`. No game was launched by the assistant.

The user reported that the new in-game screenshots look good. The inspected
16:22:11 and 16:22:15 captures show portraits, counts and hover descriptions at
3440x1440; this records visual acceptance of those views, not all filter behavior.
Original PNGs remain in `C:\Users\mario\AppData\Roaming\opendungeons`; local JPEG
inspection copies are in `build/reference-audit/user-captures`. That comparison
cache is not the game's screenshot destination and does not update automatically.

The first final-link attempt encountered LNK1104 because the user was running the
executable. After the user closed it, the incremental Release build and runtime
preparation succeeded in `build/windows/creature-panel-verified-build.log` and
`creature-panel-verified-runtime.log`. The prepared executable timestamp is
September 6, 2026 at 16:39:18, SHA-256
`141f56e38665bfab44df3741f82cbc46213637978990a4d256f7316129759024`.
It includes the final connection and knockout corrections and the parallel shadow
checkpoint `99e80b2d`; the shadow change remains a separate contribution.

### Remaining acceptance

The exact repeated-right-click target sequence is not established by the current
reference evidence; the implementation currently selects the first available
on-map creature of the requested type. Final portrait framing, category artwork,
the retained quick controls, and held/contained population comparison still need
their detailed comparison. Actual multiplayer/replay compatibility, rapid pickup
under latency and gameplay category transitions remain unverified. This feature
does not complete every HUD or hand-feedback scenario in the broader specification.
Version remains 0.7.1 because no release was requested; README now describes the
connected controls, and there is no changelog in the checkout.

At the original panel baseline, the server computes five mood levels, but creature snapshots and updates carry
only the overlay flags. Happy, Neutral and Upset therefore cannot be distinguished
by the client. Changes between them also need to schedule a refresh even when
the displayed overlay flags stay the same.

## Full mood prerequisite

Extend the existing optional connection negotiation used for live nicknames
with a separate full-creature-mood capability. Only agreeing peers append an
explicit signed mood value to the existing creature snapshot/update payload.
Preserve old packet fields, notification numbers and overlay flags. Unavailable
or undisclosed mood is Unknown, not Neutral or Happy. Disclose full mood only
to the creature's allies, preserving the existing prison-overlay exceptions.

Do not pack metadata into unused overlay bits: the current renderer cycles
every set bit into a material name, including bits unknown to older clients.
The server confirms the per-client agreement at game/editor start, before
sending entity data. Replays contain incoming packets only: an older client's
recording can contain a server offer it never accepted. The reader must use the
recorded agreement rather than enabling extended entity payloads from that offer.

At that checkpoint this was a prerequisite, not a completed UI feature. Activity
classification, per-type controls, portrait assets and user-visible acceptance
remain open. No mood mechanics or AI decisions are changed by transmission.

## Verification

### Activity data prerequisite

The server executes the last action in each creature's stack. Movement may be
stacked over a room job, digging, carrying or combat; a room-use action can also
remain queued under food, payday or combat. The existing pickup priority lists
therefore cannot provide truthful per-category UI state.

Extend the same negotiated snapshot/update path with a separate activity
capability. Transfer the executing action, the nearest non-movement action,
the assigned room type and whether the creature is currently in that room.
These are facts from the existing action stack, not new AI jobs. Room assignment
alone does not establish active work. Unknown data, off-map/dead creatures and
non-allied recipients must not be reported as idle. Sample state at the existing
end-of-turn refresh, so room/task changes trigger updates without altering AI.

Per-client confirmation at game/editor start preserves recordings from older
clients, including the preceding mood-only version. UI category mapping and
portrait controls were separate remaining work at that prerequisite checkpoint.

The implementation now samples these facts in `Creature::getActivity` and
refreshes them through the existing entity notification. The room getter is
read-only; pushing/popping actions, room use and AI scheduling are unchanged.
The receiver clears unavailable, invalid or truncated activity to Unknown.
Pickup also clears the cached state immediately, and the getter suppresses
off-map/dead client state; dropping cannot restore the previous job before a
fresh server update arrives.

The extended C++ probe passes 1,049 checks: the preceding 713 mood checks and
336 activity checks. It uses the production activity sampler, pickup and full refresh
method in addition to the serializers/negotiation blocks. Coverage includes
wandering, movement over digging/parking, room arrival, payday interrupting a
queued room job, arena fighting with room context, removed room references,
held/dead creatures, immediate pickup/drop cache invalidation, refresh suppression
for unchanged state, ally visibility,
all optional-feature combinations, truncated/invalid payloads and exact
compatibility with both `2d3e79dc` and mood checkpoint `b25ac98c`.

The same local probe scripts/logs listed below are reused. Action stacks,
room/tile storage and queued network endpoints are test doubles; this does not
claim a live simulation, multiplayer or visual acceptance run.

The clean Windows Release build, final incremental build and runtime preparation succeeded in
`build/windows/creature-activity-clean-build.log`, `creature-activity-final-build.log` and
`creature-activity-runtime.log`. The prepared executable timestamp is
September 6, 2026 at 15:16:16; SHA-256:
`667e5f70ebe7d9822a67f53b526e8ee02adcf5065c394f2c86cf50be30be806f`.

### Portrait rendering prerequisite

The existing atlas has aggregate worker/fighter images. At this feature's
baseline, creature models and materials exist, but no per-type portrait asset
or thumbnail renderer was found. The new `source/render/CreaturePortrait.cpp`
reuses those models and the minimap's existing Ogre-to-CEGUI image bridge.

The portrait path renders each existing mesh in its Idle pose to a cached
texture in a separate scene. Portrait material copies disable world shadows
without modifying shared gameplay materials. Short, wide creatures need framing
around their head rather than the standing-creature upper-body crop. Images are
owned by the current CEGUI system; shutdown releases the associated Ogre textures.

The isolated offscreen asset preview links the production renderer and image
cache with the installed Ogre and CEGUI libraries. All 33 distinct configured
meshes render nonempty images, repeat requests reuse the same image, temporary
scenes and material copies are released, and world shadow parameters remain
unchanged. CEGUI shutdown removes every cached portrait texture. Generated
previews are under `build/reference-audit/portrait-*.mesh.png`; scripts and logs
are `build/windows/creature-portrait-preview.cpp`,
`build-creature-portrait-preview.ps1`, `creature-portrait-preview-build.log`,
`creature-portrait-preview-results.log` and `creature-portrait-preview-stderr.log`.

The helper initially omitted the metal material's shader include paths and the
application's shader-system setup. Matching the existing application setup fixed
those helper failures; no game shader or dependency was changed. Compiler/shader
warnings are retained in the logs. Selected humanoid and non-humanoid previews
were inspected. Separate CEGUI geometry renders of Kobold and Orc show the correct
image and orientation (`portrait-gui-*.mesh.png` in the same preview directory).
This does not establish every model's final framing or panel appearance. No game
was launched.

The Windows Release build and runtime preparation pass in
`build/windows/creature-portrait-build.log` and `creature-portrait-runtime.log`.
The prepared executable timestamp is September 6, 2026 at 15:43:01; SHA-256:
`cb9421b005d5ca84cc463b73ea8702b33207ce53a71e48278dc641591bc25e40`.
The version remained 0.7.1. No new panel controls were connected then, so no visible
feature or completed panel is claimed in the public README.

### Population-gap investigation before integration

At that checkpoint, per-type views, count controls and pickup/focus bindings were unimplemented.
Connect the cached portraits to those views; do not substitute a generic icon for
every type. Final model framing and the rendered panel still require comparison.

The existing UI refresh runs when player-seat data arrives, before the turn's
entity refresh notifications. New activity counts must also refresh after entity
data is applied. Local pickup retains the creature in the map's creature list
while removing its tile membership, so adding the local hand list again would
double-count it. Other clients receive entity-removal notifications for pickups;
population coverage must be checked before claiming complete per-type totals.
In particular, `Creature::computeVisibleTiles` suppresses vision for knocked-out
or imprisoned creatures, and `GameEntity::notifySeatsWithVision` removes entities
from clients that lose tile vision. The client list alone therefore cannot prove
complete owned-population counts. The next integration must resolve that data
gap without revealing unseen world entities or mislabeling visible counts as totals.

The integration will send an owner-only aggregate snapshot after entity refresh,
using a separately negotiated capability. It contains class names and category
counts, not hidden entity names, positions or vision. Old peers keep their packet
layouts. The same activity/mood classification will drive counts and eligible
local pickup targets. Unknown activity does not become idle; queued room use is
not manufacturing/training until the creature is actually using that room.
Friendly arena combat belongs to both training and fighting views. Guarding stays
zero because the fork has no guard action; no AI behavior is added for the display.

### Mood checkpoint

The isolated Windows C++ probe passes 713 checks using the production creature
snapshot/update serializers, mood transition method and optional negotiation
blocks, linked with the real ODPacket/SFML implementation. It covers all five
moods for owned, allied, enemy and prison-related recipients; unchanged legacy
packet bytes against `2d3e79dc`; packed-entity boundaries; missing/declined
capabilities, older-client recordings, disconnect reset, invalid values and
all 25 mood transitions with the existing chat conditions.

The harness substitutes map/seat storage, rendering, connection endpoints and
the mood calculator. It verifies transmitted values and scheduling, not live
multiplayer, replay playback, gameplay or panel appearance. Local diagnostic
files are `build/windows/generate-creature-mood-probe.py`,
`build-creature-mood-probe.ps1`, `creature-mood-probe-build.log` and
`creature-mood-probe-results.log`.

The clean Windows Release build, final incremental build and runtime preparation
succeeded in `build/windows/creature-panel-clean-build.log`,
`creature-panel-final-build.log` and `creature-panel-runtime.log`. The prepared
executable at `build/windows/opendungeons-plus.exe` has timestamp September 6,
2026 at 14:47:45 and SHA-256
`a2a6747a0214bbe1271c82fd6f72a9d6938257ae7f4d740cf34b91c3feb98e48`.

The game version remains 0.7.1; no release is requested, the old protocol is retained for older
peers, and there is no new visible panel behavior to describe in the public
README. No game was launched, and no push or upstream PR was made.
