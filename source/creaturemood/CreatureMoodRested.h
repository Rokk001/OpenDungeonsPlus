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

#ifndef CREATUREMOODRESTED_H
#define CREATUREMOODRESTED_H

#include "creaturemood/CreatureMood.h"

//! \brief One-time event: the creature wakes up rested after sleeping in its lair.
class CreatureMoodRested : public CreatureMood
{
public:
    //! \brief Creates the modifier with all values set to zero (they are read from the configuration).
    CreatureMoodRested() :
        CreatureMood(CreatureMoodKind::Event, CreatureMoodColumns::Event)
    {}

    //! \brief Destroys the modifier.
    virtual ~CreatureMoodRested()
    {}

    //! \brief Returns the name under which this modifier is listed in the creature configuration.
    const std::string& getModifierName() const override;

    //! \brief Returns 0, waking rested is an event and not a problem that holds.
    //! \param creature The creature to look at.
    virtual double getAmount(const Creature& creature) const override;

    //! \brief Returns a copy of this modifier.
    CreatureMoodRested* clone() const override;
};

#endif // CREATUREMOODRESTED_H
