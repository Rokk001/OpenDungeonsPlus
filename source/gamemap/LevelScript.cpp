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

#include "gamemap/LevelScript.h"

#include <algorithm>
#include <cstdlib>
#include <istream>
#include <ostream>
#include <sstream>

namespace
{

bool parseInt(const std::string& str, int64_t& value)
{
    if(str.empty())
        return false;

    char* end = nullptr;
    long long parsed = std::strtoll(str.c_str(), &end, 10);
    if(*end != '\0')
        return false;

    value = static_cast<int64_t>(parsed);
    return true;
}

bool parseInt32(const std::string& str, int32_t& value)
{
    int64_t tmp;
    if(!parseInt(str, tmp))
        return false;

    value = static_cast<int32_t>(tmp);
    return true;
}

std::string trim(const std::string& str)
{
    std::string::size_type first = str.find_first_not_of(" \t\r\n");
    if(first == std::string::npos)
        return std::string();

    std::string::size_type last = str.find_last_not_of(" \t\r\n");
    return str.substr(first, last - first + 1);
}

std::vector<std::string> split(const std::string& line)
{
    std::vector<std::string> tokens;
    std::istringstream ss(line);
    std::string token;
    while(ss >> token)
        tokens.push_back(token);

    return tokens;
}

//! \brief Returns what follows the first count tokens of the line, trimmed.
std::string restOfLine(const std::string& line, uint32_t count)
{
    std::string::size_type pos = 0;
    for(uint32_t i = 0; i < count; ++i)
    {
        pos = line.find_first_not_of(" \t", pos);
        if(pos == std::string::npos)
            return std::string();

        pos = line.find_first_of(" \t", pos);
        if(pos == std::string::npos)
            return std::string();
    }
    return trim(line.substr(pos));
}

bool parseCondition(const std::vector<std::string>& t, LevelScriptCondition& cond)
{
    // t[0] is "Cond"
    if(t.size() < 2)
        return false;

    const std::string& type = t[1];
    if(type == "time")
    {
        cond.mType = LevelScriptConditionType::time;
        return (t.size() == 3) && parseInt(t[2], cond.mNumber);
    }
    if(type == "region")
    {
        cond.mType = LevelScriptConditionType::region;
        if(t.size() == 4)
        {
            cond.mName = t[3];
            return parseInt32(t[2], cond.mSeatId);
        }
        return (t.size() == 7) &&
            parseInt32(t[2], cond.mSeatId) &&
            parseInt32(t[3], cond.mX1) &&
            parseInt32(t[4], cond.mY1) &&
            parseInt32(t[5], cond.mX2) &&
            parseInt32(t[6], cond.mY2);
    }
    if(type == "creatures")
    {
        cond.mType = LevelScriptConditionType::creatures;
        if(t.size() != 5)
            return false;
        if(t[3] == ">=")
            cond.mAtLeast = true;
        else if(t[3] == "<=")
            cond.mAtLeast = false;
        else
            return false;

        return parseInt32(t[2], cond.mSeatId) && parseInt(t[4], cond.mNumber);
    }
    if((type == "gold") || (type == "mana") || (type == "kills") || (type == "mined"))
    {
        if(type == "gold")
            cond.mType = LevelScriptConditionType::gold;
        else if(type == "mana")
            cond.mType = LevelScriptConditionType::mana;
        else if(type == "kills")
            cond.mType = LevelScriptConditionType::kills;
        else
            cond.mType = LevelScriptConditionType::goldMined;

        if(t.size() != 5)
            return false;
        if(t[3] == ">=")
            cond.mAtLeast = true;
        else if(t[3] == "<=")
            cond.mAtLeast = false;
        else
            return false;

        return parseInt32(t[2], cond.mSeatId) && parseInt(t[4], cond.mNumber);
    }
    if(type == "claimed")
    {
        cond.mType = LevelScriptConditionType::claimed;
        if(t.size() != 5)
            return false;

        cond.mName = t[3];
        if(t[4] == "all")
        {
            cond.mNumber = -1;
            return parseInt32(t[2], cond.mSeatId);
        }
        return parseInt32(t[2], cond.mSeatId) && parseInt(t[4], cond.mNumber) && (cond.mNumber > 0);
    }
    if(type == "room")
    {
        cond.mType = LevelScriptConditionType::room;
        if(t.size() != 5)
            return false;

        cond.mName = t[3];
        return parseInt32(t[2], cond.mSeatId) && parseInt(t[4], cond.mNumber);
    }
    if(type == "goal")
    {
        cond.mType = LevelScriptConditionType::goal;
        if(t.size() != 4)
            return false;

        cond.mName = t[3];
        return parseInt32(t[2], cond.mSeatId);
    }
    if(type == "flag")
    {
        cond.mType = LevelScriptConditionType::flag;
        if(t.size() != 4)
            return false;

        cond.mName = t[2];
        return parseInt(t[3], cond.mNumber);
    }
    return false;
}

bool parseAction(const std::string& line, const std::vector<std::string>& t, LevelScriptAction& action)
{
    // t[0] is "Action"
    if(t.size() < 2)
        return false;

    const std::string& type = t[1];
    if((type == "message") || (type == "objective"))
    {
        action.mType = (type == "message") ? LevelScriptActionType::message : LevelScriptActionType::objective;
        if(t.size() < 4)
            return false;

        action.mText = restOfLine(line, 3);
        return parseInt32(t[2], action.mSeatId) && !action.mText.empty();
    }
    if(type == "spawn")
    {
        action.mType = LevelScriptActionType::spawn;
        if(t.size() < 7)
            return false;

        if(!parseInt32(t[2], action.mSeatId) ||
           !parseInt32(t[3], action.mX) ||
           !parseInt32(t[4], action.mY) ||
           !parseInt32(t[5], action.mTargetSeatId))
        {
            return false;
        }

        for(std::size_t i = 6; i < t.size(); ++i)
        {
            std::string::size_type colon = t[i].find(':');
            if((colon == std::string::npos) || (colon == 0))
                return false;

            int64_t level;
            if(!parseInt(t[i].substr(colon + 1), level) || (level < 1))
                return false;

            action.mCreatures.push_back(std::pair<std::string, uint32_t>(t[i].substr(0, colon), static_cast<uint32_t>(level)));
        }
        return true;
    }
    if(type == "gold")
    {
        action.mType = LevelScriptActionType::gold;
        return (t.size() == 4) && parseInt32(t[2], action.mSeatId) && parseInt(t[3], action.mNumber);
    }
    if(type == "setflag")
    {
        action.mType = LevelScriptActionType::setFlag;
        if(t.size() != 4)
            return false;

        action.mText = t[2];
        return parseInt(t[3], action.mNumber);
    }
    if(type == "addflag")
    {
        action.mType = LevelScriptActionType::addFlag;
        if(t.size() != 4)
            return false;

        action.mText = t[2];
        return parseInt(t[3], action.mNumber);
    }
    if((type == "win") || (type == "lose"))
    {
        action.mType = (type == "win") ? LevelScriptActionType::win : LevelScriptActionType::lose;
        return (t.size() == 3) && parseInt32(t[2], action.mSeatId);
    }
    if(type == "reveal")
    {
        action.mType = LevelScriptActionType::reveal;
        if(t.size() != 4)
            return false;

        action.mText = t[3];
        return parseInt32(t[2], action.mSeatId);
    }
    if(type == "discover")
    {
        action.mType = LevelScriptActionType::discoverLevel;
        if(t.size() != 3)
            return false;

        action.mText = t[2];
        return true;
    }
    return false;
}

void writeCondition(std::ostream& os, const LevelScriptCondition& c)
{
    os << "Cond\t";
    switch(c.mType)
    {
        case LevelScriptConditionType::time:
            os << "time\t" << c.mNumber;
            break;
        case LevelScriptConditionType::region:
            if(!c.mName.empty())
                os << "region\t" << c.mSeatId << "\t" << c.mName;
            else
                os << "region\t" << c.mSeatId << "\t" << c.mX1 << "\t" << c.mY1 << "\t" << c.mX2 << "\t" << c.mY2;
            break;
        case LevelScriptConditionType::creatures:
            os << "creatures\t" << c.mSeatId << "\t" << (c.mAtLeast ? ">=" : "<=") << "\t" << c.mNumber;
            break;
        case LevelScriptConditionType::room:
            os << "room\t" << c.mSeatId << "\t" << c.mName << "\t" << c.mNumber;
            break;
        case LevelScriptConditionType::goal:
            os << "goal\t" << c.mSeatId << "\t" << c.mName;
            break;
        case LevelScriptConditionType::flag:
            os << "flag\t" << c.mName << "\t" << c.mNumber;
            break;
        case LevelScriptConditionType::gold:
            os << "gold\t" << c.mSeatId << "\t" << (c.mAtLeast ? ">=" : "<=") << "\t" << c.mNumber;
            break;
        case LevelScriptConditionType::mana:
            os << "mana\t" << c.mSeatId << "\t" << (c.mAtLeast ? ">=" : "<=") << "\t" << c.mNumber;
            break;
        case LevelScriptConditionType::kills:
            os << "kills\t" << c.mSeatId << "\t" << (c.mAtLeast ? ">=" : "<=") << "\t" << c.mNumber;
            break;
        case LevelScriptConditionType::goldMined:
            os << "mined\t" << c.mSeatId << "\t" << (c.mAtLeast ? ">=" : "<=") << "\t" << c.mNumber;
            break;
        case LevelScriptConditionType::claimed:
            os << "claimed\t" << c.mSeatId << "\t" << c.mName << "\t";
            if(c.mNumber < 0)
                os << "all";
            else
                os << c.mNumber;
            break;
    }
    os << "\n";
}

void writeAction(std::ostream& os, const LevelScriptAction& a)
{
    os << "Action\t";
    switch(a.mType)
    {
        case LevelScriptActionType::message:
            os << "message\t" << a.mSeatId << "\t" << a.mText;
            break;
        case LevelScriptActionType::objective:
            os << "objective\t" << a.mSeatId << "\t" << a.mText;
            break;
        case LevelScriptActionType::spawn:
            os << "spawn\t" << a.mSeatId << "\t" << a.mX << "\t" << a.mY << "\t" << a.mTargetSeatId;
            for(const std::pair<std::string, uint32_t>& creature : a.mCreatures)
                os << "\t" << creature.first << ":" << creature.second;
            break;
        case LevelScriptActionType::gold:
            os << "gold\t" << a.mSeatId << "\t" << a.mNumber;
            break;
        case LevelScriptActionType::setFlag:
            os << "setflag\t" << a.mText << "\t" << a.mNumber;
            break;
        case LevelScriptActionType::addFlag:
            os << "addflag\t" << a.mText << "\t" << a.mNumber;
            break;
        case LevelScriptActionType::win:
            os << "win\t" << a.mSeatId;
            break;
        case LevelScriptActionType::lose:
            os << "lose\t" << a.mSeatId;
            break;
        case LevelScriptActionType::reveal:
            os << "reveal\t" << a.mSeatId << "\t" << a.mText;
            break;
        case LevelScriptActionType::discoverLevel:
            os << "discover\t" << a.mText;
            break;
    }
    os << "\n";
}

} // namespace

