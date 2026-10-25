"""Tavern assets: models, Blender sources, materials and textures, icon sources, particles, sounds and their ambience
entries, the CREDITS rows, the nine tavern clips in every creature skeleton and the innkeeper clips.

What is checked
  models      TavernCounter, Innkeeper, TavernKeg, TavernTable, TavernMug, Vomit: mesh, one Blender source each, a
              material in a material script, the innkeeper's skeleton with the clips Idle, Pour and Cheer
  materials   TavernWood, TavernBrass, TavernStone (and the other object materials) with a 128 x 128 texture each, the
              floor and wall materials with their textures and normal maps, the bird effect material
  icons       the painted 256 x 256 sources of TavernButton and BeerButton (the atlas entries are pinned by
              check_forged_icons.py)
  particles   TavernSmoke and DuelBirds, each defined once; the materials they use exist; the bird atlas is 2048 x 2048
  sounds      Pour, Murmur, Clink, Slap and Cheer exist as mono 22050 Hz Vorbis, the two ambience families are loadable,
              the ambience entries name them; scripts/check_sound_sources.py is green
  clips       Drink, Slap, ArmWrestle, Dice, KnockedOut, GetUp, Stagger, Vomit and Hangover in every skeleton a creature
              type uses (the clip names are listed once, the client asks for them in EntityAnimation)
  credits     every file above has a CREDITS row, every changed skeleton has a row for its new clips

Calls (from the repository root):
  python source/tests/check_tavern_assets.py            plain file checks, no compiler, no game
"""
from pathlib import Path
import fnmatch
import re
import struct
import subprocess
import sys

root = Path(__file__).resolve().parents[2]

# The nine clips every creature skeleton gets, in the order of the design
TAVERN_CLIPS = ['Drink', 'Slap', 'ArmWrestle', 'Dice', 'KnockedOut', 'GetUp', 'Stagger', 'Vomit', 'Hangover']
# The clips of the innkeeper figure
INNKEEPER_CLIPS = ['Idle', 'Pour', 'Cheer']
# Size of the object textures, of the painted icon sources and of the bird atlas
OBJECT_TEXTURE_SIZE = 128
ICON_SOURCE_SIZE = 256
BIRD_ATLAS_SIZE = 2048
# Format of the tavern sounds
SOUND_CHANNELS = 1
SOUND_RATE = 22050


# Returns the text of a repository file.
def read(path):
    return (root / path).read_text(encoding='utf-8', errors='replace')


# Returns (width, height) of a PNG file from its header.
def png_size(path):
    data = (root / path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path + ' is not a PNG'
    return struct.unpack('>II', data[16:24])


# Returns (channels, rate) of an Ogg Vorbis file from its identification header.
def vorbis_format(path):
    data = (root / path).read_bytes()
    assert data[:4] == b'OggS', path + ' is not an Ogg file'
    at = data.index(b'\x01vorbis')
    channels = data[at + 11]
    rate = struct.unpack('<I', data[at + 12:at + 16])[0]
    return channels, rate


# Returns the creature types of creatures.cfg: name -> mesh name
def creature_types():
    types = {}
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', read('config/creatures.cfg'), re.S):
        fields = {}
        for line in block.splitlines():
            words = line.split()
            if len(words) >= 2 and not words[0].startswith('#'):
                fields.setdefault(words[0], words[1])
        if 'Name' in fields:
            types[fields['Name']] = fields['MeshName']
    return types


materials = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'materials' / 'scripts').glob('*.material'))
credits = read('CREDITS')

# 1. Models: mesh, Blender source, material, the innkeeper's skeleton
MODELS = {'TavernCounter': 'assets-src/rooms/tavern/TavernCounter.blend', 'Innkeeper': 'assets-src/rooms/tavern/Innkeeper.blend',
          'TavernKeg': 'assets-src/rooms/tavern/TavernKeg.blend', 'TavernTable': 'assets-src/rooms/tavern/TavernTable.blend',
          'TavernMug': 'assets-src/rooms/tavern/TavernMug.blend', 'Vomit': 'assets-src/dirt/Vomit.blend'}
for name, source in MODELS.items():
    mesh = root / 'models' / (name + '.mesh')
    assert mesh.is_file() and mesh.stat().st_size > 0, 'models/' + name + '.mesh missing'
    assert (root / source).is_file(), source + ' missing'
mesh_material_names = {'TavernCounter': ('TavernWood', 'TavernBrass', 'TavernSign'), 'TavernKeg': ('TavernWood', 'TavernIron', 'TavernBrass'),
                       'TavernTable': ('TavernStone', 'TavernWood'), 'TavernMug': ('TavernWood', 'TavernFoam'),
                       'Innkeeper': ('TavernCloth', 'TavernHood', 'TavernSkin'), 'Vomit': ('TavernVomit',)}
