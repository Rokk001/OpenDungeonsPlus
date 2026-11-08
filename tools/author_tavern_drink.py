#!/usr/bin/env python3
"""Author the drink clips Drink and SitDrink of one creature skeleton as one calm drink (owner decision 901, point 2).

One clip is one sip of CYCLE seconds: the mug stands on the table top in front of a seated guest
(a standing guest holds it low in front of its belly), the creature takes it,
lifts it to its mouth, drinks with the rim AT the mouth and the mug in front of the face (not through the head), puts it
back and pauses. The body keeps the first pose of the old clip; only the limb that holds the mug moves. The limb is solved
along the way of the foot of the mug in small steps, each from the pose of the one before, so that it does not jump; the way
back is the way there. The clip starts and ends in the rest pose, so it loops without a seam. ClipSecondsDrink and
ClipSecondsSitDrink of config/rooms.cfg play it in CYCLE game seconds: a water of 10 s is two sips, a beer of 30 s six.

Writes <output>/<name>.drink.skeleton.xml with the bones and only the two clips, and <output>/<name>.drink.json with the
measures of every clip. Incomplete cycles raise an error before the output skeleton is written; held seated mugs and
paths that stop before the mouth are not finished assets. splice_animation_chunks.py puts the two clips into the game
skeleton after OgreXMLConverter made the binary.

Calls: python tools/author_tavern_drink.py <folder with the exported .skeleton.xml, .mesh.xml and TavernMug.mesh.xml>
       <output folder> <skeleton name>[:<mesh file name>]...
"""
import argparse
import json
import math
import re
from pathlib import Path

import numpy as np

import author_rest_poses as rest
import author_tavern_seats as seats
import fix_walk_feet as feet

ROOT = Path(__file__).resolve().parents[1]

# One sip, in seconds: the rest on the support (the end of the clip and its start are one pause), the lift, the drink at
# the mouth and the way back
CYCLE = 5.0
REST_END = 1.0
LIFT_END = 2.1
DRINK_END = 3.5
LOWER_END = 4.6
# While the mug moves, a key lies at every solved step of the way (WAY_STEPS), so that the limb between two keys follows
# the way and does not cut through the edge of the table; the rest and the drink hold their pose between few keys
DRINK_KEYS = 5
# The mug leans this far from upright while the creature drinks, its rim towards the face (the first that keeps the mug
# out of the face and the table); the sip in the middle of the drink tips it this much further
DRINK_TIPS = (62.0, 75.0, 88.0)
SIP_TIP = 10.0
# The foot of the mug rises this high over the straight way between the support and the mouth (so it leaves the table
# upwards), as a share of the way
# Steps along the way the limb is solved for, and rounds of the solver per step
WAY_STEPS = 41
SOLVE_ROUNDS = 4
# Bodies whose limb passes the edge of the table or the seat of the stool so closely that between two of the 41 steps
# it reaches through (the forearm of the lizardman 0.0401 into the table top, a tentacle tip of the kreatur into the seat
# of its stool): their way has twice as many steps, checked half way between two steps (MAX_HALF_DEPTH); with steps
# that fine the mug may come closer into the face before the way ends (MAX_CLEAR_FACE, check_tavern_drink_834 allows
# 0.05). A fine path that still ends before the mouth is rejected by validate_report.
FINE_WAYS = {'Lizardman': {'WAY_STEPS': 81, 'MAX_CLEAR_FACE': 0.045, 'MAX_HALF_DEPTH': 0.038},
             'Kreatur': {'WAY_STEPS': 81, 'MAX_CLEAR_FACE': 0.045, 'MAX_HALF_DEPTH': 0.038}}
# The mesh of the mug: its foot lies 0.009 below the origin, its rim 0.171 above it along the -x axis of the mesh. The
# render manager makes it 1.8 times as wide (TAVERN_MUG_GIRTH_SCALE). On Weapon_R it is held at its middle: it is shifted
# this far along the x axis of the bone (TAVERN_MUG_GRIP_SHIFT), so the hand grips the tankard and not its foot.
MUG_FOOT = 0.009
MUG_RIM = -0.171
MUG_GIRTH = 1.8
MUG_GRIP_SHIFT = 0.1
# The part of the mesh below this (along -x) is the bottom of the mug that stands on a table
MUG_BOTTOM = -0.07
# The table and the bench in the frame of a guest on the middle of its bench (author_tavern_seats). The creature scale of
# the level (1.0 to 1.1) grows the clip and not the table: the mug stands on the table at the smallest scale and is
# never in it; at the largest scale it stands up to 0.04 tiles higher.
SCALE = seats.LEVEL_SCALE_LOW
# The foot of a mug on the table stands this little above the top, the mug this far behind the near edge of the table
TABLE_CLEARANCE = 0.003
TABLE_INSET = 0.0
# The lizard guest sets its mug further onto the table before lifting it. An edge placement routes the upright mug
# beside its cheek; the deeper supported placement leaves room to tip the mug in front of the muzzle.
TABLE_INSETS = {'Lizardman': 0.1}
# A limb reaches this share of its length at most
MAX_REACH = 0.97
# The rim of the mug stays this far in front of the face at least; the search moves it further out in these steps
MOUTH_GAP_STEPS = (0.0, 0.01, 0.02, 0.03, 0.045, 0.06, 0.08, 0.1)
# A mug point lies in the face when it is this far behind the front of the face at its height and side, in tiles
FACE_DEPTH = 0.01
MAX_MUG_IN_FACE = 0.02
# Cells of the front of the face, in tiles
FACE_CELL = 0.02
# The rim counts as at the mouth this close to its place; a head bows towards a mug its limb does not bring there in this
# many rounds, by half of the way that is left each time, until the mouth moved this share of the height of the body
MOUTH_REACH = 0.02
# A drink whose rim stays further from the mouth than this is not taken while another one comes closer, in tiles
MAX_RIM_DISTANCE = 0.06
MOUTH_ROUNDS = 8
MAX_BOW_SHARE = 0.45
# How far a seated guest may bend forward to reach the table, in degrees, tried in this order
LEANS = (0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0)
# The upper body bends about a point this high above the seat of the bench
LEAN_PIVOT_HEIGHT = 0.05
# How far the way of the mug may bow forward, away from the face, and how high it rises over the table (share of the
# way), tried in this order
WAY_BULGES = (0.0, 0.04, 0.08, 0.12)
WAY_ARCS = (0.0, 0.25, 0.5, 0.75, 1.0)
# On the way the rim never comes back towards its rest by more than this (HOLD of check_tavern_drink_834 is 0.04)
MAX_OVERSHOOT = 0.01
# Where the limb reaches into the table in the pause, the mug stands this much further out (-y) and to the side (outwards
# first), and the inner joints of the limb swing about the line from its root to the grip by these degrees
# The places of the mug on the table are tried on a grid of this step, this far to either side of the root of the limb
# and this far beyond the near edge. The nearest table places that the limb reaches are tried first, this many in all.
# No part of the body that stays stands this close to the mug.
PLACE_STEP = 0.025
PLACE_SPAN = 0.2
PLACE_DEPTH = 0.2
PLACES_PER_SUPPORT = 6
BODY_CLEARANCE = 0.01
# Held places on a grid of this step this far around the root of the limb, this many lowest ones
HELD_STEP = 0.08
HELD_SPAN = 0.32
HELD_PLACES = 10
SWINGS = (0.0, 30.0, -30.0, 60.0, -60.0, 90.0, -90.0)
# A way is cut short before the first step that reaches further than this into the furniture or the head
MAX_CLEAR_DEPTH = 0.035
MAX_CLEAR_FACE = 0.03
# The clip blends two steps of the way between their keys: half way between them a limb may reach this deep before the
# way ends (see FINE_WAYS; MAX_TABLE_DEPTH of check_tavern_seat_clips is 0.04); the other bodies only
# prefer the way that stays clearest there
MAX_HALF_DEPTH = float('inf')
# Where the guest sits: on a stool at the end of the table (TAVERN_STOOL_DISTANCE from its middle, TAVERN_STOOL_BODIES of
# RoomTavern.cpp) or on a bench; and the room its seated clips took before, which the drink keeps to within this margin
SEAT = {'stool': False, 'envelope': None, 'side': None, 'inset': TABLE_INSET}
# A bench guest whose arm would swing further to the side than this (tiles at level scale 1) reaches the second place
# beside a stool guest (check_tavern_stools_863 blocked places: the slime blocks one place): the lich keeps to the room
# its SitDrink took before decision 901 (0.501)
SIDE_LIMITS = {'lich': 0.505}
STOOL_DISTANCE = 0.8
ENVELOPE_SAMPLES = 41
ENVELOPE_MARGIN = 0.0
# A body may leave its room by this little (check_tavern_stools_863 allows 1e-6); a pose beyond it, or one that reaches
# into the seat or the post of the stool (TAVERN_STOOL_* below), counts as HARD_LIMIT deep in the furniture
ENVELOPE_TOLERANCE = 1e-6
HARD_LIMIT = 1.0
STOOL_TOP = 0.2575
STOOL_RADIUS = 0.16
STOOL_POST_RADIUS = 0.034
MAX_STOOL_SINK = 0.025
BENCH_REACH_ACROSS = 1.50
BENCH_REACH_ALONG = 1.48
BENCH_OFFSET = 0.4116
# Bench places a large body takes (LARGE_BENCH_PLACES of check_tavern_stools_863.py)
BENCH_PLACES = {'Troll': 4, 'PitDemon': 4, 'Dragon': 3}
# A standing body holds the mug at least this high above the floor (its foot)
STANDING_FLOOR_CLEARANCE = 0.03
# Preferred pause depth and maximum resting-place error; the way prefers this depth (tiles). MAX_CLEAR_DEPTH remains
# the hard furniture limit when accepting a resting pose.
MAX_REST_DEPTH = 0.02
MAX_REST_ERROR = 0.01
MAX_WAY_DEPTH = 0.03

