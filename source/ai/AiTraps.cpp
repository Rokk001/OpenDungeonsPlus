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

#include "ai/AiTraps.h"

#include "ai/AiActions.h"
#include "ai/AiKnowledge.h"
#include "ai/AiMind.h"
#include "ai/KeeperAI.h"

#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "gamemap/GameMap.h"
#include "ODApplication.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "traps/Trap.h"
#include "traps/TrapDoor.h"
#include "traps/TrapManager.h"
#include "traps/TrapType.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <cstdlib>
#include <limits>
#include <map>
#include <set>
#include <string>

namespace
{
//! \brief What the trap rows remember between two trap looks of one seat.
struct TrapState
{
    TrapState() : mWantDivided(-1), mWatching(false), mLastTestSeconds(-1.0e18), mExhausted(false), mTunnelX(-1), mTunnelY(-1) {}
    //! \brief The draw of row F01 (once per game): -1 not drawn yet, 1 half the trap tiles, 0 the full number.
    int mWantDivided;
    //! \brief True while the AI thinks of its empty traps after a fight (row F12).
    bool mWatching;
    //! \brief Game time of the last test for an exhausted own trap tile (row F12).
    double mLastTestSeconds;
    //! \brief The result of that test.
    bool mExhausted;
    //! \brief The tile where the fortified tunnel breaks into the AI's land, -1 when none (row F15).
    int mTunnelX;
    int mTunnelY;
};

std::map<int, TrapState> trapStates;

//! \brief Returns a value of the [KeeperAI] section of ai.cfg.
double aiKey(const std::string& key)
{
    return ConfigManager::getSingleton().getAiConfigDouble(key);
}

//! \brief Returns the squared distance of two tiles.
double distance2(const Tile* a, const Tile* b)
{
    double dx = a->getX() - b->getX();
    double dy = a->getY() - b->getY();
    return dx * dx + dy * dy;
}

//! \brief Returns the tile k steps from the door of the entrance in the direction a walker takes (negative k: outside).
Tile* lineTile(GameMap& gameMap, const TRAP::Entrance& entrance, int k)
{
    return gameMap.getTile(entrance.mDoor->getX() + k * entrance.mDx, entrance.mDoor->getY() + k * entrance.mDy);
}

//! \brief Tells whether a trap can be built on the tile by the seat.
bool trapSpotFree(const Tile* tile, Seat* seat)
{
    return (tile != nullptr) && !tile->isFullTile() && tile->isBuildableUpon(seat);
}

//! \brief Returns the wage bill: the sum of the fees of the fighters of the seat.
double wageBill(KeeperAI& ai)
{
    double bill = 0.0;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(ai.getControlledPlayer().getSeat()))
    {
        if(!creature->getDefinition()->isWorker())
            bill += creature->getGoldFee();
    }
    return bill;
}

//! \brief Tells whether a purchase of the given cost keeps the margins free: the room margin, the wage bill and the
//! reload margin of the traps.
bool affordable(KeeperAI& ai, double cost)
{
    double gold = ai.getControlledPlayer().getSeat()->getGold();
    return gold >= (cost + aiKey("RoomGoldMargin") + wageBill(ai) + TRAP::reloadMargin(ai));
}

//! \brief Returns the rank of a door kind: the higher, the stronger. 0 for a type that is no plain door.
int doorRank(TrapType type)
{
    switch(type)
    {
        case TrapType::doorWooden: return 1;
        case TrapType::doorIronbound: return 2;
        case TrapType::doorSteel: return 3;
        default: return 0;
    }
}

//! \brief Tells whether the trap type is a door of any kind.
bool isDoor(TrapType type)
{
    return (doorRank(type) > 0) || (type == TrapType::doorBarricade) || (type == TrapType::doorSecret) || (type == TrapType::doorRuned);
}

