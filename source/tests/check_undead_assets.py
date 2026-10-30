#!/usr/bin/env python3
"""Undead death assets: the Lich beetle effect, its particle system, texture, material and credits exist, the
Skeleton bone heap keeps its material, and the Die clips of the Skeleton and the Lich last exactly as long as the
DeathVanishSeconds of their creatures.cfg block (binary animation chunk scan, no compiling, no rendering)."""
from pathlib import Path
import importlib.util
import re
import struct

ROOT = Path(__file__).resolve().parents[2]


# Read one shipped text file of the repository.
def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


# Return the [Creature] block of one creature type in creatures.cfg.
def creature_block(creatures, name):
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', creatures, re.S):
        if re.search(r'^\s*Name\s+' + name + r'\s*$', block, re.M):
            return block
    raise AssertionError('creatures.cfg has no ' + name)


# Return the length in seconds of one animation clip of a binary OGRE skeleton.
def clip_length(module, skeleton, clip):
    _, blocks = module.chunks((ROOT / 'models' / skeleton).read_bytes())
    animations = {name: data for kind, name, data in blocks if kind == module.ANIMATION}
    assert clip in animations, skeleton + ' has no ' + clip + ' clip'
    data = animations[clip]
    return struct.unpack_from('<f', data, data.index(b'\n', 6) + 1)[0]


# Run every undead asset requirement and stop at the first one that is missing.
def main():
    events = read('config/roomAmbienceSpells.cfg')
    effect = None
    for block in re.findall(r'\[Effect\](.*?)\[/Effect\]', events, re.S):
        if re.search(r'^\s*Name\s+LichBeetlesSwarm\s*$', block, re.M):
            effect = block
    assert effect is not None, 'roomAmbienceSpells.cfg has no [Effect] LichBeetlesSwarm'
    for key, value in (('Target', 'Event'), ('Event', 'SpellFxLichBeetles'), ('Kind', 'Particle'),
                       ('System', 'LichBeetles'), ('Offset', '0 0 0'), ('Duration', '2.5'),
                       ('MaxDistance', '40'), ('Priority', '5'), ('Reduced', 'yes')):
        match = re.search(r'^\s*' + key + r'\s+(.+?)\s*$', effect, re.M)
        assert match and match.group(1) == value, 'LichBeetlesSwarm ' + key + ' must be ' + value

    particles = read('particles/RoomAmbienceSpellsExtra.particle')
    assert re.search(r'^\s*(?:particle_system\s+)?LichBeetles\s*(\{|$)', particles, re.M), \
        'RoomAmbienceSpellsExtra.particle has no particle system LichBeetles'

    texture = ROOT / 'materials/textures/LichBeetle.png'
    assert texture.is_file() and texture.stat().st_size > 0, 'materials/textures/LichBeetle.png is missing'
    materials = read('materials/scripts/RoomAmbience.material')
    assert 'LichBeetle.png' in materials, 'RoomAmbience.material has no material with the LichBeetle.png texture'

    credits = read('CREDITS')
    for name in ('materials/textures/LichBeetle.png', 'materials/scripts/RoomAmbience.material',
                 'particles/RoomAmbienceSpellsExtra.particle'):
        rows = [row for row in credits.splitlines() if name in row and ('LichBeetle' in row or name.endswith('.png'))]
        assert rows, 'CREDITS has no row for ' + name + ' (LichBeetle)'
    for entry in ('materials/textures/LichBeetle.png', 'materials/scripts/RoomAmbience.material (LichBeetle',
                  'particles/RoomAmbienceSpellsExtra.particle (LichBeetles)',
                  'models/skeleton.skeleton (new Die clip)', 'models/lich.skeleton (new Die clip)',
                  'models/Pile_Skeleton.mesh (bone heap)', 'materials/textures/Pile_Skeleton.png'):
        assert entry in credits, 'CREDITS has no entry ' + entry

    pile = (ROOT / 'models/Pile_Skeleton.mesh').read_bytes()
    assert b'Pile_Skeleton' in pile, 'models/Pile_Skeleton.mesh no longer names its material Pile_Skeleton'
    assert re.search(r'^\s*material\s+Pile_Skeleton\b', read('materials/scripts/DirtPiles.material'), re.M), \
        'DirtPiles.material has no material Pile_Skeleton'

    spec = importlib.util.spec_from_file_location('undead_skeleton_chunks',
                                                  ROOT / 'tools/blender-assets/splice_animation_chunks.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    creatures = read('config/creatures.cfg')
    for creature, skeleton, seconds in (('Skeleton', 'skeleton.skeleton', 2.0), ('Lich', 'lich.skeleton', 2.5)):
        match = re.search(r'^\s*DeathVanishSeconds\s+(\S+)', creature_block(creatures, creature), re.M)
        assert match and float(match.group(1)) == seconds, creature + ' DeathVanishSeconds must be ' + str(seconds)
        length = clip_length(module, skeleton, 'Die')
        assert abs(length - float(match.group(1))) < 1e-6, \
            skeleton + ' Die clip is ' + str(length) + ' s, DeathVanishSeconds is ' + match.group(1)
    print('undead assets ok')


if __name__ == '__main__':
    main()
