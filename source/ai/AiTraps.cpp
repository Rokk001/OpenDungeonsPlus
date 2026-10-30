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
#include "ai/AiSettings.h"
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
#include "utils/Random.h"

#include <algorithm>
#include <cstdlib>
#include <functional>
#include <set>
#include <sstream>
#include <string>

namespace
{
//! \brief Returns a value of the [KeeperAI] section of ai.cfg.
double aiKey(const std::string& key)
{
    return ConfigManager::getSingleton().getAiConfigDouble(key);
}

//! \brief Supplies one uniform draw for the delay formulas.
double uniformDraw()
{
    return Random::Double(0.0, 1.0);
}

//! \brief Draws one symptom delay of the AI's level (specification 3.1), used for the extra delay of a rule mistake.
double symptomDelay(KeeperAI& ai)
{
    const AiSettings& settings = ai.getSettings();
    AiMath::DelayParams params = {settings.rho, settings.pi, settings.scanPeriod, aiKey("SymptomScanFactor"),
        aiKey("PeriodicMinDelay"), aiKey("ActionLatencyMean"), aiKey("ActionLatencySd")};
    AiMath::Uniform01 uniform = uniformDraw;
    return AiMath::reactionDelay(AiMath::ReactionKind::symptom, params, uniform);
}

//! \brief Writes a number with full double precision for a draw line.
std::string numberToken(double value)
{
    std::ostringstream os;
    os.precision(17);
    os << value;
    return os.str();
}

//! \brief Reads the trap draws of a loaded game from the mind once: F01 halved plan, F12 watching, F15 tunnels and
//! the steps that wait for the symptom delay of a mistake (F12, F13, F15). The mind imports its state at its first
//! turn, at mind time 0, so a saved remaining time is the mind time of the step.
void restoreDraws(KeeperAI& ai)
{
    TRAP::State& state = ai.getTrapState();
    if(state.mRestored)
        return;

    state.mRestored = true;
    for(const AiMath::AiStateLine& line : ai.getMind().savedRows())
    {
        if((line.tag != "draw") || (line.tokens.size() != 3))
            continue;

        const std::string& row = line.tokens[0];
        const std::string& name = line.tokens[1];
        const std::string& value = line.tokens[2];
        if((row == "F01") && (name == "trapWantDivided"))
            state.mWantDivided = std::atoi(value.c_str());
        else if((row == "F12") && (name == "watching"))
            state.mWatching = (value == "1");
        else if((row == "F12") && (name == "watchDue"))
            state.mWatchDue = std::atof(value.c_str());
        else if((row == "F13") && (name == "doorDue"))
            state.mDoorDue = std::atof(value.c_str());
        else if((row == "F15") && (name == "fortifyDue"))
        {
            // x,y,remaining
            std::string::size_type first = value.find(',');
            std::string::size_type second = (first == std::string::npos) ? std::string::npos : value.find(',', first + 1);
            if(second != std::string::npos)
            {
                TRAP::State::PendingFortify pending;
                pending.mX = std::atoi(value.substr(0, first).c_str());
                pending.mY = std::atoi(value.substr(first + 1, second - first - 1).c_str());
                pending.mDue = std::atof(value.substr(second + 1).c_str());
                state.mFortifyDue.push_back(pending);
            }
        }
        else if((row == "F15") && (name == "tunnel"))
        {
            std::string::size_type comma = value.find(',');
            if(comma != std::string::npos)
                state.mTunnels.push_back(std::make_pair(std::atoi(value.substr(0, comma).c_str()), std::atoi(value.substr(comma + 1).c_str())));
        }
    }
}

//! \brief Starts watching the exhausted own trap tiles after a fight (row F12): the reload reserve is tested at once.
void startWatching(KeeperAI& ai)
{
    TRAP::State& state = ai.getTrapState();
    state.mWatching = true;
    state.mLastTestSeconds = -1.0e18;
}

//! \brief Appends one draw line with the row, the name and the value.
void addDraw(std::vector<AiMath::AiStateLine>& lines, const std::string& row, const std::string& name, const std::string& value)
{
    AiMath::AiStateLine line;
    line.tag = "draw";
    line.tokens.push_back(row);
    line.tokens.push_back(name);
    line.tokens.push_back(value);
    lines.push_back(line);
}

//! \brief Replaces the trap draw lines of the saved AI state with the current ones.
void saveDraws(KeeperAI& ai, std::vector<AiMath::AiStateLine>& lines)
{
    restoreDraws(ai);
    std::vector<AiMath::AiStateLine> kept;
    for(const AiMath::AiStateLine& line : lines)
    {
        bool own = (line.tag == "draw") && !line.tokens.empty() &&
                   ((line.tokens[0] == "F01") || (line.tokens[0] == "F12") || (line.tokens[0] == "F13") ||
                    (line.tokens[0] == "F15"));
        if(!own)
            kept.push_back(line);
    }
    lines.swap(kept);

    const TRAP::State& state = ai.getTrapState();
    if(state.mWantDivided >= 0)
        addDraw(lines, "F01", "trapWantDivided", std::to_string(state.mWantDivided));
    if(state.mWatching)
        addDraw(lines, "F12", "watching", "1");
    for(const std::pair<int, int>& tunnel : state.mTunnels)
        addDraw(lines, "F15", "tunnel", std::to_string(tunnel.first) + "," + std::to_string(tunnel.second));

    // The waiting steps as the seconds that remain
    double now = ai.getMind().now();
    if(state.mWatchDue >= 0.0)
        addDraw(lines, "F12", "watchDue", numberToken(std::max(0.0, state.mWatchDue - now)));
    if(state.mDoorDue >= 0.0)
        addDraw(lines, "F13", "doorDue", numberToken(std::max(0.0, state.mDoorDue - now)));
    for(const TRAP::State::PendingFortify& pending : state.mFortifyDue)
    {
        addDraw(lines, "F15", "fortifyDue", std::to_string(pending.mX) + "," + std::to_string(pending.mY) + "," +
                numberToken(std::max(0.0, pending.mDue - now)));
    }
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

    // Every fortified tunnel is an entrance of its own
    restoreDraws(ai);
    for(const std::pair<int, int>& tunnelTile : ai.getTrapState().mTunnels)
    {
        Tile* tunnel = gameMap.getTile(tunnelTile.first, tunnelTile.second);
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
    restoreDraws(ai);
    TRAP::State& state = ai.getTrapState();

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

    // A special trap that cannot be built at this look does not keep the AI from the next one
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
            if(trapSpotFree(tile, seat) && buildOne(ai, TrapType::boulder, tile))
                return true;
        }
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
        if(trapSpotFree(spot, seat) && buildOne(ai, TrapType::lightning, spot))
            return true;
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
        if(trapSpotFree(spot, seat) && buildOne(ai, TrapType::fireburst, spot))
            return true;
    }