bool LevelScript::importFromStream(std::istream& is)
{
    clear();

    LevelScriptTrigger trigger;
    bool inTrigger = false;
    std::string rawLine;
    while(std::getline(is, rawLine))
    {
        std::string line = trim(rawLine);
        if(line.empty() || (line[0] == '#'))
            continue;

        if(line == "[/Triggers]")
            return !inTrigger;

        if(line == "[Trigger]")
        {
            if(inTrigger)
                return false;

            inTrigger = true;
            trigger = LevelScriptTrigger();
            continue;
        }

        if(line == "[/Trigger]")
        {
            if(!inTrigger || trigger.mConditions.empty() || trigger.mActions.empty())
                return false;

            inTrigger = false;
            mTriggers.push_back(trigger);
            continue;
        }

        std::vector<std::string> t = split(line);
        const std::string& key = t[0];
        if(key == "Flag")
        {
            int64_t value;
            if(inTrigger || (t.size() != 3) || !parseInt(t[2], value))
                return false;

            mFlags[t[1]] = value;
        }
        else if(key == "Region")
        {
            LevelScriptRegion region;
            if(inTrigger || (t.size() != 6) ||
               !parseInt32(t[2], region.mX1) || !parseInt32(t[3], region.mY1) ||
               !parseInt32(t[4], region.mX2) || !parseInt32(t[5], region.mY2))
            {
                return false;
            }

            region.mName = t[1];
            setRegion(region);
        }
        else if(!inTrigger)
        {
            return false;
        }
        else if(key == "Name")
        {
            if(t.size() != 2)
                return false;

            trigger.mName = t[1];
        }
        else if(key == "Mode")
        {
            if((t.size() == 2) && (t[1] == "once"))
            {
                trigger.mRepeat = false;
            }
            else if((t.size() == 3) && (t[1] == "repeat") && parseInt(t[2], trigger.mCooldownSeconds))
            {
                trigger.mRepeat = true;
            }
            else
            {
                return false;
            }
        }
        else if(key == "Cond")
        {
            LevelScriptCondition cond;
            if(!parseCondition(t, cond))
                return false;

            trigger.mConditions.push_back(cond);
        }
        else if(key == "Action")
        {
            LevelScriptAction action;
            if(!parseAction(line, t, action))
                return false;

            trigger.mActions.push_back(action);
        }
        else if(key == "State")
        {
            int64_t fired;
            if((t.size() != 3) || !parseInt(t[1], fired) || !parseInt(t[2], trigger.mLastFiredTurn))
                return false;

            trigger.mTimesFired = static_cast<uint32_t>(fired);
        }
        else
        {
            return false;
        }
    }

    // The end tag is missing
    return false;
}

