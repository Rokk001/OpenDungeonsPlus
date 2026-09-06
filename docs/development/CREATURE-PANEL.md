# Creature panel

## Existing behavior and implementation scope

Work branch: `feature/creature-panel`, from the complete current fork at
`2d3e79dc`, including the accepted Escape correction and all local documentation.
The existing panel offers worker/fighter pickup buttons and eligible counts.
The approved local HUD specification requires per-type views and accurate
activity and mood data; the current controls alone do not cover those views.

The server computes five mood levels, but creature snapshots and updates carry
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
