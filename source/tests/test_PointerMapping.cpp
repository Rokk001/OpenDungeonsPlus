/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "modes/PointerMapping.h"

#define BOOST_TEST_MODULE PointerMapping
#include "BoostTestTargetConfig.h"

namespace
{
const int WINDOW_SIZES[3][2] = {{640, 480}, {1920, 1200}, {7680, 4320}};
const int UI_SCALES[2] = {80, 120};

void checkPoint(int clientX, int clientY, int width, int height, int scale, int expectedX, int expectedY)
{
    PointerMapping::Point point = PointerMapping::clientToGamePointer(clientX, clientY, width, height,
        width, height, scale);
    BOOST_CHECK_EQUAL(point.mX, expectedX);
    BOOST_CHECK_EQUAL(point.mY, expectedY);
}
}

BOOST_AUTO_TEST_CASE(test_inside_positions_are_one_to_one)
{
    for(int s = 0; s < 3; ++s)
    {
        const int width = WINDOW_SIZES[s][0];
        const int height = WINDOW_SIZES[s][1];
        for(int u = 0; u < 2; ++u)
        {
            checkPoint(0, 0, width, height, UI_SCALES[u], 0, 0);
            checkPoint(width / 2, height / 3, width, height, UI_SCALES[u], width / 2, height / 3);
            checkPoint(width - 1, height - 1, width, height, UI_SCALES[u], width - 1, height - 1);
        }
    }
}

BOOST_AUTO_TEST_CASE(test_outside_positions_stay_at_nearest_edge)
{
    for(int s = 0; s < 3; ++s)
    {
        const int width = WINDOW_SIZES[s][0];
        const int height = WINDOW_SIZES[s][1];
        for(int u = 0; u < 2; ++u)
        {
            checkPoint(-5, -9, width, height, UI_SCALES[u], 0, 0);
            checkPoint(width, height, width, height, UI_SCALES[u], width - 1, height - 1);
            checkPoint(width + 500, height / 2, width, height, UI_SCALES[u], width - 1, height / 2);
            checkPoint(-1, height + 7, width, height, UI_SCALES[u], 0, height - 1);
        }
    }
}

BOOST_AUTO_TEST_CASE(test_ui_scale_does_not_change_the_position)
{
    PointerMapping::Point low = PointerMapping::clientToGamePointer(1000, 700, 1920, 1200, 1920, 1200, 80);
    PointerMapping::Point high = PointerMapping::clientToGamePointer(1000, 700, 1920, 1200, 1920, 1200, 120);
    BOOST_CHECK_EQUAL(low.mX, high.mX);
    BOOST_CHECK_EQUAL(low.mY, high.mY);
    BOOST_CHECK_EQUAL(low.mX, 1000);
    BOOST_CHECK_EQUAL(low.mY, 700);
}

BOOST_AUTO_TEST_CASE(test_client_and_render_size_differ)
{
    // Client area half the size of the render window: positions are scaled proportionally
    PointerMapping::Point point = PointerMapping::clientToGamePointer(960, 600, 1920, 1200, 3840, 2400, 100);
    BOOST_CHECK_EQUAL(point.mX, 1920);
    BOOST_CHECK_EQUAL(point.mY, 1200);
    point = PointerMapping::clientToGamePointer(5000, 5000, 1920, 1200, 3840, 2400, 100);
    BOOST_CHECK_EQUAL(point.mX, 3839);
    BOOST_CHECK_EQUAL(point.mY, 2399);
}

BOOST_AUTO_TEST_CASE(test_differing_sizes_map_first_and_last_pixel)
{
    PointerMapping::Point point = PointerMapping::clientToGamePointer(0, 0, 1920, 1200, 3840, 2400, 100);
    BOOST_CHECK_EQUAL(point.mX, 0);
    BOOST_CHECK_EQUAL(point.mY, 0);
    point = PointerMapping::clientToGamePointer(1919, 1199, 1920, 1200, 3840, 2400, 100);
    BOOST_CHECK_EQUAL(point.mX, 3839);
    BOOST_CHECK_EQUAL(point.mY, 2399);
    // Shrinking
    point = PointerMapping::clientToGamePointer(3839, 2399, 3840, 2400, 1920, 1200, 100);
    BOOST_CHECK_EQUAL(point.mX, 1919);
    BOOST_CHECK_EQUAL(point.mY, 1199);
    // Inverse direction as used for moving the Windows pointer
    BOOST_CHECK_EQUAL(PointerMapping::scaleCoordinate(1919, 1920, 3840), 3839);
    BOOST_CHECK_EQUAL(PointerMapping::scaleCoordinate(3839, 3840, 1920), 1919);
    BOOST_CHECK_EQUAL(PointerMapping::scaleCoordinate(0, 3840, 1920), 0);
    BOOST_CHECK_EQUAL(PointerMapping::scaleCoordinate(7, 100, 100), 7);
    BOOST_CHECK_EQUAL(PointerMapping::scaleCoordinate(0, 1, 100), 0);
}
