# Dungeon heart combat

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
