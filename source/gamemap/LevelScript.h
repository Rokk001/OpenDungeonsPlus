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
//!   TimeLimit <seconds>                       # written by the game: the time limit set by an action, in level seconds (-2: removed)
//!   Region  <name> <x1> <y1> <x2> <y2>        # a named rectangle of tiles (placed in the level editor)
//!   [Trigger]
//!   Name    <name>
//!   Mode    once | repeat <cooldownSeconds>
//!   Cond    time <seconds>                    # at least that many seconds since the level start
//!   Cond    region <seatId> <x1> <y1> <x2> <y2>   # a creature of the seat (-1: any) is in the rectangle
//!   Cond    region <seatId> <regionName>          # the same, with the rectangle of a named region
//!   Cond    creatures <seatId> >= | <= <count>
//!   Cond    room <seatId> <roomName> <count>  # seat owns at least count rooms of that type
//!   Cond    gold <seatId> >= | <= <amount>    # gold of the seat
//!   Cond    mana <seatId> >= | <= <amount>    # mana of the seat
//!   Cond    kills <seatId> >= | <= <count>    # creatures the seat has killed
//!   Cond    mined <seatId> >= | <= <amount>   # gold the seat has mined
//!   Cond    claimed <seatId> <regionName> <count> | all   # tiles of the region claimed by the seat
//!   Cond    goal <seatId> <goalName>          # seat completed a goal with that name
//!   Cond    flag <name> <value>               # flag has exactly that value
//!   Action  message <seatId> <text>           # seat -1: every human player
//!   Action  objective <seatId> <text>
//!   Action  spawn <seatId> <x> <y> <targetSeatId> <class:level> [<class:level> ...]
//!   Action  gold <seatId> <amount>
//!   Action  setflag <name> <value>
//!   Action  addflag <name> <delta>            # adds to the flag (a negative value subtracts)
//!   Action  win <seatId>                      # seat -1: every human player
//!   Action  lose <seatId>
//!   Action  reveal <seatId> <regionName>      # the tiles of the region stay visible to the seat
//!   Action  make <seatId> <skillName>         # room, trap, door or spell becomes available (skill type name such as roomHatchery); seat -1: every human player
//!   Action  timelimit <seconds>               # the level is lost for every keeper when that many seconds have passed from now (0: removes any time limit); the remaining time is shown on the HUD
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
    flag,
    gold,
    mana,
    kills,
    goldMined,
    claimed
};

enum class LevelScriptActionType
{
    message,
    objective,
    spawn,
    gold,
    setFlag,
    addFlag,
    win,
    lose,
    reveal,
    discoverLevel,
    make,
    timeLimit
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
    //! \brief For creatures, gold, mana, kills and goldMined: true for >=, false for <=
    bool mAtLeast;
    //! \brief Seconds (time), count (creatures, room, claimed, -1 for all of the region),
    //! amount (gold, mana, goldMined), count (kills) or value (flag)
    int64_t mNumber;
    //! \brief Room name (room), goal name (goal), flag name (flag) or, for region, the
    //! name of a region of the script (empty when the rectangle is given by mX1 to mY2)
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
    //! \brief Gold amount (gold), flag value (setflag), amount added to a flag (addflag) or
    //! seconds (timeLimit)
    int64_t mNumber;
    //! \brief Message text (message, objective), flag name (setflag), region name (reveal),
    //! level file (discoverLevel) or skill type name (make)
    std::string mText;
    //! \brief spawn: creature class name and level
    std::vector<std::pair<std::string, uint32_t> > mCreatures;
};

//! \brief A named rectangle of tiles, both corners included. The level editor places them
//! and the conditions and actions of the triggers refer to them by name.
struct LevelScriptRegion
{
    LevelScriptRegion() :
        mX1(0),
        mY1(0),
        mX2(0),
        mY2(0)
    {}

    LevelScriptRegion(const std::string& name, int32_t x1, int32_t y1, int32_t x2, int32_t y2) :
        mName(name),
        mX1(x1),
        mY1(y1),
        mX2(x2),
        mY2(y2)
    {}

    //! \brief True if the tile is inside the rectangle, whatever the order of the corners
    bool contains(int32_t x, int32_t y) const;

    std::string mName;
    int32_t mX1;
    int32_t mY1;
    int32_t mX2;
    int32_t mY2;
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
    LevelScript() :
        mTimeLimitSeconds(TIME_LIMIT_NOT_SET)
    {}

    //! \brief Reads the lines after the [Triggers] tag, up to and including [/Triggers].
    //! Returns false on a malformed section. Existing content is replaced.
    bool importFromStream(std::istream& is);

    //! \brief Writes the whole section, including the [Triggers] and [/Triggers] tags.
    void exportToStream(std::ostream& os) const;

    void clear();

    inline bool isEmpty() const
    { return mTriggers.empty() && mFlags.empty() && mRegions.empty() && (mTimeLimitSeconds == TIME_LIMIT_NOT_SET); }

    inline std::vector<LevelScriptTrigger>& getTriggers()
    { return mTriggers; }

    inline const std::vector<LevelScriptTrigger>& getTriggers() const
    { return mTriggers; }

    int64_t getFlag(const std::string& name) const;
    void setFlag(const std::string& name, int64_t value);

    inline const std::map<std::string, int64_t>& getFlags() const
    { return mFlags; }

    inline const std::vector<LevelScriptRegion>& getRegions() const
    { return mRegions; }

    //! \brief Returns the region with that name, nullptr if there is none
    const LevelScriptRegion* getRegion(const std::string& name) const;

    //! \brief Adds the region or, if the name is already used, moves that region
    void setRegion(const LevelScriptRegion& region);

    //! \brief Returns false if there was no region with that name
    bool removeRegion(const std::string& name);

    //! \brief The name of the first region that holds the tile, empty if there is none
    std::string getRegionNameAt(int32_t x, int32_t y) const;

    //! \brief A name of the form Region<number> that no region uses yet
    std::string getFreeRegionName() const;

    //! \brief Replaces all the regions, used by the editor when the server sends them
    void setRegions(const std::vector<LevelScriptRegion>& regions);

    static const int64_t TIME_LIMIT_NOT_SET = -1;
    static const int64_t TIME_LIMIT_REMOVED = -2;

    //! \brief The time limit set by a script action, as the level second at which it runs out.
    //! TIME_LIMIT_NOT_SET if no action set one (the game duration setting applies),
    //! TIME_LIMIT_REMOVED if an action removed the limit.
    inline int64_t getTimeLimitSeconds() const
    { return mTimeLimitSeconds; }

    inline void setTimeLimitSeconds(int64_t seconds)
    { mTimeLimitSeconds = seconds; }

    //! \brief Moves a time limit that is set so that it counts from a new level start, which is
    //! elapsedSeconds later than the current one. Used when a game is saved: the turn counter
    //! starts at 0 again when it is loaded.
    void rebaseTimeLimit(int64_t elapsedSeconds);

private:
    std::vector<LevelScriptTrigger> mTriggers;
    std::map<std::string, int64_t> mFlags;
    std::vector<LevelScriptRegion> mRegions;
    int64_t mTimeLimitSeconds;
};

#endif // LEVELSCRIPT_H
