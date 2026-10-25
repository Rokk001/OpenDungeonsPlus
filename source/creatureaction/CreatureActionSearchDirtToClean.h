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

#ifndef CREATUREACTIONSEARCHDIRTTOCLEAN_H
#define CREATUREACTIONSEARCHDIRTTOCLEAN_H

#include "creatureaction/CreatureAction.h"

//! \brief (worker only) Looks for something to clean and starts cleaning it: the nearest pile first, then the
//! dirtiest tile of a room that needs cleaning (ordered rooms first, then the toilet, then the others), then a
//! dirty corridor tile. Ends without success when there is nothing to clean.
class CreatureActionSearchDirtToClean : public CreatureAction
{
public:
    //! \brief Creates the search and reports the worker to its player for the cleaning share.
    CreatureActionSearchDirtToClean(Creature& creature);
    virtual ~CreatureActionSearchDirtToClean();

    CreatureActionType getType() const override
    { return CreatureActionType::searchDirtToClean; }

    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction

    //! \brief Chooses the tile to clean and pushes the cleaning of it; pops the search if there is nothing to clean
    //! or if the worker has searched for too long and should look for another job.
    //! \param nbTurns The turns this search has been running.
    //! \return True if the action ended or changed (the next action runs in the same turn).
    static bool handleSearchDirtToClean(Creature& creature, int32_t nbTurns);
};

#endif // CREATUREACTIONSEARCHDIRTTOCLEAN_H
