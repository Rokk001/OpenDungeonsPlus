/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "rooms/RoomTavern.h"
#include "ODApplication.h"

#include "creatureaction/CreatureActionSleep.h"
#include "creatureaction/CreatureActionUseRoom.h"
#include "creatureaction/CreatureActionWalkToTile.h"
#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/InnkeeperEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "gamemap/RoomObjectNavigation.h"
#include "network/CosmeticEvent.h"
#include "network/ODPacket.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "rooms/RoomManager.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <istream>
#include <limits>
#include <map>
#include <ostream>
#include <sstream>
#include <string>

const std::string RoomTavernName = "Tavern";
const std::string RoomTavernNameDisplay = "Tavern room";
const RoomType RoomTavern::mRoomType = RoomType::tavern;
const TileVisual RoomTavern::mRoomVisual = TileVisual::tavernRoom;

namespace
{
//! \brief Mesh name of the counter on the counter tile of a tavern.
const std::string TAVERN_COUNTER_MESH = "TavernCounter";
//! \brief Mesh name of the keg on a tavern tile that lies next to a wall.
const std::string TAVERN_KEG_MESH = "TavernKeg";
//! \brief Mesh name of the table on a tavern tile that lies inside the room.
const std::string TAVERN_TABLE_MESH = "TavernTable";
//! Mesh of the round stool at each end of a table (decision 863, built by tools/tavern-meshes/make_tavern_stool.py)
const std::string TAVERN_STOOL_MESH = "TavernStool";
//! \brief A stool stands this far from the middle of its table along the table, in tiles: just beyond the ends of the
//! benches (0.656), still on the tiles of the table, so that its guest looks along the table to its middle.
const float TAVERN_STOOL_DISTANCE = 0.8f;
//! \brief How far the guests of the benches of a table reach with all their seated clips, measured from the middle of the
//! table along it and across it, at the largest creature scale (1.1); a stool guest of another table keeps its footprint
//! outside. Measured on all visiting models that sit on benches; checked by check_tavern_stools_863.py.
const float TAVERN_BENCH_REACH_ALONG = 1.48f;
const float TAVERN_BENCH_REACH_ACROSS = 1.49f;
//! \brief The footprint of a stool guest is tested on points this far apart (and on its edges), in tiles.
const float FOOTPRINT_SAMPLE_STEP = 0.25f;
//! \brief A creature that sits on a stool and the floor its seated clips cover there (decision 863). The models are those
//! whose seated clips rest the body on the seat instead of sitting on legs (RESTING_MODELS of
//! tools/author_tavern_seats.py): many legs, wings, tails, large bodies. mBlockedPlaces is the number of bench places at
//! the end of the stool, on each bench, that the seated body reaches (they stay free while it sits; 4 is the whole
//! bench). mFront, mBack and mHalfWidth bound the body in all frames of the seven seated clips at level scale 1: towards
//! the table, away from it and to the side. Measured on the models; checked by check_tavern_stools_863.py.
struct TavernStoolBody
{
    const char* mMesh;
    uint32_t mBlockedPlaces;
    float mFront;
    float mBack;
    float mHalfWidth;
};

const TavernStoolBody TAVERN_STOOL_BODIES[] =
{
    { "CaveHornet.mesh", 1, 0.13f, 0.12f, 0.26f },
    { "Kreatur.mesh", 4, 0.66f, 1.23f, 0.70f },
    { "LavaSpawn.mesh", 4, 0.42f, 0.96f, 0.98f },
    { "Rat.mesh", 2, 0.34f, 0.47f, 0.37f },
    { "Roach.mesh", 2, 0.15f, 0.57f, 0.39f },
    { "Scarab.mesh", 2, 0.23f, 0.86f, 0.43f },
    { "Slime.mesh", 1, 0.14f, 0.30f, 0.23f },
    { "Spider.mesh", 1, 0.20f, 0.56f, 0.42f },
    { "TentacleAlbine.mesh", 2, 0.35f, 0.24f, 0.31f },
    { "TentacleGreen.mesh", 2, 0.35f, 0.24f, 0.31f },
    { "Wyvern.mesh", 2, 0.38f, 0.69f, 0.49f }
};
//! \brief Scale of the table mesh: across, the table with its two benches is 1.19 tiles wide unscaled and so ends at the
//! edges of its tiles; along, the two tiles long table is 1.56 tiles unscaled.
const float TAVERN_TABLE_SCALE = 0.84f;
//! \brief Distance of the middle of a bench from the middle of the table (scaled mesh: seat surface at 0.39 to 0.59).
const float TAVERN_BENCH_OFFSET = 0.4116f;
//! \brief Distance between the middles of two neighbouring places of a bench (scaled mesh: bench 1.31 long, four places).
const float TAVERN_SEAT_SPACING = 0.328f;
//! \brief Two object angles (degrees) closer than this are the same.
const double ANGLE_EPSILON = 0.01;
//! \brief The angles (degrees) a new table is tried with, in this order: long along y, then long along x.
const double TABLE_ANGLES[] = { 0.0, 90.0 };
//! \brief Number of entries of TABLE_ANGLES.
const size_t NB_TABLE_ANGLES = 2;
//! \brief Room tiles per keg at most.
const size_t TAVERN_TILES_PER_KEG = 6;
//! \brief Room tiles per table at most: one table tile per four room tiles, and a table covers two tiles.
const size_t TAVERN_TILES_PER_TABLE = 8;
//! \brief A guest closer to its seat than this (squared, in tiles) sits on it.
const float SEAT_REACHED_SQUARED = 0.0025f;
//! \brief A point this far beside the bench (in tiles) is where a guest gets on and off when it has little room.
const float SEAT_STAGING_DISTANCE = 0.5f;
//! \brief A factor that converts degrees to radians.
const double DEGREES_TO_RADIANS = 3.14159265358979323846 / 180.0;
//! \brief Object angles (degrees) for a back to the wall at +y, -y, -x and +x (same convention as the other rooms with wall furniture).
const double OBJECT_ANGLE_WALL_TOP = 0.0;
const double OBJECT_ANGLE_WALL_BOTTOM = 180.0;
const double OBJECT_ANGLE_WALL_LEFT = 90.0;
const double OBJECT_ANGLE_WALL_RIGHT = 270.0;
//! \brief Line of the room stream with who pays for the beer (0 = keeper, 1 = creature).
const std::string STREAM_TAG_PAYER = "TavernPayer";
//! \brief Line of the room stream with the tile the innkeeper stands on.
const std::string STREAM_TAG_INNKEEPER = "Innkeeper";
//! \brief Line of the room stream with the counter tile.
const std::string STREAM_TAG_COUNTER = "Counter";
//! \brief Line of the room stream with the place of one guest.
const std::string STREAM_TAG_SPOT = "Spot";
//! \brief Line of the room stream with one running game.
const std::string STREAM_TAG_GAME = "Game";
//! \brief Line of the room stream with one keg or table.
const std::string STREAM_TAG_FURNITURE = "Furniture";
//! \brief Line of the room stream that marks a save whose guests have seats at the tables (format number).
const std::string STREAM_TAG_SEAT_LAYOUT = "SeatLayout";
//! \brief The format number of the seat data written to the room stream: 2 for tables two tiles long with eight places.
//! A save of format 1 (tables of one tile with four seats) is loaded like a save without seat data.
const uint32_t SEAT_LAYOUT_VERSION = 2;
//! \brief Sound family of a drink that is poured.
const std::string SOUND_POUR = "Rooms/Tavern/Pour";
//! \brief Sound family of a slap in a slap duel.
const std::string SOUND_SLAP = "Creatures/Default/Slap";
//! \brief Sound family of the cheer when a game ends.
const std::string SOUND_CHEER = "Creatures/Default/Cheer";
//! \brief Turns the loser of a slap duel needs to get up from the floor: CreatureGetUpSeconds (6 s) rounded up.
int32_t getUpTurns()
{
    return static_cast<int32_t>(std::ceil(ConfigManager::getSingleton().getRoomConfigDouble("CreatureGetUpSeconds")
        * ODApplication::turnsPerSecond));
}
//! \brief Tolerance when seconds of the configuration are turned into whole turns (4 s x 1.4 is not exactly 5.6).
const double TURN_EPSILON = 0.000001;
//! \brief Turns of one slap or one pause of a slap duel, drawn anew every time: a whole number of turns that lasts
//! between the seconds of the room keys minKey and maxKey (TavernSlapSeconds*, TavernSlapPauseSeconds*), at least one.
int32_t randomDuelTurns(const std::string& minKey, const std::string& maxKey)
{
    const double minSeconds = ConfigManager::getSingleton().getRoomConfigDouble(minKey);
    const double maxSeconds = std::max(minSeconds, ConfigManager::getSingleton().getRoomConfigDouble(maxKey));
    const uint32_t fewest = static_cast<uint32_t>(std::max(1.0,
        std::ceil(minSeconds * ODApplication::turnsPerSecond - TURN_EPSILON)));
    const uint32_t most = std::max(fewest, static_cast<uint32_t>(
        std::floor(maxSeconds * ODApplication::turnsPerSecond + TURN_EPSILON)));
    return static_cast<int32_t>(Random::Uint(fewest, most));
}
//! \brief Turns a guest stays done after its last drink while a game partner may be found.
const int32_t DONE_WAIT_TURNS = 1;
//! \brief The turn of the knock-out itself: upkeepSpots counts it down in the same upkeep as upkeepGames knocks the loser
//! out, so the lying count starts this much above DuelKoTurns (decision 897: 42 turns lying, exactly 30 s)
const int32_t KNOCK_OUT_TURN = 1;
//! \brief The floor a knocked-out guest covers in its KnockedOut clip, in tiles at level scale 1, in the frame of the
//! creature (it looks along -y): from mBehindMin to mBehindMax along +y (behind it) and mHalfWidth to either side. Measured
//! on all 33 frames of the clip of every model that visits the tavern and is not large (decision 833: the lying body
//! must never reach into a table or a bench); checked by check_tavern_drink_834.py.
struct TavernLyingBody
{
    const char* mMesh;
    float mBehindMin;
    float mBehindMax;
    float mHalfWidth;
};

const TavernLyingBody TAVERN_LYING_BODIES[] =
{
    { "Adventurer.mesh", -0.02f, 0.94f, 0.25f },
    { "CaveHornet.mesh", -0.22f, 0.30f, 0.18f },
    { "Cultist.mesh", -0.03f, 1.08f, 0.30f },
    { "DarkElf.mesh", -0.07f, 0.88f, 0.25f },
    { "Defender.mesh", -0.12f, 0.98f, 0.68f },
    { "Dwarf1.mesh", -0.02f, 0.73f, 0.25f },
    { "Dwarf2.mesh", -0.02f, 0.73f, 0.25f },
    { "Elf.mesh", -0.07f, 0.88f, 0.25f },
    { "Gnome.mesh", -0.03f, 0.64f, 0.17f },
    { "Goblin.mesh", -0.04f, 0.75f, 0.32f },
    { "Knight.mesh", -0.03f, 0.99f, 0.26f },
    { "LavaSpawn.mesh", -0.05f, 1.00f, 0.64f },
    { "Lizardman.mesh", -0.02f, 0.90f, 0.31f },
    { "Monk.mesh", -0.04f, 0.90f, 0.23f },
    { "NatureMonster.mesh", -0.06f, 1.21f, 0.52f },
    { "Orc.mesh", -0.03f, 0.93f, 0.37f },
    { "Rat.mesh", -0.49f, 0.60f, 0.14f },
    { "Roach.mesh", -0.43f, 0.46f, 0.30f },
    { "RunelordDwarf.mesh", -0.02f, 0.78f, 0.29f },
    { "Slime.mesh", -0.25f, 0.21f, 0.15f },
    { "Spider.mesh", -0.45f, 0.43f, 0.42f },
    { "TentacleAlbine.mesh", -0.26f, 0.26f, 0.24f },
    { "TentacleGreen.mesh", -0.26f, 0.26f, 0.24f },
    { "Wizard.mesh", -0.03f, 1.05f, 0.26f },
    { "Wyvern.mesh", -0.02f, 0.83f, 0.49f },
    { "lich.mesh", -0.04f, 1.54f, 0.52f }
};
//! \brief The lying body of a model that is not in TAVERN_LYING_BODIES: the largest values of the table.
const TavernLyingBody TAVERN_LYING_BODY_DEFAULT = { "", -0.49f, 1.54f, 0.68f };
//! \brief The loser walks this far (tiles) past the place it falls on and turns back to it, so that it looks towards its
//! table when it goes down and its body falls away from the table.
const float KO_TURN_STEP = 0.15f;
//! \brief The stool body of a creature, nullptr for a creature that sits on a bench.
//! \param creature The creature.
const TavernStoolBody* findStoolBody(const Creature& creature)
{
    const CreatureDefinition* definition = creature.getDefinition();
    if(definition == nullptr)
        return nullptr;

    for(const TavernStoolBody& body : TAVERN_STOOL_BODIES)
    {
        if(definition->getMeshName() == body.mMesh)
            return &body;
    }
    return nullptr;
}
//! \brief True when a stool guest that reaches blockedPlaces bench places from the end of its stool reaches the place.
//! \param stoolIndex The stool place, 8 (at the end of the places 0 and 4) or 9 (at the end of 3 and 7).
//! \param blockedPlaces The places it reaches on each bench.
//! \param place A bench place (0 to 7).
bool stoolReachesPlace(uint32_t stoolIndex, uint32_t blockedPlaces, uint32_t place)
{
    const uint32_t along = place % TAVERN_SEATS_PER_BENCH;
    if(stoolIndex == TAVERN_SEATS_PER_TABLE)
        return along < blockedPlaces;
    return along + blockedPlaces >= TAVERN_SEATS_PER_BENCH;
}
//! \brief The side of the table a place belongs to: 0 and 1 the benches, 2 and 3 the stools. Two guests on different
//! benches, or on the two stools, face each other.
//! \param index The place at the table.
uint32_t seatSide(uint32_t index)
{
    if(index < TAVERN_SEATS_PER_TABLE)
        return index / TAVERN_SEATS_PER_BENCH;
    return 2 + (index - TAVERN_SEATS_PER_TABLE);
}
//! \brief Scale of the percent values of the [Tavern] block.
const double PERCENT_SCALE = 100.0;
//! \brief A squared direction shorter than this has no usable direction.
const double DIRECTION_EPSILON = 0.0001;
//! \brief Number of games a guest can pick when no beer is served (arm wrestling and dice).
const uint32_t NB_GAMES_WITHOUT_BEER = 2;
//! \brief Number of games a guest can pick when beer is served (arm wrestling, dice and the slap duel).
const uint32_t NB_GAMES_WITH_BEER = 3;

//! \brief Reads a value of the [Tavern] block of global.cfg.
//! \param key The key of the value.
double getTavernValue(const std::string& key)
{
    return ConfigManager::getSingleton().getTavernConfigDouble(key);
}

//! \brief The name of a guest state in the room stream.
//! \param state The state.
std::string guestStateToString(TavernGuestState state)
{
    switch(state)
    {
        case TavernGuestState::arriving:
            return "arriving";
        case TavernGuestState::drinking:
            return "drinking";
        case TavernGuestState::done:
            return "done";
        case TavernGuestState::game:
            return "game";
        case TavernGuestState::ko:
            return "ko";
        case TavernGuestState::getUp:
            return "getup";
    }
    return "done";
}

//! \brief Reads the name of a guest state from the room stream.
//! \param token The name.
//! \param state Set to the state when the name is known.
//! \return False for an unknown name.
bool guestStateFromString(const std::string& token, TavernGuestState& state)
{
    if(token == "arriving")
        state = TavernGuestState::arriving;
    else if(token == "drinking")
        state = TavernGuestState::drinking;
    else if(token == "done")
        state = TavernGuestState::done;
    else if(token == "game")
        state = TavernGuestState::game;
    else if(token == "ko")
        state = TavernGuestState::ko;
    else if(token == "getup")
        state = TavernGuestState::getUp;
    else
        return false;

    return true;
}

//! \brief The direction on the ground from a creature to a point; zero when they are on the same spot.
//! \param from The creature.
//! \param target The point.
Ogre::Vector3 directionTo(const Creature& from, const Ogre::Vector3& target)
{
    Ogre::Vector3 direction(target.x - from.getPosition().x, target.y - from.getPosition().y, 0.0f);
    if(direction.squaredLength() < DIRECTION_EPSILON)
        return Ogre::Vector3::ZERO;

    direction.normalise();
    return direction;
}

//! \brief The place of a seat relative to the middle of its table. The four places of a bench lie TAVERN_SEAT_SPACING
//! apart along the table, symmetric around its middle; a large guest sits in the middle of the places it takes. The two
//! stools stand TAVERN_STOOL_DISTANCE from the middle along the table, 8 beyond the places 0 and 4, 9 beyond 3 and 7.
//! \param index The number of the place at the table.
//! \param places The number of places the guest takes, starting at the given one (not used for a stool).
//! \param angleDegrees The rotation of the table.
Ogre::Vector2 seatOffset(uint32_t index, uint32_t places, double angleDegrees)
{
    float x = (index < TAVERN_SEATS_PER_BENCH) ? TAVERN_BENCH_OFFSET : -TAVERN_BENCH_OFFSET;
    const float place = static_cast<float>(index % TAVERN_SEATS_PER_BENCH);
    float y = (0.5f * static_cast<float>(TAVERN_SEATS_PER_BENCH - 1) - place) * TAVERN_SEAT_SPACING;
    if(places > 1)
        y -= 0.5f * static_cast<float>(places - 1) * TAVERN_SEAT_SPACING;
    if(index >= TAVERN_SEATS_PER_TABLE)
    {
        x = 0.0f;
        y = (index == TAVERN_SEATS_PER_TABLE) ? TAVERN_STOOL_DISTANCE : -TAVERN_STOOL_DISTANCE;
    }

    const double angle = angleDegrees * DEGREES_TO_RADIANS;
    const float cosine = static_cast<float>(std::cos(angle));
    const float sine = static_cast<float>(std::sin(angle));
    return Ogre::Vector2(x * cosine - y * sine, x * sine + y * cosine);
}

//! \brief The step from the tile of a table to its second tile: the table is long along its own y axis, turned by its
//! angle like seatOffset.
//! \param angleDegrees The rotation of the table.
//! \param dx Set to the step in x (-1, 0 or 1).
//! \param dy Set to the step in y (-1, 0 or 1).
void tableStep(double angleDegrees, int32_t& dx, int32_t& dy)
{
    const double angle = angleDegrees * DEGREES_TO_RADIANS;
    dx = static_cast<int32_t>(std::floor(-std::sin(angle) + 0.5));
    dy = static_cast<int32_t>(std::floor(std::cos(angle) + 0.5));
}

//! \brief The second tile of a table, next to the tile of its object along the length of the table.
//! \param gameMap The map of the table.
//! \param tile The tile of the table object.
//! \param angleDegrees The rotation of the table.
//! \return The tile, nullptr at the edge of the map.
Tile* tableSecondTile(GameMap* gameMap, const Tile& tile, double angleDegrees)
{
    int32_t dx = 0;
    int32_t dy = 0;
    tableStep(angleDegrees, dx, dy);
    return gameMap->getTile(tile.getX() + dx, tile.getY() + dy);
}

//! \brief The middle of a table on the ground: halfway between its two tiles.
//! \param tile The tile of the table object.
//! \param angleDegrees The rotation of the table.
Ogre::Vector2 tableMiddle(const Tile& tile, double angleDegrees)
{
    int32_t dx = 0;
    int32_t dy = 0;
    tableStep(angleDegrees, dx, dy);
    return Ogre::Vector2(static_cast<Ogre::Real>(tile.getX()) + 0.5f * static_cast<Ogre::Real>(dx),
        static_cast<Ogre::Real>(tile.getY()) + 0.5f * static_cast<Ogre::Real>(dy));
}

//! \brief True when a wall or the edge of the map lies directly behind a bench of a table, next to either of its two
//! tiles. Nobody sits on such a bench, so no guest ever sits in a wall. The first bench lies on the +x side of the table,
//! turned by its angle like seatOffset; the second one on the opposite side.
//! \param gameMap The map of the table.
//! \param tile The tile of the table object.
//! \param angleDegrees The rotation of the table.
//! \param bench 0 for the first bench, 1 for the second.
bool isBenchBehindWall(GameMap* gameMap, const Tile& tile, double angleDegrees, uint32_t bench)
{
    const double angle = angleDegrees * DEGREES_TO_RADIANS;
    const int32_t side = (bench == 0) ? 1 : -1;
    const int32_t dx = side * static_cast<int32_t>(std::floor(std::cos(angle) + 0.5));
    const int32_t dy = side * static_cast<int32_t>(std::floor(std::sin(angle) + 0.5));
    const Tile* second = tableSecondTile(gameMap, tile, angleDegrees);
    const Tile* pieces[] = { &tile, second };
    for(const Tile* piece : pieces)
    {
        if(piece == nullptr)
            continue;

        const Tile* behind = gameMap->getTile(piece->getX() + dx, piece->getY() + dy);
        if((behind == nullptr) || behind->isFullTile())
            return true;
    }
    return false;
}

//! \brief True when the tiles on both long sides of a table, where its benches stand, are tiles of the room without
//! furniture, so that the guests on the benches neither sit in a wall nor against other furniture.
//! \param gameMap The map of the room.
//! \param tile The tile of the table object.
//! \param second The second tile of the table.
//! \param roomTiles The tiles of the room.
//! \param furnitureTiles The tiles that already carry furniture.
bool areBenchSidesFree(GameMap* gameMap, const Tile& tile, const Tile& second, const std::vector<Tile*>& roomTiles,
    const std::vector<Tile*>& furnitureTiles)
{
    // Across the table: the length of the table turned by a quarter
    const int32_t acrossX = second.getY() - tile.getY();
    const int32_t acrossY = tile.getX() - second.getX();
    const Tile* pieces[] = { &tile, &second };
    for(const Tile* piece : pieces)
    {
        for(int32_t side = -1; side <= 1; side += 2)
        {
            Tile* neighbour = gameMap->getTile(piece->getX() + side * acrossX, piece->getY() + side * acrossY);
            if((neighbour == nullptr) || (std::find(roomTiles.begin(), roomTiles.end(), neighbour) == roomTiles.end()) ||
               (std::find(furnitureTiles.begin(), furnitureTiles.end(), neighbour) != furnitureTiles.end()))
                return false;
        }
    }
    return true;
}

//! \brief Returns whether the room contains a complete three by three block.
bool hasTavernBlock(const std::vector<Tile*>& tiles)
{
    for(const Tile* origin : tiles)
    {
        bool complete = true;
        for(int dx = 0; dx < 3 && complete; ++dx)
        {
            for(int dy = 0; dy < 3; ++dy)
            {
                bool found = false;
                for(const Tile* tile : tiles)
                {
                    if((tile->getX() == origin->getX() + dx) && (tile->getY() == origin->getY() + dy))
                    {
                        found = true;
                        break;
                    }
                }
                if(!found)
                {
                    complete = false;
                    break;
                }
            }
        }
        if(complete)
            return true;
    }
    return false;
}

//! \brief Checks every resulting tavern connected to the proposed new tiles.
bool canBuildTavern(GameMap* gameMap, Seat* seat, const std::vector<Tile*>& tiles)
{
    std::vector<Tile*> remaining = tiles;
    while(!remaining.empty())
    {
        std::vector<Tile*> connected(1, remaining.back());
        remaining.pop_back();
        for(size_t i = 0; i < connected.size(); ++i)
        {
            Tile* tile = connected[i];
            Tile* neighbours[] = {gameMap->getTile(tile->getX() + 1, tile->getY()),
                                  gameMap->getTile(tile->getX() - 1, tile->getY()),
                                  gameMap->getTile(tile->getX(), tile->getY() + 1),
                                  gameMap->getTile(tile->getX(), tile->getY() - 1)};
            for(Tile* neighbour : neighbours)
            {
                if((neighbour == nullptr) ||
                   (std::find(connected.begin(), connected.end(), neighbour) != connected.end()))
                    continue;
                std::vector<Tile*>::iterator selected = std::find(remaining.begin(), remaining.end(), neighbour);
                Room* room = neighbour->getCoveringRoom();
                if(selected != remaining.end())
                    remaining.erase(selected);
                else if((room == nullptr) || (room->getType() != RoomType::tavern) || (room->getSeat() != seat))
                    continue;
                connected.push_back(neighbour);
            }
        }
        if(!hasTavernBlock(connected))
            return false;
    }
    return !tiles.empty();
}

//! \brief Builds, prices and loads taverns; registered for RoomType::tavern.
class RoomTavernFactory : public RoomFactory
{
    RoomType getRoomType() const override
    { return RoomTavern::mRoomType; }

