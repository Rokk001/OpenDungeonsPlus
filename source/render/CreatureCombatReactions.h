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

#ifndef CREATURECOMBATREACTIONS_H
#define CREATURECOMBATREACTIONS_H

#include <cstdint>
#include <string>

class Creature;
class CreatureReactions;

/*! \brief Cosmetic reactions of fighting creatures, client side only: drawing and sheathing the weapon, the stance
 * between two blows, a different look for each blow depending on the weapon, hit reactions of the creature that is
 * attacked, and the weapon that falls to the floor when its owner dies.
 *
 * Nothing here touches the game: the attack animation, its timing, the damage and the range are the ones the server
 * decided on, no animation state is set, no activity is changed and no message is sent. Everything is an overlay of
 * the reaction framework (events 'Attack*', 'Hit*', 'Weapon*' and 'Combat*' in config/creatureReactions.cfg) plus
 * the visibility of the weapon models. The functions are called by CreatureReactions at its client hooks.
 */
class CreatureCombatReactions
{
public:
    //! \brief The creature plays an attack animation (not the work in a room). Its blow gets a look of its own,
    //! the creature that is in front of it flinches, and weapons are drawn.
    static void noteAttack(CreatureReactions& reactions, Creature* attacker, const std::string& clip);

    //! \brief True if the weapon the creature strikes with is a sword (the sword blows of the attack clips)
    static bool carriesSword(const Creature* creature);

    //! \brief The creature runs from a fight: it draws its weapon
    static void noteAlarm(CreatureReactions& reactions, Creature* creature);

    //! \brief The creature plays its death animation: its weapons fall to the floor a moment later
    static void noteDeath(CreatureReactions& reactions, Creature* creature);

    //! \brief The server updated the creature. If its health stage got worse in a fight, it shows the hit.
    static void noteHealth(CreatureReactions& reactions, Creature* creature, uint32_t oldHealth);

    //! \brief Advances the delayed reactions, the fallen weapons and the drawing and sheathing of weapons
    static void update(CreatureReactions& reactions, double timeSinceLastFrame);

    //! \brief Forgets everything, shows the weapons again and removes the fallen ones
    static void stopAll(CreatureReactions& reactions);

private:
    static bool isActive(const CreatureReactions& reactions);
    static bool show(CreatureReactions& reactions, Creature* creature, const std::string& eventName);
    static bool findTarget(CreatureReactions& reactions, Creature* attacker, double range, Creature*& target,
        double& distance);
    static std::string chooseAttackEvent(const CreatureReactions& reactions, const Creature* attacker, bool ranged);
    static void scheduleHit(CreatureReactions& reactions, Creature* target, uint32_t level, bool shield, double delay);
    static void processAttacks(CreatureReactions& reactions);
    static void processHits(CreatureReactions& reactions);
    static void processDrops(CreatureReactions& reactions);
    static void updateFallen(CreatureReactions& reactions, double timeSinceLastFrame);
    static void removeFallen(CreatureReactions& reactions);
    static void watchEvents(CreatureReactions& reactions);
    static void tick(CreatureReactions& reactions);
    static void draw(CreatureReactions& reactions, Creature* creature, bool announce);
    static bool isEnemyNear(CreatureReactions& reactions, const Creature* creature, double radius);
    static void setSheathed(CreatureReactions& reactions, Creature* creature, bool sheathed);
    static void applyVisibility(CreatureReactions& reactions, const Creature* creature, bool visible);
    static bool hasWeaponModel(CreatureReactions& reactions, const Creature* creature);
};

#endif // CREATURECOMBATREACTIONS_H
