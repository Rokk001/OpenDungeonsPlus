#include "entities/ItemInstance.h"

#include "entities/ItemEffects.h"
#include "entities/PotionDefinition.h"
#include "entities/Weapon.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <map>
#include <sstream>

namespace
{
static const double ROLL_PRECISION = 10.0;
static const uint32_t BONUS_KIND_COUNT = 17;
static const std::array<std::string, 4> QUALITY_COLOURS = {{"FF8A8A8A", "FFFFFFFF", "FF3E7BFF", "FFA64DFF"}};
static const std::array<std::string, 4> QUALITY_SUFFIXES = {{"poor", "common", "rare", "epic"}};

//! \brief Resolves a map's authoritative item catalogue, or the configuration before a map exists.
const ItemDefinition* resolveItemDefinition(const std::string& id, const GameMap* map)
{
    if(map != nullptr)
        return map->getItemDefinition(id);
    return ConfigManager::getSingleton().getItem(id);
}

//! \brief Adds all matching entries from a rolled bonus or effect list.
double sumValues(const std::vector<std::pair<std::string, double>>& values, const std::string& kind)
{
    double sum = 0.0;
    for(const std::pair<std::string, double>& entry : values)
    {
        if(entry.first == kind)
            sum += entry.second;
    }
    return sum;
}

//! \brief Formats rolled values without losing their single decimal precision.
std::string itemNumber(double value)
{
    std::ostringstream stream;
    if(value == std::floor(value))
        stream << std::fixed << std::setprecision(0) << value;
    else
        stream << std::fixed << std::setprecision(1) << value;
    return stream.str();
}

//! \brief Returns the readable text of each configured bonus kind.
std::string bonusName(const std::string& kind)
{
    static const std::map<std::string, std::string> NAMES = {
        {"Damage%", "Damage"}, {"MaxHP%", "Maximum health"}, {"CritChance", "Critical chance"},
        {"Defense%", "Defense"}, {"AttackRating%", "Attack rating"}, {"DefenseRating%", "Defense rating"},
        {"MoveSpeed%", "Movement speed"}, {"Avoid", "Avoidance"}, {"Cooldown%", "Cooldown reduction"},
        {"DamageAttribute", "Damage attribute"}, {"Life", "Life"}, {"Mana", "Mana"},
        {"ManaCost%", "Mana cost reduction"}, {"Wakefulness%", "Wakefulness"}, {"Dig%", "Digging"},
        {"Claim%", "Claiming"}, {"Carry%", "Carrying"}
    };
    std::map<std::string, std::string>::const_iterator found = NAMES.find(kind);
    if(found == NAMES.end())
        return kind;
    return found->second;
}
}

//! \brief Rolls a quality's count and ordered inclusive bonus ranges.
std::unique_ptr<ItemInstance> ItemInstance::create(const ItemDefinition& definition, Quality quality)
{
    const ItemQuality& values = definition.getQuality(quality);
    if(!values.mAvailable)
        return std::unique_ptr<ItemInstance>();
    std::unique_ptr<ItemInstance> item(new ItemInstance);
    item->mDefinitionId = definition.getId();
    item->mQuality = quality;
    const uint32_t count = Random::Uint(values.mBonusMinimum, values.mBonusMaximum);
    for(uint32_t index = 0; index < count; ++index)
    {
        const ItemBonusRange& bonus = values.mBonuses[index];
        const double rolled = std::round(Random::Double(bonus.mMinimum, bonus.mMaximum) * ROLL_PRECISION) / ROLL_PRECISION;
        item->mBonuses.push_back(std::make_pair(bonus.mKind, rolled));
    }
    item->mEffects = values.mEffects;
    return item;
}

//! \brief Creates one of the five catalogue Poor equipment lines.
std::unique_ptr<ItemInstance> ItemInstance::createPoor(const std::string& slot)
{
    static const std::map<std::string, std::string> IDS = {
        {"head", "POOR_Head"}, {"armour", "POOR_Armour"}, {"boots", "POOR_Boots"},
        {"ring", "POOR_Ring"}, {"shield", "POOR_Shield"}
    };
    std::map<std::string, std::string>::const_iterator found = IDS.find(slot);
    if(found == IDS.end())
        return std::unique_ptr<ItemInstance>();
    const ItemDefinition* definition = ConfigManager::getSingleton().getItem(found->second);
    if(definition == nullptr)
        return std::unique_ptr<ItemInstance>();
    return create(*definition, Quality::poor);
}

