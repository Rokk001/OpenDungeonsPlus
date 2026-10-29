#include "ai/AiRooms.h"
#include "ai/AiActions.h"
#include "ai/AiEconomy.h"
#include "ai/KeeperAI.h"
#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "entities/GameEntityType.h"
#include "gamemap/GameMap.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "network/ODPacket.h"
#include "rooms/Room.h"
#include "rooms/RoomCasino.h"
#include "rooms/RoomSpa.h"
#include "rooms/RoomTavern.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <functional>
#include <sstream>


#include "ai/AiKnowledge.h"
#include "rooms/RoomDormitory.h"
#include "rooms/RoomManager.h"
#include "utils/Helper.h"
#include "utils/Random.h"
#include <limits>
#include <set>

#include <cmath>
#include <map>
#include <queue>
#include <vector>

namespace
{
//! \brief Holds a path search candidate and its estimated total length.
struct PathCandidate
{
    Tile* tile;
    int distance;
    double estimate;
};

//! \brief Orders path search candidates by their estimated total length.
struct LaterCandidate
{
    //! \brief Returns whether the first candidate has a higher estimate.
    bool operator()(const PathCandidate& left, const PathCandidate& right) const
    {
        return left.estimate > right.estimate;
    }
};
}

//! \brief Finds a shortest known path while retaining the bridge tiles.
static std::vector<Tile*> knownPath(const AiKnowledge& knowledge, Tile* from, Tile* to, bool waterLavaPassable)
{
    if(!knowledge.isKnown(from) || !knowledge.isKnown(to) || from->getFullness() > 0.0 || to->getFullness() > 0.0)
        return std::vector<Tile*>();
    if(!waterLavaPassable && (from->getType() == TileType::water || from->getType() == TileType::lava ||
                              to->getType() == TileType::water || to->getType() == TileType::lava))
        return std::vector<Tile*>();

    std::priority_queue<PathCandidate, std::vector<PathCandidate>, LaterCandidate> open;
    std::map<Tile*, int> distances;
    std::map<Tile*, Tile*> previousTiles;
    distances[from] = 0;
    open.push(PathCandidate{from, 0, 0.0});
    while(!open.empty())
    {
        const PathCandidate current = open.top();
        open.pop();
        if(current.distance != distances[current.tile])
            continue;
        if(current.tile == to)
        {
            std::vector<Tile*> path;
            for(Tile* tile = to; tile != from; tile = previousTiles[tile])
                path.push_back(tile);
            path.push_back(from);
            std::reverse(path.begin(), path.end());
            return path;
        }
        for(Tile* neighbor : current.tile->getAllNeighbors())
        {
            if(!knowledge.isKnown(neighbor) || neighbor->getFullness() > 0.0)
                continue;
            if(!waterLavaPassable && (neighbor->getType() == TileType::water || neighbor->getType() == TileType::lava))
                continue;
            const int distance = current.distance + 1;
            std::map<Tile*, int>::iterator previous = distances.find(neighbor);
            if(previous != distances.end() && previous->second <= distance)
                continue;
            distances[neighbor] = distance;
            previousTiles[neighbor] = current.tile;
            const double dx = static_cast<double>(neighbor->getX() - to->getX());
            const double dy = static_cast<double>(neighbor->getY() - to->getY());
            open.push(PathCandidate{neighbor, distance, distance + std::sqrt(dx * dx + dy * dy)});
        }
    }
    return std::vector<Tile*>();
}

//! \brief Returns the shortest known path length, or -1 if no path exists.
int ROOMS::knownPathLength(const AiKnowledge& knowledge, Tile* from, Tile* to, bool waterLavaPassable)
{
    const std::vector<Tile*> path = knownPath(knowledge, from, to, waterLavaPassable);
    return path.empty() ? -1 : static_cast<int>(path.size()) - 1;
}

namespace
{
//! \brief Reads one AI rule value from the shared configuration.
double roomKey(const std::string& name)
{
    return ConfigManager::getSingleton().getAiConfigDouble(name);
}

//! \brief Finds the own heart without reading enemy rooms.
Tile* heartTile(KeeperAI& ai)
{
    const std::vector<Room*> hearts = ai.getGameMap().getRoomsByTypeAndSeat(
        RoomType::dungeonTemple, ai.getControlledPlayer().getSeat());
    return hearts.empty() ? nullptr : hearts.front()->getCentralTile();
}

//! \brief Counts existing tiles of one own room type, including merged blocks.
uint32_t roomTiles(KeeperAI& ai, RoomType type)
{
    uint32_t count = 0;
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(type, ai.getControlledPlayer().getSeat()))
        count += room->numCoveredTiles();
    return count;
}

//! \brief Computes the same room price as the human factory, including the first treasury tile.
double roomCost(KeeperAI& ai, RoomType type, uint32_t count)
{
    if(type == RoomType::treasury && count > 0 && roomTiles(ai, type) == 0)
        --count;
    return count * RoomManager::costPerTile(type);
}

//! \brief Supplies a uniform variate for the specified room reaction delays.
double roomUniform()
{
    return Random::Double(0.0, 1.0);
}

