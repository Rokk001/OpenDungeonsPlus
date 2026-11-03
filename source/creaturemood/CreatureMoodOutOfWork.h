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

#ifndef CREATUREMOODOUTOFWORK_H
#define CREATUREMOODOUTOFWORK_H

#include "creaturemood/CreatureMood.h"

//! \brief Lasting problem: the creature finds no work.
class CreatureMoodOutOfWork : public CreatureMood
{
public:
    //! \brief Creates the modifier with all values set to zero (they are read from the configuration).
    CreatureMoodOutOfWork() :
        CreatureMood(CreatureMoodKind::Lasting, CreatureMoodColumns::JumpFallReward),
        mTurnsMin(0)
    {}

    //! \brief Destroys the modifier.
    virtual ~CreatureMoodOutOfWork()
    {}

    //! \brief Returns the name under which this modifier is listed in the creature configuration.
    const std::string& getModifierName() const override;

    //! \brief Returns 1 while the creature counts at least TurnsMin turns without work, otherwise 0.
    //! \param creature The creature to look at.
    virtual double getAmount(const Creature& creature) const override;

    //! \brief Returns a copy of this modifier.
    CreatureMoodOutOfWork* clone() const override;

    //! \brief Returns the number of turns without work from which the problem holds.
    inline int32_t getTurnsMin() const
    { return mTurnsMin; }

    //! \brief Reads the parameters and then the value columns from the configuration stream; returns false if a value is missing.
    virtual bool importFromStream(std::istream& is) override;
    //! \brief Writes the parameters and then the value columns to the stream.
    virtual void exportToStream(std::ostream& os) const override;
    //! \brief Appends the names of the parameters and then of the value columns to the format string.
    virtual void getFormatString(std::string& format) const override;

private:
    //! \brief Number of turns without work from which the problem holds
    int32_t mTurnsMin;
};

#endif // CREATUREMOODOUTOFWORK_H
