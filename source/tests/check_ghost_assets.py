"""Inspect original ghost assets and existing binary skeleton clips without compiling or rendering."""
from pathlib import Path
import importlib.util
import hashlib
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

# Check the actual cauldron export, its reachable seat, material set and timed clips (decision 894).
def cauldron_delivery(credits, chunks_module):
    credited('models/GhostCauldron.skeleton', credits)
    mesh = (repo/'models/GhostCauldron.mesh').read_bytes()
    assert b'GhostCauldron.skeleton\n' in mesh, 'cauldron rig link'
    materials = sorted(set(name.decode() for name in re.findall(rb'(Ghost[A-Za-z]+)\n', mesh)))
    assert materials == ['GhostBrass','GhostCoal','GhostEctoplasm','GhostEmbers','GhostIron','GhostWindow'], materials
    material_script = read('materials/scripts/Ghost.material')
    for name in materials:
        assert re.search(r'^material '+name+r'\s*$', material_script, re.M), name

    # Walk serializer chunks, rather than searching arbitrary vertex bytes for chunk signatures.
    def children(data, start, end):
        while start < end:
            kind, size = struct.unpack_from('<HI', data, start)
            assert size >= 6 and start+size <= end, (kind,start,size)
            yield kind, start+6, start+size
            start += size
        assert start == end

    root = list(children(mesh, mesh.index(b'\n')+1, len(mesh)))
    assert len(root) == 1 and root[0][0] == 0x3000
    parts = list(children(mesh, root[0][1]+1, root[0][2]))
    bounds = next(struct.unpack_from('<7f',mesh,start) for kind,start,end in parts if kind == 0x9000)
    assert [round(value,4) for value in bounds[:6]] == [-1,-1,0,1,1,1.14], bounds
    assert re.search(r'\{"GhostCauldron", -1\.0f, -1\.0f, 1\.0f, 1\.0f, 1\.14f\}',
                     read('source/gamemap/RoomObjectBounds.h')), 'cauldron metadata'
    geometry = next((start,end) for kind,start,end in parts if kind == 0x5000)
    count = struct.unpack_from('<I',mesh,geometry[0])[0]
    assert count == 44549, count
    positions = []
    for kind,start,end in children(mesh,geometry[0]+4,geometry[1]):
        if kind == 0x5200:
            source, stride = struct.unpack_from('<HH',mesh,start)
            if source == 0:
                payload = list(children(mesh,start+4,end))
                assert len(payload) == 1 and payload[0][0] == 0x5210
                assert payload[0][2]-payload[0][1] == count*stride
                positions = [struct.unpack_from('<3f',mesh,payload[0][1]+i*stride) for i in range(count)]
    assert positions, 'missing positions'
    assert not any(x*x+y*y < .3**2 and z > 1.09 for x,y,z in positions), 'centre funnel or arms remain'
    assert any(abs(x-.5)<.08 and abs(y-.82)<.08 and abs(z-1.1)<.01 for x,y,z in positions), 'corner seat missing'
    assignments = [struct.unpack_from('<IHf',mesh,start) for kind,start,end in parts if kind == 0x7000]
    assert len({vertex for vertex,bone,weight in assignments if weight > 0}) == count, 'unweighted vertices'
    assert all(bone in (0,2) and abs(weight-1)<1e-6 for vertex,bone,weight in assignments), 'rigid body or inset glow weights'

    _, chunks = chunks_module.chunks((repo/'models/GhostCauldron.skeleton').read_bytes())
    bones = {data[6:data.index(b'\n',6)].decode(): data for kind,name,data in chunks if kind == chunks_module.BONE}
    assert set(bones) == {'Root','DeliverySocket','DeliveryGlow'}, set(bones)
    socket = bones['DeliverySocket']
    offset = struct.unpack_from('<3f',socket,socket.index(b'\n',6)+3)
    assert all(abs(a-b)<1e-6 for a,b in zip(offset,(.5,.82,1.1))), offset
    animations = {name:data for kind,name,data in chunks if kind == chunks_module.ANIMATION}
    assert set(animations) == {'Idle','Fill','Fill16','Fill13_3'}, set(animations)
    for name,expected in (('Idle',1),('Fill',20),('Fill16',16),('Fill13_3',13.3)):
        data = animations[name]
        duration = struct.unpack_from('<f',data,data.index(b'\n',6)+1)[0]
        assert abs(duration-expected)<1e-5, (name,duration)
        _, tracks = chunks_module.animation_children(data)
        assert {bone for kind,bone,track in tracks if kind == 0x4100} == {1,2}, (name,'socket/glow tracks')
    # The independent client-controlled inspection-window fill is retained byte for byte.
    assert hashlib.sha256((repo/'models/GhostCauldronFill.mesh').read_bytes()).hexdigest() == \
        '4bae03b231fed2dae105a0bc965e3c2e6ea98cefe8f5b0df1eeed4841f190a2c', 'inspection fill changed'


