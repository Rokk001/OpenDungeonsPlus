# AI levels

The skirmish seat page offers three computer levels (easy, normal, hard). They are built in
`source/ai/AIFactory.cpp` as `KeeperAI` instances. The levels follow the nine computer
personalities of the reference game: hard = Master Keeper (index 0), normal = Greyman (4),
easy = Idiot (5).

## Numbers taken from the reference rows

| Parameter (`KeeperAI`)                         | easy (Idiot) | normal (Greyman) | hard (Master Keeper) |
|------------------------------------------------|--------------|------------------|----------------------|
| `minFightersToAttack` (attack with more than N creatures) | 15 | 15            | 15                   |
| `minCreatureLevel` (minimum level for an attack) | 2          | 5                | 8                    |
| `minHpPercentToFight` (retreat at health, %)   | 20           | 20               | 10                   |

The reference table really has the same attack count (15) for the three rows; it is the minimum
creature level (2 / 5 / 8) that separates them. The reference starts an attack when the AI has more
non-worker creatures than the count, and it does not attack while more creatures than the minimum
level number are below that level. The fork does the same: `KeeperAI::handleAttack` needs more
healthy fighters than `minFightersToAttack` and waits while more than `minCreatureLevel` healthy
fighters are below level `minCreatureLevel`. The reference also sends the weak creatures home; the
fork does not, they join the call to war.

Before this change the values were 12/8/5 attackers and 70/50/30 percent.

## Own values (no counterpart in the reference)

- `reactionPercent` (scale of all AI cooldowns): 150 / 100 / 60.
- The cooldowns for defense, saving wounded creatures and looking for rooms.
- `maxTrapTiles` 2 / 5 / 8 and `maxDoors` 1 / 3 / 5. The reference has a chance of using traps and
  doors (99, 50, 25 percent for the balanced group) instead of a count; the chance is not built.
- Retreat of a whole attack at 50 percent of the fighters lost.

## Reference fields that are not built

Threat superiority needed over the enemy, share of the
creatures used in the first fight, call to arms threshold and removal rules, trap and door usage
chance, delay before placing a researched room, maximum imps, imprison percentage, openness,
wait after an attack, the "only attack attackers" and "never attack" flags, and the other economy
fields (mining until, exploring, dig policies). The six other personalities (Conqueror, Psychotic,
Stalwart, Guardian, Thick Skinned, Paranoid) are not offered; no new levels were added.

The check `source/tests/check_ai_levels.py` verifies the table above against the factory.
