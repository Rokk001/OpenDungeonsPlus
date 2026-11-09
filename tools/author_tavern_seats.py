#!/usr/bin/env python3
"""Author the seated tavern clips of one creature skeleton from its existing rest and tavern clips.

Writes <output>/<name>.seats.skeleton.xml, which holds the bones and only the seven new clips, and a report with the
measured contact of every clip against the bench and the table. The Blender step (tavern_seats_blend.py) keeps the clips
as actions of the source file of the model and exports them for the splice into the game skeleton.

Calls: python tools/author_tavern_seats.py <folder with the .skeleton.xml and .mesh.xml> <output folder> <name>...
"""
import argparse
import copy
import json
import math
from pathlib import Path

import numpy as np

import author_rest_poses as rest
import fix_walk_feet as feet
from fix_walk_feet_rigs import RIGS
import gen_walk_hurt as rig


# Height of the seat surface of the bench of the table mesh (the table is scaled in x and y only).
BENCH_TOP = 0.2575
# The guest stands on the middle of the bench and looks along -y. Where the top of the table lies from there.
TABLE_NEAR_EDGE = -0.0882
TABLE_FAR_EDGE = -0.735
TABLE_UNDERSIDE = 0.37
TABLE_TOP = 0.4425
TABLE_HALF_WIDTH = 0.26
# The guest of a seat sits this far beside the middle of the bench, on either side; a guest of a whole bench sits on its middle.
SEAT_SIDE = 0.164
# The table is two tiles long: each half is the old table, so every place sees the same parts next to it. The places of a
# bench lie this far apart; a normal guest sits on one of four places, a large one in the middle of two of them. The places,
# measured from the middle of the long table along the bench.
SEAT_SPACING = 0.328
NORMAL_PLACES = (-1.5 * SEAT_SPACING, -0.5 * SEAT_SPACING, 0.5 * SEAT_SPACING, 1.5 * SEAT_SPACING)
LARGE_PLACES = (-SEAT_SPACING, SEAT_SPACING)
# Along the long table, from its middle: half the length of the top, the middles of the two pedestals, half the length of
# a bench, and where the legs of a bench stand.
LONG_TABLE_HALF_LENGTH = TABLE_HALF_WIDTH + SEAT_SPACING
PEDESTAL_MIDDLES = (-SEAT_SPACING, SEAT_SPACING)
LONG_BENCH_HALF_LENGTH = 2.0 * SEAT_SPACING
LONG_BENCH_LEG_X = (0.187 + SEAT_SPACING, 0.26 + SEAT_SPACING)
# The parts of the table mesh below the top, seen from the middle of the bench: (half width, y from, y to, z from, z to).
PEDESTAL = (0.193, -0.605, -0.219, 0.0, 0.38)
BENCH = (0.328, -0.088, 0.087, 0.202, BENCH_TOP)
BENCH_LEG_X = (0.187, 0.26)
BENCH_LEG_Y = 0.042
BENCH_LEG_TOP = 0.21
# A body presses this far into the seat of the bench where it rests on it.
BENCH_SINK = 0.015
# How far the pelvis joint lies above the seat surface, as a share of the length of the thigh.
HIP_ABOVE_SEAT = 0.35
# The knees of a guest bend at least by this share of the length of the thigh.
MIN_KNEE_BEND = 0.25
# Tried in this order: how far the feet are placed in front of the body, as a share of the height of the body.
FOOT_REACH = (0.2, 0.16, 0.12, 0.08, 0.04, 0.0)
# Tried in this order: how much higher the pelvis lies than that, in tiles, for a thick thigh or a robe over the bench.
HIP_RAISES = (0.0, 0.015, 0.03, 0.045)
# Tried in this order: how far a tall body turns on the bench in degrees, so that its knees pass the table and the pedestal; the
# head turns back to the table for it. A guest of a whole bench also spreads its feet this far around the pedestal.
SEAT_TURNS = (0.0, 20.0, 35.0)
SEAT_SPREADS = (0.0, 0.12, 0.24, 0.36)
# A guest of a seat moves its feet this far apart at most, past the legs of the bench.
SEAT_SIDE_SPREADS = (0.0, 0.05, 0.1)
# Tried from the front in steps of this size up to MAX_BACK_SHIFT.
SEAT_BACK_STEP = 0.012
# A sitting body counts as out of the furniture up to this, without its arms: the arms have their own steps afterwards.
SEAT_TOLERANCE = 0.006
# A later choice of the search only wins when it stays this much further out of the furniture.
SEAT_GAIN = 0.004
# The furthest a sitting body moves back on its bench to stay out of the table top: its pelvis stays on the bench.
MAX_BACK_SHIFT = 0.084
# A belly or a knee too large for that sits further back at full size: the front of its seat stays on the bench.
LARGE_BACK_SHIFTS = {'Troll': 0.2, 'Dragon': 0.2, 'PitDemon': 0.2, 'lich': 0.16}
# The creature scale of the level runs from 1.0 to 1.1 (CreatureLevelGrowthMax). The clips fit the middle of that range, so
# the pelvis lies at most about 0.013 tiles beside the bench while the feet stay on the floor at every level.
LEVEL_SCALE_LOW = 1.0
LEVEL_SCALE_HIGH = 1.1
LEVEL_SCALE_MIDDLE = 1.05
# Types with a bed of 2x2 in creatures.cfg have a whole bench; every other guest has half of it.
LARGE_MODELS = ('PitDemon', 'Troll', 'Scarab', 'Dragon', 'Kreatur')
# Bodies that do not sit on a bench but rest on it in the pose they rest in on the ground, tried turned in this order: along
# the bench first. The head of a body along the bench looks towards the table.
RESTING_MODELS = ('CaveHornet', 'Kreatur', 'LavaSpawn', 'Rat', 'Roach', 'Scarab', 'Slime', 'Spider', 'Tentacle', 'Wyvern')
REST_TURNS = (90.0, -90.0, 0.0, 180.0)
# A body that may not turn its back to the table, tried in this order.
REST_TURN_LIMITS = {'Scarab': (90.0, -90.0, 0.0)}
# Tried in this order: how far the head of a body along the bench looks at the table; a head that turns less wins when that
# saves this much of the step back.
REST_HEAD_TURNS = (50.0, 25.0, 0.0)
REST_HEAD_ADVANTAGE = 0.08
# A body with free limbs lies this much further from the table, so that the limbs can move above it.
REST_EXTRA_BACK = {'LavaSpawn': 0.16, 'Rat': 0.02, 'Roach': 0.08}
# A clip that keeps less than this share of its motion plays on the spine and the head alone, if that moves more.
LOW_MOTION_SHARE = 0.25
# A clip faster than this, in heights of the body per second, moves less as a whole, tried with these shares of its motion.
MAX_CLIP_SPEED = 12.0
CALM_SHARES = (0.85, 0.7, 0.55, 0.4, 0.3)
# A flat body turns this share of a slap, because its long legs would sweep far.
RESTING_SLAP_SHARE = 0.4
# How far a resting body moves behind the middle of the bench at most, in steps of this size, to stay out of the table.
REST_BACK_STEP = 0.01
REST_BACK_MAX = 0.8
# A resting body stays out of the furniture up to this, and a turn along the bench stays unless another saves this much.
REST_TOLERANCE = 0.015
REST_TURN_ADVANTAGE = 0.25
# A snake body rolls up on the bench, and the tail of every other resting body curls around it: the degrees per joint.
COILED_MODELS = ('Tentacle', 'LavaSpawn')
COIL_TAIL_DEGREES = 110.0
CURL_TAIL_DEGREES = 40.0
# The clips a resting body takes its pose from, tried in this order; a snake body keeps its upper body up.
REST_SOURCES = {'LavaSpawn': ('AmbientSit', 'AmbientLie'), 'Scarab': ('AmbientLie', 'AmbientSit', 'Sleep')}
# A resting body lies no deeper in the floor than this: what hangs behind the bench may not sink through the floor.
REST_FLOOR_SINK = 0.03
DEFAULT_REST_SOURCES = ('AmbientLie',)
# A walking body that does not fit on its legs at full size up to this depth rests on the bench instead.
SEATED_LIMIT = 0.025
# A held item that reaches further than this from the hand, and more than this many forearms, is a long weapon: it stays
# upright while the creature sits. A chain without upper arm, forearm and hand holds no weapon of its own.
LONG_WEAPON_REACH = 0.45
LONG_WEAPON_FOREARMS = 2.0
LONG_WEAPON_DIRECTION = (0.0, 0.15, 1.0)
# How much of the motion of a clip stays at a frame that reaches into the table, tried in this order.
DAMP_SHARES = (1.0, 0.8, 0.6, 0.4, 0.2, 0.0)
# A moving clip may reach this far into the table: damping a hand on the edge makes the arm jump, and that crosses more of it.
CLIP_TABLE_TOLERANCE = 0.035
# No sample between the keys of a clip may show a limb deeper in the table than this; a clip that does moves less as a whole.
MAX_CROSSING_SHARE = 0.0
CROSSING_DEPTH = 0.04
CROSSING_STEPS = 4
CLIP_MOTION_SHARES = (0.8, 0.6, 0.4, 0.2, 0.0)
# A crossing that is left after the arms are led around the table: the clip moves less around it, in rounds over a few frames.
NOTCH_ROUNDS = 40
NOTCH_DEPTH = 0.25
NOTCH_FRAMES = 2.0
# Damping may not make a body part faster than this, in heights of the body per second, unless the clip is that fast anyway.
MAX_BODY_SPEED = 10.0
# A relaxed arm may reach this far below the floor (the tip of a weapon) before it is raised for it.
FLOOR_TOLERANCE = 0.05
# How far a relaxed arm tries to rise at the shoulder, in degrees.
RELAXED_ARM_ANGLES = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0)
# A clip may reach this far into the table (a hand on its edge); up to this many degrees the upper body leans back for it.
TABLE_TOLERANCE = 0.02
LEAN_BACK_STEP = 6.0
LEAN_BACK_MAX = 36.0
# Up to this many degrees an arm rises at its shoulder to pass over the table.
ARM_LIFT_STEP = 8.0
ARM_LIFT_MAX = 48.0
# An arm that crosses the table edge bends on its way so that the hand passes above the table. The angles at the shoulder and
# the elbow in degrees around the axis across the body, and how often a route is searched again around a crossing.
ROUTE_SHOULDER = (0.0, -15.0, -30.0, -45.0, -60.0, 15.0, 30.0, 45.0)
ROUTE_ELBOW = (0.0, -20.0, -40.0, -60.0, -80.0, -100.0, -120.0)
ROUTE_DEPTH = 0.03
ROUTE_DEPTH_COST = 1.0e5
ROUTE_BEND_COST = 1.0e-3
ROUTE_STEP_COST = 1.0e-1
ROUTE_CROSSING_COST = 1.0e4
ROUTE_NEAR = 20.0
ROUTE_SMOOTH_FRAMES = 2.0
# The route is coarse. The frames around the deepest crossing then bend by this many degrees at a time, a smooth bump over
# this many frames, in the direction that helps most; the limits keep the shoulder and the elbow in a natural range.
ROUTE_PUSH_DEGREES = 8.0
ROUTE_PUSH_MIN_DEGREES = 1.0
ROUTE_PUSH_FRAMES = 2.0
ROUTE_PUSH_NARROW_FRAMES = 0.8
ROUTE_PUSH_ROUNDS = 60
ROUTE_PUSH_DIRECTIONS = ((0.0, -1.0), (-1.0, 0.0), (1.0, 0.0), (1.0, -1.0), (-1.0, -1.0), (0.0, 1.0))
ROUTE_SHOULDER_RANGE = (-80.0, 60.0)
ROUTE_ELBOW_RANGE = (-150.0, 20.0)
ROUTE_TRIES = 40
ROUTE_PASSES = 2
# The creature scale of the level a body is posed at, and whether the guest takes a whole bench.
SCENE = {'size': LEVEL_SCALE_MIDDLE, 'whole_bench': False}
# (clip, length in seconds, keyframes, source clip of the upper body, looped)
CLIPS = (('Sit', 4.0, 17, None, True),
         ('SitDrink', None, 49, 'Drink', True),
         ('SitSlap', None, 49, 'Slap', False),
         ('SitSlapped', 0.8, 17, None, False),
         ('SitArmWrestle', None, 49, 'ArmWrestle', True),
         ('SitDice', None, 49, 'Dice', True),
         ('SitSlumped', 4.0, 17, None, True))