//! \brief Uses the same symptom and look delay formulas as the shared Mind.
double roomDelay(KeeperAI& ai, bool symptom)
{
    const AiSettings& settings = ai.getSettings();
    const AiMath::DelayParams params = {settings.rho, settings.pi, settings.scanPeriod,
        roomKey("SymptomScanFactor"), roomKey("PeriodicMinDelay"),
        roomKey("ActionLatencyMean"), roomKey("ActionLatencySd")};
    return symptom ? AiMath::reactionDelay(AiMath::ReactionKind::symptom, params, roomUniform) :
        AiMath::lookInterval(roomKey("LookFactorDormitory"), params, roomUniform);
}

//! \brief Finds the known open borders through which a walker enters own land.
std::vector<Tile*> roomEntrances(KeeperAI& ai)
{
    std::vector<Tile*> entries;
    GameMap& map = ai.getGameMap();
    Seat* seat = ai.getControlledPlayer().getSeat();
    const AiKnowledge known(map, seat);
    for(int x = 0; x < map.getMapSizeX(); ++x)
        for(int y = 0; y < map.getMapSizeY(); ++y)
        {
            Tile* tile = map.getTile(x, y);
            if(!known.isKnown(tile) || !tile->isClaimedForSeat(seat) || tile->getFullness() > 0.0)
                continue;
            for(Tile* neighbor : tile->getAllNeighbors())
            {
                if(known.isKnown(neighbor) && neighbor->getFullness() <= 0.0 && !neighbor->isClaimedForSeat(seat))
                {
                    entries.push_back(tile);
                    break;
                }
            }
        }
    Tile* breakthrough = ai.getRoomsState().breakthrough;
    if(known.isKnown(breakthrough) && std::find(entries.begin(), entries.end(), breakthrough) == entries.end())
        entries.push_back(breakthrough);
    for(const AiMath::AiStateLine& line : ai.getMind().savedRows())
        if(line.tag == "war" && line.tokens.size() == 8 && line.tokens[0] == "tunnel")
        {
            Tile* tile = map.getTile(Helper::toInt(line.tokens[5]), Helper::toInt(line.tokens[6]));
            if(known.isKnown(tile) && std::find(entries.begin(), entries.end(), tile) == entries.end())
                entries.push_back(tile);
        }
    return entries;
}

//! \brief Returns squared straight-line distance for placement comparisons.
double roomDistance(Tile* a, Tile* b)
{
    const double x = a->getX() - b->getX();
    const double y = a->getY() - b->getY();
    return x * x + y * y;
}

//! \brief Restores this keeper's pending placement and first-room decisions after Mind import.
void restoreRooms(KeeperAI& ai)
{
    ROOMS::State& state = ai.getRoomsState();
    if(state.restored)
        return;
    state.restored = true;
    for(const AiMath::AiStateLine& line : ai.getMind().savedRows())
    {
        if(line.tag != "draw" || line.tokens.size() != 3)
            continue;
        if(line.tokens[0] == "B02" && line.tokens[1] == "firstRoomSmall")
            state.dormitoryFirst = Helper::toInt(line.tokens[2]) != 0 ?
                static_cast<int>(roomKey("MistakeTilesDormitory")) : static_cast<int>(roomKey("DormitoryExtensionTiles"));
        if(line.tokens[0] == "B03" && line.tokens[1] == "firstRoomSmall")
            state.hatcheryFirst = Helper::toInt(line.tokens[2]) != 0 ?
                static_cast<int>(roomKey("MistakeTilesHatchery")) : static_cast<int>(roomKey("HatcheryExtensionMaxTiles"));
        if(line.tokens[0] == "B02" && line.tokens[1] == "population")
            state.bedPopulation = Helper::toInt(line.tokens[2]);
        if((line.tokens[0] == "B02" || line.tokens[0] == "B03") && line.tokens[1] == "extensionUntil")
        {
            const double remaining = Helper::toDouble(line.tokens[2]);
            if(line.tokens[0] == "B02")
                state.bedDue = remaining < 0.0 ? -1.0 : ai.getMind().now() + remaining;
            else
                state.foodDue = remaining < 0.0 ? -1.0 : ai.getMind().now() + remaining;
        }
        if(line.tokens[0] == "B23" && line.tokens[1] == "breakthrough")
        {
            const int index = Helper::toInt(line.tokens[2]);
            state.breakthrough = index < 0 ? nullptr : ai.getGameMap().getTile(
                index % ai.getGameMap().getMapSizeX(), index / ai.getGameMap().getMapSizeX());
        }
        if(line.tokens[0] == "B23" && line.tokens[1] == "type")
            state.pendingType = static_cast<RoomType>(Helper::toInt(line.tokens[2]));
        if(line.tokens[0] == "B23" && line.tokens[1] == "tile")
        {
            const int index = Helper::toInt(line.tokens[2]);
            Tile* tile = ai.getGameMap().getTile(index % ai.getGameMap().getMapSizeX(), index / ai.getGameMap().getMapSizeX());
            if(tile != nullptr)
                state.pendingTiles.push_back(tile);
        }
    }
}