//! \brief Creates a single potion without equipment bonuses.
std::unique_ptr<ItemInstance> ItemInstance::createPotion(const std::string& id)
{
    if(ConfigManager::getSingleton().getPotion(id) == nullptr)
        return std::unique_ptr<ItemInstance>();
    std::unique_ptr<ItemInstance> item(new ItemInstance);
    item->mDefinitionId = id;
    item->mPotionId = id;
    return item;
}

//! \brief Creates the nonempty inventory identity used by every crystal holder codec.
std::unique_ptr<ItemInstance> ItemInstance::createSoulCrystal()
{
    std::unique_ptr<ItemInstance> item(new ItemInstance);
    item->mDefinitionId = "SoulCrystal";
    item->mSoulCrystal = true;
    return item;
}

//! \brief Creates a ghost room good; ectoplasm has no apparatus until a worker picks it up.
std::unique_ptr<ItemInstance> ItemInstance::createGhostItem(GhostItem kind)
{
    std::unique_ptr<ItemInstance> item(new ItemInstance);
    item->mGhostItem = kind;
    item->mDefinitionId = kind == GhostItem::ectoplasm ? "Ectoplasm" : kind == GhostItem::manaCrystal ? "ManaCrystal" : "ResearchBook";
    return item;
}

//! \brief Writes the prescribed instance line using none for empty string fields.
void ItemInstance::exportToStream(std::ostream& stream) const
{
    stream << (mDefinitionId.empty() ? "none" : mDefinitionId) << ' ' << static_cast<int32_t>(mQuality)
        << ' ' << mBonuses.size();
    for(const std::pair<std::string, double>& bonus : mBonuses)
        stream << ' ' << bonus.first << ' ' << bonus.second;
    stream << ' ' << mEffects.size();
    for(const std::pair<std::string, double>& effect : mEffects)
        stream << ' ' << effect.first << ' ' << effect.second;
    stream << ' ' << mEpicSerial << ' ' << mMerchantGoods << ' ' << mGifted << ' '
        << (mPotionId.empty() ? "none" : mPotionId) << " SoulCrystal " << mSoulCrystal
        << " GhostItem " << static_cast<uint32_t>(mGhostItem) << ' ' << mGhostTarget;
}

//! \brief Reads the full instance; firstId is the id already consumed by a nullable holder slot.
bool ItemInstance::importFromStream(std::istream& stream, const std::string& firstId)
{
    ItemInstance item;
    item.mDefinitionId = firstId;
    if(item.mDefinitionId.empty() && !(stream >> item.mDefinitionId))
        return false;
    int32_t quality = 0;
    uint32_t count = 0;
    if(!(stream >> quality >> count) || quality < 0 || quality > static_cast<int32_t>(Quality::epic)
        || count > BONUS_KIND_COUNT)
        return false;
    item.mQuality = static_cast<Quality>(quality);
    for(uint32_t index = 0; index < count; ++index)
    {
        std::pair<std::string, double> value("", 0.0);
        if(!(stream >> value.first >> value.second) || !std::isfinite(value.second))
            return false;
        item.mBonuses.push_back(value);
    }
    if(!(stream >> count) || count > static_cast<uint32_t>(ConfigManager::getSingleton().getItemSetting("ItemEffects", "MaxItemEffects")))
        return false;
    for(uint32_t index = 0; index < count; ++index)
    {
        std::pair<std::string, double> value("", 0.0);
        if(!(stream >> value.first >> value.second) || !std::isfinite(value.second))
            return false;
        item.mEffects.push_back(value);
    }
    if(!(stream >> item.mEpicSerial >> item.mMerchantGoods >> item.mGifted >> item.mPotionId))
        return false;
    // Optional trailing fields: older saves end before them; every known marker is read
    while(!stream.eof())
    {
        const std::streampos optionalPosition = stream.tellg();
        std::string marker;
        if(stream >> marker && marker == "SoulCrystal")
        {
            if(!(stream >> item.mSoulCrystal)) return false;
        }
        else if(marker == "GhostItem")
        {
            uint32_t kind = 0;
            if(!(stream >> kind >> item.mGhostTarget) || kind > static_cast<uint32_t>(GhostItem::researchBook)) return false;
            item.mGhostItem = static_cast<GhostItem>(kind);
        }
        else
        {
            stream.clear();
            stream.seekg(optionalPosition);
            break;
        }
    }
    if(item.mDefinitionId == "none") item.mDefinitionId.clear();
    if(item.mPotionId == "none") item.mPotionId.clear();
    *this = item;
    return true;
}

