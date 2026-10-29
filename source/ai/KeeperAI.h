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
    //! \brief Creates a keeper AI. The cooldown pairs are the range of turns between two checks of the
    //! defense, of saving wounded creatures and of looking for rooms.
    //! \param type Difficulty used for the keeper's ghost product choices.
    //! \param reactionPercent Reaction time in percent of the base cooldowns (lower is faster)
    //! \param minHpPercentToFight Creatures below this percentage of their max HP are not sent to fight
    //! \param minFightersToAttack The AI attacks with more healthy fighters than this (0 = never attacks)
    //! \param minCreatureLevel Fighters below this level are too weak for an attack
    //! \param maxTrapTiles Maximum number of trap tiles (without doors) the AI owns
    //! \param maxDoors Maximum number of doors the AI owns
    KeeperAI(GameMap& gameMap, Player& player, KeeperAIType type, int cooldownDefenseMin, int cooldownDefenseMax,
             int cooldownSaveWoundedCreaturesMin, int cooldownSaveWoundedCreaturesMax,
             int cooldownLookingForRoomsMin, int cooldownLookingForRoomsMax,
             int reactionPercent, int minHpPercentToFight, int minFightersToAttack,
             int minCreatureLevel, int maxTrapTiles, int maxDoors);
    virtual bool doTurn(double timeSinceLastTurn);
    //! \brief The map this AI plays on, for the decision functions of the SPELL and TRAP namespaces.
    GameMap& getGameMap() { return mGameMap; }
    //! \brief The player this AI controls, for the decision functions of the SPELL and TRAP namespaces.
    Player& getControlledPlayer() { return mPlayer; }
    //! \brief The mind that draws the mistakes of this AI and schedules its actions (defined with the mind).
    Mind& getMind();
    //! \brief The values of the AI level of this AI (defined with the mind).
    const AiSettings& getSettings() const;
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
    //! \brief try to build the most needed available room
    bool buildMostNeededRoom();

    //! \brief Try to build the given room on the given position. Returns true if the room was built and
    //! false otherwise
    bool buildRoom(RoomType roomType, int x, int y, int roomSize);

    //! \brief Returns true if the given room is needed and false otherwise
    bool checkNeedRoom(RoomType roomType);

    //! \brief Returns a random cooldown between min and max, scaled by the AI reaction time
    int scaledCooldown(int min, int max) const;

    //! \brief Reaction time in percent of the base cooldowns (lower is faster)
    int mReactionPercent;
    //! \brief The difficulty selected when the controller was created.
    KeeperAIType mType;
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
