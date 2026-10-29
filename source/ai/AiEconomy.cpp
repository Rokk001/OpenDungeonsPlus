#include "ai/AiEconomy.h"

#include "ai/AiActions.h"
#include "ai/AiKnowledge.h"
#include "ai/AiRooms.h"
#include "ai/AiTraps.h"
#include "ai/KeeperAI.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "spells/SpellSummonWorker.h"
#include "spells/SpellType.h"
#include "traps/Trap.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <map>
#include <sstream>

namespace
{
//! \brief Reads an economy rule from the existing AI configuration.
double key(const std::string& name)
{
    return ConfigManager::getSingleton().getAiConfigDouble(name);
}

//! \brief Returns squared straight-line distance without changing tile knowledge.
double distance(Tile* first, Tile* second)
{
    double x = first->getX() - second->getX();
    double y = first->getY() - second->getY();
    return x * x + y * y;
}

//! \brief Returns owned room tiles of one type, including disconnected blocks.
std::vector<Tile*> roomTiles(KeeperAI& ai, RoomType type)
{
    std::vector<Tile*> tiles;
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(type, ai.getControlledPlayer().getSeat()))
    {
        std::vector<Tile*> covered = room->getCoveredTiles();
        tiles.insert(tiles.end(), covered.begin(), covered.end());
    }
    return tiles;
}

//! \brief Finds a legal own spell tile, preferring the heart.
Tile* castTile(KeeperAI& ai)
{
    std::vector<Tile*> tiles = roomTiles(ai, RoomType::dungeonTemple);
    for(Tile* tile : tiles)
    {
        if(!tile->isFullTile())
            return tile;
    }
    return nullptr;
}

//! \brief Checks research, cooldown and the mana reserve of Create Gold.
bool canCreateGold(KeeperAI& ai)
{
    Player& player = ai.getControlledPlayer();
    return SkillManager::isSpellAvailable(SpellType::createGold, player.getSeat()) &&
        player.getSpellCooldownTurns(SpellType::createGold) == 0 && castTile(ai) != nullptr &&
        player.getSeat()->getMana() >= ConfigManager::getSingleton().getSpellConfigDouble("CreateGoldPrice") +
            key("CreateGoldManaReserve") * ConfigManager::getSingleton().getMaxManaPerSeat();
}

//! \brief Restores reserve times relative to the newly loaded Mind clock once.
void restoreReserve(KeeperAI& ai)
{
    ECON::EconomyState& state = ai.getEconomyState();
    if(state.restored)
        return;
    state.restored = true;
    for(const AiMath::AiStateLine& line : ai.getMind().savedRows())
    {
        if(line.tag != "draw" || line.tokens.size() != 3 || line.tokens[0] != "A04")
            continue;
        double remaining = 0.0;
        std::istringstream value(line.tokens[2]);
        if(!(value >> remaining))
            continue;
        if(line.tokens[1] == "slipFrom")
            state.reserveSlipAt = ai.getMind().now() + remaining;
        else if(line.tokens[1] == "slipUntil")
            state.reserveUntil = ai.getMind().now() + remaining;
    }
}

//! \brief Draws the next reserve-slip window once for the delivered payday.
void payday(KeeperAI& ai, const AiEvent&)
{
    restoreReserve(ai);
    ECON::EconomyState& state = ai.getEconomyState();
    state.reserveSlipAt = -1.0;
    state.reserveUntil = -1.0;
    if(!ai.getMind().slip("A04"))
        return;
    double period = ConfigManager::getSingleton().getTimePayDay();
    double start = std::min(Random::Double(key("ReserveSlipStartMin"), key("ReserveSlipStartMax")) * period,
        period - key("WalletReserveWindow"));
    state.reserveUntil = ai.getMind().now() + ai.getGameMap().getTimeToPayDay();
    state.reserveSlipAt = state.reserveUntil - period + start;
}