    TileVisual getVisualType() const override
    { return RoomTavern::mRoomVisual; }

    const std::string& getName() const override
    { return RoomTavernName; }

    const std::string& getNameReadable() const override
    { return RoomTavernNameDisplay; }

    int getCostPerTile() const override
    { return ConfigManager::getSingleton().getRoomConfigInt32("TavernCostPerTile"); }

    void checkBuildRoom(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefault(gameMap, RoomTavern::mRoomType, inputManager, inputCommand);
    }

    //! \brief Builds a tavern only when each resulting room contains a three by three block.
    bool buildRoom(GameMap* gameMap, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, gameMap, player, packet) ||
           !canBuildTavern(gameMap, player->getSeat(), tiles))
            return false;

        int32_t pricePerTarget = RoomManager::costPerTile(RoomTavern::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
            return false;

        RoomTavern* room = new RoomTavern(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }

    void checkBuildRoomEditor(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefaultEditor(gameMap, RoomTavern::mRoomType, inputManager, inputCommand);
    }

    //! \brief Checks the resulting tavern before the editor changes any tiles.
    bool buildRoomEditor(GameMap* gameMap, ODPacket& packet) const override
    {
        ODPacket probe(packet);
        int32_t seatId = 0;
        uint32_t count = 0;
        if(!(probe >> seatId >> count))
            return false;
        Seat* seat = gameMap->getSeatById(seatId);
        if(seat == nullptr)
            return false;
        std::vector<Tile*> tiles;
        while(count-- > 0)
        {
            Tile* tile = gameMap->tileFromPacket(probe);
            if(tile == nullptr)
                return false;
            if(tile->getCoveringBuilding() == nullptr)
                tiles.push_back(tile);
        }
        if(!canBuildTavern(gameMap, seat, tiles))
            return false;
        RoomTavern* room = new RoomTavern(gameMap);
        return buildRoomDefaultEditor(gameMap, room, packet);
    }

    //! \brief Creates an empty room of this type, for a room that has to be split in two.
    Room* createRoom(GameMap* gameMap) const override
    { return new RoomTavern(gameMap); }

    Room* getRoomFromStream(GameMap* gameMap, std::istream& is) const override
    {
        RoomTavern* room = new RoomTavern(gameMap);
        if(!Room::importRoomFromStream(*room, is))
        {
            OD_LOG_ERR("Error while building a room from the stream");
        }
        return room;
    }

    //! \brief Builds a tavern on the tiles when each resulting room contains a three by three block.
    bool buildRoomOnTiles(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles, bool noFee =false) const override
    {
        if(!canBuildTavern(gameMap, player->getSeat(), tiles))
            return false;

        int32_t pricePerTarget = RoomManager::costPerTile(RoomTavern::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!noFee)
            if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
                return false;
        RoomTavern* room = new RoomTavern(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }
};

// Register the factory
static RoomRegister reg(new RoomTavernFactory);

//! \brief Reads the x and y of a tile from the stream and looks the tile up on the map.
//! \param gameMap The map the tile belongs to.
//! \param is The stream, positioned behind the tag of the line.
//! \param tile Set to the tile, nullptr when the numbers are fine but the map has no such tile.
//! \return False if the two numbers could not be read.
bool readTileFromStream(GameMap* gameMap, std::istream& is, Tile*& tile)
{
    int32_t x = 0;
    int32_t y = 0;
    if(!(is >> x >> y))
        return false;

    tile = gameMap->getTile(x, y);
    return true;
}
}

RoomTavern::RoomTavern(GameMap* gameMap) :
    Room(gameMap),
    mPayer(TavernPayer::keeper),
    mCounterTile(nullptr),
    mInnkeeper(nullptr),
    mLayoutCounter(nullptr)
{
    setMeshName("Room");
}

uint32_t RoomTavern::getNbDrinkingTiles() const
{
    const uint32_t nbTiles = static_cast<uint32_t>(mCoveredTiles.size());
    if((mCounterTile != nullptr) && (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), mCounterTile) != mCoveredTiles.end()))
        return nbTiles - 1;

    return nbTiles;
}

//! \brief Returns whether the tavern contains a full three by three block.
bool RoomTavern::hasMinimumBlock() const
{
    return hasTavernBlock(mCoveredTiles);
}

//! \brief Returns the free floor tile of the room nearest to the seat of the guest; the walk onto the bench starts there.
//! A tile with furniture, also the second tile of a table, is never returned while a free one exists.
Tile* RoomTavern::getArrivalTile(const Creature& creature)
{
    // The tile under the seat; a table is two tiles long, so the seat can lie on either of them
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    Tile* reference = getCoveredTile(0);
    if(it != mSpots.end())
    {
        const Ogre::Vector2 seatPosition = getSeatPosition(it->first, it->second.mPlaces);
        reference = getGameMap()->getTile(Helper::round(seatPosition.x), Helper::round(seatPosition.y));
        if(reference == nullptr)
            reference = it->first.mTable;
    }
    if(reference == nullptr)
        return nullptr;

    // The middle of a tile with furniture lies inside the furniture, so a tile path may not end there
    Tile* best = nullptr;
    int32_t bestDistance = std::numeric_limits<int32_t>::max();
    for(Tile* tile : mCoveredTiles)
    {
        if(hasFurnitureOn(tile) || !creature.canGoThroughTile(tile))
            continue;

        const int32_t dx = tile->getX() - reference->getX();
        const int32_t dy = tile->getY() - reference->getY();
        const int32_t distance = dx * dx + dy * dy;
        if(distance < bestDistance)
        {
            bestDistance = distance;
            best = tile;
        }
    }
    return (best != nullptr) ? best : reference;
}

//! \brief True when a keg, a table or the counter stands on the tile; the second tile of a table counts too.
bool RoomTavern::hasFurnitureOn(const Tile* tile) const
{
    if(tile == nullptr)
        return false;

    for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
    {
        if(entry.first == tile)
            return true;

        if((entry.second->getMeshName() == TAVERN_TABLE_MESH) &&
           (tableSecondTile(getGameMap(), *entry.first, entry.second->getRotationAngle()) == tile))
            return true;
    }
    return false;
}

//! \brief Checks that the tavern is large enough and has a free seat for the creature.
bool RoomTavern::hasOpenCreatureSpot(Creature* c)
{
    if(!hasTavernBlock(mCoveredTiles))
        return false;

    // A creature the saved room waits for has its place, whatever the other guests do
    if((c != nullptr) && (mPendingSpots.find(c->getName()) != mPendingSpots.end()))
        return true;

    // A leisure visit (the creature is not thirsty) needs a creature without a running pleasure buff and with the tavern
    // open to it (the lock since its last leisure visit is over); a thirsty creature may always come for a drink
    if((c != nullptr) && !c->canUsePleasureRoom(PleasureRoomKind::tavern) &&
       (c->getThirst() < getTavernValue("ThirstSeek")))
        return false;

    // Without a creature any free seat will do
    if(c == nullptr)
    {
        for(Tile* table : getTableTiles())
        {
            for(uint32_t index = 0; index < TAVERN_SEATS_PER_TABLE; ++index)
            {
                if(isFreeSeat(RoomTavernSeat(table, index), 1))
                    return true;
            }
        }
        return false;
    }

    RoomTavernSeat seat;
    return pickFreeSeat(*c, seat);
}