//! \brief Saves pending room preparation and persistent first-room mistakes.
void saveRooms(KeeperAI& ai, std::vector<AiMath::AiStateLine>& lines)
{
    restoreRooms(ai);
    const std::function<bool(const AiMath::AiStateLine&)> owned = [](const AiMath::AiStateLine& line)
    {
        return line.tag == "draw" && !line.tokens.empty() &&
            (line.tokens[0] == "B02" || line.tokens[0] == "B03" || line.tokens[0] == "B23");
    };
    lines.erase(std::remove_if(lines.begin(), lines.end(), owned), lines.end());
    const ROOMS::State& state = ai.getRoomsState();
    if(state.dormitoryFirst >= 0)
        lines.push_back({"draw", {"B02", "firstRoomSmall", state.dormitoryFirst == roomKey("MistakeTilesDormitory") ? "1" : "0"}});
    if(state.hatcheryFirst >= 0)
        lines.push_back({"draw", {"B03", "firstRoomSmall", state.hatcheryFirst == roomKey("MistakeTilesHatchery") ? "1" : "0"}});
    lines.push_back({"draw", {"B02", "population", Helper::toString(state.bedPopulation)}});
    lines.push_back({"draw", {"B02", "extensionUntil", Helper::toString(state.bedDue < 0.0 ? -1.0 :
        std::max(0.0, state.bedDue - ai.getMind().now()), 17)}});
    lines.push_back({"draw", {"B03", "extensionUntil", Helper::toString(state.foodDue < 0.0 ? -1.0 :
        std::max(0.0, state.foodDue - ai.getMind().now()), 17)}});
    lines.push_back({"draw", {"B23", "breakthrough", Helper::toString(state.breakthrough == nullptr ? -1 :
        state.breakthrough->getY() * ai.getGameMap().getMapSizeX() + state.breakthrough->getX())}});
    lines.push_back({"draw", {"B23", "type", Helper::toString(static_cast<int>(state.pendingType))}});
    for(Tile* tile : state.pendingTiles)
        lines.push_back({"draw", {"B23", "tile", Helper::toString(tile->getY() * ai.getGameMap().getMapSizeX() + tile->getX())}});
}

//! \brief Connects a selected room to known own land using only legal dig marks.
void prepareRoom(KeeperAI& ai, const std::vector<Tile*>& tiles)
{
    Tile* heart = heartTile(ai);
    if(heart == nullptr || tiles.empty())
        return;
    const AiKnowledge known(ai.getGameMap(), ai.getControlledPlayer().getSeat());
    std::vector<Tile*> queue(1, heart);
    std::map<Tile*, Tile*> parent;
    parent[heart] = nullptr;
    Tile* destination = tiles.front();
    for(size_t index = 0; index < queue.size() && parent.find(destination) == parent.end(); ++index)
        for(Tile* tile : queue[index]->getAllNeighbors())
        {
            if(parent.find(tile) != parent.end() || !known.isKnown(tile))
                continue;
            if(tile->getFullness() > 0.0 && !tile->isDiggable(ai.getControlledPlayer().getSeat()))
                continue;
            if(tile->getType() == TileType::water || tile->getType() == TileType::lava)
                continue;
            parent[tile] = queue[index];
            queue.push_back(tile);
        }
    std::vector<Tile*> dig;
    if(parent.find(destination) == parent.end())
        return;
    for(Tile* tile = destination; tile != nullptr; tile = parent[tile])
        if(tile->getFullness() > 0.0 && tile->isDiggable(ai.getControlledPlayer().getSeat()))
            dig.push_back(tile);
    for(Tile* tile : tiles)
        if(tile->getFullness() > 0.0 && tile->isDiggable(ai.getControlledPlayer().getSeat()) &&
            std::find(dig.begin(), dig.end(), tile) == dig.end())
            dig.push_back(tile);
    if(!dig.empty())
        ACTS::markDig(ai, dig, true);
}
}

//! \brief Chooses a known room position once and retains it while workers prepare the ground.
bool ROOMS::placeRoom(KeeperAI& ai, RoomType type, uint32_t count)
{
    // AI row B23
    restoreRooms(ai);
    State& state = ai.getRoomsState();
    Seat* seat = ai.getControlledPlayer().getSeat();
    GameMap& map = ai.getGameMap();
    const AiKnowledge known(map, seat);
    if(!state.pendingTiles.empty())
    {
        bool completed = true;
        bool buildable = true;
        for(Tile* tile : state.pendingTiles)
        {
            if(!known.isKnown(tile))
                return true;
            Room* room = tile->getCoveringRoom();
            completed = completed && room != nullptr && room->getSeat() == seat && room->getType() == state.pendingType;
            buildable = buildable && tile->isBuildableUpon(seat);
        }
        if(completed)
        {
            state.pendingTiles.clear();
            state.pendingType = RoomType::nullRoomType;
            return false;
        }
        else
        {
            if(buildable && ECON::walletGate(ai, roomCost(ai, state.pendingType, static_cast<uint32_t>(state.pendingTiles.size()))))
                ACTS::buildRoom(ai, state.pendingType, state.pendingTiles);
            return true;
        }
    }
    Tile* start = heartTile(ai);
    if(start == nullptr || count == 0 || !SkillManager::isRoomAvailable(type, seat))
        return false;
    if(!ECON::walletGate(ai, roomCost(ai, type, count)))
        return false;
    const bool mistake = ai.getMind().slip("B23");
    if(type == RoomType::treasury)
    {
        const std::vector<Tile*> entries = roomEntrances(ai);
        double selected = mistake ? std::numeric_limits<double>::max() : -1.0;
        Tile* heart = start;
        double heartDistance = std::numeric_limits<double>::max();
        for(int x = 0; !entries.empty() && x < map.getMapSizeX(); ++x)
            for(int y = 0; y < map.getMapSizeY(); ++y)
            {
                Tile* tile = map.getTile(x, y);
                if(!known.isKnown(tile) || !tile->isClaimedForSeat(seat) || tile->getFullness() > 0.0)
                    continue;
                double nearest = std::numeric_limits<double>::max();
                for(Tile* entry : entries)
                    nearest = std::min(nearest, roomDistance(tile, entry));
                const double dh = roomDistance(tile, heart);
                if((mistake ? nearest < selected : nearest > selected) || (nearest == selected && dh < heartDistance))
                {
                    selected = nearest;
                    heartDistance = dh;
                    start = tile;
                }
            }
    }
    const int32_t width = static_cast<int32_t>(std::ceil(std::sqrt(static_cast<double>(count))));
    int32_t x = 0;
    int32_t y = 0;
    if(!ai.findRoomPosition(start, width, type != RoomType::treasury && type != RoomType::dormitory, x, y))
        return false;
    state.pendingType = type;
    for(int32_t dy = 0; dy < width && state.pendingTiles.size() < count; ++dy)
        for(int32_t dx = 0; dx < width && state.pendingTiles.size() < count; ++dx)
            state.pendingTiles.push_back(map.getTile(x + dx, y + dy));
    prepareRoom(ai, state.pendingTiles);
    bool ready = true;
    for(Tile* tile : state.pendingTiles)
        ready = ready && tile->isBuildableUpon(seat);
    if(ready)
        ACTS::buildRoom(ai, type, state.pendingTiles);
    return true;
}

