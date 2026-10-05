"""Slower walk of a badly hurt creature (30 percent by default), server and clients at the same speed.

Pure source wiring checks (no compiler, no game): values in the configuration, one shared rule on the
health stage both sides know, no new network message, the walk clip keeps up and is not slowed twice."""
from pathlib import Path
import math
import re

root = Path(__file__).resolve().parents[2]


def read(path):
    return (root / path).read_text(encoding='utf-8')


def function_body(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end]


global_cfg = read('config/global.cfg')
config_h = read('source/utils/ConfigManager.h')
config_cpp = read('source/utils/ConfigManager.cpp')
creature = read('source/entities/Creature.cpp')
creature_h = read('source/entities/Creature.h')
movable = read('source/entities/MovableGameEntity.cpp')
render = read('source/render/RenderManager.cpp')
reactions_cfg = read('config/creatureReactions.cfg')

# Values: documented and set in the configuration, read with a default and a limit
for key, value in (('LowHealthWalkSpeedFactor', 0.7), ('LowHealthWalkThresholdPercent', 50.0)):
    assert re.search(r'^# .*\n    ' + key + r'\t[\d.]+', global_cfg, re.M), key + ' not documented and set'
    assert float(re.search(r'^    ' + key + r'\t([\d.]+)', global_cfg, re.M)[1]) == value, key
    assert ('"' + key + '"') in config_cpp, key + ' not read'
assert 'mLowHealthWalkSpeedFactor(0.7)' in config_cpp and 'mLowHealthWalkThresholdPercent(50.0)' in config_cpp
assert 'std::max(0.2, std::min(1.0, mLowHealthWalkSpeedFactor))' in config_h
assert 'std::max(1.0, std::min(100.0, mLowHealthWalkThresholdPercent))' in config_h

# One rule on the health stage (known on server and clients, no new message)
rule = (function_body(creature, 'bool Creature::isLowHealthWalkStage(uint32_t healthStage)') + ' ' +
        function_body(creature, 'double Creature::getLowHealthWalkFactor() const'))
assert 'mOverlayHealthValue' in rule or 'isLowHealthWalking()' in rule and 'getLowHealthWalkThresholdPercent()' in rule
assert 'getLowHealthWalkSpeedFactor()' in rule and 'getIsOnServerMap' not in rule
assert 'double getLowHealthWalkFactor() const;' in creature_h
assert 'NB_OVERLAY_HEALTH_VALUES = 8' in creature


def first_stage(percent, nb_steps=6):
    return math.ceil((100.0 - percent) / 100.0 * nb_steps - 0.000001) + 1


assert 'std::ceil((100.0 - thresholdPercent) / 100.0 * nbSteps - 0.000001) + 1.0' in rule
assert 'NB_OVERLAY_HEALTH_VALUES - 2' in rule
assert first_stage(50) == 4        # default: below half of the health = stage 4, the stage of the hurt walk reaction
assert first_stage(100) == 1 and first_stage(1) == 7 and first_stage(34) == 5 and first_stage(17) == 6

# Server and client move with it, the same product as the tired factor (no other place)
speed = function_body(creature, 'double Creature::getMoveSpeed(Tile* tile) const')
assert 'tiredFactor *= getLowHealthWalkFactor();' in speed
assert speed.index('getTiredWalkSpeedFactor()') < speed.index('getLowHealthWalkFactor()') < speed.index('getIsOnServerMap()')
assert speed.count('* tiredFactor') == 4

# The walk clip keeps up exactly once; standing keeps its slower breathing
pose = function_body(creature, 'double Creature::getClientPoseSpeedFactor() const')
assert pose.count('getLowHealthWalkFactor()') == 1
assert 'EntityAnimation::idle_anim' in pose and 'factor = 0.78;' in pose
assert 'CreatureMoodValues::Tired' in pose and pose.count('getTiredWalkSpeedFactor()') == 1
else_part = pose[pose.index('else\n    {'):]
assert 'getLowHealthWalkFactor()' in else_part and 'factor = 0.' not in else_part   # no stage factor on top of the real one
assert movable.count('getClientPoseSpeedFactor()') == 1
assert 'getLowHealthWalk' not in render and 'getLowHealthWalk' not in movable   # the renderer does not scale it again

# Matching clip: the normal walk clip at that speed plus the existing hurt walk reaction (E15)
assert re.search(r'Name\s+HurtWalk\b', reactions_cfg) and re.search(r'Name\s+Limp\b', reactions_cfg)

# Optional factor per creature type: parsed, copied, sent to the clients, saved, documented, absent = global value
definition = read('source/entities/CreatureDefinition.cpp')
definition_h = read('source/entities/CreatureDefinition.h')
creatures_cfg = read('config/creatures.cfg')
assert 'mLowHealthWalkSpeedFactor (-1.0)' in definition
assert 'mLowHealthWalkSpeedFactor(def.mLowHealthWalkSpeedFactor)' in definition
assert 'os << c->mLowHealthWalkSpeedFactor;' in definition and 'is >> c->mLowHealthWalkSpeedFactor;' in definition
assert definition.index('os << c->mTortureTimeToConvert;') < definition.index('os << c->mLowHealthWalkSpeedFactor;') < definition.index('os << c->mXPTable')     if 'os << c->mXPTable' in definition else True
assert definition.index('is >> c->mTortureTimeToConvert;') < definition.index('is >> c->mLowHealthWalkSpeedFactor;')
assert 'nextParam == "LowHealthWalkSpeedFactor"' in definition and '"    LowHealthWalkSpeedFactor' in definition
assert 'double mLowHealthWalkSpeedFactor;' in definition_h and 'getLowHealthWalkSpeedFactor () const' in definition_h
assert re.search(r'^# LowHealthWalkSpeedFactor \(Optional', creatures_cfg, re.M)
assert not re.search(r'^\s+LowHealthWalkSpeedFactor\s', creatures_cfg, re.M), 'no value set yet'
assert 'mDefinition->getLowHealthWalkSpeedFactor() >= 0.0' in rule
assert 'std::max(0.2, std::min(1.0, mDefinition->getLowHealthWalkSpeedFactor()))' in rule
assert rule.index('mDefinition->getLowHealthWalkSpeedFactor()') < rule.index('ConfigManager::getSingleton().getLowHealthWalkSpeedFactor()')
# Server speed and client clip both go through the one function, nothing else reads the factor
assert 'getLowHealthWalkFactor' in speed and pose.count('getLowHealthWalkFactor()') == 1
assert creature.count('getLowHealthWalkSpeedFactor()') == 3   # definition twice (test and clamp), global once

print('check_low_health_walk: ok')
