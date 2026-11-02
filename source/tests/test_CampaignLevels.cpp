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

#define BOOST_TEST_MODULE CampaignLevels
#include "BoostTestTargetConfig.h"

#include "game/Campaign.h"

#include <sstream>
#include <string>

static const std::string definition =
    "[Level]\n"
    "File=campaign/One.level\n"
    "Title=First\n";

//! \brief Hell stays locked until the campaign was finished on hard; the finished set is saved and read again,
//! an old progress file without it loads with nothing finished, and a new campaign keeps the set.
BOOST_AUTO_TEST_CASE(test_hell_unlock_and_finished_set)
{
    Campaign& campaign = Campaign::getSingleton();
    std::istringstream def(definition);
    BOOST_REQUIRE(campaign.importDefinition(def));

    // An old progress file without the Finished line: nothing finished, Hell locked.
    std::istringstream old("Completed\nDiscovered\nDifficulty 1\n");
    BOOST_REQUIRE(campaign.importProgress(old));
    BOOST_CHECK(!campaign.isHellUnlocked());

    // Finished on normal does not unlock Hell, finished on hard does.
    std::istringstream normalOnly("Completed 0\nDiscovered\nDifficulty 1\nFinished normal\n");
    BOOST_REQUIRE(campaign.importProgress(normalOnly));
    BOOST_CHECK(!campaign.isHellUnlocked());
    std::istringstream hard("Completed 0\nDiscovered\nDifficulty 2\nFinished normal hard\n");
    BOOST_REQUIRE(campaign.importProgress(hard));
    BOOST_CHECK(campaign.isHellUnlocked());

    // The finished set survives an export and import.
    std::ostringstream out;
    campaign.exportProgress(out);
    std::istringstream again(out.str());
    BOOST_REQUIRE(campaign.importProgress(again));
    BOOST_CHECK(campaign.isHellUnlocked());

    // Starting a new campaign keeps the finished set.
    campaign.resetProgress();
    BOOST_CHECK(campaign.isHellUnlocked());
}
