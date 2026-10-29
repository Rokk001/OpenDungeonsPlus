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

#include <vector>

class Creature;
class KeeperAI;
class Tile;

//! \brief The spell decisions of the keeper AI. Every cast goes through the ACTS wrappers, so the AI casts
//! only what a human keeper can cast (research, cooldown, mana, target ground) and pays the action time of the hand.
namespace SPELL
{
//! \brief One pass of the in-fight casting loop: picks the spell with the best damage per mana, or a heal for a
//! hurt own creature, and casts it at a target chosen with the focus fire of the level.
//! \param ai The keeper AI that casts.
//! \param enemyGround True while the casting group stands on ground not claimed for the AI's seat (an assault): then only
//! Inferno and Tremor are offered.
//! \param now Game time in seconds.
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

//! \brief Casts Call to War on the given tile. A defence rally needs more than CallToWarMinCreatures creatures to gather,
//! the banners of an assault do not.
//! \param tile The tile of the banner.
//! \param creaturesToGather How many creatures the banner would gather.
//! \param assault True for the banner of an assault launch.
//! \return true when the spell was cast.
bool castCallToWar(KeeperAI& ai, Tile* tile, int creaturesToGather, bool assault);

//! \brief Casts Slow on the strongest visible enemy melee creature that stands on ground claimed for the AI.
//! \return true when the spell was cast.
bool castSlow(KeeperAI& ai);

//! \brief Casts Weak on the visible enemy with the highest damage that stands on ground claimed for the AI.
//! \return true when the spell was cast.
bool castWeak(KeeperAI& ai);

//! \brief Casts Defector on the strongest weakened visible enemy while the AI has room for another fighter.
//! \return true when the spell was cast.
bool castDefector(KeeperAI& ai);

//! \brief Casts Hexen Hen on the visible enemy that attacks a room or the heart.
//! \return true when the spell was cast.
bool castHexenHen(KeeperAI& ai);

//! \brief Casts Summon Champion at the start of an assault or when the heart is attacked.
//! \param tile A claimed tile next to the heart (defence) or the drop tile of the main group (assault).
//! \param heartOrLaunch True for the triggers Launch and HeartCritical, false for any other fight.
//! \return true when the spell was cast.
bool castChampion(KeeperAI& ai, Tile* tile, bool heartOrLaunch);
}

#endif // AISPELLS_H
