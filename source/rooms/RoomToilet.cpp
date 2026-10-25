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

#include "rooms/RoomToilet.h"

#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomManager.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

#include <algorithm>

const std::string RoomToiletName = "Toilet";
const std::string RoomToiletNameDisplay = "Toilet room";
const RoomType RoomToilet::mRoomType = RoomType::toilet;
const TileVisual RoomToilet::mRoomVisual = TileVisual::toiletRoom;

namespace
{
//! \brief Mesh name of the seat that stands on every tile of a toilet room.
const std::string TOILET_SEAT_MESH = "ToiletSeat";
//! \brief Seat angles (degrees) for a back to the wall at +y, -y, -x and +x (same convention as the wall furniture of the library).
const double SEAT_ANGLE_WALL_TOP = 0.0;
const double SEAT_ANGLE_WALL_BOTTOM = 180.0;
const double SEAT_ANGLE_WALL_LEFT = 90.0;
const double SEAT_ANGLE_WALL_RIGHT = 270.0;

//! \brief Builds, prices and loads toilet rooms; registered for RoomType::toilet.
class RoomToiletFactory : public RoomFactory
{
    RoomType getRoomType() const override
    { return RoomToilet::mRoomType; }

    TileVisual getVisualType() const override
    { return RoomToilet::mRoomVisual; }

    const std::string& getName() const override
    { return RoomToiletName; }

    const std::string& getNameReadable() const override
    { return RoomToiletNameDisplay; }

    int getCostPerTile() const override
    { return ConfigManager::getSingleton().getRoomConfigInt32("ToiletCostPerTile"); }

    void checkBuildRoom(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefault(gameMap, RoomToilet::mRoomType, inputManager, inputCommand);
    }

    bool buildRoom(GameMap* gameMap, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, gameMap, player, packet))
            return false;

        int32_t pricePerTarget = RoomManager::costPerTile(RoomToilet::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
            return false;

        RoomToilet* room = new RoomToilet(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }

    void checkBuildRoomEditor(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefaultEditor(gameMap, RoomToilet::mRoomType, inputManager, inputCommand);
    }

    bool buildRoomEditor(GameMap* gameMap, ODPacket& packet) const override
    {
        RoomToilet* room = new RoomToilet(gameMap);
        return buildRoomDefaultEditor(gameMap, room, packet);
    }

    //! \brief Creates an empty room of this type, for a room that has to be split in two.
    Room* createRoom(GameMap* gameMap) const override
    { return new RoomToilet(gameMap); }

    Room* getRoomFromStream(GameMap* gameMap, std::istream& is) const override
    {
        RoomToilet* room = new RoomToilet(gameMap);
        if(!Room::importRoomFromStream(*room, is))
        {
            OD_LOG_ERR("Error while building a room from the stream");
        }
        return room;
    }

    bool buildRoomOnTiles(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles, bool noFee =false) const override
    {
        int32_t pricePerTarget = RoomManager::costPerTile(RoomToilet::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!noFee)
            if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
                return false;
        RoomToilet* room = new RoomToilet(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }
};

// Register the factory
static RoomRegister reg(new RoomToiletFactory);

//! \brief Collects the toilet rooms the creature may use: the ones of its seat, or all of them when its seat has none.
//! \param creature The creature that looks for a toilet.
//! \param rooms Filled with the rooms.
void collectToiletRooms(Creature& creature, std::vector<RoomToilet*>& rooms)
{
    rooms.clear();
    std::vector<Room*> allRooms = creature.getGameMap()->getRoomsByType(RoomType::toilet);
    for(Room* room : allRooms)
    {
        if(room->getSeat() == creature.getSeat())
            rooms.push_back(static_cast<RoomToilet*>(room));
    }

    if(!rooms.empty())
        return;

    for(Room* room : allRooms)
        rooms.push_back(static_cast<RoomToilet*>(room));
}
}

RoomToilet::RoomToilet(GameMap* gameMap) :
    Room(gameMap)
{
    setMeshName("Room");
}

int64_t RoomToilet::getReservationEndTurn() const
{
    ConfigManager& config = ConfigManager::getSingleton();
    double turns = config.getDirtConfigDouble("ToiletUseTurns") * config.getDirtConfigDouble("ToiletReserveFactor");
    return getGameMap()->getTurnNumber() + static_cast<int64_t>(turns);
}

bool RoomToilet::isTileFree(const Tile* tile, const Creature* user) const
{
    if(tile->getCoveringRoom() != this)
        return false;

    std::map<const Tile*, Reservation>::const_iterator it = mReserved.find(tile);
    if(it == mReserved.end())
        return true;

    if(it->second.mUser == user)
        return true;

    return getGameMap()->getTurnNumber() >= it->second.mExpireTurn;
}

bool RoomToilet::reserveTile(const Tile* tile, const Creature* user)
{
    if(!isTileFree(tile, user))
        return false;

    Reservation& reservation = mReserved[tile];
    reservation.mUser = user;
    reservation.mExpireTurn = getReservationEndTurn();
    return true;
}

void RoomToilet::releaseTile(const Tile* tile, const Creature* user)
{
    std::map<const Tile*, Reservation>::iterator it = mReserved.find(tile);
    if(it == mReserved.end())
        return;

    if(it->second.mUser == user)
        mReserved.erase(it);
}

bool RoomToilet::hasOpenCreatureSpot(Creature* c)
{
    for(Tile* tile : mCoveredTiles)
    {
        if(isTileFree(tile, c))
            return true;
    }

    return false;
}

bool RoomToilet::canBeUsedBy(const Creature& creature) const
{
    if(getSeat() == creature.getSeat())
        return true;

    return getGameMap()->numRoomsByTypeAndSeat(RoomType::toilet, creature.getSeat()) == 0;
}

double RoomToilet::getSeatAngle(const Tile* tile) const
{
    GameMap* gameMap = getGameMap();
    const int x = tile->getX();
    const int y = tile->getY();

    Tile* top = gameMap->getTile(x, y + 1);
    if((top == nullptr) || (top->getCoveringRoom() != this))
        return SEAT_ANGLE_WALL_TOP;

    Tile* bottom = gameMap->getTile(x, y - 1);
    if((bottom == nullptr) || (bottom->getCoveringRoom() != this))
        return SEAT_ANGLE_WALL_BOTTOM;

    Tile* left = gameMap->getTile(x - 1, y);
    if((left == nullptr) || (left->getCoveringRoom() != this))
        return SEAT_ANGLE_WALL_LEFT;

    Tile* right = gameMap->getTile(x + 1, y);
    if((right == nullptr) || (right->getCoveringRoom() != this))
        return SEAT_ANGLE_WALL_RIGHT;

    // A tile in the middle of the room: all four neighbours are part of it
    return SEAT_ANGLE_WALL_TOP;
}

void RoomToilet::updateActiveSpots(GameMap* gameMap)
{
    Room::updateActiveSpots(gameMap);

    // The seats are created by the server and sent to the clients like every other building object
    if(!getIsOnServerMap())
        return;

    if(gameMap == nullptr)
        gameMap = getGameMap();

    // Seats of tiles the room no longer covers go away together with their reservation
    std::vector<Tile*> seatsToRemove;
    for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
    {
        if(std::find(mCoveredTiles.begin(), mCoveredTiles.end(), entry.first) == mCoveredTiles.end())
            seatsToRemove.push_back(entry.first);
    }
    for(Tile* tile : seatsToRemove)
        removeBuildingObject(tile);

    for(std::map<const Tile*, Reservation>::iterator it = mReserved.begin(); it != mReserved.end();)
    {
        if(it->first->getCoveringRoom() != this)
            it = mReserved.erase(it);
        else
            ++it;
    }

    // Every covered tile gets a seat
    for(Tile* tile : mCoveredTiles)
    {
        if(mBuildingObjects.find(tile) != mBuildingObjects.end())
            continue;

        BuildingObject* seat = new BuildingObject(gameMap, *this, TOILET_SEAT_MESH, *tile, getSeatAngle(tile), false);
        addBuildingObject(tile, seat, gameMap);
        seat->createMesh();
    }
}

Tile* RoomToilet::findFreeToiletTile(Creature& creature)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
        return nullptr;

