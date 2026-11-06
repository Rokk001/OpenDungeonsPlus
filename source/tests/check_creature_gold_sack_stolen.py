"""Wiring check: the gold sack of a creature shows only stolen gold, hangs at the belt, and the stolen amount is
saved, sent to the clients and spent last (no compiler needed)."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


NL = chr(10)


def read(path):
    return (repo / path).read_text(encoding='utf-8')


header = read('source/entities/Creature.h')
creature = read('source/entities/Creature.cpp')
render = read('source/render/RenderManager.cpp')

# Only stolen gold is a stolen amount: the two theft paths add it, the wage path adds plain gold.
assert 'creature.addGoldStolen(gold);' in read('source/creatureaction/CreatureActionStealFreeGold.cpp')
assert 'creature.addGoldStolen(gold);' in read('source/gamemap/LevelScriptRunner.cpp')
fee = read('source/creatureaction/CreatureActionGetFee.cpp')
assert 'creature.addGoldCarried(goldTaken);' in fee and 'addGoldStolen' not in fee

# Payments take other gold first and stolen gold last: every spend clamps the stolen part to the purse.
add = header.split('inline void addGoldCarried(double gold)')[1].split('inline double getGoldStolen')[0]
assert 'mGoldCarried += gold;' in add and 'clampGoldStolen();' in add
clamp = header.split('inline void clampGoldStolen()')[1].split('}\n')[0]
assert 'mGoldStolen > mGoldCarried' in clamp
assert 'mGoldCarried = 0; mGoldStolen = 0;' in header
assert 'mGoldCarried -= deposited;' not in creature and 'addGoldCarried(-deposited);' in creature
assert 'mGoldCarried = capacity;\n    clampGoldStolen();' in creature

# Saved and loaded with the creature, and sent as the last field of both creature packets.
assert 'os << "\\t[Stolen] " << mGoldStolen << " [/Stolen]";' in creature
assert 'if(appearanceToken == "[Stolen]")' in creature and 'setGoldStolen(stolenLoaded);' in creature
ghost_out = ('mGhostThrowTarget << mGhostThrowTurns;' + NL + '    // The stolen part of the carried gold is the last field of the creature packets (it sizes the thief sack)' + NL
             + '    os << mGoldStolen;' + NL + '}')
assert creature.count(ghost_out) == 2
ghost_in = ('mGhostThrowClientTurns=mGhostThrowTurns;' + NL + '    OD_ASSERT_TRUE(is >> mGoldStolen);' + NL + '    clampGoldStolen();')
assert creature.count(ghost_in) == 2

# The sack follows the stolen gold only, for every creature (not only the ones with a steal rate), and hangs at the belt.
body = render.split('void RenderManager::rrRefreshCreatureGoldSack')[1].split('void RenderManager::removeTreasuryThiefSack')[0]
assert 'getGoldStolen()' in body and 'getGoldCarried()' not in body and 'getStealGold()' not in body
height = float(render.split('TreasuryThiefSackHeightFactor = ')[1].split('f;')[0])
assert height <= 0.55, height
# X1 rework (E8): the sack hangs at the hip inside the body box, not at the arm tip (the box includes arms and weapons).
side = float(render.split('TreasuryThiefSackSideFactor = ')[1].split('f;')[0])
assert 0.0 < side <= 0.35, side
assert 'TreasuryThiefSackSideMaxHeightFactor' in body and 'creatureBox.getMaximum().x * TreasuryThiefSackSideFactor' not in body
assert 'creatureBox.getMinimum().z + boxHeight * TreasuryThiefSackHeightFactor' in body
print('ok')
