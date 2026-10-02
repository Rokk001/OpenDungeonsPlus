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

#ifndef CAMPAIGN_H
#define CAMPAIGN_H

#include <cstddef>
#include <iosfwd>
#include <mutex>
#include <string>
#include <vector>

//! \brief One level of the campaign sequence.
//! The level file name is relative to the "levels" directory.
struct CampaignLevel
{
    std::string mFile;
    std::string mTitle;
    std::string mBriefing;
    std::string mDebriefing;
};

//! \brief The campaign: an ordered list of levels plus the saved progress.
//!
//! Definition file (levels/campaign/Campaign.cfg), one setting per line:
//!   # comment
//!   [Level]
//!   File=campaign/Level1.level
//!   Title=Some title
//!   Briefing=Text shown before the level. "\n" starts a new line.
//!   Debriefing=Text shown after the level was won.
//!
//! Progress file (written by the game):
//!   Completed <index> [<index> ...]
//! A level is unlocked when all levels before it are completed. The current
//! level is the first level that is not completed yet.
//!
//! The campaign is a process wide singleton because the single player server
//! (which detects the victory) and the menu (which shows the result) live in
//! the same process.
class Campaign
{
public:
    static Campaign& getSingleton();

    //! \brief Reads the level sequence. Returns false if no level was found.
    bool importDefinition(std::istream& is);
    //! \brief Reads the saved progress. Unknown or out of range indices are ignored.
    bool importProgress(std::istream& is);
    void exportProgress(std::ostream& os) const;

    //! \brief Sets the file the progress is written to by saveProgress() and
    //! onLevelWon(). Without a path nothing is written.
    void setProgressPath(const std::string& path);
    bool saveProgress() const;

    size_t getNumLevels() const;
    const CampaignLevel& getLevel(size_t index) const;
    bool isCompleted(size_t index) const;
    bool isUnlocked(size_t index) const;
    //! \brief First level not completed. Equals the number of levels if all are done.
    size_t getCurrentLevel() const;
    bool isFinished() const;
    //! \brief True if any level was completed (a campaign can be continued).
    bool hasProgress() const;
    //! \brief Forgets all progress (New Campaign).
    void resetProgress();

    //! \brief A campaign level was started from the campaign menu.
    void startLevel(size_t index);
    //! \brief Leaving the campaign (the main menu is shown).
    void stopCampaign();
    bool isActive() const;
    //! \brief The level that was started last, or getNumLevels() if none.
    size_t getPlayedLevel() const;
    bool getPlayedLevelWon() const;
    //! \brief Clears the "last played" result once the menu has shown it.
    void clearPlayedLevel();

    //! \brief Called by the server when a human seat completed all its goals.
    //! Marks the played level as completed and saves the progress.
    //! Returns true if a campaign level was won.
    bool onLevelWon();

    //! \brief Replaces "\n" (backslash, n) by a line feed.
    static std::string unescapeText(const std::string& text);

private:
    Campaign();

    mutable std::mutex mMutex;
    std::vector<CampaignLevel> mLevels;
    std::vector<bool> mCompleted;
    std::string mProgressPath;
    bool mActive;
    size_t mPlayedLevel;
    bool mPlayedLevelWon;

    size_t getCurrentLevelNoLock() const;
};

#endif // CAMPAIGN_H