//! \brief Builds one affordable researched entry in strict order, with the early second-treasury trigger.
void ROOMS::buildNext(KeeperAI& ai)
{
    // AI row A09
    // AI row B01
    // AI row B04
    // AI row B05
    // AI row B06
    // AI row B07
    // AI row B12
    // AI row B14
    // AI row B15
    // AI row B19
    // AI row G01
    restoreRooms(ai);
    State& state = ai.getRoomsState();
    if(!state.pendingTiles.empty())
    {
        if(placeRoom(ai, state.pendingType, static_cast<uint32_t>(state.pendingTiles.size())))
            return;
    }
    if(ai.getMind().slip("B01"))
        return;
    const std::vector<std::pair<RoomType, uint32_t>> plan = KeeperAI::getRoomPlan();
    Seat* seat = ai.getControlledPlayer().getSeat();
    std::map<RoomType, uint32_t> expected;
    uint32_t treasuryCount = 0;
    for(const std::pair<RoomType, uint32_t>& entry : plan)
        if(entry.first == RoomType::treasury)
            treasuryCount += entry.second;
    if(seat->getGold() > roomKey("GoldShareTreasury2") * seat->getGoldMax() &&
        roomTiles(ai, RoomType::treasury) > 0 && roomTiles(ai, RoomType::treasury) < treasuryCount)
    {
        uint32_t index = 0;
        for(const std::pair<RoomType, uint32_t>& entry : plan)
            if(entry.first == RoomType::treasury && ++index == 2)
            {
                if(placeRoom(ai, entry.first, entry.second))
                    return;
                break;
            }
    }
    for(const std::pair<RoomType, uint32_t>& entry : plan)
    {
        uint32_t count = entry.second;
        if(entry.first == RoomType::dormitory)
        {
            if(state.dormitoryFirst < 0)
                state.dormitoryFirst = ai.getMind().slip("B02") ?
                    static_cast<int>(roomKey("MistakeTilesDormitory")) : static_cast<int>(entry.second);
            count = static_cast<uint32_t>(state.dormitoryFirst);
        }
        if(entry.first == RoomType::hatchery)
        {
            if(state.hatcheryFirst < 0)
                state.hatcheryFirst = ai.getMind().slip("B03") ?
                    static_cast<int>(roomKey("MistakeTilesHatchery")) : static_cast<int>(entry.second);
            count = static_cast<uint32_t>(state.hatcheryFirst);
        }
        expected[entry.first] += count;
        if(roomTiles(ai, entry.first) >= expected[entry.first])
            continue;
        if(!SkillManager::isRoomAvailable(entry.first, seat))
            return;
        placeRoom(ai, entry.first, count);
        return;
    }
}

//! \brief Adds beds ahead of arrival, retrying a missed extension at its no-bed symptom.
void ROOMS::bedWatch(KeeperAI& ai)
{
    // AI row B02
    // AI row D02
    restoreRooms(ai);
    Seat* seat = ai.getControlledPlayer().getSeat();
    uint32_t beds = 0;
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::dormitory, seat))
        beds += static_cast<RoomDormitory*>(room)->getNbBeds();
    if(roomTiles(ai, RoomType::dormitory) == 0)
        return;
    if(seat->getNumCreaturesFighters() < beds - std::min<double>(beds, roomKey("BedsSpare")))
        return;
    State& state = ai.getRoomsState();
    const int population = seat->getNumCreaturesFighters();
    if(state.bedPopulation != population || state.needFired)
    {
        state.bedPopulation = population;
        state.bedDue = ai.getMind().now() + (ai.getMind().slip("B02") ? roomDelay(ai, true) : 0.0);
    }
    if(state.bedDue < 0.0 || ai.getMind().now() < state.bedDue ||
        (!state.pendingTiles.empty() && state.pendingType != RoomType::dormitory))
        return;
    if(placeRoom(ai, RoomType::dormitory, static_cast<uint32_t>(roomKey("DormitoryExtensionTiles"))))
        state.bedDue = -1.0;
}

