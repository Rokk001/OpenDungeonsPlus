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

#ifndef POINTERMAPPING_H
#define POINTERMAPPING_H

#include <algorithm>

//! \brief Pure conversion from the Windows pointer position (client coordinates of the game window)
//! to the game pointer position. It has no dependencies so that it can be tested without Windows.
namespace PointerMapping
{
    struct Point
    {
        int mX;
        int mY;
    };

    //! \brief Clamps a value to [0, size - 1]; a size below 1 gives 0.
    inline int clampToSize(int value, int size)
    {
        if(size < 1)
            return 0;
        return (std::max)(0, (std::min)(value, size - 1));
    }

    //! \brief Converts the pointer position in client coordinates to the game pointer position.
    //! The game pointer is in render window pixels and equals the client position (1:1). Only if the
    //! client area and the render window differ in size (display scaling of the system) the position
    //! is scaled proportionally. Positions outside the window give the nearest edge position.
    //! The UI scale percent changes the size of the interface, not the pointer pixels, so it does
    //! not change the result; it is part of the signature to document and test that.
    inline Point clientToGamePointer(int clientX, int clientY, int clientWidth, int clientHeight,
        int gameWidth, int gameHeight, int uiScalePercent)
    {
        (void)uiScalePercent;
        Point result;
        const int x = clampToSize(clientX, clientWidth);
        const int y = clampToSize(clientY, clientHeight);
        if(clientWidth == gameWidth || clientWidth < 1)
            result.mX = x;
        else
            result.mX = static_cast<int>(static_cast<long long>(x) * gameWidth / clientWidth);
        if(clientHeight == gameHeight || clientHeight < 1)
            result.mY = y;
        else
            result.mY = static_cast<int>(static_cast<long long>(y) * gameHeight / clientHeight);
        result.mX = clampToSize(result.mX, gameWidth);
        result.mY = clampToSize(result.mY, gameHeight);
        return result;
    }
}

#endif // POINTERMAPPING_H
