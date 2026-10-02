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

#include "ai/KeeperAIType.h"

#include <algorithm>
#include <cmath>
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
    mPlayedLevelWon(false),
    mDifficulty(getDefaultDifficulty())
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

std::vector<CampaignMapBlock> Campaign::parseMapBlocks(const std::string& text)
{
    std::vector<CampaignMapBlock> blocks;
    std::istringstream blockStream(text);
    std::string blockText;
    while(std::getline(blockStream, blockText, ';'))
    {
        std::replace(blockText.begin(), blockText.end(), ',', ' ');
        std::istringstream values(blockText);
        CampaignMapBlock block;
        if(!(values >> block.mX >> block.mY >> block.mWidth >> block.mHeight))
            continue;

        // Blocks outside of the map area are ignored
        if((block.mX < 0.0f) || (block.mY < 0.0f) || (block.mWidth <= 0.0f) || (block.mHeight <= 0.0f)
            || (block.mX + block.mWidth > 100.0f) || (block.mY + block.mHeight > 100.0f))
            continue;

        blocks.push_back(block);
    }
    return blocks;
}

bool Campaign::importDefinition(std::istream& is)
{
    std::lock_guard<std::mutex> lock(mMutex);
    mLevels.clear();
    mCompleted.clear();
    mDiscovered.clear();

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
        else if(key == "Bonus")
            level.mBonus = (value == "1");
        else if(key == "Map")
            level.mMapBlocks = parseMapBlocks(value);
    }

    if(inLevel && !level.mFile.empty())
        mLevels.push_back(level);

    mCompleted.assign(mLevels.size(), false);
    mDiscovered.assign(mLevels.size(), false);
    return !mLevels.empty();
}

bool Campaign::importProgress(std::istream& is)
{
    std::lock_guard<std::mutex> lock(mMutex);
    mCompleted.assign(mLevels.size(), false);
    mDiscovered.assign(mLevels.size(), false);
    mDifficulty = getDefaultDifficulty();

    std::string line;
    while(std::getline(is, line))
    {
        std::istringstream ss(trim(line));
        std::string keyword;
        ss >> keyword;
        if(keyword == "Difficulty")
        {
            uint32_t difficulty;
            if((ss >> difficulty) && (difficulty < static_cast<uint32_t>(KeeperAIType::nbAI)))
                mDifficulty = difficulty;
            continue;
        }
        if((keyword != "Completed") && (keyword != "Discovered"))
            continue;

        std::vector<bool>& target = (keyword == "Completed") ? mCompleted : mDiscovered;
        size_t index;
        while(ss >> index)
        {
            if(index < target.size())
                target[index] = true;
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
    os << "Discovered";
    for(size_t i = 0; i < mDiscovered.size(); ++i)
    {
        if(mDiscovered[i])
            os << " " << i;
    }
    os << "\n";
    os << "Difficulty " << mDifficulty << "\n";
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

std::vector<CampaignMapBlock> Campaign::getMapBlocks(size_t index) const
{
    std::lock_guard<std::mutex> lock(mMutex);
    if(index >= mLevels.size())
        return std::vector<CampaignMapBlock>();

    if(!mLevels[index].mMapBlocks.empty())
        return mLevels[index].mMapBlocks;

    // Automatic grid, left to right and top to bottom
    size_t columns = static_cast<size_t>(std::ceil(std::sqrt(static_cast<double>(mLevels.size()))));
    size_t rows = (mLevels.size() + columns - 1) / columns;
    float cellWidth = 100.0f / static_cast<float>(columns);
    float cellHeight = 100.0f / static_cast<float>(rows);
    CampaignMapBlock block;
    block.mX = static_cast<float>(index % columns) * cellWidth + 2.0f;
    block.mY = static_cast<float>(index / columns) * cellHeight + 2.0f;
    block.mWidth = cellWidth - 4.0f;
    block.mHeight = cellHeight - 4.0f;
    return std::vector<CampaignMapBlock>(1, block);
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
        if(!mCompleted[i] && !mLevels[i].mBonus)
            return i;
    }
    return mCompleted.size();
}

size_t Campaign::getCurrentLevel() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return getCurrentLevelNoLock();
}

bool Campaign::isUnlockedNoLock(size_t index) const
{
    if(index >= mLevels.size())
        return false;

    if(mLevels[index].mBonus)
        return mDiscovered[index] || mCompleted[index];

    // All main levels before the level must be completed
    for(size_t i = 0; i < index; ++i)
    {
        if(!mCompleted[i] && !mLevels[i].mBonus)
            return false;
    }
    return true;
}

bool Campaign::isUnlocked(size_t index) const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return isUnlockedNoLock(index);
}

bool Campaign::discoverBonusLevel(const std::string& file)
{
    {
        std::lock_guard<std::mutex> lock(mMutex);
        if(!mActive)
            return false;

        size_t index = 0;
        while((index < mLevels.size()) && (mLevels[index].mFile != file))
            ++index;

        if((index >= mLevels.size()) || !mLevels[index].mBonus || mDiscovered[index])
            return false;

        mDiscovered[index] = true;
    }
    saveProgress();
    return true;
}

bool Campaign::isDiscovered(size_t index) const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return (index < mDiscovered.size()) && mDiscovered[index];
}

size_t Campaign::getTalismanPieces() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    size_t count = 0;
    for(size_t i = 0; i < mLevels.size(); ++i)
    {
        if(mLevels[i].mBonus && mDiscovered[i])
            ++count;
    }
    return count;
}

size_t Campaign::getTalismanTotal() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    size_t count = 0;
    for(size_t i = 0; i < mLevels.size(); ++i)
    {
        if(mLevels[i].mBonus)
            ++count;
    }
    return count;
}

bool Campaign::isTalismanComplete() const
{
    size_t total = getTalismanTotal();
    return (total > 0) && (getTalismanPieces() == total);
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
        mDiscovered.assign(mLevels.size(), false);
        mPlayedLevel = mLevels.size();
        mPlayedLevelWon = false;
        mDifficulty = getDefaultDifficulty();
    }
    saveProgress();
}

uint32_t Campaign::getDifficulty() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return mDifficulty;
}

void Campaign::setDifficulty(uint32_t difficulty)
{
    if(difficulty >= static_cast<uint32_t>(KeeperAIType::nbAI))
        return;

    {
        std::lock_guard<std::mutex> lock(mMutex);
        mDifficulty = difficulty;
    }
    saveProgress();
}

uint32_t Campaign::getDefaultDifficulty()
{
    return static_cast<uint32_t>(KeeperAIType::normal);
}

void Campaign::startLevel(size_t index)
{
    std::lock_guard<std::mutex> lock(mMutex);
    mActive = true;
    mPlayedLevel = index;
    mPlayedLevelWon = false;
    mLevelSummary.clear();
}

void Campaign::stopCampaign()
{
    std::lock_guard<std::mutex> lock(mMutex);
    mActive = false;
    mPlayedLevel = mLevels.size();
    mPlayedLevelWon = false;
    mLevelSummary.clear();
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
    mLevelSummary.clear();
}

void Campaign::setLevelSummary(const std::string& summary)
{
    std::lock_guard<std::mutex> lock(mMutex);
    // Only a campaign level that is played keeps the numbers
    if(mActive)
        mLevelSummary = summary;
}

std::string Campaign::getLevelSummary() const
{
    std::lock_guard<std::mutex> lock(mMutex);
    return mLevelSummary;
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