//! \brief Extends food coverage by the configured shortage-clamped block size.
void ROOMS::hatcheryWatch(KeeperAI& ai)
{
    // AI row B03
    // AI row D03
    restoreRooms(ai);
    const uint32_t have = roomTiles(ai, RoomType::hatchery);
    if(have == 0)
        return;
    const double need = ai.getControlledPlayer().getSeat()->getNumCreaturesFighters() * roomKey("HatcheryTilesPerCreature") - have;
    if(need <= 0)
        return;
    State& state = ai.getRoomsState();
    if(state.foodDue < 0.0 || state.needFired)
        state.foodDue = ai.getMind().now() + roomDelay(ai, true) +
            (ai.getMind().slip("B03") ? roomDelay(ai, true) : 0.0);
    if(ai.getMind().now() < state.foodDue ||
        (!state.pendingTiles.empty() && state.pendingType != RoomType::hatchery))
        return;
    if(placeRoom(ai, RoomType::hatchery, static_cast<uint32_t>(std::min(roomKey("HatcheryExtensionMaxTiles"),
        std::max(roomKey("HatcheryExtensionMinTiles"), need)))))
        state.foodDue = -1.0;
}

//! \brief Runs the strict room-order look when dirt is noticed.
void ROOMS::toiletWatch(KeeperAI& ai)
{
    // AI row B10
    if(!ai.getMind().slip("B10"))
        buildNext(ai);
}

//! \brief Returns a lost room to the strict-order rebuild process.
void ROOMS::rebuildLost(KeeperAI& ai)
{
    // AI row B22
    if(!ai.getMind().slip("B22"))
        buildNext(ai);
}

//! \brief Places the water or lava tiles of a known useful shortcut through the normal build action.
void ROOMS::bridgeWatch(KeeperAI& ai)
{
    // AI row B21
    Tile* heart = heartTile(ai);
    if(heart == nullptr)
        return;
    Seat* seat = ai.getControlledPlayer().getSeat();
    GameMap& map = ai.getGameMap();
    const AiKnowledge known(map, seat);
    const bool mistake = ai.getMind().slip("B21");
    std::vector<Tile*> targets;
    for(int x = 0; x < map.getMapSizeX(); ++x)
        for(int y = 0; y < map.getMapSizeY(); ++y)
        {
            Tile* tile = map.getTile(x, y);
            if(!known.isKnown(tile))
                continue;
            if(tile->getType() == TileType::gold && tile->isDiggable(seat))
            {
                for(Tile* neighbor : tile->getAllNeighbors())
                    if(known.isKnown(neighbor) && neighbor->getFullness() <= 0.0)
                        targets.push_back(neighbor);
            }
            else if(tile->getFullness() <= 0.0 && tile->getSeat() != nullptr &&
                tile->getSeat() != seat && !seat->isAlliedSeat(tile->getSeat()))
                targets.push_back(tile);
        }
    for(Tile* target : targets)
    {
        const int without = knownPathLength(known, heart, target, false);
        const std::vector<Tile*> with = knownPath(known, heart, target, true);
        if(with.empty() || (without >= 0 && without - static_cast<int>(with.size()) + 1 <= roomKey("BridgeMinShortcutTiles")))
            continue;
        const std::vector<Tile*>* selected = &with;
        std::vector<Tile*> wrong;
        if(mistake)
        {
            for(Tile* other : targets)
                if(other != target)
                {
                    wrong = knownPath(known, heart, other, true);
                    if(!wrong.empty())
                        break;
                }
            if(wrong.empty())
                return;
            selected = &wrong;
        }
        std::vector<Tile*> bridge;
        bool lava = false;
        for(Tile* tile : *selected)
            if(tile->getType() == TileType::water || tile->getType() == TileType::lava)
            {
                lava = lava || tile->getType() == TileType::lava;
                bridge.push_back(tile);
            }
        if(bridge.empty())
            continue;
        const RoomType type = lava ? RoomType::bridgeStone : RoomType::bridgeWooden;
        if(!SkillManager::isRoomAvailable(type, seat) ||
            !ECON::walletGate(ai, bridge.size() * RoomManager::costPerTile(type)))
            return;
        ACTS::buildRoom(ai, type, bridge);
        return;
    }
}

