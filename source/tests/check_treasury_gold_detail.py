"""Wiring checks for the finer treasury gold visuals: coins and gems on the piles, overflow at the edges, scattered
coins on bare floors, glow and sparkle, dent and rolling coins, thieves carrying gold, the dungeon heart ring drawn
as piles. Client only, within the 'Treasury detail' option and its budgets (no compiler needed)."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


render = read('source/render/RenderManager.cpp')
header = read('source/render/RenderManager.h')
mesh = read('source/render/TreasuryGoldMesh.cpp')
rules = read('source/render/TreasuryCreatureRules.h')
layer = read('source/rooms/TreasuryGoldLayer.h')
treasury = read('source/rooms/RoomTreasury.cpp')
particles = read('particles/TreasuryCoins.particle')
material = read('materials/scripts/TreasuryGoldPile.material')

# Coins, gems and spilled coins: a second mesh section, only at the full detail, derived from the pile name alone.
assert 'material TreasuryGoldDetail' in material and 'ambient vertexcolour' in material
assert 'DetailMaterial' in mesh and 'buildPileMesh(sceneManager, name + ".mesh", shape, reduced ? 2 : 6, !reduced)' in mesh
for name in ('topCoinCount', 'gemCount', 'edgeOpen', 'spillCoinsPerEdge', 'hasFloorScatter', 'levelForClassicName', 'glowWeight'):
    assert name in layer and name in mesh + render + treasury
assert 'maxTopCoins' in layer and 'maxGems' in layer and 'maxSpillCoins' in layer

# Bare floor: the server names a level 0 pile for some empty tiles; the client draws nothing for it unless full.
assert 'hasFloorScatter(tile->getX(), tile->getY())' in treasury
assert 'mGoldChanged = true;\n    return new RoomTreasuryTileData' in treasury.replace('\r\n', '\n')
assert 'shape.mLevel == 0 && currentDetail != Detail::full' in mesh

# Dungeon heart ring: the classic stacks are drawn as piles on the client (server names and tests untouched).
assert 'pileNameForClassicStack' in render and 'replacesClassicStack' in render

# Rain over the whole tile, sliding, rolling and sparkling coins.
pour = particles.split('particle_system TreasuryCoinPour')[1].split('particle_system')[0]
assert 'emitter Box' in pour
for name in ('TreasuryCoinSlide', 'TreasuryCoinRoll', 'TreasuryGlint'):
    assert 'particle_system ' + name in particles
    assert '"' + name + '"' in render

# Dent and rolling coins on a pile that loses gold, growth on a pile that gains it (from the pile name only).
assert 'startTreasuryPileChange(node' in render and 'updateTreasuryPileSettles(timeSinceLastFrame)' in render
assert 'previousPileLevel' in render and 'int registerPile(' in read('source/render/TreasuryGoldMesh.h')
assert 'pileSettleScale' in rules and 'dentDepth' in rules

# Thieves carry a sack away from the heap they took; glow lights per patch.
assert 'startTreasuryThiefSack' in render and 'getStealGold() <= 0' in render
assert 'removeTreasuryThiefSack(curCreature)' in render
assert 'refreshTreasuryGlow' in render and 'glowOfPatch' in render and 'ROOM_LIGHT_MASK' in render

# Option and budgets: every new effect goes through the view test and a per-room budget; off draws nothing.
assert 'TreasuryEffectKind::ambient' in render and 'ambientBudget(TreasuryGoldMesh::getDetail())' in render
assert 'case TreasuryGoldMesh::Detail::full:' in rules.split('inline int ambientBudget')[1]
assert 'camera->isVisible' in render.split('void RenderManager::startTreasuryPileChange')[1].split('void RenderManager::updateTreasuryPileSettles')[0]
assert 'camera->isVisible' in render.split('void RenderManager::startTreasuryThiefSack')[1].split('void RenderManager::updateTreasuryThiefSacks')[0]
assert 'currentDetail == Detail::off' in mesh.split('Glow glowOfPatch')[1]

# The piles are lit by the glow but the creature walking code is not touched: no position written.
assert 'creature->setPosition' not in render.split('void RenderManager::startTreasuryThiefSack')[1].split('void RenderManager::refreshTreasuryGlow')[0]
print('ok')
