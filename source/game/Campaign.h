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
#include <cstdint>
#include <iosfwd>
#include <mutex>
#include <string>
#include <vector>

//! \brief One level of the campaign sequence.
//! The level file name is relative to the "levels" directory.
struct CampaignLevel
{
    CampaignLevel():
        mBonus(false)
    {
    }

    std::string mFile;
    std::string mTitle;
    std::string mBriefing;
    std::string mDebriefing;
    //! A bonus (secret) level does not block the main sequence. Finding one
    //! gives a piece of the talisman.
    bool mBonus;
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
//!   Bonus=1 (optional) marks a bonus level.
//!
//! A bonus level is hidden until a level script finds it (action "discover",
//! the level file name as argument). It is not needed to finish the campaign,
//! and each discovered bonus level is one piece of the talisman.
//!
//! Progress file (written by the game):
//!   Completed <index> [<index> ...]
//!   Discovered <index> [<index> ...]
//!   Difficulty <n>   (index of the AI level for the whole campaign, 0 = easy)
//! A level is unlocked when all main levels before it are completed; a bonus
//! level is unlocked when it was discovered. The current
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
    //! \brief First main (non bonus) level not completed. Equals the number of levels if all are done.
    size_t getCurrentLevel() const;
    bool isFinished() const;
    //! \brief A level script found the bonus level with that file name. Only
    //! counts while a campaign level is played. Returns true if it is newly
    //! discovered (progress is saved).
    bool discoverBonusLevel(const std::string& file);
    bool isDiscovered(size_t index) const;
    //! \brief Number of discovered bonus levels (found talisman pieces).
    size_t getTalismanPieces() const;
    //! \brief Number of bonus levels (talisman pieces to find).
    size_t getTalismanTotal() const;
    //! \brief True if the campaign has bonus levels and all were discovered.
    bool isTalismanComplete() const;
    //! \brief True if any level was completed (a campaign can be continued).
    bool hasProgress() const;
    //! \brief Forgets all progress (New Campaign).
    void resetProgress();

    //! \brief AI difficulty of the whole campaign, chosen when a new campaign
    //! is begun. The value is an index into KeeperAIType.
    uint32_t getDifficulty() const;
    //! \brief Sets the difficulty and saves the progress. Values above the
    //! highest AI level are ignored.
    void setDifficulty(uint32_t difficulty);
    //! \brief Default difficulty (normal).
    static uint32_t getDefaultDifficulty();

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
    std::vector<bool> mDiscovered;
    std::string mProgressPath;
    bool mActive;
    size_t mPlayedLevel;
    bool mPlayedLevelWon;
    uint32_t mDifficulty;

    size_t getCurrentLevelNoLock() const;
    bool isUnlockedNoLock(size_t index) const;
};

#endif // CAMPAIGN_H
