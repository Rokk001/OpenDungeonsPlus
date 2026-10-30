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
assert re.search(r'getPrisonMood\(\)\s*\+\s*creature.getTortureMood\(\)', mood)
print('prison mood ok')
