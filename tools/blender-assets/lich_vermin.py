# Builds the three 3D grave vermin that crawl out of a Lich that burst (LichBeetle, LichMaggot, LichWorm) in Blender:
# textured, jointed models at their real size (1 unit = 1 tile) with a looping skeleton clip "Crawl", and exports the
# Ogre XML files. Run inside Blender (background): blender --background --python lich_vermin.py -- <out dir> <blend dir>
# The models look along +y, z is up. All bones have identity rest rotation, so pose rotations use the world axes.
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import odp_ogre_io as oo

OUT = sys.argv[sys.argv.index("--") + 1]
BLEND = sys.argv[sys.argv.index("--") + 2]
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def rot(axis, degrees):
    """Quaternion for a rotation of degrees around the given axis."""
    return Quaternion(axis, math.radians(degrees))


class Model:
    """Collects geometry parts (each rigidly bound to one bone) and the bone list of one vermin model."""

    def __init__(self, name, materials):
        self.name = name
        self.bm = bmesh.new()
        self.materials = materials
        self.bones = []  # (name, parent, world position)
        self.groups = {}  # bone name -> vertex indices (filled after to_mesh via index layer)
        self.owner = self.bm.verts.layers.int.new("bone")
        self.bone_ids = {}

    def bone(self, name, parent, pos):
        """Adds a bone at the world position pos."""
        self.bone_ids[name] = len(self.bones)
        self.bones.append((name, parent, Vector(pos)))

    def _finish(self, geom, bone, material):
        for v in [g for g in geom if isinstance(g, bmesh.types.BMVert)]:
            v[self.owner] = self.bone_ids[bone]
        for f in set(f for v in geom if isinstance(v, bmesh.types.BMVert) for f in v.link_faces):
            f.material_index = material
            f.smooth = True

    def ellipsoid(self, bone, center, size, material=0, segments=14, rings=8):
        """An ellipsoid with the half axes size around center."""
        matrix = Matrix.Translation(center) @ Matrix.Diagonal(Vector((size[0], size[1], size[2], 1.0)))
        result = bmesh.ops.create_uvsphere(self.bm, u_segments=segments, v_segments=rings, radius=1.0, matrix=matrix)
        self._finish(result["verts"], bone, material)

    def tube(self, bone, start, end, r_start, r_end, material=1, sides=6):
        """A tapering tube from start to end."""
        start, end = Vector(start), Vector(end)
        vec = end - start
        matrix = Matrix.Translation((start + end) / 2) @ vec.to_track_quat("Z", "Y").to_matrix().to_4x4()
        result = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=sides, radius1=r_start,
                                       radius2=r_end, depth=vec.length, matrix=matrix)
        self._finish(result["verts"], bone, material)

    def build(self, uv_function, texture_dirs=None):
        """Creates the armature (without clips) and the mesh object with vertex groups and UVs."""
        skeleton_xml = os.path.join(OUT, self.name + ".base.skeleton.xml")
        lines = ['<?xml version="1.0"?>\n<skeleton blendmode="average">\n\t<bones>\n']
        world = {n: p for n, _, p in self.bones}
        parents = {n: par for n, par, _ in self.bones}
        for i, (n, par, p) in enumerate(self.bones):
            local = p - world[par] if par else p
            lines.append('\t\t<bone id="%d" name="%s">\n\t\t\t<position x="%.6f" y="%.6f" z="%.6f" />\n'
                         '\t\t\t<rotation angle="0">\n\t\t\t\t<axis x="1" y="0" z="0" />\n\t\t\t</rotation>\n\t\t</bone>\n'
                         % (i, n, local.x, local.y, local.z))
        lines.append("\t</bones>\n\t<bonehierarchy>\n")
        for n, par in parents.items():
            if par:
                lines.append('\t\t<boneparent bone="%s" parent="%s" />\n' % (n, par))
        lines.append("\t</bonehierarchy>\n\t<animations>\n\t</animations>\n</skeleton>\n")
        with open(skeleton_xml, "w", newline="\n") as handle:
            handle.write("".join(lines))
        self.arm = oo.import_skeleton(skeleton_xml, self.name + "Armature")

        mesh = bpy.data.meshes.new(self.name)
        uv_layer = self.bm.loops.layers.uv.new("UVMap")
        for face in self.bm.faces:
            for loop in face.loops:
                loop[uv_layer].uv = uv_function(loop.vert.co, face.material_index)
        owner_of = [v[self.owner] for v in self.bm.verts]
        self.bm.to_mesh(mesh)
        self.bm.free()
        self.obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(self.obj)
        for n, _, _ in self.bones:
            self.obj.vertex_groups.new(name=n)
        for vi, bi in enumerate(owner_of):
            self.obj.vertex_groups[bi].add([vi], 1.0, "REPLACE")
        for matname in self.materials:
            mat = bpy.data.materials.new(matname)
            self.obj.data.materials.append(mat)
        self.obj.parent = self.arm
        modifier = self.obj.modifiers.new("Armature", "ARMATURE")
        modifier.object = self.arm

    def clip(self, length, keys):
        """Adds the looping clip Crawl; keys(t) returns {bone: (loc or None, quaternion or None)} for time t."""
        act = oo.new_action(self.arm, "Crawl", length)
        steps = 12
        for s in range(steps + 1):
            t = length * s / steps
            pose = keys(t % length if s < steps else 0.0)
            for bone, (loc, quat) in pose.items():
                oo.add_pose_key(self.arm, act, bone, t, loc=loc, rot=quat)
        oo.assign_action(self.arm, act)

    def export(self, skeleton_name):
        """Writes <name>.mesh.xml and <name>.skeleton.xml and saves the .blend source."""
        oo.export_skeleton_xml(self.arm, os.path.join(OUT, self.name + ".skeleton.xml"))
        stats = oo.export_mesh_xml(self.obj, self.arm, os.path.join(OUT, self.name + ".mesh.xml"), skeleton_name)
        print(self.name, stats)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, self.name + ".blend"))


