/*
 * Copyright (C) 2026 OpenDungeons Team
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#define BOOST_TEST_MODULE DungeonbookQuirks
#include "BoostTestTargetConfig.h"
#include "game/CreatureAppearance.h"
#include "render/PortraitCatalog.h"
#include "render/DungeonbookQuirks.h"
#include <sstream>

//! \brief Selects stable remarks only from tags painted into the chosen whole image.
BOOST_AUTO_TEST_CASE(actual_feature_tags)
{
    PortraitCatalog catalog;
    std::istringstream images("1\t01.jpg\thair-swept,eyepatch,cigar,scar-diagonal\n2\t02.jpg\thair-braided\n");
    BOOST_REQUIRE(catalog.loadFromStream(images, "", "fixture"));
    std::istringstream lines("eyepatch\tDistrusts the other eye.\ncigar\tCounts smoke as strategy.\nscar-diagonal\tBlames a doorway.\n");
    DungeonbookQuirks quirks;
    quirks.loadFromStream(lines, "fixture");
    CreatureAppearance appearance;
    appearance.setCatalogId("Goblin.mesh");
    appearance.setImageNumber(1);
    BOOST_CHECK_EQUAL(DungeonbookQuirkLogic::collectRemarks(quirks, catalog, appearance).size(), 3u);
    std::vector<std::string> chosen = DungeonbookQuirkLogic::selectRemarks(quirks, catalog, appearance, "Brak");
    BOOST_CHECK_EQUAL(chosen.size(), 2u);
    BOOST_CHECK(chosen == DungeonbookQuirkLogic::selectRemarks(quirks, catalog, appearance, "Brak"));
    appearance.setImageNumber(2);
    BOOST_CHECK(DungeonbookQuirkLogic::selectRemarks(quirks, catalog, appearance, "Brak").empty());
    appearance.setImageNumber(3);
    BOOST_CHECK(DungeonbookQuirkLogic::selectRemarks(quirks, catalog, appearance, "Brak").empty());
}

//! \brief Rejects obsolete rows and preserves first-wins warning behavior.
BOOST_AUTO_TEST_CASE(malformed_and_duplicate_tags)
{
    std::istringstream lines("eyepatch\tFirst.\neyepatch\tSecond.\neye\tpatch\tOld format.\n");
    DungeonbookQuirks quirks;
    quirks.loadFromStream(lines, "fixture");
    BOOST_REQUIRE_EQUAL(quirks.size(), 1u);
    BOOST_CHECK_EQUAL(*quirks.find("eyepatch"), "First.");
    BOOST_CHECK_EQUAL(quirks.getWarnings().size(), 2u);
    BOOST_CHECK(quirks.find("missing") == nullptr);
}
