# Keeps the seated tavern clips of one creature as actions of its Blender source, exports them and renders a review.
#
# Usage: blender --background <Model>.blend --python tavern_seats_blend.py -- <seats.skeleton.xml> <table.mesh.xml>
#        <review folder> [--save <exported.skeleton.xml>]
# Without --save nothing is written to the Blender source: the actions exist only for the review images.
import math
import os
import sys
import xml.etree.ElementTree as ET

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odp_ogre_io as oo

CLIPS = ['Sit', 'SitDrink', 'SitSlap', 'SitSlapped', 'SitArmWrestle', 'SitDice', 'SitSlumped']
# The moment of a clip that the review shows, as a share of its length
REVIEW_MOMENTS = {'Sit': 0.5, 'SitDrink': 0.5, 'SitSlap': 0.4, 'SitSlapped': 0.2, 'SitArmWrestle': 0.5, 'SitDice': 0.5,
                  'SitSlumped': 0.5}
# Where the table stands for a guest on the middle of its bench who looks along -y, and how it is scaled in the game
TABLE_DISTANCE = 0.4116
TABLE_SCALE = 0.84
REVIEW_SIZE = 360


# Returns the armature that the mesh of the source file is bound to.
def source_armature():
    return next(obj for obj in bpy.data.objects if obj.type == 'ARMATURE')


# Replaces the actions of the seated clips with the authored ones.
def add_actions(arm, path):
    bones, parents, anims = oo.read_skeleton(path)
    found = set()
    for name, length, tracks in anims:
        assert name in CLIPS, name
        old = bpy.data.actions.get(name)
        if old is not None:
            bpy.data.actions.remove(old)
        action = oo._make_action(arm, name, length, tracks)
        action.use_fake_user = True
        found.add(name)
    assert found == set(CLIPS), found


# Builds the table of the game in the place it has for the guest.
def add_table(path):
    root = ET.parse(path).getroot()
    shared = root.find('sharedgeometry')
    points = [[float(vertex.find('position').get(axis)) for axis in 'xyz']
              for buffer in shared.findall('vertexbuffer') if buffer.get('positions') == 'true' for vertex in buffer]
    faces = []
    for submesh in root.find('submeshes'):
        for face in submesh.find('faces'):
            faces.append([int(face.get(key)) for key in ('v1', 'v2', 'v3')])
    mesh = bpy.data.meshes.new('ReviewTable')
    mesh.from_pydata(points, [], faces)
    table = bpy.data.objects.new('ReviewTable', mesh)
    table.scale = (TABLE_SCALE, TABLE_SCALE, 1.0)
    table.rotation_euler = (0.0, 0.0, math.pi / 2.0)
    table.location = (0.0, -TABLE_DISTANCE, 0.0)
    bpy.context.scene.collection.objects.link(table)
    return table


# Places an orthographic camera that looks at the guest from the given side.
def add_camera(direction, size):
    data = bpy.data.cameras.new('ReviewCamera')
    data.type = 'ORTHO'
    data.ortho_scale = size
    camera = bpy.data.objects.new('ReviewCamera', data)
    bpy.context.scene.collection.objects.link(camera)
    target = Vector((0.0, -0.15, size * 0.42))
    camera.location = target + Vector(direction).normalized() * 6.0
    camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = camera
    return camera


# Renders one image of every clip with the table in the picture.
def render_reviews(arm, table_path, folder, model):
    os.makedirs(folder, exist_ok=True)
    mesh_heights = [obj.dimensions.z for obj in bpy.data.objects if obj.type == 'MESH']
    table = add_table(table_path)
    size = max(1.5, max(mesh_heights) * 1.35)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = False
    scene.render.resolution_x = REVIEW_SIZE
    scene.render.resolution_y = REVIEW_SIZE
    scene.render.image_settings.file_format = 'PNG'
    for view, direction in (('side', (1.0, 0.0, 0.0)), ('corner', (0.8, 0.8, 0.45))):
        camera = add_camera(direction, size)
        for clip in CLIPS:
            action = bpy.data.actions[clip]
            oo.assign_action(arm, action)
            scene.frame_set(int(round(action['ogre_length'] * oo.FPS * REVIEW_MOMENTS[clip])))
            scene.render.filepath = os.path.join(folder, model + '-' + view + '-' + clip + '.png')
            bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(camera)
    bpy.data.objects.remove(table)


# Runs the steps for the Blender source that is open.
def main():
    args = sys.argv[sys.argv.index('--') + 1:]
    seats, table_path, folder = args[0], args[1], args[2]
    model = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
    arm = source_armature()
    add_actions(arm, seats)
    render_reviews(arm, table_path, folder, model)
    if '--save' in args:
        exported = args[args.index('--save') + 1]
        oo.export_skeleton_xml(arm, exported, only_actions=set(CLIPS))
        for action in bpy.data.actions:
            action.use_fake_user = True
        bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath, compress=True)


main()