    // AI row F08
    if(SkillManager::isTrapAvailable(TrapType::freeze, seat) && (countTiles(ai, TrapType::freeze) == 0))
    {
        // Before the heart room; the mistake puts it far from where the fighters stand
        int index = nearestEntrance(entrances, heart, ai.getMind().slip("F08"));
        Tile* spot = (index >= 0) ? lineTile(gameMap, entrances[index], 1) : nullptr;
        if(trapSpotFree(spot, seat) && buildOne(ai, TrapType::freeze, spot))
            return true;
    }

    // AI row F09
    if(SkillManager::isTrapAvailable(TrapType::alarm, seat))
    {
        // One alarm on the alarm spot of each entrance: only an entrance whose spot has no alarm yet gets one; the
        // mistake builds none at this look, so the intrusion is noticed late
        bool drawn = false;
        for(const TRAP::Entrance& entrance : entrances)
        {
            Tile* tile = lineTile(gameMap, entrance, -static_cast<int>(aiKey("AlarmDistanceTiles")));
            Trap* current = (tile == nullptr) ? nullptr : trapAt(ai, tile);
            if(((current != nullptr) && (current->getType() == TrapType::alarm)) || !trapSpotFree(tile, seat))
                continue;

            if(!drawn)
            {
                drawn = true;
                if(ai.getMind().slip("F09"))
                    break;
            }
            if(buildOne(ai, TrapType::alarm, tile))
                return true;
        }
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
        if(trapSpotFree(spot, seat) && buildOne(ai, TrapType::fear, spot))
            return true;
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
    return false;
}

bool TRAP::reloadGate(KeeperAI& ai)
{
    // AI row F12
    restoreDraws(ai);
    // The mistake: the AI thinks of the empty traps only after another symptom delay
    if(ai.getMind().slip("F12"))
    {
        ai.getTrapState().mWatchDue = ai.getMind().now() + symptomDelay(ai);
        return false;
    }
    startWatching(ai);
    return true;
}

double TRAP::reloadMargin(KeeperAI& ai)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    restoreDraws(ai);
    TRAP::State& state = ai.getTrapState();
    if(!state.mWatching)
        return 0.0;