void LevelScript::exportToStream(std::ostream& os) const
{
    os << "[Triggers]\n";
    for(const std::pair<const std::string, int64_t>& flag : mFlags)
        os << "Flag\t" << flag.first << "\t" << flag.second << "\n";

    for(const LevelScriptRegion& region : mRegions)
    {
        os << "Region\t" << region.mName << "\t" << region.mX1 << "\t" << region.mY1
           << "\t" << region.mX2 << "\t" << region.mY2 << "\n";
    }

    for(const LevelScriptTrigger& trigger : mTriggers)
    {
        os << "[Trigger]\n";
        os << "Name\t" << trigger.mName << "\n";
        if(trigger.mRepeat)
            os << "Mode\trepeat\t" << trigger.mCooldownSeconds << "\n";
        else
            os << "Mode\tonce\n";

        for(const LevelScriptCondition& cond : trigger.mConditions)
            writeCondition(os, cond);

        for(const LevelScriptAction& action : trigger.mActions)
            writeAction(os, action);

        if(trigger.mTimesFired > 0)
            os << "State\t" << trigger.mTimesFired << "\t" << trigger.mLastFiredTurn << "\n";

        os << "[/Trigger]\n";
    }
    os << "[/Triggers]\n";
}

void LevelScript::clear()
{
    mTriggers.clear();
    mFlags.clear();
    mRegions.clear();
}

