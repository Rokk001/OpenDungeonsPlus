# Creature panel

## Existing behavior and implementation scope

Work branch: `feature/creature-panel`, from the complete current fork at
`2d3e79dc`, including the accepted Escape correction and all local documentation.
The existing panel offers worker/fighter pickup buttons and eligible counts.
The approved local HUD specification requires per-type views and accurate
activity and mood data; the current controls alone do not cover those views.

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

This is a prerequisite for the panel, not a completed UI feature. Activity
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
portrait controls remain separate remaining work within this feature branch.

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
The version remains 0.7.1. No new panel controls are connected yet, so no visible
feature or completed panel is claimed in the public README.

### Remaining panel integration

Per-type views, count controls and pickup/focus bindings remain unimplemented.
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
