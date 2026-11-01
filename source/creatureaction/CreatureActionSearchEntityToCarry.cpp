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
#include "game/WorkerTargets.h"
#include "gamemap/GameMap.h"
#include "gamemap/Pathfinding.h"
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

//! \brief Chooses a reachable carry target in the keeper's configured order.
bool CreatureActionSearchEntityToCarry::handleSearchEntityToCarry(Creature& creature, bool forced)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr || (!forced && creature.getWorkerJob() != WorkerJob::carry))
    {
        creature.popAction();
        return true;
    }
    GameMap* map = creature.getGameMap();
    const auto& sight = creature.getTilesWithinSightRadius();
    std::vector<GameEntity*> candidates = map->getCarryableEntities(&creature, sight);
    for(const WorkerTarget& target : creature.getSeat()->getWorkerTargetLists()[static_cast<size_t>(WorkerJob::carry)])
    {
        GameEntity* entity = map->getEntityFromTypeAndName(target.entityType, target.entityName);
        if(entity == nullptr || entity->getPositionTile() == nullptr)
            continue;
        Tile* tile = entity->getPositionTile();
        const bool inSight = std::find(sight.begin(), sight.end(), tile) != sight.end();
        if(!inSight && tile->getSeat() != nullptr && tile->getSeat() != creature.getSeat() &&
           !tile->getSeat()->isRogueSeat())
            continue;
        if(std::find(candidates.begin(), candidates.end(), entity) == candidates.end())
            candidates.push_back(entity);
    }
    std::vector<Building*> buildings = map->getReachableBuildingsPerSeat(creature.getSeat(), myTile, &creature);
    std::stable_partition(buildings.begin(), buildings.end(), infirmaryFirst);
    const auto& carryOrder = creature.getSeat()->getWorkerJobSettings().carryOrder;
    std::vector<GameEntity*> best;
    uint32_t bestRank = static_cast<uint32_t>(carryOrder.size());
    int bestLocality = 3;
    float bestDistance = 0.0f;
    for(GameEntity* entity : candidates)
    {
        Tile* tile = entity->getPositionTile();
        if(tile == nullptr || (forced && tile != myTile) || entity->getCarryLock(creature) ||
           entity->getEntityCarryType(&creature) == EntityCarryType::notCarryable ||
           !map->pathExists(&creature, myTile, tile))
            continue;
        WorkerCarryEntry entry = classifyWorkerCarry(*entity, creature);
        auto order = std::find(carryOrder.begin(), carryOrder.end(), static_cast<uint32_t>(entry));
        if(order == carryOrder.end())
            continue;
        bool accepted = false;
        if(entity->getObjectType() == GameEntityType::missileObject &&
           static_cast<MissileObject*>(entity)->getMissileType() == MissileObjectType::stone)
        {
            Tile* destination = static_cast<MissileStone*>(entity)->getDeliveryTile(creature);
            accepted = destination != nullptr && map->pathExists(&creature, myTile, destination);
        }
        for(Building* building : buildings)
            if(building->hasCarryEntitySpot(entity))
                accepted = true;
        if(!accepted)
            continue;
        uint32_t rank = static_cast<uint32_t>(order - carryOrder.begin());
        const bool inSight = std::find(sight.begin(), sight.end(), tile) != sight.end();
        int locality = tile == myTile ? 0 : (inSight ? 1 : 2);
        float distance = Pathfinding::squaredDistanceTile(*myTile, *tile);
        if(rank < bestRank || (rank == bestRank && locality < bestLocality) ||
           (rank == bestRank && locality == 2 && bestLocality == 2 && distance < bestDistance))
        {
            best.clear();
            bestRank = rank;
            bestLocality = locality;
            bestDistance = distance;
        }
        if(rank == bestRank && locality == bestLocality && (locality != 2 || distance == bestDistance))
            best.push_back(entity);
    }
    if(best.empty())
    {
        creature.popAction();
        return true;
    }
    GameEntity* entity = best[Random::Uint(0, best.size()-1)];
    if(forced)
        creature.popAction();
    creature.pushAction(Utils::make_unique<CreatureActionGrabEntity>(creature, *entity, forced));
    return true;
}
