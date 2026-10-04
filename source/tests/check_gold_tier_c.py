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

# Dust: same effect list, view test and detail option, own budget per room, only full piles.
assert 'updateTreasuryDust(timeSinceLastFrame)' in render
assert 'dustBudget(TreasuryGoldMesh::getDetail())' in render
assert 'collectFullPiles' in render and 'TreasuryGoldLayer::maxLevel' in mesh
assert 'particle_system TreasuryGoldDust' in particles
assert 'ReactionParticleSpark' in particles.split('particle_system TreasuryGoldDust')[1]
print('ok')
