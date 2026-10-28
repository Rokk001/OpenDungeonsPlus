#!/usr/bin/env python3
"""Check work-first room selection, tie-breaking and configured idle decisions."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
search = (ROOT / 'source/creatureaction/CreatureActionSearchJob.cpp').read_text(encoding='utf-8')
assert not re.search(r'Random::Int\(\s*0\s*,\s*100\s*\)\s*<\s*20', search)
assert re.search(r'workRooms\.empty\(\)\s*\?\s*pleasureRooms\s*:\s*workRooms', search)
assert re.search(r'choices\[Random::Uint\(0,\s*choices\.size\(\)\s*-\s*1\)\]', search)
source = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
for key in ('FindHomeChance', 'SleepSeekWakefulnessMin', 'SleepSeekWakefulnessMax', 'StealGoldTryChance', 'TunnelTryChance', 'StealItemChancePerIdle'):
    assert 'get' + key + '()' in source, key
config = (ROOT / 'config/creatures.cfg').read_text(encoding='utf-8')
for block in re.findall(r'^\[Creature\]\s*$(.*?)^\[/Creature\]', config, re.M | re.S):
    match = re.search(r'^\s*\[RoomAffinity\]\s*$(.*?)^\s*\[/RoomAffinity\]', block, re.M | re.S)
    if not match:
        continue
    affinity = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 3 and not words[0].startswith('#'):
            affinity[words[0]] = words[1:]
    # A Casino line with likeness 0 (workers, Champion) never sends the creature to a pleasure room
    if 'Casino' in affinity and float(affinity['Casino'][0]) > 0:
        assert 'Temple' in affinity and affinity['Casino'][0] == affinity['Temple'][0]
print('decision order ok')

