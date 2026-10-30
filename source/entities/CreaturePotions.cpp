#include "entities/Creature.h"

#include "ODApplication.h"
#include "creatureaction/CreatureAction.h"
#include "creatureeffect/CreatureEffect.h"
#include "creatureeffect/CreatureEffectPotion.h"
#include "creatureeffect/CreatureEffectStrengthChange.h"
#include "creatureskill/CreatureSkill.h"
#include "entities/ItemInstance.h"
#include "entities/PotionDefinition.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "game/Player.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "gamemap/GameMap.h"
#include "gamemap/Pathfinding.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <memory>
#include <string>

namespace
{
static const double PERCENT = 100.0;
static const std::string POTION_SOURCE = "potion:";
static const std::string DRINK_SOUND = "Creatures/Default/Drink";

//! \brief Returns whether this potion kind is a temporary combat enhancement.
bool isPotionBuff(const std::string& kind)
{
    return kind == "StrengthChange" || kind == "DexterityChange" || kind == "DefenseChange" ||
        kind == "MaxHPChange" || kind == "MaxManaChange" || kind == "HealPerTenSeconds" ||
        kind == "ManaRegenChange";
}
}

//! \brief Checks the actual effect sources, including the existing strength-change effect.
bool Creature::hasPotionEffect(const std::string& kind) const
{
    for(const EntityParticleEffect* entry : mEntityParticleEffects)
    {
        if(entry->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;
        const CreatureParticleEffect* running = static_cast<const CreatureParticleEffect*>(entry);
        if(running->mEffect->getSourceId() == POTION_SOURCE + kind && running->mEffect->getNbTurnsEffect() > 0.0)
            return true;
    }
    return false;
}

//! \brief Uses the recipe's real effect and consumes only a valid potion owned by this creature.
bool Creature::drinkPotion(std::unique_ptr<ItemInstance>& item)
{
    if(item.get() == nullptr || item->mPotionId.empty() || !getIsOnServerMap() || !isAlive())
        return false;
    const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(item->mPotionId);
    if(potion == nullptr || potion->getLevelMin() > getLevel())
        return false;
    const double duration = potion->getDuration() * ODApplication::turnsPerSecond;
    if(potion->getDuration() <= 0.0)
        CreatureEffectPotion::applyInstant(*this, potion->getKind(), potion->getValue());
    else
    {
        CreatureEffect* effect = nullptr;
        if(potion->getKind() == "StrengthChange")
            effect = new CreatureEffectStrengthChange(duration, potion->getValue(), "");
        else
            effect = new CreatureEffectPotion(duration, potion->getKind(), potion->getValue());
        effect->setSourceId(POTION_SOURCE + potion->getKind());
        addCreatureEffect(effect);
    }
    item.reset();
    itemsChanged();
    Tile* tile = getPositionTile();
    if(tile != nullptr)
        for(Seat* seat : tile->getSeatsWithVision())
            if(seat->getPlayer() != nullptr && seat->getPlayer()->getIsHuman())
            {
                ServerNotification* sound = new ServerNotification(ServerNotificationType::playSpatialSound, seat->getPlayer());
                sound->mPacket << DRINK_SOUND << tile->getX() << tile->getY();
                ODServer::getSingleton().queueServerNotification(sound);
            }
    return true;
}

//! \brief Implements the gift's immediate-use, potion-slot and inventory priorities without taking failed gifts.
bool Creature::receiveGiftedPotion(std::unique_ptr<ItemInstance>& item)
{
    if(item.get() == nullptr || item->mPotionId.empty())
        return false;
    const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(item->mPotionId);
    if(potion == nullptr)
        return false;
    const std::string& kind = potion->getKind();
    const bool useful = (kind == "HealPercent" && getHP() < getMaxHp()) ||
        (kind == "ManaPercent" && getCurrentMana() < getMaxMana()) ||
        (kind == "EndFreeze" && isFrozen()) ||
        (isPotionBuff(kind) && isActionInList(CreatureActionType::fight));
    if(useful && drinkPotion(item))
        return true;
    resizePotionSlots();
    for(std::unique_ptr<ItemInstance>& slot : mPotionSlots)
    {
        if(slot.get() != nullptr)
            continue;
        slot = std::move(item);
        itemsChanged();
        return true;
    }
    for(std::unique_ptr<ItemInstance>& slot : mInventory)
    {
        if(slot.get() != nullptr)
            continue;
        slot = std::move(item);
        itemsChanged();
        return true;
    }
    return false;
}

//! \brief Refills outside combat, drinks resources and buffs only in actual combat, and permits thawing on every turn.
void Creature::decidePotion()
{
    if(!getIsOnServerMap() || !isAlive() || !getIsOnMap())
        return;
    resizePotionSlots();
    const bool fighting = isActionInList(CreatureActionType::fight);
    if(!fighting)
    {
        for(std::unique_ptr<ItemInstance>& slot : mPotionSlots)
        {
            if(slot.get() != nullptr)
                continue;
            for(std::unique_ptr<ItemInstance>& stored : mInventory)
            {
                if(stored.get() == nullptr || stored->mPotionId.empty())
                    continue;
                const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(stored->mPotionId);
                if(potion == nullptr || potion->getLevelMin() > getLevel())
                    continue;
                slot = std::move(stored);
                itemsChanged();
                break;
            }
        }
    }
    bool enemyInRange = false;
    Tile* ownTile = getPositionTile();
    for(Creature* enemy : getGameMap()->getCreatures())
    {
        if(enemy == this || !enemy->getIsOnMap() || !enemy->isAlive() || enemy->isInvisible() ||
           getSeat()->isAlliedSeat(enemy->getSeat()) || enemy->getSeat() == getSeat())
            continue;
        Tile* tile = enemy->getPositionTile();
        if(tile == nullptr || ownTile == nullptr ||
           std::find(mVisibleTiles.begin(), mVisibleTiles.end(), tile) == mVisibleTiles.end())
            continue;
        const int squaredDistance = Pathfinding::squaredDistanceTile(*tile, *ownTile);
        for(const CreatureSkillData& data : mSkillData)
        {
            if(!data.mSkill->canBeUsedBy(this))
                continue;
            const double range = data.mSkill->getRangeMax(this, enemy);
            if(range > 0.0 && squaredDistance <= range * range)
            {
                enemyInRange = true;
                break;
            }
        }
        if(enemyInRange)
            break;
    }
    const bool combatRange = fighting && enemyInRange;
    const bool combatStart = combatRange && !mPotionEnemyInRange;
    mPotionEnemyInRange = combatRange;
    const double healBelow = ConfigManager::getSingleton().getItemSetting("Potions", "PotionDrinkHpBelow");
    for(std::unique_ptr<ItemInstance>& slot : mPotionSlots)
    {
        if(slot.get() == nullptr || slot->mPotionId.empty())
            continue;
        const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(slot->mPotionId);
        if(potion == nullptr || potion->getLevelMin() > getLevel())
            continue;
        const std::string& kind = potion->getKind();
        const double hpShare = getMaxHp() > 0.0 ? getHP() / getMaxHp() : 1.0;
        const double manaShare = getMaxMana() > 0.0 ? getCurrentMana() / getMaxMana() : 1.0;
        bool useful = (kind == "HealPercent" && fighting && hpShare < healBelow) ||
            (kind == "FullRestore" && fighting && (hpShare < ConfigManager::getSingleton().getItemSetting("Potions", "LifespringLowHpShare") ||
                (hpShare < ConfigManager::getSingleton().getItemSetting("Potions", "LifespringHpShare") && manaShare < ConfigManager::getSingleton().getItemSetting("Potions", "LifespringManaShare")))) ||
            (kind == "EndFreeze" && isFrozen()) ||
            (isPotionBuff(kind) && combatStart && !hasPotionEffect(kind));
        if(kind == "ManaPercent" && fighting && manaShare < ConfigManager::getSingleton().getItemSetting("Potions", "PotionManaDrinkShare"))
        {
            const double after = std::min(getMaxMana(), getCurrentMana()+getMaxMana()*potion->getValue()/PERCENT);
            for(const CreatureSkillData& data : mSkillData)
            {
                if(!data.mSkill->canBeUsedBy(this))
                    continue;
                const double cost = getSkillManaCost(*data.mSkill);
                if(cost > getCurrentMana() && cost <= after)
                    useful = true;
            }
        }
        if(useful)
            drinkPotion(slot);
    }
}