    std::vector<RoomToilet*> rooms;
    collectToiletRooms(creature, rooms);

    std::vector<Tile*> freeTiles;
    for(RoomToilet* room : rooms)
    {
        for(Tile* tile : room->mCoveredTiles)
        {
            if(!room->isTileFree(tile, &creature))
                continue;

            if(!creature.getGameMap()->pathExists(&creature, myTile, tile))
                continue;

            freeTiles.push_back(tile);
        }
    }

    if(freeTiles.empty())
        return nullptr;

    Tile* chosenTile = nullptr;
    creature.getGameMap()->findBestPath(&creature, myTile, freeTiles, chosenTile);
    return chosenTile;
}

bool RoomToilet::hasToiletRoomFor(Creature& creature)
{
    std::vector<RoomToilet*> rooms;
    collectToiletRooms(creature, rooms);
    for(RoomToilet* room : rooms)
    {
        if(room->numCoveredTiles() > 0)
            return true;
    }

    return false;
}

Tile* RoomToilet::findWaitTile(Creature& creature, bool& waiting)
{
    waiting = false;
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
        return nullptr;

    const int radius = static_cast<int>(ConfigManager::getSingleton().getDirtConfigDouble("ToiletWaitRadius"));
    GameMap* gameMap = creature.getGameMap();
    std::vector<RoomToilet*> rooms;
    collectToiletRooms(creature, rooms);

    std::vector<Tile*> waitTiles;
    for(RoomToilet* room : rooms)
    {
        for(Tile* seatTile : room->mCoveredTiles)
        {
            for(int dx = -radius; dx <= radius; ++dx)
            {
                for(int dy = -radius; dy <= radius; ++dy)
                {
                    Tile* tile = gameMap->getTile(seatTile->getX() + dx, seatTile->getY() + dy);
                    if((tile == nullptr) || tile->isFullTile() || !creature.canGoThroughTile(tile))
                        continue;

                    // The creature already waits close to a toilet room
                    if(tile == myTile)
                    {
                        waiting = true;
                        return nullptr;
                    }

                    // Outside the room, so that the seats stay free for the creatures that use them
                    if(tile->getCoveringRoom() == room)
                        continue;

                    if(std::find(waitTiles.begin(), waitTiles.end(), tile) != waitTiles.end())
                        continue;

                    if(!gameMap->pathExists(&creature, myTile, tile))
                        continue;

                    waitTiles.push_back(tile);
                }
            }
        }
    }

    if(waitTiles.empty())
        return nullptr;

    Tile* chosenTile = nullptr;
    gameMap->findBestPath(&creature, myTile, waitTiles, chosenTile);
    return chosenTile;
}
