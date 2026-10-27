"""Lava spa assets: models, Blender sources, materials, floor, particles, icon, sounds and their ambience entry, the
CREDITS rows, the two bath clips in every creature skeleton and the clips of the pool attendant.

What is checked
  models      SpaMudPool, SpaPoolRim, SpaChair, SpaSpringboard, PoolAttendant: mesh, one Blender source each, the materials
              the mesh names exist in a material script, the attendant mesh names its skeleton; every creature skeleton has
              a Blender source below assets-src/rooms/spa/creatures
  clips       PoolAttendant.skeleton holds Sit, Whistle, TowelWave, Doze, Walk, Climb and Jump once each; Bathe and Jump are
              in every skeleton a creature type uses exactly once, next to the clips that were there before; the clip names
              are listed in EntityAnimation
  materials   SpaMud with the slow scroll 0.02 0.01, the emissive SpaLavaGlow, SpaFloor as the copy of TortureFloor with
              the name replaced, the floor textures, the textures the materials use
  floor       tools/room-floors/generate_room_floors.py lists spa (rooms, tone, flatten, seam check) and paints SpaFloor.png
              and SpaFloorNormal.png byte for byte as they are stored
  particles   SpaSteam after RoomAmbSteam and SpaMudSplash after ChickenFeathers, each defined once, with the values of the
              design; the materials they use exist
  icon        the painted 256 x 256 source of SpaButton, its slot and its imageset entry (the atlas is pinned by
              check_forged_icons.py)
  sounds      Bubble, Whistle and Splash exist as mono 22050 Hz Vorbis, the families are loadable, the ambience entry loops the
              bubbling at the pool; scripts/check_sound_sources.py is green
  credits     every file above has a CREDITS row, every changed skeleton has a row for its new clips, every sound row names a
              source address and the licence CC0
  bounds      check_room_object_bounds.py is green (the four furniture meshes have their bounds rows)

Calls (from the repository root):
  python source/tests/check_spa_assets.py            file checks and the floor painter, no compiler, no game
"""
from pathlib import Path
import fnmatch
import re
import struct
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]

# The bath clips every creature skeleton gets and the clips of the pool attendant
BATH_CLIPS = ['Bathe', 'Jump']
ATTENDANT_CLIPS = ['Sit', 'Whistle', 'TowelWave', 'Doze', 'Walk', 'Climb', 'Jump']
# Size of the painted icon source
ICON_SOURCE_SIZE = 256
# Format of the spa sounds
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


# Returns the text of a block "name { ... }" of an Ogre script that starts at a line "<kind> <name>".
def script_block(text, kind, name):
    match = re.search(r'^' + kind + r' ' + re.escape(name) + r'\b.*?(?=^' + kind + r' |\Z)', text, re.M | re.S)
    assert match is not None, kind + ' ' + name + ' missing'
    return match.group(0)


materials = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'materials' / 'scripts').glob('*.material'))
credits = read('CREDITS')
spa_material = read('materials/scripts/Spa.material')

# 1. Models: mesh, Blender source, the materials of the mesh, the attendant's skeleton
MODELS = {name: 'assets-src/rooms/spa/' + name + '.blend'
          for name in ('SpaMudPool', 'SpaPoolRim', 'SpaChair', 'SpaSpringboard', 'PoolAttendant')}
for name, source in MODELS.items():
    mesh = root / 'models' / (name + '.mesh')
    assert mesh.is_file() and mesh.stat().st_size > 0, 'models/' + name + '.mesh missing'
    assert (root / source).is_file(), source + ' missing'
    for used in set(re.findall(rb'Spa[A-Za-z]+', mesh.read_bytes())):
        assert re.search(r'^material ' + used.decode('ascii') + r'\b', materials, re.M), \
            'models/' + name + '.mesh uses the material ' + used.decode('ascii') + ' which no material script defines'
