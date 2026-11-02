/*!
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

#ifndef AIWAR_H
#define AIWAR_H

#include "ai/AiKnowledge.h"
#include "ai/AiMind.h"
#include "ai/AiSettings.h"

#include <string>
#include <set>
#include <vector>

class Creature;
class GameMap;
class KeeperAI;
class Player;
class Tile;

//! \brief The war part of the keeper AI: digging the tunnel, planning and running assaults, defending.
namespace WAR
{
//! \brief One group of an assault: the creatures moved by hand, its targets and its banner.
struct Group
{
    bool raid = false;
    std::vector<Creature*> members;
    //! \brief Target tiles in order (heart tile or room tiles).
    std::vector<Tile*> targets;
    size_t targetIndex = 0;
    Tile* dropTile = nullptr;
    Tile* bannerTile = nullptr;
    //! \brief Game seconds when the banner lapses, -1 when none stands.
    double bannerUntil = -1.0;
    bool finished = false;
};

//! \brief The war state of one keeper AI (the data of the war lines of the saved AI state).
struct WarState
{
    enum TunnelPhase { tunnelNone, tunnelDigging, tunnelOpen };
    //! assaultLaunching: the groups are being moved by hand, the last banner waits for the Launch reaction
    enum AssaultPhase { assaultNone, assaultMoving, assaultRunning, assaultEnding, assaultLaunching };

    TunnelPhase tunnel = tunnelNone;
    double detour = 0.0;
    Tile* tunnelTarget = nullptr;
    Tile* breakthrough = nullptr;
    //! \brief True once the seat knows the tunnel is open (at once for a digger, at first contact otherwise).
    bool tunnelKnown = false;
    double nextProbe = 0.0;
    double nextPlan = -1.0;
    bool exploreMarked = false;

    AssaultPhase assault = assaultNone;
    int tactic = -1;
    //! \brief Game seconds of the first contact of the assault, -1 before it.
    double contactTime = -1.0;
    //! \brief True once an own assault has reached contact; from then on the estimate uses the revealed enemy traps.
    bool contacted = false;
    double lastAssaultEnd = -1.0e18;
    double nextRetreatCheck = 0.0;
    std::vector<Group> groups;
    //! \brief Survivors awaiting a successful drop after an assault.
    std::set<std::string> returning;
    //! \brief Returners with a queued, identity-checked drop action.
    std::set<std::string> returningPending;

    bool defenceRallying = false;
    Tile* defenceBanner = nullptr;
    double lastFight = -1.0e18;
    bool fightOverRaised = true;
    bool enemyOut = false;
    bool enemyTrapsEmpty = false;
    double secondWaveUntil = -1.0;

    SightingState sighting;
};

//! \brief Everything a war function needs; built by the Mind for each call.
struct Env
{
    KeeperAI& ai;
    Mind& mind;
    GameMap& gameMap;
    Player& player;
    const AiSettings& settings;
    WarState& state;
    //! \brief Game seconds now.
    double now;
};

//! \brief Advances the war plan timer, visible spell observations and assault steps each turn.
//! Tunnel and combat symptom events are polled by the shared event source at AiPollSeconds.
void doTurn(Env& env);

//! \brief Handles an event of the war (Fight, TunnelOpen, EnemyOut, EnemyTrapEmpty, FightOver, Start,
//! Plan, Launch, Contact, AssaultOver, EnemySpellSeen) after its reaction delay.
void onEvent(Env& env, const AiEvent& event);

//! \brief Digs the tunnel toward the nearest known enemy tile (row I01) and raises Start; without a known enemy tile it
//! does nothing.
void planDig(Env& env);

//! \brief The explore look of row I05 (period LookPeriod600): while no enemy tile is known and the tunnel is not open,
//! marks the exploration tunnels once.
void exploreLook(Env& env);

//! \brief Plans an attack; bypassRest skips the post-assault rest for a second-wave attempt.
void planAttack(Env& env, bool bypassRest = false);

//! \brief Moves the groups by hand and casts the banners of all but the last group (rows K03, K04, K05); a mental step
//! after the last drop raises Launch (launchDropsDone).
void launch(Env& env, int tactic, const std::vector<Creature*>& ready, const EnemyEstimate& estimate);

//! \brief Raises Launch once the hand has dropped the groups (row K05); called by the mental step of launch.
void launchDropsDone(Env& env);

//! \brief The Launch reaction of row K05, after Strength of row E06: casts the last group's banner and raises March.
void marchOff(Env& env);

//! \brief One step of a running assault (rows K07, K09): banner renewal, next target, Contact, retreat test.
void assaultStep(Env& env);

//! \brief Attacks again when the enemy traps are empty (row K08).
void secondWave(Env& env);

//! \brief Ends the assault (row K10): banners removed, survivors on enemy ground carried home, AssaultOver raised.
void endAssault(Env& env);

//! \brief Defends at the first contact of an enemy group (rows J01, J02, J03, J06).
void defend(Env& env, const AiEvent& event);

//! \brief Protects the heart when it is critical (row J05).
void heartGuard(Env& env);

//! \brief Hands the triggers of row J05 to heartGuard: HeartCritical, and a Fight on a tile of an own dungeon temple.
//! \param event The HeartCritical or Fight event after its reaction delay; a fight elsewhere is ignored.
void heartEvent(Env& env, const AiEvent& event);

//! \brief Carries wounded creatures to their bed or an infirmary and other fleeing creatures to the temple after a fight
//! (row J08).
void restAfterFight(Env& env);

//! \brief Carries one hurt creature to its bed, or to an own infirmary when it has no bed (row J08 as the mood remedy of D07).
void restWounded(Env& env, Creature* creature);

//! \brief Appends the war and sighting lines of the saved AI state (the lines of the war and sighting tags).
void exportRows(const Env& env, std::vector<AiMath::AiStateLine>& lines);

//! \brief Restores the war and sighting lines of a loaded AI state; lines of other tags are ignored.
void importRows(Env& env, const std::vector<AiMath::AiStateLine>& lines);
}

#endif // AIWAR_H