# The bone that holds the mug of SitDrink, and the turn of an attached mesh to the axes of its bone.
MUG_BONE = 'Weapon_R'
MUG_MESH = 'TavernMug.mesh'
MUG_POINTS = 200
# How far the mug stands along its bone from the bottom to the rim, in tiles (the mesh reaches from 0.009 to -0.171 along x).
MUG_HEIGHT = 0.17
# Decision 901: the hand holds the mug at its middle; the render manager shifts it this far along the x axis of Weapon_R
# (TAVERN_MUG_GRIP_SHIFT) and makes it this much wider (TAVERN_MUG_GIRTH_SCALE)
MUG_GRIP_SHIFT = 0.1
MUG_GIRTH = 1.8
# Steps along the way of the foot of the mug that the limb is solved for
MUG_WAY_STEPS = 65
TABLE_SAMPLES_COARSE = 97
# The skeletons that have no hand or limb for the mug mount: the mug is not shown for them in SitDrink.
NO_MUG_MOUNT = ('CaveHornet', 'Defender', 'Rat', 'Roach', 'Spider', 'Tentacle')
MUG_TURN = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
# Share of a clip at each end in which the upper body goes from the seat pose to the source clip and back.
BLEND_SHARE = 0.12
# Recoil of a slap in degrees: turn of the head and spine, tilt back; damped over the clip.
SLAP_TURN = 28.0
SLAP_TILT = 16.0
SLAP_OSCILLATIONS = 2.5
# Slumped forward over the table: bow of the spine and additional bow of the head in degrees.
SLUMP_BOW = 58.0
SLUMP_HEAD = 28.0
BREATH = 0.008
BREATH_SECONDS = 4.0
SWAY_DEGREES = 2.0

# Bodies whose own clips hardly move them play a clip made for them: the bones swing on the seat pose, each as
# (bone, world axis, degrees, cycles in the clip, phase in radians, mean degrees). A swing is the mean plus the degrees times a
# sine, and it fades in and out at the ends of the clip like every clip. A limb that hangs over the table swings away from it
# and back, never into it. A chain of bones follows its first bone with a lag, like a whip.
WHIP_LAG = 0.6


def whip(chain, axis, degrees, cycles, phase, up, lag=WHIP_LAG):
    return tuple((bone, axis, degrees, cycles, phase - lag * index, up * degrees) for index, bone in enumerate(chain))


PLAY_SWINGS = {
    ('Kreatur', 'SitSlap'): (
        (('body', 'y', 4.0, 2, 0.0, -4.0), ('head', 'z', 30.0, 3, 0.0, 0.0), ('head', 'x', 12.0, 2, 1.0, 0.0))
        + whip(('tentafr1_r', 'tentafr2_r'), 'x', 18.0, 2, 0.0, -1.0) + whip(('tentab1_r', 'tentab2_r'), 'x', 18.0, 2, 3.14, -1.0)
        + whip(('tentafr1_l', 'tentafr2_l'), 'x', 18.0, 2, 3.14, 1.0) + whip(('tentab1_l', 'tentab2_l'), 'x', 18.0, 2, 0.0, 1.0)
        + whip(('tail1', 'tail2'), 'z', 40.0, 3, 0.0, 0.0, 0.7)),
    ('Kreatur', 'SitDice'): (
        (('body', 'y', 3.0, 4, 0.0, -3.0), ('head', 'y', 14.0, 4, 0.0, -2.0), ('head', 'z', 22.0, 2, 0.5, 0.0))
        + whip(('tentafr1_r', 'tentafr2_r'), 'x', 10.0, 6, 0.0, -1.0, 0.8) + whip(('tentab1_r', 'tentab2_r'), 'x', 14.0, 2, 1.5, -1.0, 0.8)
        + whip(('tentafr1_l', 'tentafr2_l'), 'x', 14.0, 2, 3.14, 1.0, 0.8) + whip(('tentab1_l', 'tentab2_l'), 'x', 14.0, 2, 0.0, 1.0, 0.8)
        + whip(('tail1', 'tail2'), 'z', 35.0, 5, 0.0, 0.0, 0.7)),
    ('Kreatur', 'SitArmWrestle'): (
        (('body', 'y', 3.0, 3, 0.0, -3.0), ('head', 'x', 8.0, 6, 0.0, 0.0), ('head', 'y', 6.0, 3, 1.0, -2.0),
         ('tentafr1_r', 'z', 12.0, 5, 0.0, 0.0), ('tentafr2_r', 'z', 10.0, 5, 0.8, 0.0),
         ('tentafr1_l', 'z', 12.0, 5, 3.14, 0.0), ('tentafr2_l', 'z', 10.0, 5, 3.9, 0.0))
        + whip(('tentab1_r', 'tentab2_r'), 'x', 8.0, 3, 0.0, -1.0, 0.8) + whip(('tail1', 'tail2'), 'z', 25.0, 4, 0.0, 0.0, 0.7)),
    ('Scarab', 'SitSlap'): (
        ('Bone.001', 'y', -4.0, 2, 0.0, -4.0), ('Bone.004', 'y', 28.0, 4, 0.0, 0.0), ('Bone.003', 'y', 14.0, 4, 0.5, 0.0),
        ('Bone.001_L', 'x', 26.0, 2, 3.14, 13.0), ('Bone.001_L.001', 'x', 30.0, 2, 2.44, 13.0), ('Bone.001_L.002', 'x', 20.0, 2, 1.74, 0.0)),
    ('Scarab', 'SitDice'): (
        ('Bone.001', 'y', -4.0, 4, 0.0, -4.0), ('Bone.004', 'y', 20.0, 4, 0.0, 0.0), ('Bone.003', 'y', 10.0, 4, 0.6, 0.0),
        ('Bone.004', 'z', 20.0, 2, 0.0, 0.0),
        ('Bone.001_L', 'x', 12.0, 6, 0.0, 12.0), ('Bone.001_L.001', 'x', 14.0, 6, -0.8, 14.0), ('Bone.001_L.002', 'x', 10.0, 6, -1.6, 0.0)),
    ('Scarab', 'SitArmWrestle'): (
        ('Bone.001', 'y', -3.0, 3, 0.0, -3.0), ('Bone.004', 'y', 12.0, 6, 0.0, 0.0), ('Bone.003', 'y', 6.0, 6, 0.5, 0.0),
        ('Bone.001_L', 'x', 10.0, 4, 0.0, 10.0), ('Bone.001_L.001', 'x', 12.0, 4, -0.8, 12.0)),
    ('CaveHornet', 'SitDice'): (
        ('Head', 'y', 20.0, 4, 0.0, 0.0), ('Head', 'z', 20.0, 2, 0.5, 0.0), ('Body2', 'z', 10.0, 2, 1.0, 0.0),
        ('Tail1', 'z', 30.0, 5, 0.0, 0.0), ('Tail2', 'z', 35.0, 5, -0.7, 0.0), ('Proboscis1_L', 'y', 15.0, 6, 0.0, 0.0),
        ('Proboscis1_R', 'y', 15.0, 6, 3.14, 0.0)),
    ('Slime', 'SitDice'): (
        ('slime_base', 'z', 18.0, 2, 0.0, 0.0), ('slime_mid', 'z', 26.0, 2, -0.8, 0.0), ('slime_head', 'y', 28.0, 4, 0.0, 0.0),
        ('slime_head', 'z', 35.0, 2, -1.6, 0.0)),
    ('LavaSpawn', 'SitSlap'): (
        ('spine', 'x', 8.0, 2, 0.0, 0.0), ('chest', 'x', 10.0, 2, 0.6, 0.0), ('head', 'z', 22.0, 3, 0.0, 0.0),
        ('tail1', 'z', 30.0, 3, 0.0, 0.0), ('tail2', 'z', 40.0, 3, 1.0, 0.0)),
}
# Arms that hammer on the table in turns, as (upper arm, forearm, end of the forearm, phase): the two segments aim at a
# direction given by the yaw (0 outwards, 90 forwards) and the pitch in degrees. Raised: (yaw, pitch) of the upper arm and the
# forearm; slammed: the same when the hand comes down on the table.
PLAY_HAMMERS = {
    ('LavaSpawn', 'SitSlap'): {
        'arms': (('arm1.L', 'arm2.L', 'finger1.L', 0.0), ('arm1.R', 'arm2.R', 'finger1.R', math.pi)),
        'cycles': 2, 'raised': ((40.0, 25.0), (35.0, 5.0)), 'slammed': ((45.0, 30.0), (70.0, -65.0))}}
PLAY_AXES = {'x': (1.0, 0.0, 0.0), 'y': (0.0, 1.0, 0.0), 'z': (0.0, 0.0, 1.0)}
# A body whose limb has no hand brings the mug to its mouth on that limb: SitDrink of the chain of bones that ends in the bone
# that carries the mug (Weapon_R), as (bones from the base of the limb to the carrier, the bone of the head, the mouth in the
# frame of that bone, where the foot of the mug is held in front of the mouth in the frame of the body, how high the foot rises
# on its way, drinks in the clip).
# The limb follows the chain of joints that reaches the foot of the mug, the mug tips from upright until its rim lies at the mouth.
PLAY_MUGS = {
    ('Kreatur', 'SitDrink'): {
        'chain': ('tentafr1_r', 'tentafr2_r', 'tentafr3_r', 'tentafr4_r'), 'head': 'head', 'mouth': (0.0, 0.11, 0.0),
        'foot': (0.0, -0.1, 0.14), 'arc': 0.15, 'drinks': 1},
    ('Scarab', 'SitDrink'): {
        'chain': ('Bone.001_R', 'Bone.001_R.001', 'Bone.001_R.002', 'Bone.001_R.003', 'Bone.001_R.004', 'Bone.001_R.005'),
        'head': 'Bone.004', 'mouth': (0.0, 0.2, 0.0), 'foot': (0.0, -0.1, 0.14), 'arc': 0.15, 'drinks': 1},
}