//! \brief Returns the tiles of the tables of the room in coordinate order.
std::vector<Tile*> RoomTavern::getTableTiles() const
{
    std::vector<Tile*> tables;
    for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
    {
        if(entry.second->getMeshName() == TAVERN_TABLE_MESH)
            tables.push_back(entry.first);
    }
    std::sort(tables.begin(), tables.end(), Room::compareTile);
    return tables;
}

//! \brief True when the seat is at a table of the room and can take a guest: its bench has no wall behind it and all the
//! places the guest needs, starting at the seat, are free on that bench and out of reach of a guest on a stool.
bool RoomTavern::isFreeSeat(const RoomTavernSeat& seat, uint32_t places) const
{
    if((seat.mTable == nullptr) || (seat.mIndex >= TAVERN_SEATS_PER_TABLE) || (places < 1))
        return false;

    // All places of the guest lie on the bench of its seat
    const uint32_t bench = seat.mIndex / TAVERN_SEATS_PER_BENCH;
    if((seat.mIndex % TAVERN_SEATS_PER_BENCH) + places > TAVERN_SEATS_PER_BENCH)
        return false;

    // A bench with a wall behind it stays empty
    if(isBenchBlocked(seat.mTable, bench))
        return false;

    // The places a guest on a stool of this table reaches stay free (decision 863)
    if(isPlaceBlockedByStool(seat, places))
        return false;

    // A guest is kept under its first place and covers the places after it
    for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
    {
        if(entry.first.mTable != seat.mTable)
            continue;

        const uint32_t takenFrom = entry.first.mIndex;
        const uint32_t takenTo = takenFrom + entry.second.mPlaces;
        if((takenFrom < seat.mIndex + places) && (seat.mIndex < takenTo))
            return false;
    }

    return true;
}

//! \brief True when a bench has a wall (or the edge of the map) directly behind it, so that nobody sits there.
bool RoomTavern::isBenchBlocked(const Tile* table, uint32_t bench) const
{
    std::map<Tile*, BuildingObject*>::const_iterator object = mBuildingObjects.find(const_cast<Tile*>(table));
    if(object == mBuildingObjects.end())
        return false;

    return isBenchBehindWall(getGameMap(), *table, object->second->getRotationAngle(), bench);
}

bool RoomTavern::usesStool(const Creature& creature)
{
    return findStoolBody(creature) != nullptr;
}

bool RoomTavern::isStoolSeat(const RoomTavernSeat& seat)
{
    return (seat.mIndex >= TAVERN_SEATS_PER_TABLE) && (seat.mIndex < TAVERN_PLACES_PER_TABLE);
}

//! \brief A stool guest may only take a free stool, every other guest only free places of a bench.
bool RoomTavern::isFreeSeatFor(const Creature& creature, const RoomTavernSeat& seat) const
{
    if(usesStool(creature))
        return isStoolSeat(seat) && isFreeStool(creature, seat);

    return !isStoolSeat(seat) && isFreeSeat(seat, getPlacesOf(creature));
}

//! \brief The stool is free, the bench places its guest reaches are free and its footprint touches nobody and nothing.
bool RoomTavern::isFreeStool(const Creature& creature, const RoomTavernSeat& seat) const
{
    const TavernStoolBody* body = findStoolBody(creature);
    if((body == nullptr) || !isStoolSeat(seat) || (seat.mTable == nullptr) ||
       (mBuildingObjects.find(seat.mTable) == mBuildingObjects.end()) || (mSpots.find(seat) != mSpots.end()))
        return false;

    // The bench places at the end of the stool that its seated body reaches must be free, also of a large guest that
    // covers them from an earlier place
    for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
    {
        if((entry.first.mTable != seat.mTable) || isStoolSeat(entry.first))
            continue;

        for(uint32_t place = entry.first.mIndex; place < entry.first.mIndex + entry.second.mPlaces; ++place)
        {
            if(stoolReachesPlace(seat.mIndex, body->mBlockedPlaces, place))
                return false;
        }
    }

    Ogre::Vector2 minimum;
    Ogre::Vector2 maximum;
    if(!getStoolFootprint(creature, seat, minimum, maximum))
        return false;

    // The footprint never overlaps the footprint of a guest on another stool of the room
    for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
    {
        if(!isStoolSeat(entry.first) || (entry.second.mCreature == nullptr) || (entry.second.mCreature == &creature))
            continue;

        Ogre::Vector2 otherMinimum;
        Ogre::Vector2 otherMaximum;
        if(!getStoolFootprint(*entry.second.mCreature, entry.first, otherMinimum, otherMaximum))
            continue;

        if((minimum.x < otherMaximum.x) && (otherMinimum.x < maximum.x) && (minimum.y < otherMaximum.y) &&
           (otherMinimum.y < maximum.y))
            return false;
    }

    // Every point of the footprint lies on a tile of this room without furniture (the tiles of its own table excepted)
    // and outside the reach of the guests of every other table
    const Tile* secondTile = nullptr;
    std::map<Tile*, BuildingObject*>::const_iterator ownTable = mBuildingObjects.find(seat.mTable);
    secondTile = tableSecondTile(getGameMap(), *seat.mTable, ownTable->second->getRotationAngle());
    const int32_t stepsX = static_cast<int32_t>(std::ceil((maximum.x - minimum.x) / FOOTPRINT_SAMPLE_STEP));
    const int32_t stepsY = static_cast<int32_t>(std::ceil((maximum.y - minimum.y) / FOOTPRINT_SAMPLE_STEP));
    for(int32_t ix = 0; ix <= stepsX; ++ix)
    {
        for(int32_t iy = 0; iy <= stepsY; ++iy)
        {
            const Ogre::Vector2 point(
                minimum.x + (maximum.x - minimum.x) * static_cast<float>(ix) / static_cast<float>(std::max(stepsX, 1)),
                minimum.y + (maximum.y - minimum.y) * static_cast<float>(iy) / static_cast<float>(std::max(stepsY, 1)));
            Tile* tile = getGameMap()->getTile(Helper::round(point.x), Helper::round(point.y));
            if((tile == nullptr) || (tile->getCoveringRoom() != this))
                return false;

            if((tile != seat.mTable) && (tile != secondTile) && hasFurnitureOn(tile))
                return false;

            for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
            {
                if((entry.first == seat.mTable) || (entry.second->getMeshName() != TAVERN_TABLE_MESH))
                    continue;

                const double angle = entry.second->getRotationAngle() * DEGREES_TO_RADIANS;
                const float dx = point.x - entry.second->getPosition().x;
                const float dy = point.y - entry.second->getPosition().y;
                const float along = -dx * static_cast<float>(std::sin(angle)) + dy * static_cast<float>(std::cos(angle));
                const float across = dx * static_cast<float>(std::cos(angle)) + dy * static_cast<float>(std::sin(angle));
                if((std::abs(along) < TAVERN_BENCH_REACH_ALONG) && (std::abs(across) < TAVERN_BENCH_REACH_ACROSS))
                    return false;
            }
        }
    }
    return true;
}

bool RoomTavern::isPlaceBlockedByStool(const RoomTavernSeat& seat, uint32_t places) const
{
    for(uint32_t stool = TAVERN_SEATS_PER_TABLE; stool < TAVERN_PLACES_PER_TABLE; ++stool)
    {
        std::map<RoomTavernSeat, RoomTavernSpot>::const_iterator guest = mSpots.find(RoomTavernSeat(seat.mTable, stool));
        if((guest == mSpots.end()) || (guest->second.mCreature == nullptr))
            continue;

        const TavernStoolBody* body = findStoolBody(*guest->second.mCreature);
        // A guest of a save that sits on a stool without a stool body reaches the whole table
        const uint32_t blocked = (body != nullptr) ? body->mBlockedPlaces : TAVERN_SEATS_PER_BENCH;
        for(uint32_t place = seat.mIndex; place < seat.mIndex + places; ++place)
        {
            if(stoolReachesPlace(stool, blocked, place))
                return true;
        }
    }
    return false;
}

bool RoomTavern::getStoolFootprint(const Creature& creature, const RoomTavernSeat& seat, Ogre::Vector2& minimum,
    Ogre::Vector2& maximum) const
{
    const TavernStoolBody* body = findStoolBody(creature);
    if(body == nullptr)
        return false;

    // The guest looks along the table; its body reaches mFront towards the table, mBack away from it, mHalfWidth aside
    const float scale = static_cast<float>(creature.getLevelScale());
    const Ogre::Vector2 position = getSeatPosition(seat, 1);
    const Ogre::Vector3 facing = getAcrossTableDirection(seat);
    const Ogre::Vector2 forward(facing.x, facing.y);
    const Ogre::Vector2 side(-facing.y, facing.x);
    const Ogre::Vector2 corners[] =
    {
        position + forward * (body->mFront * scale) + side * (body->mHalfWidth * scale),
        position + forward * (body->mFront * scale) - side * (body->mHalfWidth * scale),
        position - forward * (body->mBack * scale) + side * (body->mHalfWidth * scale),
        position - forward * (body->mBack * scale) - side * (body->mHalfWidth * scale)
    };
    minimum = corners[0];
    maximum = corners[0];
    for(const Ogre::Vector2& corner : corners)
    {
        minimum.makeFloor(corner);
        maximum.makeCeil(corner);
    }
    return true;
}

std::vector<RoomObjectPath::Obstacle> RoomTavern::seatObstacles(Creature& creature, const RoomTavernSeat& seat) const
{
    std::map<Tile*, BuildingObject*>::const_iterator table = mBuildingObjects.find(seat.mTable);
    std::vector<RoomObjectPath::Obstacle> obstacles = RoomObjectNavigation::bodyObstacles(creature,
        (table != mBuildingObjects.end()) ? table->second : nullptr);
    std::map<RoomTavernSeat, BuildingObject*>::const_iterator stool = mStoolObjects.find(seat);
    if(stool == mStoolObjects.end())
        return obstacles;

    // The stool of the seat is the piece the guest sits on: it stands where the stool stands
    const Ogre::Vector2 stoolPosition(stool->second->getPosition().x, stool->second->getPosition().y);
    for(std::vector<RoomObjectPath::Obstacle>::iterator it = obstacles.begin(); it != obstacles.end();)
    {
        if(it->position.squaredDistance(stoolPosition) < static_cast<float>(DIRECTION_EPSILON))
            it = obstacles.erase(it);
        else
            ++it;
    }
    return obstacles;
}

void RoomTavern::updateStools(GameMap* gameMap)
{
    if(!getIsOnServerMap())
        return;

    if(gameMap == nullptr)
        gameMap = getGameMap();

    // Stools of tables that are gone or were turned go away
    bool changed = false;
    std::map<RoomTavernSeat, BuildingObject*>::iterator it = mStoolObjects.begin();
    while(it != mStoolObjects.end())
    {
        std::map<Tile*, BuildingObject*>::const_iterator table = mBuildingObjects.find(it->first.mTable);
        bool keep = (table != mBuildingObjects.end()) && (table->second->getMeshName() == TAVERN_TABLE_MESH);
        if(keep)
        {
            const Ogre::Vector2 wanted = getSeatPosition(it->first, 1);
            const Ogre::Vector2 placed(it->second->getPosition().x, it->second->getPosition().y);
            keep = (wanted.squaredDistance(placed) < static_cast<float>(DIRECTION_EPSILON)) &&
                (std::abs(static_cast<double>(it->second->getRotationAngle()) - table->second->getRotationAngle()) < ANGLE_EPSILON);
        }
        if(keep)
        {
            ++it;
            continue;
        }

        it->second->removeFromGameMap();
        it->second->deleteYourself();
        it = mStoolObjects.erase(it);
        changed = true;
    }

    // Every table gets a stool at each of its two ends, turned like the table
    for(Tile* table : getTableTiles())
    {
        const double angle = mBuildingObjects.find(table)->second->getRotationAngle();
        for(uint32_t index = TAVERN_SEATS_PER_TABLE; index < TAVERN_PLACES_PER_TABLE; ++index)
        {
            const RoomTavernSeat seat(table, index);
            if(mStoolObjects.find(seat) != mStoolObjects.end())
                continue;

            const Ogre::Vector2 position = getSeatPosition(seat, 1);
            Tile* tile = gameMap->getTile(Helper::round(position.x), Helper::round(position.y));
            if(tile == nullptr)
                continue;

            BuildingObject* stool = new BuildingObject(gameMap, *this, TAVERN_STOOL_MESH, tile, position.x, position.y, 0.0f,
                static_cast<Ogre::Real>(angle), false);
            stool->addToGameMap(gameMap);
            stool->setPosition(stool->getPosition(), gameMap);
            stool->createMesh();
            mStoolObjects[seat] = stool;
            changed = true;
        }
    }

    // A creature on its way may now walk into a stool: it looks for its way again, like for any new room object
    if(changed)
    {
        for(Creature* creature : gameMap->getCreatures())
            creature->checkWalkPathValid(true);
    }
}

void RoomTavern::removeStools()
{
    for(std::pair<const RoomTavernSeat, BuildingObject*>& entry : mStoolObjects)
    {
        entry.second->removeFromGameMap();
        entry.second->deleteYourself();
    }
    mStoolObjects.clear();
}

//! \brief True when the creature is large (a bed of two by two tiles) and takes more than one place.
bool RoomTavern::isLargeGuest(const Creature& creature)
{
    const CreatureDefinition* definition = creature.getDefinition();
    return (definition != nullptr) && (definition->getBedDim1() >= 2) && (definition->getBedDim2() >= 2);
}

//! \brief The number of neighbouring places on a bench the creature needs: 1, or for a large creature as many as its
//! seated width covers.
uint32_t RoomTavern::getPlacesOf(const Creature& creature)
{
    // A stool guest takes its stool, whatever its size
    if(!isLargeGuest(creature) || usesStool(creature))
        return 1;

    // Width of the seated body in tiles, measured on the models (a bench is 1.31 tiles long). The guests share a bench
    // only when everybody fits side by side: with these widths only the dragon leaves room for one more guest, every other
    // large creature sits alone on its bench. A large creature of another model takes the whole bench.
    struct SeatedWidth
    {
        const char* mMesh;
        float mWidth;
    };
    static const SeatedWidth widths[] =
    {
        { "Kreatur.mesh", 1.03f }, { "PitDemon.mesh", 1.11f }, { "Scarab.mesh", 1.18f }, { "Troll.mesh", 1.22f },
        { "Dragon.mesh", 0.78f }
    };
    float width = static_cast<float>(TAVERN_SEATS_PER_BENCH) * TAVERN_SEAT_SPACING;
    const std::string& mesh = creature.getDefinition()->getMeshName();
    for(const SeatedWidth& seated : widths)
    {
        if(mesh == seated.mMesh)
            width = seated.mWidth;
    }

    const uint32_t places = static_cast<uint32_t>(std::ceil(width / TAVERN_SEAT_SPACING - 0.001f));
    return std::min(std::max(places, static_cast<uint32_t>(1)), TAVERN_SEATS_PER_BENCH);
}

//! \brief Picks a free seat for the creature; a table with a guest comes first, then the nearest table.
bool RoomTavern::pickFreeSeat(const Creature& creature, RoomTavernSeat& seat) const
{
    Tile* creatureTile = creature.getPositionTile();
    int32_t bestDistance = std::numeric_limits<int32_t>::max();
    bool bestHasGuest = false;
    bool found = false;
    for(Tile* table : getTableTiles())
    {
        // A table with a guest comes first, so that two guests can play a game
        bool hasGuest = false;
        for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
        {
            if(entry.first.mTable == table)
                hasGuest = true;
        }

        int32_t distance = 0;
        if(creatureTile != nullptr)
        {
            const int32_t dx = table->getX() - creatureTile->getX();
            const int32_t dy = table->getY() - creatureTile->getY();
            distance = dx * dx + dy * dy;
        }

        if(found && (hasGuest == bestHasGuest) && (distance >= bestDistance))
            continue;
        if(found && bestHasGuest && !hasGuest)
            continue;

        // A stool guest looks only at the stools, every other guest only at the benches (isFreeSeatFor)
        for(uint32_t index = 0; index < TAVERN_PLACES_PER_TABLE; ++index)
        {
            if(!isFreeSeatFor(creature, RoomTavernSeat(table, index)))
                continue;

            seat = RoomTavernSeat(table, index);
            found = true;
            bestDistance = distance;
            bestHasGuest = hasGuest;
            break;
        }
    }

    return found;
}

