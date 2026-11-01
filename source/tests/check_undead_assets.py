#!/usr/bin/env python3
"""Undead death assets: the Lich vermin effects (3D animated models with a Crawl clip), their materials and credits exist, the
Skeleton bone heap uses the original skeleton material, and the Die clips of both creatures last exactly as long as the
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
    materials = read('materials/scripts/RoomAmbience.material')
    credits = read('CREDITS')
    amounts = 0
    # Three crawl effects bring the real 3D vermin (animated models with a Crawl clip) out of the Lich that burst
    for name, mesh, matnames in (('LichBeetlesSwarm', 'LichBeetle', ('LichVerminShell', 'LichVerminLeg')),
                                 ('LichBeetlesMediumSwarm', 'LichMaggot', ('LichVerminMaggot',)),
                                 ('LichBeetlesLargeSwarm', 'LichWorm', ('LichVerminWorm',))):
        effect = None
        for block in re.findall(r'\[Effect\](.*?)\[/Effect\]', events, re.S):
            if re.search(r'^\s*Name\s+' + name + r'\s*$', block, re.M):
                effect = block
        assert effect is not None, 'roomAmbienceSpells.cfg has no [Effect] ' + name
        for key, value in (('Target', 'Event'), ('Event', 'SpellFxLichBeetles'), ('Kind', 'Crawl'), ('Mesh', mesh),
                           ('Delay', '1.5'), ('Duration', '14'), ('MaxDistance', '40'), ('Priority', '5'),
                           ('Reduced', 'yes')):
            match = re.search(r'^\s*' + key + r'\s+(.+?)\s*$', effect, re.M)
            assert match and match.group(1) == value, name + ' ' + key + ' must be ' + value
        amounts += int(re.search(r'^\s*Amount\s+(\d+)\s*$', effect, re.M).group(1))
        assert 'Kind        Particle' not in effect and 'System' not in effect, name + ' must not be a 2D particle effect'
        for ext in ('.mesh', '.skeleton'):
            path = ROOT / 'models' / (mesh + ext)
            assert path.is_file() and path.stat().st_size > 0, 'models/' + mesh + ext + ' is missing'
        assert b'Crawl' in (ROOT / 'models' / (mesh + '.skeleton')).read_bytes(), mesh + ' has no Crawl clip'
        for matname in matnames:
            assert 'material ' + matname in materials, 'RoomAmbience.material has no material ' + matname
            assert matname.encode() in (ROOT / 'models' / (mesh + '.mesh')).read_bytes(), mesh + ' does not use ' + matname
        assert 'models/' + mesh + '.mesh' in credits, 'CREDITS has no row for models/' + mesh + '.mesh'
    assert 5 <= amounts <= 10, 'the Lich must release 5 to 10 vermin, not ' + str(amounts)
    assert 'LichVerminShell' in credits, 'CREDITS has no row for the vermin materials'
    assert 'LichBeetleModel' not in materials and 'LichBeetle.png' not in materials, 'the 2D beetle materials must be gone'

    for entry in ('models/skeleton.skeleton (new Die clip)', 'models/lich.skeleton (new Die clip)',
                  'models/Pile_Skeleton.mesh (bone heap)', 'materials/textures/Pile_Skeleton.png'):
        assert entry in credits, 'CREDITS has no entry ' + entry

    pile = (ROOT / 'models/Pile_Skeleton.mesh').read_bytes()
    assert b'undead' in pile, 'models/Pile_Skeleton.mesh must use the skeleton material'

    spec = importlib.util.spec_from_file_location('undead_skeleton_chunks',
                                                  ROOT / 'tools/blender-assets/splice_animation_chunks.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    creatures = read('config/creatures.cfg')
    for creature, skeleton, seconds in (('Skeleton', 'skeleton.skeleton', 5.0), ('Lich', 'lich.skeleton', 5.0)):
        match = re.search(r'^\s*DeathVanishSeconds\s+(\S+)', creature_block(creatures, creature), re.M)
        assert match and float(match.group(1)) == seconds, creature + ' DeathVanishSeconds must be ' + str(seconds)
        length = clip_length(module, skeleton, 'Die')
        assert abs(length - float(match.group(1))) < 1e-6, \
            skeleton + ' Die clip is ' + str(length) + ' s, DeathVanishSeconds is ' + match.group(1)
    print('undead assets ok')


if __name__ == '__main__':
    main()
