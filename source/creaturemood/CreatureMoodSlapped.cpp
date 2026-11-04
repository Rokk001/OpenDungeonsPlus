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

#include "creaturemood/CreatureMoodSlapped.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"

#include <algorithm>

static const std::string CreatureMoodSlappedName = "Slapped";

namespace
{
//! \brief Factory that creates CreatureMoodSlapped objects from the creature configuration.
class CreatureMoodSlappedFactory : public CreatureMoodFactory
{
    //! \brief Creates a new CreatureMoodSlapped with default values.
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodSlapped; }

    //! \brief Returns the configuration name of this modifier.
    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodSlappedName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodSlappedFactory);
}

//! \brief Returns the name under which this modifier is listed in the creature configuration.
const std::string& CreatureMoodSlapped::getModifierName() const
{
    return CreatureMoodSlappedName;
}

//! \brief Returns 0, a slap is an event and not a problem that holds.
double CreatureMoodSlapped::getAmount(const Creature& creature) const
{
    return 0.0;
}

//! \brief Returns a copy of this modifier.
CreatureMoodSlapped* CreatureMoodSlapped::clone() const
{
    return new CreatureMoodSlapped(*this);
}

//! \brief Reads the parameters and then the value columns from the configuration stream; returns false if a value is missing.
bool CreatureMoodSlapped::importFromStream(std::istream& is)
{
    if(!(is >> mDurationTurns))
        return false;

    if(!(is >> mMaxSlaps))
        return false;

    return CreatureMood::importFromStream(is);
}

//! \brief Writes the parameters and then the value columns to the stream.
void CreatureMoodSlapped::exportToStream(std::ostream& os) const
{
    os << "\t" << mDurationTurns;
    os << "\t" << mMaxSlaps;
    CreatureMood::exportToStream(os);
}

//! \brief Appends the names of the parameters and then of the value columns to the format string.
void CreatureMoodSlapped::getFormatString(std::string& format) const
{
    if(!format.empty())
        format += "\t";

    format += "DurationTurns\tMaxSlaps";
    CreatureMood::getFormatString(format);
}