# Whether the rig is a walking body with arms: its legs stay in the seat pose while its upper body plays the clips.
def is_humanoid(body_rig):
    return isinstance(body_rig, list) and all(item['kind'] == 'biped' for item in body_rig)


# Return the bones of the legs from the rig tables, for rigs that have legs.
def leg_chains(skeleton, name, vertices, weights, base):
    config = RIGS.get(name) or rest.insect_config(skeleton, base, vertices, weights, name)
    if config is None:
        return []
    return [spec['chain'] for foot in config['feet'] for spec in foot['units']]


# Return the chains that hold a thigh: those of the leg table, or the leg of the body plan when the table has only feet.
def thigh_chains(skeleton, chains, body_rig):
    long_chains = [chain for chain in chains if len(chain) >= 2]
    if long_chains:
        return long_chains
    return [chain for item in body_rig for chain in item.get('hurt', []) if all(bone in skeleton.idx for bone in chain)]


# Return the indices of the bones that follow the legs: the chains, what hangs below them and the way up to the root.
def fixed_bones(skeleton, chains):
    fixed = set()
    for chain in chains:
        for bone in chain:
            index = skeleton.idx[bone]
            fixed.add(index)
    for index in skeleton.topo:
        if skeleton.parent[index] in fixed:
            fixed.add(index)
    for chain in chains:
        index = skeleton.parent[skeleton.idx[chain[0]]]
        while index >= 0:
            fixed.add(index)
            index = skeleton.parent[index]
    for index in skeleton.topo:
        if skeleton.parent[index] < 0:
            fixed.add(index)
    return fixed


# Return the height of the pelvis joint and the length of the thigh of a humanoid from the rest pose.
def hip_measure(skeleton, chains, world):
    heights = []
    lengths = []
    for chain in chains:
        ids = [skeleton.idx[bone] for bone in chain]
        for upper, lower in zip(ids, ids[1:]):
            length = float(np.linalg.norm(world[lower][0][0] - world[upper][0][0]))
            if length > 0.03:
                heights.append(float(world[upper][0][0, 2]))
                lengths.append(length)
                break
    assert heights, 'No thigh in the leg chains'
    return min(heights), max(lengths)


# Return the vertices that belong to the body and not to the legs, and how low the body reaches.
def body_vertices(skeleton, chains, weights):
    legs = set()
    for chain in chains:
        legs.update(skeleton.idx[bone] for bone in chain)
    for index in skeleton.topo:
        if skeleton.parent[index] in legs:
            legs.add(index)
    return [index for index, row in enumerate(weights)
            if row and sum(weight for bone, weight in row if bone not in legs) >= 0.9]


# Measure per frame how far a posed body reaches into the furniture, in units of the points. The table is two tiles long and
# the same clip plays on every place a guest can take, so the body is measured on each of them. The top of the table counts
# from its near edge, which also catches a limb deep inside this thin plate; every other part counts from its nearest face.
# Vertices outside all furniture heights and depths for the entire clip cannot contribute a positive penetration.
def frame_depths(points, selected=None):
    if selected is not None:
        points = points[:, selected, :]
    scene = SCENE['size']
    world = points * scene
    low_y = min(TABLE_FAR_EDGE, PEDESTAL[1], BENCH[1], -BENCH_LEG_Y)
    high_y = max(TABLE_NEAR_EDGE, PEDESTAL[2], BENCH[2], BENCH_LEG_Y)
    low_z = min(TABLE_UNDERSIDE, PEDESTAL[3], BENCH[3], 0.0)
    high_z = max(TABLE_TOP, PEDESTAL[4], BENCH[4] - BENCH_SINK, BENCH_LEG_TOP)
    candidate = ((world[:, :, 1] > low_y) & (world[:, :, 1] < high_y) &
                 (world[:, :, 2] > low_z) & (world[:, :, 2] < high_z))
    # Keep nonfinite coordinates too, preserving the original numerical failure behavior.
    keep = candidate.any(axis=0) | (~np.isfinite(world)).any(axis=(0, 2))
    world = world[:, keep, :]
    if world.shape[1] == 0 and points.shape[1] != 0:
        return np.zeros(points.shape[0])
    x, y, z = world[:, :, 0], world[:, :, 1], world[:, :, 2]
    worst = np.zeros(world.shape[:2])
    # Furniture depth and height planes do not vary between seat positions.
    table_yz = (z > TABLE_UNDERSIDE) & (z < TABLE_TOP) & (y > TABLE_FAR_EDGE)
    table_depth = TABLE_NEAR_EDGE - y
    half, near, far, low, high = PEDESTAL
    pedestal_yz = np.minimum(y - near, far - y)
    np.minimum(pedestal_yz, z - low, out=pedestal_yz)
    np.minimum(pedestal_yz, high - z, out=pedestal_yz)
    _, near, far, low, high = BENCH
    bench_yz = np.minimum(y - near, far - y)
    np.minimum(bench_yz, z - low, out=bench_yz)
    np.minimum(bench_yz, high - BENCH_SINK - z, out=bench_yz)
    leg_yz = np.minimum(BENCH_LEG_Y - np.abs(y), z)
    np.minimum(leg_yz, BENCH_LEG_TOP - z, out=leg_yz)
    for place in LARGE_PLACES if SCENE['whole_bench'] else NORMAL_PLACES:
        # Along the bench, measured from the middle of the long table
        along = np.abs(x + place)
        inside = table_yz & (along < LONG_TABLE_HALF_LENGTH)
        worst = np.maximum(worst, np.where(inside, table_depth, 0.0))
        half, near, far, low, high = PEDESTAL
        for middle in PEDESTAL_MIDDLES:
            beside = np.abs(x + place - middle)
            depth = np.minimum(half - beside, pedestal_yz)
            np.maximum(worst, depth, out=worst)
        depth = np.minimum(LONG_BENCH_HALF_LENGTH - along, bench_yz)
        np.maximum(worst, depth, out=worst)
        depth = np.minimum(along - LONG_BENCH_LEG_X[0], LONG_BENCH_LEG_X[1] - along)
        np.minimum(depth, leg_yz, out=depth)
        np.maximum(worst, depth, out=worst)
    return np.maximum(0.0, worst.max(axis=1)) / scene

# Measure how far a posed body reaches into the furniture; selected limits it to some vertices.
def table_depth(points, selected=None):
    return float(frame_depths(points, selected).max())


# Measure a pose of a finished clip at the smallest and the largest creature scale of the level, in tiles.
def level_depth(points):
    saved = SCENE['size']
    depth = 0.0
    for level in (LEVEL_SCALE_LOW, LEVEL_SCALE_HIGH):
        SCENE['size'] = level
        depth = max(depth, table_depth(points) * level)
    SCENE['size'] = saved
    return depth


# Measure per frame how far a pose reaches into the table at the smallest and the largest creature scale of the level, in
# tiles.
def worst_depths(points):
    saved = SCENE['size']
    depths = np.zeros(points.shape[0])
    for level in (LEVEL_SCALE_LOW, LEVEL_SCALE_HIGH):
        SCENE['size'] = level
        depths = np.maximum(depths, frame_depths(points) * SCENE['size'])
    SCENE['size'] = saved
    return depths


# Return the hand joints with a long weapon in their mesh and the direction of the weapon seen from the hand.
def long_weapons(skeleton, base, body_rig, vertices, weights):
    found = []
    if not isinstance(body_rig, list):
        return found
    world = skeleton.fk(base)
    points = rest.skin_vertices(skeleton, base, vertices, weights)[0]
    for item in body_rig:
        for chain in item.get('hang', []):
            hand = chain[-1]
            if (len(chain) < 3) or not all(bone in skeleton.idx for bone in chain[-2:]):
                continue
            index = skeleton.idx[hand]
            forearm = float(np.linalg.norm(world[index][0][0] - world[skeleton.idx[chain[-2]]][0][0]))
            bones = {index}
            for other in skeleton.topo:
                if skeleton.parent[other] in bones:
                    bones.add(other)
            held = [number for number, row in enumerate(weights) if sum(weight for bone, weight in row if bone in bones) >= 0.5]
            if not held:
                continue
            reach = points[held] - world[index][0][0]
            lengths = np.linalg.norm(reach, axis=1)
            if lengths.max() < max(LONG_WEAPON_REACH, LONG_WEAPON_FOREARMS * forearm):
                continue
            found.append((hand, world[index][1][0].T @ (reach[int(lengths.argmax())] / lengths.max())))
    return found


# Turn the hands so that a long weapon stands upright in every frame instead of lying over the table.
def hold_weapons_upright(skeleton, local, weapons):
    if not weapons:
        return
    target = np.array(LONG_WEAPON_DIRECTION)
    target = target / np.linalg.norm(target)
    for hand, direction in weapons:
        world = skeleton.fk(local)
        current = world[skeleton.idx[hand]][1] @ direction
        axis = np.cross(current, target)
        norm = np.linalg.norm(axis, axis=1)
        angle = np.arctan2(norm, current @ target)
        axis[norm < 1e-8] = rig.X_AXIS
        axis[norm >= 1e-8] /= norm[norm >= 1e-8, None]
        rest.rotate_joint(skeleton, local, hand, axis, angle)


# Mix a clip with the seat pose per frame: share 1 keeps the clip, share 0 is the seat pose.
def mix_with_seat(local, seated, shares):
    mixed = []
    for (position, rotation, scale), (seat_position, seat_rotation, _) in zip(local, seated):
        count = len(shares)
        seat_position = np.tile(seat_position[:1], (count, 1))
        seat_rotation = np.tile(seat_rotation[:1], (count, 1))
        mixed.append((seat_position + (position - seat_position) * shares[:, None],
                      slerp(seat_rotation, rotation, shares), scale))
    return mixed


# Reduce the motion of a clip in each frame that reaches into the table, as little as that frame allows. A share between two
# others can be the worse one: an arm that rests on the table top passes the edge of the table on its way there.
def damp_into_table(skeleton, local, seated, vertices, weights, smooth=True):
    limit = CLIP_TABLE_TOLERANCE
    if worst_depths(rest.skin_vertices(skeleton, local, vertices, weights)).max() <= limit:
        return local
    count = local[0][0].shape[0]
    shares = np.zeros(count)
    decided = np.zeros(count, dtype=bool)
    for share in DAMP_SHARES:
        depths = worst_depths(rest.skin_vertices(skeleton, mix_with_seat(local, seated, np.full(count, share)), vertices, weights))
        good = (depths <= limit) & ~decided
        shares[good] = share
        decided |= good
    if not smooth:
        return mix_with_seat(local, seated, shares)
    # A share that changes from one frame to the next makes the limb jump: each frame takes the lowest share around it, smoothly
    frames = np.arange(count)
    near = np.abs(frames[:, None] - frames[None, :]) <= ROUTE_SMOOTH_FRAMES
    lowest = np.where(near, shares[None, :], 1.0).min(axis=1)
    kernel = np.exp(-0.5 * ((frames[:, None] - frames[None, :]) / ROUTE_SMOOTH_FRAMES) ** 2)
    return mix_with_seat(local, seated, np.minimum(lowest, (kernel @ lowest) / kernel.sum(axis=1)))


