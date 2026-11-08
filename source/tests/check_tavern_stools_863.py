#!/usr/bin/env python3
"""Owner decision 863, findings 6 to 9 (tavern): round stools for the creatures that cannot sit on a bench, a mug that
reads from the game camera in every drink, why a drink lasted 1 to 2 s on one map and 30 s on another, and when and how
a slap duel runs.

What is checked (python only, no compiler, no game; fixed values of this branch, counted once)
  stool group  the creatures on stools are exactly the models whose seated clips rest the body on the seat instead of
               sitting on legs (RESTING_MODELS of tools/author_tavern_seats.py: 11 meshes, the two tentacles share one
               skeleton); Troll, Dragon and PitDemon sit on their legs and keep their benches
  stool rules  two stools per table at 0.8 tiles from its middle along the table (places 8 and 9), looking to its middle;
               a stool guest takes only a stool, every other guest only bench places; the bench places at the end of an
               occupied stool that its body reaches stay free (and a stool stays free while one of them is taken); the
               footprint of the body lies on tiles of the room without other furniture, outside the reach of the guests
               of every other table (1.48 tiles along, 1.51 across) and of every other stool guest; the stools are
               created with the tables, removed with them and with the room, and are furniture for the navigation; the
               own stool and table are left out of the obstacles of the walk onto the seat and of the fall of a duel loser
  stool models (need OgreXMLConverter) the stool mesh: seat top at the bench height 0.2575, radius 0.16, inside its
               navigation bounds; for every stool model, all frames of the seven seated clips at level scale 1 and 1.1:
               inside the footprint of its table row, no part deeper than 0.025 in the seat or in the post of the stool,
               no part deeper than 0.04 in the table or the benches, no overlap with a bench guest of any model beyond
               its blocked places (and an overlap at the last blocked place, so no place is blocked for nothing), no
               overlap with any stool guest on the other stool; the bench guests of a table stay within 1.48 / 1.51; the
               legs and belly of Troll, Dragon and PitDemon hang through any stool seat, which is why they keep the bench
  mug          the mug is 1.8 times as wide as its mesh and as long; a limb mug is at least 0.67 of the mesh; no weapon is
               shown in Drink (it sits on the same hand bone); a drink clip that fades out keeps its mug until the blend
               ends; models: at most 10 percent of the wide mug lies 0.02 deep in the table top in any frame of SitDrink
               on every skeleton with Weapon_R, the wide mug stays above the floor in Drink on every skeleton
  finding 8    WaterDrinkTurns 14 (water, 10 s; decision 866) and BeerDrinkTurns 42 (beer, 30 s); a beer only where Beer is researched and the
               payer has the price; [Test] Ghosts has neither Tavern nor Beer researched (its guests get water), [Test] Spa
               has both and 5000 gold (its guests get beer)
  finding 9    when a duel starts (code) and how often: a model of the upkeep of two guests at one table gives a game in
               59 percent of the visits and a slap duel in 20 when they sit down together, 29 and 9.5 percent when the
               second comes 0 to 120 turns later; a model of playDuelTurn gives slaps of 6 to 14
               turns (4.3 to 10 s), pauses of 5 to 8 turns (3.6 to 5.7 s), a knock-out state of 41 turns after the turn the
               duel ends (29.3 s: DuelKoTurns 42 is counted down once in that same turn) and a get-up of 9 turns (6.4 s)

Call from the repository root:
  python source/tests/check_tavern_stools_863.py
"""
import math
import os
import random
import re
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'source' / 'tests'))

TURNS_PER_SECOND = 1.4
# Decision 863: the creatures on stools and their measured bodies (blocked bench places, front, back, half width)
EXPECTED_BODIES = {
    'CaveHornet.mesh': (1, 0.13, 0.12, 0.26), 'Kreatur.mesh': (4, 0.66, 1.23, 0.70), 'LavaSpawn.mesh': (4, 0.42, 0.96, 0.98),
    'Rat.mesh': (1, 0.12, 0.47, 0.37), 'Roach.mesh': (2, 0.15, 0.57, 0.39), 'Scarab.mesh': (2, 0.23, 0.86, 0.43),
    'Slime.mesh': (1, 0.14, 0.30, 0.23), 'Spider.mesh': (1, 0.20, 0.56, 0.42), 'TentacleAlbine.mesh': (2, 0.35, 0.24, 0.33),
    'TentacleGreen.mesh': (2, 0.35, 0.24, 0.33), 'Wyvern.mesh': (2, 0.38, 0.69, 0.49)}
