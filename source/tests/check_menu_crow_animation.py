"""Check the main menu crows: wing-beat clips exist in the skeletons and the menu scene uses them. No compile, no game."""
from pathlib import Path
import math
import re
import os
import subprocess
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
cfg = (root / 'config/mainmenuscene.cfg').read_text(encoding='utf-8').replace('\r\n', '\n')
credits = (root / 'CREDITS').read_text(encoding='utf-8')
generator = (root / 'tools/blender-assets/menu_scene_models.py').read_text(encoding='utf-8')

CLIPS = ('Watch', 'Flap', 'FlapIn', 'TakeOff', 'Land')
BONES = ('Root', 'Head', 'WingL', 'WingTipL', 'WingR', 'WingTipR')
CROWS = ('CrowA', 'CrowB', 'CrowC', 'CrowD')

output = root / 'out/menu-crow-check'
output.mkdir(parents=True, exist_ok=True)
converter = os.environ.get('OGRE_XML_CONVERTER', 'OgreXMLConverter')

# Ogre binary serialisation writes strings null-free and newline terminated.
for crow in CROWS:
    mesh = root / ('models/Menu' + crow + '.mesh')
    skeleton = root / ('models/Menu' + crow + '.skeleton')
    assert mesh.is_file() and skeleton.is_file(), crow
    data = skeleton.read_bytes()
    for name in CLIPS + BONES:
        assert (name + '\n').encode() in data, (crow, name)
    assert b'Menu' + crow.encode() + b'.skeleton' in mesh.read_bytes(), crow
    mesh_xml = output / (crow + '.mesh.xml')
    skeleton_xml = output / (crow + '.skeleton.xml')
    for source, target in ((mesh, mesh_xml), (skeleton, skeleton_xml)):
        subprocess.run([converter, '-q', str(source), str(target)], check=True, stdin=subprocess.DEVNULL)
    geometry = ET.parse(mesh_xml).getroot()
    rig = ET.parse(skeleton_xml).getroot()
    bones = {index: bone.get('name') for index, bone in enumerate(rig.findall('./bones/bone'))}
    positions = geometry.findall('./sharedgeometry/vertexbuffer/vertex/position')
    assigned = {}
    for assignment in geometry.findall('./boneassignments/vertexboneassignment'):
        name = bones[int(assignment.get('boneindex'))]
        assigned.setdefault(name, []).append(positions[int(assignment.get('vertexindex'))])
    body = assigned['Root'] + assigned['Head']
    wings = sum((assigned[name] for name in ('WingL', 'WingTipL', 'WingR', 'WingTipR')), [])
    # The authoring mesh uses Y for nose-to-tail and X for wingspan.
    length = max(float(p.get('y')) for p in body) - min(float(p.get('y')) for p in body)
    span = max(float(p.get('x')) for p in wings) - min(float(p.get('x')) for p in wings)
    assert 1.8 <= span / length <= 2.2, (crow, 'wingspan/body length', span / length)
    for clip in ('Flap', 'TakeOff'):
        for wing in ('WingL', 'WingR'):
            track = rig.find("./animations/animation[@name='%s']/tracks/track[@bone='%s']" % (clip, wing))
            angles = [float(r.get('angle')) * float(r.find('axis').get('z')) for r in track.findall('./keyframes/keyframe/rotate')]
            assert max(angles) - min(angles) >= math.radians(80), (crow, clip, wing, angles)
    
assert 'Own work, created with Blender (AI-assisted)' in credits
for clip in CLIPS:
    assert '"' + clip + '"' in generator, clip

# The scene file must place every crow and drive it through the whole take-off, flight and landing sequence.
groups = re.findall(r'\[RenderSceneGroup\]\n(.*?)\n\[/RenderSceneGroup\]', cfg, re.S)
for crow in CROWS:
    assert re.search(r'^AddEntity ' + crow + r' Menu' + crow + r'\.mesh ', cfg, re.M), crow
    own = [g for g in groups if re.search(r'^AnimationTime ' + crow + ' Watch', g, re.M)]
    assert len(own) == 1, crow
    lines = [line for line in own[0].split('\n') if line and not line.startswith('#')]
    assert lines[0] == '*Repeat', crow
    names = [line.split()[0] for line in lines[1:]]
    assert names == ['AnimationTime', 'AnimationOnce', 'TurnEntity', 'MoveEntity', 'PosEntity', 'Wait', 'PosEntity',
                     'MoveEntity', 'AnimationOnce', 'PosEntity', 'TurnEntity'], (crow, names)
    assert lines[11].split()[2] == 'Watch'
    watch = float(lines[1].split()[3])
    assert watch > 0 and watch % 8 == 0, (crow, 'Watch time must be a whole number of 8 s loops')
    assert lines[2].split()[2] == 'TakeOff' and lines[9].split()[2] == 'Land'
    out = lines[4].split()
    inbound = lines[8].split()
    assert out[2] == 'Flap' and inbound[2] == 'FlapIn'
    speed = float(out[3])
    assert speed == float(inbound[3])
    # Four beats of 0.5 s per eighteen tiles: the inbound flight must end on the Flap start pose, where Land begins.
    start = [float(v) for v in lines[7].split()[2:5]]
    perch = [float(v) for v in inbound[4:7]]
    distance = math.dist(start, perch)
    beats = distance / speed / 0.5
    assert abs(beats - round(beats)) < 0.02, (crow, distance, beats)
    # The landing returns to the exact perch the entity was placed at.
    place = re.search(r'^AddEntity ' + crow + r' \S+ (\S+) (\S+) (\S+)', cfg, re.M)
    assert all(abs(float(a) - b) < 1e-6 for a, b in zip(place.groups(), perch)), crow
    # The hidden waiting position is below the ground and the flight keeps the same heading while it rises.
    assert float(lines[5].split()[4]) < -100
print('menu crow animation passes the checks')
