#include "game/WorkerTargets.h"

#include "creatureaction/CreatureActionCarryEntity.h"
#include "creatureaction/CreatureActionGrabEntity.h"
#include "creatureaction/CreatureActionSearchDirtToClean.h"
#include "creatureaction/CreatureActionSearchEntityToCarry.h"
#include "entities/Building.h"
#include "entities/Creature.h"
#include "entities/DirtPileEntity.h"
#include "entities/GameEntity.h"
#include "entities/MissileStone.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/WorkerAllocation.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "traps/Trap.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <map>

namespace
{
//! \brief Tests the whole-map territory rule for a particular worker and target tile.
bool territoryAllowed(Creature& worker, Tile& tile)
{
    Seat* owner = tile.getSeat();
    if(owner == nullptr || owner == worker.getSeat() || owner->isRogueSeat())
        return true;
    const auto& sight = worker.getTilesWithinSightRadius();
    return std::find(sight.begin(), sight.end(), &tile) != sight.end();
}

//! \brief Tests whether any counted worker can reach this permitted tile.
bool reachable(const std::vector<Creature*>& workers, Tile& tile)
{
    for(Creature* worker : workers)
        if(worker->getPositionTile() != nullptr && territoryAllowed(*worker, tile) &&
           worker->getGameMap()->pathExists(worker, worker->getPositionTile(), &tile))
            return true;
    return false;
}

//! \brief Appends a tile target, retaining a separate identity for each dig place or cleaning place.
void appendTile(WorkerTargetLists& targets, WorkerJob job, WorkerTargetKind kind,
                Tile* tile, Tile* standing = nullptr, uint32_t slot = 0)
{
    targets[static_cast<uint32_t>(job)].push_back(WorkerTarget{kind, tile, standing, slot,
        GameEntityType::unknown, std::string(), WorkerCarryEntry::none});
}

//! \brief Tests whether an open ground tile has a fully claimed neighbour of the keeper.
bool hasClaimedNeighbour(Tile& tile, Seat& seat)
{
    for(Tile* neighbour : tile.getAllNeighbors())
        if(!neighbour->isFullTile() && neighbour->getSeat() == &seat &&
           neighbour->getClaimedPercentage() >= 1.0)
            return true;
    return false;
}

//! \brief Adds every reachable marked dig place, including places already occupied.
void collectDig(WorkerTargetLists& targets, Seat& seat, Tile& tile, const std::vector<Creature*>& workers)
{
    if(!tile.getMarkedForDigging(seat.getPlayer()) || !tile.isDiggable(&seat))
        return;
    for(Tile* standing : tile.getAllNeighbors())
    {
        if(standing->isFullTile())
            continue;
        const uint32_t slots = ConfigManager::getSingleton().getNbWorkersDigSameFaceTile();
        for(uint32_t slot = 0; slot < slots; ++slot)
        {
            for(Creature* worker : workers)
            {
                if(!territoryAllowed(*worker, *standing))
                    continue;
                std::vector<Ogre::Vector2> path;
                if(!worker->wallDigPath(&tile, standing, slot, path))
                    continue;
                appendTile(targets, WorkerJob::dig, WorkerTargetKind::dig, &tile, standing, slot);
                break;
            }
        }
    }
}

//! \brief Adds ground and wall work on tiles permitted and reachable by a counted worker.
void collectClaim(WorkerTargetLists& targets, Seat& seat, Tile& tile, const std::vector<Creature*>& workers)
{
    Room* room = tile.getCoveringRoom();
    const bool repair = room != nullptr && room->getSeat() == &seat && room->needsClaimRepair();
    if((repair || (tile.isGroundClaimable(&seat) && hasClaimedNeighbour(tile, seat))) &&
       reachable(workers, tile))
        appendTile(targets, WorkerJob::claimGround, WorkerTargetKind::ground, &tile);
    if(tile.getMarkedForDigging(seat.getPlayer()) || !tile.isWallClaimable(&seat))
        return;
    for(Tile* standing : tile.getAllNeighbors())
    {
        if(standing->isFullTile())
            continue;
        for(Creature* worker : workers)
        {
            if(worker->getPositionTile() == nullptr || !territoryAllowed(*worker, tile) ||
               !worker->getGameMap()->pathExists(worker, worker->getPositionTile(), standing))
                continue;
            appendTile(targets, WorkerJob::claimWall, WorkerTargetKind::wall, &tile, standing);
            return;
        }
    }
}

//! \brief Adds pile and dirty corridor targets without excluding occupied tiles.
void collectCleaningTile(WorkerTargetLists& targets, Seat& seat, Tile& tile, const std::vector<Creature*>& workers)
{
    if(tile.getSeat() != &seat)
        return;
    const bool pile = (DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::pile) != nullptr ||
                       DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::vomit) != nullptr ||
                       DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::bones) != nullptr) &&
                      CreatureActionSearchDirtToClean::isPileCleanable(tile);
    const bool corridor = tile.getCoveringRoom() == nullptr &&
        (DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::blood) != nullptr ||
         tile.getDirt() >= ConfigManager::getSingleton().getDirtConfigDouble("DirtStage3At"));
    if((!pile && !corridor) || !reachable(workers, tile))
        return;
    if(pile)
        appendTile(targets, WorkerJob::clean, WorkerTargetKind::pile, &tile);
    if(corridor)
        appendTile(targets, WorkerJob::clean, WorkerTargetKind::corridor, &tile);
}
}

