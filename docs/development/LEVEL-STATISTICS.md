# Level statistics (server counters and debriefing data)

## Purpose

The server counts a few per-seat values during a level and sends a snapshot to a
defeated human player, so the client can fill a debriefing table with one column
per seat. The defeat debriefing shows them as a table (see "Debriefing table").

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

## Debriefing table

`GameMode::showDefeatDebriefing` fills the hidden container `Panel/StatisticsArea` of
`gui/WindowDefeatDebriefing.layout` (now a `OD/MenuScrollablePane`, the scrolling
widget of the settings windows, so more rows or a small window scroll instead of
being cut off) when `ODClient::hasLevelStatistics()` is true.

- `source/modes/DebriefingTable.h` holds the pure part: `buildDebriefingTable` turns
  `LevelStatistics` into rows (label plus one cell per seat, in the order of the
  packet, with the seat id and the number as text), and small helpers give the CEGUI
  area strings and the colour text. No seats gives no rows and the area stays hidden.
- `GameMode::fillDefeatStatistics` only creates `OD/StaticText` windows from those
  rows inside the area: a label on the left (40 % of the width) and one centred number
  per seat in the rest, 26 px per row. It destroys nothing itself: the windows are
  children of the debriefing window and go with it.
- Rows, in this order: Enemy keepers defeated, Enemy creatures killed, Heroes
  destroyed, Rooms captured, Items made, Creatures converted.
- Colour: each number is drawn in the colour of its seat, `Seat::getColorValue()` of
  the seat the client's `GameMap` knows under that id (`TextColours` property). A seat
  the client does not know is drawn in white. There is no column header, as in the
  reference: the colour identifies the seat.
- "Level won" and "Time elapsed" use the packet (`levelWon`, `elapsedSeconds`, the
  snapshot at defeat time) when statistics were received, and the client's own values
  (not won, turn number over turns per second) otherwise.

Rows deliberately left out: mana saved, creatures commanded and creature level
trained. The reference game shows them, but what they count is not established, so a
wrong number would be worse than none. Rank and score are left out for the same reason.

## Verification limits

`source/tests/check_level_statistics.py` compiles the production
`Seat::recordCreatureKill`, the kill part of `Creature::takeDamage`,
`Player::notifyNoMoreDungeonTemple` and the exact production statements of the
room capture, conversion, crafting and heart hooks against small mocks, and checks
the wiring (enum position, hook placement, client read order) in the sources.
`check_dungeon_heart_combat.py` covers the heart counter through the real
`takeHeartDamage`. The network round trip, the client handler and the real
counting in a running skirmish were not run.

`source/tests/check_defeat_debriefing.py` checks the pure table (row order and labels,
one cell per seat in packet order, numbers, no seats gives no rows and a hidden area),
that the packet values replace the client values for "Level won" and the time, and, with
mocked windows, the windows created for the rows and the colour set on each cell. What
is not verified because the game was not run: how the table looks (column widths, the
26 px row height, font size, that the scrolling pane shows no scrollbar for six rows
inside the 480 px panel, that the `TextColours` property with a single AARRGGBB value is
taken by the static text skin) and the real seat colours.
