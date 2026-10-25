#include "creatureaction/CreatureActionSellItem.h"
#include "entities/Creature.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomMerchant.h"

//! \brief Stores a stable room name and the inventory slot selected by the idle decision.
CreatureActionSellItem::CreatureActionSellItem(Creature& creature, const std::string& room, uint32_t slot) :
    CreatureAction(creature), mRoom(room), mSlot(slot) {}
//! \brief Identifies merchant sale work in the creature action queue.
CreatureActionType CreatureActionSellItem::getType() const { return CreatureActionType::sellItem; }
//! \brief Supplies one sale step without capturing a destructible room pointer.
// allowed-lambda: CreatureAction requires the existing std::function action interface.
std::function<bool()> CreatureActionSellItem::action()
{ return std::bind(&CreatureActionSellItem::handle, std::ref(mCreature), mRoom, mSlot); }
//! \brief Approaches a live table and sells once; true means this action ended.
bool CreatureActionSellItem::handle(Creature& creature, const std::string& name, uint32_t slot)
{
    for(Room* base : creature.getGameMap()->getRoomsByTypeAndSeat(RoomType::merchant, creature.getSeat()))
    {
        if(base->getName() != name) continue;
        RoomMerchant* room = static_cast<RoomMerchant*>(base);
        const MerchantApproach state = room->approachTable(creature, room->getFreeTable());
        if(state == MerchantApproach::walking) return false;
        const bool traded = state == MerchantApproach::ready && room->buyFromCreature(creature, slot);
        room->releaseInteractionPosition(&creature);
        creature.popAction();
        return !traded;
    }
    creature.popAction();
    return true;
}
