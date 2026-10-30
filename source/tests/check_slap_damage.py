#!/usr/bin/env python3
"""Check that keeper slaps use the configured fixed HP damage."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
start = source.index('void Creature::slap()')
opening = source.index('{', start)
end = opening + 1
depth = 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1
body = source[opening:end]
assert re.search(r'mHp\s*-=\s*ConfigManager::getSingleton\(\)\.getSlapDamage\(\)', body)
assert 'getMaxHp' not in body and 'mMaxHP' not in body
config = (ROOT / 'config/global.cfg').read_text(encoding='utf-8')
game = re.search(r'^\[GameConfig\]\s*$(.*?)^\[/GameConfig\]', config, re.M | re.S).group(1)
assert re.search(r'^\s*SlapDamage\s+10\s*$', game, re.M)
assert not re.search(r'^\s*Slap\w*Percent\s+', game, re.M)
print('slap damage ok')
