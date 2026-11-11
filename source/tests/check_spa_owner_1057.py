"""Decisions 1057-1060 and 1070: the pool attendant is massive, hairy and pot-bellied and every act is readable.

Reads the shipped models/PoolAttendant.mesh and .skeleton through OgreXMLConverter and the attendant code; no compiler, no
game. Checks (1) the look after variant 1 of D-7-v2.png: heavy belly, wide shoulders, thick legs, body hair, very little
blood, towel, whistle, hair and moustache kept; (2) the Sit pose: knees bent and apart (no stiff legs), arms beside the
belly (no intersection), body not twisted; (3) the clips: Whistle brings the whistle to the mouth, TowelWave holds the
towel in the hand above the shoulder and waves it, Doze lets him sink sideways, Climb, Walk and Jump move; (4) the code:
the acts, the whistle only with a bather and at the moment of the blow, the cannonball and its place.
"""
from pathlib import Path
import math
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
helper_source = (ROOT / 'source/tests/check_spa_owner_863.py').read_text(encoding='utf-8')
helpers = {'__file__': str(ROOT / 'source/tests/check_spa_owner_863.py')}
exec(compile(helper_source[:helper_source.index('def check_pose')], 'check_spa_owner_863_helpers', 'exec'), helpers)
CONVERTER = helpers['CONVERTER']
vector, rotation, geometry, sample_track, points_for = (helpers[name] for name in
                                                        ('vector', 'rotation', 'geometry', 'sample_track', 'points_for'))


def read(name):
    return (ROOT / name).read_text(encoding='utf-8')


with tempfile.TemporaryDirectory(prefix='spa-1057-') as folder:
    converted = {}
    for name in ('PoolAttendant.mesh', 'PoolAttendant.skeleton'):
        path = Path(folder) / (name + '.xml')
        result = subprocess.run([str(CONVERTER), str(ROOT / 'models' / name), str(path)], capture_output=True, text=True, cwd=folder)
        assert result.returncode == 0, result.stdout + result.stderr
        converted[name] = ET.parse(path).getroot()
mesh, skeleton = converted['PoolAttendant.mesh'], converted['PoolAttendant.skeleton']

# ---- 1. The look -----------------------------------------------------------------------------------------------------
sub_by_material = {}
for sub in mesh.findall('submeshes/submesh'):
    sub_by_material.setdefault(sub.get('material'), []).append(sub)
for material in ('SpaSkin', 'SpaSuit', 'SpaHair', 'SpaBodyHair', 'SpaBlood', 'SpaLinen', 'SpaWhistle', 'SpaEyes', 'SpaIron'):
    assert material in sub_by_material, 'the attendant needs the material ' + material
faces = {m: sum(len(s.findall('faces/face')) for s in subs) for m, subs in sub_by_material.items()}
assert faces['SpaBodyHair'] >= 3000, 'hairy: the chest, the arms and the legs carry thousands of hair tufts'
assert 10 <= faces['SpaBlood'] <= 150, 'very little blood, sparingly visible (a few small marks)'
assert faces['SpaLinen'] >= 300 and faces['SpaHair'] >= 1000, 'towel, grey hair and moustache stay'

suit = points_for(mesh, 'SpaSuit')
skin = points_for(mesh, 'SpaSkin')
everything = np.concatenate([suit, skin])
belly = suit[(suit[:, 2] > .42) & (suit[:, 2] < .6)]
assert np.ptp(belly[:, 0]) > .40, 'massive: the belly is wider than 0.40 (was 0.31)'
assert belly[:, 1].min() < -.27, 'pot-bellied: the belly reaches 0.27 in front of the spine (was 0.19)'
assert np.ptp(everything[:, 0]) > .68, 'broad shoulders and arms'
shoulders = skin[(skin[:, 2] > .66) & (skin[:, 2] < .78)]
assert np.ptp(shoulders[:, 0]) > .5, 'heavy shoulders'
thighs = skin[(skin[:, 2] > .3) & (skin[:, 2] < .4) & (skin[:, 0] < -.02)]
assert np.ptp(thighs[:, 0]) > .18, 'thick thighs'
whistle = points_for(mesh, 'SpaWhistle')
assert np.ptp(whistle[:, 0]) > .05 and np.ptp(whistle[:, 2]) > .095, 'whistle must read from the camera'

