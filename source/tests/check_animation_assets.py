#!/usr/bin/env python3
"""Check serialized loop closure and complete skinned chicken wings without compiling the game."""
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/blender-assets'))
import author_chicken_wings as wings
import gen_walk_hurt as rig
import splice_animation_chunks as binary
import author_loop_seams as loops
import retime_animation_chunk as retiming


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


# Reject a closed track with a discontinuous tangent, using original binary quaternion precision.
def check_track_velocity(keys, label):
    if len(keys) < 2:
        return
    durations = [keys[1][0] - keys[0][0], keys[-1][0] - keys[-2][0]]
    assert min(durations) > 0.0
    for field in (1, 3):
        start = (keys[1][field] - keys[0][field]) / durations[0]
        end = (keys[-1][field] - keys[-2][field]) / durations[1]
        assert np.linalg.norm(start - end) <= 0.005 * max(0.01, np.linalg.norm(start)), (label, field)
    start = loops.rotation_velocity(keys[0][2], keys[1][2], durations[0])
    end = loops.rotation_velocity(keys[-2][2], keys[-1][2], durations[1])
    assert np.linalg.norm(start - end) <= 0.005 * max(0.01, np.linalg.norm(start)), (label, 'angular velocity', start, end)


# Read selected native track keys because XML angle export rounds tiny quaternion rotations to zero.
def check_loop_velocity(path, selected, selected_bones=None):
    header, chunks = binary.chunks(path.read_bytes())
    checked = set()
    for kind, name, data in chunks:
        if kind != binary.ANIMATION or name not in selected:
            continue
        checked.add(name)
        position = data.index(b'\n', 6) + 5
        length = struct.unpack_from('<f', data, position - 4)[0]
        while position < len(data):
            track_kind, track_size = struct.unpack_from('<HI', data, position)
            end = position + track_size
            assert position + 6 <= end <= len(data)
            if track_kind == 0x4100:
                bone = struct.unpack_from('<H', data, position + 6)[0]
                if selected_bones is not None and bone not in selected_bones:
                    position = end
                    continue
                key_position = position + 8
                keys = []
                while key_position < end:
                    key_kind, key_size = struct.unpack_from('<HI', data, key_position)
                    assert key_kind == 0x4110 and key_size in (38, 50)
                    assert key_position + key_size <= end
                    values = struct.unpack_from('<8f', data, key_position + 6)
                    time, x, y, z, w, tx, ty, tz = values
                    scale = struct.unpack_from('<3f', data, key_position + 38) if key_size == 50 else (1.0, 1.0, 1.0)
                    keys.append((time, np.array([tx, ty, tz]), np.array([w, x, y, z]), np.array(scale)))
                    key_position += key_size
                if keys[-1][0] < length - 1e-6:
                    keys.append((length, keys[-1][1], keys[-1][2], keys[-1][3]))
                check_track_velocity(keys, (path.name, name, bone))
            position = end
    assert checked == set(selected)
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


# Ensure that matching endpoint poses cannot hide a reversed linear or angular tangent.
def check_velocity_controls():
    times = (0.0, 0.25, 0.75, 1.0)
    for angular in (False, True):
        keys = []
        for time, amount in zip(times, (0.0, 0.25, 0.25, 0.0)):
            translation = np.array([0.0 if angular else amount, 0.0, 0.0])
            rotation = np.array(rig.qaxis((1.0, 0.0, 0.0), amount if angular else 0.0))
            keys.append((time, translation, rotation, np.ones(3)))
        try:
            check_track_velocity(keys, 'negative control')
        except AssertionError:
            continue
        raise AssertionError('A closed pose with a velocity reversal was accepted')


# Check that a socket-only replacement preserves sibling tracks and rejects missing handles.
def check_track_splice():
    header = struct.pack('<H', binary.HEADER) + b'[Serializer_v1.80]\n'
    prefix = b'Idle\n' + struct.pack('<f', 1.0)
    first = struct.pack('<HIH', 0x4100, 10, 1) + b'AA'
    second = struct.pack('<HIH', 0x4100, 10, 2) + b'BB'
    original_clip = struct.pack('<HI', binary.ANIMATION, 6 + len(prefix + first + second)) + prefix + first + second
    authored_clip = original_clip.replace(b'AA', b'CC').replace(b'BB', b'DD')
    original = header + original_clip
    authored = header + authored_clip
    assert binary.splice_tracks(original, original, 'Idle', {1}) == original
    assert binary.splice_tracks(original, authored, 'Idle', {1}) == original.replace(b'AA', b'CC')
    try:
        binary.splice_tracks(original, authored, 'Idle', {3})
    except AssertionError:
        pass
    else:
        raise AssertionError('A missing selected bone track was accepted')