# Return the share of a clip, sampled between its keys, that shows a limb in the table at either end of the level scale.
def crossing_share(skeleton, local, vertices, weights):
    count = local[0][0].shape[0]
    fine = np.linspace(0.0, count - 1.0, (count - 1) * CROSSING_STEPS + 1)
    lower = np.minimum(fine.astype(int), count - 2)
    amounts = fine - lower
    sampled = [(position[lower] + (position[lower + 1] - position[lower]) * amounts[:, None],
                slerp(rotation[lower], rotation[lower + 1], amounts),
                scale[lower] + (scale[lower + 1] - scale[lower]) * amounts[:, None]) for position, rotation, scale in local]
    return float((worst_depths(rest.skin_vertices(skeleton, sampled, vertices, weights)) > CROSSING_DEPTH).mean())


# Return the depth in the table per sample between the keys of a clip, at either end of the level scale.
def fine_depths(skeleton, local, vertices, weights):
    count = local[0][0].shape[0]
    fine = np.linspace(0.0, count - 1.0, (count - 1) * CROSSING_STEPS + 1)
    lower = np.minimum(fine.astype(int), count - 2)
    amounts = fine - lower
    sampled = [(position[lower] + (position[lower + 1] - position[lower]) * amounts[:, None],
                slerp(rotation[lower], rotation[lower + 1], amounts),
                scale[lower] + (scale[lower + 1] - scale[lower]) * amounts[:, None]) for position, rotation, scale in local]
    return worst_depths(rest.skin_vertices(skeleton, sampled, vertices, weights))


# Bend an arm by the given angles per frame at the shoulder and the elbow.
def bend_arm(skeleton, local, shoulder, elbow, shoulder_degrees, elbow_degrees):
    bent = hold_copy(local)
    rest.rotate_joint(skeleton, bent, shoulder, rig.X_AXIS, np.radians(shoulder_degrees))
    rest.rotate_joint(skeleton, bent, elbow, rig.X_AXIS, np.radians(elbow_degrees))
    return bent


# Return the cheapest bend per frame through the costs of the frames; forbidden holds the expensive steps between two frames.
def cheapest_route(frame_costs, angles, forbidden):
    count, choices = frame_costs.shape
    steps = ROUTE_STEP_COST * ((angles[:, None, :] - angles[None, :, :]) ** 2).sum(axis=2)
    totals = np.full(choices, np.inf)
    totals[0] = 0.0
    back = np.zeros((count, choices), dtype=int)
    for frame in range(1, count):
        moves = steps.copy()
        for (at, first, second), cost in forbidden.items():
            if at == frame - 1:
                moves[first, second] += cost
        candidates = totals[:, None] + moves
        back[frame] = candidates.argmin(axis=0)
        totals = candidates.min(axis=0) + frame_costs[frame]
    path = np.zeros(count, dtype=int)
    for frame in range(count - 1, 0, -1):
        path[frame - 1] = back[frame, path[frame]]
    return path


# Smooth the angles of a route over time, so that the arm does not jump from one bend to the next; the ends stay.
def smooth_route(degrees):
    count = len(degrees)
    frames = np.arange(count)
    kernel = np.exp(-0.5 * ((frames[:, None] - frames[None, :]) / ROUTE_SMOOTH_FRAMES) ** 2)
    smooth = (kernel @ degrees.astype(float)) / kernel.sum(axis=1)
    fade = np.minimum(1.0, np.minimum(frames, count - 1 - frames) / (2.0 * ROUTE_SMOOTH_FRAMES))
    return smooth * fade


# Bend the frames around the deepest crossing of a route further, as long as that takes the arm out of the table.
def push_route(skeleton, local, joints, held_vertices, held_weights, shoulder_degrees, elbow_degrees):
    count = len(shoulder_degrees)
    frames = np.arange(count)
    bent = bend_arm(skeleton, local, joints[0], joints[1], shoulder_degrees, elbow_degrees)
    depths = fine_depths(skeleton, bent, held_vertices, held_weights)
    step = ROUTE_PUSH_DEGREES
    width = ROUTE_PUSH_FRAMES
    for _ in range(ROUTE_PUSH_ROUNDS):
        if depths.max() <= ROUTE_DEPTH:
            break
        if step < ROUTE_PUSH_MIN_DEGREES:
            # A crossing right after the seat pose needs a narrow bump, because the first and the last frame do not bend
            if width <= ROUTE_PUSH_NARROW_FRAMES:
                break
            width = ROUTE_PUSH_NARROW_FRAMES
            step = ROUTE_PUSH_DEGREES
        centre = float(depths.argmax()) / CROSSING_STEPS
        bump = np.exp(-0.5 * ((frames - centre) / width) ** 2)
        bump[[0, -1]] = 0.0
        score = np.maximum(0.0, depths - ROUTE_DEPTH).sum()
        found = None
        for first, second in ROUTE_PUSH_DIRECTIONS:
            trial_shoulder = np.clip(shoulder_degrees + first * step * bump, *ROUTE_SHOULDER_RANGE)
            trial_elbow = np.clip(elbow_degrees + second * step * bump, *ROUTE_ELBOW_RANGE)
            trial = bend_arm(skeleton, local, joints[0], joints[1], trial_shoulder, trial_elbow)
            trial_depths = fine_depths(skeleton, trial, held_vertices, held_weights)
            trial_score = np.maximum(0.0, trial_depths - ROUTE_DEPTH).sum()
            if trial_score < score - 1e-5:
                found = (trial_shoulder, trial_elbow, trial, trial_depths)
                score = trial_score
        if found is None:
            step *= 0.5
            continue
        shoulder_degrees, elbow_degrees, bent, depths = found
    return bent, float(depths.max())


