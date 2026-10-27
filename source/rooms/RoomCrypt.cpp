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

#include "rooms/RoomCrypt.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "creatureaction/CreatureActionCarryEntity.h"

#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/SmallSpiderEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "rooms/RoomManager.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/Random.h"
#include "utils/MakeUnique.h"

#include <cmath>

const std::string RoomCryptName = "Crypt";
const std::string RoomCryptNameDisplay = "Crypt room";
const RoomType RoomCrypt::mRoomType = RoomType::crypt;
const TileVisual RoomCrypt::mRoomVisual= TileVisual::cryptRoom;



namespace
{
class RoomCryptFactory : public RoomFactory
{
    RoomType getRoomType() const override
    { return RoomCrypt::mRoomType; }

    TileVisual getVisualType() const override
    { return RoomCrypt::mRoomVisual; }
    
    const std::string& getName() const override
    { return RoomCryptName; }

    const std::string& getNameReadable() const override
    { return RoomCryptNameDisplay; }

    int getCostPerTile() const override
    { return ConfigManager::getSingleton().getRoomConfigInt32("CryptCostPerTile"); }

    void checkBuildRoom(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefault(gameMap, RoomCrypt::mRoomType, inputManager, inputCommand);
    }

    bool buildRoom(GameMap* gameMap, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, gameMap, player, packet))
            return false;

        int32_t pricePerTarget = RoomManager::costPerTile(RoomCrypt::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
            return false;

        RoomCrypt* room = new RoomCrypt(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }

    void checkBuildRoomEditor(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefaultEditor(gameMap, RoomCrypt::mRoomType, inputManager, inputCommand);
    }

    bool buildRoomEditor(GameMap* gameMap, ODPacket& packet) const override
    {
        RoomCrypt* room = new RoomCrypt(gameMap);
        return buildRoomDefaultEditor(gameMap, room, packet);
    }

    //! \brief Creates an empty room of this type, for a room that has to be split in two.
    Room* createRoom(GameMap* gameMap) const override
    { return new RoomCrypt(gameMap); }

    Room* getRoomFromStream(GameMap* gameMap, std::istream& is) const override
    {
        RoomCrypt* room = new RoomCrypt(gameMap);
        if(!Room::importRoomFromStream(*room, is))
        {
            OD_LOG_ERR("Error while building a room from the stream");
        }
        return room;
    }
    
    bool buildRoomOnTiles(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles, bool noFee =false) const override
    {
        int32_t pricePerTarget = RoomManager::costPerTile(RoomCrypt::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!noFee)
            if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
                return false;

        RoomCrypt* room = new RoomCrypt(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }
};

// Register the factory
static RoomRegister reg(new RoomCryptFactory);
}

static const int32_t OFFSET_TILE_X = 0;
static const int32_t OFFSET_TILE_Y = -1;

//! \brief Creates an empty crypt; corpse clocks remain on the creatures.
RoomCrypt::RoomCrypt(GameMap* gameMap) :
    Room(gameMap)
{
    setMeshName("Crypt");
}

//! \brief Registers a central grave without replacing an existing corpse reservation.
BuildingObject* RoomCrypt::notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile)
{
    switch(place)
    {
        case ActiveSpotPlace::activeSpotCenter:
        {
            mRottingCreatures.emplace(tile, nullptr);
            int rnd = Random::Int(0, 100);
            if (rnd < 33)
                return new BuildingObject(getGameMap(), *this, "KnightCoffin", *tile, 0.0, false);
            else if (rnd < 66)
                return new BuildingObject(getGameMap(), *this, "CelticCross", *tile, 0.0, false);
            else
                return new BuildingObject(getGameMap(), *this, "StoneCoffin", *tile, 0.0, false);
        }
        case ActiveSpotPlace::activeSpotLeft:
        {
            return new BuildingObject(getGameMap(), *this, "KnightStatue", *tile, 90.0, false);
        }
        case ActiveSpotPlace::activeSpotRight:
        {
            return new BuildingObject(getGameMap(), *this, "KnightStatue", *tile, 270.0, false);
        }
        case ActiveSpotPlace::activeSpotTop:
        {
            return new BuildingObject(getGameMap(), *this, "KnightStatue2", *tile, 0.0, false);
        }
        case ActiveSpotPlace::activeSpotBottom:
        {
            return new BuildingObject(getGameMap(), *this, "KnightStatue2", *tile, 180.0, false);
        }
        default:
            break;
    }
    return nullptr;
}

