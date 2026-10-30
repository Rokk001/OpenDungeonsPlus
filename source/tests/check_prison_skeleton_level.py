#!/usr/bin/env python3
"""Check the prison skeleton level and its research bonuses."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/rooms/RoomPrison.cpp').read_text(encoding='utf-8')
assert re.search(r'prisonerLevel\s*=\s*creature->getLevel\(\)', source)
assert re.search(r'setLevel\(std::min<uint32_t>\(30,\s*prisonerLevel\s*\+', source)
assert 'PrisonSkeletonLevelBonus' in source and 'ResearchEffect::SkeletonLevel' in source
rooms = (ROOT / 'config/rooms.cfg').read_text(encoding='utf-8')
assert re.search(r'^\s*PrisonSkeletonLevelBonus\s+0\s*$', rooms, re.M)
assert not re.search(r'^\s*PrisonSkeletonBaseLevel\s+', rooms, re.M)
skills = (ROOT / 'config/skills.cfg').read_text(encoding='utf-8')
assert re.search(r'^\s*roomPrison\s+SkeletonLevel\s+add\s+0\s+1\s+2\s*$', skills, re.M)
print('prison skeleton level ok')
