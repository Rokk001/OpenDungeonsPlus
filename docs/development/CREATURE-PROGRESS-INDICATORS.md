# Creature experience and recovery indicators

## Existing implementation and change

Creature overlays already contain owner-coloured health segments, a centred
level and cycling need symbols. They are reused, including transparent depleted
segments and the existing Alt toggle; no second health-display system is added.
Previously regular creature updates omitted experience and skill recovery.

A gold inner ring now shows experience towards the next level; at maximum level
the ring is full. A clockwise centre dial shows the last attack's recovery,
using its actual cooldown/warmup duration. The dial clears when the server
reports readiness, smoothly interpolates within one reported turn, and freezes
when simulation time is paused. Two-digit levels fit inside the inner ring.
Mood symbols retain their existing one-second alternation with the level.

Progress is appended to full and incremental packets only after a separately
negotiated capability. Older servers/clients and replays do not receive or
consume that extension. Unknown progress remains hidden. Existing visibility
rules still determine which creatures a client receives; no fog reveal is added.
Cooldowns still reset when loading saved games, as they did before this change.

Two shared generated atlases avoid per-creature texture/material allocation.
Regenerate with `tools/generate-creature-progress-overlays.ps1`.

## Verification

- `source/tests/check_creature_progress.py`: 377 compiled production-method and
  real packet-codec checks, including concatenated payloads, old-peer omission,
  invalid/truncated payloads, maximum level, repeat attacks, pause and tick loss.
- Existing Alt/lifetime probe: 128 checks across both keyboard backends.
- Hidden-window GL3Plus probe: 299 checks, including all atlas frames and the
  actual overlay controller; rendered recovery, level 30 and mood were inspected.
  Local fixture and captures: `build/windows/generate-initial-overlay-probe.py`
  and `creature-progress-real-*.png`.
- No game was launched. Manual acceptance: XP gains/reset after level-up,
  repeated melee/casts, pause, Alt, multiple moods, ownership colours and a
  multiplayer peer/replay with and without the new capability.

## Release scope

This feature does not define a release/version bump. The development index is
updated; there is no existing release changelog entry to rewrite. Build and
deployment evidence is recorded in BUILDING.md after the cumulative queue build.
