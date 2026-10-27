# Lava spa

The lava spa is a room of tier II (research `roomSpa`, after the tavern). One big pool of hot mud, heated by lava below,
fills the room. A creature in a bad mood or with a hangover goes bathing on its own. The bath lifts the mood, ends a
hangover and leaves the creature relaxed for a while. All numbers are keys of `config/rooms.cfg` (the `Spa` keys, each
documented in the header of the file) and `config/skills.cfg` (`roomSpa`, the effect `RelaxTime`); the price of a bath is
`BeerPrice` of `config/global.cfg` (block `[Tavern]`).

## The room

- A spa needs a block of at least `SpaMinRoomSide` x `SpaMinRoomSide` tiles (4 x 4); otherwise the keeper gets the notice
  "A lava spa needs at least 4x4 tiles." and nothing is paid. Selling tiles is always allowed.
- Pool tiles are the tiles whose eight neighbours belong to the same spa; the other tiles are the rim. A 4 x 4 spa has a
  pool of 4 tiles, 5 x 5 has 9, 5 x 7 has 15, 7 x 7 has 25. A creature takes a block of pool tiles of its bed size (1 x 1,
  1 x 2 in either direction, 2 x 2) in the order smaller y, then smaller x; places that are taken are never moved when the
  room grows or shrinks.
- Every pool tile shows mud with rising steam, every pool edge a stone rim with a glowing seam. The pool attendant's chair
  stands on the rim directly above the first pool tile, the springboard on the rim directly below the last pool tile. The
  pool and the rim can be walked on, the chair and the springboard are furniture.
- A bath costs `BeerPrice`. A switch in the spa window decides whether the keeper or the creature pays; spas of computer
  keepers let the creatures pay. If the bath cannot be paid the creature does not bathe, does something else and tries
  again later. A full pool has no queue: the creature goes to another spa or does something else.

## Bathing

- A creature that is no worker, not in prison and not in the hand wants a bath when its mood is Upset, Angry or Furious and
  its relaxation has run out, or when it has a hangover (a hangover ignores the relaxation).
- The bath lasts `SpaBathTurns` (14.2857, the counted turns reach it in the 15th turn). Every turn adds `SpaMoodPerTurn`
  (21) spa mood up to `SpaMoodMax` (300, so a bath restores only a part of a bad mood); the spa mood is one more part of the
  creature's mood, does not fade while the creature sits in the bath and fades by `SpaMoodDecayPerTurn` (0.4) per turn
  once the bath is over. One bath in `SpaCannonballChance` starts with a jump from the
  springboard (an arc of `SpaJumpTurns`, `SpaJumpHeight` tiles, then a mud splash). The bath is paid at the landing, before it starts; if it cannot be paid then, the creature gets its place back and does not bathe.
- At the end of the bath the creature is relaxed for `SpaRelaxTurns` (252; 302.4 and 352.8 with research levels 2 and 3):
  the points and experience it earns in the library, workshop and training hall and in the arena are multiplied by
  `SpaRelaxWorkFactor` (1.0567). Nothing in combat changes. The hangover ends at once and the creature writes the post
  "relaxed".
- The bath does not clean the creature. A creature that leaves the pool leaves mud on the next `SpaMudTrailTiles` (3) tiles
  it enters outside the pool, `SpaDirtPerBath` in total (times its dirt factor), so the tiles around the pool get dirtier.
- A bath that is broken off (fight, flight, knock-out, pick-up by the hand, room removed or taken over, tile sold) keeps the
  mood gained so far, gives no relaxation, leaves the hangover and returns no gold.

## Pool attendant

A pool attendant sits on the chair for fun and has no effect on the game. Every `SpaAttendantActMinSeconds` to
`SpaAttendantActMaxSeconds` seconds he whistles at a bather (only while someone bathes), waves his towel or dozes off and
nearly falls from the chair. Every `SpaAttendantCannonballMinSeconds` to `SpaAttendantCannonballMaxSeconds` seconds he
climbs down, walks to the springboard and jumps into a free pool place himself. He is not a creature, belongs to the
keeper of the room and changes owner with it.

## Research, window and Dungeonbook

- The research `roomSpa` costs 250 points and needs the tavern. Each level lengthens the relaxation (`RelaxTime`: 1.0, 1.2,
  1.4 times `SpaRelaxTurns`). The computer keeper builds the spa directly after the tavern.
- Clicking a spa opens a small window with the price of a bath and the switch for who pays.
- The Dungeonbook page of a creature shows one line per active effect, buffs first: "Buff: Relaxed" while the relaxation
  lasts and "Debuff: Hangover" while the hangover of the tavern lasts, each with the remaining time.

## Saves and tools

- Creature streams hold an optional block `[Spa] <spaMood> <relaxTurns> <mudTilesLeft> [/Spa]` after the `[Thirst]` block.
  The room stream holds `SpaPayer`, `PoolAttendant` and `SpaBathers` lines, so a running bath, a jump in the air and the
  attendant in the middle of an act continue where they stood. Files without them load.
- The checks are `check_spa_config.py`, `check_spa_rules.py`, `check_spa_layout.py`, `check_spa_streams.py` and
  `check_spa_assets.py` in `source/tests`.
- `levels/skirmish/TestSpa.level` is a small test map with a 5 x 5 spa, a dormitory, a 4 x 4 tavern, a treasury with 5000
  gold, the spa and the tavern researched, eight creatures of different body sizes and four workers.