//! \brief Returns the best plain door the seat has researched, or nullTrapType.
TrapType bestDoor(const Seat* seat)
{
    if(SkillManager::isTrapAvailable(TrapType::doorSteel, seat))
        return TrapType::doorSteel;
    if(SkillManager::isTrapAvailable(TrapType::doorIronbound, seat))
        return TrapType::doorIronbound;
    if(SkillManager::isTrapAvailable(TrapType::doorWooden, seat))
        return TrapType::doorWooden;
    return TrapType::nullTrapType;
}

//! \brief Returns the trap of the seat that covers the tile, or nullptr.
Trap* trapAt(KeeperAI& ai, const Tile* tile)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    for(Trap* trap : ai.getGameMap().getTraps())
    {
        if(trap->getSeat() != seat)
            continue;

        std::vector<Tile*> covered = trap->getCoveredTiles();
        if(std::find(covered.begin(), covered.end(), tile) != covered.end())
            return trap;
    }
    return nullptr;
}

//! \brief Counts the trap tiles of the seat of the given type.
int countTiles(KeeperAI& ai, TrapType type)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    int count = 0;
    for(Trap* trap : ai.getGameMap().getTraps())
    {
        if((trap->getSeat() == seat) && (trap->getType() == type))
            count += static_cast<int>(trap->getCoveredTiles().size());
    }
    return count;
}

//! \brief Returns the central tile of the heart room of the seat, or nullptr.
Tile* heartTile(KeeperAI& ai)
{
    std::vector<Room*> hearts = ai.getGameMap().getRoomsByTypeAndSeat(RoomType::dungeonTemple, ai.getControlledPlayer().getSeat());
    return hearts.empty() ? nullptr : hearts[0]->getCoveredTile(0);
}

//! \brief Returns the index of the entrance whose door is nearest to the tile, or -1 for an empty list.
int nearestEntrance(const std::vector<TRAP::Entrance>& entrances, const Tile* tile, bool farthest)
{
    int result = -1;
    double bestDistance = 0.0;
    for(size_t i = 0; i < entrances.size(); ++i)
    {
        double d = distance2(entrances[i].mDoor, tile);
        if((result < 0) || (farthest ? (d > bestDistance) : (d < bestDistance)))
        {
            result = static_cast<int>(i);
            bestDistance = d;
        }
    }
    return result;
}

//! \brief Returns a free trap spot next to a tile of the rooms of the given type, or nullptr.
//! \param exceptType When true, any own room except the given type counts.
Tile* spotNextToRoom(KeeperAI& ai, RoomType type, bool exceptType)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    for(Room* room : ai.getGameMap().getRooms())
    {
        if((room->getSeat() != seat) || ((room->getType() == type) == exceptType))
            continue;

        for(Tile* roomTile : room->getCoveredTiles())
        {
            for(Tile* neighbor : roomTile->getAllNeighbors())
            {
                if(trapSpotFree(neighbor, seat))
                    return neighbor;
            }
        }
    }
    return nullptr;
}

//! \brief Builds one tile of a trap or door kind when the seat can afford it.
//! \return true when the build was scheduled.
bool buildOne(KeeperAI& ai, TrapType type, Tile* tile)
{
    if((tile == nullptr) || !SkillManager::isTrapAvailable(type, ai.getControlledPlayer().getSeat()))
        return false;

    if(!affordable(ai, TrapManager::costPerTile(type)))
        return false;

    std::vector<Tile*> tiles;
    tiles.push_back(tile);
    ACTS::buildTrap(ai, type, tiles);
    return true;
}

//! \brief Returns the length of the straight run of corridor tiles inward from the door of the entrance.
int corridorRun(GameMap& gameMap, const TRAP::Entrance& entrance)
{
    int run = 0;
    for(int k = 1; k <= static_cast<int>(aiKey("BoulderCorridorMinTiles")); ++k)
    {
        Tile* tile = lineTile(gameMap, entrance, k);
        if((tile == nullptr) || !TrapDoor::canDoorBeOnTile(&gameMap, tile))
            break;
        ++run;
    }
    return run;
}
}

