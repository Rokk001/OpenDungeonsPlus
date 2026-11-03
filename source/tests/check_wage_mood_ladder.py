#!/usr/bin/env python3
"""Check the unpaid-wage and injury mood rules and their saved state (case wages). Missed wages cost mood (a jump per wage,
one fall per turn while any wage is missed, a reward per wage paid); they no longer stop work and no longer make a creature
leave. Nothing is compiled."""
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

# The wage rules of work and leaving are gone: the keys, their getters and every use
global_cfg = read('config/global.cfg')
manager = read('source/utils/ConfigManager.cpp') + read('source/utils/ConfigManager.h')
for gone in ('UnpaidWagesStopWork', 'UnpaidWagesLeave', 'getUnpaidWages', 'mUnpaidWages'):
    assert gone not in global_cfg and gone not in manager, gone
for path in ('source/creatureaction/CreatureActionSearchJob.cpp', 'source/creatureaction/CreatureActionSearchSpa.cpp',
             'source/creatureaction/CreatureActionUseRoom.cpp'):
    text = read(path)
    assert 'UnpaidWages' not in text and 'getMissedWages' not in text, path
# An Upset creature stops work and seeks a pleasure room by its mood only
assert re.search(r'const bool moodSearch = creature\.getMoodValue\(\) >= CreatureMoodLevel::Upset;', read('source/creatureaction/CreatureActionSearchJob.cpp'))
assert re.search(r'const bool moodRoom = creature\.getMoodValue\(\) >= CreatureMoodLevel::Upset;', read('source/creatureaction/CreatureActionSearchSpa.cpp'))
# The leave behaviour does not look at wages: a creature leaves only through the leave clock
behaviour = read('source/creaturebehaviour/CreatureBehaviourLeaveDungeonWhenFurious.cpp')
assert 'getMissedWages' not in behaviour and 'leaveDungeon()' not in behaviour and 'UnpaidWages' not in behaviour
assert 'isLeavingByMood()' in behaviour

# Values: the Fee line of every type with mood
def lines_of(block, key):
    match = re.search(r'^\s*' + key + r'((?:\s+\S+)+?)\s*$', block, re.M)
    return [float(word) for word in match.group(1).split()] if match else None

for block in re.findall(r'^\[Creature\]\s*$(.*?)^\[/Creature\]', read('config/creatures.cfg'), re.M | re.S):
    mood = re.search(r'^\s*\[MoodModifiers\]\s*$(.*?)^\s*\[/MoodModifiers\]', block, re.M | re.S)
    # A type with an empty mood block (comments only, e.g. the Skeleton) has no moods at all
    if mood and any(line.split() and not line.split()[0].startswith('#') for line in mood.group(1).splitlines()):
        # Start (jump), fall per turn and reward: -300 -0.8929 300 per missed wage, -125 -0.1488 125 for the injury
        assert lines_of(mood.group(1), 'Fee') == [-300, -0.8929, 300], 'Fee'
        assert lines_of(mood.group(1), 'HpLoss') == [-125, -0.1488, 125], 'HpLoss'
for path in (ROOT / 'source/creaturemood').glob('*.h'):
    assert not re.search(r'\bmMoodModifier\b', path.read_text(encoding='utf-8')), path

# Three paydays missed (Wizard, sensitivity 1.0, at 1500): -300 per missed wage at once, then -0.8929 per turn once, and
# +300 per wage paid; no stop of work and no leaving by the wage count
jump, fall, reward = -300.0, -0.8929, 300.0
mood = 1500.0
for wages in (1, 2, 3):
    mood += jump
    assert mood == 1500.0 - 300.0 * wages
mood += fall * 84
assert abs(mood - (600.0 - 0.8929 * 84)) < 1e-9
mood += reward * 3
assert abs(mood - (1500.0 - 0.8929 * 84)) < 1e-9
print('wage mood ladder ok')
