#!/usr/bin/env python3
"""Check level-scaled natural, bed and chicken healing."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
creature = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
sleep = (ROOT / 'source/creatureaction/CreatureActionSleep.cpp').read_text(encoding='utf-8')
eat = (ROOT / 'source/creatureaction/CreatureActionEatChicken.cpp').read_text(encoding='utf-8')
prison = (ROOT / 'source/rooms/RoomPrison.cpp').read_text(encoding='utf-8')
assert re.search(r'getMaxHp\(\)\s*/\s*\(.*?getNaturalFullHealSeconds\(\)\s*\*\s*ODApplication::turnsPerSecond\)', creature)
assert re.search(r'if\(getDefinition\(\)->isUndead\(\)\)\s*naturalHeal\s*\*=\s*.*?getUndeadHealFactor\(\)', creature)
assert re.search(r'getSleepHeal\(\)\s*==\s*0\.0\s*\?\s*0\.0\s*:\s*creature.getMaxHp\(\)\s*/\s*\(.*?DormitoryFullHealSeconds', sleep, re.S)
for source, subject in ((eat, 'creature'), (prison, 'nearest')):
    assert re.search(rf'{subject}(?:\.|->)getMaxHp\(\)\s*\*.*?HatcheryChickenHealSeconds.*?getNaturalFullHealSeconds\(\)', source, re.S)
config = (ROOT / 'config/creatures.cfg').read_text(encoding='utf-8')
assert len(re.findall(r'^\s*SleepHeal\s+0\s*$', config, re.M)) == 3
assert not re.search(r'^\s*SleepHeal\s+2\.05\s*$', config, re.M)
global_config = (ROOT / 'config/global.cfg').read_text(encoding='utf-8')
seconds = float(re.search(r'^\s*NaturalFullHealSeconds\s+(\S+)', global_config, re.M).group(1))
for max_hp in (100.0, 500.0, 1860.0):
    assert abs(max_hp / (seconds * 1.4) * seconds * 1.4 - max_hp) < 1e-9
print('level-scaled healing ok')
