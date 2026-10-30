#!/usr/bin/env python3
"""Check torture mood and the conversion roll."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
torture = (ROOT / 'source/rooms/RoomTorture.cpp').read_text(encoding='utf-8')
definition = (ROOT / 'source/entities/CreatureDefinition.cpp').read_text(encoding='utf-8')
header = (ROOT / 'source/entities/CreatureDefinition.h').read_text(encoding='utf-8')
config = (ROOT / 'config/creatures.cfg').read_text(encoding='utf-8')
for obsolete in ('TORTURE_LEVEL_PERCENT', 'tortureTurnsToConvert', 'TortureTimeToConvert'):
    for text in (torture, definition, header, config):
        assert obsolete not in text, obsolete
assert re.search(r'addTortureMood\(.*?TortureMoodPerSecond.*?ResearchEffect::ConversionSpeed.*?ODApplication::turnsPerSecond', torture, re.S)
assert re.search(r'getSeat\(\)\s*!=\s*creature->getSeat\(\).*?getCreatureBaseMood\(\)\s*\+\s*creature->getMoodPoints\(\)\s*<=\s*config.getCreatureMoodFurious\(\).*?increaseTortureBrokenTurns\(\).*?floor\(brokenTurns\s*/\s*ODApplication::turnsPerSecond\).*?floor\(\(brokenTurns\s*-\s*1\)\s*/\s*ODApplication::turnsPerSecond\).*?secondPassed.*?Random::Double\(0\.0,\s*1\.0\).*?TortureConvertChancePerSecond.*?convertVictim\(\*creature\)', torture, re.S)
assert 'resetTortureBrokenTurns()' in torture
print('torture mood ok')
