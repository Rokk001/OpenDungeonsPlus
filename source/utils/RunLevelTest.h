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

#ifndef RUNLEVELTEST_H
#define RUNLEVELTEST_H

#include <cstdint>
#include <string>

class Creature;
class GameEntity;
class GameMap;

namespace Ogre
{
class RenderTarget;
}

//! \brief Debug mode for automated level load tests (command line: --run-level <file> --seconds <N>).
//! The game starts a local single player game on the level, lets it run for N seconds of game time,
//! then sets all main goals of the level as reached, fires the win of the human seat and checks that it
//! is reported (a refused win is a failure). A campaign level also has to show the victory message and the
//! campaign map with the next level. One result line (PASS/FAIL
//! with reason) is printed and written to run-level-result.txt in the user data folder. A watchdog
//! ends runs that hang. The process exit code tells the result (see Code).
class RunLevelTest
{
public:
    enum Code
    {
        codePass = 0,
        codeUsage = 1,
        codeLoadError = 2,
        codeRunError = 3,
        codeNoVictory = 4,
        codeTimeout = 5
    };

    //! \brief Activates the test mode and starts the watchdog.
    //! If seed is not 0, the random generator is set to it when the first turn runs and the game
    //! state at the end of the run is written to run-level-state.txt (for seeded comparisons).
    //! If scenario is not empty, that scenario is set up on the first turn (command line: --scenario <name>).
    //! The scenario "ignored-enemies" places four fighters of the human seat near the creature PostWatch1 and
    //! writes, after every turn, the combat state of every fighter near an enemy to run-level-scenario.txt.
    static void configure(const std::string& levelFile, int32_t seconds, uint32_t seed = 0,
        const std::string& scenario = std::string());

    //! \brief True if the level test mode was activated on the command line.
    static bool isActive();

    //! \brief True once a result was reported. The main loop then ends the game.
    static bool isFinished();

    //! \brief Returns the process exit code of the reported result (see Code).
    static int getExitCode();

    //! \brief Returns the level file given on the command line.
    static const std::string& getLevelFile();

    //! \brief Reports a failure. Only the first result (pass or fail) of a run counts.
    static void fail(Code code, const std::string& reason);

    //! \brief Reports an exception that ended the application. Returns the exit code.
    static int reportException(const std::string& what);

    //! \brief Called by the render thread every frame. Once the game runs, the frame times are summed and the
    //! average is printed as one line (FRAMETIME frames=... avg_ms=...) before the result line.
    static void recordFrame(float seconds);

    //! \brief Called by the server thread after every turn of the game. At the end of the run it sets all
    //! main goals of the level as reached and then fires the win; a refused win fails the run. For a campaign
    //! level the run only passes once the client showed the victory message and the campaign map.
    static void onServerTurn(GameMap& gameMap);

    //! \brief Called by the main menu right before it starts the tested level. If the level is an entry of the
    //! campaign definition, the campaign is started on it (without writing saved progress), so that its victory
    //! takes the normal campaign path.
    static void prepareCampaignLevel();

    //! \brief Called by the client when the campaign victory message is shown.
    static void onVictoryShown();

    //! \brief Called by the client when the campaign map was built after a level.
    //! \param levelWon true if the map shows the played level as won. The run passes only if the victory
    //! message was shown before and the map offers an unlocked next level (or the campaign is completed).
    static void onCampaignMapShown(bool levelWon);

    //! \brief Called by the render loop after every frame. Once the game runs, it appends one line per
    //! second to run-level-frames.txt in the user data folder (average fps, worst and best frame time
    //! in ms of that second), so that frame times can be compared between runs.
    static void onFrameRendered(Ogre::RenderTarget& target);

    //! \brief Called by the server thread with the time (microseconds) it needed to process one turn.
    static void onServerTurnTime(int64_t microseconds);

    //! \brief Called by the client thread for every frame with the time since the last frame (seconds).
    static void onFrame(double seconds);

    //! \brief Called by the fight action of a creature (server thread) with the target it chose this turn.
    //! \param attackNow true if the creature attacks from where it stands, false if it walks towards the target.
    //! Only recorded while a scenario runs; the next scenario line of the creature shows it.
    static void onFightTarget(const Creature& creature, const GameEntity& target, bool attackNow);

    //! \brief Called by the client for every update of a creature's recovery display with the atlas frame it
    //! shows (0 means no clock). The frames that show a clock are counted separately for workers and fighters
    //! and reported with the result, next to the server turns in which a creature had recovery left.
    static void onRecoveryFrame(bool worker, uint32_t frame);
};

#endif // RUNLEVELTEST_H
