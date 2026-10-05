"""Workers take over enemy rooms only when nobody guards them, and the taker can be charged.

Pure source wiring checks (no compiler, no game): server authority, configuration with defaults,
the guard and price rules in Room, their use in Tile (both the search check and the dance), the
client reactions. The probe of the two pure rules in RoomClaim.h is compiled and run only with
--probe (needs the MSVC compiler on the path)."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]


def read(path):
    return (root / path).read_text(encoding='utf-8')


def function_body(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end]


rooms_cfg = read('config/rooms.cfg')
reactions_cfg = read('config/creatureReactions.cfg')
room = read('source/rooms/Room.cpp')
room_h = read('source/rooms/Room.h')
claim_h = read('source/rooms/RoomClaim.h')
tile = read('source/entities/Tile.cpp')
worker = read('source/render/WorkerReactions.cpp')

# Configuration: documented, set, read with a default; the defaults keep the old behaviour except the guard
defaults = {'RoomTakeoverGuardRadius': '5', 'RoomTakeoverCostPercent': '0'}
for key, value in defaults.items():
    assert re.search(r'^\s+' + key + r'\s+' + value + r'\s*$', rooms_cfg, re.M), key
    assert re.search(r'^\s+# ' + key + r'\s', rooms_cfg, re.M), key + ' is not documented'
    assert '"' + key + '", ' + value + '.0)' in room, key + ' needs the same default in the source'

# Server decides; rooms of nobody, the client and the heart are not touched by the new rules
blocked = function_body(room, 'bool Room::isTakeoverBlocked(')
for needle in ('isServerGameMap()', 'isRogueSeat()', 'RoomTakeoverGuardRadius', 'isWorker()', 'isKo()', 'isInContainment()', 'isAlliedSeat(getSeat())',
               'RoomClaim::isGuardClose(', 'getTakeoverPrice()', 'getGold() < price'):
    assert needle in blocked, needle
assert 'dungeonTemple' not in blocked, 'the heart exception stays in RoomClaim::isClaimableBy'
# Every kind of room can be taken over: portals and bridges are not excluded, the switches are gone
assert 'RoomType::portal' not in blocked and 'RoomType::bridge' not in blocked, 'no room type is excluded'
for source_text in (rooms_cfg, room, room_h, claim_h, tile):
    assert 'TakeoverExclude' not in source_text, 'the takeover exclude switches no longer exist'
price = function_body(room, 'int32_t Room::getTakeoverPrice() const')
assert 'RoomClaim::takeoverPrice(' in price and 'RoomManager::costPerTile(' in price and 'isRogueSeat()' in price
assert 'RoomTakeoverCostPercent' in price

# Use: the search check and the dance both ask, the price is paid after the change of owner
ground = function_body(tile, 'bool Tile::isGroundClaimable(')
assert 'isTakeoverBlocked(seat, this)' in ground
dance = function_body(tile, 'void Tile::claimForSeat(')
assert dance.index('isTakeoverBlocked(seat, this)') < dance.index('->claimForSeat(seat, this, nDanceRate)')
assert dance.index('->claimForSeat(seat, this, nDanceRate)') < dance.index('withdrawFromTreasuries(takeoverPrice, seat)')
assert 'getSeat() != ownerBefore' in dance
# Level scripts and the heart reward call Room::claimForSeat directly and stay free and unguarded
assert 'isTakeoverBlocked' not in function_body(room, 'void Room::claimForSeat(')

# The dungeon heart can only be destroyed: every path that changes the owner of a room or of a tile
# of a room leaves it out
heart = 'RoomType::dungeonTemple'
claim_room = function_body(room, 'void Room::claimForSeat(')
assert heart in claim_room and claim_room.index(heart) < claim_room.index('mClaimHealth -='), 'Room::claimForSeat'
change = function_body(room, 'void Room::changeOwner(')
assert heart in change and change.index(heart) < change.index('handTilesOverToSeat('), 'Room::changeOwner'
hand = function_body(room, 'Room* Room::handTilesOverToSeat(')
assert heart in hand and hand.index(heart) < hand.index('RoomManager::createRoom('), 'Room::handTilesOverToSeat'
assert 'return nullptr' in hand[:hand.index('RoomManager::createRoom(')]
assert 'handTileOverToSeat' not in room and 'handTileOverToSeat' not in room_h, 'no square by square hand over is left (bridges go through changeOwner like every room)'
assert heart in function_body(tile, 'void Tile::claimForSeat(') and     function_body(tile, 'void Tile::claimForSeat(').index(heart) < function_body(tile, 'void Tile::claimForSeat(').index('isClaimable(seat)')
tile_claim = function_body(tile, 'void Tile::claimTile(')
assert heart in tile_claim and tile_claim.index(heart) < tile_claim.index('setSeat(seat)') and 'isServerGameMap()' in tile_claim
assert heart in function_body(room, 'bool Room::isClaimable(')
script = read('source/gamemap/LevelScriptRunner.cpp')
script_change = function_body(script, 'void changeRoomOwner(')
assert heart in script_change and script_change.index(heart) < script_change.index('->claimForSeat(')
reward_source = read('source/rooms/RoomDungeonTemple.cpp')
assert 'candidate->getType() == ' + heart in reward_source, 'the heart reward skips the loser heart'
assert 'tile->getCoveringBuilding() != nullptr)' in reward_source, 'the reward claims only tiles without a building directly'
assert 'isTakeoverBlocked' in room_h and 'getTakeoverPrice' in room_h

# The two pure rules
assert 'inline bool isGuardClose(' in claim_h and 'inline int32_t takeoverPrice(' in claim_h

# The room is taken over at once: one pool of tiles x duration of one tile, lowered by every dancer on any tile
assert 'inline double takeoverSeconds(double secondsPerTile, uint32_t numTiles)' in claim_h


def inline_body(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n    }\n', start)]


assert 'secondsPerTile * static_cast<double>(numTiles)' in inline_body(claim_h, 'inline double takeoverSeconds(')
for rule in ('inline double healthLostPerDance(', 'inline double healthRepairedPerDance('):
    assert 'takeoverSeconds(secondsPerTile, numTiles)' in inline_body(claim_h, rule), rule + ' uses the pool size'
# The pool is saved for every kind of room (first tile line, optional, only when worn down); the portal and the
# bridge keep their own old number as well
assert 'RoomClaim::writeClaimPool(os, mClaimHealth)' in function_body(room, 'void Room::exportTileDataToStream(')
assert 'mClaimHealth = RoomClaim::readClaimPool(is, mClaimHealth)' in function_body(room, 'bool Room::importTileDataFromStream(')
assert 'inline void writeClaimPool(' in claim_h and 'inline double readClaimPool(' in claim_h
assert 'Saved with the first tile' in room_h
# One duration value in the config (no second key with the same meaning), documented with the pool formula
assert len(re.findall(r'^\s+RoomConvertSecondsPerTile\s', rooms_cfg, re.M)) == 1, 'one set value'
assert len(re.findall(r'^\s+# RoomConvertSecondsPerTile\s', rooms_cfg, re.M)) == 1, 'one documented value'
assert not re.search(r'RoomTakeover(Seconds|Turns)PerTile', rooms_cfg + room + room_h + claim_h), 'no double of RoomConvertSecondsPerTile'
assert 'tiles times this value' in rooms_cfg and 'at once' in rooms_cfg
dance_room = function_body(room, 'void Room::claimForSeat(')
assert 'numCoveredTiles()' in dance_room, 'the size of the pool is read at every dance'
assert dance_room.index('mClaimHealth -=') < dance_room.index('changeOwner(seat)'), 'the whole room changes owner only after the pool is empty'
assert 'handTilesOverToSeat(seat, tiles)' in function_body(room, 'void Room::changeOwner(') and 'mCoveredTiles' in function_body(room, 'void Room::changeOwner(')
# A room that grows or shrinks while it is worn down keeps its share of the pool: merging averages by tiles,
# the part that breaks off keeps the share, the taker's new room starts full
assert 'mClaimHealth = (mClaimHealth * nbTilesThis' in function_body(room, 'void Room::absorbRoom(')
assert 'newRoom->mClaimHealth = mClaimHealth;' in function_body(room, 'void Room::checkForSplit(')
# Bridges are taken over at once with the same pool as every room: all squares together make the pool
# (squares x RoomConvertSecondsPerTile), a dance on any square lowers it, all squares change hands together.
# The only difference is the research of the owner that slows the dance
bridge = read('source/rooms/RoomBridge.cpp')
bridge_h = read('source/rooms/RoomBridge.h')
bridge_claim = function_body(bridge, 'void RoomBridge::claimForSeat(')
assert 'Room::claimForSeat(seat, tile, danceRate)' in bridge_claim and 'getResearchValue(' in bridge_claim
assert 'mClaimedValue' not in bridge and 'mClaimedValue' not in bridge_h and 'handTileOver' not in bridge, 'no per square claim value any more'
assert 'isBridge' not in price and 'numCoveredTiles()' in price, 'the price of a bridge is for all squares'
assert 'square by square' not in rooms_cfg and 'square by square' not in room_h
# The stream of a bridge keeps its number (the pool as a number of squares), so older versions read it
bridge_export = function_body(bridge, 'void RoomBridge::exportToStream(')
assert 'mClaimHealth * static_cast<double>(numCoveredTiles())' in bridge_export
bridge_import = function_body(bridge, 'bool RoomBridge::importFromStream(')
assert 'mClaimHealth = std::min(1.0, std::max(0.0, claimedValue / static_cast<double>(numCoveredTiles())))' in bridge_import
# The portal changes hands as a whole and restarts at a full pool
assert 'mClaimHealth = 1.0;' in function_body(read('source/rooms/RoomPortal.cpp'), 'void RoomPortal::changeOwner(')
# The end of a takeover is one small cosmetic event per room (roomTakeover, the last kind, appended): the server
# sends it from the one place where the whole room changes owner (Room::changeOwner, also the portal's own
# changeOwner), never per tile and never per worker; level scripts and the heart reward reach it through
# Room::claimForSeat, so they report too
event_h = read('source/network/CosmeticEvent.h')
event_cpp = read('source/network/CosmeticEvent.cpp')
assert 'roomTakeover = 14' in event_h and 'hatcheryGrain = 13,' in event_h
assert 'CosmeticEventType::roomTakeover));' in event_cpp and 'return "roomTakeover";' in event_cpp
fire = function_body(room, 'void Room::fireTakeoverEvent(')
for needle in ('isServerGameMap()', 'CosmeticEventType::roomTakeover', 'event.mValue = newSeat->getId()', 'event.mValue2 = static_cast<int32_t>(tiles.size())',
               'event.mObject = RoomManager::getRoomReadableName(getType())', 'event.mText = getName()', 'getSeatsWithVision()',
               'seats.push_back(newSeat)', 'seats.push_back(oldSeat)', 'std::find(seats.begin(), seats.end(), seat) == seats.end()',
               'sendCosmeticEvent(seat->getPlayer(), event)', 'getIsHuman()'):
    assert needle in fire, needle
assert 'sendCosmeticEvent' in fire and fire.count('sendCosmeticEvent(') == 1, 'one event per player'
assert fire.index('CosmeticEvent event(') < fire.index('for(Seat* seat : seats)'), 'the event is made once and sent to each seat'
assert 'fireTakeoverEvent(oldSeat, seat, tiles);' in function_body(room, 'void Room::changeOwner(')
assert 'fireTakeoverEvent(oldSeat, seat, mCoveredTiles);' in function_body(read('source/rooms/RoomPortal.cpp'), 'void RoomPortal::changeOwner(')
assert room.count('fireTakeoverEvent(') == 2 and 'fireTakeoverEvent' not in tile, 'not sent per tile'
# Order: the tile updates (new owners of the tiles) of a recipient are sent before the event, so the client knows
# the new owner when the event arrives (the messages of one client keep their order)
assert 'seat->notifyChangedVisibleTiles();' in fire
assert fire.index('seat->notifyChangedVisibleTiles();') < fire.index('sendCosmeticEvent(seat->getPlayer(), event)')
assert fire.index('->getIsHuman())') < fire.index('seat->notifyChangedVisibleTiles();')
# and the owner of the tiles is set before the event in both callers
portal_change = function_body(read('source/rooms/RoomPortal.cpp'), 'void RoomPortal::changeOwner(')
assert function_body(room, 'void Room::changeOwner(').index('handTilesOverToSeat(') < function_body(room, 'void Room::changeOwner(').index('fireTakeoverEvent(')
assert portal_change.index('tile->claimTile(seat)') < portal_change.index('fireTakeoverEvent(')
seat_cpp = read('source/game/Seat.cpp')
assert 'refreshTiles' in function_body(seat_cpp, 'void Seat::notifyChangedVisibleTiles(')
assert 'fireTakeoverEvent' in room_h
# Client: one reaction per room. The event ends the dancing of every worker that took the room and the worker
# nearest to the room celebrates; the old per worker path only remains as the fallback for a server without it
assert worker.count('"TakeoverDone"') == 2 and 'at once' in function_body(worker, 'void WorkerReactions::tickWorker(')
noted = function_body(worker, 'void WorkerReactions::noteRoomTakeover(')
for needle in ('sServerTellsTakeover = true', 'getSeatById(event.mValue)', 'getCoveringRoom() == room', 'event.mValue2',
               'celebrant', 'show(reactions, celebrant, "TakeoverDone")', 'mTakeoverTile = nullptr'):
    assert needle in noted, needle
assert noted.count('"TakeoverDone"') == 1 and noted.index('mTakeoverTile = nullptr') < noted.index('show(reactions, celebrant')
assert 'CosmeticEventType::roomTakeover' in function_body(worker, 'void WorkerReactions::noteCosmeticEvent(')
assert function_body(worker, 'void WorkerReactions::noteCosmeticEvent(').index('roomTakeover') < function_body(worker, 'void WorkerReactions::noteCosmeticEvent(').index('isWorker(worker)'), 'the event has no worker subject'
tick_done = function_body(worker, 'void WorkerReactions::tickWorker(')
assert 'if(!sServerTellsTakeover)' in tick_done and tick_done.index('TAKEOVER_EVENT_WAIT') < tick_done.index('if(!sServerTellsTakeover)'), 'fallback only without the event, after a short wait'
assert tick_done.count('"TakeoverDone"') == 1
assert 'sServerTellsTakeover = false' in function_body(worker, 'void WorkerReactions::stopAll(')

# Client: reactions while dancing on a tile of an enemy room and when the tile is ours
for name in ('TakeoverWork', 'TakeoverDone'):
    assert '"' + name + '"' in worker, name
    assert re.search(r'^\s*Name\s+' + name + r'\s*$', reactions_cfg, re.M), name
claim = function_body(worker, 'void WorkerReactions::showClaim(')
assert 'getIsRoom()' in claim and 'isAlliedSeat(tileOwner)' in claim and 'mTakeoverTile = tile' in claim
tick = function_body(worker, 'void WorkerReactions::tickWorker(')
assert 'mTakeoverTile' in tick and 'TakeoverDone' in tick

if '--probe' in sys.argv:
    probe = r'''
#include "rooms/RoomClaim.h"
#include <iostream>
static int gFailures = 0;
static void check(bool ok, const char* msg)
{
    if(!ok)
    {
        ++gFailures;
        std::cout << "FAIL: " << msg << '\n';
    }
}
int main()
{
    check(RoomClaim::isGuardClose(3, 4, 5.0), "a guard exactly at the radius guards");
    check(!RoomClaim::isGuardClose(4, 4, 5.0), "a guard beyond the radius does not");
    check(!RoomClaim::isGuardClose(0, 0, 0.0), "radius 0 switches the guard rule off");
    check(RoomClaim::takeoverPrice(100, 10, 0.0) == 0, "no share, no price");
    check(RoomClaim::takeoverPrice(100, 10, 25.0) == 250, "a quarter of 10 tiles at 100");
    check(RoomClaim::takeoverPrice(0, 10, 25.0) == 0, "a free room costs nothing");
    check(RoomClaim::takeoverPrice(100, 0, 25.0) == 0, "no tiles, no price");
    check(RoomClaim::takeoverSeconds(2.5, 25) == 62.5, "the pool is tiles times the duration of one tile");
    check(RoomClaim::takeoverSeconds(2.5, 0) == 0.0, "no tiles, no pool");
    // One worker at the reference rate: the pool of 25 tiles is empty after 62.5 s of dancing
    double lost = RoomClaim::healthLostPerDance(0.42, 0.42, 2.5, 1.4, 25);
    check(lost > 0.0 && (lost * 1.4 * 62.5 > 0.999) && (lost * 1.4 * 62.5 < 1.001), "one dance is a 1/(seconds x turns) share");
    std::cout << "FAILURES=" << gFailures << '\n';
    return gFailures ? 1 : 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='odp-room-takeover-') as directory:
        work = Path(directory)
        (work / 'check.cpp').write_text(probe)
        subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', '/I', str(root / 'source'), 'check.cpp', '/Fecheck.exe'],
                       cwd=work, check=True, stdout=subprocess.DEVNULL)
        result = subprocess.run([str(work / 'check.exe')], cwd=work, capture_output=True, text=True)
        sys.stdout.write(result.stdout)
        assert result.returncode == 0, 'probe failed'

print('room takeover: ok')
