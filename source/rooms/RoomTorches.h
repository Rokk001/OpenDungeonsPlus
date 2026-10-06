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

#ifndef ROOMTORCHES_H
#define ROOMTORCHES_H

#include "rooms/RoomType.h"

#include <cstdint>

//! \brief The rules that decide which room tiles carry a wall torch. The game (Room::hasTorchOn, used by the care
//! bonus of the hatchery) and the room ambience that draws the torches both ask here, so a torch that is drawn is
//! a torch that lights, and the other way round.
class RoomTorches
{
public:
    //! One tile in TORCH_SPACING carries a torch (if the rest of the rule is met).
    static const uint32_t TORCH_SPACING = 6;

    //! The rooms that carry wall torches.
    static bool hasTorchRoomType(RoomType type);

    //! True if the torch spot of the coordinates is taken (a fixed pick over the coordinates, no dice).
    static bool isTorchSpot(int32_t x, int32_t y);
};

#endif // ROOMTORCHES_H