//! \brief Releases a deleted grave without restarting its body's lie or decay phase.
void RoomCrypt::notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile)
{
    Room::notifyActiveSpotRemoved(place, tile);
    if(place != ActiveSpotPlace::activeSpotCenter)
        return;

    std::map<Tile*, Creature*>::iterator it = mRottingCreatures.find(tile);
    if(it == mRottingCreatures.end())
        return;
    Creature* corpse = it->second;
    // If the dead creature is already delivered, add it back so its normal corpse life continues.
    if(corpse != nullptr && !corpse->isCorpseCarried())
        corpse->addEntityToPositionTile();
    mRottingCreatures.erase(it);
}

//! \brief Combines the two crypts' grave occupants and FIFO corpse levels.
void RoomCrypt::absorbRoom(Room *r)
{
    if(r->getType() != getType())
    {
        OD_LOG_ERR("Trying to merge incompatible rooms: " + getName() + ", type=" + RoomManager::getRoomNameFromRoomType(getType()) + ", with " + r->getName() + ", type=" + RoomManager::getRoomNameFromRoomType(r->getType()));
        return;
    }
    RoomCrypt* rc = static_cast<RoomCrypt*>(r);
    mRottingCreatures.insert(rc->mRottingCreatures.begin(), rc->mRottingCreatures.end());
    rc->mRottingCreatures.clear();
    mCorpseLevels.insert(mCorpseLevels.end(), rc->mCorpseLevels.begin(), rc->mCorpseLevels.end());
    rc->mCorpseLevels.clear();
    mCorpseSpotNames.insert(rc->mCorpseSpotNames.begin(), rc->mCorpseSpotNames.end());
    rc->mCorpseSpotNames.clear();

    Room::absorbRoom(r);
}

//! \brief Keeps the existing crypt ambience; every corpse advances its own lie and decay clocks.
void RoomCrypt::doUpkeep()
{
    Room::doUpkeep();

    if(mCoveredTiles.empty())
        return;

    // Each central active spot has a probability to spawn a spider
    for(Tile* tile : mCentralActiveSpotTiles)
    {
        if(Random::Int(1, 10) > 1)
            continue;

        SmallSpiderEntity* spider = new SmallSpiderEntity(getGameMap(), getName(), 10);
        Ogre::Vector3 pos(static_cast<Ogre::Real>(tile->getX()), static_cast<Ogre::Real>(tile->getY()), 0.0f);
        spider->addToGameMap();
        spider->createMesh();
        spider->setPosition(pos);
    }

}

//! \brief Finds a delivered body's grave, excluding bodies still carried or merely reserved elsewhere.
Tile* RoomCrypt::getCorpseSpot(const Creature& creature) const
{
    Tile* tile = creature.getPositionTile();
    if(creature.isAlive() || creature.isCorpseCarried() || tile == nullptr || tile->getCoveringRoom() != this)
        return nullptr;
    for(const std::pair<Tile* const, Creature*>& spot : mRottingCreatures)
    {
        if(spot.second == &creature)
            return spot.first;
    }
    return nullptr;
}

//! \brief Releases delivery reservations or restores a delivered body to normal tile registration.
void RoomCrypt::removeCorpse(Creature& creature)
{
    if(getCorpseSpot(creature) != nullptr)
        creature.addEntityToPositionTile();
    for(std::pair<Tile* const, Creature*>& spot : mRottingCreatures)
    {
        if(spot.second == &creature)
            spot.second = nullptr;
    }
}

