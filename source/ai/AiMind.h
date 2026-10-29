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

#ifndef AIMIND_H
#define AIMIND_H

#include "ai/AiMath.h"
#include "ai/AiSettings.h"

#include <array>
#include <functional>
#include <iosfwd>
#include <map>
#include <set>
#include <string>
#include <vector>

class Creature;
class GameMap;
class Player;
class Tile;

//! \brief The events a keeper AI reacts to. The first group is raised by the game through
//! BaseAI::notifyEvent, the second is polled by the Mind, the last is raised by the AI's own war planning.
enum class AiEventType
{
    // Raised by the game
    Fight,
    HeartCritical,
    Payday,
    NotEnoughGold,
    NoSkillInQueue,
    NoWorker,
    NoTreasury,
    NoBed,
    NoFood,
    CreatureKilled,
    CreatureMood,
    CreatureLeft,
    CreatureArrived,
    RoomLost,
    BuildingDestroyed,
    Dirt,
    InfirmaryNoMana,
    TavernThirst,
    EnemySpellSeen,
    SpecialStored,
    // Polled by the Mind
    NoMarkedTile,
    GoldBelowBill,
    WoundedCreature,
    PotionReady,
    PrisonerAge,
    SurplusCreature,
    RouteBlocked,
    TunnelOpen,
    EnemyOut,
    EnemyTrapEmpty,
    FightOver,
    FirstPortalArrival,
    Loot,
    LabIdle,
    // Raised by the AI's own war planning
    Plan,
    Start,
    Launch,
    March,
    Contact,
    AssaultOver
};

//! \brief One event queued for a keeper AI.
struct AiEvent
{
    AiEventType type;
    //! \brief The tile of the event, or nullptr when none.
    Tile* tile;
    //! \brief The creature of the event, or nullptr when none.
    Creature* creature;
    //! \brief The id of the other seat (enemy or caster), or -1 when none.
    int otherSeatId;
    //! \brief An amount that belongs to the event (gold, damage ...), 0 when none.
    double amount;
    //! \brief Game time in seconds when the event was raised.
    double time;
};

//! \brief The keeper AI's mind: queues events, draws reaction delays and mistakes, schedules the
//! actions of the one hand under the click budget and keeps the state saved with the game.
class Mind
{
public:
    //! \brief Creates the mind of the given player with the values of its AI level.
    Mind(GameMap& gameMap, Player& player, const AiSettings& settings);

    //! \brief Runs the mind for one game turn: polls events, starts due reactions and performs
    //! the actions whose scheduled end time is reached.
    //! \param timeSinceLastTurn Game seconds since the previous call.
    void doTurn(double timeSinceLastTurn);

    //! \brief Queues a game, polled or internal event once for this seat; the reaction delay of its
    //! kind is drawn here, once per event.
    void enqueue(const AiEvent& event);

    //! \brief Schedules count actions of one kind of the [Actions] table on the hand under the click
    //! budget, starting not before from. perform is called once per action when its end time is reached.
    //! \param actionKey The action name of the [Actions] table.
    //! \param rowId The catalogue row the actions belong to.
    //! \param tile Target tile, or nullptr when none.
    //! \param target Name of the target (creature, room ...), or empty when none.
    //! \return The end time of the last scheduled action.
    double exec(const std::string& actionKey, int count, double from, const std::string& rowId,
                Tile* tile, const std::string& target, const std::function<void()>& perform);

    //! \brief Draws the mistake of a row with its class and multiplier from [RowClasses] and the
    //! mistake multiplier of the level.
    //! \return true when the mistake is taken.
    bool slip(const std::string& rowId);

    //! \brief Draws the mistake of a row with its class from [RowClasses] and the given row multiplier
    //! instead of the configured one.
    //! \return true when the mistake is taken.
    bool slip(const std::string& rowId, double rowMultiplier);

    //! \brief Draws a tactic against "wait" from the priors, the scores and the temperature.
    //! \return The tactic index (allin 0, single 1, split 2, raid 3, counter 4), or -1 for wait.
    int drawTactic(const std::array<double, 5>& priors, const AiMath::TacticScores& scores, double tau);

    //! \brief Checks the hard-limit rows of [RowClasses]: every row the mind draws for has a class,
    //! and the hard-limit rows have no mistake roll (the AI never pauses the game to plan).
    //! \return true when the row classes are complete.
    bool rowClassAudit() const;