//! \brief Returns where a guest sits on the ground, from the place and rotation of the table.
Ogre::Vector2 RoomTavern::getSeatPosition(const RoomTavernSeat& seat, uint32_t places) const
{
    // The table object stands halfway between its two tiles
    double angle = 0.0;
    Ogre::Vector2 middle(static_cast<Ogre::Real>(seat.mTable->getX()), static_cast<Ogre::Real>(seat.mTable->getY()));
    std::map<Tile*, BuildingObject*>::const_iterator table = mBuildingObjects.find(seat.mTable);
    if(table != mBuildingObjects.end())
    {
        angle = table->second->getRotationAngle();
        middle = Ogre::Vector2(table->second->getPosition().x, table->second->getPosition().y);
    }

    const Ogre::Vector2 offset = seatOffset(seat.mIndex, places, angle);
    return middle + offset;
}

//! \brief Returns the direction on the ground in which a guest on the seat looks across its table.
Ogre::Vector3 RoomTavern::getAcrossTableDirection(const RoomTavernSeat& seat) const
{
    double angleDegrees = 0.0;
    std::map<Tile*, BuildingObject*>::const_iterator table = mBuildingObjects.find(seat.mTable);
    if(table != mBuildingObjects.end())
        angleDegrees = table->second->getRotationAngle();

    // The first bench lies on the +x side of the table, so its guests look towards -x; the second bench looks back
    const double angle = angleDegrees * DEGREES_TO_RADIANS;
    if(isStoolSeat(seat))
    {
        // A stool guest looks along the table to its middle: from the stool on +y towards -y, from the other one back
        const float along = (seat.mIndex == TAVERN_SEATS_PER_TABLE) ? -1.0f : 1.0f;
        return Ogre::Vector3(-along * static_cast<float>(std::sin(angle)), along * static_cast<float>(std::cos(angle)), 0.0f);
    }
    const float across = (seat.mIndex < TAVERN_SEATS_PER_BENCH) ? -1.0f : 1.0f;
    return Ogre::Vector3(across * static_cast<float>(std::cos(angle)), across * static_cast<float>(std::sin(angle)), 0.0f);
}

//! \brief True when the guest is at the place of its seat.
bool RoomTavern::isOnSeat(const Creature& creature, const RoomTavernSeat& seat, uint32_t places) const
{
    const Ogre::Vector2 position = getSeatPosition(seat, places);
    const Ogre::Vector2 current(creature.getPosition().x, creature.getPosition().y);
    return current.squaredDistance(position) < SEAT_REACHED_SQUARED;
}

//! \brief The direction a guest looks in while it plays a game with another guest or slaps it. A seated guest looks
//! straight across its table like in every other seated clip: the clips are made for that direction only, and a body
//! turned on the bench towards a partner further along the table (up to 50 degrees) or on its own bench (90 degrees)
//! pushes its legs and arms through the bench, the pedestal and the table top. A guest that is not on its seat turns
//! to the partner.
Ogre::Vector3 RoomTavern::getFacingDirection(const Creature& creature, const Creature& partner)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator own = findSpotOf(&creature);
    if((own != mSpots.end()) && isOnSeat(creature, own->first, own->second.mPlaces))
        return getAcrossTableDirection(own->first);

    return directionTo(creature, partner.getPosition());
}

//! \brief Finds free points next to the seat from where a creature gets onto the bench.
void RoomTavern::findSeatStagingPoints(Creature& creature, const RoomTavernSeat& seat, uint32_t places,
    std::vector<Ogre::Vector2>& stagingPoints) const
{
    stagingPoints.clear();
    std::map<Tile*, BuildingObject*>::const_iterator table = mBuildingObjects.find(seat.mTable);
    if(table == mBuildingObjects.end())
        return;

    // The table and the stool of the seat are the objects the creature may enter; everything else stays an obstacle
    const std::vector<RoomObjectPath::Obstacle> obstacles = seatObstacles(creature, seat);
    const Ogre::Vector2 target = getSeatPosition(seat, places);
    // Away from the table means across it, not along: the outer places of a long bench lie far from its middle
    const Ogre::Vector3 across = getAcrossTableDirection(seat);
    const Ogre::Vector2 away(-across.x, -across.y);
    const Ogre::Vector2 side(-away.y, away.x);
    const Ogre::Vector2 directions[] = { away, away + side, away - side, side, -side };
    const float distances[] = { RoomObjectNavigation::clearance(creature) + SEAT_STAGING_DISTANCE, SEAT_STAGING_DISTANCE };
    for(float distance : distances)
    {
        for(const Ogre::Vector2& direction : directions)
        {
            const Ogre::Vector2 staging = target + direction.normalisedCopy() * distance;
            Tile* tile = getGameMap()->getTile(Helper::round(staging.x), Helper::round(staging.y));
            if((tile == nullptr) || !creature.canGoThroughTile(tile) ||
               !RoomObjectPath::clearPoint(obstacles, staging) || !RoomObjectPath::clearSegment(obstacles, staging, target))
                continue;

            stagingPoints.push_back(staging);
        }
    }
}

//! \brief Walks the guest around the furniture and onto its seat; the last leg goes straight to the bench.
bool RoomTavern::walkToSeat(Creature& creature, const RoomTavernSeat& seat, uint32_t places)
{
    Tile* creatureTile = creature.getPositionTile();
    if(creatureTile == nullptr)
        return false;

    const Ogre::Vector2 target = getSeatPosition(seat, places);
    std::vector<Ogre::Vector2> route;
    std::vector<Ogre::Vector2> stagingPoints;
    findSeatStagingPoints(creature, seat, places, stagingPoints);
    for(const Ogre::Vector2& staging : stagingPoints)
    {
        std::vector<Ogre::Vector2> path;
        Tile* stagingTile = getGameMap()->getTile(Helper::round(staging.x), Helper::round(staging.y));
        if(stagingTile != creatureTile)
        {
            const std::list<Tile*> tiles = getGameMap()->path(&creature, stagingTile);
            if(tiles.empty())
                continue;
            Creature::tileToVector2(tiles, path, true, 0.0f);
        }
        path.push_back(staging);
        RoomObjectNavigation::refine(creature, path);
        if(path.empty() || !(path.back() == staging))
            continue;

        path.push_back(target);
        route = path;
        break;
    }

    // Without a clear way around the furniture the seat cannot be reached; the guest never walks through furniture
    if(route.empty())
        return false;

    creature.setWalkPath(EntityAnimation::walk_anim, EntityAnimation::sit_anim, true, false, route, false, true);
    creature.pushAction(Utils::make_unique<CreatureActionWalkToTile>(creature));
    return true;
}

//! \brief Lets a guest at the end of its visit step away from the bench, so it never leaves through the furniture.
bool RoomTavern::stepOffSeat(Creature& creature, const RoomTavernSeat& seat, uint32_t places)
{
    std::vector<Ogre::Vector2> stagingPoints;
    findSeatStagingPoints(creature, seat, places, stagingPoints);
    if(stagingPoints.empty())
        return false;

    const std::vector<Ogre::Vector2> route(1, stagingPoints.front());
    creature.setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, route, false, true);
    creature.pushAction(Utils::make_unique<CreatureActionWalkToTile>(creature));
    return true;
}

//! \brief Moves a guest whose seat cannot be reached to another free seat it can walk to.
bool RoomTavern::walkToOtherSeat(Creature& creature, const RoomTavernSeat& seat)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator own = mSpots.find(seat);
    if((own == mSpots.end()) || (own->second.mCreature != &creature))
        return false;

    const uint32_t places = own->second.mPlaces;
    for(Tile* table : getTableTiles())
    {
        for(uint32_t index = 0; index < TAVERN_PLACES_PER_TABLE; ++index)
        {
            const RoomTavernSeat candidate(table, index);
            if((candidate == seat) || !isFreeSeatFor(creature, candidate) || !walkToSeat(creature, candidate, places))
                continue;

            const RoomTavernSpot spot = own->second;
            mSpots.erase(own);
            mSpots.insert(std::make_pair(candidate, spot));
            return true;
        }
    }
    return false;
}

//! \brief Returns another tavern of the keeper that has a seat for the creature and can be reached.
Room* RoomTavern::findOtherTavern(Creature& creature)
{
    Tile* position = creature.getPositionTile();
    if(position == nullptr)
        return nullptr;

    for(Room* room : getGameMap()->getRoomsByTypeAndSeat(RoomType::tavern, creature.getSeat()))
    {
        if((room == this) || (room->numCoveredTiles() <= 0) || !room->hasOpenCreatureSpot(&creature))
            continue;

        Tile* tile = room->getArrivalTile(creature);
        if((tile != nullptr) && getGameMap()->pathExists(&creature, position, tile))
            return room;
    }
    return nullptr;
}

//! \brief Sends a guest this tavern has no seat for away; its action queue must no longer hold a use of this tavern.
void RoomTavern::sendToOtherTavernOrWork(Creature& creature, Room* otherTavern)
{
    if(otherTavern != nullptr)
        creature.pushAction(Utils::make_unique<CreatureActionUseRoom>(creature, *otherTavern, false));
    else
        creature.startTavernCooldown();
}

std::map<RoomTavernSeat, RoomTavernSpot>::iterator RoomTavern::findSpotOf(const Creature* creature)
{
    for(std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if(it->second.mCreature == creature)
            return it;
    }

    return mSpots.end();
}

//! \brief All guests stand up and look for a free seat again by the normal rule.
void RoomTavern::standUpGuests()
{
    // Running games end without a winner and without effects
    mGames.clear();

    std::vector<RoomTavernSpot> guests;
    for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
        guests.push_back(entry.second);
    mSpots.clear();

    const bool hasBlock = hasTavernBlock(mCoveredTiles);
    std::vector<Creature*> withoutSeat;
    for(RoomTavernSpot& guest : guests)
    {
        RoomTavernSeat seat;
        if(!hasBlock || !pickFreeSeat(*guest.mCreature, seat))
        {
            withoutSeat.push_back(guest.mCreature);
            continue;
        }

        // A guest that was drinking or playing sits down again; a guest whose visit was over only passes through its seat to leave
        const bool visitOver = guest.mSleepAfter ||
            ((guest.mState != TavernGuestState::arriving) && (guest.mState != TavernGuestState::drinking) &&
             (guest.mState != TavernGuestState::game));
        guest.mPlaces = getPlacesOf(*guest.mCreature);
        // A player of the game that ended looks for a new game from its seat and orders nothing for it
        guest.mWantsGame = !visitOver && (guest.mState == TavernGuestState::game);
        guest.mLeftSeat = false;
        guest.mState = visitOver ? TavernGuestState::done : TavernGuestState::arriving;
        guest.mTurnsLeft = 0;
        std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.insert(std::make_pair(seat, guest)).first;
        showSpotState(seat.mTable, it->second);
    }

    // Clearing the actions releases the guest from the room, so they are handled after the loop
    for(Creature* creature : withoutSeat)
    {
        Room* otherTavern = findOtherTavern(*creature);
        creature->clearActionQueue();
        sendToOtherTavernOrWork(*creature, otherTavern);
    }
}

//! \brief Assigns a guest a tavern spot and restores its saved state.
bool RoomTavern::addCreatureUsingRoom(Creature* creature)
{
    if((creature == nullptr) || !hasTavernBlock(mCoveredTiles))
        return false;

    // The seat the creature had when the room was saved, if it is still free
    const uint32_t places = getPlacesOf(*creature);
    const std::vector<Tile*> tables = getTableTiles();
    RoomTavernSeat seat;
    std::map<std::string, RoomTavernPendingSpot>::iterator pending = mPendingSpots.find(creature->getName());
    if((pending != mPendingSpots.end()) && isFreeSeatFor(*creature, pending->second.mSeat) &&
       (std::find(tables.begin(), tables.end(), pending->second.mSeat.mTable) != tables.end()))
    {
        seat = pending->second.mSeat;
    }
    else if(!pickFreeSeat(*creature, seat))
    {
        return false;
    }

    if(!Room::addCreatureUsingRoom(creature))
        return false;

    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.insert(std::make_pair(seat, RoomTavernSpot(creature))).first;
    it->second.mPlaces = places;

    // A creature that is not thirsty comes for a leisure visit, which counts toward PleasureVisitMax and ends with the
    // pleasure buff and the tavern lock; a thirsty one comes for a drink and gets neither. A visit saved with the
    // creature goes on with the gain it had
    if((pending == mPendingSpots.end()) && (creature->getThirst() < getTavernValue("ThirstSeek")))
        creature->beginPleasureVisit(PleasureRoomKind::tavern);

    if(pending != mPendingSpots.end())
    {
        it->second.mState = pending->second.mState;
        it->second.mTurnsLeft = pending->second.mTurnsLeft;
        it->second.mDrinks = pending->second.mDrinks;
        it->second.mSleepAfter = pending->second.mSleepAfter;
        it->second.mWantsGame = pending->second.mWantsGame;
        // A guest that lost its saved seat walks to the new one before it drinks again
        if(!(seat == pending->second.mSeat) && (it->second.mState == TavernGuestState::drinking))
            setSpotState(it->second, TavernGuestState::arriving, 0);
        mPendingSpots.erase(pending);
        showSpotState(seat.mTable, it->second);
    }

    return true;
}

void RoomTavern::removeCreatureUsingRoom(Creature* creature)
{
    Room::removeCreatureUsingRoom(creature);

    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = findSpotOf(creature);
    if(it == mSpots.end())
        return;

    // The place goes first: the creature may be on its way out of the game (dead, removed), so its clips are not touched here.
    // Whatever clip it still shows is replaced by the next thing it does. A leisure visit ends: a visit that gained mood
    // gives the pleasure buff, and the tavern is closed to the creature (also after a visit that gained nothing), so that
    // the job search does not send it back in at once while it still stands on a tavern tile. A drink visit gives neither
    // buff nor lock; a thirsty guest that was stopped before its first drink keeps looking for a drink.
    it->second.mCreature->finishPleasureVisit(PleasureRoomKind::tavern, true);
    mSpots.erase(it);

    // A game of the guest ends without effects; its partner is done
    std::map<RoomTavernSeat, RoomTavernGame>::iterator game = mGames.begin();
    while(game != mGames.end())
    {
        if((game->second.mCreatureA == creature) || (game->second.mCreatureB == creature))
        {
            abortGame(game);
            game = mGames.begin();
            continue;
        }
        ++game;
    }
}

//! \brief Returns whether this guest is arriving for a drink or drinking.
bool RoomTavern::isGuestDrinking(const Creature& creature)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    return it != mSpots.end() && (it->second.mState == TavernGuestState::arriving ||
        it->second.mState == TavernGuestState::drinking);
}

bool RoomTavern::shouldStopUseIfHungrySleepy(Creature& creature, bool forced)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    if(it == mSpots.end())
        return true;

    const TavernGuestState state = it->second.mState;
    return (state != TavernGuestState::game) && (state != TavernGuestState::ko) && (state != TavernGuestState::getUp);
}

bool RoomTavern::shouldNotUseIfBadMood(Creature& creature, bool forced)
{
    return shouldStopUseIfHungrySleepy(creature, forced);
}

bool RoomTavern::keepGuestUntilItLeft(Creature& creature)
{
    // Only a guest on its bench is held: one that stands on the floor may go at once
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    if((it == mSpots.end()) || it->second.mLeftSeat || !creature.getIsOnMap() ||
       !isOnSeat(creature, it->first, it->second.mPlaces))
        return false;

    // The loser of a slap duel that slumps on its seat gets up first, then it is done and gets off the bench
    if((it->second.mState == TavernGuestState::ko) || (it->second.mState == TavernGuestState::getUp))
        return true;

    // A game of the guest ends without effects; both players are done then
    for(std::map<RoomTavernSeat, RoomTavernGame>::iterator game = mGames.begin(); game != mGames.end(); ++game)
    {
        if((game->second.mCreatureA == &creature) || (game->second.mCreatureB == &creature))
        {
            abortGame(game);
            break;
        }
    }

    // The visit is over: no further drink, no wait for a game; useRoom steps the guest off its bench and lets it go
    RoomTavernSpot& spot = it->second;
    if((spot.mState != TavernGuestState::done) || (spot.mTurnsLeft > 0) || spot.mWantsGame)
        setSpotDone(spot, 0);
    return true;
}