BENCH_MODELS_ON_LEGS = ('Troll.mesh', 'Dragon.mesh', 'PitDemon.mesh')
STOOL_DISTANCE = 0.8
REACH_ALONG = 1.48
REACH_ACROSS = 1.51
STOOL_TOP = 0.2575
STOOL_RADIUS = 0.16
STOOL_POST_RADIUS = 0.034
# A body may press this far into the seat of the stool (the bench allows 0.015; the wyvern presses 0.0195)
MAX_STOOL_SINK = 0.025
# A body may reach this far into the table or a bench (MAX_TABLE_DEPTH of check_tavern_seat_clips.py)
MAX_TABLE_DEPTH = 0.04
# Footprints and reaches are rounded up to the next 0.01 tile: they may exceed the measured value by this much
MAX_ROUNDING = 0.011
MUG_GIRTH = 1.8
MIN_LIMB_MUG_SCALE = 0.67
MAX_MUG_IN_TABLE = 0.10
MIN_MUG_FLOOR = -0.03
SEAT_CLIPS = ['Sit', 'SitDrink', 'SitSlap', 'SitSlapped', 'SitArmWrestle', 'SitDice', 'SitSlumped']
SAMPLES = 33
VOXEL = 0.04
BENCH_OFFSET = 0.4116
SEAT_SPACING = 0.328
LARGE_BENCH_PLACES = {'Troll.mesh': 4, 'PitDemon.mesh': 4, 'Dragon.mesh': 3}


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
            values.setdefault(words[0], words[1])
    return values


def stool_bodies(room):
    table = room[room.index('const TavernStoolBody TAVERN_STOOL_BODIES[] ='):]
    table = table[:table.index('};')]
    rows = re.findall(r'\{ "([^"]+)", ([0-9]+), ([0-9.]+)f, ([0-9.]+)f, ([0-9.]+)f \}', table)
    return {mesh: (int(k), float(f), float(b), float(h)) for mesh, k, f, b, h in rows}


def float_constant(text, name):
    match = re.search(r'^const float ' + name + r' = ([0-9.]+)f;$', text, re.M)
    assert match is not None, name
    return float(match.group(1))


def stool_reaches_place(stool, blocked, place):
    # The rule of stoolReachesPlace in RoomTavern.cpp
    along = place % 4
    return along < blocked if stool == 8 else along + blocked >= 4


