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

#ifndef CREATUREMOODSLAPPED_H
#define CREATUREMOODSLAPPED_H

#include "creaturemood/CreatureMood.h"

//! \brief One-time event: the creature was slapped. At most MaxSlaps slaps within DurationTurns turns cost mood.
class CreatureMoodSlapped : public CreatureMood
{
public:
    //! \brief Creates the modifier with all values set to zero (they are read from the configuration).
    CreatureMoodSlapped() :
        CreatureMood(CreatureMoodKind::Event, CreatureMoodColumns::Event),
        mDurationTurns(0),
        mMaxSlaps(0)
    {}

    //! \brief Destroys the modifier.
    virtual ~CreatureMoodSlapped()
    {}

    //! \brief Returns the name under which this modifier is listed in the creature configuration.
    const std::string& getModifierName() const override;

    //! \brief Returns 0, a slap is an event and not a problem that holds.
    //! \param creature The creature to look at.
    virtual double getAmount(const Creature& creature) const override;

    //! \brief Returns a copy of this modifier.
    CreatureMoodSlapped* clone() const override;

    //! \brief Returns the number of turns a slap counts.
    inline int32_t getDurationTurns() const
    { return mDurationTurns; }

    //! \brief Returns the number of slaps within the duration that cost mood.
    inline int32_t getMaxSlaps() const
    { return mMaxSlaps; }

    //! \brief Reads the parameters and then the value columns from the configuration stream; returns false if a value is missing.
    virtual bool importFromStream(std::istream& is) override;
    //! \brief Writes the parameters and then the value columns to the stream.
    virtual void exportToStream(std::ostream& os) const override;
    //! \brief Appends the names of the parameters and then of the value columns to the format string.
    virtual void getFormatString(std::string& format) const override;

private:
    //! \brief Turns a slap counts
    int32_t mDurationTurns;
    //! \brief Number of slaps within DurationTurns that cost mood
    int32_t mMaxSlaps;
};

#endif // CREATUREMOODSLAPPED_H
