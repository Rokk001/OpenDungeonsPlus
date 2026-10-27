"""Author the original iron-and-brass ghost-room models and their editable Blender sources."""
from pathlib import Path
import json
import math
import shutil
import sys

import bpy
import bmesh
from mathutils import Vector, Quaternion

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'tools/blender-assets'))
import odp_ogre_io as oo

PALETTE = {
    'GhostIron': ((0.008, 0.013, 0.016), (0.045, 0.050, 0.045), 0.88),
    'GhostBrass': ((0.018, 0.025, 0.014), (0.16, 0.09, 0.024), 0.62),
    'GhostLeather': ((0.008, 0.003, 0.002), (0.055, 0.020, 0.007), 0.93),
    'GhostStone': ((0.015, 0.018, 0.019), (0.075, 0.080, 0.070), 0.98),
    'GhostGaugeFace': ((0.12, 0.11, 0.075), (0.35, 0.32, 0.21), 0.94),
}
SPECS = {
    'GhostCauldron': (2.00, 2.00, 1.60),
    'GhostCauldronFill': (0.40, 0.05, 0.60),
    'CrystalBowl': (0.50, 0.50, 0.40),
    'GhostBell': (0.60, 0.34, 0.90),
    'GhostHook': (0.40, 0.31, 0.80),
    'GhostHookEmpty': (0.40, 0.20, 0.80),
    'GhostWallGauges': (0.90, 0.20, 0.90),
    'GhostRack': (1.00, 0.16, 1.00),
    'GhostBackpack': (0.35, 0.25, 0.50),
    'GhostBox': (0.25, 0.25, 0.20),
    'SoulCrystal': (0.20, 0.20, 0.35),
}
PARTS = []


# Start an empty unit scene and its original surface materials.
def start_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    PARTS.clear()
    for name, (dark, light, rough) in PALETTE.items():
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        tree = mat.node_tree
        bsdf = tree.nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = 0.65 if name in {'GhostIron', 'GhostBrass'} else 0.0
        noise = tree.nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 9.0
        noise.inputs['Detail'].default_value = 5.0
        noise.inputs['Roughness'].default_value = 0.8
        ramp = tree.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = 0.2
        ramp.color_ramp.elements[0].color = (*dark, 1)
        ramp.color_ramp.elements[1].position = 0.8
        ramp.color_ramp.elements[1].color = (*light, 1)
        if name=='GhostIron':
            ramp.color_ramp.elements[1].position=.68
            rust=ramp.color_ramp.elements.new(.79)
            rust.color=(.12,.037,.012,1)
        tree.links.new(noise.outputs['Fac'], ramp.inputs[0])
        tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
        mat.diffuse_color = (*light, 1.0)
    glow_material('GhostWindow', (0.15, 0.65, 0.26, 0.28), 0.6)
    glow_material('GhostEctoplasm', (0.25, 0.95, 0.38, 0.9), 1.3)
    glow_material('GhostCrystal', (0.47, 0.88, 0.59, 0.70), 0.35)
    glow_material('GhostCrystalCore', (0.76, 1.0, 0.82, 1.0), 1.8)
    # The exported lamps share one two-colour animated texture; UV halves select red or green.
    mat = bpy.data.materials.new('GhostLamps')
    mat.use_nodes = True
    mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.15, 0.7, 0.1, 1.0)
    mat.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value = (0.15, 0.7, 0.1, 1.0)


# Create a translucent, gently luminous Blender preview material with the matching export name.
def glow_material(name, color, power):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 0.42
    bsdf.inputs['Alpha'].default_value = color[3]
    bsdf.inputs['Emission Color'].default_value = color
    bsdf.inputs['Emission Strength'].default_value = power
    mat.surface_render_method = 'DITHERED'
    return mat


