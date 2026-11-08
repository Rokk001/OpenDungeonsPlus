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
#include "utils/LogManager.h"

#include <boost/thread/thread_only.hpp>
#include <algorithm>
#include <sstream>

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
  : mMinFrameTime(fromFrameRate(frameRate)), mReportElapsed(0), mSleepCount(0),
    mRequestedSleep(0), mActualSleep(0), mMaxOversleep(0)
{
    setFrameRate(frameRate);
}


//! \brief Keeps the existing sleep policy and records effective wake delay with the monotonic frame clock.
void FrameRateLimiter::sleepIfEarly()
{
    std::int64_t timeSinceLast = mClock.getElapsedTime().asMicroseconds();
    if(mMinFrameTime - timeSinceLast > minDifference)
    {
        const std::int64_t requested = mMinFrameTime - timeSinceLast;
        boost::this_thread::sleep_for(boost::chrono::microseconds(requested));
        const std::int64_t actual = mClock.getElapsedTime().asMicroseconds() - timeSinceLast;
        ++mSleepCount;
        mRequestedSleep += requested;
        mActualSleep += actual;
        mMaxOversleep = std::max(mMaxOversleep, actual - requested);
    }
    mReportElapsed += mClock.restart().asMicroseconds();
    if(mReportElapsed >= 60 * divisor)
    {
        std::ostringstream report;
        report << "Frame limiter sleep samples=" << mSleepCount
            << " intervalMs=" << mReportElapsed / 1000.0
            << " requestedMeanMs=" << (mSleepCount == 0 ? 0.0 : mRequestedSleep / (1000.0 * mSleepCount))
            << " actualMeanMs=" << (mSleepCount == 0 ? 0.0 : mActualSleep / (1000.0 * mSleepCount))
            << " maxOversleepMs=" << mMaxOversleep / 1000.0;
        OD_LOG_INF(report.str());
        mReportElapsed = 0;
        mSleepCount = 0;
        mRequestedSleep = 0;
        mActualSleep = 0;
        mMaxOversleep = 0;
    }
}

unsigned int FrameRateLimiter::getFrameRate()
{
    return toFrameRate(mMinFrameTime);
}

void FrameRateLimiter::setFrameRate(unsigned int frameRate)
{
    mMinFrameTime = fromFrameRate(frameRate);
}
