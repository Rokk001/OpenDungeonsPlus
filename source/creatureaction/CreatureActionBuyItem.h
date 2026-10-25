#ifndef CREATUREACTIONBUYITEM_H
#define CREATUREACTIONBUYITEM_H

#include "creatureaction/CreatureAction.h"
#include <string>

//! \brief Walks to the reserved merchant good and buys it if it is still wanted and affordable.
class CreatureActionBuyItem : public CreatureAction
{
public:
    //! \brief Retains the selected room name and stable goods index.
    CreatureActionBuyItem(Creature& creature, const std::string& room, uint32_t index);
    //! \brief Returns the appended purchase action type.
    CreatureActionType getType() const override;
    //! \brief Binds one purchase step through the existing action dispatcher.
    std::function<bool()> action() override;
    //! \brief Approaches the table and buys once; true means this action ended.
    static bool handle(Creature& creature, const std::string& room, uint32_t index);
private:
    std::string mRoom;
    uint32_t mIndex;
};
#endif // CREATUREACTIONBUYITEM_H