    // The empty traps are looked at again every ReloadRetrySeconds
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

    // The door of the best researched kind on every entrance; the mistake forgets the upgrade: a door that stands
    // stays, an entrance without a door gets a wooden one, and the doors are looked at again after a symptom delay
    TrapType best = bestDoor(seat);
    bool slipped = ai.getMind().slip("F13");
    bool forgotten = false;
    bool scheduled = false;
    bool stopped = false;
    for(const Entrance& entrance : entrances)
    {
        Trap* current = trapAt(ai, entrance.mDoor);
        int currentRank = (current == nullptr) ? 0 : doorRank(current->getType());
        // A tile with another trap or a special door is left alone
        if((current != nullptr) && (currentRank == 0))
            continue;

        if(currentRank >= doorRank(best))
            continue;

        TrapType kind = best;
        if(slipped)
        {
            forgotten = true;
            if(current != nullptr)
                continue;
            kind = TrapType::doorWooden;
        }
        if(!SkillManager::isTrapAvailable(kind, seat))
            continue;

        // Without the gold the look ends here, as before the special doors
        if(!affordable(ai, TrapManager::costPerTile(kind)))
        {
            stopped = true;
            break;
        }

        // An older door is sold first, the new one is built on the freed tile
        if(current != nullptr)
        {
            std::vector<Tile*> tiles;
            tiles.push_back(entrance.mDoor);
            ACTS::sellTrapTiles(ai, tiles);
        }
        scheduled = buildOne(ai, kind, entrance.mDoor);
        break;
    }
    TRAP::State& state = ai.getTrapState();
    if(forgotten && (state.mDoorDue < 0.0))
        state.mDoorDue = ai.getMind().now() + symptomDelay(ai);
    if(scheduled || stopped)
        return scheduled;

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

namespace
{
//! \brief Fortifies the tunnel entrance at the breakthrough tile now: it becomes an entrance of its own, the trap look
//! runs at once (so the F rows build its door and its trap tiles) and the barricade is built one step inside (row F14).
void fortifyNow(KeeperAI& ai, Tile* breakthrough)
{
    if(breakthrough == nullptr)
        return;

    TRAP::State& state = ai.getTrapState();
    std::pair<int, int> tile(breakthrough->getX(), breakthrough->getY());
    if(std::find(state.mTunnels.begin(), state.mTunnels.end(), tile) == state.mTunnels.end())
        state.mTunnels.push_back(tile);
    TRAP::trapLook(ai);

    std::vector<TRAP::Entrance> entrances = TRAP::findEntrances(ai);
    Seat* seat = ai.getControlledPlayer().getSeat();
    for(const TRAP::Entrance& entrance : entrances)
    {
        if((entrance.mDoor == breakthrough) && SkillManager::isTrapAvailable(TrapType::doorBarricade, seat) &&
           !ai.getMind().slip("F14"))
        {
            Tile* inside = lineTile(ai.getGameMap(), entrance, 1);
            if(trapSpotFree(inside, seat))
                buildOne(ai, TrapType::doorBarricade, inside);
        }
    }
}

//! \brief Runs the steps whose mistake delay is over: watching the empty traps (F12), the next look at the doors (F13)
//! and the delayed tunnel fortifications (F15). Run by the mind every AiPollSeconds; it never raises an event, and the
//! hand is used only by the actions of the steps themselves.
//! \return Always false.
bool pendingStep(KeeperAI& ai)
{
    restoreDraws(ai);
    TRAP::State& state = ai.getTrapState();
    double now = ai.getMind().now();
    if((state.mWatchDue >= 0.0) && (now >= state.mWatchDue))
    {
        state.mWatchDue = -1.0;
        startWatching(ai);
    }
    if((state.mDoorDue >= 0.0) && (now >= state.mDoorDue))
    {
        state.mDoorDue = -1.0;
        TRAP::placeDoor(ai, TRAP::findEntrances(ai));
    }
    std::vector<TRAP::State::PendingFortify> due;
    std::vector<TRAP::State::PendingFortify> waiting;
    for(const TRAP::State::PendingFortify& pending : state.mFortifyDue)
    {
        if(now >= pending.mDue)
            due.push_back(pending);
        else
            waiting.push_back(pending);
    }
    state.mFortifyDue.swap(waiting);
    for(const TRAP::State::PendingFortify& pending : due)
        fortifyNow(ai, ai.getGameMap().getTile(pending.mX, pending.mY));
    return false;
}

//! \brief The reaction to a destroyed building: a broken door of an entrance is rebuilt at once (row F13).
void onBuildingDestroyed(KeeperAI& ai, const AiEvent& event)
{
    if(event.tile == nullptr)
        return;

    std::vector<TRAP::Entrance> entrances = TRAP::findEntrances(ai);
    for(const TRAP::Entrance& entrance : entrances)
    {
        if(entrance.mDoor == event.tile)
        {
            TRAP::placeDoor(ai, entrances);
            return;
        }
    }
}
}

TRAP::State::State() :
    mWantDivided(-1),
    mWatching(false),
    mLastTestSeconds(-1.0e18),
    mExhausted(false),
    mWatchDue(-1.0),
    mDoorDue(-1.0),
    mRestored(false)
{
}

void TRAP::bindRows(KeeperAI& ai)
{
    Mind& mind = ai.getMind();
    KeeperAI* self = &ai;
    std::function<void()> look = [self]() { TRAP::trapLook(*self); };
    std::function<void(const AiEvent&)> fightOver = [self](const AiEvent&) { TRAP::reloadGate(*self); };
    std::function<void(const AiEvent&)> broken = [self](const AiEvent& event) { onBuildingDestroyed(*self, event); };
    std::function<void(const AiEvent&)> tunnel = [self](const AiEvent& event) { TRAP::fortifyTunnel(*self, event.tile); };
    std::function<bool()> pending = [self]() { return pendingStep(*self); };
    std::function<void(std::vector<AiMath::AiStateLine>&)> save = [self](std::vector<AiMath::AiStateLine>& lines) { saveDraws(*self, lines); };

    // One trap look for all F rows (specification 3.2 item 1)
    mind.onLook("F01", aiKey("LookFactorTrap"), look);
    mind.onEvent("F12", std::vector<AiEventType>(1, AiEventType::FightOver), fightOver);
    mind.onEvent("F13", std::vector<AiEventType>(1, AiEventType::BuildingDestroyed), broken);
    mind.onEvent("F15", std::vector<AiEventType>(1, AiEventType::TunnelOpen), tunnel);
    mind.onPoll("F12", AiEventType::FightOver, pending);
    mind.onSave(save);
}

bool TRAP::fortifyTunnel(KeeperAI& ai, Tile* breakthrough)
{
    // AI row F15
    if(breakthrough == nullptr)
        return false;

    restoreDraws(ai);
    // The mistake: the AI notices the open tunnel only after another symptom delay
    if(ai.getMind().slip("F15"))
    {
        TRAP::State::PendingFortify pending;
        pending.mX = breakthrough->getX();
        pending.mY = breakthrough->getY();
        pending.mDue = ai.getMind().now() + symptomDelay(ai);
        ai.getTrapState().mFortifyDue.push_back(pending);
        return false;
    }

    // The tunnel is an entrance from now on, so the trap look builds its door and the trap tiles per entrance
    fortifyNow(ai, breakthrough);
    return true;
}

double TRAP::fortifyRemaining(KeeperAI& ai)
{
    restoreDraws(ai);
    double remaining = -1.0;
    double now = ai.getMind().now();
    for(const TRAP::State::PendingFortify& pending : ai.getTrapState().mFortifyDue)
    {
        double left = std::max(0.0, pending.mDue - now);
        if((remaining < 0.0) || (left < remaining))
            remaining = left;
    }
    return remaining;
}
