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

#include "ai/KeeperAI.h"
#include "ai/KeeperAIType.h"
#include "ai/AiActions.h"

#include "creatureaction/CreatureAction.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/SkillManager.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomManager.h"
#include "rooms/RoomType.h"
#include "spells/Spell.h"
#include "spells/SpellCallToWar.h"
#include "spells/SpellType.h"
#include "spells/SpellSummonWorker.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <functional>
#include <vector>

// Contains the rooms the AI will try to build. It will try to build them in the given order
// (the compiled room plan, equal to the [RoomPlan] section of ai.cfg; the treasury is planned twice)
static const std::vector<RoomType> wantedBuildings = {
    RoomType::treasury,
    RoomType::dormitory,
    RoomType::hatchery,
    RoomType::tavern,
    RoomType::library,
    RoomType::trainingHall,
    RoomType::workshop,
    RoomType::casino,
    RoomType::toilet,
    RoomType::treasury,
    RoomType::merchant,
    RoomType::guardRoom,
    RoomType::herbGarden,
    RoomType::arena,
    RoomType::prison,
    RoomType::alchemyLab,
    RoomType::infirmary,
    RoomType::ghostRoom,
    RoomType::spa,
    RoomType::crypt,
    RoomType::temple,
    RoomType::torture
};

//! \brief The names of the entries of wantedBuildings in the [RoomPlan] section of ai.cfg (the name-to-room map)
static const std::vector<std::string> wantedBuildingKeys = {
    "treasury", "dormitory", "hatchery", "tavern", "library", "training", "workshop", "casino", "toilet", "treasury2",
    "merchant", "guard", "herbgarden", "arena", "prison", "alchemy", "infirmary", "ghostroom", "spa", "crypt",
    "temple", "torture"
};

//! \brief The tiles of each entry of wantedBuildings (the compiled tiles of the [RoomPlan] section of ai.cfg)
static const std::vector<uint32_t> wantedBuildingTiles = {
    9, 25, 25, 16, 25, 25, 25, 16, 9, 25, 16, 9, 9, 25, 16, 9, 16, 16, 16, 16, 25, 16
};

// LEGACY-AI
//! Interim normal settings for the legacy paths while their replacements are being implemented.
static const int NORMAL_COOLDOWN_DEFENSE_MIN = 0;
static const int NORMAL_COOLDOWN_DEFENSE_MAX = 5;
static const int NORMAL_COOLDOWN_SAVE_WOUNDED_MIN = 0;
static const int NORMAL_COOLDOWN_SAVE_WOUNDED_MAX = 5;
static const int NORMAL_COOLDOWN_LOOKING_FOR_ROOMS_MIN = 30;
static const int NORMAL_COOLDOWN_LOOKING_FOR_ROOMS_MAX = 50;
static const int NORMAL_REACTION_PERCENT = 100;
static const int NORMAL_MIN_HP_PERCENT_TO_FIGHT = 20;
static const int NORMAL_MIN_FIGHTERS_TO_ATTACK = 11;
static const int NORMAL_MIN_CREATURE_LEVEL = 4;

//! \brief Converts the keeper's percentage margin and item discounts to shares.
static const double GHOST_VALUE_PERCENT = 100.0;


