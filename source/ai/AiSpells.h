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

#ifndef AISPELLS_H
#define AISPELLS_H

#include <cstdint>
#include <vector>

class Creature;
class KeeperAI;
class Tile;

//! \brief The spell decisions of the keeper AI. Every cast goes through the ACTS wrappers, so the AI casts
//! only what a human keeper can cast (research, cooldown, mana, target ground) and pays the action time of the hand.
namespace SPELL
{
//! \brief What the spell rows remember for one keeper AI. It lives as long as the AI; the decisions that last longer
//! than one trigger and a running fight session are saved as "draw" lines of the AI state.
struct State
{
    //! \brief Starts without a cast, without a fight session and without restored lines.
    State();
    //! \brief The game turn of the last Eye of Evil cast, -1 when none (row E04).
    int64_t mLastEyeTurn;
    //! \brief True when the Defense cast of the current fight was drawn as a mistake and follows at FightOver (row E05).
    bool mLateDefense;
    //! \brief True while a fight session runs: from the first Fight reaction until no Fight event came for FightOverSeconds.
    bool mInSession;
    //! \brief Mind time of the first Fight reaction of the session.
    double mSessionStart;
    //! \brief Mind time of the last Fight reaction of the session.
    double mLastFight;
    //! \brief The tile of the last Fight event of the session, -1 when none.
    int mFightX;
    //! \brief The tile of the last Fight event of the session, -1 when none.
    int mFightY;
    //! \brief Mind time before which the casting loop of the session casts nothing.
    double mNextCast;
    //! \brief True once Haste was tried for the length of the current session (row E03).
    bool mSessionHaste;
    //! \brief True once the saved draw lines of the mind were read.
    bool mRestored;
};

//! \brief Connects the spell rows to the mind of the AI: the Fight session (E02, E03, E05, E08-E11, E15-E20, J04, K06),
//! FightOver (the late Defense of E05), March (E03), Launch (E06, E20), HeartCritical (E20) and the saved draw lines.
//! Rows E04 and E07 are cast by the war rows that own the decision to scout and to rally (castEye, castCallToWar,
//! drawLaunchGathering).
void bindRows(KeeperAI& ai);

//! \brief One pass of the in-fight casting loop: picks the spell with the best damage per mana, or a heal for a
//! hurt own creature, and casts it at a target chosen with the focus fire of the level.
//! Only the creatures of the fight count: own fighters and enemies in sight that are fighting; without such an enemy
//! nothing is cast.
//! \param ai The keeper AI that casts.
//! \param enemyGround True while the casting group stands on ground not claimed for the AI's seat (an assault): then only
//! Inferno and Tremor are offered.
//! \param now The mind time in seconds (Mind::now).
//! \param nextCast In: no cast is made before this time. Out: the earliest time of the next cast.
//! \return true when a spell was cast.
bool chooseSpell(KeeperAI& ai, bool enemyGround, double now, double& nextCast);

//! \brief Casts Haste on the main group when it starts the march and when a fight lasts longer than HasteFightSeconds.
//! \param group The creatures of the main group.
//! \param march True for the trigger "march", false for the trigger "fight".
//! \param fightSeconds How long the fight has lasted (ignored for the march).
//! \return true when the spell was cast.
bool castHaste(KeeperAI& ai, const std::vector<Creature*>& group, bool march, double fightSeconds);

//! \brief Casts Eye of Evil on the given tile to scout the enemy, at most once per EyeCastIntervalMinutes.
//! \return true when the spell was cast.
bool castEye(KeeperAI& ai, Tile* tile);

//! \brief Casts Defense on the group that holds the entrance, before the first contact.
//! \param holders The own creatures that hold the entrance.
//! \param fightOver True when the call is made at the end of the fight (the late cast of the mistake).
//! \return true when the spell was cast.
bool castDefense(KeeperAI& ai, const std::vector<Creature*>& holders, bool fightOver);

//! \brief Casts Strength on the main attack group while it stands on its drop tile.
//! \return true when the spell was cast.
bool castStrength(KeeperAI& ai, const std::vector<Creature*>& group);

//! \brief Casts Call to War on the given tile. A defence rally needs more than CallToWarMinCreatures creatures to gather
//! and no complex mistake (the mistake rallies by hand instead); the banners of an assault are always cast, the complex
//! draw of the launch is drawLaunchGathering.
//! \param tile The tile of the banner.
//! \param creaturesToGather How many creatures the banner would gather.
//! \param assault True for the banner of an assault launch.
//! \return true when the spell was cast.
bool castCallToWar(KeeperAI& ai, Tile* tile, int creaturesToGather, bool assault);

//! \brief The complex draw of row E07 at the launch of an assault, made once per launch.
//! \return true for the mistake: only the banners are cast and the groups walk from home; false: every creature of the
//! groups is picked up and dropped at the tunnel end before the banners are cast.
bool drawLaunchGathering(KeeperAI& ai);

//! \brief Casts Slow on the strongest fighting enemy melee creature in sight that stands on ground claimed for the AI.
//! \return true when the spell was cast.
bool castSlow(KeeperAI& ai);

//! \brief Casts Weak on the fighting enemy in sight with the highest damage that stands on ground claimed for the AI.
//! \return true when the spell was cast.
bool castWeak(KeeperAI& ai);

//! \brief Casts Defector on the strongest fighting enemy in sight whose mood is Upset or worse (the creature window
//! shows the mood of any creature) while the AI has room for another fighter.
//! \return true when the spell was cast.
bool castDefector(KeeperAI& ai);

//! \brief Casts Hexen Hen on the enemy that attacks a room or the heart: the Fight event came from a tile of an own
//! room and the enemy fights on or next to it.
//! \param fightTile The tile of the Fight event.
//! \return true when the spell was cast.
bool castHexenHen(KeeperAI& ai, Tile* fightTile);

//! \brief Casts Summon Champion at the start of an assault or when the heart is attacked.
//! \param tile A claimed tile next to the heart (defence) or the drop tile of the main group (assault).
//! \param heartOrLaunch True for the triggers Launch, HeartCritical and a Fight on a heart tile, false for any other fight.
//! \return true when the spell was cast.
bool castChampion(KeeperAI& ai, Tile* tile, bool heartOrLaunch);
}

#endif // AISPELLS_H
