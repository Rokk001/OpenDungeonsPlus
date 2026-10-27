#include "entities/Creature.h"

#include "creatureaction/CreatureAction.h"
#include "entities/CreatureDefinition.h"
#include "entities/ItemBagEntity.h"
#include "entities/Tile.h"
#include "entities/Weapon.h"
#include "gamemap/GameMap.h"
#include "game/ItemDrops.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "spells/Spell.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cctype>
#include <limits>

namespace
{
static const double EQUIP_UPGRADE_MARGIN = 0.5;
static const double DROP_JITTER = 0.3;

//! \brief Compares skill path and family names using the skill tree's case-insensitive convention.
bool sameItemPath(const std::string& left, const std::string& right)
{
    if(left.size() != right.size())
        return false;
    for(size_t index = 0; index < left.size(); ++index)
        if(std::tolower(static_cast<unsigned char>(left[index])) != std::tolower(static_cast<unsigned char>(right[index])))
            return false;
    return true;
}

//! \brief Places a transferred instance on the creature's tile without changing its Epic registration.
void dropCreatureItem(Creature& creature, std::unique_ptr<ItemInstance> item)
{
    if(item.get() == nullptr)
        return;
    ItemBagEntity* bag = new ItemBagEntity(creature.getGameMap(), std::move(item));
    bag->setSeat(creature.getSeat());
    bag->addToGameMap();
    bag->createMesh();
    Ogre::Vector3 position = creature.getPosition();
    position.x += static_cast<Ogre::Real>(Random::Double(-DROP_JITTER, DROP_JITTER));
    position.y += static_cast<Ogre::Real>(Random::Double(-DROP_JITTER, DROP_JITTER));
    bag->setPosition(position);
}
}

//! \brief Resolves body slots or the matching spawn-weapon hand without allowing new weapon classes.
int32_t Creature::getItemEquipmentSlot(const ItemInstance& item) const
{
    if(item.mSoulCrystal || !item.mPotionId.empty())
        return -1;
    const ItemDefinition* definition = getGameMap()->getItemDefinition(item.mDefinitionId);
    if(definition == nullptr)
        return -1;
    const std::string& slot = definition->getSlot();
    if(slot == "head") return 2;
    if(slot == "armour") return 3;
    if(slot == "boots") return 4;
    if(slot == "ring") return 5;
    if(slot == "shield")
    {
        if(mWeaponL != nullptr && mWeaponL->getWeaponType() == "shield" && (mWeaponR == nullptr || mWeaponR->getHands() != 2))
            return 1;
        return -1;
    }
    if(slot == "weapon")
    {
        if(mWeaponR != nullptr && definition->getWeaponClass() == mWeaponR->getWeaponType())
            return 0;
        if(mWeaponL != nullptr && mWeaponL->getWeaponType() == "bow" && definition->getWeaponClass() == "bow")
            return 1;
    }
    return -1;
}

//! \brief Keeps weapons compatible with the spawn equipment and honours level gates.
bool Creature::isItemEquippable(const ItemInstance& item) const
{
    return getItemEquipmentSlot(item) >= 0 && getLevel() >= item.getLevelMin(getGameMap());
}

