#ifndef WORKERTARGETS_H
#define WORKERTARGETS_H

#include "entities/GameEntityType.h"
#include "game/WorkerJobs.h"

#include <array>
#include <cstdint>
#include <string>
#include <vector>

class Tile;
class Seat;

//! \brief Kinds of work tracked separately when several kinds share a tile.
enum class WorkerTargetKind { dig, ground, wall, carry, pile, room, corridor, reload };

//! \brief A stable tile and, for carried things, an identity resolved again when a worker searches.
struct WorkerTarget
{
    WorkerTargetKind kind;
    Tile* tile;
    Tile* standingTile;
    uint32_t slot;
    GameEntityType entityType;
    std::string entityName;
    WorkerCarryEntry carryEntry;
};

using WorkerTargetLists = std::array<std::vector<WorkerTarget>, 6>;

//! \brief Recounts reachable work for one keeper and stores its current target lists.
void refreshWorkerTargets(Seat& seat);

#endif // WORKERTARGETS_H