# Search the route of one arm for the two joints that bend it; returns the bent clip and its depth, or None if nothing helped.
def route_arm(skeleton, local, joints, held_vertices, held_weights, start_depth):
    count = local[0][0].shape[0]
    angles = np.array([(first, second) for first in ROUTE_SHOULDER for second in ROUTE_ELBOW])
    frame_costs = np.zeros((count, len(angles)))
    for choice, (first, second) in enumerate(angles):
        bent = bend_arm(skeleton, local, joints[0], joints[1], np.full(count, first), np.full(count, second))
        depths = worst_depths(rest.skin_vertices(skeleton, bent, held_vertices, held_weights))
        frame_costs[:, choice] = (ROUTE_DEPTH_COST * np.maximum(0.0, depths - ROUTE_DEPTH) ** 2 +
                                  ROUTE_BEND_COST * (first * first + second * second))
    # The ends of a clip stay the seat pose, so that it joins the other clips
    frame_costs[[0, -1], :] = np.inf
    frame_costs[[0, -1], 0] = 0.0
    forbidden = {}
    best_path = None
    best_depth = start_depth
    for _ in range(ROUTE_TRIES):
        path = cheapest_route(frame_costs, angles, forbidden)
        bent = bend_arm(skeleton, local, joints[0], joints[1], angles[path, 0], angles[path, 1])
        depths = fine_depths(skeleton, bent, held_vertices, held_weights)
        if (best_path is None) or (depths.max() < best_depth - 1e-4):
            best_path, best_depth = path, float(depths.max())
        if depths.max() <= ROUTE_DEPTH:
            break
        for sample in np.flatnonzero(depths > ROUTE_DEPTH):
            at = min(int(sample) // CROSSING_STEPS, count - 2)
            # What lies one step of the grid beside a step through the table goes through it as well
            near_first = np.flatnonzero(np.abs(angles - angles[path[at]]).max(axis=1) <= ROUTE_NEAR)
            near_second = np.flatnonzero(np.abs(angles - angles[path[at + 1]]).max(axis=1) <= ROUTE_NEAR)
            for first in near_first:
                for second in near_second:
                    forbidden[(at, int(first), int(second))] = ROUTE_CROSSING_COST
    result, depth = push_route(skeleton, local, joints, held_vertices, held_weights,
                               smooth_route(angles[best_path, 0]), smooth_route(angles[best_path, 1]))
    return (result, depth) if depth < start_depth - 1e-4 else None


# Lead every arm that crosses the table edge around it: the first and the last frame stay the seat pose, the frames between
# bend as little as it takes. Only the arm and what it holds are measured here. A chain can end at the hand or at the forearm,
# so the last two pairs of its joints are tried.
def route_arms_over_table(skeleton, local, body_rig, vertices, weights):
    if not isinstance(body_rig, list):
        return local
    vertices = np.asarray(vertices)
    for item in body_rig:
        for chain in list(item.get('hang', [])) + ([item['press']] if item.get('press') else []):
            joints = [bone for bone in chain if bone in skeleton.idx]
            if len(joints) < 2:
                continue
            bones = {skeleton.idx[bone] for bone in joints[-3:]}
            for index in skeleton.topo:
                if skeleton.parent[index] in bones:
                    bones.add(index)
            held = [index for index, row in enumerate(weights) if sum(weight for bone, weight in row if bone in bones) >= 0.5]
            if not held:
                continue
            held_vertices = vertices[held]
            held_weights = [weights[index] for index in held]
            depth = float(fine_depths(skeleton, local, held_vertices, held_weights).max())
            pairs = [joints[-2:]] if len(joints) < 3 else [joints[-3:-1], joints[-2:]]
            for pair in pairs:
                if depth <= ROUTE_DEPTH:
                    break
                routed = route_arm(skeleton, local, pair, held_vertices, held_weights, depth)
                if routed is not None:
                    local, depth = routed
    return local


# Let a clip move less only around its crossings of the table, as long as that clears them; returns None if it does not.
def notch_crossings(skeleton, local, seated, vertices, weights):
    count = local[0][0].shape[0]
    frames = np.arange(count)
    shares = np.ones(count)
    result = local
    for _ in range(NOTCH_ROUNDS):
        depths = fine_depths(skeleton, result, vertices, weights)
        if depths.max() <= CROSSING_DEPTH:
            return result
        centre = float(depths.argmax()) / CROSSING_STEPS
        shares *= 1.0 - NOTCH_DEPTH * np.exp(-0.5 * ((frames - centre) / NOTCH_FRAMES) ** 2)
        result = mix_with_seat(local, seated, shares)
    return None


# Return how far a clip moves from its first frame, and the highest speed of a vertex per frame.
def clip_motion(skeleton, local, vertices, weights):
    points = rest.skin_vertices(skeleton, local, vertices, weights)
    return (float(np.linalg.norm(points - points[:1], axis=2).max()),
            float(np.linalg.norm(np.diff(points, axis=0), axis=2).max()))


# Damp a clip into the table, and let it move less as a whole when a limb still stays in the table. Smooth damping does not
# jump but can stop a clip that needs its full reach, so both are tried: the clip that moves most without jumping is kept.
def keep_out_of_table(skeleton, local, seated, vertices, weights, height, seconds_per_frame):
    fastest = max(MAX_BODY_SPEED * height * seconds_per_frame, clip_motion(skeleton, local, vertices, weights)[1])
    candidates = []
    for smooth in (False, True):
        result = damp_into_table(skeleton, local, seated, vertices, weights, smooth)
        notched = notch_crossings(skeleton, result, seated, vertices, weights)
        if notched is not None:
            candidates.append((notched,) + clip_motion(skeleton, notched, vertices, weights))
    calm = [item for item in candidates if item[2] <= fastest]
    if calm:
        return max(calm, key=lambda item: item[1])[0]
    if candidates:
        return min(candidates, key=lambda item: item[2])[0]
    result = damp_into_table(skeleton, local, seated, vertices, weights)
    for share in CLIP_MOTION_SHARES:
        if crossing_share(skeleton, result, vertices, weights) <= MAX_CROSSING_SHARE:
            break
        calmer = mix_with_seat(local, seated, np.full(local[0][0].shape[0], share))
        result = damp_into_table(skeleton, calmer, seated, vertices, weights)
    return result


# Let a clip that is too fast move less as a whole, as long as it stays out of the furniture.
def calm_clip(skeleton, local, start, vertices, weights, height, seconds_per_frame):
    limit = MAX_CLIP_SPEED * height * seconds_per_frame
    if clip_motion(skeleton, local, vertices, weights)[1] <= limit:
        return local
    count = local[0][0].shape[0]
    allowed = max(CROSSING_DEPTH, float(fine_depths(skeleton, local, vertices, weights).max()))
    for share in CALM_SHARES:
        trial = mix_with_seat(local, start, np.full(count, share))
        if float(fine_depths(skeleton, trial, vertices, weights).max()) > allowed:
            continue
        local = trial
        if clip_motion(skeleton, local, vertices, weights)[1] <= limit:
            break
    return local


# Return a clip that plays only the spine and the head of a played clip on the pose it starts from.
def spine_only(skeleton, start, played, count, spine, head):
    local = hold(start, count)
    for bone in spine + ([head] if head else []):
        index = skeleton.idx[bone]
        local[index] = (local[index][0], played[index][1].copy(), local[index][2])
    return local


# Turn a posed body around the vertical through the floor origin.
def turn_body(skeleton, local, degrees):
    amount = np.full(1, math.radians(degrees))
    quaternion = feet.rv2q(np.array([[0.0, 0.0, 1.0]]) * amount[:, None])
    matrix = feet.q2m(quaternion)
    for index in skeleton.topo:
        if skeleton.parent[index] < 0:
            position, rotation, scale = local[index]
            local[index] = (np.einsum('nij,nj->ni', matrix, position), feet.qmul(quaternion, rotation), scale)


# Return the bones of the arms of a humanoid and what they hold.
def arm_bones(skeleton, body_rig):
    bones = set()
    if isinstance(body_rig, list):
        for item in body_rig:
            for chain in list(item.get('hang', [])) + ([item['press']] if item.get('press') else []):
                bones.update(skeleton.idx[bone] for bone in chain if bone in skeleton.idx)
    for index in skeleton.topo:
        if skeleton.parent[index] in bones:
            bones.add(index)
    return bones


# Return the bones of the wings of a body: they stay folded while it sits.
def wing_bones(skeleton, body_rig):
    bones = set()
    for item in body_rig:
        bones.update(skeleton.idx[bone] for bone in item.get('wings', []) if bone in skeleton.idx)
    for index in skeleton.topo:
        if skeleton.parent[index] in bones:
            bones.add(index)
    return bones


# Return the bones of the tails of a body and what hangs on them.
def tail_bones(skeleton, body_rig):
    bones = set()
    if isinstance(body_rig, list):
        for item in body_rig:
            for chain in item.get('tail', []):
                bones.update(skeleton.idx[bone] for bone in chain if bone in skeleton.idx)
    for index in skeleton.topo:
        if skeleton.parent[index] in bones:
            bones.add(index)
    return bones


# Return the bones that do not carry a body on the bench: its tail and, for a body that walks on its arms, these arms.
def free_bones(skeleton, body_rig):
    bones = tail_bones(skeleton, body_rig)
    if isinstance(body_rig, list):
        for item in body_rig:
            if item['kind'] == 'torso':
                for chain in list(item.get('hang', [])) + list(item.get('hurt', [])):
                    bones.update(skeleton.idx[bone] for bone in chain if bone in skeleton.idx)
    for index in skeleton.topo:
        if skeleton.parent[index] in bones:
            bones.add(index)
    return bones


# Let an arm that rests in the table (a long arm, a long weapon) hang as it does when the creature stands idle, raised at
# the shoulder until it and what it holds stay out of the table and the floor. An arm that cannot do better stays as it was.
def relax_arms(skeleton, local, base, body_rig, vertices, weights, floor):
    if not isinstance(body_rig, list):
        return
    for item in body_rig:
        for chain in list(item.get('hang', [])) + ([item['press']] if item.get('press') else []):
            bones = {skeleton.idx[bone] for bone in chain if bone in skeleton.idx}
            for index in skeleton.topo:
                if skeleton.parent[index] in bones:
                    bones.add(index)
            held = [index for index, row in enumerate(weights) if sum(weight for bone, weight in row if bone in bones) >= 0.5]
            if not held:
                continue
            points = rest.skin_vertices(skeleton, local, vertices, weights)
            best_depth = float(worst_depths(points[:, held]).max())
            if best_depth <= TABLE_TOLERANCE:
                continue
            best_low = max(0.0, floor - float(points[0, held, 2].min()) - FLOOR_TOLERANCE)
            best = None
            for degrees in RELAXED_ARM_ANGLES:
                trial = hold_copy(local)
                for index in bones:
                    trial[index] = (trial[index][0], base[index][1].copy(), trial[index][2])
                if degrees > 0.0:
                    rest.rotate_joint(skeleton, trial, chain[0], rig.X_AXIS, np.radians(np.full(1, -degrees)))
                points = rest.skin_vertices(skeleton, trial, vertices, weights)
                depth = float(worst_depths(points[:, held]).max())
                low = max(0.0, floor - float(points[0, held, 2].min()) - FLOOR_TOLERANCE)
                if depth + low < best_depth + best_low - 1e-4:
                    best, best_depth, best_low = trial, depth, low
                if depth <= TABLE_TOLERANCE and low <= 0.0:
                    break
            if best is not None:
                for index, entry in enumerate(best):
                    local[index] = entry


# Raise an arm that passes through the table during a clip at its shoulder, as far as that helps.
def lift_arms_over_table(skeleton, local, times, length, body_rig, vertices, weights):
    if not isinstance(body_rig, list):
        return
    envelope = ends(times, length)
    for item in body_rig:
        for chain in list(item.get('hang', [])) + ([item['press']] if item.get('press') else []):
            bones = {skeleton.idx[bone] for bone in chain if bone in skeleton.idx}
            for index in skeleton.topo:
                if skeleton.parent[index] in bones:
                    bones.add(index)
            held = [index for index, row in enumerate(weights) if sum(weight for bone, weight in row if bone in bones) >= 0.5]
            if not held or chain[0] not in skeleton.idx:
                continue
            best = None
            best_depth = table_depth(rest.skin_vertices(skeleton, local, vertices, weights), held)
            degrees = ARM_LIFT_STEP
            while best_depth > TABLE_TOLERANCE / SCENE['size'] and degrees <= ARM_LIFT_MAX:
                trial = hold_copy(local)
                rest.rotate_joint(skeleton, trial, chain[0], rig.X_AXIS, np.radians(-degrees) * envelope)
                depth = table_depth(rest.skin_vertices(skeleton, trial, vertices, weights), held)
                if depth < best_depth - 1e-4:
                    best = trial
                    best_depth = depth
                degrees += ARM_LIFT_STEP
            if best is not None:
                for index, entry in enumerate(best):
                    local[index] = entry


# Lean the upper body back during a clip until it stays out of the table, as far as that is possible.
def lean_out_of_table(skeleton, local, times, length, spine, head, vertices, weights):
    bone = spine[0] if spine else head
    if bone is None:
        return
    envelope = ends(times, length)
    best = local
    best_depth = table_depth(rest.skin_vertices(skeleton, local, vertices, weights))
    degrees = LEAN_BACK_STEP
    while best_depth > TABLE_TOLERANCE / SCENE['size'] and degrees <= LEAN_BACK_MAX:
        trial = hold_copy(local)
        rest.rotate_joint(skeleton, trial, bone, rig.X_AXIS, np.radians(-degrees) * envelope)
        depth = table_depth(rest.skin_vertices(skeleton, trial, vertices, weights))
        if depth < best_depth - 1e-4:
            best = trial
            best_depth = depth
        degrees += LEAN_BACK_STEP
    for index, entry in enumerate(best):
        local[index] = entry


# Lean the upper body of a seat pose back as far as that takes it out of the table.
def straighten_seat(skeleton, local, spine, head, vertices, weights):
    bone = spine[0] if spine else head
    if bone is None:
        return
    best = local
    best_depth = worst_depths(rest.skin_vertices(skeleton, local, vertices, weights)).max()
    degrees = LEAN_BACK_STEP
    while best_depth > TABLE_TOLERANCE and degrees <= LEAN_BACK_MAX:
        trial = hold_copy(local)
        rest.rotate_joint(skeleton, trial, bone, rig.X_AXIS, np.radians(np.full(1, -degrees)))
        depth = worst_depths(rest.skin_vertices(skeleton, trial, vertices, weights)).max()
        if depth < best_depth - 1e-4:
            best = trial
            best_depth = depth
        degrees += LEAN_BACK_STEP
    for index, entry in enumerate(best):
        local[index] = entry


# Return a copy of a clip.
def hold_copy(local):
    return [(p.copy(), q.copy(), s.copy()) for p, q, s in local]


# Return the vertices whose weight lies mostly outside the given bones.
def vertices_without(weights, bones):
    return [index for index, row in enumerate(weights)
            if sum(weight for bone, weight in row if bone in bones) < 0.5]


# Pose the guest on the bench for one candidate of foot placement; returns the hold pose and the support height.
def seat_candidate(skeleton, body_rig, base, height, name, vertices, weights, chains, forward, raised=0.0, spread=0.0):
    amount = np.ones(1)
    world = skeleton.fk(base)
    thighs = thigh_chains(skeleton, chains, body_rig)
    hip, thigh = hip_measure(skeleton, thighs, world)
    wanted = (BENCH_TOP + raised) / SCENE['size'] + HIP_ABOVE_SEAT * thigh
    drop = hip - wanted
    lift = max(0.0, MIN_KNEE_BEND * thigh - drop)
    for attempt in range(8):
        try:
            local, error = rest.sitting(skeleton, body_rig, base, amount, height, name, vertices, weights,
                                        seat={'drop': drop, 'lift': lift, 'forward': forward, 'spread': spread})
            break
        except AssertionError:
            # The feet cannot reach their place: they hang a bit higher
            lift += 0.02 * height
    else:
        raise AssertionError((name, 'no seated leg solution'))
    posed = skeleton.fk(local)
    offset = np.zeros((1, 3))
    centre = np.mean([posed[skeleton.idx[chain[0]]][0][0, 1] for chain in thighs])
    offset[0, 1] = -centre
    rest.move_roots(skeleton, local, offset)
    points = rest.skin_vertices(skeleton, local, vertices, weights)
    return local, max(0.0, float(points[0, :, 2].min())), 'seated'


# Lift a body onto the seat of the bench: the lowest part above the seat rests on it, what hangs beside the seat may go lower.
def lift_onto_bench(skeleton, local, vertices, weights):
    half, near, far = BENCH[:3]
    scene = SCENE['size']
    # The same clip plays on both seats of a bench
    reach = half if SCENE['whole_bench'] else half + SEAT_SIDE
    for _ in range(4):
        points = rest.skin_vertices(skeleton, local, vertices, weights)[0] * scene
        over = (np.abs(points[:, 0]) < reach) & (points[:, 1] > near) & (points[:, 1] < far)
        if not over.any():
            return False
        offset = np.zeros((1, 3))
        offset[0, 2] = (BENCH_TOP - float(points[over, 2].min())) / scene
        rest.move_roots(skeleton, local, offset)
        if abs(offset[0, 2]) < 1e-4:
            break
    return True


# Roll up the tail of a resting body joint by joint, around the vertical of the body.
def coil_tail(skeleton, local, body_rig, degrees):
    if not isinstance(body_rig, list):
        return
    for item in body_rig:
        for chain in item.get('tail', []):
            for bone in chain:
                if bone in skeleton.idx:
                    rest.rotate_joint(skeleton, local, bone, rig.Z_AXIS, np.radians(np.full(1, degrees)))


# Return the pose in which a body rests on the bench at full size, in the pose it rests in on the ground: turned along the
# bench when that stays out of the table, and moved back as little as that takes.
def resting_pose(skeleton, body_rig, name, vertices, weights):
    best = None
    for source_name in REST_SOURCES.get(name, DEFAULT_REST_SOURCES):
        played = skeleton.clips[source_name]
        source = skeleton.locals_at(played, np.array([played.length * 0.5]))
        for turn in REST_TURN_LIMITS.get(name, REST_TURNS):
            head = upper_chain(skeleton, body_rig, [])[1]
            turn_best = None
            # The tail curls to the side that needs the smaller step back
            curl = COIL_TAIL_DEGREES if name in COILED_MODELS else CURL_TAIL_DEGREES
            heads = REST_HEAD_TURNS if head and abs(turn) == 90.0 else (0.0,)
            for head_turn, tail_turn in [(first, second) for first in heads for second in (curl, -curl)]:
                local = hold_copy(source)
                coil_tail(skeleton, local, body_rig, tail_turn)
                turn_body(skeleton, local, turn)
                if head_turn > 0.0:
                    rest.rotate_joint(skeleton, local, head, rig.Z_AXIS, np.radians(np.full(1, -math.copysign(head_turn, turn))))
                points = rest.skin_vertices(skeleton, local, vertices, weights)[0]
                offset = np.zeros((1, 3))
                offset[0, 0] = -0.5 * float(points[:, 0].min() + points[:, 0].max())
                offset[0, 1] = -0.5 * float(np.percentile(points[:, 1], 10) + np.percentile(points[:, 1], 90))
                rest.move_roots(skeleton, local, offset)
                back = 0.0
                trial = None
                while back <= REST_BACK_MAX:
                    trial = hold_copy(local)
                    offset = np.zeros((1, 3))
                    offset[0, 1] = back / SCENE['size']
                    rest.move_roots(skeleton, trial, offset)
                    if lift_onto_bench(skeleton, trial, vertices, weights):
                        depth = float(worst_depths(rest.skin_vertices(skeleton, trial, vertices, weights)).max())
                        sunk = float(rest.skin_vertices(skeleton, trial, vertices, weights)[0, :, 2].min()) * SCENE['size']
                        if depth <= REST_TOLERANCE and sunk >= -REST_FLOOR_SINK:
                            break
                    back += REST_BACK_STEP
                else:
                    continue
                if turn_best is None or back < turn_best[1] - REST_HEAD_ADVANTAGE:
                    turn_best = (trial, back, turn)
            # A later turn only wins with a clearly smaller step back
            if turn_best is not None and (best is None or turn_best[1] < best[1] - REST_TURN_ADVANTAGE):
                best = turn_best
    assert best is not None, (name, 'no resting pose on the bench')
    extra = REST_EXTRA_BACK.get(name, 0.0)
    if extra > 0.0:
        offset = np.zeros((1, 3))
        offset[0, 1] = extra / SCENE['size']
        rest.move_roots(skeleton, best[0], offset)
        lift_onto_bench(skeleton, best[0], vertices, weights)
    return best[0], best[1] + extra, best[2]


# Choose the pose of the guest on the bench at full size: it sits on its legs or rests on the bench.
def seat_pose(skeleton, body_rig, base, height, name, vertices, weights, chains):
    weapons = [] if name in RESTING_MODELS else long_weapons(skeleton, base, body_rig, vertices, weights)
    if name not in RESTING_MODELS:
        try:
            found = seat_pose_on_legs(skeleton, body_rig, base, height, name, vertices, weights, chains, weapons)
        except AssertionError:
            found = None
        if found is not None and found[2]['body_depth'] <= SEATED_LIMIT:
            return found + (weapons,)
    local, back, turn = resting_pose(skeleton, body_rig, name, vertices, weights)
    carrying = vertices_without(weights, free_bones(skeleton, body_rig))
    support = float(rest.skin_vertices(skeleton, local, vertices, weights)[0, carrying, 2].min())
    return local, support, {'mode': 'resting', 'foot_reach': 0.0, 'rear': 0.0, 'back_shift': back, 'turn': turn}, carrying, []


# Choose the seat pose of a body that sits on its legs.
def seat_pose_on_legs(skeleton, body_rig, base, height, name, vertices, weights, chains, weapons):
    carrying = vertices_without(weights, free_bones(skeleton, body_rig))
    without_arms = vertices_without(weights, arm_bones(skeleton, body_rig) | free_bones(skeleton, body_rig))
    # Everything but the arms decides the place of the feet, the height of the pelvis and how far the body moves back and turns
    best = None
    solved = {}
    spreads = SEAT_SPREADS if SCENE['whole_bench'] else SEAT_SIDE_SPREADS
    furthest = LARGE_BACK_SHIFTS.get(name, MAX_BACK_SHIFT)
    choices = [(turn, spread, raised, share) for turn in SEAT_TURNS for spread in spreads for raised in HIP_RAISES for share in FOOT_REACH]
    for turn, spread, raised, share in choices:
        key = (spread, raised, share)
        if key not in solved:
            try:
                local, support, mode = seat_candidate(skeleton, body_rig, base, height, name, vertices, weights, chains, height * share, raised, spread)
                solved[key] = (local, support, mode, rest.skin_vertices(skeleton, local, vertices, weights)[:, without_arms])
            except AssertionError:
                solved[key] = None
        if solved[key] is None:
            continue
        local, support, mode, points = solved[key]
        angle = math.radians(turn)
        turned = points.copy()
        turned[:, :, 0] = points[:, :, 0] * math.cos(angle) - points[:, :, 1] * math.sin(angle)
        turned[:, :, 1] = points[:, :, 0] * math.sin(angle) + points[:, :, 1] * math.cos(angle)
        for step in np.arange(0.0, furthest + 1e-6, SEAT_BACK_STEP):
            depth = float(worst_depths(turned + np.array([0.0, step / SCENE['size'], 0.0])).max())
            if best is None or depth < best[3] - SEAT_GAIN:
                best = (local, support, mode, depth, share, step / SCENE['size'], turn, raised, spread)
            if depth <= SEAT_TOLERANCE:
                break
        if best is not None and best[3] <= SEAT_TOLERANCE:
            break
    assert best is not None, (name, 'no seated leg solution')
    local, support, mode, depth, share, back, turn, raised, spread = best
    local = hold_copy(local)
    if turn > 0.0:
        turn_body(skeleton, local, turn)
        spine, head = upper_chain(skeleton, body_rig, chains)
        if head:
            rest.rotate_joint(skeleton, local, head, rig.Z_AXIS, np.radians(np.full(1, -turn)))
    if back > 0.0:
        offset = np.zeros((1, 3))
        offset[0, 1] = back
        rest.move_roots(skeleton, local, offset)
    floor = float(rest.skin_vertices(skeleton, base, vertices, weights)[0, :, 2].min())
    hold_weapons_upright(skeleton, local, weapons)
    relax_arms(skeleton, local, base, body_rig, vertices, weights, floor)
    hold_weapons_upright(skeleton, local, weapons)
    # A hunched body straightens up on the bench to stay out of the table; its arms follow it
    spine, head = upper_chain(skeleton, body_rig, chains)
    straighten_seat(skeleton, local, spine, head, vertices, weights)
    relax_arms(skeleton, local, base, body_rig, vertices, weights, floor)
    hold_weapons_upright(skeleton, local, weapons)
    return local, support, {'mode': mode, 'foot_reach': share, 'rear': 0.0, 'back_shift': back * SCENE['size'], 'turn': turn, 'raised': raised,
                            'spread': spread, 'body_depth': depth}, carrying


# Repeat a hold pose for the frames of a clip.
def hold(local, count):
    return [(np.tile(p, (count, 1)), np.tile(q, (count, 1)), np.tile(s, (count, 1))) for p, q, s in local]


# Return the conjugates of an array of quaternions.
def conjugate(quaternions):
    return quaternions * np.array([1.0, -1.0, -1.0, -1.0])


# Interpolate along the shorter arc of two quaternion arrays with the weights per frame.
def slerp(first, second, weights):
    dot = np.einsum('ni,ni->n', first, second)
    second = np.where(dot[:, None] < 0.0, -second, second)
    delta = feet.qmul(conjugate(first), second)
    w = np.clip(delta[:, 0], -1.0, 1.0)
    angle = 2.0 * np.arccos(w)
    sine = np.sqrt(np.maximum(1e-16, 1.0 - w * w))
    vector = delta[:, 1:] / sine[:, None] * angle[:, None]
    return feet.qnorm(feet.qmul(first, feet.rv2q(vector * weights[:, None])))


# Return the weight per frame that is 0 at both ends of a clip and 1 in between.
def ends(times, length):
    progress = times / length
    rising = np.clip(progress / BLEND_SHARE, 0.0, 1.0)
    falling = np.clip((1.0 - progress) / BLEND_SHARE, 0.0, 1.0)
    return rising * rising * (3.0 - 2.0 * rising) * falling * falling * (3.0 - 2.0 * falling)


# Play a standing clip on the upper body of a seated humanoid; the legs and the pelvis stay on the bench.
def upper_body_clip(skeleton, seated, base, source, times, length, fixed):
    count = len(times)
    played = skeleton.locals_at(source, times * (source.length / length))
    weights = ends(times, length)
    local = hold(seated, count)
    inherited = {}
    for index in skeleton.topo:
        parent = skeleton.parent[index]
        idle = base[index][1][:1].repeat(count, axis=0)
        own = feet.qmul(conjugate(idle), played[index][1])
        if parent in inherited:
            own = feet.qmul(feet.qmul(conjugate(idle), feet.qmul(inherited[parent], idle)), own)
        if index in fixed:
            inherited[index] = own
            continue
        target = feet.qmul(idle, own)
        local[index] = (local[index][0], slerp(local[index][1], target, weights), local[index][2])
    return local


# Add the motion of a standing clip to a seated body of any other build, joint by joint; the support is kept afterwards.
def whole_body_clip(skeleton, seated, base, source, times, length):
    count = len(times)
    played = skeleton.locals_at(source, times * (source.length / length))
    weights = ends(times, length)
    local = hold(seated, count)
    for index in skeleton.topo:
        idle_rotation = base[index][1][:1].repeat(count, axis=0)
        own = feet.qmul(conjugate(idle_rotation), played[index][1])
        unit = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (count, 1))
        rotation = feet.qmul(local[index][1], slerp(unit, own, weights))
        moved = local[index][0]
        if skeleton.parent[index] >= 0:
            moved = moved + (played[index][0] - base[index][0][:1]) * weights[:, None]
        local[index] = (moved, rotation, local[index][2])
    return local


