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

#include <cstdlib>
#include <fstream>
#include <set>
#include <sstream>
#include <string>

//! \brief Keeps exact ground endpoints and room footprints stable through parsing and saving.
BOOST_AUTO_TEST_CASE(exact_ground_and_room_footprint_condition_round_trip)
{
    const std::string text =
        "[Trigger]\nName exactDisplay\nMode once\n"
        "Cond groundconnected 1 13 57 40 22\n"
        "Cond roomclaimed 1 44 106 47 107\n"
        "Action objectivestate 1 task reached\n[/Trigger]\n[/Triggers]\n";
    LevelScript script;
    std::istringstream input(text);
    BOOST_REQUIRE(script.importFromStream(input));
    const std::vector<LevelScriptCondition>& conditions = script.getTriggers()[0].mConditions;
    BOOST_REQUIRE_EQUAL(conditions.size(), 2);
    BOOST_CHECK(conditions[0].mType == LevelScriptConditionType::groundConnected);
    BOOST_CHECK_EQUAL(conditions[0].mX1, 13);
    BOOST_CHECK_EQUAL(conditions[0].mY1, 57);
    BOOST_CHECK_EQUAL(conditions[0].mX2, 40);
    BOOST_CHECK_EQUAL(conditions[0].mY2, 22);
    BOOST_CHECK(conditions[1].mType == LevelScriptConditionType::roomFootprintClaimed);
    BOOST_CHECK_EQUAL(conditions[1].mX1, 44);
    BOOST_CHECK_EQUAL(conditions[1].mY1, 106);
    BOOST_CHECK_EQUAL(conditions[1].mX2, 47);
    BOOST_CHECK_EQUAL(conditions[1].mY2, 107);
    std::ostringstream output;
    script.exportToStream(output);
    LevelScript loaded;
    std::istringstream saved(output.str().substr(output.str().find('\n') + 1));
    BOOST_REQUIRE(loaded.importFromStream(saved));
    std::ostringstream again;
    loaded.exportToStream(again);
    BOOST_CHECK_EQUAL(output.str(), again.str());
}

//! \brief Rejects missing or negative ground coordinates and room-mask seats.
BOOST_AUTO_TEST_CASE(invalid_ground_and_room_footprint_conditions)
{
    const char* conditions[] = {
        "Cond groundconnected 1 13 57 40", "Cond groundconnected 1 -1 57 40 22",
        "Cond groundconnected -1 13 57 40 22", "Cond roomclaimed 1 44 106 47",
        "Cond roomclaimed 1 44 106 47 -1", "Cond roomclaimed -1 44 106 47 107"
    };
    for(const char* condition : conditions)
    {
        LevelScript script;
        std::istringstream input(std::string("[Trigger]\nName invalid\nMode once\n") +
            condition + "\nAction hint 1 text\n[/Trigger]\n[/Triggers]\n");
        BOOST_CHECK(!script.importFromStream(input));
    }
}

//! \brief Preserves exact regional gold credits and actual named death locations through save/load.
BOOST_AUTO_TEST_CASE(regional_mining_and_death_position_history)
{
    const std::string text =
        "Region Block 10 10 20 20\nRegion Road 30 30 35 35\n"
        "[Trigger]\nName regional\nMode once\n"
        "Cond minedregion 1 Block >= 600\nCond killedin Warden Road\n"
        "Action hint 1 Observed only.\n[/Trigger]\n[/Triggers]\n";
    LevelScript script;
    std::istringstream input(text);
    BOOST_REQUIRE(script.importFromStream(input));
    BOOST_CHECK_EQUAL(script.getGoldMinedInRegion(1, "Block"), 0);
    script.observeGoldMined(1, 9, 10, 900);
    script.observeGoldMined(2, 10, 10, 900);
    script.observeGoldMined(1, 10, 10, 37);
    script.observeGoldMined(1, 20, 20, 563);
    script.observeGoldMined(1, 15, 15, 0);
    BOOST_CHECK_EQUAL(script.getGoldMinedInRegion(1, "Block"), 600);
    BOOST_CHECK_EQUAL(script.getGoldMinedInRegion(2, "Block"), 0);
    BOOST_CHECK(!script.wasCreatureKilledInRegion("Warden", "Road"));
    script.observeCreatureDeath("Warden", 29, 30);
    BOOST_CHECK(!script.wasCreatureKilledInRegion("Warden", "Road"));
    script.observeCreatureDeath("Warden", 30, 30);
    BOOST_CHECK(script.wasCreatureKilledInRegion("Warden", "Road"));
    BOOST_CHECK(!script.wasCreatureKilledInRegion("Warden", "Block"));
    BOOST_CHECK(!script.wasCreatureKilledInRegion("Unknown", "Road"));
    std::ostringstream output;
    script.exportToStream(output);
    LevelScript loaded;
    std::istringstream saved(output.str().substr(output.str().find('\n') + 1));
    BOOST_REQUIRE(loaded.importFromStream(saved));
    BOOST_CHECK_EQUAL(loaded.getGoldMinedInRegion(1, "Block"), 600);
    BOOST_CHECK(loaded.wasCreatureKilledInRegion("Warden", "Road"));
    std::ostringstream again;
    loaded.exportToStream(again);
    BOOST_CHECK_EQUAL(output.str(), again.str());
    loaded.clear();
    BOOST_CHECK(loaded.isEmpty());
    BOOST_CHECK(!loaded.wasCreatureKilledInRegion("Warden", "Road"));
}

//! \brief Rejects malformed regional observation records and predicates.
BOOST_AUTO_TEST_CASE(invalid_regional_observation_records)
{
    const char* records[] = {
        "MinedGold 1 10 10 -1\n[/Triggers]\n", "MinedGold -1 10 10 10\n[/Triggers]\n",
        "MinedGold 1 -1 10 10\n[/Triggers]\n", "DeathTile Warden -1 0\n[/Triggers]\n",
        "[Trigger]\nName x\nCond minedregion 1 Block >= -1\nAction hint 1 text\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName x\nCond killedin Warden\nAction hint 1 text\n[/Trigger]\n[/Triggers]\n"
    };
    for(const char* record : records)
    {
        LevelScript script;
        std::istringstream input(record);
        BOOST_CHECK(!script.importFromStream(input));
    }
}

//! \brief Tracks every actual source instance, including death location, reused names and saved history.
BOOST_AUTO_TEST_CASE(observed_spawn_death_history_round_trip)
{
    const std::string text =
        "[Trigger]\nName wave\nMode once\nCond time 0\nAction spawn 3 1 1 1 Knight:1\n[/Trigger]\n"
        "[Trigger]\nName status\nMode once\nCond spawncleared wave 0 atheart 1\n"
        "Cond trapgone DoorWooden1\nCond objective 1 route open\nCond trigger wave 0\n"
        "Action objectivestate 1 wave reached\n[/Trigger]\n[/Triggers]\n";
    LevelScript script;
    std::istringstream input(text);
    BOOST_REQUIRE(script.importFromStream(input));
    BOOST_CHECK(!script.areSpawnsCleared("wave", 0, 1));
    script.observeSpawn("wave", 0, "First");
    script.observeSpawn("wave", 0, "Second");
    script.observeSpawnDeath("First", 1);
    BOOST_CHECK(!script.areSpawnsCleared("wave", 0, 1));
    script.observeSpawnDeath("Second", 1);
    BOOST_CHECK(script.areSpawnsCleared("wave", 0, 1));
    BOOST_CHECK(!script.areSpawnsCleared("wave", 0, 2));
    BOOST_CHECK(!script.areSpawnsCleared("wave", 1, 1));
    script.observeSpawn("wave", 0, "First");
    BOOST_CHECK(!script.areSpawnsCleared("wave", 0, -1));
    script.observeSpawnDeath("First", -1);
    BOOST_CHECK(script.areSpawnsCleared("wave", 0, -1));
    BOOST_CHECK(!script.areSpawnsCleared("wave", 0, 1));
    std::ostringstream output;
    script.exportToStream(output);
    LevelScript loaded;
    std::istringstream saved(output.str().substr(output.str().find('\n') + 1));
    BOOST_REQUIRE(loaded.importFromStream(saved));
    BOOST_CHECK(loaded.areSpawnsCleared("wave", 0, -1));
    BOOST_CHECK(!loaded.areSpawnsCleared("wave", 0, 1));
    std::ostringstream again;
    loaded.exportToStream(again);
    BOOST_CHECK_EQUAL(output.str(), again.str());
    loaded.clear();
    BOOST_CHECK(loaded.isEmpty());
    BOOST_CHECK(!loaded.areSpawnsCleared("wave", 0, -1));
}

//! \brief Rejects malformed source identities, death records and negative trigger-history selectors.
BOOST_AUTO_TEST_CASE(invalid_spawn_observation_records)
{
    const char* records[] = {
        "SpawnObservation wave -1 name 1 1\n[/Triggers]\n",
        "SpawnObservation wave 0 name 2 1\n[/Triggers]\n",
        "SpawnObservation wave 0 name 0 1\n[/Triggers]\n",
        "SpawnObservation wave 0 name 1 -2\n[/Triggers]\n",
        "[Trigger]\nName x\nCond spawncleared wave -1\nAction hint 1 text\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName x\nCond spawncleared wave 0 atheart -1\nAction hint 1 text\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName x\nCond trigger wave 2\nAction hint 1 text\n[/Trigger]\n[/Triggers]\n"
    };
    for(const char* record : records)
    {
        LevelScript script;
        std::istringstream input(record);
        BOOST_CHECK(!script.importFromStream(input));
    }
}

