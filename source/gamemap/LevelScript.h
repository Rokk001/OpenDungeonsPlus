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

#ifndef LEVELSCRIPT_H
#define LEVELSCRIPT_H

#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>
#include <utility>
#include <vector>

//! \brief Level scripting: triggers made of conditions and actions, read from the
//! [Triggers] section of a level file. This file only holds the data and the text
//! format. The evaluation on the server is done in LevelScriptRunner.cpp.
//!
//! Section format (one item per line, fields separated by tabs):
//!
//!   [Triggers]
//!   Flag    <name>  <value>                   # initial value of a flag (unset flags are 0)
//!   [Trigger]
//!   Name    <name>
//!   Mode    once | repeat <cooldownSeconds>
//!   Cond    time <seconds>                    # at least that many seconds since the level start
//!   Cond    region <seatId> <x1> <y1> <x2> <y2>   # a creature of the seat (-1: any) is in the rectangle
//!   Cond    creatures <seatId> >= | <= <count>
//!   Cond    room <seatId> <roomName> <count>  # seat owns at least count rooms of that type
//!   Cond    goal <seatId> <goalName>          # seat completed a goal with that name
//!   Cond    flag <name> <value>               # flag has exactly that value
//!   Action  message <seatId> <text>           # seat -1: every human player
//!   Action  objective <seatId> <text>
//!   Action  spawn <seatId> <x> <y> <targetSeatId> <class:level> [<class:level> ...]
//!   Action  gold <seatId> <amount>
//!   Action  setflag <name> <value>
//!   Action  win <seatId>                      # seat -1: every human player
//!   Action  lose <seatId>
//!   Action  discover <levelFile>              # campaign: reveals a bonus level (level file as in Campaign.cfg)
//!   State   <timesFired> <lastFiredTurn>      # written by the game, only needed in savegames
//!   [/Trigger]
//!   [/Triggers]
//!
//! All the conditions of a trigger must be true at the same time. A trigger that is
//! not repeatable fires once. A repeatable one fires again once the cooldown elapsed
//! and the conditions are (still) true.

enum class LevelScriptConditionType
{
    time,
    region,
    creatures,
    room,
    goal,
    flag
};

enum class LevelScriptActionType
{
    message,
    objective,
    spawn,
    gold,
    setFlag,
    win,
    lose,
    discoverLevel
};

struct LevelScriptCondition
{
    LevelScriptCondition() :
        mType(LevelScriptConditionType::time),
        mSeatId(-1),
        mX1(0),
        mY1(0),
        mX2(0),
        mY2(0),
        mAtLeast(true),
        mNumber(0)
    {}

    LevelScriptConditionType mType;
    int32_t mSeatId;
    int32_t mX1;
    int32_t mY1;
    int32_t mX2;
    int32_t mY2;
    //! \brief For creatures: true for >=, false for <=
    bool mAtLeast;
    //! \brief Seconds (time), count (creatures, room) or value (flag)
    int64_t mNumber;
    //! \brief Room name (room), goal name (goal) or flag name (flag)
    std::string mName;
};

struct LevelScriptAction
{
    LevelScriptAction() :
        mType(LevelScriptActionType::message),
        mSeatId(-1),
        mX(0),
        mY(0),
        mTargetSeatId(-1),
        mNumber(0)
    {}

    LevelScriptActionType mType;
    int32_t mSeatId;
    int32_t mX;
    int32_t mY;
    //! \brief spawn: seat whose dungeon the spawned group attacks (-1: none)
    int32_t mTargetSeatId;
    //! \brief Gold amount (gold) or flag value (setflag)
    int64_t mNumber;
    //! \brief Message text (message, objective) or flag name (setflag)
    std::string mText;
    //! \brief spawn: creature class name and level
    std::vector<std::pair<std::string, uint32_t> > mCreatures;
};

struct LevelScriptTrigger
{
    LevelScriptTrigger() :
        mRepeat(false),
        mCooldownSeconds(0),
        mTimesFired(0),
        mLastFiredTurn(-1)
    {}

    std::string mName;
    bool mRepeat;
    int64_t mCooldownSeconds;
    std::vector<LevelScriptCondition> mConditions;
    std::vector<LevelScriptAction> mActions;
    //! \brief Runtime state, saved with the game
    uint32_t mTimesFired;
    int64_t mLastFiredTurn;
};

class LevelScript
{
public:
    //! \brief Reads the lines after the [Triggers] tag, up to and including [/Triggers].
    //! Returns false on a malformed section. Existing content is replaced.
    bool importFromStream(std::istream& is);

    //! \brief Writes the whole section, including the [Triggers] and [/Triggers] tags.
    void exportToStream(std::ostream& os) const;

    void clear();

    inline bool isEmpty() const
    { return mTriggers.empty() && mFlags.empty(); }

    inline std::vector<LevelScriptTrigger>& getTriggers()
    { return mTriggers; }

    inline const std::vector<LevelScriptTrigger>& getTriggers() const
    { return mTriggers; }

    int64_t getFlag(const std::string& name) const;
    void setFlag(const std::string& name, int64_t value);

    inline const std::map<std::string, int64_t>& getFlags() const
    { return mFlags; }

private:
    std::vector<LevelScriptTrigger> mTriggers;
    std::map<std::string, int64_t> mFlags;
};

#endif // LEVELSCRIPT_H
