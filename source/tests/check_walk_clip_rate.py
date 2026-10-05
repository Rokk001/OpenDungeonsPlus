#!/usr/bin/env python3
"""Pure check (nothing compiled, nothing started): the optional key WalkClipRate of config/creatures.cfg is parsed,
copied, streamed and dumped like LowHealthWalkSpeedFactor, limited to 0.3 - 3.0, applied only to the client clip speed
of the walk state (Walk, WalkHurt, CarryWalk), never to the move speed, and set for the types whose feet slide."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]

def read(path):
    return (root / path).read_text(encoding='utf-8').replace('\r\n', '\n')

definition = read('source/entities/CreatureDefinition.cpp')
definition_h = read('source/entities/CreatureDefinition.h')
creature = read('source/entities/Creature.cpp')
creatures_cfg = read('config/creatures.cfg')

# Definition: default 1, copy, stream (same place after the low health factor, same order for out and in), parse, dump
assert 'mWalkClipRate (1.0)' in definition and 'mWalkClipRate(def.mWalkClipRate)' in definition
assert definition.index('os << c->mLowHealthWalkSpeedFactor;') < definition.index('os << c->mWalkClipRate;') < definition.index('os << c->mXPTable') \
    if 'os << c->mXPTable' in definition else True
assert definition.index('is >> c->mLowHealthWalkSpeedFactor;') < definition.index('is >> c->mWalkClipRate;')
assert 'nextParam == "WalkClipRate"' in definition and 'creatureDef->mWalkClipRate = Helper::toDouble(nextParam);' in definition
assert '"    WalkClipRate' in definition and 'mWalkClipRate != 1.0' in definition
assert 'std::max(0.3, std::min(3.0, mWalkClipRate))' in definition_h and '#include <algorithm>' in definition_h

# Applied only to the client clip speed of the walk state, not to the move speed
pose = creature[creature.index('double Creature::getClientPoseSpeedFactor'):creature.index('double Creature::getPhysicalDefense')]
assert '(getAnimationStateName() == EntityAnimation::walk_anim)' in pose and 'getWalkClipRate()' in pose
assert 'getWalkClipRate' not in creature[:creature.index('double Creature::getClientPoseSpeedFactor')]
assert 'getWalkClipRate' not in read('source/entities/MovableGameEntity.cpp')

# Config: documented, the key is only in creature blocks, every value inside the limits and the computed types set
assert re.search(r'^# WalkClipRate\s', creatures_cfg, re.M)
rates = {}
for match in re.finditer(r'\[Creature\](.*?)\[/Creature\]', creatures_cfg, re.S):
    body = match.group(1)
    name = re.search(r'^\s*Name\s+(\S+)', body, re.M)
    rate = re.search(r'^\s*WalkClipRate\s+(\S+)', body, re.M)
    if name and rate:
        rates[name.group(1)] = float(rate.group(1))
for name, value in rates.items():
    assert 0.6 <= value <= 1.6, (name, value)
for name in ('Kobold', 'Rat', 'Spider', 'Adventurer', 'Monk', 'DarkElf', 'Elf', 'Champion', 'TentacleAlbine', 'TentacleGreen'):
    assert name in rates, name
assert len(rates) == 10, rates
print('check_walk_clip_rate: ok')
