#include "game/CreatureMerchantAI.h"

#include "creatureaction/CreatureActionBuyItem.h"
#include "creatureaction/CreatureActionSellItem.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/ItemBagEntity.h"
#include "entities/PotionDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomArena.h"
#include "rooms/RoomMerchant.h"
#include "utils/ConfigManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

#include <algorithm>

namespace
{
static const double TRADE_CHANCE = 0.3;
static const double PERCENT = 100.0;
//! \brief Orders usable potions by the approved healing, group buff, and mana priorities.
enum class PotionPriority { other, mana, groupBuff, healing };
//! \brief Finds the priority of one potion for this wearer's group.
PotionPriority potionPriority(const Creature& creature, const ItemInstance& item)
{
    const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(item.mPotionId);
    if(potion == nullptr) return PotionPriority::other;
    if(potion->getKind() == "HealPercent") return PotionPriority::healing;
    const std::string& group = creature.getDefinition()->getSkillGroup();
    std::string buff = "MaxHPChange";
    if(group == "blocker" || group == "blitzer") buff = "StrengthChange";
    else if(group == "flanker" || group == "archer") buff = "DexterityChange";
    else if(group == "caster") buff = "MaxManaChange";
    if(potion->getKind() == buff) return PotionPriority::groupBuff;
    if(potion->getKind() == "ManaPercent") return PotionPriority::mana;
    return PotionPriority::other;
}

//! \brief Offers one gift to its specific recipient without losing a full-inventory potion.
bool deliverGift(Creature& creature, ItemBagEntity& bag)
{
    const ItemInstance* offered = bag.getItem();
    if(offered == nullptr) return false;
    const ItemInstance copy = *offered;
    std::unique_ptr<ItemInstance> item = bag.takeItem();
    item->mGifted = false;
    bool consumed = true;
    if(!item->mPotionId.empty()) consumed = creature.receiveGiftedPotion(item);
    else creature.acceptItem(std::move(item), true);
    creature.addMerchantMood(ConfigManager::getSingleton().getRoomConfigDouble("MerchantGiftMood"));
    RoomMerchant::announceDeal(creature, copy, 4);
    if(!consumed)
    {
        item->mGifted = true;
        bag.restoreItem(std::move(item));
        return false;
    }
    bag.removeFromGameMap();
    bag.deleteYourself();
    return true;
}
}

//! \brief Tries the independent thirty-percent sale and purchase decisions outside combat.
bool CreatureMerchantAI::decideTrade(Creature& creature)
{
    if(!creature.getIsOnServerMap() || creature.isActionInList(CreatureActionType::fight) || creature.getSeat() == nullptr)
        return false;
    const int32_t slot = RoomMerchant::findSaleSlot(creature);
    if(slot >= 0 && !creature.hasActionBeenTried(CreatureActionType::sellItem) && Random::Double(0.0, 1.0) < TRADE_CHANCE)
        for(Room* base : creature.getGameMap()->getRoomsByTypeAndSeat(RoomType::merchant, creature.getSeat()))
        {
            RoomMerchant* room = static_cast<RoomMerchant*>(base);
            if(room->getFreeTable() != nullptr)
            {
                creature.pushAction(Utils::make_unique<CreatureActionSellItem>(creature, room->getName(), static_cast<uint32_t>(slot)));
                return true;
            }
        }
    if(creature.hasActionBeenTried(CreatureActionType::buyItem) || Random::Double(0.0, 1.0) >= TRADE_CHANCE) return false;
    const MerchantStockEntry* best = nullptr;
    const std::vector<MerchantStockEntry> stock = RoomMerchant::getStock(*creature.getGameMap(), creature.getSeat());
    for(const MerchantStockEntry& entry : stock)
    {
        const ItemInstance& item = entry.mGood->mItem;
        const double price = item.getPrice(creature.getGameMap()) * (1.0 + creature.getSeat()->getMerchantMargin() / PERCENT)
            * std::max(0.0, 1.0 - creature.getItemEffect("Thrift") / PERCENT);
        if(entry.mGood->mReservedBy != creature.getName() || !RoomMerchant::wantsItem(creature, item)
            || creature.getGoldCarriedAmount() < price) continue;
        if(best == nullptr) { best = &entry; continue; }
        if(!item.mPotionId.empty() && !best->mGood->mItem.mPotionId.empty())
        {
            if(potionPriority(creature, item) > potionPriority(creature, best->mGood->mItem)) best = &entry;
        }
        else if(creature.rateItem(item) > creature.rateItem(best->mGood->mItem)) best = &entry;
    }
    if(best == nullptr) return false;
    creature.pushAction(Utils::make_unique<CreatureActionBuyItem>(creature, best->mRoom->getName(), best->mGood->mIndex));
    return true;
}

//! \brief Gives the bag to the first own creature on its tile, except while its arena fight is running.
bool CreatureMerchantAI::offerGift(ItemBagEntity& bag, Tile& tile)
{
    if(bag.getItem() == nullptr || !bag.getItem()->mGifted || bag.getSeat() == nullptr) return false;
    Room* room = tile.getCoveringRoom();
    if(room != nullptr && room->getType() == RoomType::arena && static_cast<RoomArena*>(room)->hasRunningFight())
        return false;
    const std::vector<GameEntity*> entities = tile.getEntitiesInTile();
    for(GameEntity* entity : entities)
        if(entity->getObjectType() == GameEntityType::creature && entity->getSeat() == bag.getSeat())
            return deliverGift(*static_cast<Creature*>(entity), bag);
    return false;
}

//! \brief Awards all pending arena gifts to its actual last-standing winner.
void CreatureMerchantAI::collectArenaGifts(Creature& winner)
{
    Tile* position = winner.getPositionTile();
    Room* room = position == nullptr ? nullptr : position->getCoveringRoom();
    if(room == nullptr || room->getType() != RoomType::arena) return;
    for(Tile* tile : room->getCoveredTiles())
    {
        const std::vector<GameEntity*> entities = tile->getEntitiesInTile();
        for(GameEntity* entity : entities)
        {
            if(entity->getObjectType() != GameEntityType::itemBagEntity || entity->getSeat() != winner.getSeat()) continue;
            ItemBagEntity* bag = static_cast<ItemBagEntity*>(entity);
            if(bag->getItem() != nullptr && bag->getItem()->mGifted) deliverGift(winner, *bag);
        }
    }
}
