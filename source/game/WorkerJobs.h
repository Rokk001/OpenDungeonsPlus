#ifndef WORKERJOBS_H
#define WORKERJOBS_H

#include <array>
#include <cstdint>

class Creature;
class GameEntity;

//! \brief Jobs in the fixed window order, plus an unassigned state.
enum class WorkerJob : uint32_t { dig, claimGround, claimWall, carry, clean, reload, none };
//! \brief Categories in which workers transport objects.
enum class WorkerCarryEntry : uint32_t { ownKnockedOut, enemyKnockedOut, corpse, gold, items, giftBoxes, trapsDoors, none };
//! \brief Free-worker allocation modes.
enum class WorkerFreeMode : uint32_t { automatic, priority };

//! \brief Keeper preferences for fixed jobs, free jobs and transport.
struct WorkerJobSettings
{
    std::array<uint32_t, 6> fixed{{0, 0, 0, 0, 0, 0}};
    uint32_t freeMode = 0;
    std::array<uint32_t, 6> priority{{3, 0, 1, 2, 4, 5}};
    std::array<uint32_t, 7> carryOrder{{0, 1, 2, 3, 4, 5, 6}};
    uint32_t goldFirst = 0;
};

//! \brief Validates the complete settings record without adopting partial values.
inline bool validWorkerJobSettings(const WorkerJobSettings& settings)
{
    if(settings.freeMode > 1 || settings.goldFirst > 1)
        return false;
    std::array<bool, 6> jobs{{false, false, false, false, false, false}};
    std::array<bool, 7> entries{{false, false, false, false, false, false, false}};
    for(uint32_t job : settings.priority)
    {
        if(job >= jobs.size() || jobs[job]) return false;
        jobs[job] = true;
    }
    for(uint32_t entry : settings.carryOrder)
    {
        if(entry >= entries.size() || entries[entry]) return false;
        entries[entry] = true;
    }
    return true;
}

//! \brief Classifies an entity even while carried; callers separately check pickup and destination eligibility.
WorkerCarryEntry classifyWorkerCarry(GameEntity& entity, Creature& carrier);

#endif // WORKERJOBS_H
