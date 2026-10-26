"""Dirt, cleaning and toilet assets: pile models and textures, stain and decal models, the toilet seat, icon, particle,
sounds, the credits rows, and the Relieve / Clean clips in the creature skeletons.

Calls (from the repository root):
  python source/tests/check_dirt_assets.py            plain file checks, no compiler, no game
"""
from pathlib import Path
import fnmatch
import re
import struct

root = Path(__file__).resolve().parents[2]

# Width and height of a pile texture
PILE_TEXTURE_SIZE = 64


def read(path):
    return (root / path).read_text(encoding='utf-8')


# Returns (width, height) of a PNG file from its header.
def png_size(path):
    data = (root / path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path + ' is not a PNG'
    return struct.unpack('>II', data[16:24])


# The creature types of creatures.cfg: name -> mesh name
creatures_cfg = read('config/creatures.cfg')
types = {}
for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', creatures_cfg, re.S):
    fields = {}
    for line in block.splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            fields.setdefault(words[0], words[1])
    if 'Name' in fields:
        types[fields['Name']] = fields['MeshName']
assert len(types) == 35, len(types)

materials = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'materials' / 'scripts').glob('*.material'))
credits = read('CREDITS')

# 1. Pile models and textures: one per creature type, a material each, 64 x 64 textures
for name in types:
    assert (root / 'models' / ('Pile_' + name + '.mesh')).is_file(), 'models/Pile_' + name + '.mesh missing'
    assert (root / 'assets-src' / 'dirt' / ('Pile_' + name + '.blend')).is_file(), 'assets-src/dirt/Pile_' + name + '.blend missing'
    assert png_size('materials/textures/Pile_' + name + '.png') == (PILE_TEXTURE_SIZE, PILE_TEXTURE_SIZE), name + ' texture size'
    assert re.search(r'^material Pile_' + name + r'\b', materials, re.M), 'material Pile_' + name + ' missing'
# Level-specific classes keep their explicitly declared species mesh, including its unchanged pile geometry.
pile_aliases = {'DragonBoss': 'Dragon', 'BossDragon': 'Dragon', 'VeteranScarab': 'Scarab'}
expected_piles = {'Pile_' + name + '.mesh' for name in types} | {'Pile_' + name + '.mesh' for name in pile_aliases}
assert {path.name for path in (root / 'models').glob('Pile_*.mesh')} == expected_piles, 'exactly 35 species piles and three declared-species aliases'
for alias, original in pile_aliases.items():
    original_bytes = (root / 'models' / ('Pile_' + original + '.mesh')).read_bytes()
    assert (root / 'models' / ('Pile_' + alias + '.mesh')).read_bytes() == original_bytes, alias + ' changes the original geometry'
    assert ('Pile_' + original + '\n').encode('ascii') in original_bytes, original + ' pile material is missing'
    assert re.search(r'^material Pile_' + original + r'\b', materials, re.M), original + ' pile material has no definition'
    alias_credit = next((line for line in credits.splitlines() if line.startswith('models/Pile_' + alias + '.mesh ')), '')
    assert 'OD Team' in alias_credit and 'GPLv3+' in alias_credit and 'models/Pile_' + original + '.mesh' in alias_credit, alias + ' needs its own original-source credit'
assert len(list((root / 'materials' / 'textures').glob('Pile_*.png'))) == 35, 'exactly 35 pile textures'

# 2. Stain, decals and the seat: model, texture, material, Blender source
for name, source in [('BloodStain', 'assets-src/dirt/BloodStain.blend'), ('DirtStage1', 'assets-src/dirt/DirtStage1.blend'),
                     ('DirtStage2', 'assets-src/dirt/DirtStage2.blend'), ('DirtStage3', 'assets-src/dirt/DirtStage3.blend'),
                     ('ToiletSeat', 'assets-src/rooms/ToiletSeat.blend')]:
    assert (root / 'models' / (name + '.mesh')).is_file(), name + '.mesh missing'
    assert (root / 'materials' / 'textures' / (name + '.png')).is_file(), name + '.png missing'
    assert (root / source).is_file(), source + ' missing'
    assert re.search(r'^material ' + name + r'\b', materials, re.M), 'material ' + name + ' missing'

# 3. Particle, icon and the sounds
assert re.search(r'^particle_system DirtFlies\b', read('particles/DirtFlies.particle'), re.M), 'particle DirtFlies missing'
imageset = read('gui/ODIcons.imageset')
assert 'name="ToiletButton"' in imageset, 'icon ToiletButton missing in ODIcons.imageset'
assert (root / 'gui' / 'ODIcons.png').is_file()
for sound in ['Creatures/Default/Relieve/FxRelieve01.ogg', 'Creatures/Default/Clean/FxClean01.ogg',
              'Rooms/Toilet/Flush/FxToiletFlush01.ogg', 'Rooms/Toilet/Drip/FxToiletDrip01.ogg']:
    assert (root / 'sounds' / 'Spatial' / sound).is_file(), 'sounds/Spatial/' + sound + ' missing'