# Bake original procedural paint and lamp pulses to the textures consumed by Ogre.
def bake_textures(force=False):
    directory=REPO/'materials/textures'
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=1
    for name in PALETTE:
        target=directory/(name+'.png')
        if target.is_file() and not force:
            mat=bpy.data.materials[name]
            tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image=bpy.data.images.load(str(target),check_existing=True)
            mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
            continue
        bpy.ops.mesh.primitive_plane_add(size=2)
        plane=bpy.context.object
        mat=bpy.data.materials[name]
        plane.data.materials.append(mat)
        tree=mat.node_tree
        output=tree.nodes.get('Material Output')
        bsdf=tree.nodes.get('Principled BSDF')
        emission=tree.nodes.new('ShaderNodeEmission')
        color_source=bsdf.inputs['Base Color'].links[0].from_socket
        tree.links.new(color_source,emission.inputs['Color'])
        tree.links.new(emission.outputs[0],output.inputs['Surface'])
        image=bpy.data.images.new(name+'Surface',512,512,alpha=False)
        node=tree.nodes.new('ShaderNodeTexImage')
        node.image=image
        tree.nodes.active=node
        bpy.ops.object.bake(type='EMIT',margin=8)
        image.filepath_raw=str(target)
        image.file_format='PNG'
        image.save()
        tree.links.new(bsdf.outputs[0],output.inputs['Surface'])
        tree.links.new(node.outputs['Color'],bsdf.inputs['Base Color'])
        tree.nodes.remove(emission)
        bpy.data.objects.remove(plane,do_unlink=True)
    if not (directory/'GhostLamps_0.png').is_file():
        bpy.ops.mesh.primitive_plane_add(size=2)
        plane=bpy.context.object
        mat=bpy.data.materials.new('LampPaintBake')
        mat.use_nodes=True
        plane.data.materials.append(mat)
        nodes=mat.node_tree.nodes
        links=mat.node_tree.links
        uv=nodes.new('ShaderNodeTexCoord')
        separate=nodes.new('ShaderNodeSeparateXYZ')
        split=nodes.new('ShaderNodeMath')
        split.operation='GREATER_THAN'
        split.inputs[1].default_value=.5
        color=nodes.new('ShaderNodeMixRGB')
        color.inputs[1].default_value=(.82,.025,.008,1)
        color.inputs[2].default_value=(.05,.78,.14,1)
        multiply=nodes.new('ShaderNodeMixRGB')
        multiply.blend_type='MULTIPLY'
        multiply.inputs[0].default_value=1
        emission=nodes.new('ShaderNodeEmission')
        links.new(uv.outputs['UV'],separate.inputs[0])
        links.new(separate.outputs['X'],split.inputs[0])
        links.new(split.outputs[0],color.inputs[0])
        links.new(color.outputs[0],multiply.inputs[1])
        links.new(multiply.outputs[0],emission.inputs[0])
        links.new(emission.outputs[0],nodes.get('Material Output').inputs['Surface'])
        for frame in range(8):
            value=.48+.52*(.5+.5*math.sin(2*math.pi*frame/8))
            multiply.inputs[2].default_value=(value,value,value,1)
            image=bpy.data.images.new('LampPulse'+str(frame),512,128,alpha=False)
            node=nodes.new('ShaderNodeTexImage')
            node.image=image
            nodes.active=node
            bpy.ops.object.bake(type='EMIT',margin=2)
            image.filepath_raw=str(directory/('GhostLamps_'+str(frame)+'.png'))
            image.file_format='PNG'
            image.save()
        bpy.data.objects.remove(plane,do_unlink=True)
    lamps=bpy.data.materials['GhostLamps']
    tree=lamps.node_tree
    image=tree.nodes.new('ShaderNodeTexImage')
    image.image=bpy.data.images.load(str(directory/'GhostLamps_0.png'),check_existing=True)
    bsdf=tree.nodes.get('Principled BSDF')
    tree.links.new(image.outputs['Color'],bsdf.inputs['Base Color'])
    tree.links.new(image.outputs['Color'],bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value=1.0


# Add a material, optional pivot group and planar UVs to a newly made component.
def finish(obj, material='GhostIron', group='Root', bevel=0.0):
    obj.data.materials.append(bpy.data.materials[material])
    if group:
        vg = obj.vertex_groups.new(name=group)
        vg.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new('Worn bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    PARTS.append(obj)
    return obj


# Create a worn rectangular solid, retaining its separate editable component.
def box(name, p, size, mat='GhostIron', bevel=0.008, rot=0.0, group='Root'):
    bpy.ops.mesh.primitive_cube_add(size=1, location=p)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = size
    obj.rotation_euler.z = rot
    return finish(obj, mat, group, min(bevel, min(size) * 0.22))


# Create a cylinder between any two endpoints.
def rod(name, a, b, radius, mat='GhostIron', vertices=16, group='Root'):
    a, b = Vector(a), Vector(b)
    delta = b - a
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=delta.length, location=(a+b)/2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = delta.to_track_quat('Z', 'Y')
    return finish(obj, mat, group, radius * 0.15)


# Create a tapering claw, crystal point or nozzle between two endpoints.
def cone(name, a, b, r1, r2, mat='GhostIron', vertices=12, group='Root'):
    a, b = Vector(a), Vector(b)
    delta = b - a
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=r1, radius2=r2, depth=delta.length, location=(a+b)/2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = delta.to_track_quat('Z', 'Y')
    return finish(obj, mat, group)


# Build a riveted ring facing upward or toward the front of the room object.
def ring(name, p, major, minor, mat='GhostBrass', front=False, group='Root'):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=32, minor_segments=8, location=p)
    obj = bpy.context.object
    obj.name = name
    if front:
        obj.rotation_euler.x = math.pi / 2
    return finish(obj, mat, group)


# Build a closed irregular surface of revolution for a bowl, bell or pressure vessel.
def lathe(name, profile, mat='GhostIron', sectors=32):
    vertices, faces = [], []
    for j, (radius, z) in enumerate(profile):
        for i in range(sectors):
            angle = 2 * math.pi * i / sectors
            wear = 1.0 + 0.008 * math.sin(i * 2.1 + j * 0.7)
            vertices.append((radius * math.cos(angle) * wear, radius * math.sin(angle) * wear, z))
    for j in range(len(profile) - 1):
        for i in range(sectors):
            n = (i + 1) % sectors
            faces.append((j*sectors+i, j*sectors+n, (j+1)*sectors+n, (j+1)*sectors+i))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=bm.verts[:],dist=0.000001)
    bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return finish(obj, mat)