assert b'SpaMud' in (root / 'models' / 'SpaMudPool.mesh').read_bytes(), 'the pool uses SpaMud'
assert b'SpaLavaGlow' in (root / 'models' / 'SpaPoolRim.mesh').read_bytes(), 'the rim carries the lava seam'
assert b'PoolAttendant.skeleton' in (root / 'models' / 'PoolAttendant.mesh').read_bytes(), 'the attendant mesh needs its skeleton'
attendant_skeleton = (root / 'models' / 'PoolAttendant.skeleton').read_bytes()
for clip in ATTENDANT_CLIPS:
    assert len(re.findall(rb'(?<![A-Za-z0-9_])' + clip.encode('ascii') + rb'\n', attendant_skeleton)) == 1, \
        'PoolAttendant.skeleton must hold the clip ' + clip + ' exactly once'
# The clip names the code asks for are the clips of the skeleton
attendant_h = read('source/entities/PoolAttendantEntity.h')
for token in ('sit = "Sit"', 'whistle = "Whistle"', 'towelWave = "TowelWave"', 'doze = "Doze"', 'climb = "Climb"'):
    assert token in attendant_h, 'PoolAttendantEntity.h lacks the clip name ' + token
animation_h = read('source/entities/MovableGameEntity.h')
for token in ('walk_anim = "Walk"', 'bathe_anim = "Bathe"', 'jump_anim = "Jump"'):
    assert token in animation_h, 'EntityAnimation lacks ' + token

# 2. Materials and textures
mud = script_block(spa_material, 'material', 'SpaMud')
assert 'scroll_anim 0.02 0.01' in mud, 'the mud scrolls slowly'
glow = script_block(spa_material, 'material', 'SpaLavaGlow')
assert 'emissive' in glow and 'lighting off' in glow, 'the lava seam glows'
for used in re.findall(r'^\s*texture\s+(\S+)', spa_material, re.M):
    assert list((root / 'materials' / 'textures').rglob(used)), 'texture ' + used + ' of Spa.material is missing'
torture = read('materials/scripts/TortureFloor.material')
spa_floor = read('materials/scripts/SpaFloor.material')


# The material script without the trailing blanks of each line (the copy was cleaned of them)
def normalised(text):
    return [line.rstrip() for line in text.replace('\r\n', '\n').split('\n')]


assert normalised(spa_floor) == normalised(torture.replace('TortureFloor', 'SpaFloor')), \
    'SpaFloor.material must be TortureFloor.material with every TortureFloor replaced by SpaFloor'
for suffix in ('', 'Normal'):
    assert png_size('materials/textures/SpaFloor' + suffix + '.png')[0] > 0, 'SpaFloor' + suffix + '.png missing'
assert png_size('materials/textures/SpaFloor.png') == png_size('materials/textures/TortureFloor.png'), 'SpaFloor.png has the size of the torture floor'

# 3. The floor painter lists the spa and paints the stored textures byte for byte
generator = read('tools/room-floors/generate_room_floors.py')
assert re.search(r"'spa': \{\s*'field': torture_field, 'band': None, 'strength': 1\.3, 'tone': 'spa',\s*'pieces': \{'SpaFloor': \('', 'SpaFloorNormal'\)\},", generator)
assert generator.index("    'spa': {") < generator.index("    'torture': {"), 'the spa entry stands directly before the torture entry'
assert "'spa': (0.50, 0.85, (1.10, 0.98, 0.90))," in generator and "'spa': (48.0, 0.7)," in generator
assert re.search(r"SEAM_CHECK_ROOMS = \('spa', ", generator)
with tempfile.TemporaryDirectory(prefix='odp-spa-floor-') as directory:
    painted = subprocess.run([sys.executable, str(root / 'tools' / 'room-floors' / 'generate_room_floors.py'), directory, '--only=spa', '--check'],
                             capture_output=True, text=True, cwd=str(root))
    assert painted.returncode == 0, 'generate_room_floors.py failed:\n' + painted.stdout + painted.stderr
    assert 'spa wrap seam ratio' in painted.stdout, 'the check output lists the spa floor'
    for name in ('SpaFloor.png', 'SpaFloorNormal.png'):
        assert (Path(directory) / name).read_bytes() == (root / 'materials' / 'textures' / name).read_bytes(), name + ' differs from what the painter writes'

# 4. Particles: each defined once, the values of the design, the order next to the template, the materials exist
all_particles = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'particles').glob('*.particle'))
for system in ('SpaSteam', 'SpaMudSplash'):
    assert len(re.findall(r'^particle_system ' + system + r'\s*$', all_particles, re.M)) == 1, 'particle ' + system + ' must be defined exactly once'
