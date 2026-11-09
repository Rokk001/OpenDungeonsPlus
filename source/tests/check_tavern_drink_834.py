#!/usr/bin/env python3
"""Owner decisions 834, 835 and 833 (tavern): the mug in the hand, a beer of 30 seconds, the drink chain and the game, and
no guest that lies in or through a table.

What is checked (python only, no compiler, no game)
  mug        every skeleton of a visiting type holds the mug during Drink and SitDrink: on Weapon_R, or else on the limb
             mount of RenderManager (TAVERN_MUG_LIMB_MOUNTS) that the lookup of findTavernMugLimbMount finds for it; a
             limb mount stands the mug upright in the rest pose of its bone, puts its foot on the limb, keeps the mug
             above the floor in every frame of Drink and SitDrink and its size within 0.67 to 1 (decision 863: at least
             0.12 tiles tall, readable from the game camera; decision 834 had 0.35 to 1 and at most 0.35 of the height of
             a small body); every mug is 1.8 times as wide as its mesh, its length stays; the mug is attached for
             the requested clip before the clip fallback, so a skeleton without the clip still shows it; it is taken
             away only when the clip changes (a drink clip that fades out in a seat blend keeps it to the end of the
             blend, decision 863), the creature is picked up or destroyed; the seated weapon hiding never touches it
  sip        decision 901: Drink and SitDrink of every visiting skeleton are one calm sip of 5 s (ClipSecondsDrink and
             ClipSecondsSitDrink 5, water two sips, beer six): the mug stands upright on the table when seated,
             is lifted once to the mouth, the rim holds at the mouth with the mug
             in front of the face, then it goes back and pauses; no fast back and forth; Weapon_R and the hand of the
             Defender hold the mug at its middle (TAVERN_MUG_GRIP_SHIFT)
  duration   [Tavern] BeerDrinkTurns = 30 s x 1.4 turns per second = 42, WaterDrinkTurns = 10 s x 1.4 = 14; every drink starts
             with nextDrinkTurns, which reads BeerDrinkTurns for a beer the payer can pay and WaterDrinkTurns otherwise; the
             drink clips are set looping and nothing sets another clip while a guest drinks; Drink of every visiting
             skeleton starts and ends in the same pose, so the 30 s loop has no jump
  chain      D16 from the config and finishDrink: 50, 25, 12.5, 6.25 percent, at most five drinks, 1.64 drinks per visit
             on average; D5: a game with GameChancePercent 50 after the last drink, partner at the same table and of the
             same keeper; a guest that wants a game waits while such a partner still drinks (a model of the upkeep with
             two guests: before, the partner had to finish within the same turn, now every second wish gives a game)
  lying      a guest on its bench is never sent away from the use action before it got off the bench
             (keepGuestUntilItLeft in all three branches of CreatureActionUseRoom::handleJob); the tavern sets no sleep,
             death, drop or drag clip and the knocked-out clip only on the floor; the duel loser turns back to its seat
             before it goes down and the floor its lying body covers (TAVERN_LYING_BODIES, measured here on all frames of
             KnockedOut of every visiting model that is not large) is kept free of furniture; a large loser slumps on
             its seat; no sit or lie reaction plays on a tavern tile

Call from the repository root (the model parts need OgreXMLConverter on the PATH or in OGRE_XML_CONVERTER and are
skipped with a note otherwise):
  python source/tests/check_tavern_drink_834.py
"""
import math
import os
import re
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'source' / 'tests'))

TURNS_PER_SECOND = 1.4
BEER_SECONDS = 30
WATER_TURNS = 14
# The mug of a limb mount stands this close to upright in the rest pose of its bone, in degrees
MAX_MUG_TILT = 2.0
# The foot of the mug lies this close to the middle of the limb, in tiles
MAX_MUG_FOOT_GAP = 0.06
# The lowest point of the mug may sink this far below the floor in a drink clip, in tiles
MIN_MUG_FLOOR = -0.03
# First and last frame of Drink differ by at most this share of the height of the body
MAX_SEAM = 1e-3
MUG_HEIGHT = 0.18
# Decision 863: the mug of a limb mount is at least this share of the mesh, 0.12 tiles tall (0.06 on the spider before)
MIN_LIMB_MUG_SCALE = 0.67
# Decision 901: the limb mounts that are hands hold the mug at its middle, this far above its foot like Weapon_R
HAND_MOUNTS = ('Defender.skeleton', 'Spider.skeleton', 'Roach.skeleton')
GRIP_SHIFT = 0.1
# Decision 901: Drink and SitDrink are one calm sip of SIP_SECONDS (ClipSecondsDrink, ClipSecondsSitDrink), measured at
# CYCLE_SAMPLES times. The mug pauses at least MIN_PAUSE (its rim moves less than STILL, tiles), upright within
# MAX_REST_TILT degrees; it is lifted once, by at least MIN_LIFT of the height of the body, and its rim holds its place at
# the mouth (within HOLD) for at least MIN_DRINK; it moves at most MAX_SPEED_HEIGHTS body heights per second (bodies smaller
# than MIN_HEIGHT count as that tall); at most MAX_MUG_IN_FACE of it lies in the head in any frame and its rim comes within
# MAX_RIM_TO_MOUTH of the mouth. Seated, it stands on the table top within MAX_STAND_GAP at the smallest
# creature scale.
SIP_SECONDS = 5.0
CYCLE_SAMPLES = 251
STILL = 0.01
MIN_PAUSE = 1.2
MAX_REST_TILT = 5.0
MIN_LIFT = 0.15
HOLD = 0.04
MIN_DRINK = 1.2
MAX_SPEED_HEIGHTS = 3.0
MIN_HEIGHT = 0.3
MAX_MUG_IN_FACE = 0.05
MAX_RIM_TO_MOUTH = 0.06
MAX_STAND_GAP = 0.015
# Independently measured centres of the annotated mouth openings in the original mesh coordinates.
EXPECTED_MOUTHS = {'CaveHornet': (0.0, -0.189098, 0.061582),
                   'Dragon': (0.0, -0.705906, 0.957832), 'Spider': (0.0, -0.142194, 0.131078),
                   'Rat': (0.0, -0.430011, 0.145937), 'Slime': (0.0, -0.274409, 0.27),
                   'Tentacle': (0.0, -0.0146598, 0.511544),
    'Kreatur': (0.0, -0.317763, 0.472901),
    'LavaSpawn': (-5.75e-06, -0.4630071, 0.60245494),
    'Roach': (0.0, -0.20523333333333335, 0.19490566666666667),
    'Scarab': (0.0019446, -0.24109942111655863, 1.0398758589264896),
    'Wyvern': (0.0, -0.169624, 0.646443),
}
# Fixed distance of a stool from the table centre (decision 863).
STOOL_DISTANCE = 0.8
STOOL_TABLE_HALF_WIDTH = 0.323
# Decision 901(2) applies to every creature: a short limb, a held mug or a path cut short by furniture is a failed cycle.


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


