"""Decision 863 (4)/(5): natural seated arms and one visibly continuous hot mud bath.

Reads the shipped meshes/skeleton through OgreXMLConverter; no compiler or game.
Checks 49 Sit samples and shoulder skinning, bold props, both joined surface axes,
opaque scrolling gloss, bubble animation wiring and deterministic sprite output.
"""
from pathlib import Path
import math
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CONVERTER = Path(os.environ.get('OGRE_XML_CONVERTER', str(Path.home() / 'build-deps/install/bin/OgreXMLConverter.exe')))


def read(name):
    """Read a game source file."""
    return (ROOT / name).read_text(encoding='utf-8')


def vector(element):
    """Read an XML xyz vector."""
    return np.array([float(element.get(axis, 0)) for axis in 'xyz'])


def rotation(element):
    """Convert an Ogre axis/angle rotation to a 3x3 matrix."""
    axis = vector(element.find('axis'))
    if np.linalg.norm(axis) < 1e-8:
        return np.eye(3)
    x, y, z = axis / np.linalg.norm(axis)
    cross = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    angle = float(element.get('angle'))
    return np.eye(3) + math.sin(angle) * cross + (1 - math.cos(angle)) * (cross @ cross)


def geometry(element):
    """Read all exported vertex attributes from one geometry block."""
    positions, normals, uv = [], [], []
    for buffer in element.findall('vertexbuffer'):
        for vertex in buffer.findall('vertex'):
            if vertex.find('position') is not None:
                positions.append(vector(vertex.find('position')))
            if vertex.find('normal') is not None:
                normals.append(vector(vertex.find('normal')))
            if vertex.find('texcoord') is not None:
                uv.append([float(vertex.find('texcoord').get(axis)) for axis in ('u', 'v')])
    return np.array(positions), np.array(normals), np.array(uv)