namespace
{
//! \brief Registers one room event without adding a second reaction delay.
void roomEvent(KeeperAI& ai, void (*perform)(KeeperAI&), const AiEvent&)
{
    perform(ai);
}

//! \brief Uses the build look for a missing first need room and its own watcher for extensions.
void needRoomEvent(KeeperAI& ai, RoomType type, const AiEvent&)
{
    if(roomTiles(ai, type) == 0)
        ROOMS::buildNext(ai);
    else if(type == RoomType::dormitory)
        ROOMS::bedWatch(ai);
    else
        ROOMS::hatcheryWatch(ai);
}

//! \brief Remembers the tunnel tile reported to this keeper for entrance-based placement.
void tunnelRoomEvent(KeeperAI& ai, const AiEvent& event)
{
    restoreRooms(ai);
    ai.getRoomsState().breakthrough = event.tile;
}

//! \brief Reacts only to the Upset-or-worse mood event specified by the room rows.
void roomMoodEvent(KeeperAI& ai, void (*perform)(KeeperAI&), const AiEvent& event)
{
    if(event.creature != nullptr && event.creature->getSeat() == ai.getControlledPlayer().getSeat() &&
        event.creature->getMoodValue() >= CreatureMoodLevel::Upset)
        perform(ai);
}

//! \brief Ignores destroyed traps and restarts room building only for a lost room.
void lostRoomEvent(KeeperAI& ai, const AiEvent& event)
{
    if(event.type == AiEventType::RoomLost || event.amount == static_cast<double>(GameEntityType::room))
        ROOMS::rebuildLost(ai);
}
}

//! \brief Registers room looks, event reactions and the keeper-owned saved decisions.
void ROOMS::bind(KeeperAI& ai)
{
    Mind& mind = ai.getMind();
    mind.onLook("B01", roomKey("LookFactorBuild"), std::bind(buildNext, std::ref(ai)));
    mind.onLook("B02", roomKey("LookFactorDormitory"), std::bind(bedWatch, std::ref(ai)));
    mind.onLook("B03", roomKey("LookFactorBuild"), std::bind(hatcheryWatch, std::ref(ai)));
    mind.onLook("B10", roomKey("LookFactorScan"), std::bind(toiletWatch, std::ref(ai)));
    mind.onLook("B13", roomKey("LookFactorScan"), std::bind(auditLab, std::ref(ai)));
    mind.onLook("B16", roomKey("LookFactorScan"), std::bind(auditInfirmary, std::ref(ai)));
    mind.onLook("B18", roomKey("LookFactorScan"), std::bind(auditSpa, std::ref(ai)));
    mind.onLook("B20", roomKey("LookFactorScan"), std::bind(templeSacrifice, std::ref(ai)));
    mind.onLook("B08", roomKey("LookPeriod600") / roomKey("ReferenceScanPeriod"), std::bind(auditTavern, std::ref(ai)));
    mind.onLook("B09", roomKey("LookPeriod600") / roomKey("ReferenceScanPeriod"), std::bind(auditCasino, std::ref(ai)));
    mind.onLook("B11", roomKey("LookPeriod600") / roomKey("ReferenceScanPeriod"), std::bind(auditMerchant, std::ref(ai)));
    mind.onLook("B15", roomKey("LookPeriod60") / roomKey("ReferenceScanPeriod"), std::bind(buildNext, std::ref(ai)));
    mind.onLook("B17", roomKey("LookPeriod600") / roomKey("ReferenceScanPeriod"), std::bind(ghostProduct, std::ref(ai)));
    mind.onLook("B24", roomKey("LookPeriod600") / roomKey("ReferenceScanPeriod"), std::bind(auditSettings, std::ref(ai)));
    mind.onEvent("B02", {AiEventType::CreatureArrived, AiEventType::NoBed}, std::bind(needRoomEvent, std::ref(ai), RoomType::dormitory, std::placeholders::_1));
    mind.onEvent("B03", {AiEventType::CreatureArrived, AiEventType::FirstPortalArrival, AiEventType::NoFood},
        std::bind(needRoomEvent, std::ref(ai), RoomType::hatchery, std::placeholders::_1));
    mind.onEvent("B09", {AiEventType::CreatureMood}, std::bind(roomMoodEvent, std::ref(ai), auditCasino, std::placeholders::_1));
    mind.onEvent("B10", {AiEventType::Dirt}, std::bind(roomEvent, std::ref(ai), toiletWatch, std::placeholders::_1));
    mind.onEvent("B13", {AiEventType::PotionReady}, std::bind(roomEvent, std::ref(ai), auditLab, std::placeholders::_1));
    mind.onEvent("B15", {AiEventType::PrisonerAge}, std::bind(roomEvent, std::ref(ai), buildNext, std::placeholders::_1));
    mind.onEvent("B16", {AiEventType::WoundedCreature}, std::bind(roomEvent, std::ref(ai), auditInfirmary, std::placeholders::_1));
    mind.onEvent("B18", {AiEventType::CreatureMood}, std::bind(roomMoodEvent, std::ref(ai), auditSpa, std::placeholders::_1));
    mind.onEvent("B20", {AiEventType::SurplusCreature}, std::bind(roomEvent, std::ref(ai), templeSacrifice, std::placeholders::_1));
    mind.onEvent("B21", {AiEventType::RouteBlocked}, std::bind(roomEvent, std::ref(ai), bridgeWatch, std::placeholders::_1));
    mind.onEvent("B22", {AiEventType::RoomLost, AiEventType::BuildingDestroyed}, std::bind(lostRoomEvent, std::ref(ai), std::placeholders::_1));
    mind.onEvent("B23", {AiEventType::TunnelOpen}, std::bind(tunnelRoomEvent, std::ref(ai), std::placeholders::_1));
    mind.onSave(std::bind(saveRooms, std::ref(ai), std::placeholders::_1));
}

