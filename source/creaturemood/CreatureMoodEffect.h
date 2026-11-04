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

#ifndef CREATUREMOODEFFECT_H
#define CREATUREMOODEFFECT_H

#include <string>

//! \brief A running mood effect (a buff or a debuff) of a creature: it adds a mood strength per turn for a number of
//! turns. Effects are separate instances and add up, also the same effect several times on one creature.
struct CreatureMoodEffect
{
    //! \brief Creates an empty effect that does nothing.
    CreatureMoodEffect() :
        mStrength(0.0),
        mTurnsLeft(0.0)
    {}

    //! \brief Creates an effect.
    //! \param name The name of the effect without spaces (for example "MakeUnhappy").
    //! \param strength The mood per turn, negative for a debuff.
    //! \param turnsLeft The turns the effect still runs.
    CreatureMoodEffect(const std::string& name, double strength, double turnsLeft) :
        mName(name),
        mStrength(strength),
        mTurnsLeft(turnsLeft)
    {}

    //! \brief The name of the effect without spaces, the effect line of the profile page shows it with spaces
    std::string mName;
    //! \brief The mood per turn, negative for a debuff
    double mStrength;
    //! \brief The turns the effect still runs
    double mTurnsLeft;
};

#endif // CREATUREMOODEFFECT_H
