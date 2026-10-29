#ifndef AICARE_H
#define AICARE_H

#include "ai/AiMath.h"
#include "ai/AiPrison.h"

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

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
//! \brief Owns one keeper's care callbacks and persistent decisions for the shared mind.
class Controller
{
public:
    //! \brief Registers care, prison and item rows after this keeper's mind has been constructed.
    explicit Controller(KeeperAI& ai);

private:
    //! \brief Restores this controller's relative times and one-time prisoner decisions before use.
    void load();
    //! \brief Advances active slapping and possession through the mind's regular poll.
    bool poll();
    //! \brief Runs the two creature-list rows sharing the plan look.
    void planLook();
    //! \brief Runs idle placement and immediate mood remedies at the scan look.
    void scanLook();
    //! \brief Runs the joint prisoner-age and torture-priority decision.
    void prisonLook();
    //! \brief Reconsiders stored specials and merchant buying at the long look.
    void itemsLook();
    //! \brief Runs D06's idle placement once per mind time for its look, its events and D07's remedy.
    void idle();
    //! \brief Dispatches the named remedy directly inside D07's current trigger.
    void need(const std::string& row, Creature* creature);
    //! \brief Runs care rows for an already delayed game or internal event.
    void event(const AiEvent& event);
    //! \brief Replaces this owner's draw lines with full-precision state relative to the mind clock.
    void save(std::vector<AiMath::AiStateLine>& lines);

    KeeperAI& mAi;
    SlapState mSlap;
    PRIS::State mPrison;
    double mNextControl;
    //! \brief Mind time of the last idle placement, so one firing never moves the same fighters twice.
    double mIdleAt;
    //! \brief Own spell cooldowns at the last poll; a rise marks an own cast for the held mana box.
    std::vector<uint32_t> mCooldowns;
    bool mLoaded;
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
//! \brief Draws a row's mistake for one creature, independent of the other draws of the same trigger.
//! \param rowId The catalogue row whose class and multiplier from [RowClasses] are used.
//! \return true when the mistake is taken for this creature.
bool slipFor(KeeperAI& ai, const std::string& rowId);
}

#endif // AICARE_H
