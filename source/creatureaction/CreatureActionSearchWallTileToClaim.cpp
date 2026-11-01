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

#include "creatureaction/CreatureActionSearchWallTileToClaim.h"
#include "creatureaction/WorkerSearchTargets.h"

#include "creatureaction/CreatureActionClaimWallTile.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/Pathfinding.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

CreatureActionSearchWallTileToClaim::CreatureActionSearchWallTileToClaim(Creature& creature, bool forced) :
    CreatureAction(creature),
    mForced(forced)
{
    mCreature.getSeat()->getPlayer()->notifyWorkerAction(mCreature, getType());
}

CreatureActionSearchWallTileToClaim::~CreatureActionSearchWallTileToClaim()
{
    mCreature.getSeat()->getPlayer()->notifyWorkerStopsAction(mCreature, getType());
}
std::function<bool()> CreatureActionSearchWallTileToClaim::action()
{
    return std::bind(&CreatureActionSearchWallTileToClaim::handleSearchWallTileToClaim,
        std::ref(mCreature), getNbTurns(), mForced);
}

//! \brief Searches eligible work while the worker retains this job.
bool CreatureActionSearchWallTileToClaim::handleSearchWallTileToClaim(Creature& creature, int32_t nbTurns, bool forced)
{
    if(creature.getClaimRate() <= 0.0)
        return false;

    Tile* myTile = creature.getPositionTile();
    if (myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName() + ", pos=" + Helper::toString(creature.getPosition()));
        creature.popAction();
        return false;
    }

    if(!forced && creature.getWorkerJob() != WorkerJob::claimWall)
    {
        creature.popAction();
        return true;
    }

    if(!forced)
    {
        // If we are claiming walls for too long, we stop to check if there is
        // something else to do
        if(nbTurns >= Creature::NB_TURNS_BEFORE_CHECKING_TASK)
        {
            creature.popAction();
            return true;
        }
    }

    // Choose randomly among reachable free walls, whether nearby or beyond sight.
    Player* tempPlayer = creature.getSeat()->getPlayer();
    std::vector<Tile*> available;
    for(Tile* tile : workerSearchTiles(creature, WorkerJob::claimWall))
    {
        if(tile == nullptr || tile->getMarkedForDigging(tempPlayer) ||
           !tile->isWallClaimable(creature.getSeat()) || !tile->canWorkerClaim(creature))
            continue;
        for(Tile* neighbour : tile->getAllNeighbors())
        {
            if(creature.getGameMap()->pathExists(&creature, myTile, neighbour))
            {
                available.push_back(tile);
                break;
            }
        }
    }
    Tile* tileToClaim = available.empty() ? nullptr : available[Random::Uint(0, available.size()-1)];

    if(tileToClaim != nullptr)
    {
        // We also push the dig action to lock the tile to make sure not every worker will try to go to the same tile
        creature.pushAction(Utils::make_unique<CreatureActionClaimWallTile>(creature, *tileToClaim));
        return true;
    }

    // We couldn't find a tile to claim so we do something else
    creature.popAction();
    return true;
}
