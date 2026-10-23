/*!
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

#include "FrameRateLimiter.h"

#include <boost/thread/thread_only.hpp>

namespace
{
    const std::int64_t divisor = boost::micro::den;
    const std::int64_t minDifference = divisor / 1000;

    template<typename T>
    T fromFrameRate(T frameRate)
    {
        return divisor / frameRate;
    }

    //Since we are just inverting to get the framerate,
    //we can use the same fuction to invert back.
#define toFrameRate fromFrameRate
}

//! \brief Creates a limiter for the given frame rate (64-bit integer type).
FrameRateLimiter::FrameRateLimiter(std::int64_t frameRate)
  : mMinFrameTime(fromFrameRate(frameRate))
{
    setFrameRate(frameRate);
}


//! \brief Sleeps for the rest of the frame time if the last frame was shorter than the minimum.
void FrameRateLimiter::sleepIfEarly()
{
    std::int64_t timeSinceLast = mClock.getElapsedTime().asMicroseconds();
    if(mMinFrameTime - timeSinceLast > minDifference)
    {
        boost::this_thread::sleep_for(boost::chrono::microseconds(mMinFrameTime - timeSinceLast));
    }
    mClock.restart();
}

unsigned int FrameRateLimiter::getFrameRate()
{
    return toFrameRate(mMinFrameTime);
}

void FrameRateLimiter::setFrameRate(unsigned int frameRate)
{
    mMinFrameTime = fromFrameRate(frameRate);
}