//! \brief Writes the fields in save order with explicit packet counter widths.
void ItemInstance::exportToPacket(ODPacket& packet) const
{
    packet << mDefinitionId << mQuality << static_cast<uint32_t>(mBonuses.size());
    for(const std::pair<std::string, double>& bonus : mBonuses)
        packet << bonus.first << bonus.second;
    packet << static_cast<uint32_t>(mEffects.size());
    for(const std::pair<std::string, double>& effect : mEffects)
        packet << effect.first << effect.second;
    packet << mEpicSerial << mMerchantGoods << mGifted << mPotionId << std::string("SoulCrystal") << mSoulCrystal
        << std::string("GhostItem") << static_cast<uint32_t>(mGhostItem) << mGhostTarget;
}

//! \brief Rejects short packet instances without adopting any partially received fields.
bool ItemInstance::importFromPacket(ODPacket& packet)
{
    ItemInstance item;
    uint32_t count = 0;
    if(!(packet >> item.mDefinitionId >> item.mQuality >> count) || static_cast<int32_t>(item.mQuality) < 0 ||
        static_cast<int32_t>(item.mQuality) > static_cast<int32_t>(Quality::epic) || count > BONUS_KIND_COUNT)
        return false;
    for(uint32_t index = 0; index < count; ++index)
    {
        std::pair<std::string, double> value("", 0.0);
        if(!(packet >> value.first >> value.second) || !std::isfinite(value.second))
            return false;
        item.mBonuses.push_back(value);
    }
    if(!(packet >> count) || count > static_cast<uint32_t>(ConfigManager::getSingleton().getItemSetting("ItemEffects", "MaxItemEffects")))
        return false;
    for(uint32_t index = 0; index < count; ++index)
    {
        std::pair<std::string, double> value("", 0.0);
        if(!(packet >> value.first >> value.second) || !std::isfinite(value.second))
            return false;
        item.mEffects.push_back(value);
    }
    if(!(packet >> item.mEpicSerial >> item.mMerchantGoods >> item.mGifted >> item.mPotionId))
        return false;
    ODPacket optional = packet;
    std::string marker;
    if(optional >> marker && marker == "SoulCrystal")
    {
        if(!(optional >> item.mSoulCrystal)) return false;
        packet = optional;
    }
    ODPacket ghost = packet;
    uint32_t kind = 0;
    if(ghost >> marker && marker == "GhostItem")
    {
        if(!(ghost >> kind >> item.mGhostTarget) || kind > static_cast<uint32_t>(GhostItem::researchBook)) return false;
        item.mGhostItem = static_cast<GhostItem>(kind);
        packet = ghost;
    }
    *this = item;
    return true;
}

//! \brief Returns this instance's contribution to one bonus kind.
double ItemInstance::getBonus(const std::string& kind) const { return sumValues(mBonuses, kind); }
//! \brief Returns this instance's contribution to one effect.
double ItemInstance::getEffect(const std::string& id) const { return sumValues(mEffects, id); }