std::vector<TRAP::Entrance> TRAP::findEntrances(KeeperAI& ai)
{
    GameMap& gameMap = ai.getGameMap();
    Seat* seat = ai.getControlledPlayer().getSeat();
    AiKnowledge knowledge(gameMap, seat);
    static const int dx[4] = {1, -1, 0, 0};
    static const int dy[4] = {0, 0, 1, -1};

    std::vector<Entrance> entrances;
    for(int x = 0; x < gameMap.getMapSizeX(); ++x)
    {
        for(int y = 0; y < gameMap.getMapSizeY(); ++y)
        {
            Tile* tile = gameMap.getTile(x, y);
            if((tile == nullptr) || !tile->isClaimedForSeat(seat) || tile->isFullTile() ||
               !TrapDoor::canDoorBeOnTile(&gameMap, tile))
            {
                continue;
            }

            // A known open neighbor that is not the AI's own land is where a walker comes from
            for(int i = 0; i < 4; ++i)
            {
                Tile* outside = gameMap.getTile(x + dx[i], y + dy[i]);
                if((outside == nullptr) || !knowledge.isKnown(outside) || outside->isFullTile() ||
                   outside->isClaimedForSeat(seat))
                {
                    continue;
                }

                Entrance entrance;
                entrance.mDoor = tile;
                entrance.mDx = -dx[i];
                entrance.mDy = -dy[i];
                entrances.push_back(entrance);
                break;
            }
        }
    }

    // The fortified tunnel is an entrance of its own
    std::map<int, TrapState>::const_iterator it = trapStates.find(seat->getId());
    if((it != trapStates.end()) && (it->second.mTunnelX >= 0))
    {
        Tile* tunnel = gameMap.getTile(it->second.mTunnelX, it->second.mTunnelY);
        bool known = false;
        for(const Entrance& entrance : entrances)
            known = known || (entrance.mDoor == tunnel);

        if((tunnel != nullptr) && !known)
        {
            Entrance entrance;
            entrance.mDoor = tunnel;
            entrance.mDx = 1;
            entrance.mDy = 0;
            for(int i = 0; i < 4; ++i)
            {
                Tile* outside = gameMap.getTile(tunnel->getX() + dx[i], tunnel->getY() + dy[i]);
                if((outside != nullptr) && !outside->isFullTile() && !outside->isClaimedForSeat(seat))
                {
                    entrance.mDx = -dx[i];
                    entrance.mDy = -dy[i];
                    break;
                }
            }
            entrances.push_back(entrance);
        }
    }
    return entrances;
}

void TRAP::trapLook(KeeperAI& ai)
{
    // AI row F01
    GameMap& gameMap = ai.getGameMap();
    Seat* seat = ai.getControlledPlayer().getSeat();
    TrapState& state = trapStates[seat->getId()];

    // Traps and doors are crafted in a workshop, and the AI plans them only once it has built enough kinds of rooms
    if(seat->getNbRooms(RoomType::workshop) == 0)
        return;

    std::set<RoomType> builtTypes;
    for(Room* room : gameMap.getRooms())
    {
        if(room->getSeat() == seat)
            builtTypes.insert(room->getType());
    }
    if(static_cast<double>(builtTypes.size()) < aiKey("TrapPlanMinRooms"))
        return;

    std::vector<Entrance> entrances = findEntrances(ai);
    if(entrances.empty())
        return;

    // The workshop is not done with the previous orders, so the AI orders no more
    int waiting = 0;
    int trapTiles = 0;
    for(Trap* trap : gameMap.getTraps())
    {
        if(trap->getSeat() != seat)
            continue;

        if(trap->getNbNeededCraftedTrap() > 0)
            ++waiting;
        if(!isDoor(trap->getType()))
            trapTiles += static_cast<int>(trap->getCoveredTiles().size());
    }
    if(waiting >= static_cast<int>(aiKey("MaxWaitingForCraft")))
        return;

    if(placeDoor(ai, entrances))
        return;

    // The plan: the trap tiles per entrance; the mistake of the first plan of the game halves them for good
    int want = static_cast<int>(entrances.size()) * static_cast<int>(aiKey("TrapTilesPerEntrance"));
    if(state.mWantDivided < 0)
        state.mWantDivided = ai.getMind().slip("F01") ? 1 : 0;
    if(state.mWantDivided == 1)
        want = std::max(1, want / static_cast<int>(aiKey("MistakeTrapWantDivisor")));

    placeTrap(ai, trapTiles, want, entrances);
}

