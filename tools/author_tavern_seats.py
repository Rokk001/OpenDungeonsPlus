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
# The guest stands on the middle of the bench and looks along -y. Where the top of the table starts from there.
TABLE_NEAR_EDGE = -0.0882
TABLE_UNDERSIDE = 0.351
TABLE_TOP = 0.4425
# Half of the length of the table top, plus the side offset of a seat on its bench.
TABLE_HALF_WIDTH = 0.30
# How far the pelvis joint lies above the seat surface, as a share of the length of the thigh.
HIP_ABOVE_SEAT = 0.35
# The knees of a guest bend at least by this share of the length of the thigh.
MIN_KNEE_BEND = 0.25
# Tried in this order: how far the feet are placed in front of the body, as a share of the height of the body.
FOOT_REACH = (0.2, 0.12, 0.05, 0.0)
# The furthest a body moves back on its bench to stay out of the table top: the pelvis stays on the bench (0.084 to its edge).
MAX_BACK_SHIFT = 0.06
MAX_ARM_BACK_SHIFT = 0.06
# Tried in this order: the size of a walking body on the bench, kept by a scale key on the roots in every seated clip.
SEAT_SCALES = (1.0, 0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6)
# The creature scale of the level runs from 1.0 to 1.1 (CreatureLevelGrowthMax). The clips fit the middle of that range, so
# the pelvis lies at most about 0.013 tiles beside the bench while the feet stay on the floor at every level.
LEVEL_SCALE_LOW = 1.0
LEVEL_SCALE_HIGH = 1.1
LEVEL_SCALE_MIDDLE = 1.05
# Types with a bed of 2x2 in creatures.cfg have a whole bench; every other guest has half of it.
LARGE_MODELS = ('PitDemon', 'Troll', 'Scarab', 'Dragon', 'Kreatur')
BENCH_LENGTH = 0.78
# A body on four or more legs that does not fit in front of the table lies along the bench, not smaller than this.
MIN_LENGTHWISE_SCALE = 0.45
LENGTHWISE_TURN = 90.0
LENGTHWISE_HEAD_TURN = -63.0
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
RELAXED_ARM_ANGLES = (0.0, 15.0, 30.0, 45.0, 60.0)
# Tried in this order: how far a long body rears up in degrees, so that it fits on the bench in front of the table.
REAR_ANGLES = (0.0, 25.0, 40.0, 55.0, 70.0, 85.0)
# Share of the rearing that the head and the tail turn back, so that the head looks ahead and the tail stays low.
REAR_HEAD_SHARE = 0.8
REAR_TAIL_SHARE = 1.0
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
# Size of the body while it is posed: the bench and the table are measured in the units of the unscaled model.
SCENE = {'size': 1.0}
# (clip, length in seconds, keyframes, source clip of the upper body, looped)
CLIPS = (('Sit', 4.0, 17, None, True),
         ('SitDrink', None, 49, 'Drink', True),
         ('SitSlap', None, 49, 'Slap', False),
         ('SitSlapped', 0.8, 17, None, False),
         ('SitArmWrestle', None, 49, 'ArmWrestle', True),
         ('SitDice', None, 49, 'Dice', True),
         ('SitSlumped', 4.0, 17, None, True))
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


# Measure per frame how far a posed body reaches into the table on the side the guest looks at, in units of the points.
def frame_depths(points, selected=None, under=False):
    if selected is not None:
        points = points[:, selected, :]
    scene = SCENE['size']
    low = (BENCH_TOP if under else TABLE_UNDERSIDE) / scene
    inside = ((points[:, :, 2] > low) & (points[:, :, 2] < TABLE_TOP / scene) &
              (np.abs(points[:, :, 0]) < TABLE_HALF_WIDTH / scene))
    depth = TABLE_NEAR_EDGE / scene - points[:, :, 1]
    depth[~inside] = 0.0
    return np.maximum(0.0, depth.max(axis=1))


# Measure how far a posed body reaches into the table on the side the guest looks at; selected limits it to some vertices.
def table_depth(points, selected=None, under=False):
    return float(frame_depths(points, selected, under).max())


