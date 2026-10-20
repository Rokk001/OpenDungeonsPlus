/*
 * Copyright (C) 2026 OpenDungeons Team
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#define BOOST_TEST_MODULE PortraitCatalog
#include "BoostTestTargetConfig.h"
#include "render/PortraitCatalog.h"
#include <sstream>

//! \brief Keeps permanent numeric order and tags without filling reserved gaps.
BOOST_AUTO_TEST_CASE(images_and_reserved_numbers)
{
    PortraitCatalog catalog;
    std::istringstream rows("3\t03.jpg\thair-braided\n# retired 2\n1\t01.jpg\thair-swept,eyepatch\n");
    BOOST_REQUIRE(catalog.loadFromStream(rows, "whole/", "fixture"));
    BOOST_CHECK_EQUAL(catalog.getImages().size(), 2u);
    BOOST_CHECK_EQUAL(catalog.getImages()[0].mNumber, 1u);
    BOOST_CHECK_EQUAL(catalog.findImage(1)->mPath, "whole/01.jpg");
    BOOST_CHECK_EQUAL(catalog.findImage(1)->mTags[1], "eyepatch");
    BOOST_CHECK(catalog.findImage(2) == nullptr);
}

//! \brief Rejects malformed or ambiguous indices instead of inventing a portrait.
BOOST_AUTO_TEST_CASE(invalid_catalogs_fall_back)
{
    for(const char* text : {"", "0\t00.jpg\thair-swept\n", "1\t../01.jpg\thair-swept\n",
        "1\t01.png\thair-swept\n", "1\t02.jpg\thair-swept\n", "1\t01.jpg\t\n",
        "1\t01.jpg\thair swept\n", "1\t01.jpg\thair-swept,\n", "1\t01.jpg\thair-swept,hair-swept\n",
        "1\t01.jpg\thair-swept\n1\t01.jpg\thair-other\n", "4294967296\t01.jpg\thair-swept\n"})
    {
        PortraitCatalog catalog;
        std::istringstream rows(text);
        BOOST_CHECK(!catalog.loadFromStream(rows, "", "invalid"));
        BOOST_CHECK(catalog.getImages().empty());
    }
}
