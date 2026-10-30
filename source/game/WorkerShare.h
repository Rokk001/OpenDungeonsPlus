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

#ifndef WORKERSHARE_H
#define WORKERSHARE_H

#include <cstdint>


//! \brief The counting rules for how a seat's workers are spread over their jobs, without any
//! game state so that they can be checked on their own (see source/tests/check_worker_share.py).
namespace WorkerShare
{
    //! \brief Carrying is tried first as long as the carrying share of the counted workers is at most this
    //! \brief Claiming walls is tried first when the digging and ground claiming share is above this
    //! \brief Divisor that turns a share given in percent into a fraction
    static const double PERCENT_DIVISOR = 100.0;

    //! \brief The workers that count for the shares: those doing one of the listed jobs
    //! (digging, claiming ground, claiming walls, carrying, reloading traps) plus the one
    //! that is choosing a job.
    inline uint32_t totalWorkers(uint32_t nbDigging, uint32_t nbClaimingGround, uint32_t nbClaimingWall,
        uint32_t nbCarrying, uint32_t nbReloading)
    {
        return nbDigging + nbClaimingGround + nbClaimingWall + nbCarrying + nbReloading + 1;
    }

    //! \brief Tries carrying first up to the configured carrying share.
    inline bool isCarryFirst(uint32_t nbCarrying, uint32_t nbTotal, double maxShare)
    {
        double percent = static_cast<double>(nbCarrying) / static_cast<double>(nbTotal);
        return percent <= maxShare;
    }

    //! \brief Tries wall claiming above the configured digging and ground-claiming share.
    inline bool isClaimWallFirst(uint32_t nbDigging, uint32_t nbClaimingGround, uint32_t nbTotal, double minShare)
    {
        double percent = static_cast<double>(nbDigging + nbClaimingGround) / static_cast<double>(nbTotal);
        return percent > minShare;
    }

    //! \brief Whether one more worker may reload a trap: the first one always may, then the
    //! workers reloading may be at most the share (percent) of the counted workers.
    inline bool isReloadShareOpen(uint32_t nbReloading, uint32_t nbTotal, double sharePercent)
    {
        if(nbReloading == 0)
            return true;

        double percent = static_cast<double>(nbReloading) / static_cast<double>(nbTotal);
        return percent <= sharePercent / PERCENT_DIVISOR;
    }

    //! \brief Whether one more worker may clean: same counting as the trap reloading share, the first one
    //! always may, then the workers cleaning may be at most the share (percent) of the counted workers.
    inline bool isCleanShareOpen(uint32_t nbCleaning, uint32_t nbTotal, double sharePercent)
    {
        if(nbCleaning == 0)
            return true;

        double percent = static_cast<double>(nbCleaning) / static_cast<double>(nbTotal);
        return percent <= sharePercent / PERCENT_DIVISOR;
    }
}

#endif // WORKERSHARE_H
