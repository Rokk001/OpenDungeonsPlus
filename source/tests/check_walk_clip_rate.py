#!/usr/bin/env python3
"""Pure check (nothing compiled, nothing started): the optional key WalkClipRate of config/creatures.cfg is parsed,
copied, streamed and dumped like LowHealthWalkSpeedFactor, limited to 0.2 - 8.0, applied only to the client clip speed
of the walk state (Walk, WalkHurt, CarryWalk), never to the move speed, divided by the creature scale, and set for every type that has feet on the ground."""
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
assert 'std::max(0.2, std::min(8.0, mWalkClipRate))' in definition_h and '#include <algorithm>' in definition_h

# Applied only to the client clip speed of the walk state, not to the move speed
pose = creature[creature.index('double Creature::getClientPoseSpeedFactor'):creature.index('double Creature::getPhysicalDefense')]
assert '(getAnimationStateName() == EntityAnimation::walk_anim)' in pose and 'getWalkClipRate()' in pose
assert '(1.0 + 0.02 * static_cast<double>(getLevel()))' in pose
assert '//! \\brief Speed factor of the walk clips' in definition_h and '//! \\brief Optional (WalkClipRate)' in definition_h
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
    assert 0.2 <= value <= 8.0, (name, value)
no_feet = ('LavaSpawn', 'CaveHornet', 'Slime', 'Wyvern', 'TentacleAlbine', 'TentacleGreen')  # blobs, fliers and gliders: no planted foot, rate 1
names = [m.group(1) for m in re.finditer(r'\[Creature\].*?^\s*Name\s+(\S+)', creatures_cfg, re.S | re.M)]
assert len(names) == 35, len(names)
for name in names:
    assert (name in rates) != (name in no_feet), name
# WalkHurtClipRate: own optional key for the clip WalkHurt only, fallback WalkClipRate, same limits, streamed right after WalkClipRate
assert 'mWalkHurtClipRate (-1.0)' in definition and 'mWalkHurtClipRate(def.mWalkHurtClipRate)' in definition
assert definition.index('os << c->mWalkClipRate;') < definition.index('os << c->mWalkHurtClipRate;')
assert definition.index('os << c->mWalkHurtClipRate;') < definition.index('os << c->mXPTable')
assert definition.index('is >> c->mWalkClipRate;') < definition.index('is >> c->mWalkHurtClipRate;')
assert 'nextParam == "WalkHurtClipRate"' in definition and 'creatureDef->mWalkHurtClipRate = Helper::toDouble(nextParam);' in definition
assert '"    WalkHurtClipRate' in definition and 'mWalkHurtClipRate >= 0.0' in definition
hurt_getter = definition_h[definition_h.index('getWalkHurtClipRate ()'):]
hurt_getter = hurt_getter[:hurt_getter.index('}') + 1]
assert 'if(mWalkHurtClipRate < 0.0)' in hurt_getter and 'return getWalkClipRate();' in hurt_getter
assert 'std::max(0.2, std::min(8.0, mWalkHurtClipRate))' in hurt_getter
BS = chr(92)
assert '//! ' + BS + 'brief Optional (WalkHurtClipRate)' in definition_h and '//! ' + BS + 'brief Speed factor of the WalkHurt clip' in definition_h
# no control character in the header (a backspace once replaced a backslash)
assert chr(8) not in definition_h
# Applied only while the clip WalkHurt plays (follows the playing clip), Walk and CarryWalk keep WalkClipRate
assert 'getAnimationName() == EntityAnimation::walk_hurt_anim' in pose
assert 'playsHurtClip ? mDefinition->getWalkHurtClipRate() : mDefinition->getWalkClipRate()' in pose
assert 'getWalkHurtClipRate' not in creature[:creature.index('double Creature::getClientPoseSpeedFactor')]
assert 'getWalkHurtClipRate' not in read('source/entities/MovableGameEntity.cpp')
# Header documentation of the cfg: key, limits and fallback chain; a value is optional and, when set, inside the limits
assert re.search(r'^# WalkHurtClipRate\s', creatures_cfg, re.M)
header = creatures_cfg[creatures_cfg.index('# WalkHurtClipRate'):][:900]
assert '0.2 - 8.0' in header and 'Fallback chain' in header and 'else WalkClipRate' in header
for match in re.finditer(r'\[Creature\](.*?)\[/Creature\]', creatures_cfg, re.S):
    hurt_rate = re.search(r'^\s*WalkHurtClipRate\s+(\S+)', match.group(1), re.M)
    if hurt_rate:
        assert 0.2 <= float(hurt_rate.group(1)) <= 8.0
print('check_walk_clip_rate: ok')