//! \brief Returns known own land where another walker can enter.
std::vector<Tile*> entrances(KeeperAI& ai)
{
    std::vector<Tile*> result;
    GameMap& map = ai.getGameMap();
    Seat* seat = ai.getControlledPlayer().getSeat();
    AiKnowledge knowledge(map, seat);
    for(int x = 0; x < map.getMapSizeX(); ++x)
    {
        for(int y = 0; y < map.getMapSizeY(); ++y)
        {
            Tile* tile = map.getTile(x, y);
            if(!knowledge.isKnown(tile) || !tile->isClaimedForSeat(seat))
                continue;
            for(Tile* next : tile->getAllNeighbors())
            {
                if(knowledge.isKnown(next) && !next->isFullTile() && !next->isClaimedForSeat(seat))
                {
                    result.push_back(tile);
                    break;
                }
            }
        }
    }
    return result;
}
}

namespace
{
//! \brief Saves the remaining wage-reserve mistake interval without duplicating imported rows.
void saveEconomy(KeeperAI& ai, std::vector<AiMath::AiStateLine>& lines)
{
    restoreReserve(ai);
    const std::function<bool(const AiMath::AiStateLine&)> owned = [](const AiMath::AiStateLine& line)
    {
        return line.tag == "draw" && !line.tokens.empty() && line.tokens[0] == "A04";
    };
    lines.erase(std::remove_if(lines.begin(), lines.end(), owned), lines.end());
    const ECON::EconomyState& state = ai.getEconomyState();
    if(state.reserveUntil > ai.getMind().now())
    {
        std::ostringstream from, until;
        from.precision(17);
        until.precision(17);
        from << state.reserveSlipAt - ai.getMind().now();
        until << state.reserveUntil - ai.getMind().now();
        lines.push_back({"draw", {"A04", "slipFrom", from.str()}});
        lines.push_back({"draw", {"A04", "slipUntil", until.str()}});
    }

}

//! \brief Reports the empty mining queue only when a worker exists.
bool noMarkedTiles(KeeperAI& ai)
{
    return ai.getControlledPlayer().getSeat()->getNumCreaturesWorkers() > 0 &&
        ai.getControlledPlayer().getNbMarkedTiles() == 0;
}

//! \brief Reports whether the treasury cannot cover the next wage bill.
bool belowBill(KeeperAI& ai)
{
    return ai.getControlledPlayer().getSeat()->getGold() < ECON::wageBill(ai);
}
}

//! \brief Registers the economy triggers without drawing mistakes during registration.
void ECON::bind(KeeperAI& ai)
{
    Mind& mind = ai.getMind();
    mind.onLook("A01", key("LookPeriod60") / key("ReferenceScanPeriod"), std::bind(digQueueWatch, std::ref(ai)));
    mind.onPoll("A01", AiEventType::NoMarkedTile, std::bind(noMarkedTiles, std::ref(ai)));
    mind.onEvent("A01", {AiEventType::NoMarkedTile}, std::bind(digQueueWatch, std::ref(ai)));
    mind.onLook("A02", key("LookPeriod120") / key("ReferenceScanPeriod"), std::bind(claimWatch, std::ref(ai)));
    mind.onLook("A03", key("LookFactorSummon"), std::bind(summonWatch, std::ref(ai)));
    mind.onLook("A04", key("LookPeriod600") / key("ReferenceScanPeriod"), std::bind(walletGate, std::ref(ai), 0.0));
    mind.onEvent("A04", {AiEventType::Payday}, std::bind(payday, std::ref(ai), std::placeholders::_1));
    mind.onPoll("A05", AiEventType::GoldBelowBill, std::bind(belowBill, std::ref(ai)));
    mind.onEvent("A05", {AiEventType::GoldBelowBill}, std::bind(castCreateGold, std::ref(ai), false));
    mind.onLook("A06", key("LookPeriod120") / key("ReferenceScanPeriod"), std::bind(goldCapacityWatch, std::ref(ai)));
    mind.onLook("A07", key("LookPeriod60") / key("ReferenceScanPeriod"), std::bind(manaCapWatch, std::ref(ai)));
    mind.onEvent("A08", {AiEventType::GoldBelowBill}, std::bind(sellObsolete, std::ref(ai)));
    mind.onSave(std::bind(saveEconomy, std::ref(ai), std::placeholders::_1));
}

