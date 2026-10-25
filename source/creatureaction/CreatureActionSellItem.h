#ifndef CREATUREACTIONSELLITEM_H
#define CREATUREACTIONSELLITEM_H

#include "creatureaction/CreatureAction.h"
#include <string>

//! \brief Walks to a merchant table and sells one unwanted inventory item in one work turn.
class CreatureActionSellItem : public CreatureAction
{
public:
    //! \brief Retains a room name and inventory slot without keeping a room pointer alive.
    CreatureActionSellItem(Creature& creature, const std::string& room, uint32_t slot);
    //! \brief Returns the appended sale action type.
    CreatureActionType getType() const override;
    //! \brief Binds a sale step using the existing creature action dispatcher.
    // allowed-lambda: CreatureAction requires the existing std::function action interface.
    std::function<bool()> action() override;
    //! \brief Walks to a valid free table and completes or abandons this sale.
    static bool handle(Creature& creature, const std::string& room, uint32_t slot);
private:
    std::string mRoom;
    uint32_t mSlot;
};
#endif // CREATUREACTIONSELLITEM_H
