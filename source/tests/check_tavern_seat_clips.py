#!/usr/bin/env python3
"""Seated tavern clips: every skeleton of a creature type that visits the tavern holds the seven clips, each starts and
ends in the seat pose, the body rests on the bench or its feet and the seat pose stays out of the table top.

What is checked (fixed values of this branch, counted once)
  visitors   30 skeletons belong to the types whose Tavern line in creatures.cfg is not "0 0"
  clips      Sit, SitDrink, SitSlap, SitSlapped, SitArmWrestle, SitDice and SitSlumped; a bone without a track stays in its rest pose
  seam       the first and the last frame of a clip show the same pose, so that it loops and returns to the seat pose
  height     the pose of Sit reaches above the seat of the bench
  table      no clip reaches more than 0.04 tiles into the table top at any of 385 samples, also between its keys, seen from
             the middle of the bench, at the smallest and the largest creature scale of the level
  weapons    attached weapon models are hidden during a seated clip (read from the source, not run)
  bench      the pelvis of a walking body stays on the bench in Sit
  large      the types with a 2x2 bed are the large models of the clip author

Calls (from the repository root; needs OgreXMLConverter on the PATH or in OGRE_XML_CONVERTER, no compiler, no game):
  python source/tests/check_tavern_seat_clips.py
"""
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'source' / 'tests'))
import author_tavern_seats as seats
import author_rest_poses as rest
import fix_walk_feet as feet
from check_animation_assets import export

SEAT_CLIPS = ['Sit', 'SitDrink', 'SitSlap', 'SitSlapped', 'SitArmWrestle', 'SitDice', 'SitSlumped']
VISITING_SKELETONS = 30
# A clip may reach this far into the table top (a hand or a tusk on its edge), in tiles
MAX_TABLE_DEPTH = 0.04
# Samples per clip: dense enough that a fast arm does not pass the table top between two of them
TABLE_SAMPLES = 385
# The pelvis stays this close to the middle of the bench (half of the depth of the bench), in tiles
MAX_PELVIS_BEHIND = 0.084
# First and last frame of a clip may differ by this share of the height of the body
MAX_SEAM = 1e-3


# Returns the skeleton names of the creature types with a tavern line other than 0 0, and their mesh names.
def visitors():
    found = {}
    configuration = (ROOT / 'config' / 'creatures.cfg').read_text(encoding='utf-8', errors='replace')
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', configuration, re.S):
        mesh = re.search(r'^\s*MeshName\s+(\S+)', block, re.M)
        tavern = re.search(r'^\s*Tavern\s+(\S+)\s+(\S+)', block, re.M)
        if (mesh is None) or (tavern is None) or (float(tavern.group(1)) <= 0.0 and float(tavern.group(2)) <= 0.0):
            continue
        data = (ROOT / 'models' / mesh.group(1)).read_bytes()
        skeleton = re.findall(rb'([A-Za-z0-9_]+)\.skeleton', data)[0].decode('ascii')
        found.setdefault(skeleton, mesh.group(1))
    return found


# Checks the clips of one skeleton and returns the number of clips checked.
def check_skeleton(name, mesh_name, out):
    export(name + '.skeleton', out)
    export(mesh_name, out)
    skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
    vertices, faces, weights = rest.mesh_data(out / (mesh_name + '.xml'))
    idle = skeleton.locals_at(skeleton.clips['Idle'], np.zeros(1))
    height = float(np.ptp(rest.skin_vertices(skeleton, idle, vertices, weights)[0, :, 2]))
    for clip in SEAT_CLIPS:
        assert clip in skeleton.clips, (name, 'misses', clip)
        played = skeleton.clips[clip]
        assert played.length > 0.0, (name, clip)
        assert played.tracks and set(played.tracks) <= set(skeleton.names), (name, clip, 'needs tracks of its own bones')
        ends = skeleton.locals_at(played, np.array([0.0, played.length]))
        points = rest.skin_vertices(skeleton, ends, vertices, weights)
        seam = float(np.abs(points[0] - points[1]).max() / height)
        assert seam < MAX_SEAM, (name, clip, 'first and last frame differ', seam)
        fine = np.linspace(0.0, played.length, TABLE_SAMPLES)
        points = rest.skin_vertices(skeleton, skeleton.locals_at(played, fine), vertices, weights)
        depth = seats.level_depth(points)
        assert depth <= MAX_TABLE_DEPTH, (name, clip, 'reaches into the table top', depth)
    sit = skeleton.locals_at(skeleton.clips['Sit'], np.zeros(1))
    points = rest.skin_vertices(skeleton, sit, vertices, weights)
    assert float(points[0, :, 2].max()) > seats.BENCH_TOP, (name, 'Sit lies below the seat of the bench')
    body_rig = seats.rig.config(name, seats.rig.Skeleton(str(out / (name + '.skeleton.xml'))))
    if seats.is_humanoid(body_rig):
        chains = seats.thigh_chains(skeleton, seats.leg_chains(skeleton, name, vertices, weights, idle), body_rig)
        world = skeleton.fk(sit)
        for chain in chains:
            pelvis = world[skeleton.idx[chain[0]]][0][0]
            assert pelvis[1] <= MAX_PELVIS_BEHIND, (name, 'the pelvis lies behind the bench', pelvis[1])
    return len(SEAT_CLIPS)


# Checks in the source that the attached weapon models stay hidden while a guest sits.
def check_weapons_hidden():
    combat = (ROOT / 'source' / 'render' / 'CreatureCombatReactions.cpp').read_text(encoding='utf-8')
    assert 'setWeaponsVisible(creature, visible && !playsSeatClip(creature));' in combat, 'a drawn weapon shows on a seated guest'
    assert 'setWeaponsVisible(creature, !sheathed && !playsSeatClip(creature));' in combat, 'getting up restores the wrong state'
    assert combat.index('if(playsSeatClip(creature))') < combat.index('if(carriesWeapon && hasWeaponModel(reactions, creature))\n        {'), \
        'the tick draws or sheathes a seated guest with a standing clip'
    render = (ROOT / 'source' / 'render' / 'RenderManager.cpp').read_text(encoding='utf-8')
    assert 'CreatureCombatReactions::showWeaponsForClip(dropCreature);' in render, 'a change of the clip does not update the weapons'


# Runs the check over all visiting skeletons.
def main():
    check_weapons_hidden()
    found = visitors()
    assert len(found) == VISITING_SKELETONS, len(found)
    assert 'Kobold' not in found and 'skeleton' not in found, 'workers and the Skeleton do not visit the tavern'
    configuration = (ROOT / 'config' / 'creatures.cfg').read_text(encoding='utf-8', errors='replace')
    large = set()
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', configuration, re.S):
        mesh = re.search(r'^\s*MeshName\s+(\S+)', block, re.M)
        bed = re.search(r'^\s*BedDim\s+(\d+)\s+(\d+)', block, re.M)
        if mesh and bed and int(bed.group(1)) >= 2 and int(bed.group(2)) >= 2 and mesh.group(1) in found.values():
            large.add(next(key for key, value in found.items() if value == mesh.group(1)))
    assert large == set(seats.LARGE_MODELS), ('large models', sorted(large))
    out = ROOT / 'out' / 'tavern-seat-clips'
    out.mkdir(parents=True, exist_ok=True)
    tested = 0
    for name, mesh_name in sorted(found.items()):
        tested += check_skeleton(name, mesh_name, out)
    assert tested == 210, tested
    print('tavern seat clips ok:', tested, 'clips on', len(found), 'skeletons')


if __name__ == '__main__':
    main()