# 1. The stools in the code
def check_stool_code():
    room = read('source/rooms/RoomTavern.cpp')
    header = read('source/rooms/RoomTavern.h')
    bodies = stool_bodies(room)
    assert bodies == EXPECTED_BODIES, ('stool bodies', bodies)
    # The group is the resting models of the clip author; the large bodies on legs keep their benches
    author = read('tools/author_tavern_seats.py')
    resting = re.search(r"^RESTING_MODELS = \(([^)]*)\)", author, re.M).group(1)
    names = sorted(re.findall(r"'(\w+)'", resting))
    expected = sorted(n + '.mesh' for n in names if n != 'Tentacle') + ['TentacleAlbine.mesh', 'TentacleGreen.mesh']
    assert sorted(bodies) == sorted(expected), ('the stool group is not the resting models', sorted(bodies), expected)
    for mesh in BENCH_MODELS_ON_LEGS:
        assert mesh not in bodies, mesh
    assert float_constant(room, 'TAVERN_STOOL_DISTANCE') == STOOL_DISTANCE
    assert float_constant(room, 'TAVERN_BENCH_REACH_ALONG') == REACH_ALONG
    assert float_constant(room, 'TAVERN_BENCH_REACH_ACROSS') == REACH_ACROSS
    assert 'const uint32_t TAVERN_STOOLS_PER_TABLE = 2;' in header
    assert 'const uint32_t TAVERN_PLACES_PER_TABLE = TAVERN_SEATS_PER_TABLE + TAVERN_STOOLS_PER_TABLE;' in header
    assert 'const std::string TAVERN_STOOL_MESH = "TavernStool";' in room

    offset = extract(room, 'Ogre::Vector2 seatOffset(')
    assert 'y = (index == TAVERN_SEATS_PER_TABLE) ? TAVERN_STOOL_DISTANCE : -TAVERN_STOOL_DISTANCE;' in offset and 'x = 0.0f;' in offset
    facing = extract(room, 'Ogre::Vector3 RoomTavern::getAcrossTableDirection(')
    assert 'const float along = (seat.mIndex == TAVERN_SEATS_PER_TABLE) ? -1.0f : 1.0f;' in facing
    assert 'return Ogre::Vector3(-along * static_cast<float>(std::sin(angle)), along * static_cast<float>(std::cos(angle)), 0.0f);' in facing
    # Seat 8 lies at +y of the table frame (rotated like seatOffset) and looks to the middle: a model of both
    for angle in (0.0, 90.0):
        a = math.radians(angle)
        for index, sign in ((8, 1.0), (9, -1.0)):
            ox, oy = -sign * STOOL_DISTANCE * math.sin(a), sign * STOOL_DISTANCE * math.cos(a)
            along = -1.0 if index == 8 else 1.0
            fx, fy = -along * math.sin(a), along * math.cos(a)
            assert abs(fx * ox + fy * oy + STOOL_DISTANCE) < 1e-9, ('the stool guest does not look to the middle', angle, index)

    # Only stools for stool guests, only benches for the others, everywhere a seat is taken
    for_creature = extract(room, 'bool RoomTavern::isFreeSeatFor(')
    assert 'return isStoolSeat(seat) && isFreeStool(creature, seat);' in for_creature
    assert 'return !isStoolSeat(seat) && isFreeSeat(seat, getPlacesOf(creature));' in for_creature
    pick = extract(room, 'bool RoomTavern::pickFreeSeat(')
    assert 'index < TAVERN_PLACES_PER_TABLE' in pick and 'isFreeSeatFor(creature, RoomTavernSeat(table, index))' in pick
    assert 'isFreeSeat(' not in pick.replace('isFreeSeatFor(', '')
    other = extract(room, 'bool RoomTavern::walkToOtherSeat(')
    assert 'index < TAVERN_PLACES_PER_TABLE' in other and '!isFreeSeatFor(creature, candidate)' in other
    add = extract(room, 'bool RoomTavern::addCreatureUsingRoom(')
    assert 'isFreeSeatFor(*creature, pending->second.mSeat)' in add
    places = extract(room, 'uint32_t RoomTavern::getPlacesOf(')
    assert 'if(!isLargeGuest(creature) || usesStool(creature))' in places
    # The bench places the stool guest reaches
    free_seat = extract(room, 'bool RoomTavern::isFreeSeat(')
    assert 'if(isPlaceBlockedByStool(seat, places))' in free_seat
    blocked = extract(room, 'bool RoomTavern::isPlaceBlockedByStool(')
    assert 'stoolReachesPlace(stool, blocked, place)' in blocked
    reaches = extract(room, 'bool stoolReachesPlace(')
    assert 'return along < blockedPlaces;' in reaches and 'return along + blockedPlaces >= TAVERN_SEATS_PER_BENCH;' in reaches
    stool = extract(room, 'bool RoomTavern::isFreeStool(')
    for token in ('stoolReachesPlace(seat.mIndex, body->mBlockedPlaces, place)',
                  'place < entry.first.mIndex + entry.second.mPlaces',
                  'getStoolFootprint(*entry.second.mCreature, entry.first, otherMinimum, otherMaximum)',
                  '(tile == nullptr) || (tile->getCoveringRoom() != this)',
                  '(tile != seat.mTable) && (tile != secondTile) && hasFurnitureOn(tile)',
                  '(std::abs(along) < TAVERN_BENCH_REACH_ALONG) && (std::abs(across) < TAVERN_BENCH_REACH_ACROSS)',
                  'FOOTPRINT_SAMPLE_STEP'):
        assert token in stool, token
    footprint = extract(room, 'bool RoomTavern::getStoolFootprint(')
    for token in ('body->mFront * scale', 'body->mBack * scale', 'body->mHalfWidth * scale', 'creature.getLevelScale()'):
        assert token in footprint, token
    # The blocked places of the two stools, for every count of the table: a model of the rule
    for k in (1, 2, 4):
        assert {p for p in range(8) if stool_reaches_place(8, k, p)} == {p for p in range(8) if p % 4 < k}
        assert {p for p in range(8) if stool_reaches_place(9, k, p)} == {p for p in range(8) if p % 4 >= 4 - k}
    # Games: the two stools face each other like the two benches
    game = extract(room, 'void RoomTavern::tryStartGame(')
    assert 'index < TAVERN_PLACES_PER_TABLE' in game and '(ownSide != otherSide) && ((ownSide < 2) == (otherSide < 2))' in game
    # Stools follow the tables and the room
    update = extract(room, 'void RoomTavern::updateActiveSpots(')
    assert update.count('updateStools(gameMap);') == 3, 'the stools do not follow every layout'
    stools = extract(room, 'void RoomTavern::updateStools(')
    for token in ('new BuildingObject(gameMap, *this, TAVERN_STOOL_MESH, tile, position.x, position.y, 0.0f,',
                  'getSeatPosition(seat, 1)', 'creature->checkWalkPathValid(true)', 'it->second->removeFromGameMap();'):
        assert token in stools, token
    assert 'removeStools();' in extract(room, 'void RoomTavern::removeFromGameMap(')
    assert 'other->removeStools();' in extract(room, 'void RoomTavern::absorbRoom(')
    load = extract(room, 'bool RoomTavern::importFromStream(')
    assert load.count('TAVERN_PLACES_PER_TABLE') == 3 and 'TAVERN_SEATS_PER_TABLE' not in load
    # The own table and stool are no obstacles on the way onto the seat and for the fall of a duel loser
    obstacles = extract(room, 'std::vector<RoomObjectPath::Obstacle> RoomTavern::seatObstacles(')
    assert 'it->position.squaredDistance(stoolPosition)' in obstacles
    assert 'seatObstacles(creature, seat)' in extract(room, 'void RoomTavern::findSeatStagingPoints(')
    assert 'seatObstacles(*creature, own->first)' in extract(room, 'bool RoomTavern::fallNextToBench(')
    navigation = read('source/gamemap/RoomObjectNavigation.cpp')
    assert 'static_cast<RoomTavern*>(room)->getStoolObjects()' in extract(navigation, 'std::vector<RoomObjectPath::Obstacle> RoomObjectNavigation::collect(')
    bounds = read('source/gamemap/RoomObjectBounds.h')
    assert '{"TavernStool", -.1655f, -.1655f, .1655f, .1655f},' in bounds
    assert 'name == "TavernStool"' in bounds
    credits = read('CREDITS')
    assert re.search(r'^models/TavernStool\.mesh\s+AI-generated with Claude Code\s+GPLv3\+\s+Original', credits, re.M)
    assert re.search(r'^tools/tavern-meshes/make_tavern_stool\.py\s+AI-generated', credits, re.M)
    assert (ROOT / 'models' / 'TavernStool.mesh').is_file()
    print('stool code ok: %d stool models, stools at %.1f, places 8 and 9, blocked places, footprint and reach rules' % (len(bodies), STOOL_DISTANCE))


