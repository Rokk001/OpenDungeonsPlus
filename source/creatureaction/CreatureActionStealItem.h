#ifndef CREATUREACTIONSTEALITEM_H
#define CREATUREACTIONSTEALITEM_H

#include "creatureaction/CreatureAction.h"

//! \brief Loots an enemy bag, including sealed merchant goods and treasury storage.
class CreatureActionStealItem : public CreatureAction
{
public:
    //! \brief Creates a theft action without holding a stale target pointer.
    explicit CreatureActionStealItem(Creature& creature) : CreatureAction(creature) {}
    //! \brief Returns the appended item theft type.
    CreatureActionType getType() const override { return CreatureActionType::stealItem; }
    //! \brief Binds the enemy-bag form of the shared pickup implementation.
    // allowed-lambda: CreatureAction requires the existing std::function action interface.
    std::function<bool()> action() override;
};

#endif
