"""Check the undead death resources and their configured animation lengths."""
import importlib.util
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[2]


# Check each required resource and the shipped animation durations.
def main():
    config = (ROOT / 'config/roomAmbienceSpells.cfg').read_text(encoding='utf-8')
    blocks = re.findall(r'\[Effect\](.*?)\[/Effect\]', config, re.S)
    effect = next(block for block in blocks if re.search(r'^\s*Name\s+LichBeetlesSwarm\s*$', block, re.M))
    for key, value in (('Target', 'Event'), ('Event', 'SpellFxLichBeetles'), ('Kind', 'Particle'),
                       ('System', 'LichBeetles'), ('Offset', '0 0 0'), ('Duration', '2.5'),
                       ('MaxDistance', '40'), ('Priority', '5'), ('Reduced', 'yes')):
        assert re.search(r'^\s*' + key + r'\s+' + re.escape(value) + r'\s*$', effect, re.M), key
    particles = (ROOT / 'particles/RoomAmbienceSpellsExtra.particle').read_text(encoding='utf-8')
    assert re.search(r'^\s*(?:particle_system\s+)?LichBeetles\s*\{', particles, re.M)
    texture = 'materials/textures/LichBeetle.png'
    assert (ROOT / texture).is_file() and (ROOT / texture).stat().st_size
    materials = (ROOT / 'materials/scripts/RoomAmbience.material').read_text(encoding='utf-8')
    assert 'LichBeetle.png' in materials
    credits = (ROOT / 'CREDITS').read_text(encoding='utf-8')
    for entry in (texture, 'materials/scripts/RoomAmbience.material (LichBeetle',
                  'particles/RoomAmbienceSpellsExtra.particle (LichBeetles)',
                  'models/skeleton.skeleton (new Die clip)', 'models/lich.skeleton (new Die clip)',
                  'models/Pile_Skeleton.mesh (bone heap)', 'materials/textures/Pile_Skeleton.png'):
        assert entry in credits, entry
    assert b'Pile_Skeleton' in (ROOT / 'models/Pile_Skeleton.mesh').read_bytes()
    spec = importlib.util.spec_from_file_location('skeleton_chunks', ROOT / 'tools/blender-assets/splice_animation_chunks.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    creatures = (ROOT / 'config/creatures.cfg').read_text(encoding='utf-8')
    blocks = re.findall(r'\[Creature\](.*?)\[/Creature\]', creatures, re.S)
    for name, length in (('Skeleton', 2.0), ('Lich', 2.5)):
        block = next(block for block in blocks if re.search(r'^\s*Name\s+' + name + r'\s*$', block, re.M))
        configured = float(re.search(r'^\s*DeathVanishSeconds\s+(\S+)', block, re.M)[1])
        _, chunks = module.chunks((ROOT / ('models/' + name.lower() + '.skeleton')).read_bytes())
        clip = next(data for kind, clip_name, data in chunks if kind == module.ANIMATION and clip_name == 'Die')
        duration = struct.unpack_from('<f', clip, clip.index(b'\n', 6) + 1)[0]
        assert configured == length and abs(duration - configured) < 1e-6, (name, configured, duration)
    print('Undead assets OK')


if __name__ == '__main__':
    main()
