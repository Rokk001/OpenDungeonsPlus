#ifndef WORKERALLOCATION_H
#define WORKERALLOCATION_H

#include "game/WorkerJobs.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstddef>
#include <numeric>
#include <string>
#include <vector>

class Creature;
class Seat;

//! \brief Calculates the fixed quotas and free targets in window order.
namespace WorkerAllocation
{
using Counts = std::array<uint32_t, 6>;
//! \brief Returns the keeper workers eligible for allocation this turn.
std::vector<Creature*> countedWorkers(Seat& seat);
//! \brief Updates fixed assignments for counted workers of the keeper.
void refreshFixed(Seat& seat);
//! \brief Picks an available free job for an idle counted worker.
WorkerJob chooseForIdle(Seat& seat, Creature& creature, const std::array<bool, 6>& available);

//! \brief Splits a total by weight using largest remainders and the supplied tie order.
inline Counts distribute(uint32_t total, const Counts& weights, const Counts& order)
{
    Counts result{{0, 0, 0, 0, 0, 0}};
    std::array<uint64_t, 6> remainder{{0, 0, 0, 0, 0, 0}};
    const uint64_t sum = std::accumulate(weights.begin(), weights.end(), uint64_t{0});
    if(sum == 0)
        return result;
    uint32_t used = 0;
    for(uint32_t job : order)
    {
        const uint64_t product = uint64_t{total} * weights[job];
        result[job] = static_cast<uint32_t>(product / sum);
        remainder[job] = product % sum;
        used += result[job];
    }
    while(used < total)
    {
        uint32_t best = 6;
        for(uint32_t job : order)
            if(weights[job] != 0 && (best == 6 || remainder[job] > remainder[best]))
                best = job;
        ++result[best];
        remainder[best] = 0;
        ++used;
    }
    return result;
}

//! \brief Scales fixed settings to the counted population when necessary.
inline Counts fixedQuotas(const Counts& fixed, uint32_t workers)
{
    const uint64_t sum = std::accumulate(fixed.begin(), fixed.end(), uint64_t{0});
    if(sum <= workers)
        return fixed;
    return distribute(workers, fixed, Counts{{0, 1, 2, 3, 4, 5}});
}

//! \brief Distributes free workers across jobs without exceeding their target caps.
inline Counts freeTargets(uint32_t workers, const Counts& caps, bool priority,
                          const Counts& order, const Counts& parts)
{
    Counts result{{0, 0, 0, 0, 0, 0}};
    if(!priority)
    {
        while(workers > 0)
        {
            uint32_t best = 6;
            for(uint32_t job = 0; job < 6; ++job)
                if(result[job] < caps[job] && (best == 6 || result[job] < result[best]))
                    best = job;
            if(best == 6)
                break;
            ++result[best];
            --workers;
        }
        return result;
    }
    Counts weights{{0, 0, 0, 0, 0, 0}};
    for(uint32_t rank = 0; rank < 6; ++rank)
        if(caps[order[rank]] > 0)
            weights[order[rank]] = parts[rank];
    while(workers > 0)
    {
        const Counts proposed = distribute(workers, weights, order);
        bool capped = false;
        for(uint32_t job : order)
        {
            if(weights[job] != 0 && proposed[job] > caps[job] - result[job])
            {
                const uint32_t available = caps[job] - result[job];
                result[job] += available;
                workers -= available;
                weights[job] = 0;
                capped = true;
            }
        }
        if(!capped)
        {
            for(uint32_t job = 0; job < 6; ++job)
                result[job] += proposed[job];
            break;
        }
    }
    return result;
}
//! \brief The counted worker data needed to rank and update fixed assignments.
struct Worker
{
    std::array<double, 6> skill;
    uint32_t level;
    std::string name;
    uint32_t job;
    bool fixed;
};

//! \brief Returns whether the first worker ranks above the second for a fixed job.
inline bool ranksHigher(const Worker& first, const Worker& second, uint32_t job)
{
    if(first.skill[job] != second.skill[job])
        return first.skill[job] > second.skill[job];
    if(first.level != second.level)
        return first.level > second.level;
    return first.name < second.name;
}

//! \brief Keeps the highest-ranked fixed workers and fills missing quotas in window order.
inline void assignFixed(std::vector<Worker>& workers, const Counts& quotas)
{
    for(uint32_t job = 0; job < 6; ++job)
    {
        std::vector<std::size_t> assigned;
        for(std::size_t i = 0; i < workers.size(); ++i)
            if(workers[i].fixed && workers[i].job == job)
                assigned.push_back(i);
        std::stable_sort(assigned.begin(), assigned.end(), [&](std::size_t a, std::size_t b) {
            return ranksHigher(workers[a], workers[b], job);
        });
        for(std::size_t i = quotas[job]; i < assigned.size(); ++i)
            workers[assigned[i]].fixed = false;
        uint32_t have = static_cast<uint32_t>(std::min<std::size_t>(assigned.size(), quotas[job]));
        while(have < quotas[job])
        {
            std::size_t best = workers.size();
            for(std::size_t i = 0; i < workers.size(); ++i)
                if(!workers[i].fixed && (best == workers.size() || ranksHigher(workers[i], workers[best], job)))
                    best = i;
            if(best == workers.size())
            {
                for(uint32_t later = job + 1; later < 6 && best == workers.size(); ++later)
                {
                    uint32_t laterCount = 0;
                    for(const Worker& worker : workers)
                        if(worker.fixed && worker.job == later)
                            ++laterCount;
                    if(laterCount <= quotas[later])
                        continue;
                    for(std::size_t i = 0; i < workers.size(); ++i)
                        if(workers[i].fixed && workers[i].job == later &&
                           (best == workers.size() || ranksHigher(workers[i], workers[best], job)))
                            best = i;
                }
            }
            if(best == workers.size())
                break;
            workers[best].job = job;
            workers[best].fixed = true;
            ++have;
        }
    }
}
//! \brief Keeps a free job within its target or chooses the largest available gap.
inline uint32_t chooseFreeJob(uint32_t current, const Counts& counts, const Counts& targets,
                              const std::array<bool, 6>& available)
{
    if(current < 6 && available[current] && counts[current] <= targets[current])
        return current;
    uint32_t best = 6;
    uint32_t bestGap = 0;
    for(uint32_t job = 0; job < 6; ++job)
    {
        if(!available[job])
            continue;
        const uint32_t otherWorkers = counts[job] - ((job == current && counts[job] > 0) ? 1 : 0);
        const uint32_t gap = targets[job] > otherWorkers ? targets[job] - otherWorkers : 0;
        if(gap > bestGap)
        {
            best = job;
            bestGap = gap;
        }
    }
    return best;
}
}

#endif // WORKERALLOCATION_H
