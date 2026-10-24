#include "entities/PotionDefinition.h"
#include "network/ODPacket.h"

#include <sstream>

//! \brief Reads a recipe, preserving fractional effect and brewing values.
bool PotionDefinition::importFromStream(std::istream& stream)
{
    std::string line;
    while(std::getline(stream, line))
    {
        std::stringstream row(line);
        std::string key;
        if(!(row >> key))
            continue;
        if(key == "[/Potion]")
            return !mId.empty() && !mKind.empty() && !mDisplay.empty() && !mImage.empty();
        if(key == "Id") row >> mId;
        else if(key == "Display") std::getline(row >> std::ws, mDisplay);
        else if(key == "Size") row >> mSize;
        else if(key == "Kind") row >> mKind;
        else if(key == "Value") row >> mValue;
        else if(key == "Duration") row >> mDuration;
        else if(key == "LevelMin") row >> mLevelMin;
        else if(key == "BrewSeconds") row >> mBrewSeconds;
        else if(key == "Price") row >> mPrice;
        else if(key == "Image") row >> mImage;
        else if(key == "Herbs")
        {
            std::string herb;
            uint32_t count = 0;
            while(row >> herb)
            {
                if(!(row >> count))
                    return false;
                mHerbs[herb] = count;
            }
            continue;
        }
        else
            return false;
        if(row.fail())
            return false;
    }
    return false;
}

//! \brief Writes all recipe values in the format accepted by the configuration parser.
void PotionDefinition::exportToStream(std::ostream& stream) const
{
    stream << "[Potion]\nId " << mId << "\nDisplay " << mDisplay << "\nSize " << mSize << "\nKind " << mKind
        << "\nValue " << mValue << "\nDuration " << mDuration << "\nLevelMin " << mLevelMin << "\nHerbs";
    for(const std::pair<const std::string, uint32_t>& herb : mHerbs)
        stream << ' ' << herb.first << ' ' << herb.second;
    stream << "\nBrewSeconds " << mBrewSeconds << "\nPrice " << mPrice << "\nImage " << mImage << "\n[/Potion]\n";
}

//! \brief Sends the recipe using its canonical text representation.
void PotionDefinition::exportToPacket(ODPacket& packet) const
{
    std::ostringstream stream;
    exportToStream(stream);
    packet << stream.str();
}

//! \brief Adopts a transferred recipe only after it was fully parsed.
bool PotionDefinition::importFromPacket(ODPacket& packet)
{
    std::string text;
    if(!(packet >> text))
        return false;
    std::stringstream stream(text);
    std::string tag;
    PotionDefinition definition;
    if(!(stream >> tag) || tag != "[Potion]" || !definition.importFromStream(stream))
        return false;
    *this = definition;
    return true;
}

//! \brief Reads one herb's growth time, colour and unlock requirement.
bool HerbDefinition::importFromStream(std::istream& stream)
{
    std::string line;
    while(std::getline(stream, line))
    {
        std::stringstream row(line);
        std::string key;
        if(!(row >> key))
            continue;
        if(key == "[/Herb]")
            return !mId.empty() && !mDisplay.empty() && mGrowSeconds > 0.0 && mStages > 0;
        if(key == "Id") row >> mId;
        else if(key == "Display") std::getline(row >> std::ws, mDisplay);
        else if(key == "Colour") row >> mColour;
        else if(key == "GrowSeconds") row >> mGrowSeconds;
        else if(key == "Research") row >> mResearch;
        else if(key == "Stages") row >> mStages;
        else
            return false;
        if(row.fail())
            return false;
    }
    return false;
}

//! \brief Writes a herb block so the server can transfer its complete definition.
void HerbDefinition::exportToStream(std::ostream& stream) const
{
    stream << "[Herb]\nId " << mId << "\nDisplay " << mDisplay << "\nColour " << mColour
        << "\nGrowSeconds " << mGrowSeconds << "\nResearch " << mResearch << "\nStages " << mStages << "\n[/Herb]\n";
}