# Check the assigned asset families and exact existing generator registration without running its writing path.
# Inspect the shipped rigid hose fitting, whose unit dimensions are scaled by the live hose radius.
def hose_coupling(credits):
    credited('models/GhostHoseCoupling.mesh', credits)
    spec = importlib.util.spec_from_file_location('ghost_mesh_reader', repo/'source/tests/check_ghost_apparatus_visible.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mesh = module.read_mesh('GhostHoseCoupling')
    assert mesh['skeleton'] is None, 'fitting is rigid and follows the endpoint scene node'
    assert len(mesh['positions']) == 742, 'measured export vertex count'
    assert len(mesh['submeshes']) == 1 and mesh['submeshes'][0][0] == 'GhostPackSteel'
    assert [round(value, 2) for value in mesh['bounds'][:6]] == [-1.35, -1.35, -0.3, 1.35, 1.35, 2.0]
    assert max(mesh['submeshes'][0][1]) < 742, 'every index addresses a shipped vertex'
    assert all(0.77 < (x*x+y*y)**0.5 < 1.36 for x,y,z in mesh['positions']), 'open bore and stepped outer metal shell'
    script = read('materials/scripts/Ghost.material')
    steel = script.split('material GhostPackSteel', 1)[1].split('material GhostPackRubber', 1)[0]
    assert 'texture GhostPackSteel.png' in steel, 'same metal as the backpack'


# Check all original ghost assets and their runtime registrations.
def main():
    credits = read('CREDITS')
    hose_coupling(credits)
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
    cauldron_delivery(credits, chunks_module)
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
    # Rework 2 (owner decision 686): copper coil and the puff texture of the vapour plume and green glows.
    # Rework 3 (owner decision 697): the coil is a bevelled copper band with its own band texture; dim column glow in Idle.
    textures = ['ManaStillIron.png','ManaStillFlow.png','ManaStillGlowRamp.png','ManaStillWeb.png','ManaStillCopper.png',
        'ManaStillPuff.png','ManaStillCoilCopper.png']+['ManaStillEmbers_%d.png'%k for k in range(6)]
    for texture in textures:
        credited('materials/textures/'+texture,credits)
    still_mesh = (repo/'models/ManaStill.mesh').read_bytes()
    for name in ('ManaStillIron','ManaStillCoilGlass','ManaStillCoil','ManaStillEmbers','ManaStillBanked','ManaStillFireGlow',
            'ManaStillColumnGlow','ManaStillVapour','ManaStillDust','ManaStillWeb','ManaStillWebStrand','ManaStillCopper',
            'ManaStillPuff','ManaStillPuffDim','ManaStillFloorGlow','ManaStillResidue','ManaStillCoilCopper',
            'ManaStillColumnGlowDim'):
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
    # The coil is lit copper (its own texture), not glass; the vapour plume, its idle thread and the floor glow are additive.
    assert re.search(r'^material ManaStillCopper\s*\{(?:(?!^\}).)*texture ManaStillCopper\.png',still_material,re.S|re.M), 'copper coil'
    for name in ('ManaStillPuff','ManaStillPuffDim','ManaStillFloorGlow','ManaStillColumnGlowDim'):
        assert re.search(r'^material '+name+r'\s*\{(?:(?!^\}).)*scene_blend add',still_material,re.S|re.M), (name,'additive')
    # The coil band is lit with its own copper texture, which is not one flat colour (luminance spread 37.8 when painted,
    # the flat rework 2 copper had 9.7).
    assert re.search(r'^material ManaStillCoilCopper\s*\{(?:(?!^\}).)*texture ManaStillCoilCopper\.png',still_material,re.S|re.M), 'coil band'
    with Image.open(repo/'materials/textures/ManaStillCoilCopper.png') as band:
        luminance = list(band.convert('L').tobytes())
    mean = sum(luminance)/len(luminance)
    assert (sum((value-mean)**2 for value in luminance)/len(luminance))**0.5 > 30, 'coil copper texture is flat'
    still_skeleton = (repo/'models/ManaStill.skeleton').read_bytes()
    for bone in (b'Root',b'Glow',b'Coil',b'Dull',b'Webs',b'Embers',b'FireGlow',b'Bubble1',b'Wisp1',b'Pool',b'Banked',b'WebSway',
            b'Halo',b'FloorGlow',b'Puff1',b'Puff6',b'IdleGlow',b'IdlePuff1',b'IdlePuff2'):
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
    # Rework 2 (owner decision 686): heavy chains in their own steel, the book and green light also in Idle (dimmer).
    for texture in ['GhostPressIron.png','GhostPressPages.png','GhostPressRune.png','GhostPressStain.png','GhostPressChain.png']+['GhostPressGlow_%d.png'%k for k in range(4)]:
        credited('materials/textures/'+texture,credits)
    press_mesh = (repo/'models/GhostPress.mesh').read_bytes()
    for name in ('GhostPressIron','GhostPressEngraving','GhostPressEmblem','GhostPressPages','GhostPressRune','GhostPressFlow',
            'GhostPressVapour','GhostPressResidue','GhostBookLeather','GhostBrass','GhostEctoplasm','ManaStillWeb','ManaStillWebStrand',
            'GhostPressChain','GhostPressEmblemDim','GhostPressRuneDim','GhostPressGlow','GhostPressGlowDim','GhostPressPuff'):
        block = re.search(r'^\s*material\s+'+name+r'\s*\n\s*\{(.*?)^\}',still_material,re.M|re.S)
        assert block, name
        for texture in re.findall(r'(?:texture|anim_texture)\s+([^\n]+)',block[1]):
            for file in texture.split():
                if file.endswith('.png'):
                    assert (repo/'materials/textures'/file).is_file(), (name,file)
        assert name.encode()+b'\n' in press_mesh, ('ghost press uses',name)
    assert re.search(r'anim_texture GhostPressGlow_0\.png( GhostPressGlow_\d\.png){3} [\d.]+',still_material), 'emblem pulse'
    assert re.search(r'material GhostPressFlow\s*\{.*?scroll_anim -?[\d.]+ ',still_material,re.S), 'ectoplasm flow'
    # The chains are lit steel with their own texture; the green light, the idle glow and the haze are additive.
    assert re.search(r'^material GhostPressChain\s*\{(?:(?!^\}).)*texture GhostPressChain\.png',still_material,re.S|re.M), 'press chains'
    for name in ('GhostPressRuneDim','GhostPressGlow','GhostPressGlowDim','GhostPressPuff'):
        assert re.search(r'^material '+name+r'\s*\{(?:(?!^\}).)*scene_blend add',still_material,re.S|re.M), (name,'additive')
    press_skeleton = (repo/'models/GhostPress.skeleton').read_bytes()
    for bone in (b'Root',b'Press',b'Handle',b'Glow',b'Drips',b'Dull',b'Webs',b'SpringL',b'Stream',b'RuneL',b'Drip1',b'Drop1',
            b'Wisp1',b'Mist',b'Residue',b'WebSway',b'Book',b'Halo',b'FloorGlow',b'Puff1',b'Puff6',b'IdleGlow',b'IdleRuneL',
            b'IdleRuneR',b'IdleHalo',b'IdlePuff1',b'IdlePuff2'):
        assert bone+b'\n' in press_skeleton, bone
    # Rework 3 (owner decision 697): a clearly visible green light in Idle and a brighter one in Working. Rework 2 lit
    # Idle with a small soft dot texture (mean 41) times 0.13 0.46 0.18, which added almost nothing in the game. Now a
    # broad glow texture, a steady light set (bone Light: opening under the platen, pages, columns, emblem halos, floor)
    # shown in Working and Idle, and on top of it in Working the bright cards.
    credited('materials/textures/GhostApparatusGlow.png',credits)
    with Image.open(repo/'materials/textures/GhostApparatusGlow.png') as glow:
        glow_values = list(glow.convert('L').tobytes())
    assert sum(glow_values)/len(glow_values) > 70, 'apparatus glow texture is too small a spot'
    def manual_tint(name):
        block = re.search(r'^material '+name+r'\s*\{(.*?)^\}',still_material,re.M|re.S)
        assert block, name
        tint = re.search(r'colour_op_ex modulate src_texture src_manual ([\d.]+) ([\d.]+) ([\d.]+)',block[1])
        assert tint, (name,'tint')
        return [float(value) for value in tint.groups()]
    for name in ('GhostApparatusGlow','GhostApparatusGlowIdle'):
        assert re.search(r'^material '+name+r'\s*\{(?:(?!^\}).)*texture GhostApparatusGlow\.png',still_material,re.S|re.M), (name,'texture')
        assert re.search(r'^material '+name+r'\s*\{(?:(?!^\}).)*scene_blend add',still_material,re.S|re.M), (name,'additive')
        assert name.encode()+b'\n' in press_mesh, ('ghost press uses',name)
    idle_tint, working_tint = manual_tint('GhostApparatusGlowIdle'), manual_tint('GhostApparatusGlow')
    assert idle_tint[1] >= 0.6, ('idle glow too dim',idle_tint)
    assert all(w >= i for w,i in zip(working_tint,idle_tint)) and working_tint[1] > idle_tint[1], ('working not brighter',working_tint)
    assert manual_tint('GhostPressGlowDim')[1] >= 0.6, 'idle page glow too dim'
    assert min(manual_tint('GhostPressRuneDim')) >= 0.85, 'idle runes too dim'
    assert manual_tint('GhostPressEmblemDim')[1] >= 0.95, 'idle emblems too dim'
    for bone in (b'Light',b'LightHalo',b'LightFloor'):
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
    # Rework 2 (owner decision 686): light steel anvil face, grate and hammer head, green crystals in Working and Idle,
    # additive green light in the grate, on the floor and over the crystals, dim idle cores and glow.
    for texture in ['SoulForgeStone.png','SoulForgeIron.png','SoulForgeSteel.png','SoulForgeSpark.png']+['SoulForgeFire_%d.png'%k for k in range(4)]:
        credited('materials/textures/'+texture,credits)
    forge_mesh = (repo/'models/SoulForge.mesh').read_bytes()
    for name in ('SoulForgeStone','SoulForgeIron','SoulForgeFire','SoulForgeGlow','SoulForgeSpark','GhostCoal','ManaStillEmbers',
            'ManaStillBanked','GhostEctoplasm','GhostPressFlow','GhostCrystalCore','GhostEmbers','GhostPressVapour',
            'GhostPressResidue','ManaStillWeb','ManaStillWebStrand','SoulForgeSteel','SoulForgeCrystal','SoulForgeCoreDim',
            'GhostPressGlow','GhostPressGlowDim','GhostPressPuff','ManaStillFloorGlow'):
        block = re.search(r'^\s*material\s+'+name+r'\s*\n\s*\{(.*?)^\}',still_material,re.M|re.S)
        assert block, name
        for texture in re.findall(r'(?:texture|anim_texture)\s+([^\n]+)',block[1]):
            for file in texture.split():
                if file.endswith('.png'):
                    assert (repo/'materials/textures'/file).is_file(), (name,file)
        assert name.encode()+b'\n' in forge_mesh, ('soul forge uses',name)
    assert re.search(r'anim_texture SoulForgeFire_0\.png( SoulForgeFire_\d\.png){3} [\d.]+',still_material), 'forge flame flicker'
    # The anvil face, grate bars and hammer head are lit steel with their own texture; the green light is additive.
    assert re.search(r'^material SoulForgeSteel\s*\{(?:(?!^\}).)*texture SoulForgeSteel\.png',still_material,re.S|re.M), 'forge steel'
    for name in ('GhostPressGlow','GhostPressGlowDim','GhostPressPuff','ManaStillFloorGlow'):
        assert re.search(r'^material '+name+r'\s*\{(?:(?!^\}).)*scene_blend add',still_material,re.S|re.M), (name,'additive')
    for bone in (b'Root',b'Hammer',b'Sparks',b'Glow',b'Dull',b'Webs',b'Spirit',b'Flame1',b'Embers',b'FireGlow',b'Pool',
            b'CrystalGlow',b'Shock',b'Spark1',b'Wisp1',b'Wisp5',b'Banked',b'Residue',b'WebSway',b'Crystals',b'Halo',
            b'GrateGlow',b'FloorGlow',b'Puff1',b'Puff4',b'IdleGlow',b'IdleCore',b'IdleHalo',b'IdleGrate',b'IdleFloor',
            b'IdlePuff1',b'IdlePuff2'):
        assert bone+b'\n' in forge_skeleton, bone
    # Rework 3 (owner decision 697): clearly visible green light in Idle, brighter in Working, as on the press: the
    # steady set (bone Light: crystals and face, grate, floor) in Working and Idle with GhostApparatusGlowIdle, Working
    # adds GhostApparatusGlow; brighter crystals and idle cores.
    for name in ('GhostApparatusGlow','GhostApparatusGlowIdle'):
        assert name.encode()+b'\n' in forge_mesh, ('soul forge uses',name)
    crystal_block = re.search(r'^material SoulForgeCrystal\s*\{(.*?)^\}',still_material,re.M|re.S)
    emissive = [float(value) for value in re.search(r'emissive ([\d.]+) ([\d.]+) ([\d.]+)',crystal_block[1]).groups()]
    assert emissive[1] >= 0.9, ('forge crystals too dim',emissive)
    assert manual_tint('SoulForgeCoreDim')[1] >= 0.95, 'idle crystal cores too dim'
    for bone in (b'Light',b'LightHalo',b'LightGrate',b'LightFloor'):
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