production = read('particles/RoomAmbienceProduction.particle')
assert production.index('particle_system RoomAmbSteam') < production.index('particle_system SpaSteam'), 'SpaSteam follows RoomAmbSteam'
steam = script_block(production.replace('particle_system', 'particle_system'), 'particle_system', 'SpaSteam')
assert re.search(r'colour_range_start\s+0\.9 0\.9 0\.9 0\.5', steam) and re.search(r'emission_rate\s+2\b', steam) and re.search(r'time_to_live\s+3\b', steam)
feathers = read('particles/ChickenFeathers.particle')
assert feathers.index('particle_system ChickenFeathers') < feathers.index('particle_system SpaMudSplash'), 'SpaMudSplash follows ChickenFeathers'
splash = script_block(feathers, 'particle_system', 'SpaMudSplash')
assert 'colour_range_start 0.30 0.20 0.12 1.0' in splash and 'duration 0.5' in splash, 'the mud splash is brown and lasts half a second'
for text in (steam, splash):
    for used in re.findall(r'^\s*material\s+(\S+)', text, re.M):
        assert re.search(r'^material ' + used + r'\b', materials, re.M), 'particle material ' + used + ' missing'
room_h = read('source/rooms/RoomSpa.cpp')
assert 'SPA_STEAM_EFFECT = "SpaSteam"' in room_h and 'SPA_SPLASH_EFFECT = "SpaMudSplash"' in room_h, 'the room names the particles'

# 5. Icon: the painted source, its slot and its imageset entry
assert png_size('assets-src/gui/icons/tiles/SpaButton.png') == (ICON_SOURCE_SIZE, ICON_SOURCE_SIZE), 'SpaButton source size'
assert '"SpaButton"' in read('assets-src/gui/icons/slots.json') or 'SpaButton' in read('assets-src/gui/icons/slots.json'), 'SpaButton has a slot'
assert len(re.findall(r'<Image [^>]*name="SpaButton"', read('gui/ODIcons.imageset'))) == 1, 'SpaButton has one imageset entry'
assert 'OpenDungeonsIcons/SpaButton' in read('gui/WindowTabRooms.layout') or 'SpaButton' in read('gui/WindowTabRooms.layout')
assert 'SpaButton' in read('gui/WindowSkillTree.layout'), 'the research tree shows the button'

# 6. Sounds: the three files as mono 22050 Hz Vorbis, the families, the ambience entry
ambience = read('config/roomAmbience.cfg')
for family in ('Bubble', 'Whistle', 'Splash'):
    sound = 'sounds/Spatial/Rooms/Spa/' + family + '/' + family + '.ogg'
    assert (root / sound).is_file(), sound + ' missing'
    assert vorbis_format(sound) == (SOUND_CHANNELS, SOUND_RATE), sound + ' must be mono 22050 Hz Vorbis, found ' + str(vorbis_format(sound))
bubble_effect = ambience[ambience.index('Name        SpaBubbleLoop'):]
bubble_effect = bubble_effect[:bubble_effect.index('[/Effect]')]
for line in ('Target      Object', 'Match       SpaMudPool', 'Kind        Sound', 'Family      Rooms/Spa/Bubble', 'Loop        yes'):
    assert line in bubble_effect, 'the bubbling loop lacks the line ' + line
assert '"Rooms/Spa/Whistle"' in read('source/entities/PoolAttendantEntity.cpp') and '"Rooms/Spa/Splash"' in room_h
sound_check = subprocess.run([sys.executable, str(root / 'scripts' / 'check_sound_sources.py')], capture_output=True, text=True, cwd=str(root))
assert sound_check.returncode == 0, 'check_sound_sources.py failed:\n' + sound_check.stdout + sound_check.stderr

# 7. The bath clips in every skeleton a creature type uses (binary skeleton: the clip names end with a line feed)
types = creature_types()
assert len(types) == 35, len(types)
skeletons = {}
for name, mesh in types.items():
    found = re.findall(rb'([A-Za-z0-9_]+)\.skeleton', (root / 'models' / mesh).read_bytes())
    assert found, mesh + ' has no skeleton'
    skeletons[name] = found[0].decode('ascii') + '.skeleton'
