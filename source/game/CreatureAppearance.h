/*
 *  Copyright (C) 2026 OpenDungeons Team
 *  SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef CREATUREAPPEARANCE_H
#define CREATUREAPPEARANCE_H

#include <stdint.h>
#include <functional>
#include <string>
#include <vector>

class PortraitCatalog;

//! \brief Server-assigned catalog and permanent whole-portrait image number, saved and sent together.
class CreatureAppearance
{
public:
    //! \brief Starts without an assigned portrait.
    CreatureAppearance() : mImageNumber(0) {}
    //! \brief Returns the creature's portrait catalog identity.
    const std::string& getCatalogId() const { return mCatalogId; }
    //! \brief Sets the catalog while preserving its assigned image number.
    void setCatalogId(const std::string& catalogId) { mCatalogId = catalogId; }
    //! \brief Returns the permanent image number, or zero before migration/assignment.
    uint32_t getImageNumber() const { return mImageNumber; }
    //! \brief Stores the permanent image number chosen by the server.
    void setImageNumber(uint32_t number) { mImageNumber = number; }
    //! \brief Reports whether a usable portrait has not yet been assigned.
    bool isEmpty() const { return mCatalogId.empty() || mImageNumber == 0; }
    //! \brief Compares the stored catalog and image number.
    bool operator==(const CreatureAppearance& other) const;
    //! \brief Reports a different stored catalog or image number.
    bool operator!=(const CreatureAppearance& other) const { return !(*this == other); }
private:
    std::string mCatalogId;
    uint32_t mImageNumber;
};

namespace CreatureAppearanceLogic
{
//! \brief Inclusive integer random source, supplied by the server.
typedef std::function<uint32_t(uint32_t, uint32_t)> RandomFunction;
//! \brief Catalog existence lookup, retaining the existing gender fallback.
typedef std::function<bool(const std::string&)> CatalogExistsFunction;
//! \brief Computes platform-independent 32-bit FNV-1a from the original name bytes.
uint32_t stableHash(const std::string& text);
//! \brief Resolves the gender-specific catalog, then the original mesh catalog, or returns empty.
std::string resolveCatalogId(const std::string& meshName, const std::string& gender,
    const CatalogExistsFunction& exists);
//! \brief Chooses uniformly among unused images; duplicates are allowed only after all are taken.
CreatureAppearance pickRandom(const PortraitCatalog& catalog, const std::string& catalogId,
    const RandomFunction& random, const std::vector<CreatureAppearance>& taken);
//! \brief Retains the existing periodic retry policy for missing or unvalidated catalogs.
bool needsAppearanceCheck(bool appearanceEmpty, bool validated, bool noCatalog, uint32_t noCatalogGeneration,
    uint32_t currentGeneration);
//! \brief Migrates old saves or missing image IDs using the stable name hash and sorted image numbers.
CreatureAppearance pickStable(const PortraitCatalog& catalog, const std::string& catalogId,
    const std::string& creatureName);
//! \brief Preserves an existing image, replacing absent/removed IDs deterministically; returns whether changed.
bool validate(const PortraitCatalog& catalog, const std::string& catalogId,
    const std::string& creatureName, CreatureAppearance& appearance);
//! \brief Serializes one whitespace-free catalog:image-number token for saves and network snapshots.
std::string toToken(const CreatureAppearance& appearance);
//! \brief Reads current tokens or accepts legacy part-choice tokens as pending stable migration.
bool fromToken(const std::string& token, CreatureAppearance& appearance);
}
#endif