# ---- 2/3. The skeleton and its clips ---------------------------------------------------------------------------------
bones = {bone.get('name'): bone for bone in skeleton.findall('bones/bone')}
parents = {item.get('bone'): item.get('parent') for item in skeleton.findall('bonehierarchy/boneparent')}
clips = {clip.get('name'): clip for clip in skeleton.findall('animations/animation')}
assert set(clips) == {'Sit', 'Whistle', 'TowelWave', 'Doze', 'Walk', 'Climb', 'Jump'}
assert all(abs(float(clip.get('length')) - 2) < 1e-6 for clip in clips.values())
tracks = {name: {track.get('bone'): track.findall('keyframes/keyframe') for track in clip.findall('tracks/track')}
          for name, clip in clips.items()}


def pose(clip, seconds):
    """World matrices of all bones in a clip at a time."""
    result = {}

    def world(name):
        if name in result:
            return result[name]
        bone = bones[name]
        local = np.eye(4)
        local[:3, :3] = rotation(bone.find('rotation'))
        local[:3, 3] = vector(bone.find('position'))
        if name in tracks[clip]:
            translation, orientation = sample_track(tracks[clip][name], seconds)
            local[:3, 3] += translation
            local[:3, :3] = local[:3, :3] @ orientation
        result[name] = world(parents[name]) @ local if name in parents else local
        return result[name]
    for name in bones:
        world(name)
    return {name: matrix[:3, 3] for name, matrix in result.items()}, result


def angle_between(a, b):
    return math.acos(max(-1, min(1, float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))))))


for seconds in (0, .5, 1.0, 1.5):
    sit, matrices = pose('Sit', seconds)
    for suffix, sign in (('_R', -1), ('_L', 1)):
        thigh, shin, foot = sit['Thigh' + suffix], sit['Shin' + suffix], sit['Foot' + suffix]
        bend = angle_between(shin - thigh, foot - shin)
        assert bend > .45, 'sitting legs are not stiff: the knee bends (%.2f rad)' % bend
        assert sign * shin[0] > .14, 'the knees are apart'
        elbow, wrist = sit['Forearm' + suffix], sit['Hand' + suffix]
        # the arm hangs beside the belly: its inner edge (elbow 0.058 thick) stays outside the belly of the suit
        assert sign * elbow[0] - .058 > np.percentile(np.abs(belly[:, 0]), 98) - .002, 'the elbow is beside the belly, not in it'
        assert sign * wrist[0] - .04 > .22, 'the hand rests beside the belly, not in it'
    assert abs(sit['Thigh_R'][0] + sit['Thigh_L'][0]) < .02 and abs(sit['Thigh_R'][1] - sit['Thigh_L'][1]) < .02, 'hips not twisted'
    assert abs(sit['UpperArm_R'][2] - sit['UpperArm_L'][2]) < .03 and abs(sit['UpperArm_R'][1] - sit['UpperArm_L'][1]) < .03, \
        'shoulders not twisted against the hips'

sit0, _ = pose('Sit', 0)
for seconds in (.9, 1.05):
    whistle, whistle_matrices = pose('Whistle', seconds)
    head = whistle['Head']
    mouth_distance = np.linalg.norm(whistle['WhistleHang'] - (head + np.array([0, -.13, .05])))
    assert mouth_distance < .12, 'Whistle: the whistle is at the mouth (%.3f)' % mouth_distance
    assert np.linalg.norm(whistle['Hand_R'] - whistle['WhistleHang']) < .14, 'Whistle: the whistle is in the hand'
assert np.linalg.norm(sit0['WhistleHang'] - (sit0['Head'] + np.array([0, -.13, .05]))) > .2, 'the whistle hangs on his chest at rest'

