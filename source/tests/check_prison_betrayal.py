#!/usr/bin/env python3
"""Check the prisoner betrayal research, mood gate, timing and reveal."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
prison = (ROOT / 'source/rooms/RoomPrison.cpp').read_text(encoding='utf-8')
torture = (ROOT / 'source/rooms/RoomTorture.cpp').read_text(encoding='utf-8')
skills = (ROOT / 'config/skills.cfg').read_text(encoding='utf-8')
assert re.search(r'^\s*roomPrison\s+BetrayChance\s+add\s+0\s+0\.00033175355450236967\s+0\.0065727699530516446\s*$', skills, re.M)
assert re.search(r'getResearchValue\(getSeat\(\),\s*SkillType::roomPrison,\s*0\.0,\s*ResearchEffect::BetrayChance\)', prison)
assert re.search(r'betrayChance\s*>\s*0\.0.*?getCreatureBaseMood\(\)\s*\+\s*creature->getMoodPoints\(\).*?<=\s*.*?getCreatureMoodFurious\(\)', prison, re.S)
assert re.search(r'increasePrisonBrokenTurns\(\).*?floor\(brokenTurns\s*/\s*ODApplication::turnsPerSecond\).*?floor\(\(brokenTurns\s*-\s*1\)\s*/\s*ODApplication::turnsPerSecond\).*?secondPassed\s*&&\s*\(Random::Double\(0\.0,\s*1\.0\)\s*<\s*betrayChance\).*?RoomTorture::revealEnemyInformation\(\*getSeat\(\),\s*\*creature\)', prison, re.S)
assert 'resetPrisonBrokenTurns()' in prison
assert 'void RoomTorture::revealEnemyInformation(Seat& keeperSeat, Creature& creature)' in torture
print('prison betrayal ok')
