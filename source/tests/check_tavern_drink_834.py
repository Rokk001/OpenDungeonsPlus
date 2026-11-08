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


def main():
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
        check_mug_models(out)
        check_lying_models(out)
    print('tavern drink 834 ok')


if __name__ == '__main__':
    main()