for name, used in mesh_material_names.items():
    data = (root / 'models' / (name + '.mesh')).read_bytes()
    assert any(m.encode('ascii') in data for m in used), 'models/' + name + '.mesh uses none of ' + ', '.join(used)
assert b'Innkeeper.skeleton' in (root / 'models' / 'Innkeeper.mesh').read_bytes(), 'the innkeeper mesh needs its skeleton'
innkeeper_skeleton = (root / 'models' / 'Innkeeper.skeleton').read_bytes()
for clip in INNKEEPER_CLIPS:
    assert (clip + '\n').encode('ascii') in innkeeper_skeleton, 'Innkeeper.skeleton has no clip ' + clip

# 2. Materials and textures
for name in ('TavernWood', 'TavernBrass', 'TavernStone', 'TavernIron', 'TavernCloth', 'TavernHood', 'TavernSkin', 'TavernFoam',
             'TavernSign', 'TavernVomit'):
    assert re.search(r'^material ' + name + r'\b', materials, re.M), 'material ' + name + ' missing'
    assert png_size('materials/textures/tavern/' + name + '.png') == (OBJECT_TEXTURE_SIZE, OBJECT_TEXTURE_SIZE), name + ' texture size'
for name in ('TavernFloor', 'TavernWall'):
    assert re.search(r'^material ' + name + r'\b', materials, re.M), 'material ' + name + ' missing'
    for suffix in ('', 'Normal'):
        assert png_size('materials/textures/tavern/' + name + suffix + '.png')[0] > 0, name + suffix + '.png missing'
assert re.search(r'^material TavernDuelBirds\b', materials, re.M), 'material TavernDuelBirds missing'
assert png_size('materials/textures/tavern/DuelBird.png') == (BIRD_ATLAS_SIZE, BIRD_ATLAS_SIZE), 'bird atlas size'
assert (root / 'assets-src' / 'rooms' / 'tavern' / 'DuelBird.png').is_file(), 'bird source missing'

# 3. Icons: the painted sources of the two buttons
for icon in ('TavernButton', 'BeerButton'):
    assert png_size('assets-src/gui/icons/tiles/' + icon + '.png') == (ICON_SOURCE_SIZE, ICON_SOURCE_SIZE), icon + ' source size'

# 4. Particles: each defined once in all particle files, the materials exist
all_particles = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'particles').glob('*.particle'))
for system in ('TavernSmoke', 'DuelBirds'):
    assert len(re.findall(r'^particle_system ' + system + r'\s*$', all_particles, re.M)) == 1, 'particle ' + system + ' must be defined exactly once'
tavern_particles = read('particles/Tavern.particle')
for used in re.findall(r'^\s*material\s+(\S+)', tavern_particles, re.M):
    assert re.search(r'^material ' + used + r'\b', materials, re.M), 'particle material ' + used + ' missing'
ambience = read('config/roomAmbience.cfg')
assert 'System      TavernSmoke' in ambience and 'Match       TavernCounter' in ambience, 'the counter smoke is wired in roomAmbience.cfg'
assert 'DuelBirds' in read('source/render/RenderManager.cpp'), 'the bird particle is attached by the render code'

# 5. Sounds: the five files as mono 22050 Hz Vorbis, the two ambience families, the ambience entries
for sound in ('sounds/Rooms/Tavern/Pour.ogg', 'sounds/Rooms/Tavern/Murmur.ogg', 'sounds/Rooms/Tavern/Clink.ogg',
              'sounds/Creatures/Default/Slap.ogg', 'sounds/Creatures/Default/Cheer.ogg',
              'sounds/Spatial/Rooms/Tavern/Murmur/Murmur.ogg', 'sounds/Spatial/Rooms/Tavern/Clink/Clink.ogg'):
    assert (root / sound).is_file(), sound + ' missing'
    assert vorbis_format(sound) == (SOUND_CHANNELS, SOUND_RATE), sound + ' must be mono 22050 Hz Vorbis, found ' + str(vorbis_format(sound))
for family in ('Rooms/Tavern/Murmur', 'Rooms/Tavern/Clink'):
    assert 'Family      ' + family in ambience, 'roomAmbience.cfg needs the family ' + family
assert 'Loop        yes' in ambience[ambience.index('Name        TavernMurmur'):], 'the murmur is a loop'
sound_check = subprocess.run([sys.executable, str(root / 'scripts' / 'check_sound_sources.py')], capture_output=True, text=True, cwd=str(root))
assert sound_check.returncode == 0, 'check_sound_sources.py failed:\n' + sound_check.stdout + sound_check.stderr