# Reject a held trailing pose that snaps on wrap and avoid duplicate serialized sample times.
def check_held_loop():
    times = np.array([0.0, 0.2, 0.8])
    translation = np.array([[0.0, 0.0, 0.0], [0.1, 0.0, 0.0], [0.2, 0.0, 0.0]])
    rotations = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (3, 1))
    scale = np.ones((3, 3))
    track = loops.feet.Track(times, translation, rotations, scale, True)
    assert loops.discontinuous(track, 1.0), 'A held final pose still snaps when the clip wraps'
    times, translation, rotations, scale = loops.close_smooth_track(track, 1.0)
    assert np.all(np.diff([float(loops.feet.fmt(time)) for time in times]) > 0.0)
    assert np.array_equal(translation[0], translation[-1])
    keys = [(time, translation[index], rotations[index], scale[index]) for index, time in enumerate(times)]
    check_track_velocity(keys, 'held trailing interval')


# Verify retiming preserves all transforms, unrelated chunks and identity, and rejects missing clips.
def check_retiming():
    data = (ROOT / 'models/Chicken.skeleton').read_bytes()
    assert retiming.retime(data, 'Lay', 7.0) == data
    changed = retiming.retime(data, 'Lay', 14.0)
    original_header, original = binary.chunks(data)
    new_header, altered = binary.chunks(changed)
    assert original_header == new_header and len(original) == len(altered)
    for before, after in zip(original, altered):
        assert before[:2] == after[:2]
        if before[1] != 'Lay':
            assert before == after
            continue
        first = bytearray(before[2])
        second = bytearray(after[2])
        offset = first.index(b'\n', 6) + 1
        assert struct.unpack_from('<f', second, offset)[0] == 14.0
        second[offset:offset + 4] = first[offset:offset + 4]
        offset += 4
        while offset < len(first):
            kind, size = struct.unpack_from('<HI', first, offset)
            if kind == 0x4100:
                key = offset + 8
                while key < offset + size:
                    key_size = struct.unpack_from('<I', first, key + 2)[0]
                    old_time = struct.unpack_from('<f', first, key + 6)[0]
                    new_time = struct.unpack_from('<f', second, key + 6)[0]
                    assert new_time == 2.0 * old_time
                    second[key + 6:key + 10] = first[key + 6:key + 10]
                    key += key_size
            offset += size
        assert first == second
    try:
        retiming.retime(data, 'Absent', 7.0)
    except AssertionError:
        pass
    else:
        raise AssertionError('A missing retiming clip was accepted')


# Check actual serialized assets and the non-destructive animation replacement helper.
def main():
    out = ROOT / 'out/animation-assets'
    out.mkdir(parents=True, exist_ok=True)
    chicken = None
    for name, clips in (('Chicken', ('Walk', 'Run', 'Idle')), ('CaveHornet', ('Walk', 'Idle')),
                        ('SmallSpider', ('Idle',)), ('Defender', ('Idle', 'Flee')), ('Spider', ('Flee',)),
                        ('Rat', ('Flee',)), ('Troll', ('Run',)), ('Goblin', ('Flee',)),
                        ('DarkElf', ('Idle', 'Flee')), ('Elf', ('Idle', 'Flee'))):
        skeleton = export(name + '.skeleton', out)
        animations = {clip.get('name'): clip for clip in skeleton.find('animations')}
        for name_clip in clips:
            clip = animations[name_clip]
            for track in clip.find('tracks'):
                keys = list(track.find('keyframes'))
                assert float(keys[-1].get('time')) <= float(clip.get('length')) + 1e-6
                matching_keys(keys[0], keys[-1])
        check_loop_velocity(ROOT / 'models' / (name + '.skeleton'), clips)
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
    wizard = export('Wizard.skeleton', out)
    socket = next(track for clip in wizard.find('animations') if clip.get('name') == 'Idle'
                  for track in clip.find('tracks') if track.get('bone') == 'Weapon_L')
    matching_keys(list(socket.find('keyframes'))[0], list(socket.find('keyframes'))[-1])
    bone = next(int(bone.get('id')) for bone in wizard.find('bones') if bone.get('name') == 'Weapon_L')
    check_loop_velocity(ROOT / 'models/Wizard.skeleton', ('Idle',), {bone})
    check_splice()
    check_track_splice()
    check_held_loop()
    check_retiming()
    check_velocity_controls()
    print('Serialized loop poses and velocities, wing skinning, vertex channels and preservation controls passed.')


if __name__ == '__main__':
    main()