# Measure a pose of a finished clip at the smallest and the largest creature scale of the level, in tiles.
def level_depth(points):
    saved = SCENE['size']
    SCENE['size'] = 1.0
    depth = max(table_depth(points * LEVEL_SCALE_LOW), table_depth(points * LEVEL_SCALE_HIGH))
    SCENE['size'] = saved
    return depth


# Measure per frame how far a pose reaches into the table at the smallest and the largest creature scale of the level, in
# tiles; the points are in the units of the current scene, whose size holds the middle of that scale.
def worst_depths(points):
    saved = SCENE['size']
    depths = np.zeros(points.shape[0])
    for level in (LEVEL_SCALE_LOW, LEVEL_SCALE_HIGH):
        SCENE['size'] = saved * level / LEVEL_SCALE_MIDDLE
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


# Turn a posed body around the vertical through the floor origin, so that it lies along its bench.
def turn_lengthwise(skeleton, local, body_rig):
    amount = np.full(1, math.radians(LENGTHWISE_TURN))
    quaternion = feet.rv2q(np.array([[0.0, 0.0, 1.0]]) * amount[:, None])
    matrix = feet.q2m(quaternion)
    for index in skeleton.topo:
        if skeleton.parent[index] < 0:
            position, rotation, scale = local[index]
            local[index] = (np.einsum('nij,nj->ni', matrix, position), feet.qmul(quaternion, rotation), scale)
    if isinstance(body_rig, list):
        for item in body_rig:
            if item.get('head') in skeleton.idx:
                rest.rotate_joint(skeleton, local, item['head'], rig.Z_AXIS, np.radians(np.full(1, LENGTHWISE_HEAD_TURN)))


# Make the bones of a clip keep the size of the body on the bench, seen from the floor origin.
def apply_seat_scale(skeleton, local, size):
    if size >= 1.0:
        return
    for index in skeleton.topo:
        if skeleton.parent[index] < 0:
            position, rotation, scale = local[index]
            local[index] = (position * size, rotation, scale * size)


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
            best_depth = table_depth(points, held)
            if best_depth <= TABLE_TOLERANCE / SCENE['size']:
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
                depth = table_depth(points, held)
                low = max(0.0, floor - float(points[0, held, 2].min()) - FLOOR_TOLERANCE)
                if depth + low < best_depth + best_low - 1e-4:
                    best, best_depth, best_low = trial, depth, low
                if depth <= TABLE_TOLERANCE / SCENE['size'] and low <= 0.0:
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


# Let a long body rear up on its hind part; the head looks ahead again and the tail stays low behind the bench.
def rear_up(skeleton, local, body_rig, degrees):
    if degrees <= 0.0:
        return
    rest.tilt_body(skeleton, local, np.radians(np.full(1, -degrees)))
    if isinstance(body_rig, list):
        for item in body_rig:
            if item.get('head') in skeleton.idx:
                rest.rotate_joint(skeleton, local, item['head'], rig.X_AXIS, np.radians(np.full(1, degrees * REAR_HEAD_SHARE)))
            for chain in item.get('tail', []):
                if chain and chain[0] in skeleton.idx:
                    rest.rotate_joint(skeleton, local, chain[0], rig.X_AXIS, np.radians(np.full(1, degrees * REAR_TAIL_SHARE)))


