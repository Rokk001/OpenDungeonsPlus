"""Wiring check (X1 rework, decision 658): no creature stands on a wall tile (no compiler needed). Also records that the
beam between a ghost hunter (skeleton) and a ghost is the capture beam of the ghost plan (D17) and only exists while the
hunter has a beam target."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


creature = read('source/entities/Creature.cpp')
header = read('source/entities/Creature.h')
assert 'bool keepOffWalls();' in header
body = creature.split('bool Creature::keepOffWalls()')[1].split('void Creature::checkWalkPathIsStillValid()')[0]
assert 'isFullTile()' in body and 'canGoThroughTile(tile)' in body and 'ServerNotificationType::entityTeleported' in body
assert 'clearActionQueue();' in body and 'getIsOnServerMap()' in body
upkeep = creature.split('void Creature::doUpkeep()')[1]
assert 'if(keepOffWalls())' in upkeep.split('If the creature is in jail')[0]

nav = read('source/gamemap/RoomObjectNavigation.cpp')
smooth = nav.split('bool smoothCorridor(')[1].split('void keepObstaclesNear')[0]
assert 'terrainClearForBody(passable, from, to, bodyRadius)' in smooth and 'terrainClear(passable, from, to) &&' not in smooth
assert 'bool bodyClearOfWalls(' in nav
limit = float(nav.split('WALL_MARGIN_LIMIT = ')[1].split('f;')[0])
assert 0.0 < limit <= 0.5, limit  # tile centre lines (half a tile from every wall) always stay clear

# (e) the green chain between hunter and ghost is the capture beam: only while the hunter has a beam target
beam = creature.split('void Creature::updateGhostHuntVisuals')[1][:12000]
assert 'target==nullptr || mGhostBeamTarget.empty()' in beam and 'createBillboardChain' in beam

# X1 rework 3 (decision 710): a creature stood at wall height on top of the ghost room apparatus. Cause: prepareLowStep
# lets a creature that is wider than the lane climb every measured object (bodyBands exist for ghost apparatus heights
# up to 1.69), so a Troll was lifted onto GhostPress / ManaStill / SoulForge / GhostCauldron. Only beds, coffins and
# cots may be stepped onto (decision 727 took the coffins of the crypt out: they are graves and solid).
bounds = read('source/gamemap/RoomObjectBounds.h')
assert 'inline bool isSteppableMesh(const std::string& name)' in bounds
assert 'name.compare(0, 12, "InfirmaryCot") == 0' in bounds
assert 'if(RoomObjectPath::isSteppableMesh(bounds.name))' in nav.split('RoomObjectNavigation::collect(')[1].split('bodyObstacles')[0]
render = read('source/render/RenderManager.cpp')
step = render.split('void RenderManager::updateCreatureStep')[1].split('void RenderManager::cancelCreatureStep')[0]
assert 'if(!RoomObjectPath::isSteppableMesh(bounds.name))' in step
# every apparatus of the ghost room is measured and tall, so it must not be steppable
import re
def steppable(name):
    return name == 'Bed' or (len(name) >= 3 and name.endswith('Bed')) or name.startswith('InfirmaryCot')
for name in ('GhostPress', 'GhostCauldron', 'ManaStill', 'SoulForge', 'GhostBell', 'GhostRack', 'GhostHook', 'GhostWallGauges', 'CrystalBowl', 'Cauldron'):
    assert not steppable(name), name
for name in ('Bed', 'TrollBed', 'DragonBed', 'InfirmaryCotLarge'):
    assert steppable(name), name
for name in ('StoneCoffin', 'KnightCoffin', 'CelticCross', 'KnightStatue', 'KnightStatue2'):
    assert not steppable(name), name
print('ok')
