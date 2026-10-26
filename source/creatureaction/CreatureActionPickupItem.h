#ifndef CREATUREACTIONPICKUPITEM_H
#define CREATUREACTIONPICKUPITEM_H

#include "creatureaction/CreatureAction.h"

//! \brief Walks to a visible wanted item bag and transfers its single instance to the creature.
class CreatureActionPickupItem : public CreatureAction
{
public:
    //! \brief Creates a pickup action without retaining pointers to bags that can disappear.
    explicit CreatureActionPickupItem(Creature& creature) : CreatureAction(creature) {}
    //! \brief Returns the appended pickup action type.
    CreatureActionType getType() const override { return CreatureActionType::pickupItem; }
    //! \brief Binds this action to the shared safe bag-transfer implementation.
    // allowed-lambda: CreatureAction requires the existing std::function action interface.
    std::function<bool()> action() override;
    //! \brief Walks to a reachable bag; true means the action ended, false means it keeps running.
    static bool handle(Creature& creature, bool stealing);
};

#endif
