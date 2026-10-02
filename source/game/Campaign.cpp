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

#include "game/Campaign.h"

#include <fstream>
#include <istream>
#include <ostream>
#include <sstream>

namespace
{
std::string trim(const std::string& text)
{
    const std::string whitespace = " \t\r\n";
    size_t first = text.find_first_not_of(whitespace);
    if(first == std::string::npos)
        return std::string();

    size_t last = text.find_last_not_of(whitespace);
    return text.substr(first, last - first + 1);
}
} // namespace

Campaign::Campaign():
    mActive(false),
    mPlayedLevel(0),
    mPlayedLevelWon(false)
{
}

Campaign& Campaign::getSingleton()
{
    static Campaign campaign;
    return campaign;
}

std::string Campaign::unescapeText(const std::string& text)
{
    std::string result;
    for(size_t i = 0; i < text.size(); ++i)
    {
        if((text[i] == '\\') && (i + 1 < text.size()) && (text[i + 1] == 'n'))
        {
            result += '\n';
            ++i;
            continue;
        }
        result += text[i];
    }
    return result;
}

bool Campaign::importDefinition(std::istream& is)
{
    std::lock_guard<std::mutex> lock(mMutex);
    mLevels.clear();
    mCompleted.clear();

    CampaignLevel level;
    bool inLevel = false;
    std::string line;
    while(std::getline(is, line))
    {
        line = trim(line);
        if(line.empty() || (line[0] == '#'))
            continue;

        if(line == "[Level]")
        {
            if(inLevel && !level.mFile.empty())
                mLevels.push_back(level);

            level = CampaignLevel();
            inLevel = true;
            continue;
        }

        size_t pos = line.find('=');
        if(!inLevel || (pos == std::string::npos))
            continue;

        std::string key = trim(line.substr(0, pos));
        std::string value = trim(line.substr(pos + 1));
        if(key == "File")
            level.mFile = value;
        else if(key == "Title")
            level.mTitle = value;
        else if(key == "Briefing")
            level.mBriefing = unescapeText(value);
        else if(key == "Debriefing")
            level.mDebriefing = unescapeText(value);
    }

    if(inLevel && !level.mFile.empty())
        mLevels.push_back(level);

    mCompleted.assign(mLevels.size(), false);
    return !mLevels.empty();
}

bool Campaign::importProgress(std::istream& is)
{
    std::lock_guard<std::mutex> lock(mMutex);
    mCompleted.assign(mLevels.size(), false);

    std::string line;
    while(std::getline(is, line))
    {
        std::istringstream ss(trim(line));
        std::string keyword;
        ss >> keyword;
        if(keyword != "Completed")
            continue;

        size_t index;
        while(ss >> index)
        {
            if(index < mCompleted.size())
                mCompleted[index] = true;
        }
    }
    return true;
}

void Campaign::exportProgress(std::ostream& os) const
{
    std::lock_guard<std::mutex> lock(mMutex);
    os << "# Campaign progress. Do not edit while the game is running.\n";
    os << "Completed";
    for(size_t i = 0; i < mCompleted.size(); ++i)
    {
        if(mCompleted[i])
            os << " " << i;
    }
    os << "\n";
}

void Campaign::setProgressPath(const std::string& path)
{
    std::lock_guard<std::mutex> lock(mMutex);
    mProgressPath = path;
}

bool Campaign::saveProgress() const
{
    std::string path;
    {
        std::lock_guard<std::mutex> lock(mMutex);
        path = mProgressPath;
    }
    if(path.empty())
        return false;

    std::ofstream file(path.c_str());
    if(!file.is_open())
        return false;

    exportProgress(file);
    return file.good();
}

size_t Campaign::getNumLevels() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return mLevels.size();
}

const CampaignLevel& Campaign::getLevel(size_t index) const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return mLevels.at(index);
}

bool Campaign::isCompleted(size_t index) const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return (index < mCompleted.size()) && mCompleted[index];
}

size_t Campaign::getCurrentLevelNoLock() const
{
    for(size_t i = 0; i < mCompleted.size(); ++i)
    {
        if(!mCompleted[i])
            return i;
    }
    return mCompleted.size();
}

size_t Campaign::getCurrentLevel() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return getCurrentLevelNoLock();
}

bool Campaign::isUnlocked(size_t index) const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return (index < mLevels.size()) && (index <= getCurrentLevelNoLock());
}

bool Campaign::isFinished() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return !mLevels.empty() && (getCurrentLevelNoLock() == mLevels.size());
}

bool Campaign::hasProgress() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    for(size_t i = 0; i < mCompleted.size(); ++i)
    {
        if(mCompleted[i])
            return true;
    }
    return false;
}

void Campaign::resetProgress()
{
    {
        std::lock_guard<std::mutex> lock(mMutex);
        mCompleted.assign(mLevels.size(), false);
        mPlayedLevel = mLevels.size();
        mPlayedLevelWon = false;
    }
    saveProgress();
}

void Campaign::startLevel(size_t index)
{
    std::lock_guard<std::mutex> lock(mMutex);
    mActive = true;
    mPlayedLevel = index;
    mPlayedLevelWon = false;
}

void Campaign::stopCampaign()
{
    std::lock_guard<std::mutex> lock(mMutex);
    mActive = false;
    mPlayedLevel = mLevels.size();
    mPlayedLevelWon = false;
}

bool Campaign::isActive() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return mActive;
}

size_t Campaign::getPlayedLevel() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return mPlayedLevel;
}

bool Campaign::getPlayedLevelWon() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return mPlayedLevelWon;
}

void Campaign::clearPlayedLevel()
{
    std::lock_guard<std::mutex> lock(mMutex);
    mPlayedLevel = mLevels.size();
    mPlayedLevelWon = false;
}

bool Campaign::onLevelWon()
{
    {
        std::lock_guard<std::mutex> lock(mMutex);
        if(!mActive || (mPlayedLevel >= mLevels.size()))
            return false;

        mCompleted[mPlayedLevel] = true;
        mPlayedLevelWon = true;
    }
    saveProgress();
    return true;
}