# Return the bones that carry the upper body (spine first, head last) and the head alone.
def upper_chain(skeleton, body_rig, chains):
    spine = []
    head = None
    if isinstance(body_rig, list):
        for item in body_rig:
            spine.extend(bone for bone in item.get('spine', []) if bone is not None)
            head = head or item.get('head')
    spine = [bone for bone in dict.fromkeys(spine) if bone in skeleton.idx and bone != head]
    if head is not None and head not in skeleton.idx:
        head = None
    if not spine and head is None:
        spine = [skeleton.names[index] for index in skeleton.topo if skeleton.parent[index] < 0][:1]
    return spine, head


# Turn the upper body as a reaction to a slap: it swings away, comes back and settles.
def slapped_clip(skeleton, seated, times, length, spine, head, share_of_slap):
    count = len(times)
    local = hold(seated, count)
    progress = times / length
    decay = share_of_slap * np.exp(-3.5 * progress) * np.sin(2.0 * math.pi * SLAP_OSCILLATIONS * progress) * (1.0 - progress)
    tilt = share_of_slap * np.exp(-4.0 * progress) * np.sin(math.pi * np.minimum(1.0, progress * 3.0)) * (1.0 - progress)
    bones = spine + ([head] if head else [])
    for bone in bones:
        share = 1.0 / len(bones)
        rest.rotate_joint(skeleton, local, bone, rig.Z_AXIS, np.radians(SLAP_TURN * share * decay))
        rest.rotate_joint(skeleton, local, bone, rig.X_AXIS, np.radians(-SLAP_TILT * share * tilt))
    return local