//! \brief Scores equipment bonuses and marks worthwhile crystals as wanted.
double Creature::rateItem(const ItemInstance& item) const
{
    if(item.mSoulCrystal)
        return wantsSoulCrystal(item.getPrice(getGameMap())) ? 1.0 : 0.0;
    if(!item.mPotionId.empty() || item.mQuality == Quality::poor)
        return 0.0;
    const ItemDefinition* definition = getGameMap()->getItemDefinition(item.mDefinitionId);
    if(definition == nullptr || getItemEquipmentSlot(item) < 0)
        return 0.0;
    const CreatureSkillTree::SkillTreeConfig& tree = ConfigManager::getSingleton().getCreatureSkillTree();
    const CreatureSkillTree::TemplateDef* templ = tree.findTemplate(mDefinition->getSkillGroup(), mSkillBuild.mTemplate);
    double pathWeight = 0.3;
    if(templ != nullptr && sameItemPath(definition->getPath(), templ->mPrimary))
        pathWeight = 1.0;
    else if(sameItemPath(definition->getPath(), mDefinition->getSkillFamily()))
        pathWeight = 0.8;
    else if(definition->getGroup() == mDefinition->getSkillGroup())
        pathWeight = 0.5;
    static const double QUALITY_RANKS[] = {0.0, 1.0, 3.0, 6.0};
    double rating = QUALITY_RANKS[static_cast<size_t>(item.mQuality)] + item.mEffects.size() * 2.0;
    for(const std::pair<std::string, double>& bonus : item.mBonuses)
    {
        if(!mDefinition->isWorker() && (bonus.first == "Dig%" || bonus.first == "Claim%" || bonus.first == "Carry%"))
            continue;
        rating += bonus.second * ConfigManager::getSingleton().getItemSetting("ItemRating", bonus.first) * pathWeight;
    }
    return rating;
}

//! \brief Equips an upgrade when safe, otherwise stores it and preserves all overflow as floor bags.
bool Creature::acceptItem(std::unique_ptr<ItemInstance> item, bool equip)
{
    bool equipped = false;
    if(item.get() == nullptr)
        return false;
    if(!item->mPotionId.empty())
    {
        if(!isActionInList(CreatureActionType::fight))
        {
            for(size_t index = 0; index < mPotionSlots.size(); ++index)
            {
                if(mPotionSlots[index].get() == nullptr)
                {
                    setPotionSlot(index, std::move(item));
                    return true;
                }
            }
        }
    }
    else if(equip && !isActionInList(CreatureActionType::fight) && isItemEquippable(*item))
    {
        const size_t slot = static_cast<size_t>(getItemEquipmentSlot(*item));
        const double wornRating = mEquipment[slot].get() == nullptr ? 0.0 : rateItem(*mEquipment[slot]);
        if(rateItem(*item) > wornRating + EQUIP_UPGRADE_MARGIN)
        {
            item = setEquipment(slot, std::move(item));
            equipped = true;
            if(item.get() == nullptr)
                return true;
        }
    }
    for(size_t index = 0; index < mInventory.size(); ++index)
    {
        if(mInventory[index].get() == nullptr)
        {
            setInventorySlot(index, std::move(item));
            return true;
        }
    }
    size_t worstIndex = 0;
    double worstRating = std::numeric_limits<double>::max();
    for(size_t index = 0; index < mInventory.size(); ++index)
    {
        const double rating = rateItem(*mInventory[index]);
        if(rating < worstRating)
        {
            worstRating = rating;
            worstIndex = index;
        }
    }
    if(rateItem(*item) > worstRating)
    {
        dropCreatureItem(*this, setInventorySlot(worstIndex, std::move(item)));
        return true;
    }
    dropCreatureItem(*this, std::move(item));
    return equipped;
}

//! \brief Exchanges carried upgrades outside combat and drops unwanted inventory when crossing an own treasury.
void Creature::decideEquipment()
{
    if(isActionInList(CreatureActionType::fight))
        return;
    for(size_t index = 0; index < mInventory.size(); ++index)
    {
        ItemInstance* item = mInventory[index].get();
        if(item == nullptr || !item->mPotionId.empty() || !isItemEquippable(*item))
            continue;
        const size_t slot = static_cast<size_t>(getItemEquipmentSlot(*item));
        const double wornRating = mEquipment[slot].get() == nullptr ? 0.0 : rateItem(*mEquipment[slot]);
        if(rateItem(*item) > wornRating + EQUIP_UPGRADE_MARGIN)
            setInventorySlot(index, setEquipment(slot, setInventorySlot(index, std::unique_ptr<ItemInstance>())));
    }
    Tile* tile = getPositionTile();
    Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
    if(room == nullptr || room->getType() != RoomType::treasury || room->getSeat() != getSeat() ||
        !getGameMap()->getRoomsByTypeAndSeat(RoomType::merchant, getSeat()).empty())
        return;
    for(size_t index = 0; index < mInventory.size(); ++index)
    {
        ItemInstance* item = mInventory[index].get();
        if(item != nullptr && item->mPotionId.empty() && getLevel() >= item->getLevelMin(getGameMap())
            && (!item->mSoulCrystal || !wantsSoulCrystal(item->getPrice(getGameMap()))))
            dropCreatureItem(*this, setInventorySlot(index, std::unique_ptr<ItemInstance>()));
    }
}

