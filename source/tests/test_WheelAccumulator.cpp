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

#include "modes/WheelAccumulator.h"

#define BOOST_TEST_MODULE WheelAccumulator
#include "BoostTestTargetConfig.h"

BOOST_AUTO_TEST_CASE(test_wheel_is_collected_and_taken_once)
{
    WheelAccumulator wheel;
    BOOST_CHECK(!wheel.hasPending());
    wheel.add(120, true);
    wheel.add(120, true);
    wheel.add(-120, true);
    BOOST_CHECK(wheel.hasPending());
    BOOST_CHECK_EQUAL(wheel.take(), 120);
    BOOST_CHECK(!wheel.hasPending());
    BOOST_CHECK_EQUAL(wheel.take(), 0);
}

BOOST_AUTO_TEST_CASE(test_wheel_in_background_is_dropped)
{
    WheelAccumulator wheel;
    wheel.add(240, false);
    BOOST_CHECK_EQUAL(wheel.take(), 0);
    wheel.add(-120, true);
    wheel.clear();
    BOOST_CHECK_EQUAL(wheel.take(), 0);
}
