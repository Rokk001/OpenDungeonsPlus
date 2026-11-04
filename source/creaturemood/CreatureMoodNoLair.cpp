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

#include "creaturemood/CreatureMoodNoLair.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"

#include <algorithm>

static const std::string CreatureMoodNoLairName = "NoLair";

namespace
{
//! \brief Factory that creates CreatureMoodNoLair objects from the creature configuration.
class CreatureMoodNoLairFactory : public CreatureMoodFactory
{
    //! \brief Creates a new CreatureMoodNoLair with default values.
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodNoLair; }

    //! \brief Returns the configuration name of this modifier.
    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodNoLairName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodNoLairFactory);
}

//! \brief Returns the name under which this modifier is listed in the creature configuration.
const std::string& CreatureMoodNoLair::getModifierName() const
{
    return CreatureMoodNoLairName;
}

//! \brief Returns 1 while the creature has no home tile, otherwise 0.
double CreatureMoodNoLair::getAmount(const Creature& creature) const
{
    return (creature.getHomeTile() == nullptr) ? 1.0 : 0.0;
}

//! \brief Returns a copy of this modifier.
CreatureMoodNoLair* CreatureMoodNoLair::clone() const
{
    return new CreatureMoodNoLair(*this);
}
