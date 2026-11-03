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
# The fee amount is the number of missed wages; the Fee line of the config gives jump, fall and reward per wage
assert re.search(r'CreatureMoodFee::getAmount\(const Creature& creature\) const\s*\{\s*return static_cast<double>\(creature\.getMissedWages\(\)\);', fee)
# The injury amount is 1 while the health is below the low health threshold, otherwise 0
assert re.search(r'CreatureMoodHpLoss::getAmount.*?creature\.getHP\(\)\s*/\s*creature\.getMaxHp\(\)\s*\*\s*100\.0\s*<\s*thresholdPercent\)\s*\?\s*1\.0\s*:\s*0\.0', hp, re.S)
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
        # Start (jump), fall per turn and reward: -300 -0.8929 300 per missed wage, -125 -0.1488 125 for the injury
        for key, values in (('Fee', [-300, -0.8929, 300]), ('HpLoss', [-125, -0.1488, 125])):
            match = re.search(r'^\s*' + key + r'((?:\s+\S+)+?)\s*$', mood.group(1), re.M)
            assert match and [float(word) for word in match.group(1).split()] == values, key
for path in (ROOT / 'source/creaturemood').glob('*.h'):
    assert not re.search(r'\bmMoodModifier\b', path.read_text(encoding='utf-8')), path
print('wage mood ladder ok')