# Place a row of uneven forged rivets around a circular joint.
def rivets(name, p, radius, count, front=False, size=0.025):
    for i in range(count):
        angle = i * 2 * math.pi / count + 0.05
        if front:
            x, y, z = p[0] + radius*math.cos(angle), p[1], p[2] + radius*math.sin(angle)
            rod(name+str(i), (x,y-0.01,z), (x,y+0.02,z), size, 'GhostIron', 8)
        else:
            x, y, z = p[0] + radius*math.cos(angle), p[1] + radius*math.sin(angle), p[2]
            rod(name+str(i), (x,y,z-0.01), (x,y,z+0.02), size, 'GhostBrass', 8)


# Make a bent pipe or hook from short joined, beveled metal segments.
def pipe(name, points, radius=0.035, material='GhostBrass'):
    for i in range(len(points)-1):
        rod(name+str(i), points[i], points[i+1], radius, material, 12)
    for i in range(1, len(points)-1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius*1.18, location=points[i])
        obj=bpy.context.object
        obj.name=name+'Elbow'+str(i)
        finish(obj, material)


# Create the leather pack, canister, stitched straps and a curved nozzle hose.
def backpack(scale=1.0, centre=(0,0,0), group='Root'):
    # Scale local pack details around the chosen attachment centre.
    def pos(x,y,z):
        return tuple(centre[i] + scale*v for i,v in enumerate((x,y,z)))
    box('Leather pack', pos(0,0,0.24), (0.29*scale,0.17*scale,0.42*scale), 'GhostLeather', 0.025*scale, group=group)
    for x in (-0.115,0.115):
        box('Worn leather strap', pos(x,0.095,0.24), (0.027*scale,0.02*scale,0.43*scale), 'GhostLeather', 0.003*scale, group=group)
        box('Strap buckle', pos(x,0.111,0.20), (0.043*scale,0.012*scale,0.047*scale), 'GhostBrass', 0.003*scale, group=group)
        for z in (0.08,0.13,0.32,0.37):
            box('Stitch', pos(x,0.108,z), (0.018*scale,0.003*scale,0.004*scale), 'GhostBrass', 0.001*scale, group=group)
    rod('Pressure canister', pos(-0.145,0.02,0.13), pos(-0.145,0.02,0.40), 0.065*scale, 'GhostBrass', 20, group)
    ring('Canister collar', pos(-0.145,0.02,0.37), 0.067*scale,0.012*scale,'GhostIron',group=group)
    pipe('Flexible hose', [pos(-.145,.02,.43),pos(-.04,.02,.46),pos(.17,-.05,.35),pos(.16,.06,.17)], .012*scale)
    cone('Capture nozzle', pos(.16,.06,.17), pos(.16,.10,.24), .025*scale,.014*scale,'GhostBrass',12,group)


