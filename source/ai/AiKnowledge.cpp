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

#include "ai/AiKnowledge.h"

#include "ai/AiActions.h"
#include "ai/AiMind.h"
#include "ai/KeeperAI.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomDungeonTemple.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>

namespace
{
//! \brief One uniform draw in [0, 1) for the pure functions of AiMath.
double uniform01()
{
    return Random::Double(0.0, 1.0);
}

//! \brief The value of a [KeeperAI] key of ai.cfg.
double aiKey(const std::string& key)
{
    return ConfigManager::getSingleton().getAiConfigDouble(key);
}

//! \brief The own dungeon heart tile of the seat, or nullptr when it has no dungeon temple.
Tile* ownHeartTile(GameMap& gameMap, Seat* seat)
{
    std::vector<Room*> temples = gameMap.getRoomsByTypeAndSeat(RoomType::dungeonTemple, seat);
    if(temples.empty())
        return nullptr;

    RoomDungeonTemple* temple = static_cast<RoomDungeonTemple*>(temples.front());
    return temple->getHeartTile();
}

//! \brief The tiles of a straight line between two tiles, joined by edges (no diagonal step).
void lineTiles(GameMap& gameMap, int x0, int y0, int x1, int y1, std::vector<Tile*>& out)
{
    int steps = std::max(std::abs(x1 - x0), std::abs(y1 - y0));
    int prevX = x0;
    int prevY = y0;
    for(int i = 0; i <= steps; ++i)
    {
        double t = (steps == 0) ? 0.0 : static_cast<double>(i) / steps;
        int x = static_cast<int>(std::lround(x0 + (x1 - x0) * t));
        int y = static_cast<int>(std::lround(y0 + (y1 - y0) * t));
        if((x != prevX) && (y != prevY))
        {
            Tile* bridge = gameMap.getTile(x, prevY);
            if(bridge != nullptr)
                out.push_back(bridge);
        }
        Tile* tile = gameMap.getTile(x, y);
        if(tile != nullptr)
            out.push_back(tile);
        prevX = x;
        prevY = y;
    }
}
}

AiKnowledge::AiKnowledge(GameMap& gameMap, Seat* seat) :
    mGameMap(gameMap),
    mSeat(seat)
{
}

bool AiKnowledge::isKnown(Tile* tile) const
{
    // AI row L03: hard limit, an AI seat reads only tiles it has seen
    if(tile == nullptr)
        return false;

    if(!mGameMap.getIsFOWActivated())
        return true;

    if(tile->getSeat() == mSeat)
        return true;

    if(mGameMap.everVisitedFlagPool == nullptr)
        return false;

    return mGameMap.everVisitedFlagPool[tile->getX()][tile->getY()][mSeat->getId()];
}

Tile* AiKnowledge::nearestKnownEnemyTile(const SightingState& sighting) const
{
    Tile* heart = ownHeartTile(mGameMap, mSeat);
    if(heart == nullptr)
        return nullptr;

    Tile* best = nullptr;
    double bestDistance = 0.0;
    int sizeX = mGameMap.getMapSizeX();
    int sizeY = mGameMap.getMapSizeY();
    for(int x = 0; x < sizeX; ++x)
    {
        for(int y = 0; y < sizeY; ++y)
        {
            Tile* tile = mGameMap.getTile(x, y);
            if((tile == nullptr) || !isKnown(tile))
                continue;

            Seat* owner = tile->getSeat();
            if((owner == nullptr) || owner->isAlliedSeat(mSeat))
                continue;

            double dx = tile->getX() - heart->getX();
            double dy = tile->getY() - heart->getY();
            double distance = std::sqrt(dx * dx + dy * dy);
            if((best == nullptr) || (distance < bestDistance))
            {
                best = tile;
                bestDistance = distance;
            }
        }
    }

    // Tiles on which the seat saw an enemy creature
    for(const std::pair<const int, SeatSighting>& seatEntry : sighting.seats)
    {
        for(const std::pair<const std::string, EnemyRecord>& record : seatEntry.second.records)
        {
            Tile* tile = record.second.tile;
            if(tile == nullptr)
                continue;

            double dx = tile->getX() - heart->getX();
            double dy = tile->getY() - heart->getY();
            double distance = std::sqrt(dx * dx + dy * dy);
            if((best == nullptr) || (distance < bestDistance))
            {
                best = tile;
                bestDistance = distance;
            }
        }
    }
    return best;
}