//! \brief Uses the game's actual level-dependent wages and unpaid fees.
double ECON::wageBill(KeeperAI& ai)
{
    double bill = 0.0;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(ai.getControlledPlayer().getSeat()))
        bill += creature->getDefinition()->getFee(creature->getLevel()) + creature->getGoldFee();
    return bill;
}

//! \brief Marks a known seam and its configured rings up to the mining stock target.
void ECON::digQueueWatch(KeeperAI& ai)
{
    // AI row A01
    if(ai.getMind().slip("A01"))
        return;
    Player& player = ai.getControlledPlayer();
    double share = ai.getMind().now() / 60.0 < key("MinerShareSwitchMinute") ? key("MinerShareEarly") : key("MinerShareLate");
    int wanted = static_cast<int>(std::ceil(key("MarkedTilesPerWorker") * share * player.getSeat()->getNumCreaturesWorkers())) - player.getNbMarkedTiles();
    if(wanted <= 0)
        return;
    GameMap& map = ai.getGameMap();
    AiKnowledge knowledge(map, player.getSeat());
    std::vector<Tile*> treasuries = roomTiles(ai, RoomType::treasury);
    Tile* seam = nullptr;
    double nearest = std::numeric_limits<double>::max();
    for(int x = 0; x < map.getMapSizeX(); ++x)
    {
        for(int y = 0; y < map.getMapSizeY(); ++y)
        {
            Tile* tile = map.getTile(x, y);
            if(!knowledge.isKnown(tile) || tile->getType() != TileType::gold || !tile->isDiggable(player.getSeat()) || tile->getMarkedForDigging(&player))
                continue;
            for(Tile* treasury : treasuries)
            {
                double d = distance(tile, treasury);
                if(d < nearest)
                {
                    nearest = d;
                    seam = tile;
                }
            }
        }
    }
    if(seam == nullptr)
        return;
    std::vector<Tile*> tiles;
    int rings = static_cast<int>(key("Leveltilesdig"));
    for(int ring = 0; ring <= rings && wanted > 0; ++ring)
    {
        for(int x = -ring; x <= ring && wanted > 0; ++x)
        {
            for(int y = -ring; y <= ring && wanted > 0; ++y)
            {
                if(std::max(std::abs(x), std::abs(y)) != ring)
                    continue;
                Tile* tile = map.getTile(seam->getX() + x, seam->getY() + y);
                if(knowledge.isKnown(tile) && tile->isDiggable(player.getSeat()) && !tile->getMarkedForDigging(&player))
                {
                    tiles.push_back(tile);
                    --wanted;
                }
            }
        }
    }
    if(!tiles.empty())
        ACTS::markDig(ai, tiles, true);
}

//! \brief Marks known diggable border tiles nearest the heart when claimable land is exhausted.
void ECON::claimWatch(KeeperAI& ai)
{
    // AI row A02
    if(ai.getMind().slip("A02"))
        return;
    GameMap& map = ai.getGameMap();
    Player& player = ai.getControlledPlayer();
    Seat* seat = player.getSeat();
    std::vector<Tile*> heart = roomTiles(ai, RoomType::dungeonTemple);
    if(heart.empty() || static_cast<double>(seat->getNumClaimedTiles()) - heart.size() >= map.getManaIncomeTilesCap())
        return;
    AiKnowledge knowledge(map, seat);
    std::vector<Tile*> candidates;
    for(int x = 0; x < map.getMapSizeX(); ++x)
    {
        for(int y = 0; y < map.getMapSizeY(); ++y)
        {
            Tile* tile = map.getTile(x, y);
            if(!knowledge.isKnown(tile) || !tile->isClaimedForSeat(seat))
                continue;
            for(Tile* next : tile->getAllNeighbors())
            {
                if(!knowledge.isKnown(next))
                    continue;
                if(!next->isFullTile() && !next->isClaimed())
                    return;
                if(next->isDiggable(seat) && !next->getMarkedForDigging(&player) &&
                    std::find(candidates.begin(), candidates.end(), next) == candidates.end())
                    candidates.push_back(next);
            }
        }
    }
    const std::function<bool(Tile*, Tile*)> nearest = [&heart](Tile* first, Tile* second)
    {
        return distance(first, heart.front()) < distance(second, heart.front());
    };
    std::sort(candidates.begin(), candidates.end(), nearest);
    size_t wanted = static_cast<size_t>(std::ceil(key("MarkedTilesPerWorker") * seat->getNumCreaturesWorkers()));
    if(candidates.size() > wanted)
        candidates.resize(wanted);
    if(!candidates.empty())
        ACTS::markDig(ai, candidates, true);
}

