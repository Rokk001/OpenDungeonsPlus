/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "render/CreatureAppearancePicture.h"

#include "game/CreatureAppearance.h"
#include "render/DungeonbookAppearanceConfig.h"
#include "render/DungeonbookQuirks.h"
#include "render/PortraitCatalog.h"
#include "render/PortraitCatalogRegistry.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/ResourceManager.h"

#include <Ogre.h>
#include <OgreDataStream.h>
#include <OgreHardwarePixelBuffer.h>

#include <CEGUI/BasicImage.h>
#include <CEGUI/ImageManager.h>
#include <CEGUI/RendererModules/Ogre/Renderer.h>
#include <CEGUI/System.h>
#include <CEGUI/Texture.h>

#include <chrono>
#include <fstream>
#include <iterator>
#include <set>
#include <stdexcept>
#include <vector>

namespace
{
const std::string PICTURE_PREFIX = "DungeonbookAppearance/";

//! \brief One whole-picture cache entry, ordered by most recent use.
struct CacheEntry
{
    std::string mKey;
    uint64_t mBytes;
};

//! \brief Client-side whole-image catalogs, GPU cache and one-time failures.
struct PictureState
{
    //! \brief Starts with unloaded catalog and remark configuration.
    PictureState() :
        mInitialized(false)
    {
    }

