#!/usr/bin/env python3
"""Check unpaid-wage and injury mood rules and their saved state."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
# Read project files relative to this check.
def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

fee = read('source/creaturemood/CreatureMoodFee.cpp')
hp = read('source/creaturemood/CreatureMoodHpLoss.cpp')
assert re.search(r'getMissedWages\(\)\s*\*\s*mMoodModifier', fee)
assert re.search(r'\(creature\.getMaxHp\(\)\s*-\s*creature\.getHP\(\)\)\s*/\s*creature\.getMaxHp\(\)', hp)
creature = read('source/entities/Creature.cpp')
assert r'os << "\t[Wages] "' in creature and 'appearanceToken == "[Wages]"' in creature and '[/Wages]' in creature
assert 'getUnpaidWagesLeave()' in read('source/creaturebehaviour/CreatureBehaviourLeaveDungeonWhenFurious.cpp')
global_cfg = read('config/global.cfg')
# Read the single configured threshold as an integer.
def threshold(key):
    return int(re.search(r'^\s*' + key + r'\s+(\d+)', global_cfg, re.M).group(1))
assert threshold('UnpaidWagesStopWork') < threshold('UnpaidWagesLeave')
for block in re.findall(r'^\[Creature\]\s*$(.*?)^\[/Creature\]', read('config/creatures.cfg'), re.M | re.S):
    mood = re.search(r'^\s*\[MoodModifiers\]\s*$(.*?)^\s*\[/MoodModifiers\]', block, re.M | re.S)
    # A type with an empty mood block (comments only, e.g. the Skeleton) has no moods at all
    if mood and any(line.split() and not line.split()[0].startswith('#') for line in mood.group(1).splitlines()):
        for key, value in (('Fee', -1000), ('HpLoss', -500)):
            match = re.search(r'^\s*' + key + r'\s+(\S+)', mood.group(1), re.M)
            assert match and float(match.group(1)) == value, key
for path in (ROOT / 'source/creaturemood').glob('*.h'):
    assert not re.search(r'\bint32_t\s+mMoodModifier\b', path.read_text(encoding='utf-8')), path
print('wage mood ladder ok')