bool RoomTavern::useRoom(Creature& creature, bool forced)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    if(it == mSpots.end())
    {
        OD_LOG_ERR("room=" + getName() + ", creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    const RoomTavernSeat seat = it->first;
    RoomTavernSpot& spot = it->second;
    switch(spot.mState)
    {
        case TavernGuestState::arriving:
        {
            // Walk to the seat; the walk is an action on top of this one, so we are called again when it is over
            if(!isOnSeat(creature, seat, spot.mPlaces))
            {
                if(!creature.isMoving() && !walkToSeat(creature, seat, spot.mPlaces) && !walkToOtherSeat(creature, seat))
                {
                    // No seat of this room can be reached: another tavern of the keeper, otherwise back to work
                    Room* otherTavern = findOtherTavern(creature);
                    creature.popAction();
                    sendToOtherTavernOrWork(creature, otherTavern);
                    return true;
                }
                return false;
            }

            // A player whose game ended when the room changed goes on looking for a game, without a further drink
            if(spot.mWantsGame)
            {
                setSpotState(spot, TavernGuestState::done, DONE_WAIT_TURNS);
                showSpotState(seat.mTable, spot);
                return false;
            }

            // On the seat the first drink starts
            setSpotState(spot, TavernGuestState::drinking, nextDrinkTurns(creature));
            showSpotState(seat.mTable, spot);
            return false;
        }
        case TavernGuestState::done:
        {
            // The guest waits until the room has let the turns of the state pass
            if(spot.mTurnsLeft > 0)
                return false;

            // The guest gets off the bench before it leaves, so it does not walk through the table. While furniture
            // closes in its seat it stays seated and tries again in the next turn
            if(!spot.mLeftSeat)
            {
                if(isOnSeat(creature, seat, spot.mPlaces))
                {
                    if(stepOffSeat(creature, seat, spot.mPlaces))
                        spot.mLeftSeat = true;
                    return false;
                }
                spot.mLeftSeat = true;
            }

            // The visit is over. The loser of a slap duel goes to its bed, whatever its wakefulness
            const bool goToBed = spot.mSleepAfter && (creature.getHomeTile() != nullptr);
            creature.popAction();
            if(goToBed)
                creature.pushAction(Utils::make_unique<CreatureActionSleep>(creature));
            return true;
        }
        default:
            // drinking, game, ko and getUp are run by doUpkeep
            return false;
    }
}

void RoomTavern::setSpotState(RoomTavernSpot& spot, TavernGuestState state, int32_t turns)
{
    spot.mState = state;
    spot.mTurnsLeft = turns;
}

void RoomTavern::setSpotDone(RoomTavernSpot& spot, int32_t turns)
{
    setSpotState(spot, TavernGuestState::done, turns);
    spot.mWantsGame = false;
    showSpotState(nullptr, spot);
}

//! \brief Shows the clip of the state of a guest, seated while it is on its seat and turned towards what it looks at.
void RoomTavern::showSpotState(Tile* tile, RoomTavernSpot& spot)
{
    Creature* creature = spot.mCreature;
    if((creature == nullptr) || !creature->getIsOnMap())
        return;

    std::map<RoomTavernSeat, RoomTavernSpot>::iterator own = findSpotOf(creature);
    const bool seated = (own != mSpots.end()) && isOnSeat(*creature, own->first, spot.mPlaces);
    // A seated guest looks straight across its table, wherever it sits along the bench
    Ogre::Vector3 towardsTable = Ogre::Vector3::ZERO;
    if(seated)
        towardsTable = getAcrossTableDirection(own->first);

    switch(spot.mState)
    {
        case TavernGuestState::drinking:
            // The seated drink clip is made for the bench: a guest that is not on its seat drinks standing
            if(seated)
                creature->setAnimationState(EntityAnimation::sit_drink_anim, true, towardsTable, false);
            else
                creature->setAnimationState(EntityAnimation::drink_anim, true);
            break;
        case TavernGuestState::ko:
            // Without a free floor tile the loser stays on its seat
            if(seated)
                creature->setAnimationState(EntityAnimation::sit_slumped_anim, true, towardsTable, false);
            else
                creature->setAnimationState(EntityAnimation::knockedout_anim, true, Ogre::Vector3::ZERO, false);
            break;
        case TavernGuestState::getUp:
            if(seated)
                creature->setAnimationState(EntityAnimation::sit_anim, true, towardsTable, false);
            else
                creature->setAnimationState(EntityAnimation::getup_anim, false, Ogre::Vector3::ZERO, false);
            break;
        case TavernGuestState::game:
        {
            // The clip of the game, turned towards the opponent
            for(std::map<RoomTavernSeat, RoomTavernGame>::iterator it = mGames.begin(); it != mGames.end(); ++it)
            {
                RoomTavernGame& game = it->second;
                Creature* opponent = nullptr;
                if(game.mCreatureA == creature)
                    opponent = game.mCreatureB;
                else if(game.mCreatureB == creature)
                    opponent = game.mCreatureA;
                if(opponent == nullptr)
                    continue;

                std::string clip = EntityAnimation::sit_anim;
                if(game.mKind == TavernGameKind::armWrestling)
                    clip = EntityAnimation::sit_armwrestle_anim;
                else if(game.mKind == TavernGameKind::dice)
                    clip = EntityAnimation::sit_dice_anim;
                creature->setAnimationState(clip, true, getFacingDirection(*creature, *opponent), false);
                break;
            }
            break;
        }
        default:
            if(seated)
                creature->setAnimationState(EntityAnimation::sit_anim, true, towardsTable, false);
            else
                creature->setAnimationState(EntityAnimation::idle_anim, true);
            break;
    }
}

bool RoomTavern::isGuestDisturbed(const Creature& creature)
{
    if(!creature.getIsOnMap() || !creature.isAlive() || creature.isKo() || creature.isBeingDragged())
        return true;

    return creature.isActionInList(CreatureActionType::fight) ||
        creature.isActionInList(CreatureActionType::fightFriendly) ||
        creature.isActionInList(CreatureActionType::flee);
}

void RoomTavern::playSoundAt(Tile* tile, const std::string& family)
{
    if(tile == nullptr)
        return;

    for(Seat* seat : tile->getSeatsWithVision())
    {
        if((seat->getPlayer() == nullptr) || !seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* serverNotification = new ServerNotification(
            ServerNotificationType::playSpatialSound, seat->getPlayer());
        serverNotification->mPacket << family << tile->getX() << tile->getY();
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

void RoomTavern::doUpkeep()
{
    Room::doUpkeep();

    if(!getIsOnServerMap())
        return;

    resumeLoadedGuests();
    reseatGuestsAtLostTables();
    abortDisturbedGuests();
    upkeepGames();
    upkeepSpots();

    // A guest that wants a game and waits for a partner at its table looks for one again every turn
    for(std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if((it->second.mState == TavernGuestState::done) && it->second.mWantsGame && (it->second.mTurnsLeft > 0))
            tryStartGame(it->first);
    }

    // A guest that is done is looked for by a partner during these turns only. A guest that wants a game keeps waiting
    // while another guest of its keeper drinks at its table (D5: a game when a second creature is in the tavern)
    for(std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if((it->second.mState == TavernGuestState::done) && (it->second.mTurnsLeft > 0) &&
           !(it->second.mWantsGame && hasDrinkingTableMate(it->first)))
            --it->second.mTurnsLeft;
    }
}

//! \brief A guest whose table is gone gets up with the others and looks for a seat again.
void RoomTavern::reseatGuestsAtLostTables()
{
    const std::vector<Tile*> tables = getTableTiles();
    for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
    {
        if(std::find(tables.begin(), tables.end(), entry.first.mTable) != tables.end())
            continue;

        standUpGuests();
        return;
    }
}

void RoomTavern::abortDisturbedGuests()
{
    // A fight, a flight, a knock-out or a hand that takes a guest away ends its game without effects
    std::map<RoomTavernSeat, RoomTavernGame>::iterator game = mGames.begin();
    while(game != mGames.end())
    {
        if(isGuestDisturbed(*game->second.mCreatureA) || isGuestDisturbed(*game->second.mCreatureB))
        {
            abortGame(game);
            game = mGames.begin();
            continue;
        }
        ++game;
    }

    // A fight nearby ends the lying at once: the guest gets up and does not go to bed
    for(std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        RoomTavernSpot& spot = it->second;
        if((spot.mState != TavernGuestState::ko) && (spot.mState != TavernGuestState::getUp))
            continue;

        if(!isGuestDisturbed(*spot.mCreature))
            continue;

        spot.mSleepAfter = false;
        setSpotDone(spot, 0);
    }
}

void RoomTavern::upkeepSpots()
{
    for(std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        RoomTavernSpot& spot = it->second;
        switch(spot.mState)
        {
            case TavernGuestState::drinking:
            {
                --spot.mTurnsLeft;
                if(spot.mTurnsLeft <= 0)
                    finishDrink(it->first.mTable, spot);
                break;
            }
            case TavernGuestState::ko:
            {
                --spot.mTurnsLeft;
                if(spot.mTurnsLeft <= 0)
                {
                    setSpotState(spot, TavernGuestState::getUp, getUpTurns());
                    showSpotState(it->first.mTable, spot);
                }
                break;
            }
            case TavernGuestState::getUp:
            {
                --spot.mTurnsLeft;
                if(spot.mTurnsLeft <= 0)
                    setSpotDone(spot, 0);
                break;
            }
            default:
                break;
        }
    }
}

bool RoomTavern::payForBeer(Creature& creature, bool& noCoin)
{
    noCoin = false;
    const int32_t price = static_cast<int32_t>(std::floor(getTavernValue("BeerPrice") + 0.5));
    if(mPayer == TavernPayer::keeper)
        return getGameMap()->withdrawFromTreasuries(price, getSeat());

    if(creature.getGoldCarried() >= price)
    {
        creature.addGoldCarried(-price);
        getGameMap()->addGoldToSeat(price, getSeat()->getId());
        return true;
    }

    noCoin = true;
    return false;
}

//! \brief The turns the next drink of the guest lasts: a beer BeerDrinkTurns (30 seconds), water WaterDrinkTurns (10 seconds). A beer is
//! expected when the tavern serves beer and whoever pays has the price at hand; the drink is paid when it is finished.
int32_t RoomTavern::nextDrinkTurns(const Creature& creature) const
{
    const double price = std::floor(getTavernValue("BeerPrice") + 0.5);
    bool beer = servesBeer();
    if(beer && (mPayer == TavernPayer::keeper))
        beer = (getSeat() != nullptr) && (getSeat()->getGold() >= price);
    else if(beer)
        beer = creature.getGoldCarried() >= price;

    const int32_t turns = static_cast<int32_t>(std::floor(getTavernValue(beer ? "BeerDrinkTurns" : "WaterDrinkTurns") + 0.5));
    return std::max(turns, static_cast<int32_t>(1));
}

//! \brief True while another guest of the same keeper sits at the table of the seat and drinks: a guest that wants a
//! game waits for it, since it is done after this drink at the latest.
bool RoomTavern::hasDrinkingTableMate(const RoomTavernSeat& seat) const
{
    std::map<RoomTavernSeat, RoomTavernSpot>::const_iterator own = mSpots.find(seat);
    if(own == mSpots.end())
        return false;

    for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
    {
        if((entry.first.mTable != seat.mTable) || (entry.first == seat) || (entry.second.mCreature == nullptr))
            continue;

        if((entry.second.mState == TavernGuestState::drinking) &&
           (entry.second.mCreature->getSeat() == own->second.mCreature->getSeat()))
            return true;
    }
    return false;
}

//! \brief Finishes a drink and chooses the guest's next tavern activity.
void RoomTavern::finishDrink(Tile* tile, RoomTavernSpot& spot)
{
    Creature* creature = spot.mCreature;
    DrinkKind kind = DrinkKind::water;
    bool noCoin = false;
    if(servesBeer() && payForBeer(*creature, noCoin))
        kind = DrinkKind::beer;

    creature->drinkTaken(kind);
    if(kind == DrinkKind::beer)
        creature->addTavernMood(getTavernValue("BeerMood"));
    else if(noCoin)
        creature->addTavernMood(getTavernValue("NoCoinMood"));

    sendTavernEvent(*creature, static_cast<int32_t>((kind == DrinkKind::beer) ? CosmeticTavernKind::beer : CosmeticTavernKind::water), nullptr);
    addDrinkDirt(tile);
    if(mInnkeeper != nullptr)
        mInnkeeper->onDrink();
    playSoundAt(tile, SOUND_POUR);
    ++spot.mDrinks;

    // A leisure visit that has gained PleasureVisitMax ends here: no further drink and no game
    if(creature->isPleasureVisitFull(PleasureRoomKind::tavern))
    {
        setSpotDone(spot, DONE_WAIT_TURNS);
        return;
    }

    // The guest decides itself about another drink: 50, 25, 12.5 and 6.25 percent after the 1st to the 4th drink,
    // never more than MaxDrinksPerVisit
    if(spot.mDrinks < static_cast<uint32_t>(getTavernValue("MaxDrinksPerVisit")))
    {
        const double nextDrinkPercent = getTavernValue("NextDrinkPercent") /
            std::pow(ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("TavernDrinkChainHalving", 2.0), static_cast<double>(spot.mDrinks - 1));
        if(Random::Double(0.0, PERCENT_SCALE) < nextDrinkPercent)
        {
            setSpotState(spot, TavernGuestState::drinking, nextDrinkTurns(*creature));
            showSpotState(tile, spot);
            return;
        }
    }

    // The guest can find a game partner during this turn before the visit ends
    setSpotDone(spot, DONE_WAIT_TURNS);
    if(Random::Double(0.0, PERCENT_SCALE) < getTavernValue("GameChancePercent"))
    {
        spot.mWantsGame = true;
        std::map<RoomTavernSeat, RoomTavernSpot>::iterator own = findSpotOf(creature);
        if(own != mSpots.end())
            tryStartGame(own->first);
    }
}

//! \brief Lets the guest that wants a game start it with a guest of the same table.
void RoomTavern::tryStartGame(const RoomTavernSeat& seat)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator own = mSpots.find(seat);
    if((own == mSpots.end()) || !own->second.mWantsGame)
        return;

    // A guest at the same table that is done too (and waits for the turns to pass) and of the same seat of the keeper;
    // one on the opposite bench (or, from a stool, on the other stool) comes first, so that the two can face each other
    std::vector<RoomTavernSeat> partners;
    std::vector<RoomTavernSeat> oppositePartners;
    for(uint32_t index = 0; index < TAVERN_PLACES_PER_TABLE; ++index)
    {
        if(index == seat.mIndex)
            continue;

        const RoomTavernSeat otherSeat(seat.mTable, index);
        std::map<RoomTavernSeat, RoomTavernSpot>::iterator other = mSpots.find(otherSeat);
        if(other == mSpots.end())
            continue;

        if((other->second.mState != TavernGuestState::done) || (other->second.mTurnsLeft <= 0))
            continue;

        if(other->second.mCreature->getSeat() != own->second.mCreature->getSeat())
            continue;

        const uint32_t ownSide = seatSide(seat.mIndex);
        const uint32_t otherSide = seatSide(index);
        if((ownSide != otherSide) && ((ownSide < 2) == (otherSide < 2)))
            oppositePartners.push_back(otherSeat);
        else
            partners.push_back(otherSeat);
    }

    if(!oppositePartners.empty())
        partners = oppositePartners;

    if(partners.empty())
        return;

    startGame(seat, partners[Random::Uint(0, static_cast<uint32_t>(partners.size()) - 1)]);
}

//! \brief Starts a tavern game using the available game kinds and configured duel limit.
void RoomTavern::startGame(const RoomTavernSeat& seatA, const RoomTavernSeat& seatB)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotA = mSpots.find(seatA);
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotB = mSpots.find(seatB);
    if((spotA == mSpots.end()) || (spotB == mSpots.end()))
        return;

    // Duels and games take place only at one table
    if(!(seatA.mTable == seatB.mTable))
        return;

    // Arm wrestling and dice with the same chance; the slap duel joins the draw when beer is served
    const uint32_t nbGames = servesBeer() ? NB_GAMES_WITH_BEER : NB_GAMES_WITHOUT_BEER;
    RoomTavernGame game;
    game.mKind = static_cast<TavernGameKind>(Random::Uint(0, nbGames - 1));
    game.mSeatA = seatA;
    game.mSeatB = seatB;
    game.mCreatureA = spotA->second.mCreature;
    game.mCreatureB = spotB->second.mCreature;
    game.mTurnIsA = true;
    // A slap duel counts slaps (each of them 4 to 10 s with a pause after it), the other games count turns
    if(game.mKind == TavernGameKind::slapDuel)
        game.mTurnsLeft = static_cast<int32_t>(ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("TavernDuelMaxTurnsFactor", 4.0) * getTavernValue("GameTurns"));
    else
        game.mTurnsLeft = static_cast<int32_t>(getTavernValue("GameTurns"));
    mGames[seatA] = game;

    spotA->second.mWantsGame = false;
    spotB->second.mWantsGame = false;
    setSpotState(spotA->second, TavernGuestState::game, 0);
    setSpotState(spotB->second, TavernGuestState::game, 0);
    showSpotState(seatA.mTable, spotA->second);
    showSpotState(seatB.mTable, spotB->second);
}

void RoomTavern::upkeepGames()
{
    std::map<RoomTavernSeat, RoomTavernGame>::iterator it = mGames.begin();
    while(it != mGames.end())
    {
        // A game that ends erases itself, so the next entry is taken first
        std::map<RoomTavernSeat, RoomTavernGame>::iterator current = it;
        ++it;
        if(current->second.mKind == TavernGameKind::slapDuel)
            playDuelTurn(current);
        else
            playContestTurn(current);
    }
}

void RoomTavern::playContestTurn(std::map<RoomTavernSeat, RoomTavernGame>::iterator it)
{
    RoomTavernGame& game = it->second;
    --game.mTurnsLeft;
    if(game.mTurnsLeft > 0)
        return;

    // The weaker creature wins with 50 percent minus 2.5 points per level of difference, never below 5 percent
    Creature* lower = game.mCreatureA;
    Creature* higher = game.mCreatureB;
    if(lower->getLevel() > higher->getLevel())
        std::swap(lower, higher);

    const uint32_t levelDifference = higher->getLevel() - lower->getLevel();
    const double lowerPercent = std::max(getTavernValue("GameUnderdogMinPercent"),
        getTavernValue("GameUnderdogBasePercent") - getTavernValue("GameUnderdogPerLevel") * levelDifference);
    if(Random::Double(0.0, PERCENT_SCALE) < lowerPercent)
        concludeGame(it, lower, levelDifference);
    else
        concludeGame(it, higher, 0);
}

//! \brief Plays one turn of a slap duel. One slap (wind-up, slap, reaction) lasts TavernSlapSecondsMin to
//! TavernSlapSecondsMax seconds, drawn for every slap; the seated slapper's clip takes the whole slap, the hand lands
//! when half of it is left and the other guest reels for the rest. Then a pause of TavernSlapPauseSecondsMin to
//! TavernSlapPauseSecondsMax seconds, drawn for every pause, and the other guest slaps (decisions 856 and 858).
void RoomTavern::playDuelTurn(std::map<RoomTavernSeat, RoomTavernGame>::iterator it)
{
    RoomTavernGame& game = it->second;
    RoomTavernDuelClock& clock = game.mDuelClock;
    Creature* slapper = game.mTurnIsA ? game.mCreatureA : game.mCreatureB;
    Creature* target = game.mTurnIsA ? game.mCreatureB : game.mCreatureA;
    uint32_t& targetSlaps = game.mTurnIsA ? game.mSlapsTakenB : game.mSlapsTakenA;

    // The pause after a slap runs out; then the next slap starts in the same turn
    if(clock.mPhase == TavernDuelPhase::pause)
    {
        --clock.mTurnsLeft;
        if(clock.mTurnsLeft > 0)
            return;

        clock.mPhase = TavernDuelPhase::none;
    }

    // A new slap: its length is drawn and the slapper's clip is stretched to it
    if(clock.mPhase == TavernDuelPhase::none)
    {
        clock.mPhase = TavernDuelPhase::slap;
        clock.mSlapTurns = randomDuelTurns("TavernSlapSecondsMin", "TavernSlapSecondsMax");
        clock.mTurnsLeft = clock.mSlapTurns;
        clock.mSlapResult = TavernSlapResult::open;
        slapper->setTimedAnimationState(EntityAnimation::sit_slap_anim,
            static_cast<double>(clock.mSlapTurns) / ODApplication::turnsPerSecond, false,
            getFacingDirection(*slapper, *target), false);
        return;
    }

    // The slap runs; the hand lands when half of it is left, a miss does nothing
    --clock.mTurnsLeft;
    if((clock.mSlapResult == TavernSlapResult::open) && (clock.mTurnsLeft <= clock.mSlapTurns / 2))
    {
        playSoundAt(slapper->getPositionTile(), SOUND_SLAP);
        clock.mSlapResult = TavernSlapResult::miss;
        if(target->rollAttackHit(slapper->getAttackRating(), slapper->getLevel(), slapper->isPossessed()))
        {
            // The target reels for the rest of the slap
            target->setTimedAnimationState(EntityAnimation::sit_slapped_anim,
                static_cast<double>(std::max(clock.mTurnsLeft, 1)) / ODApplication::turnsPerSecond, false,
                getFacingDirection(*target, *slapper), false);
            // A critical slap (10 percent at equal level, 0.25 points per level of difference) wins the duel when the
            // slap is over
            const double levelDifference = static_cast<double>(slapper->getLevel()) - static_cast<double>(target->getLevel());
            const double criticalPercent = getTavernValue("SlapCritBasePercent") +
                getTavernValue("SlapCritPerLevel") * levelDifference;
            if(Random::Double(0.0, PERCENT_SCALE) < criticalPercent)
                clock.mSlapResult = TavernSlapResult::critical;
            else
            {
                // A normal slap takes SlapDamage hit points but never the last one
                clock.mSlapResult = TavernSlapResult::hit;
                const double damage = std::max(0.0, std::min(getTavernValue("SlapDamage"), target->getHP() - 1.0));
                target->takeDamage(slapper, damage, 0.0, 0.0, 0.0, target->getPositionTile(), false);
                ++targetSlaps;
            }
        }
    }
    if(clock.mTurnsLeft > 0)
        return;

    // The slap and the reaction are over: a critical slap or a target below SlapDuelLoseBelowHp decides the duel
    const TavernSlapResult result = clock.mSlapResult;
    clock.mPhase = TavernDuelPhase::none;
    clock.mSlapTurns = 0;
    clock.mSlapResult = TavernSlapResult::open;
    if((result == TavernSlapResult::critical) ||
       ((result == TavernSlapResult::hit) && (target->getHP() < getTavernValue("SlapDuelLoseBelowHp"))))
    {
        concludeGame(it, slapper, 0);
        return;
    }

    // The other guest slaps after the pause; mTurnsLeft counts the slaps the duel may still last
    game.mTurnIsA = !game.mTurnIsA;
    --game.mTurnsLeft;
    if(game.mTurnsLeft > 0)
    {
        clock.mPhase = TavernDuelPhase::pause;
        clock.mTurnsLeft = randomDuelTurns("TavernSlapPauseSecondsMin", "TavernSlapPauseSecondsMax");
        // Both sit and face each other during the pause
        std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotA = findSpotOf(game.mCreatureA);
        if(spotA != mSpots.end())
            showSpotState(spotA->first.mTable, spotA->second);
        std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotB = findSpotOf(game.mCreatureB);
        if(spotB != mSpots.end())
            showSpotState(spotB->first.mTable, spotB->second);
        return;
    }

    // No decision: the one with more hit points left wins, a tie is decided by chance
    Creature* winner = game.mCreatureA;
    if(game.mCreatureB->getHP() > game.mCreatureA->getHP())
        winner = game.mCreatureB;
    else if((game.mCreatureB->getHP() == game.mCreatureA->getHP()) && (Random::Uint(0, 1) == 1))
        winner = game.mCreatureB;
    concludeGame(it, winner, 0);
}

void RoomTavern::cheerSpectators(const RoomTavernGame& game)
{
    const int32_t radius = static_cast<int32_t>(getTavernValue("GameSpectatorRadius"));
    for(Creature* creature : getGameMap()->getCreaturesBySeat(getSeat()))
    {
        if((creature == game.mCreatureA) || (creature == game.mCreatureB) || creature->isPossessed() ||
           !creature->getIsOnMap() || !creature->isAlive())
            continue;

        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;

        // Within the radius (Chebyshev distance) of one of the two players, from where each of them sits
        Tile* tileA = game.mCreatureA->getPositionTile();
        Tile* tileB = game.mCreatureB->getPositionTile();
        if((tileA == nullptr) || (tileB == nullptr))
            continue;

        const int32_t distanceA = std::max(std::abs(tile->getX() - tileA->getX()),
            std::abs(tile->getY() - tileA->getY()));
        const int32_t distanceB = std::max(std::abs(tile->getX() - tileB->getX()),
            std::abs(tile->getY() - tileB->getY()));
        if(std::min(distanceA, distanceB) <= radius)
            creature->addTavernMood(getTavernValue("GameSpectatorMood"));
    }
}

void RoomTavern::concludeGame(std::map<RoomTavernSeat, RoomTavernGame>::iterator it, Creature* winner, uint32_t underdogLevels)
{
    RoomTavernGame game = it->second;
    mGames.erase(it);

    Creature* loser = (winner == game.mCreatureA) ? game.mCreatureB : game.mCreatureA;
    double winnerMood = getTavernValue("GameWinnerMood");
    double winnerXp = getTavernValue("GameWinnerXp");
    if(underdogLevels > 0)
    {
        // The weaker creature that wins gets more mood and double experience
        winnerMood = std::min(getTavernValue("GameUnderdogMoodMax"),
            winnerMood + getTavernValue("GameUnderdogMoodPerLevel") * underdogLevels);
        winnerXp *= 2.0;
    }
    winner->addTavernMood(winnerMood);
    winner->receiveExp(winnerXp);
    cheerSpectators(game);

    // Only a slap duel is told to the clients (bubbles and posts of the winner and the loser)
    if(game.mKind == TavernGameKind::slapDuel)
    {
        sendTavernEvent(*winner, static_cast<int32_t>(CosmeticTavernKind::duelWon), loser);
        sendTavernEvent(*loser, static_cast<int32_t>(CosmeticTavernKind::duelLost), winner);
    }

    if(mInnkeeper != nullptr)
        mInnkeeper->onCheer();
    playSoundAt(mCounterTile, SOUND_CHEER);

    // Both players are done; the loser of a slap duel goes down
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator winnerSpot = findSpotOf(winner);
    if(winnerSpot != mSpots.end())
        setSpotDone(winnerSpot->second, 0);

    std::map<RoomTavernSeat, RoomTavernSpot>::iterator loserSpot = findSpotOf(loser);
    if(loserSpot == mSpots.end())
        return;

    if(game.mKind == TavernGameKind::slapDuel)
    {
        loser->addTavernMood(getTavernValue("GameLoserMood"));
        knockOut(loserSpot->second);
    }
    else
    {
        setSpotDone(loserSpot->second, 0);
    }
}

void RoomTavern::abortGame(std::map<RoomTavernSeat, RoomTavernGame>::iterator it)
{
    RoomTavernGame game = it->second;
    mGames.erase(it);

    // Both guests are done; one of them may have left the room already
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotA = findSpotOf(game.mCreatureA);
    if(spotA != mSpots.end())
        setSpotDone(spotA->second, 0);

    std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotB = findSpotOf(game.mCreatureB);
    if(spotB != mSpots.end())
        setSpotDone(spotB->second, 0);
}

void RoomTavern::knockOut(RoomTavernSpot& spot)
{
    spot.mSleepAfter = true;
    // Decision 897: the loser lies exactly DuelKoTurns turns (42 turns, 30 s). The knock-out comes from upkeepGames, and
    // upkeepSpots counts the same turn down right after it, so the count starts one turn higher
    setSpotState(spot, TavernGuestState::ko, static_cast<int32_t>(getTavernValue("DuelKoTurns")) + KNOCK_OUT_TURN);
    if(!fallNextToBench(spot))
        showSpotState(nullptr, spot);
}

//! \brief The loser of a slap duel falls from its bench onto a free floor tile next to its seat.
bool RoomTavern::fallNextToBench(RoomTavernSpot& spot)
{
    Creature* creature = spot.mCreature;
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator own = findSpotOf(creature);
    if((creature == nullptr) || (own == mSpots.end()) || !creature->getIsOnMap())
        return false;

    // The free floor tile nearest to the seat: part of the room, without furniture, and no other loser lies on it.
    // The way there may leave the own bench but never crosses other furniture, and the loser never lands in furniture.
    const Ogre::Vector2 position = getSeatPosition(own->first, spot.mPlaces);
    std::map<Tile*, BuildingObject*>::const_iterator ownTable = mBuildingObjects.find(own->first.mTable);
    if(ownTable == mBuildingObjects.end())
        return false;
    // The tiles around the seat; the table is two tiles long, so the seat may lie on either of its tiles
    const int32_t seatX = Helper::round(position.x);
    const int32_t seatY = Helper::round(position.y);
    // A large guest finds no floor between the tables that its lying body fits on: it slumps on its seat
    if(isLargeGuest(*creature))
        return false;

    // The floor the lying body covers (decision 833): the loser looks towards its seat when it goes down, so its body lies
    // on the side away from the table; that whole stretch must stay clear of every piece of furniture
    const TavernLyingBody* body = &TAVERN_LYING_BODY_DEFAULT;
    for(const TavernLyingBody& entry : TAVERN_LYING_BODIES)
    {
        if(creature->getDefinition()->getMeshName() == entry.mMesh)
            body = &entry;
    }
    const float scale = static_cast<float>(creature->getLevelScale());
    const std::vector<RoomObjectPath::Obstacle> lying = RoomObjectNavigation::collect(*getGameMap(), body->mHalfWidth * scale);
    const std::vector<RoomObjectPath::Obstacle> solid = RoomObjectNavigation::bodyObstacles(*creature);
    const std::vector<RoomObjectPath::Obstacle> onTheWay = seatObstacles(*creature, own->first);
    Tile* best = nullptr;
    Ogre::Vector2 bestPoint = position;
    Ogre::Vector2 bestTurn = position;
    float bestDistance = std::numeric_limits<float>::max();
    for(int32_t dx = -1; dx <= 1; ++dx)
    {
        for(int32_t dy = -1; dy <= 1; ++dy)
        {
            Tile* tile = getGameMap()->getTile(seatX + dx, seatY + dy);
            if((tile == nullptr) || (tile->getCoveringRoom() != this) || hasFurnitureOn(tile) ||
               !creature->canGoThroughTile(tile))
                continue;

            bool taken = false;
            for(const std::pair<const RoomTavernSeat, RoomTavernSpot>& entry : mSpots)
            {
                if((entry.second.mCreature != creature) && (entry.second.mCreature->getPositionTile() == tile) &&
                   ((entry.second.mState == TavernGuestState::ko) || (entry.second.mState == TavernGuestState::getUp)))
                    taken = true;
            }
            if(taken)
                continue;

            const Ogre::Vector2 middle(static_cast<Ogre::Real>(tile->getX()), static_cast<Ogre::Real>(tile->getY()));
            Ogre::Vector2 point = middle;
            if(!RoomObjectNavigation::standingPosition(solid, middle, point))
                continue;

            // Away from the seat: the loser walks KO_TURN_STEP past the point, turns back and goes down looking at
            // its seat, its body on the floor behind it from mBehindMin to mBehindMax
            Ogre::Vector2 away = point - position;
            if(away.squaredLength() < static_cast<Ogre::Real>(DIRECTION_EPSILON))
                continue;
            away.normalise();
            const Ogre::Vector2 turn = point + away * KO_TURN_STEP;
            const Ogre::Vector2 feet = point + away * (body->mBehindMin * scale);
            const Ogre::Vector2 head = point + away * (body->mBehindMax * scale);
            Tile* headTile = getGameMap()->getTile(Helper::round(head.x), Helper::round(head.y));
            if((headTile == nullptr) || (headTile->getCoveringRoom() != this) ||
               !RoomObjectPath::clearSegment(onTheWay, position, turn) ||
               !RoomObjectPath::clearSegment(lying, feet, head))
                continue;

            const float distance = point.squaredDistance(position);
            if(distance < bestDistance)
            {
                bestDistance = distance;
                best = tile;
                bestPoint = point;
                bestTurn = turn;
            }
        }
    }

    if(best == nullptr)
        return false;

    // The loser reels off the bench, turns back towards its table and goes down where the short walk ends
    std::vector<Ogre::Vector2> route;
    route.push_back(bestTurn);
    route.push_back(bestPoint);
    creature->setWalkPath(EntityAnimation::stagger_anim, EntityAnimation::knockedout_anim, true, false, route, false, true);
    return true;
}

void RoomTavern::resumeLoadedGuests()
{
    if(mPendingSpots.empty() && mPendingGames.empty())
        return;

    // The creatures take their saved places again; the use of the room binds them in addCreatureUsingRoom
    std::vector<std::string> names;
    for(std::map<std::string, RoomTavernPendingSpot>::iterator it = mPendingSpots.begin(); it != mPendingSpots.end(); ++it)
        names.push_back(it->first);

    for(const std::string& name : names)
    {
        Creature* creature = getGameMap()->getCreature(name);
        if((creature == nullptr) || !creature->isAlive() || !creature->getIsOnMap() || (creature->getSeat() != getSeat()))
            continue;

        if(!creature->isActionInList(CreatureActionType::useRoom))
            creature->pushAction(Utils::make_unique<CreatureActionUseRoom>(*creature, *this, false));
    }
    mPendingSpots.clear();

    // A game goes on when both of its guests are back; otherwise it ends without effects
    for(const RoomTavernPendingGame& saved : mPendingGames)
    {
        Creature* creatureA = getGameMap()->getCreature(saved.mNameA);
        Creature* creatureB = getGameMap()->getCreature(saved.mNameB);
        std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotA = findSpotOf(creatureA);
        std::map<RoomTavernSeat, RoomTavernSpot>::iterator spotB = findSpotOf(creatureB);
        if((creatureA == nullptr) || (creatureB == nullptr) || (spotA == mSpots.end()) || (spotB == mSpots.end()) ||
           (spotA->second.mState != TavernGuestState::game) || (spotB->second.mState != TavernGuestState::game))
            continue;

        RoomTavernGame game;
        game.mKind = saved.mKind;
        game.mSeatA = spotA->first;
        game.mSeatB = spotB->first;
        game.mCreatureA = creatureA;
        game.mCreatureB = creatureB;
        game.mTurnsLeft = saved.mTurnsLeft;
        game.mSlapsTakenA = saved.mSlapsTakenA;
        game.mSlapsTakenB = saved.mSlapsTakenB;
        game.mTurnIsA = saved.mTurnIsA;
        game.mDuelClock = saved.mDuelClock;
        mGames[game.mSeatA] = game;
        showSpotState(spotA->first.mTable, spotA->second);
        showSpotState(spotB->first.mTable, spotB->second);
        // A slap that ran when the game was saved goes on for the rest of its time, its clips with it
        const RoomTavernDuelClock& clock = game.mDuelClock;
        if((game.mKind == TavernGameKind::slapDuel) && (clock.mPhase == TavernDuelPhase::slap) && (clock.mTurnsLeft > 0))
        {
            Creature* slapper = game.mTurnIsA ? creatureA : creatureB;
            Creature* target = game.mTurnIsA ? creatureB : creatureA;
            const double secondsLeft = static_cast<double>(clock.mTurnsLeft) / ODApplication::turnsPerSecond;
            slapper->setTimedAnimationState(EntityAnimation::sit_slap_anim, secondsLeft, false,
                getFacingDirection(*slapper, *target), false);
            if((clock.mSlapResult == TavernSlapResult::hit) || (clock.mSlapResult == TavernSlapResult::critical))
                target->setTimedAnimationState(EntityAnimation::sit_slapped_anim, secondsLeft, false,
                    getFacingDirection(*target, *slapper), false);
        }
    }
    mPendingGames.clear();

    // A guest in a game whose partner did not come back is done
    for(std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if(it->second.mState != TavernGuestState::game)
            continue;

        bool inGame = false;
        for(std::map<RoomTavernSeat, RoomTavernGame>::iterator game = mGames.begin(); game != mGames.end(); ++game)
        {
            if((game->second.mCreatureA == it->second.mCreature) || (game->second.mCreatureB == it->second.mCreature))
                inGame = true;
        }
        if(!inGame)
            setSpotDone(it->second, 0);
    }
}

void RoomTavern::addDrinkDirt(Tile* tile)
{
    if(tile == nullptr)
        return;

    tile->addDirt(ConfigManager::getSingleton().getRoomConfigDouble("TavernDirtPerDrink"));
}

void RoomTavern::sendTavernEvent(Creature& creature, int32_t kind, const Creature* opponent)
{
    Tile* tile = creature.getPositionTile();
    if(tile == nullptr)
        return;

    CosmeticEvent event(CosmeticEventType::tavernEvent);
    event.mSubject = creature.getName();
    if(opponent != nullptr)
        event.mObject = opponent->getName();
    event.mValue = kind;
    event.mPosition = creature.getPosition();

    // The keepers that see the tile and the keeper of the creature itself (its post is written on its own client)
    std::vector<Seat*> receivers = tile->getSeatsWithVision();
    if((creature.getSeat() != nullptr) && (std::find(receivers.begin(), receivers.end(), creature.getSeat()) == receivers.end()))
        receivers.push_back(creature.getSeat());

    for(Seat* seat : receivers)
    {
        if((seat->getPlayer() == nullptr) || !seat->getPlayer()->getIsHuman())
            continue;

        ODServer::getSingleton().sendCosmeticEvent(seat->getPlayer(), event);
    }
}

bool RoomTavern::servesBeer() const
{
    return (getSeat() != nullptr) && (getSeat()->getSkillLevel(SkillType::tavernBeer) >= 1);
}

void RoomTavern::setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles)
{
    Room::setupRoom(name, seat, tiles);

    if(!tiles.empty())
        mCounterTile = tiles.front();

    // The computer keepers let their creatures pay for the beer
    if((seat != nullptr) && (seat->getPlayer() != nullptr) && !seat->getPlayer()->getIsHuman())
        mPayer = TavernPayer::creature;
}

bool RoomTavern::hasPlacedCounter() const
{
    if(mCounterTile == nullptr)
        return false;

    std::map<Tile*, BuildingObject*>::const_iterator it = mBuildingObjects.find(mCounterTile);
    if(it == mBuildingObjects.end())
        return false;

    return it->second->getMeshName() == TAVERN_COUNTER_MESH;
}

void RoomTavern::absorbRoom(Room* r)
{
    if(r->getType() != getType())
    {
        OD_LOG_ERR("Trying to merge incompatible rooms: " + getName() + ", type=" + RoomManager::getRoomNameFromRoomType(getType()) + ", with " + r->getName() + ", type=" + RoomManager::getRoomNameFromRoomType(r->getType()));
        return;
    }

    // The room that already has its counter and innkeeper is the older one and keeps them with its payer setting. The
    // room that is built last has only picked a counter tile so far; the other room has its objects.
    RoomTavern* other = static_cast<RoomTavern*>(r);
    if(!hasPlacedCounter() && other->hasPlacedCounter())
    {
        mCounterTile = other->mCounterTile;
        mPayer = other->mPayer;
    }

    // The figure of the other room goes away; updateActiveSpots puts one on the counter of the merged room. Its stools go
    // too: updateActiveSpots puts them at the tables of the merged room
    other->removeInnkeeper();
    other->removeStools();
    other->mCounterTile = nullptr;

    Room::absorbRoom(r);
}

void RoomTavern::splitRoom(Room& newRoom, const std::vector<Tile*>& tiles)
{
    if(newRoom.getType() != getType())
        return;

    // The room that gets the tiles keeps the payer setting of this one, also when the seat changes
    RoomTavern& newTavern = static_cast<RoomTavern&>(newRoom);
    newTavern.mPayer = mPayer;

    // The counter stays where it was when its tile goes over with the others
    if((mCounterTile != nullptr) && (std::find(tiles.begin(), tiles.end(), mCounterTile) != tiles.end()))
        newTavern.mCounterTile = mCounterTile;
}

bool RoomTavern::removeCoveredTile(Tile* t)
{
    if(!Room::removeCoveredTile(t))
        return false;

    // The guests stay: updateActiveSpots follows every lost tile, spreads the furniture again and lets them look for a seat.

    // The next remaining tile becomes the counter; the innkeeper follows in updateActiveSpots
    if(t == mCounterTile)
    {
        if(mCoveredTiles.empty())
            mCounterTile = nullptr;
        else
            mCounterTile = mCoveredTiles.front();
    }

    return true;
}

void RoomTavern::removeFromGameMap(GameMap* gameMap)
{
    removeInnkeeper();
    removeStools();
    Room::removeFromGameMap(gameMap);
}

void RoomTavern::removeInnkeeper()
{
    if(mInnkeeper == nullptr)
        return;

    mInnkeeper->removeFromRoom();
    mInnkeeper = nullptr;
}

double RoomTavern::getBackToWallAngle(const Tile* tile, bool& isNextToWall) const
{
    GameMap* gameMap = getGameMap();
    const int x = tile->getX();
    const int y = tile->getY();
    isNextToWall = true;

    Tile* top = gameMap->getTile(x, y + 1);
    if((top == nullptr) || (top->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_TOP;

    Tile* bottom = gameMap->getTile(x, y - 1);
    if((bottom == nullptr) || (bottom->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_BOTTOM;

    Tile* left = gameMap->getTile(x - 1, y);
    if((left == nullptr) || (left->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_LEFT;

    Tile* right = gameMap->getTile(x + 1, y);
    if((right == nullptr) || (right->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_RIGHT;

    // A tile in the middle of the room: all four neighbours are part of it
    isNextToWall = false;
    return OBJECT_ANGLE_WALL_TOP;
}

void RoomTavern::placeInnkeeper()
{
    if(mCounterTile == nullptr)
        return;

    bool isNextToWall = false;
    const Ogre::Real angle = static_cast<Ogre::Real>(getBackToWallAngle(mCounterTile, isNextToWall));

    // The figure is turned like the counter. One that stands elsewhere or looks the wrong way is spawned again, since
    // the angle of an entity cannot be changed.
    if((mInnkeeper != nullptr) && ((mInnkeeper->getPositionTile() != mCounterTile) || (mInnkeeper->getRotationAngle() != angle)))
        removeInnkeeper();

    if(mInnkeeper == nullptr)
        mInnkeeper = InnkeeperEntity::spawnOnTile(getGameMap(), getName(), mCounterTile, angle);
}

//! \brief Updates tavern furniture and the innkeeper for the current room tiles.
void RoomTavern::updateActiveSpots(GameMap* gameMap)
{
    Room::updateActiveSpots(gameMap);

    // The objects and the figure are created by the server and sent to the clients like every other entity
    if(!getIsOnServerMap())
        return;

    if(gameMap == nullptr)
        gameMap = getGameMap();

    // Objects of tiles the room no longer covers go away; a table goes when either of its two tiles is lost
    std::vector<Tile*> objectsToRemove;
    for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
    {
        bool covered = std::find(mCoveredTiles.begin(), mCoveredTiles.end(), entry.first) != mCoveredTiles.end();
        if(covered && (entry.second->getMeshName() == TAVERN_TABLE_MESH))
        {
            Tile* second = tableSecondTile(gameMap, *entry.first, entry.second->getRotationAngle());
            covered = (second != nullptr) && (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), second) != mCoveredTiles.end());
        }
        if(!covered)
            objectsToRemove.push_back(entry.first);
    }
    for(Tile* tile : objectsToRemove)
        removeBuildingObject(tile);

    // A room without tiles has neither counter nor innkeeper
    if(mCoveredTiles.empty())
    {
        mCounterTile = nullptr;
        removeInnkeeper();
        mLayoutTiles.clear();
        mLayoutCounter = nullptr;
        updateStools(gameMap);
        // Nothing is left to sit on: the guests go to another tavern or back to work
        standUpGuests();
        return;
    }

    // The first tile is the counter tile, also when the old counter tile is gone
    if((mCounterTile == nullptr) || (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), mCounterTile) == mCoveredTiles.end()))
        mCounterTile = mCoveredTiles.front();

    // Order candidates for deterministic furniture placement.
    std::vector<Tile*> orderedTiles = mCoveredTiles;
    std::sort(orderedTiles.begin(), orderedTiles.end(), Room::compareTile);
    // The furniture stays as it is while the tiles and the counter stay the same; seated guests depend on it
    const bool hadLayout = !mLayoutTiles.empty();
    const bool layoutChanged = (orderedTiles != mLayoutTiles) || (mCounterTile != mLayoutCounter);
    if(!layoutChanged && mSavedFurniture.empty())
    {
        updateStools(gameMap);
        placeInnkeeper();
        return;
    }

    std::map<Tile*, std::string> wantedObjects;
    std::map<Tile*, double> objectAngles;
    // Every tile that carries furniture: the counter, the kegs and both tiles of each table
    std::vector<Tile*> furnitureTiles;
    wantedObjects[mCounterTile] = TAVERN_COUNTER_MESH;
    furnitureTiles.push_back(mCounterTile);
    // A loaded room gets back exactly the kegs and tables it was saved with, at most one piece per tile of the room.
    const bool restoreSaved = !mSavedFurniture.empty();
    for(const RoomTavernSavedFurniture& saved : mSavedFurniture)
    {
        if((std::find(furnitureTiles.begin(), furnitureTiles.end(), saved.mTile) != furnitureTiles.end()) ||
           (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), saved.mTile) == mCoveredTiles.end()))
            continue;
        Tile* second = nullptr;
        if(saved.mMesh == TAVERN_TABLE_MESH)
        {
            second = tableSecondTile(gameMap, *saved.mTile, saved.mAngle);
            if((second == nullptr) || (std::find(furnitureTiles.begin(), furnitureTiles.end(), second) != furnitureTiles.end()) ||
               (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), second) == mCoveredTiles.end()))
                continue;
            furnitureTiles.push_back(second);
        }
        wantedObjects[saved.mTile] = saved.mMesh;
        objectAngles[saved.mTile] = saved.mAngle;
        furnitureTiles.push_back(saved.mTile);
    }
    mSavedFurniture.clear();
    const size_t kegLimit = orderedTiles.size() / TAVERN_TILES_PER_KEG;
    const size_t tableLimit = orderedTiles.size() / TAVERN_TILES_PER_TABLE;
    // Pick the candidate furthest from already placed furniture, with coordinate order breaking ties. A table needs two
    // free tiles next to each other; when no such pair is left, no further table is placed. A table whose benches face
    // free floor of the room on both sides comes before one with a bench at a wall or at other furniture; a bench with a
    // wall behind it stays empty, and a table with a wall behind both benches is not placed.
    for(size_t kind = 0; !restoreSaved && (kind < 2); ++kind)
    {
        const size_t limit = (kind == 0) ? kegLimit : tableLimit;
        for(size_t count = 0; count < limit; ++count)
        {
            Tile* best = nullptr;
            Tile* bestSecond = nullptr;
            double bestAngle = 0.0;
            int32_t bestDistance = -1;
            bool bestBenchesFree = false;
            for(Tile* tile : orderedTiles)
            {
                if(std::find(furnitureTiles.begin(), furnitureTiles.end(), tile) != furnitureTiles.end())
                    continue;
                const int x = tile->getX();
                const int y = tile->getY();
                // A keg stands on one tile at a wall, a table on two tiles in one of its two directions
                const size_t nbAngles = (kind == 0) ? 1 : NB_TABLE_ANGLES;
                for(size_t angleIndex = 0; angleIndex < nbAngles; ++angleIndex)
                {
                    double angle = 0.0;
                    Tile* second = nullptr;
                    bool benchesFree = false;
                    if(kind == 0)
                    {
                        Tile* neighbours[] = {gameMap->getTile(x, y + 1), gameMap->getTile(x, y - 1),
                                              gameMap->getTile(x - 1, y), gameMap->getTile(x + 1, y)};
                        const double angles[] = {OBJECT_ANGLE_WALL_TOP, OBJECT_ANGLE_WALL_BOTTOM,
                                                 OBJECT_ANGLE_WALL_LEFT, OBJECT_ANGLE_WALL_RIGHT};
                        bool wall = false;
                        bool adjacentKeg = false;
                        for(size_t i = 0; i < 4; ++i)
                        {
                            if((neighbours[i] != nullptr) && neighbours[i]->isFullTile() && !wall)
                            {
                                wall = true;
                                angle = angles[i];
                            }
                            std::map<Tile*, std::string>::const_iterator object = wantedObjects.find(neighbours[i]);
                            if((object != wantedObjects.end()) && (object->second == TAVERN_KEG_MESH))
                                adjacentKeg = true;
                        }
                        if(!wall || adjacentKeg)
                            continue;
                    }
                    else
                    {
                        angle = TABLE_ANGLES[angleIndex];
                        second = tableSecondTile(gameMap, *tile, angle);
                        if((second == nullptr) ||
                           (std::find(orderedTiles.begin(), orderedTiles.end(), second) == orderedTiles.end()) ||
                           (std::find(furnitureTiles.begin(), furnitureTiles.end(), second) != furnitureTiles.end()))
                            continue;
                        // A table with a wall behind both benches would have no place to sit
                        if(isBenchBehindWall(gameMap, *tile, angle, 0) && isBenchBehindWall(gameMap, *tile, angle, 1))
                            continue;
                        benchesFree = areBenchSidesFree(gameMap, *tile, *second, orderedTiles, furnitureTiles);
                    }
                    // The distance of the piece to the nearest furniture, from each of its tiles
                    int32_t distance = std::numeric_limits<int32_t>::max();
                    for(Tile* furniture : furnitureTiles)
                    {
                        const int32_t dx = x - furniture->getX();
                        const int32_t dy = y - furniture->getY();
                        distance = std::min(distance, dx * dx + dy * dy);
                        if(second != nullptr)
                        {
                            const int32_t sx = second->getX() - furniture->getX();
                            const int32_t sy = second->getY() - furniture->getY();
                            distance = std::min(distance, sx * sx + sy * sy);
                        }
                    }
                    if((benchesFree && !bestBenchesFree) || ((benchesFree == bestBenchesFree) && (distance > bestDistance)))
                    {
                        best = tile;
                        bestSecond = second;
                        bestAngle = angle;
                        bestDistance = distance;
                        bestBenchesFree = benchesFree;
                    }
                }
            }
            if(best == nullptr)
                break;
            wantedObjects[best] = (kind == 0) ? TAVERN_KEG_MESH : TAVERN_TABLE_MESH;
            objectAngles[best] = bestAngle;
            furnitureTiles.push_back(best);
            if(bestSecond != nullptr)
                furnitureTiles.push_back(bestSecond);
        }
    }

    // Replace obsolete or turned furniture and leave every unselected tile as free floor.
    for(Tile* tile : orderedTiles)
    {
        std::map<Tile*, std::string>::const_iterator wanted = wantedObjects.find(tile);
        std::map<Tile*, BuildingObject*>::iterator existing = mBuildingObjects.find(tile);
        double angle = 0.0;
        if(wanted != wantedObjects.end())
        {
            bool isNextToWall = false;
            std::map<Tile*, double>::const_iterator savedAngle = objectAngles.find(tile);
            angle = (savedAngle != objectAngles.end()) ? savedAngle->second : getBackToWallAngle(tile, isNextToWall);
        }
        if(existing != mBuildingObjects.end())
        {
            if((wanted != wantedObjects.end()) && (existing->second->getMeshName() == wanted->second) &&
               (std::abs(static_cast<double>(existing->second->getRotationAngle()) - angle) < ANGLE_EPSILON))
                continue;
            removeBuildingObject(tile);
        }
        if(wanted == wantedObjects.end())
            continue;
        BuildingObject* object = nullptr;
        if(wanted->second == TAVERN_TABLE_MESH)
        {
            // The table stands halfway between its two tiles
            const Ogre::Vector2 middle = tableMiddle(*tile, angle);
            object = new BuildingObject(gameMap, *this, wanted->second, tile, middle.x, middle.y, 0.0f,
                static_cast<Ogre::Real>(angle), false);
            object->setFurnitureScale(Ogre::Vector2(TAVERN_TABLE_SCALE, TAVERN_TABLE_SCALE));
        }
        else
        {
            object = new BuildingObject(gameMap, *this, wanted->second, *tile, static_cast<Ogre::Real>(angle), false);
        }
        addBuildingObject(tile, object, gameMap);
        object->createMesh();
    }

    updateStools(gameMap);
    placeInnkeeper();

    // The furniture was spread again: all guests stand up and look for a seat at the new tables
    mLayoutTiles = orderedTiles;
    mLayoutCounter = mCounterTile;
    if(hadLayout && layoutChanged)
        standUpGuests();
}

//! \brief Writes the tavern and its guest and game states to the stream.
void RoomTavern::exportToStream(std::ostream& os) const
{
    Room::exportToStream(os);
    os << STREAM_TAG_PAYER << " " << static_cast<uint32_t>(mPayer) << std::endl;
    if(mCounterTile == nullptr)
        return;

    if(mInnkeeper != nullptr)
        os << STREAM_TAG_INNKEEPER << " " << mCounterTile->getX() << " " << mCounterTile->getY() << std::endl;

    os << STREAM_TAG_COUNTER << " " << mCounterTile->getX() << " " << mCounterTile->getY() << std::endl;
    os << STREAM_TAG_SEAT_LAYOUT << " " << SEAT_LAYOUT_VERSION << std::endl;

    // Furniture <x> <y> <mesh> <angle>: one line for every keg and table (the tile of its object; the second tile of a
    // table follows from its angle), so loading puts them back where they stood
    for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
    {
        const std::string& mesh = entry.second->getMeshName();
        if((mesh != TAVERN_KEG_MESH) && (mesh != TAVERN_TABLE_MESH))
            continue;

        os << STREAM_TAG_FURNITURE << " " << entry.first->getX() << " " << entry.first->getY() << " " << mesh << " "
           << entry.second->getRotationAngle() << std::endl;
    }

    // Spot <tableX> <tableY> <creature> <state> <turnsLeft> <drinks> <sleepAfter> <wantsGame> <seat>: one line for every guest
    for(std::map<RoomTavernSeat, RoomTavernSpot>::const_iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        const RoomTavernSpot& spot = it->second;
        if(spot.mCreature == nullptr)
            continue;

        os << STREAM_TAG_SPOT << " " << it->first.mTable->getX() << " " << it->first.mTable->getY() << " " << spot.mCreature->getName()
           << " " << guestStateToString(spot.mState) << " " << spot.mTurnsLeft << " " << spot.mDrinks << " "
           << (spot.mSleepAfter ? 1 : 0) << " " << (spot.mWantsGame ? 1 : 0) << " " << it->first.mIndex << std::endl;
    }

    // Game <kind> <xA> <yA> <xB> <yB> <creatureA> <creatureB> <turnsLeft> <slapsA> <slapsB> <turn> <seatA> <seatB>
    // <duelPhase> <duelTurnsLeft> <slapTurns> <slapResult>: one line for every running game (turn: 0 = the first guest
    // slaps or slaps next, 1 = the second; the last four are the clock of a slap duel, see RoomTavernDuelClock)
    for(std::map<RoomTavernSeat, RoomTavernGame>::const_iterator it = mGames.begin(); it != mGames.end(); ++it)
    {
        const RoomTavernGame& game = it->second;
        os << STREAM_TAG_GAME << " " << static_cast<uint32_t>(game.mKind) << " " << game.mSeatA.mTable->getX() << " "
           << game.mSeatA.mTable->getY() << " " << game.mSeatB.mTable->getX() << " " << game.mSeatB.mTable->getY() << " "
           << game.mCreatureA->getName() << " " << game.mCreatureB->getName() << " " << game.mTurnsLeft << " "
           << game.mSlapsTakenA << " " << game.mSlapsTakenB << " " << (game.mTurnIsA ? 0 : 1) << " "
           << game.mSeatA.mIndex << " " << game.mSeatB.mIndex << " "
           << static_cast<uint32_t>(game.mDuelClock.mPhase) << " " << game.mDuelClock.mTurnsLeft << " "
           << game.mDuelClock.mSlapTurns << " " << static_cast<uint32_t>(game.mDuelClock.mSlapResult) << std::endl;
    }
}

//! \brief Reads the tavern and its saved guest and game states from the stream.
bool RoomTavern::importFromStream(std::istream& is)
{
    if(!Room::importFromStream(is))
        return false;

    // The lines come after the tiles of the room, in any order, and every one of them is optional. The first word that
    // is none of them belongs to what follows in the stream: it is put back.
    Tile* innkeeperTile = nullptr;
    Tile* counterTile = nullptr;
    bool hasSeatLayout = false;
    while(true)
    {
        std::streampos pos = is.tellg();
        std::string tag;
        if(!(is >> tag))
        {
            is.clear();
            is.seekg(pos);
            break;
        }

        if(tag == STREAM_TAG_PAYER)
        {
            uint32_t payer = 0;
            if(!(is >> payer) || (payer > static_cast<uint32_t>(TavernPayer::creature)))
                return false;

            mPayer = static_cast<TavernPayer>(payer);
        }
        else if(tag == STREAM_TAG_INNKEEPER)
        {
            if(!readTileFromStream(getGameMap(), is, innkeeperTile))
                return false;
        }
        else if(tag == STREAM_TAG_COUNTER)
        {
            if(!readTileFromStream(getGameMap(), is, counterTile))
                return false;
        }
        else if(tag == STREAM_TAG_SEAT_LAYOUT)
        {
            uint32_t version = 0;
            if(!(is >> version) || (version == 0) || (version > SEAT_LAYOUT_VERSION))
                return false;

            // Format 1 had tables of one tile with four seats: it is loaded like a save without seat data
            hasSeatLayout = (version == SEAT_LAYOUT_VERSION);
        }
        else if(tag == STREAM_TAG_FURNITURE)
        {
            RoomTavernSavedFurniture saved;
            if(!readTileFromStream(getGameMap(), is, saved.mTile) || !(is >> saved.mMesh >> saved.mAngle) ||
               ((saved.mMesh != TAVERN_KEG_MESH) && (saved.mMesh != TAVERN_TABLE_MESH)))
                return false;

            mSavedFurniture.push_back(saved);
        }
        else if(tag == STREAM_TAG_SPOT)
        {
            // The rest of the line: x y creature state turnsLeft [drinks sleepAfter wantsGame seat]
            std::string rest;
            std::getline(is, rest);
            std::istringstream line(rest);
            int32_t x = 0;
            int32_t y = 0;
            std::string name;
            std::string stateToken;
            RoomTavernPendingSpot saved;
            if(!(line >> x >> y >> name >> stateToken >> saved.mTurnsLeft) || !guestStateFromString(stateToken, saved.mState))
                return false;

            int32_t sleepAfter = 0;
            int32_t wantsGame = 0;
            uint32_t seatIndex = 0;
            line >> saved.mDrinks >> sleepAfter >> wantsGame >> seatIndex;
            if(seatIndex >= TAVERN_PLACES_PER_TABLE)
                return false;

            saved.mSleepAfter = (sleepAfter != 0);
            saved.mWantsGame = (wantsGame != 0);
            saved.mSeat = RoomTavernSeat(getGameMap()->getTile(x, y), seatIndex);
            if(saved.mSeat.mTable != nullptr)
                mPendingSpots[name] = saved;
        }
        else if(tag == STREAM_TAG_GAME)
        {
            // The rest of the line: kind xA yA xB yB creatureA creatureB turnsLeft slapsA slapsB turn [seatA seatB
            // [duelPhase duelTurnsLeft slapTurns slapResult]]
            std::string rest;
            std::getline(is, rest);
            std::istringstream line(rest);
            uint32_t kind = 0;
            int32_t xA = 0;
            int32_t yA = 0;
            int32_t xB = 0;
            int32_t yB = 0;
            int32_t turn = 0;
            RoomTavernPendingGame saved;
            if(!(line >> kind >> xA >> yA >> xB >> yB >> saved.mNameA >> saved.mNameB >> saved.mTurnsLeft >>
                 saved.mSlapsTakenA >> saved.mSlapsTakenB >> turn) ||
               (kind > static_cast<uint32_t>(TavernGameKind::slapDuel)))
                return false;

            uint32_t seatA = 0;
            uint32_t seatB = 0;
            line >> seatA >> seatB;
            if((seatA >= TAVERN_PLACES_PER_TABLE) || (seatB >= TAVERN_PLACES_PER_TABLE))
                return false;

            // The clock of a slap duel: the slap or pause goes on where it was. A save made before the duel clock has
            // none, then the next slap starts in the next turn.
            uint32_t duelPhase = 0;
            int32_t duelTurnsLeft = 0;
            int32_t slapTurns = 0;
            uint32_t slapResult = 0;
            if(line >> duelPhase >> duelTurnsLeft >> slapTurns >> slapResult)
            {
                if((duelPhase > static_cast<uint32_t>(TavernDuelPhase::pause)) ||
                   (slapResult > static_cast<uint32_t>(TavernSlapResult::critical)))
                    return false;

                saved.mDuelClock.mPhase = static_cast<TavernDuelPhase>(duelPhase);
                saved.mDuelClock.mTurnsLeft = std::max(duelTurnsLeft, 0);
                saved.mDuelClock.mSlapTurns = std::max(slapTurns, 0);
                saved.mDuelClock.mSlapResult = static_cast<TavernSlapResult>(slapResult);
            }

            saved.mKind = static_cast<TavernGameKind>(kind);
            saved.mSeatA = RoomTavernSeat(getGameMap()->getTile(xA, yA), seatA);
            saved.mSeatB = RoomTavernSeat(getGameMap()->getTile(xB, yB), seatB);
            saved.mTurnIsA = (turn == 0);
            mPendingGames.push_back(saved);
        }
        else
        {
            is.clear();
            is.seekg(pos);
            break;
        }
    }

    // The innkeeper stands on the counter tile, so its tile tells the counter if the counter line is missing. A tile
    // that is not part of the room is ignored: updateActiveSpots takes the first tile then.
    Tile* wantedCounter = (counterTile != nullptr) ? counterTile : innkeeperTile;
    if((wantedCounter != nullptr) && (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), wantedCounter) != mCoveredTiles.end()))
        mCounterTile = wantedCounter;

    // A save made before tables had seats, or before they were two tiles long: the furniture is spread again by the
    // current rule, running games end without a winner, and each guest looks for a free seat by the normal rule
    if(!hasSeatLayout)
    {
        mSavedFurniture.clear();
        mPendingGames.clear();
        for(std::map<std::string, RoomTavernPendingSpot>::iterator it = mPendingSpots.begin(); it != mPendingSpots.end(); ++it)
        {
            RoomTavernPendingSpot& saved = it->second;
            const bool stillDrinking = (saved.mState == TavernGuestState::arriving) || (saved.mState == TavernGuestState::drinking);
            saved.mState = stillDrinking ? TavernGuestState::arriving : TavernGuestState::done;
            saved.mSeat = RoomTavernSeat();
            saved.mTurnsLeft = 0;
            saved.mWantsGame = false;
        }
    }

    return true;
}