//! \brief Resolves catalogue display names and the equipment name of Poor spawn weapons.
std::string ItemInstance::getDisplayName(const GameMap* map) const
{
    if(mSoulCrystal) return "Soul crystal";
    if(mGhostItem == GhostItem::ectoplasm) return "Ectoplasm";
    if(mGhostItem == GhostItem::manaCrystal) return "Mana crystal";
    if(mGhostItem == GhostItem::researchBook) return "Research book";
    if(!mPotionId.empty())
    {
        const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(mPotionId);
        return potion == nullptr ? std::string() : potion->getDisplay();
    }
    const ItemDefinition* definition = resolveItemDefinition(mDefinitionId, map);
    if(definition != nullptr)
        return definition->getQuality(mQuality).mDisplay;
    const Weapon* weapon = ConfigManager::getSingleton().getWeapon(mDefinitionId);
    return mQuality == Quality::poor && weapon != nullptr ? weapon->getName() : std::string();
}

//! \brief Resolves the base price and adds per-bonus pricing for the rolled instance.
double ItemInstance::getPrice(const GameMap* map) const
{
    if(mSoulCrystal) return ConfigManager::getSingleton().getSoulCrystalPrice();
    // Ectoplasm, mana crystals and research books are used by the keeper and are never traded
    if(mGhostItem != GhostItem::none) return 0.0;
    if(!mPotionId.empty())
    {
        const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(mPotionId);
        return potion == nullptr ? 0.0 : potion->getPrice();
    }
    const ItemDefinition* definition = resolveItemDefinition(mDefinitionId, map);
    if(definition == nullptr)
    {
        if(mQuality == Quality::poor && ConfigManager::getSingleton().getWeapon(mDefinitionId) != nullptr)
        {
            const ItemDefinition* poor = ConfigManager::getSingleton().getItem("POOR_Shield");
            if(poor != nullptr) return poor->getQuality(Quality::poor).mPrice;
        }
        return 0.0;
    }
    const ItemQuality& values = definition->getQuality(mQuality);
    return values.mPrice + values.mPricePerBonus * mBonuses.size();
}

//! \brief Resolves the level gate of this particular quality or potion size.
uint32_t ItemInstance::getLevelMin(const GameMap* map) const
{
    if(!mPotionId.empty())
    {
        const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(mPotionId);
        return potion == nullptr ? 1 : potion->getLevelMin();
    }
    const ItemDefinition* definition = resolveItemDefinition(mDefinitionId, map);
    return definition == nullptr ? 1 : definition->getQuality(mQuality).mLevelMin;
}

//! \brief Prefers the exact spawn equipment's base picture, then a matching weapon class, otherwise the catalogue image.
std::string ItemInstance::getImageName(const Weapon* heldWeapon) const
{
    // The ghost goods share the crystal picture until pictures of their own exist
    if(mSoulCrystal || mGhostItem != GhostItem::none) return "soul_crystal";
    if(!mPotionId.empty())
    {
        const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(mPotionId);
        return potion == nullptr ? std::string() : potion->getImage();
    }
    if(mQuality == Quality::poor)
    {
        const Weapon* weapon = heldWeapon != nullptr ? heldWeapon : ConfigManager::getSingleton().getWeapon(mDefinitionId);
        if(weapon != nullptr)
        {
            const std::string slot = weapon->getWeaponType() == "shield" ? "shield" : "weapon";
            for(const ItemDefinition* definition : ConfigManager::getSingleton().getItems())
                if(definition->getSlot() == slot && definition->getWeaponClass() == weapon->getWeaponType() &&
                   definition->getPoorEquipment() == weapon->getName() &&
                   definition->getQuality(Quality::common).mAvailable)
                    return definition->getId() + "_base";
            for(const ItemDefinition* definition : ConfigManager::getSingleton().getItems())
                if(definition->getSlot() == slot && definition->getWeaponClass() == weapon->getWeaponType() &&
                   definition->getQuality(Quality::common).mAvailable)
                    return definition->getId() + "_base";
            return std::string();
        }
        return mDefinitionId;
    }
    return mDefinitionId + "_" + QUALITY_SUFFIXES.at(static_cast<size_t>(mQuality));
}

