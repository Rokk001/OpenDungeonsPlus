#include "ai/AiItems.h"

#include "ai/AiActions.h"
#include "ai/AiMind.h"
#include "ai/AiTraps.h"
#include "ai/KeeperAI.h"
#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GiftBoxEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "rooms/RoomMerchant.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <vector>

namespace ITEMS
{
//! \brief Records catalogue rows without a keeper command.
void classNRows(KeeperAI&)
{
    // AI row D11
    // AI row E14
    // AI row G03
    // AI row H01
}

//! \brief Evaluates one firing of the special row, drawing its mistake once for all held types.
void useStoredSpecial(KeeperAI& ai, const AiEvent& event, bool fightSession, bool periodicLook, bool afterSpell)
{
    // AI row H03
    Seat* seat = ai.getControlledPlayer().getSeat();
    ConfigManager& config = ConfigManager::getSingleton();
    const bool mistaken = ai.getMind().slip("H03");
    bool upset = false;
    bool wounded = false;
    bool enemyVisible = false;
    for(Creature* creature : ai.getGameMap().getCreatures())
    {
        if(!creature->isAlive())
            continue;
        if(creature->getSeat() == seat)
        {
            upset = upset || creature->getMoodValue() >= CreatureMoodLevel::Upset;
            wounded = wounded || (!creature->getDefinition()->isWorker() &&
                creature->getHP() < config.getAiConfigDouble("HealBelow") * creature->getMaxHp());
            continue;
        }
        Tile* tile = creature->getPositionTile();
        if(creature->getSeat() == nullptr || seat->isAlliedSeat(creature->getSeat()) || tile == nullptr)
            continue;
        const std::vector<Seat*>& vision = tile->getSeatsWithVision();
        enemyVisible = enemyVisible || std::find(vision.begin(), vision.end(), seat) != vision.end();
    }
    const GiftBoxType types[] = {GiftBoxType::mana, GiftBoxType::gold, GiftBoxType::revealMap,
        GiftBoxType::levelUp, GiftBoxType::healAll, GiftBoxType::makeSafe, GiftBoxType::makeHappy,
        GiftBoxType::receiveWorkers, GiftBoxType::weakenWalls, GiftBoxType::stunWorkers,
        GiftBoxType::makeUnhappy, GiftBoxType::killCreatures};
    for(GiftBoxType type : types)
    {
        if(seat->getNbStoredSpecials(static_cast<uint32_t>(type)) == 0)
            continue;
        bool use = mistaken;
        const double amount = seat->getStoredSpecialAmount(type);
        switch(type)
        {
            case GiftBoxType::mana:
                use = use || seat->getMana() + amount <= config.getMaxManaPerSeat() || afterSpell;
                break;
            case GiftBoxType::gold:
                use = use || seat->getGold() + amount <= seat->getGoldMax() || periodicLook;
                break;
            case GiftBoxType::healAll: use = use || (fightSession && wounded); break;
            case GiftBoxType::makeHappy: use = use || upset; break;
            case GiftBoxType::weakenWalls: use = use || event.type == AiEventType::Start; break;
            case GiftBoxType::stunWorkers:
            case GiftBoxType::makeUnhappy: use = use || event.type == AiEventType::Launch; break;
            case GiftBoxType::killCreatures: use = use || (fightSession && enemyVisible); break;
            default: use = true; break;
        }
        if(use)
            ACTS::useSpecial(ai, type);
    }
}

//! \brief Keeps the wage and building reserves when choosing the strongest fighter's merchant gift.
void buyForStrongest(KeeperAI& ai)
{
    // AI row H04
    Player& player = ai.getControlledPlayer();
    Seat* seat = player.getSeat();
    Creature* strongest = nullptr;
    double bill = 0.0;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(seat))
    {
        if(!creature->isAlive() || creature->getDefinition()->isWorker())
            continue;
        bill += creature->getDefinition()->getFee(creature->getLevel()) + creature->getGoldFee();
        if(creature->getIsOnMap() && !creature->isInContainment() &&
           (strongest == nullptr || creature->getHP() * creature->getRawDamagePerSecond() >
               strongest->getHP() * strongest->getRawDamagePerSecond()))
            strongest = creature;
    }
    if(strongest == nullptr || player.numObjectsInHand() != 0)
        return;
    Tile* tile = strongest->getPositionTile();
    if(tile == nullptr || !tile->isClaimedForSeat(seat))
        return;
    bool freeSlot = false;
    for(const std::unique_ptr<ItemInstance>& item : strongest->getInventory())
        freeSlot = freeSlot || item.get() == nullptr;
    if(!freeSlot)
        return;
    const bool mistaken = ai.getMind().slip("H04");
    const double budget = seat->getGold() - bill -
        ConfigManager::getSingleton().getAiConfigDouble("RoomGoldMargin") - TRAP::reloadMargin(ai);
    const std::vector<MerchantStockEntry> stock = RoomMerchant::getStock(ai.getGameMap(), seat);
    const MerchantStockEntry* best = nullptr;
    double bestPrice = 0.0;
    for(const MerchantStockEntry& entry : stock)
    {
        const double price = entry.mGood->mItem.getPrice(&ai.getGameMap());
        if(price > budget || (!mistaken && !RoomMerchant::wantsItem(*strongest, entry.mGood->mItem)))
            continue;
        if(best == nullptr || price > bestPrice)
        {
            best = &entry;
            bestPrice = price;
        }
    }
    if(best == nullptr)
        return;
    ODPacket packet;
    packet << best->mGood->mIndex;
    ACTS::merchantBuy(ai, packet);
    ACTS::drop(ai, tile);
}
}