# The limb that holds the mug, from its root to the bone that carries the mug, where the three bones up from the carrier
# are not the limb
LIMBS = {
    'lich': ('shoulderRight', 'ellbowRight', 'wristRight'),
    'Rat': ('FrontLeg_R', 'FrontLeg_R.001', 'FrontLeg_R.002', 'FrontLeg_R.003'),
    'Kreatur': ('tentafr1_r', 'tentafr2_r', 'tentafr3_r', 'tentafr4_r'),
    'Scarab': ('Bone.001_R', 'Bone.001_R.001', 'Bone.001_R.002', 'Bone.001_R.003', 'Bone.001_R.004', 'Bone.001_R.005'),
    'Roach': ('ArmRootR', 'ArmR', 'ForearmFrontR', 'ClawFrontR'),
}
# The bones whose vertices make the head, where it is not the bone named Head or head with the most vertices, and the
# height above the root of the limb from which they count (for a head that shares its bone with the chest); a third value
# False takes only the vertices of these bones and not of their children (the body bone of the spider carries all legs)
HEADS = {
    'Cultist': (('neck',), 0.0),
    'Goblin': (('Spine1',), 0.06),
    'Scarab': (('Bone.004',), None),
    'Spider': (('Zahn_R', 'Zahn_L', 'Body'), None, False),
    'lich': (('spine3', 'crown'), 0.05),
    'Kreatur': (('head',), None),
    'RunelordDwarf': (('head.cr',), None),
    'Slime': (('slime_head',), None),
}

# Anatomically identified material points, in the original mesh vertex order. A turned head keeps the same mouth:
# selecting its global front again would move the target onto another part of the head. Dragon uses the opening between
# its upper and lower centre lips, Spider the midpoint between its inner fangs, Rat its muzzle centre and Slime its front.
MOUTHS = {
    'Dragon': ((80, (0.0, -0.708788, 0.961628)), (72, (0.0, -0.703024, 0.954036))),
    'Spider': ((14, (-0.00848184, -0.142194, 0.131078)), (69, (0.00848184, -0.142194, 0.131078))),
    'Rat': ((462, (0.0, -0.430011, 0.145937)),),
    'Slime': ((16, (0.0, -0.274409, 0.27)),),
}

# The seated dragon brings its long muzzle around the right shoulder with its independent neck joints. The hip, legs
# and seat stay fixed. The mug approaches the front of the turned muzzle, whose forward direction is (-0.5, sqrt(0.75)).
DRINK_NECK_TURNS = {('Dragon', 'SitDrink'): (('Spine_3', -60.0), ('Spine_4', -90.0))}
DRINK_APPROACHES = {('Dragon', 'SitDrink'): (('neck-front', (0.5, -math.sqrt(0.75), 0.0)),)}


def read_limb_mounts():
    render = (ROOT / 'source' / 'render' / 'RenderManager.cpp').read_text(encoding='utf-8')
    table = render[render.index('const TavernMugLimbMount TAVERN_MUG_LIMB_MOUNTS[] ='):]
    table = table[:table.index('};')]
    number = r'(-?[0-9.]+)f'
    rows = re.findall(r'\{ "([^"]+)", "([^"]+)", ' + ', '.join([number] * 8) + r' \}', table)
    return {skeleton[:-len('.skeleton')]: (bone, np.array([float(v) for v in values[:4]]), np.array([float(v) for v in values[4:7]]),
                                          float(values[7])) for skeleton, bone, *values in rows}