bool LevelScriptRegion::contains(int32_t x, int32_t y) const
{
    return (x >= std::min(mX1, mX2)) && (x <= std::max(mX1, mX2)) &&
           (y >= std::min(mY1, mY2)) && (y <= std::max(mY1, mY2));
}

const LevelScriptRegion* LevelScript::getRegion(const std::string& name) const
{
    for(const LevelScriptRegion& region : mRegions)
    {
        if(region.mName == name)
            return &region;
    }
    return nullptr;
}

void LevelScript::setRegion(const LevelScriptRegion& region)
{
    for(LevelScriptRegion& other : mRegions)
    {
        if(other.mName == region.mName)
        {
            other = region;
            return;
        }
    }
    mRegions.push_back(region);
}

bool LevelScript::removeRegion(const std::string& name)
{
    for(std::vector<LevelScriptRegion>::iterator it = mRegions.begin(); it != mRegions.end(); ++it)
    {
        if(it->mName == name)
        {
            mRegions.erase(it);
            return true;
        }
    }
    return false;
}

std::string LevelScript::getRegionNameAt(int32_t x, int32_t y) const
{
    for(const LevelScriptRegion& region : mRegions)
    {
        if(region.contains(x, y))
            return region.mName;
    }
    return std::string();
}

std::string LevelScript::getFreeRegionName() const
{
    for(uint32_t number = 1; ; ++number)
    {
        std::ostringstream name;
        name << "Region" << number;
        if(getRegion(name.str()) == nullptr)
            return name.str();
    }
}

void LevelScript::setRegions(const std::vector<LevelScriptRegion>& regions)
{
    mRegions = regions;
}

int64_t LevelScript::getFlag(const std::string& name) const
{
    std::map<std::string, int64_t>::const_iterator it = mFlags.find(name);
    if(it == mFlags.end())
        return 0;

    return it->second;
}

void LevelScript::setFlag(const std::string& name, int64_t value)
{
    mFlags[name] = value;
}
