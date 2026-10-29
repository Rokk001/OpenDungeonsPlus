#ifndef AICARE_H
#define AICARE_H

#include <functional>
#include <string>

class Creature;
class KeeperAI;
struct AiEvent;

namespace CARE
{
//! \brief Persistent timing of a production-slap mistake; owned by one keeper's mind.
struct SlapState
{
    double episodeUntil = 0.0;
    double interval = 0.0;
    double nextSlap = 0.0;
    double nextCheck = 0.0;
};
//! \brief Checks the production-slap mistake at a creature-list look and stops own brawls.
void slapWatch(KeeperAI& ai, SlapState& state);
//! \brief Advances an active slap episode without a second mistake draw; called during the mind's regular poll.
void slapEpisodeStep(KeeperAI& ai, SlapState& state);
//! \brief Possesses the strongest defender at a heart or treasury fight, or the weakest on a mistake.
void possessDefender(KeeperAI& ai, const AiEvent& event);
//! \brief Leaves a badly hurt possessed defender and otherwise drives it using the human possession commands.
void possessionStep(KeeperAI& ai, double& nextControl);
//! \brief Moves idle fighters to available training places, strongest first unless the row mistakes the order.
void idleToHall(KeeperAI& ai);
//! \brief Moves capped trainees to the arena and fighters without work to the casino or temple.
void levelWatch(KeeperAI& ai);
//! \brief Takes upset creatures to the available mood room their class likes most.
void moodRelief(KeeperAI& ai);
//! \brief Immediately triggers the row that removes each upset creature's first applicable cause.
//! \param trigger Invokes the named row now with its own draw, without queuing another reaction delay.
void moodPatrol(KeeperAI& ai, const std::function<void(const std::string&, Creature*)>& trigger);
}

#endif // AICARE_H