//! \brief Shares one summon decision between the worker and spell rows.
void ECON::summonWatch(KeeperAI& ai)
{
    // AI row A03
    // AI row E01
    if(ai.getMind().slip("A03"))
        return;
    Player& player = ai.getControlledPlayer();
    Seat* seat = player.getSeat();
    double price = SpellSummonWorker::getNextWorkerPriceForPlayer(&ai.getGameMap(), &player);
    if(seat->getNumCreaturesWorkers() < key("SummonWorkersMax") && seat->getMana() > key("SummonManaFactor") * price &&
        seat->getManaIncomePerSecond() > key("SummonIncomeMin") && SkillManager::isSpellAvailable(SpellType::summonWorker, seat) &&
        player.getSpellCooldownTurns(SpellType::summonWorker) == 0 && castTile(ai) != nullptr)
        ACTS::castSpell(ai, SpellType::summonWorker, castTile(ai));
}

//! \brief Applies the one saved reserve draw to every purchase without drawing again.
bool ECON::walletGate(KeeperAI& ai, double cost)
{
    // AI row A04
    // AI row D01
    restoreReserve(ai);
    const EconomyState& state = ai.getEconomyState();
    double now = ai.getMind().now();
    bool ignore = state.reserveSlipAt >= 0.0 && now >= state.reserveSlipAt && now < state.reserveUntil;
    return ai.getControlledPlayer().getSeat()->getGold() >= cost + key("RoomGoldMargin") + (ignore ? 0.0 : wageBill(ai)) + TRAP::reloadMargin(ai);
}

//! \brief Casts the shared gold spell with its configured reserve and mistake.
void ECON::castCreateGold(KeeperAI& ai, bool surplus)
{
    // AI row A05
    // AI row E13
    bool mistaken = ai.getMind().slip("A05");
    if(!canCreateGold(ai))
        return;
    Seat* seat = ai.getControlledPlayer().getSeat();
    double value = std::lround(SkillManager::getResearchValue(seat, SkillType::spellCreateGold,
        ConfigManager::getSingleton().getSpellConfigDouble("CreateGoldValue"), ResearchEffect::Gold));
    if((surplus && seat->getGold() + value <= seat->getGoldMax()) ||
        (!surplus && (mistaken || seat->getGold() < wageBill(ai))))
        ACTS::castSpell(ai, SpellType::createGold, castTile(ai));
}

//! \brief Extends storage only after both configured treasury blocks are present.
void ECON::goldCapacityWatch(KeeperAI& ai)
{
    // AI row A06
    if(ai.getMind().slip("A06"))
        return;
    Seat* seat = ai.getControlledPlayer().getSeat();
    if(seat->getGold() <= key("GoldShareBuild") * seat->getGoldMax())
        return;
    std::vector<std::pair<RoomType, uint32_t>> plan = KeeperAI::getRoomPlan();
    uint32_t required = 0, first = 0;
    for(const std::pair<RoomType, uint32_t>& entry : plan)
    {
        if(entry.first == RoomType::treasury)
        {
            if(first == 0)
                first = entry.second;
            required += entry.second;
        }
    }
    if(first > 0 && roomTiles(ai, RoomType::treasury).size() >= required)
        ROOMS::placeRoom(ai, RoomType::treasury, first);
}

