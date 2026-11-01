#ifndef WORKERSEARCHTARGETS_H
#define WORKERSEARCHTARGETS_H

#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "game/WorkerTargets.h"
#include <algorithm>
#include <vector>

//! \brief Combines targets accessible beyond sight with this worker's own visible tiles.
inline std::vector<Tile*> workerSearchTiles(Creature& worker, WorkerJob job)
{
    const std::vector<Tile*>& sight = worker.getTilesWithinSightRadius();
    std::vector<Tile*> tiles(sight.begin(), sight.end());
    for(const WorkerTarget& target : worker.getSeat()->getWorkerTargetLists()[static_cast<size_t>(job)])
    {
        Tile* territory = job == WorkerJob::dig ? target.standingTile : target.tile;
        if(target.tile == nullptr || territory == nullptr)
            continue;
        const bool inSight = std::find(sight.begin(), sight.end(), territory) != sight.end();
        Seat* owner = territory->getSeat();
        if(!inSight && owner != nullptr && owner != worker.getSeat() && !owner->isRogueSeat())
            continue;
        if(std::find(tiles.begin(), tiles.end(), target.tile) == tiles.end())
            tiles.push_back(target.tile);
    }
    return tiles;
}

#endif