towel0, _ = pose('TowelWave', .75)
towel1, _ = pose('TowelWave', .95)
towel2, _ = pose('TowelWave', 1.15)
for towel in (towel0, towel1, towel2):
    assert np.linalg.norm(towel['Towel'] - towel['Hand_R']) < .2, 'TowelWave: the towel is in his hand'
    assert towel['Towel'][2] > towel['UpperArm_R'][2] + .1, 'TowelWave: the towel is above his shoulder'
assert np.linalg.norm(towel0['Towel'] - towel1['Towel']) > .08 and np.linalg.norm(towel1['Towel'] - towel2['Towel']) > .08, \
    'TowelWave: the towel is visibly waved'
assert np.linalg.norm(towel0['TowelTip'] - towel1['TowelTip']) > .1, 'TowelWave: the end of the towel flaps'
assert np.linalg.norm(sit0['Towel'] - sit0['Hand_R']) > .25, 'the towel lies on the shoulder at rest, not in the hand'

doze, _ = pose('Doze', 1.3)
assert sit0['Head'][2] - doze['Head'][2] > .02 and abs(doze['Head'][0] - sit0['Head'][0]) > .04, 'Doze: he sinks and slides sideways'
assert doze['Head'][1] < sit0['Head'][1] - .04, 'Doze: he slumps forward'

climb0, _ = pose('Climb', 0)
climb1, _ = pose('Climb', .5)
assert abs(climb0['Hand_R'][2] - climb1['Hand_R'][2]) > .05 or abs(climb0['Hand_L'][2] - climb1['Hand_L'][2]) > .05, 'Climb moves the hands'
walk0, _ = pose('Walk', 0)
walk1, _ = pose('Walk', .08)
assert abs(walk0['Foot_R'][1] - walk1['Foot_R'][1]) > .02 or abs(walk0['Foot_R'][2] - walk1['Foot_R'][2]) > .02, 'Walk moves the feet'
jump0, _ = pose('Jump', 0)
jump1, _ = pose('Jump', 1.0)
assert np.linalg.norm(jump0['Foot_R'] - jump1['Foot_R']) > .15, 'Jump tucks the legs (cannonball)'
assert jump1['Foot_R'][1] < jump1['Pelvis'][1] - .02 or jump1['Foot_R'][2] > jump1['Pelvis'][2] - .35, 'Jump: knees pulled up'

# ---- 4. The code ------------------------------------------------------------------------------------------------------
cpp = read('source/entities/PoolAttendantEntity.cpp')
assert 'const bool canWhistle = mRoom->hasBatherInPool();' in cpp and 'NB_ACTS_WITH_BATHER' in cpp, 'whistle only with a bather'
assert 'WHISTLE_BLOW_SECONDS' in cpp and cpp.count('SOUND_WHISTLE') == 2, 'the whistle sounds when the hand blows, once per act'
assert cpp.index('mWhistleSounded = true;') < cpp.index('RoomSpa::playSoundAt(mChairTile, SOUND_WHISTLE);'), 'sound after the flag'
assert 'getConfigTurns("SpaAttendantActMinSeconds")' in cpp and 'getConfigTurns("SpaAttendantActMaxSeconds")' in cpp
assert 'getConfigTurns("SpaAttendantCannonballMinSeconds")' in cpp and 'findAttendantPlace' in cpp and 'startJump' in cpp
for clip in ('towelWave', 'doze', 'whistle', 'sit', 'climb'):
    assert 'PoolAttendantPose::' + clip in cpp, clip
rooms = read('config/rooms.cfg')
for key, value in (('SpaAttendantActMinSeconds', '10'), ('SpaAttendantActMaxSeconds', '20'),
                   ('SpaAttendantCannonballMinSeconds', '120'), ('SpaAttendantCannonballMaxSeconds', '180')):
    assert re.search(r'^\s+' + key + r'\s+' + value + r'\s*$', rooms, re.M), key
materials = read('materials/scripts/Spa.material')
for material in ('SpaBodyHair', 'SpaBlood'):
    assert re.search(r'^material ' + material + r' ', materials, re.M), material
credits = read('CREDITS')
assert 'models/PoolAttendant.mesh' in credits and 'decision 1070' in credits

print('check_spa_owner_1057 ok: massive hairy pot-bellied attendant, bent legs, arms beside the belly, readable acts')
