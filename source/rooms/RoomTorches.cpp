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

#include "rooms/RoomTorches.h"

bool RoomTorches::hasTorchRoomType(RoomType type)
{
    switch(type)
    {
        case RoomType::dormitory:
        case RoomType::library:
        case RoomType::workshop:
        case RoomType::trainingHall:
        case RoomType::treasury:
        case RoomType::hatchery:
        case RoomType::prison:
        case RoomType::torture:
        case RoomType::crypt:
        case RoomType::arena:
        case RoomType::casino:
        case RoomType::guardRoom:
        case RoomType::temple:
            return true;
        default:
            return false;
    }
}

bool RoomTorches::isTorchSpot(int32_t x, int32_t y)
{
    uint32_t hash = (static_cast<uint32_t>(x) * 73856093u) ^ (static_cast<uint32_t>(y) * 19349663u);
    return ((hash >> 3) % TORCH_SPACING) == 0;
}