namespace
{
//! \brief Returns whether an own living creature is Upset or worse.
bool settingsHasUpset(KeeperAI& ai)
{
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(ai.getControlledPlayer().getSeat()))
    {
        if(creature->isAlive() && creature->getMoodValue() >= CreatureMoodLevel::Upset)
            return true;
    }
    return false;
}

//! \brief Finds a sacrifice pool tile surrounded by the same temple on all eight sides.
Tile* settingsPoolTile(KeeperAI& ai, Room* room)
{
    for(Tile* tile : room->getCoveredTiles())
    {
        bool pool = true;
        for(int dx = -1; dx <= 1; ++dx)
        {
            for(int dy = -1; dy <= 1; ++dy)
            {
                Tile* neighbour = ai.getGameMap().getTile(tile->getX() + dx, tile->getY() + dy);
                if(neighbour == nullptr || neighbour->getCoveringRoom() != room)
                    pool = false;
            }
        }
        if(pool)
            return tile;
    }
    return nullptr;
}
}

namespace ROOMS
{
//! \brief Sets the tavern payer according to the treasury's wage reserve.
void auditTavern(KeeperAI& ai)
{
    // AI row B08
    Seat* seat = ai.getControlledPlayer().getSeat();
    const bool mistake = ai.getMind().slip("B08");
    const TavernPayer payer = mistake || seat->getGold() >
        ConfigManager::getSingleton().getAiConfigDouble("TavernKeeperPaysFactor") * ECON::wageBill(ai) ?
        TavernPayer::keeper : TavernPayer::creature;
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::tavern, seat))
    {
        if(static_cast<RoomTavern*>(room)->getPayer() == payer || room->numCoveredTiles() == 0)
            continue;
        Tile* tile = room->getCoveredTile(0);
        ODPacket packet;
        packet << tile->getX() << tile->getY() << static_cast<uint32_t>(payer);
        ACTS::setRoomSetting(ai, room, packet);
    }
}

//! \brief Chooses casino smiles unless a wage shortage and calm creatures allow money.
void auditCasino(KeeperAI& ai)
{
    // AI row B09
    Seat* seat = ai.getControlledPlayer().getSeat();
    const bool mistake = ai.getMind().slip("B09");
    const CasinoPayout payout = mistake || (seat->getGold() < ECON::wageBill(ai) && !settingsHasUpset(ai)) ?
        CasinoPayout::money : CasinoPayout::smiles;
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::casino, seat))
    {
        if(static_cast<RoomCasino*>(room)->getPayout() == payout || room->numCoveredTiles() == 0)
            continue;
        Tile* tile = room->getCoveredTile(0);
        ODPacket packet;
        packet << tile->getX() << tile->getY() << static_cast<uint32_t>(payout) << true;
        ACTS::setRoomSetting(ai, room, packet);
    }
}

//! \brief Sets the merchant's fair or profit margin from the creatures' mood.
void auditMerchant(KeeperAI& ai)
{
    // AI row B11
    Seat* seat = ai.getControlledPlayer().getSeat();
    const bool mistake = ai.getMind().slip("B11");
    const bool fair = settingsHasUpset(ai);
    const std::string mode = fair ? "fair" : "profit";
    const int32_t margin = mistake ? 0 : ConfigManager::getSingleton().getAiConfigInt32(
        fair ? "MerchantMarginMin" : "MerchantMarginMax");
    const std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(RoomType::merchant, seat);
    if(rooms.empty() || (seat->getMerchantMargin() == margin && seat->getMerchantMode() == mode))
        return;
    ODPacket packet;
    packet << margin << mode;
    ACTS::setRoomSetting(ai, rooms.front(), packet);
}

//! \brief Configures the laboratory's shared potion production mode.
void auditLab(KeeperAI& ai)
{
    // AI row B13
    // AI row H02
    Seat* seat = ai.getControlledPlayer().getSeat();
    const bool mistake = ai.getMind().slip("B13");
    const int32_t mode = mistake ? 0 : ConfigManager::getSingleton().getAiConfigInt32("LabModeDefault");
    const std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(RoomType::alchemyLab, seat);
    if(rooms.empty() || seat->getLabMode() == mode)
        return;
    ODPacket packet;
    packet << mode;
    ACTS::setRoomSetting(ai, rooms.front(), packet);
}

//! \brief Enables keeper-funded infirmary healing to the configured discharge threshold.
void auditInfirmary(KeeperAI& ai)
{
    // AI row B16
    Seat* seat = ai.getControlledPlayer().getSeat();
    const bool heal = !ai.getMind().slip("B16");
    const int32_t threshold = ConfigManager::getSingleton().getAiConfigInt32("InfirmaryDischargePercent");
    const std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(RoomType::infirmary, seat);
    if(rooms.empty() || (seat->getInfirmaryPayer() == 0 && seat->getInfirmaryThreshold() == threshold &&
        seat->getInfirmaryHealOn() == heal))
        return;
    ODPacket packet;
    packet << static_cast<int32_t>(0) << threshold << heal;
    ACTS::setRoomSetting(ai, rooms.front(), packet);
}