bool TRAP::placeTrap(KeeperAI& ai, int trapTiles, int want, const std::vector<Entrance>& entrances)
{
    // AI row F02
    // AI row F03
    // AI row F04
    GameMap& gameMap = ai.getGameMap();
    Seat* seat = ai.getControlledPlayer().getSeat();
    if(entrances.empty())
        return false;

    // The basic mix first: spike, cannon and gas up to the planned number of tiles
    if(trapTiles < want)
    {
        // Every n-th tile is gas, the others alternate cannon and spike
        int nth = static_cast<int>(aiKey("GasEveryNthTile"));
        TrapType kind = ((trapTiles % nth) == (nth - 1)) ? TrapType::gas : ((trapTiles % 2) ? TrapType::cannon : TrapType::spike);
        if(!SkillManager::isTrapAvailable(kind, seat))
            return false;

        const Entrance& entrance = entrances[trapTiles % entrances.size()];
        int index = trapTiles / static_cast<int>(entrances.size());
        Tile* spot = nullptr;
        if(kind == TrapType::spike)
        {
            // Behind the door, where it fires when the door is open; the mistake builds it in front of the door
            bool slipped = ai.getMind().slip("F02");
            int first = static_cast<int>(aiKey("SpikeBehindDoorMinTiles")) + index;
            int last = static_cast<int>(aiKey("SpikeBehindDoorMaxTiles"));
            for(int k = first; (spot == nullptr) && (k <= last); ++k)
            {
                Tile* tile = lineTile(gameMap, entrance, slipped ? -(k - first + 1) : k);
                if(trapSpotFree(tile, seat))
                    spot = tile;
            }
        }
        else if(kind == TrapType::cannon)
        {
            // Within reach of the door with mana for its shots; the mistake does not keep the mana
            bool slipped = ai.getMind().slip("F03");
            double manaNeeded = aiKey("CannonManaPerTile") * (countTiles(ai, TrapType::cannon) + 1);
            if(!slipped && (seat->getMana() < manaNeeded))
                return false;

            for(int k = 1 + index; (spot == nullptr) && (k <= static_cast<int>(aiKey("CannonMaxDoorDistance"))); ++k)
            {
                Tile* tile = lineTile(gameMap, entrance, k);
                if(trapSpotFree(tile, seat))
                    spot = tile;
            }
        }
        else
        {
            // In front of the door; the mistake does not build it
            if(ai.getMind().slip("F04"))
                return false;

            for(int k = 1 + index; (spot == nullptr) && (k <= static_cast<int>(aiKey("CannonMaxDoorDistance"))); ++k)
            {
                Tile* tile = lineTile(gameMap, entrance, -k);
                if(trapSpotFree(tile, seat))
                    spot = tile;
            }
        }
        return buildOne(ai, kind, spot);
    }

    // Then the special traps, one per look
    Tile* heart = heartTile(ai);
    if(heart == nullptr)
        return false;

    // AI row F05
    if(SkillManager::isTrapAvailable(TrapType::boulder, seat) && (countTiles(ai, TrapType::boulder) == 0))
    {
        bool slipped = ai.getMind().slip("F05");
        for(const TRAP::Entrance& entrance : entrances)
        {
            // A straight corridor of the minimum length; the mistake takes a bend instead
            bool straight = corridorRun(gameMap, entrance) >= static_cast<int>(aiKey("BoulderCorridorMinTiles"));
            if(straight == slipped)
                continue;

            Tile* tile = lineTile(gameMap, entrance, 1);
            if(trapSpotFree(tile, seat))
                return buildOne(ai, TrapType::boulder, tile);
        }
        return false;
    }

    // AI row F06
    if(SkillManager::isTrapAvailable(TrapType::lightning, seat) && (countTiles(ai, TrapType::lightning) == 0))
    {
        bool slipped = ai.getMind().slip("F06");
        Tile* spot = nullptr;
        int innermost = nearestEntrance(entrances, heart, false);
        if(!slipped)
        {
            // Over water near a door, else at the last door (the one nearest to the heart)
            for(const TRAP::Entrance& entrance : entrances)
            {
                for(int k = 1; (spot == nullptr) && (k <= static_cast<int>(aiKey("CannonMaxDoorDistance"))); ++k)
                {
                    Tile* tile = lineTile(gameMap, entrance, k);
                    if(trapSpotFree(tile, seat) && (tile->getType() == TileType::water))
                        spot = tile;
                }
            }
        }
        if((spot == nullptr) && (innermost >= 0))
            spot = lineTile(gameMap, entrances[innermost], 1);
        return trapSpotFree(spot, seat) && buildOne(ai, TrapType::lightning, spot);
    }

    // AI row F07
    if(SkillManager::isTrapAvailable(TrapType::fireburst, seat) && (countTiles(ai, TrapType::fireburst) == 0))
    {
        // At the treasury door; the mistake builds it next to the own rooms, where the area damage hurts
        Tile* spot = nullptr;
        if(ai.getMind().slip("F07"))
        {
            spot = spotNextToRoom(ai, RoomType::dungeonTemple, true);
        }
        else
        {
            std::vector<Room*> treasuries = gameMap.getRoomsByTypeAndSeat(RoomType::treasury, seat);
            if(!treasuries.empty())
            {
                int index = nearestEntrance(entrances, treasuries[0]->getCoveredTile(0), false);
                if(index >= 0)
                    spot = lineTile(gameMap, entrances[index], 1);
            }
        }
        return trapSpotFree(spot, seat) && buildOne(ai, TrapType::fireburst, spot);
    }

    // AI row F08
    if(SkillManager::isTrapAvailable(TrapType::freeze, seat) && (countTiles(ai, TrapType::freeze) == 0))
    {
        // Before the heart room; the mistake puts it far from where the fighters stand
        int index = nearestEntrance(entrances, heart, ai.getMind().slip("F08"));
        Tile* spot = (index >= 0) ? lineTile(gameMap, entrances[index], 1) : nullptr;
        return trapSpotFree(spot, seat) && buildOne(ai, TrapType::freeze, spot);
    }

    // AI row F09
    if(SkillManager::isTrapAvailable(TrapType::alarm, seat) && (countTiles(ai, TrapType::alarm) < static_cast<int>(entrances.size())))
    {
        // The mistake builds none, so the intrusion is noticed late
        if(ai.getMind().slip("F09"))
            return false;

        for(const TRAP::Entrance& entrance : entrances)
        {
            Tile* tile = lineTile(gameMap, entrance, -static_cast<int>(aiKey("AlarmDistanceTiles")));
            if(trapSpotFree(tile, seat))
                return buildOne(ai, TrapType::alarm, tile);
        }
        return false;
    }

    // AI row F10
    if(SkillManager::isTrapAvailable(TrapType::fear, seat) && (countTiles(ai, TrapType::fear) == 0))
    {
        // In front of the heart; the mistake puts it next to the own rooms, where it scares the own creatures
        Tile* spot = nullptr;
        if(ai.getMind().slip("F10"))
        {
            spot = spotNextToRoom(ai, RoomType::dungeonTemple, true);
        }
        else
        {
            for(Tile* neighbor : heart->getAllNeighbors())
            {
                if(trapSpotFree(neighbor, seat))
                {
                    spot = neighbor;
                    break;
                }
            }
        }
        return trapSpotFree(spot, seat) && buildOne(ai, TrapType::fear, spot);
    }

    // AI row F11
    bool needBanner = SkillManager::isTrapAvailable(TrapType::watchBanner, seat) && (countTiles(ai, TrapType::watchBanner) == 0);
    bool needTrigger = SkillManager::isTrapAvailable(TrapType::trigger, seat) && (countTiles(ai, TrapType::trigger) == 0) &&
                       (countTiles(ai, TrapType::watchBanner) > 0);
    if((needBanner || needTrigger) && !entrances.empty() && !ai.getMind().slip("F11"))
    {
        // The banner stands at the entrance, the trigger on the way to the trap field
        const TRAP::Entrance& entrance = entrances[0];
        Tile* tile = lineTile(gameMap, entrance, needBanner ? -1 : 1);
        return trapSpotFree(tile, seat) && buildOne(ai, needBanner ? TrapType::watchBanner : TrapType::trigger, tile);
    }
}