//! \brief Creates a keeper whose mind reads the selected level's configured values.
KeeperAI::KeeperAI(GameMap& gameMap, Player& player, KeeperAIType type) :
    BaseAI(gameMap, player),
    mReactionPercent(NORMAL_REACTION_PERCENT),
    mType(type),
    mSettings(ConfigManager::getSingleton().getAiLevel(type)),
    mMind(gameMap, player, mSettings),
    mEvents(*this),
    mMinHpPercentToFight(NORMAL_MIN_HP_PERCENT_TO_FIGHT),
    mMinFightersToAttack(NORMAL_MIN_FIGHTERS_TO_ATTACK),
    mMinCreatureLevel(NORMAL_MIN_CREATURE_LEVEL),
    mIsAttacking(false),
    mNbFightersAtAttackStart(0),
    mCooldownAttack(0),
    mCooldownCheckTreasury(0),
    mCooldownLookingForRooms(0),
    mCooldownLookingForRoomsMin(NORMAL_COOLDOWN_LOOKING_FOR_ROOMS_MIN),
    mCooldownLookingForRoomsMax(NORMAL_COOLDOWN_LOOKING_FOR_ROOMS_MAX),
    mRoomPosX(-1),
    mRoomPosY(-1),
    mRoomSize(-1),
    mNoMoreReachableGold(false),
    mCooldownLookingForGold(0),
    mCooldownDefense(0),
    mCooldownDefenseMin(NORMAL_COOLDOWN_DEFENSE_MIN),
    mCooldownDefenseMax(NORMAL_COOLDOWN_DEFENSE_MAX),
    mCooldownWorkers(0),
    mCooldownSaveWoundedCreatures(0),
    mCooldownSaveWoundedCreaturesMin(NORMAL_COOLDOWN_SAVE_WOUNDED_MIN),
    mCooldownSaveWoundedCreaturesMax(NORMAL_COOLDOWN_SAVE_WOUNDED_MAX),
    mIsFirstUpkeepDone(false)
{
    ACTS::bind(*this);
    mEvents.bind();
    // The war rows react to their events after the shared reaction delay
    std::function<void(const AiEvent&)> warHandler = std::bind(&KeeperAI::handleWarEvent, this, std::placeholders::_1);
    mMind.onEvent("J01", std::vector<AiEventType>(1, AiEventType::Fight), warHandler);
    mMind.onEvent("J05", std::vector<AiEventType>(1, AiEventType::HeartCritical), warHandler);
    mMind.onEvent("J07", std::vector<AiEventType>(1, AiEventType::EnemyOut), warHandler);
    mMind.onEvent("J08", std::vector<AiEventType>(1, AiEventType::FightOver), warHandler);
    mMind.onEvent("K08", std::vector<AiEventType>(1, AiEventType::EnemyTrapEmpty), warHandler);
    std::function<void(std::vector<AiMath::AiStateLine>&)> warSaver = std::bind(&KeeperAI::saveWarRows, this, std::placeholders::_1);
    mMind.onSave(warSaver);
}

int KeeperAI::scaledCooldown(int min, int max) const
{
    return Random::Int((min * mReactionPercent) / 100, (max * mReactionPercent) / 100);
}

//! \brief Advances the shared mind and the paths still waiting for their owner packages.
bool KeeperAI::doTurn(double timeSinceLastTurn)
{
    // If we have no dungeon temple, we are dead
    if(getDungeonTemple() == nullptr)
        return false;
    mMind.doTurn(timeSinceLastTurn);
    runWar();
    return legacyEconomyTurn();
}

//! \brief Returns the common scheduler to the action and decision owners.
Mind& KeeperAI::getMind()
{
    return mMind;
}

//! \brief Retains raw symptom timing and forwards each game notice to the shared reaction queue.
void KeeperAI::notifyEvent(const AiEvent& event)
{
    mEvents.notify(event);
    mMind.enqueue(event);
}

//! \brief Returns the configured level values used by the decision functions.
const AiSettings& KeeperAI::getSettings() const
{
    return mSettings;
}

//! \brief Saves the complete shared mind inside the seat's AIState block.
void KeeperAI::exportState(std::ostream& os) const
{
    mMind.exportState(os);
}

//! \brief Restores the complete shared mind from the saved block contents.
bool KeeperAI::importState(const std::vector<std::string>& lines)
{
    bool restored = mMind.importState(lines);
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::importRows(env, mMind.savedRows());
    return restored;
}

//! \brief Appends the war and sighting lines to the saved AI state of the mind.
void KeeperAI::saveWarRows(std::vector<AiMath::AiStateLine>& lines)
{
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::exportRows(env, lines);
}

