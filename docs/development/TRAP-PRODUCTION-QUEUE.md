# Trap production queue

## Existing path and scoped extension

The accepted workshop scheduler uses GameMap's trap insertion order, filters
reachable owned orders and accounts for uncarried stock before starting an item.
Work already in progress is retained. Gameplay saves preserve trap order.

Expose that priority order and each owned workshop's current type and work points
in a production window. Up/down controls swap a pending owned order with the
adjacent pending owned order in the authoritative trap vector. Other seats,
completed orders, current work and the scheduler remain untouched. Query and
reorder replies contain owner-only snapshots; refresh while the window is open.
Add production access beside the minimap and in F10. The research button belongs
to the separately queued research branch; preserve the existing four controls.

## Verification

`source/tests/check_trap_production.py` compiles the actual reorder method and
real ODPacket codec: 35 checks pass for ownership, boundaries, stale/completed
orders, client/editor rejection, field roundtrips and malformed snapshots.
The existing `check_workshop_order.py` passes all 13 scheduling/save scenarios.

The isolated installed-CEGUI probe passes 288 layout/controller checks at four
display sizes from 800x600 through 3840x2160 and three UI scales. It exercises
stable selection after reorder, disabled controls during a pending reply,
empty snapshots, retained minimap controls and F10 access. These layout checks
use CEGUI's null renderer; separate real Ogre views at 800x600 and 1280x720 were
inspected, including correcting clipped workshop rows. Those views use fixture
orders and the existing background, not a live game session.

Release compilation and runtime preparation pass. Evidence: ignored
`build/windows/production-build.log`, `production-ui-probe-results.log` and
`build/reference-audit/production-*.png`. No game was launched or pushed.
Live multiplayer timing, actual workshop progression after reorder and manual
appearance remain for user testing. The research minimap control and upgrades
are still a separate queued task; this branch adds only production access.
