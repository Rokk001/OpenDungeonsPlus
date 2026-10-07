#!/usr/bin/env python3
"""Static check of the wall torches (no compiler needed).

    python scripts/check_wall_torches.py

Checks the config keys of config/rooms.cfg, the wiring server -> network -> client -> room ambience /
wall torch view, the hatchery light check, the build entries, and that the old room torches are gone.
The placement rules themselves are covered by the unit test 00-WallTorches.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def body(text, start):
    """The text of the function that starts with start, up to the first closing brace in column 0"""
    index = text.index(start)
    return text[index:text.index("\n}\n", index)]


problems = []


def check(condition, message):
    if not condition:
        problems.append(message)


# Config keys: every key read by the code is in rooms.cfg, with the default of the code
config_cpp = read("source", "rooms", "WallTorchConfig.cpp")
rooms_cfg = read("config", "rooms.cfg")
reads = re.findall(r'read(?:Count|Clamped)\("(WallTorch\w+)",\s*([0-9.]+)', config_cpp)
check(len(reads) >= 12, "WallTorchConfig reads fewer than 12 keys")
for key, default in reads:
    match = re.search(r"^\s*%s\s+([0-9.]+)\s*$" % key, rooms_cfg, re.M)
    check(match is not None, "config/rooms.cfg has no value for " + key)
    if match is not None:
        check(float(match.group(1)) == float(default), "%s: rooms.cfg %s differs from the default %s of the code"
              % (key, match.group(1), default))
for key in ("WallTorchRoomSideDivisor", "WallTorchCorridorSpacing", "WallTorchMinDistance", "WallTorchActiveLights",
            "WallTorchActiveLightsReduced", "WallTorchSoundLoops", "WallTorchLightRadius", "WallTorchLightIntensity",
            "WallTorchFlickerStrength", "WallTorchFlickerSpeed"):
    check(key in dict(reads), "WallTorchConfig does not read " + key)
check("HatcheryCareLightRadius" in rooms_cfg, "HatcheryCareLightRadius is missing in rooms.cfg")

# Server: the list is computed by the placement and sent after the visible tiles
game_map = read("source", "gamemap", "GameMap.cpp")
check("WallTorches::compute(" in body(game_map, "void GameMap::updateWallTorches"),
      "the server does not compute the torches with WallTorches::compute")
turn = body(game_map, "unsigned long int GameMap::doMiscUpkeep")
check("updateWallTorches();" in turn and turn.index("sendVisibleTiles") < turn.index("updateWallTorches();"),
      "updateWallTorches is not called after sendVisibleTiles in doMiscUpkeep")
for place in (("source", "entities", "Tile.cpp"), ("source", "entities", "Building.cpp")):
    check("markWallTorchesDirty" in read(*place), "%s does not mark the torches dirty" % place[-1])
check("markWallTorchesDirty" in body(game_map, "void GameMap::addRoom") or
      game_map.count("markWallTorchesDirty();") >= 3, "adding or removing a room does not mark the torches dirty")

# Network: the packet is written and read in the same order, the message is known on both sides
written = body(game_map, "void GameMap::updateWallTorches")
read_back = body(game_map, "void GameMap::updateWallTorchesFromPacket")
check("mPacket << full;" in written and "OD_ASSERT_TRUE(is >> full >> nbRemoved);" in read_back,
      "wall torch packet: header differs on the two sides")
check("<< (index % sizeX) << (index / sizeX) << dir;" in written and "is >> x >> y >> dir" in read_back,
      "wall torch packet: removed torches differ on the two sides")
check("<< torch->mX << torch->mY << torch->mDir << torch->mSeatId;" in written
      and "is >> torch.mX >> torch.mY >> torch.mDir >> torch.mSeatId" in read_back,
      "wall torch packet: added torches differ on the two sides")
check("wallTorches" in read("source", "network", "ServerNotification.h"), "no wallTorches server notification")
check('return "wallTorches";' in read("source", "network", "ServerNotification.cpp"), "wallTorches has no type string")
client = read("source", "network", "ODClient.cpp")
check("case ServerNotificationType::wallTorches:" in client and "updateWallTorchesFromPacket" in client,
      "the client does not handle wallTorches")
server = read("source", "network", "ODServer.cpp")
check("resetWallTorchesSent" in server and "setWallTorchesSynced" in server,
      "the server does not send the whole list to a joining player")

# Client: the room ambience hands the list to the wall torch view, which reads the same config
ambience = read("source", "render", "RoomAmbience.cpp")
check("getWallTorchesVersion()" in body(ambience, "void RoomAmbience::syncWallTorches")
      and "setWallTorchSpots(spots)" in body(ambience, "void RoomAmbience::syncWallTorches"),
      "RoomAmbience does not pass the torch list on")
check("syncWallTorches();" in body(ambience, "void RoomAmbience::update"), "RoomAmbience::update does not sync the torches")
check("mWallTorches.update(" in ambience, "RoomAmbience does not update the wall torch view")
# The client shows exactly the list of the server: it stores what it receives and derives nothing
game_map_cpp = read("source", "gamemap", "GameMap.cpp")
received = body(game_map_cpp, "void GameMap::updateWallTorchesFromPacket")
check("WallTorches::compute(" not in received and "getTile(" not in received and "isServerGameMap" not in received,
      "the client derives torches from the map instead of taking the server list")
check("mWallTorches[WallTorches::getKey(torch.mX, torch.mY, torch.mDir, sizeX)] = torch;" in received
      and "mWallTorches.erase(" in received and "mWallTorches.clear();" in received,
      "updateWallTorchesFromPacket does not store the received list as it is")
check(game_map_cpp.count("WallTorches::compute(") == 1, "the torches are computed in more than one place")
check(game_map_cpp.count("mWallTorches[") == 2, "mWallTorches is written in an unexpected place")
sync = body(ambience, "void RoomAmbience::syncWallTorches")
check("getWallTorches()" in sync and "WallTorches::compute(" not in sync and "getTile(" not in sync
      and sync.count("spots.push_back(") == 1, "RoomAmbience::syncWallTorches does not pass on the list one to one")
# Recomputation at most once per turn: a flag, cleared when the list is computed
update = body(game_map_cpp, "void GameMap::updateWallTorches")
check("if(mWallTorchesDirty)" in update and "mWallTorchesDirty = false;" in update,
      "updateWallTorches does not compute only when the dirty flag is set")
check(game_map_cpp.count("updateWallTorches();") == 1, "updateWallTorches is called more than once per turn")
view = read("source", "render", "WallTorchView.cpp")
check("WallTorchConfig::load()" in view, "WallTorchView does not read WallTorchConfig")
for system in ("RoomAmbTorchBracket", "RoomAmbTorchFlame", "RoomAmbTorchSmoke"):
    check(system in view, "WallTorchView does not use " + system)
    check(system in read("particles", "RoomAmbienceDeferred.particle"), "particle system %s is missing" % system)
check("RoomAmbTorchGlow" not in view and "RoomAmbTorchGlow" not in read("particles", "RoomAmbienceDeferred.particle"),
      "the torch glow sprite is still present")

# Hatchery: torches of every owner within HatcheryCareLightRadius, asked for the box around the hatchery
lit = body(read("source", "rooms", "RoomHatchery.cpp"), "bool RoomHatchery::isLit")
check("WallTorches::hasTorchWithin(getGameMap()->getWallTorches()" in lit, "isLit does not ask the wall torches")
check("HatcheryCareLightRadius" in lit and "getMapLights" in lit, "isLit lost the radius or the map lights")
check("getSeat" not in lit and "isAlliedSeat" not in lit, "isLit must count the torches of every owner")
check("getRooms" not in lit, "isLit must not walk over all rooms")

# The old room torches are gone
for old in ("RoomTorches.h", "RoomTorches.cpp"):
    check(not os.path.exists(os.path.join(ROOT, "source", "rooms", old)), "source/rooms/%s still exists" % old)
for path in (("source", "rooms", "Room.h"), ("source", "rooms", "Room.cpp"), ("source", "render", "RoomAmbience.cpp"),
             ("source", "render", "RoomAmbienceConfig.h"), ("source", "render", "RoomAmbienceConfig.cpp"),
             ("source", "rooms", "RoomHatchery.cpp"), ("CMakeLists.txt")):
    text = read(*path) if isinstance(path, tuple) else read(path)
    for word in ("RoomTorches", "hasTorchOn", "isTorchSpot", "torchShift", "mTorch"):
        check(word not in text, "%s still mentions %s" % ("/".join(path) if isinstance(path, tuple) else path, word))
check("Torch       yes" not in read("config", "roomAmbienceDeferred.cfg")
      and "WallTorchBracket" not in read("config", "roomAmbienceDeferred.cfg"),
      "roomAmbienceDeferred.cfg still has the old room torch effects")

# Build entries
cmake = read("CMakeLists.txt")
for source in ("rooms/WallTorches.cpp", "rooms/WallTorchConfig.cpp", "render/WallTorchView.cpp"):
    check("${SRC}/" + source in cmake, source + " is not in CMakeLists.txt")
tests_cmake = read("source", "tests", "CMakeLists.txt")
check("add_boost_test(00-WallTorches" in tests_cmake and "test_WallTorches.cpp" in tests_cmake,
      "the unit test 00-WallTorches is not registered")
check("RoomTorches" not in tests_cmake, "source/tests/CMakeLists.txt still names RoomTorches")

# Crackling loop: nearest N torches, loop family from the real recording, stopped on removal / stopAll / hide
sounds = read("source", "sound", "SoundEffectsManager.cpp")
check("startSpatialLoop" in sounds and "stopSpatialLoop" in sounds and "setLoop(true)" in sounds,
      "SoundEffectsManager has no start/stop for positioned loops")
check(os.path.exists(os.path.join(ROOT, "sounds", "Spatial", "Rooms", "Torch", "Loop", "FxWallTorchLoop01.ogg")),
      "the torch loop recording is missing")
check('"Rooms/Torch/Loop"' in view and "startSpatialLoop(LOOP_FAMILY" in view and "mSettings.mSoundLoops" in view,
      "WallTorchView does not start the loop for the nearest torches")
check("stopSound(torch);" in body(view, "void WallTorchView::destroyTorch")
      and "stopSound(torch);" in body(view, "void WallTorchView::refresh"),
      "the loop is not stopped when a torch is removed or hidden")
check("destroyTorch(it->second);" in body(view, "void WallTorchView::stopAll"), "stopAll does not free the loops")
if problems:
    print("\n".join("PROBLEM: " + p for p in problems))
    sys.exit(1)

print("wall torch checks passed")
