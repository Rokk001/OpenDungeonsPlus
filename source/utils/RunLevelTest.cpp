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

#include "utils/RunLevelTest.h"

#include "creatureaction/CreatureAction.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/LevelScript.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/Random.h"
#include "utils/ResourceManager.h"
#include "ODApplication.h"

#include <OgreRenderTarget.h>

#include <boost/filesystem.hpp>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <map>
#include <mutex>
#include <sstream>
#include <thread>
#include <vector>

namespace
{
    //! Real time allowed for the game to start (level load and connection)
    const int32_t LOAD_LIMIT_SECONDS = 90;
    //! Directory identifying campaign maps in the existing level test input.
    const std::string CAMPAIGN_DIRECTORY = "campaign";

    std::atomic<bool> sActive(false);
    std::atomic<bool> sFinished(false);
    std::atomic<bool> sGameStarted(false);
    std::atomic<int> sExitCode(0);
    //! Frames drawn since the game started and their summed time in microseconds
    std::atomic<uint64_t> sFrameCount(0);
    std::atomic<uint64_t> sFrameMicros(0);
    std::mutex sResultMutex;
    //! Render thread only: start of the current one second frame statistics window
    std::chrono::steady_clock::time_point sFrameWindowStart;
    bool sFrameWindowStarted = false;
    std::string sLevelFile;
    std::string sLevelName;
    int32_t sSeconds = 120;
    uint32_t sSeed = 0;
    std::vector<double> sFrameTimes;
    std::vector<double> sTurnTimes;
    std::mutex sTimeMutex;
    //! Server: creature turns that ended with recovery left, for fighters and for workers
    std::atomic<uint64_t> sServerRecoveryFighters(0);
    std::atomic<uint64_t> sServerRecoveryWorkers(0);
    //! Client: recovery display updates that showed a clock, for fighters and for workers
    std::atomic<uint64_t> sClientClockFighters(0);
    std::atomic<uint64_t> sClientClockWorkers(0);

    //! \brief Writes the recovery display counts to stdout and to run-level-recovery.txt. A run in which the
    //! server had recovery left but the client never showed a clock points at the transfer or the display.
    void writeRecovery()
    {
        std::ostringstream line;
        line << "RECOVERY serverFighterTurns=" << sServerRecoveryFighters.load()
            << " clientFighterClockFrames=" << sClientClockFighters.load()
            << " serverWorkerTurns=" << sServerRecoveryWorkers.load()
            << " clientWorkerClockFrames=" << sClientClockWorkers.load();
        std::cout << line.str() << std::endl;
        if(ResourceManager::getSingletonPtr() != nullptr)
        {
            std::ofstream out((ResourceManager::getSingleton().getUserDataPath() + "run-level-recovery.txt").c_str());
            out << line.str() << "\n";
        }
    }

    //! Scenario that places own fighters near an enemy and writes their combat state after every turn
    const std::string SCENARIO_IGNORED_ENEMIES = "ignored-enemies";
    //! Enemy creature of the level the scenario fighters are placed near
    const std::string SCENARIO_ENEMY_NAME = "PostWatch1";
    //! Class and number of the fighters the scenario places for the human seat
    const std::string SCENARIO_FIGHTER_CLASS = "Goblin";
    const uint32_t SCENARIO_FIGHTERS = 4;
    //! Squared tile distances from the enemy within which the scenario fighters are placed
    const int32_t SCENARIO_MIN_DIST_SQUARED = 16;
    const int32_t SCENARIO_MAX_DIST_SQUARED = 49;
    //! A fighter is written when an enemy creature is within this squared tile distance
    const int32_t SCENARIO_LOG_DIST_SQUARED = 225;
    //! Output file of the scenario in the user data folder
    const std::string SCENARIO_FILE = "run-level-scenario.txt";

    std::string sScenario;
    //! Server thread only: target each creature chose in its fight action during the current turn
    std::map<std::string, std::string> sFightTargets;

