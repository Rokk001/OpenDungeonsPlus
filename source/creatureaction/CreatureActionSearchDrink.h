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

#ifndef CREATUREACTIONSEARCHDRINK_H
#define CREATUREACTIONSEARCHDRINK_H

#include "creatureaction/CreatureAction.h"

//! \brief A thirsty creature (thirst at ThirstSeek or more) looks for a tavern of its own seat with a free place to
//! drink and lets that room handle it (CreatureActionUseRoom). Without a tavern, or when all of them are full, the
//! action ends at once and the thirst keeps rising (the mood malus of the thirst acts).
class CreatureActionSearchDrink : public CreatureAction
{
public:
    //! \brief Creates the search for the given creature.
    //! \param creature The thirsty creature.
    //! \param forced True if the creature has to go whatever its thirst is.
    CreatureActionSearchDrink(Creature& creature, bool forced) :
        CreatureAction(creature),
        mForced(forced)
    {}

    virtual ~CreatureActionSearchDrink()
    {}

    CreatureActionType getType() const override
    { return CreatureActionType::searchDrink; }

    //! \brief Gets the function that runs this action.
    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction

    //! \brief One turn of the search: ends when the creature is not thirsty or no tavern can be reached, otherwise
    //! replaces itself with the use of the nearest tavern that has a free place.
    //! \param creature The creature that looks for a drink.
    //! \param forced True if the thirst is not checked.
    //! \return True when the action ended (or started the use) and the creature may go on in the same turn.
    static bool handleSearchDrink(Creature& creature, bool forced);

private:
    //! \brief True if the creature goes to a tavern whatever its thirst is.
    bool mForced;
};

#endif // CREATUREACTIONSEARCHDRINK_H