//! \brief Runs the polled parts of the war (plan step, tunnel probe, assault steps, enemy edges) once per turn.
void KeeperAI::runWar()
{
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::doTurn(env);
}

//! \brief Hands an event of the war rows to the war module after the reaction delay of the Mind.
void KeeperAI::handleWarEvent(const AiEvent& event)
{
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::onEvent(env, event);
}

//! \brief Preserves the first-turn setup and economy chain, excluding the removed repair action.
bool KeeperAI::legacyEconomyTurn()
{
    if(!mIsFirstUpkeepDone)
    {
        mIsFirstUpkeepDone = true;
        handleFirstTurn();
    }


    if (handleWorkers())
        return true;
    if (checkTreasury())
        return true;
    if (handleRooms())
        return true;
    if (lookForGold())
        return true;
    if(handleTiredCreatures())
        return true;
    if(handleHungryCreatures())
        return true;
    return true;
}

bool KeeperAI::checkTreasury()
{
    // If the treasury gets destroyed, we don't want the AI to build each turn the
    // free treasury
    if(mCooldownCheckTreasury > 0)
    {
        --mCooldownCheckTreasury;
        return false;
    }
    mCooldownCheckTreasury = scaledCooldown(10, 30);

    int totalGold = 0;
    int totalStorage = 0;
    for(Room* room : mGameMap.getRooms())
    {
        if(room->getSeat() != mPlayer.getSeat())
            continue;

        totalGold += room->getTotalGoldStored();
        totalStorage += room->getTotalGoldStorage();
    }

    // We want at least to be allowed to store 3000 gold
    if(totalStorage >= 3000)
        return false;

    // The treasury is too small, we try to increase it
    // A treasury can be built if we have none (in this case, it is free). Otherwise,
    // we check if we have enough gold
    if((totalStorage > 0) && (totalGold < RoomManager::costPerTile(RoomType::treasury)))
        return false;

    Tile* central = getDungeonTemple()->getCentralTile();

    Creature* worker = mGameMap.getWorkerForPathFinding(mPlayer.getSeat());
    if (worker == nullptr)
        return false;

    // We try in priority to gold next to an existing treasury
    std::vector<Room*> treasuriesOwned = mGameMap.getRoomsByTypeAndSeat(RoomType::treasury, mPlayer.getSeat());
    for(Room* treasury : treasuriesOwned)
    {
        for(Tile* tile : treasury->getCoveredTiles())
        {
            for(Tile* neigh : tile->getAllNeighbors())
            {
                if(neigh->isBuildableUpon(mPlayer.getSeat()) &&
                   mGameMap.pathExists(worker, central, neigh))
                {
                    std::vector<Tile*> tiles;
                    tiles.push_back(neigh);

                    if(!RoomManager::buildRoomOnTiles(&mGameMap, RoomType::treasury, &mPlayer, tiles))
                        return false;

                    return true;
                }
            }
        }
    }

    int widerSide = mGameMap.getMapSizeX() > mGameMap.getMapSizeY() ?
        mGameMap.getMapSizeX() : mGameMap.getMapSizeY();

    // If we have found no tile available to an existing treasury, we search for the closest
    // buildable claimed tile available
    Tile* firstAvailableTile = nullptr;
    for(int32_t distance = 1; distance < widerSide; ++distance)
    {
        for(int k = 0; k <= distance; ++k)
        {
            Tile* t;
            // North-East
            t = mGameMap.getTile(central->getX() + k, central->getY() + distance);
            if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
               mGameMap.pathExists(worker, central, t))
            {
                firstAvailableTile = t;
                break;
            }
            // North-West
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() - k, central->getY() + distance);
                if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
                   mGameMap.pathExists(worker, central, t))
                {
                    firstAvailableTile = t;
                    break;
                }
            }
            // South-East
            t = mGameMap.getTile(central->getX() + k, central->getY() - distance);
            if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
               mGameMap.pathExists(worker, central, t))
            {
                firstAvailableTile = t;
                break;
            }
            // South-West
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() - k, central->getY() - distance);
                if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
                   mGameMap.pathExists(worker, central, t))
                {
                    firstAvailableTile = t;
                    break;
                }
            }
            // East-North
            t = mGameMap.getTile(central->getX() + distance, central->getY() + k);
            if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
               mGameMap.pathExists(worker, central, t))
            {
                firstAvailableTile = t;
                break;
            }
            // East-South
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() + distance, central->getY() - k);
                if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
                   mGameMap.pathExists(worker, central, t))
                {
                    firstAvailableTile = t;
                    break;
                }
            }
            // West-North
            t = mGameMap.getTile(central->getX() - distance, central->getY() + k);
            if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
               mGameMap.pathExists(worker, central, t))
            {
                firstAvailableTile = t;
                break;
            }
            // West-South
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() - distance, central->getY() - k);
                if(t != nullptr && t->isBuildableUpon(mPlayer.getSeat()) &&
                   mGameMap.pathExists(worker, central, t))
                {
                    firstAvailableTile = t;
                    break;
                }
            }
        }

        if(firstAvailableTile != nullptr)
            break;
    }

    // We couldn't find any available tile T_T
    // We return true to avoid doing something else to let workers claim
    if(firstAvailableTile == nullptr)
        return true;

    std::vector<Tile*> tiles;
    tiles.push_back(firstAvailableTile);

    if(!RoomManager::buildRoomOnTiles(&mGameMap, RoomType::treasury, &mPlayer, tiles))
        return false;

    return true;
}

