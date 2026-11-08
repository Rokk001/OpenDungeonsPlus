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
    //! \brief Sleep as before and report requested versus actual sleep once per minute.
    void sleepIfEarly();
    unsigned int getFrameRate();
    void setFrameRate(unsigned int frameRate);
private:
    std::int64_t mMinFrameTime;
    sf::Clock mClock;
    //! Aggregated sleep observations; no timer-resolution or scheduling policy changes.
    std::int64_t mReportElapsed;
    std::int64_t mSleepCount;
    std::int64_t mRequestedSleep;
    std::int64_t mActualSleep;
    std::int64_t mMaxOversleep;
};

#endif // FPSLIMITER_H
