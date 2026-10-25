# Dirt, cleaning and toilets

Creatures eat and drink, so they need the toilet. Rooms get dirty with use, fights leave blood, and
workers clean as a side job. All numbers are keys of `config/global.cfg` (block `[Dirt]`),
`config/rooms.cfg` (`...DirtPer...` keys) and `config/creatures.cfg` (`UrgeGrowth/Turn`, `Cleanliness`,
`DirtFactor`); each key is documented in the header of its file.

## Tile dirt and stages

- Every floor tile of a room and every claimed corridor tile carries dirt from 0 to 100
  (`Tile::getDirt`). Rock, water, lava, gold and walls never carry dirt. A sold or destroyed room
  keeps the dirt of its floor.
- The dirt stage of a room comes from the mean dirt of its tiles: stage 1 below `DirtStage2At`
  (clean), stage 2 below `DirtStage3At` (dirty), stage 3 above (filthy). The same thresholds applied to
  one tile value give the decal that is drawn on the floor (`DirtStage1/2/3.mesh`); stage 3 adds
  flies.
- The server tells each human player the stages of the tiles and rooms in sight (cosmetic event
  `tileDirt`), a change after `DirtSyncTurns` turns, a full resend every `DirtResyncTurns` turns.

## Where dirt comes from

- Using a room: every use adds the room's `...DirtPer...` key, times the `DirtFactor` of the
  creature type, to the tile the creature stands on. Treasury, portals, dungeon heart, bridges and
  crypt make none. The keys follow one formula (see `tools/balance/dirt_values.py`): a quarter of one
  worker's time keeps a reference dungeon in balance.
- Fights: every landed blow adds `CombatDirtPerHit` to the tile of the target, every death leaves a
  blood stain that dries after `BloodDryTurns`, and a corpse adds dirt every turn while it lies there.
- Trails: workers carrying a load, workers pulling a wounded creature and dirty creatures add
  `TrailDirtPerTile` to every tile they enter. A creature gets dirty after a fight (`CreatureDirtPerFightWon`),
  more when it is knocked out (`CreatureDirtPerKo`), and is always filthy in a prison or when tortured.

## Piles and urge

- A creature has an urge from 0 to 100. It grows by `UrgeGrowth/Turn` of its type (workers, the
  undead and the Champion never feel it) and by `UrgePerChicken` for every chicken eaten.
- From `UrgeSeek` the creature looks for a free seat in a toilet room; from `UrgeOnTheWay` it uses a
  free seat it walks over; with no toilet room nothing happens until `UrgeRelieve`. Then it
  relieves itself where it stands (in a treasury, the heart room or a temple it steps out first) and
  leaves a pile with the look of its type. A pile sets its tile to full dirt and stays until a
  worker cleans it.

## Effects

- Output: library and workshop points, training experience, sleep recovery, casino mood, temple
  mana and arena experience are multiplied by the room's output factor (`DirtOutputStage2/3`); the
  hatchery lays slower; prison damage and the time to convert in a torture chamber change with the
  stage (`PrisonDirtDamageStage2/3`, `TortureDirtConvertStage2/3`) - prisons and torture chambers
  profit from dirt.
- Mood: a creature in a dirty room loses `DirtMoodStage2/3`, and it loses `DirtPileMood` for every
  pile within `DirtPileRadius` tiles, both times the `Cleanliness` of its type. Free heroes and
  creatures without a seat have no mood; blood and the crypt give none.

## Cleaning

- At most `CleaningWorkerSharePercent` of the workers clean (the first one always may, the same
  counting as the trap reloading share), only while the keeper has a pile or a room from stage
  `CleanRoomFromStage` to clean. Cleaning comes first in the list of the workers' jobs but never
  replaces digging, claiming, carrying or reloading, which stay in the list after it.
- A worker walks to the nearest pile, else the dirtiest tile of the nearest dirty room (the toilet room
  first), else a dirty corridor tile, and removes `ClaimRate x 100 x CleanRateFactor` dirt per turn
  (at most `CleaningMaxTurnsPerTile` turns per tile).
- Prison, torture chamber and crypt are never cleaned by workers. The keeper can order one cleaning
  of a prison or torture chamber with the button "Clean" in the window that opens when its tile is
  clicked; the order ends when the room is clean.

## Saves and tools

- Creature streams hold an optional block `[Needs] <urge> <dirt> [/Needs]`; level and save files hold
  the optional sections `[Dirt]` (`x y dirt`) and `[DirtPiles]` (`kind creatureClass x y dirtLeft ageTurns`)
  after the gift boxes; prison and torture rooms end with `CleanOrder <0|1>`. Files without them load.
- `python tools/balance/dirt_values.py --check` recomputes the per-room keys and holds the config to
  them. The checks are `check_dirt_values.py`, `check_dirt_rules.py`, `check_dirt_streams.py`,
  `check_dirt_assets.py` and `check_toilet_room.py` in `source/tests`.
- `levels/skirmish/TestCleaning.level` is a small test map with a toilet room, a dirty workshop and
  library, piles, a blood stain, a prison, six workers and eight fighters.