bool KeeperAI::handleRooms()
{
    if(mCooldownLookingForRooms > 0)
    {
        --mCooldownLookingForRooms;
        return false;
    }

    mCooldownLookingForRooms = Random::Int(mCooldownLookingForRoomsMin, mCooldownLookingForRoomsMax);

    // We check if the last built room is done
    if(mRoomSize != -1)
    {
        Tile* tile = mGameMap.getTile(mRoomPosX, mRoomPosY);
        if(tile == nullptr)
        {
            OD_LOG_ERR("mRoomPosX=" + Helper::toString(mRoomPosX) + ", mRoomPosY=" + Helper::toString(mRoomPosY));
            mRoomSize = -1;
            return false;
        }
        int32_t points;
        if(!computePointsForRoom(tile, mPlayer.getSeat(), mRoomSize, true, false, points))
        {
            // The room is not valid anymore (may be claimed or built by somebody else). We redo
            mRoomSize = -1;
            return false;
        }

        if(buildMostNeededRoom())
        {
            mRoomSize = -1;
            return true;
        }

        return false;
    }

    Tile* central = getDungeonTemple()->getCentralTile();
    int32_t bestX = 0;
    int32_t bestY = 0;
    if(!findBestPlaceForRoom(central, mPlayer.getSeat(), 5, true, bestX, bestY))
        return false;

    mRoomSize = 5;
    mRoomPosX = bestX;
    mRoomPosY = bestY;

    Tile* tileDest = mGameMap.getTile(mRoomPosX, mRoomPosY);
    if(tileDest == nullptr)
    {
        OD_LOG_ERR("tileDest=" + Tile::displayAsString(tileDest) + ", mRoomPosX=" + Helper::toString(mRoomPosX) + ", mRoomPosY=" + Helper::toString(mRoomPosY));
        return false;
    }
    if(!digWayToTile(central, tileDest))
        return false;

    for(int xx = 0; xx < mRoomSize; ++xx)
    {
        for(int yy = 0; yy < mRoomSize; ++yy)
        {
            Tile* tile = mGameMap.getTile(mRoomPosX + xx, mRoomPosY + yy);
            if(tile == nullptr)
            {
                OD_LOG_ERR("xx=" + Helper::toString(mRoomPosX + xx) + ", yy=" + Helper::toString(mRoomPosY + yy));
                continue;
            }

            tile->setMarkedForDigging(true, &mPlayer);
        }
    }

    return true;
}