namespace
{
//! \brief Adds the configured number of cleaning places for each dirty reachable room.
void collectRooms(WorkerTargetLists& targets, Seat& seat, const std::vector<Creature*>& workers)
{
    const uint32_t tilesPerCleaner = ConfigManager::getSingleton().getWorkerCleanTilesPerCleaner();
    for(Room* room : seat.getGameMap()->getRooms())
    {
        if(room->getSeat() != &seat || !room->needsCleaning())
            continue;
        Tile* dirtyTile = nullptr;
        for(Tile* tile : room->getCoveredTiles())
            if(tile->getDirt() > 0.0 && reachable(workers, *tile))
            {
                dirtyTile = tile;
                break;
            }
        if(dirtyTile == nullptr)
            continue;
        const uint32_t tileCount = static_cast<uint32_t>(room->numCoveredTiles());
        const uint32_t places = (tileCount + tilesPerCleaner - 1) / tilesPerCleaner;
        for(uint32_t slot = 0; slot < places; ++slot)
            appendTile(targets, WorkerJob::clean, WorkerTargetKind::room, dirtyTile, nullptr, slot);
    }
}

//! \brief Adds affordable trap reloads, including a tile already held by a worker.
void collectReloads(WorkerTargetLists& targets, Seat& seat, const std::vector<Creature*>& workers)
{
    for(Trap* trap : seat.getGameMap()->getTraps())
    {
        if(trap->getSeat() != &seat || seat.getGold() < trap->getReloadPrice())
            continue;
        for(Tile* tile : trap->getCoveredTiles())
        {
            if(!reachable(workers, *tile))
                continue;
            Creature* reserved = trap->getReloadWorker(tile);
            for(Creature* worker : workers)
            {
                if(trap->canBeReloadedByWorker(tile, reserved != nullptr ? reserved : worker))
                {
                    appendTile(targets, WorkerJob::reload, WorkerTargetKind::reload, tile);
                    break;
                }
            }
        }
    }
}

//! \brief Checks whether an entity has a reachable accepting destination for a worker.
bool hasCarryDestination(Creature& worker, GameEntity& entity, const std::vector<Building*>& buildings)
{
    GameMap* map = worker.getGameMap();
    Tile* start = worker.getPositionTile();
    if(start == nullptr)
        return false;
    if(entity.getObjectType() == GameEntityType::missileObject)
    {
        MissileStone* stone = dynamic_cast<MissileStone*>(&entity);
        if(stone != nullptr)
        {
            Tile* destination = stone->getDeliveryTile(worker);
            return destination != nullptr && map->pathExists(&worker, start, destination);
        }
    }
    for(Building* building : buildings)
        if(building->hasCarryEntitySpot(&entity))
            return true;
    return false;
}

//! \brief Tests whether a lock belongs to a normal carry search of the keeper.
bool reservedByKeeper(GameEntity& entity, const std::vector<Creature*>& workers)
{
    for(Creature* worker : workers)
    {
        if(worker->getWorkerJob() != WorkerJob::carry)
            continue;
        bool normalSearch = false;
        bool reserved = false;
        for(const auto& action : worker->getActions())
        {
            if(action->getType() == CreatureActionType::searchEntityToCarry &&
               !static_cast<const CreatureActionSearchEntityToCarry*>(action.get())->isForced())
                normalSearch = true;
            else if(action->getType() == CreatureActionType::grabEntity &&
                    static_cast<const CreatureActionGrabEntity*>(action.get())->getGrabTarget() == &entity)
                reserved = true;
            else if(action->getType() == CreatureActionType::carryEntity &&
                    static_cast<const CreatureActionCarryEntity*>(action.get())->getCarriedTarget() == &entity)
                reserved = true;
        }
        if(normalSearch && reserved)
            return true;
    }
    return false;
}
//! \brief Adds each reachable classified carry entity once, including one already reserved.
void collectCarryTile(WorkerTargetLists& targets, Tile& tile, const std::vector<Creature*>& workers,
                      const std::vector<Creature*>& allWorkers,
                      const std::map<Creature*, std::vector<Building*>>& buildings)
{
    for(GameEntity* entity : tile.getEntitiesInTile())
    {
        if(entity == nullptr)
            continue;
        const auto& carries = targets[static_cast<uint32_t>(WorkerJob::carry)];
        if(std::any_of(carries.begin(), carries.end(), [&](const WorkerTarget& target) {
            return target.entityType == entity->getObjectType() && target.entityName == entity->getName();
        }))
            continue;
        if(entity->getCarryLock(*workers.front()) && !reservedByKeeper(*entity, allWorkers))
            continue;
        for(Creature* worker : workers)
        {
            const WorkerCarryEntry entry = classifyWorkerCarry(*entity, *worker);
            if(entry == WorkerCarryEntry::none || worker->getPositionTile() == nullptr ||
               (!entity->getCarryLock(*worker) && entity->getEntityCarryType(worker) == EntityCarryType::notCarryable) ||
               !territoryAllowed(*worker, tile) ||
               !worker->getGameMap()->pathExists(worker, worker->getPositionTile(), &tile) ||
               !hasCarryDestination(*worker, *entity, buildings.at(worker)))
                continue;
            targets[static_cast<uint32_t>(WorkerJob::carry)].push_back(WorkerTarget{
                WorkerTargetKind::carry, &tile, nullptr, 0, entity->getObjectType(), entity->getName(), entry});
            break;
        }
    }
}
}

