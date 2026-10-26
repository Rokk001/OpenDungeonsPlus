#include "entities/ItemDefinition.h"

#include "network/ODPacket.h"

#include <memory>
#include <sstream>

namespace
{
static const std::array<std::string, 4> QUALITY_NAMES = {{"Poor", "Common", "Rare", "Epic"}};

//! \brief Reads one quality block, retaining the order of its bonus lines.
bool readItemQuality(std::stringstream& stream, Quality& quality, ItemQuality& result)
{
    std::string line;
    bool named = false;
    while(std::getline(stream, line))
    {
        std::stringstream row(line);
        std::string key;
        if(!(row >> key))
            continue;
        if(key == "[/Quality]")
        {
            result.mAvailable = named && !result.mDisplay.empty() && result.mBonusMinimum <= result.mBonusMaximum &&
                result.mBonusMaximum <= result.mBonuses.size();
            return result.mAvailable;
        }
        if(key == "Name")
        {
            std::string name;
            row >> name;
            named = parseQuality(name, quality);
            if(!named)
                return false;
        }
        else if(key == "Display")
            std::getline(row >> std::ws, result.mDisplay);
        else if(key == "LevelMin")
        {
            if(!(row >> result.mLevelMin))
                return false;
        }
        else if(key == "Price")
        {
            if(!(row >> result.mPrice))
                return false;
            row >> result.mPricePerBonus;
        }
        else if(key == "BonusCount")
        {
            if(!(row >> result.mBonusMinimum >> result.mBonusMaximum))
                return false;
        }
        else if(key == "Bonus")
        {
            ItemBonusRange bonus;
            if(!(row >> bonus.mKind >> bonus.mMinimum >> bonus.mMaximum) || bonus.mMinimum > bonus.mMaximum)
                return false;
            result.mBonuses.push_back(bonus);
        }
        else if(key == "Effect")
        {
            std::pair<std::string, double> effect("", 0.0);
            if(!(row >> effect.first >> effect.second))
                return false;
            result.mEffects.push_back(effect);
        }
        else
            return false;
    }
    return false;
}
}

//! \brief Returns the catalogue spelling for a valid quality.
const std::string& qualityName(Quality quality)
{
    return QUALITY_NAMES.at(static_cast<size_t>(quality));
}

//! \brief Parses the four quality spellings from definition files.
bool parseQuality(const std::string& name, Quality& quality)
{
    for(size_t index = 0; index < QUALITY_NAMES.size(); ++index)
    {
        if(name != QUALITY_NAMES[index])
            continue;
        quality = static_cast<Quality>(index);
        return true;
    }
    return false;
}

//! \brief Writes the fixed-width quality value.
ODPacket& operator <<(ODPacket& packet, Quality quality)
{
    return packet << static_cast<int32_t>(quality);
}

//! \brief Reads a fixed-width quality value; definition and instance readers validate its range.
ODPacket& operator >>(ODPacket& packet, Quality& quality)
{
    int32_t value = 0;
    packet >> value;
    quality = static_cast<Quality>(value);
    return packet;
}

//! \brief Reads one item line and all its available qualities.
ItemDefinition* ItemDefinition::load(std::stringstream& stream)
{
    std::unique_ptr<ItemDefinition> definition(new ItemDefinition);
    std::string line;
    bool hasQuality = false;
    while(std::getline(stream, line))
    {
        std::stringstream row(line);
        std::string key;
        if(!(row >> key))
            continue;
        if(key == "[/Item]")
        {
            if(definition->mId.empty() || definition->mSlot.empty() || !hasQuality)
                return nullptr;
            return definition.release();
        }
        if(key == "[Quality]")
        {
            Quality quality = Quality::poor;
            ItemQuality values;
            if(!readItemQuality(stream, quality, values))
                return nullptr;
            ItemQuality& target = definition->mQualities[static_cast<size_t>(quality)];
            if(target.mAvailable)
                return nullptr;
            target = values;
            hasQuality = true;
        }
        else if(key == "Id")
            row >> definition->mId;
        else if(key == "Slot")
            row >> definition->mSlot;
        else if(key == "Path")
            std::getline(row >> std::ws, definition->mPath);
        else if(key == "Group")
            row >> definition->mGroup;
        else if(key == "WeaponClass")
            row >> definition->mWeaponClass;
        else if(key == "PoorEquipment")
            row >> definition->mPoorEquipment;
        else
            return nullptr;
    }
    return nullptr;
}

//! \brief Returns the requested quality using checked indexing.
const ItemQuality& ItemDefinition::getQuality(Quality quality) const
{
    return mQualities.at(static_cast<size_t>(quality));
}

//! \brief Writes every definition field and preserves the bonus roll order.
void ItemDefinition::exportToStream(std::ostream& stream) const
{
    stream << "[Item]\nId " << mId << "\nSlot " << mSlot << "\nPath " << mPath << "\nGroup " << mGroup
        << "\nWeaponClass " << mWeaponClass << "\nPoorEquipment " << mPoorEquipment << '\n';
    for(size_t index = 0; index < mQualities.size(); ++index)
    {
        const ItemQuality& quality = mQualities[index];
        if(!quality.mAvailable)
            continue;
        stream << "[Quality]\nName " << QUALITY_NAMES[index] << "\nDisplay " << quality.mDisplay
            << "\nLevelMin " << quality.mLevelMin << "\nPrice " << quality.mPrice << ' ' << quality.mPricePerBonus
            << "\nBonusCount " << quality.mBonusMinimum << ' ' << quality.mBonusMaximum << '\n';
        for(const ItemBonusRange& bonus : quality.mBonuses)
            stream << "Bonus " << bonus.mKind << ' ' << bonus.mMinimum << ' ' << bonus.mMaximum << '\n';
        for(const std::pair<std::string, double>& effect : quality.mEffects)
            stream << "Effect " << effect.first << ' ' << effect.second << '\n';
        stream << "[/Quality]\n";
    }
    stream << "[/Item]\n";
}

//! \brief Sends the same definition representation the configuration parser consumes.
void ItemDefinition::exportToPacket(ODPacket& packet) const
{
    std::ostringstream stream;
    exportToStream(stream);
    packet << stream.str();
}

//! \brief Loads a transferred definition only after the complete text was received.
ItemDefinition* ItemDefinition::loadFromPacket(ODPacket& packet)
{
    std::string text;
    if(!(packet >> text))
        return nullptr;
    std::stringstream stream(text);
    std::string tag;
    if(!(stream >> tag) || tag != "[Item]")
        return nullptr;
    return load(stream);
}