# Author the press cauldron with four clawed feet, screw, rivets, pipes and green window.
def cauldron():
    body=lathe('Forged pressure body', [(0,.18),(.43,.18),(.59,.31),(.69,.77),(.64,1.02),(.54,1.08),(.46,1.08),(.47,.92),(.0,.92)])
    # The porthole is a true opening; the independent fill can sit behind its glass.
    bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=.258,depth=1.2,location=(0,.65,.65),rotation=(math.pi/2,0,0))
    cutter=bpy.context.object
    modifier=body.modifiers.new('Inspection opening','BOOLEAN')
    modifier.operation='DIFFERENCE'
    modifier.solver='EXACT'
    modifier.object=cutter
    bpy.context.view_layer.objects.active=body
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    ring('Lower reinforced rim',(0,0,.32),.58,.045)
    ring('Upper reinforced rim',(0,0,1.01),.64,.048)
    rivets('Drum rivet',(0,0,.96),.64,18,size=.024)
    for sx in (-1,1):
        for sy in (-1,1):
            rod('Claw leg',(sx*.46,sy*.46,.47),(sx*.77,sy*.77,.12),.09,'GhostIron')
            for offset in (-.085,0,.085):
                a=(sx*.72-offset,sy*.73+offset,.13)
                b=(sx*.93-offset*.35,sy*.93+offset*.35,.035)
                cone('Clawed toe',a,b,.055,.008,'GhostIron',10)
    for sx in (-1,1):
        box('Press upright',(sx*.74,-.05,.89),(.12,.16,1.36),'GhostIron',.018)
        box('Brass guide shoe',(sx*.74,-.05,1.22),(.18,.20,.19),'GhostBrass',.012)
    box('Uneven press crossbar',(0,-.05,1.52),(1.68,.22,.16),'GhostIron',.02,rot=.018)
    rod('Threaded press spindle',(0,-.05,1.02),(0,-.05,1.53),.055,'GhostBrass',20)
    for turn in range(13):
        ring('Screw thread',(0,-.05,1.03+turn*.036),.062,.013,'GhostIron')
    rod('Press wheel axle',(-.26,-.05,1.50),(.26,-.05,1.50),.022,'GhostIron')
    rod('Green inspection glass',(0,.697,.65),(0,.710,.65),.255,'GhostWindow',36)
    ring('Inspection window rim',(0,.725,.65),.277,.034,'GhostBrass',True)
    rivets('Window bolt',(0,.758,.65),.276,12,True,.017)
    for x in (-.10,.10):
        rod('Window iron grille',(x,.761,.43),(x,.761,.87),.012,'GhostIron',10)
    pipe('Left worn feed pipe',[(-.63,-.15,.74),(-.86,-.15,.74),(-.89,-.45,.36),(-.89,-.45,.01)],.042)
    pipe('Right worn exhaust',[(.51,-.36,.87),(.80,-.37,.87),(.82,-.63,.43),(.82,-.63,.02)],.035)


# Make the independent green fill plane with a floor-centred origin for height scaling.
def fill_level():
    box('Contained ectoplasm',(0,0,.30),(.40,.05,.60),'GhostEctoplasm',.015)