def quaternion_matrix(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


# The skeletons whose Weapon_R is a passive mount that no clip animates (check_rest_animation_assets.py): the mug hangs on
# Weapon_R as the render manager attaches it, and the limb moves its parent bone, which carries Weapon_R in its rest pose
PASSIVE_MOUNTS = ('skeleton', 'lich', 'PitDemon', 'Kreatur', 'Scarab')


class Mug(object):
    """The mug as the render manager attaches it: the bone, the mesh points, its foot and its axis in the frame of the bone."""

    def __init__(self, skeleton, name, mesh_points, limb_mounts):
        self.on_weapon = seats.MUG_BONE in skeleton.idx
        self.passive = self.on_weapon and name in PASSIVE_MOUNTS
        if self.on_weapon:
            self.bone = seats.MUG_BONE
            turn, offset, scale = seats.MUG_TURN, np.array([MUG_GRIP_SHIFT, 0.0, 0.0]), 1.0
        else:
            bone, rotation, offset, scale = limb_mounts[name]
            self.bone = bone
            turn = quaternion_matrix(rotation)
        wide = mesh_points * scale * np.array([1.0, MUG_GIRTH, MUG_GIRTH])
        self.points = wide @ turn.T + offset
        self.foot = turn @ np.array([MUG_FOOT * scale, 0.0, 0.0]) + offset
        self.axis = turn @ np.array([-1.0, 0.0, 0.0])
        self.length = (MUG_FOOT - MUG_RIM) * scale
        self.radius = float(np.abs(mesh_points[:, 1:]).max()) * scale * MUG_GIRTH
        # The bottom of the mug, which stands on the table
        bottom = mesh_points[mesh_points[:, 0] > MUG_BOTTOM]
        self.base_radius = float(np.abs(bottom[:, 1:]).max()) * scale * MUG_GIRTH
        self.scale = scale
        # From the foot of the mug to the origin of the bone along its axis (Weapon_R holds the mug at its middle)
        self.grip = (MUG_FOOT + MUG_GRIP_SHIFT) * scale
        if self.passive:
            # The mug in the frame of the parent of Weapon_R, through the rest pose of Weapon_R, which no clip moves
            index = skeleton.idx[seats.MUG_BONE]
            position, turn, size = skeleton.rest_pos[index], quaternion_matrix(skeleton.rest_q[index]), skeleton.rest_s[index]
            self.points = (self.points * size) @ turn.T + position
            self.foot = turn @ (self.foot * size) + position
            self.axis = turn @ self.axis
            self.bone = skeleton.names[skeleton.parent[index]]
            self.on_weapon = False

    def world(self, frames, skeleton):
        """Foot, axis (foot to rim) and points of the mug in every frame."""
        index = skeleton.idx[self.bone]
        position, rotation, scale = frames[index]
        foot = position + np.einsum('nij,nj->ni', rotation, self.foot[None] * scale)
        axis = np.einsum('nij,j->ni', rotation, self.axis)
        axis /= np.linalg.norm(axis, axis=1)[:, None]
        points = position[:, None, :] + np.einsum('nij,nmj->nmi', rotation, self.points[None] * scale[:, None, :])
        return foot, axis, points


def limb_of(skeleton, name, mug):
    if name in LIMBS:
        limb = list(LIMBS[name])
        # The limb ends in the bone that carries the mug (the item bone of the hand of the lich)
        tail = []
        walk = skeleton.idx[mug.bone]
        while skeleton.names[walk] not in limb and walk >= 0:
            tail.append(skeleton.names[walk])
            walk = skeleton.parent[walk]
        return limb + list(reversed(tail)) if walk >= 0 else limb
    carrier = skeleton.idx[mug.bone]
    if mug.bone == seats.MUG_BONE:
        carrier = skeleton.parent[carrier]
    chain = [carrier]
    while len(chain) < 3 and skeleton.parent[chain[-1]] >= 0:
        chain.append(skeleton.parent[chain[-1]])
    return [skeleton.names[index] for index in reversed(chain)]


def head_vertices(skeleton, name, weights, limb_root_z, posed, limb=()):
    """Indices of the vertices of the head. The limb that holds the mug is never part of it (a head bone that also carries
    the arm, like the spine of the lich, would count the raised hand as head)."""
    children = True
    if name in HEADS:
        bones, above = HEADS[name][:2]
        children = HEADS[name][2] if len(HEADS[name]) > 2 else True
    else:
        candidates = [bone for bone in skeleton.names if bone.lower() == 'head']
        counts = {bone: sum(1 for row in weights if any(b == skeleton.idx[bone] and w >= 0.5 for b, w in row)) for bone in candidates}
        bones, above = ((max(counts, key=counts.get),) if counts else ()), None
    selected = {skeleton.idx[bone] for bone in bones if bone in skeleton.idx}
    for index in (skeleton.topo if children else ()):
        if skeleton.parent[index] in selected and skeleton.names[index] != seats.MUG_BONE and skeleton.names[index] not in limb:
            selected.add(index)
    found = [index for index, row in enumerate(weights) if sum(w for b, w in row if b in selected) >= 0.5]
    if above is not None:
        found = [index for index in found if posed[index, 2] >= limb_root_z + above]
    assert found, (name, 'no head')
    return np.array(found)


class Face(object):
    """The front of the head: per cell across (x) and up (z), how far forward (-y) the head reaches and how far back."""

    def __init__(self, points, mouth=None):
        """Build collision cells and optionally carry the skinned anatomical mouth point."""
        self.cells = {}
        for x, y, z in points:
            key = (int(math.floor(x / FACE_CELL)), int(math.floor(z / FACE_CELL)))
            front, back = self.cells.get(key, (y, y))
            self.cells[key] = (min(front, y), max(back, y))
        self.points = points
        self.material_mouth = mouth

    def inside(self, points):
        """Share of the points that lie in the head."""
        count = 0
        for x, y, z in points:
            key = (int(math.floor(x / FACE_CELL)), int(math.floor(z / FACE_CELL)))
            if key in self.cells:
                front, back = self.cells[key]
                if front + FACE_DEPTH < y < back:
                    count += 1
        return count / max(1, len(points))

    def mouth(self):
        """Return the material mouth, or estimate the front of the lower half of an unannotated head."""
        if self.material_mouth is not None:
            return self.material_mouth
        p = self.points
        low, high = np.percentile(p[:, 2], 15), np.percentile(p[:, 2], 55)
        part = p[(p[:, 2] >= low) & (p[:, 2] <= high)]
        front = part[part[:, 1] <= np.percentile(part[:, 1], 8)]
        return np.array([float(np.median(front[:, 0])), float(front[:, 1].min()), float(np.median(front[:, 2]))])


def turn_between(current, wanted):
    """Axis and angle of the shortest turn of one unit vector onto another."""
    axis = np.cross(current, wanted)
    size = float(np.linalg.norm(axis))
    angle = math.atan2(size, float(np.dot(current, wanted)))
    if size < 1e-9:
        return np.array([0.0, 0.0, 1.0]), 0.0
    return axis / size, angle


def rotation_matrix(axis, angle):
    return feet.q2m(feet.rv2q(np.asarray(axis)[None] * angle))[0]


def copy_pose(local):
    return [(p.copy(), q.copy(), s.copy()) for p, q, s in local]


def aim_at(skeleton, local, bone, current, wanted):
    """Turn a bone about its origin so that a point it carries moves from current onto the line to wanted."""
    origin = skeleton.fk(local)[skeleton.idx[bone]][0][0]
    turn_axis, angle = turn_between(unit(current - origin), unit(wanted - origin))
    rest.rotate_joint(skeleton, local, bone, turn_axis, np.array([angle]))


def unit(vector):
    return vector / max(float(np.linalg.norm(vector)), 1e-12)


def solve(skeleton, local, limb, mug, foot, axis, swing=0.0):
    """Move the limb of a one-frame pose so that the foot of the mug stands at foot and the mug points along axis.

    The limb is a chain of joints that ends in the grip: the origin of Weapon_R, which holds the mug at its middle, or the
    foot of the mug on a limb mount. On Weapon_R the grip lies on the axis of the mug, so the limb only has to bring the grip
    to its place and Weapon_R turns the mug about it. A mug on a limb mount can only roll about the line from the end of the
    limb to its foot. The swing turns the inner joints of the limb about the line from its root to the grip first (degrees),
    which lifts an elbow off the table."""
    if not mug.on_weapon:
        return solve_mount(skeleton, local, limb, mug, foot, axis, swing)
    grip_target = foot + axis * mug.grip if mug.on_weapon else foot
    for round_index in range(SOLVE_ROUNDS):
        world = skeleton.fk(local)
        current_foot, current_axis, _ = mug.world(world, skeleton)
        grip = world[skeleton.idx[mug.bone]][0][0] if mug.on_weapon else current_foot[0]
        joints = [world[skeleton.idx[bone]][0][0] for bone in limb]
        # A grip in the joint of the last bone (Weapon_R at the tip of a tentacle) ends the chain itself
        own_grip = np.linalg.norm(grip - joints[-1]) > 1e-4
        solved = seats.reach_chain(joints + [grip] if own_grip else joints, grip_target)
        if round_index == 0 and swing != 0.0:
            line = unit(solved[-1] - solved[0])
            turn = rotation_matrix(line, math.radians(swing))
            solved = [solved[0]] + [solved[0] + turn @ (point - solved[0]) for point in solved[1:-1]] + [solved[-1]]
        for index in range(len(limb) - 1):
            seats.aim_bone(skeleton, local, limb[index], limb[index + 1], (solved[index + 1] - solved[index])[None])
        if own_grip:
            world = skeleton.fk(local)
            current_foot, _, _ = mug.world(world, skeleton)
            grip = world[skeleton.idx[mug.bone]][0][0] if mug.on_weapon else current_foot[0]
            aim_at(skeleton, local, limb[-1], grip, solved[-1])
    world = skeleton.fk(local)
    _, current_axis, _ = mug.world(world, skeleton)
    if mug.on_weapon:
        turn_axis, angle = turn_between(current_axis[0], axis)
        rest.rotate_joint(skeleton, local, mug.bone, turn_axis, np.array([angle]))
    else:
        carrier = world[skeleton.idx[limb[-1]]][0][0]
        line = unit(mug.world(world, skeleton)[0][0] - carrier)
        have = current_axis[0] - line * float(np.dot(current_axis[0], line))
        want = axis - line * float(np.dot(axis, line))
        if np.linalg.norm(have) > 1e-6 and np.linalg.norm(want) > 1e-6:
            turn_axis, angle = turn_between(unit(have), unit(want))
            rest.rotate_joint(skeleton, local, limb[-1], line if np.dot(turn_axis, line) >= 0.0 else -line, np.array([angle]))
    world = skeleton.fk(local)
    return float(np.linalg.norm(mug.world(world, skeleton)[0][0] - foot))


def rotation_vector(matrix):
    """Axis and angle of a rotation matrix."""
    angle = math.acos(max(-1.0, min(1.0, 0.5 * (float(np.trace(matrix)) - 1.0))))
    if angle < 1e-9:
        return np.array([0.0, 0.0, 1.0]), 0.0
    axis = np.array([matrix[2, 1] - matrix[1, 2], matrix[0, 2] - matrix[2, 0], matrix[1, 0] - matrix[0, 1]])
    if np.linalg.norm(axis) < 1e-9:
        # A half turn: the axis is the column of matrix + 1 with the largest size
        columns = matrix + np.eye(3)
        axis = columns[:, int(np.argmax(np.linalg.norm(columns, axis=0)))]
    return unit(axis), angle


MOUNT_ROLL_STEP = 15


def solve_mount(skeleton, local, limb, mug, foot, axis, swing=0.0):
    """Move the limb so that the foot of a mug on a limb mount stands at foot and the mug points along axis.

    The mug is fixed to the last bone of the limb (the carrier), so the carrier takes the turn that brings the axis of the
    mug onto the wanted one by the shortest way from its current turn; the joints before it bring the origin of the carrier
    to where that turn puts the foot of the mug onto its place."""
    carrier = skeleton.idx[limb[-1]]
    world = skeleton.fk(local)
    have = world[carrier][1][0]
    scale = world[carrier][2][0]
    turn_axis, angle = turn_between(unit(have @ mug.axis), unit(axis))
    shortest = rotation_matrix(turn_axis, angle) @ have
    # The carrier may also roll about the axis of the mug: the shortest turn while the limb reaches the origin it needs, else
    # the roll that brings that origin closest into reach
    joints = [world[skeleton.idx[bone]][0][0] for bone in limb]
    length = MAX_REACH * sum(float(np.linalg.norm(joints[i + 1] - joints[i])) for i in range(len(joints) - 1))
    best = None
    for degrees in sorted(range(-180, 181, MOUNT_ROLL_STEP), key=abs):
        trial = rotation_matrix(unit(axis), math.radians(degrees)) @ shortest
        target = foot - trial @ (mug.foot * scale)
        score = (max(0.0, float(np.linalg.norm(target - joints[0])) - length), abs(degrees))
        if best is None or score < best[0]:
            best = (score, trial, target)
    _, wanted, origin_target = best
    for round_index in range(SOLVE_ROUNDS):
        world = skeleton.fk(local)
        joints = [world[skeleton.idx[bone]][0][0] for bone in limb]
        solved = seats.reach_chain(joints, origin_target)
        if round_index == 0 and swing != 0.0:
            line = unit(solved[-1] - solved[0])
            turn = rotation_matrix(line, math.radians(swing))
            solved = [solved[0]] + [solved[0] + turn @ (point - solved[0]) for point in solved[1:-1]] + [solved[-1]]
        for index in range(len(limb) - 1):
            seats.aim_bone(skeleton, local, limb[index], limb[index + 1], (solved[index + 1] - solved[index])[None])
    world = skeleton.fk(local)
    turn_axis, angle = rotation_vector(wanted @ world[carrier][1][0].T)
    rest.rotate_joint(skeleton, local, limb[-1], turn_axis, np.array([angle]))
    world = skeleton.fk(local)
    return float(np.linalg.norm(mug.world(world, skeleton)[0][0] - foot))


def tipped(degrees, towards):
    """The axis of the mug leaning from upright towards the face (towards is level: +y for a mug in front of a face that
    looks along -y, or across for a mug beside it)."""
    angle = math.radians(degrees)
    return towards * math.sin(angle) + np.array([0.0, 0.0, math.cos(angle)])


def smooth(share):
    share = np.clip(share, 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def key_times():
    times = [0.0]
    # The time share u at which smooth(u) reaches each step of the way
    fine = np.linspace(0.0, 1.0, 20001)
    steps = np.interp(np.linspace(0.0, 1.0, WAY_STEPS), smooth(fine), fine)
    times += list(REST_END + steps * (LIFT_END - REST_END))
    times += list(np.linspace(LIFT_END, DRINK_END, DRINK_KEYS))
    times += list(DRINK_END + steps * (LOWER_END - DRINK_END))
    times += [LOWER_END, CYCLE]
    return np.array(sorted(set(round(t, 6) for t in times)))


def phase(times):
    """Share of the way from the support to the mouth and the extra tip of the sip, per time."""
    way = np.zeros(len(times))
    sip = np.zeros(len(times))
    lifting = (times >= REST_END) & (times < LIFT_END)
    way[lifting] = smooth((times[lifting] - REST_END) / (LIFT_END - REST_END))
    drinking = (times >= LIFT_END) & (times <= DRINK_END)
    way[drinking] = 1.0
    sip[drinking] = np.sin(math.pi * (times[drinking] - LIFT_END) / (DRINK_END - LIFT_END)) ** 2
    lowering = (times > DRINK_END) & (times < LOWER_END)
    way[lowering] = 1.0 - smooth((times[lowering] - DRINK_END) / (LOWER_END - DRINK_END))
    return way, sip


def rest_targets(skeleton, start, limb, mug, seated, reach, still_points):
    """The places where the foot of the mug may stand in the pause, upright, best first, each with what carries it: the
    table top in front of a seated guest; a standing guest holds it as low as it reaches.
    A place counts where the limb reaches it and no part of the body that does not move stands where the mug would be."""
    root = skeleton.fk(start)[skeleton.idx[limb[0]]][0][0]
    lift = MUG_FOOT * mug.scale
    height = mug.length + 0.01

    def clear(point):
        near = np.linalg.norm(still_points[:, :2] - point[None, :2], axis=1) < mug.base_radius + BODY_CLEARANCE
        low = (still_points[:, 2] > point[2] - lift - 0.01) & (still_points[:, 2] < point[2] + height)
        return not np.any(near & low)

    def places(xs, ys, z, kind):
        found = []
        for x in xs:
            for y in ys:
                point = np.array([x, y, z])
                distance = float(np.linalg.norm(point - root))
                if distance <= MAX_REACH * reach and clear(point):
                    found.append((distance, point, kind))
        found.sort(key=lambda item: item[0])
        return [(point, kind) for _, point, kind in found[:PLACES_PER_SUPPORT]]

    if seated:
        # Every seated guest sets the mug on the table. A short limb needs a different pose or rig, never a held fallback.
        edge = -(STOOL_DISTANCE - seats.LONG_TABLE_HALF_LENGTH) if SEAT['stool'] else seats.TABLE_NEAR_EDGE
        near_edge = (edge - SEAT['inset']) / SCALE - mug.base_radius
        across = root[0] + np.arange(-PLACE_SPAN, PLACE_SPAN + 1e-9, PLACE_STEP)
        return places(across, near_edge - np.arange(0.0, PLACE_DEPTH + 1e-9, PLACE_STEP),
                      seats.TABLE_TOP / SCALE + TABLE_CLEARANCE + lift, 'table')

    # Held places lie above the floor, on a grid that is finer for a short limb.
    lowest = STANDING_FLOOR_CLEARANCE + lift
    step = min(HELD_STEP, MAX_REACH * reach / 3.0)
    span = min(HELD_SPAN, MAX_REACH * reach)
    grid = []
    for dx in np.arange(-span, span + 1e-9, step):
        for dy in np.arange(-span, span + 1e-9, step):
            for dz in np.arange(-span, 0.0 + 1e-9, step):
                point = root + np.array([dx, dy, dz])
                # Above the floor, never below it.
                if point[2] >= lowest and np.linalg.norm(point - root) <= MAX_REACH * reach:
                    grid.append((not clear(point), round(float(point[2]), 6), float(np.linalg.norm(point[:2] - root[:2])), point))
    grid.sort(key=lambda item: item[:3])
    # The places clear of the body first; a limb so short that the mug touches the body wherever it holds it (the cave
    # hornet) takes the lowest of the others, which the rest pose then keeps out of the head
    grid = [(point, 'held') for _, _, _, point in [g for g in grid if not g[0]][:HELD_PLACES] + [g for g in grid if g[0]][:HELD_PLACES]]
    # Standing: low in front of the belly, else anywhere in reach where the mug is clear of the body. A body whose
    # mouth is so low that the floor stops the mug (the roach) holds it out to the side of its limb by as much, so the
    # mug still travels to the mouth.
    low = root[2] - 0.7 * reach
    carried = skeleton.fk(start)
    out = 1.0 if mug.world(carried, skeleton)[0][0][0] >= root[0] else -1.0
    aside = out * max(0.0, lowest - low)
    return [(np.array([root[0] + aside, root[1] - 0.35 * reach, max(low, lowest)]), 'held')] + grid


def stool_depth(points):
    """How far points of a guest on a stool reach into the furniture: the table top, its pedestals, the benches and their
    legs, seen from the stool (TAVERN_STOOL_DISTANCE along the table from its middle; the guest looks along -y to the end of
    the table). The boxes are those of furniture_depth in check_tavern_stools_863.py."""
    table = np.stack([points[:, 0], STOOL_DISTANCE + points[:, 1], points[:, 2]], axis=1)
    boxes = [((-0.323, 0.323), (-0.588, 0.588), (0.37, 0.4425))]
    for s in (1, -1):
        boxes.append(((-0.193, 0.193), (0.135, 0.521) if s > 0 else (-0.521, -0.135), (0.0, 0.38)))
        boxes.append(((0.3236, 0.4986) if s > 0 else (-0.4986, -0.3236), (-0.656, 0.656), (0.202, 0.2575)))
        for e in (1, -1):
            boxes.append(((s * BENCH_OFFSET - 0.042, s * BENCH_OFFSET + 0.042), (0.515, 0.588) if e > 0 else (-0.588, -0.515), (0.0, 0.21)))
    worst = 0.0
    for (x0, x1), (y0, y1), (z0, z1) in boxes:
        low, high = np.array([x0, y0, z0]), np.array([x1, y1, z1])
        inside = np.all((table > low) & (table < high), axis=1)
        if inside.any():
            q = table[inside]
            worst = max(worst, float(np.minimum(q - low, high - q).min(axis=1).max()))
    return worst


def pose_depth(skeleton, local, mug, vertices, weights):
    """How far the body and its mug reach into the furniture in a one-frame pose, at both ends of the level scale, and how
    far the body leaves the room the seated clips of the model had before (the footprints of the room, TAVERN_STOOL_BODIES
    and TAVERN_BENCH_REACH_*, stay right)."""
    _, _, points = mug.world(skeleton.fk(local), skeleton)
    body = rest.skin_vertices(skeleton, local, vertices, weights)
    if SEAT['stool']:
        depth = max(stool_depth(np.concatenate((body[0], points[0])) * level) * 1.0 for level in (seats.LEVEL_SCALE_LOW, seats.LEVEL_SCALE_HIGH))
    else:
        depth = seats.level_depth(np.concatenate((body, points), axis=1))
    # The room of the body (the footprint of a stool guest, the reach of a bench guest) and the seat of the stool are hard
    # limits: a pose that leaves them counts as far deeper than any furniture depth that is allowed
    excess = 0.0
    if SEAT['envelope'] is not None:
        front, back, half = SEAT['envelope']
        for level in (seats.LEVEL_SCALE_LOW, seats.LEVEL_SCALE_HIGH):
            scaled = body[0] * level
            excess = max(excess, -float(scaled[:, 1].min()) - front * level, float(scaled[:, 1].max()) - back * level,
                         float(np.abs(scaled[:, 0]).max()) - half * level)
    if SEAT['side'] is not None:
        excess = max(excess, float(np.abs(body[0][:, 0]).max()) - SEAT['side'])
    if SEAT['stool']:
        for level in (seats.LEVEL_SCALE_LOW, seats.LEVEL_SCALE_HIGH):
            scaled = body[0] * level
            r = np.hypot(scaled[:, 0], scaled[:, 1])
            z = scaled[:, 2]
            seat = (r < STOOL_RADIUS) & (z < STOOL_TOP - MAX_STOOL_SINK) & (z > STOOL_TOP - 0.035)
            post = (r < STOOL_POST_RADIUS) & (z < STOOL_TOP - 0.035)
            if seat.any() or post.any():
                excess = max(excess, 0.01)
    return depth if excess <= ENVELOPE_TOLERANCE else max(depth, HARD_LIMIT + excess)


def seat_envelope(skeleton, vertices, weights):
    """The room the body takes in all seated clips (front, back and half width at both ends of the level scale)."""
    front = back = half = 0.0
    for clip in seats.CLIPS:
        played = skeleton.clips[clip[0]]
        body = rest.skin_vertices(skeleton, skeleton.locals_at(played, np.linspace(0.0, played.length, ENVELOPE_SAMPLES)), vertices, weights).reshape(-1, 3)
        for level in (seats.LEVEL_SCALE_LOW, seats.LEVEL_SCALE_HIGH):
            front = max(front, -float(body[:, 1].min()) * level)
            back = max(back, float(body[:, 1].max()) * level)
            half = max(half, float(np.abs(body[:, 0]).max()) * level)
    return front + ENVELOPE_MARGIN, back + ENVELOPE_MARGIN, half + ENVELOPE_MARGIN


def limb_reach(skeleton, local, limb, mug):
    world = skeleton.fk(local)
    joints = [world[skeleton.idx[bone]][0][0] for bone in limb]
    carrier_to_foot = float(np.linalg.norm(mug.world(world, skeleton)[0][0] - joints[-1]))
    return sum(float(np.linalg.norm(joints[i + 1] - joints[i])) for i in range(len(joints) - 1)) + carrier_to_foot


def lean_forward(skeleton, local, spine, degrees):
    """The pose with the upper body bent forward by the degrees at the hip: the lowest bone of the spine turns about a point
    just above the seat of the bench (its origin moves with the turn), so the shoulders come over the table."""
    leaned = copy_pose(local)
    if degrees == 0.0:
        return leaned
    bone = spine[0]
    index = skeleton.idx[bone]
    world = skeleton.fk(leaned)
    origin = world[index][0][0]
    pivot = np.array([origin[0], origin[1], min(origin[2], seats.BENCH_TOP / SCALE + LEAN_PIVOT_HEIGHT)])
    turn = rotation_matrix(np.array([1.0, 0.0, 0.0]), math.radians(degrees))
    moved = pivot + turn @ (origin - pivot) - origin
    rest.rotate_joint(skeleton, leaned, bone, np.array([1.0, 0.0, 0.0]), np.array([math.radians(degrees)]))
    parent = skeleton.parent[index]
    position, rotation, scale = leaned[index]
    if parent >= 0:
        moved = world[parent][1][0].T @ moved / world[parent][2][0]
    leaned[index] = (position + moved[None], rotation, scale)
    return leaned


class Head(object):
    """The head surface, anatomical mouth anchors and the bone that bows it."""

    def __init__(self, skeleton, name, vertices, weights, limb, start):
        """Identify the head and verify annotated mouths against the original mesh topology."""
        world = skeleton.fk(start)
        posed = rest.skin_vertices(skeleton, start, vertices, weights)[0]
        self.indices = head_vertices(skeleton, name, weights, world[skeleton.idx[limb[0]]][0][0][2], posed, limb)
        self.vertices = np.asarray(vertices)[self.indices]
        self.weights = [weights[index] for index in self.indices]
        anchors = MOUTHS.get(name, ())
        for index, expected in anchors:
            assert np.allclose(vertices[index], expected, atol=1e-5, rtol=0.0), (name, 'mouth topology changed', index)
        self.mouth_vertices = np.asarray([vertices[index] for index, _ in anchors])
        self.mouth_weights = [weights[index] for index, _ in anchors]
        self.drink_turns = ()
        totals = {}
        for index in self.indices:
            for bone, weight in weights[index]:
                totals[bone] = totals.get(bone, 0.0) + weight
        bone = max(totals, key=totals.get)
        # A head bows at its neck: the parent of the bone of the head, unless that parent also carries the limb
        ancestors = set()
        walk = skeleton.idx[limb[0]]
        while walk >= 0:
            ancestors.add(walk)
            walk = skeleton.parent[walk]
        parent = skeleton.parent[bone]
        pivot = parent if parent >= 0 and parent not in ancestors else bone
        self.pivot = skeleton.names[pivot]
        self.movable = (pivot not in ancestors) and (self.pivot not in limb)

    def face(self, skeleton, local):
        """Return the posed collision surface with its anatomical mouth when annotated."""
        mouth = self.mouths(skeleton, local)[0] if len(self.mouth_vertices) else None
        return Face(rest.skin_vertices(skeleton, local, self.vertices, self.weights)[0], mouth)

    def mouths(self, skeleton, local):
        """Follow the same lip vertices through skinning in every frame of a clip."""
        if len(self.mouth_vertices):
            return rest.skin_vertices(skeleton, local, self.mouth_vertices, self.mouth_weights).mean(axis=1)
        return np.asarray([Face(points).mouth() for points in rest.skin_vertices(skeleton, local, self.vertices, self.weights)])


def mug_rim(skeleton, local, mug):
    foot, axis, points = mug.world(skeleton.fk(local), skeleton)
    return foot[0] + axis[0] * mug.length, points[0]


def bow_head(skeleton, local, head, mouth, rim, share):
    """Turn the head at its neck so that the mouth comes a share of the way to the rim."""
    world = skeleton.fk(local)
    pivot = world[skeleton.idx[head.pivot]][0][0]
    turn_axis, angle = turn_between((mouth - pivot) / np.linalg.norm(mouth - pivot), (rim - pivot) / np.linalg.norm(rim - pivot))
    rest.rotate_joint(skeleton, local, head.pivot, turn_axis, np.array([angle * share]))


def drink_pose(skeleton, resting, limb, mug, head, gap, towards, tip, depth_of=None):
    """The pose of the drink: the rim of the mug at the mouth, the mug leaning back in front of the face. A limb too short
    to bring the mug to the mouth meets the mouth half way: the head bows to the mug, until its mouth moved max_bow."""
    drinking = copy_pose(resting)
    for bone, degrees in head.drink_turns:
        rest.rotate_joint(skeleton, drinking, bone, np.array([0.0, 0.0, 1.0]), np.array([math.radians(degrees)]))
    axis = tipped(tip, towards)
    start_mouth = head.face(skeleton, resting).mouth()
    for _ in range(MOUTH_ROUNDS):
        mouth = head.face(skeleton, drinking).mouth()
        rim = mouth - towards * (gap + 0.5 * mug.radius * math.cos(math.radians(tip)))
        for _ in range(2):
            solve(skeleton, drinking, limb, mug, rim - axis * mug.length, axis)
        reached, _ = mug_rim(skeleton, drinking, mug)
        if np.linalg.norm(reached - rim) <= MOUTH_REACH or not head.movable:
            break
        if np.linalg.norm(mouth - start_mouth) >= head.max_bow:
            break
        bowed = copy_pose(drinking)
        bow_head(skeleton, bowed, head, mouth, reached + (mouth - rim), 0.5)
        # The head never bows into the table
        if depth_of is not None and depth_of(bowed) > MAX_WAY_DEPTH:
            break
        drinking = bowed
    mouth = head.face(skeleton, drinking).mouth()
    reached, points = mug_rim(skeleton, drinking, mug)
    face = head.face(skeleton, drinking)
    _, sip_points = mug_rim(skeleton, sipped(skeleton, drinking, limb, 1.0, towards, mug), mug)
    in_face = max(face.inside(points), face.inside(sip_points))
    return drinking, float(np.linalg.norm(reached - mouth)), in_face


def author_clip(skeleton, name, clip, mug, vertices, weights, body_rig):
    """Solve one calm sip, rejecting a seated pose that cannot rest its mug on the table."""
    seated = clip == 'SitDrink'
    SEAT['inset'] = TABLE_INSETS.get(name, TABLE_INSET)
    old = skeleton.clips[clip]
    start = skeleton.locals_at(old, np.zeros(1))
    # The mug shows at its own size: a clip that shrank the weapon bone to hide a weapon (Troll) does not shrink the mug
    index = skeleton.idx[mug.bone]
    if not mug.passive:
        start[index] = (start[index][0], start[index][1], skeleton.rest_s[index][None].copy())
    limb = limb_of(skeleton, name, mug)
    reach = limb_reach(skeleton, start, limb, mug)
    posed = rest.skin_vertices(skeleton, start, vertices, weights)[0]

    # The parts of the body that do not move with the limb
    moving = {skeleton.idx[bone] for bone in limb}
    for index in skeleton.topo:
        if skeleton.parent[index] in moving:
            moving.add(index)
    still = posed[[index for index, row in enumerate(weights) if sum(w for b, w in row if b in moving) < 0.5]]

    # A seated guest whose limb does not reach the table bends forward over it, as little as it needs
    lean = 0.0
    upright = start
    carrying = set()
    walk = skeleton.parent[skeleton.idx[limb[0]]]
    while walk >= 0:
        carrying.add(skeleton.names[walk])
        walk = skeleton.parent[walk]
    spine = [bone for bone in seats.upper_chain(skeleton, body_rig, [])[0] if bone in carrying]
    if seated and spine:
        for degrees in LEANS:
            trial = lean_forward(skeleton, start, spine, degrees)
            candidates = rest_targets(skeleton, trial, limb, mug, True, reach, still)
            if not candidates:
                continue
            point, kind = candidates[0]
            # The limb really brings the upright mug onto the table (a hand mount holds the mug above the hand)
            if kind == 'table' and solve(skeleton, copy_pose(trial), limb, mug, point, np.array([0.0, 0.0, 1.0])) <= MAX_REST_ERROR:
                start, lean = trial, degrees
                break
    head = Head(skeleton, name, vertices, weights, limb, start)
    head.drink_turns = DRINK_NECK_TURNS.get((name, clip), ())
    head.max_bow = MAX_BOW_SHARE * float(np.ptp(posed[:, 2]))

    # The pause: the mug upright on its support. Where the limb would reach into the table, the mug stands a little further
    # out or to the side and the inner joints of the limb swing up
    seats.SCENE['whole_bench'] = name in seats.LARGE_MODELS
    up = np.array([0.0, 0.0, 1.0])
    side = 1.0 if skeleton.fk(start)[skeleton.idx[limb[0]]][0][0][0] >= float(np.median(posed[:, 0])) else -1.0
    found = None
    rest_limit = MAX_REST_DEPTH
    targets = rest_targets(skeleton, start, limb, mug, seated, reach, still)
    if not targets:
        raise ValueError('%s %s has no reachable mug place on the table; its seated pose or rig needs repair' % (name, clip))
    for order, (point, kind) in enumerate(targets):
        for swing in SWINGS:
            trial = copy_pose(start)
            error = solve(skeleton, trial, limb, mug, point, up, swing)
            depth = pose_depth(skeleton, trial, mug, vertices, weights) if seated else 0.0
            # A resting mug in the head counts like one deep in the furniture
            depth = max(depth, head.face(skeleton, trial).inside(mug_rim(skeleton, trial, mug)[1]) - MAX_MUG_IN_FACE + rest_limit)
            score = (max(depth, rest_limit) + 10.0 * max(error, MAX_REST_ERROR), order, abs(swing))
            if found is None or score < found[0]:
                found = (score, trial, point, error, depth, swing, kind)
            if score[0] <= rest_limit + 10.0 * MAX_REST_ERROR:
                break
        if found[0][0] <= rest_limit + 10.0 * MAX_REST_ERROR:
            break
    _, resting, support, rest_error, rest_depth, swing, carrier = found
    if seated and (rest_error > MAX_REST_ERROR or rest_depth > MAX_CLEAR_DEPTH):
        raise ValueError('%s %s cannot rest the mug on the table: error %.6f, obstruction %.6f' %
                         (name, clip, rest_error, rest_depth))

    # The drink: the mug moves out until no part of it is in the head
    best = None
    lifted = copy_pose(upright)
    solve(skeleton, lifted, limb, mug, support, up)
    # The mug comes to the mouth from the front; where the mouth is so low that a mug in front of it stands in the table,
    # it comes from the side of the limb, or between the two
    approaches = (('front', np.array([0.0, 1.0, 0.0])), ('side', np.array([-side, 0.0, 0.0])),
                  ('corner', unit(np.array([-side, 1.0, 0.0]))), ('behind', unit(np.array([-side, -1.0, 0.0]))))
    if (name, clip) in DRINK_APPROACHES:
        approaches = tuple((approach, np.asarray(direction)) for approach, direction in DRINK_APPROACHES[(name, clip)])

    def depth_of(pose):
        return pose_depth(skeleton, pose, mug, vertices, weights)
    for approach, towards in approaches:
        # A mouth just above the table drinks with the mug nearly level, so that the wide mug stays over the table
        for tip in DRINK_TIPS:
            for gap in MOUTH_GAP_STEPS:
                drinking, rim_distance, in_face = drink_pose(skeleton, lifted, limb, mug, head, gap, towards, tip,
                                                             depth_of if seated else None)
                depth = pose_depth(skeleton, drinking, mug, vertices, weights) if seated else 0.0
                failed = in_face > MAX_MUG_IN_FACE or depth > MAX_WAY_DEPTH or rim_distance > MAX_RIM_DISTANCE
                excess = max(in_face - MAX_MUG_IN_FACE, 0.0) + max(depth - MAX_WAY_DEPTH, 0.0)
                result = (failed, excess, rim_distance, gap, drinking, in_face, approach, towards, depth, tip)
                if best is None or result[:3] < best[:3]:
                    best = result
                if in_face <= MAX_MUG_IN_FACE:
                    break
            if not best[0]:
                break
        if not best[0]:
            break
    _, _, rim_distance, gap, drinking, in_face, approach, towards, drink_depth, tip = best
    drink_foot, drink_axis, _ = mug.world(skeleton.fk(drinking), skeleton)
    pivot = [skeleton.idx[head.pivot]] if head.movable else []
    pivot = sorted(set(pivot) | {skeleton.idx[bone] for bone, _ in head.drink_turns})
    # The bones that go from the rest to the drink with the way: the head and a spine that straightens up again
    pivot = sorted(set(pivot) | ({skeleton.idx[bone] for bone in spine} if lean > 0.0 else set()))

    # The way: the foot of the mug rises from the support and comes to the mouth, the mug tips on the way and the head
    # bows with it; on a way that passes through the face the mug keeps further forward
    shares = np.linspace(0.0, 1.0, WAY_STEPS)
    best_way = None
    for arc, bulge in [(arc, bulge) for arc in WAY_ARCS for bulge in WAY_BULGES]:
        poses = [resting]
        for share in shares[1:]:
            pose = copy_pose(poses[-1])
            moved = blend(resting, drinking, smooth(share), pivot)
            for index in pivot:
                pose[index] = moved[index]
            # The rim goes from its place over the support to the mouth (so that it comes ever closer to the mouth and does
            # not rise past it while the mug still stands upright); the foot follows from the tip of the mug
            rim_rest = support + up * mug.length
            rim_drink = drink_foot[0] + drink_axis[0] * mug.length
            rise = np.array([0.0, 0.0, arc * float(np.linalg.norm(rim_drink - rim_rest))])
            leaning = smooth((share - 0.3) / 0.7)
            axis = up + (drink_axis[0] - up) * leaning
            axis /= np.linalg.norm(axis)
            rim = rim_rest + (rim_drink - rim_rest) * share + (rise + np.array([0.0, -bulge, 0.0])) * 6.75 * share * (1.0 - share) ** 2
            foot = rim - axis * mug.length
            solve(skeleton, pose, limb, mug, foot, axis)
            poses.append(pose)
        # The clip blends two steps between their keys: the half way between them counts too. A way that reaches into the
        # table or the face ends at the last step that is still clear: the mug comes as close to the mouth as the table and
        # the head let it (a body whose mouth is below or beyond the reach of its limb)
        moved_bones = sorted({skeleton.idx[bone] for bone in limb + [mug.bone]} | set(pivot))
        clear, cut, strict = len(poses) - 1, None, 0.0
        for index in range(1, len(poses)):
            depth = pose_depth(skeleton, poses[index], mug, vertices, weights) if seated else 0.0
            face_share = head.face(skeleton, poses[index]).inside(mug_rim(skeleton, poses[index], mug)[1])
            if depth > MAX_CLEAR_DEPTH or face_share > MAX_CLEAR_FACE:
                clear, cut = index - 1, (('depth', depth) if depth > MAX_CLEAR_DEPTH else ('face', face_share))
                break
            half = pose_depth(skeleton, blend(poses[index - 1], poses[index], 0.5, moved_bones), mug, vertices, weights) if seated else 0.0
            if half > MAX_HALF_DEPTH:
                clear, cut = index - 1, ('half', half)
                break
            strict = max(strict, max(face_share - MAX_MUG_IN_FACE, 0.0) + max(max(depth, half) - MAX_WAY_DEPTH, 0.0))
        clear = max(clear, 1)
        # The rim comes ever further from its place on the support until the end of the way: it does not rise past the
        # mouth (or past the end of a way cut short) and come back towards its place
        away = [float(np.linalg.norm(mug_rim(skeleton, pose, mug)[0] - mug_rim(skeleton, poses[0], mug)[0])) for pose in poses[:clear + 1]]
        overshoot = max(max(away[:index + 1]) - away[index] for index in range(len(away)))
        score = (max(overshoot - MAX_OVERSHOOT, 0.0), -clear, strict, arc, bulge)
        if best_way is None or score < best_way[0]:
            best_way = (score, poses, arc, bulge, clear, cut)
        if score[0] <= 0.0 and cut is None and strict <= 0.0:
            break
    _, poses, arc, bulge, clear, cut_by = best_way
    shortened = 1.0
    if clear < len(poses) - 1:
        clear = max(clear, 1)
        shortened = shares[clear]
        # The shortened way keeps its steps evenly spread: each step blends the two solved steps around it
        moved_bones = sorted({skeleton.idx[bone] for bone in limb + [mug.bone]} | set(pivot))
        kept = poses[:clear + 1]
        poses = []
        for share in shares:
            place = share * clear
            low = int(min(clear - 1, math.floor(place)))
            poses.append(blend(kept[low], kept[low + 1], place - low, moved_bones))
    drinking = poses[-1]
    # The sip tips the mug only as far as the furniture, the stool and the head let it (a slime tips its whole body)
    sip_share = 1.0
    for sip_share in (1.0, 0.5, 0.25, 0.0):
        tipped_pose = sipped(skeleton, drinking, limb, sip_share, towards, mug)
        if ((pose_depth(skeleton, tipped_pose, mug, vertices, weights) if seated else 0.0) <= MAX_CLEAR_DEPTH and
                head.face(skeleton, tipped_pose).inside(mug_rim(skeleton, tipped_pose, mug)[1]) <= MAX_CLEAR_FACE):
            break
    reached, points = mug_rim(skeleton, drinking, mug)
    face = head.face(skeleton, drinking)
    rim_distance = float(np.linalg.norm(reached - face.mouth()))
    in_face = max(face.inside(points), face.inside(mug_rim(skeleton, sipped(skeleton, drinking, limb, sip_share, towards, mug), mug)[1]))
    drink_depth = pose_depth(skeleton, drinking, mug, vertices, weights) if seated else 0.0

    times = key_times()
    way, sip = phase(times)
    local = seats.hold(start, len(times))
    bones = sorted({skeleton.idx[bone] for bone in limb + [mug.bone]} | set(pivot))
    for frame, (share, extra) in enumerate(zip(way, sip)):
        place = share * (WAY_STEPS - 1)
        low = int(min(WAY_STEPS - 2, math.floor(place)))
        weight = place - low
        pose = blend(poses[low], poses[low + 1], weight, bones)
        if extra * sip_share > 0.0:
            pose = sipped(skeleton, pose, limb, extra * sip_share, towards, mug)
        for index in bones:
            p, q, s = local[index]
            p[frame], q[frame], s[frame] = pose[index][0][0], pose[index][1][0], pose[index][2][0]
    frames = skeleton.fk(local)
    feet_way, axes, points = mug.world(frames, skeleton)
    rims = feet_way + axes * mug.length
    faces = [Face(p) for p in rest.skin_vertices(skeleton, local, head.vertices, head.weights)]
    # The body with its mug against the furniture (seated) or the floor (standing)
    body = np.concatenate((rest.skin_vertices(skeleton, local, vertices, weights), points), axis=1)
    seats.SCENE['whole_bench'] = name in seats.LARGE_MODELS
    furniture = max(pose_depth(skeleton, [(p[i:i + 1], q[i:i + 1], c[i:i + 1]) for p, q, c in local], mug, vertices, weights)
                    for i in range(len(times))) if seated else 0.0
    report = {'shortened': shortened, 'cut_by': cut_by, 'sip_share': sip_share, 'tip': tip, 'approach': approach, 'drink_depth': drink_depth, 'swing': swing, 'arc': arc, 'rest_depth': rest_depth, 'table_depth': furniture, 'mug_lowest': float(points[:, :, 2].min()),'limb': limb, 'head_pivot': head.pivot if head.movable else None, 'lean': lean, 'support': carrier,
              'support_point': support.tolist(), 'rest_error': rest_error, 'rim_to_mouth': rim_distance, 'gap': gap,
              'bulge': bulge, 'mug_in_face': in_face, 'reach': reach,
              'most_in_face': max(face.inside(frame_points) for face, frame_points in zip(faces, points)),
              'fastest': float((np.linalg.norm(np.diff(rims, axis=0), axis=1) / np.diff(times)).max())}
    block = seats.clip_xml(skeleton, local, times, clip, CYCLE)
    if mug.passive:
        # A passive Weapon_R gets no track (it keeps its rest pose under its parent)
        block = re.sub(r'<track bone="' + seats.MUG_BONE + r'"><keyframes>.*?</keyframes></track>\s*', '', block, flags=re.S)
        assert seats.MUG_BONE + '"' not in block
    return block, local, times, report


def blend(first, second, weight, bones):
    pose = copy_pose(first)
    for index in bones:
        q = seats.slerp(first[index][1], second[index][1], np.array([weight]))
        pose[index] = (first[index][0] + (second[index][0] - first[index][0]) * weight, q, first[index][2])
    return pose


def sipped(skeleton, pose, limb, share, towards, mug):
    """The pose with the mug tipped a little further towards the face about its rim, which stays at the mouth: the limb
    lifts the bottom of the mug."""
    tilted = copy_pose(pose)
    if share <= 0.0:
        return tilted
    foot, axis, _ = mug.world(skeleton.fk(tilted), skeleton)
    rim = foot[0] + axis[0] * mug.length
    turned = rotation_matrix(unit(np.cross(np.array([0.0, 0.0, 1.0]), towards)), math.radians(SIP_TIP) * share) @ axis[0]
    solve(skeleton, tilted, limb, mug, rim - turned * mug.length, turned)
    return tilted


NORMAL_WAY = {'WAY_STEPS': WAY_STEPS, 'MAX_CLEAR_FACE': MAX_CLEAR_FACE, 'MAX_HALF_DEPTH': MAX_HALF_DEPTH}


# Reject partial solver results before they can replace the game's complete drinking clips.
def validate_report(name, report):
    problems = []
    for clip in ('Drink', 'SitDrink'):
        measured = report[clip]
        if clip == 'SitDrink' and measured['support'] != 'table':
            problems.append('%s rests on %s instead of the table' % (clip, measured['support']))
        if measured['rest_error'] > MAX_REST_ERROR:
            problems.append('%s misses its resting place by %.6f' % (clip, measured['rest_error']))
        if measured['shortened'] < 1.0:
            problems.append('%s completes only %.4f of its lift (%s)' % (clip, measured['shortened'], measured['cut_by']))
        if measured['rim_to_mouth'] > MAX_RIM_DISTANCE:
            problems.append('%s rim is %.6f from the mouth (maximum %.6f)' % (clip, measured['rim_to_mouth'], MAX_RIM_DISTANCE))
    if problems:
        raise ValueError('Incomplete calm drink cycle for %s: %s' % (name, '; '.join(problems)))


# Author both clips and publish their skeleton XML only when both complete the required cycle.
def author(source, mesh, mug_mesh, destination):
    skeleton = feet.Skel(str(source))
    name = source.name.removesuffix('.skeleton.xml')
    globals().update(NORMAL_WAY)
    globals().update(FINE_WAYS.get(name, {}))
    vertices, _, weights = rest.mesh_data(mesh)
    mug_points = rest.mesh_data(mug_mesh)[0]
    mug = Mug(skeleton, name, mug_points, read_limb_mounts())
    blocks = []
    report = {'model': name}
    body_rig = seats.rig.config(name, seats.rig.Skeleton(str(source)))
    table = (ROOT / 'source' / 'rooms' / 'RoomTavern.cpp').read_text(encoding='utf-8').split('TAVERN_STOOL_BODIES[] =')[1].split('};')[0]
    bodies = {mesh_name: tuple(float(v) for v in values)
              for mesh_name, values in ((row[0], row[1:]) for row in re.findall(r'\{ "([^"]+)", [0-9]+, ([0-9.]+)f, ([0-9.]+)f, ([0-9.]+)f \}', table))}
    SEAT['stool'] = mesh.name.removesuffix('.xml') in bodies
    # A guest of a stool keeps the footprint of its body (TAVERN_STOOL_BODIES: front, back, half width at level scale 1); a
    # guest of a bench the reach of all bench guests around their table at the largest level scale
    # (TAVERN_BENCH_REACH_ACROSS behind the bench, TAVERN_BENCH_REACH_ALONG beside its outermost place)
    places = BENCH_PLACES.get(name, 1)
    SEAT['envelope'] = bodies[mesh.name.removesuffix('.xml')] if SEAT['stool'] else (
        float('inf'), (BENCH_REACH_ACROSS - BENCH_OFFSET) / seats.LEVEL_SCALE_HIGH,
        (BENCH_REACH_ALONG - (2.0 - 0.5 * places) * seats.SEAT_SPACING) / seats.LEVEL_SCALE_HIGH)
    SEAT['side'] = SIDE_LIMITS.get(name)
    report['stool'] = SEAT['stool']
    for clip in ('Drink', 'SitDrink'):
        if clip == 'Drink':
            saved, SEAT['envelope'] = SEAT['envelope'], None
        block, _, _, measured = author_clip(skeleton, name, clip, mug, vertices, weights, body_rig)
        if clip == 'Drink':
            SEAT['envelope'] = saved
        blocks.append(block)
        report[clip] = measured
    validate_report(name, report)
    text = source.read_text(encoding='utf-8')
    head_part = text[:text.index('<animations>')]
    destination.write_text(head_part + '<animations>\n' + '\n'.join(blocks) + '\n</animations>\n</skeleton>\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('names', nargs='+')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for item in args.names:
        name, _, mesh_name = item.partition(':')
        report = author(args.input / (name + '.skeleton.xml'), args.input / ((mesh_name or name + '.mesh') + '.xml'),
                        args.input / 'TavernMug.mesh.xml', args.output / (name + '.drink.skeleton.xml'))
        (args.output / (name + '.drink.json')).write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
        print(name, {clip: {key: (round(value, 3) if isinstance(value, float) else value) for key, value in report[clip].items()
                            if key in ('support', 'rest_error', 'rim_to_mouth', 'gap', 'mug_in_face', 'most_in_face', 'fastest', 'lean', 'bulge', 'head_pivot', 'table_depth', 'mug_lowest')}
                     for clip in ('Drink', 'SitDrink')}, flush=True)


if __name__ == '__main__':
    main()