# 6. The nine clips in every skeleton a creature type uses (binary skeleton: the clip names end with a line feed)
animation_h = read('source/entities/MovableGameEntity.h')
for token in ('drink_anim = "Drink"', 'armwrestle_anim = "ArmWrestle"', 'slap_anim = "Slap"', 'dice_anim = "Dice"', 'knockedout_anim = "KnockedOut"',
              'getup_anim = "GetUp"', 'stagger_anim = "Stagger"', 'vomit_anim = "Vomit"', 'hangover_anim = "Hangover"'):
    assert token in animation_h, 'EntityAnimation lacks ' + token
types = creature_types()
assert len(types) == 35, len(types)
skeletons = {}
for name, mesh in types.items():
    data = (root / 'models' / mesh).read_bytes()
    found = re.findall(rb'([A-Za-z0-9_]+)\.skeleton', data)
    assert found, mesh + ' has no skeleton'
    skeletons[name] = found[0].decode('ascii') + '.skeleton'
unique_skeletons = sorted(set(skeletons.values()))
assert len(unique_skeletons) == 32, 'the 35 types use 32 skeletons, found ' + str(len(unique_skeletons))
for skeleton in unique_skeletons:
    data = (root / 'models' / skeleton).read_bytes()
    for clip in TAVERN_CLIPS:
        assert len(re.findall(rb'(?<![A-Za-z0-9_])' + clip.encode('ascii') + rb'\n', data)) == 1, skeleton + ' must hold the clip ' + clip + ' exactly once'

# 7. CREDITS: a row for every file of the tavern assets and for every skeleton with new clips
patterns = []
for line in credits.splitlines():
    first = re.split(r'\s{2,}', line.strip())[0]
    for part in first.split(','):
        part = re.sub(r'\s*\(.*$', '', part.strip().lstrip('->').strip())
        if part:
            patterns.append(part)


# Whether a CREDITS row names the file (a path or a wildcard pattern).
def credited(path):
    return any(fnmatch.fnmatchcase(path.lower(), p.lower()) for p in patterns)


files = ['models/' + name + '.mesh' for name in MODELS] + list(MODELS.values()) + ['models/Innkeeper.skeleton']
files += ['materials/scripts/TavernObjects.material', 'materials/scripts/TavernFloor.material', 'materials/scripts/TavernWall.material',
          'materials/scripts/TavernEffects.material', 'particles/Tavern.particle', 'materials/textures/tavern/DuelBird.png',
          'assets-src/rooms/tavern/DuelBird.png', 'assets-src/gui/icons/tiles/TavernButton.png', 'assets-src/gui/icons/tiles/BeerButton.png',
          'materials/textures/tavern/TavernFloor.png', 'materials/textures/tavern/TavernFloorNormal.png',
          'materials/textures/tavern/TavernWall.png', 'materials/textures/tavern/TavernWallNormal.png']
files += ['materials/textures/tavern/' + name + '.png' for name in ('TavernWood', 'TavernBrass', 'TavernStone', 'TavernIron', 'TavernCloth',
                                                                      'TavernHood', 'TavernSkin', 'TavernFoam', 'TavernSign', 'TavernVomit')]
files += ['sounds/Rooms/Tavern/Pour.ogg', 'sounds/Rooms/Tavern/Murmur.ogg', 'sounds/Rooms/Tavern/Clink.ogg',
          'sounds/Creatures/Default/Slap.ogg', 'sounds/Creatures/Default/Cheer.ogg',
          'sounds/Spatial/Rooms/Tavern/Murmur/Murmur.ogg', 'sounds/Spatial/Rooms/Tavern/Clink/Clink.ogg']
for path in files:
    assert credited(path), 'CREDITS has no row for ' + path
for skeleton in unique_skeletons:
    assert re.search(r'^models/' + re.escape(skeleton) + r' \(new Drink, Slap, ArmWrestle, Dice, KnockedOut, GetUp, Stagger, Vomit, Hangover tracks\)',
                     credits, re.M | re.I), 'CREDITS has no row for the new clips in ' + skeleton
# Every sound row names a source address and the licence CC0 (the recordings are real, never generated)
for sound in ('Pour', 'Murmur', 'Clink', 'Slap', 'Cheer'):
    row = [l for l in credits.splitlines() if re.search(r'/' + sound + r'\.ogg\s', l)]
    assert row, 'CREDITS has no row for ' + sound + '.ogg'
    for line in row:
        assert 'https://freesound.org/' in line and 'CC0' in line, sound + ' row needs a source address and CC0: ' + line[:80]

print('tavern assets ok')
