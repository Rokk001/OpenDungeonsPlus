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

#define BOOST_TEST_MODULE LevelScript
#include "BoostTestTargetConfig.h"

#include "gamemap/LevelScript.h"

#include <sstream>
#include <string>

static const std::string sample =
    "# comment\n"
    "Flag\tgateOpen\t1\n"
    "[Trigger]\n"
    "Name\tambush\n"
    "Mode\trepeat\t30\n"
    "Cond\ttime\t10\n"
    "Cond\tregion\t1\t20\t21\t25\t26\n"
    "Cond\tcreatures\t1\t>=\t3\n"
    "Cond\troom\t1\tTreasury\t1\n"
    "Cond\tgoal\t1\tClaimNTiles\n"
    "Cond\tflag\tgateOpen\t1\n"
    "Action\tmessage\t-1\tThey are coming, keeper.\n"
    "Action\tobjective\t1\tDefend the heart\n"
    "Action\tspawn\t0\t30\t30\t1\tKnight:2\tArcher:1\n"
    "Action\tgold\t1\t500\n"
    "Action\tsetflag\tambushDone\t1\n"
    "Action\twin\t1\n"
    "Action\tlose\t2\n"
    "State\t2\t120\n"
    "[/Trigger]\n"
    "[Trigger]\n"
    "Name\tsecond\n"
    "Mode\tonce\n"
    "Cond\tflag\tambushDone\t1\n"
    "Action\tmessage\t1\tDone\n"
    "[/Trigger]\n"
    "[/Triggers]\n";

BOOST_AUTO_TEST_CASE(test_parse)
{
    LevelScript script;
    std::istringstream is(sample);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_REQUIRE_EQUAL(script.getTriggers().size(), 2u);
    BOOST_CHECK_EQUAL(script.getFlag("gateOpen"), 1);
    BOOST_CHECK_EQUAL(script.getFlag("unknown"), 0);

    const LevelScriptTrigger& t = script.getTriggers()[0];
    BOOST_CHECK_EQUAL(t.mName, "ambush");
    BOOST_CHECK(t.mRepeat);
    BOOST_CHECK_EQUAL(t.mCooldownSeconds, 30);
    BOOST_REQUIRE_EQUAL(t.mConditions.size(), 6u);
    BOOST_REQUIRE_EQUAL(t.mActions.size(), 7u);
    BOOST_CHECK_EQUAL(t.mTimesFired, 2u);
    BOOST_CHECK_EQUAL(t.mLastFiredTurn, 120);

    BOOST_CHECK(t.mConditions[1].mType == LevelScriptConditionType::region);
    BOOST_CHECK_EQUAL(t.mConditions[1].mX1, 20);
    BOOST_CHECK_EQUAL(t.mConditions[1].mY2, 26);
    BOOST_CHECK(t.mConditions[2].mAtLeast);
    BOOST_CHECK_EQUAL(t.mConditions[3].mName, "Treasury");

    BOOST_CHECK_EQUAL(t.mActions[0].mText, "They are coming, keeper.");
    BOOST_CHECK_EQUAL(t.mActions[0].mSeatId, -1);
    BOOST_REQUIRE_EQUAL(t.mActions[2].mCreatures.size(), 2u);
    BOOST_CHECK_EQUAL(t.mActions[2].mCreatures[0].first, "Knight");
    BOOST_CHECK_EQUAL(t.mActions[2].mCreatures[0].second, 2u);
    BOOST_CHECK_EQUAL(t.mActions[2].mTargetSeatId, 1);
    BOOST_CHECK_EQUAL(script.getTriggers()[1].mTimesFired, 0u);
}

BOOST_AUTO_TEST_CASE(test_roundtrip)
{
    LevelScript script;
    std::istringstream is(sample);
    BOOST_REQUIRE(script.importFromStream(is));

    std::ostringstream os;
    script.exportToStream(os);

    // The tag has to be consumed by the level reader before the import
    std::string written = os.str();
    BOOST_REQUIRE_EQUAL(written.compare(0, 11, "[Triggers]\n"), 0);

    LevelScript script2;
    std::istringstream is2(written.substr(11));
    BOOST_REQUIRE(script2.importFromStream(is2));

    std::ostringstream os2;
    script2.exportToStream(os2);
    BOOST_CHECK_EQUAL(written, os2.str());
}

BOOST_AUTO_TEST_CASE(test_invalid)
{
    const char* invalid[] = {
        // Unknown condition
        "[Trigger]\nName\tx\nCond\tmoon\t1\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // No action
        "[Trigger]\nName\tx\nCond\ttime\t1\n[/Trigger]\n[/Triggers]\n",
        // Missing argument
        "[Trigger]\nName\tx\nCond\tregion\t1\t2\t3\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // Bad creature entry
        "[Trigger]\nName\tx\nCond\ttime\t1\nAction\tspawn\t0\t1\t1\t-1\tKnight\n[/Trigger]\n[/Triggers]\n",
        // Missing end tag
        "[Trigger]\nName\tx\nCond\ttime\t1\nAction\twin\t1\n[/Trigger]\n",
        // Not a number
        "[Trigger]\nName\tx\nCond\ttime\tsoon\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n"
    };

    for(const char* text : invalid)
    {
        LevelScript script;
        std::istringstream is(text);
        BOOST_CHECK_MESSAGE(!script.importFromStream(is), text);
    }
}

BOOST_AUTO_TEST_CASE(test_empty)
{
    LevelScript script;
    std::istringstream is("[/Triggers]\n");
    BOOST_CHECK(script.importFromStream(is));
    BOOST_CHECK(script.isEmpty());
}
