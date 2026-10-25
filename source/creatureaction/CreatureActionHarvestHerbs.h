#ifndef CREATUREACTIONHARVESTHERBS_H
#define CREATUREACTIONHARVESTHERBS_H
#include "creatureaction/CreatureActionUseRoom.h"

//! \brief Harvests garden beds through the existing room-work lifecycle.
class CreatureActionHarvestHerbs : public CreatureActionUseRoom
{
public:
    //! \brief Reserves a garden work place for this creature.
    CreatureActionHarvestHerbs(Creature& creature, Room& room, bool forced) :
        CreatureActionUseRoom(creature, room, forced) {}
    //! \brief Identifies harvesting in the creature's action list.
    CreatureActionType getType() const override { return CreatureActionType::harvestHerbs; }
};
#endif
