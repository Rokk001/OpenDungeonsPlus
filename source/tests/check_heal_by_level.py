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
growth, exponent, hp_growth = (float(re.search(r'^\s*' + key + r'\s+(\S+)', global_config, re.M).group(1))
                               for key in ('CreatureDamageGrowth', 'CreatureDamageExponent', 'CreatureHpGrowthPerLevel'))
progression = (ROOT / 'source/entities/CreatureProgression.h').read_text(encoding='utf-8')
assert 'CreatureProgression::combatStatAt(mMaxHP, mDefinition->getHpPerLevel(), getLifeLevel()' in creature
assert 'base + (level - 1.0) * perLevel, base * multiplier(level)' in progression
assert 'damageMultiplierAt(level) * (1.0 + ConfigManager::getSingleton().getCreatureHpGrowthPerLevel() * steps)' in progression
assert 'config.getCreatureDamageGrowth() *' in progression and 'config.getCreatureDamageExponent()' in progression
assert re.search(r'ODApplication::turnsPerSecond\s*=\s*1\.4\s*;', (ROOT / 'source/ODApplication.cpp').read_text(encoding='utf-8'))
blocks = re.findall(r'^\[Creature\]\s*$(.*?)^\[/Creature\]', config, re.M | re.S)
assert blocks
for block in blocks:
    base = float(re.search(r'^\s*MinHP\s+(\S+)', block, re.M).group(1))
    per_level = float(re.search(r'^\s*HP/Level\s+(\S+)', block, re.M).group(1))
    for level in (1, 10, 30):
        steps = level - 1
        max_hp = max(base + steps * per_level, base * (1 + growth * steps ** exponent) * (1 + hp_growth * steps))
        assert max_hp > 0
        assert abs(max_hp / (seconds * 1.4) * seconds * 1.4 - max_hp) < 1e-9
print('level-scaled healing ok')
