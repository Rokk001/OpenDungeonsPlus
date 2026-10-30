#include "entities/ItemInstance.h"

#include "entities/ItemEffects.h"
#include "entities/PotionDefinition.h"
#include "entities/Weapon.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

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
        << (mPotionId.empty() ? "none" : mPotionId) << " SoulCrystal " << mSoulCrystal;
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
    if(!stream.eof())
    {
        const std::streampos optionalPosition = stream.tellg();
        std::string marker;
        if(stream >> marker && marker == "SoulCrystal")
        {
            if(!(stream >> item.mSoulCrystal)) return false;
        }
        else
        {
            stream.clear();
            stream.seekg(optionalPosition);
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
    packet << mEpicSerial << mMerchantGoods << mGifted << mPotionId << std::string("SoulCrystal") << mSoulCrystal;
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

//! \brief Uses a matching weapon-class base image for Poor spawn gear, otherwise the catalogue image.
std::string ItemInstance::getImageName() const
{
    if(mSoulCrystal) return "soul_crystal";
    if(!mPotionId.empty())
    {
        const PotionDefinition* potion = ConfigManager::getSingleton().getPotion(mPotionId);
        return potion == nullptr ? std::string() : potion->getImage();
    }
    if(mQuality == Quality::poor)
    {
        const Weapon* weapon = ConfigManager::getSingleton().getWeapon(mDefinitionId);
        if(weapon != nullptr)
        {
            const std::string slot = weapon->getWeaponType() == "shield" ? "shield" : "weapon";
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

//! \brief Builds the tooltip shared by bags, profile slots and merchant stock.
std::string ItemInstance::describe(const GameMap* map) const
{
    std::string text = "[colour='" + QUALITY_COLOURS.at(static_cast<size_t>(mQuality)) + "']" + getDisplayName(map)
        + "[colour='FFFFFFFF']";
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
