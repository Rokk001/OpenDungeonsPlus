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

#ifndef CREATUREACTIONRAMPAGE_H
#define CREATUREACTIONRAMPAGE_H

#include "creatureaction/CreatureAction.h"
#include "entities/CreatureMoodValues.h"

class Tile;

//! \brief The rampage of a creature that was left at the bottom of its mood for too long: it walks to a room tile of its
//! keeper and stays on it. The hits and the dirt piles are counted by the creature (Creature::upkeepRampage).
class CreatureActionRampage : public CreatureAction
{
public:
    CreatureActionRampage(Creature& creature) :
        CreatureAction(creature)
    {}

    virtual ~CreatureActionRampage()
    {}

    CreatureActionType getType() const override
    { return CreatureActionType::rampage; }

    uint32_t updateMoodModifier() const override
    { return CreatureMoodValues::Furious; }

    std::function<bool()> action() override;

    //! \brief Walks to the room tile the creature hits, or chooses a new one; ends when there is nothing to destroy.
    static bool handleRampage(Creature& creature);

    //! \brief True if the tile is a room tile a rampaging creature may hit: a tile of a room of its keeper that can still be
    //! attacked, but not of the dungeon heart (it has its own health logic) and not of a portal.
    //! \param creature The rampaging creature.
    //! \param tile The tile to test.
    static bool isTargetTile(const Creature& creature, const Tile& tile);

    //! \brief Chooses a random room tile of the keeper's rooms that the creature may hit and can reach, nullptr if there is
    //! none.
    //! \param creature The rampaging creature.
    static Tile* findTarget(Creature& creature);

    //! \brief Hits the room tile with RampageTileDamage of absolute damage (no attack or defense roll).
    //! \param creature The rampaging creature.
    //! \param tile The room tile it stands on.
    //! \return True if the tile can be hit again (it is not destroyed).
    static bool hitTile(Creature& creature, Tile& tile);
};

#endif // CREATUREACTIONRAMPAGE_H
