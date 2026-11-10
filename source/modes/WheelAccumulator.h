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

#ifndef WHEELACCUMULATOR_H
#define WHEELACCUMULATOR_H

//! \brief Collects mouse wheel movement (in OIS units, 120 per notch) reported by the window
//! between two input captures, so that it can be handed to the modes as one wheel event.
//! The wheel is taken from the window messages because the non exclusive DirectInput mouse does not
//! report it reliably (remote desktop). It has no dependencies so that it can be tested without Windows.
class WheelAccumulator
{
public:
    WheelAccumulator(): mPending(0) {}

    //! \brief Adds wheel movement; ignored while the window is not in the foreground.
    void add(int delta, bool foreground)
    {
        if(foreground)
            mPending += delta;
    }

    //! \brief Returns the movement collected since the last call and clears it.
    int take()
    {
        const int result = mPending;
        mPending = 0;
        return result;
    }

    void clear() { mPending = 0; }
    bool hasPending() const { return mPending != 0; }

private:
    int mPending;
};

#endif // WHEELACCUMULATOR_H
