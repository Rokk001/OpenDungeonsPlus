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
        'GhostWallGauges','GhostBackpack','GhostBox','SoulCrystal','GhostRack')
    for name in models:
        credited('models/'+name+'.mesh',credits)
        credited('assets-src/rooms/ghostroom/'+name+'.blend',credits)
    # Apparatus models: the mana still (state clips) and the mana crystal item; their Blender sources live outside Git.
    for path in ('models/ManaStill.mesh','models/ManaStill.skeleton','models/ManaCrystal.mesh','materials/textures/GhostCobweb.png'):
        credited(path,credits)
    spec = importlib.util.spec_from_file_location('ghost_still_chunks', repo/'tools/blender-assets/splice_animation_chunks.py')
    chunks_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chunks_module)
    _, chunks = chunks_module.chunks((repo/'models/ManaStill.skeleton').read_bytes())
    still_clips = {name for kind,name,data in chunks if kind==chunks_module.ANIMATION}
    assert {'Working','Idle','Locked'} <= still_clips, still_clips
    assert b'ManaStill.skeleton' in (repo/'models/ManaStill.mesh').read_bytes()
    apparatus = read('source/rooms/RoomGhostRoom.cpp')
    assert re.search(r'meshes\[APPARATUS_COUNT\]=\{"ManaStill",',apparatus), 'mana still mesh'
    assert 'MANA_CRYSTAL_MESH = "ManaCrystal"' in read('source/entities/ItemBagEntity.cpp')
    still_material = read('materials/scripts/Ghost.material')
    for name in ('ManaCrystal','ManaCrystalDull','ManaStillGlass','GhostEmbers','GhostCoal','GhostGlassDull','GhostCobweb'):
        assert re.search(r'^\s*material\s+'+name+r'\s*$',still_material,re.M), name
    # Mana still rework after mockup A (owner decision 665): rusty iron, flickering embers, flowing coil, vapour, draped webs.
    textures = ['ManaStillIron.png','ManaStillFlow.png','ManaStillGlowRamp.png','ManaStillWeb.png']+['ManaStillEmbers_%d.png'%k for k in range(6)]
    for texture in textures:
        credited('materials/textures/'+texture,credits)
    still_mesh = (repo/'models/ManaStill.mesh').read_bytes()
    for name in ('ManaStillIron','ManaStillCoilGlass','ManaStillCoil','ManaStillEmbers','ManaStillBanked','ManaStillFireGlow',
            'ManaStillColumnGlow','ManaStillVapour','ManaStillDust','ManaStillWeb','ManaStillWebStrand'):
        block = re.search(r'^\s*material\s+'+name+r'\s*\n\s*\{(.*?)^\}',still_material,re.M|re.S)
        assert block, name
        for texture in re.findall(r'(?:texture|anim_texture)\s+([^\n]+)',block[1]):
            for file in texture.split():
                if file.endswith('.png'):
                    assert (repo/'materials/textures'/file).is_file(), (name,file)
        assert name.encode()+b'\n' in still_mesh, ('mana still uses',name)
    # Visible motion: the embers flicker by texture, the coil ectoplasm flows, the vapour drifts.
    assert re.search(r'anim_texture ManaStillEmbers_0\.png( ManaStillEmbers_\d\.png){5} [\d.]+',still_material), 'ember flicker'
    assert re.search(r'material ManaStillCoil\s*\{.*?scroll_anim -?[\d.]+ ',still_material,re.S), 'coil flow'
    still_skeleton = (repo/'models/ManaStill.skeleton').read_bytes()
    for bone in (b'Root',b'Glow',b'Coil',b'Dull',b'Webs',b'Embers',b'FireGlow',b'Bubble1',b'Wisp1',b'Pool',b'Banked',b'WebSway'):
        assert bone+b'\n' in still_skeleton, bone
    assert b'ManaCrystal\n' in (repo/'models/ManaCrystal.mesh').read_bytes(), 'mana crystal material'
    # Ghost press (state clips); the research book it makes keeps today's Grimoire mesh.
    for path in ('models/GhostPress.mesh','models/GhostPress.skeleton'):
        credited(path,credits)
    _, chunks = chunks_module.chunks((repo/'models/GhostPress.skeleton').read_bytes())
    press_clips = {name for kind,name,data in chunks if kind==chunks_module.ANIMATION}
    assert {'Working','Idle','Locked'} <= press_clips, press_clips
    assert b'GhostPress.skeleton' in (repo/'models/GhostPress.mesh').read_bytes()
    assert re.search(r'meshes\[APPARATUS_COUNT\]=\{"ManaStill","GhostPress",',apparatus), 'ghost press mesh'
    assert 'RESEARCH_BOOK_MESH = "Grimoire"' in read('source/entities/ItemBagEntity.cpp')
    for name in ('GhostBookLeather','GhostBookPages'):
        assert re.search(r'^\s*material\s+'+name+r'\s*$',still_material,re.M), name
    # Ghost press rework after mockup A (owner decision 665): rusty iron, pulsing emblems, open book with turning runes,
    # flowing ectoplasm, vapour, idle stain and draped webs.
    for texture in ['GhostPressIron.png','GhostPressPages.png','GhostPressRune.png','GhostPressStain.png']+['GhostPressGlow_%d.png'%k for k in range(4)]:
        credited('materials/textures/'+texture,credits)
    press_mesh = (repo/'models/GhostPress.mesh').read_bytes()
    for name in ('GhostPressIron','GhostPressEngraving','GhostPressEmblem','GhostPressPages','GhostPressRune','GhostPressFlow',
            'GhostPressVapour','GhostPressResidue','GhostBookLeather','GhostBrass','GhostEctoplasm','ManaStillWeb','ManaStillWebStrand'):
        block = re.search(r'^\s*material\s+'+name+r'\s*\n\s*\{(.*?)^\}',still_material,re.M|re.S)
        assert block, name
        for texture in re.findall(r'(?:texture|anim_texture)\s+([^\n]+)',block[1]):
            for file in texture.split():
                if file.endswith('.png'):
                    assert (repo/'materials/textures'/file).is_file(), (name,file)
        assert name.encode()+b'\n' in press_mesh, ('ghost press uses',name)
    assert re.search(r'anim_texture GhostPressGlow_0\.png( GhostPressGlow_\d\.png){3} [\d.]+',still_material), 'emblem pulse'
    assert re.search(r'material GhostPressFlow\s*\{.*?scroll_anim -?[\d.]+ ',still_material,re.S), 'ectoplasm flow'
    press_skeleton = (repo/'models/GhostPress.skeleton').read_bytes()
    for bone in (b'Root',b'Press',b'Handle',b'Glow',b'Drips',b'Dull',b'Webs',b'SpringL',b'Stream',b'RuneL',b'Drip1',b'Drop1',
            b'Wisp1',b'Mist',b'Residue',b'WebSway'):
        assert bone+b'\n' in press_skeleton, bone
    # Soul forge (state clips, self-striking hammer); the level crystal it makes keeps today's SoulCrystal mesh.
    for path in ('models/SoulForge.mesh','models/SoulForge.skeleton'):
        credited(path,credits)
    forge_skeleton = (repo/'models/SoulForge.skeleton').read_bytes()
    _, chunks = chunks_module.chunks(forge_skeleton)
    forge_clips = {name for kind,name,data in chunks if kind==chunks_module.ANIMATION}
    assert {'Working','Idle','Locked'} <= forge_clips, forge_clips
    assert b'Hammer' in forge_skeleton, 'soul forge hammer bone'
    assert b'SoulForge.skeleton' in (repo/'models/SoulForge.mesh').read_bytes()
    assert re.search(r'meshes\[APPARATUS_COUNT\]=\{"ManaStill","GhostPress","SoulForge"\}',apparatus), 'soul forge mesh'
    assert 'ItemInstance::createSoulCrystal()' in apparatus, 'level crystal'
    assert re.search(r'^\s*material\s+GhostForgeFire\s*$',still_material,re.M), 'GhostForgeFire'
    # Soul forge rework after mockup A (owner decision 665): weathered stone, rusted iron, flickering green flames,
    # glow, sparks, ectoplasm pool and crystals, vapour, idle embers and stain, draped webs; motion bones of the clips.
    for texture in ['SoulForgeStone.png','SoulForgeIron.png','SoulForgeSpark.png']+['SoulForgeFire_%d.png'%k for k in range(4)]:
        credited('materials/textures/'+texture,credits)
    forge_mesh = (repo/'models/SoulForge.mesh').read_bytes()
    for name in ('SoulForgeStone','SoulForgeIron','SoulForgeFire','SoulForgeGlow','SoulForgeSpark','GhostCoal','ManaStillEmbers',
            'ManaStillBanked','GhostEctoplasm','GhostPressFlow','ManaCrystal','GhostCrystalCore','GhostEmbers','GhostPressVapour',
            'GhostPressResidue','ManaStillWeb','ManaStillWebStrand'):
        block = re.search(r'^\s*material\s+'+name+r'\s*\n\s*\{(.*?)^\}',still_material,re.M|re.S)
        assert block, name
        for texture in re.findall(r'(?:texture|anim_texture)\s+([^\n]+)',block[1]):
            for file in texture.split():
                if file.endswith('.png'):
                    assert (repo/'materials/textures'/file).is_file(), (name,file)
        assert name.encode()+b'\n' in forge_mesh, ('soul forge uses',name)
    assert re.search(r'anim_texture SoulForgeFire_0\.png( SoulForgeFire_\d\.png){3} [\d.]+',still_material), 'forge flame flicker'
    for bone in (b'Root',b'Hammer',b'Sparks',b'Glow',b'Dull',b'Webs',b'Spirit',b'Flame1',b'Embers',b'FireGlow',b'Pool',
            b'CrystalGlow',b'Shock',b'Spark1',b'Wisp1',b'Wisp5',b'Banked',b'Residue',b'WebSway'):
        assert bone+b'\n' in forge_skeleton, bone
    # Ectoplasm item: its own static mesh replaces the cauldron fill placeholder (the cauldron keeps its fill level).
    credited('models/Ectoplasm.mesh',credits)
    assert (repo/'models/Ectoplasm.mesh').read_bytes()[2:20] == b'[MeshSerializer_v1', 'ectoplasm mesh'
    assert 'ECTOPLASM_MESH = "Ectoplasm"' in read('source/entities/ItemBagEntity.cpp')
    for name in ('EctoplasmShell','EctoplasmSwirl','GhostEctoplasm'):
        assert re.search(r'^\s*material\s+'+name+r'\s*$',still_material,re.M), name
    bounds = read('source/gamemap/RoomObjectBounds.h')
    assert re.search(r'\{"ManaStill"\s*,',bounds), 'ManaStill'
    assert re.search(r'\{"GhostPress"\s*,',bounds), 'GhostPress'
    assert re.search(r'\{"SoulForge"\s*,',bounds), 'SoulForge'
    for name in models[:7]+models[10:]:
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
    particles = read('particles/ChickenFeathers.particle')+read('particles/RoomAmbienceProduction.particle')+read('particles/RoomAmbienceSpellsExtra.particle')
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
