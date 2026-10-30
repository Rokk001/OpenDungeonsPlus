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
    //! \brief One fight session: from the first Fight reaction of a fight until the fight is over. Parallel fights at
    //! different places have their own sessions, casting loops and first reactions.
    struct Session
    {
        //! \brief Mind time when the first fight of the session began.
        double mStart;
        //! \brief Mind time of the last Fight reaction of the session, or of the last poll that still saw the fight.
        double mLastFight;
        //! \brief The tile of the last Fight event of the session, -1 when none.
        int mFightX;
        //! \brief The tile of the last Fight event of the session, -1 when none.
        int mFightY;
        //! \brief Mind time before which the casting loop of the session casts nothing.
        double mNextCast;
        //! \brief True once Haste was tried for the length of this session (row E03).
        bool mHaste;
        //! \brief True when the Defense cast of this fight was drawn as a mistake and follows when the fight is over
        //! (row E05).
        bool mLateDefense;
    };
    //! \brief The running fight sessions.
    std::vector<Session> mSessions;
    //! \brief The tile of the session whose decisions run now, -1 when none: the fight spells look only at its creatures.
    int mFightX;
    //! \brief The tile of the session whose decisions run now, -1 when none.
    int mFightY;
    //! \brief True once the saved draw lines of the mind were read.
    bool mRestored;
};

//! \brief Connects the spell rows to the mind of the AI: the Fight sessions (E02, E03, E05, E08-E11, E15-E20, J04, K06),
//! the end of a session (the late Defense of E05), Launch (E20), HeartCritical (E20) and the saved draw lines.
//! Rows E04 and E07 are cast by the war rows that own the decision to scout and to rally (castEye, castCallToWar,
//! drawLaunchGathering); Strength (E06) and the march Haste (E03) are reserved by the launch between the drops of the
//! main group and its banner (castStrength, castHaste).
void bindRows(KeeperAI& ai);

//! \brief One pass of the in-fight casting loop: picks the spell with the best damage per mana, or a heal for a
//! hurt own creature, and casts it at a target chosen with the focus fire of the level.
//! Only the creatures of the current fight count: the fighting own fighters and enemies in sight linked to the tile of
//! the last Fight event of the session whose decisions run now; without such an enemy nothing is cast.
//! \param ai The keeper AI that casts.
//! \param enemyGround True while the casting group stands on ground not claimed for the AI's seat (an assault): then only
//! Inferno and Tremor are offered.
//! \param now The mind time in seconds (Mind::now).
//! \param nextCast In: no cast is made before this time. Out: the earliest time of the next cast.
//! \return true when a spell was cast.
bool chooseSpell(KeeperAI& ai, bool enemyGround, double now, double& nextCast);

//! \brief Casts Haste on the main group when it starts the march and when a fight lasts longer than HasteFightSeconds.
//! The launch reserves the march cast right before the banner that starts the march, while the group still stands on
//! its drop tile (own claimed ground).
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
//! \param lateDefense The flag of the fight (Session::mLateDefense): set when the mistake delays the cast, cleared by
//! the late cast.
//! \return true when the spell was cast.
bool castDefense(KeeperAI& ai, const std::vector<Creature*>& holders, bool fightOver, bool& lateDefense);

//! \brief Casts Strength on the main attack group while it stands on its drop tile. The launch calls it after the hand
//! moves of the main group and before its banner, so the hand casts it after the drops.
//! \return true when the spell was cast.
bool castStrength(KeeperAI& ai, const std::vector<Creature*>& group);

//! \brief Casts Call to War on the given tile when the mana covers its price (no spell reserve). A defence rally needs more than CallToWarMinCreatures creatures to gather
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

//! \brief Casts Slow on the strongest enemy melee creature of the current fight that stands on ground claimed for the AI.
//! \return true when the spell was cast.
bool castSlow(KeeperAI& ai);

//! \brief Casts Weak on the enemy of the current fight with the highest damage that stands on ground claimed for the AI.
//! \return true when the spell was cast.
bool castWeak(KeeperAI& ai);

//! \brief Casts Defector on the strongest enemy of the current fight whose mood is Upset or worse (the creature window
//! shows the mood of any creature) while the AI has room for another fighter.
//! \return true when the spell was cast.
bool castDefector(KeeperAI& ai);

//! \brief Casts Hexen Hen on an enemy of the current fight that attacks a room or the heart of the AI: the target its
//! fight action chooses now (the same choice as CreatureActionFight::handleFight) is an own room.
//! \return true when the spell was cast.
bool castHexenHen(KeeperAI& ai);

//! \brief Casts Summon Champion at the start of an assault or when the heart is attacked.
//! \param tile A claimed tile next to the heart (defence) or the drop tile of the main group (assault).
//! \param heartOrLaunch True for the triggers Launch, HeartCritical and a Fight on a heart tile, false for any other fight.
//! \return true when the spell was cast.
bool castChampion(KeeperAI& ai, Tile* tile, bool heartOrLaunch);
}

#endif // AISPELLS_H
