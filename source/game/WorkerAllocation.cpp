#include "game/WorkerAllocation.h"

#include "creatureaction/CreatureAction.h"
#include "creatureskill/CreatureSkillTree.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "utils/ConfigManager.h"

namespace WorkerAllocation
{
//! \brief Returns the keeper's workers that participate in this turn's allocation.
std::vector<Creature*> countedWorkers(Seat& seat)
{
    std::vector<Creature*> result;
    for(Creature* creature : seat.getGameMap()->getCreaturesBySeat(&seat))
    {
        if(!creature->getDefinition()->isWorker() || !creature->isAlive() || !creature->getIsOnMap() ||
           creature->isInHand() || creature->isKo() || creature->isPossessed() ||
           creature->isActionInList(CreatureActionType::fight) ||
           creature->isActionInList(CreatureActionType::fightFriendly) ||
           creature->isActionInList(CreatureActionType::flee) ||
           creature->isActionInList(CreatureActionType::goDefendHeart))
            continue;
        result.push_back(creature);
    }
    return result;
}

//! \brief Updates counted workers' fixed assignments while preserving excluded workers' jobs.
void refreshFixed(Seat& seat)
{
    const std::vector<Creature*> creatures = countedWorkers(seat);
    std::vector<Worker> workers;
    workers.reserve(creatures.size());
    const CreatureSkillTree::SkillTreeConfig& skillTree = ConfigManager::getSingleton().getCreatureSkillTree();
    for(Creature* creature : creatures)
    {
        const CreatureSkillTree::SkillBuild& build = creature->getSkillBuild();
        const double dig = CreatureSkillTree::passiveSum(skillTree, build, "dig%");
        const double claim = CreatureSkillTree::passiveSum(skillTree, build, "claim%");
        const double carry = CreatureSkillTree::passiveSum(skillTree, build, "carry%");
        workers.push_back(Worker{{{dig, claim, claim, carry, 0.0, 0.0}}, creature->getLevel(),
                                 creature->getName(), static_cast<uint32_t>(creature->getWorkerJob()),
                                 creature->isWorkerJobFixed()});
    }
    const Counts quotas = fixedQuotas(seat.getWorkerJobSettings().fixed, static_cast<uint32_t>(workers.size()));
    assignFixed(workers, quotas);
    for(std::size_t i = 0; i < workers.size(); ++i)
        creatures[i]->setWorkerJob(static_cast<WorkerJob>(workers[i].job), workers[i].fixed);
}

//! \brief Chooses a free worker's job from current targets and reachable choices.
WorkerJob chooseForIdle(Seat& seat, Creature& creature, const std::array<bool, 6>& available)
{
    const std::vector<Creature*> creatures = countedWorkers(seat);
    const WorkerJobSettings& settings = seat.getWorkerJobSettings();
    const Counts quotas = fixedQuotas(settings.fixed, static_cast<uint32_t>(creatures.size()));
    Counts caps{{0, 0, 0, 0, 0, 0}};
    const Counts& targets = seat.getWorkerJobTargets();
    for(uint32_t job = 0; job < 6; ++job)
        if(targets[job] > quotas[job])
            caps[job] = targets[job] - quotas[job];
    Counts freeCounts{{0, 0, 0, 0, 0, 0}};
    uint32_t freeWorkers = 0;
    for(Creature* worker : creatures)
    {
        if(worker->isWorkerJobFixed())
            continue;
        ++freeWorkers;
        const uint32_t job = static_cast<uint32_t>(worker->getWorkerJob());
        if(job < 6)
            ++freeCounts[job];
    }
    const Counts desired = freeTargets(freeWorkers, caps, settings.freeMode == static_cast<uint32_t>(WorkerFreeMode::priority),
                                       settings.priority, ConfigManager::getSingleton().getWorkerPriorityParts());
    return static_cast<WorkerJob>(chooseFreeJob(static_cast<uint32_t>(creature.getWorkerJob()), freeCounts, desired, available));
}
}
