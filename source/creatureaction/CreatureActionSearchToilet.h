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

#ifndef CREATUREACTIONSEARCHTOILET_H
#define CREATUREACTIONSEARCHTOILET_H

#include "creatureaction/CreatureAction.h"

//! \brief A creature whose urge reached UrgeSeek looks for a free toilet seat. It walks to the nearest free
//! seat and uses it; when all seats are busy it waits near the toilet room until one frees up (or until the
//! urge reaches UrgeRelieve and the creature relieves itself). Without any toilet room the action ends at once.
class CreatureActionSearchToilet : public CreatureAction
{
public:
    //! \brief Creates the search for the given creature.
    CreatureActionSearchToilet(Creature& creature) :
        CreatureAction(creature)
    {}

    virtual ~CreatureActionSearchToilet()
    {}

    CreatureActionType getType() const override
    { return CreatureActionType::searchToilet; }

    //! \brief Gets the function that runs this action.
    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction

    //! \brief One turn of the search: ends when the urge is gone or no toilet room exists, starts the use of a
    //! free seat, or waits near the toilet room.
    //! \return True when the action ended (or started the use) and the creature may go on in the same turn.
    static bool handleSearchToilet(Creature& creature);
};

#endif // CREATUREACTIONSEARCHTOILET_H
