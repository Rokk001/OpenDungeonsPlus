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

#include "creatureaction/CreatureActionSearchDirtToClean.h"

#include "creatureaction/CreatureActionCleanTile.h"
#include "entities/Creature.h"
#include "entities/DirtPileEntity.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/Pathfinding.h"
#include "rooms/Room.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"

#include <algorithm>
#include <vector>

//! \brief Rank of a room the keeper ordered to be cleaned: cleaned before every other room.
static const int32_t ROOM_RANK_ORDER = 0;
//! \brief Rank of the toilet room: cleaned before the other rooms of the same dirt stage.
static const int32_t ROOM_RANK_TOILET = 1;
//! \brief Rank of every other room.
static const int32_t ROOM_RANK_OTHER = 2;

CreatureActionSearchDirtToClean::CreatureActionSearchDirtToClean(Creature& creature) :
    CreatureAction(creature)
{
    mCreature.getSeat()->getPlayer()->notifyWorkerAction(mCreature, getType());
}

CreatureActionSearchDirtToClean::~CreatureActionSearchDirtToClean()
{
    mCreature.getSeat()->getPlayer()->notifyWorkerStopsAction(mCreature, getType());
}

std::function<bool()> CreatureActionSearchDirtToClean::action() // allowed-lambda: signature required by CreatureAction
{
    return std::bind(&CreatureActionSearchDirtToClean::handleSearchDirtToClean,
        std::ref(mCreature), getNbTurns());
}

bool CreatureActionSearchDirtToClean::isPileCleanable(const Tile& tile)
{
    const Room* room = tile.getCoveringRoom();
    if(room == nullptr)
        return true;

    return room->isCleanableByWorkers() || room->getCleanOrder();
}

//! \brief Orders tiles with the most dirt first.
static bool isDirtier(const Tile* first, const Tile* second)
{
    return first->getDirt() > second->getDirt();
}

//! \brief Finds the pile nearest to the worker that lies on a tile of the worker's seat, outside the rooms workers
//! never clean, and can be reached.
//! \return The tile of the pile, nullptr if there is none.
static Tile* findPileTile(Creature& creature, Tile* myTile)
{
    Tile* bestTile = nullptr;
    float bestDist = 0.0f;
    for(RenderedMovableEntity* entity : creature.getGameMap()->getRenderedMovableEntities())
    {
        if((entity == nullptr) || (entity->getObjectType() != GameEntityType::dirtPileEntity))
            continue;

        DirtPileEntity* dirtPile = static_cast<DirtPileEntity*>(entity);
        if(dirtPile->getKind() != DirtPileKind::pile)
            continue;

        Tile* tile = dirtPile->getPositionTile();
        if((tile == nullptr) || (tile->getSeat() != creature.getSeat()))
            continue;

        if(!CreatureActionSearchDirtToClean::isPileCleanable(*tile))
            continue;

        float dist = Pathfinding::squaredDistanceTile(*myTile, *tile);
        if((bestTile != nullptr) && (bestDist <= dist))
            continue;

        if(!creature.getGameMap()->pathExists(&creature, myTile, tile))
            continue;

        bestTile = tile;
        bestDist = dist;
    }

    return bestTile;
}

//! \brief Tells how urgent the cleaning of a room is: ordered rooms first, then the toilet, then the others.
static int32_t getRoomRank(const Room* room)
{
    if(room->getCleanOrder())
        return ROOM_RANK_ORDER;

    if(room->isToiletRoom())
        return ROOM_RANK_TOILET;

    return ROOM_RANK_OTHER;
}