bool KeeperAI::lookForGold()
{
    if (mNoMoreReachableGold)
        return false;

    if(mCooldownLookingForGold > 0)
    {
        --mCooldownLookingForGold;
        return false;
    }

    mCooldownLookingForGold = scaledCooldown(70, 120);

    // Do we need gold ?
    int emptyStorage = 0;
    for(Room* room : mGameMap.getRooms())
    {
        if(room->getSeat() != mPlayer.getSeat())
            continue;

        emptyStorage += (room->getTotalGoldStorage() - room->getTotalGoldStored());
    }

    // No need to search for gold
    if(emptyStorage < 100)
        return false;

    Tile* central = getDungeonTemple()->getCentralTile();
    int widerSide = mGameMap.getMapSizeX() > mGameMap.getMapSizeY() ?
        mGameMap.getMapSizeX() : mGameMap.getMapSizeY();

    // We search for the closest gold tile
    Tile* firstGoldTile = nullptr;
    for(int32_t distance = 1; distance < widerSide; ++distance)
    {
        for(int k = 0; k <= distance; ++k)
        {
            Tile* t;
            // North-East
            t = mGameMap.getTile(central->getX() + k, central->getY() + distance);
            if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
            {
                // If we already have a tile at same distance, we randomly change to
                // try to not be too predictable
                if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                    firstGoldTile = t;
            }
            // North-West
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() - k, central->getY() + distance);
                if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
                {
                    if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                        firstGoldTile = t;
                }
            }
            // South-East
            t = mGameMap.getTile(central->getX() + k, central->getY() - distance);
            if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
            {
                if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                    firstGoldTile = t;
            }
            // South-West
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() - k, central->getY() - distance);
                if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
                {
                    if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                        firstGoldTile = t;
                }
            }
            // East-North
            t = mGameMap.getTile(central->getX() + distance, central->getY() + k);
            if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
            {
                if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                    firstGoldTile = t;
            }
            // East-South
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() + distance, central->getY() - k);
                if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
                {
                    if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                        firstGoldTile = t;
                }
            }
            // West-North
            t = mGameMap.getTile(central->getX() - distance, central->getY() + k);
            if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
            {
                if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                    firstGoldTile = t;
            }
            // West-South
            if(k > 0)
            {
                t = mGameMap.getTile(central->getX() - distance, central->getY() - k);
                if(t != nullptr && t->getType() == TileType::gold && t->getFullness() > 0.0)
                {
                    if((firstGoldTile == nullptr) || (Random::Uint(1,2) == 1))
                        firstGoldTile = t;
                }
            }

            if(firstGoldTile != nullptr)
                break;
        }

        // If we found a tile, no need to continue
        if(firstGoldTile != nullptr)
            break;
    }

    // No more gold
    if (firstGoldTile == nullptr)
    {
        mNoMoreReachableGold = true;
        return false;
    }

    if(!digWayToTile(central, firstGoldTile))
    {
        mNoMoreReachableGold = true;
        return false;
    }

    // If the neighbors are gold, we dig them
    const int levelTilesDig = 2;
    std::set<Tile*> tilesDig;
    // Because we can't insert Tiles in tilesDig while iterating, we use a copy: tilesDigTmp
    std::set<Tile*> tilesDigTmp;
    tilesDig.insert(firstGoldTile);

    for(int i = 0; i < levelTilesDig; ++i)
    {
        tilesDigTmp = tilesDig;
        for(Tile* tile : tilesDigTmp)
        {
            for(Tile* neigh : tile->getAllNeighbors())
            {
                if(neigh->getType() == TileType::gold && neigh->getFullness() > 0.0)
                    tilesDig.insert(neigh);
            }
        }
    }

    for(Tile* tile : tilesDig)
        tile->setMarkedForDigging(true, &mPlayer);

    return true;
}

