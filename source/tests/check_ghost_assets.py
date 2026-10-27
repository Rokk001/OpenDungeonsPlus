"""Inspect original ghost assets and existing binary skeleton clips without compiling or rendering."""
from pathlib import Path
import importlib.util
import json
import re
import struct
import xml.etree.ElementTree as ET
from PIL import Image

repo = Path(__file__).resolve().parents[2]

# Read one shipped text asset.
def read(path):
    return (repo / path).read_text(encoding='utf-8')

# Require a concrete asset and its own source/licence credit.
def credited(path, credits):
    asset = repo / path
    assert asset.is_file() and asset.stat().st_size, path
    rows = [row for row in credits.splitlines() if path in row]
    assert any(any(licence in row for licence in ('GPL','CC0','CC-BY','public domain')) for row in rows), path
    return rows

# Read actual native animation chunks using the maintained serializer parser.
def clips(credits):
    spec = importlib.util.spec_from_file_location('ghost_skeleton_chunks', repo/'tools/blender-assets/splice_animation_chunks.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    creatures = read('config/creatures.cfg')
    scared = ('Rat','Roach','Spider','CaveHornet','Goblin','Adventurer','Elf','Gnome','Dwarf1','Dwarf2')
    hunters = ('PitDemon','Troll','Skeleton','RunelordDwarf','Knight','Defender')
    for creature in scared+hunters:
        block = next(block for block in re.findall(r'\[Creature\](.*?)\[/Creature\]',creatures,re.S)
            if re.search(r'^\s*Name\s+'+creature+r'\s*$',block,re.M))
        mesh = re.search(r'^\s*MeshName\s+(\S+)',block,re.M)[1]
        skeleton = mesh.removesuffix('.mesh')+'.skeleton'
        credited('models/'+skeleton, credits)
        credited('assets-src/creatures/ghosts/'+skeleton.removesuffix('.skeleton')+'.blend', credits)
        _, chunks = module.chunks((repo/'models'/skeleton).read_bytes())
        animations = {name:data for kind,name,data in chunks if kind==module.ANIMATION}
        expected = ('Scared',) if creature in scared else ('Beam','Throw','Empty')
        for name in expected:
            assert name in animations, (creature,name)
            data = animations[name]
            duration = struct.unpack_from('<f',data,data.index(b'\n',6)+1)[0]
            assert abs(duration-1)<1e-6, (creature,name,duration)
            _, children = module.animation_children(data)
            assert any(kind==0x4100 for kind,bone,track in children), (creature,name,'no bone track')
        assert 'Idle' in animations and 'Walk' in animations, (creature,'prior clips lost')

# Check the assigned asset families and exact existing generator registration without running its writing path.
def main():
    credits = read('CREDITS')
    models = ('GhostCauldron','GhostCauldronFill','CrystalBowl','GhostBell','GhostHook','GhostHookEmpty',
        'GhostWallGauges','GhostBackpack','GhostBox','SoulCrystal')
    for name in models:
        credited('models/'+name+'.mesh',credits)
        credited('assets-src/rooms/ghostroom/'+name+'.blend',credits)
    bounds = read('source/gamemap/RoomObjectBounds.h')
    for name in models[:7]:
        assert re.search(r'\{"'+name+r'"\s*,',bounds), name
    for path in ('materials/scripts/Ghost.material','materials/scripts/GhostRoomFloor.material',
            'materials/textures/GhostRoomFloor.png','materials/textures/GhostRoomFloorNormal.png',
            'materials/textures/GhostNoise.png','gui/potions/soul_crystal.png',
            'assets-src/gui/icons/tiles/GhostRoomButton.png','assets-src/gui/items/soul_crystal.png'):
        credited(path,credits)
    material = read('materials/scripts/Ghost.material')+read('materials/scripts/GhostParticles.material')
    for name in ('GhostGlow','GhostLamps','GhostWindow','GhostBeam'):
        assert re.search(r'^\s*material\s+'+name+r'\b',material,re.M), name
    for value in ('scene_blend alpha_blend','depth_write off','scroll_anim 0 0.05'):
        assert value in material, value
    particles = read('particles/ChickenFeathers.particle')+read('particles/RoomAmbienceProduction.particle')
    for name in ('CauldronSteam','GhostRise','GhostDissolve','GhostBeam','EctoplasmBurst','GhostRevive','SoulCrystalBreak','WorkerVanish'):
        assert re.search(r'^\s*(?:particle_system\s+)?'+name+r'\s*\{',particles,re.M), name
        assert name in credits, name
    events = read('config/roomAmbienceSpells.cfg')
    assert 'SpellFxWorkerVanish' in events and re.search(r'System\s+WorkerVanish\b',events)
    ambience = read('config/roomAmbience.cfg')
    assert 'Rooms/GhostRoom/Hum' in ambience
    for family in ('Ghost/Howl','Rooms/GhostRoom/Hum','Rooms/GhostRoom/Bell','Rooms/GhostRoom/Beam',
            'Rooms/GhostRoom/BoxSnap','Rooms/GhostRoom/PressHiss','Rooms/GhostRoom/CrystalRing'):
        path = 'sounds/Spatial/'+family+'/'+family.rsplit('/',1)[1]+'.ogg'
        rows = credited(path,credits)
        assert (repo/path).read_bytes().startswith(b'OggS'), path
        assert any('CC0' in row and 'https://freesound.org/' in row for row in rows), path
    imageset = ET.parse(repo/'gui/ODIcons.imageset').getroot()
    icon = imageset.find("Image[@name='GhostRoomButton']")
    assert icon is not None
    with Image.open(repo/'gui'/imageset.get('imagefile')) as atlas, Image.open(repo/'assets-src/gui/icons/tiles/GhostRoomButton.png') as source:
        x,y,w,h = (int(icon.get(key)) for key in ('xPos','yPos','width','height'))
        assert (w,h)==(128,128) and source.size==(256,256), 'native painted source and logical icon size'
        assert atlas.crop((x,y,x+w,y+h)).convert('RGBA').getbbox() is not None, 'painted icon atlas binding'
    items = ET.parse(repo/'gui/Items.imageset').getroot()
    assert len(items.findall('Image'))==769, 'item atlas count'
    crystal = items.find("Image[@name='soul_crystal']")
    assert crystal is not None
    with Image.open(repo/'gui'/items.get('imagefile')) as atlas, Image.open(repo/'gui/potions/soul_crystal.png') as source:
        x,y,w,h = (int(crystal.get(key)) for key in ('xPos','yPos','width','height'))
        assert (w,h)==(128,128) and atlas.crop((x,y,x+w,y+h)).convert('RGBA').tobytes()==source.convert('RGBA').tobytes(), 'crystal binding'
    generator = read('tools/room-floors/generate_room_floors.py')
    block = re.search(r"'ghostroom':\s*\{(.*?)^    \},",generator,re.S|re.M)[1]
    for declaration in ("'field': torture_field", "'band': None", "'strength': 1.3", "'tone': 'ghostroom'",
            "'pieces': {'GhostRoomFloor': ('', 'GhostRoomFloorNormal')}"):
        assert declaration in block, declaration
    assert generator.index("'ghostroom': {",generator.index('ROOMS =')) < generator.index("'torture': {",generator.index('ROOMS ='))
    assert "'ghostroom': (0.42, 0.80, (0.92, 1.02, 0.95))" in generator
    assert "'ghostroom': (48.0, 0.7)" in generator
    assert "'ghostroom'" in generator.split('SEAM_CHECK_ROOMS =',1)[1].split(')',1)[0]
    clips(credits)
    print('ghost assets: ok (source registration only; writing floor --check and compiled bounds remain separate gated checks)')

if __name__ == '__main__':
    main()