# 2. The mug in the code
def check_mug_code():
    render = read('source/render/RenderManager.cpp')
    assert re.search(r'^const Ogre::Real TAVERN_MUG_GIRTH_SCALE = 1\.8f;$', render, re.M)
    props = extract(render, 'void RenderManager::updateCreatureTavernProps(')
    assert 'mugPoint->setScale(mugScale, mugScale * TAVERN_MUG_GIRTH_SCALE, mugScale * TAVERN_MUG_GIRTH_SCALE);' in props
    assert 'EntityAnimation::isDrinkClip(anim) || fadingDrink' in props
    assert '(EntityAnimation::isSeatClip(previousState->getAnimationName()) != EntityAnimation::isSeatClip(anim))' in props
    blends = extract(render, 'void RenderManager::updateCreatureSeatBlends(')
    assert blends.count('removeCreatureTavernMug(it->mCreature);') == 2
    table = render[render.index('const TavernMugLimbMount TAVERN_MUG_LIMB_MOUNTS[] ='):]
    table = table[:table.index('};')]
    scales = [float(v) for v in re.findall(r', ([0-9.]+)f \}', table)]
    assert len(scales) == 7 and min(scales) >= MIN_LIMB_MUG_SCALE, scales
    entity = read('source/entities/MovableGameEntity.h')
    assert 'return isSeatClip(clip) || (clip == drink_anim);' in extract(entity, 'inline bool hidesWeapons(')
    reactions = read('source/render/CreatureCombatReactions.cpp')
    assert 'EntityAnimation::hidesWeapons(animState->getAnimationName())' in extract(reactions, 'bool playsSeatClip(')
    state = extract(render, 'void RenderManager::rrSetObjectAnimationState(')
    assert '(EntityAnimation::hidesWeapons(anim) != ((previousState != nullptr) && EntityAnimation::hidesWeapons(previousState->getAnimationName())))' in state
    print('mug code ok: girth %.1f, limb mugs >= %.2f, no weapon in Drink, mug kept through the seat blend' % (MUG_GIRTH, MIN_LIMB_MUG_SCALE))


# 3. Finding 8: water on one map, beer on the other
def seat_skills(level, seat_id):
    text = read(level)
    for block in re.findall(r'\[Seat\](.*?)\[/Seat\]', text, re.S):
        if re.search(r'^seatId\s+%d\s*$' % seat_id, block, re.M):
            skills = re.search(r'\[SkillDone\](.*?)\[/SkillDone\]', block, re.S).group(1).split()
            gold = int(re.search(r'^gold\s+(\d+)', block, re.M).group(1))
            player = re.search(r'^player\s+(\S+)', block, re.M).group(1)
            return skills, gold, player
    raise AssertionError((level, seat_id))


def check_drink_duration():
    tavern = block_values(read('config/global.cfg'), 'Tavern')
    assert int(tavern['DrinkTurns']) == 4 and int(tavern['WaterDrinkTurns']) == 14 and int(tavern['BeerDrinkTurns']) == 42 and int(tavern['BeerPrice']) == 5
    room = read('source/rooms/RoomTavern.cpp')
    turns = extract(room, 'int32_t RoomTavern::nextDrinkTurns(')
    assert 'bool beer = servesBeer();' in turns and 'getTavernValue(beer ? "BeerDrinkTurns" : "WaterDrinkTurns")' in turns
    assert 'getSkillLevel(SkillType::tavernBeer) >= 1' in extract(room, 'bool RoomTavern::servesBeer(')
    ghosts, ghost_gold, ghost_player = seat_skills('levels/skirmish/TestGhosts.level', 1)
    spa, spa_gold, spa_player = seat_skills('levels/skirmish/TestSpa.level', 1)
    assert re.search(r'^Name\s+\\\[Test\\\] Ghosts$', read('levels/skirmish/TestGhosts.level'), re.M)
    assert ghost_player == 'Human' and 'tavernBeer' not in ghosts and 'roomTavern' not in ghosts
    assert spa_player == 'Human' and 'tavernBeer' in spa and 'roomTavern' in spa and spa_gold >= 5
    water = 14 / TURNS_PER_SECOND
    beer = 42 / TURNS_PER_SECOND
    assert abs(water - 10.0) < 1e-9 and abs(beer - 30.0) < 1e-9
    print('finding 8 ok: [Test] Ghosts without Beer serves water, %.2f s a drink; [Test] Spa with Beer and %d gold serves beer, %.0f s'
          % (water, spa_gold, beer))


