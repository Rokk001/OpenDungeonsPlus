#include "game/WorkerJobs.h"

#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntity.h"
#include "entities/GameEntityType.h"
#include "entities/MissileStone.h"
#include "game/Seat.h"

//! \brief Classifies a carryable entity for the carrier's keeper, excluding allied living patients.
WorkerCarryEntry classifyWorkerCarry(GameEntity& entity, Creature& carrier)
{
    if(entity.getObjectType() == GameEntityType::creature)
    {
        Creature& patient = static_cast<Creature&>(entity);
        if(patient.getDefinition()->isWorker() || patient.getDefinition()->isUndead()) return WorkerCarryEntry::none;
        if(!patient.isAlive()) return patient.getEntityCarryType(&carrier) == EntityCarryType::corpse ? WorkerCarryEntry::corpse : WorkerCarryEntry::none;
        if(patient.getKoTurnCounter() >= 0) return WorkerCarryEntry::none;
        if(patient.getSeat() == carrier.getSeat()) return WorkerCarryEntry::ownKnockedOut;
        if(carrier.getSeat() == nullptr || (patient.getSeat() != nullptr && carrier.getSeat()->isAlliedSeat(patient.getSeat()))) return WorkerCarryEntry::none;
        return WorkerCarryEntry::enemyKnockedOut;
    }
    switch(entity.getObjectType())
    {
        case GameEntityType::treasuryObject: return WorkerCarryEntry::gold;
        case GameEntityType::itemBagEntity:
        case GameEntityType::herbBundleEntity: return WorkerCarryEntry::items;
        case GameEntityType::giftBoxEntity: return WorkerCarryEntry::giftBoxes;
        case GameEntityType::craftedTrap: return WorkerCarryEntry::trapsDoors;
        case GameEntityType::missileObject:
            return dynamic_cast<MissileStone*>(&entity) != nullptr ? WorkerCarryEntry::giftBoxes : WorkerCarryEntry::none;
        default: return WorkerCarryEntry::none;
    }
}
