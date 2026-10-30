#!/usr/bin/env python3
"""Check level-scaled lava damage and the creature types that can walk on lava."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
body = source.split('void Creature::applyLavaDamage()', 1)[1].split('\nbool Creature::', 1)[0]
assert 'getLavaDamageScalesWithHp()' in body
assert re.search(r'lavaDamagePerSecond\s*\*=\s*CreatureProgression::hpMultiplier\(getLevel\(\)\)', body)
assert 'takeDamage(nullptr, lavaDamagePerSecond / ODApplication::turnsPerSecond' in body
config = (ROOT / 'config/creatures.cfg').read_text(encoding='utf-8')
walkers = set()
for block in re.findall(r'^\[Creature\]\s*$(.*?)^\[/Creature\]', config, re.M | re.S):
    name = re.search(r'^\s*Name\s+(\S+)', block, re.M)
    speed = re.search(r'^\s*LavaMoveSpeed\s+(\S+)', block, re.M)
    assert name and speed
    if float(speed.group(1)) > 0:
        walkers.add(name.group(1))
assert walkers == {'LavaSpawn', 'PitDemon', 'Dragon', 'Wyvern', 'CaveHornet'}, walkers
print('lava walkers ok')
