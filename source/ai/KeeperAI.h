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

#include <cstdint>
#include <utility>
#include <vector>

class Tile;
enum class RoomType;

//! \brief Controls a keeper using its selected difficulty and current dungeon resources.
class KeeperAI : public BaseAI
{

public:
    //! \brief Creates a keeper with the selected level's configured mind and interim legacy defaults.
    KeeperAI(GameMap& gameMap, Player& player, KeeperAIType type);
    //! \brief Advances the mind and the legacy paths until their owners replace them.
    virtual bool doTurn(double timeSinceLastTurn);
    //! \brief Gives the row owners the shared scheduler, mistakes and saved-state interface.
    Mind& getMind();
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
    //! \brief Checks if the AI has a treasury. If not, we search for the first available tile
    //! to add it
    //! Returns true if the action has been done and false if nothing has been done
    bool checkTreasury();

    //! \brief Checks if a room is needed. If yes, it will check if place is available
    //! and start digging for it.
    //! Returns true if the action has been done and false if nothing has been done
    bool handleRooms();

    //! \brief Look for gold and make way up to it.
    //! \brief Returns whether the action could succeed.
    //! It will also return false once it's done.
    bool lookForGold();

    //! \brief Picks up wounded creatures and drops then in the dungeon temple
    void saveWoundedCreatures();

    //! \brief Checks if we are under attack and does the needed if it is the case
    void handleDefense();

    //! \brief Offensive state machine: once enough healthy fighters are available, digs toward the
    //! closest enemy dungeon temple and rallies the fighters there with a call to war banner.
    //! Retreats (removes the banner) when too many fighters were lost. It only starts with more healthy fighters
    //! than the attack threshold and while not too many of them are below the minimum creature level.
    void handleAttack();

    //! \brief Places researched traps and wooden doors at the entrances of the AI rooms and in the
    //! corridors in front of them. Limited by gold, workshop production and the AI level
    void handleTraps();

    //! \brief Casts heal on hurt fighting creatures and a call to war banner on a fight in the dungeon
    //! when the mana allows it
    void handleSpells();

    //! \brief Checks if a new worker should be summoned
    //! Returns true if the action has been done and false if nothing has been done
    bool handleWorkers();

    //! \brief Checks if a room needs to be repaired and repairs if so
    //! Returns true if the action has been done and false if nothing has been done
    bool repairRooms();

    //! \brief Try to help tired creatures to reach dormitory
    //! Returns true if the action has been done and false if nothing has been done
    bool handleTiredCreatures();

    //! \brief Try to help hungry creatures to reach hatchery
    //! Returns true if the action has been done and false if nothing has been done
    bool handleHungryCreatures();

    //! \brief This function will be called once only during this player's first upkeep
    //! It should setup what is needed for the AI
    void handleFirstTurn();

private:
    //! \brief Runs the original economy chain until the economy package replaces it.
    bool legacyEconomyTurn();
    //! \brief Runs the original spell and trap paths until their owner replaces them.
    void legacySpellTrapTurn();
    //! \brief Runs the original wounded-creature, defence and attack paths until their owner replaces them.
    void legacyWarTurn();

    //! \brief try to build the most needed available room
    bool buildMostNeededRoom();

    //! \brief Try to build the given room on the given position. Returns true if the room was built and
    //! false otherwise
    bool buildRoom(RoomType roomType, int x, int y, int roomSize);

    //! \brief Returns true if the given room is needed and false otherwise
    bool checkNeedRoom(RoomType roomType);

    //! \brief Returns the number of non-worker creatures with enough HP to be sent to fight
    int countHealthyFighters() const;

    //! \brief Returns the number of healthy non-worker creatures below the minimum attack level
    int countWeakFighters() const;

    //! \brief Returns the central tile of the closest enemy dungeon temple or nullptr if there is none
    Tile* findEnemyTempleTile();

    //! \brief Fills the tiles where a door can be built (entrances of the rooms) and the tiles in the
    //! corridor right in front of them (trap places)
    void findChokePoints(std::vector<Tile*>& doorTiles, std::vector<Tile*>& trapTiles);

    //! \brief Removes every call to war banner owned by this AI
    void removeBanners();

    //! \brief Returns a random cooldown between min and max, scaled by the AI reaction time
    int scaledCooldown(int min, int max) const;

    //! \brief Reaction time in percent of the base cooldowns (lower is faster)
    int mReactionPercent;
    //! \brief The difficulty selected when the controller was created.
    KeeperAIType mType;
    //! \brief The common mind uses the selected level independently of the interim legacy paths.
    Mind mMind;
    //! \brief Creatures below this percentage of their max HP are not sent to fight (lower is more aggressive)
    int mMinHpPercentToFight;
    //! \brief The AI attacks with more healthy fighters than this (0 = never attacks)
    int mMinFightersToAttack;
    //! \brief Fighters below this level are too weak for an attack; the AI waits while more of them exist than this value
    int mMinCreatureLevel;
    //! \brief Maximum number of trap tiles (without doors) the AI owns
    int mMaxTrapTiles;
    //! \brief Maximum number of doors the AI owns
    int mMaxDoors;
    int mCooldownTraps;
    int mCooldownSpells;
    //! \brief True while a call to war banner placed to defend the dungeon is out
    bool mIsDefenseBannerOut;
    //! \brief True while the AI is sending its fighters against an enemy dungeon
    bool mIsAttacking;
    //! \brief Number of healthy fighters when the attack started. Used to decide when to retreat
    int mNbFightersAtAttackStart;
    int mCooldownAttack;
    int mCooldownCheckTreasury;
    int mCooldownLookingForRooms;
    int mCooldownLookingForRoomsMin;
    int mCooldownLookingForRoomsMax;
    int mRoomPosX;
    int mRoomPosY;
    int mRoomSize;
    bool mNoMoreReachableGold;
    int mCooldownLookingForGold;
    int mCooldownDefense;
    int mCooldownDefenseMin;
    int mCooldownDefenseMax;
    int mCooldownWorkers;
    int mCooldownRepairRooms;
    int mCooldownSaveWoundedCreatures;
    int mCooldownSaveWoundedCreaturesMin;
    int mCooldownSaveWoundedCreaturesMax;
    bool mIsFirstUpkeepDone;
};

#endif // KEEPERAI_H