bool KeeperAI::buildMostNeededRoom()
{
    for(RoomType roomType: wantedBuildings)
    {
        if(!checkNeedRoom(roomType))
            continue;

        if(!SkillManager::isRoomAvailable(roomType, mPlayer.getSeat()))
            continue;

        if(buildRoom(roomType, mRoomPosX, mRoomPosY, mRoomSize))
            return true;

    }
    return false;
}

bool KeeperAI::buildRoom(RoomType roomType, int x, int y, int roomSize)
{
    std::vector<Tile*> tiles = mGameMap.getBuildableTilesForPlayerInArea(x, y, x + roomSize - 1,
        y + roomSize - 1, &mPlayer);
    if (tiles.size() < static_cast<uint32_t>(roomSize * roomSize))
        return false;

    if(!RoomManager::buildRoomOnTiles(&mGameMap, roomType, &mPlayer, tiles))
        return false;

    OD_LOG_INF("AI seatId=" + Helper::toString(mPlayer.getSeat()->getId())+ " builds room type=" + Helper::toString(static_cast<uint32_t>(roomType)) + ", x=" + Helper::toString(x) + ", y=" + Helper::toString(y) + ", roomSize=" + Helper::toString(roomSize));
    return true;
}

bool KeeperAI::checkNeedRoom(RoomType roomType)
{
    // We should try to build one room of each except special rooms (like bridges)
    switch(roomType)
    {
        case RoomType::dormitory:
        {
            // If we have no dormitory, we try to build 1. If we already have one, we try to build another
            // if nothing else can be built
            if(mPlayer.getSeat()->getNbRooms(roomType) <= 0)
                return true;

            // If too many dormitories, no need to build more
            if(mPlayer.getSeat()->getNbRooms(roomType) > 1)
                return false;

            for(RoomType roomType: wantedBuildings)
            {
                if(roomType == RoomType::dormitory)
                    continue;

                if(!checkNeedRoom(roomType))
                    continue;

                if(!SkillManager::isRoomAvailable(roomType, mPlayer.getSeat()))
                    continue;

                // Another room is needed
                return false;
            }

            return true;
        }
        case RoomType::treasury:
        {
            int totalStorage = mPlayer.getSeat()->getGoldMax();
            int totalGold = mPlayer.getSeat()->getGold();

            if(((totalStorage - totalGold) < 200) && (totalGold < 20000))
                return true;

            return false;
        }
        case RoomType::bridgeWooden:
        case RoomType::bridgeStone:
            return false;

        default:
        {
            if(mPlayer.getSeat()->getNbRooms(roomType) <= 0)
                return true;

            return false;
        }
    }
}


bool KeeperAI::handleWorkers()
{
    if(mCooldownWorkers > 0)
    {
        --mCooldownWorkers;
        return false;
    }

    mCooldownWorkers = scaledCooldown(3, 10);

    // We want to use the first covered tile because the central might be destroyed and enemy claimed
    // and, if it is the case, we will not be able to spawn a worker.
    int mana = static_cast<int>(mPlayer.getSeat()->getMana());
    int summonCost = SpellSummonWorker::getNextWorkerPriceForPlayer(&mGameMap, &mPlayer);
    if(mana < summonCost)
        return false;


    // If we have less than 4 workers or we have the chance, we summon
    int nbWorkers = mPlayer.getSeat()->getNumCreaturesWorkers();
    if((nbWorkers < 4) ||
       (Random::Int(0, nbWorkers * 3) == 0))
    {
        Tile* tile = getDungeonTemple()->getCoveredTile(0);
        std::vector<Tile*> tiles;
        tiles.push_back(tile);
        if(!SpellSummonWorker::summonWorkersOnTiles(&mGameMap, &mPlayer, tiles))
            return false;

        return true;
    }

    return false;
}

