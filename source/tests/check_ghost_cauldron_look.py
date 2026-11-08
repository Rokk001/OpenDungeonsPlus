"""Cauldron look check (decision 845 item 4): the ghost cauldron must not look like a wine press.

The generator (assets-src/rooms/ghostroom/create_models.py, cauldron()) builds no press parts any more (no uprights,
crossbar, threaded spindle, screw threads or press wheel) but an open bellied pot with a rolled rim, a glowing
ectoplasm surface, ring handles, clawed feet over a fire grate with coals and embers, the inspection window and the
brass trap socket over the mouth (the delivery point of decision 845 item 5). Owner decision 894 rebuilt the pot: the
centre funnel and its arms are gone, an open trap seat sits on the rim at the corner and the mesh has the rig
models/GhostCauldron.skeleton (the later parts of the exported mesh are checked in check_ghost_assets.py). The exported
models/GhostCauldron.mesh uses exactly these six materials and keeps its two-tile footprint (2.0 x 2.0 x 1.14, read from
the mesh bounds chunk; the old 1.6 high mesh had the funnel);
the client fill sits behind the new glass; the CREDITS line names the rework. Fixed values measured once on the
export of this branch.
"""
from pathlib import Path
import re
import struct

repo = Path(__file__).resolve().parents[2]
import sys
# ODP_ASSETS_SRC (else <repo>/assets-src) holds the asset sources, see scripts/assets_src.py
sys.path.insert(0, str(repo / 'scripts'))
from assets_src import assets_src_dir  # noqa: E402

generator = (assets_src_dir(repo) / 'rooms/ghostroom/create_models.py').read_text(encoding='utf-8')
start = generator.index('def cauldron():')
body = generator[start:generator.index('\ndef ', start + 1)]
for removed in ('Press upright', 'press crossbar', 'press spindle', 'Screw thread', 'Press wheel', 'guide shoe'):
    assert removed not in body, ('press part still built', removed)
for part in ('Bellied cauldron body', 'Ectoplasm surface', 'Rolled rim', 'Ring handle', 'Fire grate', "'Coal'", "'Ember'",
             'Green inspection glass', 'Claw leg'):
    assert part in body, ('cauldron part missing', part)
assert "'GhostCauldron'}" in generator.split('OUTSIDE_GIT = ')[1].split('\n')[0], 'reworked source kept outside Git'

mesh = (repo / 'models/GhostCauldron.mesh').read_bytes()
materials = sorted(set(m.decode() for m in re.findall(rb'(Ghost[A-Za-z]+)\n', mesh)))
assert materials == ['GhostBrass', 'GhostCoal', 'GhostEctoplasm', 'GhostEmbers', 'GhostIron', 'GhostWindow'], materials
bounds = None
position = 0
while True:
    position = mesh.find(struct.pack('<H', 0x9000), position)
    if position < 0:
        break
    if struct.unpack('<I', mesh[position + 2:position + 6])[0] == 34:
        bounds = struct.unpack('<7f', mesh[position + 6:position + 34])
    position += 1
assert bounds is not None
assert [round(v, 2) for v in bounds[:6]] == [-1.0, -1.0, 0.0, 1.0, 1.0, 1.14], bounds
assert b'GhostCauldron.skeleton' in mesh, 'the cauldron has the rig of the trap seat'

material_script = (repo / 'materials/scripts/Ghost.material').read_text(encoding='utf-8')
for name in materials:
    assert re.search(r'^material ' + name + r'\s*$', material_script, re.M), name

building = (repo / 'source/entities/BuildingObject.cpp').read_text(encoding='utf-8')
assert 'createChildSceneNode(getName()+"_GhostFillNode",Ogre::Vector3(0.0f,0.74f,0.40f));' in building

credits = (repo / 'CREDITS').read_text(encoding='utf-8')
assert re.search(r'^models/GhostCauldron\.mesh\s+AI-generated with Claude Code\s+GPLv3\+\s+Ghost cauldron reworked so it no '
                 r'longer reads as a press \(owner decision 845\)', credits, re.M)
print('ghost cauldron look: ok')
