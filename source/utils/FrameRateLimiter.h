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

#ifndef FRAMERATELIMITER_H
#define FRAMERATELIMITER_H

#include <SFML/System/Clock.hpp>
#include <SFML/System/Time.hpp>

#include <cstdint>

//! \brief Wrapper class to limit framerates
class FrameRateLimiter
{
public:
    FrameRateLimiter(std::int64_t frameRate);
    ~FrameRateLimiter();
    FrameRateLimiter(const FrameRateLimiter&) = delete;
    FrameRateLimiter& operator=(const FrameRateLimiter&) = delete;
    //! \brief Sleep until the frame's minimum time and report requested versus actual sleep once per minute.
    void sleepIfEarly();
    unsigned int getFrameRate();
    void setFrameRate(unsigned int frameRate);
private:
    //! \brief Waits the requested microseconds, on Windows with a high-resolution waitable timer.
    void waitFor(std::int64_t microseconds);
    std::int64_t mMinFrameTime;
    //! Windows high-resolution waitable timer (a HANDLE), or null where it is unavailable.
    void* mWaitTimer;
    sf::Clock mClock;
    //! Aggregated sleep observations; the global timer resolution is not changed.
    std::int64_t mReportElapsed;
    std::int64_t mSleepCount;
    std::int64_t mRequestedSleep;
    std::int64_t mActualSleep;
    std::int64_t mMaxOversleep;
};

#endif // FPSLIMITER_H
