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
#include "ai/AiRooms.h"
#include "ai/AiEconomy.h"
#include "ai/AiResearch.h"

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
    //! \brief Picks up wounded creatures and drops then in the dungeon temple
    void saveWoundedCreatures();

    //! \brief Checks if we are under attack and does the needed if it is the case
    void handleDefense();

    //! \brief Offensive state machine: once enough healthy fighters are available, digs toward the
    //! closest enemy dungeon temple and rallies the fighters there with a call to war banner.
    //! Retreats (removes the banner) when too many fighters were lost. It only starts with more healthy fighters
    //! than the attack threshold and while not too many of them are below the minimum creature level.
    void handleAttack();

    //! \brief Checks if a room needs to be repaired and repairs if so
    //! Returns true if the action has been done and false if nothing has been done
    bool repairRooms();

private:
    //! \brief Runs the original wounded-creature, defence and attack paths until their owner replaces them.
    void legacyWarTurn();

    //! \brief Returns the number of non-worker creatures with enough HP to be sent to fight
    int countHealthyFighters() const;

    //! \brief Returns the number of healthy non-worker creatures below the minimum attack level
    int countWeakFighters() const;

    //! \brief Returns the central tile of the closest enemy dungeon temple or nullptr if there is none
    Tile* findEnemyTempleTile();

    //! \brief Removes every call to war banner owned by this AI
    void removeBanners();

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
    ROOMS::State mRoomsState;
    ECON::EconomyState mEconomyState;
    RES::ResearchState mResearchState;
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
    int mCooldownRepairRooms;
    int mCooldownSaveWoundedCreatures;
    int mCooldownSaveWoundedCreaturesMin;
    int mCooldownSaveWoundedCreaturesMax;
};

#endif // KEEPERAI_H