//! \brief Credits a completely decayed body, removes it, then consumes complete FIFO groups for liches.
void RoomCrypt::notifyCorpseDecayed(Creature& creature)
{
    Tile* tileSpawn = getCorpseSpot(creature);
    if(tileSpawn != nullptr)
        mCorpseLevels.push_back(creature.getLevel());
    // Remove before testing the creature limit, so the vanished body no longer occupies a slot.
    creature.removeFromGameMap();
    creature.deleteYourself();
    if(tileSpawn == nullptr)
        return;

    ConfigManager& config = ConfigManager::getSingleton();
    const double corpsesPerLich = SkillManager::getResearchValue(getSeat(), SkillType::roomCrypt,
        config.getRoomConfigDouble("CryptCorpsesPerLich"), "LichCorpses");
    const double levelBonus = SkillManager::getResearchValue(getSeat(), SkillType::roomCrypt,
        config.getRoomConfigDouble("CryptLichLevelBonus"), "LichLevel");
    while(mCorpseLevels.size() >= corpsesPerLich &&
          getGameMap()->getCreaturesBySeat(getSeat()).size() < config.getMaxCreaturesPerSeatAbsolute())
    {
        const std::string& className = config.getRoomConfigString("CryptSpawnClass");
        const CreatureDefinition* definition = getGameMap()->getClassDescription(className);
        if(definition == nullptr)
        {
            OD_LOG_ERR("className=" + className);
            break;
        }
        const size_t count = static_cast<size_t>(std::ceil(corpsesPerLich));
        double levels = 0.0;
        for(size_t i = 0; i < count; ++i)
            levels += mCorpseLevels[i];
        const unsigned int level = static_cast<unsigned int>(std::min(static_cast<double>(MAX_LEVEL),
            std::floor(levels / count) + levelBonus));
        mCorpseLevels.erase(mCorpseLevels.begin(), mCorpseLevels.begin() + count);
        // Create a new creature from the class parameters at the released grave.
        Creature* lich = new Creature(getGameMap(), definition, getSeat());
        lich->setLevel(level);
        // Add it to the map and create its mesh so that the new arrival is visible.
        lich->addToGameMap();
        lich->setPosition(Ogre::Vector3(tileSpawn->getX(), tileSpawn->getY(), 0.0f));
        lich->createMesh();
        getSeat()->notifyCreatureArrival(className);
    }
}

//! \brief Finds the first unfurnished crypt tile adjacent to the grave for worker delivery.
Tile* RoomCrypt::getDeliveryTile(Tile* spot)
{
    // Wall statues may occupy the old fixed delivery tile and prevent turning.
    const int offsets[][2] = {{OFFSET_TILE_X, OFFSET_TILE_Y}, {-1, 0}, {1, 0}, {0, 1}};
    const std::map<Tile*, BuildingObject*>& objects = getBuildingObjects();
    for(const int (&offset)[2] : offsets)
    {
        Tile* tile = getGameMap()->getTile(spot->getX() + offset[0], spot->getY() + offset[1]);
        if(tile != nullptr && tile->getCoveringRoom() == this && objects.find(tile) == objects.end())
            return tile;
    }
    return nullptr;
}

//! \brief Accepts intact non-worker bodies only where a free grave has an unblocked approach.
bool RoomCrypt::hasCarryEntitySpot(GameEntity* carriedEntity)
{
    if(carriedEntity->getObjectType() != GameEntityType::creature)
        return false;

    Creature* creature = static_cast<Creature*>(carriedEntity);
    // Only dead creatures can be carried to the crypt. Seat doesn't matter
    if(creature->isAlive() || creature->getDefinition()->isWorker() || creature->isCorpseDecaying())
        return false;

    for(std::pair<Tile* const, Creature*>& p : mRottingCreatures)
    {
        if(p.second == nullptr && getDeliveryTile(p.first) != nullptr)
            return true;
    }
    return false;
}

//! \brief Reserves an available grave while preserving the carried body phase.
Tile* RoomCrypt::askSpotForCarriedEntity(GameEntity* carriedEntity)
{
    if(carriedEntity->getObjectType() != GameEntityType::creature)
    {
        OD_LOG_ERR("room=" + getName() + ", entity=" + carriedEntity->getName());
        return nullptr;
    }

    Creature* creature = static_cast<Creature*>(carriedEntity);
    if(creature->isAlive() || creature->getDefinition()->isWorker() || creature->isCorpseDecaying())
        return nullptr;
    for(const std::pair<Tile* const, Creature*>& spot : mRottingCreatures)
    {
        if(spot.second == creature)
            return getDeliveryTile(spot.first);
    }
    for(std::pair<Tile* const, Creature*>& p : mRottingCreatures)
    {
        if(p.second == nullptr)
        {
            Tile* tile = getDeliveryTile(p.first);
            if(tile == nullptr)
                continue;
            p.second = creature;
            return tile;
        }
    }
    return nullptr;
}

