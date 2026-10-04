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

#ifndef WORKERREACTIONS_H
#define WORKERREACTIONS_H

#include <string>

struct CosmeticEvent;
class Creature;
class CreatureReactions;
class GameEntity;

/*! \brief Cosmetic reactions of the workers, client side only: hit effects while digging (each material has its
 * own), the heavy last blow, tiredness after a long dig, stomping and knocking while claiming and reinforcing,
 * picking up and putting down things (gold, bodies, prisoners, traps), a heavy gait with a load, the gold on the
 * body of a worker, coins flying when a worker with gold is slapped, panic, a weak fight, hurried work, stepping
 * aside in narrow passages and small habits when there is no work.
 *
 * Nothing here touches the game: no animation state is set, no activity is changed and no message is sent. All is an
 * overlay of the reaction framework (events 'Dig*', 'Claim*', 'Pick*', 'Worker*', ... in config/creatureReactions.cfg)
 * plus one model on the body of a worker that carries gold. The functions are called by CreatureReactions at its
 * client hooks.
 */
class WorkerReactions
{
public:
    //! \brief The creature starts the animation. Digging, claiming, idling and fighting of workers are noted.
    static void noteAnimation(CreatureReactions& reactions, Creature* creature, const std::string& clip);

    //! \brief The server sent a cosmetic event (digFinished and carriedGold are used here)
    static void noteCosmeticEvent(CreatureReactions& reactions, const CosmeticEvent& event);

    //! \brief The worker picks up the entity
    static void noteCarry(CreatureReactions& reactions, Creature* carrier, GameEntity* carried);

    //! \brief The worker puts down the entity
    static void noteRelease(CreatureReactions& reactions, Creature* carrier, GameEntity* carried);

    //! \brief The keeper slapped or picked up the creature
    static void noteHandled(CreatureReactions& reactions, Creature* creature);

    //! \brief The creature got the particle effect of the spell script
    static void noteParticleEffect(CreatureReactions& reactions, Creature* creature, const std::string& script);

    //! \brief Advances the delayed reactions and looks at the workers now and then
    static void update(CreatureReactions& reactions, double timeSinceLastFrame);

    //! \brief Forgets everything and removes the gold from the bodies
    static void stopAll(CreatureReactions& reactions);

private:
    static bool isActive(const CreatureReactions& reactions);
    static bool isWorker(const Creature* creature);
    static bool show(CreatureReactions& reactions, Creature* creature, const std::string& eventName);
    static void later(CreatureReactions& reactions, Creature* creature, const std::string& eventName, double delay);
    static void processLater(CreatureReactions& reactions);
    static void tick(CreatureReactions& reactions);
    static void tickWorker(CreatureReactions& reactions, Creature* worker);
    static void showDigHit(CreatureReactions& reactions, Creature* worker);
    static void showClaim(CreatureReactions& reactions, Creature* worker);
    static void updateGoldBody(CreatureReactions& reactions, Creature* worker, bool visible);
    static void removeGoldBody(const std::string& workerName);
    static void removeAllGoldBodies();
};

#endif // WORKERREACTIONS_H
