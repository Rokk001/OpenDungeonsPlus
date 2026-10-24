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

#ifndef MENUFLIGHT_H
#define MENUFLIGHT_H

#include <algorithm>
#include <cmath>

//! \brief Timing limits for the configured three-dimensional menu camera paths.
namespace MenuFlightSettings
{
    //! Default seconds until a menu destination is reached; authored routes supply their duration.
    const float DURATION = 2.0f;
    //! Longest time step taken into account, so that a slow frame cannot skip the flight
    const float MAX_STEP = 0.25f;
}

//! \brief Advances one configured camera path and rejects overlapping flight requests.
class MenuFlight
{
public:
    //! \brief Returns clamped progress for a positive duration, or completion for an invalid duration.
    static float progressAt(float time, float duration = MenuFlightSettings::DURATION)
    {
        if(time <= 0.0f)
            return 0.0f;
        if(duration <= 0.0f || time >= duration)
            return 1.0f;
        return time / duration;
    }

    //! \brief Returns smooth ease-in/out progress with zero speed at both endpoints.
    static float easedProgressAt(float time, float duration = MenuFlightSettings::DURATION)
    {
        const float progress = progressAt(time, duration);
        return progress * progress * (3.0f - 2.0f * progress);
    }

    //! \brief Starts a positive finite duration; returns false while another flight is running.
    bool start(float duration = MenuFlightSettings::DURATION)
    {
        if(mActive || !std::isfinite(duration) || duration <= 0.0f)
            return false;
        mActive = true;
        mElapsed = 0.0f;
        mDuration = duration;
        return true;
    }

    //! \brief Advances by at most MAX_STEP and returns true on the step reaching the endpoint.
    bool advance(float elapsed)
    {
        if(!mActive)
            return false;
        if(elapsed > MenuFlightSettings::MAX_STEP)
            elapsed = MenuFlightSettings::MAX_STEP;
        if(elapsed > 0.0f)
            mElapsed += elapsed;
        if(mElapsed < mDuration)
            return false;
        mElapsed = mDuration;
        mActive = false;
        return true;
    }

    //! \brief Stops the flight when its scene is freed.
    void reset()
    {
        mActive = false;
        mElapsed = 0.0f;
    }

    //! \brief Returns whether a camera path is still advancing.
    bool isActive() const
    { return mActive; }

    //! \brief Returns eased progress along the currently started path, including its final endpoint.
    float getProgress() const
    { return easedProgressAt(mElapsed, mDuration); }

private:
    //! Whether a path has an unfinished timer.
    bool mActive = false;
    //! Seconds consumed by the current path.
    float mElapsed = 0.0f;
    //! Duration supplied by the scene configuration.
    float mDuration = MenuFlightSettings::DURATION;
};

#endif // MENUFLIGHT_H