unique_skeletons = sorted(set(skeletons.values()))
assert len(unique_skeletons) == 32, 'the 35 types use 32 skeletons, found ' + str(len(unique_skeletons))
for skeleton in unique_skeletons:
    data = (root / 'models' / skeleton).read_bytes()
    for clip in BATH_CLIPS:
        assert len(re.findall(rb'(?<![A-Za-z0-9_])' + clip.encode('ascii') + rb'\n', data)) == 1, skeleton + ' must hold the clip ' + clip + ' exactly once'
    # The clips of the tavern and the older ones are still there
    for clip in ('Idle', 'Walk', 'Drink', 'Hangover'):
        assert (clip + '\n').encode('ascii') in data, skeleton + ' lost its clip ' + clip
    assert (root / 'assets-src' / 'rooms' / 'spa' / 'creatures' / (skeleton[:-len('.skeleton')] + '.blend')).is_file(), \
        'no Blender source for ' + skeleton
sources = sorted(p.name for p in (root / 'assets-src' / 'rooms' / 'spa' / 'creatures').glob('*.blend'))
assert len(sources) == 32, 'one Blender source per skeleton, found ' + str(len(sources))

# 8. CREDITS: a row for every file of the spa assets and for every skeleton with new clips
patterns = []
for line in credits.splitlines():
    first = re.split(r'\s{2,}', line.strip())[0]
    # Rows written with single blanks start with the path (no blank inside a path)
    if re.match(r'^(?:models|materials|sounds|assets-src|particles)/\S+\s', line.strip()):
        first = line.strip().split()[0]
    for part in first.split(','):
        part = re.sub(r'\s*\(.*$', '', part.strip().lstrip('->').strip())
        if part:
            patterns.append(part)


# Whether a CREDITS row names the file (a path or a wildcard pattern).
def credited(path):
    return any(fnmatch.fnmatchcase(path.lower(), p.lower()) for p in patterns)


files = ['models/' + name + '.mesh' for name in MODELS] + list(MODELS.values()) + ['models/PoolAttendant.skeleton']
files += ['materials/scripts/SpaFloor.material', 'materials/textures/SpaFloor.png', 'materials/textures/SpaFloorNormal.png',
          'assets-src/gui/icons/tiles/SpaButton.png',
          'sounds/Spatial/Rooms/Spa/Bubble/Bubble.ogg', 'sounds/Spatial/Rooms/Spa/Whistle/Whistle.ogg', 'sounds/Spatial/Rooms/Spa/Splash/Splash.ogg']
for path in files:
    assert credited(path), 'CREDITS has no row for ' + path
assert 'particles/RoomAmbienceProduction.particle (SpaSteam)' in credits and 'particles/ChickenFeathers.particle (SpaMudSplash)' in credits
for skeleton in unique_skeletons:
    assert re.search(r'^models/' + re.escape(skeleton) + r' \(Bathe, Jump clips\)', credits, re.M | re.I), \
        'CREDITS has no row for the new clips in ' + skeleton
    assert credited('assets-src/rooms/spa/creatures/' + skeleton[:-len('.skeleton')] + '.blend'), 'CREDITS has no row for the Blender source of ' + skeleton
# Every sound row names a source address and the licence CC0 (the recordings are real, never generated)
for sound in ('Bubble', 'Whistle', 'Splash'):
    row = [l for l in credits.splitlines() if re.search(r'Spa/' + sound + r'/' + sound + r'\.ogg\s', l)]
    assert row, 'CREDITS has no row for ' + sound + '.ogg'
    for line in row:
        assert 'https://freesound.org/' in line and 'CC0' in line, sound + ' row needs a source address and CC0: ' + line[:80]

# 9. The furniture bounds and the sound sources are checked by their own scripts
bounds = subprocess.run([sys.executable, str(root / 'source' / 'tests' / 'check_room_object_bounds.py')], capture_output=True, text=True, cwd=str(root))
assert bounds.returncode == 0, 'check_room_object_bounds.py failed:\n' + bounds.stdout[-2000:] + bounds.stderr[-2000:]

print('spa assets ok')
