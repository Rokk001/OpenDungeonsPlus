#!/usr/bin/env python3
"""Non-compiling wall-worker source contracts and geometry/yield regression cases.

The integrator must still verify simultaneous digging in the running game.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

def value(config, name):
    return float(re.search(r"^\s*" + re.escape(name) + r"\s+([\d.]+)", config, re.M).group(1))

config = read("config/global.cfg")
assert value(config, "NbWorkersDigSameFaceTile") == 3
assert "mNbWorkersDigSameFaceTile(3)" in read("source/utils/ConfigManager.cpp")
tile = read("source/entities/Tile.cpp")
header = read("source/entities/Tile.h")
creature = read("source/entities/Creature.cpp")
dig = read("source/creatureaction/CreatureActionDigTile.cpp")
assert "std::vector<std::array<const Creature*, 3>> mWorkersDigging" in header
assert "mWorkersDigging[i][slot] == nullptr && worker.wallDigPath" in tile
assert "mWorkersDigging[i][slot] != nullptr || !worker.wallDigPath" in tile
assert "mWorkersDigging[i][slot] = &worker" in tile
assert "if(reserved == &worker)" in tile and "reserved = nullptr" in tile
assert "slot < ConfigManager::getSingleton().getNbWorkersDigSameFaceTile()" in tile
assert "if(!getIsOnServerMap())" in tile[tile.index("bool Tile::addWorkerDigging"):]
assert "getWorkerDiggingSlot(creature, tilePos) < 0" in dig
assert "if(!creature.parkToWallTile(&tileDig, &tilePos))" in dig
assert "tileDig.getX() - tilePos.getX(), tileDig.getY() - tilePos.getY()" in dig
assert "path, false, true)" in creature[creature.index("bool Creature::parkToWallTile"):]
assert "RoomObjectNavigation::blocked(*this, path)" in creature
assert "path.back() != point" in creature
assert "!RoomObjectNavigation::refine" not in creature[creature.index("bool Creature::wallDigPath"):creature.index("bool Creature::parkToWallTile")]
assert "current.squaredDistance(desired) > 0.0025f" in dig
assert "isWorkerDiggingPositionFree" not in tile
assert "mWorkerDigPositions[&worker] = path.back()" in tile
assert "facing * 0.2f + sideways * offset" in creature
assert "-1.0f / 3.0f : 1.0f / 3.0f" in creature

# Capacity and released-slot reuse are per face, independent of worker count
# on other faces; a blocked candidate cannot become a reservation.
slots = [[None] * 3 for _ in range(4)]
def reserve(face, worker, reachable=(True, True, True)):
    for index in range(3):
        if slots[face][index] is None and reachable[index]:
            slots[face][index] = worker
            return index
    return None
for count in (1, 2, 3):
    assert reserve(0, count) == count - 1
assert reserve(0, 4) is None
assert reserve(1, 4) == 0
slots[0][1] = None
assert reserve(0, 5) == 1
assert slots[0] == [1, 5, 3]
assert reserve(2, 6, (False, False, False)) is None
assert reserve(2, 6, (False, True, False)) == 1

# All centers stay in one tile for all faces, even with solid side walls.
for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    points = [(dx * 0.2 - dy * offset, dy * 0.2 + dx * offset)
              for offset in (0, -1/3, 1/3)]
    assert len(set(points)) == 3
    assert all(-0.5 < x < 0.5 and -0.5 < y < 0.5 for x, y in points)
    assert all(round(x) == 0 and round(y) == 0 for x, y in points)

# Per-worker mining: other walls are dug by the dig rate of the worker, a gold wall pays gold per step (not
# depending on the worker), the last step pays what is left and the worker carries the whole part of the gold
# (the fraction stays in its remainder).
assert "tileDig.digOut(creature.getDigRate())" in dig
assert "tileDig.digOutGold()" in dig
assert "payMinedGold(creature, tileDig, amountDug)" in dig
assert "payMinedGold(creature, tileDig, gemGoldPerDigStep)" in dig
assert "creature.addGoldCarriedFraction(gold)" in dig
assert "digCoefGold" not in dig and "digCoefGem" not in dig
assert "digRateScaled = mFullness" in tile
assert "double Tile::digOutGold()" in tile
assert "return remaining;" in tile[tile.index("double Tile::digOutGold()"):]
assert value(config, "GoldPerSeamTile") == 3000
assert value(config, "GoldPerDigStep") == 25
assert value(config, "GemGoldPerDigStep") == 16.67


def mine_gold_tile(density, skirmish=100):
    """Mirrors Tile::digOutGold for one tile; returns the paid step amounts."""
    total = value(config, "GoldPerSeamTile") * density / 100.0 * skirmish / 100.0
    step = value(config, "GoldPerDigStep") * density / 100.0 * skirmish / 100.0
    fullness, paid = 100.0, []
    while fullness > 0.0:
        remaining = fullness / 100.0 * total
        if remaining - step <= 0.001:
            paid.append(remaining)
            fullness = 0.0
        else:
            fullness = (remaining - step) / total * 100.0
            paid.append(step)
    return paid


for density in (50, 100, 150):
    paid = mine_gold_tile(density)
    assert len(paid) == 120
    assert abs(sum(paid) - 3000.0 * density / 100.0) < 0.01
assert abs(sum(mine_gold_tile(100, 50)) - 1500.0) < 0.01
# Three workers share a tile: every step is paid to the worker that made it, the sum is the tile gold
carried = [0, 0, 0]
remainder = [0.0, 0.0, 0.0]
for index, amount in enumerate(mine_gold_tile(150)):
    worker = index % 3
    remainder[worker] += amount
    whole = int(remainder[worker])
    remainder[worker] -= whole
    carried[worker] += whole
assert abs(sum(carried) + sum(remainder) - 4500.0) < 0.01
# A gem step pays 16.67 whatever the worker level; three steps carry 50 and keep a fraction
gem_remainder, gem_carried = 0.0, 0
for _ in range(3):
    gem_remainder += value(config, "GemGoldPerDigStep")
    whole = int(gem_remainder)
    gem_remainder -= whole
    gem_carried += whole
assert gem_carried == 50 and 0.0 < gem_remainder < 1.0
movement = read("source/entities/MovableGameEntity.cpp")
assert "ServerNotificationType::animatedObjectSetWalkPath" in movement
assert "serverNotification->mPacket << v" in movement
assert "ServerNotificationType::setObjectAnimationState" in movement
assert "serverNotification->mPacket << true << direction" in movement
print("Wall dig workers: source contracts, 1/2/3/4 assignment, slot reuse, blocked spots, worker geometry, additive finite/vein yield and replication passed")