bool TRAP::reloadGate(KeeperAI& ai)
{
    // AI row F12
    TrapState& state = trapStates[ai.getControlledPlayer().getSeat()->getId()];
    // The mistake: the AI forgets the reload, so the trap stays empty
    state.mWatching = !ai.getMind().slip("F12");
    state.mLastTestSeconds = -1.0e18;
    return state.mWatching;
}

double TRAP::reloadMargin(KeeperAI& ai)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    std::map<int, TrapState>::iterator it = trapStates.find(seat->getId());
    if((it == trapStates.end()) || !it->second.mWatching)
        return 0.0;

    // The empty traps are looked at again every ReloadRetrySeconds
    TrapState& state = it->second;
    double now = static_cast<double>(ai.getGameMap().getTurnNumber()) / ODApplication::turnsPerSecond;
    if((now - state.mLastTestSeconds) >= aiKey("ReloadRetrySeconds"))
    {
        state.mLastTestSeconds = now;
        state.mExhausted = false;
        for(Trap* trap : ai.getGameMap().getTraps())
        {
            if(trap->getSeat() != seat)
                continue;

            for(Tile* tile : trap->getCoveredTiles())
                state.mExhausted = state.mExhausted || trap->isTileExhausted(tile);
        }
        // Everything is loaded again: the AI stops watching
        if(!state.mExhausted)
            state.mWatching = false;
    }
    return state.mExhausted ? aiKey("TrapGoldMargin") : 0.0;
}