//! \brief Finds the dirtiest tile of a room that has dirt and can be reached by the worker.
//! \return The tile, nullptr if the room has no such tile.
static Tile* findDirtiestReachableTile(Creature& creature, Tile* myTile, Room* room)
{
    std::vector<Tile*> dirtyTiles;
    for(Tile* tile : room->getCoveredTiles())
    {
        if(tile->getDirt() > 0.0)
            dirtyTiles.push_back(tile);
    }

    std::sort(dirtyTiles.begin(), dirtyTiles.end(), isDirtier);
    for(Tile* tile : dirtyTiles)
    {
        if(creature.getGameMap()->pathExists(&creature, myTile, tile))
            return tile;
    }

    return nullptr;
}

//! \brief Finds the tile to clean in the rooms of the worker's seat that need cleaning: the best rank first, and of
//! equal rank the room whose dirtiest tile is nearest.
//! \return The tile, nullptr if no room needs cleaning or none can be reached.
static Tile* findRoomTile(Creature& creature, Tile* myTile)
{
    Tile* bestTile = nullptr;
    int32_t bestRank = ROOM_RANK_OTHER + 1;
    float bestDist = 0.0f;
    for(Room* room : creature.getGameMap()->getRooms())
    {
        if(room->getSeat() != creature.getSeat())
            continue;

        if(!room->needsCleaning())
            continue;

        int32_t rank = getRoomRank(room);
        if(rank > bestRank)
            continue;

        Tile* tile = findDirtiestReachableTile(creature, myTile, room);
        if(tile == nullptr)
            continue;

        float dist = Pathfinding::squaredDistanceTile(*myTile, *tile);
        if((rank == bestRank) && (bestDist <= dist))
            continue;

        bestTile = tile;
        bestRank = rank;
        bestDist = dist;
    }

    return bestTile;
}

//! \brief Finds the nearest reachable tile of the worker's seat outside rooms that has a blood stain or is as dirty
//! as the third dirt stage.
//! \return The tile, nullptr if there is none.
static Tile* findCorridorTile(Creature& creature, Tile* myTile)
{
    GameMap* gameMap = creature.getGameMap();
    double filthyDirt = ConfigManager::getSingleton().getDirtConfigDouble("DirtStage3At");
    Tile* bestTile = nullptr;
    float bestDist = 0.0f;
    for(int32_t xx = 0; xx < gameMap->getMapSizeX(); ++xx)
    {
        for(int32_t yy = 0; yy < gameMap->getMapSizeY(); ++yy)
        {
            Tile* tile = gameMap->getTile(xx, yy);
            if((tile == nullptr) || (tile->getSeat() != creature.getSeat()) || (tile->getCoveringRoom() != nullptr))
                continue;

            bool hasBlood = (DirtPileEntity::getEntityOnTile(tile, DirtPileKind::blood) != nullptr);
            if(!hasBlood && (tile->getDirt() < filthyDirt))
                continue;

            float dist = Pathfinding::squaredDistanceTile(*myTile, *tile);
            if((bestTile != nullptr) && (bestDist <= dist))
                continue;

            if(!gameMap->pathExists(&creature, myTile, tile))
                continue;

            bestTile = tile;
            bestDist = dist;
        }
    }

    return bestTile;
}

bool CreatureActionSearchDirtToClean::handleSearchDirtToClean(Creature& creature, int32_t nbTurns)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName() + ", pos=" + Helper::toString(creature.getPosition()));
        creature.popAction();
        return true;
    }

    // If we have been cleaning for too long, we stop to check if there is something else to do
    if(nbTurns >= Creature::NB_TURNS_BEFORE_CHECKING_TASK)
    {
        creature.popAction();
        return true;
    }

    // Piles first, then the rooms that need cleaning, then the corridors
    Tile* tileToClean = findPileTile(creature, myTile);
    if(tileToClean == nullptr)
        tileToClean = findRoomTile(creature, myTile);

    if(tileToClean == nullptr)
        tileToClean = findCorridorTile(creature, myTile);

    if(tileToClean != nullptr)
    {
        creature.pushAction(Utils::make_unique<CreatureActionCleanTile>(creature, *tileToClean));
        return true;
    }

    // Nothing to clean, so we do something else
    creature.popAction();
    return true;
}