def sample_track(keys, seconds):
    """Interpolate optimized Ogre keyframes, which may omit redundant source samples."""
    before = keys[0]
    after = keys[-1]
    for key in keys:
        if float(key.get('time')) <= seconds + 1e-7:
            before = key
        if float(key.get('time')) >= seconds - 1e-7:
            after = key
            break
    start, end = float(before.get('time')), float(after.get('time'))
    factor = 0 if end - start < 1e-7 else (seconds - start) / (end - start)
    quaternions = []
    for key in (before, after):
        rot = key.find('rotate')
        angle = float(rot.get('angle')) / 2
        axis = vector(rot.find('axis'))
        axis /= max(np.linalg.norm(axis), 1e-10)
        quaternions.append(np.append(math.cos(angle), axis * math.sin(angle)))
    a, b = quaternions
    dot = float(np.dot(a, b))
    if dot < 0:
        b = -b
        dot = -dot
    if dot > .9995:
        q = (1 - factor) * a + factor * b
        q /= np.linalg.norm(q)
    else:
        angle = math.acos(min(1, dot))
        q = (math.sin((1 - factor) * angle) * a + math.sin(factor * angle) * b) / math.sin(angle)
    w, x, y, z = q
    matrix = np.array([[1 - 2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                       [2*(x*y+z*w), 1 - 2*(x*x+z*z), 2*(y*z-x*w)],
                       [2*(x*z-y*w), 2*(y*z+x*w), 1 - 2*(x*x+y*y)]])
    translation = (1 - factor) * vector(before.find('translate')) + factor * vector(after.find('translate'))
    scales = [vector(key.find('scale')) if key.find('scale') is not None else np.ones(3) for key in (before, after)]
    return translation, matrix @ np.diag((1 - factor) * scales[0] + factor * scales[1])


def points_for(mesh, material):
    """Read the vertices used by a material, supporting shared and dedicated geometry."""
    points = []
    for sub in mesh.findall('submeshes/submesh'):
        if sub.get('material') != material:
            continue
        geom = mesh.find('sharedgeometry') if sub.get('usesharedvertices') == 'true' else sub.find('geometry')
        vertices = geometry(geom)[0]
        indices = {int(face.get(axis)) for face in sub.findall('faces/face') for axis in ('v1', 'v2', 'v3')}
        points.extend(vertices[sorted(indices)])
    assert points, material + ' has no vertices'
    return np.array(points)


def check_pose(mesh, skeleton):
    """Evaluate Ogre parent transforms and linear skinning at every shipped Sit key."""
    bones = {bone.get('name'): bone for bone in skeleton.findall('bones/bone')}
    # OgreXMLConverter omits sequential ids on export; explicit ids remain valid input too.
    names = {int(bone.get('id', index)): bone.get('name') for index, bone in enumerate(bones.values())}
    parents = {item.get('bone'): item.get('parent') for item in skeleton.findall('bonehierarchy/boneparent')}
    clips = skeleton.findall('animations/animation')
    assert {clip.get('name') for clip in clips} == {'Sit', 'Whistle', 'TowelWave', 'Doze', 'Walk', 'Climb', 'Jump'}
    assert all(abs(float(clip.get('length')) - 2) < 1e-6 for clip in clips)
    sit = next(clip for clip in clips if clip.get('name') == 'Sit')
    tracks = {track.get('bone'): track.findall('keyframes/keyframe') for track in sit.findall('tracks/track')}
    assert len(tracks['Head']) == 49, 'Sit must retain its 49 head motion samples'

    def transforms(index):
        """Build bind transforms or the indexed sampled pose in model coordinates."""
        result = {}

        def world(name):
            """Resolve one bone after its parent."""
            if name in result:
                return result[name]
            bone = bones[name]
            local = np.eye(4)
            local[:3, :3] = rotation(bone.find('rotation'))
            local[:3, 3] = vector(bone.find('position'))
            if index is not None and name in tracks:
                translation, orientation = sample_track(tracks[name], index / 24)
                local[:3, 3] += translation
                local[:3, :3] = local[:3, :3] @ orientation
            result[name] = world(parents[name]) @ local if name in parents else local
            return result[name]

        for name in bones:
            world(name)
        return result

    bind = transforms(None)
    inverse = {name: np.linalg.inv(matrix) for name, matrix in bind.items()}
    vertices = geometry(mesh.find('sharedgeometry'))[0]
    assignments = {}
    for item in mesh.findall('boneassignments/vertexboneassignment'):
        assignments.setdefault(int(item.get('vertexindex')), []).append((names[int(item.get('boneindex'))], float(item.get('weight'))))
    shoulders = [i for i, p in enumerate(vertices) if .16 < abs(p[0]) < .24 and .66 < p[2] < .76]
    assert len(shoulders) > 100, 'the real shoulder skin must be sampled'
    for index in shoulders:
        side = '_R' if vertices[index][0] < 0 else '_L'
        assert all(name in ('Chest', 'UpperArm' + side) for name, weight in assignments[index] if weight > 1e-6), \
            'shoulder skin must not follow a distal or opposite limb'
    shoulder_edges = set()
    for sub in mesh.findall('submeshes/submesh'):
        for face in sub.findall('faces/face'):
            tri = [int(face.get(axis)) for axis in ('v1', 'v2', 'v3')]
            if all(i in shoulders for i in tri):
                shoulder_edges.update(tuple(sorted((tri[i], tri[(i + 1) % 3]))) for i in range(3))
    assert len(shoulder_edges) > 100
    for frame in range(49):
        pose = transforms(frame)
        for suffix, sign in (('_R', -1), ('_L', 1)):
            shoulder = pose['UpperArm' + suffix][:3, 3]
            elbow = pose['Forearm' + suffix][:3, 3]
            wrist = pose['Hand' + suffix][:3, 3]
            assert shoulder[2] - elbow[2] > .13, 'elbow must hang below the shoulder'
            assert elbow[1] - wrist[1] > .10, 'forearm must rest forward'
            assert sign * elbow[0] > .17 and sign * wrist[0] > .15, 'resting arms must stay on their own side'
            assert all(abs(float(key.find('rotate').get('angle'))) < .4 for key in tracks['UpperArm' + suffix]), \
                'shoulder must use a small swing from its neutral pose'
        skinned = {}
        for index in shoulders:
            vertex = np.append(vertices[index], 1)
            skinned[index] = sum(weight * (pose[name] @ inverse[name] @ vertex)[:3] for name, weight in assignments[index])
        for a, b in shoulder_edges:
            rest = np.linalg.norm(vertices[a] - vertices[b])
            if rest > .0001:
                ratio = np.linalg.norm(skinned[a] - skinned[b]) / rest
                assert .45 < ratio < 1.65, 'shoulder skin collapses or stretches: %.3f at key %d' % (ratio, frame)


with tempfile.TemporaryDirectory(prefix='spa-863-') as folder:
    converted = {}
    for name in ('SpaMudPool.mesh', 'SpaChair.mesh', 'PoolAttendant.mesh', 'PoolAttendant.skeleton'):
        path = Path(folder) / (name + '.xml')
        result = subprocess.run([str(CONVERTER), str(ROOT / 'models' / name), str(path)], capture_output=True, text=True, cwd=folder)
        assert result.returncode == 0, result.stdout + result.stderr
        converted[name] = ET.parse(path).getroot()
    check_pose(converted['PoolAttendant.mesh'], converted['PoolAttendant.skeleton'])
    mud = converted['SpaMudPool.mesh']
    positions, normals, uv = geometry(mud.find('sharedgeometry'))
    assert len(positions) == 4 and len(mud.findall('submeshes/submesh/faces/face')) == 2, 'no bevels, walls or static bubble lumps'
    assert np.allclose(positions[:, 2], .25) and np.allclose(normals, [0, 0, 1]), 'flat liquid edges with matching lighting'
    assert np.allclose(positions[:, :2].min(axis=0), [-.5, -.5]) and np.allclose(positions[:, :2].max(axis=0), [.5, .5])
    assert {tuple(p[:2]) for p in positions} == {(-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5)}
    triangles = [tuple(int(face.get(axis)) for axis in ('v1', 'v2', 'v3')) for face in mud.findall('submeshes/submesh/faces/face')]
    assert len({frozenset(triangle) for triangle in triangles}) == 2, 'duplicate liquid triangles'
    area = 0
    for a, b, c in triangles:
        cross = np.cross(positions[b] - positions[a], positions[c] - positions[a])
        assert cross[2] > 0, 'liquid triangle must have positive area and face upward'
        area += cross[2] / 2
    assert abs(area - 1) < 1e-6, 'the liquid triangles must cover one whole tile'
    # Both opposite edges must have the same integer offset at their endpoints, hence also between them.
    # This joins every repeated patch in a multi-tile bath at every scrolling phase.
    for dx, dy in ((1, 0), (0, 1)):
        axis = 0 if dx else 1
        offsets = []
        for index, p in enumerate(positions):
            if abs(p[axis] - .5) > 1e-6:
                continue
            match = next(j for j, q in enumerate(positions) if np.allclose(q + [dx, dy, 0], p))
            assert np.allclose(normals[index], normals[match])
            offsets.append(uv[index] - uv[match])
            for seconds in (0, .5, 3.7, 25):
                a = uv[index] + seconds * np.array([.02, .01])
                b = uv[match] + seconds * np.array([.02, .01])
                assert np.allclose(a - b, np.round(a - b)), 'the scrolling texture tears at an internal border'
        assert len(offsets) == 2 and np.allclose(offsets[0], offsets[1]), 'UV slopes differ along the joined edge'
    chair = converted['SpaChair.mesh']
    ring = np.concatenate([points_for(chair, material) for material in ('SpaLifebuoyRed', 'SpaLifebuoyWhite')])
    assert np.ptp(ring[:, 2]) > .52 and np.ptp(ring[:, 0]) > .11, 'life ring needs a bold silhouette'
    whistle = points_for(converted['PoolAttendant.mesh'], 'SpaWhistle')
    assert np.ptp(whistle[:, 0]) > .05 and np.ptp(whistle[:, 2]) > .095, 'whistle barrel and mouthpiece must read from the camera'
    subprocess.run([sys.executable, str(ROOT / 'tools/spa-textures/generate_spa_bubbles.py'), folder], check=True)
    assert (Path(folder) / 'SpaMudBubble.png').read_bytes() == (ROOT / 'materials/textures/SpaMudBubble.png').read_bytes()

material = read('materials/scripts/Spa.material')
mud_material = material[material.index('material SpaMud '):material.index('material SpaMudBubble')]
assert 'scroll_anim 0.02 0.01' in mud_material and 'tex_address_mode wrap' in mud_material
assert 'specular 0.5 0.42 0.32 1 36' in mud_material
assert 'scene_blend' not in mud_material and 'depth_write off' not in mud_material, 'D6 mud must stay opaque'
particles = read('particles/RoomAmbienceProduction.particle')
bubbles = particles[particles.index('particle_system SpaMudBubbles'):particles.index('// Something was finished')]
for required in ('material        SpaMudBubble', 'billboard_type  perpendicular_common', 'common_direction 0 0 1',
                 'position            0 0 0.256', 'emission_rate       2.5', 'rate    0.16', 'alpha   -1.6'):
    assert required in bubbles, required
assert 'particle_system SpaSteam' in particles and 'position            0 0 0.32' in particles
config = read('config/roomAmbience.cfg')
effect = config[config.index('Name        SpaMudBubbles'):].split('[/Effect]')[0]
assert 'Match       SpaMudPool' in effect and 'System      SpaMudBubbles' in effect and 'Kind        Particle' in effect
assert 'materials/textures/SpaMudBubble.png' in read('CREDITS')
print('check_spa_owner_863 ok: 49 seated shoulder poses, readable props, joined liquid edges and animated bubbles')
