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
assert 'shape.mLevel == 0 && (currentDetail != Detail::full || farAway)' in mesh

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

# Local dent: at the full detail a taken pile shows a bowl where the gold was taken (a dynamic copy of the pile
# with a vertex offset, drawn in place of the entity while it settles), which fills up again; the entity is given
# back when the settle ends, when the entity goes away and when the renderer is cleared.
assert 'createDentedPile' in mesh and 'updateDentedPile' in mesh and 'dentedHeight' in mesh
assert 'object->setDynamic(true)' in mesh and 'object->beginUpdate(section)' in mesh
assert 'fillPile(object, shape, DentDivisions, true, &dent, true)' in mesh
change = render.split('void RenderManager::startTreasuryPileChange')[1].split('void RenderManager::updateTreasuryDents')[0]
assert 'createDentedPile(mSceneManager, pileMeshName' in change and 'node->detachObject(entity)' in change
assert 'settle.mLocalDent' in change and 'dentLocalDepth' in change
dents = render.split('void RenderManager::updateTreasuryDents')[1].split('void RenderManager::updateTreasuryPileSettles')[0]
assert 'localDentFactor' in dents
assert 'attachObject(it->mEntity)' in dents and 'destroyManualObject(it->mObject)' in dents
assert 'finishTreasuryDent(entityName);' in render.split('void RenderManager::cancelTreasuryPileSettle')[1].split('void RenderManager::registerBuriedObject')[0]
assert 'finishTreasuryDent(mTreasuryPileDents.back().mEntityName)' in render.split('void RenderManager::clearTreasuryEffects')[1]
assert 'updateTreasuryDents(timeSinceLastFrame)' in render
assert 'it->mTaken && !it->mLocalDent' in render
assert 'localDentFactor' in rules and 'dentRadius' in rules and 'dentLocalDepth' in rules

# Glow lights: one candidate per patch, but only the patches near the camera get a light, the nearest first, within a
# limit per room and in all; reduced detail allows few, off none. Counted again when the camera moved.
glow = render.split('void RenderManager::applyTreasuryGlowLights')[1].split('void RenderManager::setTreasuryGlowLight')[0]
assert 'glowViewDistance' in glow and 'glowLimitPerRoom(detail)' in glow and 'glowLimitTotal(detail)' in glow
assert 'std::sort(candidates.begin(), candidates.end())' in glow and 'getDerivedPosition()' in glow
assert 'updateTreasuryGlow(timeSinceLastFrame)' in render and 'glowUpdateInterval' in render
assert 'createLight' not in render.split('void RenderManager::refreshTreasuryGlow')[1].split('void RenderManager::updateTreasuryGlow')[0]
assert 'mRoom' in mesh.split('Glow glowOfPatch')[1] and 'glowLimitPerRoom' in rules and 'glowLimitTotal' in rules
assert 'case TreasuryGoldMesh::Detail::reduced:' in rules.split('inline int glowLimitTotal')[1]

# Level of detail by distance: piles beyond lodFarDistance use the reduced mesh (no coins and gems, nothing on a bare
# tile), return below lodFarDistance - lodHysteresis (no flipping), at most a few per check, never while settling;
# the new entity stays hidden while the room batch still shows the old one.
assert 'farAway && currentDetail == Detail::full' in mesh and 'bool farAway = false' in read('source/render/TreasuryGoldMesh.h')
lod = render.split('void RenderManager::updateTreasuryLod')[1].split('void RenderManager::updateTreasuryDents')[0]
assert 'lodReducedAt(it->second.mFar' in lod and 'lodSwitchesPerUpdate' in lod and 'isTreasuryPileSettling' in lod
assert 'destroyMesh(nodeType)' in lod and 'createMesh(nodeType)' in lod and 'hideUntilBatched' in lod
assert 'Detail::full' in lod.split('lodReducedAt')[0]
assert 'mTreasuryPiles.erase(curRenderedMovableEntity)' in render and 'updateTreasuryLod(timeSinceLastFrame)' in render
assert 'lodReducedAt(false' in render and 'prepareMesh(mSceneManager, meshName, pileFar)' in render
assert 'inline bool lodReducedAt' in rules and 'lodHysteresis' in rules
assert 'void TreasuryGoldBatch::hideUntilBatched' in read('source/render/TreasuryGoldBatch.cpp')

# Thieves show a sack sized by the gold the server sends with the creature packet; glow lights per patch.
assert 'rrRefreshCreatureGoldSack' in render and 'getStealGold() <= 0' in render
assert 'removeTreasuryThiefSack(curCreature)' in render
assert 'refreshTreasuryGlow' in render and 'glowOfPatch' in render and 'ROOM_LIGHT_MASK' in render

# Option and budgets: every new effect goes through the view test and a per-room budget; off draws nothing.
assert 'TreasuryEffectKind::ambient' in render and 'ambientBudget(TreasuryGoldMesh::getDetail())' in render
assert 'case TreasuryGoldMesh::Detail::full:' in rules.split('inline int ambientBudget')[1]
assert 'camera->isVisible' in render.split('void RenderManager::startTreasuryPileChange')[1].split('void RenderManager::updateTreasuryPileSettles')[0]
assert 'currentDetail == Detail::off' in mesh.split('Glow glowOfPatch')[1]

# The piles are lit by the glow but the creature walking code is not touched: no position written.
assert 'creature->setPosition' not in render.split('void RenderManager::rrRefreshCreatureGoldSack')[1].split('void RenderManager::refreshTreasuryGlow')[0]
print('ok')
