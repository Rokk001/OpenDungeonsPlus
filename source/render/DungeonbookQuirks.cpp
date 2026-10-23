/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "render/DungeonbookQuirks.h"

#include "game/CreatureAppearance.h"
#include "render/PortraitCatalog.h"

#include <algorithm>
#include <fstream>
#include <sstream>

namespace
{
//! \brief Trims whitespace around configuration columns.
std::string trimBlanks(const std::string& text)
{
    std::string::size_type first = text.find_first_not_of(" \t\r");
    if(first == std::string::npos)
        return std::string();
    std::string::size_type last = text.find_last_not_of(" \t\r");
    return text.substr(first, last - first + 1);
}

//! Candidate with the value that decides whether it is picked
struct ScoredRemark
{
    uint32_t mScore;
    std::size_t mIndex;
};

//! \brief Orders remark candidates by their stable score and original position.
bool isLowerScore(const ScoredRemark& a, const ScoredRemark& b)
{
    if(a.mScore != b.mScore)
        return a.mScore < b.mScore;
    return a.mIndex < b.mIndex;
}

//! \brief Restores the original order of selected remarks.
bool isLowerIndex(const ScoredRemark& a, const ScoredRemark& b)
{
    return a.mIndex < b.mIndex;
}
}

//! \brief Loads tag-keyed remarks, preserving missing-file warnings.
bool DungeonbookQuirks::loadFromFile(const std::string& path)
{
    mTexts.clear();
    mWarnings.clear();
    std::ifstream file(path.c_str());
    if(!file.is_open())
    {
        mWarnings.push_back(path + ": cannot open the Dungeonbook quirks, no remarks are shown");
        return false;
    }
    loadFromStream(file, path);
    return true;
}

//! \brief Reads unique TAB-separated feature-tag and remark pairs.
void DungeonbookQuirks::loadFromStream(std::istream& is, const std::string& source)
{
    mTexts.clear();
    mWarnings.clear();

    std::string line;
    uint32_t lineNumber = 0;
    while(std::getline(is, line))
    {
        ++lineNumber;
        std::string::size_type comment = line.find('#');
        if(comment != std::string::npos)
            line = line.substr(0, comment);
        if(trimBlanks(line).empty())
            continue;

        std::vector<std::string> columns;
        std::string::size_type start = 0;
        while(true)
        {
            std::string::size_type tab = line.find('\t', start);
            if(tab == std::string::npos)
            {
                columns.push_back(trimBlanks(line.substr(start)));
                break;
            }
            columns.push_back(trimBlanks(line.substr(start, tab - start)));
            start = tab + 1;
        }

        std::ostringstream where;
        where << source << ":" << lineNumber << ": ";
        if((columns.size() != 2) || columns[0].empty() || columns[1].empty())
        {
            mWarnings.push_back(where.str() + "expected feature tag and text separated by TAB, line dropped");
            continue;
        }

        const std::string& key = columns[0];
        if(mTexts.count(key) != 0)
        {
            mWarnings.push_back(where.str() + "repeated entry " + columns[0] + ", line dropped");
            continue;
        }
        mTexts[key] = columns[1];
    }
}

//! \brief Finds the remark matching one tag painted into a whole portrait.
const std::string* DungeonbookQuirks::find(const std::string& tag) const
{
    std::map<std::string, std::string>::const_iterator it = mTexts.find(tag);
    return it == mTexts.end() ? nullptr : &it->second;
}

namespace DungeonbookQuirkLogic
{
const uint32_t MAX_REMARKS = 2;

//! \brief Collects tags of the stored whole image, so missing images never invent character details.
std::vector<std::string> collectRemarks(const DungeonbookQuirks& quirks, const PortraitCatalog& catalog,
    const CreatureAppearance& appearance)
{
    std::vector<std::string> candidates;
    const PortraitCatalog::Image* image = catalog.findImage(appearance.getImageNumber());
    if(image == nullptr)
        return candidates;
    for(const std::string& tag : image->mTags)
    {
        const std::string* text = quirks.find(tag);
        if(text != nullptr)
            candidates.push_back(*text);
    }
    return candidates;
}

//! \brief Selects at most maxCount remarks using the stable name and image token.
std::vector<std::string> pickRemarks(const std::vector<std::string>& candidates, const std::string& creatureName,
    const CreatureAppearance& appearance, uint32_t maxCount)
{
    if(candidates.size() <= maxCount)
        return candidates;

    const std::string seed = creatureName + "|" + CreatureAppearanceLogic::toToken(appearance) + "|";
    std::vector<ScoredRemark> scored;
    for(std::size_t i = 0; i < candidates.size(); ++i)
    {
        ScoredRemark remark;
        remark.mScore = CreatureAppearanceLogic::stableHash(seed + candidates[i]);
        remark.mIndex = i;
        scored.push_back(remark);
    }

    std::sort(scored.begin(), scored.end(), isLowerScore);
    scored.resize(maxCount);
    std::sort(scored.begin(), scored.end(), isLowerIndex);

    std::vector<std::string> result;
    for(std::vector<ScoredRemark>::const_iterator it = scored.begin(); it != scored.end(); ++it)
        result.push_back(candidates[it->mIndex]);
    return result;
}

//! \brief Selects stable remarks for the stored whole-image feature tags.
std::vector<std::string> selectRemarks(const DungeonbookQuirks& quirks, const PortraitCatalog& catalog,
    const CreatureAppearance& appearance, const std::string& creatureName)
{
    return pickRemarks(collectRemarks(quirks, catalog, appearance), creatureName, appearance, MAX_REMARKS);
}

//! \brief Formats the selected remarks for the existing profile label.
std::string formatRemarks(const std::vector<std::string>& remarks)
{
    if(remarks.empty())
        return std::string();

    std::string text = "Quirks:";
    for(std::vector<std::string>::const_iterator it = remarks.begin(); it != remarks.end(); ++it)
        text += "\n- " + *it;
    return text;
}
}
