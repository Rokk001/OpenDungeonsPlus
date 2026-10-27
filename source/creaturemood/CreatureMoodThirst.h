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

#ifndef CREATUREMOODTHIRST_H
#define CREATUREMOODTHIRST_H

#include "creaturemood/CreatureMood.h"

//! \brief Mood modifier of the thirst: from a start value of the thirst (0 - 100) on, every point costs
//! the configured mood (config line "Thirst <start> <modifier>" in the mood modifiers of a creature type).
class CreatureMoodThirst : public CreatureMood
{
public:
    //! \brief Creates the modifier with no effect (start 0, modifier 0) until it is read from the configuration.
    CreatureMoodThirst() :
        mStartThirst(0),
        mMoodModifier(0)
    {}

    virtual ~CreatureMoodThirst()
    {}

    //! \brief Returns the name of this modifier ("Thirst").
    const std::string& getModifierName() const override;

    //! \brief Returns the mood of the creature's thirst: 0 below the start value, else (thirst - start) x modifier.
    //! \brief Computes this mood contribution.
    virtual double computeMood(const Creature& creature) const override;

    //! \brief Returns a copy of this modifier.
    inline CreatureMoodThirst* clone() const override;

    //! \brief Reads the start value and the modifier from the stream.
    virtual bool importFromStream(std::istream& is) override;
    //! \brief Writes the start value and the modifier to the stream.
    virtual void exportToStream(std::ostream& os) const override;
    //! \brief Appends the column names of the configuration line to the format string.
    virtual void getFormatString(std::string& format) const override;

private:
    //! \brief Creates the modifier with the given values (used by clone).
    CreatureMoodThirst(int32_t startThirst, double moodModifier) :
        mStartThirst(startThirst),
        mMoodModifier(moodModifier)
    {}

    //! \brief The thirst (0 - 100) from which the modifier acts.
    int32_t mStartThirst;
    //! \brief The mood per point of thirst above the start value (negative = a malus).
    double mMoodModifier;
};

#endif // CREATUREMOODTHIRST_H
