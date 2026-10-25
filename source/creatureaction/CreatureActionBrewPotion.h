#ifndef CREATUREACTIONBREWPOTION_H
#define CREATUREACTIONBREWPOTION_H
#include "creatureaction/CreatureActionUseRoom.h"

//! \brief Brews a laboratory recipe through the existing room-work lifecycle.
class CreatureActionBrewPotion : public CreatureActionUseRoom
{
public:
    //! \brief Reserves a cauldron for this creature.
    CreatureActionBrewPotion(Creature& creature, Room& room, bool forced) :
        CreatureActionUseRoom(creature, room, forced) {}
    //! \brief Identifies brewing in the creature's action list.
    CreatureActionType getType() const override { return CreatureActionType::brewPotion; }
};
#endif
