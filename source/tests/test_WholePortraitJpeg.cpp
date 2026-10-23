/*
 * Copyright (C) 2026 OpenDungeons Team
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#define BOOST_TEST_MODULE WholePortraitJpeg
#include "BoostTestTargetConfig.h"
#include <Ogre.h>
#include <OgreDataStream.h>
#include <fstream>
#include <iterator>
#include <vector>

//! \brief The integrator loads a delivered JPEG through the same deployed codec and stream path.
BOOST_AUTO_TEST_CASE(load_delivered_jpeg_without_rendering)
{
    Ogre::Root root("", "", "");
    root.loadPlugin("Codec_STBI");
    std::ifstream file(OD_WHOLE_PORTRAIT_SAMPLE, std::ios::binary);
    std::vector<char> bytes((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
    BOOST_REQUIRE(!bytes.empty());
    Ogre::DataStreamPtr stream(new Ogre::MemoryDataStream(&bytes[0], bytes.size(), false, true));
    Ogre::Image image;
    image.load(stream, "jpg");
    BOOST_CHECK_EQUAL(image.getWidth(), 1024u);
    BOOST_CHECK_EQUAL(image.getHeight(), 1024u);
}
