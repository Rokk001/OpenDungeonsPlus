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

#ifndef CREATUREACTIONSEARCHSPA_H
#define CREATUREACTIONSEARCHSPA_H

#include "creatureaction/CreatureAction.h"

//! \brief A creature in a bad mood or with a hangover looks for a lava spa of its own seat that can take it now (a free
//! bath place of its size and a payer who can pay) and lets that room handle it (CreatureActionUseRoom). The place is
//! reserved when the use of the room starts. Without such a spa the action ends at once and the creature goes on with
//! its next steps; it tries again at its next search.
class CreatureActionSearchSpa : public CreatureAction
{
public:
    //! \brief Creates the search for the given creature.
    //! \param creature The creature that wants a bath.
    CreatureActionSearchSpa(Creature& creature) :
        CreatureAction(creature)
    {}

    virtual ~CreatureActionSearchSpa()
    {}

    CreatureActionType getType() const override
    { return CreatureActionType::searchSpa; }

    //! \brief Gets the function that runs this action.
    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction

    //! \brief One turn of the search: ends when the creature does not want a bath any more or no spa can take it,
    //! otherwise replaces itself with the use of the nearest spa that can take it.
    //! \param creature The creature that looks for a bath.
    //! \return True when the action ended (or started the use) and the creature may go on in the same turn.
    static bool handleSearchSpa(Creature& creature);
};

#endif // CREATUREACTIONSEARCHSPA_H