bool KeeperAI::handleTiredCreatures()
{
    // Handle tired creatures if we have a dormitory
    if(mPlayer.getSeat()->getNbRooms(RoomType::dormitory) <= 0)
        return false;

    std::vector<Creature*> creatures = mGameMap.getCreaturesBySeat(mPlayer.getSeat());
    for(Creature* creature : creatures)
    {
        // We do not take creatures fighting
        if(creature->isActionInList(CreatureActionType::fight))
            continue;

        if(!creature->isTired())
            continue;

        Tile* dropTile = nullptr;
        // If the creature has a bed, we drop it in its dormitory
        Tile* homeTile = creature->getHomeTile();
        if(homeTile != nullptr)
        {
            // We check if it is already in the dormitory. If yes, do nothing
            Tile* posTile = creature->getPositionTile();
            if(posTile == nullptr)
            {
                OD_LOG_ERR("null position tile for creature=" + creature->getName() + ", pos=" + Helper::toString(creature->getPosition()));
                continue;
            }
            if(homeTile->getCoveringRoom() == posTile->getCoveringRoom())
                continue;

            // It is not on its dormitory, we try to drop it there
            dropTile = homeTile;
        }
        else
        {
            // The creature do not have a home tile. We check it can reach the
            // dungeon temple. If not, we drop it there
            Tile* posTile = creature->getPositionTile();
            if(posTile == nullptr)
            {
                OD_LOG_ERR("null position tile for creature=" + creature->getName() + ", pos=" + Helper::toString(creature->getPosition()));
                continue;
            }

            Tile* dungeonTempleTile = getDungeonTemple()->getCentralTile();
            if(mGameMap.pathExists(creature, posTile, dungeonTempleTile))
                continue;

            // The creature cannot reach its dungeon temple. We drop it there
            dropTile = dungeonTempleTile;
        }

        if(dropTile == nullptr)
            continue;

        if(!creature->tryPickup(mPlayer.getSeat()))
            continue;

        mPlayer.pickUpEntity(creature);

        mPlayer.dropHand(dropTile);

        // We help only 1 creature per turn
        return true;
    }

    return false;
}

bool KeeperAI::handleHungryCreatures()
{
    // Handle hungry creatures if we have a hatchery
    if(mPlayer.getSeat()->getNbRooms(RoomType::hatchery) <= 0)
        return false;

    std::vector<Creature*> creatures = mGameMap.getCreaturesBySeat(mPlayer.getSeat());
    for(Creature* creature : creatures)
    {
        // We do not take creatures fighting
        if(creature->isActionInList(CreatureActionType::fight))
            continue;

        if(!creature->isHungry())
            continue;

        // We check it can reach the dungeon temple. If not, we drop it there
        Tile* posTile = creature->getPositionTile();
        if(posTile == nullptr)
        {
            OD_LOG_ERR("null position tile for creature=" + creature->getName() + ", pos=" + Helper::toString(creature->getPosition()));
            continue;
        }

        Tile* dungeonTempleTile = getDungeonTemple()->getCentralTile();
        if(mGameMap.pathExists(creature, posTile, dungeonTempleTile))
            continue;

        // The creature cannot reach its dungeon temple. We drop it there
        if(!creature->tryPickup(mPlayer.getSeat()))
            continue;

        mPlayer.pickUpEntity(creature);

        mPlayer.dropHand(dungeonTempleTile);

        // We help only 1 creature per turn
        return true;
    }

    return false;
}

void KeeperAI::handleFirstTurn()
{
    Seat* seat = mPlayer.getSeat();
    // We set the skills to research. We start with pending skills to not modify research
    // order if it was already set in the level
    std::vector<SkillType> skills = seat->getSkillPending();
    SkillManager::buildRandomPendingSkillsForSeat(skills, seat);
    seat->setSkillTree(skills);
}

