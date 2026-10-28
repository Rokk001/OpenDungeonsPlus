#!/usr/bin/env python3
"""Check that urgent needs interrupt room use and sleep without interrupting fights."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
hungry = source.split('bool Creature::isHungry() const', 1)[1].split('\n}', 1)[0]
assert 'getHungerSeek()' in hungry
need = source.split('bool Creature::needInterrupt(bool servingNeed) const', 1)[1].split('\n}', 1)[0]
for key in ('UrgeSeek', 'ThirstSeek', 'isHungry()', 'servingNeed', 'CreatureActionType::fight', 'CreatureActionType::fightFriendly'):
    assert key in need, key
room = (ROOT / 'source/creatureaction/CreatureActionUseRoom.cpp').read_text(encoding='utf-8')
assert 'needInterrupt(' in room
assert not re.search(r'Random::Int\(\s*0\s*,\s*100\s*\)\s*<\s*20', room)
sleep = (ROOT / 'source/creatureaction/CreatureActionSleep.cpp').read_text(encoding='utf-8')
assert 'needInterrupt(' in sleep
for action in ('CreatureActionFight.cpp', 'CreatureActionFightFriendly.cpp'):
    assert 'needInterrupt(' not in (ROOT / 'source/creatureaction' / action).read_text(encoding='utf-8')
print('need interrupts ok')
