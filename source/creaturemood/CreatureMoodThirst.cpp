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

#include <sstream>

static const std::string CreatureMoodThirstName = "Thirst";

namespace
{
//! \brief Creates the Thirst modifier when the configuration names it.
class CreatureMoodThirstFactory : public CreatureMoodFactory
{
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodThirst; }

    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodThirstName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodThirstFactory);
}

const std::string& CreatureMoodThirst::getModifierName() const
{
    return CreatureMoodThirstName;
}

int32_t CreatureMoodThirst::computeMood(const Creature& creature) const
{
    int32_t thirst = static_cast<int32_t>(creature.getThirst());
    if(thirst < mStartThirst)
        return 0;

    return (thirst - mStartThirst) * mMoodModifier;
}

CreatureMoodThirst* CreatureMoodThirst::clone() const
{
    return new CreatureMoodThirst(*this);
}

bool CreatureMoodThirst::importFromStream(std::istream& is)
{
    if(!CreatureMood::importFromStream(is))
        return false;

    if(!(is >> mStartThirst))
        return false;
    if(!(is >> mMoodModifier))
        return false;

    return true;
}

void CreatureMoodThirst::exportToStream(std::ostream& os) const
{
    CreatureMood::exportToStream(os);
    os << "\t" << mStartThirst;
    os << "\t" << mMoodModifier;
}

void CreatureMoodThirst::getFormatString(std::string& format) const
{
    CreatureMood::getFormatString(format);
    if(!format.empty())
        format += "\t";

    format += "StartThirst\tMoodModifier";
}