ambience = read('config/roomAmbience.cfg')
assert 'ToiletDrip' in ambience, 'roomAmbience.cfg has no toilet entry'

# 4. Clips: every creature skeleton has Relieve, the worker skeletons also Clean (binary skeleton: names end with a line feed)
skeletons = {}
for name, mesh in types.items():
    data = (root / 'models' / mesh).read_bytes()
    found = re.findall(rb'([A-Za-z0-9_]+)\.skeleton', data)
    assert found, mesh + ' has no skeleton'
    skeletons[name] = found[0].decode('ascii') + '.skeleton'
for name, skeleton in skeletons.items():
    clips = (root / 'models' / skeleton).read_bytes()
    assert b'Relieve\n' in clips, skeleton + ' of ' + name + ' has no Relieve clip'
for name in ('Kobold', 'DwarfWorker'):
    clips = (root / 'models' / skeletons[name]).read_bytes()
    assert b'Clean\n' in clips, skeletons[name] + ' of ' + name + ' has no Clean clip'
# The clip names the client asks for
animation_h = read('source/entities/MovableGameEntity.h')
assert 'relieve_anim = "Relieve"' in animation_h and 'clean_anim = "Clean"' in animation_h

# 5. Credits rows in the same change: every file is covered by a row
credit_lines = credits.splitlines()
patterns = []
for line in credit_lines:
    first = re.split(r'\s{2,}', line.strip())[0]
    for part in first.split(','):
        part = part.strip().lstrip('->').strip()
        part = re.sub(r'\s*\(.*$', '', part)
        if part:
            patterns.append(part)


# Whether a CREDITS row names the file (a path, a wildcard, or a file-name pattern in the same folder).
def credited(path):
    return any(fnmatch.fnmatchcase(path.lower(), p.lower()) for p in patterns)


files = ['models/Pile_Orc.mesh', 'assets-src/dirt/Pile_Orc.blend', 'materials/textures/Pile_Orc.png', 'models/BloodStain.mesh',
         'assets-src/dirt/BloodStain.blend', 'materials/textures/BloodStain.png', 'models/ToiletSeat.mesh',
         'assets-src/rooms/ToiletSeat.blend', 'materials/textures/ToiletSeat.png', 'models/DirtStage1.mesh',
         'models/DirtStage3.mesh', 'assets-src/dirt/DirtStage2.blend', 'materials/textures/DirtStage1.png',
         'materials/textures/DirtStage3.png', 'materials/scripts/DirtPiles.material', 'materials/scripts/DirtStage.material',
         'materials/scripts/ToiletSeat.material', 'particles/DirtFlies.particle', 'tools/gen_pile_textures.py',
         'tools/gen_dirt_decals.py',
         'sounds/Spatial/Creatures/Default/Relieve/FxRelieve01.ogg', 'sounds/Spatial/Creatures/Default/Clean/FxClean01.ogg',
         'sounds/Spatial/Rooms/Toilet/Flush/FxToiletFlush01.ogg', 'sounds/Spatial/Rooms/Toilet/Drip/FxToiletDrip01.ogg']
for path in files:
    assert credited(path), 'CREDITS has no row for ' + path
assert re.search(r'^gui/ODIcons\.png \(ToiletButton\)', credits, re.M), 'CREDITS row for the toilet icon'
for skeleton in sorted(set(skeletons.values())):
    assert re.search(r'^models/' + re.escape(skeleton) + r' \(clip', credits, re.M | re.I), 'CREDITS has no row for the clip in ' + skeleton
# The floor and wall pieces of the toilet room
for mask in range(16):
    name = 'Toilet' + format(mask, '04b')
    assert (root / 'materials' / 'textures' / (name + '.png')).is_file(), name + '.png missing'
# The credits must hold a row that names exactly the toilet floor pattern and its normal maps (no looser fallback), and
# every piece and normal map must be covered by a pattern of such a row
toilet_row = [line for line in credit_lines if line.startswith('materials/textures/Toilet????.png')]
assert len(toilet_row) == 1, 'CREDITS needs exactly one row that starts with the pattern materials/textures/Toilet????.png'
assert 'materials/textures/Toilet????Normal.png' in toilet_row[0].split('  ')[0], 'the toilet row must also name the Normal variants'
toilet_patterns = [part.strip() for part in re.split(r'\s{2,}', toilet_row[0].strip())[0].split(',')]
for mask in range(16):
    for suffix in ('', 'Normal'):
        piece = 'materials/textures/Toilet' + format(mask, '04b') + suffix + '.png'
        assert (root / piece).is_file(), piece + ' missing'
        assert any(fnmatch.fnmatchcase(piece.lower(), pattern.lower()) for pattern in toilet_patterns), 'the toilet row does not cover ' + piece
assert credited('materials/scripts/ToiletFloor.material'), 'CREDITS has no row for the toilet floor material'

print('dirt assets ok')
