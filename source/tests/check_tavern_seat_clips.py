#!/usr/bin/env python3
"""Seated tavern clips: every skeleton of a creature type that visits the tavern holds the seven clips at full size, each
starts and ends in the seat pose, the body rests on the bench or its feet and stays out of the furniture.

What is checked (fixed values of this branch, counted once)
  visitors   30 skeletons belong to the types whose Tavern line in creatures.cfg is not "0 0"
  clips      Sit, SitDrink, SitSlap, SitSlapped, SitArmWrestle, SitDice and SitSlumped; a bone without a track stays in its rest pose
  seam       the first and the last frame of a clip show the same pose, so that it loops and returns to the seat pose
  height     the pose of Sit reaches above the seat of the bench
  full size  every root of a skeleton keeps the scale it has in Idle in a seated clip
  furniture  no clip reaches more than 0.04 tiles into the table top, the pedestal, the bench or its legs at any of 385 samples,
             also between its keys, on every seat the guest can take, at the smallest and the largest creature scale of the
             level; the bench counts below the 0.015 tiles a body presses into it; the mug counts in SitDrink
  resting    the bodies that do not sit on legs lie on the bench: the lowest part above the seat rests on it
  mug        every skeleton has the mount Weapon_R for the mug except the listed ones; SitDrink is the calm sip of 5 s of
             tools/author_tavern_drink.py (decision 901; the rim at the mouth is checked by check_tavern_drink_834.py); a
             guest of a stool is measured in SitDrink against the furniture as it sits at the end of the table
  weapons    attached weapon models are hidden during a seated clip (read from the source, not run)
  bench      the pelvis of a walking body stays on the bench in Sit, except for the listed large bodies, whose limit is their own
  floor      the feet of a sitting body stand on the floor in Sit
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
import author_tavern_drink as drink
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
# How far the pelvis joint of one leg can lie behind the middle of the pelvis when the body turns on the bench
MAX_BACK_SIDE = 0.06
# A root may differ from its scale in Idle by this share: the breath of a spine that is a root, 0.008, passes; the smallest
# shrinking of a body that was ever used, 0.04, does not
MAX_ROOT_SCALE = 0.01
# The lowest part above the seat of a resting body lies this close to the seat, in tiles
MAX_REST_GAP = 0.03
# Mesh below the floor in Sit, in tiles: the foot of a rig stands in the floor by this little in its own rest pose
MIN_FLOOR = -0.1
# First and last frame of a clip may differ by this share of the height of the body
MAX_SEAM = 1e-3


# Returns the meshes of the guests of a stool (TAVERN_STOOL_BODIES of RoomTavern.cpp).
def stool_meshes():
    room = (ROOT / 'source' / 'rooms' / 'RoomTavern.cpp').read_text(encoding='utf-8')
    return set(re.findall(r'\{ "([^"]+)", [0-9]+, ', room.split('TAVERN_STOOL_BODIES[] =')[1].split('};')[0]))


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
    export(seats.MUG_MESH, out)
    seats.SCENE['whole_bench'] = name in seats.LARGE_MODELS
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
        locals_fine = skeleton.locals_at(played, fine)
        for index in skeleton.topo:
            if skeleton.parent[index] < 0:
                assert np.abs(locals_fine[index][2] / idle[index][2][0] - 1.0).max() < MAX_ROOT_SCALE, (name, clip, 'a root is scaled', skeleton.names[index])
        clip_vertices, clip_weights = (seats.with_mug(skeleton, vertices, weights, out / (mesh_name + '.xml')) if clip == 'SitDrink' else (vertices, weights))
        points = rest.skin_vertices(skeleton, locals_fine, clip_vertices, clip_weights)
        if clip == 'SitDrink' and mesh_name in stool_meshes():
            # Decision 901: a guest of a stool (decision 863) drinks at the end of the table, on its stool; the mug of a
            # limb mount counts too
            mug = drink.Mug(skeleton, name, rest.mesh_data(out / (seats.MUG_MESH + '.xml'))[0], drink.read_limb_mounts())
            _, _, mug_points = mug.world(skeleton.fk(locals_fine), skeleton)
            both = np.concatenate((points, mug_points), axis=1)
            depth = max(drink.stool_depth(both[frame] * level) for frame in range(len(fine))
                        for level in (seats.LEVEL_SCALE_LOW, seats.LEVEL_SCALE_HIGH))
        else:
            depth = seats.level_depth(points)
        assert depth <= MAX_TABLE_DEPTH, (name, clip, 'reaches into the furniture', depth)
    has_mount = seats.MUG_BONE in skeleton.idx
    assert has_mount == (name not in seats.NO_MUG_MOUNT), (name, 'mug mount', has_mount)
    # Decision 901: SitDrink is one calm sip of tools/author_tavern_drink.py for every skeleton; the rim at the mouth of every
    # body (Kreatur and Scarab included, which had their own limb drink here) is checked by check_tavern_drink_834.py
    assert abs(skeleton.clips['SitDrink'].length - drink.CYCLE) < 1e-6, (name, 'SitDrink is not the sip of 5 s')
    sit = skeleton.locals_at(skeleton.clips['Sit'], np.zeros(1))
    points = rest.skin_vertices(skeleton, sit, vertices, weights)
    assert float(points[0, :, 2].max()) > seats.BENCH_TOP, (name, 'Sit lies below the seat of the bench')
    body_rig = seats.rig.config(name, seats.rig.Skeleton(str(out / (name + '.skeleton.xml'))))
    if name in seats.RESTING_MODELS:
        half, near, far = seats.BENCH[:3]
        reach = half if seats.SCENE['whole_bench'] else half + seats.SEAT_SIDE
        over = (np.abs(points[0, :, 0]) < reach) & (points[0, :, 1] > near) & (points[0, :, 1] < far)
        assert over.any(), (name, 'rests beside the bench')
        assert abs(float(points[0, over, 2].min()) * seats.LEVEL_SCALE_MIDDLE - seats.BENCH_TOP) < MAX_REST_GAP, (name, 'does not rest on the bench')
    else:
        chains = seats.thigh_chains(skeleton, seats.leg_chains(skeleton, name, vertices, weights, idle), body_rig)
        world = skeleton.fk(sit)
        limit = seats.LARGE_BACK_SHIFTS.get(name, MAX_PELVIS_BEHIND)
        for chain in chains:
            pelvis = world[skeleton.idx[chain[0]]][0][0]
            assert pelvis[1] <= limit + MAX_BACK_SIDE, (name, 'the pelvis lies behind its place on the bench', pelvis[1])
        assert float(points[0, :, 2].min()) > MIN_FLOOR, (name, 'a part of the body lies below the floor', float(points[0, :, 2].min()))
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