# Sink the upper body forward and let it rest there, with a slow breath; a bow that would enter the table is reduced.
def slumped_clip(skeleton, seated, times, length, spine, head, vertices, weights, limit, settle):
    count = len(times)
    amount = np.full(count, 1.0)
    for scale in (1.0, 0.8, 0.6, 0.45, 0.3, 0.2, 0.1, 0.05, 0.0):
        local = hold(seated, count)
        for bone in spine:
            bow = min(SLUMP_BOW * scale, limit)
            rest.rotate_joint(skeleton, local, bone, rig.X_AXIS, np.radians(bow * amount / max(1, len(spine))))
        if head:
            rest.rotate_joint(skeleton, local, head, rig.X_AXIS, np.radians(SLUMP_HEAD * scale * amount))
        settle(local)
        posed = rest.skin_vertices(skeleton, [(p[:1], q[:1], s[:1]) for p, q, s in local], vertices, weights)
        if worst_depths(posed).max() <= TABLE_TOLERANCE:
            break
    return local


# Turn a bone so that the vector from it to one of its children points along the given direction in every frame.
def aim_bone(skeleton, local, bone, child, direction):
    world = skeleton.fk(local)
    current = world[skeleton.idx[child]][0] - world[skeleton.idx[bone]][0]
    current /= np.linalg.norm(current, axis=1)[:, None]
    direction = direction / np.linalg.norm(direction, axis=1)[:, None]
    axis = np.cross(current, direction)
    length = np.linalg.norm(axis, axis=1)
    angle = np.arctan2(length, np.einsum('ni,ni->n', current, direction))
    axis = np.where(length[:, None] > 1e-9, axis / np.maximum(length, 1e-9)[:, None], np.array([[0.0, 0.0, 1.0]]))
    rest.rotate_joint(skeleton, local, bone, axis, angle)


# Return the yaw and the pitch in degrees of a vector, seen from a body that looks along -y with its side at +x or -x.
def yaw_pitch(vector, side):
    return (math.degrees(math.atan2(-vector[1], side * vector[0])), math.degrees(math.asin(vector[2] / np.linalg.norm(vector))))


# Let the arms hammer on the table in turns. The hand rises before it moves forward and moves back before it comes down, so
# that it does not cross the table on its way from and to the hanging arm.
def hammer_arms(skeleton, local, seated, times, length, hammer):
    progress = times / length
    fade = ends(times, length)
    lagging = fade ** 3
    world = skeleton.fk(seated)
    for upper, forearm, hand, phase in hammer['arms']:
        start = [world[skeleton.idx[bone]][0][0] for bone in (upper, forearm, hand)]
        side = 1.0 if start[1][0] >= start[0][0] else -1.0
        hanging = (yaw_pitch(start[1] - start[0], side), yaw_pitch(start[2] - start[1], side))
        swing = 0.5 + 0.5 * np.sin(2.0 * math.pi * hammer['cycles'] * progress + phase - 0.5 * math.pi)
        directions = []
        for hang, raised, slammed in zip(hanging, hammer['raised'], hammer['slammed']):
            yaw = hang[0] + (raised[0] + (slammed[0] - raised[0]) * swing - hang[0]) * lagging
            pitch = hang[1] + (raised[1] + (slammed[1] - raised[1]) * swing - hang[1]) * fade
            yaw, pitch = np.radians(yaw), np.radians(pitch)
            directions.append(np.stack([side * np.cos(pitch) * np.cos(yaw), -np.cos(pitch) * np.sin(yaw), np.sin(pitch)], axis=1))
        aim_bone(skeleton, local, upper, forearm, directions[0])
        aim_bone(skeleton, local, forearm, hand, directions[1])


# Solve a chain of joints without stretching; stop converged iterations and directly handle targets beyond full reach.
def reach_chain(joints, target, rounds=80):
    """Keep the root and segment lengths while reaching the target, including the straight unreachable case."""
    lengths = [float(np.linalg.norm(joints[index + 1] - joints[index])) for index in range(len(joints) - 1)]
    points = [joint.copy() for joint in joints]
    root = points[0].copy()
    distance = float(np.linalg.norm(target - root))
    if distance >= sum(lengths) and distance > 1e-12:
        direction = (target - root) / distance
        for index, length in enumerate(lengths):
            points[index + 1] = points[index] + direction * length
        return points
    for _ in range(rounds):
        points[-1] = target.copy()
        for index in range(len(points) - 2, -1, -1):
            step = points[index] - points[index + 1]
            points[index] = points[index + 1] + step / np.linalg.norm(step) * lengths[index]
        points[0] = root.copy()
        for index in range(1, len(points)):
            step = points[index] - points[index - 1]
            points[index] = points[index - 1] + step / np.linalg.norm(step) * lengths[index - 1]
        if np.linalg.norm(points[-1] - target) <= 1e-10:
            break
    return points


# Return how close the rim of the mug comes to the mouth in a clip of a body that drinks on a limb, in tiles.
def mug_rim_distance(skeleton, clip, mug):
    played = skeleton.clips[clip]
    world = skeleton.fk(skeleton.locals_at(played, np.linspace(0.0, played.length, TABLE_SAMPLES_COARSE)))
    holder = world[skeleton.idx[MUG_BONE]]
    rim = holder[0] - (MUG_HEIGHT - MUG_GRIP_SHIFT) * holder[1][:, :, 0] * holder[2][:, :1]
    head = world[skeleton.idx[mug['head']]]
    mouth = head[0] + np.einsum('nij,j->ni', head[1], np.array(mug['mouth']))
    return float(np.linalg.norm(rim - mouth, axis=1).min())


# Bring the mug of a limb to the mouth and back, as often as the clip drinks: the limb goes from the seat pose to the pose that
# holds the foot of the mug in front of the mouth, and the mug tips from upright until its rim lies at the mouth.
def drink_with_limb(skeleton, local, seated, times, length, mug):
    chain = mug['chain']
    world = skeleton.fk(seated)
    head, rotation = world[skeleton.idx[mug['head']]][0][0], world[skeleton.idx[mug['head']]][1][0]
    mouth = head + rotation @ np.array(mug['mouth'])
    foot = mouth + np.array(mug['foot'])
    joints = [world[skeleton.idx[bone]][0][0] for bone in chain]
    tipped = (mouth - foot) / np.linalg.norm(mouth - foot)
    progress = times / length
    lift = np.clip(1.6 * (0.5 - 0.5 * np.cos(2.0 * math.pi * mug['drinks'] * progress)), 0.0, 1.0)
    share = (lift * lift * (3.0 - 2.0 * lift) * ends(times, length))[:, None]
    # The foot of the mug goes from where the limb hangs to the mouth over an arc that rises. The limb is solved along that way
    # in small steps, each from the pose of the one before, so that it does not jump; a frame takes the pose of its share of the
    # way, so that the first and the last frame show the seat pose and the way back is the way there.
    way = np.linspace(0.0, 1.0, MUG_WAY_STEPS)
    poses = [joints]
    for place in way[1:]:
        poses.append(reach_chain(poses[-1], joints[-1] + (foot - joints[-1]) * place + np.array([0.0, 0.0, mug['arc']]) * (4.0 * place * (1.0 - place))))
    steps = []
    for index in range(len(chain) - 1):
        vectors = np.array([pose[index + 1] - pose[index] for pose in poses])
        along = np.stack([np.interp(share[:, 0], way, vectors[:, axis]) for axis in range(3)], axis=1)
        steps.append(along / np.linalg.norm(along, axis=1)[:, None])
    for index in range(len(chain) - 1):
        aim_bone(skeleton, local, chain[index], chain[index + 1], steps[index])
    upright = np.array([0.0, 0.0, 1.0])
    wanted = upright + (tipped - upright) * share
    wanted /= np.linalg.norm(wanted, axis=1)[:, None]
    # The mug stands along the -x axis of its bone
    current = -skeleton.fk(local)[skeleton.idx[MUG_BONE]][1][:, :, 0]
    axis = np.cross(current, wanted)
    size = np.linalg.norm(axis, axis=1)
    angle = np.arctan2(size, np.einsum('ni,ni->n', current, wanted))
    axis = np.where(size[:, None] > 1e-9, axis / np.maximum(size, 1e-9)[:, None], np.array([[0.0, 0.0, 1.0]]))
    rest.rotate_joint(skeleton, local, chain[-1], axis, angle)