def block_values(text, name):
    match = re.search(r'^\[' + name + r'\]\s*$(.*?)^\[/' + name + r'\]', text, re.M | re.S)
    assert match is not None, name
    values = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            values[words[0]] = words[1]
    return values


FLOAT = r'(-?[0-9.]+)f'


def mug_mounts(render):
    table = render[render.index('const TavernMugLimbMount TAVERN_MUG_LIMB_MOUNTS[] ='):]
    table = table[:table.index('};')]
    rows = re.findall(r'\{ "([^"]+)", "([^"]+)", ' + ', '.join([FLOAT] * 8) + r' \}', table)
    assert rows, 'no limb mounts'
    return [(s, b, np.array([float(v) for v in values[:4]]), np.array([float(v) for v in values[4:7]]), float(values[7]))
            for s, b, *values in rows]


def lying_bodies(room):
    table = room[room.index('const TavernLyingBody TAVERN_LYING_BODIES[] ='):]
    table = table[:table.index('};')]
    rows = re.findall(r'\{ "([^"]+)", ' + ', '.join([FLOAT] * 3) + r' \}', table)
    assert rows, 'no lying bodies'
    default = re.search(r'const TavernLyingBody TAVERN_LYING_BODY_DEFAULT = \{ "", ' + ', '.join([FLOAT] * 3) + r' \};', room)
    assert default is not None
    return {m: tuple(float(v) for v in values) for m, *values in rows}, tuple(float(v) for v in default.groups())


def visiting_meshes():
    found = []
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', read('config/creatures.cfg'), re.S):
        mesh = re.search(r'^\s*MeshName\s+(\S+)', block, re.M)
        tavern = re.search(r'^\s*Tavern\s+(\S+)\s+(\S+)', block, re.M)
        if (mesh is None) or (tavern is None) or (float(tavern.group(1)) <= 0.0 and float(tavern.group(2)) <= 0.0):
            continue
        if mesh.group(1) not in found:
            found.append(mesh.group(1))
    return found


def skeleton_of(mesh):
    return re.findall(rb'([A-Za-z0-9_]+)\.skeleton', (ROOT / 'models' / mesh).read_bytes())[0].decode('ascii')


