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

#include "creaturemood/CreatureMoodThirst.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"

#include <algorithm>

static const std::string CreatureMoodThirstName = "Thirst";

namespace
{
//! \brief Factory that creates CreatureMoodThirst objects from the creature configuration.
class CreatureMoodThirstFactory : public CreatureMoodFactory
{
    //! \brief Creates a new CreatureMoodThirst with default values.
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodThirst; }

    //! \brief Returns the configuration name of this modifier.
    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodThirstName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodThirstFactory);
}

//! \brief Returns the name under which this modifier is listed in the creature configuration.
const std::string& CreatureMoodThirst::getModifierName() const
{
    return CreatureMoodThirstName;
}

//! \brief Returns 1 while the thirst of the creature has reached the start value, otherwise 0.
double CreatureMoodThirst::getAmount(const Creature& creature) const
{
    return (creature.getThirst() >= mStartThirst) ? 1.0 : 0.0;
}

//! \brief Returns a copy of this modifier.
CreatureMoodThirst* CreatureMoodThirst::clone() const
{
    return new CreatureMoodThirst(*this);
}

//! \brief Reads the parameters and then the value columns from the configuration stream; returns false if a value is missing.
bool CreatureMoodThirst::importFromStream(std::istream& is)
{
    if(!(is >> mStartThirst))
        return false;

    return CreatureMood::importFromStream(is);
}

//! \brief Writes the parameters and then the value columns to the stream.
void CreatureMoodThirst::exportToStream(std::ostream& os) const
{
    os << "\t" << mStartThirst;
    CreatureMood::exportToStream(os);
}

//! \brief Appends the names of the parameters and then of the value columns to the format string.
void CreatureMoodThirst::getFormatString(std::string& format) const
{
    if(!format.empty())
        format += "\t";

    format += "StartThirst";
    CreatureMood::getFormatString(format);
}