# Form a chipped bowl on a low battered stone pedestal.
def crystal_bowl():
    box('Chipped foot',(0,0,.045),(.36,.36,.09),'GhostStone',.025,rot=.055)
    cone('Stone pedestal',(0,0,.07),(0,0,.25),.14,.10,'GhostStone',9)
    basin=lathe('Chipped stone basin',[(.0,.21),(.17,.21),(.25,.33),(.245,.40),(.20,.39),(.15,.27),(.0,.26)],'GhostStone',19)
    for angle in (.8,2.7,4.3):
        x,y=.21*math.cos(angle),.21*math.sin(angle)
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y,.41),rotation=(.23,-.21,angle))
        cutter=bpy.context.object
        cutter.scale=(.08,.13,.095)
        modifier=basin.modifiers.new('Broken rim','BOOLEAN')
        modifier.operation='DIFFERENCE'
        modifier.solver='EXACT'
        modifier.object=cutter
        bpy.context.view_layer.objects.active=basin
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(cutter,do_unlink=True)


# Make an iron alarm bell with a deep skirt, clapper, bracket and striking hammer.
def bell():
    body=lathe('Heavy iron bell',[(.07,.78),(.10,.76),(.12,.61),(.19,.37),(.26,.27),(.27,.24),(.25,.20),(.22,.23),(.17,.36),(.09,.58),(.07,.70)],'GhostIron')
    ring('Bell skirt reinforcement',(0,0,.24),.25,.018,'GhostBrass')
    rod('Clapper',(0,0,.66),(0,0,.26),.016,'GhostIron',10)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=.04,location=(0,0,.25))
    finish(bpy.context.object,'GhostIron')
    box('Wall mounting plate',(0,-.12,.49),(.23,.035,.78),'GhostIron',.015)
    box('Top bracket',(0,-.01,.83),(.18,.28,.065),'GhostIron',.012)
    ring('Bell hanging eye',(0,0,.79),.065,.017,'GhostBrass',True)
    rod('Hammer shaft',(.16,-.08,.66),(.25,.06,.39),.018,'GhostIron',10)
    box('Hammer head',(.25,.065,.39),(.09,.08,.10),'GhostBrass',.012,rot=-.18)
    for x in (-.07,.07):
        for z in (.2,.72):
            rod('Wall bolt',(x,-.15,z),(x,-.10,z),.023,'GhostBrass',8)


# Build a rough wall rack with a forged hook and an optional leather pack.
def hook(with_pack):
    box('Worn hook backing',(0,-.02,.40),(.34,.05,.80),'GhostIron',.02)
    for z in (.12,.65):
        rod('Hook wall bolt',(0,-.055,z),(0,.025,z),.027,'GhostBrass',8)
    pipe('Forged curved hook',[(0,.025,.64),(0,.095,.60),(0,.12,.49),(0,.10,.45),(0,.07,.49)],.024,'GhostIron')
    if with_pack:
        backpack(.62,(0,.12,.06))


# Build an open free-standing iron rack frame (posts, feet, cross rails, diagonal brace) that carries a bell, hook or gauges.
def rack():
    for x in (-.46,.46):
        box('Rack post',(x,0,.50),(.07,.08,1.0),'GhostIron',.012)
        box('Rack foot',(x,0,.03),(.10,.16,.06),'GhostIron',.012)
        rod('Rack foot bolt',(x,-.085,.03),(x,.085,.03),.014,'GhostBrass',8)
    for z in (.20,.93):
        box('Rack rail',(0,0,z),(.96,.06,.07),'GhostIron',.01)
    rod('Rack brace',(-.42,0,.24),(.42,0,.90),.018,'GhostIron',10)
    for x in (-.46,.46):
        for z in (.20,.93):
            rod('Rack rail bolt',(x,-.045,z),(x,.045,z),.016,'GhostBrass',8)