    //! \brief Squared distance in tiles between two tiles.
    int32_t squaredTileDistance(const Tile& tile1, const Tile& tile2)
    {
        int32_t dx = tile1.getX() - tile2.getX();
        int32_t dy = tile1.getY() - tile2.getY();
        return dx * dx + dy * dy;
    }

    //! \brief Sums the threat of the fighters in the list, the creature given as skip is left out.
    //! Counted like the fear of stronger enemy groups counts it (workers do not count).
    double scenarioThreat(const std::vector<GameEntity*>& entities, const Creature* skip)
    {
        double threat = 0.0;
        for(GameEntity* entity : entities)
        {
            if(entity->getObjectType() != GameEntityType::creature)
                continue;

            const Creature* other = static_cast<const Creature*>(entity);
            if((other == skip) || other->getDefinition()->isWorker())
                continue;

            threat += other->getThreat();
        }
        return threat;
    }

    //! \brief Places the scenario fighters of the human seat near the scenario enemy and starts the output file.
    //! \return An empty string on success, otherwise the reason why the scenario cannot be set up.
    std::string setupIgnoredEnemiesScenario(GameMap& gameMap, Seat* humanSeat)
    {
        Creature* enemy = gameMap.getCreature(SCENARIO_ENEMY_NAME);
        if(enemy == nullptr)
            return "no creature " + SCENARIO_ENEMY_NAME + " in the level";

        Tile* enemyTile = enemy->getPositionTile();
        if(enemyTile == nullptr)
            return SCENARIO_ENEMY_NAME + " is not on the map";

        const CreatureDefinition* definition = gameMap.getClassDescription(SCENARIO_FIGHTER_CLASS);
        if(definition == nullptr)
            return "no creature class " + SCENARIO_FIGHTER_CLASS;

        std::ofstream out((ResourceManager::getSingleton().getUserDataPath() + SCENARIO_FILE).c_str(), std::ios::trunc);
        out << "scenario " << SCENARIO_IGNORED_ENEMIES << " enemy=" << SCENARIO_ENEMY_NAME
            << " pos=" << enemyTile->getX() << "," << enemyTile->getY() << "\n";

        uint32_t placed = 0;
        int radius = static_cast<int>(std::sqrt(static_cast<double>(SCENARIO_MAX_DIST_SQUARED)));
        std::vector<Tile*> tiles = gameMap.circularRegion(enemyTile->getX(), enemyTile->getY(), radius);
        for(Tile* tile : tiles)
        {
            if(placed >= SCENARIO_FIGHTERS)
                break;

            int32_t dist = squaredTileDistance(*tile, *enemyTile);
            if((dist < SCENARIO_MIN_DIST_SQUARED) || (dist > SCENARIO_MAX_DIST_SQUARED))
                continue;

            if(tile->isFullTile() || !gameMap.pathExists(enemy, enemyTile, tile))
                continue;

            Ogre::Vector3 position(static_cast<Ogre::Real>(tile->getX()), static_cast<Ogre::Real>(tile->getY()), 0.0f);
            Creature* fighter = new Creature(&gameMap, definition, humanSeat, position);
            fighter->setLevel(1);
            fighter->setHP(fighter->getMaxHp());
            fighter->addToGameMap();
            fighter->createMesh();
            fighter->setPosition(fighter->getPosition());
            out << "placed " << fighter->getName() << " pos=" << tile->getX() << "," << tile->getY() << "\n";
            ++placed;
        }

        if(placed == 0)
            return "no reachable free tile near " + SCENARIO_ENEMY_NAME;

        return std::string();
    }

