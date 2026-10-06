"""Wiring checks for the tier C gold visuals: workers climbing and tipping over the heap while pouring,
and the gold dust over completely filled treasuries (client only, no compiler needed)."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


render = read('source/render/RenderManager.cpp')
rules = read('source/render/TreasuryCreatureRules.h')
mesh = read('source/render/TreasuryGoldMesh.cpp')
particles = read('particles/TreasuryCoins.particle')

# Pour motion: render node only, started by the deposit message, reset when it ends or is cancelled.
assert 'startTreasuryPour(tile, level)' in render
assert 'updateTreasuryPours(timeSinceLastFrame)' in render
assert 'lift += goldHeight + pourRise' in render
assert 'cancelTreasuryPour(creature)' in render
assert 'creature->setPosition' not in render.split('void RenderManager::updateTreasuryPours')[1].split(
    'void RenderManager::cancelTreasuryPour')[0]
for name in ('pourRise', 'pourLean', 'pourSway', 'pourDuration'):
    assert name in rules

# Pour clips: the Kobold skeleton carries ClimbGold and PourGold, the code plays them and keeps the procedural
# motion as the fallback when a mesh has no such clips.
assert 'pourClimbClip = "ClimbGold"' in rules and 'pourTipClip = "PourGold"' in rules
assert 'pourClipPhase' in rules and 'pourClipTime' in rules
assert 'TreasuryCreatureRules::pourClipTime' in render and 'newPour.mEntity = entity' in render
assert 'it->mEntity == nullptr' in render
skeleton = (repo / 'models/Kobold.skeleton').read_bytes()
assert b'ClimbGold' in skeleton and b'PourGold' in skeleton

# Dust: same effect list, view test and detail option, own budget per room, only full piles.
assert 'updateTreasuryDust(timeSinceLastFrame)' in render
assert 'dustBudget(TreasuryGoldMesh::getDetail())' in render
assert 'collectFullPiles' in render and 'TreasuryGoldLayer::maxLevel' in mesh
assert 'particle_system TreasuryGoldDust' in particles
assert 'ReactionParticleSpark' in particles.split('particle_system TreasuryGoldDust')[1]

# Portal dust: the existing dust effect and budget, started from the dust timer, only for the local keeper's
# portals when rich; the threshold values live in the rules header.
portal = render.split('void RenderManager::startTreasuryPortalDust')[1].split('void RenderManager::updateTreasuryAmbient')[0]
assert 'RoomType::portal' in portal and 'isRichKeeper(seat->getGold(), seat->getGoldMax())' in portal
assert 'TreasuryEffectKind::dust' in portal and '"TreasuryGoldDust"' in portal
assert 'startTreasuryPortalDust();' in render.split('void RenderManager::updateTreasuryDust')[1].split('collectFullPiles')[0]
assert 'portalRichShare' in rules and 'portalRichMinGold' in rules and 'portalDustHeight' in rules
import re
settings = read('source/rooms/TreasurySettings.h')
share = float(re.search(r'portalRichShare = ([0-9.]+)f', settings).group(1))
min_gold = int(re.search(r'portalRichMinGold = ([0-9]+)', settings).group(1))
def rich(gold, gold_max):
    return gold_max > 0 and gold >= min_gold and gold >= share * gold_max
assert not rich(0, 0) and not rich(400, 400) and not rich(499, 600)
assert rich(500, 1000) and not rich(499, 1000) and rich(2000, 3000) and not rich(1400, 3000)

# Heart dust: same rule, effect list, budget and detail option as the portal dust, but its own height and its own
# particle system, only for the dungeon heart of the local keeper.
heart = render.split('void RenderManager::startTreasuryHeartDust')[1].split('void RenderManager::updateTreasuryAmbient')[0]
assert 'RoomType::dungeonTemple' in heart and 'isRichKeeper(seat->getGold(), seat->getGoldMax())' in heart
assert 'getLocalPlayer()->getSeat()' in heart and 'TreasuryEffectKind::dust' in heart
assert '"TreasuryHeartDust"' in heart and 'heartDustHeight' in heart
assert 'startTreasuryHeartDust();' in render.split('void RenderManager::updateTreasuryDust')[1].split('collectFullPiles')[0]
assert 'void startTreasuryHeartDust();' in read('source/render/RenderManager.h')
assert 'heartDustHeight' in rules
assert 'particle_system TreasuryHeartDust' in particles
assert 'ReactionParticleSpark' in particles.split('particle_system TreasuryHeartDust')[1].split('particle_system')[0]

# Thief gold: one trailing field in the creature packets (new and update), written and read at the end,
# only sent again when the amount changed; the client sack follows it. The old heap guess is gone.
creature = read('source/entities/Creature.cpp')
for name in ('exportToPacket(ODPacket& os, const Seat* seat) const', 'exportToPacketForUpdate(ODPacket& os, Seat* seat)'):
    body = creature.split('void Creature::' + name)[1].split('\n}\n')[0]
    assert body.rstrip().endswith('os << mGoldCarried;'), name
for name in ('importFromPacket(ODPacket& is)', 'updateFromPacket(ODPacket& is)'):
    body = creature.split('void Creature::' + name)[1].split('\n}\n')[0]
    assert 'OD_ASSERT_TRUE(is >> mGoldCarried);' in body, name
    assert body.index('importProgressFromPacket(is);') < body.index('is >> mGoldCarried'), name
assert 'mGoldCarried != mGoldCarriedNotified' in creature
assert 'rrRefreshCreatureGoldSack(this)' in creature
assert 'rrRefreshCreatureGoldSack(curCreature)' in render
for gone in ('startTreasuryThiefSack', 'updateTreasuryThiefSacks', 'thiefSackTime'):
    assert gone not in render and gone not in rules, gone
assert 'getMeshNameForGold(creature->getGoldCarried())' in render
print('ok')
