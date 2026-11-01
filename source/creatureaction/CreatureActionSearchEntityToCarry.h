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

#ifndef CREATUREACTIONSEARCHENTITYTOCARRY_H
#define CREATUREACTIONSEARCHENTITYTOCARRY_H

#include "creatureaction/CreatureAction.h"

//! \brief Finds eligible cargo and prioritizes available infirmary admissions.
class CreatureActionSearchEntityToCarry : public CreatureAction
{
public:
    //! \brief Creates a search that returns to job selection after one target.
    CreatureActionSearchEntityToCarry(Creature& creature, bool forced);
    virtual ~CreatureActionSearchEntityToCarry();

    CreatureActionType getType() const override
    { return CreatureActionType::searchEntityToCarry; }

    //! \brief Advances the search while retaining its one-target state.
    std::function<bool()> action() override;

    //! \brief Returns whether this search was forced by a hand drop.
    bool isForced() const { return mForced; }
    //! \brief Selects reachable cargo and its existing building or configured mission destination.
    //! \brief Searches cargo with infirmaries considered before beds.
    //! \param targetStarted Whether a target has already been handed to a grab action.
    static bool handleSearchEntityToCarry(Creature& creature, bool forced, bool& targetStarted);

private:
    bool mForced;
    bool mTargetStarted;
};

#endif // CREATUREACTIONSEARCHENTITYTOCARRY_H
