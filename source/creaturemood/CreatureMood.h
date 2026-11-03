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

#ifndef CREATUREMOOD_H
#define CREATUREMOOD_H

#include <cstdint>
#include <iosfwd>
#include <string>

class Creature;
class GameMap;

enum class CreatureMoodLevel
{
    Happy,
    Neutral,
    Upset,
    Angry,
    Furious,
    //! \brief The mood is not known on this side, e.g. on a client for creatures of other seats
    Unknown = -1
};

//! \brief How a mood modifier acts on the stored mood.
enum class CreatureMoodKind
{
    //! \brief A lasting problem: a jump down when it starts, a fall per turn while it holds, a rise when it is solved
    Lasting,
    //! \brief A problem that comes and goes with every step: only the fall per turn while it holds
    ComeAndGo,
    //! \brief A one-time event: the value is added to the stored mood when the event happens
    Event
};

//! \brief The value columns a mood modifier reads after its own parameters in the creature configuration.
enum class CreatureMoodColumns
{
    //! \brief Jump, fall per turn and reward
    JumpFallReward,
    //! \brief Only the fall per turn
    Fall,
    //! \brief One value, the mood of the event
    Event
};

//! \brief One mood modifier of a creature type: tells whether its problem holds and carries the jump, fall and reward
//! (values at sensitivity 1.0, the sensitivity of the creature type is applied by the creature).
class CreatureMood
{
public:
    //! \brief Creates the modifier with the kind and the value columns of its configuration line and all values 0.
    //! \param kind How the modifier acts on the stored mood.
    //! \param columns The value columns that follow the parameters of the modifier in the configuration.
    CreatureMood(CreatureMoodKind kind, CreatureMoodColumns columns) :
        mKind(kind),
        mColumns(columns),
        mJump(0.0),
        mFall(0.0),
        mReward(0.0)
    {}

    virtual ~CreatureMood()
    {}

    virtual const std::string& getModifierName() const = 0;

    //! \brief Returns how the modifier acts on the stored mood.
    inline CreatureMoodKind getKind() const
    { return mKind; }

    //! \brief Returns how strong the problem is now: 0 when it does not hold, 1 when it holds (the number of missed
    //! wages for the wage problem, the number of causes for a come-and-go problem). Events always return 0.
    //! \param creature The creature to look at.
    virtual double getAmount(const Creature& creature) const = 0;

    //! \brief Returns the fall per turn (negative) the problem causes now, at sensitivity 1.0. A come-and-go problem
    //! with its own way to count (dirt) overrides it.
    //! \param creature The creature to look at.
    virtual double getFallPerTurn(const Creature& creature) const;

    //! \brief Returns the jump when the problem starts (per wage for the wage problem) or the mood of an event.
    inline double getJump() const
    { return mJump; }

    //! \brief Returns the fall per turn while the problem holds (negative).
    inline double getFall() const
    { return mFall; }

    //! \brief Returns the rise when the problem ends (per wage paid for the wage problem).
    inline double getReward() const
    { return mReward; }

    //! \brief This function should return a copy of the current class
    virtual CreatureMood* clone() const = 0;

    virtual bool isEqual(const CreatureMood& creatureMood) const;

    //! \brief Returns the format string (including specific additional parameters)
    virtual void getFormatString(std::string& format) const;

    //! \brief Reads the value columns (jump, fall and reward, or the fall, or the event value) from the stream.
    //! Subclasses read their own parameters first and call this last.
    virtual bool importFromStream(std::istream& file);
    //! \brief Writes the value columns to the stream, subclasses write their own parameters first.
    virtual void exportToStream(std::ostream& os) const;

    static std::string toString(CreatureMoodLevel moodLevel);

private:
    CreatureMoodKind mKind;
    CreatureMoodColumns mColumns;
    //! \brief The jump of a lasting problem or the value of an event
    double mJump;
    //! \brief The fall per turn
    double mFall;
    //! \brief The rise when the problem ends
    double mReward;
};

#endif // CREATUREMOOD_H