//! \brief Drops one uniform eligible item on the first knockout, or every owned item when dead.
void Creature::dropItems(bool dead)
{
    if(getPositionTile() == nullptr || (!dead && mKoDroppedThisFight))
        return;
    std::vector<std::unique_ptr<ItemInstance>*> candidates;
    for(std::unique_ptr<ItemInstance>& item : mEquipment)
        if(item.get() != nullptr && (dead || item->mQuality != Quality::poor)) candidates.push_back(&item);
    for(std::unique_ptr<ItemInstance>& item : mPotionSlots)
        if(item.get() != nullptr) candidates.push_back(&item);
    for(std::unique_ptr<ItemInstance>& item : mInventory)
        if(item.get() != nullptr) candidates.push_back(&item);
    if(!dead)
    {
        mKoDroppedThisFight = true;
        if(!candidates.empty())
            dropCreatureItem(*this, std::move(*candidates[Random::Uint(0, static_cast<uint32_t>(candidates.size() - 1))]));
    }
    else
    {
        for(std::unique_ptr<ItemInstance>* item : candidates) dropCreatureItem(*this, std::move(*item));
        if(mWeaponR != nullptr) dropCreatureItem(*this, ItemDrops::poorWeapon(*mWeaponR));
        if(mWeaponL != nullptr) dropCreatureItem(*this, ItemDrops::poorWeapon(*mWeaponL));
    }
    itemsChanged();
}

//! \brief Frees Epics only when their creature permanently leaves the map rather than transferring a holder.
void Creature::unregisterHeldEpics()
{
    if(mHeldEpicsUnregistered)
        return;
    mHeldEpicsUnregistered = true;
    for(const std::unique_ptr<ItemInstance>& item : mEquipment)
        if(item.get() != nullptr) getGameMap()->unregisterEpic(*item);
    for(const std::unique_ptr<ItemInstance>& item : mInventory)
        if(item.get() != nullptr) getGameMap()->unregisterEpic(*item);
}

//! \brief Compares the time saved by a full XP step with the creature's payday earning time.
bool Creature::wantsSoulCrystal(double price) const
{
    if(getLevel() >= MAX_LEVEL) return false;
    const ConfigManager& config = ConfigManager::getSingleton();
    const double wage = mDefinition->getFee(getLevel()) / static_cast<double>(config.getTimePayDay());
    return wage > 0.0 && mDefinition->getXPNeededWhenLevel(getLevel()) / config.getSoulCrystalNormalXpPerSecond() >= price / wage;
}

//! \brief Grants the normal level transition and destroys the consumed crystal.
bool Creature::breakSoulCrystal(std::unique_ptr<ItemInstance>& item)
{
    if(item.get() == nullptr || !item->mSoulCrystal || getLevel() >= MAX_LEVEL) return false;
    setLevel(getLevel() + 1);
    item.reset();
    itemsChanged();
    Tile* tile = getPositionTile();
    if(tile != nullptr)
    {
        Spell::fireSpellEffect(*tile, "SoulCrystalBreak", "");
        for(Seat* seat : tile->getSeatsWithVision())
            if(seat->getPlayer() != nullptr && seat->getPlayer()->getIsHuman())
            {
                ServerNotification* sound = new ServerNotification(ServerNotificationType::playSpatialSound, seat->getPlayer());
                sound->mPacket << std::string("Rooms/GhostRoom/CrystalRing") << tile->getX() << tile->getY();
                ODServer::getSingleton().queueServerNotification(sound);
            }
    }
    return true;
}
