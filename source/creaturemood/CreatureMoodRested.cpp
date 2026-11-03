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

#include "creaturemood/CreatureMoodRested.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"

#include <algorithm>

static const std::string CreatureMoodRestedName = "Rested";

namespace
{
//! \brief Factory that creates CreatureMoodRested objects from the creature configuration.
class CreatureMoodRestedFactory : public CreatureMoodFactory
{
    //! \brief Creates a new CreatureMoodRested with default values.
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodRested; }

    //! \brief Returns the configuration name of this modifier.
    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodRestedName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodRestedFactory);
}

//! \brief Returns the name under which this modifier is listed in the creature configuration.
const std::string& CreatureMoodRested::getModifierName() const
{
    return CreatureMoodRestedName;
}

//! \brief Returns 0, waking rested is an event and not a problem that holds.
double CreatureMoodRested::getAmount(const Creature& creature) const
{
    return 0.0;
}

//! \brief Returns a copy of this modifier.
CreatureMoodRested* CreatureMoodRested::clone() const
{
    return new CreatureMoodRested(*this);
}
