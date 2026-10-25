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

- The first tile of a tavern is the counter with the innkeeper figure (not a creature); the other tiles are
  places to drink with kegs along the walls and tables inside. One guest stands on each place.
- A drink takes `DrinkTurns` turns. The keeper chooses per tavern who pays for the beer: the keeper (treasury)
  or the creature (its own purse). If the payer cannot pay, the guest gets water (a creature that cannot pay
  also loses `NoCoinMood` mood). Beer adds drunkenness, mood and urge; water only a little urge.
- After a drink the guest takes another one with `NextDrinkPercent` / 2 per further drink, at most
  `MaxDrinksPerVisit` per visit. Drunkenness falls by `DrunkDecayPerTurn`; from `StaggerAt` the creature walks
  slower, from `VomitAt` it vomits once per drunk episode (a dirt pile that workers clean). A creature that falls
  asleep above `HangoverAt` wakes up with a hangover (`HangoverTurns`: half work and experience, less mood).
- After the last drink a guest plays a game with `GameChancePercent` when a neighbour is done as well: arm
  wrestling, dice or (with Beer) a slap duel. Games cost no gold. The weaker creature has the better chance than
  its level suggests (`GameUnderdog...`). In a slap duel a normal slap takes `SlapDamage` hit points, a critical
  slap (`SlapCritBasePercent` plus `SlapCritPerLevel` per level of difference) ends the duel, and so does
  falling below `SlapDuelLoseBelowHp`. The loser lies `DuelKoTurns` turns and then goes to bed.
- Beer research levels 2 and 3 shorten the portal cooldown (research effect `PortalCooldown`).

## Saves and tools

- Creature streams hold an optional block `[Thirst] <thirst> <tavernMood> <tavernMoodTurns> <drunk> <vomited>
  <hangoverTurns> [/Thirst]` after the `[Needs]` block; the room stream holds `TavernPayer`, `Innkeeper`,
  `Counter`, `Spot` and `Game` lines, so a running game continues where it stood. Files without them load.
- The checks are `check_tavern_config.py`, `check_tavern_rules.py`, `check_tavern_room.py`,
  `check_tavern_streams.py` and `check_tavern_assets.py` in `source/tests`.
- `levels/skirmish/TestTavern.level` is a small test map with a tavern, a hatchery, a casino, a treasury with
  5000 gold, Beer researched and eight creatures with 300 gold and thirst 70. `TestTavernNone.level` has the same
  creatures without a tavern and with the tavern research switched off.
