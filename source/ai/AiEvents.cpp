#include "ai/AiEvents.h"
#include "ai/AiKnowledge.h"
#include "ai/KeeperAI.h"
#include "ODApplication.h"
#include "creatureaction/CreatureAction.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/PotionDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomAlchemyLab.h"
#include "rooms/RoomDungeonTemple.h"
#include "rooms/RoomType.h"
#include "traps/Trap.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <iomanip>
#include <limits>
#include <sstream>

namespace
{
//! \brief Serializes a counter without losing fractional game seconds.
std::string eventNumber(double value)
{
    std::ostringstream out;
    out << std::setprecision(std::numeric_limits<double>::max_digits10) << value;
    return out.str();
}

//! \brief Returns the own heart tile, or nullptr after the keeper has lost it.
Tile* heartTile(KeeperAI& ai)
{
    const std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(
        RoomType::dungeonTemple, ai.getControlledPlayer().getSeat());
    return rooms.empty() ? nullptr : static_cast<RoomDungeonTemple*>(rooms.front())->getHeartTile();
}
}

//! \brief Starts a keeper's symptom history with no previous fight or portal arrival.
AiEvents::AiEvents(KeeperAI& ai) : mAi(ai), mLoaded(false), mPayday(false), mArrival(false),
    mPendingArrival(false), mBuildDue(-1.0), mPotions(0)
{
}

//! \brief Uses the existing mind poll clock and AIState callbacks, without a second scheduler.
void AiEvents::bind()
{
    mAi.getMind().onPoll("I06Events", AiEventType::NoMarkedTile, [this]() { return poll(); });
    mAi.getMind().onSave([this](std::vector<AiMath::AiStateLine>& lines) { save(lines); });
}

//! \brief Imports only this source's I06 records, leaving other row owners' data untouched.
void AiEvents::load()
{
    if(mLoaded)
        return;
    mLoaded = true;
    for(const AiMath::AiStateLine& line : mAi.getMind().savedRows())
    {
        if(line.tag != "draw" || line.tokens.size() != 3 || line.tokens[0] != "I06")
            continue;
        const std::string& name = line.tokens[1];
        double value = 0.0;
        std::istringstream in(line.tokens[2]);
        if(!(in >> value))
            continue;
        if(name == "pollArrival") mArrival = value != 0.0;
        else if(name == "pollPayday") mPayday = mPayday || value != 0.0;
        else if(name == "pollBuild") mBuildDue = mAi.getMind().now() + value;
        else if(name == "pollPotions") mPotions = static_cast<uint32_t>(value);
        else if(name == "pollPendingArrival") mPendingArrival = mPendingArrival || value != 0.0;
        else if(name.compare(0, 4, "edge") == 0) mEdges[name.substr(4)] = value != 0.0;
    }
}

//! \brief Retains arrivals and payday resets before the notice's reaction delay.
void AiEvents::notify(const AiEvent& event)
{
    // Game notices can arrive before the first mind turn; loaded history is adopted by the first poll.
    if(event.type == AiEventType::Payday)
        mPayday = true;
    if(event.type == AiEventType::CreatureArrived && event.amount == 0.0)
        mPendingArrival = true;
}

//! \brief Emits a symptom only when it changes from absent to present.
void AiEvents::edge(const std::string& name, AiEventType type, bool value, Tile* tile)
{
    if(value && !mEdges[name])
    {
        const AiEvent event = {type, tile, nullptr, -1, 0.0, mAi.getMind().now()};
        mAi.getMind().enqueue(event);
    }
    mEdges[name] = value;
}

//! \brief Observes the existing build look through its public save data, keeping the room owner's timer intact.
double AiEvents::buildLookDue()
{
    std::ostringstream out;
    mAi.exportState(out);
    std::istringstream input(out.str());
    std::string text;
    while(std::getline(input, text))
    {
        std::istringstream in(text);
        std::string tag, name;
        double remaining;
        if(in >> tag >> name >> remaining && tag == "look" && name == "B01")
            return mAi.getMind().now() + remaining;
    }
    return mBuildDue;
}