//! \brief Tries gold, then the most wounded own-ground creature, then a worker.
void ECON::manaCapWatch(KeeperAI& ai)
{
    // AI row A07
    if(ai.getMind().slip("A07"))
        return;
    Player& player = ai.getControlledPlayer();
    Seat* seat = player.getSeat();
    if(seat->getMana() <= key("ManaShareSpend") * ConfigManager::getSingleton().getMaxManaPerSeat())
        return;
    double value = std::lround(SkillManager::getResearchValue(seat, SkillType::spellCreateGold,
        ConfigManager::getSingleton().getSpellConfigDouble("CreateGoldValue"), ResearchEffect::Gold));
    if(canCreateGold(ai) && seat->getGold() + value <= seat->getGoldMax())
    {
        castCreateGold(ai, true);
        return;
    }
    Creature* hurt = nullptr;
    double lowest = key("HealNeverAbove");
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(seat))
    {
        Tile* tile = creature->getPositionTile();
        double share = creature->getHP() / std::max(1.0, creature->getMaxHp());
        if(tile != nullptr && tile->isClaimedForSeat(seat) && creature->getHP() > 0.0 && share < lowest)
        {
            lowest = share;
            hurt = creature;
        }
    }
    if(hurt != nullptr && SkillManager::isSpellAvailable(SpellType::creatureHeal, seat) &&
        player.getSpellCooldownTurns(SpellType::creatureHeal) == 0 && seat->getMana() >= ConfigManager::getSingleton().getSpellConfigDouble("CreatureHealPrice"))
    {
        ACTS::castSpell(ai, SpellType::creatureHeal, hurt);
        return;
    }
    summonWatch(ai);
}

//! \brief Sells only specified redundant rooms or distant traps unless the sale mistake occurs.
void ECON::sellObsolete(KeeperAI& ai)
{
    // AI row A08
    bool mistaken = ai.getMind().slip("A08");
    if(canCreateGold(ai))
        return;
    Seat* seat = ai.getControlledPlayer().getSeat();
    if(seat->getGold() >= wageBill(ai))
        return;
    std::vector<std::pair<RoomType, uint32_t>> plan = KeeperAI::getRoomPlan();
    if(mistaken)
    {
        for(std::vector<std::pair<RoomType, uint32_t>>::reverse_iterator entry = plan.rbegin(); entry != plan.rend(); ++entry)
        {
            std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(entry->first, seat);
            if(!rooms.empty())
            {
                ACTS::sellRoomTiles(ai, rooms.back()->getCoveredTiles());
                return;
            }
        }
        return;
    }
    std::map<RoomType, uint32_t> minimumSize;
    for(const std::pair<RoomType, uint32_t>& entry : plan)
    {
        std::map<RoomType, uint32_t>::iterator found = minimumSize.find(entry.first);
        if(found == minimumSize.end() || entry.second < found->second)
            minimumSize[entry.first] = entry.second;
    }
    for(const std::pair<const RoomType, uint32_t>& entry : minimumSize)
    {
        std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(entry.first, seat);
        bool complete = false;
        for(Room* room : rooms)
            complete = complete || room->numCoveredTiles() >= entry.second;
        if(!complete)
            continue;
        for(Room* room : rooms)
        {
            if(room->numCoveredTiles() < entry.second)
                ACTS::sellRoomTiles(ai, room->getCoveredTiles());
        }
    }
    std::vector<Tile*> entryTiles = entrances(ai);
    if(entryTiles.empty())
        return;
    double limit = key("CannonMaxDoorDistance");
    for(Trap* trap : ai.getGameMap().getTraps())
    {
        if(trap->getSeat() != seat)
            continue;
        std::vector<Tile*> obsolete;
        for(Tile* tile : trap->getCoveredTiles())
        {
            bool far = true;
            for(Tile* entry : entryTiles)
                far = far && distance(tile, entry) > limit * limit;
            if(far)
                obsolete.push_back(tile);
        }
        if(!obsolete.empty())
            ACTS::sellTrapTiles(ai, obsolete);
    }
}
