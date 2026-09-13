# Trap production queue

## Repeated navigation clicks and exclusive windows

The production minimap and F10 bindings both call an unconditional show handler.
Repeated clicks therefore cannot close the panel, and research remains visible
behind it. Capture the panel's visibility before closing existing dialogs through
the established Escape close handlers, then open it only if it was previously
closed. This preserves each dialog's cancellation behavior instead of hiding
its window without completing its controller lifecycle. No save format or
network version change is required for this client-only navigation correction.

The expanded installed-CEGUI fixture sends real mouse down/up events through
the minimap and F10 controls and exercises the actual Escape close dispatcher.
All 420 checks pass, including second-click closure and closing research and
objectives before production opens; the previous handler produces 58 failures
(including follow-on state failures). The 41 reorder/packet checks also pass.
Research-to-production closure is covered here; the opposite direction is
completed on the research branch. Manual gameplay acceptance remains pending.

## Reported priority-button regression

The once-per-second read refresh sets the same pending flag used to disable
both priority buttons and reject move commands. With a delayed reply, a valid
selection is therefore unusable even though reordering uses a stable trap name
and the server already validates ownership, pending state and boundaries.
Keep the flag solely for throttling refreshes; allow selected-order commands
while snapshots are in flight, preserving authoritative server ordering.
The delayed-reply case reproduced 48 failures in the installed-CEGUI fixture;
all 372 checks pass after removing the two blocking guards. This supersedes
the earlier expectation below that pending replies disable both buttons.

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
