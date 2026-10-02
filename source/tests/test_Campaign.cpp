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

#define BOOST_TEST_MODULE Campaign
#include "BoostTestTargetConfig.h"

#include "game/Campaign.h"

#include <sstream>
#include <string>

static const std::string sample =
    "# comment\n"
    "[Level]\n"
    "File=campaign/One.level\n"
    "Title=First\n"
    "Briefing=Line one\\nLine two\n"
    "Debriefing=Well done\n"
    "[Level]\n"
    "File=campaign/Two.level\n"
    "Title=Second\n"
    "[Level]\n"
    "Title=No file, ignored\n";

BOOST_AUTO_TEST_CASE(test_sequence_and_progress)
{
    Campaign& campaign = Campaign::getSingleton();
    std::istringstream is(sample);
    BOOST_REQUIRE(campaign.importDefinition(is));
    BOOST_REQUIRE_EQUAL(campaign.getNumLevels(), 2u);
    BOOST_CHECK_EQUAL(campaign.getLevel(0).mFile, "campaign/One.level");
    BOOST_CHECK_EQUAL(campaign.getLevel(0).mBriefing, "Line one\nLine two");
    BOOST_CHECK_EQUAL(campaign.getLevel(1).mTitle, "Second");

    // New campaign: only level 1 is unlocked.
    BOOST_CHECK_EQUAL(campaign.getCurrentLevel(), 0u);
    BOOST_CHECK(campaign.isUnlocked(0));
    BOOST_CHECK(!campaign.isUnlocked(1));
    BOOST_CHECK(!campaign.hasProgress());

    // Win level 1: level 2 becomes the current one.
    BOOST_CHECK(!campaign.onLevelWon());
    campaign.startLevel(0);
    BOOST_CHECK(campaign.onLevelWon());
    BOOST_CHECK(campaign.getPlayedLevelWon());
    BOOST_CHECK(campaign.isCompleted(0));
    BOOST_CHECK_EQUAL(campaign.getCurrentLevel(), 1u);
    BOOST_CHECK(campaign.isUnlocked(1));

    // Save and load into a fresh state: continue lands on level 2.
    std::ostringstream os;
    campaign.exportProgress(os);
    std::istringstream is2(sample);
    BOOST_REQUIRE(campaign.importDefinition(is2));
    BOOST_CHECK_EQUAL(campaign.getCurrentLevel(), 0u);
    std::istringstream progress(os.str());
    BOOST_REQUIRE(campaign.importProgress(progress));
    BOOST_CHECK_EQUAL(campaign.getCurrentLevel(), 1u);
    BOOST_CHECK(campaign.hasProgress());
    BOOST_CHECK(!campaign.isFinished());

    // A won level can be replayed.
    BOOST_CHECK(campaign.isUnlocked(0));
}

static const std::string sampleBonus =
    "[Level]\nFile=campaign/One.level\nTitle=First\n"
    "[Level]\nFile=campaign/Bonus.level\nTitle=Hidden\nBonus=1\n"
    "[Level]\nFile=campaign/Two.level\nTitle=Second\n";

BOOST_AUTO_TEST_CASE(test_bonus_levels_and_talisman)
{
    Campaign& campaign = Campaign::getSingleton();
    std::istringstream is(sampleBonus);
    BOOST_REQUIRE(campaign.importDefinition(is));
    BOOST_REQUIRE_EQUAL(campaign.getNumLevels(), 3u);
    BOOST_CHECK(campaign.getLevel(1).mBonus);
    BOOST_CHECK_EQUAL(campaign.getTalismanTotal(), 1u);
    BOOST_CHECK_EQUAL(campaign.getTalismanPieces(), 0u);

    // The bonus level stays hidden when level 1 is completed.
    BOOST_CHECK(!campaign.isUnlocked(1));
    campaign.startLevel(0);
    BOOST_CHECK(campaign.onLevelWon());
    BOOST_CHECK(!campaign.isUnlocked(1));
    // It does not block level 2.
    BOOST_CHECK(campaign.isUnlocked(2));
    BOOST_CHECK_EQUAL(campaign.getCurrentLevel(), 2u);

    // A level script finds it (only for a bonus level of the campaign).
    BOOST_CHECK(!campaign.discoverBonusLevel("campaign/Two.level"));
    BOOST_CHECK(!campaign.discoverBonusLevel("campaign/Unknown.level"));
    BOOST_CHECK(campaign.discoverBonusLevel("campaign/Bonus.level"));
    BOOST_CHECK(!campaign.discoverBonusLevel("campaign/Bonus.level"));
    BOOST_CHECK(campaign.isUnlocked(1));
    BOOST_CHECK_EQUAL(campaign.getTalismanPieces(), 1u);
    BOOST_CHECK(campaign.isTalismanComplete());

    // The discovery is saved.
    std::ostringstream os;
    campaign.exportProgress(os);
    std::istringstream is2(sampleBonus);
    BOOST_REQUIRE(campaign.importDefinition(is2));
    BOOST_CHECK(!campaign.isDiscovered(1));
    std::istringstream progress(os.str());
    BOOST_REQUIRE(campaign.importProgress(progress));
    BOOST_CHECK(campaign.isDiscovered(1));

    // The campaign can be finished without completing the bonus level.
    campaign.startLevel(2);
    campaign.onLevelWon();
    BOOST_CHECK(campaign.isFinished());
}
