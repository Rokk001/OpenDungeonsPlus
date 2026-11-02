"""Tavern and thirst rules: the real functions of the thirst model and of the tavern are cut out of the sources and run
against small stubs; the random rolls are scripted so that every threshold is hit from both sides.

What is run (the function bodies are taken from the source files, not copied by hand):
  Creature::increaseThirst / setThirst / drinkTaken / increaseUrge / setDrunk / setHangoverTurns / addTavernMood /
  isStaggering / getHangoverWorkFactor / sleepStarted / sleepEnded / upkeepTavernState
                      thirst growth and the clamp at 100, rogue creatures and types without thirst (no hunger, no thirst),
                      the notice at 100, a drink sets thirst 0 and raises the urge (beer 15, water 5), beer adds 25
                      drunkenness (cap 100) and water none, decay 0.5 per turn, stagger at 50, the vomit mark is reset
                      below 75, a hangover of 252 turns after a sleep that started above 50 (not shortened, mood -10,
                      half work), the tavern mood value and its timer
  RoomTavern::servesBeer / payForBeer / finishDrink / tryStartGame / startGame / playContestTurn / playDuelTurn /
  cheerSpectators / concludeGame / abortGame / abortDisturbedGuests / knockOut / upkeepSpots / addDrinkDirt
                      beer only with the research, both payment paths and their fallbacks to water, the drink chain
                      50 / 25 / 12.5 / 6.25 percent with the cap of five, the 50 percent game chance and the same table
                      rule, eight places per table (four per bench), two neighbouring places for a large creature and
                      mixed benches, the draw of the three games (the slap duel only with beer), the underdog chances with the
                      floor of 5 percent, underdog mood and double experience, spectators, the slap duel (10 HP per hit,
                      critical chance 10 +- 0.25 per level, knock-out at a critical or below 30 HP, HP never below 1,
                      the time limit), 42 turns lying then getting up, a fight, a flight, a knock-out or a pick-up ends a
                      game without effects
  CreatureMoodThirst::computeMood      the same numbers as the hunger mood, for prisoners as for every seat creature
  RoomPortal getResearchedCooldown     the portal cooldown factors 1.0 / 0.9 / 0.8 per Beer level
The values come from config/global.cfg [Tavern] and config/rooms.cfg. The source wiring (where thirst is sought, where the
hangover factor is used, the vomit pile) is checked on the source text.

Calls (from the repository root):
  python source/tests/check_tavern_rules.py

The probe needs the MSVC compiler on the path (run it in a Visual Studio developer shell, like the other probes)."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]


# Returns the text of a repository file.
def read(path):
    return (root / path).read_text(encoding='utf-8')


# Returns the text of a function from its first line up to its closing brace (a brace in column 0).
def extract(text, header):
    start = text.index(header)
    end = text.index('\n}\n', start) + 2
    return text[start:end]


# Returns the key -> value words of the first block [tag]...[/tag] of a text (comments skipped).
def block_values(text, tag):
    match = re.search(r'^\[' + tag + r'\]\s*$(.*?)^\[/' + tag + r'\]', text, re.M | re.S)
    assert match is not None, 'block [' + tag + '] missing'
    values = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            values.setdefault(words[0], words[1])
    return values


# Returns the line of a text that matches a regular expression.
def find_line(text, pattern):
    match = re.search(pattern, text, re.M)
    assert match is not None, pattern
    return match.group(0)


creature_cpp = read('source/entities/Creature.cpp')
room_cpp = read('source/rooms/RoomTavern.cpp')

# Furniture occupies distinct tiles, kegs require a full neighbouring wall, and ordering is stable across saves.
placement = extract(room_cpp, 'void RoomTavern::updateActiveSpots(')
assert 'std::sort(orderedTiles.begin(), orderedTiles.end(), Room::compareTile)' in placement
assert 'orderedTiles.size() / TAVERN_TILES_PER_TABLE' in placement and 'orderedTiles.size() / TAVERN_TILES_PER_KEG' in placement
assert 'const size_t TAVERN_TILES_PER_KEG = 6;' in room_cpp and 'const size_t TAVERN_TILES_PER_TABLE = 8;' in room_cpp
assert 'neighbours[i]->isFullTile()' in placement
assert 'std::find(furnitureTiles.begin(), furnitureTiles.end(), tile) != furnitureTiles.end()' in placement
assert 'wantedObjects[mCounterTile] = TAVERN_COUNTER_MESH' in placement

# The table carries its two benches; it is scaled so that across (1.19 tiles unscaled) it stays on its tiles and along
# (1.56 tiles unscaled, two tiles long) it stays on its two tiles.
scale = float(find_line(room_cpp, r'const float TAVERN_TABLE_SCALE = [0-9.]+f;').split('=')[1].strip().rstrip('f;'))
assert 1.19 * scale <= 1.0, 'the benches of the table stay on its tiles'
assert 1.56 * scale <= 2.0, 'the long table stays on its two tiles'
assert 'object->setFurnitureScale(Ogre::Vector2(TAVERN_TABLE_SCALE, TAVERN_TABLE_SCALE));' in placement

# A table is two tiles long (decision of the owner): it is tried in both directions on two free tiles of the room, stands
# halfway between them, and no table is placed when no such pair is left. Its second tile follows from its angle, so the
# saved line of a table stays one tile and one angle and loads 1:1; a table whose second tile is lost goes away.
assert 'const double TABLE_ANGLES[] = { 0.0, 90.0 };' in room_cpp
assert 'second = tableSecondTile(gameMap, *tile, angle);' in placement
assert '(std::find(furnitureTiles.begin(), furnitureTiles.end(), second) != furnitureTiles.end())' in placement
assert 'furnitureTiles.push_back(bestSecond);' in placement and 'if(best == nullptr)\n                break;' in placement
assert 'const Ogre::Vector2 middle = tableMiddle(*tile, angle);' in placement
assert 'second = tableSecondTile(gameMap, *saved.mTile, saved.mAngle);' in placement, 'a saved table needs its second tile'
assert 'covered = (second != nullptr) && (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), second) != mCoveredTiles.end());' in placement
assert 'std::abs(static_cast<double>(existing->second->getRotationAngle()) - angle) < ANGLE_EPSILON' in placement, 'a turned table is placed again'
table_step = extract(room_cpp, 'void tableStep(')
assert 'dx = static_cast<int32_t>(std::floor(-std::sin(angle) + 0.5));' in table_step and 'dy = static_cast<int32_t>(std::floor(std::cos(angle) + 0.5));' in table_step
# The step to the second tile turns like the seats: (0, 1) at 0 degrees, (-1, 0) at 90, (0, -1) at 180, (1, 0) at 270
import math
for degrees, step in ((0.0, (0, 1)), (90.0, (-1, 0)), (180.0, (0, -1)), (270.0, (1, 0))):
    radians = degrees * math.pi / 180.0
    assert (math.floor(-math.sin(radians) + 0.5), math.floor(math.cos(radians) + 0.5)) == step, degrees
furniture_on = extract(room_cpp, 'bool RoomTavern::hasFurnitureOn(')
assert 'tableSecondTile(getGameMap(), *entry.first, entry.second->getRotationAngle()) == tile' in furniture_on

# Save/load keeps every keg and table 1:1: one Furniture line each, read back and placed instead of being recomputed.
export = extract(room_cpp, 'void RoomTavern::exportToStream(')
assert 'os << STREAM_TAG_FURNITURE' in export and 'getRotationAngle()' in export
load = extract(room_cpp, 'bool RoomTavern::importFromStream(')
assert 'tag == STREAM_TAG_FURNITURE' in load and 'mSavedFurniture.push_back(saved);' in load
assert 'const bool restoreSaved = !mSavedFurniture.empty();' in placement and 'mSavedFurniture.clear();' in placement
assert '!restoreSaved && (kind < 2)' in placement
assert 'const size_t limit = (kind == 0) ? kegLimit : tableLimit;' in placement
assert 'if(!wall || adjacentKeg)' in placement
assert 'if((benchesFree && !bestBenchesFree) || ((benchesFree == bestBenchesFree) && (distance > bestDistance)))' in placement
assert 'benchesFree = areBenchSidesFree(gameMap, *tile, *second, orderedTiles, furnitureTiles);' in placement

# The furniture stays while the tiles and the counter stay; a change spreads it again and all guests stand up.
assert '(orderedTiles != mLayoutTiles) || (mCounterTile != mLayoutCounter)' in placement
assert 'if(hadLayout && layoutChanged)' in placement and 'standUpGuests();' in placement
stand_up = extract(room_cpp, 'void RoomTavern::standUpGuests(')
assert 'mGames.clear();' in stand_up and 'pickFreeSeat(*guest.mCreature, seat)' in stand_up and 'sendToOtherTavernOrWork(*creature, otherTavern);' in stand_up
assert 'TavernGuestState::game' in stand_up, 'a guest whose game ended looks for a seat again'
# A guest without a seat tries another tavern of the keeper, otherwise it goes to work under the visit cooldown.
assert 'startTavernCooldown();' in extract(room_cpp, 'void RoomTavern::sendToOtherTavernOrWork(')
assert 'hasOpenCreatureSpot(&creature)' in extract(room_cpp, 'Room* RoomTavern::findOtherTavern(')
# A lost tile or table does not dismiss a guest: it looks for a seat again.
assert 'clearActionQueue' not in extract(room_cpp, 'bool RoomTavern::removeCoveredTile(')
assert 'standUpGuests();' in extract(room_cpp, 'void RoomTavern::reseatGuestsAtLostTables(')
# A save without seat data spreads the furniture again, ends its games and lets its guests look for a seat.
assert 'if(!hasSeatLayout)' in load and 'mSavedFurniture.clear();' in load and 'mPendingGames.clear();' in load
assert 'os << STREAM_TAG_SEAT_LAYOUT' in export
# Format 2 has the tables of two tiles; a save of format 1 (tables of one tile) is spread again like one without seat data
assert 'const uint32_t SEAT_LAYOUT_VERSION = 2;' in room_cpp
assert 'hasSeatLayout = (version == SEAT_LAYOUT_VERSION);' in load and '(version == 0) || (version > SEAT_LAYOUT_VERSION)' in load
# Guests walk to a seat on a bench, never to the middle of a tile with furniture, and step off it when they leave.
use_room_text = extract(room_cpp, 'bool RoomTavern::useRoom(')
assert 'walkToSeat(creature, seat, spot.mTwoPlaces)' in use_room_text and 'stepOffSeat(creature, seat, spot.mTwoPlaces)' in use_room_text
assert 'setDestination' not in use_room_text
walk_to_seat = extract(room_cpp, 'bool RoomTavern::walkToSeat(')
assert 'EntityAnimation::sit_anim, true, false, route, false, true' in walk_to_seat
# Without a way around the furniture a guest takes another seat or leaves; it never walks through furniture.
assert 'path(&creature, seat.mTable)' not in walk_to_seat
assert '!walkToOtherSeat(creature, seat)' in use_room_text
# A guest closed in on its seat stays on it, and the plain tile path never leads through tavern furniture.
assert 'if(stepOffSeat(creature, seat, spot.mTwoPlaces))' in use_room_text
set_destination = extract(read('source/entities/Creature.cpp'), 'bool Creature::setDestination(')
assert 'RoomType::tavern' in set_destination and 'static_cast<RoomTavern*>(room)->hasFurnitureOn(step)' in set_destination
assert set_destination.index('RoomType::tavern') < set_destination.index('path, true, true)')
# A player of a game that ended with the room change sits down again and orders no further drink for it.
assert 'guest.mWantsGame = !visitOver && (guest.mState == TavernGuestState::game);' in extract(room_cpp, 'void RoomTavern::standUpGuests(')
assert use_room_text.index('if(spot.mWantsGame)') < use_room_text.index('On the seat the first drink starts')
# Sitting down and getting up blend the clips.
render_cpp = read('source/render/RenderManager.cpp')
assert 'mCreatureSeatBlends.push_back' in render_cpp and 'updateCreatureSeatBlends(timeSinceLastFrame);' in render_cpp
assert render_cpp.count('cancelCreatureSeatBlend(curCreature);') == 2
# The walk into the room ends on free floor next to the seat, not on a tile of a table (also not on its second tile).
arrival = extract(room_cpp, 'Tile* RoomTavern::getArrivalTile(')
assert 'hasFurnitureOn(tile)' in arrival and 'getSeatPosition(it->first, it->second.mTwoPlaces)' in arrival
# The benches of the scaled table mesh: seat surface 0.39 to 0.59 from the middle, bench 1.31 long with four places.
assert 'const float TAVERN_BENCH_OFFSET = 0.4116f;' in room_cpp and 'const float TAVERN_SEAT_SPACING = 0.328f;' in room_cpp
tavern_h_text = read('source/rooms/RoomTavern.h')
assert 'const uint32_t TAVERN_SEATS_PER_BENCH = 4;' in tavern_h_text
assert 'const uint32_t TAVERN_SEATS_PER_TABLE = 2 * TAVERN_SEATS_PER_BENCH;' in tavern_h_text
assert 'const uint32_t TAVERN_SEATS_PER_LARGE_GUEST = 2;' in tavern_h_text
# The places of a bench, from the formula of seatOffset: four places 0.328 apart, symmetric around the middle of the table;
# a large guest sits in the middle of two places, above a pedestal. All of them lie on the bench (1.56 x 0.84 long).
seat_offset = extract(room_cpp, 'Ogre::Vector2 seatOffset(')
assert 'float y = (0.5f * static_cast<float>(TAVERN_SEATS_PER_BENCH - 1) - place) * TAVERN_SEAT_SPACING;' in seat_offset
assert 'y -= 0.5f * static_cast<float>(TAVERN_SEATS_PER_LARGE_GUEST - 1) * TAVERN_SEAT_SPACING;' in seat_offset
spacing = 0.328
places = [(0.5 * 3 - place) * spacing for place in range(4)]
large_places = [(0.5 * 3 - place) * spacing - 0.5 * spacing for place in (0, 2)]
assert [round(value, 3) for value in places] == [0.492, 0.164, -0.164, -0.492], places
assert [round(value, 3) for value in large_places] == [0.328, -0.328], large_places
bench_half = 0.78 * scale
assert all(abs(value) + 0.5 * spacing <= bench_half + 1e-3 for value in places), 'every place lies on the bench'
assert all(abs(abs(value) - 0.39 * scale) < 0.01 for value in large_places), 'a large guest sits above a pedestal'
# A seated guest looks straight across its table, wherever it sits along the bench
assert 'towardsTable = getAcrossTableDirection(own->first);' in extract(room_cpp, 'void RoomTavern::showSpotState(')
assert 'getBedDim1() >= 2' in extract(room_cpp, 'bool RoomTavern::isLargeGuest(') and 'getBedDim2() >= 2' in extract(room_cpp, 'bool RoomTavern::isLargeGuest(')
# Tables, kegs and the counter are obstacles of the navigation, drawn at their authored size.
bounds_h = read('source/gamemap/RoomObjectBounds.h')
for mesh in ('TavernCounter', 'TavernKeg', 'TavernTable'):
    assert '{"' + mesh + '", ' in bounds_h and 'name == "' + mesh + '"' in bounds_h, mesh
assert '{"TavernTable", -.595f, -.78f, .595f, .78f, .4425f},' in bounds_h, 'the navigation knows the long table'

# A creature without a seat does not enter; a thirsty one tries again after the visit cooldown.
assert 'creature.startTavernCooldown();' in read('source/creatureaction/CreatureActionSearchDrink.cpp')
use_room_action = read('source/creatureaction/CreatureActionUseRoom.cpp')
assert '!room->hasCreatureUsingRoom(creature)' in use_room_action and 'room->getArrivalTile(creature)' in use_room_action
assert creature_cpp.count('(mTavernCooldownTurns <= 0)') == 3
# The loser falls onto a free floor tile, or slumps on its seat when none is free.
fall = extract(room_cpp, 'bool RoomTavern::fallNextToBench(')
assert 'hasFurnitureOn(tile)' in fall and 'tile->getCoveringRoom() != this' in fall
assert 'getGameMap()->getTile(seatX + dx, seatY + dy)' in fall, 'the loser falls next to its own place of the long bench'
assert 'standingPosition(solid, middle, point)' in fall and 'clearSegment(onTheWay, position, point)' in fall
assert 'if(!fallNextToBench(spot))' in extract(room_cpp, 'void RoomTavern::knockOut(')
assert 'EntityAnimation::sit_slumped_anim' in extract(room_cpp, 'void RoomTavern::showSpotState(')

portal_cpp = read('source/rooms/RoomPortal.cpp')
mood_thirst_cpp = read('source/creaturemood/CreatureMoodThirst.cpp')
mood_hunger_cpp = read('source/creaturemood/CreatureMoodHunger.cpp')
global_cfg = read('config/global.cfg')
rooms_cfg = read('config/rooms.cfg')
skills_cfg = read('config/skills.cfg')

# ---- Source wiring -----------------------------------------------------------------------------------------------
# Thirst grows where hunger grows (rogue creatures are skipped by the same condition) and the idle decision seeks a tavern
growth_at = creature_cpp.index('increaseThirst(mDefinition->getThirstGrowthPerTurn());')
assert 'increaseHunger(mDefinition->getHungerGrowthPerTurn());' in creature_cpp[growth_at - 400:growth_at]
assert 'if(getSeat()->isRogueSeat())' in creature_cpp[growth_at - 800:growth_at], 'thirst growth is split for rogue creatures (they grow directly)'
seek = creature_cpp[creature_cpp.index('// If we are thirsty, we go to a tavern'):]
seek = seek[:seek.index('return true;')]
assert 'getTavernConfigDouble("ThirstSeek")' in seek and 'isWorker()' in seek and 'hasThirst()' in seek, 'seek at ThirstSeek, never for workers or types without thirst'
food_at = creature_cpp.index('pushAction(Utils::make_unique<CreatureActionSearchFood>')
assert food_at < creature_cpp.index('CreatureActionSearchDrink>(*this'), 'the thirst check follows the hunger check'
# The upkeep of the tavern state runs every turn; a staggering creature is slower
assert 'upkeepTavernState();' in creature_cpp
assert creature_cpp.count('getTavernConfigDouble("StaggerSpeedFactor")') == 2 and creature_cpp.count('if(isStaggering())') == 2
# One vomit per drunk episode at VomitAt, with a vomit pile of the dirt model
vomit_check = creature_cpp[creature_cpp.index('// If we are drunk enough, we vomit once per drunk episode'):]
vomit_check = vomit_check[:vomit_check.index('return true;')]
assert '!mVomited' in vomit_check and 'getTavernConfigDouble("VomitAt")' in vomit_check and 'mVomited = true;' in vomit_check
vomit_action = read('source/creatureaction/CreatureActionVomit.cpp')
assert 'DirtPileEntity::createOnTile(mCreature.getGameMap(), myTile, DirtPileKind::vomit' in vomit_action
assert 'vomit_anim' in vomit_action and '"DrinkTurns"' in vomit_action
# A hangover halves the room points and the experience of the library, the workshop, the training hall and the arena
for path, token in (('source/rooms/RoomLibrary.cpp', 'creature.getHangoverWorkFactor()'), ('source/rooms/RoomWorkshop.cpp', 'creature.getHangoverWorkFactor()'),
                    ('source/rooms/RoomTrainingHall.cpp', 'creature.getHangoverWorkFactor()')):
    assert token in read(path), path + ' must use the hangover work factor'
assert 'getHangoverWorkFactor()' in creature_cpp[creature_cpp.index('attackRoom->getDirtOutputFactor()') - 200:creature_cpp.index('attackRoom->getDirtOutputFactor()') + 200]
# The sleep start and end notes are called by the sleep action
sleep_cpp = read('source/creatureaction/CreatureActionSleep.cpp')
assert 'sleepStarted()' in sleep_cpp and 'sleepEnded()' in sleep_cpp
# The tavern mood is summed with the other mood parts, the thirst mood has the same numbers as the hunger mood and checks
# neither a seat nor a prison: prisoners get the malus like every seat creature, seat-less heroes have no mood at all
assert 'getTavernMood()' in read('source/creaturemood/CreatureMoodManager.cpp')
for text in (mood_thirst_cpp, mood_hunger_cpp):
    compute = extract(text, 'double CreatureMood' + ('Thirst' if text is mood_thirst_cpp else 'Hunger') + '::computeMood(')
    assert 'getSeat' not in compute and 'Prison' not in compute and 'isPrisoner' not in compute, 'the thirst/hunger mood is the same for every creature'
# Games end without effects on a fight, a flight, a knock-out, a pick-up
disturbed = extract(room_cpp, 'bool RoomTavern::isGuestDisturbed(')
for token in ('isKo()', 'isBeingDragged()', 'CreatureActionType::fight', 'CreatureActionType::flee'):
    assert token in disturbed, token
# The loser of a slap duel goes to its bed after the visit, whatever its wakefulness
assert 'CreatureActionSleep' in extract(room_cpp, 'bool RoomTavern::useRoom(') and 'goToBed' in room_cpp

# A guest leaves the tavern: the visit pops the action, the leaving starts the leisure cooldown, the job search does not
# send the guest back in during the cooldown, and the cooldown counts down every turn and is saved
assert 'creature.popAction();' in extract(room_cpp, 'bool RoomTavern::useRoom(')
assert re.search(r'const int32_t DONE_WAIT_TURNS = 1;', room_cpp), 'completed visits wait at most one turn'
finish_drink = extract(room_cpp, 'void RoomTavern::finishDrink(')
assert 'setSpotDone(spot, DONE_WAIT_TURNS);' in finish_drink and 'spot.mTurnsLeft =' not in finish_drink, 'a game request must not extend the completed visit'
# The room consumes the one-turn wait and the done action then ends; conscious game players have no extra wait.
upkeep = extract(room_cpp, 'void RoomTavern::doUpkeep(')
assert re.search(r'if\(\(it->second.mState == TavernGuestState::done\) && \(it->second.mTurnsLeft > 0\)\)\s*--it->second.mTurnsLeft;', upkeep), 'each upkeep must consume the completed visit wait'
use_room = extract(room_cpp, 'bool RoomTavern::useRoom(')
done_action = use_room[use_room.index('case TavernGuestState::done:'):use_room.index('default:')]
assert re.search(r'if\(spot.mTurnsLeft > 0\)\s*return false;', done_action), 'only a positive completed visit wait may delay exit'
assert re.search(r'creature.popAction\(\);\s*if\(goToBed\)\s*creature.pushAction\([^;]+;\s*return true;', done_action), 'the completed visit must pop its action and resume the action queue'
conclude = extract(room_cpp, 'void RoomTavern::concludeGame(')
assert 'setSpotDone(winnerSpot->second, 0);' in conclude and 'setSpotDone(loserSpot->second, 0);' in conclude, 'conscious game players must finish without a wait'
assert 'knockOut(loserSpot->second);' in conclude, 'the slap duel loser keeps the decided knock-out exception'
assert 'startTavernCooldown()' in extract(room_cpp, 'void RoomTavern::removeCreatureUsingRoom(')
open_spot = extract(room_cpp, 'bool RoomTavern::hasOpenCreatureSpot(')
assert 'getTavernCooldownTurns() > 0' in open_spot and 'getThirst() < getTavernValue("ThirstSeek")' in open_spot, 'leisure visit blocked during the cooldown, thirst not'
assert 'hasOpenCreatureSpot(&creature)' in read('source/creatureaction/CreatureActionSearchJob.cpp')
assert 'TavernLeisureCooldownTurns' in extract(creature_cpp, 'void Creature::startTavernCooldown(')
assert '--mTavernCooldownTurns' in extract(creature_cpp, 'void Creature::upkeepTavernState(')
assert 'TAVERN_COOLDOWN_SAVE_OPEN << " " << mTavernCooldownTurns' in creature_cpp and 'setTavernCooldownTurns(loadedCooldown)' in creature_cpp, 'cooldown saved and loaded'
assert re.search(r'^\s+TavernLeisureCooldownTurns\s+600\s*$', rooms_cfg, re.M), 'TavernLeisureCooldownTurns is 600 in rooms.cfg'

# ---- Probe -------------------------------------------------------------------------------------------------------
tavern = block_values(global_cfg, 'Tavern')
rooms = block_values(rooms_cfg, 'Rooms')
config_entries = [(k, v) for k, v in tavern.items()] + [('Room' + k, rooms[k]) for k in ('TavernDirtPerDrink', 'PortalCooldownSpawnMin', 'PortalCooldownSpawnMax',
    'TavernDuelMaxTurnsFactor', 'TavernDrinkChainHalving')]
config_table = ',\n'.join('    {"%s", %s}' % (k, v) for k, v in config_entries)
effect_line = re.search(r'^\s*tavernBeer\s+PortalCooldown\s+mul\s+(\S+)\s+(\S+)\s+(\S+)\s*$', skills_cfg, re.M)
assert effect_line is not None, 'the portal cooldown effect line is missing'
effect_table = ', '.join(effect_line.groups())

probe = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <string>
#include <vector>

#define OD_LOG_WRN(x) do { } while(0)
#define OD_LOG_ERR(x) do { } while(0)

static int failures = 0;
static void expect(bool ok, const std::string& what) { if(!ok) { ++failures; std::cout << "FAIL: " << what << std::endl; } }
static void expectNear(double a, double b, const std::string& what, double eps = 1e-9)
{ if(std::fabs(a - b) > eps) { ++failures; std::cout << "FAIL: " << what << " got " << a << " expected " << b << std::endl; } }

namespace Ogre
{
typedef float Real;
struct Vector3
{
    Real x, y, z;
    Vector3() : x(0), y(0), z(0) {}
    Vector3(Real ax, Real ay, Real az) : x(ax), y(ay), z(az) {}
    Real squaredLength() const { return x * x + y * y + z * z; }
    void normalise() { Real l = std::sqrt(squaredLength()); if(l > 0) { x /= l; y /= l; z /= l; } }
    static const Vector3 ZERO;
};
const Vector3 Vector3::ZERO(0, 0, 0);
}

// ---- Scripted random numbers: a roll takes the next scripted value; without one a double roll fails every chance
// (100) and an integer roll takes its lower bound
namespace Random
{
static std::vector<double> doubles; static std::vector<uint32_t> uints; static unsigned doublePos = 0, uintPos = 0;
static uint32_t lastUintMax = 0;
static void script(const std::vector<double>& d, const std::vector<uint32_t>& u) { doubles = d; uints = u; doublePos = 0; uintPos = 0; lastUintMax = 0; }
static double Double(double a, double b) { return (doublePos < doubles.size()) ? doubles[doublePos++] : 100.0; }
static uint32_t Uint(uint32_t a, uint32_t b) { lastUintMax = b; return (uintPos < uints.size()) ? uints[uintPos++] : a; }
}

// ---- Configuration: the real values of the config files, an unknown key is a failure
struct ConfigManager
{
    std::map<std::string, double> values;
    static ConfigManager& getSingleton() { static ConfigManager instance; return instance; }
    double lookup(const std::string& key) const
    {
        std::map<std::string, double>::const_iterator it = values.find(key);
        if(it == values.end()) { ++failures; std::cout << "FAIL: unknown config key " << key << std::endl; return 0.0; }
        return it->second;
    }
    double getTavernConfigDouble(const std::string& key) const { return lookup(key); }
    double getRoomConfigDouble(const std::string& key) const { return lookup("Room" + key); }
    uint32_t getRoomConfigUInt32(const std::string& key) const { return static_cast<uint32_t>(lookup("Room" + key)); }
    //! \brief Returns the shipped room value; the probe needs every key in the config, so the default is not used.
    double getRoomConfigDoubleOrDefault(const std::string& key, double) const { return lookup("Room" + key); }
    double getDirtConfigDouble(const std::string& key) const { return lookup(key); }
};
static void loadConfig()
{
    static const struct { const char* key; double value; } table[] = {
@@CONFIG@@
    };
    for(unsigned i = 0; i < sizeof(table) / sizeof(table[0]); ++i)
        ConfigManager::getSingleton().values[table[i].key] = table[i].value;
}

enum class SkillType { tavernBeer, other };
enum class CreatureActionType { fight, fightFriendly, flee, other };
enum class ResearchEffect { PortalCooldown };
struct EntityAnimation { static const std::string sit_slap_anim; static const std::string sit_slapped_anim; };
const std::string EntityAnimation::sit_slap_anim = "SitSlap";
const std::string EntityAnimation::sit_slapped_anim = "SitSlapped";
@@DRINKKIND@@
static const double THIRST_STATE_MAX = 100.0;
static const double NEED_MAX = 100.0;

struct Creature; struct Tile; struct GameMap; struct Seat;

struct Tile
{
    int x, y; double dirt;
    Tile(int ax, int ay) : x(ax), y(ay), dirt(0.0) {}
    int getX() const { return x; } int getY() const { return y; }
    void addDirt(double amount) { dirt += amount; }
};

struct Player
{
    int notices; bool human;
    Player() : notices(0), human(true) {}
    void notifyTavernEvent() { ++notices; }
    bool getIsHuman() const { return human; }
};

// The seat: rogue flag, id, level of the Beer research and the player
struct Seat
{
    bool rogue; int id; uint32_t beerLevel; Player* player;
    Seat() : rogue(false), id(1), beerLevel(0), player(nullptr) {}
    bool isRogueSeat() const { return rogue; }
    int getId() const { return id; }
    uint32_t getSkillLevel(SkillType type) const { return (type == SkillType::tavernBeer) ? beerLevel : 0; }
    Player* getPlayer() const { return player; }
};

struct CreatureDefinition
{
    bool thirsty; int bedDim;
    explicit CreatureDefinition(bool t) : thirsty(t), bedDim(1) {}
    bool hasThirst() const { return thirsty; }
    int getBedDim1() const { return bedDim; }
    int getBedDim2() const { return bedDim; }
};

//! \brief Supplies tavern creature state with the production fractional purse API.
struct Creature
{
    CreatureDefinition* mDefinition; Seat* mSeat; std::string mName; Tile* mTile; Ogre::Vector3 mPos;
    double mUrge, mThirst, mTavernMood, mTavernMoodTurns, mDrunk, mHangoverTurns, mHp, mExp;
    bool mVomited, mHangoverPending, mOnMap, mAlive, mKo, mDragged, mPossessed, mFighting, mFleeing, mHit;
    uint32_t mLevel; double mGold; int takeDamageCalls; int32_t mTavernCooldownTurns = 0;
    //! \brief Initializes the tavern creature with the production fractional gold balance.
    Creature(const std::string& name, CreatureDefinition* def, Seat* seat, uint32_t level)
      : mDefinition(def), mSeat(seat), mName(name), mTile(nullptr), mUrge(0.0), mThirst(0.0), mTavernMood(0.0), mTavernMoodTurns(0.0), mDrunk(0.0),
        mHangoverTurns(0.0), mHp(100.0), mExp(0.0), mVomited(false), mHangoverPending(false), mOnMap(true), mAlive(true), mKo(false),
        mDragged(false), mPossessed(false), mFighting(false), mFleeing(false), mHit(true), mLevel(level), mGold(0), takeDamageCalls(0) {}
    Seat* getSeat() const { return mSeat; }
    CreatureDefinition* getDefinition() const { return mDefinition; }
    const std::string& getName() const { return mName; }
    bool getIsOnServerMap() const { return true; }
    bool getIsOnMap() const { return mOnMap; }
    bool isAlive() const { return mAlive; }
    bool isKo() const { return mKo; }
    bool isBeingDragged() const { return mDragged; }
    bool isPossessed() const { return mPossessed; }
    bool isActionInList(CreatureActionType type) const
    { return ((type == CreatureActionType::fight) && mFighting) || ((type == CreatureActionType::flee) && mFleeing); }
    uint32_t getLevel() const { return mLevel; }
    double getHP() const { return mHp; }
    double getAttackRating() const { return 300.0; }
    bool rollAttackHit(double attackRating, uint32_t attackerLevel, bool possessed) const { return mHit; }
    double takeDamage(Creature* attacker, double absoluteDamage, double a, double b, double c, Tile* tile, bool d)
    { ++takeDamageCalls; mHp -= absoluteDamage; return absoluteDamage; }
    void receiveExp(double xp) { mExp += xp; }
    //! \brief Returns the full production purse balance without narrowing.
    double getGoldCarried() const { return mGold; }
    //! \brief Applies the production fractional purse charge.
    void addGoldCarried(double gold) { mGold += gold; }
    Tile* getPositionTile() const { return mTile; }
    const Ogre::Vector3& getPosition() const { return mPos; }
    void setAnimationState(const std::string& state, bool loop = true, const Ogre::Vector3& direction = Ogre::Vector3::ZERO, bool idle = true) {}
    void increaseUrge(double value);
    void increaseThirst(double value);
    void setThirst(double val);
    void setDrunk(double val);
    void setHangoverTurns(double turns);
    void addTavernMood(double points, double turns);
    void drinkTaken(DrinkKind kind);
    bool isStaggering() const;
    double getHangoverWorkFactor() const;
    void sleepStarted();
    void sleepEnded();
    void upkeepTavernState();
};
@@CREATURE_FUNCTIONS@@

//! \brief Supplies tavern tiles and production fractional keeper balances.
struct GameMap
{
    int sizeX, sizeY; std::vector<Tile> tiles; double treasury, seatGold; std::vector<Creature*> creatures;
    //! \brief Initializes the tavern map with fractional treasury and seat balances.
    GameMap(int x, int y) : sizeX(x), sizeY(y), treasury(0), seatGold(0) { for(int yy = 0; yy < y; ++yy) for(int xx = 0; xx < x; ++xx) tiles.push_back(Tile(xx, yy)); }
    Tile* getTile(int x, int y) { return ((x < 0) || (y < 0) || (x >= sizeX) || (y >= sizeY)) ? nullptr : &tiles[y * sizeX + x]; }
    //! \brief Withdraws the complete production amount from the treasury fixture.
    bool withdrawFromTreasuries(double gold, Seat* seat) { if(treasury < gold) return false; treasury -= gold; return true; }
    //! \brief Credits the complete production amount to the seat fixture.
    void addGoldToSeat(double gold, int seatId) { seatGold += gold; }
    const std::vector<Creature*>& getCreaturesBySeat(Seat* seat) const { return creatures; }
};

struct InnkeeperEntity { int drinks, cheers; InnkeeperEntity() : drinks(0), cheers(0) {} void onDrink() { ++drinks; } void onCheer() { ++cheers; } };

struct Room
{
    GameMap* mMap; Seat* mSeat; std::vector<Tile*> mCoveredTiles;
    Room(GameMap* map, Seat* seat) : mMap(map), mSeat(seat) {}
    GameMap* getGameMap() const { return mMap; }
    Seat* getSeat() const { return mSeat; }
};
@@ROOM_TYPES@@
@@ROOM_CONSTANTS@@
@@ROOM_HELPERS@@

enum class CosmeticTavernKind { beer = 0, water = 1, duelWon = 2, duelLost = 3, vomit = 4 };

class RoomTavern : public Room
{
public:
    RoomTavern(GameMap* map, Seat* seat) : Room(map, seat), mPayer(TavernPayer::keeper), mCounterTile(nullptr), mInnkeeper(nullptr), events(0), lastKind(-1) {}
    bool servesBeer() const;
    static void addDrinkDirt(Tile* tile);
    void sendTavernEvent(Creature& creature, int32_t kind, const Creature* opponent) { ++events; lastKind = kind; kinds.push_back(kind); }
    void playSoundAt(Tile* tile, const std::string& family) {}
    void showSpotState(Tile* tile, RoomTavernSpot& spot) {}
    bool fallNextToBench(RoomTavernSpot& spot) { return false; }
    std::vector<Tile*> getTableTiles() const { return mTestTables; }
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator findSpotOf(const Creature* creature);
    void setSpotDone(RoomTavernSpot& spot, int32_t turns);
    void setSpotState(RoomTavernSpot& spot, TavernGuestState state, int32_t turns);
    void upkeepSpots();
    void abortDisturbedGuests();
    void finishDrink(Tile* tile, RoomTavernSpot& spot);
    bool payForBeer(Creature& creature, bool& noCoin);
    bool isFreeSeat(const RoomTavernSeat& seat, bool twoPlaces) const;
    bool pickFreeSeat(const Creature& creature, RoomTavernSeat& seat) const;
    static bool isLargeGuest(const Creature& creature);
    void tryStartGame(const RoomTavernSeat& seat);
    void startGame(const RoomTavernSeat& seatA, const RoomTavernSeat& seatB);
    void playContestTurn(std::map<RoomTavernSeat, RoomTavernGame>::iterator it);
    void playDuelTurn(std::map<RoomTavernSeat, RoomTavernGame>::iterator it);
    void concludeGame(std::map<RoomTavernSeat, RoomTavernGame>::iterator it, Creature* winner, uint32_t underdogLevels);
    void abortGame(std::map<RoomTavernSeat, RoomTavernGame>::iterator it);
    void knockOut(RoomTavernSpot& spot);
    void cheerSpectators(const RoomTavernGame& game);
    static bool isGuestDisturbed(const Creature& creature);
    TavernPayer mPayer;
    Tile* mCounterTile;
    InnkeeperEntity* mInnkeeper;
    std::map<RoomTavernSeat, RoomTavernSpot> mSpots;
    std::map<RoomTavernSeat, RoomTavernGame> mGames;
    std::vector<Tile*> mTestTables;
    int events; int lastKind; std::vector<int> kinds;
};
@@ROOM_FUNCTIONS@@

// ---- Portal cooldown: the research factor of the Beer levels
struct SkillManager
{
    static double getResearchValue(const Seat* seat, SkillType type, double base, ResearchEffect effect)
    {
        static const double factors[] = { @@EFFECTS@@ };
        uint32_t level = seat->getSkillLevel(type);
        return (level == 0) ? base : base * factors[std::min<uint32_t>(level, 3) - 1];
    }
};
@@PORTAL_FUNCTION@@

// ---- A tavern with guests for the tests
struct Fixture
{
    GameMap map; Seat seat; Player player; CreatureDefinition thirsty; CreatureDefinition largeDefinition; RoomTavern room;
    InnkeeperEntity innkeeper;
    std::vector<Creature*> guests;
    Fixture() : map(12, 12), thirsty(true), largeDefinition(true), room(&map, &seat)
    {
        largeDefinition.bedDim = 2;
        seat.player = &player; room.mInnkeeper = &innkeeper;
        for(int i = 1; i < 10; ++i) room.mCoveredTiles.push_back(map.getTile(i, 5));
        room.mCounterTile = map.getTile(1, 5);
        room.mTestTables.push_back(map.getTile(2, 5)); room.mTestTables.push_back(map.getTile(6, 5));
    }
    ~Fixture() { for(unsigned i = 0; i < guests.size(); ++i) delete guests[i]; }
    // The seat that belongs to the tile (x, 5): the tiles 2 and 3 are the first two places of the first bench of the first
    // table, 4 and 5 the first two of its second bench; 6 to 9 the same at the second table
    RoomTavernSeat seatAt(int x)
    {
        const uint32_t step = static_cast<uint32_t>((x - 2) % 4);
        return RoomTavernSeat(map.getTile(2 + 4 * ((x - 2) / 4), 5), (step < 2) ? step : step + 2);
    }
    // Adds a guest on the given place of a table without changing where it stands
    Creature* guestOn(const std::string& name, Tile* table, uint32_t index, bool large)
    {
        Creature* c = new Creature(name, large ? &largeDefinition : &thirsty, &seat, 1);
        c->mTile = table; c->mPos = Ogre::Vector3(static_cast<float>(table->x), 5.0f, 0.0f);
        guests.push_back(c); map.creatures.push_back(c);
        RoomTavernSpot spot(c); spot.mState = TavernGuestState::drinking; spot.mTurnsLeft = 2; spot.mTwoPlaces = large;
        room.mSpots.insert(std::make_pair(RoomTavernSeat(table, index), spot));
        return c;
    }
    // Adds a guest standing at the tile (x, 5) on the seat of that tile, with the given level and state
    Creature* guest(const std::string& name, int x, uint32_t level, TavernGuestState state, int32_t turns)
    {
        Creature* c = new Creature(name, &thirsty, &seat, level);
        c->mTile = map.getTile(x, 5); c->mPos = Ogre::Vector3(static_cast<float>(x), 5.0f, 0.0f);
        guests.push_back(c); map.creatures.push_back(c);
        RoomTavernSpot spot(c); spot.mState = state; spot.mTurnsLeft = turns;
        room.mSpots.insert(std::make_pair(seatAt(x), spot));
        return c;
    }
    // The seat of a guest
    RoomTavernSeat seatOf(Creature* c) { return room.findSpotOf(c)->first; }
    // Starts a game of the given kind between two guests of one table
    std::map<RoomTavernSeat, RoomTavernGame>::iterator game(Creature* a, Creature* b, TavernGameKind kind, int32_t turns)
    {
        RoomTavernGame g; g.mKind = kind; g.mSeatA = seatOf(a); g.mSeatB = seatOf(b); g.mCreatureA = a; g.mCreatureB = b; g.mTurnsLeft = turns;
        room.findSpotOf(a)->second.mState = TavernGuestState::game; room.findSpotOf(b)->second.mState = TavernGuestState::game;
        room.mGames[g.mSeatA] = g; return room.mGames.find(g.mSeatA);
    }
    TavernGuestState stateOf(Creature* c) { return room.findSpotOf(c)->second.mState; }
};

// ---- Thirst, drunkenness, hangover
static void checkThirst()
{
    Seat seat; Player player; seat.player = &player; CreatureDefinition thirsty(true), dry(false);
    Creature c("C", &thirsty, &seat, 1);
    for(int i = 0; i < 800; ++i) c.increaseThirst(0.1);
    expectNear(c.mThirst, 80.0, "0.1 per turn reaches the seek value after 800 turns", 1e-6);
    expect(player.notices == 0, "no notice below 100");
    for(int i = 0; i < 300; ++i) c.increaseThirst(0.1);
    expectNear(c.mThirst, 100.0, "thirst is clamped at 100");
    expect(player.notices > 0, "the keeper is told at thirst 100");
    c.setThirst(250.0); expectNear(c.mThirst, 100.0, "setThirst clamps up"); c.setThirst(-3.0); expectNear(c.mThirst, 0.0, "setThirst clamps down");
    Seat rogue; rogue.rogue = true; Creature wild("W", &thirsty, &rogue, 1); wild.increaseThirst(50.0);
    expectNear(wild.mThirst, 0.0, "rogue creatures never get thirsty");
    Creature noHunger("Skeleton", &dry, &seat, 1); noHunger.increaseThirst(50.0); noHunger.setThirst(70.0);
    expectNear(noHunger.mThirst, 0.0, "a type without thirst never gets thirsty and a load cannot set it");
    Seat plain; Creature other("O", &thirsty, &plain, 1); other.setThirst(100.0); other.increaseThirst(1.0);
    expectNear(other.mThirst, 100.0, "no keeper, no notice, no crash");

    // A drink sets the thirst to 0 and raises the urge: beer 15 and water 5
    Creature d("D", &thirsty, &seat, 1); d.setThirst(95.0);
    d.drinkTaken(DrinkKind::water);
    expectNear(d.mThirst, 0.0, "water quenches"); expectNear(d.mUrge, 5.0, "water urge 5"); expectNear(d.mDrunk, 0.0, "water adds no drunkenness");
    d.setThirst(95.0); d.drinkTaken(DrinkKind::beer);
    expectNear(d.mThirst, 0.0, "beer quenches"); expectNear(d.mUrge, 20.0, "beer urge 15 on top"); expectNear(d.mDrunk, 25.0, "beer adds 25 drunkenness");
    for(int i = 0; i < 6; ++i) d.drinkTaken(DrinkKind::beer);
    expectNear(d.mDrunk, 100.0, "drunkenness is capped at 100");

    // Drunkenness falls by 0.5 per turn; stagger at 50; the vomit mark is reset below 75
    Creature s("S", &thirsty, &seat, 1); s.mDrunk = 49.5;
    expect(!s.isStaggering(), "49.5 does not stagger"); s.mDrunk = 50.0; expect(s.isStaggering(), "50 staggers"); s.mDrunk = 0.0; expect(!s.isStaggering(), "sober");
    s.mDrunk = 80.0; s.mVomited = true;
    for(int i = 0; i < 9; ++i) s.upkeepTavernState();
    expectNear(s.mDrunk, 75.5, "decay 0.5 per turn"); expect(s.mVomited, "still marked at 75.5");
    s.upkeepTavernState(); s.upkeepTavernState();
    expectNear(s.mDrunk, 74.5, "74.5"); expect(!s.mVomited, "the mark is reset below 75, so the next episode vomits again");
    s.mDrunk = 25.0; for(int i = 0; i < 50; ++i) s.upkeepTavernState();
    expectNear(s.mDrunk, 0.0, "25 drunkenness are gone after 50 turns");

    // Tavern mood: value and timer, a new drink refreshes both, 0 when the timer ends
    Creature m("M", &thirsty, &seat, 1); m.addTavernMood(15.0, 168.0);
    for(int i = 0; i < 167; ++i) m.upkeepTavernState();
    expectNear(m.mTavernMood, 15.0, "the mood holds for 167 turns");
    m.addTavernMood(15.0, 168.0);
    for(int i = 0; i < 167; ++i) m.upkeepTavernState();
    expectNear(m.mTavernMood, 15.0, "a new drink refreshes the timer");
    m.upkeepTavernState(); expectNear(m.mTavernMood, 0.0, "the mood is gone after 168 turns"); expectNear(m.mTavernMoodTurns, 0.0, "timer 0");

    // Hangover: only after a sleep that started above 50, 252 turns, half work, mood -10, not shortened
    Creature h("H", &thirsty, &seat, 1); h.mDrunk = 50.0; h.sleepStarted(); h.sleepEnded();
    expectNear(h.mHangoverTurns, 0.0, "exactly 50 does not give a hangover"); expectNear(h.getHangoverWorkFactor(), 1.0, "no hangover, full work");
    h.mDrunk = 50.5; h.sleepStarted(); h.sleepEnded();
    expectNear(h.mHangoverTurns, 252.0, "a hangover lasts 252 turns"); expectNear(h.mTavernMood, -66.6667, "hangover mood -66.6667");
    expectNear(h.mTavernMoodTurns, 252.0, "the mood lasts as long"); expectNear(h.getHangoverWorkFactor(), 0.5, "half work and experience");
    h.sleepEnded(); expectNear(h.mHangoverTurns, 252.0, "a second wake-up without drunk sleep changes nothing");
    h.mHangoverTurns = 300.0; h.mDrunk = 60.0; h.sleepStarted(); h.sleepEnded();
    expectNear(h.mHangoverTurns, 300.0, "sleeping again does not shorten the hangover");
    for(int i = 0; i < 300; ++i) h.upkeepTavernState();
    expectNear(h.mHangoverTurns, 0.0, "the hangover runs out one turn at a time");
    // The leisure cooldown after leaving a tavern counts down one turn at a time and stops at 0
    h.mTavernCooldownTurns = 600;
    for(int i = 0; i < 599; ++i) h.upkeepTavernState();
    expectNear(h.mTavernCooldownTurns, 1.0, "the leisure cooldown has one turn left after 599 turns");
    h.upkeepTavernState(); h.upkeepTavernState();
    expectNear(h.mTavernCooldownTurns, 0.0, "the leisure cooldown ends at 0 and does not go below");
}

// ---- Drinks, payment, the chain
//! \brief Tests the original drink rules and preserves fractional balances through both payment paths.
static void checkDrinks()
{
    // Without the research the tavern serves water: nothing is paid, no mood
    { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.map.treasury = 50; c->mThirst = 90.0;
      expect(!f.room.servesBeer(), "no beer without the research");
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.findSpotOf(c)->second);
      expect(f.map.treasury == 50 && c->mDrunk == 0.0 && c->mTavernMood == 0.0 && c->mThirst == 0.0, "water: free, no mood, thirst 0");
      expect(f.room.lastKind == 1, "a water event is sent"); expect(f.innkeeper.drinks == 1, "the innkeeper pours");
      expectNear(f.map.getTile(2, 5)->dirt, 0.29, "every drink dirties the tile", 1e-9); }
    // Beer paid by the keeper
    { Fixture f; f.seat.beerLevel = 1; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.map.treasury = 50;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.findSpotOf(c)->second);
      expect(f.map.treasury == 45 && c->mGold == 0, "the keeper pays 5 from the treasury");
      expectNear(c->mDrunk, 25.0, "beer: 25 drunkenness"); expectNear(c->mTavernMood, 100.0, "beer: mood +100"); expectNear(c->mTavernMoodTurns, 168.0, "beer: mood for 168 turns");
      expect(f.room.lastKind == 0, "a beer event is sent"); }
    // The keeper cannot pay: water, no malus
    { Fixture f; f.seat.beerLevel = 1; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.map.treasury = 4;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.findSpotOf(c)->second);
      expect(f.map.treasury == 4 && c->mDrunk == 0.0 && c->mTavernMood == 0.0, "an empty treasury gives water and no mood malus"); expect(f.room.lastKind == 1, "water event"); }
    // The creature pays from its purse; the gold goes to the treasury of the seat
    { Fixture f; f.seat.beerLevel = 1; f.room.mPayer = TavernPayer::creature; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); c->mGold = 12; f.map.treasury = 0;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.findSpotOf(c)->second);
      expect(c->mGold == 7 && f.map.seatGold == 5 && f.map.treasury == 0, "the creature pays 5 from its purse to the seat");
      expectNear(c->mTavernMood, 100.0, "beer mood"); expectNear(c->mDrunk, 25.0, "beer drunkenness"); }
    // Keep the original integer payment cases and preserve existing fractional balances as well.
    { Fixture f; Creature* c = f.guest("Fractional", 2, 1, TavernGuestState::drinking, 0); bool noCoin = true;
      f.map.treasury = 50.625; c->mGold = 12.375;
      expect(f.room.payForBeer(*c, noCoin) && !noCoin, "fractional treasury can pay the unchanged beer price");
      expect(f.map.treasury == 45.625 && c->mGold == 12.375, "keeper payment retains both gold fractions");
      f.room.mPayer = TavernPayer::creature; f.map.seatGold = 0.625;
      expect(f.room.payForBeer(*c, noCoin) && !noCoin, "fractional purse can pay the unchanged beer price");
      expect(c->mGold == 7.375 && f.map.seatGold == 5.625 && f.map.treasury == 45.625, "purse payment retains purse, seat and treasury fractions"); }
    // The creature cannot pay: water and mood -5 for 168 turns
    { Fixture f; f.seat.beerLevel = 1; f.room.mPayer = TavernPayer::creature; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); c->mGold = 4; f.map.treasury = 100;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.findSpotOf(c)->second);
      expect(c->mGold == 4 && f.map.seatGold == 0 && f.map.treasury == 100 && c->mDrunk == 0.0, "an empty purse gives water and costs nothing");
      expectNear(c->mTavernMood, -33.3333, "no coin: mood -33.3333"); expectNear(c->mTavernMoodTurns, 168.0, "no coin: for 168 turns"); }

    // The drink chain: 50, 25, 12.5 and 6.25 percent after the 1st to the 4th drink, never more than five
    const double thresholds[] = { 50.0, 25.0, 12.5, 6.25 };
    for(int n = 1; n <= 4; ++n)
    {
        { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); RoomTavernSpot& spot = f.room.findSpotOf(c)->second; spot.mDrinks = n - 1;
          Random::script({ thresholds[n - 1] - 0.01 }, {});
          f.room.finishDrink(c->mTile, spot);
          expect(spot.mState == TavernGuestState::drinking && spot.mTurnsLeft == 4, "drink " + std::to_string(n) + ": a roll just below " + std::to_string(thresholds[n - 1]) + " takes another drink for 4 turns"); }
        { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); RoomTavernSpot& spot = f.room.findSpotOf(c)->second; spot.mDrinks = n - 1;
          Random::script({ thresholds[n - 1] + 0.01 }, {});
          f.room.finishDrink(c->mTile, spot);
          expect(spot.mState == TavernGuestState::done, "drink " + std::to_string(n) + ": a roll just above " + std::to_string(thresholds[n - 1]) + " ends the visit"); }
    }
    { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); RoomTavernSpot& spot = f.room.findSpotOf(c)->second; spot.mDrinks = 4;
      Random::script({ 0.0 }, {});
      f.room.finishDrink(c->mTile, spot);
      expect(spot.mState == TavernGuestState::done && spot.mDrinks == 5, "the fifth drink is the last whatever the roll says"); }
    { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); c->mThirst = 0.0; RoomTavernSpot& spot = f.room.findSpotOf(c)->second;
      Random::script({ 10.0 }, {});
      f.room.finishDrink(c->mTile, spot);
      expect(spot.mState == TavernGuestState::drinking, "a creature without thirst still drinks when the roll says so"); }
}

// ---- Games
static void checkGameStart()
{
    // 50 percent chance after the last drink, a guest of the same table and keeper that is done and waits
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.guest("B", 3, 1, TavernGuestState::done, 2);
      RoomTavernSpot& spot = f.room.findSpotOf(a)->second; spot.mDrinks = 4;
      Random::script({ 49.9 }, { 0 }); f.room.finishDrink(a->mTile, spot);
      expect(f.room.mGames.size() == 1, "a roll below 50 starts a game with the guest of the same table");
      expect(f.stateOf(a) == TavernGuestState::game, "both guests are in the game"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.guest("B", 3, 1, TavernGuestState::done, 2);
      RoomTavernSpot& spot = f.room.findSpotOf(a)->second; spot.mDrinks = 4;
      Random::script({ 50.0 }, { 0 }); f.room.finishDrink(a->mTile, spot);
      expect(f.room.mGames.empty() && !spot.mWantsGame, "a roll of 50 starts no game and the guest wants none"); }
    // Without a partner the guest waits one turn for one and starts the game when one is done
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::drinking, 0);
      RoomTavernSpot& spot = f.room.findSpotOf(a)->second; spot.mDrinks = 4;
      Random::script({ 1.0 }, { 0 }); f.room.finishDrink(a->mTile, spot);
      expect(f.room.mGames.empty() && spot.mWantsGame && spot.mState == TavernGuestState::done && spot.mTurnsLeft == 1, "a guest that wants a game waits for one turn");
      f.guest("B", 3, 1, TavernGuestState::done, 2);
      Random::script({}, { 0 }); f.room.tryStartGame(f.seatOf(a));
      expect(f.room.mGames.size() == 1 && !spot.mWantsGame, "the waiting guest starts the game when a guest of its table is done"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2);
      f.room.findSpotOf(a)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(f.seatOf(a));
      expect(f.room.mGames.empty(), "no partner, no game"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); f.guest("B", 6, 1, TavernGuestState::done, 2);
      f.room.findSpotOf(a)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(f.seatOf(a));
      expect(f.room.mGames.empty(), "a guest at another table is no partner, wherever it is"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 0); (void)b;
      f.room.findSpotOf(a)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(f.seatOf(a));
      expect(f.room.mGames.empty(), "a guest whose waiting turns ran out is gone"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 2); Seat other; b->mSeat = &other;
      f.room.findSpotOf(a)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(f.seatOf(a));
      expect(f.room.mGames.empty(), "a guest of another seat is no partner"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); f.guest("B", 3, 1, TavernGuestState::drinking, 2);
      f.room.findSpotOf(a)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(f.seatOf(a));
      expect(f.room.mGames.empty(), "a guest that still drinks is no partner"); }

    // The draw: arm wrestling and dice without beer, the slap duel joins with beer
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 2);
      Random::script({}, { 1 }); f.room.startGame(f.seatOf(a), f.seatOf(b));
      expect(Random::lastUintMax == 1, "without beer two games are drawn");
      expect(f.room.mGames.begin()->second.mKind == TavernGameKind::dice && f.room.mGames.begin()->second.mTurnsLeft == 8, "dice take 8 turns"); }
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 2);
      Random::script({}, { 2 }); f.room.startGame(f.seatOf(a), f.seatOf(b));
      expect(Random::lastUintMax == 2, "with beer three games are drawn");
      expect(f.room.mGames.begin()->second.mKind == TavernGameKind::slapDuel && f.room.mGames.begin()->second.mTurnsLeft == 32, "the duel ends after 4 x 8 turns at the latest"); }

    // A guest on the opposite bench comes before the one next to it
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* side = f.guest("Side", 3, 1, TavernGuestState::done, 2); Creature* across = f.guest("Across", 4, 1, TavernGuestState::done, 2);
      (void)side; f.room.findSpotOf(a)->second.mWantsGame = true; Random::script({}, { 0, 0 }); f.room.tryStartGame(f.seatOf(a));
      expect(f.room.mGames.size() == 1 && f.room.mGames.begin()->second.mCreatureB == across, "the partner comes from the opposite bench first"); }
    // A game between two tables is refused
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 6, 1, TavernGuestState::done, 2);
      Random::script({}, { 0 }); f.room.startGame(f.seatOf(a), f.seatOf(b));
      expect(f.room.mGames.empty(), "games take place only at one table"); }
}

// ---- Seats
static void checkSeats()
{
    // A new guest takes a free seat at a table with a guest, not at the nearer empty table
    { Fixture f; f.guest("G", 8, 1, TavernGuestState::drinking, 2); Creature* n = f.guest("N", 3, 1, TavernGuestState::arriving, 0);
      f.room.mSpots.erase(f.seatOf(n)); RoomTavernSeat picked;
      expect(f.room.pickFreeSeat(*n, picked) && picked.mTable == f.map.getTile(6, 5) && picked.mIndex == 0, "a new guest joins the table with a guest"); }
    // Without guests the nearest table is taken
    { Fixture f; Creature* n = f.guest("N", 7, 1, TavernGuestState::arriving, 0);
      f.room.mSpots.erase(f.seatOf(n)); RoomTavernSeat picked;
      expect(f.room.pickFreeSeat(*n, picked) && picked.mTable == f.map.getTile(6, 5), "without guests the nearest table is taken"); }
    // Eight places per table (four on each bench), then the next table, then nobody: no entry without a free seat
    { Fixture f; Tile* tables[] = { f.map.getTile(2, 5), f.map.getTile(6, 5) };
      for(int t = 0; t < 2; ++t) for(uint32_t i = 0; i < 8; ++i) if(!(t == 1 && i == 7)) f.guestOn("G" + std::to_string(t * 8 + i), tables[t], i, false);
      Creature late("Late", &f.thirsty, &f.seat, 1); late.mTile = f.map.getTile(2, 5); RoomTavernSeat picked;
      expect(f.room.pickFreeSeat(late, picked) && picked.mTable == tables[1] && picked.mIndex == 7, "the last free place of eight is found");
      f.guestOn("G15", tables[1], 7, false);
      expect(f.room.mSpots.size() == 16, "two tables hold sixteen guests");
      expect(!f.room.pickFreeSeat(late, picked), "a creature without a free seat finds none"); }
    // Each bench has four places; a taken place is not free, the others of the bench are
    { Fixture f; Tile* table = f.map.getTile(2, 5); f.guestOn("G", table, 0, false);
      expect(!f.room.isFreeSeat(RoomTavernSeat(table, 0), false), "a taken place is not free");
      expect(f.room.isFreeSeat(RoomTavernSeat(table, 1), false) && f.room.isFreeSeat(RoomTavernSeat(table, 2), false) &&
             f.room.isFreeSeat(RoomTavernSeat(table, 3), false), "three more guests fit on the bench");
      expect(!f.room.isFreeSeat(RoomTavernSeat(table, 0), true), "a large guest does not fit on a pair with another guest");
      expect(!f.room.isFreeSeat(RoomTavernSeat(table, 1), true), "a large guest starts on an even place");
      expect(f.room.isFreeSeat(RoomTavernSeat(table, 2), true), "the other half of the bench is free for a large guest");
      expect(f.room.isFreeSeat(RoomTavernSeat(table, 4), true) && f.room.isFreeSeat(RoomTavernSeat(table, 6), true), "the other bench takes two large guests");
      expect(!f.room.isFreeSeat(RoomTavernSeat(table, 8), false), "a table has eight places");
      expect(!f.room.isFreeSeat(RoomTavernSeat(nullptr, 0), false), "no table, no seat"); }
    // A large creature takes two places, half of a bench, so a table holds four of them; bed size 2x2 makes a creature large
    { Fixture f; Creature troll("Troll", &f.largeDefinition, &f.seat, 1); troll.mTile = f.map.getTile(2, 5); Creature goblin("Goblin", &f.thirsty, &f.seat, 1);
      expect(RoomTavern::isLargeGuest(troll) && !RoomTavern::isLargeGuest(goblin), "a bed of two by two tiles makes a creature large");
      RoomTavernSeat picked; expect(f.room.pickFreeSeat(troll, picked) && picked.mIndex == 0, "a large creature takes the first pair of a bench");
      f.guestOn("Troll1", picked.mTable, picked.mIndex, true);
      expect(!f.room.isFreeSeat(RoomTavernSeat(picked.mTable, 1), false), "nobody sits on the second place of a large creature");
      expect(f.room.isFreeSeat(RoomTavernSeat(picked.mTable, 2), false), "a normal guest sits next to a large creature");
      for(uint32_t expected = 2; expected <= 6; expected += 2)
      { RoomTavernSeat next; expect(f.room.pickFreeSeat(troll, next) && next.mTable == picked.mTable && next.mIndex == expected, "the next large creature takes the next pair of the table");
        f.guestOn("Troll" + std::to_string(expected), next.mTable, next.mIndex, true); }
      RoomTavernSeat fifth; expect(f.room.pickFreeSeat(troll, fifth) && fifth.mTable == f.map.getTile(6, 5), "a table holds four large guests, the fifth goes to the next table"); }
    // Large and normal guests share a bench: a large one and two normal ones fill it
    { Fixture f; Tile* table = f.map.getTile(2, 5); f.guestOn("Troll", table, 0, true); f.guestOn("A", table, 2, false); f.guestOn("B", table, 3, false);
      Creature goblin("Goblin", &f.thirsty, &f.seat, 1); goblin.mTile = table; RoomTavernSeat picked;
      expect(f.room.pickFreeSeat(goblin, picked) && picked.mTable == table && picked.mIndex == 4, "the full bench sends the next guest to the other bench"); }
    // One guest on every pair: a large creature finds no two free places next to each other, a small one still finds a seat
    { Fixture f; Tile* tables[] = { f.map.getTile(2, 5), f.map.getTile(6, 5) };
      for(int t = 0; t < 2; ++t) for(uint32_t i = 0; i < 8; i += 2) f.guestOn("G" + std::to_string(t * 8 + i), tables[t], i, false);
      Creature troll("Troll", &f.largeDefinition, &f.seat, 1); RoomTavernSeat picked;
      expect(!f.room.pickFreeSeat(troll, picked), "a large creature does not enter without two free places");
      Creature goblin("Goblin", &f.thirsty, &f.seat, 1); expect(f.room.pickFreeSeat(goblin, picked), "a small one still finds a seat"); }
}

static void checkContest()
{
    // Level 12 against level 10: the weaker wins with 50 - 2.5 x 2 = 45 percent
    { Fixture f; Creature* a = f.guest("A", 2, 12, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::armWrestling, 2);
      Random::script({ 44.9 }, {});
      f.room.playContestTurn(g); expect(f.room.mGames.size() == 1, "the game runs while turns are left");
      f.room.playContestTurn(f.room.mGames.begin());
      expect(f.room.mGames.empty() && b->mExp == 5.72 && a->mExp == 0.0, "44.9: the weaker wins and gets double experience");
      expectNear(b->mTavernMood, 199.9999, "underdog mood 133.3333 + 33.3333 x 2"); expectNear(a->mTavernMood, 0.0, "the loser gets nothing"); expect(f.innkeeper.cheers == 1, "the innkeeper cheers"); }
    { Fixture f; Creature* a = f.guest("A", 2, 12, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 45.1 }, {});
      f.room.playContestTurn(g);
      expect(f.room.mGames.empty() && a->mExp == 2.86 && b->mExp == 0.0, "45.1: the stronger wins with normal experience");
      expectNear(a->mTavernMood, 133.3333, "winner mood 133.3333"); expectNear(a->mTavernMoodTurns, 168.0, "winner mood for 168 turns"); }
    // Equal levels: 50 / 50 and normal values for the winner
    { Fixture f; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 49.9 }, {}); f.room.playContestTurn(g);
      expect(a->mExp == 2.86 && a->mTavernMood == 133.3333 && b->mExp == 0.0, "equal levels: 49.9 wins for the first guest with normal values"); }
    // The floor: 20 levels of difference would give 0 percent, the weaker still wins with 5 percent
    { Fixture f; Creature* a = f.guest("A", 2, 25, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 5, TavernGuestState::game, 0);
      std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 4.9 }, {}); f.room.playContestTurn(g);
      expect(b->mExp == 5.72, "20 levels: 4.9 still lets the weaker win (floor 5 percent)"); expectNear(b->mTavernMood, 333.3333, "underdog mood is capped at 333.3333"); }
    { Fixture f; Creature* a = f.guest("A", 2, 25, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 5, TavernGuestState::game, 0);
      std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 5.1 }, {}); f.room.playContestTurn(g);
      expect(a->mExp == 2.86 && b->mExp == 0.0, "20 levels: 5.1 is a win of the stronger"); }
    // Spectators: own creatures within 2 tiles (Chebyshev) of where a player sits, not the players, not a possessed one
    { Fixture f; Creature* a = f.guest("A", 4, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 5, 10, TavernGuestState::game, 0);
      Creature* near = f.guest("Near", 7, 1, TavernGuestState::done, 0); Creature* far = f.guest("Far", 8, 1, TavernGuestState::done, 0);
      Creature* up = f.guest("Up", 4, 1, TavernGuestState::done, 0); up->mTile = f.map.getTile(4, 7);
      Creature* possessed = f.guest("Possessed", 3, 1, TavernGuestState::done, 0); possessed->mPossessed = true;
      Creature* off = f.guest("Off", 3, 1, TavernGuestState::done, 0); off->mOnMap = false;
      std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 10.0 }, {}); f.room.playContestTurn(g);
      expectNear(near->mTavernMood, 66.6667, "a spectator 2 tiles from a player gets +66.6667"); expectNear(near->mTavernMoodTurns, 168.0, "spectator mood for 168 turns");
      expectNear(far->mTavernMood, 0.0, "3 tiles away is no spectator"); expectNear(up->mTavernMood, 66.6667, "2 tiles away on the other axis is a spectator");
      expectNear(possessed->mTavernMood, 0.0, "a possessed creature does not cheer"); expectNear(off->mTavernMood, 0.0, "a creature off the map does not cheer"); }
}

static void checkDuel()
{
    // The critical chance is 10 percent at equal level and 0.25 points per level of difference
    struct Case { uint32_t slapper, target; double roll; bool crit; const char* what; };
    const Case cases[] = {
        { 10, 10, 9.99, true, "equal level: 9.99 is critical" }, { 10, 10, 10.01, false, "equal level: 10.01 is not" },
        { 11, 10, 10.24, true, "one level above: 10.24 is critical" }, { 11, 10, 10.26, false, "one level above: 10.26 is not" },
        { 9, 10, 9.74, true, "one level below: 9.74 is critical" }, { 9, 10, 9.76, false, "one level below: 9.76 is not" },
    };
    for(unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
    {
        Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, cases[i].slapper, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, cases[i].target, TavernGuestState::game, 0);
        std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 32);
        Random::script({ cases[i].roll }, {}); f.room.playDuelTurn(g);
        if(cases[i].crit)
        {
            expect(f.room.mGames.empty() && b->mHp == 100.0, std::string(cases[i].what) + ": the duel is decided, no damage");
            expect(f.stateOf(b) == TavernGuestState::ko && f.room.findSpotOf(b)->second.mTurnsLeft == 42 && f.room.findSpotOf(b)->second.mSleepAfter, "a critical slap knocks the loser out for 42 turns and sends it to bed");
        }
        else expect(f.room.mGames.size() == 1 && b->mHp == 90.0, std::string(cases[i].what) + ": a normal slap takes 10 HP");
    }

    // A normal hit: 10 HP, the loser is the one who falls below 30, HP never below 1
    struct HpCase { double hp; bool decided; double after; const char* what; };
    const HpCase hpCases[] = { { 100.0, false, 90.0, "100 HP -> 90" }, { 45.0, false, 35.0, "45 HP -> 35" }, { 40.0, false, 30.0, "40 HP -> 30 is not below 30" },
                               { 39.9, true, 29.9, "39.9 HP -> 29.9 is below 30" }, { 31.0, true, 21.0, "31 HP -> 21" }, { 5.0, true, 1.0, "5 HP -> 1, never below 1" },
                               { 1.0, true, 1.0, "1 HP stays 1" } };
    for(unsigned i = 0; i < sizeof(hpCases) / sizeof(hpCases[0]); ++i)
    {
        Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0); b->mHp = hpCases[i].hp;
        std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 32);
        Random::script({ 50.0 }, {}); f.room.playDuelTurn(g);
        expectNear(b->mHp, hpCases[i].after, hpCases[i].what, 1e-9);
        expect(f.room.mGames.empty() == hpCases[i].decided, std::string(hpCases[i].what) + ": decided = " + (hpCases[i].decided ? "yes" : "no"));
        if(hpCases[i].decided)
        {
            expect(f.stateOf(b) == TavernGuestState::ko && f.stateOf(a) == TavernGuestState::done, "the loser goes down, the winner is done");
            expectNear(a->mTavernMood, 133.3333, "winner mood 133.3333"); expect(a->mExp == 2.86, "winner experience 2.86"); expectNear(b->mTavernMood, -66.6667, "loser mood -66.6667 for the duel");
            expect(f.room.kinds.size() == 2 && f.room.kinds[0] == 2 && f.room.kinds[1] == 3, "winner and loser are told to the clients");
        }
    }
    // A miss passes the turn and does no damage
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0); a->mHit = true; b->mHit = false;
      std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 32);
      b->mHit = false;   // the target rolls the hit: a miss
      Random::script({}, {}); f.room.playDuelTurn(g);
      expect(g->second.mTurnIsA == false && b->mHp == 100.0 && g->second.mTurnsLeft == 31, "a miss passes the turn without damage"); }
    // After 4 x 8 turns without a decision the one with more HP left wins; a tie is decided by chance
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0); a->mHp = 80.0; b->mHp = 60.0;
      b->mHit = false; std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 1);
      Random::script({}, {}); f.room.playDuelTurn(g);
      expect(f.room.mGames.empty() && a->mExp == 2.86 && f.stateOf(b) == TavernGuestState::ko, "no decision: the one with more HP wins and the other goes down"); }
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      b->mHit = false; std::map<RoomTavernSeat, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 1);
      Random::script({}, { 1 }); f.room.playDuelTurn(g);
      expect(f.room.mGames.empty() && b->mExp == 2.86, "a tie is decided by chance"); }
}

static void checkKnockOutAndAbort()
{
    // 42 turns lying, then 2 turns getting up, then done (the room sends the loser to bed in useRoom)
    { Fixture f; f.seat.beerLevel = 1; Creature* b = f.guest("B", 3, 10, TavernGuestState::done, 0);
      f.room.knockOut(f.room.findSpotOf(b)->second);
      for(int i = 0; i < 41; ++i) f.room.upkeepSpots();
      expect(f.stateOf(b) == TavernGuestState::ko, "still lying after 41 turns");
      f.room.upkeepSpots(); expect(f.stateOf(b) == TavernGuestState::getUp && f.room.findSpotOf(b)->second.mTurnsLeft == 2, "after 42 turns the loser gets up for 2 turns");
      f.room.upkeepSpots(); f.room.upkeepSpots(); expect(f.stateOf(b) == TavernGuestState::done, "then it is done"); }
    // A fight, a flight, a knock-out or a pick-up ends a game without effects
    for(int reason = 0; reason < 4; ++reason)
    {
        Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
        Creature* spectator = f.guest("S", 4, 1, TavernGuestState::done, 0);
        f.game(a, b, TavernGameKind::slapDuel, 20);
        if(reason == 0) b->mFighting = true; else if(reason == 1) a->mFleeing = true; else if(reason == 2) b->mKo = true; else a->mDragged = true;
        f.room.abortDisturbedGuests();
        expect(f.room.mGames.empty(), "reason " + std::to_string(reason) + ": the game ends");
        expect(a->mExp == 0.0 && b->mExp == 0.0 && a->mTavernMood == 0.0 && b->mTavernMood == 0.0 && spectator->mTavernMood == 0.0 && f.innkeeper.cheers == 0 && f.room.events == 0,
               "reason " + std::to_string(reason) + ": no effects (no experience, no mood, no cheer, no event)");
        expect(f.stateOf(a) == TavernGuestState::done && f.stateOf(b) == TavernGuestState::done, "both guests are done");
    }
    // A fight nearby ends the lying at once, without the walk to bed
    { Fixture f; Creature* b = f.guest("B", 3, 10, TavernGuestState::ko, 30); f.room.findSpotOf(b)->second.mSleepAfter = true; b->mFighting = true;
      f.room.abortDisturbedGuests();
      expect(f.stateOf(b) == TavernGuestState::done && !f.room.findSpotOf(b)->second.mSleepAfter, "a fight ends the lying and the way to bed"); }
}

// ---- Mood of thirst and the portal cooldown
struct CreatureS { double thirst; double getThirst() const { return thirst; } double getHunger() const { return thirst; } };
@@MOOD_FUNCTIONS@@

static void checkMoodAndPortal()
{
    // The thirst mood is the hunger mood with the same numbers: nothing below the start, then (value - start) x modifier
    struct M { int start; int modifier; };
    const M moods[] = { { 80, -60 }, { 80, -40 }, { 80, -20 } };
    for(unsigned i = 0; i < 3; ++i)
        for(int v = 0; v <= 100; v += 5)
        {
            CreatureS c; c.thirst = v;
            expect(thirstMood(c, moods[i].start, moods[i].modifier) == hungerMood(c, moods[i].start, moods[i].modifier), "thirst mood equals hunger mood");
        }
    CreatureS full; full.thirst = 100.0;
    expect(thirstMood(full, 80, -60) == -1200, "thirst 100 with 80 / -60");
    CreatureS below; below.thirst = 79.9;
    expect(thirstMood(below, 80, -60) == 0, "no malus below the start");

    // Portal cooldown: both bounds times the factor of the Beer level
    Seat seat; const double factors[] = { 1.0, 0.9, 0.8 };
    for(uint32_t level = 0; level <= 3; ++level)
    {
        seat.beerLevel = level;
        const double factor = (level == 0) ? 1.0 : factors[level - 1];
        expect(std::fabs(getResearchedCooldown(&seat, "PortalCooldownSpawnMin") - 230.15307692307692 * factor) < 1e-9, "portal min cooldown at Beer level " + std::to_string(level));
        expect(std::fabs(getResearchedCooldown(&seat, "PortalCooldownSpawnMax") - ConfigManager::getSingleton().values["RoomPortalCooldownSpawnMax"] * factor) < 1e-9, "portal max cooldown at Beer level " + std::to_string(level));
    }
}

int main()
{
    loadConfig();
    checkThirst();
    checkDrinks();
    checkGameStart();
    checkSeats();
    checkContest();
    checkDuel();
    checkKnockOutAndAbort();
    checkMoodAndPortal();
    if(failures == 0) std::cout << "tavern rules ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

# The pieces of the sources
drink_kind = room_h = read('source/entities/Creature.h')
drink_kind = drink_kind[drink_kind.index('enum class DrinkKind'):]
drink_kind = drink_kind[:drink_kind.index('};') + 2]
creature_functions = '\n'.join(extract(creature_cpp, h) for h in [
    'void Creature::increaseUrge(', 'void Creature::increaseThirst(', 'void Creature::setThirst(', 'void Creature::setDrunk(',
    'void Creature::setHangoverTurns(', 'void Creature::addTavernMood(', 'void Creature::drinkTaken(', 'bool Creature::isStaggering(',
    'double Creature::getHangoverWorkFactor(', 'void Creature::sleepStarted(', 'void Creature::sleepEnded(', 'void Creature::upkeepTavernState('])
tavern_h = read('source/rooms/RoomTavern.h')
types_start = tavern_h.index('//! \\brief Who pays for the beer a tavern serves.')
types_end = tavern_h.index('//! \\brief A room where creatures quench their thirst.')
room_types = tavern_h[types_start:types_end]
constants = '\n'.join(find_line(room_cpp, r'^const (?:int32_t|uint32_t|double) ' + name + r' = [^;]+;$') for name in (
    'GET_UP_TURNS', 'DONE_WAIT_TURNS', 'PERCENT_SCALE', 'DIRECTION_EPSILON', 'NB_GAMES_WITHOUT_BEER', 'NB_GAMES_WITH_BEER'))
constants += '\n' + '\n'.join(find_line(room_cpp, r'^const std::string ' + name + r' = "[^"]+";$') for name in ('SOUND_POUR', 'SOUND_SLAP', 'SOUND_CHEER'))
helpers = '\n'.join(extract(room_cpp, h) for h in ['double getTavernValue(', 'Ogre::Vector3 directionTo('])
room_functions = '\n'.join(extract(room_cpp, h) for h in [
    'bool RoomTavern::servesBeer(', 'bool RoomTavern::isFreeSeat(', 'bool RoomTavern::isLargeGuest(', 'bool RoomTavern::pickFreeSeat(', 'void RoomTavern::addDrinkDirt(', 'std::map<RoomTavernSeat, RoomTavernSpot>::iterator RoomTavern::findSpotOf(',
    'void RoomTavern::setSpotState(', 'void RoomTavern::setSpotDone(', 'bool RoomTavern::isGuestDisturbed(', 'void RoomTavern::upkeepSpots(',
    'void RoomTavern::abortDisturbedGuests(', 'bool RoomTavern::payForBeer(', 'void RoomTavern::finishDrink(', 'void RoomTavern::tryStartGame(',
    'void RoomTavern::startGame(', 'void RoomTavern::playContestTurn(', 'void RoomTavern::playDuelTurn(', 'void RoomTavern::cheerSpectators(',
    'void RoomTavern::concludeGame(', 'void RoomTavern::abortGame(', 'void RoomTavern::knockOut('])
portal_function = extract(portal_cpp, 'static double getResearchedCooldown(')


# The mood function bodies, taken from the mood classes and renamed to free functions on the small stub
def mood_function(text, name, free_name):
    compute = extract(text, 'double CreatureMood' + name + '::computeMood(')
    body = compute[compute.index('{'):]
    getter = 'creature.get' + name + '()'
    assert getter in body, name
    start_name = 'mStart' + name
    return ('static int32_t ' + free_name + '(const CreatureS& creature, int32_t ' + start_name + ', int32_t mMoodModifier)\n' + body)


mood_functions = mood_function(mood_thirst_cpp, 'Thirst', 'thirstMood') + '\n' + mood_function(mood_hunger_cpp, 'Hunger', 'hungerMood')

replacements = {
    '@@CONFIG@@': config_table,
    '@@DRINKKIND@@': drink_kind,
    '@@CREATURE_FUNCTIONS@@': creature_functions,
    '@@ROOM_TYPES@@': 'struct Creature; struct Tile;\n' + room_types,
    '@@ROOM_CONSTANTS@@': constants,
    '@@ROOM_HELPERS@@': helpers,
    '@@ROOM_FUNCTIONS@@': room_functions,
    '@@EFFECTS@@': effect_table,
    '@@PORTAL_FUNCTION@@': portal_function,
    '@@MOOD_FUNCTIONS@@': mood_functions,
}
for token, text in replacements.items():
    assert token in probe, token
    probe = probe.replace(token, text)

with tempfile.TemporaryDirectory(prefix='odp-tavern-rules-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('tavern rules ok')
