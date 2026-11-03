#!/usr/bin/env python3
"""Check prisoner wake health, needs and captivity mood."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
prison = (ROOT / 'source/rooms/RoomPrison.cpp').read_text(encoding='utf-8')
creature = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
mood = (ROOT / 'source/creaturemood/CreatureMoodManager.cpp').read_text(encoding='utf-8')
assert re.search(r'setHP\(std::max\(prisonerCreature->getHP\(\),\s*.*?PrisonWakeHpShare.*?\*\s*prisonerCreature->getMaxHp\(\)\)\)', prison, re.S)
jail = creature.split('// If the creature is in jail, it should not auto heal or do anything', 1)[1].split('// If we are not standing somewhere on the map', 1)[0]
for expression in ('getHungerGrowthPerTurn()', 'getThirstGrowthPerTurn()', 'increaseHunger(', 'increaseThirst(', 'PrisonMoodPerSecond', 'ResearchEffect::MoodLoss', 'ODApplication::turnsPerSecond', 'computeMood()', 'computeCreatureOverlayMoodValue()'):
    assert expression in jail, expression
# The prison and the torture chamber take mood points from the stored mood, which is all a captive's effective mood is
header = (ROOT / 'source/entities/Creature.h').read_text(encoding='utf-8')
assert re.search(r'void addPrisonMood\(double points\)\s*\{\s*changeStoredMood\(points\);', header)
assert re.search(r'void addTortureMood\(double points\)\s*\{\s*changeStoredMood\(points\);', header)
assert re.search(r'double Creature::getEffectiveMood\(\) const\s*\{\s*if\(isInContainment\(\)\)\s*return mStoredMood;', creature)
assert 'getPrisonMood' not in mood and 'getTortureMood' not in mood
rooms = (ROOT / 'config/rooms.cfg').read_text(encoding='utf-8')
assert re.search(r'^\s*PrisonMoodPerSecond\s+-0\.9333\s*$', rooms, re.M)
assert re.search(r'^\s*TortureMoodPerSecond\s+-10\.5024\s*$', rooms, re.M)
print('prison mood ok')