bool TRAP::placeDoor(KeeperAI& ai, const std::vector<Entrance>& entrances)
{
    // AI row F13
    // AI row F14
    GameMap& gameMap = ai.getGameMap();
    Seat* seat = ai.getControlledPlayer().getSeat();

    // The door of the best researched kind on every entrance; the mistake keeps the wooden door
    TrapType best = bestDoor(seat);
    TrapType kind = ai.getMind().slip("F13") ? TrapType::doorWooden : best;
    if(!SkillManager::isTrapAvailable(kind, seat))
        kind = TrapType::nullTrapType;

    for(const Entrance& entrance : entrances)
    {
        if(kind == TrapType::nullTrapType)
            break;

        Trap* current = trapAt(ai, entrance.mDoor);
        int currentRank = (current == nullptr) ? 0 : doorRank(current->getType());
        // A tile with another trap or a special door is left alone
        if((current != nullptr) && (currentRank == 0))
            continue;

        if(currentRank >= doorRank(kind))
            continue;

        if(!affordable(ai, TrapManager::costPerTile(kind)))
            return false;

        // An older door is sold first, the new one is built on the freed tile
        if(current != nullptr)
        {
            std::vector<Tile*> tiles;
            tiles.push_back(entrance.mDoor);
            ACTS::sellTrapTiles(ai, tiles);
        }
        return buildOne(ai, kind, entrance.mDoor);
    }

    // The special doors; the mistake does not use them at this look
    if(entrances.empty() || ai.getMind().slip("F14"))
        return false;

    Tile* heart = heartTile(ai);
    if(heart == nullptr)
        return false;

    std::vector<Room*> treasuries = gameMap.getRoomsByTypeAndSeat(RoomType::treasury, seat);
    struct SpecialDoor { TrapType mType; Tile* mNear; };
    SpecialDoor specials[2];
    specials[0].mType = TrapType::doorSecret;
    specials[0].mNear = treasuries.empty() ? nullptr : treasuries[0]->getCoveredTile(0);
    specials[1].mType = TrapType::doorRuned;
    specials[1].mNear = heart;
    for(int i = 0; i < 2; ++i)
    {
        if((specials[i].mNear == nullptr) || !SkillManager::isTrapAvailable(specials[i].mType, seat) ||
           (countTiles(ai, specials[i].mType) > 0))
        {
            continue;
        }

        int index = nearestEntrance(entrances, specials[i].mNear, false);
        if(index < 0)
            continue;

        Tile* door = entrances[index].mDoor;
        if(!affordable(ai, TrapManager::costPerTile(specials[i].mType)))
            return false;

        Trap* current = trapAt(ai, door);
        if(current != nullptr)
        {
            std::vector<Tile*> tiles;
            tiles.push_back(door);
            ACTS::sellTrapTiles(ai, tiles);
        }
        return buildOne(ai, specials[i].mType, door);
    }
    return false;
}

