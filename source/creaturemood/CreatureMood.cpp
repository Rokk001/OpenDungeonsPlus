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

#include "creaturemood/CreatureMood.h"

#include "utils/Helper.h"
#include "utils/LogManager.h"

#include <istream>
#include <ostream>
#include <typeinfo>

std::string CreatureMood::toString(CreatureMoodLevel moodLevel)
{
    switch(moodLevel)
    {
        case CreatureMoodLevel::Happy:
            return "Happy";
        case CreatureMoodLevel::Neutral:
            return "Neutral";
        case CreatureMoodLevel::Upset:
            return "Upset";
        case CreatureMoodLevel::Angry:
            return "Angry";
        case CreatureMoodLevel::Furious:
            return "Furious";
        case CreatureMoodLevel::Unknown:
            return "Unknown";
        default:
            OD_LOG_ERR("moodLevel=" + Helper::toString(static_cast<int>(moodLevel)));
            return "";
    }
}

//! \brief Returns the fall per turn of the problem: the fall per turn times how strong it is now.
double CreatureMood::getFallPerTurn(const Creature& creature) const
{
    return getAmount(creature) * mFall;
}

//! \brief Two modifiers are equal when they have the same type and the same value columns.
bool CreatureMood::isEqual(const CreatureMood& creatureMood) const
{
    if(typeid(*this) != typeid(creatureMood))
        return false;

    return (mJump == creatureMood.mJump) && (mFall == creatureMood.mFall) && (mReward == creatureMood.mReward);
}

//! \brief Appends the names of the value columns to the format string.
void CreatureMood::getFormatString(std::string& format) const
{
    if(!format.empty())
        format += "\t";

    switch(mColumns)
    {
        case CreatureMoodColumns::JumpFallReward:
            format += "Jump\tFallPerTurn\tReward";
            break;
        case CreatureMoodColumns::Fall:
            format += "FallPerTurn";
            break;
        case CreatureMoodColumns::Event:
            format += "MoodModifier";
            break;
    }
}

//! \brief Reads the value columns of the configuration line; returns false if a value is missing.
bool CreatureMood::importFromStream(std::istream& is)
{
    switch(mColumns)
    {
        case CreatureMoodColumns::JumpFallReward:
            return static_cast<bool>(is >> mJump >> mFall >> mReward);
        case CreatureMoodColumns::Fall:
            return static_cast<bool>(is >> mFall);
        case CreatureMoodColumns::Event:
            return static_cast<bool>(is >> mJump);
    }
    return false;
}

//! \brief Writes the value columns of the configuration line.
void CreatureMood::exportToStream(std::ostream& os) const
{
    switch(mColumns)
    {
        case CreatureMoodColumns::JumpFallReward:
            os << "\t" << mJump << "\t" << mFall << "\t" << mReward;
            break;
        case CreatureMoodColumns::Fall:
            os << "\t" << mFall;
            break;
        case CreatureMoodColumns::Event:
            os << "\t" << mJump;
            break;
    }
}
