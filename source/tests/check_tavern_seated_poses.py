#!/usr/bin/env python3
"""Owner decision 830 (b): a grey creature lay deformed through a tavern table and the innkeeper lay over the counter.

The seated clips themselves stay out of the furniture (check_tavern_seat_clips), but only in the direction they were made
for, across the table, and only without anything on top of them. What is checked (no compiler, no game):
  facing     games and slap duels turn a seated guest across its table (getFacingDirection), not towards a partner that
             sits further along the table or on the same bench; the turn that would need is larger than the 35 degrees
             a seated clip may turn (SEAT_TURNS of the clip author); SitDrink only plays on the seat
  reactions  a guest that plays a seated clip gets no reaction clip, no motion of the whole body (hop, squash, sit, lie,
             turn) and no prop, and a running one ends when it sits down; only emotes and particles stay
  rotation   a lie or turn motion is not taken back after someone else turned the creature (a walk step, a seat): a
             model of the node rotations shows that the old way left the creature tipped by up to 80 degrees and the
             new one leaves it upright and looking where the server said
  innkeeper  in Idle, Pour and Cheer the head never hangs forward of the vertical, the hands and the jug rest on the
             counter top instead of in it, and the body stays behind the back edge of the top (needs OgreXMLConverter
             on the PATH or in OGRE_XML_CONVERTER; skipped with a note otherwise)

Call from the repository root:
  python source/tests/check_tavern_seated_poses.py
"""
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))


def read(path):
    return (ROOT / path).read_text(encoding='utf-8', errors='replace')


