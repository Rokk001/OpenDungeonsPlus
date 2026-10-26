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

#include "creatureaction/CreatureActionSearchEntityToCarry.h"

#include "creatureaction/CreatureActionGrabEntity.h"
#include "entities/Building.h"
#include "entities/Creature.h"
#include "entities/MissileStone.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include <algorithm>
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

namespace
{
//! \brief Prioritizes infirmaries before other reachable delivery buildings.
bool infirmaryFirst(Building* building)
{
    return building->getObjectType() == GameEntityType::room &&
        static_cast<Room*>(building)->getType() == RoomType::infirmary;
}
//! \brief Keeps appended item bags below gold and knockout transports without changing saved enum values.
static int32_t carryPriority(EntityCarryType type)
{
    if(type == EntityCarryType::itemBag || type == EntityCarryType::herbBundle)
        return static_cast<int32_t>(EntityCarryType::gold) - 1;
    return static_cast<int32_t>(type);
}

CreatureActionSearchEntityToCarry::CreatureActionSearchEntityToCarry(Creature& creature, bool forced) :
    CreatureAction(creature),
    mForced(forced)
{
    mCreature.getSeat()->getPlayer()->notifyWorkerAction(mCreature, getType());
}

CreatureActionSearchEntityToCarry::~CreatureActionSearchEntityToCarry()
{
    mCreature.getSeat()->getPlayer()->notifyWorkerStopsAction(mCreature, getType());
}

std::function<bool()> CreatureActionSearchEntityToCarry::action()
{
    return std::bind(&CreatureActionSearchEntityToCarry::handleSearchEntityToCarry,
        std::ref(mCreature), mForced);
}

//! \brief Finds reachable ordinary transports and exact configured mission destinations without changing other cargo.
bool CreatureActionSearchEntityToCarry::handleSearchEntityToCarry(Creature& creature, bool forced)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    std::vector<Building*> buildings = creature.getGameMap()->getReachableBuildingsPerSeat(creature.getSeat(), myTile, &creature);
    std::stable_partition(buildings.begin(), buildings.end(), infirmaryFirst);
    std::vector<GameEntity*> carryableEntities = creature.getGameMap()->getCarryableEntities(&creature, creature.getTilesWithinSightRadius());
    std::vector<Tile*> carryableEntityInMyTileClients;
    std::vector<GameEntity*> availableEntities;
    EntityCarryType highestPriority = EntityCarryType::notCarryable;
    // If a carryable entity of highest priority is in my tile, I proceed it
    GameEntity* carryableEntityInMyTile = nullptr;
    for(GameEntity* entity : carryableEntities)
    {
        // We check that the carryable entity is reachable
        Tile* carryableEntTile = entity->getPositionTile();
        if(!creature.getGameMap()->pathExists(&creature, myTile, carryableEntTile))
            continue;

        // If we are forced to carry something, we consider only entities on our tile
        if(forced && (myTile != carryableEntTile))
            continue;

        std::vector<Tile*> missionDestinations;
        if(entity->getObjectType() == GameEntityType::missileObject &&
           static_cast<MissileObject*>(entity)->getMissileType() == MissileObjectType::stone)
        {
            Tile* destination = static_cast<MissileStone*>(entity)->getDeliveryTile(creature);
            if(destination == nullptr || !creature.getGameMap()->pathExists(&creature, myTile, destination))
                continue;
            missionDestinations.push_back(destination);
        }

        // We check if the current entity is highest or equal to the older one (if any)
        if(carryPriority(entity->getEntityCarryType(&creature)) > carryPriority(highestPriority))
        {
            // We check if a buildings wants this entity
            std::vector<Tile*> tilesDest = missionDestinations;
            for(Building* building : buildings)
            {
                if(building->hasCarryEntitySpot(entity))
                {
                    Tile* tile = building->getCoveredTile(0);
                    tilesDest.push_back(tile);
                }
            }

            if(!tilesDest.empty())
            {
                // We found a reachable building for a higher priority entity. We use this from now on
                carryableEntityInMyTile = nullptr;
                availableEntities.clear();
                availableEntities.push_back(entity);
                highestPriority = entity->getEntityCarryType(&creature);
                if(myTile == carryableEntTile)
                {
                    carryableEntityInMyTile = entity;
                    carryableEntityInMyTileClients = tilesDest;
                }
            }
        }
        else if(carryPriority(entity->getEntityCarryType(&creature)) == carryPriority(highestPriority))
        {
            // We check if a buildings wants this entity
            std::vector<Tile*> tilesDest = missionDestinations;
            for(Building* building : buildings)
            {
                if(building->hasCarryEntitySpot(entity))
                {
                    Tile* tile = building->getCoveredTile(0);
                    tilesDest.push_back(tile);
                }
            }

            if(!tilesDest.empty())
            {
                // We found a reachable building for a higher priority entity. We use this from now on
                availableEntities.push_back(entity);
                if((myTile == carryableEntTile) &&
                   (carryableEntityInMyTile == nullptr))
                {
                    carryableEntityInMyTile = entity;
                    carryableEntityInMyTileClients = tilesDest;
                }
            }
        }
        else
        {
            // Entity with lower priority. We don't proceed
        }
    }

    if(availableEntities.empty())
    {
        // No entity to carry. We can do something else
        creature.popAction();
        return true;
    }

    // If a carryable entity is in my tile, I take it
    if(carryableEntityInMyTile != nullptr)
    {
        creature.pushAction(Utils::make_unique<CreatureActionGrabEntity>(creature, *carryableEntityInMyTile));
        return true;
    }

    // We randomly choose one of the visible carryable entities
    uint32_t index = Random::Uint(0,availableEntities.size()-1);
    GameEntity* entity = availableEntities[index];
    creature.pushAction(Utils::make_unique<CreatureActionGrabEntity>(creature, *entity));
    return true;
}
