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
//! \brief Scale of the table mesh (with its two benches 1.19 tiles long) so the benches end at the edges of the table tile.
const float TAVERN_TABLE_SCALE = 0.84f;
//! \brief Distance of the middle of a bench from the middle of the table (scaled mesh: seat surface at 0.39 to 0.59).
const float TAVERN_BENCH_OFFSET = 0.4116f;
//! \brief Distance of a seat from the middle of its bench (scaled mesh: bench 0.78 long, two seats).
const float TAVERN_SEAT_SIDE_OFFSET = 0.164f;
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
//! \brief The format number of the seat data written to the room stream.
const uint32_t SEAT_LAYOUT_VERSION = 1;
//! \brief Sound family of a drink that is poured.
const std::string SOUND_POUR = "Rooms/Tavern/Pour";
//! \brief Sound family of a slap in a slap duel.
const std::string SOUND_SLAP = "Creatures/Default/Slap";
//! \brief Sound family of the cheer when a game ends.
const std::string SOUND_CHEER = "Creatures/Default/Cheer";
//! \brief Turns the loser of a slap duel needs to get up from the floor (plan: 2 turns).
const int32_t GET_UP_TURNS = 2;
//! \brief Turns a guest stays done after its last drink while a game partner may be found.
const int32_t DONE_WAIT_TURNS = 1;
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

//! \brief The middle of a tile on the ground.
//! \param tile The tile.
Ogre::Vector3 tileMiddle(const Tile& tile)
{
    return Ogre::Vector3(static_cast<Ogre::Real>(tile.getX()), static_cast<Ogre::Real>(tile.getY()), 0.0f);
}

