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

#ifndef CREATUREACTIONVOMIT_H
#define CREATUREACTIONVOMIT_H

#include "creatureaction/CreatureAction.h"

#include <cstdint>

//! \brief A drunk creature vomits where it stands: it plays the Vomit clip for DrinkTurns turns and a dirt pile of
//! the kind vomit stays on its tile until a worker cleans it. The creature decides this once per drunk episode
//! (see Creature::handleIdleAction), the action itself only plays it.
class CreatureActionVomit : public CreatureAction
{
public:
    //! \brief Creates the action for the given creature.
    CreatureActionVomit(Creature& creature) :
        CreatureAction(creature),
        mTurnsLeft(-1)
    {}

    virtual ~CreatureActionVomit()
    {}

    CreatureActionType getType() const override
    { return CreatureActionType::vomit; }

    //! \brief Gets the function that runs this action.
    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction

private:
    //! \brief One turn of the action: starts the clip, counts the turns and leaves the vomit on the tile at the end.
    //! \return True when the action ended and the creature may go on in the same turn.
    bool handleVomit();

    //! \brief Turns of vomiting that are left; -1 until the clip was started.
    int32_t mTurnsLeft;
};

#endif // CREATUREACTIONVOMIT_H