# 4. Finding 9: when a duel starts and how long its parts last
def duel_turns(rng, low, high):
    fewest = max(1, math.ceil(low * TURNS_PER_SECOND - 1e-6))
    most = max(fewest, math.floor(high * TURNS_PER_SECOND + 1e-6))
    return rng.randint(fewest, most)


def simulate_duel(rng, slaps, pauses):
    # playDuelTurn of RoomTavern.cpp, turn by turn; returns the turn the duel ends in
    phase, left, slap_turns, result, turn_a, max_slaps = 'none', 0, 0, 'open', True, 4 * 8
    hp = {True: 100.0, False: 100.0}
    turn, start = 0, None
    while True:
        turn += 1
        if phase == 'pause':
            left -= 1
            if left > 0:
                continue
            pauses.append(turn - start)
            phase = 'none'
        if phase == 'none':
            phase, slap_turns, result, start = 'slap', duel_turns(rng, 4, 10), 'open', turn
            left = slap_turns
            continue
        left -= 1
        if result == 'open' and left <= slap_turns // 2:
            result = 'miss'
            if rng.random() < 0.7:
                if rng.random() * 100 < 10:
                    result = 'crit'
                else:
                    result = 'hit'
                    hp[not turn_a] -= min(10, hp[not turn_a] - 1)
        if left > 0:
            continue
        slaps.append(turn - start)
        if result == 'crit' or (result == 'hit' and hp[not turn_a] < 30):
            return turn
        turn_a = not turn_a
        max_slaps -= 1
        if max_slaps > 0:
            phase, left, start = 'pause', duel_turns(rng, 3, 6), turn
            continue
        return turn


def check_duel():
    text = read('config/rooms.cfg')
    for key, value in (('TavernSlapSecondsMin', '4'), ('TavernSlapSecondsMax', '10'), ('TavernSlapPauseSecondsMin', '3'),
                       ('TavernSlapPauseSecondsMax', '6'), ('CreatureGetUpSeconds', '6'), ('TavernDuelMaxTurnsFactor', '4')):
        assert re.search(r'^\s*' + key + r'\s+' + value + r'\s*$', text, re.M), key
    tavern = block_values(read('config/global.cfg'), 'Tavern')
    assert int(tavern['DuelKoTurns']) == 42 and int(tavern['GameChancePercent']) == 50 and int(tavern['GameTurns']) == 8
    room = read('source/rooms/RoomTavern.cpp')
    # When a duel starts: after the last drink, with GameChancePercent, against a guest of the same keeper at the same
    # table that is done too; a slap duel is one of three games when beer is served
    finish = extract(room, 'void RoomTavern::finishDrink(')
    assert 'Random::Double(0.0, PERCENT_SCALE) < getTavernValue("GameChancePercent")' in finish and 'tryStartGame(own->first)' in finish
    assert finish.index('isPleasureVisitFull') < finish.index('GameChancePercent')
    start = extract(room, 'void RoomTavern::startGame(')
    assert 'const uint32_t nbGames = servesBeer() ? NB_GAMES_WITH_BEER : NB_GAMES_WITHOUT_BEER;' in start
    assert 'Random::Uint(0, nbGames - 1)' in start and 'TavernDuelMaxTurnsFactor' in start
    try_start = extract(room, 'void RoomTavern::tryStartGame(')
    assert '(other->second.mState != TavernGuestState::done) || (other->second.mTurnsLeft <= 0)' in try_start
    assert 'other->second.mCreature->getSeat() != own->second.mCreature->getSeat()' in try_start
    upkeep = extract(room, 'void RoomTavern::doUpkeep(')
    assert upkeep.index('upkeepGames();') < upkeep.index('upkeepSpots();')
    assert '!(it->second.mWantsGame && hasDrinkingTableMate(it->first))' in upkeep
    duel = extract(room, 'void RoomTavern::playDuelTurn(')
    for token in ('randomDuelTurns("TavernSlapSecondsMin", "TavernSlapSecondsMax")', 'randomDuelTurns("TavernSlapPauseSecondsMin", "TavernSlapPauseSecondsMax")',
                  'clock.mTurnsLeft <= clock.mSlapTurns / 2', 'getTavernValue("SlapDuelLoseBelowHp")'):
        assert token in duel, token
    knock = extract(room, 'void RoomTavern::knockOut(')
    assert 'setSpotState(spot, TavernGuestState::ko, static_cast<int32_t>(getTavernValue("DuelKoTurns")));' in knock
    spots = extract(room, 'void RoomTavern::upkeepSpots(')
    assert 'setSpotState(spot, TavernGuestState::getUp, getUpTurns());' in spots

    # How long the parts of a duel last
    rng = random.Random(863)
    slaps, pauses, lengths = [], [], []
    for _ in range(4000):
        lengths.append(simulate_duel(rng, slaps, pauses))
    assert set(slaps) == set(range(6, 15)), sorted(set(slaps))
    assert set(pauses) == set(range(5, 9)), sorted(set(pauses))
    assert 4.0 <= min(slaps) / TURNS_PER_SECOND and max(slaps) / TURNS_PER_SECOND <= 10.0
    assert 3.0 <= min(pauses) / TURNS_PER_SECOND and max(pauses) / TURNS_PER_SECOND <= 6.0
    # The knock-out: set in upkeepGames, counted down by upkeepSpots in the same turn and every turn after it
    # (the turns after the knock-out turn until the get-up starts)
    ko_left, ko_turns = 42, 0
    ko_left -= 1
    while ko_left > 0:
        ko_turns += 1
        ko_left -= 1
    get_up = math.ceil(6 * TURNS_PER_SECOND)
    assert ko_turns == 41 and get_up == 9
    # How often: two guests of one keeper at one table, beer served and paid. Measured with these seeds on this branch:
    # seated in the same turn, a game in 59.4 percent of the visits and a slap duel in 19.8; the second guest 0 to 120 turns
    # later, a game in 28.5 and a duel in 9.5 percent (a guest that is done before its mate came does not wait for it)
    shares = []
    for spread, game_expected, duel_expected in ((0, 0.594, 0.198), (120, 0.285, 0.095)):
        rng = random.Random(8630)
        games = duels = 0
        visits = 20000
        for _ in range(visits):
            kind = table_visit(rng, rng.randint(0, spread) if spread else 0)
            if kind is not None:
                games += 1
                duels += kind == 2
        game_share, duel_share = games / visits, duels / visits
        assert abs(game_share - game_expected) <= 0.015, (spread, game_share)
        assert abs(duel_share - duel_expected) <= 0.015, (spread, duel_share)
        assert abs(duel_share / game_share - 1.0 / 3.0) <= 0.02, 'a slap duel is one of three games'
        shares.append((game_share, duel_share))
    game_share, duel_share = shares[0]
    print('finding 9 ok: slaps %d-%d turns (%.1f-%.1f s), pauses %d-%d turns (%.1f-%.1f s), knock-out %d turns (%.1f s), get-up %d turns (%.1f s); '
          'two guests seated together: game %.0f %%, slap duel %.1f %% of the visits (arriving 0-120 turns apart: %.0f %%, %.1f %%), %.1f slaps per duel'
          % (min(slaps), max(slaps), min(slaps) / 1.4, max(slaps) / 1.4, min(pauses), max(pauses), min(pauses) / 1.4,
             max(pauses) / 1.4, ko_turns, ko_turns / 1.4, get_up, get_up / 1.4, 100 * game_share, 100 * duel_share,
             100 * shares[1][0], 100 * shares[1][1],
             len(slaps) / len(lengths)))


