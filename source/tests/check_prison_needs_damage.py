#!/usr/bin/env python3
"""Check hunger and thirst damage and chicken healing in the prison."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/rooms/RoomPrison.cpp').read_text(encoding='utf-8')
assert not re.search(r'getRoomConfig\w*\("PrisonDamagePerTurn(?:Min)?"\)', source)
assert re.search(r'if\(creature->isHungry\(\)\)\s*hpSharePerSecond\s*\+=.*?"PrisonHungerHpSharePerSecond"', source, re.S)
assert re.search(r'if\(creature->getThirst\(\)\s*>=.*?"ThirstSeek"\)\)\s*hpSharePerSecond\s*\+=.*?"PrisonThirstHpSharePerSecond"', source, re.S)
assert re.search(r'if\(hpSharePerSecond\s*>\s*0\.0\).*?takeDamage\(this,\s*hpSharePerSecond\s*\*\s*creature->getMaxHp\(\)\s*/\s*ODApplication::turnsPerSecond', source, re.S)
feeding = source.split('void RoomPrison::feedPrisoners()', 1)[1]
assert 'chicken->eatChicken(nearest)' in feeding
assert re.search(r'nearest->getMaxHp\(\)\s*\*.*?"HatcheryChickenHealSeconds"\)\s*/\s*ConfigManager::getSingleton\(\)\.getNaturalFullHealSeconds\(\)', feeding, re.S)
print('prison needs damage ok')