def reset_scene():
    """Empties the scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ---------------------------------------------------------------- beetle (about 0.30 tile long)
def build_beetle():
    reset_scene()
    m = Model("LichBeetle", ["LichVerminShell", "LichVerminLeg"])
    m.bone("Root", None, (0, 0, 0.06))
    m.bone("Body", "Root", (0, 0, 0.06))
    m.bone("Head", "Body", (0, 0.092, 0.058))
    legs = []
    for side, sx in (("L", -1), ("R", 1)):
        for i, y in enumerate((0.055, 0.0, -0.05)):
            hip = (sx * 0.050, y, 0.055)
            name = "Leg%s%d" % (side, i)
            m.bone(name + "_up", "Body", hip)
            m.bone(name + "_low", name + "_up", (sx * 0.095, y + 0.012 * (1 if i < 2 else -1), 0.06))
            legs.append((name, side, sx, i, hip))
    # shell, pronotum, head
    m.ellipsoid("Body", (0, -0.035, 0.066), (0.068, 0.105, 0.052), 0)
    m.ellipsoid("Body", (0, 0.062, 0.066), (0.056, 0.042, 0.040), 0)
    m.ellipsoid("Head", (0, 0.108, 0.056), (0.034, 0.030, 0.026), 0)
    for sx in (-1, 1):
        m.ellipsoid("Head", (sx * 0.022, 0.120, 0.070), (0.010, 0.010, 0.010), 1, 8, 5)  # eyes
        m.tube("Head", (sx * 0.014, 0.132, 0.050), (sx * 0.006, 0.160, 0.046), 0.008, 0.002, 1, 5)  # mandible
        m.tube("Head", (sx * 0.016, 0.130, 0.072), (sx * 0.050, 0.168, 0.090), 0.004, 0.0015, 1, 5)  # antenna
    for name, side, sx, i, hip in legs:
        low = (sx * 0.095, hip[1] + 0.012 * (1 if i < 2 else -1), 0.06)
        foot = (sx * 0.112, low[1] + 0.025 * (1 if i < 2 else -1), 0.0)
        m.tube(name + "_up", hip, low, 0.0065, 0.0050, 1, 5)
        m.tube(name + "_low", low, foot, 0.0050, 0.0020, 1, 5)

    def uv(co, material):
        return (0.5 + co.x / 0.30, 0.5 + (co.y + 0.02) / 0.40)

    m.build(uv)

    def keys(t):
        phase = t / 1.0 * 2 * math.pi
        pose = {
            "Root": (Vector((0, 0, 0.003 * math.sin(phase * 2))), None),
            "Body": (None, rot(Z, 4.0 * math.sin(phase))),
            "Head": (None, rot(Z, -6.0 * math.sin(phase + 0.8))),
        }
        for name, side, sx, i, hip in legs:
            group = 0 if (i % 2 == 0) == (side == "L") else math.pi
            swing = math.sin(phase + group)
            lift = max(0.0, math.cos(phase + group))
            pose[name + "_up"] = (None, rot(Z, sx * 24.0 * swing) @ rot(Y, sx * -28.0 * lift))
            pose[name + "_low"] = (None, rot(Y, sx * -18.0 * lift))
        return pose

    m.clip(1.0, keys)
    m.export("LichBeetle.skeleton")


# ---------------------------------------------------------------- segmented crawlers (maggot and worm)
def build_crawler(name, material, count, length, radius_function, wave_degrees, wave_lag, head_scale):
    reset_scene()
    m = Model(name, [material])
    step = length / count
    ys = [-length / 2 + step * (i + 0.5) for i in range(count)]
    height = lambda r: r * 0.9
    previous = None
    for i, y in enumerate(ys):
        m.bone("Seg%d" % i, previous, (0, y, height(radius_function(i / (count - 1.0)))))
        previous = "Seg%d" % i
    for i, y in enumerate(ys):
        r = radius_function(i / (count - 1.0))
        m.ellipsoid("Seg%d" % i, (0, y, height(r)), (r, step * 0.78, r * 0.92), 0, 12, 7)
    # the head end (+y) is a little darker blob so the front is readable
    r = radius_function(1.0)
    m.ellipsoid("Seg%d" % (count - 1), (0, ys[-1] + step * 0.55, height(r)), (r * head_scale, step * 0.55, r * head_scale * 0.9),
                0, 12, 7)

    def uv(co, material_index):
        angle = math.atan2(co.x, co.z - 0.0) / (2 * math.pi)
        return (0.5 + angle, (co.y + length / 2) / length)

    m.build(uv)

    def keys(t):
        phase = t / 1.2 * 2 * math.pi
        pose = {}
        for i in range(count):
            pose["Seg%d" % i] = (None, rot(Z, wave_degrees * math.sin(phase - i * wave_lag)))
        return pose

    m.clip(1.2, keys)
    m.export(name + ".skeleton")


def maggot_radius(u):
    """Plump in the middle, thin at the head (u = 1)."""
    return 0.012 + 0.026 * math.sin(math.pi * (0.12 + 0.85 * (1.0 - u) ** 0.8)) * (1.0 - 0.35 * u)


def worm_radius(u):
    """Thin and nearly even, thicker behind the head."""
    return 0.0105 + 0.006 * math.sin(math.pi * min(1.0, u * 0.8 + 0.1))


build_beetle()
build_crawler("LichMaggot", "LichVerminMaggot", 7, 0.20, maggot_radius, 16.0, 0.9, 0.7)
build_crawler("LichWorm", "LichVerminWorm", 14, 0.46, worm_radius, 22.0, 0.65, 1.15)