//! \brief Confirms delivery without an independent rot timer, or releases an interrupted delivery.
void RoomCrypt::notifyCarryingStateChanged(Creature* carrier, GameEntity* carriedEntity)
{
    for(std::pair<Tile* const, Creature*>& p : mRottingCreatures)
    {
        if(p.second == carriedEntity)
        {
            // We check if the carrier is at the expected destination
            Tile* carrierTile = carrier->getPositionTile();
            if(carrierTile == nullptr)
            {
                OD_LOG_ERR("carrier=" + carrier->getName());
                p.second = nullptr;
                return;
            }

            Tile* spot = p.first;
            Tile* tileExpected = getDeliveryTile(spot);
            if(tileExpected != carrierTile)
            {
                p.second = nullptr;
                return;
            }

            // The carrier has brought the dead creature
            if(carriedEntity->getObjectType() != GameEntityType::creature)
            {
                OD_LOG_ERR("room=" + getName() + ", entity=" + carriedEntity->getName());
                return;
            }

            Creature* deadCreature = static_cast<Creature*>(carriedEntity);
            Tile* tileDeadCreature = deadCreature->getPositionTile();
            if(tileDeadCreature == nullptr)
            {
                OD_LOG_ERR("deadCreature=" + deadCreature->getName());
                return;
            }
            // The delivered body keeps its remaining lie time; its own upkeep starts decay later.
            deadCreature->removeEntityFromPositionTile();
            return;
        }
    }

    // We couldn't find the entity in the list. That may happen if the active spot has
    // been erased between the time the carrier tried to come and the time it arrived.
    // In any case, nothing to do
}

//! \brief Writes a legacy zero and optional tags for every FIFO level and grave reservation.
void RoomCrypt::exportToStream(std::ostream& os) const
{
    Room::exportToStream(os);
    os << "0\n";
    // Corpse occupants are saved by name and rebound after creatures have loaded.
    os << "CorpseLevels " << mCorpseLevels.size();
    for(unsigned int level : mCorpseLevels)
        os << " " << level;
    os << "\nCryptSpots " << mRottingCreatures.size() << "\n";
    for(const std::pair<Tile* const, Creature*>& spot : mRottingCreatures)
        os << spot.first->getX() << " " << spot.first->getY() << " "
           << (spot.second == nullptr ? "none" : spot.second->getName()) << "\n";
}

//! \brief Reads optional crypt tags, rewinding before the next room or section in legacy files.
bool RoomCrypt::importFromStream(std::istream& is)
{
    if(!Room::importFromStream(is))
        return false;
    int32_t legacyPoints;
    if(!(is >> legacyPoints))
        return false;
    while(true)
    {
        const std::streampos pos = is.tellg();
        std::string tag;
        if(!(is >> tag) || (tag != "CorpseLevels" && tag != "CryptSpots"))
        {
            is.clear();
            is.seekg(pos);
            return true;
        }
        size_t count;
        if(!(is >> count))
            return false;
        if(tag == "CorpseLevels")
        {
            for(size_t i = 0; i < count; ++i)
            {
                unsigned int level;
                if(!(is >> level))
                    return false;
                mCorpseLevels.push_back(level);
            }
        }
        else
        {
            for(size_t i = 0; i < count; ++i)
            {
                int x, y;
                std::string name;
                if(!(is >> x >> y >> name))
                    return false;
                mCorpseSpotNames[{x, y}] = name;
            }
        }
    }
}

//! \brief Rebinds saved bodies after all creatures and central grave furniture are available.
void RoomCrypt::restoreInitialEntityState()
{
    Room::restoreInitialEntityState();
    for(const std::pair<const std::pair<int, int>, std::string>& saved : mCorpseSpotNames)
    {
        Tile* tile = getGameMap()->getTile(saved.first.first, saved.first.second);
        std::map<Tile*, Creature*>::iterator spot = mRottingCreatures.find(tile);
        if(spot == mRottingCreatures.end() || saved.second == "none")
            continue;
        Creature* creature = getGameMap()->getCreature(saved.second);
        if(creature == nullptr || creature->isAlive() || creature->getDefinition()->isWorker())
            continue;
        spot->second = creature;
        if(creature->getCorpseCarrierName().empty() && getCorpseSpot(*creature) != nullptr)
            creature->removeEntityFromPositionTile();
    }
    mCorpseSpotNames.clear();
    // All occupants are rebound before a restored carry asks for its existing reservation.
    for(const std::pair<Tile* const, Creature*>& spot : mRottingCreatures)
    {
        Creature* creature = spot.second;
        if(creature == nullptr || creature->getCorpseCarrierName().empty())
            continue;
        Creature* carrier = getGameMap()->getCreature(creature->getCorpseCarrierName());
        if(carrier != nullptr && carrier->isAlive() && carrier->getDefinition()->isWorker() &&
           carrier->getCarriedEntity() == nullptr)
            carrier->pushAction(Utils::make_unique<CreatureActionCarryEntity>(*carrier, *creature, *this));
    }
}
