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

#include "creatureaction/CreatureActionSearchTileToDig.h"
#include "creatureaction/WorkerSearchTargets.h"

#include "creatureaction/CreatureActionDigTile.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "entities/TreasuryObject.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/Pathfinding.h"
#include "utils/Helper.h"
#include "utils/MakeUnique.h"
#include "utils/LogManager.h"

CreatureActionSearchTileToDig::CreatureActionSearchTileToDig(Creature& creature, bool forced) :
    CreatureAction(creature),
    mForced(forced)
{
    mCreature.getSeat()->getPlayer()->notifyWorkerAction(mCreature, getType());
}

CreatureActionSearchTileToDig::~CreatureActionSearchTileToDig()
{
    mCreature.getSeat()->getPlayer()->notifyWorkerStopsAction(mCreature, getType());
}

std::function<bool()> CreatureActionSearchTileToDig::action()
{
    return std::bind(&CreatureActionSearchTileToDig::handleSearchTileToDig,
        std::ref(mCreature), getNbTurns(), mForced);
}

//! \brief Searches eligible dig work and reports a lack of treasury capacity.
bool CreatureActionSearchTileToDig::handleSearchTileToDig(Creature& creature, int32_t nbTurns, bool forced)
{
    if(creature.getDigRate() <= 0.0)
        return false;

    Tile* myTile = creature.getPositionTile();
    if (myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName() + ", pos=" + Helper::toString(creature.getPosition()));
        creature.popAction();
        return false;
    }

    if(!forced && creature.getWorkerJob() != WorkerJob::dig)
    {
        creature.popAction();
        if(creature.getGoldCarried() > 0)
        {
            TreasuryObject* gold = new TreasuryObject(creature.getGameMap(), creature.getGoldCarried());
            creature.resetGoldCarried();
            gold->addToGameMap();
            gold->createMesh();
            gold->setPosition(Ogre::Vector3(static_cast<Ogre::Real>(myTile->getX()),
                static_cast<Ogre::Real>(myTile->getY()), 0.0f));
        }
        return true;
    }

    if(!forced)
    {
        // If we are digging tiles for too long, we stop to check if there is
        // something else to do
        if(nbTurns >= Creature::NB_TURNS_BEFORE_CHECKING_TASK)
        {
            creature.popAction();
            return true;
        }
    }

    // Prefer untouched targets, and optionally gold and gems, before distance.
    Player* tempPlayer = creature.getGameMap()->getPlayerBySeat(creature.getSeat());
    const bool goldFirst = creature.getSeat()->getWorkerJobSettings().goldFirst != 0;
    const std::vector<Tile*>& sight = creature.getTilesWithinSightRadius();
    int bestGroup = 5;
    bool bestStanding = false;
    float distBest = 0.0f;
    Tile* tileToDig = nullptr;
    Tile* tilePos = nullptr;
    for(Tile* tile : workerSearchTiles(creature, WorkerJob::dig))
    {
        if(tile == nullptr || tempPlayer == nullptr || !tile->getMarkedForDigging(tempPlayer))
            continue;
        const bool gold = tile->getType() == TileType::gold || tile->getType() == TileType::gem;
        const int group = (goldFirst && !gold ? 2 : 0) + (tile->hasWorkerDigging() ? 1 : 0);
        std::vector<Tile*> positions;
        tile->canWorkerDig(creature, positions);
        for(Tile* standing : positions)
        {
            const bool inSight = std::find(sight.begin(), sight.end(), standing) != sight.end();
            Seat* owner = standing->getSeat();
            if(!inSight && owner != nullptr && owner != creature.getSeat() && !owner->isRogueSeat())
                continue;
            if(!creature.getGameMap()->pathExists(&creature, myTile, standing))
                continue;
            const bool here = standing == myTile;
            float dist = Pathfinding::squaredDistanceTile(*myTile, *standing);
            if(tileToDig != nullptr && (group > bestGroup ||
               (group == bestGroup && bestStanding && !here) ||
               (group == bestGroup && bestStanding == here && dist >= distBest)))
                continue;
            bestGroup = group;
            bestStanding = here;
            distBest = dist;
            tileToDig = tile;
            tilePos = standing;
        }
    }

    if((tileToDig != nullptr) && (tilePos != nullptr))
    {
        // We also push the dig action to lock the tile to make sure not every worker will try to go to the same tile
        if(forced)
            creature.popAction();
        creature.pushAction(Utils::make_unique<CreatureActionDigTile>(creature, *tileToDig, *tilePos, forced));
        return true;
    }

    // If none of our neighbors are marked for digging we got here too late.
    // Finish digging
    creature.popAction();
    if(creature.getGoldCarried() > 0)
    {
        TreasuryObject* obj = new TreasuryObject(creature.getGameMap(), creature.getGoldCarried());
        creature.resetGoldCarried();
        Ogre::Vector3 pos(static_cast<Ogre::Real>(myTile->getX()), static_cast<Ogre::Real>(myTile->getY()), 0.0f);
        obj->addToGameMap();
        obj->createMesh();
        obj->setPosition(pos);

        bool isTreasuryAvailable = false;
        for(Room* room : creature.getGameMap()->getRooms())
        {
            if(room->getSeat() != creature.getSeat())
                continue;

            if(room->getTotalGoldStorage() <= 0)
                continue;

            if(room->getTotalGoldStored() >= room->getTotalGoldStorage())
                continue;

            if(room->numCoveredTiles() <= 0)
                continue;

            Tile* tile = room->getCoveredTile(0);
            if(!creature.getGameMap()->pathExists(&creature, myTile, tile))
                continue;

            isTreasuryAvailable = true;
            break;
        }
        if(isTreasuryAvailable)
        {
            // We do not push CreatureActionType::searchEntityToCarry because we want
            // this worker to be count as digging, not as carrying stuff
            creature.pushAction(Utils::make_unique<CreatureActionGrabEntity>(creature, *obj));
            return true;
        }
        else if(creature.getSeat()->getPlayer()->getIsHuman())
        {
            creature.getSeat()->getPlayer()->notifyNoTreasuryAvailable();
        }
        else if(creature.getSeat()->getPlayer() != nullptr)
        {
            creature.getSeat()->getPlayer()->notifyNoTreasuryAvailable();
        }
    }

    return true;
}
