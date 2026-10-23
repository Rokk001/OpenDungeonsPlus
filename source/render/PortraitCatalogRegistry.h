/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef PORTRAITCATALOGREGISTRY_H
#define PORTRAITCATALOGREGISTRY_H

#include "render/PortraitCatalog.h"

#include <map>
#include <memory>
#include <string>
#include <vector>

//! \brief Cache of loaded portrait catalogs: catalog id -> catalog, every catalog is read once.
//! Pure source without Ogre. A catalog id without a usable catalog is remembered as missing, so the
//! file is not read again and again. Messages (dropped entries, missing catalogs) are collected for the
//! caller, which logs them once with takeMessages().
class PortraitCatalogRegistry
{
public:
    //! \brief Starts with an empty catalog registry.
    PortraitCatalogRegistry()
    {
    }

    //! \brief Folder with one sub folder per catalog id, each holding its index.cfg. Resets the cache.
    void setAssetRoot(const std::string& assetRoot);

    //! \brief Returns the configured catalog folder.
    const std::string& getAssetRoot() const
    { return mAssetRoot; }

    //! \brief The catalog of the catalog id, loaded on first use. Returns nullptr if there is none or it
    //! is invalid as a whole (the caller then uses the fallback picture).
    const PortraitCatalog* getCatalog(const std::string& catalogId);

    //! \brief True if the folder of the catalog id holds an index.cfg file (it is not loaded or validated).
    //! The answer is remembered; it is looked up again only after invalidateCatalogs(), so asking for many
    //! creatures does not touch the file system each time.
    bool hasCatalog(const std::string& catalogId) const;

    //! \brief Forgets the remembered hasCatalog answers (new folders are found) and counts a new generation.
    void invalidateCatalogs();

    //! \brief Changes with every invalidateCatalogs() and clear(); a creature without a catalog id looks again
    //! only when it changes.
    uint32_t getCatalogGeneration() const
    { return mCatalogGeneration; }

    //! \brief Forgets everything that was loaded (also the missing ones).
    void clear();

    //! \brief Makes the next getCatalog call load every catalog id again that failed before (missing or
    //! invalid catalog), so a catalog that was added or repaired later is found without a restart. The
    //! callers use it now and then (every few seconds), never every frame, because loading reads files.
    //! Catalogs that loaded fine are kept. Returns true if there was a failed catalog id.
    bool retryFailed();

    //! \brief Hands out the messages collected since the last call.
    std::vector<std::string> takeMessages();

private:
    std::string mAssetRoot;
    //! nullptr values are catalog ids whose catalog is missing or invalid
    std::map<std::string, std::shared_ptr<PortraitCatalog> > mCatalogs;
    std::vector<std::string> mMessages;
    //! The problem text of the catalog ids that failed, so a failure that stays the same is reported once
    std::map<std::string, std::string> mFailures;
    mutable std::map<std::string, bool> mCatalogAnswers;
    uint32_t mCatalogGeneration = 0;
};

#endif // PORTRAITCATALOGREGISTRY_H