def quaternion_matrix(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


# 1. The mug in the hand: the code
def check_mug_code():
    render = read('source/render/RenderManager.cpp')
    props = extract(render, 'void RenderManager::updateCreatureTavernProps(')
    assert 'EntityAnimation::isDrinkClip(anim) || fadingDrink' in props
    entity = read('source/entities/MovableGameEntity.h')
    assert 'return (clip == drink_anim) || (clip == sit_drink_anim);' in extract(entity, 'inline bool isDrinkClip(')
    assert props.index('getWeaponMount(skeleton, "R", TAVERN_MUG_MESH, mount)') < props.index('findTavernMugLimbMount(skeleton, limb)')
    # Decision 901: the hand holds the mug at its middle (Weapon_R: shifted along the x axis of the bone)
    assert re.search(r'^const Ogre::Real TAVERN_MUG_GRIP_SHIFT = 0\.1f;$', render, re.M)
    assert re.search(r'if\(hasMount\)\s*mount\.mOffset = mount\.mRotation \* Ogre::Vector3\(TAVERN_MUG_GRIP_SHIFT, 0\.0f, 0\.0f\);', props)
    assert props.index('mount.mOffset = mount.mRotation * Ogre::Vector3(TAVERN_MUG_GRIP_SHIFT') < props.index('findTavernMugLimbMount(skeleton, limb)')
    for token in ('mount.mBoneName = limb->mBone;', 'Ogre::Quaternion(limb->mW, limb->mX, limb->mY, limb->mZ)',
                  'Ogre::Vector3(limb->mOffsetX, limb->mOffsetY, limb->mOffsetZ)',
                  'mugPoint->setScale(mugScale, mugScale * TAVERN_MUG_GIRTH_SCALE, mugScale * TAVERN_MUG_GIRTH_SCALE);'):
        assert token in props, token
    lookup = extract(render, 'static bool findTavernMugLimbMount(')
    assert 'skeleton->hasBone(mount.mBone)' in lookup and 'skeleton->getName() == mount.mSkeleton' in lookup
    # The mug is attached for the clip the server asked for, before a missing clip falls back to another one
    state = extract(render, 'void RenderManager::rrSetObjectAnimationState(')
    assert state.index('updateCreatureTavernProps(dropCreature, anim);') < state.index('while (!objectEntity->getSkeleton()->hasAnimation(anim))')
    # Only a new clip, a pick-up or the end of the creature take the mug away
    assert render.count('removeCreatureTavernProps(') == 4, 'the mug is taken away somewhere else'
    # The mug alone goes only at the end of a seat blend out of a drink clip (decision 863)
    assert render.count('removeCreatureTavernMug(') == 4, 'the mug alone is taken away somewhere else'
    assert render.count('removeCreatureTavernMug(it->mCreature);') == 2
    assert 'removeCreatureTavernMug(it->mCreature);' in extract(render, 'void RenderManager::updateCreatureSeatBlends(')
    for head in ('void RenderManager::rrDestroyCreature(', 'void RenderManager::rrPickUpEntity(', 'void RenderManager::updateCreatureTavernProps('):
        assert 'removeCreatureTavernProps(' in extract(render, head), head
    assert 'TavernMug' not in read('source/render/CreatureCombatReactions.cpp'), 'the weapon hiding touches the mug'
    room = read('source/rooms/RoomTavern.cpp')
    show = extract(room, 'void RoomTavern::showSpotState(')
    drinking = show[show.index('case TavernGuestState::drinking:'):show.index('case TavernGuestState::ko:')]
    assert 'setAnimationState(EntityAnimation::sit_drink_anim, true, towardsTable, false)' in drinking
    assert 'setAnimationState(EntityAnimation::drink_anim, true)' in drinking
    print('mug code ok: Weapon_R first, then %d limb mounts, attached before the clip fallback' % len(mug_mounts(render)))


# 1b. The mug in the hand: the models
def check_mug_models(out):
    from check_animation_assets import export
    import fix_walk_feet as feet
    import author_rest_poses as rest
    render = read('source/render/RenderManager.cpp')
    mounts = mug_mounts(render)
    used = set()
    skeletons = sorted({skeleton_of(mesh): mesh for mesh in visiting_meshes()}.items())
    export('TavernMug.mesh', out)
    mug = rest.mesh_data(out / 'TavernMug.mesh.xml')[0]
    assert abs(float(np.ptp(mug[:, 0])) - MUG_HEIGHT) < 0.005, 'the mug changed its height'
    for name, mesh in skeletons:
        export(name + '.skeleton', out)
        skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
        if 'Weapon_R' in skeleton.idx:
            continue
        # The lookup of findTavernMugLimbMount: the entry of the skeleton, else the first entry whose bone it has
        candidates = [m for m in mounts if m[1] in skeleton.idx]
        own = [m for m in candidates if m[0] == name + '.skeleton']
        assert candidates, (name, 'no mug: the skeleton has neither Weapon_R nor a limb mount')
        mount = own[0] if own else candidates[0]
        assert mount[0] == name + '.skeleton', (name, 'takes the mount of', mount[0])
        used.add(mount[0])
        export(mesh, out)
        vertices, _, weights = rest.mesh_data(out / (mesh + '.xml'))
        bone = skeleton.idx[mount[1]]
        rest_world = skeleton.fk([(skeleton.rest_pos[i][None], skeleton.rest_q[i][None], skeleton.rest_s[i][None])
                                  for i in range(len(skeleton.names))])[bone]
        turn = quaternion_matrix(mount[2])
        up = rest_world[1][0] @ turn @ np.array([-1.0, 0.0, 0.0])
        tilt = math.degrees(math.acos(max(-1.0, min(1.0, float(up[2])))))
        assert tilt <= MAX_MUG_TILT, (name, 'the mug does not stand upright', tilt)
        limb = [i for i, row in enumerate(weights) if sum(w for b, w in row if b == bone) >= 0.5]
        foot = rest_world[0][0] + rest_world[1][0] @ (rest_world[2][0] * mount[3])
        # A hand holds the mug at its middle (decision 901): its grip, TAVERN_MUG_GRIP_SHIFT above the foot, lies on the hand
        if mount[0] in HAND_MOUNTS:
            foot = foot + up * GRIP_SHIFT * mount[4]
        middle = vertices[limb].mean(axis=0) if limb else rest_world[0][0]
        assert np.linalg.norm(foot - middle) <= MAX_MUG_FOOT_GAP, (name, 'the foot of the mug is off the limb', foot, middle)
        height = float(np.ptp(vertices[:, 2]))
        assert MIN_LIMB_MUG_SCALE <= mount[4] <= 1.0, (name, 'mug size', mount[4])
        lowest = []
        for clip in ('Drink', 'SitDrink'):
            played = skeleton.clips[clip]
            local = skeleton.locals_at(played, np.linspace(0.0, played.length, 49))
            world = skeleton.fk(local)[bone]
            placed = world[0][:, None, :] + np.einsum('nij,mj->nmi', world[1], (mug * mount[4]) @ turn.T + mount[3]) * 1.0
            if clip == 'Drink':
                lowest.append(float(placed[:, :, 2].min()))
        assert min(lowest) >= MIN_MUG_FLOOR, (name, 'the mug sinks into the floor in Drink', min(lowest))
        print('mug %-12s on %-16s upright %.1f deg, foot %.3f off the limb, scale %.2f, lowest %.3f in Drink'
              % (name, mount[1], tilt, float(np.linalg.norm(foot - middle)), mount[4], min(lowest)))
    assert used == {m[0] for m in mounts}, ('limb mounts nobody uses', {m[0] for m in mounts} - used)
    # The drink clip loops for the whole 30 seconds without a jump
    for name, mesh in skeletons:
        skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
        export(mesh, out)
        vertices, _, weights = rest.mesh_data(out / (mesh + '.xml'))
        played = skeleton.clips['Drink']
        assert played.length < BEER_SECONDS, (name, 'Drink is longer than a beer')
        points = rest.skin_vertices(skeleton, skeleton.locals_at(played, np.array([0.0, played.length])), vertices, weights)
        seam = float(np.abs(points[0] - points[1]).max()) / max(float(np.ptp(points[0][:, 2])), 1e-6)
        assert seam <= MAX_SEAM, (name, 'Drink does not loop', seam)
    print('mug models ok: %d skeletons, %d on limb mounts, Drink loops on all' % (len(skeletons), len(used)))


# 1c. Check every creature's complete calm sip, without support, reach or lift exemptions.
def check_drink_cycle(out):
    """Require complete supported sips with continuous contact at each creature's anatomical mouth."""
    from check_animation_assets import export
    import fix_walk_feet as feet
    import author_rest_poses as rest
    import author_tavern_seats as seats
    drink = sys.modules[__name__]
    rooms = block_values(read('config/rooms.cfg'), 'Rooms')
    tavern = block_values(read('config/global.cfg'), 'Tavern')
    for clip in ('Drink', 'SitDrink'):
        assert float(rooms['ClipSeconds' + clip]) == SIP_SECONDS, clip
    sips = [round(float(tavern[key]) / TURNS_PER_SECOND / SIP_SECONDS, 6) for key in ('WaterDrinkTurns', 'BeerDrinkTurns')]
    assert sips == [2.0, 6.0], sips
    export('TavernMug.mesh', out)
    check_physical_mug_geometry(out / 'TavernMug.mesh.xml')
    mug_points = rest.mesh_data(out / 'TavernMug.mesh.xml')[0]
    mounts = drink.read_limb_mounts()
    times = np.linspace(0.0, SIP_SECONDS, CYCLE_SAMPLES)
    step = times[1] - times[0]
    worst = {'speed': 0.0, 'face': 0.0, 'mouth': 0.0}
    for name, mesh in sorted({skeleton_of(m): m for m in visiting_meshes()}.items()):
        export(name + '.skeleton', out)
        export(mesh, out)
        skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
        vertices, _, weights = rest.mesh_data(out / (mesh + '.xml'))
        mug = drink.Mug(skeleton, name, mug_points, mounts)
        limb = drink.limb_of(skeleton, name, mug)
        for clip in ('Drink', 'SitDrink'):
            played = skeleton.clips[clip]
            assert abs(played.length - SIP_SECONDS) < 1e-6, (name, clip, 'is not one sip of 5 s', played.length)
            local = skeleton.locals_at(played, times)
            foot, axis, points = mug.world(skeleton.fk(local), skeleton)
            rim = foot + axis * mug.length
            assert float(np.abs(points[0] - points[-1]).max()) <= MAX_SEAM, (name, clip, 'the mug does not return to its starting pose')
            height = float(np.ptp(rest.skin_vertices(skeleton, skeleton.locals_at(played, np.zeros(1)), vertices, weights)[0, :, 2]))
            # The pause: the mug stands still and upright at the start and the end of the clip, at least MIN_PAUSE in all
            away = np.linalg.norm(rim - rim[0], axis=1)
            still = away < STILL
            pause = (np.argmin(still) if not still.all() else len(still)) + (np.argmin(still[::-1]) if not still.all() else 0)
            assert (pause - 1) * step >= MIN_PAUSE, (name, clip, 'no pause with the mug down', pause * step)
            assert float(axis[0, 2]) >= math.cos(math.radians(MAX_REST_TILT)), (name, clip, 'the resting mug does not stand upright')
            # One lift: the rim leaves its place once and comes back once
            lifted = away >= 0.5 * float(away.max())
            assert int(np.sum(lifted[1:] & ~lifted[:-1])) == 1, (name, clip, 'lifts the mug more than once')
            assert float(away.max()) >= MIN_LIFT * height, (name, clip, 'hardly lifts the mug', float(away.max()))
            # The drink: the rim holds its place at the mouth for at least MIN_DRINK
            top = int(np.argmax(away))
            held = np.linalg.norm(rim - rim[top], axis=1) < HOLD
            assert int(held.sum()) * step >= MIN_DRINK, (name, clip, 'no drink at the mouth', held.sum() * step)
            # Calm: no fast back and forth
            speed = float((np.linalg.norm(np.diff(rim, axis=0), axis=1) / step).max())
            worst['speed'] = max(worst['speed'], speed / max(height, MIN_HEIGHT))
            assert speed <= MAX_SPEED_HEIGHTS * max(height, MIN_HEIGHT), (name, clip, 'moves the mug too fast', speed)
            # The rim at the mouth, the mug in front of the face, never through the head
            start = skeleton.locals_at(played, np.zeros(1))
            head = drink.Head(skeleton, name, vertices, weights, limb, start)
            heads = rest.skin_vertices(skeleton, local, head.vertices, head.weights)
            in_face = max(drink.Face(heads[i]).inside(points[i]) for i in range(0, len(times), 4))
            worst['face'] = max(worst['face'], in_face)
            assert in_face <= MAX_MUG_IN_FACE, (name, clip, 'the mug goes through the head', in_face)
            mouths = head.mouths(skeleton, local)
            mouth = mouths[top]
            reach = float(np.linalg.norm(rim[top] - mouth))
            worst['mouth'] = max(worst['mouth'], reach)
            assert reach <= MAX_RIM_TO_MOUTH, (name, clip, 'the rim does not come to the mouth', reach)
            # A single frame at the mouth is insufficient: the calm hold must remain there for a continuous drink.
            mouth_distances = np.linalg.norm(rim - mouths, axis=1)
            at_mouth = held & (mouth_distances <= MAX_RIM_TO_MOUTH)
            changes = np.diff(np.concatenate(([False], at_mouth, [False])).astype(int))
            spans = np.flatnonzero(changes == -1) - np.flatnonzero(changes == 1)
            assert len(spans) and (int(spans.max()) - 1) * step >= MIN_DRINK, (name, clip, 'does not hold the rim at the mouth for a full drink')
            # Seated: every mug stands on the table top at the smallest creature scale. Stool guests face the table end;
            # bench guests face its long edge. The same rule applies at both ends of the closed loop.
            if clip == 'SitDrink':
                surface = seats.TABLE_TOP
                edge = -(STOOL_DISTANCE - seats.LONG_TABLE_HALF_LENGTH) if name in seats.RESTING_MODELS else seats.TABLE_NEAR_EDGE
                for frame in (0, -1):
                    base = foot[frame] - axis[frame] * drink.MUG_FOOT * mug.scale
                    assert 0.0 <= base[2] - surface <= MAX_STAND_GAP, (name, 'the mug does not stand on its support', base, surface)
                    assert base[1] + mug.base_radius <= edge + 1e-3, (name, 'the mug stands beyond the table edge', base)
                    if name in seats.RESTING_MODELS:
                        assert abs(base[0]) + mug.base_radius <= STOOL_TABLE_HALF_WIDTH + 1e-3, (name, 'the mug stands beside the tabletop', base)
    print('drink cycle ok: one sip of %.0f s per clip (water %d, beer %d sips), pause and drink of at least %.1f s, mug at most '
          '%.2f body heights per second, at most %.0f %% of it in the head, rim within %.3f of the mouth'
          % (SIP_SECONDS, sips[0], sips[1], MIN_PAUSE, worst['speed'], 100 * worst['face'], worst['mouth']))


# 2. A beer lasts 30 seconds and water lasts 10 seconds (decision 866)
def check_duration():
    tavern = block_values(read('config/global.cfg'), 'Tavern')
    assert float(tavern['BeerDrinkTurns']) == round(BEER_SECONDS * TURNS_PER_SECOND) == 42, 'a beer lasts 30 s'
    assert float(tavern['WaterDrinkTurns']) == WATER_TURNS == round(10 * TURNS_PER_SECOND), 'a water lasts 10 s'
    assert float(tavern['DrinkTurns']) == 4, 'vomiting and pouring keep DrinkTurns 4'
    assert re.search(r'^# WaterDrinkTurns\s+\S', read('config/global.cfg'), re.M), 'WaterDrinkTurns is not documented'
    assert re.search(r'^# BeerDrinkTurns\s+\S', read('config/global.cfg'), re.M), 'BeerDrinkTurns is not documented'
    room = read('source/rooms/RoomTavern.cpp')
    turns = extract(room, 'int32_t RoomTavern::nextDrinkTurns(')
    assert 'getTavernValue(beer ? "BeerDrinkTurns" : "WaterDrinkTurns")' in turns and 'servesBeer()' in turns
    assert 'mPayer == TavernPayer::keeper' in turns and 'getSeat()->getGold() >= price' in turns
    assert 'creature.getGoldCarried() >= price' in turns
    assert room.count('setSpotState(spot, TavernGuestState::drinking, nextDrinkTurns(') == 2, 'a drink starts without its duration'
    assert 'getTavernValue("DrinkTurns")' not in room.replace(turns, ''), 'a drink still lasts DrinkTurns'
    # Nothing else sets a clip while the guest drinks: the room only counts the turns, the use action waits
    upkeep = extract(room, 'void RoomTavern::upkeepSpots(')
    drinking = upkeep[upkeep.index('case TavernGuestState::drinking:'):upkeep.index('case TavernGuestState::ko:')]
    assert 'setAnimationState' not in drinking and 'showSpotState' not in drinking
    use = extract(room, 'bool RoomTavern::useRoom(')
    assert re.search(r'default:\s*// drinking, game, ko and getUp are run by doUpkeep\s*return false;', use)
    print('duration ok: beer %d turns (%d s), water %d turns' % (int(float(tavern['BeerDrinkTurns'])), BEER_SECONDS, WATER_TURNS))


# 3. The drink chain (D16) and the game (D5)
def check_chain_and_game():
    tavern = block_values(read('config/global.cfg'), 'Tavern')
    rooms = block_values(read('config/rooms.cfg'), 'Rooms')
    first, most, halving = float(tavern['NextDrinkPercent']), int(float(tavern['MaxDrinksPerVisit'])), float(rooms['TavernDrinkChainHalving'])
    room = read('source/rooms/RoomTavern.cpp')
    finish = extract(room, 'void RoomTavern::finishDrink(')
    assert 'spot.mDrinks < static_cast<uint32_t>(getTavernValue("MaxDrinksPerVisit"))' in finish
    assert 'getTavernValue("NextDrinkPercent") /' in finish and '"TavernDrinkChainHalving", 2.0), static_cast<double>(spot.mDrinks - 1))' in finish
    chances = [first / halving ** (n - 1) for n in range(1, most)]
    assert chances == [50.0, 25.0, 12.5, 6.25] and most == 5, chances
    mean = 1.0
    stay = 1.0
    for chance in chances:
        stay *= chance / 100.0
        mean += stay
    assert abs(mean - 1.6416) < 0.0001, mean
    # The game after the last drink
    assert float(tavern['GameChancePercent']) == 50.0
    assert finish.index('getTavernValue("GameChancePercent")') > finish.index('setSpotDone(spot, DONE_WAIT_TURNS);')
    start = extract(room, 'void RoomTavern::tryStartGame(')
    assert '(other->second.mState != TavernGuestState::done) || (other->second.mTurnsLeft <= 0)' in start
    assert 'other->second.mCreature->getSeat() != own->second.mCreature->getSeat()' in start
    assert '!(seatA.mTable == seatB.mTable)' in extract(room, 'void RoomTavern::startGame(')
    upkeep = extract(room, 'void RoomTavern::doUpkeep(')
    assert '!(it->second.mWantsGame && hasDrinkingTableMate(it->first))' in upkeep
    assert upkeep.index('upkeepSpots();') < upkeep.index('tryStartGame(it->first);') < upkeep.index('--it->second.mTurnsLeft;')

    # A model of the upkeep for two guests at one table: A finishes its last drink, B still drinks for d more turns
    def game_after(delay, wait_for_mate):
        a_turns = 1  # DONE_WAIT_TURNS
        for turn in range(delay + 2):
            b_done_now = (turn == delay)
            # tryStartGame of the waiting guest: B is a partner in the turn it finishes (done with one turn left)
            if b_done_now and a_turns > 0:
                return True
            mate_drinks = turn < delay
            if a_turns > 0 and not (wait_for_mate and mate_drinks):
                a_turns -= 1
        return False
    delays = range(0, int(float(tavern['BeerDrinkTurns'])))
    old = sum(game_after(d, False) for d in delays) / len(delays)
    new = sum(game_after(d, True) for d in delays) / len(delays)
    assert new == 1.0 and old < 0.1, (old, new)
    print('chain ok: %s percent, at most %d, %.2f drinks per visit; a wish for a game finds the drinking partner %d%% '
          '(before %d%%)' % (', '.join('%g' % c for c in chances), most, mean, round(100 * new), round(100 * old)))


# 4. No guest lies in or through a table
def check_lying_code():
    room_h = read('source/rooms/Room.h')
    assert re.search(r'virtual bool keepGuestUntilItLeft\(Creature& creature\)\s*\{ return false; \}', room_h)
    room = read('source/rooms/RoomTavern.cpp')
    keep = extract(room, 'bool RoomTavern::keepGuestUntilItLeft(')
    assert '!isOnSeat(creature, it->first, it->second.mPlaces)' in keep and 'it->second.mLeftSeat' in keep
    assert 'abortGame(game);' in keep and 'setSpotDone(spot, 0);' in keep
    action = read('source/creatureaction/CreatureActionUseRoom.cpp')
    job = extract(action, 'bool CreatureActionUseRoom::handleJob(')
    for head in ('if(creature.needInterrupt(servingNeed))', 'if(moodRoom && !fighting && creature.getMoodValue() <= CreatureMoodLevel::Neutral)',
                 'if((room->shouldStopUseIfHungrySleepy(creature, forced)) &&'):
        branch = job[job.index(head):]
        branch = branch[:branch.index('\n    }\n')]
        keep_at = branch.index('room->keepGuestUntilItLeft(creature)')
        assert 'return room->useRoom(creature, forced);' in branch[keep_at:keep_at + 200], head
        for leave in ('creature.popAction();', 'creature.pushAction('):
            if leave in branch:
                assert keep_at < branch.index(leave), (head, 'leaves the bench before getting off it')
    for clip in ('sleep_anim', 'die_anim', 'drop_anim', 'dragged_anim', 'rot_anim'):
        assert 'EntityAnimation::' + clip not in room, clip
    assert room.count('EntityAnimation::knockedout_anim') == 2
    show = extract(room, 'void RoomTavern::showSpotState(')
    ko = show[show.index('case TavernGuestState::ko:'):show.index('case TavernGuestState::getUp:')]
    assert ko.index('if(seated)') < ko.index('sit_slumped_anim') < ko.index('else') < ko.index('knockedout_anim')
    fall = extract(room, 'bool RoomTavern::fallNextToBench(')
    assert 'EntityAnimation::knockedout_anim' in fall and re.search(r'if\(isLargeGuest\(\*creature\)\)\s*return false;', fall)
    assert fall.index('route.push_back(bestTurn);') < fall.index('route.push_back(bestPoint);')
    assert 'const Ogre::Vector2 turn = point + away * KO_TURN_STEP;' in fall
    assert 'const Ogre::Vector2 feet = point + away * (body->mBehindMin * scale);' in fall
    assert 'const Ogre::Vector2 head = point + away * (body->mBehindMax * scale);' in fall
    assert 'clearSegment(lying, feet, head)' in fall and 'headTile->getCoveringRoom() != this' in fall
    reactions = read('source/render/CreatureReactions.cpp')
    assert 'const bool seated = sitsAtTable(creature) || (lowersBody(variant) && standsInTavern(creature));' in reactions
    print('lying code ok: guests get off the bench first, no lying clip at a table, the loser falls away from it')


def check_lying_models(out):
    from check_animation_assets import export
    import fix_walk_feet as feet
    import author_rest_poses as rest
    import author_tavern_seats as seats
    bodies, default = lying_bodies(read('source/rooms/RoomTavern.cpp'))
    checked = 0
    for mesh in visiting_meshes():
        name = skeleton_of(mesh)
        if name in seats.LARGE_MODELS:
            continue
        assert mesh in bodies, (mesh, 'has no lying body')
        export(name + '.skeleton', out)
        export(mesh, out)
        skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
        vertices, _, weights = rest.mesh_data(out / (mesh + '.xml'))
        played = skeleton.clips['KnockedOut']
        points = rest.skin_vertices(skeleton, skeleton.locals_at(played, np.linspace(0.0, played.length, 33)), vertices, weights)
        behind_min, behind_max, half = bodies[mesh]
        # The creature looks along -y: behind it is +y
        assert behind_min <= float(points[:, :, 1].min()) and float(points[:, :, 1].max()) <= behind_max, (mesh, 'length')
        assert float(np.abs(points[:, :, 0]).max()) <= half, (mesh, 'width')
        assert default[0] <= behind_min and behind_max <= default[1] and half <= default[2], (mesh, 'default')
        checked += 1
    assert set(bodies) <= set(visiting_meshes()), set(bodies) - set(visiting_meshes())
    print('lying models ok: %d bodies inside their measured floor' % checked)


# Material geometry keeps the contact proxies on actual wood rather than a misleading bounding-box edge.
def point_to_triangle_distance(point, triangle):
    """Measure contact with actual material, including an edge between mesh vertices."""
    a, b, c = triangle
    normal = np.cross(b - a, c - a)
    length = float(np.linalg.norm(normal))
    assert length > 1e-12, 'degenerate physical mug end triangle'
    normal /= length
    signed = float(np.dot(point - a, normal))
    projected = point - normal * signed
    first, second = b - a, c - a
    aa, ab, bb = float(np.dot(first, first)), float(np.dot(first, second)), float(np.dot(second, second))
    pa, pb = float(np.dot(projected - a, first)), float(np.dot(projected - a, second))
    denominator = aa * bb - ab * ab
    u = (pa * bb - pb * ab) / denominator
    v = (pb * aa - pa * ab) / denominator
    if u >= -1e-8 and v >= -1e-8 and u + v <= 1.0 + 1e-8:
        return abs(signed)
    closest = float('inf')
    for start, end in ((a, b), (b, c), (c, a)):
        edge = end - start
        share = float(np.clip(np.dot(point - start, edge) / np.dot(edge, edge), 0.0, 1.0))
        closest = min(closest, float(np.linalg.norm(point - (start + edge * share))))
    return closest


def check_physical_mug_geometry(mesh_path):
    """Require the material-defined bowl, foam and actual wooden contact edges to match the attachment contract."""
    import author_rest_poses as rest
    drink = sys.modules[__name__]
    assert drink.MUG_FOOT == 0.009 and drink.MUG_RIM == -0.171, 'mug contact coordinates changed'
    vertices, faces, _ = rest.mesh_data(mesh_path)
    expected_triangles = {'TavernWood': 1868, 'TavernIron': 768, 'TavernFoam': 3744}
    assert len(vertices) == 8412, ('mug vertices', len(vertices))
    materials = {material: [] for material in expected_triangles}
    for face, material in faces:
        assert material in materials, ('unexpected mug material', material)
        materials[material].append(face)
    assert {material: len(triangles) for material, triangles in materials.items()} == expected_triangles
    points = {material: np.unique(vertices[sorted({index for face in triangles for index in face})], axis=0)
              for material, triangles in materials.items()}
    foam = points['TavernFoam']
    values, directions = np.linalg.eigh(np.cov(foam.T))
    foam_normal = directions[:, 0]
    assert abs(float(foam_normal[0])) >= math.cos(math.radians(2.0)), ('foam is sideways', foam_normal)
    assert np.allclose((float(foam[:, 0].min()), float(foam[:, 0].max())), (-0.171, -0.14508),
                       atol=2e-5, rtol=0.0), ('foam axial bounds', foam.min(axis=0), foam.max(axis=0))
    assert float(values[0]) < 0.3 * float(values[1]), ('foam does not have a cup-facing plane', values)
    wood = points['TavernWood']
    assert np.allclose(wood.min(axis=0), (-0.171, -0.0384, -0.0756), atol=2e-5, rtol=0.0), ('wood minimum', wood.min(axis=0))
    assert np.allclose(wood.max(axis=0), (0.009, 0.0384, 0.0324), atol=2e-5, rtol=0.0), ('wood maximum', wood.max(axis=0))
    centres = []
    for label, axial in (('base', 0.009), ('rim', -0.171)):
        ring = wood[np.abs(wood[:, 0] - axial) <= 2e-5]
        assert len(ring) == 48, (label, 'physical wood ring vertices', len(ring))
        centre = ring.mean(axis=0)
        assert np.allclose(centre, (axial, 0.0, -0.0372), atol=2e-5, rtol=0.0), (label, 'physical ring centre', centre)
        centres.append(centre)
        triangles = [vertices[face] for face in materials['TavernWood']
                     if np.max(np.abs(vertices[face, 0] - axial)) <= 2e-5]
        assert len(triangles) == 24, (label, 'physical wood end triangles', len(triangles))
        contact = np.array([axial, 0.0, 0.0])
        distance = min(point_to_triangle_distance(contact, triangle) for triangle in triangles)
        assert distance <= 2e-5, (label, 'attachment proxy misses actual wood', distance)
        if label == 'rim':
            # The centre is an opening, not a lip: measuring only distance to its plane would give a false contact.
            assert min(point_to_triangle_distance(centre, triangle) for triangle in triangles) > 0.025, 'rim hole treated as wood'
    assert np.allclose(centres[1] - centres[0], (-0.18, 0.0, 0.0), atol=2e-5, rtol=0.0), 'physical bowl axis changed'
    iron = points['TavernIron']
    assert np.allclose((float(iron[:, 0].min()), float(iron[:, 0].max())), (-0.14364, -0.01404),
                       atol=2e-5, rtol=0.0), ('iron hoops are sideways', iron.min(axis=0), iron.max(axis=0))
    assert np.allclose(iron.mean(axis=0)[1:], (0.0, -0.0372), atol=2e-5, rtol=0.0), 'iron hoop centre changed'
    print('physical mug geometry ok: foam and wooden bowl face -x, actual base/lip contacts match the attachment contract')


# A head turn must transport the same mouth opening rather than select a new global-front surface point.
def check_mouth_anchors(out):
    """Check fixed anatomical centres and their movement under a rigid turn and translation of each actual rig."""
    from check_animation_assets import export
    import fix_walk_feet as feet
    import author_rest_poses as rest
    drink = sys.modules[__name__]
    assert set(drink.MOUTHS) == set(EXPECTED_MOUTHS)
    meshes = {skeleton_of(mesh): mesh for mesh in visiting_meshes()}
    export('TavernMug.mesh', out)
    mug_points = rest.mesh_data(out / 'TavernMug.mesh.xml')[0]
    turn = drink.rotation_matrix(np.array([0.0, 0.0, 1.0]), math.pi / 2.0)
    shift = np.array([0.2, 0.1, 0.3])
    for name, expected in EXPECTED_MOUTHS.items():
        export(name + '.skeleton', out)
        export(meshes[name], out)
        skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
        vertices, _, weights = rest.mesh_data(out / (meshes[name] + '.xml'))
        mug = drink.Mug(skeleton, name, mug_points, drink.read_limb_mounts())
        bind = skeleton.locals_at(feet.Clip('bind', 1.0), np.zeros(1))
        head = drink.Head(skeleton, name, vertices, weights, drink.limb_of(skeleton, name, mug), bind)
        assert np.allclose(head.mouths(skeleton, bind)[0], expected, atol=1e-5, rtol=0.0), name
        moved = drink.copy_pose(bind)
        for index, parent in enumerate(skeleton.parent):
            if parent >= 0:
                continue
            rest.rotate_joint(skeleton, moved, skeleton.names[index], np.array([0.0, 0.0, 1.0]), np.array([math.pi / 2.0]))
            position, rotation, scale = moved[index]
            moved[index] = (position @ turn.T + shift, rotation, scale)
        assert np.allclose(head.mouths(skeleton, moved)[0], turn @ np.asarray(expected) + shift,
                           atol=1e-5, rtol=0.0), (name, 'mouth changed surface during a turn')
    print('mouth anchors ok: eleven measured anatomical openings follow their rig through a rigid turn')




# Independent native geometry measurements retained with the strict asset check.
import author_rest_poses as rest
import author_tavern_seats as seats
import fix_walk_feet as feet

CYCLE = 5.0


MUG_FOOT = 0.009


MUG_RIM = -0.171


MUG_GIRTH = 1.8


MUG_GRIP_SHIFT = 0.1


MUG_BOTTOM = -0.07


FACE_DEPTH = 0.01


FACE_CELL = 0.02


BENCH_OFFSET = 0.4116


LIMBS = {
    'lich': ('shoulderRight', 'ellbowRight', 'wristRight'),
    'Rat': ('FrontLeg_R', 'FrontLeg_R.001', 'FrontLeg_R.002', 'FrontLeg_R.003'),
    'Kreatur': ('tentafr1_r', 'tentafr2_r', 'tentafr3_r', 'tentafr4_r'),
    'Scarab': ('Bone.001_R', 'Bone.001_R.001', 'Bone.001_R.002', 'Bone.001_R.003', 'Bone.001_R.004', 'Bone.001_R.005'),
    'Roach': ('ArmRootR', 'ArmR', 'ForearmFrontR', 'ClawFrontR'),
    'Slime': ('sip_root', 'sip_bend1', 'sip_bend2', 'sip_bend3', 'sip_bend4', 'sip_tip'),
    'Spider': ('sip_shoulder', 'sip_elbow', 'sip_palm', 'sip_tip'),
}


HEADS = {
    'Cultist': (('neck',), 0.0),
    'Goblin': (('Spine1',), 0.06),
    'Scarab': (('Bone.004',), None),
    'Spider': (('Zahn_R', 'Zahn_L', 'Body'), None, False),
    'lich': (('spine3', 'crown'), 0.05),
    'Kreatur': (('head',), None),
    'RunelordDwarf': (('head.cr',), None),
    'Slime': (('slime_head',), None),
    'Roach': (('Head', 'JawR', 'JawL', 'Tongue'), None),
}


MOUTHS = {
    'CaveHornet': ((249, (0.0016052, -0.189098, 0.061582)), (1299, (-0.0016052, -0.189098, 0.061582))),
    'Dragon': ((80, (0.0, -0.708788, 0.961628)), (72, (0.0, -0.703024, 0.954036))),
    'Spider': ((14, (-0.00848184, -0.142194, 0.131078)), (69, (0.00848184, -0.142194, 0.131078))),
    'Rat': ((462, (0.0, -0.430011, 0.145937)),),
    'Slime': ((16, (0.0, -0.274409, 0.27)),),
    'Tentacle': ((121, (0.0, -0.0146598, 0.511544)),),
    'Kreatur': ((18, (0.0, -0.317763, 0.472901)),),
    'LavaSpawn': ((2075, (-5.75e-06, -0.46090289110446825, 0.59545494)),
     (2102, (-5.75e-06, -0.4651113088955317, 0.60945494))),
    'Roach': ((91, (0.0, -0.217098, 0.206459)),
     (1391, (-0.0131999, -0.199301, 0.189129)),
     (1387, (0.0131999, -0.199301, 0.189129))),
    'Scarab': ((481, (0.0019446, -0.24109942111655863, 1.0398758589264896)),),
    'Wyvern': ((223, (0.0, -0.169624, 0.646443)),),
}


def read_limb_mounts():
    """Evaluate the physical rig using its native attachment and geometry contract."""
    render = (ROOT / 'source' / 'render' / 'RenderManager.cpp').read_text(encoding='utf-8')
    table = render[render.index('const TavernMugLimbMount TAVERN_MUG_LIMB_MOUNTS[] ='):]
    table = table[:table.index('};')]
    number = r'(-?[0-9.]+)f'
    rows = re.findall(r'\{ "([^"]+)", "([^"]+)", ' + ', '.join([number] * 8) + r' \}', table)
    return {skeleton[:-len('.skeleton')]: (bone, np.array([float(v) for v in values[:4]]), np.array([float(v) for v in values[4:7]]),
                                          float(values[7])) for skeleton, bone, *values in rows}


def quaternion_matrix(q):
    """Evaluate the physical rig using its native attachment and geometry contract."""
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


PASSIVE_MOUNTS = ('skeleton', 'lich', 'PitDemon', 'Kreatur')


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
    """Evaluate the physical rig using its native attachment and geometry contract."""
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


def rotation_matrix(axis, angle):
    """Evaluate the physical rig using its native attachment and geometry contract."""
    return feet.q2m(feet.rv2q(np.asarray(axis)[None] * angle))[0]


def copy_pose(local):
    """Evaluate the physical rig using its native attachment and geometry contract."""
    return [(p.copy(), q.copy(), s.copy()) for p, q, s in local]


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


def main():
    """Run the source contracts, anatomical anchors and strict serialized-model checks."""
    check_mug_code()
    check_duration()
    check_chain_and_game()
    check_lying_code()
    converter = os.environ.get('OGRE_XML_CONVERTER', 'OgreXMLConverter')
    if shutil.which(converter) is None and not Path(converter).is_file():
        print('models skipped: no OgreXMLConverter')
    else:
        out = ROOT / 'out' / 'tavern-drink-834'
        out.mkdir(parents=True, exist_ok=True)
        from check_animation_assets import export
        export('TavernMug.mesh', out)
        check_physical_mug_geometry(out / 'TavernMug.mesh.xml')
        check_mug_models(out)
        check_mouth_anchors(out)
        check_drink_cycle(out)
        check_lying_models(out)
    print('tavern drink 834 ok')


if __name__ == '__main__':
    main()