# Pose the guest on the bench for one candidate of foot placement; returns the hold pose and the support height.
def seat_candidate(skeleton, body_rig, base, height, name, vertices, weights, chains, forward):
    amount = np.ones(1)
    humanoid = is_humanoid(body_rig)
    world = skeleton.fk(base)
    if humanoid:
        thighs = thigh_chains(skeleton, chains, body_rig)
        hip, thigh = hip_measure(skeleton, thighs, world)
        wanted = BENCH_TOP / SCENE['size'] + HIP_ABOVE_SEAT * thigh
        drop = hip - wanted
        lift = max(0.0, MIN_KNEE_BEND * thigh - drop)
        for attempt in range(8):
            try:
                local, error = rest.sitting(skeleton, body_rig, base, amount, height, name, vertices, weights,
                                            seat={'drop': drop, 'lift': lift, 'forward': forward})
                break
            except AssertionError:
                # The feet cannot reach their place: they hang a bit higher
                lift += 0.02 * height
        else:
            raise AssertionError((name, 'no seated leg solution'))
        # The correction of the rest tool can lift a body; the pelvis goes back to the seat, the feet go with it
        posed = skeleton.fk(local)
        now, _ = hip_measure(skeleton, thighs, posed)
        offset = np.zeros((1, 3))
        offset[0, 2] = wanted - now
        centre = np.mean([posed[skeleton.idx[chain[0]]][0][0, 1] for chain in thighs])
        offset[0, 1] = -centre
        rest.move_roots(skeleton, local, offset)
        points = rest.skin_vertices(skeleton, local, vertices, weights)
        return local, max(0.0, float(points[0, :, 2].min())), 'seated'

    # Every other body rests like on the ground, on its belly when it is tall, otherwise on top of the bench
    plain = rest.sitting(skeleton, body_rig, base, amount, height, name, vertices, weights)[0]
    floor = float(rest.skin_vertices(skeleton, base, vertices, weights)[0, :, 2].min())
    carrying = vertices_without(weights, free_bones(skeleton, body_rig))
    selected = body_vertices(skeleton, chains, weights) if chains else []
    if selected:
        belly = float(rest.skin_vertices(skeleton, base, vertices, weights)[0, selected, 2].min()) - floor
        if belly >= BENCH_TOP / SCENE['size']:
            try:
                local = rest.sitting(skeleton, body_rig, base, amount, height, name, vertices, weights,
                                     seat={'drop': belly - BENCH_TOP / SCENE['size'], 'lift': 0.0, 'forward': 0.0})[0]
            except AssertionError:
                local = None
            if local is not None:
                points = rest.skin_vertices(skeleton, local, vertices, weights)
                offset = np.zeros((1, 3))
                offset[0, 2] = floor - float(points[0, carrying, 2].min())
                rest.move_roots(skeleton, local, offset)
                return local, floor, 'belly'
    return plain, BENCH_TOP / SCENE['size'], 'perched'


# Lift a perched body onto the bench and move it so that its rear lies on the middle of the bench.
def place_on_bench(skeleton, local, vertices, weights, carrying):
    points = rest.skin_vertices(skeleton, local, vertices, weights)
    offset = np.zeros((1, 3))
    offset[0, 2] = BENCH_TOP / SCENE['size'] - float(points[0, carrying, 2].min())
    near = points[0, carrying, 2] < float(points[0, carrying, 2].min()) + 0.04
    offset[0, 1] = -float(points[0, carrying, 1][near].mean())
    offset[0, 0] = -float(points[0, carrying, 0][near].mean())
    rest.move_roots(skeleton, local, offset)


# Lay a body along its bench when it does not fit in front of the table; returns None when it still does not fit.
def lengthwise_pose(skeleton, body_rig, base, height, name, vertices, weights, chains, carrying):
    lengths = rest.skin_vertices(skeleton, base, vertices, weights)[0, carrying, 1]
    room = BENCH_LENGTH if name in LARGE_MODELS else BENCH_LENGTH / 2.0
    size = min(1.0, room / float(np.ptp(lengths)))
    if size < MIN_LENGTHWISE_SCALE:
        return None
    SCENE['size'] = size * LEVEL_SCALE_MIDDLE
    local, support, mode = seat_candidate(skeleton, body_rig, base, height, name, vertices, weights, chains, 0.0)
    turn_lengthwise(skeleton, local, body_rig)
    if mode == 'perched':
        place_on_bench(skeleton, local, vertices, weights, carrying)
    # The body stays on the bench: from its middle it may lie back as far as the bench goes
    depth = table_depth(rest.skin_vertices(skeleton, local, vertices, weights), carrying, True)
    if depth > MAX_BACK_SHIFT / SCENE['size'] + TABLE_TOLERANCE / SCENE['size']:
        return None
    offset = np.zeros((1, 3))
    offset[0, 1] = min(depth, MAX_BACK_SHIFT / SCENE['size'])
    rest.move_roots(skeleton, local, offset)
    if worst_depths(rest.skin_vertices(skeleton, local, vertices, weights)).max() > TABLE_TOLERANCE:
        return None
    return local, support, mode, size