def extract(text, head):
    start = text.index(head)
    depth = 0
    for index in range(text.index('{', start), len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError(head)


def constant(text, name):
    return float(re.search(r'const float ' + name + r' = ([0-9.]+)f;', text).group(1))


# 1. Facing of seated guests
def check_facing():
    room = read('source/rooms/RoomTavern.cpp')
    facing = extract(room, 'Ogre::Vector3 RoomTavern::getFacingDirection(')
    assert 'isOnSeat(creature, own->first, own->second.mPlaces)' in facing and 'return getAcrossTableDirection(own->first);' in facing
    assert 'Ogre::Vector3 getFacingDirection(const Creature& creature, const Creature& partner);' in read('source/rooms/RoomTavern.h')
    show = extract(room, 'void RoomTavern::showSpotState(')
    assert 'getFacingDirection(*creature, *opponent)' in show, 'a game turns the seated guest towards its partner'
    drinking = show[show.index('case TavernGuestState::drinking:'):show.index('case TavernGuestState::ko:')]
    assert 'if(seated)' in drinking and 'EntityAnimation::drink_anim' in drinking, 'SitDrink plays off the seat'
    duel = extract(room, 'void RoomTavern::playDuelTurn(')
    assert 'getFacingDirection(*slapper, *target)' in duel and 'getFacingDirection(*target, *slapper)' in duel
    assert 'directionTo(*slapper' not in duel and 'directionTo(*target' not in duel
    # The turn a guest would need towards its partner, from the seat layout of the room
    import author_tavern_seats as seats
    offset = constant(room, 'TAVERN_BENCH_OFFSET')
    spacing = constant(room, 'TAVERN_SEAT_SPACING')
    places = [(1.5 - i) * spacing for i in range(4)]
    worst_opposite = max(math.degrees(math.atan2(abs(a - b), 2 * offset)) for a in places for b in places)
    assert worst_opposite > max(seats.SEAT_TURNS), worst_opposite
    print('facing ok: a partner on the other bench needs up to %.0f degrees, the same bench 90, a seated clip allows %.0f'
          % (worst_opposite, max(seats.SEAT_TURNS)))


# 2. Reactions on seated guests
def check_reactions():
    cpp = read('source/render/CreatureReactions.cpp')
    helper = extract(cpp, 'static bool sitsAtTable(')
    assert 'EntityAnimation::isSeatClip(animState->getAnimationName())' in helper
    start = extract(cpp, 'bool CreatureReactions::startReaction(')
    assert 'const bool seated = sitsAtTable(creature);' in start
    assert '(!event.mWhileWorking || !variant.mClip.empty()) && !seated;' in start, 'a reaction clip plays on a seated guest'
    assert '!playsHurtWalk && !seated)' in start, 'a motion moves a seated guest'
    assert '!creature->isMoving() && !seated &&' in start, 'a prop is shown on a seated guest'
    update = extract(cpp, 'bool CreatureReactions::updateReaction(')
    block = update[update.index('if(sitsAtTable(creature))'):]
    assert block.index('stopClip(reaction, creature);') < block.index('updateLate(reaction, creature);')
    assert block.index('clearMotion(reaction, creature);') < block.index('updateLate(reaction, creature);')
    motion = extract(cpp, 'void CreatureReactions::applyMotion(')
    assert '!node->getOrientation().equals(reaction.mMotionLastOrientation, Ogre::Radian(static_cast<Ogre::Real>(TURN_TOLERANCE)))' in motion
    assert 'reaction.mMotionTurnLost = true;' in motion and 'if(reaction.mMotionTurnLost)' in motion
    assert motion.rstrip().endswith('reaction.mMotionLastOrientation = node->getOrientation();\n}')
    header = read('source/render/CreatureReactions.h')
    assert 'Ogre::Quaternion mMotionLastOrientation;' in header and 'bool mMotionTurnLost;' in header
    assert 'mMotionLastOrientation(Ogre::Quaternion::IDENTITY),' in header and 'mMotionTurnLost(false),' in header
    print('reactions ok: seated guests show emotes and particles only')


def rotation(angle, axis):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * k @ k


def rotation_to(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    if np.linalg.norm(v) < 1e-12:
        return np.eye(3)
    return rotation(math.atan2(np.linalg.norm(v), float(np.dot(a, b))), v)


def orient_toward(node, direction):
    # RenderManager::rrOrientEntityToward: the shortest turn of the forward axis (-y) onto the direction
    return rotation_to(node @ np.array([0.0, -1.0, 0.0]), direction) @ node


# 3. A lie motion, a turn of the server in the middle and the end of the motion, the old and the new way
def check_rotation():
    lie = math.radians(80.0)
    for turn in (30.0, 90.0, 150.0):
        node = np.eye(3)
        axis = node @ np.array([0.0, -1.0, 0.0])
        node = rotation(lie, axis) @ node
        last = node.copy()
        target = np.array([math.sin(math.radians(turn)), -math.cos(math.radians(turn)), 0.0])
        node = orient_toward(node, target)
        old = rotation(-lie, axis) @ node
        old_tilt = math.degrees(math.acos(np.clip((old @ [0, 0, 1])[2], -1, 1)))
        # New: the orientation changed, so the share is not taken back; a tilt that survived is removed at once
        assert not np.allclose(node, last)
        up = node @ np.array([0.0, 0.0, 1.0])
        tilt = math.acos(np.clip(up[2], -1, 1))
        assert abs(tilt - lie) < 0.01, 'the turn of the server keeps the tilt'
        new = rotation_to(up, np.array([0.0, 0.0, 1.0])) @ node
        assert abs((new @ [0, 0, 1])[2] - 1.0) < 1e-9, 'the creature stays tipped over'
        forward = new @ np.array([0.0, -1.0, 0.0])
        assert np.allclose(forward, target, atol=1e-9), 'the creature does not look where the server said'
        assert old_tilt > 10.0, (turn, old_tilt)
        print('rotation ok: turned %3.0f degrees during a lie, the old way left a tilt of %4.1f degrees, now 0' % (turn, old_tilt))


# 4. The innkeeper at its counter
COUNTER_TOP = 0.527
COUNTER_TOP_UNDERSIDE = 0.47
COUNTER_FRONT = -0.335
COUNTER_TOP_BACK = -0.06
COUNTER_HALF_WIDTH = 0.514
MAX_BODY_OVER_TOP = 0.01
MAX_FORWARD_HEAD = 0.5
MIN_IDLE_HEAD_BACK = 5.0
MAX_TOP_DEPTH = 0.003


def check_innkeeper():
    converter = os.environ.get('OGRE_XML_CONVERTER', 'OgreXMLConverter')
    if shutil.which(converter) is None and not Path(converter).is_file():
        print('innkeeper skipped: no OgreXMLConverter')
        return
    import author_rest_poses as rest
    import fix_walk_feet as feet
    out = ROOT / 'out' / 'tavern-seated-poses'
    out.mkdir(parents=True, exist_ok=True)
    for name in ('Innkeeper.skeleton', 'Innkeeper.mesh', 'TavernCounter.mesh'):
        subprocess.run([converter, '-q', str(ROOT / 'models' / name), str(out / (name + '.xml'))],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=60, check=True)
    counter, faces, _ = rest.mesh_data(out / 'TavernCounter.mesh.xml')
    # The top boards: flat faces over the whole width above the underside; the hands and the jug rest on them
    tops = [float(counter[index, 2].max()) for index, material in faces
            if material == 'TavernCounterWood' and np.ptp(counter[index, 2]) < 1e-4 and
            counter[index, 2].min() > 0.5 and np.ptp(counter[index, 0]) > 0.9]
    assert tops and abs(max(tops) - 0.53) < 0.002 and abs(min(tops) - COUNTER_TOP) < 0.002, ('the counter top moved', tops)
    assert max(float(counter[index, 1].max()) for index, material in faces if material == 'TavernCounterWood' and
               np.ptp(counter[index, 2]) < 1e-4 and counter[index, 2].min() > 0.5 and np.ptp(counter[index, 0]) > 0.9) \
        <= COUNTER_TOP_BACK + 0.007, 'the counter top reaches further back'
    skeleton = feet.Skel(str(out / 'Innkeeper.skeleton.xml'))
    vertices, _, weights = rest.mesh_data(out / 'Innkeeper.mesh.xml')
    limbs = {skeleton.idx[b] for b in ('UpperArm_R', 'Forearm_R', 'Hand_R', 'UpperArm_L', 'Forearm_L', 'Hand_L', 'Jug')}
    body = np.array([sum(w for bone, w in row if bone not in limbs) >= 0.5 for row in weights])
    for clip in ('Idle', 'Pour', 'Cheer'):
        played = skeleton.clips[clip]
        times = np.linspace(0.0, played.length, 97)
        local = skeleton.locals_at(played, times)
        up = skeleton.fk(local)[skeleton.idx['Head']][1][:, :, 2]
        forward = np.degrees(np.arctan2(-up[:, 1], up[:, 2]))
        assert forward.max() <= MAX_FORWARD_HEAD, (clip, 'the head hangs forward over the counter', forward.max())
        if clip == 'Idle':
            assert forward.max() <= -MIN_IDLE_HEAD_BACK, ('the innkeeper looks down onto the counter', forward.max())
        points = rest.skin_vertices(skeleton, local, vertices, weights)
        x, y, z = points[:, :, 0], points[:, :, 1], points[:, :, 2]
        inside = (z > COUNTER_TOP_UNDERSIDE) & (z < COUNTER_TOP) & (y > COUNTER_FRONT) & (y < COUNTER_TOP_BACK) & \
            (np.abs(x) < COUNTER_HALF_WIDTH)
        depth = np.where(inside, np.minimum.reduce([z - COUNTER_TOP_UNDERSIDE, COUNTER_TOP - z, COUNTER_TOP_BACK - y,
                                                    y - COUNTER_FRONT]), 0.0)
        assert depth.max() <= MAX_TOP_DEPTH, (clip, 'a hand or the jug reaches into the counter top', float(depth.max()))
        low = body[None, :] & (z < 0.56)
        front = float(y[low].min())
        assert front >= COUNTER_TOP_BACK - MAX_BODY_OVER_TOP, (clip, 'the body lies on the counter top', front)
        print('innkeeper %-5s ok: head at most %5.1f degrees forward, %d points in the top, body front at y %.3f'
              % (clip, forward.max(), int(inside.sum(axis=1).max()), front))


def main():
    check_facing()
    check_reactions()
    check_rotation()
    check_innkeeper()
    print('tavern seated poses ok')


if __name__ == '__main__':
    main()
