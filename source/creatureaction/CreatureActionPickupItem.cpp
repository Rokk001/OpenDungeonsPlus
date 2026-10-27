#include "creatureaction/CreatureActionPickupItem.h"
#include "creatureaction/CreatureActionStealItem.h"

#include "entities/Creature.h"
#include "entities/GameEntityType.h"
#include "entities/ItemBagEntity.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomType.h"
#include "rooms/RoomMerchant.h"

//! \brief Binds ordinary floor pickup to the shared transfer handler.
// allowed-lambda: CreatureAction requires the existing std::function action interface.
std::function<bool()> CreatureActionPickupItem::action()
{ return std::bind(&CreatureActionPickupItem::handle, std::ref(mCreature), false); }

//! \brief Binds enemy looting to the same walk-and-transfer handler.
// allowed-lambda: CreatureAction requires the existing std::function action interface.
std::function<bool()> CreatureActionStealItem::action()
{ return std::bind(&CreatureActionPickupItem::handle, std::ref(mCreature), true); }

//! \brief Selects the closest visible eligible bag and spends the arrival turn taking it.
bool CreatureActionPickupItem::handle(Creature& creature, bool stealing)
{
    Tile* ownTile = creature.getPositionTile();
    if(ownTile == nullptr || creature.isActionInList(CreatureActionType::fight))
    {
        creature.popAction();
        return true;
    }
    bool freeSlot = false;
    for(const std::unique_ptr<ItemInstance>& item : creature.getInventory())
        if(item.get() == nullptr) freeSlot = true;
    if(!freeSlot)
    {
        creature.popAction();
        return true;
    }
    if(stealing)
    {
        Tile* table = nullptr;
        std::unique_ptr<ItemInstance> goods = RoomMerchant::stealGoods(creature, table);
        if(goods.get() != nullptr)
        {
            if(goods->mQuality == Quality::epic)
                RoomMerchant::announceDeal(creature, *goods, 5);
            creature.acceptItem(std::move(goods));
            creature.popAction();
            return false;
        }
        if(table != nullptr)
            return false;
    }
    ItemBagEntity* target = nullptr;
    for(Tile* tile : creature.getVisibleTiles())
    {
        if(!creature.getGameMap()->pathExists(&creature, ownTile, tile))
            continue;
        for(GameEntity* entity : tile->getEntitiesInTile())
        {
            if(entity->getObjectType() != GameEntityType::itemBagEntity)
                continue;
            ItemBagEntity* bag = static_cast<ItemBagEntity*>(entity);
            const ItemInstance* item = bag->getItem();
            if(item == nullptr || bag->getCarryLock(creature))
                continue;
            const bool enemy = bag->getSeat() != nullptr && !creature.getSeat()->isAlliedSeat(bag->getSeat());
            if(stealing && !enemy)
                continue;
            if(item->mMerchantGoods && !enemy)
                continue;
            const bool sellable = (item->mSoulCrystal || item->mQuality != Quality::poor || !item->mPotionId.empty()) &&
                !creature.getGameMap()->getRoomsByTypeAndSeat(RoomType::merchant, creature.getSeat()).empty();
            if(creature.rateItem(*item) <= 0.0 && !sellable && !stealing)
                continue;
            target = bag;
            break;
        }
        if(target != nullptr)
            break;
    }
    if(target == nullptr)
    {
        creature.popAction();
        return true;
    }
    Tile* targetTile = target->getPositionTile();
    if(targetTile != ownTile)
    {
        if(!creature.setDestination(targetTile))
            creature.popAction();
        return false;
    }
    std::unique_ptr<ItemInstance> item = target->takeItem();
    item->mMerchantGoods = false;
    if(item->mQuality == Quality::epic)
        RoomMerchant::announceDeal(creature, *item, 5);
    creature.acceptItem(std::move(item));
    target->removeFromGameMap();
    target->deleteYourself();
    creature.popAction();
    return false;
}
