#include "game/ItemDrops.h"

#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Weapon.h"
#include "gamemap/GameMap.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <sstream>
#include <vector>

namespace
{
static const uint32_t MEDIUM_HERO_LEVEL = 10;
static const uint32_t LARGE_HERO_LEVEL = 20;

//! \brief Returns one of the configured probability constants by its exact key.
double dropSetting(const std::string& key)
{ return ConfigManager::getSingleton().getItemSetting("ItemDrops", key); }

//! \brief Draws the hero quality from the linear level-dependent chances.
Quality heroQuality(uint32_t level)
{
    const double steps = static_cast<double>(level - 1);
    const double poor = dropSetting("DropPoorBase") + dropSetting("DropPoorPerLevel") * steps;
    const double rare = dropSetting("DropRareBase") + dropSetting("DropRarePerLevel") * steps;
    const double epic = dropSetting("DropEpicBase") + dropSetting("DropEpicPerLevel") * steps;
    const double draw = Random::Double(0.0, 1.0);
    if(draw < poor) return Quality::poor;
    if(draw < poor + rare) return Quality::rare;
    if(draw < poor + rare + epic) return Quality::epic;
    return Quality::common;
}

//! \brief Selects a uniform permitted slot and one of the creature's four actual skill paths.
std::unique_ptr<ItemInstance> rollForCreature(Creature& creature, Quality quality)
{
    std::vector<std::string> slots = {"head", "armour", "boots", "ring"};
    const Weapon* weapon = creature.getWeaponR();
    if(weapon == nullptr && creature.getWeaponL() != nullptr && creature.getWeaponL()->getWeaponType() == "bow")
        weapon = creature.getWeaponL();
    if(weapon != nullptr && weapon->getWeaponType() != "shield") slots.push_back("weapon");
    const Weapon* shield = creature.getWeaponL();
    if(shield != nullptr && shield->getWeaponType() == "shield" && (weapon == nullptr || weapon->getHands() != 2))
        slots.push_back("shield");
    const std::string slot = slots[Random::Uint(0, static_cast<uint32_t>(slots.size() - 1))];
    if(quality == Quality::poor)
    {
        // Rolled Poor weapons are carried instances in addition to the permanent spawn fallback.
        if(slot == "weapon") return ItemDrops::poorWeapon(*weapon);
        if(slot == "shield") return ItemDrops::poorWeapon(*shield);
        return ItemInstance::createPoor(slot);
    }
    CreatureSkillTree::TypeInfo type;
    type.mGroup = creature.getDefinition()->getSkillGroup();
    type.mFamily = creature.getDefinition()->getSkillFamily();
    const std::vector<std::string> paths = ConfigManager::getSingleton().getCreatureSkillTree().getPathNames(type);
    if(paths.empty())
        return std::unique_ptr<ItemInstance>();
    const std::string path = paths[Random::Uint(0, static_cast<uint32_t>(paths.size() - 1))];
    std::string weaponClass;
    if(slot == "weapon") weaponClass = weapon->getWeaponType();
    else if(slot == "shield") weaponClass = "shield";
    return creature.getGameMap()->rollItem(quality, slot, weaponClass, path);
}
}

//! \brief Uses the existing spawn-equipment id without inventing a new Poor weapon line.
std::unique_ptr<ItemInstance> ItemDrops::poorWeapon(const Weapon& weapon)
{
    std::unique_ptr<ItemInstance> item(new ItemInstance);
    item->mDefinitionId = weapon.getName();
    return item;
}

//! \brief Resolves the existing fixed-line format or the prescribed random quality token.
std::unique_ptr<ItemInstance> ItemDrops::resolve(GameMap& map, const std::string& content)
{
    if(content == "RandomEpic") return map.rollItem(Quality::epic);
    if(content == "RandomRare") return map.rollItem(Quality::rare);
    if(content == "RandomCommon") return map.rollItem(Quality::common);
    std::stringstream selection(content);
    std::string id;
    std::string qualityNameText;
    Quality quality = Quality::poor;
    if((selection >> id >> qualityNameText) && parseQuality(qualityNameText, quality))
    {
        selection >> std::ws;
        if(!selection.eof()) return std::unique_ptr<ItemInstance>();
        const ItemDefinition* definition = map.getItemDefinition(id);
        if(definition == nullptr)
            return std::unique_ptr<ItemInstance>();
        if(quality == Quality::epic && map.isEpicRegistered(id))
            quality = Quality::rare;
        std::unique_ptr<ItemInstance> selected = ItemInstance::create(*definition, quality);
        if(selected.get() != nullptr && quality == Quality::epic)
        {
            selected->mEpicSerial = map.allocateEpicSerial();
            map.registerEpic(*selected);
        }
        return selected;
    }
    std::stringstream stream(content);
    std::unique_ptr<ItemInstance> item(new ItemInstance);
    if(!item->importFromStream(stream))
        return std::unique_ptr<ItemInstance>();
    map.registerEpic(*item);
    return item;
}

//! \brief Generates the exact item and potion rolls for hero and portal arrivals.
void ItemDrops::outfit(Creature& creature, const std::string& kind)
{
    const uint32_t level = creature.getLevel();
    if(kind == "portal")
    {
        const double draw = Random::Double(0.0, 1.0);
        if(draw < dropSetting("PortalRare"))
            creature.acceptItem(rollForCreature(creature, Quality::rare));
        else if(draw < dropSetting("PortalRare") + dropSetting("PortalCommon"))
            creature.acceptItem(rollForCreature(creature, Quality::common));
        creature.setHP(creature.getMaxHp());
        creature.setCurrentMana(creature.getMaxMana());
        return;
    }
    uint32_t count = 1;
    if(level > LARGE_HERO_LEVEL) count = 3;
    else if(level > MEDIUM_HERO_LEVEL) count = 2;
    for(uint32_t index = 0; index < count; ++index)
    {
        if(Random::Double(0.0, 1.0) < dropSetting("HeroItemBase") + dropSetting("HeroItemPerLevel") * level)
            creature.acceptItem(rollForCreature(creature, heroQuality(level)));
    }
    creature.setHP(creature.getMaxHp());
    creature.setCurrentMana(creature.getMaxMana());
    if(Random::Double(0.0, 1.0) >= dropSetting("HeroPotionBase") + dropSetting("HeroPotionPerLevel") * level)
        return;
    std::string potionId;
    const double special = Random::Double(0.0, 1.0);
    const double share = dropSetting("HeroSpecialPotionShare");
    if(level >= dropSetting("HeroSpecialPotionLevel") && special < share)
        potionId = "lifespring";
    else if(level >= dropSetting("HeroSpecialPotionLevel") && special < share * 2.0)
        potionId = "thaw";
    else
    {
        static const std::vector<std::string> KINDS = {"healing", "mana", "strength", "dexterity", "guard", "vitality", "focus", "mending", "flow"};
        potionId = KINDS[Random::Uint(0, static_cast<uint32_t>(KINDS.size() - 1))];
        if(level > LARGE_HERO_LEVEL) potionId += "_large";
        else if(level > MEDIUM_HERO_LEVEL) potionId += "_medium";
        else potionId += "_small";
    }
    creature.acceptItem(ItemInstance::createPotion(potionId), false);
}