# Build two trembling gauge needles, brass pipes and red/green warning lamps.
def gauges():
    box('Instrument backing',(0,-.025,.45),(.78,.05,.82),'GhostIron',.025)
    for sx in (-1,1):
        pipe('Gauge feed',[(sx*.40,-.005,.02),(sx*.40,-.005,.83),(sx*.22,.02,.83),(sx*.22,.045,.70)],.025)
    for idx,x in enumerate((-.22,.22)):
        rod('Gauge housing',(x,.005,.56),(x,.080,.56),.17,'GhostBrass',28)
        rod('Stained gauge face',(x,.081,.56),(x,.085,.56),.145,'GhostGaugeFace',32)
        ring('Riveted gauge bezel',(x,.089,.56),.159,.018,'GhostBrass',True)
        group='NeedleLeft' if idx==0 else 'NeedleRight'
        angle=.63 if idx==0 else 2.15
        end=(x+.11*math.cos(angle),.103,.56+.11*math.sin(angle))
        rod('Trembling needle',(x,.103,.56),end,.008,'GhostIron',8,group)
        rod('Needle cap',(x,.102,.56),(x,.113,.56),.017,'GhostBrass',12,group)
        for tick in range(10):
            a=.3+tick*2.5/9
            rod('Gauge tick',(x+.111*math.cos(a),.096,.56+.111*math.sin(a)),(x+.132*math.cos(a),.096,.56+.132*math.sin(a)),.004,'GhostIron',6)
    for index,x in enumerate((-.20,.20)):
        ring('Lamp brass socket',(x,.07,.18),.065,.012,'GhostBrass',True)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.052,location=(x,.085,.18))
        obj=finish(bpy.context.object,'GhostLamps')
        for uv in obj.data.uv_layers.active.data:
            uv.uv.x = uv.uv.x*.35 + (.075 if index==0 else .575)


# Form the small locking capture box with a real visible hinge, latch and green slit.
def ghost_box():
    box('Riveted box case',(0,0,.085),(.24,.23,.17),'GhostIron',.012)
    box('Hinged iron lid',(0,0,.18),(.25,.25,.035),'GhostIron',.009)
    for x in (-.075,.075):
        rod('Rear hinge pin',(x-.025,-.12,.17),(x+.025,-.12,.17),.013,'GhostBrass',10)
    box('Green containment slit',(0,.121,.10),(.14,.008,.022),'GhostWindow',.003)
    box('Locking latch',(0,.129,.155),(.035,.015,.055),'GhostBrass',.003)
    for x in (-.095,.095):
        for y in (-.08,.08):
            rod('Box lid rivet',(x,y,.192),(x,y,.200),.008,'GhostBrass',8)


# Shape a jagged pale-green crystal and its luminous inner core.
def crystal():
    cone('Main jagged crystal',(0,0,.02),(.012,.006,.35),.083,0,'GhostCrystal',5)
    cone('Broken side crystal',(-.045,.0,.01),(-.08,.015,.23),.052,0,'GhostCrystal',4)
    cone('Short crystal splinter',(.05,-.015,.0),(.085,-.015,.18),.042,0,'GhostCrystal',5)
    cone('Glow core',(0,0,.03),(.01,.002,.29),.038,0,'GhostCrystalCore',5)


# Join the editable components, fit the specified bounding box and keep its origin on the floor.
def join_and_fit(name):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in PARTS:
        obj.select_set(True)
    bpy.context.view_layer.objects.active=PARTS[0]
    bpy.ops.object.join()
    obj=bpy.context.object
    obj.name=name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    lo=Vector((min(v.co.x for v in obj.data.vertices),min(v.co.y for v in obj.data.vertices),min(v.co.z for v in obj.data.vertices)))
    hi=Vector((max(v.co.x for v in obj.data.vertices),max(v.co.y for v in obj.data.vertices),max(v.co.z for v in obj.data.vertices)))
    size=hi-lo
    target=SPECS[name]
    factors=Vector(tuple(target[i]/size[i] for i in range(3)))
    centre=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    for vertex in obj.data.vertices:
        vertex.co=(vertex.co-centre)*factors
    obj.data.update()
    obj.location=(0,0,0)
    return obj,factors,centre


