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

#ifndef CREATUREACTIONGUARDPOST_H
#define CREATUREACTIONGUARDPOST_H

#include "creatureaction/CreatureAction.h"

class Tile;

//! \brief The creature mans a guard post: it stands on the post tile until it has to eat, sleep
//! or get its fee, or until the post is gone. Enemies in sight are fought by the usual behaviour,
//! then the creature returns to the post.
class CreatureActionGuardPost : public CreatureAction
{
public:
    CreatureActionGuardPost(Creature& creature, Tile& postTile) :
        CreatureAction(creature),
        mPostTile(&postTile)
    {}

    virtual ~CreatureActionGuardPost()
    {}

    CreatureActionType getType() const override
    { return CreatureActionType::guardPost; }

    std::function<bool()> action() override;

    inline Tile* getPostTile() const
    { return mPostTile; }

    static bool handleGuardPost(Creature& creature, Tile* postTile);

    //! \brief Tells whether another creature of the same seat already mans (or walks to) the given post tile
    static bool isPostTaken(const Creature& creature, Tile* postTile);

    //! \brief Looks for a free reachable guard post of the creature seat and pushes the action to man it.
    //! Returns true if the action has been pushed.
    static bool tryManPost(Creature& creature);

private:
    Tile* mPostTile;
};

#endif // CREATUREACTIONGUARDPOST_H
