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

#ifndef CREATUREMOODDIRT_H
#define CREATUREMOODDIRT_H

#include "creaturemood/CreatureMood.h"

//! \brief Mood change from dirt: the dirt stage of the room the creature stands in plus the dirt piles around it, both
//! scaled by the Cleanliness of the creature type. Needs no line in the creature configuration, all values come from
//! the [Dirt] block of the global configuration.
class CreatureMoodDirt : public CreatureMood
{
public:
    //! \brief Creates the modifier.
    CreatureMoodDirt() :
        CreatureMood(CreatureMoodKind::ComeAndGo, CreatureMoodColumns::Fall)
    {}

    //! \brief Destroys the modifier.
    virtual ~CreatureMoodDirt()
    {}

    //! \brief Returns the name under which this modifier is registered.
    const std::string& getModifierName() const override;

    //! \brief Returns 0: the dirt has no count of causes, its fall comes from getFallPerTurn.
    //! \param creature The creature to look at.
    virtual double getAmount(const Creature& creature) const override;

    //! \brief Returns the fall per turn (negative) from the dirt stage of the room the creature stands in plus the
    //! dirt piles around it, both times the Cleanliness of the creature type. Creatures that belong to no seat and
    //! free heroes feel no dirt.
    //! \param creature The creature to look at.
    virtual double getFallPerTurn(const Creature& creature) const override;

    //! \brief Returns the mood a creature gets once when a room it uses is cleaned from the given dirt stage back to
    //! stage 1, times the Cleanliness of the creature type. 0 for a stage below 2 and for a creature that feels no dirt.
    //! \param creature The creature that uses the room.
    //! \param stage The highest dirt stage (2 or 3) the room had since it was last clean.
    static double getCleanedReward(const Creature& creature, uint32_t stage);

    //! \brief Returns a copy of this modifier.
    CreatureMoodDirt* clone() const override;
};

#endif // CREATUREMOODDIRT_H
