#!/usr/bin/env python3
"""Check experience from room work and guard duty."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
for name, key, cycle, dirt in (
    ('RoomLibrary.cpp', 'JobXpPerTurn', 'workCycleTurns', True),
    ('RoomWorkshop.cpp', 'JobXpPerTurn', 'workCycleTurns', True),
    ('RoomGuardRoom.cpp', 'GuardRoomXpPerDutyTurn', 'dutyCycleTurns', False),
    ('RoomHerbGarden.cpp', 'JobXpPerTurn', None, True),
    ('RoomAlchemyLab.cpp', 'JobXpPerTurn', None, True),
):
    source = (ROOT / 'source/rooms' / name).read_text(encoding='utf-8')
    match = re.search(r'creature\.receiveExp\((.*?);', source, re.S)
    assert match, name
    expr = match.group(1)
    assert 'getRoomConfigDouble("' + key + '")' in expr, name
    assert 'SkillType::roomTrainingHall' in expr and 'ResearchEffect::XpPerHit' in expr, name
    if cycle:
        assert cycle in expr, name
        assert re.search(r'1\.0\s*\+\s*static_cast<double>\(creature\.getJobCooldown\(\)\)', source), name
    if dirt:
        assert 'getDirtOutputFactor()' in expr, name
print('job xp ok')