def table_visit(rng, offset):
    # finishDrink, tryStartGame and doUpkeep of RoomTavern.cpp for two guests at one table; returns the game kind
    guests = [{'arrive': 0, 'state': 'away', 'left': 0, 'drinks': 0, 'wants': False},
              {'arrive': offset, 'state': 'away', 'left': 0, 'drinks': 0, 'wants': False}]
    for turn in range(2000):
        for g in guests:
            if g['state'] == 'away' and turn == g['arrive']:
                g['state'], g['left'] = 'drinking', 42
        for index, g in enumerate(guests):
            if g['state'] != 'drinking':
                continue
            g['left'] -= 1
            if g['left'] > 0:
                continue
            g['drinks'] += 1
            if g['drinks'] < 5 and rng.random() * 100 < 50 / 2 ** (g['drinks'] - 1):
                g['left'] = 42
                continue
            g['state'], g['left'], g['wants'] = 'done', 1, False
            if rng.random() * 100 < 50:
                g['wants'] = True
                kind = try_game(rng, guests, index)
                if kind is not None:
                    return kind
        for index, g in enumerate(guests):
            if g['state'] == 'done' and g['wants'] and g['left'] > 0:
                kind = try_game(rng, guests, index)
                if kind is not None:
                    return kind
        for index, g in enumerate(guests):
            mate = guests[1 - index]
            if g['state'] == 'done' and g['left'] > 0 and not (g['wants'] and mate['state'] == 'drinking'):
                g['left'] -= 1
        for g in guests:
            if g['state'] == 'done' and g['left'] <= 0:
                g['state'] = 'gone'
        if all(g['state'] == 'gone' for g in guests):
            return None
    return None


def try_game(rng, guests, index):
    mate = guests[1 - index]
    if mate['state'] == 'done' and mate['left'] > 0:
        return rng.randint(0, 2)
    return None


# 5. The models
def posed_points(skeleton, vertices, weights, rest):
    points = []
    for clip in SEAT_CLIPS:
        played = skeleton.clips[clip]
        points.append(rest.skin_vertices(skeleton, skeleton.locals_at(played, np.linspace(0.0, played.length, SAMPLES)),
                                         vertices, weights).reshape(-1, 3))
    return np.concatenate(points)


def both_scales(points):
    return np.concatenate([points, points * 1.1])