# Give the two gauge needles a real repeating motion without moving the instrument body.
def gauge_rig(obj,factors,centre):
    bpy.ops.object.armature_add(enter_editmode=True)
    arm=bpy.context.object
    arm.name='GhostWallGaugesRig'
    root=arm.data.edit_bones[0]
    root.name='Root'
    root.head=(0,0,0)
    root.tail=(0,0,.05)
    for name,x in (('NeedleLeft',-.22),('NeedleRight',.22)):
        bone=arm.data.edit_bones.new(name)
        pivot=(Vector((x,.103,.56))-centre)*factors
        bone.head=pivot
        bone.tail=pivot+Vector((0,.025,0))
        bone.parent=root
    bpy.ops.object.mode_set(mode='OBJECT')
    arm['ogre_bone_order']=['Root','NeedleLeft','NeedleRight']
    modifier=obj.modifiers.new('Gauge needles','ARMATURE')
    modifier.object=arm
    obj.parent=arm
    action=oo.new_action(arm,'Idle',1.0)
    oo.assign_action(arm,action)
    for name,phase in (('NeedleLeft',0.0),('NeedleRight',1.3)):
        for frame in range(25):
            t=frame/24
            angle=.025*math.sin(2*math.pi*5*t+phase)+.013*math.sin(2*math.pi*9*t)
            oo.add_pose_key(arm,action,name,t,rot=Quaternion((0,1,0),angle))
    return arm


# Add a normal Blender preview camera and lights for visual review of the authored asset.
def preview(name,private):
    scene=bpy.context.scene
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_x=960
    scene.render.resolution_y=960
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=True
    scene.world=bpy.data.worlds.new('Dark workshop')
    scene.world.color=(.045,.045,.045)
    size=max(SPECS[name])
    target=Vector((0,0,SPECS[name][2]*.48))
    bpy.ops.object.camera_add(location=(size*1.7,size*2.4,size*1.9))
    camera=bpy.context.object
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'
    camera.data.ortho_scale=size*1.60
    scene.camera=camera
    for p,power,colour in (((size*1.5,size*2.0,size*3.0),260,(1.0,.87,.72)),((-size*2,-size,size*2),180,(.55,.70,1.0))):
        bpy.ops.object.light_add(type='AREA',location=p)
        lamp=bpy.context.object
        lamp.data.energy=power*size*size
        lamp.data.color=colour
        lamp.data.shape='DISK'
        lamp.data.size=size*2
        lamp.rotation_euler=(target-lamp.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX'
    scene.render.filepath=str(private/(name+'-preview.png'))
    bpy.ops.render.render(write_still=True)


# Save one independent source, export its mesh and capture exact bounds for the room metadata.
def main():
    args=sys.argv[sys.argv.index('--')+1:]
    name=args[0]
    private=Path(args[1])
    private.mkdir(parents=True,exist_ok=True)
    out=REPO/'out/ghost-models'
    out.mkdir(parents=True,exist_ok=True)
    start_scene()
    bake_textures('--rebake' in args)
    builders={'GhostCauldron':cauldron,'GhostCauldronFill':fill_level,'CrystalBowl':crystal_bowl,'GhostBell':bell,'GhostHook':lambda:hook(True),'GhostHookEmpty':lambda:hook(False),'GhostWallGauges':gauges,'GhostRack':rack,'GhostBackpack':backpack,'GhostBox':ghost_box,'SoulCrystal':crystal}
    builders[name]()
    obj,factors,centre=join_and_fit(name)
    arm=gauge_rig(obj,factors,centre) if name=='GhostWallGauges' else None
    report=oo.export_mesh_xml(obj,arm,str(out/(name+'.mesh.xml')),name+'.skeleton',smooth=False)
    if arm:
        oo.export_skeleton_xml(arm,str(out/(name+'.skeleton.xml')))
    bounds={axis:[min(v.co[i] for v in obj.data.vertices),max(v.co[i] for v in obj.data.vertices)] for i,axis in enumerate('xyz')}
    report['bounds']=bounds
    report['dimensions']=list(SPECS[name])
    (out/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    source=REPO/'assets-src/rooms/ghostroom'/(name+'.blend')
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    shutil.copyfile(source,private/source.name)
    preview(name,private)
    print('GHOST_MODEL_DONE '+name+' '+json.dumps(report),flush=True)


if __name__=='__main__':
    import traceback
    log_dir=REPO/'out/ghost-models'
    log_dir.mkdir(parents=True,exist_ok=True)
    model_name=sys.argv[sys.argv.index('--')+1]
    with (log_dir/(model_name+'.author.log')).open('w',encoding='utf-8',buffering=1) as log:
        sys.stdout=log
        sys.stderr=log
        try:
            main()
        except Exception:
            traceback.print_exc()
            raise