# Choose the seat pose that stays out of the table, moving a large body back on its bench when it must.
def seat_pose(skeleton, body_rig, base, height, name, vertices, weights, chains):
    humanoid = is_humanoid(body_rig)
    weapons = long_weapons(skeleton, base, body_rig, vertices, weights)
    if humanoid:
        for size in SEAT_SCALES:
            SCENE['size'] = size * LEVEL_SCALE_MIDDLE
            found = seat_pose_at_size(skeleton, body_rig, base, height, name, vertices, weights, chains, weapons)
            if worst_depths(rest.skin_vertices(skeleton, found[0], vertices, weights)).max() <= TABLE_TOLERANCE:
                break
        found[2]['size'] = size
        found[2]['lengthwise'] = False
        return found + (weapons,)
    SCENE['size'] = LEVEL_SCALE_MIDDLE
    found = seat_pose_at_size(skeleton, body_rig, base, height, name, vertices, weights, chains, weapons)
    found[2]['size'] = 1.0
    found[2]['lengthwise'] = False
    if found[2]['rear'] > 0.0:
        lying = lengthwise_pose(skeleton, body_rig, base, height, name, vertices, weights, chains, found[3])
        if lying is not None:
            local, support, mode, size = lying
            return local, support, {'mode': mode, 'foot_reach': 0.0, 'rear': 0.0, 'back_shift': 0.0, 'size': size,
                                    'lengthwise': True}, found[3], weapons
    # A body that keeps reaching into the table gets smaller on the bench
    for size in SEAT_SCALES:
        SCENE['size'] = size * LEVEL_SCALE_MIDDLE
        found = seat_pose_at_size(skeleton, body_rig, base, height, name, vertices, weights, chains, weapons)
        if worst_depths(rest.skin_vertices(skeleton, found[0], vertices, weights)).max() <= TABLE_TOLERANCE:
            break
    found[2]['size'] = size
    found[2]['lengthwise'] = False
    return found + (weapons,)


