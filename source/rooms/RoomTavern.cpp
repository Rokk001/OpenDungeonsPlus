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

#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/InnkeeperEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomManager.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

#include <algorithm>
#include <istream>
#include <map>
#include <ostream>
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

    bool buildRoom(GameMap* gameMap, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, gameMap, player, packet))
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

    bool buildRoomEditor(GameMap* gameMap, ODPacket& packet) const override
    {
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

    bool buildRoomOnTiles(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles, bool noFee =false) const override
    {
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
    mInnkeeper(nullptr)
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

bool RoomTavern::hasOpenCreatureSpot(Creature* c)
{
    return static_cast<uint32_t>(mCreaturesUsingRoom.size()) < getNbDrinkingTiles();
}

bool RoomTavern::useRoom(Creature& creature, bool forced)
{
    creature.popAction();
    return true;
}

void RoomTavern::addDrinkDirt(Tile* tile)
{
    if(tile == nullptr)
        return;

    tile->addDirt(ConfigManager::getSingleton().getRoomConfigDouble("TavernDirtPerDrink"));
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

    // A guest drinking on the tile stops. Clearing its actions releases it from the room, so we work on a copy.
    std::vector<Creature*> guests = mCreaturesUsingRoom;
    for(Creature* guest : guests)
    {
        if(guest->getPositionTile() == t)
            guest->clearActionQueue();
    }

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
        return;
    }

    // The first tile is the counter tile, also when the old counter tile is gone
    if((mCounterTile == nullptr) || (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), mCounterTile) == mCoveredTiles.end()))
        mCounterTile = mCoveredTiles.front();

    // The counter on the counter tile, a keg on the tiles next to a wall, a table on the tiles inside the room. The
    // object of a tile that has the wrong kind (a room that grew, the counter that moved) is replaced.
    for(Tile* tile : mCoveredTiles)
    {
        bool isNextToWall = false;
        const double angle = getBackToWallAngle(tile, isNextToWall);
        std::string wantedMesh = TAVERN_TABLE_MESH;
        if(tile == mCounterTile)
            wantedMesh = TAVERN_COUNTER_MESH;
        else if(isNextToWall)
            wantedMesh = TAVERN_KEG_MESH;

        std::map<Tile*, BuildingObject*>::iterator it = mBuildingObjects.find(tile);
        if(it != mBuildingObjects.end())
        {
            if(it->second->getMeshName() == wantedMesh)
                continue;

            removeBuildingObject(tile);
        }

        BuildingObject* object = new BuildingObject(gameMap, *this, wantedMesh, *tile, angle, false);
        addBuildingObject(tile, object, gameMap);
        object->createMesh();
    }

    placeInnkeeper();
}

void RoomTavern::exportToStream(std::ostream& os) const
{
    Room::exportToStream(os);
    os << STREAM_TAG_PAYER << " " << static_cast<uint32_t>(mPayer) << std::endl;
    if(mCounterTile == nullptr)
        return;

    if(mInnkeeper != nullptr)
        os << STREAM_TAG_INNKEEPER << " " << mCounterTile->getX() << " " << mCounterTile->getY() << std::endl;

    os << STREAM_TAG_COUNTER << " " << mCounterTile->getX() << " " << mCounterTile->getY() << std::endl;
}

bool RoomTavern::importFromStream(std::istream& is)
{
    if(!Room::importFromStream(is))
        return false;

    // The lines come after the tiles of the room, in any order, and every one of them is optional. The first word that
    // is none of them belongs to what follows in the stream: it is put back.
    Tile* innkeeperTile = nullptr;
    Tile* counterTile = nullptr;
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

    return true;
}
