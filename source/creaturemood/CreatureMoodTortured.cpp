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

#include "creaturemood/CreatureMoodTortured.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"

#include <algorithm>

static const std::string CreatureMoodTorturedName = "Tortured";

namespace
{
//! \brief Factory that creates CreatureMoodTortured objects from the creature configuration.
class CreatureMoodTorturedFactory : public CreatureMoodFactory
{
    //! \brief Creates a new CreatureMoodTortured with default values.
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodTortured; }

    //! \brief Returns the configuration name of this modifier.
    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodTorturedName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodTorturedFactory);
}

//! \brief Returns the name under which this modifier is listed in the creature configuration.
const std::string& CreatureMoodTortured::getModifierName() const
{
    return CreatureMoodTorturedName;
}

//! \brief Returns 1 while the torture still weighs on the creature, otherwise 0.
double CreatureMoodTortured::getAmount(const Creature& creature) const
{
    return (creature.getNbTurnsTortureMood() > 0) ? 1.0 : 0.0;
}

//! \brief Returns a copy of this modifier.
CreatureMoodTortured* CreatureMoodTortured::clone() const
{
    return new CreatureMoodTortured(*this);
}
