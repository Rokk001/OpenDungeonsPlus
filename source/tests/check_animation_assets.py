#!/usr/bin/env python3
"""Check serialized loop closure and complete skinned chicken wings without compiling the game."""
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/blender-assets'))
import author_chicken_wings as wings
import gen_walk_hurt as rig
import splice_animation_chunks as binary


# Export an actual tracked game asset through the installed serializer with bounded, closed-input execution.
def export(name, out):
    converter = os.environ.get('OGRE_XML_CONVERTER', 'OgreXMLConverter')
    target = out / (name + '.xml')
    subprocess.run([converter, '-q', '-log', str(target) + '.log', str(ROOT / 'models' / name), str(target)],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=60, check=True)
    return ET.parse(target).getroot()


# Compare full key transforms, allowing only quaternion sign and serializer rounding differences.
def matching_keys(first, last):
    for tag, axes, default in (('translate', 'xyz', 0.0), ('scale', 'xyz', 1.0)):
        for axis in axes:
            a = first.find(tag)
            b = last.find(tag)
            av = float(a.get(axis)) if a is not None else default
            bv = float(b.get(axis)) if b is not None else default
            assert abs(av - bv) < 1e-6, (tag, axis, av, bv)
    rotations = []
    for key in (first, last):
        rotation = key.find('rotate')
        axis = rotation.find('axis')
        rotations.append(rig.qaxis(tuple(float(axis.get(c)) for c in 'xyz'), float(rotation.get('angle'))))
    assert abs(rig.qdot(rotations[0], rotations[1])) > 1.0 - 1e-6


# Verify append-only feather geometry, complete wing weights and every exported vertex channel.
def check_wings(mesh, skeleton):
    bones = {bone.get('name'): bone.get('id') for bone in skeleton.find('bones')}
    geometry = mesh.find('sharedgeometry')
    count = int(geometry.get('vertexcount'))
    added = wings.FEATHER_COUNT * 2 * 10
    assert count > added
    for buffer in geometry.findall('vertexbuffer'):
        assert len(buffer) == count
        for vertex in buffer:
            assert len(vertex.findall('texcoord')) == int(buffer.get('texture_coords', '0'))
    assignments = {}
    for assignment in mesh.find('boneassignments'):
        index = int(assignment.get('vertexindex'))
        assignments.setdefault(index, []).append((assignment.get('boneindex'), float(assignment.get('weight'))))
    for offset in range(added):
        expected = bones['Wing_L' if offset < added // 2 else 'Wing_R']
        assert assignments[count - added + offset] == [(expected, 1.0)]
    for submesh in mesh.find('submeshes'):
        faces = submesh.find('faces')
        assert len(faces) == int(faces.get('count'))
        for face in faces:
            assert all(0 <= int(face.get(axis)) < count for axis in ('v1', 'v2', 'v3'))


# Exercise binary preservation and fail-closed selection with complete synthetic serializer chunks.
def check_splice():
    header = struct.pack('<H', binary.HEADER) + b'[Serializer_v1.80]\n'
    clips = []
    for name in (b'Idle\n', b'Walk\n'):
        payload = name + struct.pack('<f', 1.0)
        clips.append(struct.pack('<HI', binary.ANIMATION, len(payload) + 6) + payload)
    original = header + b''.join(clips)
    assert binary.splice(original, original, {'Walk'}) == original
    for authored, selected in ((original, {'Absent'}), (original.replace(b'v1.80', b'v1.10'), {'Walk'})):
        try:
            binary.splice(original, authored, selected)
        except AssertionError:
            continue
        raise AssertionError('Invalid clip selection or serializer version was accepted')


# Check actual serialized assets and the non-destructive animation replacement helper.
def main():
    out = ROOT / 'out/animation-assets'
    out.mkdir(parents=True, exist_ok=True)
    chicken = None
    for name, clips in (('Chicken', ('Walk', 'Run')), ('CaveHornet', ('Walk',)), ('SmallSpider', ('Idle',))):
        skeleton = export(name + '.skeleton', out)
        animations = {clip.get('name'): clip for clip in skeleton.find('animations')}
        for name_clip in clips:
            clip = animations[name_clip]
            for track in clip.find('tracks'):
                keys = list(track.find('keyframes'))
                assert abs(float(keys[-1].get('time')) - float(clip.get('length'))) < 1e-6
                matching_keys(keys[0], keys[-1])
        if name == 'Chicken':
            chicken = skeleton
            for name_clip in wings.FLIGHT_CLIPS:
                clip = animations[name_clip]
                tracks = {track.get('bone'): list(track.find('keyframes')) for track in clip.find('tracks')}
                for bone in ('Wing_L', 'Wing_R'):
                    angles = [float(key.find('rotate').get('angle')) for key in tracks[bone]]
                    if name_clip != 'Tread':
                        assert max(angles) - min(angles) > math.radians(30.0), (name_clip, bone)
    for mesh in ('Chicken.mesh', 'ChickenRooster.mesh'):
        check_wings(export(mesh, out), chicken)
    check_splice()
    print('Serialized loops, complete wing skinning, vertex channels and binary preservation controls passed.')


if __name__ == '__main__':
    main()