    //! \brief Writes the mind's state as the lines of the [AIState] block.
    void exportState(std::ostream& os) const;

    //! \brief Restores the mind's state from the lines of a loaded [AIState] block.
    //! \return false on an unknown tag or a wrong token count; the mind then starts fresh.
    bool importState(const std::vector<std::string>& lines);

    //! \brief Returns the mind clock in game seconds, for scheduling an action from a row.
    double now() const;

    //! \brief Registers a row's reaction to events; rows run in catalogue order after the shared delay.
    void onEvent(const std::string& rowId, const std::vector<AiEventType>& events,
                 const std::function<void(const AiEvent&)>& handler);

    //! \brief Registers one periodic topic; its owner invokes the other rows sharing that look.
    void onLook(const std::string& rowId, double factor, const std::function<void()>& handler);

    //! \brief Registers a polled symptom; only its false-to-true edge queues a reaction.
    void onPoll(const std::string& rowId, AiEventType type, const std::function<bool()>& predicate);

    //! \brief Registers how an action's saved tile and target restore its server call after loading.
    //! The wrapper encodes its arguments without whitespace in target and rechecks legality at execution.
    void onAction(const std::string& actionKey, const std::string& rowId,
                  const std::function<void(Tile*, const std::string&)>& handler);

    //! \brief Returns the age of the last visible enemy cast, or -1 when none has been seen.
    double enemySpellAge(int seatId) const;

    //! \brief Gives row owners their saved war, sighting and persistent-draw lines after loading.
    const std::vector<AiMath::AiStateLine>& savedRows() const;

    //! \brief Registers a row owner's export of war, sighting and persistent-draw lines.
    void onSave(const std::function<void(std::vector<AiMath::AiStateLine>&)>& handler);

private:
    //! \brief A queued reaction stores entity names rather than pointers that may expire.
    struct Reaction
    {
        AiEventType type;
        double due;
        AiMath::ReactionKind kind;
        int x, y;
        std::string creature;
        int seatId;
        double amount;
        bool noticed;
        std::string rowId;
        //! \brief Orders reactions by their scheduled time, preserving input order on ties.
        bool operator<(const Reaction& other) const { return due < other.due; }
    };

    //! \brief A queued hand action retains the fields needed by the saved-action resolver.
    struct Action
    {
        std::string key;
        double due;
        std::string rowId;
        int x, y;
        std::string target;
        std::function<void()> perform;
    };

    //! \brief One periodic topic and its last polled-event value.
    struct Look { double due; bool flag; };

    //! \brief One row's event subscription and reaction function.
    struct EventHandler
    {
        std::vector<AiEventType> types;
        std::function<void(const AiEvent&)> perform;
    };

    //! \brief The interval factor and callback of a periodic topic.
    struct LookHandler { double factor; std::function<void()> perform; };

    //! \brief A polled condition and the event raised by its rising edge.
    struct PollHandler { AiEventType type; std::function<bool()> predicate; };

    //! \brief Returns the configured reaction-delay parameters for this level.
    AiMath::DelayParams delayParams() const;

    //! \brief Clears transient state and restarts registered looks from the current game time.
    void resetState();

    GameMap& mGameMap;
    Player& mPlayer;
    AiSettings mSettings;
    AiMath::HandState mHand;
    double mNow;
    double mSavedAt;
    std::map<int, double> mEnemySpells;
    bool mLoaded;
    std::vector<Reaction> mEvents;
    std::vector<Action> mActions;
    std::map<std::string, Look> mLooks;
    std::map<std::string, EventHandler> mEventHandlers;
    std::map<std::string, LookHandler> mLookHandlers;
    std::map<std::string, PollHandler> mPollHandlers;
    std::map<std::pair<std::string, std::string>, std::function<void(Tile*, const std::string&)>> mActionHandlers;
    std::vector<std::function<void(std::vector<AiMath::AiStateLine>&)>> mSaveHandlers;
    std::vector<AiMath::AiStateLine> mSavedRows;
    std::set<std::string> mDrawnRows;
    std::map<std::string, bool> mTriggerSlips;
    bool mInTrigger;
};

#endif // AIMIND_H
