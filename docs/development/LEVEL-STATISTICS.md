# Level statistics (server counters and debriefing data)

## Purpose

The server counts a few per-seat values during a level and sends a snapshot to a
defeated human player, so the client can fill a debriefing table with one column
per seat. This change only produces and stores the data; showing it is a separate
step.

## Counters

Held in `SeatStatistics` (`source/game/SeatStatistics.h`), one instance per `Seat`
(`Seat::getStatistics()`), server side only. All counters start at 0 when a map is
loaded. They are not saved: a loaded saved game restarts its statistics at 0.

| Counter | Incremented in |
|---|---|
| `mKeepersDefeated` | `RoomDungeonTemple::takeHeartDamage`, when the heart's health reaches 0: the attacker's seat gets +1 |
| `mCreaturesKilled` | `Creature::takeDamage` via `Seat::recordCreatureKill`, victim is a creature of a non-allied seat that is not playing the Hero faction |
| `mHeroesDestroyed` | same place, victim seat's faction is `Hero` |
| `mRoomsCaptured` | `Room::handTileOverToSeat` (called by `Room::claimForSeat`), see below |
| `mItemsMade` | `RoomWorkshop::doUpkeep`, when the crafted trap is created: +1 for the workshop's seat |
| `mCreaturesConverted` | `RoomTorture::useRoom`, when `creature.changeSeat(getSeat())` succeeds: +1 for the torturing seat |

Elapsed time is not a counter: the server sends `GameMap::getTurnNumber()` divided
by `ODApplication::turnsPerSecond`, as whole seconds.

## Assumptions

The meaning of the reference game's rows is not documented, so these are
assumptions:

- Creatures killed: the killing blow is the `Creature::takeDamage` call that takes
  the creature from alive to dead, with an attacker that has a seat. A knocked-out
  creature is not a kill, a second hit on a corpse does not count again. Workers
  count like other creatures. Creatures of the rogue seat (id 0) count as creatures
  killed by their killer. Kills by traps count for the seat of the trap.
- Heroes destroyed: same rule, but when the victim's seat plays the `Hero` faction
  (`SeatData::getFaction()`); such kills count only here, never as creatures killed.
  Creatures of an allied seat (same team id) are never counted.
- Rooms captured: `Room::claimForSeat` hands a room over tile by tile
  (`handTileOverToSeat`). A room counts as captured once, when the claiming seat
  takes the last remaining tile of a room whose seat is not allied to it. Taking
  only part of a room counts nothing. Rooms of the rogue seat count. Dungeon
  hearts cannot be claimed (`Room::isClaimable`).

## Packet

`ServerNotificationType::levelStatistics` (appended as the last enum value). It is
sent to the defeated human player only, right after `playerDefeated` inside
`Player::notifyNoMoreDungeonTemple`, as a snapshot of that moment (the game keeps
running for the others). Payload, in packet order:

| Field | Type |
|---|---|
| `elapsedSeconds` | `int32_t` |
| `levelWon` | `bool` (always false here, the message is sent on defeat) |
| `seatCount` | `int32_t` |
| per seat: `seatId` | `int32_t` |
| per seat: keepers defeated, creatures killed, heroes destroyed, rooms captured, items made, creatures converted | 6 x `uint32_t` |

Listed seats: every seat that has a player, except the rogue seat 0.

## Client

`ODClient::processServerNotification` reads the packet into `LevelStatistics`
(`source/game/LevelStatistics.h`: elapsed seconds, `levelWon`, vector of per-seat
entries) and keeps it in `ODClient`: `hasLevelStatistics()` and
`const LevelStatistics& getLevelStatistics() const`. The packet is ignored when the
client is not in the game mode, and the stored data is cleared when a new game
connection is accepted.

## Verification limits

`source/tests/check_level_statistics.py` compiles the production
`Seat::recordCreatureKill`, the kill part of `Creature::takeDamage`,
`Player::notifyNoMoreDungeonTemple` and the exact production statements of the
room capture, conversion, crafting and heart hooks against small mocks, and checks
the wiring (enum position, hook placement, client read order) in the sources.
`check_dungeon_heart_combat.py` covers the heart counter through the real
`takeHeartDamage`. The network round trip, the client handler and the real
counting in a running skirmish were not run.