//! \brief Evaluates only own creatures, remembered terrain and enemy entities currently visible to the seat.
bool AiEvents::poll()
{
    load();
    if(mPendingArrival && !mArrival)
    {
        mArrival = true;
        const AiEvent first = {AiEventType::FirstPortalArrival, nullptr, nullptr, -1, 0.0, mAi.getMind().now()};
        mAi.getMind().enqueue(first);
    }
    mPendingArrival = false;
    GameMap& map = mAi.getGameMap();
    Seat* seat = mAi.getControlledPlayer().getSeat();
    const ConfigManager& cfg = ConfigManager::getSingleton();
    const std::vector<Creature*> own = map.getCreaturesBySeat(seat);
    std::vector<unsigned int> levels;
    Creature* worker = nullptr;
    double bill = 0.0;
    bool wounded = false, prisoner = false;
    for(Creature* creature : own)
    {
        if(!creature->isAlive())
            continue;
        if(creature->getDefinition()->isWorker())
        {
            if(worker == nullptr) worker = creature;
            continue;
        }
        levels.push_back(creature->getLevel());
        bill += creature->getDefinition()->getFee(creature->getLevel()) + creature->getGoldFee();
        Tile* tile = creature->getPositionTile();
        Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
        const bool inBed = tile != nullptr && tile == creature->getHomeTile() &&
            creature->isActionInList(CreatureActionType::sleep);
        if(creature->isHurt() && !inBed && (room == nullptr || room->getType() != RoomType::infirmary))
            wounded = true;
    }
    for(Creature* creature : map.getCreatures())
    {
        if(creature->isAlive() && creature->getSeatPrison() == seat && creature->isInPrison() &&
            creature->getNbTurnsPrison() >= cfg.getAiConfigDouble("PrisonWaitMinutes") * 60.0 * ODApplication::turnsPerSecond)
            prisoner = true;
    }
    edge("NoMarkedTile", AiEventType::NoMarkedTile,
        worker != nullptr && mAi.getControlledPlayer().getNbMarkedTiles() == 0);
    if(mPayday)
    {
        mEdges["GoldBelowBill"] = false;
        mPayday = false;
    }
    edge("GoldBelowBill", AiEventType::GoldBelowBill, seat->getGold() < bill);
    edge("WoundedCreature", AiEventType::WoundedCreature, wounded);
    edge("PrisonerAge", AiEventType::PrisonerAge, prisoner);
    std::sort(levels.begin(), levels.end());
    bool surplus = false;
    if(!levels.empty() && seat->getNumCreaturesFighters() == seat->getNumCreaturesFightersMax())
    {
        const std::size_t n = levels.size();
        const double median = (levels[(n - 1) / 2] + levels[n / 2]) / 2.0;
        surplus = levels.front() < median;
    }
    edge("SurplusCreature", AiEventType::SurplusCreature, surplus);
    uint32_t potions = 0;
    for(const PotionDefinition& potion : cfg.getPotions())
        potions += RoomAlchemyLab::countWaitingPotion(map, seat, potion.getId());
    if(potions > mPotions)
    {
        const AiEvent ready = {AiEventType::PotionReady, nullptr, nullptr, -1,
            static_cast<double>(potions - mPotions), mAi.getMind().now()};
        mAi.getMind().enqueue(ready);
    }
    mPotions = potions;
    const double buildDue = buildLookDue();
    Tile* heart = heartTile(mAi);
    AiKnowledge known(map, seat);
    // The build owner supplies the B01 look; observe its next due time without drawing another look.
    if(buildDue != mBuildDue)
    {
        mBuildDue = buildDue;
        bool blocked = false;
        Tile* blockedTile = nullptr;
        if(worker != nullptr && heart != nullptr)
        {
            for(int x = 0; x < map.getMapSizeX(); ++x)
                for(int y = 0; y < map.getMapSizeY(); ++y)
                {
                    Tile* tile = map.getTile(x, y);
                    if(!known.isKnown(tile)) continue;
                    const TileStateNotified* memory = seat->getKnownTileState(tile);
                    if(memory == nullptr) continue;
                    Seat* owner = map.getSeatById(memory->mSeatIdOwner);
                    const bool seam = memory->mTileVisual == TileVisual::goldFull || memory->mTileVisual == TileVisual::gemFull;
                    if(!seam && (owner == nullptr || seat->isAlliedSeat(owner))) continue;
                    if(!map.pathExists(worker, heart, tile))
                    {
                        blocked = true;
                        blockedTile = tile;
                    }
                }
        }
        edge("RouteBlocked", AiEventType::RouteBlocked, blocked, blockedTile);
    }
    // TunnelOpen, EnemyOut, EnemyTrapEmpty and FightOver are polled by L9 with its war state.
    // Loot and LabIdle have no condition or keeper command (class N); internal war events also belong to L9.
    return false;
}

//! \brief Saves symptom edges, counter history and the observed build timer across loading.
void AiEvents::save(std::vector<AiMath::AiStateLine>& lines)
{
    load();
    lines.erase(std::remove_if(lines.begin(), lines.end(), [](const AiMath::AiStateLine& line)
    {
        return line.tag == "draw" && line.tokens.size() == 3 && line.tokens[0] == "I06" &&
            (line.tokens[1].compare(0, 4, "poll") == 0 || line.tokens[1].compare(0, 4, "edge") == 0);
    }), lines.end());
    const double now = mAi.getMind().now();
    lines.push_back({"draw", {"I06", "pollArrival", eventNumber(mArrival)}});
    lines.push_back({"draw", {"I06", "pollPayday", eventNumber(mPayday)}});
    lines.push_back({"draw", {"I06", "pollBuild", eventNumber(mBuildDue - now)}});
    lines.push_back({"draw", {"I06", "pollPotions", eventNumber(mPotions)}});
    lines.push_back({"draw", {"I06", "pollPendingArrival", eventNumber(mPendingArrival)}});
    for(const std::pair<const std::string, bool>& entry : mEdges)
        lines.push_back({"draw", {"I06", "edge" + entry.first, eventNumber(entry.second)}});
}