    bool mInitialized;
    PortraitCatalogRegistry mRegistry;
    DungeonbookAppearanceConfig mConfig;
    //! Profile remarks (config/dungeonbook-quirks.cfg)
    DungeonbookQuirks mQuirks;
    //! Cached pictures, least recently used first
    std::vector<CacheEntry> mEntries;
    //! Catalog ids and picture keys that failed; they are logged once and not tried again until the map is
    //! unloaded. Only failures that come from the files, never the empty appearance.
    std::set<std::string> mFailed;
    //! What was logged already (catalog id or key plus the reason), so a failure that repeats is logged once
    std::set<std::string> mLogged;
    //! Last time the failed pictures and catalogs were given another chance
    std::chrono::steady_clock::time_point mLastRetry;
};

//! Seconds between two new tries of failed catalogs and pictures (they read files, so never every frame)
const int RETRY_SECONDS = 10;

//! \brief Owns the single client-side whole-image state.
PictureState& getRawState()
{
    static PictureState state;
    return state;
}

//! \brief Loads whole-image catalog and quirk configuration once.
PictureState& getState()
{
    PictureState& state = getRawState();
    if(state.mInitialized)
        return state;

    state.mInitialized = true;
    std::string path = ConfigManager::getSingleton().getConfigPath();
    if(!path.empty() && (path[path.size() - 1] != '/') && (path[path.size() - 1] != '\\'))
        path += "/";

    state.mConfig.loadFromFile(path + "dungeonbook-appearance.cfg");
    const std::vector<std::string>& warnings = state.mConfig.getWarnings();
    for(std::vector<std::string>::const_iterator it = warnings.begin(); it != warnings.end(); ++it)
    {
        OD_LOG_WRN("Dungeonbook appearance: " + *it);
    }

    // Same root resolution as the server registry
    std::string root = state.mConfig.getAssetRoot();
    if(root.empty())
        root = "materials/portraits/whole";

    bool isAbsolute = (root.size() > 1) && ((root[1] == ':') || (root[0] == '/') || (root[0] == '\\'));
    if(!isAbsolute)
        root = ResourceManager::getSingleton().getGameDataPath() + root;

    state.mRegistry.setAssetRoot(root);

    // A missing file or a bad line only costs the remarks
    state.mQuirks.loadFromFile(path + "dungeonbook-quirks.cfg");
    const std::vector<std::string>& quirkWarnings = state.mQuirks.getWarnings();
    for(std::vector<std::string>::const_iterator it = quirkWarnings.begin(); it != quirkWarnings.end(); ++it)
    {
        OD_LOG_WRN("Dungeonbook quirks: " + *it);
    }
    return state;
}

//! \brief Logs newly reported catalog failures once.
void logRegistryMessages(PictureState& state)
{
    std::vector<std::string> messages = state.mRegistry.takeMessages();
    for(std::vector<std::string>::const_iterator it = messages.begin(); it != messages.end(); ++it)
    {
        OD_LOG_WRN("Dungeonbook appearance: " + *it);
    }
}

//! Logs the reason once per catalog id or picture key and remembers the failure
void rememberFailure(PictureState& state, const std::string& failedKey, const std::string& reason)
{
    state.mFailed.insert(failedKey);
    if(state.mLogged.insert(failedKey + "|" + reason).second)
    {
        OD_LOG_WRN("Dungeonbook appearance of " + failedKey + " falls back to the creature portrait: " + reason);
    }
}

//! \brief Loads a whole square image using its actual file extension, without composition or tint.
bool loadRgbaImage(const std::string& path, std::vector<uint8_t>& pixels, uint32_t& width,
    uint32_t& height, std::string& error)
{
    std::ifstream file(path.c_str(), std::ios::in | std::ios::binary);
    std::vector<char> bytes((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    if(bytes.empty())
    {
        error = "cannot read " + path;
        return false;
    }
    try
    {
        const std::string::size_type dot = path.find_last_of('.');
        if(dot == std::string::npos)
            throw std::runtime_error("image extension missing");
        const std::string extension = path.substr(dot + 1);
        Ogre::DataStreamPtr stream(new Ogre::MemoryDataStream(&bytes[0], bytes.size(), false, true));
        Ogre::Image image;
        image.load(stream, extension);
        width = static_cast<uint32_t>(image.getWidth());
        height = static_cast<uint32_t>(image.getHeight());
        if(width != 1024 || height != 1024)
            throw std::runtime_error("whole portraits must be 1024 by 1024");
        pixels.resize(static_cast<size_t>(width) * height * 4);
        Ogre::PixelBox box(width, height, 1, Ogre::PF_BYTE_RGBA, &pixels[0]);
        Ogre::PixelUtil::bulkPixelConversion(image.getPixelBox(), box);
    }
    catch(const std::exception& exception)
    {
        error = "cannot decode " + path + ": " + exception.what();
        return false;
    }
    return true;
}

//! Destroys the CEGUI image and texture of a cached picture (the Ogre texture belongs to the CEGUI texture)
void destroyPicture(const std::string& name)
{
    CEGUI::ImageManager& images = CEGUI::ImageManager::getSingleton();
    CEGUI::Renderer& renderer = *CEGUI::System::getSingleton().getRenderer();
    if(images.isDefined(name))
        images.destroy(name);
    if(renderer.isTextureDefined(name))
        renderer.destroyTexture(name);
}

//! \brief Uploads the selected JPEG as-is, preserving its whole square and natural painted colors.
const CEGUI::Image* buildPicture(PictureState& state, const CreatureAppearance& appearance,
    const PortraitCatalog& catalog, const std::string& name, uint64_t& bytes, std::string& error)
{
    const PortraitCatalog::Image* entry = catalog.findImage(appearance.getImageNumber());
    if(entry == nullptr)
    {
        error = "selected whole image is not listed";
        return nullptr;
    }
    uint32_t width = 0;
    uint32_t height = 0;
    std::vector<uint8_t> data;
    if(!loadRgbaImage(entry->mPath, data, width, height, error))
        return nullptr;

    CEGUI::OgreRenderer& renderer = static_cast<CEGUI::OgreRenderer&>(*CEGUI::System::getSingleton().getRenderer());
    CEGUI::ImageManager& images = CEGUI::ImageManager::getSingleton();
    Ogre::TexturePtr texture;
    try
    {
        texture = Ogre::TextureManager::getSingleton().createManual(name, "General", Ogre::TEX_TYPE_2D,
            width, height, 0, Ogre::PF_BYTE_RGBA, Ogre::TU_DEFAULT);
        texture->getBuffer()->blitFromMemory(Ogre::PixelBox(width, height, 1, Ogre::PF_BYTE_RGBA, &data[0]));

        CEGUI::Texture& guiTexture = renderer.createTexture(name, texture, true);
        CEGUI::BasicImage& image = static_cast<CEGUI::BasicImage&>(images.create("BasicImage", name));
        image.setTexture(&guiTexture);
        image.setArea(CEGUI::Rectf(0.0f, 0.0f, static_cast<float>(width), static_cast<float>(height)));
        image.setAutoScaled(CEGUI::ASM_Disabled);
        bytes = static_cast<uint64_t>(width) * height * 4;
        return &image;
    }
    catch(const std::exception& e)
    {
        error = std::string("texture creation failed: ") + e.what();
    }

    if(images.isDefined(name))
        images.destroy(name);
    if(renderer.isTextureDefined(name))
        renderer.destroyTexture(name);
    else if(texture)
        Ogre::TextureManager::getSingleton().remove(texture->getHandle());
    return nullptr;
}
//! \brief Moves an existing whole picture to the most recently used position.
bool cacheTouch(std::vector<CacheEntry>& entries, const std::string& key)
{
    for(size_t i = 0; i < entries.size(); ++i)
    {
        if(entries[i].mKey != key)
            continue;

        CacheEntry entry = entries[i];
        entries.erase(entries.begin() + i);
        entries.push_back(entry);
        return true;
    }
    return false;
}

//! \brief Adds or replaces one whole-picture cache record.
void cacheAdd(std::vector<CacheEntry>& entries, const std::string& key, uint64_t bytes)
{
    for(size_t i = 0; i < entries.size(); ++i)
    {
        if(entries[i].mKey == key)
        {
            entries.erase(entries.begin() + i);
            break;
        }
    }

    CacheEntry entry;
    entry.mKey = key;
    entry.mBytes = bytes;
    entries.push_back(entry);
}

//! \brief Enforces the existing picture/memory bounds while keeping the newest four images.
std::vector<std::string> cacheEvict(std::vector<CacheEntry>& entries, uint32_t maxPictures, uint64_t maxBytes,
    uint32_t keepNewest)
{
    std::vector<std::string> removed;
    uint64_t total = 0;
    for(size_t i = 0; i < entries.size(); ++i)
        total += entries[i].mBytes;

    while((entries.size() > keepNewest) && ((entries.size() > maxPictures) || (total > maxBytes)))
    {
        removed.push_back(entries.front().mKey);
        total -= entries.front().mBytes;
        entries.erase(entries.begin());
    }
    return removed;
}

}

//! \brief Shows a stored whole portrait, falling back through the existing caller on any failure.
const CEGUI::Image* getCreatureAppearanceImage(const std::string& creatureName, const CreatureAppearance& appearance)
{
    if(appearance.isEmpty())
        return nullptr;
    PictureState& state = getState();
    const std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
    if(!state.mFailed.empty() && now - state.mLastRetry >= std::chrono::seconds(RETRY_SECONDS))
    {
        state.mLastRetry = now;
        state.mFailed.clear();
        state.mRegistry.retryFailed();
    }
    const std::string& catalogId = appearance.getCatalogId();
    if(state.mFailed.count(catalogId) != 0)
        return nullptr;
    const PortraitCatalog* catalog = state.mRegistry.getCatalog(catalogId);
    logRegistryMessages(state);
    if(catalog == nullptr)
    {
        rememberFailure(state, catalogId, "no valid whole-image catalog");
        return nullptr;
    }
    CreatureAppearance shown = appearance;
    CreatureAppearanceLogic::validate(*catalog, catalogId, creatureName, shown);
    if(shown.isEmpty())
        return nullptr;
    const std::string key = CreatureAppearanceLogic::toToken(shown);
    const std::string name = PICTURE_PREFIX + key;
    if(state.mFailed.count(key) != 0)
        return nullptr;
    CEGUI::ImageManager& images = CEGUI::ImageManager::getSingleton();
    if(cacheTouch(state.mEntries, key) && images.isDefined(name))
        return &images.get(name);
    uint64_t bytes = 0;
    std::string error;
    const CEGUI::Image* image = buildPicture(state, shown, *catalog, name, bytes, error);
    if(image == nullptr)
    {
        rememberFailure(state, key, error);
        return nullptr;
    }
    cacheAdd(state.mEntries, key, bytes);
    const uint64_t maxBytes = static_cast<uint64_t>(state.mConfig.getMaxCacheMegabytes()) * 1024 * 1024;
    const std::vector<std::string> evicted = cacheEvict(state.mEntries,
        state.mConfig.getMaxCachedPictures(), maxBytes, 4);
    for(const std::string& removed : evicted)
        destroyPicture(PICTURE_PREFIX + removed);
    return image;
}

//! \brief Exposes the cached whole-image catalog to client callers.
const PortraitCatalog* getClientPortraitCatalog(const std::string& catalogId)
{
    PictureState& state = getState();
    const PortraitCatalog* catalog = state.mRegistry.getCatalog(catalogId);
    logRegistryMessages(state);
    return catalog;
}

//! \brief Selects stable remarks from the feature tags of the same displayed image.
std::vector<std::string> getCreatureAppearanceRemarks(const std::string& creatureName,
    const CreatureAppearance& appearance)
{
    if(appearance.isEmpty())
        return std::vector<std::string>();

    PictureState& state = getState();
    const PortraitCatalog* catalog = state.mRegistry.getCatalog(appearance.getCatalogId());
    logRegistryMessages(state);
    if(catalog == nullptr)
        return std::vector<std::string>();

    CreatureAppearance shown = appearance;
    CreatureAppearanceLogic::validate(*catalog, appearance.getCatalogId(), creatureName, shown);
    return DungeonbookQuirkLogic::selectRemarks(state.mQuirks, *catalog, shown, creatureName);
}

//! \brief Releases whole-image GPU resources and catalog/failure caches when a game ends.
void clearCreatureAppearancePictures()
{
    PictureState& state = getRawState();
    if(!state.mInitialized)
        return;

    for(std::vector<CacheEntry>::const_iterator it = state.mEntries.begin();
        it != state.mEntries.end(); ++it)
    {
        destroyPicture(PICTURE_PREFIX + it->mKey);
    }
    state.mEntries.clear();
    state.mFailed.clear();
    state.mLogged.clear();
    state.mRegistry.clear();
}