bool AiKnowledge::planRoute(KeeperAI& ai, Mind& mind, const AiSettings& settings, Tile* start, Tile* target, double& detour) const
{
    // AI row I02: the detour represents "only the explored map is known"
    if((start == nullptr) || (target == nullptr))
        return false;

    AiMath::Uniform01 u = uniform01;
    double sigma = aiKey("DetourSigma");
    detour = AiMath::lognormalMedian(settings.tunnelDetour, sigma, u);
    // Mistake: a winding route (the longer of two draws)
    if(mind.slip("I02"))
        detour = std::max(detour, AiMath::lognormalMedian(settings.tunnelDetour, sigma, u));

    double dx = target->getX() - start->getX();
    double dy = target->getY() - start->getY();
    double distance = std::sqrt(dx * dx + dy * dy);
    if(distance < 1.0)
        return false;

    // The waypoint lies on the perpendicular through the middle so that start - waypoint - target is (1 + detour) x distance long
    double half = distance / 2.0;
    double legLength = (1.0 + detour) * half;
    double offset = std::sqrt(std::max(0.0, legLength * legLength - half * half));
    double side = (uniform01() < 0.5) ? 1.0 : -1.0;
    double wx = start->getX() + dx / 2.0 + side * offset * (-dy / distance);
    double wy = start->getY() + dy / 2.0 + side * offset * (dx / distance);
    int wpx = std::max(0, std::min(mGameMap.getMapSizeX() - 1, static_cast<int>(std::lround(wx))));
    int wpy = std::max(0, std::min(mGameMap.getMapSizeY() - 1, static_cast<int>(std::lround(wy))));

    std::vector<Tile*> route;
    lineTiles(mGameMap, start->getX(), start->getY(), wpx, wpy, route);
    lineTiles(mGameMap, wpx, wpy, target->getX(), target->getY(), route);

    // Only tiles to dig: an unknown tile may be marked like a human may, a known one only when it is diggable
    std::vector<Tile*> toDig;
    for(Tile* tile : route)
    {
        if(std::find(toDig.begin(), toDig.end(), tile) != toDig.end())
            continue;
        if(isKnown(tile) && (!tile->isDiggable(mSeat) || (tile->getFullness() == 0.0)))
            continue;
        toDig.push_back(tile);
    }
    if(toDig.empty())
        return false;

    // At most DigActions drags
    size_t drags = static_cast<size_t>(std::max(1.0, aiKey("DigActions")));
    size_t perDrag = (toDig.size() + drags - 1) / drags;
    for(size_t first = 0; first < toDig.size(); first += perDrag)
    {
        size_t last = std::min(toDig.size(), first + perDrag);
        std::vector<Tile*> drag(toDig.begin() + first, toDig.begin() + last);
        ACTS::markDig(ai, drag, true);
    }
    return true;
}

std::vector<Creature*> AiKnowledge::visibleEnemyFighters() const
{
    std::vector<Creature*> seen;
    for(Seat* seat : mGameMap.getSeats())
    {
        if((seat == mSeat) || seat->isAlliedSeat(mSeat))
            continue;

        for(Creature* creature : mGameMap.getCreaturesBySeat(seat))
        {
            if(creature->getDefinition()->isWorker() || !creature->isAlive())
                continue;

            Tile* tile = creature->getPositionTile();
            if(tile == nullptr)
                continue;

            const std::vector<Seat*>& viewers = tile->getSeatsWithVision();
            if(std::find(viewers.begin(), viewers.end(), mSeat) != viewers.end())
                seen.push_back(creature);
        }
    }
    return seen;
}

void AiKnowledge::scout(KeeperAI& ai, Mind& mind, const AiSettings& settings, SightingState& sighting, double now,
                        double trapPotential, bool trapReady, bool ownTraps) const
{
    // AI row I03: unless the mistake is drawn the AI looks at the enemy before the decision
    if(mind.slip("I03"))
        return;

    std::vector<Creature*> seen = visibleEnemyFighters();
    for(Seat* seat : mGameMap.getSeats())
    {
        if((seat == mSeat) || seat->isAlliedSeat(mSeat))
            continue;

        SeatSighting& entry = sighting.seats[seat->getId()];
        // Records of dead creatures are removed, the ones seen now written, unseen ones kept
        std::vector<Creature*> known = mGameMap.getCreaturesBySeat(seat);
        for(std::map<std::string, EnemyRecord>::iterator it = entry.records.begin(); it != entry.records.end();)
        {
            bool alive = false;
            for(Creature* creature : known)
            {
                if((creature->getName() == it->first) && creature->isAlive())
                {
                    alive = true;
                    break;
                }
            }
            if(alive)
                ++it;
            else
                it = entry.records.erase(it);
        }
        for(Creature* creature : seen)
        {
            if(creature->getSeat() != seat)
                continue;
            EnemyRecord record;
            record.hp = creature->getHP();
            record.rawDps = creature->getRawDamagePerSecond();
            record.tile = creature->getPositionTile();
            entry.records[creature->getName()] = record;
        }

        AiMath::Uniform01 u = uniform01;
        double sigma = settings.estimateNoise;
        entry.fHp = AiMath::lognormalMedian(1.0, sigma, u);
        entry.fDps = AiMath::lognormalMedian(1.0, sigma, u);
        entry.fGold = AiMath::lognormalMedian(1.0, sigma, u);
        entry.fMana = AiMath::lognormalMedian(1.0, sigma, u);
        entry.fTrap = AiMath::lognormalMedian(1.0, sigma, u);
        bool flip = uniform01() <= sigma * aiKey("EstimateReadyFlipRate");
        entry.ready = flip ? !trapReady : trapReady;
        entry.trapBase = trapPotential;
        entry.ownTraps = ownTraps;
        entry.time = now;
        entry.valid = !entry.records.empty();
    }

    mind.exec("camera", static_cast<int>(aiKey("ScoutCameraActions")), now, "I03", nullptr, "", std::function<void()>());
}