//! \brief Selects research, scarce mana or saleable crystals and affordable own-body revival.
void ghostProduct(KeeperAI& ai)
{
    // AI row B17
    if(ai.getMind().slip("B17"))
        return;
    Seat* seat = ai.getControlledPlayer().getSeat();
    const std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(RoomType::ghostRoom, seat);
    if(rooms.empty() || rooms.front()->numCoveredTiles() == 0)
        return;
    const ConfigManager& config = ConfigManager::getSingleton();
    uint32_t entries = 0;
    uint32_t researched = 0;
    const std::function<void(const std::string&, const std::string&, const std::string&, SkillType)> count =
        [seat, &entries, &researched](const std::string&, const std::string&, const std::string&, SkillType skill)
        {
            if(Skills::isRewardSkill(skill) || seat->isSkillNotAllowed(skill))
                return;
            ++entries;
            if(seat->isSkillDone(skill))
                ++researched;
        };
    SkillManager::listAllSkills(count);
    GhostProduct product = seat->getGhostProduct();
    if(entries > 0 && researched < config.getAiConfigDouble("GhostResearchShare") * entries)
        product = GhostProduct::research;
    else if(seat->getMana() < config.getAiConfigDouble("GhostManaShare") * config.getMaxManaPerSeat())
        product = GhostProduct::mana;
    else if(!ai.getGameMap().getRoomsByTypeAndSeat(RoomType::merchant, seat).empty() &&
        seat->getGold() < ECON::wageBill(ai))
        product = GhostProduct::crystal;
    const double price = SkillManager::getResearchValue(seat, SkillType::roomGhostRoom,
        config.getRoomConfigDouble("GhostReviveMana"), ResearchEffect::RevivePrice);
    const bool revive = seat->getMana() > config.getAiConfigDouble("ReviveManaFactor") * price;
    if(seat->getGhostProduct() == product && seat->getGhostRevive() == revive)
        return;
    Tile* tile = rooms.front()->getCoveredTile(0);
    ODPacket packet;
    packet << tile->getX() << tile->getY() << static_cast<uint32_t>(product) << revive << true;
    ACTS::setRoomSetting(ai, rooms.front(), packet);
}

//! \brief Makes creatures pay for the spa unless this look is mistaken.
void auditSpa(KeeperAI& ai)
{
    // AI row B18
    const bool mistake = ai.getMind().slip("B18");
    if(mistake)
        return;
    Seat* seat = ai.getControlledPlayer().getSeat();
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::spa, seat))
    {
        if(static_cast<RoomSpa*>(room)->getPayer() == SpaPayer::creature || room->numCoveredTiles() == 0)
            continue;
        Tile* tile = room->getCoveredTile(0);
        ODPacket packet;
        packet << tile->getX() << tile->getY() << static_cast<uint32_t>(SpaPayer::creature) << true;
        ACTS::setRoomSetting(ai, room, packet);
    }
}

//! \brief Drops a complete configured recipe's weakest surplus inputs into a temple pool.
void templeSacrifice(KeeperAI& ai)
{
    // AI row B20
    const bool mistake = ai.getMind().slip("B20");
    Seat* seat = ai.getControlledPlayer().getSeat();
    if(seat->getNumCreaturesFighters() != seat->getNumCreaturesFightersMax())
        return;
    std::vector<Creature*> fighters;
    std::vector<uint32_t> levels;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(seat))
    {
        if(!creature->isAlive() || creature->getDefinition()->isWorker())
            continue;
        fighters.push_back(creature);
        levels.push_back(creature->getLevel());
    }
    if(levels.empty())
        return;
    std::sort(levels.begin(), levels.end());
    const size_t middle = levels.size() / 2;
    const double median = levels.size() % 2 == 0 ?
        (static_cast<double>(levels[middle - 1]) + levels[middle]) / 2.0 : levels[middle];
    Tile* pool = nullptr;
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::temple, seat))
    {
        pool = settingsPoolTile(ai, room);
        if(pool != nullptr)
            break;
    }
    if(pool == nullptr)
        return;
    const std::string recipeKeys[] = {"TempleRecipe2", "TempleRecipe12"};
    for(const std::string& key : recipeKeys)
    {
        const std::string recipe = ConfigManager::getSingleton().getRoomConfigString(key);
        const std::string::size_type equals = recipe.find('=');
        if(equals == std::string::npos)
            continue;
        std::istringstream inputs(recipe.substr(0, equals));
        std::string className;
        std::vector<Creature*> chosen;
        bool complete = true;
        while(std::getline(inputs, className, '+'))
        {
            Creature* best = nullptr;
            for(Creature* creature : fighters)
            {
                if(creature->getDefinition()->getClassName() != className ||
                    std::find(chosen.begin(), chosen.end(), creature) != chosen.end() ||
                    (!mistake && creature->getLevel() >= median))
                    continue;
                if(best == nullptr || (mistake ? creature->getLevel() > best->getLevel() :
                    creature->getLevel() < best->getLevel()))
                    best = creature;
            }
            if(best == nullptr)
            {
                complete = false;
                break;
            }
            chosen.push_back(best);
        }
        if(!complete || chosen.empty())
            continue;
        for(Creature* creature : chosen)
            ACTS::moveCreature(ai, creature, pool);
        return;
    }
}

//! \brief Revisits the six configured room switches at the long audit look.
void auditSettings(KeeperAI& ai)
{
    // AI row B24
    if(ai.getMind().slip("B24"))
        return;
    auditTavern(ai);
    auditCasino(ai);
    auditMerchant(ai);
    auditInfirmary(ai);
    ghostProduct(ai);
    auditSpa(ai);
}
}