def place(points, kind, a):
    cx, cy, z = points[:, 0], points[:, 1], points[:, 2]
    if kind == 'bench0':
        return np.stack([BENCH_OFFSET + cy, a - cx, z], 1)
    if kind == 'bench1':
        return np.stack([-BENCH_OFFSET - cy, a + cx, z], 1)
    if kind == 'stool8':
        return np.stack([cx, a + cy, z], 1)
    return np.stack([-cx, -a - cy, z], 1)


def voxels(points):
    keys = np.floor(points / VOXEL).astype(np.int64) + 500
    return np.unique(keys[:, 0] * 1000000 + keys[:, 1] * 1000 + keys[:, 2])


def overlap(a, b):
    return np.intersect1d(a, b, assume_unique=True).size > 0


def furniture_depth(points):
    boxes = [((-0.323, 0.323), (-0.588, 0.588), (0.37, 0.4425))]
    for s in (1, -1):
        boxes.append(((-0.193, 0.193), (0.135, 0.521) if s > 0 else (-0.521, -0.135), (0.0, 0.38)))
        boxes.append(((0.3236, 0.4986) if s > 0 else (-0.4986, -0.3236), (-0.656, 0.656), (0.202, 0.2575)))
        for e in (1, -1):
            boxes.append(((s * BENCH_OFFSET - 0.042, s * BENCH_OFFSET + 0.042), (0.515, 0.588) if e > 0 else (-0.588, -0.515), (0.0, 0.21)))
    worst = 0.0
    for (x0, x1), (y0, y1), (z0, z1) in boxes:
        low, high = np.array([x0, y0, z0]), np.array([x1, y1, z1])
        inside = np.all((points > low) & (points < high), axis=1)
        if inside.any():
            q = points[inside]
            worst = max(worst, float(np.minimum(q - low, high - q).min(axis=1).max()))
    return worst


def stool_sink(points):
    # Points of the body (in the frame of the guest, the stool under its origin) in the seat or the post of the stool
    r = np.hypot(points[:, 0], points[:, 1])
    seat = (r < STOOL_RADIUS) & (points[:, 2] < STOOL_TOP - MAX_STOOL_SINK) & (points[:, 2] > STOOL_TOP - 0.035)
    post = (r < STOOL_POST_RADIUS) & (points[:, 2] < STOOL_TOP - 0.035)
    return int(seat.sum()), int(post.sum())


