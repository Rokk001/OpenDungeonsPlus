# Tavern and thirst

Creatures get thirsty like they get hungry. A tavern room quenches the thirst: it serves water for free and,
once the keeper has researched Beer, beer for gold. All numbers are keys of `config/global.cfg` (block
`[Tavern]`), `config/rooms.cfg` (`TavernCostPerTile`, `TavernHP`, `TavernDirtPerDrink`), `config/creatures.cfg`
(`ThirstGrowth/Turn`, the `Thirst` mood line, the `Tavern` room affinity) and `config/skills.cfg` (`roomTavern`,
`tavernBeer`, the portal cooldown effect); each key is documented in the header of its file.

## Thirst

- A creature type that has a `Hunger` mood line also has thirst (0 - 100). It grows by `ThirstGrowth/Turn`
  (the same value as `HungerGrowth/Turn`) and costs mood like hunger (the `Thirst` mood line has the numbers of
  the `Hunger` line). Types without a `Hunger` line (workers, Skeleton, Champion) have `ThirstGrowth/Turn 0`,
  no `Thirst` line and `Tavern 0 0`: they never get thirsty and never visit a tavern.
- From `ThirstSeek` on a creature looks for a tavern of its keeper; idle creatures also visit by their room
  affinity (the `Tavern` line has the likeness of the `Casino` line). Without a tavern the thirst only costs mood
  and the keeper gets a notice (at most one per `TavernNoticeSeconds`).
- Rogue creatures, heroes without a keeper and workers have no thirst. Prisoners keep the mood malus.

## The room

- The first tile of a tavern is the counter with the innkeeper figure (not a creature). Kegs stand along the
  walls (at most one per six tiles, never two side by side) and tables are spread over the room (at most one per
  eight tiles, preferably with free floor on both bench sides). A table is two tiles long and has two benches with four places each; a large creature (a bed of
  two by two tiles) takes two neighbouring places, half of a bench. A creature without a free place does not
  enter: it tries another tavern of its keeper, otherwise it goes back to work until its visit lock is over.
- A tavern needs a block of three by three tiles. One that loses it takes no guests until it has one again, and
  its room information says why. When a tavern grows or shrinks, the furniture is spread again, all guests stand
  up, running games end without a winner and the guests look for a place again.
- A beer takes `BeerDrinkTurns` turns (30 seconds), a water `WaterDrinkTurns` turns (10 seconds); the guest holds a mug in its hand and the
  drink clip loops for the whole drink. The keeper chooses per tavern who pays for the beer: the keeper (treasury)
  or the creature (its own purse). If the payer cannot pay, the guest gets water (a creature that cannot pay
  also loses `NoCoinMood` mood). Beer adds drunkenness, mood and urge; water only a little urge.
- A creature that is not thirsty comes for a leisure visit. It gives at most `PleasureVisitMax` of rooms.cfg (200) mood
  from beer, games and no coin together; at its end a visit that gained mood starts the pleasure buff (`PleasureBuffMood`
  over `SpaRelaxTurns`), and the tavern is closed to the creature for `TavernLeisureCooldownTurns`. A creature with a
  running pleasure buff or a closed tavern does not come for leisure. A thirsty creature may always come for a drink: a
  drink visit gives `BeerMood` per beer, but no pleasure buff, no lock and no limit.
- After a drink the guest takes another one with `NextDrinkPercent` / 2 per further drink, at most
  `MaxDrinksPerVisit` per visit. Drunkenness falls by `DrunkDecayPerTurn`; from `StaggerAt` the creature walks
  slower, from `VomitAt` it vomits once per drunk episode (a dirt pile that workers clean). A creature that falls
  asleep above `HangoverAt` wakes up with a hangover (`HangoverTurns`: half work and experience, less mood).
- After the last drink a guest plays a game with `GameChancePercent` when a guest at the same table is done as well (it
  waits while another guest of its keeper still drinks at its table): arm
  wrestling, dice or (with Beer) a slap duel. Games cost no gold. The weaker creature has the better chance than
  its level suggests (`GameUnderdog...`). In a slap duel a normal slap takes `SlapDamage` hit points, a critical
  slap (`SlapCritBasePercent` plus `SlapCritPerLevel` per level of difference) ends the duel, and so does
  falling below `SlapDuelLoseBelowHp`. The loser falls onto a free floor tile next to its bench (on its seat
  when none is free), lies `DuelKoTurns` turns and then goes to bed. Guests within `GameSpectatorRadius` cheer.
- Beer research levels 2 and 3 shorten the portal cooldown (research effect `PortalCooldown`).

## Saves and tools

- Creature streams hold an optional block `[Thirst] <thirst> <tavernMood> <tavernMoodTurns> <drunk> <vomited>
  <hangoverTurns> [/Thirst]` after the `[Needs]` block; the room stream holds `TavernPayer`, `Innkeeper`,
  `Counter`, `SeatLayout`, `Furniture`, `Spot` and `Game` lines, so the kegs and tables stand where they stood
  and a running game continues. Files without them load. A room without `SeatLayout 2` (saved before the tables
  were two tiles long) spreads its furniture again, ends its games and lets its guests look for a place.
- The checks are `check_tavern_config.py`, `check_tavern_rules.py`, `check_tavern_room.py`,
  `check_tavern_streams.py` and `check_tavern_assets.py` in `source/tests`.
- `levels/skirmish/TestTavern.level` is a small test map with a tavern, a hatchery, a casino, a treasury with
  5000 gold, Beer researched and eight creatures with 300 gold and thirst 70. `TestTavernNone.level` has the same
  creatures without a tavern and with the tavern research switched off.