//! \brief Preserves advice without objective IDs and round-trips read-only presentation predicates.
BOOST_AUTO_TEST_CASE(hint_and_precise_presentation_condition_round_trip)
{
    const std::string text =
        "[Trigger]\nName advice\nMode once\nCond time 0\n"
        "Action hint 1 Build before you march.\n[/Trigger]\n"
        "[Trigger]\nName displayOnly\nMode once\n"
        "Cond objective 1 gate reached\nCond objective 1 route failed\n"
        "Cond goalmet 1 KillAllEnemies\nCond creaturesatheart 1 >= 12\n"
        "Cond trigger advice\nAction objectivestate 1 finale reached\n"
        "[/Trigger]\n[/Triggers]\n";
    LevelScript script;
    std::istringstream input(text);
    BOOST_REQUIRE(script.importFromStream(input));
    const LevelScriptAction& hint = script.getTriggers()[0].mActions[0];
    BOOST_CHECK(hint.mType == LevelScriptActionType::hint);
    BOOST_CHECK(hint.mObjectiveId.empty());
    BOOST_CHECK_EQUAL(hint.mText, "Build before you march.");
    const std::vector<LevelScriptCondition>& conditions = script.getTriggers()[1].mConditions;
    BOOST_REQUIRE_EQUAL(conditions.size(), 5);
    BOOST_CHECK(conditions[0].mType == LevelScriptConditionType::objectiveState);
    BOOST_CHECK_EQUAL(conditions[0].mName, "gate");
    BOOST_CHECK_EQUAL(conditions[0].mNumber, static_cast<int64_t>(LevelScriptObjectiveState::reached));
    BOOST_CHECK_EQUAL(conditions[1].mNumber, static_cast<int64_t>(LevelScriptObjectiveState::failed));
    BOOST_CHECK(conditions[2].mType == LevelScriptConditionType::goalMet);
    BOOST_CHECK_EQUAL(conditions[2].mName, "KillAllEnemies");
    BOOST_CHECK(conditions[3].mType == LevelScriptConditionType::creaturesAtHeart);
    BOOST_CHECK_EQUAL(conditions[3].mNumber, 12);
    BOOST_CHECK(conditions[4].mType == LevelScriptConditionType::triggerFired);
    BOOST_CHECK_EQUAL(conditions[4].mName, "advice");
    std::ostringstream output;
    script.exportToStream(output);
    BOOST_CHECK(output.str().find("Action\thint\t1\tBuild before you march.") != std::string::npos);
    LevelScript loaded;
    std::istringstream saved(output.str().substr(output.str().find('\n') + 1));
    BOOST_REQUIRE(loaded.importFromStream(saved));
    std::ostringstream again;
    loaded.exportToStream(again);
    BOOST_CHECK_EQUAL(output.str(), again.str());
}

//! \brief Rejects incomplete advice and malformed exact-presentation condition syntax.
BOOST_AUTO_TEST_CASE(invalid_hint_and_presentation_conditions)
{
    const char* bodies[] = {
        "Cond time 0\nAction hint 1",
        "Cond objective 1 gate maybe\nAction hint 1 advice",
        "Cond objective -1 gate reached\nAction hint 1 advice",
        "Cond creaturesatheart 1 >= -1\nAction hint 1 advice",
        "Cond goalmet 1\nAction hint 1 advice",
        "Cond trigger\nAction hint 1 advice"
    };
    for(const char* body : bodies)
    {
        LevelScript script;
        std::istringstream input(std::string("[Trigger]\nName invalid\nMode once\n") +
            body + "\n[/Trigger]\n[/Triggers]\n");
        BOOST_CHECK(!script.importFromStream(input));
    }
}

//! \brief Checks identified objectives, explicit seat state, legacy syntax and saved-state round trips.
BOOST_AUTO_TEST_CASE(identified_objective_state_round_trip)
{
    const std::string text =
        "[Trigger]\nName goals\nMode once\nCond time 0\n"
        "Action objective 1 Keep the old text\n"
        "Action objectiveid 1 heart Hold the heart\n"
        "Action objectivestate 1 heart reached\n"
        "Action objectivestate 2 heart failed\n"
        "[/Trigger]\n[/Triggers]\n";
    LevelScript script;
    std::istringstream input(text);
    BOOST_REQUIRE(script.importFromStream(input));
    const std::vector<LevelScriptAction>& actions = script.getTriggers()[0].mActions;
    BOOST_CHECK(actions[0].mObjectiveId.empty());
    BOOST_CHECK_EQUAL(actions[0].mText, "Keep the old text");
    BOOST_CHECK_EQUAL(actions[1].mObjectiveId, "heart");
    BOOST_CHECK_EQUAL(actions[1].mText, "Hold the heart");
    BOOST_CHECK(actions[2].mType == LevelScriptActionType::objectiveState);
    BOOST_CHECK(script.getObjectiveState(1, "heart") == LevelScriptObjectiveState::open);
    script.setObjectiveState(1, "heart", LevelScriptObjectiveState::reached);
    script.setObjectiveState(2, "heart", LevelScriptObjectiveState::failed);
    BOOST_CHECK(script.getObjectiveState(1, "heart") == LevelScriptObjectiveState::reached);
    BOOST_CHECK(script.getObjectiveState(2, "heart") == LevelScriptObjectiveState::failed);
    BOOST_CHECK(script.getObjectiveState(3, "heart") == LevelScriptObjectiveState::open);
    std::ostringstream output;
    script.exportToStream(output);
    BOOST_CHECK(output.str().find("Action\tobjective\t1\tKeep the old text") != std::string::npos);
    BOOST_CHECK(output.str().find("Action\tobjectiveid\t1\theart\tHold the heart") != std::string::npos);
    LevelScript loaded;
    std::istringstream saved(output.str().substr(output.str().find('\n') + 1));
    BOOST_REQUIRE(loaded.importFromStream(saved));
    BOOST_CHECK(loaded.getObjectiveState(1, "heart") == LevelScriptObjectiveState::reached);
    BOOST_CHECK(loaded.getObjectiveState(2, "heart") == LevelScriptObjectiveState::failed);
    std::ostringstream again;
    loaded.exportToStream(again);
    BOOST_CHECK_EQUAL(output.str(), again.str());
    loaded.clear();
    BOOST_CHECK(loaded.isEmpty());
    BOOST_CHECK(loaded.getObjectiveState(1, "heart") == LevelScriptObjectiveState::open);
}

//! \brief Rejects malformed IDs and state words without changing legacy objective parsing.
BOOST_AUTO_TEST_CASE(identified_objective_invalid_state)
{
    const char* actions[] = {
        "Action objectiveid 1 heart", "Action objectivestate 1 heart maybe",
        "Action objectivestate 1 heart open", "Action objectivestate 1 heart",
        "Action objectiveid bad heart Text"
    };
    for(const char* action : actions)
    {
        LevelScript script;
        std::istringstream input(std::string("[Trigger]\nName x\nMode once\nCond time 0\n") +
            action + "\n[/Trigger]\n[/Triggers]\n");
        BOOST_CHECK(!script.importFromStream(input));
    }
    LevelScript script;
    std::istringstream input("ObjectiveState 1 heart maybe\n[/Triggers]\n");
    BOOST_CHECK(!script.importFromStream(input));
}

static const std::string sample =
    "# comment\n"
    "Flag\tgateOpen\t1\n"
    "TimeLimit\t300\n"
    "Region\tGate\t30\t12\t28\t10\n"
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
    "[Trigger]\n"
    "Name\tgateWatch\n"
    "Mode\tonce\n"
    "Cond\tregion\t1\tGate\n"
    "Cond\tgold\t1\t>=\t500\n"
    "Cond\tmana\t1\t<=\t100\n"
    "Cond\tkills\t1\t>=\t7\n"
    "Cond\tmined\t1\t>=\t900\n"
    "Cond\tclaimed\t1\tGate\t4\n"
    "Cond\tclaimed\t2\tGate\tall\n"
    "Action\treveal\t1\tGate\n"
    "Action\taddflag\tvisits\t-2\n"
    "[/Trigger]\n"
    "[Trigger]\n"
    "Name\tunlock\n"
    "Mode\tonce\n"
    "Cond\tflag\tvisits\t-2\n"
    "Action\tmake\t1\troomHatchery\n"
    "Action\ttimelimit\t120\n"
    "[/Trigger]\n"
    "[Trigger]\n"
    "Name\tcreatureEvents\n"
    "Mode\tonce\n"
    "Cond\thappy\t1\t>=\t2\n"
    "Cond\tangry\t1\t<=\t0\n"
    "Cond\tatlevel\t1\t3\t>=\t2\n"
    "Cond\tlost\t1\t>=\t1\n"
    "Cond\tpickedup\t1\t>=\t4\n"
    "Cond\tdropped\t1\t>=\t3\n"
    "Cond\tslapped\t1\t<=\t5\n"
    "Action\tmessage\t1\tEvents\n"
    "[/Trigger]\n"
    "[/Triggers]\n";

