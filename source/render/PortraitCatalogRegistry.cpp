/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "render/PortraitCatalogRegistry.h"

#include <fstream>

//! \brief Sets the catalog folder and discards cached lookups.
void PortraitCatalogRegistry::setAssetRoot(const std::string& assetRoot)
{
    mAssetRoot = assetRoot;
    if(!mAssetRoot.empty() && mAssetRoot[mAssetRoot.size() - 1] != '/' && mAssetRoot[mAssetRoot.size() - 1] != '\\')
        mAssetRoot += "/";

    clear();
}

//! \brief Loads a safe catalog ID once and reports new failures.
const PortraitCatalog* PortraitCatalogRegistry::getCatalog(const std::string& catalogId)
{
    if(catalogId.empty() || catalogId == "." || catalogId == ".." ||
        catalogId.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.") != std::string::npos)
        return nullptr;

    std::map<std::string, std::shared_ptr<PortraitCatalog> >::iterator it = mCatalogs.find(catalogId);
    if(it != mCatalogs.end())
        return it->second.get();

    std::shared_ptr<PortraitCatalog> catalog(new PortraitCatalog());
    std::string path = mAssetRoot + catalogId + "/index.cfg";
    bool loaded = catalog->loadFromFile(path);

    std::vector<std::string> messages = catalog->getErrors();
    if(!loaded)
        messages.push_back("Portrait catalog of " + catalogId + " is missing or invalid: " + path);

    std::string text;
    for(std::vector<std::string>::const_iterator message = messages.begin(); message != messages.end(); ++message)
        text += *message + "\n";

    // A problem is reported when it is new; a catalog that stays broken is not reported at every retry
    std::map<std::string, std::string>::iterator failure = mFailures.find(catalogId);
    if(!text.empty() && ((failure == mFailures.end()) || (failure->second != text)))
        mMessages.insert(mMessages.end(), messages.begin(), messages.end());

    if(!loaded)
    {
        mFailures[catalogId] = text;
        catalog.reset();
    }
    else if(failure != mFailures.end())
    {
        mFailures.erase(failure);
    }

    mCatalogs[catalogId] = catalog;
    return catalog.get();
}

//! \brief Caches whether a safe catalog ID has an index.
bool PortraitCatalogRegistry::hasCatalog(const std::string& catalogId) const
{
    if(catalogId.empty() || catalogId == "." || catalogId == ".." ||
        catalogId.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.") != std::string::npos)
        return false;

    std::map<std::string, bool>::const_iterator known = mCatalogAnswers.find(catalogId);
    if(known != mCatalogAnswers.end())
        return known->second;

    std::ifstream file((mAssetRoot + catalogId + "/index.cfg").c_str());
    bool exists = file.good();
    mCatalogAnswers[catalogId] = exists;
    return exists;
}

//! \brief Refreshes catalog existence lookups for creatures that had no catalog.
void PortraitCatalogRegistry::invalidateCatalogs()
{
    mCatalogAnswers.clear();
    ++mCatalogGeneration;
}

//! \brief Clears loaded catalogs and their remembered failures.
void PortraitCatalogRegistry::clear()
{
    mCatalogs.clear();
    mFailures.clear();
    invalidateCatalogs();
}

//! \brief Retries failed catalogs while retaining valid ones.
bool PortraitCatalogRegistry::retryFailed()
{
    bool anyFailed = false;
    std::map<std::string, std::shared_ptr<PortraitCatalog> >::iterator it = mCatalogs.begin();
    while(it != mCatalogs.end())
    {
        if(it->second)
        {
            ++it;
            continue;
        }

        anyFailed = true;
        mCatalogs.erase(it++);
    }
    return anyFailed;
}

//! \brief Returns and clears newly collected load messages.
std::vector<std::string> PortraitCatalogRegistry::takeMessages()
{
    std::vector<std::string> messages;
    messages.swap(mMessages);
    return messages;
}
