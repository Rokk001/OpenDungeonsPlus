#include "creatureaction/CreatureActionBuyItem.h"
#include "entities/Creature.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomMerchant.h"

//! \brief Stores only stable identities for goods whose reservation can expire during the walk.
CreatureActionBuyItem::CreatureActionBuyItem(Creature& creature, const std::string& room, uint32_t index) :
    CreatureAction(creature), mRoom(room), mIndex(index) {}
//! \brief Identifies merchant purchase work in the creature action queue.
CreatureActionType CreatureActionBuyItem::getType() const { return CreatureActionType::buyItem; }
//! \brief Supplies one purchase step without retaining a deleted room pointer.
// allowed-lambda: CreatureAction requires the existing std::function action interface.
std::function<bool()> CreatureActionBuyItem::action()
{ return std::bind(&CreatureActionBuyItem::handle, std::ref(mCreature), mRoom, mIndex); }
//! \brief Approaches a still-existing table and validates the purchase again on arrival.
bool CreatureActionBuyItem::handle(Creature& creature, const std::string& name, uint32_t index)
{
    for(Room* base : creature.getGameMap()->getRoomsByTypeAndSeat(RoomType::merchant, creature.getSeat()))
    {
        if(base->getName() != name) continue;
        RoomMerchant* room = static_cast<RoomMerchant*>(base);
        Tile* tile = nullptr;
        const MerchantGood* good = room->findGood(index, tile);
        if(good == nullptr) break;
        const MerchantApproach state = room->approachTable(creature, tile);
        if(state == MerchantApproach::walking) return false;
        const bool traded = state == MerchantApproach::ready && room->sellToCreature(creature, index);
        room->releaseInteractionPosition(&creature);
        creature.popAction();
        return !traded;
    }
    creature.popAction();
    return true;
}