//! \brief Builds the shared tooltip; spawn fallbacks show the actual held weapon's base values without rolling an item.
std::string ItemInstance::describe(const GameMap* map, const Weapon* heldWeapon) const
{
    std::string text = "[colour='" + QUALITY_COLOURS.at(static_cast<size_t>(mQuality)) + "']" +
        (heldWeapon == nullptr ? getDisplayName(map) : heldWeapon->getName())
        + "[colour='FFFFFFFF']";
    if(heldWeapon != nullptr)
    {
        std::ostringstream values;
        values << "\nQuality: " << qualityName(mQuality)
            << "\nType: " << heldWeapon->getWeaponType() << "\nHands: " << heldWeapon->getHands()
            << "\nBase damage (physical/magical/elemental): "
            << heldWeapon->getPhysicalDamageMin() << "-" << heldWeapon->getPhysicalDamage() << " / "
            << heldWeapon->getMagicalDamageMin() << "-" << heldWeapon->getMagicalDamage() << " / "
            << heldWeapon->getElementDamageMin() << "-" << heldWeapon->getElementDamage()
            << "\nBase defense (physical/magical/elemental): "
            << heldWeapon->getPhysicalDefense() << " / " << heldWeapon->getMagicalDefense() << " / "
            << heldWeapon->getElementDefense()
            << "\nAttack rating: " << heldWeapon->getAttackRating()
            << "\nDefense rating: " << heldWeapon->getDefenseRating();
        text += values.str();
    }
    for(const std::pair<std::string, double>& bonus : mBonuses)
    {
        text += "\n" + bonusName(bonus.first) + " +" + itemNumber(bonus.second);
        if(bonus.first.find('%') != std::string::npos)
            text += "%";
    }
    for(const std::pair<std::string, double>& effect : mEffects)
        text += "\n" + ItemEffects::getName(effect.first) + " " + itemNumber(effect.second);
    return text + "\nLevel " + std::to_string(getLevelMin(map));
}

//! \brief Builds the item card tooltip (owner decision 1026, finding 5): large name and quality in the quality colour,
//! the price after a gold coin, a short left-aligned list of the values and the level in grey. The values are those of
//! describe(); only their layout and the labels of a held weapon are shorter.
std::string ItemInstance::describeTooltip(const GameMap* map, const Weapon* heldWeapon, int32_t coinSize) const
{
    const std::string quality = "[colour='" + QUALITY_COLOURS.at(static_cast<size_t>(mQuality)) + "']";
    const std::string size = std::to_string(std::max<int32_t>(coinSize, 1));
    std::ostringstream text;
    text << "[font='MedievalSharp-13']" << quality << (heldWeapon == nullptr ? getDisplayName(map) : heldWeapon->getName())
        << "\n[font='MedievalSharp-10']" << quality << qualityName(mQuality)
        << "     [colour='FFF2C860'][image-size='w:" << size << " h:" << size << "'][image='OpenDungeonsIcons/GoldCoin'] "
        << itemNumber(getPrice(map)) << "[colour='FFE8DCC0']";
    if(heldWeapon != nullptr)
    {
        text << "\nType: " << heldWeapon->getWeaponType() << "\nHands: " << heldWeapon->getHands()
            << "\nDamage: "
            << heldWeapon->getPhysicalDamageMin() << "-" << heldWeapon->getPhysicalDamage() << " / "
            << heldWeapon->getMagicalDamageMin() << "-" << heldWeapon->getMagicalDamage() << " / "
            << heldWeapon->getElementDamageMin() << "-" << heldWeapon->getElementDamage()
            << "\nDefense: "
            << heldWeapon->getPhysicalDefense() << " / " << heldWeapon->getMagicalDefense() << " / "
            << heldWeapon->getElementDefense()
            << "\nAttack rating: " << heldWeapon->getAttackRating()
            << "\nDefense rating: " << heldWeapon->getDefenseRating();
    }
    for(const std::pair<std::string, double>& bonus : mBonuses)
    {
        text << "\n" << bonusName(bonus.first) << " +" << itemNumber(bonus.second);
        if(bonus.first.find('%') != std::string::npos)
            text << "%";
    }
    for(const std::pair<std::string, double>& effect : mEffects)
        text << "\n" << ItemEffects::getName(effect.first) << " " << itemNumber(effect.second);
    text << "\n[colour='FF9A9080']Level " << getLevelMin(map);
    return text.str();
}
