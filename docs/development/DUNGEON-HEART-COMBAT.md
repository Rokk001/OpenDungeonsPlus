# Dungeon heart combat

September 22 acceptance update: after the rejected-click follow-up was deployed,
the user reported successful in-game retests. This supersedes the pending user
retest status in the historical entries below; Windows-blocked automated probes
remain explicitly unverified, and no agent-run game test is claimed.

The existing room exposes every floor tile as a combat target and stores damage
per tile. Its persistent central object has no health or attackability; the room
can also be sold. The requested behaviour is an enemy-only attackable heart,
with floor tiles protected from demolition and direct damage.

Reuse the existing persistent object and room lifecycle: a server-side heart
object delegates to one room-owned health pool and participates in visible enemy
target discovery. The ordinary room target/damage and sale paths reject the
heart's floor. Actual heart death releases the room through the existing cleanup
and last-temple defeat paths. Editor tile removal remains available.

Preserve existing total durability when loading old maps/saves rather than
introducing an unrelated balance change. A tagged optional room record saves
the independent remaining heart health; old files without it still load.
Numerical rebalancing, regeneration and unrelated resource rewards are outside
this targeted combat/protection change.

## Verification

### Construction footprint follow-up

The September 22 user log records a treasury built at (56,102), while the
heart room covers (57..59,101..103), centred at (58,102). The shipped heart
mesh extends 1.73308 units from its centre, overlapping the supposedly free
adjacent tile. The existing building flag correctly protects the nine room
tiles but does not represent this visible overhang. Reuse the measured bounds
in `RoomObjectBounds.h` in the shared tile construction validator, on both
client and server, without changing editor placement or creature navigation.
Treasury hover preview also needs to use that existing validator instead of
unconditionally offering construction. This completes the unmerged heart
protection feature on its existing branch; no numerical rebalance is involved.

The extracted production construction validator and treasury hover pass 250
checks (76 failures before the fix), including the logged overlapping tile,
all surrounding footprint edges, ordinary land, existing buildings, editor
placement and portal isolation. All 51 demolition-selection regressions pass.
The shared validator also gates trap placement and server room packets, so the
protection is not limited to the treasury preview. No header layout changed;
an incremental Release rebuild is sufficient for this follow-up.

The next user retest exposed treasury click feedback: its empty-selection path
reports a white zero-cost build message, which the game dispatch interprets as
success and uses to trigger the hammer. It returns without sending a build
packet; the latest user log contains no new room after loading. Replace this
success feedback with the existing failure path and extend the production
dispatch fixture to cover treasury clicks, not just hover and ordinary rooms.
All 745 input/dispatch checks now pass (five hammer failures before), together
with the 250 footprint checks and 32 resource checks. Release compilation and
hash-verified deployment pass; user click/animation retest remains pending.

The production-method heart fixture passes 46 checks, including the actual
server heart object, owner/allied/unknown rejection, independent damage,
single death notification, retained floor, editor removal and save/legacy-load
handling. The production sale-selection fixture passes 51 checks, including
preview, dragging and validated commands over protected heart tiles. All 361
temple-duplication regression checks also pass with the new object constructor.

The production enemy-discovery fixture compiles, but Windows application control
blocks execution with error 4551, both in the sandbox and in the approved
external run; it is not reported as passed. No security policy was changed.
The inherited movable-object footprint is its position tile, so normal combat
selection targets the heart's centre rather than its surrounding room floor.
The existing seat upkeep excludes rooms with zero health from temple counts,
feeding the existing last-temple defeat notification.

Clean Release compilation, hash-verified backup/deployment, runtime preparation
and all 32 resource checks pass; see [the build record](BUILDING.md).
User gameplay acceptance must
cover blocked demolition, enemy attacks on the heart itself, and defeat after
heart destruction; no manual game test is run by the agent.

This is a local feature without a release-version change; the development index
and build record contain its documentation, with no top-level README or release
changelog update needed. No remote publication is authorized.