BOOST_AUTO_TEST_CASE(test_parse)
{
    LevelScript script;
    std::istringstream is(sample);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_REQUIRE_EQUAL(script.getTriggers().size(), 5u);
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

    BOOST_REQUIRE_EQUAL(script.getRegions().size(), 1u);
    const LevelScriptTrigger& watch = script.getTriggers()[2];
    BOOST_CHECK_EQUAL(watch.mConditions[0].mName, "Gate");
    BOOST_CHECK(watch.mActions[0].mType == LevelScriptActionType::reveal);
    BOOST_CHECK_EQUAL(watch.mActions[0].mText, "Gate");

    BOOST_REQUIRE_EQUAL(watch.mConditions.size(), 7u);
    BOOST_CHECK(watch.mConditions[1].mType == LevelScriptConditionType::gold);
    BOOST_CHECK(watch.mConditions[1].mAtLeast);
    BOOST_CHECK_EQUAL(watch.mConditions[1].mNumber, 500);
    BOOST_CHECK(watch.mConditions[2].mType == LevelScriptConditionType::mana);
    BOOST_CHECK(!watch.mConditions[2].mAtLeast);
    BOOST_CHECK(watch.mConditions[3].mType == LevelScriptConditionType::kills);
    BOOST_CHECK_EQUAL(watch.mConditions[3].mNumber, 7);
    BOOST_CHECK(watch.mConditions[4].mType == LevelScriptConditionType::goldMined);
    BOOST_CHECK_EQUAL(watch.mConditions[5].mNumber, 4);
    BOOST_CHECK_EQUAL(watch.mConditions[6].mNumber, -1);
    BOOST_REQUIRE_EQUAL(watch.mActions.size(), 2u);
    BOOST_CHECK(watch.mActions[1].mType == LevelScriptActionType::addFlag);
    BOOST_CHECK_EQUAL(watch.mActions[1].mNumber, -2);

    const LevelScriptTrigger& unlock = script.getTriggers()[3];
    BOOST_REQUIRE_EQUAL(unlock.mActions.size(), 2u);
    BOOST_CHECK(unlock.mActions[0].mType == LevelScriptActionType::make);
    BOOST_CHECK_EQUAL(unlock.mActions[0].mSeatId, 1);
    BOOST_CHECK_EQUAL(unlock.mActions[0].mText, "roomHatchery");
    BOOST_REQUIRE_EQUAL(unlock.mActions.size(), 2u);
    BOOST_CHECK(unlock.mActions[1].mType == LevelScriptActionType::timeLimit);
    BOOST_CHECK_EQUAL(unlock.mActions[1].mNumber, 120);

    const LevelScriptTrigger& events = script.getTriggers()[4];
    BOOST_REQUIRE_EQUAL(events.mConditions.size(), 7u);
    BOOST_CHECK(events.mConditions[0].mType == LevelScriptConditionType::happyCreatures);
    BOOST_CHECK(events.mConditions[0].mAtLeast);
    BOOST_CHECK_EQUAL(events.mConditions[0].mNumber, 2);
    BOOST_CHECK(events.mConditions[1].mType == LevelScriptConditionType::angryCreatures);
    BOOST_CHECK(!events.mConditions[1].mAtLeast);
    BOOST_CHECK(events.mConditions[2].mType == LevelScriptConditionType::creaturesAtLevel);
    BOOST_CHECK_EQUAL(events.mConditions[2].mSeatId, 1);
    BOOST_CHECK_EQUAL(events.mConditions[2].mX1, 3);
    BOOST_CHECK(events.mConditions[2].mAtLeast);
    BOOST_CHECK_EQUAL(events.mConditions[2].mNumber, 2);
    BOOST_CHECK(events.mConditions[3].mType == LevelScriptConditionType::creaturesLost);
    BOOST_CHECK(events.mConditions[4].mType == LevelScriptConditionType::creaturesPickedUp);
    BOOST_CHECK_EQUAL(events.mConditions[4].mNumber, 4);
    BOOST_CHECK(events.mConditions[5].mType == LevelScriptConditionType::creaturesDropped);
    BOOST_CHECK(events.mConditions[6].mType == LevelScriptConditionType::creaturesSlapped);
    BOOST_CHECK(!events.mConditions[6].mAtLeast);
}

BOOST_AUTO_TEST_CASE(test_time_limit)
{
    LevelScript script;
    BOOST_CHECK_EQUAL(script.getTimeLimitSeconds(), LevelScript::TIME_LIMIT_NOT_SET);
    BOOST_CHECK(script.isEmpty());

    std::istringstream is(sample);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_CHECK_EQUAL(script.getTimeLimitSeconds(), 300);

    // A saved game counts the limit from its new start, which is later than the old one
    script.rebaseTimeLimit(100);
    BOOST_CHECK_EQUAL(script.getTimeLimitSeconds(), 200);
    script.rebaseTimeLimit(500);
    BOOST_CHECK_EQUAL(script.getTimeLimitSeconds(), 0);

    // No limit and a removed limit stay what they are
    script.setTimeLimitSeconds(LevelScript::TIME_LIMIT_REMOVED);
    script.rebaseTimeLimit(10);
    BOOST_CHECK_EQUAL(script.getTimeLimitSeconds(), LevelScript::TIME_LIMIT_REMOVED);
    script.setTimeLimitSeconds(LevelScript::TIME_LIMIT_NOT_SET);
    script.rebaseTimeLimit(10);
    BOOST_CHECK_EQUAL(script.getTimeLimitSeconds(), LevelScript::TIME_LIMIT_NOT_SET);

    // The limit alone is a script worth writing, and it survives the round trip
    LevelScript onlyLimit;
    onlyLimit.setTimeLimitSeconds(42);
    BOOST_CHECK(!onlyLimit.isEmpty());
    std::ostringstream os;
    onlyLimit.exportToStream(os);
    std::string written = os.str();
    BOOST_REQUIRE_EQUAL(written.compare(0, 11, "[Triggers]\n"), 0);
    LevelScript again;
    std::istringstream is2(written.substr(11));
    BOOST_REQUIRE(again.importFromStream(is2));
    BOOST_CHECK_EQUAL(again.getTimeLimitSeconds(), 42);

    again.clear();
    BOOST_CHECK_EQUAL(again.getTimeLimitSeconds(), LevelScript::TIME_LIMIT_NOT_SET);
}

BOOST_AUTO_TEST_CASE(test_regions)
{
    LevelScript script;
    std::istringstream is(sample);
    BOOST_REQUIRE(script.importFromStream(is));

    // The corners may be given in any order
    const LevelScriptRegion* gate = script.getRegion("Gate");
    BOOST_REQUIRE(gate != nullptr);
    BOOST_CHECK(gate->contains(29, 11));
    BOOST_CHECK(gate->contains(28, 10));
    BOOST_CHECK(gate->contains(30, 12));
    BOOST_CHECK(!gate->contains(31, 11));
    BOOST_CHECK_EQUAL(script.getRegionNameAt(29, 11), "Gate");
    BOOST_CHECK_EQUAL(script.getRegionNameAt(0, 0), "");
    BOOST_CHECK(script.getRegion("Missing") == nullptr);

    BOOST_CHECK_EQUAL(script.getFreeRegionName(), "Region1");
    script.setRegion(LevelScriptRegion("Region1", 1, 2, 3, 4));
    BOOST_CHECK_EQUAL(script.getFreeRegionName(), "Region2");

    // Same name: the region is moved, not duplicated
    script.setRegion(LevelScriptRegion("Gate", 5, 5, 6, 6));
    BOOST_CHECK_EQUAL(script.getRegions().size(), 2u);
    BOOST_CHECK(!script.getRegion("Gate")->contains(29, 11));

    BOOST_CHECK(script.removeRegion("Region1"));
    BOOST_CHECK(!script.removeRegion("Region1"));
    BOOST_CHECK_EQUAL(script.getRegions().size(), 1u);

    // A level with markers and no triggers must still be written
    LevelScript onlyRegion;
    onlyRegion.setRegion(LevelScriptRegion("A", 0, 0, 1, 1));
    BOOST_CHECK(!onlyRegion.isEmpty());
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
        "[Trigger]\nName\tx\nCond\ttime\tsoon\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // Nothing to claim
        "[Trigger]\nName\tx\nCond\tclaimed\t1\tGate\t0\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // Wrong comparison
        "[Trigger]\nName\tx\nCond\tgold\t1\t=\t5\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // Region with a missing corner value
        "Region\tA\t1\t2\t3\n[/Triggers]\n",
        // Region inside a trigger
        "[Trigger]\nName\tx\nRegion\tA\t1\t2\t3\t4\nCond\ttime\t1\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // reveal without a region name
        "[Trigger]\nName\tx\nCond\ttime\t1\nAction\treveal\t1\n[/Trigger]\n[/Triggers]\n",
        // atlevel without a level
        "[Trigger]\nName\tx\nCond\tatlevel\t1\t>=\t2\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // atlevel with level 0
        "[Trigger]\nName\tx\nCond\tatlevel\t1\t0\t>=\t2\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // A creature event with a wrong comparison
        "[Trigger]\nName\tx\nCond\tslapped\t1\t=\t2\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // A negative time limit
        "[Trigger]\nName\tx\nCond\ttime\t1\nAction\ttimelimit\t-5\n[/Trigger]\n[/Triggers]\n",
        // TimeLimit inside a trigger
        "[Trigger]\nName\tx\nTimeLimit\t5\nCond\ttime\t1\nAction\twin\t1\n[/Trigger]\n[/Triggers]\n",
        // make without a skill name
        "[Trigger]\nName\tx\nCond\ttime\t1\nAction\tmake\t1\n[/Trigger]\n[/Triggers]\n"
    };

    for(const char* text : invalid)
    {
        LevelScript script;
        std::istringstream is(text);
        BOOST_CHECK_MESSAGE(!script.importFromStream(is), text);
    }
}

