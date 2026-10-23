/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef CREATUREAPPEARANCEPICTURE_H
#define CREATUREAPPEARANCEPICTURE_H

#include <string>
#include <vector>

class CreatureAppearance;
class PortraitCatalog;

namespace CEGUI
{
    class Image;
}

//! \brief Returns the stored whole JPEG, unchanged and square; nullptr requests the existing tinted fallback.
//! Loads on first request and keeps the existing bounded LRU cache; call from the GUI thread only.
//! Set the returned image immediately because later requests may evict older textures.
const CEGUI::Image* getCreatureAppearanceImage(const std::string& creatureName, const CreatureAppearance& appearance);

//! \brief Returns the client's cached whole-image catalog, or nullptr if it is missing or invalid.
const PortraitCatalog* getClientPortraitCatalog(const std::string& catalogId);

//! \brief The profile remarks that match the painted feature tags (config/dungeonbook-quirks.cfg), at most
//! DungeonbookQuirkLogic::MAX_REMARKS, chosen from the creature name and the appearance with a fixed hash
//! (same on every client and after loading). Empty if the appearance is empty or has no catalog. The caller
//! shows them only when getCreatureAppearanceImage() returned a picture, never in the fallback.
std::vector<std::string> getCreatureAppearanceRemarks(const std::string& creatureName,
    const CreatureAppearance& appearance);

//! \brief Releases all whole pictures and forgets the loaded catalogs and failures (end of a game,
//! next to clearCreatureProfilePortraits()).
void clearCreatureAppearancePictures();

#endif // CREATUREAPPEARANCEPICTURE_H
