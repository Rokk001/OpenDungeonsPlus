# Creature experience and recovery indicators

September 21: the user accepted the experience and attack-recovery indicators.

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

The September 20 screenshot shows dark level digits losing contrast against
dark owner colours and the recovery dial. Add a thin warm-light outline behind
the existing dark level glyphs only. Reuse the same font, caption, position and
lifetime, including empty captions during mood display; retain accepted petal
transparency and all progress values/timing. No health asset changes are needed.

## Verification

September 20 readability follow-up (`fix/creature-indicator-readability`): the
18:31 and 18:32 screenshots confirm that fixed 48-pixel rings and 18-pixel
two-digit captions remain small at close zoom. Increase the minimum ring to 64
pixels and levels to 32/26 pixels, with light filled digits and a dark outline.
Project a three-quarter-tile camera-facing diameter at the creature's position;
scale health, experience, recovery, moods, captions and outlines together, with
the readable minimum retained at distance. This also updates while paused.
Gameplay starts with indicators enabled; existing edge-triggered Alt behavior
and editor hover remain unchanged. No packet, saved preference or version change
is needed; README describes the changed default and zoom behavior.
The real Ogre caption/zoom fixture passes 557 checks, covering levels 1-30,
perspective zoom, proportional layers/outlines, paused updates, non-square
viewports, offscreen restoration and cleanup. Ogre quantizes pixel-mode glyph
heights to whole pixels, so size comparisons allow that documented rounding.
All 377 progress/packet regressions pass. The updated default/Alt fixture compiles
but Windows application control blocks execution (4551); it is not a runtime
pass. Manual appearance/default-toggle acceptance remains with the user.
The clean cumulative Windows Release build passes
(`build/review-followups/indicator-readability-build.log`); deployment follows
the remaining approved UI follow-ups after the running game has closed.

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

September 20 caption follow-up: Windows Release compilation passes
(`build/review-followups/level-outline-build.log`). The production Ogre caption
fixture `check_level_caption_outline.py --compile-only` compiles all checks for
levels 1–30, foreground/outline ordering, size/position synchronization, mood
replacement, hiding, reuse and cleanup. Its runtime checks have not run because
Windows application control blocks newly compiled test executables. The existing
200 health-transparency and 32 resource-generation checks still pass. Earlier
299-check render evidence above predates the outlined caption.

## Release scope

This feature does not define a release/version bump. The development index is
updated; there is no existing release changelog entry to rewrite. Build and
deployment evidence is recorded in BUILDING.md after the cumulative queue build.