    //! \brief Writes one line per living fighter that has an enemy creature nearby: position, health, knock out
    //! counter, mood, action stack, the enemies it decided with this turn, the threat of both sides and the
    //! target its fight action chose this turn.
    void writeIgnoredEnemiesTurn(GameMap& gameMap)
    {
        std::ofstream out((ResourceManager::getSingleton().getUserDataPath() + SCENARIO_FILE).c_str(), std::ios::app);
        for(Creature* creature : gameMap.getCreatures())
        {
            if(!creature->getIsOnMap() || (creature->getHP() <= 0.0) || creature->getDefinition()->isWorker())
                continue;

            Tile* myTile = creature->getPositionTile();
            if(myTile == nullptr)
                continue;

            int32_t nearest = -1;
            for(Creature* other : gameMap.getCreatures())
            {
                if(!other->getIsOnMap() || (other->getHP() <= 0.0) || other->getSeat()->isAlliedSeat(creature->getSeat()))
                    continue;

                Tile* otherTile = other->getPositionTile();
                if(otherTile == nullptr)
                    continue;

                int32_t dist = squaredTileDistance(*myTile, *otherTile);
                if((nearest < 0) || (dist < nearest))
                    nearest = dist;
            }
            if((nearest < 0) || (nearest > SCENARIO_LOG_DIST_SQUARED))
                continue;

            // The lists the creature decided with this turn (the const accessors do not compute them again)
            const Creature& decided = *creature;
            std::ostringstream line;
            line << "turn=" << gameMap.getTurnNumber() << " name=" << creature->getName()
                << " seat=" << creature->getSeat()->getId() << std::fixed << std::setprecision(2)
                << " pos=" << creature->getPosition().x << "," << creature->getPosition().y
                << " hp=" << creature->getHP() << "/" << creature->getMaxHp()
                << " ko=" << creature->getKoTurnCounter()
                << " mood=" << static_cast<int32_t>(creature->getMoodValue())
                << " moving=" << (creature->isMoving() ? 1 : 0)
                << " nearestEnemyDist2=" << nearest << " actions=";
            for(const std::unique_ptr<CreatureAction>& action : decided.getActions())
                line << CreatureAction::toString(action->getType()) << ":" << action->getNbTurns() << ",";

            line << " visibleEnemies=";
            for(GameEntity* entity : decided.getVisibleEnemyObjects())
            {
                line << entity->getName();
                Tile* entityTile = entity->getPositionTile();
                if(entityTile != nullptr)
                    line << "(dist2=" << squaredTileDistance(*myTile, *entityTile);
                else
                    line << "(dist2=?";

                if(entity->getObjectType() == GameEntityType::creature)
                {
                    const Creature* enemy = static_cast<const Creature*>(entity);
                    line << " hp=" << enemy->getHP() << " ko=" << enemy->getKoTurnCounter();
                }
                line << "),";
            }

            line << " threatOwn=" << (creature->getThreat() + scenarioThreat(decided.getVisibleAlliedObjects(), creature))
                << " threatEnemy=" << scenarioThreat(decided.getVisibleEnemyObjects(), nullptr);

            std::map<std::string, std::string>::const_iterator target = sFightTargets.find(creature->getName());
            line << " fightTarget=" << ((target != sFightTargets.end()) ? target->second : std::string("-"));
            out << line.str() << "\n";
        }
        sFightTargets.clear();
    }

    //! Average and 95th percentile of the values, scaled by factor
    std::string describeTimes(std::vector<double>& values, double factor)
    {
        std::ostringstream out;
        if(values.empty())
        {
            out << "n=0";
            return out.str();
        }
        std::sort(values.begin(), values.end());
        double sum = 0.0;
        for(double value : values)
            sum += value;
        double p95 = values[static_cast<size_t>(0.95 * static_cast<double>(values.size() - 1))];
        out << std::fixed << std::setprecision(4) << "n=" << values.size()
            << " avg=" << (sum / static_cast<double>(values.size())) * factor << " p95=" << p95 * factor;
        return out.str();
    }