def check_models(out):
    from check_animation_assets import export
    import fix_walk_feet as feet
    import author_rest_poses as rest
    import author_tavern_seats as seats
    # The stool mesh
    export('TavernStool.mesh', out)
    stool = rest.mesh_data(out / 'TavernStool.mesh.xml')[0]
    assert abs(float(stool[:, 2].max()) - STOOL_TOP) < 0.002 and abs(float(stool[:, 2].min())) < 0.002
    radius = float(np.hypot(stool[:, 0], stool[:, 1]).max())
    assert STOOL_RADIUS <= radius <= 0.1655, radius
    top = stool[stool[:, 2] > STOOL_TOP - 0.001]
    assert float(np.hypot(top[:, 0], top[:, 1]).max()) >= STOOL_RADIUS - 0.009
    print('stool mesh ok: seat top %.4f, radius %.4f within the bounds 0.1655' % (float(stool[:, 2].max()), radius))

    meshes = []
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', read('config/creatures.cfg'), re.S):
        mesh = re.search(r'^\s*MeshName\s+(\S+)', block, re.M)
        tavern = re.search(r'^\s*Tavern\s+(\S+)\s+(\S+)', block, re.M)
        if mesh and tavern and (float(tavern.group(1)) > 0.0 or float(tavern.group(2)) > 0.0) and mesh.group(1) not in meshes:
            meshes.append(mesh.group(1))
    assert len(meshes) == 31, len(meshes)
    posed = {}
    for mesh in meshes:
        name = re.findall(rb'([A-Za-z0-9_]+)\.skeleton', (ROOT / 'models' / mesh).read_bytes())[0].decode('ascii')
        export(name + '.skeleton', out)
        export(mesh, out)
        skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
        vertices, _, weights = rest.mesh_data(out / (mesh + '.xml'))
        posed[mesh] = posed_points(skeleton, vertices, weights, rest)
    bench = [m for m in meshes if m not in EXPECTED_BODIES]
    normal = [m for m in bench if m not in LARGE_BENCH_PLACES]

    def bench_y(start, count):
        return (1.5 - start) * SEAT_SPACING - 0.5 * (count - 1) * SEAT_SPACING

    # The reach of the bench guests around their table
    along = across = 0.0
    for mesh in bench:
        count = LARGE_BENCH_PLACES.get(mesh, 1)
        for start in range(0, 5 - count):
            points = place(both_scales(posed[mesh]), 'bench0', bench_y(start, count))
            across = max(across, float(np.abs(points[:, 0]).max()))
            along = max(along, float(np.abs(points[:, 1]).max()))
    assert along <= REACH_ALONG + 1e-6 and REACH_ALONG - along <= MAX_ROUNDING, along
    assert across <= REACH_ACROSS + 1e-6 and REACH_ACROSS - across <= MAX_ROUNDING, across
    print('bench reach ok: %.3f along, %.3f across (limits %.2f, %.2f)' % (along, across, REACH_ALONG, REACH_ACROSS))

    bench_voxels = {}
    for mesh in bench:
        count = LARGE_BENCH_PLACES.get(mesh, 1)
        for kind in ('bench0', 'bench1'):
            for start in range(0, 5 - count):
                bench_voxels[(mesh, kind, start)] = voxels(place(both_scales(posed[mesh]), kind, bench_y(start, count)))
    stool9 = {mesh: voxels(place(both_scales(posed[mesh]), 'stool9', STOOL_DISTANCE)) for mesh in EXPECTED_BODIES}
    for mesh, (blocked, front, back, half) in sorted(EXPECTED_BODIES.items()):
        points = posed[mesh]
        measured = (-float(points[:, 1].min()), float(points[:, 1].max()), float(np.abs(points[:, 0]).max()))
        for value, limit, what in zip(measured, (front, back, half), ('front', 'back', 'half width')):
            assert value <= limit + 1e-6 and limit - value <= MAX_ROUNDING, (mesh, what, value, limit)
        scaled = both_scales(points)
        seat_points, post_points = stool_sink(scaled)
        assert seat_points == 0 and post_points == 0, (mesh, 'reaches into the stool', seat_points, post_points)
        placed = place(scaled, 'stool8', STOOL_DISTANCE)
        depth = furniture_depth(placed)
        assert depth <= MAX_TABLE_DEPTH, (mesh, 'reaches into the table', depth)
        own = voxels(placed)
        reached = 0
        for (other, kind, start), cells in bench_voxels.items():
            if overlap(own, cells):
                reached = max(reached, start + 1)
        assert reached == blocked, (mesh, 'blocked places', reached, blocked)
        for other, cells in stool9.items():
            assert not overlap(own, cells), (mesh, 'touches the guest of the other stool', other)
        print('stool %-20s footprint %.3f/%.3f/%.3f, blocks %d places, %.3f into the table, nothing in the stool'
              % (mesh, measured[0], measured[1], measured[2], blocked, depth))
    # The bodies on legs hang through the seat of a stool under them: they keep their benches
    for mesh in BENCH_MODELS_ON_LEGS:
        seat_points, post_points = stool_sink(both_scales(posed[mesh]))
        assert seat_points + post_points > 0, (mesh, 'would fit on a stool')
        print('bench %-10s keeps the bench: %d points through the seat and %d in the post of a stool' % (mesh, seat_points, post_points))

    # The wide mug: in the table top and above the floor
    export('TavernMug.mesh', out)
    mug = rest.mesh_data(out / 'TavernMug.mesh.xml')[0]
    wide = mug.copy()
    wide[:, 1:] *= MUG_GIRTH
    turned = wide @ seats.MUG_TURN.T
    names = sorted({re.findall(rb'([A-Za-z0-9_]+)\.skeleton', (ROOT / 'models' / m).read_bytes())[0].decode('ascii') for m in meshes})
    worst = 0.0
    for name in names:
        skeleton = feet.Skel(str(out / (name + '.skeleton.xml')))
        if seats.MUG_BONE not in skeleton.idx:
            continue
        for clip in ('SitDrink', 'Drink'):
            played = skeleton.clips[clip]
            world = skeleton.fk(skeleton.locals_at(played, np.linspace(0.0, played.length, 97)))[skeleton.idx[seats.MUG_BONE]]
            points = world[0][:, None, :] + np.einsum('nij,nmj->nmi', world[1], turned[None, :, :] * world[2][:, None, :])
            for scale in (1.0, 1.1):
                q = points * scale
                if clip == 'SitDrink':
                    inside = (q[:, :, 1] < -0.108) & (q[:, :, 1] > -0.735) & (q[:, :, 2] > 0.39) & (q[:, :, 2] < 0.4225)
                    share = float(inside.mean(axis=1).max())
                    worst = max(worst, share)
                    assert share <= MAX_MUG_IN_TABLE, (name, 'the wide mug sinks into the table', share)
                else:
                    assert float(q[:, :, 2].min()) >= MIN_MUG_FLOOR, (name, 'the wide mug sinks into the floor')
    print('wide mug ok: at most %.0f %% of it 0.02 deep in the table top in SitDrink, above the floor in Drink' % (100 * worst))


def main():
    check_stool_code()
    check_mug_code()
    check_drink_duration()
    check_duel()
    converter = os.environ.get('OGRE_XML_CONVERTER') or shutil.which('OgreXMLConverter') or shutil.which('OgreXMLConverter.exe')
    if converter is None:
        print('models skipped: OgreXMLConverter not found')
    else:
        with tempfile.TemporaryDirectory(prefix='odp-tavern-stools-') as directory:
            check_models(Path(directory))
    print('tavern stools 863 ok')


if __name__ == '__main__':
    main()