EnemyEstimate AiKnowledge::estimateEnemy(const AiSettings& settings, const SightingState& sighting, int seatId, double now,
                                         double ownHp, double ownDps, double ownMana, double ownTrap, double ownIncome) const
{
    // AI row I04: the last sighting is used as seen, it is never aged
    EnemyEstimate estimate;
    std::map<int, SeatSighting>::const_iterator found = sighting.seats.find(seatId);
    double lastSpell = (found == sighting.seats.end()) ? -1.0 : found->second.lastSpellTime;
    bool observed = (settings.enemyManaEstimate == EnemyManaEstimateMode::observed);
    // Enemy mana, mode observed: the income since the last cast the AI saw (or since game start)
    double sinceCast = std::max(0.0, now - std::max(0.0, lastSpell));
    double observedMana = std::min(ConfigManager::getSingleton().getMaxManaPerSeat(), ownIncome * sinceCast);

    if((found == sighting.seats.end()) || !found->second.valid)
    {
        AiMath::Uniform01 u = uniform01;
        double f = AiMath::lognormalMedian(1.0, aiKey("EstimateNoSightingNoise"), u);
        estimate.hp = ownHp * f;
        estimate.dps = ownDps * f;
        estimate.gold = aiKey("EstimateGoldDefault");
        estimate.mana = observed ? observedMana : ownMana;
        estimate.trap = ownTrap;
        estimate.ready = true;
        estimate.ownTraps = true;
        return estimate;
    }

    const SeatSighting& sight = found->second;
    double hp = 0.0;
    double dps = 0.0;
    for(const std::pair<const std::string, EnemyRecord>& record : sight.records)
    {
        hp += record.second.hp;
        dps += record.second.rawDps;
    }
    estimate.hp = hp * sight.fHp;
    estimate.dps = dps * sight.fDps;
    estimate.gold = aiKey("EstimateGoldDefault") * sight.fGold;
    estimate.mana = observed ? observedMana * sight.fMana : ownMana * sight.fMana;
    estimate.trap = sight.ownTraps ? sight.trapBase : sight.trapBase * sight.fTrap;
    estimate.ready = sight.ready;
    estimate.ownTraps = sight.ownTraps;
    return estimate;
}

bool AiKnowledge::exploreTunnels(KeeperAI& ai, Mind& mind, bool& marked) const
{
    // AI row I05: one exploration tunnel per direction, marked once; the mistake is that no tunnel is marked at this look
    if(marked)
        return false;

    if(mind.slip("I05"))
        return false;

    Tile* heart = ownHeartTile(mGameMap, mSeat);
    if(heart == nullptr)
        return false;

    static const int directionX[4] = {0, 1, 0, -1};
    static const int directionY[4] = {-1, 0, 1, 0};
    int perDirection = static_cast<int>(aiKey("ExploreTunnelsPerDirection"));
    bool any = false;
    for(int direction = 0; direction < 4; ++direction)
    {
        for(int k = 0; k < perDirection; ++k)
        {
            std::vector<Tile*> tunnel;
            // Start at the outermost own claimed tile on the line through the heart, then go toward the map edge
            int x = heart->getX();
            int y = heart->getY();
            Tile* tile = mGameMap.getTile(x, y);
            while((tile != nullptr) && (tile->getSeat() == mSeat) && (tile->getFullness() == 0.0))
            {
                x += directionX[direction];
                y += directionY[direction];
                tile = mGameMap.getTile(x, y);
            }
            while(tile != nullptr)
            {
                bool known = isKnown(tile);
                // Ends before a known tile that cannot be dug or that another seat owns
                if(known && (tile->getFullness() > 0.0) && !tile->isDiggable(mSeat))
                    break;
                if(known && (tile->getSeat() != nullptr) && (tile->getSeat() != mSeat))
                    break;
                if(!known || (tile->getFullness() > 0.0))
                    tunnel.push_back(tile);
                x += directionX[direction];
                y += directionY[direction];
                tile = mGameMap.getTile(x, y);
            }
            if(tunnel.empty())
                continue;

            ACTS::markDig(ai, tunnel, true);
            any = true;
        }
    }
    marked = true;
    return any;
}