    //! Writes frame and turn time statistics to run-level-timing.txt
    void writeTimings()
    {
        std::lock_guard<std::mutex> lock(sTimeMutex);
        std::ofstream out((ResourceManager::getSingleton().getUserDataPath() + "run-level-timing.txt").c_str());
        out << "frame_ms " << describeTimes(sFrameTimes, 1000.0) << "\n";
        out << "turn_ms " << describeTimes(sTurnTimes, 0.001) << "\n";
    }

    //! Writes seats and creatures (sorted) to run-level-state.txt, so two runs can be compared
    void writeState(GameMap& gameMap)
    {
        std::vector<std::string> lines;
        for(Seat* seat : gameMap.getSeats())
        {
            std::ostringstream line;
            line << "seat " << seat->getId() << " gold=" << seat->getGold() << " claimed=" << seat->getNumClaimedTiles()
                << " fighters=" << seat->getNumCreaturesFighters() << " workers=" << seat->getNumCreaturesWorkers();
            lines.push_back(line.str());
        }
        for(Creature* creature : gameMap.getCreatures())
        {
            std::ostringstream line;
            line << "creature " << creature->getName() << " class=" << creature->getDefinition()->getClassName()
                << " seat=" << creature->getSeat()->getId() << " level=" << creature->getLevel()
                << " hp=" << std::fixed << std::setprecision(2) << creature->getHP() << "/" << creature->getMaxHp()
                << " pos=" << creature->getPosition().x << "," << creature->getPosition().y;
            lines.push_back(line.str());
        }
        std::sort(lines.begin(), lines.end());
        std::ofstream out((ResourceManager::getSingleton().getUserDataPath() + "run-level-state.txt").c_str());
        out << "turn " << gameMap.getTurnNumber() << "\n";
        for(const std::string& line : lines)
            out << line << "\n";
    }

    //! Writes the result line to stdout and to run-level-result.txt. Returns false if a result was already reported.
    bool emitResult(int code, const std::string& line)
    {
        std::lock_guard<std::mutex> lock(sResultMutex);
        if(sFinished.load())
            return false;

        sExitCode = code;
        writeRecovery();
        const uint64_t frames = sFrameCount.load();
        if(frames > 0)
            std::cout << "FRAMETIME frames=" << frames << " avg_ms="
                << (static_cast<double>(sFrameMicros.load()) / 1000.0 / static_cast<double>(frames)) << std::endl;
        std::cout << line << std::endl;
        if(ResourceManager::getSingletonPtr() != nullptr)
        {
            std::ofstream out((ResourceManager::getSingleton().getUserDataPath() + "run-level-result.txt").c_str());
            out << line << "\n" << "exit code " << code << "\n";
        }
        sFinished = true;
        return true;
    }

    void watchdog()
    {
        std::chrono::steady_clock::time_point start = std::chrono::steady_clock::now();
        const int64_t totalLimit = LOAD_LIMIT_SECONDS + 2 * static_cast<int64_t>(sSeconds) + 60;
        while(!sFinished.load())
        {
            std::this_thread::sleep_for(std::chrono::milliseconds(200));
            int64_t elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::steady_clock::now() - start).count();
            if(!sGameStarted.load() && (elapsed > LOAD_LIMIT_SECONDS))
            {
                RunLevelTest::fail(RunLevelTest::codeLoadError, "load error: the game did not start within "
                    + Helper::toString(LOAD_LIMIT_SECONDS) + " s");
                return;
            }
            if(elapsed > totalLimit)
            {
                if(emitResult(RunLevelTest::codeTimeout, "FAIL " + sLevelName + " : timeout: no result within "
                    + Helper::toString(totalLimit) + " s (watchdog)"))
                    std::_Exit(RunLevelTest::codeTimeout);
                return;
            }
        }
    }
}

void RunLevelTest::configure(const std::string& levelFile, int32_t seconds, uint32_t seed, const std::string& scenario)
{
    sSeed = seed;
    sScenario = scenario;
    sLevelFile = levelFile;
    sLevelName = boost::filesystem::path(levelFile).filename().string();
    sSeconds = seconds;
    sActive = true;
    std::thread(watchdog).detach();
}