//! \brief The place of a seat relative to the middle of its table.
//! \param index The number of the seat at the table.
//! \param wholeBench True for a guest that sits in the middle of the bench.
//! \param angleDegrees The rotation of the table.
Ogre::Vector2 seatOffset(uint32_t index, bool wholeBench, double angleDegrees)
{
    const float x = (index < TAVERN_SEATS_PER_BENCH) ? TAVERN_BENCH_OFFSET : -TAVERN_BENCH_OFFSET;
    float y = 0.0f;
    if(!wholeBench)
        y = ((index % TAVERN_SEATS_PER_BENCH) == 0) ? TAVERN_SEAT_SIDE_OFFSET : -TAVERN_SEAT_SIDE_OFFSET;

    const double angle = angleDegrees * DEGREES_TO_RADIANS;
    const float cosine = static_cast<float>(std::cos(angle));
    const float sine = static_cast<float>(std::sin(angle));
    return Ogre::Vector2(x * cosine - y * sine, x * sine + y * cosine);
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
Tile* RoomTavern::getArrivalTile(const Creature& creature)
{
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    Tile* reference = (it != mSpots.end()) ? it->first.mTable : getCoveredTile(0);
    if(reference == nullptr)
        return nullptr;

    // The middle of a tile with furniture lies inside the furniture, so a tile path may not end there
    Tile* best = nullptr;
    int32_t bestDistance = std::numeric_limits<int32_t>::max();
    for(Tile* tile : mCoveredTiles)
    {
        if((mBuildingObjects.find(tile) != mBuildingObjects.end()) || !creature.canGoThroughTile(tile))
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

//! \brief Checks that the tavern is large enough and has a free seat for the creature.
bool RoomTavern::hasOpenCreatureSpot(Creature* c)
{
    if(!hasTavernBlock(mCoveredTiles))
        return false;

    // A creature the saved room waits for has its place, whatever the other guests do
    if((c != nullptr) && (mPendingSpots.find(c->getName()) != mPendingSpots.end()))
        return true;

    // A leisure visit (the creature is not thirsty) waits until the cooldown since its last tavern visit is over
    if((c != nullptr) && (c->getTavernCooldownTurns() > 0) &&
       (c->getThirst() < getTavernValue("ThirstSeek")))
        return false;

    // Without a creature any free seat will do
    if(c == nullptr)
    {
        for(Tile* table : getTableTiles())
        {
            for(uint32_t index = 0; index < TAVERN_SEATS_PER_TABLE; ++index)
            {
                if(isFreeSeat(RoomTavernSeat(table, index), false))
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

//! \brief True when the seat is at a table of the room and can take a guest.
bool RoomTavern::isFreeSeat(const RoomTavernSeat& seat, bool wholeBench) const
{
    if((seat.mTable == nullptr) || (seat.mIndex >= TAVERN_SEATS_PER_TABLE))
        return false;

    const uint32_t first = seat.mIndex - (seat.mIndex % TAVERN_SEATS_PER_BENCH);
    std::map<RoomTavernSeat, RoomTavernSpot>::const_iterator firstSeat = mSpots.find(RoomTavernSeat(seat.mTable, first));
    std::map<RoomTavernSeat, RoomTavernSpot>::const_iterator secondSeat = mSpots.find(RoomTavernSeat(seat.mTable, first + 1));
    if(wholeBench)
        return (seat.mIndex == first) && (firstSeat == mSpots.end()) && (secondSeat == mSpots.end());

    // A guest that takes the whole bench is kept under the first seat of the bench
    if((firstSeat != mSpots.end()) && firstSeat->second.mWholeBench)
        return false;

    return mSpots.find(seat) == mSpots.end();
}

//! \brief True when the creature is large (a bed of two by two tiles) and takes a whole bench alone.
bool RoomTavern::isLargeGuest(const Creature& creature)
{
    const CreatureDefinition* definition = creature.getDefinition();
    return (definition != nullptr) && (definition->getBedDim1() >= 2) && (definition->getBedDim2() >= 2);
}

//! \brief Picks a free seat for the creature; a table with a guest comes first, then the nearest table.
bool RoomTavern::pickFreeSeat(const Creature& creature, RoomTavernSeat& seat) const
{
    const bool wholeBench = isLargeGuest(creature);
    const uint32_t step = wholeBench ? TAVERN_SEATS_PER_BENCH : 1;
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

        for(uint32_t index = 0; index < TAVERN_SEATS_PER_TABLE; index += step)
        {
            if(!isFreeSeat(RoomTavernSeat(table, index), wholeBench))
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
Ogre::Vector2 RoomTavern::getSeatPosition(const RoomTavernSeat& seat, bool wholeBench) const
{
    double angle = 0.0;
    std::map<Tile*, BuildingObject*>::const_iterator table = mBuildingObjects.find(seat.mTable);
    if(table != mBuildingObjects.end())
        angle = table->second->getRotationAngle();

    const Ogre::Vector2 offset = seatOffset(seat.mIndex, wholeBench, angle);
    return Ogre::Vector2(static_cast<Ogre::Real>(seat.mTable->getX()) + offset.x,
        static_cast<Ogre::Real>(seat.mTable->getY()) + offset.y);
}

//! \brief True when the guest is at the place of its seat.
bool RoomTavern::isOnSeat(const Creature& creature, const RoomTavernSeat& seat, bool wholeBench) const
{
    const Ogre::Vector2 position = getSeatPosition(seat, wholeBench);
    const Ogre::Vector2 current(creature.getPosition().x, creature.getPosition().y);
    return current.squaredDistance(position) < SEAT_REACHED_SQUARED;
}

//! \brief Finds free points next to the seat from where a creature gets onto the bench.
void RoomTavern::findSeatStagingPoints(Creature& creature, const RoomTavernSeat& seat, bool wholeBench,
    std::vector<Ogre::Vector2>& stagingPoints) const
{
    stagingPoints.clear();
    std::map<Tile*, BuildingObject*>::const_iterator table = mBuildingObjects.find(seat.mTable);
    if(table == mBuildingObjects.end())
        return;

    // The table of the seat is the object the creature may enter; everything else stays an obstacle
    const std::vector<RoomObjectPath::Obstacle> obstacles = RoomObjectNavigation::bodyObstacles(creature, table->second);
    const Ogre::Vector2 target = getSeatPosition(seat, wholeBench);
    const Ogre::Vector2 middle(static_cast<Ogre::Real>(seat.mTable->getX()), static_cast<Ogre::Real>(seat.mTable->getY()));
    Ogre::Vector2 away = target - middle;
    away.normalise();
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
bool RoomTavern::walkToSeat(Creature& creature, const RoomTavernSeat& seat, bool wholeBench)
{
    Tile* creatureTile = creature.getPositionTile();
    if(creatureTile == nullptr)
        return false;

    const Ogre::Vector2 target = getSeatPosition(seat, wholeBench);
    std::vector<Ogre::Vector2> route;
    std::vector<Ogre::Vector2> stagingPoints;
    findSeatStagingPoints(creature, seat, wholeBench, stagingPoints);
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
bool RoomTavern::stepOffSeat(Creature& creature, const RoomTavernSeat& seat, bool wholeBench)
{
    std::vector<Ogre::Vector2> stagingPoints;
    findSeatStagingPoints(creature, seat, wholeBench, stagingPoints);
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

    const bool wholeBench = own->second.mWholeBench;
    const uint32_t step = wholeBench ? TAVERN_SEATS_PER_BENCH : 1;
    for(Tile* table : getTableTiles())
    {
        for(uint32_t index = 0; index < TAVERN_SEATS_PER_TABLE; index += step)
        {
            const RoomTavernSeat candidate(table, index);
            if((candidate == seat) || !isFreeSeat(candidate, wholeBench) || !walkToSeat(creature, candidate, wholeBench))
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
        guest.mWholeBench = isLargeGuest(*guest.mCreature);
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
    const bool wholeBench = isLargeGuest(*creature);
    const std::vector<Tile*> tables = getTableTiles();
    RoomTavernSeat seat;
    std::map<std::string, RoomTavernPendingSpot>::iterator pending = mPendingSpots.find(creature->getName());
    if((pending != mPendingSpots.end()) && isFreeSeat(pending->second.mSeat, wholeBench) &&
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
    it->second.mWholeBench = wholeBench;
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
    // Whatever clip it still shows is replaced by the next thing it does. Its leisure cooldown starts, so that the job search
    // does not send it back in at once while it still stands on a tavern tile. A thirsty guest that was stopped before its
    // first drink keeps looking for a drink.
    if((it->second.mDrinks > 0) || (it->second.mCreature->getThirst() < getTavernValue("ThirstSeek")))
        it->second.mCreature->startTavernCooldown();
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
            if(!isOnSeat(creature, seat, spot.mWholeBench))
            {
                if(!creature.isMoving() && !walkToSeat(creature, seat, spot.mWholeBench) && !walkToOtherSeat(creature, seat))
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
            setSpotState(spot, TavernGuestState::drinking, static_cast<int32_t>(getTavernValue("DrinkTurns")));
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
                if(isOnSeat(creature, seat, spot.mWholeBench))
                {
                    if(stepOffSeat(creature, seat, spot.mWholeBench))
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
    const bool seated = (own != mSpots.end()) && isOnSeat(*creature, own->first, spot.mWholeBench);
    // A seated guest looks across its table
    Ogre::Vector3 towardsTable = Ogre::Vector3::ZERO;
    if(seated)
        towardsTable = directionTo(*creature, tileMiddle(*own->first.mTable));

    switch(spot.mState)
    {
        case TavernGuestState::drinking:
            creature->setAnimationState(EntityAnimation::sit_drink_anim, true, towardsTable, false);
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
                creature->setAnimationState(clip, true, directionTo(*creature, opponent->getPosition()), false);
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

    // A guest that is done is looked for by a partner during these turns only
    for(std::map<RoomTavernSeat, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if((it->second.mState == TavernGuestState::done) && (it->second.mTurnsLeft > 0))
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
                    setSpotState(spot, TavernGuestState::getUp, GET_UP_TURNS);
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
        creature->addTavernMood(getTavernValue("BeerMood"), getTavernValue("BeerMoodTurns"));
    else if(noCoin)
        creature->addTavernMood(getTavernValue("NoCoinMood"), getTavernValue("NoCoinMoodTurns"));

    sendTavernEvent(*creature, static_cast<int32_t>((kind == DrinkKind::beer) ? CosmeticTavernKind::beer : CosmeticTavernKind::water), nullptr);
    addDrinkDirt(tile);
    if(mInnkeeper != nullptr)
        mInnkeeper->onDrink();
    playSoundAt(tile, SOUND_POUR);
    ++spot.mDrinks;

    // The guest decides itself about another drink: 50, 25, 12.5 and 6.25 percent after the 1st to the 4th drink,
    // never more than MaxDrinksPerVisit
    if(spot.mDrinks < static_cast<uint32_t>(getTavernValue("MaxDrinksPerVisit")))
    {
        const double nextDrinkPercent = getTavernValue("NextDrinkPercent") /
            std::pow(ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("TavernDrinkChainHalving", 2.0), static_cast<double>(spot.mDrinks - 1));
        if(Random::Double(0.0, PERCENT_SCALE) < nextDrinkPercent)
        {
            setSpotState(spot, TavernGuestState::drinking, static_cast<int32_t>(getTavernValue("DrinkTurns")));
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
    // one on the opposite bench comes first, so that the two can face each other
    std::vector<RoomTavernSeat> partners;
    std::vector<RoomTavernSeat> oppositePartners;
    for(uint32_t index = 0; index < TAVERN_SEATS_PER_TABLE; ++index)
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

        if((index / TAVERN_SEATS_PER_BENCH) != (seat.mIndex / TAVERN_SEATS_PER_BENCH))
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

//! \brief Plays one turn of a slap duel: the seated guest whose turn it is swings and the other one reels when it is hit.
void RoomTavern::playDuelTurn(std::map<RoomTavernSeat, RoomTavernGame>::iterator it)
{
    RoomTavernGame& game = it->second;
    Creature* slapper = game.mTurnIsA ? game.mCreatureA : game.mCreatureB;
    Creature* target = game.mTurnIsA ? game.mCreatureB : game.mCreatureA;
    uint32_t& targetSlaps = game.mTurnIsA ? game.mSlapsTakenB : game.mSlapsTakenA;

    // The slapper swings; a miss passes the turn
    slapper->setAnimationState(EntityAnimation::sit_slap_anim, false, directionTo(*slapper, target->getPosition()), false);
    playSoundAt(slapper->getPositionTile(), SOUND_SLAP);
    if(target->rollAttackHit(slapper->getAttackRating(), slapper->getLevel(), slapper->isPossessed()))
    {
        target->setAnimationState(EntityAnimation::sit_slapped_anim, false, directionTo(*target, slapper->getPosition()), false);
        // A critical slap (10 percent at equal level, 0.25 points per level of difference) wins the duel at once
        const double levelDifference = static_cast<double>(slapper->getLevel()) - static_cast<double>(target->getLevel());
        const double criticalPercent = getTavernValue("SlapCritBasePercent") +
            getTavernValue("SlapCritPerLevel") * levelDifference;
        if(Random::Double(0.0, PERCENT_SCALE) < criticalPercent)
        {
            concludeGame(it, slapper, 0);
            return;
        }

        // A normal slap takes SlapDamage hit points but never the last one
        const double damage = std::max(0.0, std::min(getTavernValue("SlapDamage"), target->getHP() - 1.0));
        target->takeDamage(slapper, damage, 0.0, 0.0, 0.0, target->getPositionTile(), false);
        ++targetSlaps;
        if(target->getHP() < getTavernValue("SlapDuelLoseBelowHp"))
        {
            concludeGame(it, slapper, 0);
            return;
        }
    }

    game.mTurnIsA = !game.mTurnIsA;
    --game.mTurnsLeft;
    if(game.mTurnsLeft > 0)
        return;

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
            creature->addTavernMood(getTavernValue("GameSpectatorMood"), getTavernValue("BeerMoodTurns"));
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
    winner->addTavernMood(winnerMood, getTavernValue("BeerMoodTurns"));
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
        loser->addTavernMood(getTavernValue("GameLoserMood"), getTavernValue("BeerMoodTurns"));
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
    setSpotState(spot, TavernGuestState::ko, static_cast<int32_t>(getTavernValue("DuelKoTurns")));
    if(!fallNextToBench(spot))
        showSpotState(nullptr, spot);
}

//! \brief The loser of a slap duel falls from its bench onto a free floor tile next to the table.
bool RoomTavern::fallNextToBench(RoomTavernSpot& spot)
{
    Creature* creature = spot.mCreature;
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator own = findSpotOf(creature);
    if((creature == nullptr) || (own == mSpots.end()) || !creature->getIsOnMap())
        return false;

    // The free floor tile nearest to the seat: part of the room, without furniture, and no other loser lies on it.
    // The way there may leave the own bench but never crosses other furniture, and the loser never lands in furniture.
    const Ogre::Vector2 position = getSeatPosition(own->first, spot.mWholeBench);
    std::map<Tile*, BuildingObject*>::const_iterator ownTable = mBuildingObjects.find(own->first.mTable);
    if(ownTable == mBuildingObjects.end())
        return false;
    const std::vector<RoomObjectPath::Obstacle> solid = RoomObjectNavigation::bodyObstacles(*creature);
    const std::vector<RoomObjectPath::Obstacle> onTheWay = RoomObjectNavigation::bodyObstacles(*creature, ownTable->second);
    Tile* best = nullptr;
    Ogre::Vector2 bestPoint = position;
    float bestDistance = std::numeric_limits<float>::max();
    for(int32_t dx = -1; dx <= 1; ++dx)
    {
        for(int32_t dy = -1; dy <= 1; ++dy)
        {
            Tile* tile = getGameMap()->getTile(own->first.mTable->getX() + dx, own->first.mTable->getY() + dy);
            if((tile == nullptr) || (tile->getCoveringRoom() != this) ||
               (mBuildingObjects.find(tile) != mBuildingObjects.end()) || !creature->canGoThroughTile(tile))
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
            if(!RoomObjectNavigation::standingPosition(solid, middle, point) ||
               !RoomObjectPath::clearSegment(onTheWay, position, point))
                continue;

            const float distance = point.squaredDistance(position);
            if(distance < bestDistance)
            {
                bestDistance = distance;
                best = tile;
                bestPoint = point;
            }
        }
    }

    if(best == nullptr)
        return false;

    // The loser reels off the bench and goes down where the short walk ends
    const std::vector<Ogre::Vector2> route(1, bestPoint);
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
        mGames[game.mSeatA] = game;
        showSpotState(spotA->first.mTable, spotA->second);
        showSpotState(spotB->first.mTable, spotB->second);
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

    // The figure of the other room goes away; updateActiveSpots puts one on the counter of the merged room
    other->removeInnkeeper();
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

    // Objects of tiles the room no longer covers go away
    std::vector<Tile*> objectsToRemove;
    for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
    {
        if(std::find(mCoveredTiles.begin(), mCoveredTiles.end(), entry.first) == mCoveredTiles.end())
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
        placeInnkeeper();
        return;
    }

    std::map<Tile*, std::string> wantedObjects;
    std::map<Tile*, double> objectAngles;
    wantedObjects[mCounterTile] = TAVERN_COUNTER_MESH;
    // A loaded room gets back exactly the kegs and tables it was saved with, at most one per tile of the room.
    const bool restoreSaved = !mSavedFurniture.empty();
    for(const RoomTavernSavedFurniture& saved : mSavedFurniture)
    {
        if((wantedObjects.count(saved.mTile) != 0) ||
           (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), saved.mTile) == mCoveredTiles.end()))
            continue;
        wantedObjects[saved.mTile] = saved.mMesh;
        objectAngles[saved.mTile] = saved.mAngle;
    }
    mSavedFurniture.clear();
    const size_t kegLimit = orderedTiles.size() / 6;
    const size_t tableLimit = orderedTiles.size() / 4;
    // Pick the candidate furthest from already placed furniture, with coordinate order breaking ties.
    for(size_t kind = 0; !restoreSaved && (kind < 2); ++kind)
    {
        const size_t limit = (kind == 0) ? kegLimit : tableLimit;
        for(size_t count = 0; count < limit; ++count)
        {
            Tile* best = nullptr;
            double bestAngle = 0.0;
            int32_t bestDistance = -1;
            for(Tile* tile : orderedTiles)
            {
                if(wantedObjects.count(tile) != 0)
                    continue;
                const int x = tile->getX();
                const int y = tile->getY();
                double angle = 0.0;
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
                int32_t distance = std::numeric_limits<int32_t>::max();
                for(const std::pair<Tile* const, std::string>& object : wantedObjects)
                {
                    const int32_t dx = x - object.first->getX();
                    const int32_t dy = y - object.first->getY();
                    distance = std::min(distance, dx * dx + dy * dy);
                }
                if(distance > bestDistance)
                {
                    best = tile;
                    bestAngle = angle;
                    bestDistance = distance;
                }
            }
            if(best == nullptr)
                break;
            wantedObjects[best] = (kind == 0) ? TAVERN_KEG_MESH : TAVERN_TABLE_MESH;
            if(kind == 0)
                objectAngles[best] = bestAngle;
        }
    }

    // Replace obsolete furniture and leave every unselected tile as free floor.
    for(Tile* tile : orderedTiles)
    {
        std::map<Tile*, std::string>::const_iterator wanted = wantedObjects.find(tile);
        std::map<Tile*, BuildingObject*>::iterator existing = mBuildingObjects.find(tile);
        if(existing != mBuildingObjects.end())
        {
            if((wanted != wantedObjects.end()) && (existing->second->getMeshName() == wanted->second))
                continue;
            removeBuildingObject(tile);
        }
        if(wanted == wantedObjects.end())
            continue;
        bool isNextToWall = false;
        std::map<Tile*, double>::const_iterator savedAngle = objectAngles.find(tile);
        const double angle = (savedAngle != objectAngles.end()) ? savedAngle->second : getBackToWallAngle(tile, isNextToWall);
        BuildingObject* object = new BuildingObject(gameMap, *this, wanted->second, *tile, angle, false);
        if(wanted->second == TAVERN_TABLE_MESH)
            object->setFurnitureScale(Ogre::Vector2(TAVERN_TABLE_SCALE, TAVERN_TABLE_SCALE));
        addBuildingObject(tile, object, gameMap);
        object->createMesh();
    }

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

    // Furniture <x> <y> <mesh> <angle>: one line for every keg and table, so loading puts them back where they stood
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

    // Game <kind> <xA> <yA> <xB> <yB> <creatureA> <creatureB> <turnsLeft> <slapsA> <slapsB> <turn> <seatA> <seatB>: one line
    // for every running game (turn: 0 = the first guest slaps next, 1 = the second)
    for(std::map<RoomTavernSeat, RoomTavernGame>::const_iterator it = mGames.begin(); it != mGames.end(); ++it)
    {
        const RoomTavernGame& game = it->second;
        os << STREAM_TAG_GAME << " " << static_cast<uint32_t>(game.mKind) << " " << game.mSeatA.mTable->getX() << " "
           << game.mSeatA.mTable->getY() << " " << game.mSeatB.mTable->getX() << " " << game.mSeatB.mTable->getY() << " "
           << game.mCreatureA->getName() << " " << game.mCreatureB->getName() << " " << game.mTurnsLeft << " "
           << game.mSlapsTakenA << " " << game.mSlapsTakenB << " " << (game.mTurnIsA ? 0 : 1) << " "
           << game.mSeatA.mIndex << " " << game.mSeatB.mIndex << std::endl;
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
            if(!(is >> version) || (version != SEAT_LAYOUT_VERSION))
                return false;

            hasSeatLayout = true;
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
            if(seatIndex >= TAVERN_SEATS_PER_TABLE)
                return false;

            saved.mSleepAfter = (sleepAfter != 0);
            saved.mWantsGame = (wantsGame != 0);
            saved.mSeat = RoomTavernSeat(getGameMap()->getTile(x, y), seatIndex);
            if(saved.mSeat.mTable != nullptr)
                mPendingSpots[name] = saved;
        }
        else if(tag == STREAM_TAG_GAME)
        {
            // The rest of the line: kind xA yA xB yB creatureA creatureB turnsLeft slapsA slapsB turn [seatA seatB]
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
            if((seatA >= TAVERN_SEATS_PER_TABLE) || (seatB >= TAVERN_SEATS_PER_TABLE))
                return false;

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

    // A save made before tables had seats: the furniture is spread again by the current rule, running games end without
    // a winner, and each guest looks for a free seat by the normal rule
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
