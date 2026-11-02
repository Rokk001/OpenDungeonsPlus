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
# The furthest a large body moves back on its bench to stay out of the table top.
MAX_BACK_SHIFT = 0.16
# The furthest a body moves back for its arms alone: it stays on the bench for that.
MAX_ARM_BACK_SHIFT = 0.08
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
# (clip, length in seconds, keyframes, source clip of the upper body, looped)
CLIPS = (('Sit', 4.0, 17, None, True),
         ('SitDrink', None, 25, 'Drink', True),
         ('SitSlap', None, 25, 'Slap', False),
         ('SitSlapped', 0.8, 17, None, False),
         ('SitArmWrestle', None, 25, 'ArmWrestle', True),
         ('SitDice', None, 25, 'Dice', True),
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


# Measure how far a posed body reaches into the table on the side the guest looks at; selected limits it to some vertices.
def table_depth(points, selected=None, under=False):
    if selected is not None:
        points = points[:, selected, :]
    low = BENCH_TOP if under else TABLE_UNDERSIDE
    inside = (points[:, :, 2] > low) & (points[:, :, 2] < TABLE_TOP) & (np.abs(points[:, :, 0]) < TABLE_HALF_WIDTH)
    depth = TABLE_NEAR_EDGE - points[:, :, 1]
    depth[~inside] = 0.0
    return max(0.0, float(depth.max()))


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
                depth = table_depth(points, held)
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
            while best_depth > TABLE_TOLERANCE and degrees <= ARM_LIFT_MAX:
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
    while best_depth > TABLE_TOLERANCE and degrees <= LEAN_BACK_MAX:
        trial = hold_copy(local)
        rest.rotate_joint(skeleton, trial, bone, rig.X_AXIS, np.radians(-degrees) * envelope)
        depth = table_depth(rest.skin_vertices(skeleton, trial, vertices, weights))
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
        wanted = BENCH_TOP + HIP_ABOVE_SEAT * thigh
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
        if belly >= BENCH_TOP:
            try:
                local = rest.sitting(skeleton, body_rig, base, amount, height, name, vertices, weights,
                                     seat={'drop': belly - BENCH_TOP, 'lift': 0.0, 'forward': 0.0})[0]
            except AssertionError:
                local = None
            if local is not None:
                points = rest.skin_vertices(skeleton, local, vertices, weights)
                offset = np.zeros((1, 3))
                offset[0, 2] = floor - float(points[0, carrying, 2].min())
                rest.move_roots(skeleton, local, offset)
                return local, floor, 'belly'
    return plain, BENCH_TOP, 'perched'


# Lift a perched body onto the bench and move it so that its rear lies on the middle of the bench.
def place_on_bench(skeleton, local, vertices, weights, carrying):
    points = rest.skin_vertices(skeleton, local, vertices, weights)
    offset = np.zeros((1, 3))
    offset[0, 2] = BENCH_TOP - float(points[0, carrying, 2].min())
    near = points[0, carrying, 2] < float(points[0, carrying, 2].min()) + 0.04
    offset[0, 1] = -float(points[0, carrying, 1][near].mean())
    rest.move_roots(skeleton, local, offset)


# Choose the seat pose that stays out of the table, moving a large body back on its bench when it must.
def seat_pose(skeleton, body_rig, base, height, name, vertices, weights, chains):
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
    back = min(depth, MAX_BACK_SHIFT)
    if back > 0.0:
        offset = np.zeros((1, 3))
        offset[0, 1] = back
        rest.move_roots(skeleton, local, offset)
    if humanoid:
        floor = float(rest.skin_vertices(skeleton, base, vertices, weights)[0, :, 2].min())
        relax_arms(skeleton, local, base, body_rig, vertices, weights, floor)
        remaining = table_depth(rest.skin_vertices(skeleton, local, vertices, weights))
        extra = min(remaining, max(0.0, MAX_ARM_BACK_SHIFT - back)) if remaining > TABLE_TOLERANCE else 0.0
        if extra > 0.0:
            offset = np.zeros((1, 3))
            offset[0, 1] = extra
            rest.move_roots(skeleton, local, offset)
            back += extra
    return local, support, {'mode': mode, 'foot_reach': share, 'rear': degrees, 'back_shift': back}, carrying


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
    for scale in (1.0, 0.8, 0.6, 0.45, 0.3, 0.2, 0.1, 0.05):
        local = hold(seated, count)
        for bone in spine:
            bow = min(SLUMP_BOW * scale, limit)
            rest.rotate_joint(skeleton, local, bone, rig.X_AXIS, np.radians(bow * amount / max(1, len(spine))))
        if head:
            rest.rotate_joint(skeleton, local, head, rig.X_AXIS, np.radians(SLUMP_HEAD * scale * amount))
        settle(local)
        if table_depth(rest.skin_vertices(skeleton, [(p[:1], q[:1], s[:1]) for p, q, s in local], vertices, weights)) <= TABLE_TOLERANCE:
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
    seated, support, info, carrying = seat_pose(skeleton, body_rig, base, height, name, vertices, weights, chains)
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
        if source_clip:
            lift_arms_over_table(skeleton, local, times, length, body_rig, vertices, weights)
        if source_clip or clip == 'SitSlapped':
            lean_out_of_table(skeleton, local, times, length, spine, head, vertices, weights)
        settle(local)
        posed = rest.skin_vertices(skeleton, local, vertices, weights)
        report['clips'][clip] = {
            'length': length,
            'table_depth': table_depth(posed),
            'lowest': float(posed[:, carrying, 2].min()),
            'highest': float(posed[:, :, 2].max()),
            'end_error': float(np.abs(posed[0] - posed[-1]).max() / height),
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
              'rear', report['rear'], 'back', round(report['back_shift'], 3), 'depth',
              {clip: round(values['table_depth'], 3) for clip, values in report['clips'].items()}, flush=True)


if __name__ == '__main__':
    main()
