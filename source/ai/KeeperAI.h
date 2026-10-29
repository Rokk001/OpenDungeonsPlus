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

#ifndef KEEPERAI_H
#define KEEPERAI_H

#include "ai/BaseAI.h"
#include "ai/AiMind.h"
#include "ai/AiEvents.h"
#include "ai/AiWar.h"
#include "ai/AiRooms.h"
#include "ai/AiEconomy.h"
#include "ai/AiResearch.h"
#include "ai/AiCare.h"

#include <cstdint>
#include <utility>
#include <vector>

class Mind;
class Tile;
struct AiSettings;
enum class RoomType;

//! \brief Controls a keeper using its selected difficulty and current dungeon resources.
class KeeperAI : public BaseAI
{

public:
    //! \brief Creates a keeper with the selected level's configured mind and interim legacy defaults.
    KeeperAI(GameMap& gameMap, Player& player, KeeperAIType type);
    //! \brief Advances the mind and the legacy paths until their owners replace them.
    virtual bool doTurn(double timeSinceLastTurn);
    //! \brief The map this AI plays on, for the decision functions of the SPELL and TRAP namespaces.
    GameMap& getGameMap() { return mGameMap; }
    //! \brief The player this AI controls, for the decision functions of the SPELL and TRAP namespaces.
    Player& getControlledPlayer() { return mPlayer; }
    //! \brief The mind that draws mistakes and schedules this keeper's actions.
    Mind& getMind();
    //! \brief Gives the shared event source access to this keeper's current tunnel and combat state.
    WAR::WarState& getWarState() { return mWar; }
    //! \brief Observes shared symptoms and queues the game's notice in the mind.
    void notifyEvent(const AiEvent& event) override;
    //! \brief The values of the selected AI level.
    const AiSettings& getSettings() const;
    //! \brief Returns the room decisions and pending placement owned by this keeper.
    ROOMS::State& getRoomsState() { return mRoomsState; }
    //! \brief Returns the payday reserve decisions owned by this keeper.
    ECON::EconomyState& getEconomyState() { return mEconomyState; }
    //! \brief Returns the research queue decisions owned by this keeper.
    RES::ResearchState& getResearchState() { return mResearchState; }
    //! \brief Scores known room squares around the selected placement origin.
    bool findRoomPosition(Tile* start, int32_t size, bool walls, int32_t& x, int32_t& y);
    //! \brief Writes the keeper's mind as the contents of its AIState block.
    virtual void exportState(std::ostream& os) const;
    //! \brief Restores the contents of an AIState block, or starts fresh when invalid.
    bool importState(const std::vector<std::string>& lines);
    //! \brief Chooses the AI keeper switches immediately before each ectoplasm product.
    static void updateGhostRoomSettings(Seat& seat);
    //! \brief The room plan of the keeper AI in build order: the [RoomPlan] section of ai.cfg, or the compiled
    //! plan when ai.cfg has none. An unknown room name of ai.cfg is logged as an error and skipped.
    //! \return Pairs of the room type and the tiles of the room
    static std::vector<std::pair<RoomType, uint32_t>> getRoomPlan();

protected:
private:
    //! \brief Runs the polled parts of the war once per turn.
    void runWar();
    //! \brief Hands an event of the war rows to the war module after its reaction delay.
    void handleWarEvent(const AiEvent& event);
    //! \brief Appends the war and sighting lines to the saved AI state of the mind.
    void saveWarRows(std::vector<AiMath::AiStateLine>& lines);


    //! \brief Returns a random cooldown between min and max, scaled by the AI reaction time
    int scaledCooldown(int min, int max) const;

    //! \brief Reaction time in percent of the base cooldowns (lower is faster)
    int mReactionPercent;
    //! \brief The difficulty selected when the controller was created.
    KeeperAIType mType;
    //! \brief The selected level settings shared with the row functions.
    AiSettings mSettings;
    //! \brief The common mind uses the selected level independently of the interim legacy paths.
    Mind mMind;
    //! \brief Keeper-visible poll history, owned by this game and saved with its mind.
    AiEvents mEvents;
    //! \brief The war state of this keeper (tunnel, assault, defence, sightings).
    WAR::WarState mWar;
    ROOMS::State mRoomsState;
    ECON::EconomyState mEconomyState;
    RES::ResearchState mResearchState;
    //! \brief Registers and retains this keeper's creature-care, prisoner and item decisions.
    CARE::Controller mCare{*this};
    //! \brief Creatures below this percentage of their max HP are not sent to fight (lower is more aggressive)
    int mMinHpPercentToFight;
    //! \brief The AI attacks with more healthy fighters than this (0 = never attacks)
    int mMinFightersToAttack;
    //! \brief Fighters below this level are too weak for an attack; the AI waits while more of them exist than this value
    int mMinCreatureLevel;
    //! \brief True while the AI is sending its fighters against an enemy dungeon
    bool mIsAttacking;
    //! \brief Number of healthy fighters when the attack started. Used to decide when to retreat
    int mNbFightersAtAttackStart;
    int mCooldownAttack;
    int mCooldownDefense;
    int mCooldownDefenseMin;
    int mCooldownDefenseMax;
    int mCooldownSaveWoundedCreatures;
    int mCooldownSaveWoundedCreaturesMin;
    int mCooldownSaveWoundedCreaturesMax;
};

#endif // KEEPERAI_H
