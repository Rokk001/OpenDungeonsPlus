# Creature picker counts after pickup

## Cause and correction scope

The September 6 user captures at 19:17 and 19:19 show several creatures held
beside the hand while their per-type picker counts remain unchanged. The
server builds the panel snapshot from living owned creatures, including those
already picked up; the Total and mood criteria therefore keep counting them.
The UI displays that snapshot without subtracting held creatures. Its pickup
handler correctly excludes off-map creatures, so the number and action disagree.

Reuse the existing on-map state: pickup removes a creature from its position
tile and dropping restores it. Count on-map creatures in the existing server
snapshot while retaining a zero-count class entry when all of its creatures
are held. This also excludes creatures currently carried off-map. Keep the
existing owner scope, category rules, packet layout, pickup validation and
refresh order; do not optimistically subtract a request that might be rejected.

Work branch: `fix/creature-picker-counts`, from complete checkpoint `65506edf`.
The shared checkout and normal index remain reserved for the parallel task.

## Verification

The source-derived server collection loop, actual packet codec and installed
CEGUI panel pass 64 focused checks: successive pickups count down from three to
zero, the portrait stays in place, zero disables pickup, drops restore counts,
and both mood and worker counts follow the same state. The first pickup check
fails before the correction. Including the existing UI/scaling regression
matrix, the probe passes 911 checks. Game entities, pickup acknowledgement and
map state are simulated; this is not a live multiplayer test.

Release compilation and runtime preparation pass in
`build/windows/picker-count-release-build.log` and `picker-count-runtime.log`.
The executable at `build/windows/opendungeons-plus.exe` is dated September 6,
2026 at 19:31:52, SHA-256
`7ed9bd019a7bc711244523ec9e33ac3b0c6d1b3084e8d99c1f6421c46cf5184a`.
Probe sources/helpers and results are `generate-picker-count-probe.py`,
`build-picker-count-probe.ps1`, `picker-count-before.log`,
`picker-count-probe-results.log` and `picker-count-after.log` under `build/windows`.

The user performs in-game acceptance: pick up all creatures of one type through
the picker, verify the count reaches zero, then drop them and verify it returns.
No game was launched. The separate hand-orientation request remains its own task.

Version remains 0.7.1 because this is a correction in development, not a release.
README controls are unchanged and no changelog exists; the creature-panel note
now describes the corrected count semantics alongside this investigation.
