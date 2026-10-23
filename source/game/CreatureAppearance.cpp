/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */
#include "game/CreatureAppearance.h"
#include "render/PortraitCatalog.h"

#include <cctype>
#include <set>

//! \brief Compares the catalog and permanent image number.
bool CreatureAppearance::operator==(const CreatureAppearance& other) const
{
    return mCatalogId == other.mCatalogId && mImageNumber == other.mImageNumber;
}

namespace CreatureAppearanceLogic
{
namespace
{
//! \brief Reads one positive uint32, rejecting nondecimal input and overflow.
bool parseNumber(const std::string& text, uint32_t& number)
{
    if(text.empty())
        return false;
    uint64_t result = 0;
    for(char ch : text)
    {
        if(ch < '0' || ch > '9')
            return false;
        result = result * 10 + static_cast<uint32_t>(ch - '0');
        if(result > UINT32_MAX)
            return false;
    }
    number = static_cast<uint32_t>(result);
    return number != 0;
}

//! \brief Constructs the stored server-authoritative catalog/image pair.
CreatureAppearance makeAppearance(const std::string& catalogId, uint32_t imageNumber)
{
    CreatureAppearance result;
    result.setCatalogId(catalogId);
    result.setImageNumber(imageNumber);
    return result;
}
}

//! \brief Preserves the fixed FNV-1a name hash used by existing saved appearances.
uint32_t stableHash(const std::string& text)
{
    uint32_t hash = 2166136261u;
    for(std::string::size_type i = 0; i < text.size(); ++i)
    {
        hash ^= static_cast<uint32_t>(static_cast<unsigned char>(text[i]));
        hash *= 16777619u;
    }
    return hash;
}

//! \brief Resolves the gender suffix before trying the original mesh catalog.
std::string resolveCatalogId(const std::string& meshName, const std::string& gender,
    const CatalogExistsFunction& exists)
{
    if(meshName.empty())
        return std::string();
    if(!gender.empty())
    {
        std::string lowerGender = gender;
        for(std::string::size_type i = 0; i < lowerGender.size(); ++i)
            lowerGender[i] = static_cast<char>(std::tolower(static_cast<unsigned char>(lowerGender[i])));
        const std::string withGender = meshName + "-" + lowerGender;
        if(exists(withGender))
            return withGender;
    }
    return exists(meshName) ? meshName : std::string();
}

//! \brief Chooses from free image IDs directly, avoiding retry loops even with a scripted RNG.
CreatureAppearance pickRandom(const PortraitCatalog& catalog, const std::string& catalogId,
    const RandomFunction& random, const std::vector<CreatureAppearance>& taken)
{
    const std::vector<PortraitCatalog::Image>& images = catalog.getImages();
    if(images.empty())
        return CreatureAppearance();
    std::set<uint32_t> used;
    for(const CreatureAppearance& other : taken)
        if(other.getCatalogId() == catalogId && catalog.findImage(other.getImageNumber()) != nullptr)
            used.insert(other.getImageNumber());
    std::vector<uint32_t> available;
    for(const PortraitCatalog::Image& image : images)
        if(used.count(image.mNumber) == 0)
            available.push_back(image.mNumber);
    if(available.empty())
        for(const PortraitCatalog::Image& image : images)
            available.push_back(image.mNumber);
    uint32_t index = random(0, static_cast<uint32_t>(available.size()) - 1);
    if(index >= available.size())
        index = static_cast<uint32_t>(available.size()) - 1;
    return makeAppearance(catalogId, available[index]);
}

//! \brief Retries missing catalog identities only when the registry generation changes.
bool needsAppearanceCheck(bool appearanceEmpty, bool validated, bool noCatalog, uint32_t noCatalogGeneration,
    uint32_t currentGeneration)
{
    if(noCatalog && noCatalogGeneration == currentGeneration)
        return false;
    return appearanceEmpty || !validated;
}

//! \brief Maps the unchanged creature name hash onto current, numerically sorted image IDs.
CreatureAppearance pickStable(const PortraitCatalog& catalog, const std::string& catalogId,
    const std::string& creatureName)
{
    const std::vector<PortraitCatalog::Image>& images = catalog.getImages();
    if(images.empty())
        return CreatureAppearance();
    return makeAppearance(catalogId, images[stableHash(creatureName) % images.size()].mNumber);
}

//! \brief Keeps valid saved images and repairs legacy or removed images with the same stable rule.
bool validate(const PortraitCatalog& catalog, const std::string& catalogId,
    const std::string& creatureName, CreatureAppearance& appearance)
{
    if(appearance.getCatalogId() == catalogId && catalog.findImage(appearance.getImageNumber()) != nullptr)
        return false;
    CreatureAppearance replacement = pickStable(catalog, catalogId, creatureName);
    const bool changed = replacement != appearance;
    appearance = replacement;
    return changed;
}

//! \brief Uses the same single token field already present in save files and creature snapshots.
std::string toToken(const CreatureAppearance& appearance)
{
    if(appearance.isEmpty())
        return std::string();
    return appearance.getCatalogId() + ":" + std::to_string(appearance.getImageNumber());
}

//! \brief Accepts valid old part-choice syntax without retaining the removed runtime slot data.
bool fromToken(const std::string& token, CreatureAppearance& appearance)
{
    appearance = CreatureAppearance();
    const std::string::size_type colon = token.find(':');
    if(colon == std::string::npos || colon == 0 ||
        token.substr(0, colon).find_first_of(" \t\r\n/\\") != std::string::npos)
        return false;
    CreatureAppearance result;
    result.setCatalogId(token.substr(0, colon));
    const std::string value = token.substr(colon + 1);
    if(value.empty())
    {
        // A legacy catalog-only token is migrated from the name on the server.
        appearance = result;
        return true;
    }
    if(value.find('=') == std::string::npos)
    {
        uint32_t number = 0;
        if(!parseNumber(value, number))
            return false;
        result.setImageNumber(number);
    }
    else
    {
        std::string::size_type start = 0;
        while(start < value.size())
        {
            std::string::size_type end = value.find(',', start);
            if(end == std::string::npos)
                end = value.size();
            const std::string choice = value.substr(start, end - start);
            const std::string::size_type equal = choice.find('=');
            uint32_t unused = 0;
            if(equal == std::string::npos || equal == 0 ||
                choice.substr(0, equal).find_first_not_of("abcdefghijklmnopqrstuvwxyz") != std::string::npos ||
                !parseNumber(choice.substr(equal + 1), unused))
                return false;
            if(end + 1 == value.size())
                return false;
            start = end + 1;
        }
    }
    appearance = result;
    return true;
}
}