//! \brief The room plan from ai.cfg mapped to room types, or the compiled plan when ai.cfg has none.
std::vector<std::pair<RoomType, uint32_t>> KeeperAI::getRoomPlan()
{
    std::vector<std::pair<RoomType, uint32_t>> plan;
    const std::vector<std::pair<std::string, uint32_t>>& configPlan = ConfigManager::getSingleton().getAiRoomPlan();
    if(configPlan.empty())
    {
        for(uint32_t i = 0; i < wantedBuildings.size(); ++i)
            plan.push_back(std::make_pair(wantedBuildings[i], wantedBuildingTiles[i]));
        return plan;
    }

    for(const std::pair<std::string, uint32_t>& entry : configPlan)
    {
        std::vector<std::string>::const_iterator it = std::find(wantedBuildingKeys.begin(), wantedBuildingKeys.end(), entry.first);
        if(it == wantedBuildingKeys.end())
        {
            OD_LOG_ERR("Unknown room in the AI room plan=" + entry.first);
            continue;
        }
        plan.push_back(std::make_pair(wantedBuildings[it - wantedBuildingKeys.begin()], entry.second));
    }
    return plan;
}

//! \brief Re-evaluates real keeper resources and eligible buyers before every product.
void KeeperAI::updateGhostRoomSettings(Seat& seat)
{
    Player* player = seat.getPlayer();
    if(player == nullptr || player->getIsHuman())
        return;
    GameMap* map = seat.getGameMap();
    if(map == nullptr)
        return;
    KeeperAI* ai = dynamic_cast<KeeperAI*>(map->getAI(*player));
    if(ai == nullptr)
        return;
    seat.setGhostRevive(true);
    const bool researchLeft = !SkillManager::isAllSkillsDoneForSeat(&seat);
    if(ai->mType == KeeperAIType::easy)
    {
        seat.setGhostProduct(researchLeft ? GhostProduct::research : GhostProduct::mana);
        return;
    }
    const ConfigManager& config = ConfigManager::getSingleton();
    const double manaProduct = config.getRoomConfigDouble("GhostEctoplasmMana");
    const double researchValue = researchLeft ? config.getRoomConfigDouble("GhostEctoplasmResearchPoints") *
        config.getGhostAiGoldPerResearchPoint() : 0.0;
    const double manaValue = seat.getMana() > config.getMaxManaPerSeat() - manaProduct ? 0.0 :
        manaProduct / (config.getSpellConfigDouble("CreateGoldPrice") / config.getSpellConfigDouble("CreateGoldValue"));
    double crystalValue = 0.0;
    const Creature* buyer = nullptr;
    if(!map->getRoomsByTypeAndSeat(RoomType::merchant, &seat).empty())
    {
        for(Creature* creature : map->getCreaturesBySeat(&seat))
        {
            if(!creature->isAlive())
                continue;
            const double price = config.getSoulCrystalPrice() * (1.0 + seat.getMerchantMargin() / GHOST_VALUE_PERCENT) *
                std::max(0.0, 1.0 - creature->getItemEffect("Thrift") / GHOST_VALUE_PERCENT);
            if(!creature->wantsSoulCrystal(price))
                continue;
            if(buyer == nullptr || creature->getLevel() > buyer->getLevel())
                buyer = creature;
        }
    }
    if(buyer != nullptr)
        crystalValue = config.getSoulCrystalPrice() * config.getRoomConfigDouble("MerchantBuyShare") +
            config.getSoulCrystalPrice() * seat.getMerchantMargin() / GHOST_VALUE_PERCENT +
            buyer->getDefinition()->getXPNeededWhenLevel(buyer->getLevel()) * config.getGhostAiGoldPerXp();
    // The other products are valued per ectoplasm, a crystal takes several of them.
    crystalValue /= config.getRoomConfigDouble("GhostEctoplasmPerCrystal");
    GhostProduct product = GhostProduct::crystal;
    double bestValue = 0.0;
    if(researchValue > bestValue) { bestValue = researchValue; product = GhostProduct::research; }
    if(manaValue > bestValue) { bestValue = manaValue; product = GhostProduct::mana; }
    if(crystalValue > bestValue) { product = GhostProduct::crystal; }
    seat.setGhostProduct(product);
}
