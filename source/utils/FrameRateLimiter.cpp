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

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#ifndef CREATE_WAITABLE_TIMER_HIGH_RESOLUTION
#define CREATE_WAITABLE_TIMER_HIGH_RESOLUTION 0x00000002
#endif
#endif

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
  : mMinFrameTime(fromFrameRate(frameRate)), mWaitTimer(nullptr), mReportElapsed(0), mSleepCount(0),
    mRequestedSleep(0), mActualSleep(0), mMaxOversleep(0)
{
    setFrameRate(frameRate);
#ifdef _WIN32
    // Tilda F1 (build 52): the plain sleep woke on average 7.3 ms (menu) and 7.7 ms (P1 game) late
    // with the default Windows timer, up to 24 ms: 28% of the menu time and 11.6% of the first P1 game minute.
    // A high-resolution waitable timer wakes at the requested time without raising the global timer
    // resolution. Where Windows does not offer it (before Windows 10 1803), the old sleep remains.
    mWaitTimer = CreateWaitableTimerExW(nullptr, nullptr, CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, TIMER_ALL_ACCESS);
#endif
}

FrameRateLimiter::~FrameRateLimiter()
{
#ifdef _WIN32
    if(mWaitTimer != nullptr)
        CloseHandle(mWaitTimer);
#endif
}

//! \brief Waits once for the requested time; the boost sleep is the fallback without a usable timer.
void FrameRateLimiter::waitFor(std::int64_t microseconds)
{
#ifdef _WIN32
    if(mWaitTimer != nullptr)
    {
        LARGE_INTEGER due;
        // Negative: relative to now, in 100 ns units.
        due.QuadPart = -microseconds * 10;
        if(SetWaitableTimer(mWaitTimer, &due, 0, nullptr, nullptr, FALSE))
        {
            WaitForSingleObject(mWaitTimer, INFINITE);
            return;
        }
    }
#endif
    boost::this_thread::sleep_for(boost::chrono::microseconds(microseconds));
}

//! \brief Keeps the existing sleep decision and records effective wake delay with the monotonic frame clock.
void FrameRateLimiter::sleepIfEarly()
{
    std::int64_t timeSinceLast = mClock.getElapsedTime().asMicroseconds();
    if(mMinFrameTime - timeSinceLast > minDifference)
    {
        const std::int64_t requested = mMinFrameTime - timeSinceLast;
        waitFor(requested);
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