//! \brief Reads the [Triggers] section of the level file named by the environment variable
//! OD_TEST_LEVEL_FILE (the region test level). Does nothing when the variable is not set.
BOOST_AUTO_TEST_CASE(test_region_level)
{
    const char* path = std::getenv("OD_TEST_LEVEL_FILE");
    if(path == nullptr)
        return;

    std::ifstream file(path);
    BOOST_REQUIRE(file.good());
    std::string line;
    bool found = false;
    while(std::getline(file, line))
    {
        if(line.compare(0, 10, "[Triggers]") == 0)
        {
            found = true;
            break;
        }
    }
    BOOST_REQUIRE(found);

    LevelScript script;
    BOOST_REQUIRE(script.importFromStream(file));
    BOOST_CHECK(script.getRegion("Gate") != nullptr);
    BOOST_CHECK(script.getRegion("Home") != nullptr);
    BOOST_CHECK(script.getRegion("Far") != nullptr);

    // Every condition and action kind that the level is meant to exercise is used
    std::set<int> conditions;
    std::set<int> actions;
    for(const LevelScriptTrigger& trigger : script.getTriggers())
    {
        for(const LevelScriptCondition& cond : trigger.mConditions)
        {
            conditions.insert(static_cast<int>(cond.mType));
            // A named region has to exist
            if(!cond.mName.empty() && ((cond.mType == LevelScriptConditionType::region) ||
               (cond.mType == LevelScriptConditionType::claimed)))
            {
                BOOST_CHECK_MESSAGE(script.getRegion(cond.mName) != nullptr, cond.mName);
            }
        }
        for(const LevelScriptAction& action : trigger.mActions)
        {
            actions.insert(static_cast<int>(action.mType));
            if(action.mType == LevelScriptActionType::reveal)
                BOOST_CHECK_MESSAGE(script.getRegion(action.mText) != nullptr, action.mText);
        }
    }
    BOOST_CHECK(conditions.count(static_cast<int>(LevelScriptConditionType::region)) == 1);
    BOOST_CHECK(conditions.count(static_cast<int>(LevelScriptConditionType::claimed)) == 1);
    BOOST_CHECK(conditions.count(static_cast<int>(LevelScriptConditionType::gold)) == 1);
    BOOST_CHECK(conditions.count(static_cast<int>(LevelScriptConditionType::kills)) == 1);
    BOOST_CHECK(actions.count(static_cast<int>(LevelScriptActionType::reveal)) == 1);
    BOOST_CHECK(actions.count(static_cast<int>(LevelScriptActionType::make)) == 1);
    BOOST_CHECK(actions.count(static_cast<int>(LevelScriptActionType::timeLimit)) == 1);
    BOOST_CHECK(actions.count(static_cast<int>(LevelScriptActionType::win)) == 1);
}

BOOST_AUTO_TEST_CASE(test_empty)
{
    LevelScript script;
    std::istringstream is("[/Triggers]\n");
    BOOST_CHECK(script.importFromStream(is));
    BOOST_CHECK(script.isEmpty());
}

//! Every comparison operator, a flag compared with another flag, and the timers
BOOST_AUTO_TEST_CASE(test_flag_operators_and_timers)
{
    static const std::string text =
        "Timer\tspawnDelay\t1\t45\n"
        "Timer\tstopped\t0\t7\n"
        "[Trigger]\n"
        "Name\tops\n"
        "Mode\tonce\n"
        "Cond\tflag\tF1\t!=\t0\n"
        "Cond\tflag\tF2\t>\t3\n"
        "Cond\tflag\tF3\t<\t4\n"
        "Cond\tflag\tF4\t>=\t@F5\n"
        "Cond\tflag\tF6\t==\t2\n"
        "Cond\tflag\tF7\t1\n"
        "Cond\tgold\t1\t==\t500\n"
        "Cond\tcreatures\t1\t!=\t0\n"
        "Cond\ttimer\tspawnDelay\t>=\t30\n"
        "Action\ttimer\tspawnDelay\t5\n"
        "Action\ttimer\tother\n"
        "[/Trigger]\n"
        "[/Triggers]\n";
    LevelScript script;
    std::istringstream is(text);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_REQUIRE_EQUAL(script.getTriggers().size(), 1u);
    const LevelScriptTrigger& trigger = script.getTriggers()[0];
    BOOST_REQUIRE_EQUAL(trigger.mConditions.size(), 9u);
    BOOST_CHECK(trigger.mConditions[0].mCompare == LevelScriptCompare::notEqual);
    BOOST_CHECK(trigger.mConditions[1].mCompare == LevelScriptCompare::greater);
    BOOST_CHECK(trigger.mConditions[2].mCompare == LevelScriptCompare::less);
    BOOST_CHECK(trigger.mConditions[3].mCompare == LevelScriptCompare::atLeast);
    BOOST_CHECK_EQUAL(trigger.mConditions[3].mName2, "F5");
    BOOST_CHECK(trigger.mConditions[4].mCompare == LevelScriptCompare::equal);
    BOOST_CHECK(trigger.mConditions[5].mCompare == LevelScriptCompare::equal);
    BOOST_CHECK_EQUAL(trigger.mConditions[5].mNumber, 1);
    BOOST_CHECK(trigger.mConditions[6].mCompare == LevelScriptCompare::equal);
    BOOST_CHECK(trigger.mConditions[7].mCompare == LevelScriptCompare::notEqual);
    BOOST_CHECK(trigger.mConditions[8].mType == LevelScriptConditionType::timer);
    BOOST_CHECK_EQUAL(trigger.mConditions[8].mNumber, 30);
    BOOST_REQUIRE_EQUAL(trigger.mActions.size(), 2u);
    BOOST_CHECK(trigger.mActions[0].mType == LevelScriptActionType::startTimer);
    BOOST_CHECK_EQUAL(trigger.mActions[0].mNumber, 5);
    BOOST_CHECK_EQUAL(trigger.mActions[1].mNumber, 0);

    BOOST_CHECK(levelScriptCompare(5, LevelScriptCompare::greater, 4));
    BOOST_CHECK(!levelScriptCompare(4, LevelScriptCompare::greater, 4));
    BOOST_CHECK(levelScriptCompare(4, LevelScriptCompare::less, 5));
    BOOST_CHECK(levelScriptCompare(4, LevelScriptCompare::notEqual, 5));
    BOOST_CHECK(levelScriptCompare(4, LevelScriptCompare::equal, 4));

    // Timers are saved with their turns and keep running after a load
    BOOST_CHECK_EQUAL(script.getTimerTurns("spawnDelay"), 45);
    BOOST_CHECK_EQUAL(script.getTimerTurns("never"), 0);
    script.advanceTimers();
    BOOST_CHECK_EQUAL(script.getTimerTurns("spawnDelay"), 46);
    BOOST_CHECK_EQUAL(script.getTimerTurns("stopped"), 7);
    script.startTimer("fresh", 3);
    std::ostringstream os;
    script.exportToStream(os);
    std::string written = os.str();
    LevelScript again;
    std::istringstream is2(written.substr(11));
    BOOST_REQUIRE(again.importFromStream(is2));
    BOOST_CHECK_EQUAL(again.getTimerTurns("spawnDelay"), 46);
    BOOST_CHECK_EQUAL(again.getTimerTurns("fresh"), 3);
    BOOST_CHECK_EQUAL(again.getTimers().size(), 3u);
    std::ostringstream os2;
    again.exportToStream(os2);
    BOOST_CHECK_EQUAL(os2.str(), written);

    // Invalid forms are refused
    static const char* bad[] = {
        "[Trigger]\nName\tx\nMode\tonce\nCond\tflag\tF1\t<>\t2\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttimer\tt\t1\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\ttimer\n[/Trigger]\n[/Triggers]\n"};
    for(const char* entry : bad)
    {
        LevelScript invalid;
        std::istringstream isBad(entry);
        BOOST_CHECK_MESSAGE(!invalid.importFromStream(isBad), entry);
    }
}

//! The conditions for seats, specific creatures, spells, traps and rooms
BOOST_AUTO_TEST_CASE(test_seat_and_creature_conditions)
{
    static const std::string text =
        "Region\tGate\t10\t10\t20\t20\n"
        "[Trigger]\n"
        "Name\tmany\n"
        "Mode\tonce\n"
        "Cond\tdefeated\t4\n"
        "Cond\towns\t1\tLordKnight3\n"
        "Cond\thealth\tLordKnight3\t<\t50\n"
        "Cond\tspell\t1\tspellPossess\n"
        "Cond\tbuilt\t1\tCannon\t>=\t2\n"
        "Cond\tbuilt\t2\tany\t==\t0\n"
        "Cond\troomtiles\t1\tTreasury\t>=\t12\n"
        "Cond\troomsize\t1\tHatchery\t>=\t9\n"
        "Cond\tcreatures\t1\t>=\t2\tKnight\n"
        "Cond\tcreatures\t1\t>=\t2\n"
        "Cond\tregion\t1\tGate\n"
        "Cond\tregion\t1\tGate\t>=\t3\n"
        "Cond\tregion\t1\tGate\t==\t2\tKnight\n"
        "Cond\tregion\t1\t4\t5\t6\t7\n"
        "Action\tmessage\t1\tHello\n"
        "[/Trigger]\n"
        "[/Triggers]\n";
    LevelScript script;
    std::istringstream is(text);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_REQUIRE_EQUAL(script.getTriggers().size(), 1u);
    const std::vector<LevelScriptCondition>& c = script.getTriggers()[0].mConditions;
    BOOST_REQUIRE_EQUAL(c.size(), 14u);
    BOOST_CHECK(c[0].mType == LevelScriptConditionType::seatDefeated);
    BOOST_CHECK_EQUAL(c[0].mSeatId, 4);
    BOOST_CHECK(c[1].mType == LevelScriptConditionType::ownsCreature);
    BOOST_CHECK_EQUAL(c[1].mName, "LordKnight3");
    BOOST_CHECK(c[2].mType == LevelScriptConditionType::creatureHealth);
    BOOST_CHECK(c[2].mCompare == LevelScriptCompare::less);
    BOOST_CHECK_EQUAL(c[2].mNumber, 50);
    BOOST_CHECK(c[3].mType == LevelScriptConditionType::spellKnown);
    BOOST_CHECK(c[4].mType == LevelScriptConditionType::trapsBuilt);
    BOOST_CHECK_EQUAL(c[4].mName, "Cannon");
    BOOST_CHECK(c[5].mCompare == LevelScriptCompare::equal);
    BOOST_CHECK(c[6].mType == LevelScriptConditionType::roomTiles);
    BOOST_CHECK(c[7].mType == LevelScriptConditionType::largestRoom);
    BOOST_CHECK_EQUAL(c[8].mName2, "Knight");
    BOOST_CHECK(c[9].mName2.empty());
    // A region without an operator wants one creature, as before
    BOOST_CHECK(c[10].mCompare == LevelScriptCompare::atLeast);
    BOOST_CHECK_EQUAL(c[10].mNumber, 1);
    BOOST_CHECK_EQUAL(c[11].mNumber, 3);
    BOOST_CHECK(c[12].mCompare == LevelScriptCompare::equal);
    BOOST_CHECK_EQUAL(c[12].mName2, "Knight");
    BOOST_CHECK(c[13].mName.empty());
    BOOST_CHECK_EQUAL(c[13].mX2, 6);

    std::ostringstream os;
    script.exportToStream(os);
    std::string written = os.str();
    LevelScript again;
    std::istringstream is2(written.substr(11));
    BOOST_REQUIRE(again.importFromStream(is2));
    std::ostringstream os2;
    again.exportToStream(os2);
    BOOST_CHECK_EQUAL(os2.str(), written);

    static const char* bad[] = {
        "[Trigger]\nName\tx\nMode\tonce\nCond\tdefeated\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\thealth\tA\t>=\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\tbuilt\t1\tCannon\t2\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\tregion\t1\tGate\t>=\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n"};
    for(const char* entry : bad)
    {
        LevelScript invalid;
        std::istringstream isBad(entry);
        BOOST_CHECK_MESSAGE(!invalid.importFromStream(isBad), entry);
    }
}

