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

#ifndef CREATUREMOODNOLAIR_H
#define CREATUREMOODNOLAIR_H

#include "creaturemood/CreatureMood.h"

//! \brief Lasting problem: the creature has no lair (bed) to sleep in.
class CreatureMoodNoLair : public CreatureMood
{
public:
    //! \brief Creates the modifier with all values set to zero (they are read from the configuration).
    CreatureMoodNoLair() :
        CreatureMood(CreatureMoodKind::Lasting, CreatureMoodColumns::JumpFallReward)
    {}

    //! \brief Destroys the modifier.
    virtual ~CreatureMoodNoLair()
    {}

    //! \brief Returns the name under which this modifier is listed in the creature configuration.
    const std::string& getModifierName() const override;

    //! \brief Returns 1 while the creature has no home tile, otherwise 0.
    //! \param creature The creature to look at.
    virtual double getAmount(const Creature& creature) const override;

    //! \brief Returns a copy of this modifier.
    CreatureMoodNoLair* clone() const override;
};

#endif // CREATUREMOODNOLAIR_H