namespace
{
//! \brief Keeps normal carry-job transports in their category while cargo is in flight.
void collectActiveCarries(WorkerTargetLists& targets, const std::vector<Creature*>& workers)
{
    std::vector<WorkerTarget>& carries = targets[static_cast<uint32_t>(WorkerJob::carry)];
    for(Creature* worker : workers)
    {
        if(worker->getWorkerJob() != WorkerJob::carry)
            continue;
        const CreatureActionCarryEntity* carry = nullptr;
        bool normalSearch = false;
        bool digSearch = false;
        for(const auto& action : worker->getActions())
        {
            if(action->getType() == CreatureActionType::carryEntity)
                carry = static_cast<const CreatureActionCarryEntity*>(action.get());
            else if(action->getType() == CreatureActionType::searchTileToDig)
                digSearch = true;
            else if(action->getType() == CreatureActionType::searchEntityToCarry &&
                    !static_cast<const CreatureActionSearchEntityToCarry*>(action.get())->isForced())
                normalSearch = true;
        }
        if(carry == nullptr || carry->isForced() || (!normalSearch && digSearch) ||
           carry->getCarriedTarget() == nullptr)
            continue;
        GameEntity* entity = carry->getCarriedTarget();
        const WorkerCarryEntry entry = classifyWorkerCarry(*entity, *worker);
        if(entry == WorkerCarryEntry::none)
            continue;
        const auto sameEntity = [&](const WorkerTarget& target) {
            return target.entityType == entity->getObjectType() && target.entityName == entity->getName();
        };
        if(std::find_if(carries.begin(), carries.end(), sameEntity) != carries.end())
            continue;
        carries.push_back(WorkerTarget{WorkerTargetKind::carry, worker->getPositionTile(), nullptr, 0,
                                       entity->getObjectType(), entity->getName(), entry});
    }
}
}

//! \brief Rebuilds the keeper's target lists and counts once for the current game turn.
void refreshWorkerTargets(Seat& seat)
{
    GameMap* map = seat.getGameMap();
    const std::vector<Creature*> workers = WorkerAllocation::countedWorkers(seat);
    const std::vector<Creature*> allWorkers = map->getCreaturesBySeat(&seat);
    WorkerTargetLists targets;
    std::map<Creature*, std::vector<Building*>> buildings;
    for(Creature* worker : workers)
        if(worker->getPositionTile() != nullptr)
            buildings.emplace(worker, map->getReachableBuildingsPerSeat(&seat, worker->getPositionTile(), worker));
    if(!workers.empty())
    {
        for(int32_t x = 0; x < map->getMapSizeX(); ++x)
            for(int32_t y = 0; y < map->getMapSizeY(); ++y)
            {
                Tile* tile = map->getTile(x, y);
                if(tile == nullptr)
                    continue;
                collectDig(targets, seat, *tile, workers);
                collectClaim(targets, seat, *tile, workers);
                collectCleaningTile(targets, seat, *tile, workers);
                collectCarryTile(targets, *tile, workers, allWorkers, buildings);
            }
        collectRooms(targets, seat, workers);
        collectReloads(targets, seat, workers);
    }
    collectActiveCarries(targets, allWorkers);
    std::array<uint32_t, 6> counts{{0, 0, 0, 0, 0, 0}};
    for(uint32_t job = 0; job < counts.size(); ++job)
        counts[job] = static_cast<uint32_t>(targets[job].size());
    seat.setWorkerJobTargets(counts);
    seat.setWorkerTargetLists(std::move(targets));
}
