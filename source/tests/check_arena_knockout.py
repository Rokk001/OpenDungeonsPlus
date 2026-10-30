#!/usr/bin/env python3
"""Check that allied arena knockouts have a positive timer and a configured recovery."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
arena = source.split('if(arenaFight)', 1)[1].split('else', 1)[0]
assert re.search(r'mKoTurnCounter\s*=\s*ConfigManager::getSingleton\(\)\.getRoomConfigDouble\("ArenaKnockOutSeconds"\)\s*\*\s*ODApplication::turnsPerSecond', arena)
assert 'mArenaKnockOut = true' in arena
assert re.search(r'setHP\(getMaxHp\(\)\s*\*\s*ConfigManager::getSingleton\(\)\.getRoomConfigDouble\("ArenaGetUpHpShare"\)\)', source)
assert re.search(r'KO_SAVE_OPEN\s*=\s*"\[Ko\]"', source)
assert re.search(r'KO_SAVE_CLOSE\s*=\s*"\[/Ko\]"', source)
assert '[Ko koTurnCounter arenaKnockOut /Ko]' in source
export = source.split('Creature::exportToStream', 1)[1].split('Creature::importFromStream', 1)[0]
assert re.search(r'if\s*\(mArenaKnockOut\).*?KO_SAVE_OPEN.*?mKoTurnCounter.*?KO_SAVE_CLOSE', export, re.S)
loaded = source.split('Creature::importFromStream', 1)[1]
assert 'KO_SAVE_OPEN' in loaded and 'KO_SAVE_CLOSE' in loaded
assert 'mKoTurnCounter' in loaded and 'mArenaKnockOut' in loaded
rooms = (ROOT / 'config/rooms.cfg').read_text(encoding='utf-8')
for key, value in (('ArenaKnockOutSeconds', 30), ('ArenaGetUpHpShare', 0.35)):
    match = re.search(r'^\s*' + key + r'\s+(\S+)', rooms, re.M)
    assert match and float(match.group(1)) == value, key
print('arena knockout ok')