bool RunLevelTest::isActive()
{
    return sActive.load();
}

bool RunLevelTest::isFinished()
{
    return sFinished.load();
}

int RunLevelTest::getExitCode()
{
    return sExitCode.load();
}

const std::string& RunLevelTest::getLevelFile()
{
    return sLevelFile;
}

void RunLevelTest::fail(Code code, const std::string& reason)
{
    std::string detail = reason;
    if((LogManager::getSingletonPtr() != nullptr) && (LogManager::getSingleton().getCriticalCount() > 0))
        detail += " (first error: " + LogManager::getSingleton().getFirstCritical() + ")";
    emitResult(code, "FAIL " + sLevelName + " : " + detail);
}

int RunLevelTest::reportException(const std::string& what)
{
    emitResult(codeRunError, "FAIL " + sLevelName + " : run error: unhandled exception: " + what);
    return sExitCode.load();
}

void RunLevelTest::recordFrame(float seconds)
{
    if(!sActive.load() || !sGameStarted.load() || sFinished.load() || seconds <= 0.0f)
        return;

    sFrameCount.fetch_add(1);
    sFrameMicros.fetch_add(static_cast<uint64_t>(seconds * 1000000.0f));
}

//! \brief Checks loading, registered goals and the existing timed victory probe on server turns; a forced win
//! that the level holds back because its main goals are still open counts as the expected result.
void RunLevelTest::onServerTurn(GameMap& gameMap)
{
    if(sFinished.load())
        return;

    int64_t turn = gameMap.getTurnNumber();
    if(turn < 1)
        return;

    bool firstTurn = !sGameStarted.exchange(true);
    if(firstTurn && (sSeed != 0))
        Random::setSeed(sSeed);
    // The refresh of this turn is already sent: these are the recovery values the clients received
    for(Creature* creature : gameMap.getCreatures())
    {
        if(creature->getAttackRecoveryTurns() == 0)
            continue;
        if(creature->getDefinition()->isWorker())
            sServerRecoveryWorkers.fetch_add(1);
        else
            sServerRecoveryFighters.fetch_add(1);
    }
    uint32_t criticalCount = LogManager::getSingleton().getCriticalCount();
    if(criticalCount > 0)
    {
        if(firstTurn)
            fail(codeLoadError, "load error: " + Helper::toString(criticalCount) + " error(s) logged while loading");
        else
            fail(codeRunError, "run error: " + Helper::toString(criticalCount) + " error(s) logged up to turn "
                + Helper::toString(turn));
        return;
    }

    Seat* humanSeat = nullptr;
    for(Player* player : gameMap.getPlayers())
    {
        if(player->getIsHuman())
        {
            humanSeat = player->getSeat();
            break;
        }
    }
    if(humanSeat == nullptr)
    {
        fail(codeRunError, "run error: no human player in the game");
        return;
    }

    if(firstTurn && boost::filesystem::path(sLevelFile).parent_path().filename().string() == CAMPAIGN_DIRECTORY)
    {
        const unsigned int goalCount = humanSeat->numUncompleteGoals()
            + humanSeat->numCompletedGoals() + humanSeat->numFailedGoals();
        if(goalCount == 0)
        {
            fail(codeLoadError, "load error: no registered goals for the human seat");
            return;
        }
        std::cout << "GOALS registered=" << goalCount << std::endl;
    }

    if(firstTurn && !sScenario.empty())
    {
        if(sScenario != SCENARIO_IGNORED_ENEMIES)
        {
            fail(codeUsage, "usage error: unknown scenario " + sScenario);
            return;
        }

        std::string error = setupIgnoredEnemiesScenario(gameMap, humanSeat);
        if(!error.empty())
        {
            fail(codeRunError, "scenario error: " + error);
            return;
        }
    }
    if(sScenario == SCENARIO_IGNORED_ENEMIES)
        writeIgnoredEnemiesTurn(gameMap);

    std::string played = Helper::toString(static_cast<int64_t>(turn / ODApplication::turnsPerSecond)) + " s game time";
    if(gameMap.seatIsAWinner(humanSeat))
    {
        if(sSeed != 0)
            writeState(gameMap);
        writeTimings();
        emitResult(codePass, "PASS " + sLevelName + " : level loaded, victory reported by the level goals after " + played);
        return;
    }

    if(humanSeat->numFailedGoals() > 0)
    {
        fail(codeNoVictory, "no victory: the player seat failed a goal (defeated) after " + played);
        return;
    }

    if(static_cast<double>(turn) < sSeconds * ODApplication::turnsPerSecond)
        return;

    // Time is over: record the state before the win changes anything
    if(sSeed != 0)
        writeState(gameMap);
    writeTimings();

    // Fire the win of the human seat and check that it is reported
    gameMap.addWinningSeat(humanSeat);
    if(!gameMap.seatIsAWinner(humanSeat))
    {
        // Levels with grouped main goals hold a victory back until every main goal is reached; that is the
        // expected answer to a forced win at the end of a short run, not a missing victory report
        const LevelScript& script = gameMap.getLevelScript();
        if(script.hasMainObjectives(humanSeat->getId()) && !script.areMainObjectivesReached(humanSeat->getId()))
        {
            emitResult(codePass, "PASS " + sLevelName + " : level loaded, ran " + played
                + ", no errors, triggered win held back until all main goals are reached");
            return;
        }
        fail(codeNoVictory, "no victory: win was triggered after " + played + " but not reported");
        return;
    }
    emitResult(codePass, "PASS " + sLevelName + " : level loaded, ran " + played + ", no errors, triggered win reported");
}