bool TRAP::fortifyTunnel(KeeperAI& ai, Tile* breakthrough)
{
    // AI row F15
    if(breakthrough == nullptr)
        return false;

    // The mistake: the AI forgets, the tunnel has no traps and no door
    if(ai.getMind().slip("F15"))
        return false;

    // The tunnel is an entrance from now on, so the trap look builds its door and the trap tiles per entrance
    TrapState& state = trapStates[ai.getControlledPlayer().getSeat()->getId()];
    state.mTunnelX = breakthrough->getX();
    state.mTunnelY = breakthrough->getY();
    trapLook(ai);

    // The barricade one step inside the tunnel (row F14)
    std::vector<Entrance> entrances = findEntrances(ai);
    for(const Entrance& entrance : entrances)
    {
        if((entrance.mDoor == breakthrough) && SkillManager::isTrapAvailable(TrapType::doorBarricade, ai.getControlledPlayer().getSeat()) &&
           !ai.getMind().slip("F14"))
        {
            Tile* inside = lineTile(ai.getGameMap(), entrance, 1);
            if(trapSpotFree(inside, ai.getControlledPlayer().getSeat()))
                buildOne(ai, TrapType::doorBarricade, inside);
        }
    }
    return true;
}

std::vector<std::string> TRAP::exportDraws(int seatId)
{
    std::vector<std::string> lines;
    std::map<int, TrapState>::const_iterator it = trapStates.find(seatId);
    if(it == trapStates.end())
        return lines;

    if(it->second.mWantDivided >= 0)
        lines.push_back("F01 trapWantDivided " + std::to_string(it->second.mWantDivided));
    if(it->second.mTunnelX >= 0)
    {
        lines.push_back("F15 tunnelX " + std::to_string(it->second.mTunnelX));
        lines.push_back("F15 tunnelY " + std::to_string(it->second.mTunnelY));
    }
    return lines;
}

void TRAP::importDraw(int seatId, const std::string& rowId, const std::string& name, const std::string& value)
{
    TrapState& state = trapStates[seatId];
    int number = std::atoi(value.c_str());
    if((rowId == "F01") && (name == "trapWantDivided"))
        state.mWantDivided = number;
    else if((rowId == "F15") && (name == "tunnelX"))
        state.mTunnelX = number;
    else if((rowId == "F15") && (name == "tunnelY"))
        state.mTunnelY = number;
}