# Choose the seat pose at the size of the current scene.
def seat_pose_at_size(skeleton, body_rig, base, height, name, vertices, weights, chains, weapons):
    humanoid = is_humanoid(body_rig)
    carrying = vertices_without(weights, free_bones(skeleton, body_rig))
    without_arms = vertices_without(weights, arm_bones(skeleton, body_rig) | free_bones(skeleton, body_rig))
    best = None
    for share in FOOT_REACH if humanoid else (0.0,):
        original, support, mode = seat_candidate(skeleton, body_rig, base, height, name, vertices, weights, chains, height * share)
        for degrees in (0.0,) if humanoid else REAR_ANGLES:
            local = copy.deepcopy(original)
            rear_up(skeleton, local, body_rig, degrees)
            if mode == 'perched':
                place_on_bench(skeleton, local, vertices, weights, carrying)
            depth = table_depth(rest.skin_vertices(skeleton, local, vertices, weights), without_arms, not humanoid)
            if best is None or depth < best[3] - 1e-4:
                best = (local, support, mode, depth, share, degrees)
            if depth <= 0.0:
                break
        if best[3] <= 0.0:
            break
    local, support, mode, depth, share, degrees = best
    back = min(depth, MAX_BACK_SHIFT / SCENE['size'])
    if back > 0.0:
        offset = np.zeros((1, 3))
        offset[0, 1] = back
        rest.move_roots(skeleton, local, offset)
    if humanoid:
        floor = float(rest.skin_vertices(skeleton, base, vertices, weights)[0, :, 2].min())
        hold_weapons_upright(skeleton, local, weapons)
        relax_arms(skeleton, local, base, body_rig, vertices, weights, floor)
        hold_weapons_upright(skeleton, local, weapons)
        remaining = table_depth(rest.skin_vertices(skeleton, local, vertices, weights))
        extra = 0.0
        if remaining > TABLE_TOLERANCE / SCENE['size']:
            extra = min(remaining, max(0.0, MAX_ARM_BACK_SHIFT / SCENE['size'] - back))
        if extra > 0.0:
            offset = np.zeros((1, 3))
            offset[0, 1] = extra
            rest.move_roots(skeleton, local, offset)
            back += extra
        # A hunched body straightens up on the bench to stay out of the table; its arms follow it
        spine, head = upper_chain(skeleton, body_rig, chains)
        straighten_seat(skeleton, local, spine, head, vertices, weights)
        relax_arms(skeleton, local, base, body_rig, vertices, weights, floor)
        hold_weapons_upright(skeleton, local, weapons)
    return local, support, {'mode': mode, 'foot_reach': share, 'rear': degrees, 'back_shift': back * SCENE['size']}, carrying


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
def slapped_clip(skeleton, seated, times, length, spine, head):
    count = len(times)
    local = hold(seated, count)
    progress = times / length
    decay = np.exp(-3.5 * progress) * np.sin(2.0 * math.pi * SLAP_OSCILLATIONS * progress) * (1.0 - progress)
    tilt = np.exp(-4.0 * progress) * np.sin(math.pi * np.minimum(1.0, progress * 3.0)) * (1.0 - progress)
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
    # (in the units of the model: the seat scale comes after this)
    def settle(local):
        if not humanoid:
            keep_on_support(skeleton, local, vertices, weights, support, carrying)

    for clip, length, keys, source_clip, looped in CLIPS:
        played = skeleton.clips[source_clip] if source_clip else None
        if length is None:
            length = float(played.length)
        times = np.linspace(0.0, length, keys)
        if source_clip and upper_only:
            local = upper_body_clip(skeleton, seated, base, played, times, length, fixed)
        elif source_clip:
            local = whole_body_clip(skeleton, seated, base, played, times, length)
        elif clip == 'SitSlapped':
            local = slapped_clip(skeleton, seated, times, length, spine, head)
        elif clip == 'SitSlumped':
            limit = SLUMP_BOW if isinstance(body_rig, list) and any(item.get('spine') for item in body_rig) else info['rear']
            local = slumped_clip(skeleton, seated, times, length, spine, head, vertices, weights, limit, settle)
            alive(skeleton, local, body_rig, name, times, None, 0.6)
        else:
            local = hold(seated, keys)
            alive(skeleton, local, body_rig, name, times, head)
        hold_weapons_upright(skeleton, local, weapons)
        if source_clip:
            lift_arms_over_table(skeleton, local, times, length, body_rig, vertices, weights)
        if source_clip or clip == 'SitSlapped':
            lean_out_of_table(skeleton, local, times, length, spine, head, vertices, weights)
        hold_weapons_upright(skeleton, local, weapons)
        settle(local)
        if source_clip or clip == 'SitSlapped':
            for _ in range(ROUTE_PASSES):
                local = route_arms_over_table(skeleton, local, body_rig, vertices, weights)
                hold_weapons_upright(skeleton, local, weapons)
        local = keep_out_of_table(skeleton, local, seated, vertices, weights, height, length / (keys - 1))
        settle(local)
        apply_seat_scale(skeleton, local, info['size'])
        posed = rest.skin_vertices(skeleton, local, vertices, weights)
        report['clips'][clip] = {
            'length': length,
            'table_depth': level_depth(posed),
            'lowest': float(posed[:, carrying, 2].min()),
            'highest': float(posed[:, :, 2].max()),
            'end_error': float(np.abs(posed[0] - posed[-1]).max() / height),
            'step': float(np.linalg.norm(np.diff(posed, axis=0), axis=2).max() / height)}
        blocks.append(clip_xml(skeleton, local, times, clip, length))
    SCENE['size'] = 1.0
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
              'rear', report['rear'], 'back', round(report['back_shift'], 3), 'size', report['size'],
              'lengthwise', report['lengthwise'], 'weapons', report['long_weapons'], 'depth',
              {clip: round(values['table_depth'], 3) for clip, values in report['clips'].items()}, flush=True)


if __name__ == '__main__':
    main()
