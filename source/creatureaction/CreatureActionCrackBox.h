#ifndef CREATUREACTIONCRACKBOX_H
#define CREATUREACTIONCRACKBOX_H

#include "creatureaction/CreatureActionUseRoom.h"

//! \brief Uses the workshop's ordinary work cycle while identifying an item-box cracking job.
class CreatureActionCrackBox : public CreatureActionUseRoom
{
public:
    //! \brief Reserves a workshop work position through the existing room-action lifecycle.
    CreatureActionCrackBox(Creature& creature, Room& room, bool forced) : CreatureActionUseRoom(creature, room, forced) {}
    //! \brief Returns the appended box-cracking action type.
    CreatureActionType getType() const override { return CreatureActionType::crackBox; }
};

#endif