//! Events of named creatures and parties, counted only for the names that a condition watches
BOOST_AUTO_TEST_CASE(test_creature_events)
{
    static const std::string text =
        "Event\tLordKnight3\tkilled\t1\n"
        "Member\tKnight_7\tPartyA\n"
        "[Trigger]\n"
        "Name\tlord\n"
        "Mode\tonce\n"
        "Cond\tevent\tLordKnight3\tkilled\n"
        "Cond\tevent\tPartyA\tincapacitated\t>=\t2\n"
        "Cond\troom\t1\tTreasury\t>\t0\n"
        "Cond\troom\t1\tHatchery\t2\n"
        "Action\tspawn\t2\t5\t6\t-1\tparty=PartyA\tKnight:2\n"
        "[/Trigger]\n"
        "[/Triggers]\n";
    LevelScript script;
    std::istringstream is(text);
    BOOST_REQUIRE(script.importFromStream(is));
    const LevelScriptTrigger& trigger = script.getTriggers()[0];
    BOOST_REQUIRE_EQUAL(trigger.mConditions.size(), 4u);
    BOOST_CHECK(trigger.mConditions[0].mType == LevelScriptConditionType::creatureEvent);
    BOOST_CHECK_EQUAL(trigger.mConditions[0].mName2, "killed");
    BOOST_CHECK_EQUAL(trigger.mConditions[0].mNumber, 1);
    BOOST_CHECK_EQUAL(trigger.mConditions[1].mNumber, 2);
    BOOST_CHECK(trigger.mConditions[2].mCompare == LevelScriptCompare::greater);
    BOOST_CHECK(trigger.mConditions[3].mCompare == LevelScriptCompare::atLeast);
    BOOST_CHECK_EQUAL(trigger.mActions[0].mParty, "PartyA");
    BOOST_CHECK_EQUAL(trigger.mActions[0].mCreatures.size(), 1u);

    BOOST_CHECK_EQUAL(script.getEventCount("LordKnight3", "killed"), 1);
    script.recordEvent("Unwatched", "killed");
    BOOST_CHECK_EQUAL(script.getEventCount("Unwatched", "killed"), 0);
    // A member counts for its own name only if watched, and always for its party
    script.recordEvent("Knight_7", "incapacitated");
    BOOST_CHECK_EQUAL(script.getEventCount("PartyA", "incapacitated"), 1);
    BOOST_CHECK_EQUAL(script.getEventCount("Knight_7", "incapacitated"), 0);
    script.addPartyMember("PartyA", "Knight_8");
    script.recordEvent("Knight_8", "incapacitated");
    BOOST_CHECK_EQUAL(script.getEventCount("PartyA", "incapacitated"), 2);

    std::ostringstream os;
    script.exportToStream(os);
    std::string written = os.str();
    LevelScript again;
    std::istringstream is2(written.substr(11));
    BOOST_REQUIRE(again.importFromStream(is2));
    BOOST_CHECK_EQUAL(again.getEventCount("PartyA", "incapacitated"), 2);
    BOOST_CHECK_EQUAL(again.getPartyMembers().size(), 2u);
    std::ostringstream os2;
    again.exportToStream(os2);
    BOOST_CHECK_EQUAL(os2.str(), written);
}

