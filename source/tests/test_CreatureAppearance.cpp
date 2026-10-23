/*
 * Copyright (C) 2026 OpenDungeons Team
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#define BOOST_TEST_MODULE CreatureAppearance
#include "BoostTestTargetConfig.h"
#include "game/CreatureAppearance.h"
#include "render/PortraitCatalog.h"
#include <sstream>
#include <set>

//! \brief Supplies the fifty-image catalog, optionally with a permanently removed image.
PortraitCatalog makeCatalog(uint32_t removed = 0)
{
    std::ostringstream rows;
    for(uint32_t n = 1; n <= 50; ++n)
        if(n != removed)
            rows << n << "\t" << (n < 10 ? "0" : "") << n << ".jpg\thair-swept\n";
    std::istringstream stream(rows.str());
    PortraitCatalog catalog;
    BOOST_REQUIRE(catalog.loadFromStream(stream, "", "fixture"));
    return catalog;
}

//! \brief Selects the first candidate even when all previous draws chose the first candidate.
uint32_t chooseFirst(uint32_t lower, uint32_t upper)
{
    BOOST_REQUIRE(lower <= upper);
    return lower;
}

//! \brief Lists the fixture catalogs used to verify gender fallback.
bool fixtureCatalogExists(const std::string& id)
{
    return id == "Elf.mesh-male" || id == "Goblin.mesh";
}

//! \brief Uses all fifty images before a duplicate and scopes uniqueness to the keeper's catalog.
BOOST_AUTO_TEST_CASE(unique_fifty_then_duplicate)
{
    PortraitCatalog catalog = makeCatalog();
    std::vector<CreatureAppearance> taken;
    std::set<uint32_t> used;
    for(uint32_t n = 0; n < 50; ++n)
    {
        CreatureAppearance next = CreatureAppearanceLogic::pickRandom(catalog, "Goblin.mesh", chooseFirst, taken);
        BOOST_CHECK(used.insert(next.getImageNumber()).second);
        taken.push_back(next);
    }
    BOOST_CHECK_EQUAL(used.size(), 50u);
    BOOST_CHECK(used.count(CreatureAppearanceLogic::pickRandom(catalog, "Goblin.mesh", chooseFirst, taken).getImageNumber()));
    taken[0].setCatalogId("Other.mesh");
    BOOST_CHECK_EQUAL(CreatureAppearanceLogic::pickRandom(catalog, "Goblin.mesh", chooseFirst, taken).getImageNumber(), 1u);
}

//! \brief Preserves valid saves, deterministically migrates old choices and repairs removed numbers.
BOOST_AUTO_TEST_CASE(stable_migration_and_save_roundtrip)
{
    BOOST_CHECK_EQUAL(CreatureAppearanceLogic::stableHash(""), 2166136261u);
    BOOST_CHECK_EQUAL(CreatureAppearanceLogic::stableHash("a"), 3826002220u);
    PortraitCatalog full = makeCatalog();
    CreatureAppearance saved = CreatureAppearanceLogic::pickStable(full, "Goblin.mesh", "Brak"), restored;
    BOOST_REQUIRE(CreatureAppearanceLogic::fromToken(CreatureAppearanceLogic::toToken(saved), restored));
    BOOST_CHECK(saved == restored);
    BOOST_CHECK(!CreatureAppearanceLogic::validate(full, "Goblin.mesh", "Changed name", saved));
    BOOST_REQUIRE(CreatureAppearanceLogic::fromToken("Goblin.mesh:hair=2,eyes=3,mouth=1", restored));
    BOOST_CHECK_EQUAL(restored.getImageNumber(), 0u);
    CreatureAppearance catalogOnly;
    BOOST_REQUIRE(CreatureAppearanceLogic::fromToken("Goblin.mesh:", catalogOnly));
    BOOST_CHECK(CreatureAppearanceLogic::validate(full, "Goblin.mesh", "Brak", catalogOnly));
    BOOST_CHECK(saved == catalogOnly);
    BOOST_CHECK(CreatureAppearanceLogic::validate(full, "Goblin.mesh", "Brak", restored));
    BOOST_CHECK(saved == restored);
    PortraitCatalog reduced = makeCatalog(saved.getImageNumber());
    CreatureAppearance client = saved;
    BOOST_CHECK(CreatureAppearanceLogic::validate(reduced, "Goblin.mesh", "Brak", saved));
    BOOST_CHECK(CreatureAppearanceLogic::validate(reduced, "Goblin.mesh", "Brak", client));
    BOOST_CHECK(saved == client);
    for(const char* bad : {"", ":1", "Goblin.mesh:-1", "Goblin.mesh:0", "Goblin.mesh:4294967296",
        "Goblin.mesh:eyes=0", "Goblin.mesh:eyes=1,", "Goblin.mesh:eyes=1,,mouth=2"})
        BOOST_CHECK(!CreatureAppearanceLogic::fromToken(bad, restored));
}

//! \brief Retains gender fallback, bounded retries and absence of invented images in empty catalogs.
BOOST_AUTO_TEST_CASE(fallback_and_retry)
{
    CreatureAppearanceLogic::CatalogExistsFunction exists = fixtureCatalogExists;
    BOOST_CHECK_EQUAL(CreatureAppearanceLogic::resolveCatalogId("Elf.mesh", "Male", exists), "Elf.mesh-male");
    BOOST_CHECK_EQUAL(CreatureAppearanceLogic::resolveCatalogId("Goblin.mesh", "Female", exists), "Goblin.mesh");
    BOOST_CHECK(CreatureAppearanceLogic::resolveCatalogId("Missing.mesh", "Male", exists).empty());
    BOOST_CHECK(!CreatureAppearanceLogic::needsAppearanceCheck(true, false, true, 7, 7));
    BOOST_CHECK(CreatureAppearanceLogic::needsAppearanceCheck(true, false, true, 7, 8));
    BOOST_CHECK(!CreatureAppearanceLogic::needsAppearanceCheck(false, true, false, 0, 0));
    PortraitCatalog empty;
    BOOST_CHECK(CreatureAppearanceLogic::pickRandom(empty, "Missing.mesh", chooseFirst, {}).isEmpty());
    BOOST_CHECK(CreatureAppearanceLogic::pickStable(empty, "Missing.mesh", "Brak").isEmpty());
}