void RunLevelTest::onFrameRendered(Ogre::RenderTarget& target)
{
    if(!sActive.load() || !sGameStarted.load() || sFinished.load())
        return;

    std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
    if(!sFrameWindowStarted)
    {
        sFrameWindowStarted = true;
        sFrameWindowStart = now;
        target.resetStatistics();
        return;
    }

    if(now - sFrameWindowStart < std::chrono::seconds(1))
        return;

    sFrameWindowStart = now;
    const Ogre::RenderTarget::FrameStats& stats = target.getStatistics();
    std::ofstream out((ResourceManager::getSingleton().getUserDataPath() + "run-level-frames.txt").c_str(),
        std::ios::app);
    out << "frames avgFps " << stats.avgFPS << " worstFrameMs " << stats.worstFrameTime
        << " bestFrameMs " << stats.bestFrameTime << "\n";
    target.resetStatistics();
}

void RunLevelTest::onServerTurnTime(int64_t microseconds)
{
    if(!sActive.load() || !sGameStarted.load() || sFinished.load())
        return;

    std::lock_guard<std::mutex> lock(sTimeMutex);
    sTurnTimes.push_back(static_cast<double>(microseconds));
}

void RunLevelTest::onFrame(double seconds)
{
    if(!sActive.load() || !sGameStarted.load() || sFinished.load())
        return;

    std::lock_guard<std::mutex> lock(sTimeMutex);
    sFrameTimes.push_back(seconds);
}

//! \brief Remembers the fight target of the creature for the scenario line of the current turn.
void RunLevelTest::onFightTarget(const Creature& creature, const GameEntity& target, bool attackNow)
{
    if(sScenario.empty() || sFinished.load())
        return;

    sFightTargets[creature.getName()] = target.getName() + (attackNow ? ":attack" : ":approach");
}

//! \brief Counts the client recovery display updates that show a clock, separately for workers and fighters.
void RunLevelTest::onRecoveryFrame(bool worker, uint32_t frame)
{
    if(!sActive.load() || !sGameStarted.load() || sFinished.load() || (frame == 0))
        return;

    if(worker)
        sClientClockWorkers.fetch_add(1);
    else
        sClientClockFighters.fetch_add(1);
}