//! Tiles, tags, possession, boulders and the actions that change the level
BOOST_AUTO_TEST_CASE(test_terrain_and_world_actions)
{
    static const std::string text =
        "PortalOff\t3\n"
        "Block\t1\tTroll\n"
        "Region\tHole\t5\t5\t7\t7\n"
        "[Trigger]\n"
        "Name\tworld\n"
        "Mode\tonce\n"
        "Cond\tslabs\t0\tHole\tpath\t>=\t4\n"
        "Cond\tslabs\t-1\tHole\tTreasury\t==\t0\n"
        "Cond\ttagged\t1\tHole\t>=\t2\n"
        "Cond\ttagged\t1\tHole\tall\n"
        "Cond\tpossessed\t1\tHole\n"
        "Cond\tpossessed\t1\tHole\tWyvern\n"
        "Cond\tboulder\tHole\t>=\t1\n"
        "Action\tterrain\t5\t5\t7\t7\trock\n"
        "Action\tterrain\t8\t8\t8\t8\tclaimed\t1\n"
        "Action\tportal\t2\toff\n"
        "Action\tportal\t2\ton\n"
        "Action\tavailable\t1\tTroll\t0\n"
        "Action\tavailable\t1\tTroll\t1\n"
        "Action\tremove\tKnight_5\n"
        "Action\tpossess\tWizard4\n"
        "Action\talliance\t4\t5\tmake\n"
        "Action\talliance\t4\t5\tbreak\n"
        "Action\tgenerate\t2\tGoblin:3\n"
        "Action\tspawn\t3\t9\t9\t-1\tparty=Raid\tKnight:2@LordTitus\tArcher:1\n"
        "Action\tterrain\t9\t9\t9\t9\tmanawell\t1\n"
        "Action\tcountdown\t1800\n"
        "Action\twavecountdown\t420\n"
        "[/Trigger]\n"
        "[/Triggers]\n";
    LevelScript script;
    std::istringstream is(text);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_CHECK(script.isPortalOff(3));
    BOOST_CHECK(!script.isPortalOff(2));
    BOOST_CHECK(script.isCreatureBlocked(1, "Troll"));
    BOOST_CHECK(!script.isCreatureBlocked(2, "Troll"));
    script.setPortalOff(2, true);
    script.setCreatureBlocked(1, "Troll", false);
    BOOST_CHECK(script.isPortalOff(2));
    BOOST_CHECK(!script.isCreatureBlocked(1, "Troll"));
    script.setPortalOff(2, false);
    script.setCreatureBlocked(1, "Troll", true);

    const LevelScriptTrigger& trigger = script.getTriggers()[0];
    BOOST_REQUIRE_EQUAL(trigger.mConditions.size(), 7u);
    BOOST_CHECK(trigger.mConditions[0].mType == LevelScriptConditionType::tileKinds);
    BOOST_CHECK_EQUAL(trigger.mConditions[0].mName2, "path");
    BOOST_CHECK_EQUAL(trigger.mConditions[0].mSeatId, 0);
    BOOST_CHECK(trigger.mConditions[2].mType == LevelScriptConditionType::tilesTagged);
    BOOST_CHECK_EQUAL(trigger.mConditions[2].mNumber, 2);
    BOOST_CHECK_EQUAL(trigger.mConditions[3].mNumber, -1);
    BOOST_CHECK(trigger.mConditions[4].mType == LevelScriptConditionType::possessedInRegion);
    BOOST_CHECK_EQUAL(trigger.mConditions[5].mName2, "Wyvern");
    BOOST_CHECK(trigger.mConditions[6].mType == LevelScriptConditionType::boulderInRegion);
    BOOST_REQUIRE_EQUAL(trigger.mActions.size(), 15u);
    BOOST_CHECK(trigger.mActions[0].mType == LevelScriptActionType::alterTerrain);
    BOOST_CHECK_EQUAL(trigger.mActions[0].mX2, 7);
    BOOST_CHECK_EQUAL(trigger.mActions[0].mSeatId, -1);
    BOOST_CHECK_EQUAL(trigger.mActions[1].mSeatId, 1);
    BOOST_CHECK_EQUAL(trigger.mActions[2].mNumber, 0);
    BOOST_CHECK_EQUAL(trigger.mActions[3].mNumber, 1);
    BOOST_CHECK(trigger.mActions[6].mType == LevelScriptActionType::removeCreature);
    BOOST_CHECK(trigger.mActions[7].mType == LevelScriptActionType::possessCreature);
    BOOST_CHECK_EQUAL(trigger.mActions[8].mNumber, 1);
    BOOST_CHECK_EQUAL(trigger.mActions[9].mNumber, 0);
    BOOST_CHECK(trigger.mActions[10].mType == LevelScriptActionType::generateCreature);
    BOOST_CHECK_EQUAL(trigger.mActions[11].mCreatureNames.size(), 2u);
    BOOST_CHECK_EQUAL(trigger.mActions[11].mCreatureNames[0], "LordTitus");
    BOOST_CHECK(trigger.mActions[11].mCreatureNames[1].empty());
    BOOST_CHECK(trigger.mActions[12].mType == LevelScriptActionType::alterTerrain);
    BOOST_CHECK_EQUAL(trigger.mActions[12].mText, "manawell");
    BOOST_CHECK_EQUAL(trigger.mActions[12].mSeatId, 1);
    BOOST_CHECK(trigger.mActions[13].mType == LevelScriptActionType::countdown);
    BOOST_CHECK_EQUAL(trigger.mActions[13].mNumber, 1800);
    BOOST_CHECK(trigger.mActions[14].mType == LevelScriptActionType::waveCountdown);
    BOOST_CHECK_EQUAL(trigger.mActions[14].mNumber, 420);

    std::ostringstream os;
    script.exportToStream(os);
    std::string written = os.str();
    LevelScript again;
    std::istringstream is2(written.substr(11));
    BOOST_REQUIRE(again.importFromStream(is2));
    std::ostringstream os2;
    again.exportToStream(os2);
    BOOST_CHECK_EQUAL(os2.str(), written);

    static const char* bad[] = {
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\tterrain\t1\t1\t2\t2\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\tportal\t1\tmaybe\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\tavailable\t1\tTroll\t2\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\talliance\t1\t2\tfriends\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\tspawn\t1\t1\t1\t-1\tKnight:2@\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\tslabs\t1\tHole\tpath\t2\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttagged\t1\tHole\tsome\nAction\tmessage\t1\tx\n[/Trigger]\n[/Triggers]\n"};
    for(const char* entry : bad)
    {
        LevelScript invalid;
        std::istringstream isBad(entry);
        BOOST_CHECK_MESSAGE(!invalid.importFromStream(isBad), entry);
    }
}

//! A level that starts with a scripted possession does not drain mana
BOOST_AUTO_TEST_CASE(test_free_possession)
{
    LevelScript script;
    BOOST_CHECK(!script.isFreePossession());
    script.setFreePossession(true);
    BOOST_CHECK(!script.isEmpty());
    std::ostringstream os;
    script.exportToStream(os);
    std::string written = os.str();
    LevelScript again;
    std::istringstream is(written.substr(11));
    BOOST_REQUIRE(again.importFromStream(is));
    BOOST_CHECK(again.isFreePossession());
    again.clear();
    BOOST_CHECK(!again.isFreePossession());
}

//! Standing orders, the slap counter and the last conditions and actions the campaign needs
BOOST_AUTO_TEST_CASE(test_orders_and_slaps)
{
    const std::string text =
        "SlapLimit\t10\n"
        "Slaps\t3\t4\n"
        "Order\tKnight1\tgoto\t-1\t1\t5,6;7,8\n"
        "Order\tKnight2\tkillplayer\t1\t0\t-\n"
        "[Trigger]\n"
        "Name\tt1\n"
        "Mode\tonce\n"
        "Cond\tslaps\t3\t>=\t11\n"
        "Cond\tfurniture\t3\tLibrary\t>=\t1\n"
        "Cond\tbreached\t3\n"
        "Cond\tevent\tSeat3\tcast:callToWar\n"
        "Cond\tevent\tLevel\tpayday\n"
        "Action\torder\tgoto\t-1\t5,6;7,8\tKnight3\tParty1\n"
        "Action\torder\twait\t-1\t-\tKnight4\n"
        "Action\tspeed\trun\tKnight3\n"
        "Action\troomowner\t40\t40\t3\n"
        "Action\tslaplimit\t10\n"
        "[/Trigger]\n"
        "[/Triggers]\n";
    LevelScript script;
    std::istringstream is(text);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_CHECK(!script.isEmpty());
    BOOST_CHECK_EQUAL(script.getSlapLimit(), 10);
    BOOST_CHECK_EQUAL(script.getSlaps(3), 4);
    BOOST_REQUIRE(script.getOrder("Knight1") != nullptr);
    BOOST_CHECK(script.getOrder("Knight1")->mJob == "goto");
    BOOST_CHECK_EQUAL(script.getOrder("Knight1")->mIndex, 1u);
    BOOST_CHECK_EQUAL(script.getOrder("Knight1")->mWaypoints.size(), 2u);
    BOOST_CHECK(script.getOrder("Knight1")->mWaypoints[1] == std::make_pair(7, 8));
    BOOST_REQUIRE(script.getOrder("Knight2") != nullptr);
    BOOST_CHECK_EQUAL(script.getOrder("Knight2")->mSeatId, 1);
    BOOST_CHECK(script.getOrder("Nobody") == nullptr);

    BOOST_REQUIRE_EQUAL(script.getTriggers().size(), 1u);
    const LevelScriptTrigger& trigger = script.getTriggers()[0];
    BOOST_REQUIRE_EQUAL(trigger.mConditions.size(), 5u);
    BOOST_CHECK(trigger.mConditions[0].mType == LevelScriptConditionType::playerSlaps);
    BOOST_CHECK_EQUAL(trigger.mConditions[0].mNumber, 11);
    BOOST_CHECK(trigger.mConditions[1].mType == LevelScriptConditionType::roomFurniture);
    BOOST_CHECK(trigger.mConditions[1].mName == "Library");
    BOOST_CHECK(trigger.mConditions[2].mType == LevelScriptConditionType::dungeonBreached);
    BOOST_CHECK(trigger.mConditions[3].mType == LevelScriptConditionType::creatureEvent);
    BOOST_CHECK(trigger.mConditions[3].mName2 == "cast:callToWar");
    BOOST_REQUIRE_EQUAL(trigger.mActions.size(), 5u);
    BOOST_CHECK(trigger.mActions[0].mType == LevelScriptActionType::creatureOrder);
    BOOST_CHECK_EQUAL(trigger.mActions[0].mCreatureNames.size(), 2u);
    BOOST_CHECK_EQUAL(trigger.mActions[0].mWaypoints.size(), 2u);
    BOOST_CHECK(trigger.mActions[1].mWaypoints.empty());
    BOOST_CHECK(trigger.mActions[2].mType == LevelScriptActionType::creatureSpeed);
    BOOST_CHECK_EQUAL(trigger.mActions[2].mNumber, 1);
    BOOST_CHECK(trigger.mActions[3].mType == LevelScriptActionType::roomOwner);
    BOOST_CHECK_EQUAL(trigger.mActions[3].mX, 40);
    BOOST_CHECK(trigger.mActions[4].mType == LevelScriptActionType::slapLimit);

    // Written and read again
    std::ostringstream os;
    script.exportToStream(os);
    std::string written = os.str();
    LevelScript again;
    std::istringstream isAgain(written.substr(written.find('\n') + 1));
    BOOST_REQUIRE(again.importFromStream(isAgain));
    std::ostringstream os2;
    again.exportToStream(os2);
    BOOST_CHECK(written == os2.str());

    // A goto order moves on and turns into a wait order after the last waypoint
    script.advanceOrder("Knight1");
    BOOST_CHECK(script.getOrder("Knight1")->mJob == "wait");
    script.advanceOrder("Knight2");
    BOOST_CHECK(script.getOrder("Knight2")->mJob == "killplayer");
    script.clearOrder("Knight2");
    BOOST_CHECK(script.getOrder("Knight2") == nullptr);

    // A slap beyond the limit is refused, but counted
    LevelScript limited;
    limited.setSlapLimit(2);
    BOOST_CHECK(limited.registerSlap(3));
    BOOST_CHECK(limited.registerSlap(3));
    BOOST_CHECK(!limited.registerSlap(3));
    BOOST_CHECK_EQUAL(limited.getSlaps(3), 3);
    BOOST_CHECK(limited.registerSlap(4));
    LevelScript unlimited;
    BOOST_CHECK(unlimited.registerSlap(3));

    // Malformed lines
    const char* invalid[] = {
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\torder\tdance\t-1\t-\tKnight1\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\torder\twait\t-1\t-\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\torder\tgoto\t-1\t5;6\tKnight1\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\tspeed\tfly\tKnight1\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\ttime\t1\nAction\troomowner\t1\t2\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\tslaps\t3\t11\nAction\tslaplimit\t1\n[/Trigger]\n[/Triggers]\n",
        "Order\tKnight1\tgoto\t-1\t0\n[/Triggers]\n"
    };
    for(const char* entry : invalid)
    {
        LevelScript bad;
        std::istringstream isBad(entry);
        BOOST_CHECK_MESSAGE(!bad.importFromStream(isBad), entry);
    }
}

//! Story conditions: portal state, named creatures, reaching a place and portal stones on the ground
BOOST_AUTO_TEST_CASE(test_story_conditions)
{
    const std::string text =
        "Region\tExit\t5\t6\t7\t8\n"
        "[Trigger]\n"
        "Name\tt1\n"
        "Mode\tonce\n"
        "Cond\tportal\t2\toff\n"
        "Cond\talive\tWarden\n"
        "Cond\talive\tKing\t0\n"
        "Cond\treached\tWarden\tregion\tExit\n"
        "Cond\treached\tCarrier\theart\t1\n"
        "Cond\tstone\tExit\t>=\t1\n"
        "Action\tportal\t2\ton\n"
        "[/Trigger]\n"
        "[/Triggers]\n";
    LevelScript script;
    std::istringstream is(text);
    BOOST_REQUIRE(script.importFromStream(is));
    BOOST_REQUIRE_EQUAL(script.getTriggers().size(), 1u);
    const LevelScriptTrigger& trigger = script.getTriggers()[0];
    BOOST_REQUIRE_EQUAL(trigger.mConditions.size(), 6u);
    BOOST_CHECK(trigger.mConditions[0].mType == LevelScriptConditionType::portalActive);
    BOOST_CHECK_EQUAL(trigger.mConditions[0].mSeatId, 2);
    BOOST_CHECK_EQUAL(trigger.mConditions[0].mNumber, 0);
    BOOST_CHECK(trigger.mConditions[1].mType == LevelScriptConditionType::creatureAlive);
    BOOST_CHECK_EQUAL(trigger.mConditions[1].mNumber, 1);
    BOOST_CHECK_EQUAL(trigger.mConditions[2].mNumber, 0);
    BOOST_CHECK(trigger.mConditions[3].mType == LevelScriptConditionType::creatureReached);
    BOOST_CHECK(trigger.mConditions[3].mName == "Warden");
    BOOST_CHECK(trigger.mConditions[3].mName2 == "Exit");
    BOOST_CHECK(trigger.mConditions[4].mName2.empty());
    BOOST_CHECK_EQUAL(trigger.mConditions[4].mSeatId, 1);
    BOOST_CHECK(trigger.mConditions[5].mType == LevelScriptConditionType::stoneInRegion);
    BOOST_CHECK(trigger.mConditions[5].mCompare == LevelScriptCompare::atLeast);

    std::ostringstream os;
    script.exportToStream(os);
    std::string written = os.str();
    LevelScript again;
    std::istringstream isAgain(written.substr(written.find('\n') + 1));
    BOOST_REQUIRE(again.importFromStream(isAgain));
    std::ostringstream os2;
    again.exportToStream(os2);
    BOOST_CHECK(written == os2.str());

    const char* invalid[] = {
        "[Trigger]\nName\tx\nMode\tonce\nCond\tportal\t2\tmaybe\nAction\tgold\t1\t1\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\talive\tKing\t2\nAction\tgold\t1\t1\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\treached\tKing\tcorner\tExit\nAction\tgold\t1\t1\n[/Trigger]\n[/Triggers]\n",
        "[Trigger]\nName\tx\nMode\tonce\nCond\tstone\tExit\t3\nAction\tgold\t1\t1\n[/Trigger]\n[/Triggers]\n"
    };
    for(const char* entry : invalid)
    {
        LevelScript bad;
        std::istringstream isBad(entry);
        BOOST_CHECK_MESSAGE(!bad.importFromStream(isBad), entry);
    }
}

//! \brief Required goals gate victory; optional goals and undiscovered conditional goals do not.
BOOST_AUTO_TEST_CASE(required_objectives_and_pending_victory_round_trip)
{
    LevelScript script;
    std::istringstream input(
        "[Trigger]\nName intro\nMode once\n"
        "Action mainobjectiveid 1 main Secure the village.\n"
        "Action optionalobjectiveid 1 extra Explore the gallery.\n"
        "Action mainobjectiveid 2 other Secure the fortress.\n"
        "Action objectiveid 1 legacy An old description.\n[/Trigger]\n"
        "[Trigger]\nName discovery\nMode once\n"
        "Action conditionalobjectiveid 1 carrier Bring the stone home.\n"
        "[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    BOOST_CHECK(!script.areMainObjectivesReached(1));
    BOOST_CHECK(!script.areMainObjectivesReached(2));
    BOOST_CHECK(script.areMainObjectivesReached(3));
    script.setObjectiveState(1, "main", LevelScriptObjectiveState::reached);
    BOOST_CHECK(script.areMainObjectivesReached(1));
    script.setObjectiveState(1, "extra", LevelScriptObjectiveState::failed);
    BOOST_CHECK(script.areMainObjectivesReached(1));
    script.getTriggers()[1].mTimesFired = 1;
    BOOST_CHECK(!script.areMainObjectivesReached(1));
    script.setObjectiveState(1, "carrier", LevelScriptObjectiveState::failed);
    BOOST_CHECK(!script.areMainObjectivesReached(1));
    script.setObjectiveState(1, "carrier", LevelScriptObjectiveState::reached);
    BOOST_CHECK(script.areMainObjectivesReached(1));
    script.setObjectiveState(1, "main", LevelScriptObjectiveState::failed);
    BOOST_CHECK(!script.areMainObjectivesReached(1));
    script.requestVictory(1);
    script.requestVictory(1);
    BOOST_CHECK(script.hasVictoryRequest(1));
    BOOST_CHECK(!script.hasVictoryRequest(2));
    std::ostringstream saved;
    script.exportToStream(saved);
    BOOST_CHECK(saved.str().find("VictoryRequest\t1\n") != std::string::npos);
    BOOST_CHECK(saved.str().find("mainobjectiveid\t1\tmain") != std::string::npos);
    BOOST_CHECK(saved.str().find("optionalobjectiveid\t1\textra") != std::string::npos);
    BOOST_CHECK(saved.str().find("conditionalobjectiveid\t1\tcarrier") != std::string::npos);
    LevelScript restored;
    std::istringstream reload(saved.str().substr(saved.str().find('\n') + 1));
    BOOST_REQUIRE(restored.importFromStream(reload));
    BOOST_CHECK(restored.hasVictoryRequest(1));
    BOOST_CHECK(!restored.areMainObjectivesReached(1));
    restored.setObjectiveState(1, "main", LevelScriptObjectiveState::reached);
    BOOST_CHECK(restored.areMainObjectivesReached(1));
    restored.clear();
    BOOST_CHECK(!restored.hasVictoryRequest(1));
    BOOST_CHECK(restored.isEmpty());
}

//! \brief Legacy objective descriptions do not acquire a new victory requirement.
BOOST_AUTO_TEST_CASE(legacy_objectives_keep_their_original_victory_rules)
{
    LevelScript script;
    std::istringstream input("[Trigger]\nName old\nMode once\nAction objectiveid 1 old Open a path.\n[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    BOOST_CHECK(script.areMainObjectivesReached(1));
    BOOST_CHECK(!script.hasVictoryRequest(1));
    BOOST_CHECK(script.getTriggers()[0].mActions[0].mObjectiveGroup == LevelScriptObjectiveGroup::legacy);
}

//! \brief Main goals must be reaffirmed by current observers; optional completion and real failure persist.
BOOST_AUTO_TEST_CASE(main_goal_refresh_does_not_keep_obsolete_success)
{
    LevelScript script;
    std::istringstream input("[Trigger]\nName setup\nMode once\n"
        "Action mainobjectiveid 1 control Hold the fortress.\n"
        "Action mainobjectiveid 1 deadline Reach the camp in time.\n"
        "Action optionalobjectiveid 1 explore Explore the gallery.\n[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    script.setObjectiveState(1, "control", LevelScriptObjectiveState::reached);
    script.setObjectiveState(1, "deadline", LevelScriptObjectiveState::failed);
    script.setObjectiveState(1, "explore", LevelScriptObjectiveState::reached);
    script.refreshMainObjectives(1);
    BOOST_CHECK(script.getObjectiveState(1, "control") == LevelScriptObjectiveState::open);
    BOOST_CHECK(script.getObjectiveState(1, "deadline") == LevelScriptObjectiveState::failed);
    BOOST_CHECK(script.getObjectiveState(1, "explore") == LevelScriptObjectiveState::reached);
    BOOST_CHECK(!script.areMainObjectivesReached(1));
}

//! \brief Only explicit main goals opt a seat into end-of-turn victory evaluation.
BOOST_AUTO_TEST_CASE(main_goal_model_detection_is_scoped_to_the_target_seat)
{
    LevelScript script;
    std::istringstream input("[Trigger]\nName setup\nMode once\n"
        "Action mainobjectiveid 1 keep Hold the keep.\n"
        "Action optionalobjectiveid 2 scout Explore the gallery.\n[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    BOOST_CHECK(script.hasMainObjectives(1));
    BOOST_CHECK(!script.hasMainObjectives(2));
    BOOST_CHECK(!script.hasMainObjectives(3));
}

//! \brief Fixed natural-floor ownership and fighter-only assembly survive script save/load.
BOOST_AUTO_TEST_CASE(natural_floor_and_fighter_assembly_conditions_round_trip)
{
    LevelScript script;
    std::istringstream input("Region Grove 8 22 21 31\n[Trigger]\nName claim\nMode repeat 0\n"
        "Cond groundclaimed 1 44 5 48 5\nCond region 1 Grove >= 2 @fighters\n"
        "Action mainobjectiveid 1 keep Claim the keep.\n[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    const auto& conditions = script.getTriggers()[0].mConditions;
    BOOST_CHECK(conditions[0].mType == LevelScriptConditionType::groundFootprintClaimed);
    BOOST_CHECK_EQUAL(conditions[0].mX1, 44);
    BOOST_CHECK_EQUAL(conditions[0].mX2, 48);
    BOOST_CHECK_EQUAL(conditions[1].mName2, "@fighters");
    std::ostringstream saved;
    script.exportToStream(saved);
    LevelScript restored;
    std::istringstream reload(saved.str().substr(saved.str().find('\n') + 1));
    BOOST_REQUIRE(restored.importFromStream(reload));
    std::ostringstream again;
    restored.exportToStream(again);
    BOOST_CHECK_EQUAL(saved.str(), again.str());
    for(const std::string bad : {"Cond groundclaimed 1 -1 5 48 5", "Cond groundclaimed 1 44 5 48"})
    {
        LevelScript invalid;
        std::istringstream malformed("[Trigger]\nName bad\nMode once\n" + bad + "\nAction message 1 x\n[/Trigger]\n[/Triggers]\n");
        BOOST_CHECK(!invalid.importFromStream(malformed));
    }
}

//! \brief A transport condition identifies the actual attached stone through parsing and saves.
BOOST_AUTO_TEST_CASE(carried_stone_condition_and_state_round_trip)
{
    LevelScript script;
    std::istringstream input("[Trigger]\nName home\nMode once\n"
        "Cond carryingstone VaultBearer\nCond owns 1 VaultBearer\nCond reached VaultBearer heart 1\n"
        "Action message 1 home\n[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    BOOST_CHECK(script.getTriggers()[0].mConditions[0].mType == LevelScriptConditionType::carryingStone);
    BOOST_CHECK_EQUAL(script.getTriggers()[0].mConditions[0].mName, "VaultBearer");
    script.addStoneCarrier("VaultBearer");
    std::ostringstream saved;
    script.exportToStream(saved);
    LevelScript restored;
    std::istringstream reload(saved.str().substr(saved.str().find('\n') + 1));
    BOOST_REQUIRE(restored.importFromStream(reload));
    BOOST_CHECK(restored.getStoneCarriers().count("VaultBearer") == 1);
    restored.removeStoneCarrier("VaultBearer");
    BOOST_CHECK(restored.getStoneCarriers().empty());
    for(const std::string condition : {"Cond carryingstone", "Cond carryingstone VaultBearer extra"})
    {
        LevelScript invalid;
        std::istringstream malformed("[Trigger]\nName bad\nMode once\n" + condition + "\nAction message 1 x\n[/Trigger]\n[/Triggers]\n");
        BOOST_CHECK(!invalid.importFromStream(malformed));
    }
}

//! \brief Crossings require one actual ordered path, survive saves and reject unrelated visitors.
BOOST_AUTO_TEST_CASE(actual_crossing_progress_and_save_round_trip)
{
    const std::string text = "Region Bridge 11 43 13 46\n[Trigger]\nName crossing\nMode once\n"
        "Cond crossed 1 Bridge north\nAction message 1 crossed\n[/Trigger]\n[/Triggers]\n";
    LevelScript script;
    std::istringstream input(text);
    BOOST_REQUIRE(script.importFromStream(input));
    BOOST_CHECK(script.hasCrossingObservers());
    script.observeCrossingStep("WalkerA", 1, 12, 47, 12, 46);
    script.observeCrossingStep("WalkerA", 1, 12, 46, 12, 45);
    script.observeCrossingStep("WalkerB", 1, 12, 44, 12, 43);
    script.observeCrossingStep("WalkerB", 1, 12, 43, 12, 42);
    BOOST_CHECK(!script.wasRegionCrossed(1, "Bridge", "north", ""));
    std::ostringstream saved;
    script.exportToStream(saved);
    BOOST_CHECK(saved.str().find("CrossingProgress\t1\tWalkerA\tBridge\tnorth\t-\t12\t45") != std::string::npos);
    LevelScript restored;
    std::istringstream reload(saved.str().substr(saved.str().find('\n') + 1));
    BOOST_REQUIRE(restored.importFromStream(reload));
    restored.observeCrossingStep("WalkerA", 1, 12, 45, 12, 44);
    restored.observeCrossingStep("WalkerA", 1, 12, 44, 12, 43);
    restored.observeCrossingStep("WalkerA", 1, 12, 43, 12, 42);
    BOOST_CHECK(restored.wasRegionCrossed(1, "Bridge", "north", ""));
    BOOST_CHECK(!restored.wasRegionCrossed(2, "Bridge", "north", ""));
    std::ostringstream complete;
    restored.exportToStream(complete);
    LevelScript completed;
    std::istringstream done(complete.str().substr(complete.str().find('\n') + 1));
    BOOST_REQUIRE(completed.importFromStream(done));
    BOOST_CHECK(completed.wasRegionCrossed(1, "Bridge", "north", ""));
    LevelScript reset;
    std::istringstream clean(text);
    BOOST_REQUIRE(reset.importFromStream(clean));
    reset.observeCrossingStep("WalkerA", 1, 12, 47, 12, 46);
    reset.clearCreatureCrossings("WalkerA");
    reset.observeCrossingStep("WalkerA", 1, 12, 46, 12, 45);
    reset.observeCrossingStep("WalkerA", 1, 12, 45, 12, 44);
    reset.observeCrossingStep("WalkerA", 1, 12, 44, 12, 43);
    reset.observeCrossingStep("WalkerA", 1, 12, 43, 12, 42);
    BOOST_CHECK(!reset.wasRegionCrossed(1, "Bridge", "north", ""));
}

//! \brief A crossing made before its prerequisite, by another seat, sideways or by a jump is not success.
BOOST_AUTO_TEST_CASE(crossing_order_and_negative_paths)
{
    LevelScript script;
    std::istringstream input("Region Bridge 11 43 13 46\n[Trigger]\nName shelfHeld\nMode once\n"
        "Action message 1 held\n[/Trigger]\n[Trigger]\nName crossing\nMode once\n"
        "Cond crossed 1 Bridge north after shelfHeld\nCond crossed 1 Bridge north after shelfHeld\n"
        "Action message 1 crossed\n[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    for(int y = 47; y > 42; --y)
        script.observeCrossingStep("Walker", 1, 12, y, 12, y - 1);
    BOOST_CHECK(!script.wasRegionCrossed(1, "Bridge", "north", "shelfHeld"));
    script.getTriggers()[0].mTimesFired = 1;
    script.observeCrossingStep("Walker", 1, 12, 47, 12, 42);
    script.observeCrossingStep("Walker", 1, 10, 45, 11, 45);
    script.observeCrossingStep("Walker", 1, 11, 45, 11, 44);
    script.observeCrossingStep("Walker", 1, 11, 44, 11, 43);
    script.observeCrossingStep("Walker", 1, 11, 43, 11, 42);
    for(int y = 47; y > 42; --y)
        script.observeCrossingStep("Enemy", 2, 12, y, 12, y - 1);
    BOOST_CHECK(!script.wasRegionCrossed(1, "Bridge", "north", "shelfHeld"));
    for(int y = 47; y > 42; --y)
        script.observeCrossingStep("Walker", 1, 12, y, 12, y - 1);
    BOOST_CHECK(script.wasRegionCrossed(1, "Bridge", "north", "shelfHeld"));
    script.clear();
    BOOST_CHECK(!script.hasCrossingObservers());
    BOOST_CHECK(script.isEmpty());
}

//! \brief All four directions reject a return to the entry bank and accept only the opposite exit.
BOOST_AUTO_TEST_CASE(crossing_directions_and_backtracking)
{
    for(const std::string direction : {"north", "south", "east", "west"})
    {
        LevelScript script;
        std::istringstream input("Region Bridge 10 10 12 12\n[Trigger]\nName crossing\nMode once\n"
            "Cond crossed 1 Bridge " + direction + "\nAction message 1 crossed\n[/Trigger]\n[/Triggers]\n");
        BOOST_REQUIRE(script.importFromStream(input));
        const bool vertical = direction == "north" || direction == "south";
        const int delta = direction == "north" || direction == "west" ? -1 : 1;
        const int entry = delta < 0 ? 13 : 9;
        const int edge = entry + delta;
        script.observeCrossingStep("Walker", 1, vertical ? 11 : entry, vertical ? entry : 11,
            vertical ? 11 : edge, vertical ? edge : 11);
        script.observeCrossingStep("Walker", 1, vertical ? 11 : edge, vertical ? edge : 11,
            vertical ? 11 : entry, vertical ? entry : 11);
        BOOST_CHECK(!script.wasRegionCrossed(1, "Bridge", direction, ""));
        for(int step = 0; step < 4; ++step)
        {
            const int from = entry + step * delta;
            const int to = from + delta;
            script.observeCrossingStep("Walker", 1, vertical ? 11 : from, vertical ? from : 11,
                vertical ? 11 : to, vertical ? to : 11);
        }
        BOOST_CHECK(script.wasRegionCrossed(1, "Bridge", direction, ""));
    }
    for(const std::string condition : {"Cond crossed 0 Bridge north", "Cond crossed 1 Bridge up",
        "Cond crossed 1 Bridge north after", "Cond crossed 1 Bridge north after -"})
    {
        LevelScript invalid;
        std::istringstream input("[Trigger]\nName bad\nMode once\n" + condition +
            "\nAction message 1 bad\n[/Trigger]\n[/Triggers]\n");
        BOOST_CHECK(!invalid.importFromStream(input));
    }
}

//! \brief A regional hit belongs to the attacking seat, target seat and actual impact region, including saves.
BOOST_AUTO_TEST_CASE(regional_attack_attribution_and_save)
{
    LevelScript script;
    std::istringstream input("Region Siege 33 30 42 42\n[Trigger]\nName fought\nMode once\n"
        "Cond attackedregion 1 3 Siege\nAction message 1 fought\n[/Trigger]\n[/Triggers]\n");
    BOOST_REQUIRE(script.importFromStream(input));
    script.observeRegionAttack(2, 3, 38, 35);
    script.observeRegionAttack(1, 2, 38, 35);
    script.observeRegionAttack(1, 3, 32, 35);
    BOOST_CHECK(!script.wasRegionAttacked(1, 3, "Siege"));
    script.observeRegionAttack(1, 3, 38, 35);
    BOOST_CHECK(script.wasRegionAttacked(1, 3, "Siege"));
    BOOST_CHECK(!script.wasRegionAttacked(2, 3, "Siege"));
    BOOST_CHECK(!script.wasRegionAttacked(1, 2, "Siege"));
    BOOST_CHECK(!script.wasRegionAttacked(1, 3, "Other"));
    std::ostringstream saved;
    script.exportToStream(saved);
    BOOST_CHECK(saved.str().find("Cond\tattackedregion\t1\t3\tSiege") != std::string::npos);
    LevelScript restored;
    std::istringstream reload(saved.str().substr(saved.str().find('\n') + 1));
    BOOST_REQUIRE(restored.importFromStream(reload));
    BOOST_CHECK(restored.wasRegionAttacked(1, 3, "Siege"));
    restored.clear();
    BOOST_CHECK(!restored.wasRegionAttacked(1, 3, "Siege"));
    for(const std::string condition : {"Cond attackedregion 0 3 Siege", "Cond attackedregion 1 1 Siege",
        "Cond attackedregion 1 -3 Siege", "Cond attackedregion 1 2147483648 Siege", "Cond attackedregion 1 3"})
    {
        LevelScript invalid;
        std::istringstream bad("[Trigger]\nName bad\nMode once\n" + condition +
            "\nAction message 1 bad\n[/Trigger]\n[/Triggers]\n");
        BOOST_CHECK(!invalid.importFromStream(bad));
    }
}