# Return the clip a body plays on its own bones in place of its source clip, or None.
def playful_clip(skeleton, seated, times, length, name, clip):
    swings = PLAY_SWINGS.get((name, clip))
    mug = PLAY_MUGS.get((name, clip))
    if swings is None and mug is None:
        return None
    swings = swings or ()
    progress = times / length
    fade = ends(times, length)
    local = hold(seated, len(times))
    for bone, axis, degrees, cycles, phase, mean in swings:
        angle = fade * np.radians(mean + degrees * np.sin(2.0 * math.pi * cycles * progress + phase))
        rest.rotate_joint(skeleton, local, bone, PLAY_AXES[axis], angle)
    if (name, clip) in PLAY_HAMMERS:
        hammer_arms(skeleton, local, seated, times, length, PLAY_HAMMERS[(name, clip)])
    if mug is not None:
        drink_with_limb(skeleton, local, seated, times, length, mug)
    return local


# Add the breath and a small movement of the head to a clip that holds the seat pose.
def alive(skeleton, local, body_rig, name, times, head, amount=1.0):
    breath = amount * BREATH * np.sin(times * (2.0 * math.pi / BREATH_SECONDS))
    rest.breathe(skeleton, local, body_rig, breath, name)
    if head:
        sway = amount * np.radians(SWAY_DEGREES) * np.sin(times * (2.0 * math.pi / BREATH_SECONDS))
        rest.rotate_joint(skeleton, local, head, rig.Z_AXIS, sway)


# Keep a body on what carries it in every frame, without moving the frames that are clear.
def keep_on_support(skeleton, local, vertices, weights, support, carrying):
    points = rest.skin_vertices(skeleton, local, vertices, weights)
    offset = np.zeros((points.shape[0], 3))
    offset[:, 2] = np.maximum(0.0, support - points[:, carrying, 2].min(axis=1))
    if offset.max() > 0.0:
        rest.move_roots(skeleton, local, offset)


# Return the vertices and weights of a body with the mug it drinks from in its right hand, or as they are without that hand.
def with_mug(skeleton, vertices, weights, mesh):
    if MUG_BONE not in skeleton.idx:
        return vertices, weights
    path = mesh.parent / (MUG_MESH + '.xml')
    # The outline of a mug is enough for a collision and its full mesh slows every measure down
    mug = rest.mesh_data(path)[0]
    mug = mug[::max(1, len(mug) // MUG_POINTS)]
    bone = skeleton.idx[MUG_BONE]
    bind = skeleton.fk([(skeleton.rest_pos[index][None], skeleton.rest_q[index][None], skeleton.rest_s[index][None])
                        for index in range(len(skeleton.names))])[bone]
    # The mesh of an attached item is turned from the upright of its file to the axes of the bone; the mug is wide and held at
    # its middle as the render manager attaches it
    turned = (mug * np.array([1.0, MUG_GIRTH, MUG_GIRTH])) @ MUG_TURN.T + np.array([MUG_GRIP_SHIFT, 0.0, 0.0])
    placed = (turned * bind[2][0]) @ bind[1][0].T + bind[0][0]
    return np.concatenate((np.asarray(vertices), placed)), list(weights) + [[(bone, 1.0)] for _ in range(len(placed))]


# Serialize a clip; a bone that does not move in the clip gets two keys instead of all of them.
def clip_xml(skeleton, local, times, name, length):
    lines = ['<animation name="' + name + '" length="' + str(float(length)) + '"><tracks>']
    last = len(times) - 1
    for index, bone in enumerate(skeleton.names):
        position, rotation, scale = local[index]
        translation = position - skeleton.rest_pos[index]
        key_rotation = feet.qmul(np.tile(feet.qconj(skeleton.rest_q[index]), (len(times), 1)), rotation)
        key_scale = scale / skeleton.rest_s[index]
        moving = (np.abs(translation - translation[:1]).max() > 1e-6 or
                  np.abs(np.abs(np.einsum('ni,i->n', key_rotation, key_rotation[0])) - 1.0).max() > 1e-7 or
                  np.abs(key_scale - key_scale[:1]).max() > 1e-6)
        frames = range(len(times)) if moving else (0, last)
        lines.append('<track bone="' + bone + '"><keyframes>')
        for frame in frames:
            lines.append(feet.key_xml(times[frame], translation[frame], key_rotation[frame], key_scale[frame], True))
        lines.append('</keyframes></track>')
    lines.append('</tracks></animation>')
    return '\n'.join(lines)


# Author all seven clips of one model and return the measured report.
def author(source, mesh, destination):
    skeleton = feet.Skel(str(source))
    name = source.name.removesuffix('.skeleton.xml')
    body_rig = rig.config(name, rig.Skeleton(str(source)))
    vertices, faces, weights = rest.mesh_data(mesh)
    if isinstance(body_rig, list):
        weighted = {bone for row in weights for bone, weight in row if weight > 0.0}
        body_rig = [item for item in body_rig if rest.rig_visible(skeleton, item, weighted)]
    base = skeleton.locals_at(skeleton.clips['Idle'], np.zeros(1))
    points = rest.skin_vertices(skeleton, base, vertices, weights)
    floor = float(points[0, :, 2].min())
    height = float(np.ptp(points[0, :, 2]))
    chains = leg_chains(skeleton, name, vertices, weights, base)
    humanoid = is_humanoid(body_rig)
    SCENE['whole_bench'] = name in LARGE_MODELS
    SCENE['size'] = LEVEL_SCALE_MIDDLE
    seated, support, info, carrying, weapons = seat_pose(skeleton, body_rig, base, height, name, vertices, weights, chains)
    info['long_weapons'] = [hand for hand, _ in weapons]
    upper_only = humanoid or (isinstance(body_rig, list) and all(item['kind'] == 'torso' for item in body_rig))
    fixed = fixed_bones(skeleton, chains) if upper_only else set()
    if upper_only:
        fixed |= wing_bones(skeleton, body_rig)
    spine, head = upper_chain(skeleton, body_rig, chains)
    report = {'model': name, 'height': height, 'floor': floor, 'support': support, 'humanoid': humanoid, **info, 'clips': {}}
    blocks = []

    # Keeps a body that is not seated on its legs on what carries it
    def settle(local):
        if not humanoid:
            keep_on_support(skeleton, local, vertices, weights, support, carrying)

    body_vertices_only, body_weights_only = vertices, weights
    for clip, length, keys, source_clip, looped in CLIPS:
        vertices, weights = with_mug(skeleton, body_vertices_only, body_weights_only, mesh) if clip == 'SitDrink' else (body_vertices_only, body_weights_only)
        played = skeleton.clips[source_clip] if source_clip else None
        if length is None:
            length = float(played.length)
        times = np.linspace(0.0, length, keys)
        # The arm with the mug starts a little higher than in the seat pose where the mug would reach into the table
        start = seated
        if clip == 'SitDrink':
            start = hold_copy(seated)
            relax_arms(skeleton, start, base, body_rig, vertices, weights, floor)
        played_own = playful_clip(skeleton, start, times, length, name, clip) if source_clip else None
        if played_own is not None:
            local = played_own
        elif source_clip and upper_only:
            local = upper_body_clip(skeleton, start, base, played, times, length, fixed)
        elif source_clip:
            local = whole_body_clip(skeleton, start, base, played, times, length)
        elif clip == 'SitSlapped':
            local = slapped_clip(skeleton, seated, times, length, spine, head, RESTING_SLAP_SHARE if info['mode'] == 'resting' else 1.0)
        elif clip == 'SitSlumped':
            limit = SLUMP_BOW if isinstance(body_rig, list) and any(item.get('spine') for item in body_rig) else info['rear']
            local = slumped_clip(skeleton, seated, times, length, spine, head, vertices, weights, limit, settle)
            alive(skeleton, local, body_rig, name, times, None, 0.6)
        else:
            local = hold(seated, keys)
            alive(skeleton, local, body_rig, name, times, head)
        hold_weapons_upright(skeleton, local, weapons)
        unrouted = hold_copy(local)
        if source_clip and played_own is None:
            lift_arms_over_table(skeleton, local, times, length, body_rig, vertices, weights)
        if (source_clip and played_own is None) or clip == 'SitSlapped':
            lean_out_of_table(skeleton, local, times, length, spine, head, vertices, weights)
        hold_weapons_upright(skeleton, local, weapons)
        settle(local)
        if (source_clip and played_own is None) or clip == 'SitSlapped':
            for _ in range(ROUTE_PASSES):
                local = route_arms_over_table(skeleton, local, body_rig, vertices, weights)
                hold_weapons_upright(skeleton, local, weapons)
        free_motion = clip_motion(skeleton, local, vertices, weights)[0]
        local = keep_out_of_table(skeleton, local, start, vertices, weights, height, length / (keys - 1))
        if source_clip and played_own is None and clip_motion(skeleton, local, vertices, weights)[0] < LOW_MOTION_SHARE * free_motion:
            calmer = spine_only(skeleton, start, unrouted, keys, spine, head)
            calmer = keep_out_of_table(skeleton, calmer, start, vertices, weights, height, length / (keys - 1))
            if clip_motion(skeleton, calmer, vertices, weights)[0] > clip_motion(skeleton, local, vertices, weights)[0]:
                local = calmer
        local = calm_clip(skeleton, local, start, vertices, weights, height, length / (keys - 1))
        # An arm that stays far too fast around the table rests and leaves the clip to the spine and the head
        if source_clip and played_own is None and clip_motion(skeleton, local, vertices, weights)[1] > 2.0 * MAX_CLIP_SPEED * height * length / (keys - 1):
            local = keep_out_of_table(skeleton, spine_only(skeleton, start, unrouted, keys, spine, head), start, vertices, weights,
                                      height, length / (keys - 1))
        settle(local)
        posed = rest.skin_vertices(skeleton, local, vertices, weights)
        report['clips'][clip] = {
            'length': length,
            'table_depth': level_depth(posed),
            'lowest': float(posed[:, carrying, 2].min()),
            'highest': float(posed[:, :, 2].max()),
            'end_error': float(np.abs(posed[0] - posed[-1]).max() / height),
            'motion': float(np.linalg.norm(posed - posed[:1], axis=2).max() / height),
            'free_motion': float(free_motion / height),
            'step': float(np.linalg.norm(np.diff(posed, axis=0), axis=2).max() / height)}
        blocks.append(clip_xml(skeleton, local, times, clip, length))
    text = source.read_text(encoding='utf-8')
    head_part = text[:text.index('<animations>')]
    destination.write_text(head_part + '<animations>\n' + '\n'.join(blocks) + '\n</animations>\n</skeleton>\n', encoding='utf-8')
    return report


# Author the requested models and write their report.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('names', nargs='+')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for name in args.names:
        mesh_name = 'TentacleGreen' if name == 'Tentacle' else name
        report = author(args.input / (name + '.skeleton.xml'), args.input / (mesh_name + '.mesh.xml'),
                        args.output / (name + '.seats.skeleton.xml'))
        (args.output / (name + '.seats.json')).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
        print(name, report['mode'], 'support', round(report['support'], 3), 'reach', report['foot_reach'],
              'back', round(report['back_shift'], 3), 'turn', report['turn'], 'weapons', report['long_weapons'], 'depth',
              {clip: round(values['table_depth'], 3) for clip, values in report['clips'].items()}, flush=True)


if __name__ == '__main__':
    main()
