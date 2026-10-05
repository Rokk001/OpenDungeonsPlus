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

#ifndef ROOMCLAIM_H
#define ROOMCLAIM_H

#include <cstdint>

//! \brief The rules for taking over a room, without any game state so that they
//! can be checked on their own (see source/tests/check_room_capture.py).
namespace RoomClaim
{
    //! \brief Whether a worker of another seat may take the room over. The
    //! dungeon heart is the one room with an exception: it can only be destroyed.
    inline bool isClaimableBy(bool claimingEnabled, bool isAllied, bool isDungeonHeart)
    {
        if(!claimingEnabled)
            return false;

        if(isAllied)
            return false;

        if(isDungeonHeart)
            return false;

        return true;
    }

    //! \brief Whether a defender standing dx and dy tiles away from the tile that is
    //! danced on is close enough to keep it safe. A radius of 0 or less switches the
    //! guard rule off.
    inline bool isGuardClose(int32_t dx, int32_t dy, double radius)
    {
        if(radius <= 0.0)
            return false;

        return (static_cast<double>(dx) * static_cast<double>(dx) + static_cast<double>(dy) * static_cast<double>(dy))
            <= (radius * radius);
    }

    //! \brief The gold the taker pays when a room changes hands: a share (percent) of
    //! what the tiles taken cost to build. 0 when the share is 0 or there is nothing to pay for.
    inline int32_t takeoverPrice(int32_t costPerTile, uint32_t numTiles, double percent)
    {
        if((costPerTile <= 0) || (numTiles == 0) || (percent <= 0.0))
            return 0;

        return static_cast<int32_t>(static_cast<double>(costPerTile) * static_cast<double>(numTiles) * percent / 100.0);
    }

    //! \brief The part of the health of a whole room (1.0 = full) one dance takes
    //! away. A worker whose claim rate equals referenceClaimRate working alone
    //! empties a room in secondsPerTile seconds for every tile of it.
    inline double healthLostPerDance(double danceRate, double referenceClaimRate, double secondsPerTile,
        double turnsPerSecond, uint32_t numTiles)
    {
        if((referenceClaimRate <= 0.0) || (secondsPerTile <= 0.0) || (turnsPerSecond <= 0.0) || (numTiles == 0))
            return 1.0;

        return (danceRate / referenceClaimRate) / (secondsPerTile * turnsPerSecond * static_cast<double>(numTiles));
    }

    //! \brief The part of the health of a whole room (1.0 = full) one dance of an own
    //! worker gives back. It is repairFactor times what the same dance takes away from
    //! an enemy room, so a single worker out-repairs several enemy workers.
    inline double healthRepairedPerDance(double danceRate, double referenceClaimRate, double secondsPerTile,
        double turnsPerSecond, uint32_t numTiles, double repairFactor)
    {
        if((referenceClaimRate <= 0.0) || (secondsPerTile <= 0.0) || (turnsPerSecond <= 0.0) || (numTiles == 0))
            return 1.0;

        return repairFactor * (danceRate / referenceClaimRate) / (secondsPerTile * turnsPerSecond * static_cast<double>(numTiles));
    }
}

#endif // ROOMCLAIM_H
