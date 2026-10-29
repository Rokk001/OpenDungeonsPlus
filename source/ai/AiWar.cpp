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

#include "ai/AiWar.h"

#include "ODApplication.h"
#include "ai/AiActions.h"
#include "ai/AiCare.h"
#include "ai/AiKnowledge.h"
#include "ai/AiMath.h"
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
#include "rooms/RoomDungeonTemple.h"
#include "rooms/RoomType.h"
#include "spells/Spell.h"
#include "spells/SpellType.h"
#include "traps/Trap.h"
#include "traps/TrapDoor.h"
#include "traps/TrapType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <sstream>

namespace WAR
{
namespace
{
//! \brief One uniform draw in [0, 1) for the pure functions of AiMath.
double uniform01()
{
    return Random::Double(0.0, 1.0);
}

//! \brief The value of a [KeeperAI] key of ai.cfg.
double key(const std::string& name)
{
    return ConfigManager::getSingleton().getAiConfigDouble(name);
}

//! \brief The own dungeon temple of the AI, or nullptr when it has none.
RoomDungeonTemple* ownTemple(Env& env)
{
    std::vector<Room*> temples = env.gameMap.getRoomsByTypeAndSeat(RoomType::dungeonTemple, env.player.getSeat());
    if(temples.empty())
        return nullptr;
    return static_cast<RoomDungeonTemple*>(temples.front());
}

//! \brief The price of one Call to War.
double callToWarPrice()
{
    return ConfigManager::getSingleton().getSpellConfigDouble("CallToWarPrice");
}

//! \brief True when the AI may cast Call to War now: researched, off cooldown.
bool callToWarReady(Env& env)
{
    Seat* seat = env.player.getSeat();
    return SkillManager::isSpellAvailable(SpellType::callToWar, seat) &&
           (env.player.getSpellCooldownTurns(SpellType::callToWar) == 0);
}

//! \brief The war constants of AiMath read from ai.cfg in the order of the structure.
AiMath::WarConstants loadWarConstants()
{
    AiMath::WarConstants k;
    k.doorTimeCap = key("DoorTimeCap");
    k.fightEstimateDamageShare = key("FightEstimateDamageShare");
    k.estimateSetupSeconds = key("EstimateSetupSeconds");
    k.estimateRoomTiles = key("EstimateRoomTiles");
    k.estimateTileHp = key("EstimateTileHp");
    k.heartHealMargin = key("HeartHealMargin");
    k.heartBreakFallbackSeconds = key("HeartBreakFallbackSeconds");
    k.potentialCastsMax = key("PotentialCastsMax");
    k.potentialCastsBase = key("PotentialCastsBase");
    k.potentialCastPeriod = key("PotentialCastPeriod");
    k.spellPotentialEff = key("SpellPotentialEff");
    k.spellManaReserve = key("SpellManaReserve");
    k.maxManaPerSeat = ConfigManager::getSingleton().getMaxManaPerSeat();
    k.trapEff = key("TrapEff");
    k.trapPassSeconds = key("TrapPassSeconds");
    k.advFloor = key("AdvFloor");
    k.advHpFloorShare = key("AdvHpFloorShare");
    k.enemyHpFloorShare = key("EnemyHpFloorShare");
    k.strengthRatioCap = key("StrengthRatioCap");
    k.scorePenaltyBase = key("ScorePenaltyBase");
    k.scorePenaltyAllin = key("ScorePenaltyAllin");
    k.scorePenaltySingle = key("ScorePenaltySingle");
    k.scorePenaltySplit = key("ScorePenaltySplit");
    k.scorePenaltyRaid = key("ScorePenaltyRaid");
    k.scorePenaltyCounter = key("ScorePenaltyCounter");
    k.scorePenaltyCounterFactor = key("ScorePenaltyCounterFactor");
    k.bonusSplit = key("BonusSplit");
    k.bonusRaidBase = key("BonusRaidBase");
    k.bonusRaidGold = key("BonusRaidGold");
    k.bonusRaidGoldDivisor = key("BonusRaidGoldDivisor");
    k.bonusCounter = key("BonusCounter");
    k.groupShareSingle = key("GroupShareSingle");
    k.groupShareMain = key("GroupShareMain");
    k.groupShareRaidTactic = key("GroupShareRaidTactic");
    k.counterArmyShare = key("CounterArmyShare");
    return k;
}

//! \brief The trap kinds of the trap potential with their config prefix.
struct TrapKindInfo
{
    TrapType type;
    const char* prefix;
};

const TrapKindInfo TRAP_KINDS[6] = {
    {TrapType::spike, "Spike"}, {TrapType::cannon, "Cannon"}, {TrapType::gas, "Gas"},
    {TrapType::boulder, "Boulder"}, {TrapType::lightning, "Lightning"}, {TrapType::fireburst, "Fireburst"}};

//! \brief The trap set of a seat around a tile: the tiles within CannonMaxDoorDistance of the center, per kind.
//! \param revealedFor When not nullptr, only tiles this seat has seen count and ready is false when all are exhausted.
//! \param ready Receives false when every counted tile is exhausted.
std::vector<AiMath::TrapKindSet> trapSet(Env& env, Seat* owner, Tile* center, Seat* revealedFor, bool& ready)
{
    std::vector<AiMath::TrapKindSet> set;
    ready = true;
    if(center == nullptr)
        return set;

    double radius = key("CannonMaxDoorDistance");
    int counted = 0;
    int exhausted = 0;
    for(const TrapKindInfo& kind : TRAP_KINDS)
    {
        AiMath::TrapKindSet entry;
        entry.tiles = 0;
        double damage = 0.0;
        double shots = 0.0;
        for(Trap* trap : env.gameMap.getTraps())
        {
            if((trap->getSeat() != owner) || (trap->getType() != kind.type))
                continue;

            for(Tile* tile : trap->getCoveredTiles())
            {
                double dx = tile->getX() - center->getX();
                double dy = tile->getY() - center->getY();
                if(std::sqrt(dx * dx + dy * dy) > radius)
                    continue;
                if((revealedFor != nullptr) && !trap->isTileVisibleForSeat(tile, revealedFor))
                    continue;

                double minDamage = 0.0;
                double maxDamage = 0.0;
                if(!trap->getTileDamageRange(tile, minDamage, maxDamage))
                    continue;

                ++entry.tiles;
                damage += 0.5 * (minDamage + maxDamage);
                ++counted;
                if(trap->isTileExhausted(tile))
                    ++exhausted;
                else
                    shots += ConfigManager::getSingleton().getTrapConfigDoubleOrDefault(std::string(kind.prefix) + "NbShootsBeforeDeactivation", 1.0);
            }
        }
        if(entry.tiles == 0)
            continue;

        std::string prefix(kind.prefix);
        double reloadTurns = ConfigManager::getSingleton().getTrapConfigDoubleOrDefault(prefix + "ReloadTurns", 5.0);
        entry.reloadSeconds = reloadTurns / ODApplication::turnsPerSecond;
        entry.shots = shots / entry.tiles;
        // The research Damage effect of the trap kinds is not applied here
        entry.damagePerShot = damage / entry.tiles;
        entry.targets = key("TrapTargets" + prefix);
        entry.spike = (kind.type == TrapType::spike);
        set.push_back(entry);
    }
    if((revealedFor != nullptr) && (counted > 0) && (exhausted == counted))
        ready = false;
    return set;
}

//! \brief The researched damage spells of the AI.
//! \param enemyGround True when the spells are cast in enemy land (only Inferno and Tremor).
std::vector<AiMath::SpellOption> spellOptions(Env& env, bool enemyGround)
{
    std::vector<AiMath::SpellOption> options;
    Seat* seat = env.player.getSeat();
    ConfigManager& config = ConfigManager::getSingleton();

    if(!enemyGround && SkillManager::isSpellAvailable(SpellType::lightning, seat))
    {
        AiMath::SpellOption o;
        o.damagePerTarget = 0.5 * (config.getSpellConfigDouble("LightningDamageMin") + config.getSpellConfigDouble("LightningDamage")) *
            SkillManager::getResearchValue(seat, SkillType::spellLightning, 1.0, ResearchEffect::Damage);
        o.targets = key("SpellTargetsLightning");
        o.price = config.getSpellConfigDouble("LightningPrice");
        options.push_back(o);
    }
    if(!enemyGround && SkillManager::isSpellAvailable(SpellType::creatureExplosion, seat))
    {
        AiMath::SpellOption o;
        o.damagePerTarget = config.getSpellConfigDouble("CreatureExplosionValue") * config.getSpellConfigDouble("CreatureExplosionDuration") *
            SkillManager::getResearchValue(seat, SkillType::spellCreatureExplosion, 1.0, ResearchEffect::Damage);
        o.targets = key("SpellTargetsExplosion");
        o.price = config.getSpellConfigDouble("CreatureExplosionPrice");
        options.push_back(o);
    }
    if(SkillManager::isSpellAvailable(SpellType::tremor, seat))
    {
        AiMath::SpellOption o;
        o.damagePerTarget = 0.5 * (config.getSpellConfigDouble("TremorDamageMin") + config.getSpellConfigDouble("TremorDamage")) *
            SkillManager::getResearchValue(seat, SkillType::spellTremor, 1.0, ResearchEffect::Damage);
        o.targets = key("SpellTargetsTremor");
        o.price = config.getSpellConfigDouble("TremorPrice");
        options.push_back(o);
    }
    if(SkillManager::isSpellAvailable(SpellType::inferno, seat))
    {
        AiMath::SpellOption o;
        o.damagePerTarget = 0.5 * (config.getSpellConfigDouble("InfernoDamagePerTurnMin") + config.getSpellConfigDouble("InfernoDamagePerTurn")) *
            config.getSpellConfigDouble("InfernoNbTurns") *
            SkillManager::getResearchValue(seat, SkillType::spellInferno, 1.0, ResearchEffect::Damage);
        o.targets = key("SpellTargetsInferno");
        o.price = config.getSpellConfigDouble("InfernoPrice");
        options.push_back(o);
    }
    return options;
}

//! \brief True when a creature is a fighter that can take part: not a worker, alive, not in prison, not KO.
bool isFreeFighter(Creature* creature)
{
    return creature->isAlive() && !creature->getDefinition()->isWorker() && !creature->isInPrison() && !creature->isKo();
}

//! \brief Sorts creatures by single-creature power HP x rawDps, descending.
bool strongerFirst(Creature* a, Creature* b)
{
    return (a->getHP() * a->getRawDamagePerSecond()) > (b->getHP() * b->getRawDamagePerSecond());
}

//! \brief The tile that nearerToCenter measures distances to.
Tile* gSortCenter = nullptr;

//! \brief True when tile a is nearer to gSortCenter than tile b.
bool nearerToCenter(Tile* a, Tile* b)
{
    double da = std::pow(a->getX() - gSortCenter->getX(), 2) + std::pow(a->getY() - gSortCenter->getY(), 2);
    double db = std::pow(b->getX() - gSortCenter->getX(), 2) + std::pow(b->getY() - gSortCenter->getY(), 2);
    return da < db;
}

//! \brief True when creature a has fewer hit points than creature b.
bool lowerHpFirst(Creature* a, Creature* b)
{
    return a->getHP() < b->getHP();
}

//! \brief The legal drop tile among the neighbours of a tile that is nearest to it, skipping the first skip candidates.
Tile* dropTileNear(Env& env, Creature* creature, Tile* around, size_t skip)
{
    Seat* seat = env.player.getSeat();
    std::vector<Tile*> candidates;
    for(Tile* neighbour : around->getAllNeighbors())
    {
        if(creature->tryDrop(seat, neighbour))
            candidates.push_back(neighbour);
    }
    if(candidates.empty())
        return nullptr;

    gSortCenter = around;
    std::sort(candidates.begin(), candidates.end(), nearerToCenter);
    return candidates[std::min(skip, candidates.size() - 1)];
}

//! \brief Casts a Call to War banner on a tile and remembers it in the group.
//! \return false when the mana does not suffice.
bool castBanner(Env& env, Group& group, Tile* tile)
{
    if(env.player.getSeat()->getMana() < callToWarPrice())
        return false;

    ACTS::castSpell(env.ai, SpellType::callToWar, tile);
    group.bannerTile = tile;
    double lifeSeconds = ConfigManager::getSingleton().getSpellConfigDouble("CallToWarNbTurnsMax") / ODApplication::turnsPerSecond;
    group.bannerUntil = env.now + lifeSeconds;
    return true;
}

//! \brief True when a tile is claimed for the own seat.
bool isOwnGround(Env& env, Tile* tile)
{
    return (tile != nullptr) && tile->isClaimedForSeat(env.player.getSeat());
}

//! \brief The own fighters that stand on tiles not claimed for the own seat (the attackers of 1.7a item 4).
std::vector<Creature*> attackers(Env& env)
{
    std::vector<Creature*> result;
    for(Creature* creature : env.gameMap.getCreaturesBySeat(env.player.getSeat()))
    {
        if(!isFreeFighter(creature))
            continue;
        Tile* tile = creature->getPositionTile();
        if((tile != nullptr) && !isOwnGround(env, tile))
            result.push_back(creature);
    }
    return result;
}

//! \brief The sum of hit points times the sum of raw damage per second of creatures.
double powerOf(const std::vector<Creature*>& creatures)
{
    double hp = 0.0;
    double dps = 0.0;
    for(Creature* creature : creatures)
    {
        hp += creature->getHP();
        dps += creature->getRawDamagePerSecond();
    }
    return hp * dps;
}

//! \brief The id of the enemy seat the war aims at: the first non-allied seat that has a dungeon temple.
Seat* enemySeat(Env& env)
{
    Seat* own = env.player.getSeat();
    for(Seat* seat : env.gameMap.getSeats())
    {
        if((seat == own) || seat->isAlliedSeat(own))
            continue;
        if(!env.gameMap.getRoomsByTypeAndSeat(RoomType::dungeonTemple, seat).empty())
            return seat;
    }
    return nullptr;
}

//! \brief The tile of a known enemy room of the type nearest to the breakthrough tile, or nullptr when none is known.
Tile* knownRoomTile(Env& env, AiKnowledge& knowledge, Seat* enemy, RoomType type, bool smallest, bool largest)
{
    Tile* from = env.state.breakthrough;
    Room* chosen = nullptr;
    for(Room* room : env.gameMap.getRoomsByTypeAndSeat(type, enemy))
    {
        bool known = false;
        for(Tile* tile : room->getCoveredTiles())
        {
            if(knowledge.isKnown(tile))
            {
                known = true;
                break;
            }
        }
        if(!known)
            continue;
        if((chosen == nullptr) ||
           (smallest && (room->numCoveredTiles() < chosen->numCoveredTiles())) ||
           (largest && (room->numCoveredTiles() > chosen->numCoveredTiles())))
            chosen = room;
    }
    if(chosen == nullptr)
        return nullptr;

    Tile* best = nullptr;
    double bestDistance = 0.0;
    for(Tile* tile : chosen->getCoveredTiles())
    {
        if(!knowledge.isKnown(tile))
            continue;
        double distance = (from == nullptr) ? 0.0 :
            std::pow(tile->getX() - from->getX(), 2) + std::pow(tile->getY() - from->getY(), 2);
        if((best == nullptr) || (distance < bestDistance))
        {
            best = tile;
            bestDistance = distance;
        }
    }
    return best;
}

//! \brief The target tile of the group for the heart: the enemy heart when known, else the nearest known enemy tile.
Tile* heartTarget(Env& env, AiKnowledge& knowledge, Seat* enemy)
{
    if(enemy != nullptr)
    {
        std::vector<Room*> temples = env.gameMap.getRoomsByTypeAndSeat(RoomType::dungeonTemple, enemy);
        if(!temples.empty())
        {
            Tile* heart = static_cast<RoomDungeonTemple*>(temples.front())->getHeartTile();
            if(knowledge.isKnown(heart))
                return heart;
        }
    }
    return knowledge.nearestKnownEnemyTile(env.state.sighting);
}
}

void planDig(Env& env)
{
    // AI row I01: dig toward the nearest known enemy tile once ready; before it explore (row I05)
    WarState& st = env.state;
    if(st.tunnel != WarState::tunnelNone)
        return;

    Seat* seat = env.player.getSeat();
    AiKnowledge knowledge(env.gameMap, seat);
    Tile* target = knowledge.nearestKnownEnemyTile(st.sighting);
    if(target == nullptr)
    {
        knowledge.exploreTunnels(env.ai, env.mind, st.exploreMarked);
        return;
    }

    double minute = env.now / 60.0;
    int fighters = 0;
    for(Creature* creature : env.gameMap.getCreaturesBySeat(seat))
    {
        if(isFreeFighter(creature))
            ++fighters;
    }
    int workers = 0;
    for(Creature* creature : env.gameMap.getCreaturesBySeat(seat))
    {
        if(creature->getDefinition()->isWorker())
            ++workers;
    }
    int trapTiles = 0;
    bool hasDoor = false;
    for(Trap* trap : env.gameMap.getTraps())
    {
        if(trap->getSeat() != seat)
            continue;
        if(trap->isDoor())
            hasDoor = true;
        else
            trapTiles += static_cast<int>(trap->getCoveredTiles().size());
    }

    bool ready = (minute >= key("AttackMinMinute")) && (fighters >= key("AttackMinFighters")) &&
                 ((trapTiles >= key("AttackMinTrapTiles")) || hasDoor);
    bool early = (minute >= key("EarlyDigMinute")) && (fighters >= key("EarlyDigMinFighters"));
    bool start = false;
    if(ready)
        start = !env.mind.slip("I01");
    else if(early)
        start = env.mind.slip("I01", key("EarlyDigMultiplier"));
    if(!start)
        return;

    RoomDungeonTemple* temple = ownTemple(env);
    if((temple == nullptr) || (temple->getHeartTile() == nullptr))
        return;

    // Start event: row I02 plans the route and marks it
    double detour = 0.0;
    if(!knowledge.planRoute(env.ai, env.mind, env.settings, temple->getHeartTile(), target, detour))
        return;

    st.tunnel = WarState::tunnelDigging;
    st.detour = detour;
    st.tunnelTarget = target;
    st.tunnelKnown = true;
    st.nextProbe = env.now + key("TunnelProbeSeconds");
    // The tunnel start is announced to the rows that react to it (H03 hostile specials)
    env.mind.enqueue({AiEventType::Start, target, nullptr, -1, 0.0, env.now});
    (void)workers;
}

void planAttack(Env& env)
{
    // AI row K01: eligibility and the ready list
    // AI row K02: the estimate, the scores and the draw of the tactic
    // AI row J07: the counter tactic is valid only while the enemy assault is out
    WarState& st = env.state;
    Seat* seat = env.player.getSeat();
    if((st.tunnel != WarState::tunnelOpen) || !st.tunnelKnown || (st.assault != WarState::assaultNone))
        return;
    if(env.now - st.lastAssaultEnd < key("RestSecondsAfterAssault"))
        return;
    if(!callToWarReady(env) || (seat->getMana() < callToWarPrice()))
        return;
    if(st.breakthrough == nullptr)
        return;

    // A legal drop tile next to the breakthrough tile must exist
    std::vector<Creature*> ready;
    for(Creature* creature : env.gameMap.getCreaturesBySeat(seat))
    {
        if(!isFreeFighter(creature))
            continue;
        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;
        double share = creature->getHP() / std::max(1.0, creature->getMaxHp());
        // The rule mistake (row J08 class) is drawn for each fighter: only RestHpShareSlip is needed
        double needed = env.mind.slip("J08") ? key("RestHpShareSlip") : key("RestHpShare");
        if(share >= needed)
            ready.push_back(creature);
    }
    if(static_cast<int>(ready.size()) < static_cast<int>(key("AttackMinReady")))
        return;
    if(dropTileNear(env, ready.front(), st.breakthrough, 0) == nullptr)
        return;

    std::sort(ready.begin(), ready.end(), strongerFirst);

    AiKnowledge knowledge(env.gameMap, seat);
    RoomDungeonTemple* temple = ownTemple(env);
    if(temple == nullptr)
        return;

    bool ownContact = (st.contactTime >= 0.0) || (st.lastAssaultEnd > -1.0e17);
    bool trapReady = true;
    Seat* enemy = enemySeat(env);
    std::vector<AiMath::TrapKindSet> ownSet = trapSet(env, seat, st.breakthrough, nullptr, trapReady);
    AiMath::WarConstants k = loadWarConstants();
    double hpAll = 0.0;
    double dpsAll = 0.0;
    for(Creature* creature : ready)
    {
        hpAll += creature->getHP();
        dpsAll += creature->getRawDamagePerSecond();
    }

    // Scouting (row I03) with the trap set in use
    std::vector<AiMath::TrapKindSet> usedSet = ownSet;
    bool usedReady = true;
    if(ownContact && (enemy != nullptr))
        usedSet = trapSet(env, enemy, st.breakthrough, seat, usedReady);
    double doorSeconds = 8.0;
    double trapPotential = AiMath::trapPotential(usedSet, doorSeconds, 1.0, k);
    knowledge.scout(env.ai, env.mind, env.settings, st.sighting, env.now, trapPotential, usedReady, !ownContact);

    // Estimate (row I04)
    double ownIncome = seat->getManaIncomePerSecond();
    EnemyEstimate estimate = knowledge.estimateEnemy(env.settings, st.sighting, (enemy == nullptr) ? -1 : enemy->getId(), env.now,
                                                     hpAll, dpsAll, seat->getMana(), trapPotential, ownIncome);

    AiMath::AdvantageInput in;
    in.hpAll = hpAll;
    in.dpsAll = dpsAll;
    in.ownDoorHp = TrapDoor::getEstimatedDoorHp(seat);
    in.heartHp = temple->getHeartMaxHP();
    in.heartHeal = temple->getHeartHealPerSecond();
    in.mySpells = spellOptions(env, true);
    in.myMana = seat->getMana();
    in.enemySpells = spellOptions(env, false);
    in.enemyMana = estimate.mana;
    in.trapSet = usedSet;
    in.trapReady = 1.0;
    in.trapFactor = (trapPotential > 0.0) ? estimate.trap / trapPotential : 1.0;
    in.estimateReady = estimate.ready ? 1.0 : 0.0;
    in.enemyHp = estimate.hp;
    in.enemyDps = estimate.dps;
    in.attackAdvantage = env.settings.attackAdvantage;

    AiMath::TacticScores scores = AiMath::tacticScores(in, estimate.gold, st.enemyOut, k);
    int tactic = env.mind.drawTactic(env.settings.tacticPriors, scores, env.settings.tacticTemperature);
    if(tactic < 0)
        return;

    launch(env, tactic, ready, estimate);
}

void launch(Env& env, int tactic, const std::vector<Creature*>& ready, const EnemyEstimate& estimate)
{
    // AI row K03: the groups of the tactic
    // AI row K04: the raid targets
    // AI row K05: the gathering (hand moves or only banners)
    WarState& st = env.state;
    Seat* seat = env.player.getSeat();
    AiKnowledge knowledge(env.gameMap, seat);
    Seat* enemy = enemySeat(env);
    int n = static_cast<int>(ready.size());
    AiMath::WarConstants k = loadWarConstants();

    std::vector<Creature*> mainGroup;
    std::vector<Creature*> raidGroup;
    // Indices 0 allin, 1 single, 2 split, 3 raid, 4 counter
    if(tactic == 0)
        mainGroup = ready;
    else if(tactic == 1)
        mainGroup.assign(ready.begin(), ready.begin() + AiMath::takeIndex(k.groupShareSingle, n));
    else if(tactic == 2)
    {
        int mainEnd = AiMath::takeIndex(k.groupShareMain, n);
        int raidEnd = AiMath::takeIndex(k.groupShareMain + key("GroupShareRaid"), n);
        mainGroup.assign(ready.begin(), ready.begin() + mainEnd);
        raidGroup.assign(ready.begin() + mainEnd, ready.begin() + std::max(mainEnd, raidEnd));
    }
    else if(tactic == 3)
        raidGroup.assign(ready.begin(), ready.begin() + AiMath::takeIndex(k.groupShareRaidTactic, n));
    else
        mainGroup.assign(ready.begin(), ready.begin() + AiMath::takeIndex(k.counterArmyShare, n));

    // The raid target list: rich or no mistake - economy rooms, else the other list; a second mistake permutes
    std::vector<RoomType> order;
    if((estimate.gold > key("RaidGoldThreshold")) || !env.mind.slip("K04"))
    {
        order.push_back(RoomType::treasury);
        order.push_back(RoomType::treasury);
        order.push_back(RoomType::library);
    }
    else
    {
        order.push_back(RoomType::library);
        order.push_back(RoomType::hatchery);
        order.push_back(RoomType::dormitory);
    }
    if(env.mind.slip("K04"))
    {
        order.clear();
        order.push_back(RoomType::treasury);
        order.push_back(RoomType::treasury);
        order.push_back(RoomType::library);
        order.push_back(RoomType::hatchery);
        order.push_back(RoomType::dormitory);
        order.push_back(RoomType::trainingHall);
        for(size_t i = order.size(); i > 1; --i)
            std::swap(order[i - 1], order[static_cast<size_t>(Random::Int(0, static_cast<int32_t>(i) - 1))]);
    }

    std::vector<Group> groups;
    Tile* heart = heartTarget(env, knowledge, enemy);
    if(!mainGroup.empty())
    {
        Group g;
        g.members = mainGroup;
        if(heart != nullptr)
            g.targets.push_back(heart);
        groups.push_back(g);
    }
    if(!raidGroup.empty())
    {
        Group g;
        g.raid = true;
        g.members = raidGroup;
        size_t wanted = static_cast<size_t>(key((tactic == 3) ? "RaidTargetsRaid" : "RaidTargetsSplit"));
        bool firstTreasury = true;
        for(RoomType type : order)
        {
            if(g.targets.size() >= wanted)
                break;
            // The first treasury entry is the larger known block, the second the smaller
            Tile* tile = knownRoomTile(env, knowledge, enemy, type, !firstTreasury && (type == RoomType::treasury),
                                       firstTreasury && (type == RoomType::treasury));
            if(type == RoomType::treasury)
                firstTreasury = false;
            if(tile != nullptr)
                g.targets.push_back(tile);
        }
        if(g.targets.empty() && (heart != nullptr))
            g.targets.push_back(heart);
        groups.push_back(g);
    }
    if(groups.empty())
        return;

    // One banner per group; groups are removed from the end until the mana suffices
    while(!groups.empty() && (seat->getMana() < groups.size() * callToWarPrice()))
        groups.pop_back();
    if(groups.empty())
        return;

    // The drop tiles: the nearest legal tile for the first group, the second nearest for the raid group
    for(size_t i = 0; i < groups.size(); ++i)
    {
        Group& g = groups[i];
        g.dropTile = dropTileNear(env, g.members.front(), st.breakthrough, (groups.size() > 1 && g.raid) ? 1 : 0);
        if(g.dropTile == nullptr)
            return;
    }
    // The raid group of a split is moved and its banner cast first
    if((groups.size() > 1) && !groups[0].raid && groups[1].raid)
        std::swap(groups[0], groups[1]);

    // Gathering decision (row E07 class complex, drawn here as K05): a mistake skips the hand moves
    bool walkFromHome = env.mind.slip("K05");
    for(Group& g : groups)
    {
        if(!walkFromHome)
        {
            std::vector<Creature*> moved;
            for(Creature* creature : g.members)
            {
                if(!creature->tryPickup(seat) || !creature->tryDrop(seat, g.dropTile))
                    continue;
                ACTS::moveCreature(env.ai, creature, g.dropTile);
                moved.push_back(creature);
            }
            g.members = moved;
        }
        if(g.targets.empty())
        {
            g.finished = true;
            continue;
        }
        castBanner(env, g, g.targets.front());
    }

    st.groups = groups;
    st.assault = WarState::assaultMoving;
    st.tactic = tactic;
    st.contactTime = -1.0;
    st.nextRetreatCheck = env.now + key("RetreatCheckSeconds");
    // The chosen and dropped groups are announced to the rows that react to the launch (H03 hostile specials)
    env.mind.enqueue({AiEventType::Launch, groups.front().dropTile, nullptr, (enemy == nullptr) ? -1 : enemy->getId(),
                      0.0, env.now});
}

void assaultStep(Env& env)
{
    // AI row K09: banners are renewed and moved to the next target
    // AI row K07: the retreat test
    WarState& st = env.state;
    if(st.assault == WarState::assaultNone)
        return;

    Seat* seat = env.player.getSeat();
    AiKnowledge knowledge(env.gameMap, seat);
    Seat* enemy = enemySeat(env);
    bool allFinished = true;
    for(Group& g : st.groups)
    {
        if(g.finished)
            continue;

        bool alive = false;
        for(Creature* creature : g.members)
            alive = alive || (creature->isAlive() && !creature->isKo());
        if(!alive || (g.targetIndex >= g.targets.size()))
        {
            g.finished = true;
            continue;
        }
        allFinished = false;

        // The heart became known while the main group's banner stands elsewhere
        if(!g.raid && (g.targetIndex == 0))
        {
            Tile* heart = heartTarget(env, knowledge, enemy);
            if((heart != nullptr) && (g.bannerTile != heart))
            {
                if(g.bannerTile != nullptr)
                    ACTS::removeBanner(env.ai, g.bannerTile);
                g.targets[0] = heart;
                if(!castBanner(env, g, heart))
                    g.finished = true;
                continue;
            }
        }

        // The target is destroyed or no longer known: next target
        Tile* target = g.targets[g.targetIndex];
        Room* room = target->getCoveringRoom();
        bool gone = g.raid && ((room == nullptr) || (room->getSeat() == seat) || !knowledge.isKnown(target));
        if(gone)
        {
            if(g.bannerTile != nullptr)
                ACTS::removeBanner(env.ai, g.bannerTile);
            ++g.targetIndex;
            if((g.targetIndex >= g.targets.size()) || !castBanner(env, g, g.targets[g.targetIndex]))
                g.finished = true;
            continue;
        }

        // The banner lapsed: cast it again on the same tile
        if((g.bannerUntil >= 0.0) && (env.now >= g.bannerUntil))
        {
            if(!castBanner(env, g, target))
                g.finished = true;
        }
    }

    if(allFinished)
    {
        endAssault(env);
        return;
    }

    // Contact: the first attacker on a tile not claimed for the own seat
    std::vector<Creature*> out = attackers(env);
    if((st.contactTime < 0.0) && (st.lastFight > env.now - key("FightOverSeconds")) && !out.empty())
    {
        st.contactTime = env.now;
        st.assault = WarState::assaultRunning;
    }
    if(st.contactTime < 0.0)
        return;

    if(env.now - st.contactTime > key("ContactTimeoutSeconds"))
    {
        endAssault(env);
        return;
    }

    if(env.now < st.nextRetreatCheck)
        return;
    st.nextRetreatCheck = env.now + key("RetreatCheckSeconds");

    // Retreat test: a complex mistake keeps the assault going
    std::vector<Creature*> defenders;
    for(Creature* creature : env.gameMap.getCreaturesBySeat(enemy))
    {
        if(isFreeFighter(creature) && (creature->getPositionTile() != nullptr))
        {
            const std::vector<Seat*>& viewers = creature->getPositionTile()->getSeatsWithVision();
            if(std::find(viewers.begin(), viewers.end(), seat) != viewers.end())
                defenders.push_back(creature);
        }
    }
    if(out.empty() || (powerOf(out) < env.settings.retreatThreshold * powerOf(defenders)))
    {
        if(!env.mind.slip("K07"))
            endAssault(env);
    }
}

void secondWave(Env& env)
{
    // AI row K08: the enemy traps are empty, attack again at once; the mistake waits (no second wave now)
    WarState& st = env.state;
    if(env.mind.slip("K08"))
        return;

    st.secondWaveUntil = env.now + key("SecondWaveMinutes") * 60.0;
    // The rest after the last assault does not hold the second wave back
    st.lastAssaultEnd = -1.0e18;
    planAttack(env);
}

void endAssault(Env& env)
{
    // AI row K10: banners removed, survivors on enemy ground carried home by hand, the rest started
    WarState& st = env.state;
    Seat* seat = env.player.getSeat();
    for(Group& g : st.groups)
    {
        if(g.bannerTile != nullptr)
            ACTS::removeBanner(env.ai, g.bannerTile);
        g.bannerTile = nullptr;
    }

    RoomDungeonTemple* temple = ownTemple(env);
    std::vector<Creature*> survivors = attackers(env);
    std::sort(survivors.begin(), survivors.end(), strongerFirst);
    if((temple != nullptr) && !env.mind.slip("K10"))
    {
        std::vector<Tile*> templeTiles = temple->getCoveredTiles();
        for(Creature* creature : survivors)
        {
            for(Tile* tile : templeTiles)
            {
                if(creature->tryPickup(seat) && creature->tryDrop(seat, tile))
                {
                    ACTS::moveCreature(env.ai, creature, tile);
                    break;
                }
            }
        }
    }

    st.groups.clear();
    st.assault = WarState::assaultNone;
    st.tactic = -1;
    st.contactTime = -1.0;
    st.lastAssaultEnd = env.now;
}

void defend(Env& env, const AiEvent& event)
{
    // AI row J01: the alert delay of the Fight event has passed
    // AI row J02: rally the defenders unless the rule mistake is drawn
    // AI row J03: the complex mistake spreads the defenders instead of focussing them
    // AI row J06: a wave (hero) response uses the same rally
    WarState& st = env.state;
    Seat* seat = env.player.getSeat();
    if(st.defenceRallying)
        return;

    // The first contact tells a seat that did not dig about the open tunnel
    if(!st.tunnelKnown && (st.tunnel != WarState::tunnelNone))
        st.tunnelKnown = true;

    bool poor = env.mind.slip("J03");
    bool rally = !env.mind.slip("J02");
    if(!rally)
        return;

    std::vector<Creature*> home;
    for(Creature* creature : env.gameMap.getCreaturesBySeat(seat))
    {
        Tile* tile = creature->getPositionTile();
        if(isFreeFighter(creature) && isOwnGround(env, tile))
            home.push_back(creature);
    }
    std::sort(home.begin(), home.end(), strongerFirst);
    if(poor && (uniform01() < key("PoorDefenceShuffleChance")))
    {
        for(size_t i = home.size(); i > 1; --i)
            std::swap(home[i - 1], home[static_cast<size_t>(Random::Int(0, static_cast<int32_t>(i) - 1))]);
    }

    // The intruders in sight
    std::vector<Creature*> intruders;
    for(Seat* other : env.gameMap.getSeats())
    {
        if((other == seat) || other->isAlliedSeat(seat))
            continue;
        for(Creature* creature : env.gameMap.getCreaturesBySeat(other))
        {
            Tile* tile = creature->getPositionTile();
            if(isFreeFighter(creature) && isOwnGround(env, tile))
                intruders.push_back(creature);
        }
    }
    Tile* fightTile = event.tile;
    if(!intruders.empty())
    {
        Creature* chosen = intruders[static_cast<size_t>(Random::Int(0, static_cast<int32_t>(intruders.size()) - 1))];
        if(uniform01() < env.settings.focusFire)
        {
            chosen = *std::min_element(intruders.begin(), intruders.end(), lowerHpFirst);
        }
        fightTile = chosen->getPositionTile();
    }
    if(fightTile == nullptr)
        return;

    bool banner = callToWarReady(env) && (seat->getMana() >= callToWarPrice()) &&
                  (static_cast<int>(home.size()) > static_cast<int>(key("CallToWarMinCreatures"))) && !env.mind.slip("E07");
    if(banner)
    {
        ACTS::castSpell(env.ai, SpellType::callToWar, fightTile);
        st.defenceBanner = fightTile;
    }
    else
    {
        for(Creature* creature : home)
        {
            Tile* drop = dropTileNear(env, creature, fightTile, 0);
            if((drop != nullptr) && creature->tryPickup(seat))
                ACTS::moveCreature(env.ai, creature, drop);
        }
    }
    st.defenceRallying = true;
}

void heartGuard(Env& env)
{
    // AI row J05: hand the low heart to the defender possession of row D05; the complex mistake leaves the heart unprotected
    RoomDungeonTemple* temple = ownTemple(env);
    if((temple == nullptr) || (temple->getHeartHealthFraction() >= key("HeartPossessBelow")))
        return;
    if(env.mind.slip("J05"))
        return;

    // The possession itself is row D05's decision and draw
    const AiEvent critical = {AiEventType::HeartCritical, temple->getHeartTile(), nullptr, -1, 0.0, env.now};
    CARE::possessDefender(env.ai, critical);
}

void restAfterFight(Env& env)
{
    // AI row J08: fleeing creatures are carried to the dungeon temple; the rule mistake leaves them
    WarState& st = env.state;
    st.defenceRallying = false;
    if(st.defenceBanner != nullptr)
    {
        ACTS::removeBanner(env.ai, st.defenceBanner);
        st.defenceBanner = nullptr;
    }
    if(env.mind.slip("J08"))
        return;

    RoomDungeonTemple* temple = ownTemple(env);
    if((temple == nullptr) || (temple->getCentralTile() == nullptr))
        return;

    Seat* seat = env.player.getSeat();
    Tile* center = temple->getCentralTile();
    int area = static_cast<int>(key("HeartDefenceAreaTiles"));
    for(Creature* creature : env.gameMap.getCreaturesBySeat(seat))
    {
        if(!creature->isActionInList(CreatureActionType::flee))
            continue;
        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;
        if((std::abs(center->getX() - tile->getX()) <= area) && (std::abs(center->getY() - tile->getY()) <= area))
            continue;
        if(creature->tryPickup(seat) && creature->tryDrop(seat, center))
            ACTS::moveCreature(env.ai, creature, center);
    }
}

//! \brief Carries one hurt own creature to its bed, or to an own infirmary with a free place when it has no bed
//! (row J08 "wounded creatures to bed or infirmary" as the mood remedy of D07).
//! \param creature The hurt creature named by the mood patrol.
void restWounded(Env& env, Creature* creature)
{
    // Each hurt creature is its own firing with its own rule draw; the mistake leaves this creature where it is.
    // Already in its bed or in an infirmary, the creature stays.
    if((creature == nullptr) || !creature->isHurt() || (creature->getPositionTile() == nullptr) ||
       CARE::slipFor(env.ai, "J08"))
        return;

    Seat* seat = env.player.getSeat();
    Tile* tile = creature->getPositionTile();
    Room* room = tile->getCoveringRoom();
    if((tile == creature->getHomeTile()) || ((room != nullptr) && (room->getType() == RoomType::infirmary)))
        return;

    Tile* rest = creature->getHomeTile();
    if(rest == nullptr)
    {
        for(Room* infirmary : env.gameMap.getRoomsByTypeAndSeat(RoomType::infirmary, seat))
        {
            // The infirmary has no open-spot override; a free cot of the fitting size is its admission test
            if(!infirmary->hasCarryEntitySpot(creature))
                continue;
            for(Tile* covered : infirmary->getCoveredTiles())
            {
                if(covered->isClaimedForSeat(seat) && !covered->isFullTile())
                {
                    rest = covered;
                    break;
                }
            }
            if(rest != nullptr)
                break;
        }
    }
    if((rest != nullptr) && creature->tryPickup(seat) && creature->tryDrop(seat, rest))
        ACTS::moveCreature(env.ai, creature, rest);
}

//! \brief Advances war planning and assault actions; the shared event source polls symptoms.
void doTurn(Env& env)
{
    WarState& st = env.state;
    Seat* seat = env.player.getSeat();

    // The plan step: the first one at FirstPlanSeconds + U(0, jitter), then every ScanPeriod x LookFactorPlan on average
    if(st.nextPlan < 0.0)
        st.nextPlan = key("FirstPlanSeconds") + Random::Double(0.0, key("FirstPlanJitterSeconds"));
    if(env.now >= st.nextPlan)
    {
        AiMath::DelayParams p;
        p.rho = env.settings.rho;
        p.pi = env.settings.pi;
        p.scanPeriod = env.settings.scanPeriod;
        p.symptomScanFactor = key("LookFactorSymptom");
        p.periodicMinDelay = key("PeriodicMinDelay");
        p.latencyMean = key("LatencyMean");
        p.latencySd = key("LatencySd");
        AiMath::Uniform01 u = uniform01;
        st.nextPlan = env.now + AiMath::lookInterval(key("LookFactorPlan"), p, u);
        planDig(env);
        if(st.tunnel == WarState::tunnelOpen)
            planAttack(env);
    }

    // The game time of the last enemy cast the Mind saw, kept per enemy seat for the mana estimate
    for(Seat* other : env.gameMap.getSeats())
    {
        double age = env.mind.enemySpellAge(other->getId());
        if(age >= 0.0)
            st.sighting.seats[other->getId()].lastSpellTime = env.now - age;
    }

    // Tunnel and combat symptom polling is owned by the shared event source (AiEvents).
    if(st.assault != WarState::assaultNone)
        assaultStep(env);

}

void onEvent(Env& env, const AiEvent& event)
{
    WarState& st = env.state;
    switch(event.type)
    {
        case AiEventType::Fight:
            st.lastFight = event.time;
            st.fightOverRaised = false;
            defend(env, event);
            break;
        case AiEventType::HeartCritical:
            heartGuard(env);
            break;
        case AiEventType::FightOver:
            restAfterFight(env);
            break;
        case AiEventType::EnemyOut:
            planAttack(env);
            break;
        case AiEventType::EnemyTrapEmpty:
            secondWave(env);
            break;
        case AiEventType::AssaultOver:
            break;
        case AiEventType::EnemySpellSeen:
            st.sighting.seats[event.otherSeatId].lastSpellTime = event.time;
            break;
        default:
            break;
    }
}

namespace
{
//! \brief Appends a line with the given tag and tokens.
void addLine(std::vector<AiMath::AiStateLine>& lines, const std::string& tag, const std::vector<std::string>& tokens)
{
    AiMath::AiStateLine line;
    line.tag = tag;
    line.tokens = tokens;
    lines.push_back(line);
}

//! \brief A number as the text of a saved token.
std::string num(double value)
{
    std::ostringstream os;
    os << value;
    return os.str();
}

//! \brief The tile x coordinate token, -1 when there is no tile.
std::string tileX(Tile* tile)
{
    return num(tile == nullptr ? -1 : tile->getX());
}

//! \brief The tile y coordinate token, -1 when there is no tile.
std::string tileY(Tile* tile)
{
    return num(tile == nullptr ? -1 : tile->getY());
}

//! \brief The tile at saved coordinates, nullptr for -1.
Tile* tileAt(GameMap& gameMap, const std::string& x, const std::string& y)
{
    int xx = std::atoi(x.c_str());
    int yy = std::atoi(y.c_str());
    if((xx < 0) || (yy < 0))
        return nullptr;
    return gameMap.getTile(xx, yy);
}
}

void exportRows(const Env& env, std::vector<AiMath::AiStateLine>& lines)
{
    const WarState& st = env.state;
    const char* tunnelNames[3] = {"none", "digging", "open"};
    const char* assaultNames[4] = {"none", "moving", "running", "ending"};
    std::vector<std::string> t;
    t.push_back("tunnel");
    t.push_back(tunnelNames[st.tunnel]);
    t.push_back(num(st.detour));
    t.push_back(tileX(st.tunnelTarget));
    t.push_back(tileY(st.tunnelTarget));
    t.push_back(tileX(st.breakthrough));
    t.push_back(tileY(st.breakthrough));
    // The fortify of the tunnel is row F15 of another package: no fortify is pending here
    t.push_back("-1");
    addLine(lines, "war", t);

    std::vector<std::string> a;
    a.push_back("assault");
    a.push_back(assaultNames[st.assault]);
    a.push_back(st.tactic < 0 ? "-" : num(st.tactic));
    a.push_back(st.contactTime < 0.0 ? "-1" : num(env.now - st.contactTime));
    a.push_back(num(std::max(0.0, key("RestSecondsAfterAssault") - (env.now - st.lastAssaultEnd))));
    addLine(lines, "war", a);

    for(size_t i = 0; i < st.groups.size(); ++i)
    {
        const Group& g = st.groups[i];
        std::vector<std::string> gl;
        gl.push_back("group");
        gl.push_back(num(static_cast<double>(i)));
        gl.push_back(g.raid ? "raid" : "main");
        gl.push_back(num(static_cast<double>(g.targetIndex)));
        gl.push_back(tileX(g.bannerTile));
        gl.push_back(tileY(g.bannerTile));
        gl.push_back(g.bannerTile == nullptr ? "-1" : num(std::max(0.0, g.bannerUntil - env.now)));
        gl.push_back(tileX(g.dropTile));
        gl.push_back(tileY(g.dropTile));
        gl.push_back(num(static_cast<double>(g.members.size())));
        for(Creature* creature : g.members)
            gl.push_back(creature->getName());
        addLine(lines, "war", gl);
        for(size_t j = 0; j < g.targets.size(); ++j)
        {
            std::vector<std::string> tl;
            tl.push_back("target");
            tl.push_back(num(static_cast<double>(i)));
            tl.push_back(num(static_cast<double>(j)));
            tl.push_back(tileX(g.targets[j]));
            tl.push_back(tileY(g.targets[j]));
            addLine(lines, "war", tl);
        }
    }

    std::vector<std::string> d;
    d.push_back("defence");
    d.push_back(st.defenceRallying ? "rallying" : "none");
    d.push_back(tileX(st.defenceBanner));
    d.push_back(tileY(st.defenceBanner));
    addLine(lines, "war", d);

    for(const std::pair<const int, SeatSighting>& entry : st.sighting.seats)
    {
        const SeatSighting& s = entry.second;
        if(s.valid)
        {
            std::vector<std::string> sl;
            sl.push_back("seat");
            sl.push_back(num(entry.first));
            sl.push_back(num(env.now - s.time));
            sl.push_back(num(s.fHp));
            sl.push_back(num(s.fDps));
            sl.push_back(num(s.fGold));
            sl.push_back(num(s.fMana));
            sl.push_back(num(s.fTrap));
            sl.push_back(s.ready ? "1" : "0");
            addLine(lines, "sighting", sl);
            for(const std::pair<const std::string, EnemyRecord>& record : s.records)
            {
                std::vector<std::string> cl;
                cl.push_back("creature");
                cl.push_back(num(entry.first));
                cl.push_back(record.first);
                cl.push_back(num(record.second.hp));
                cl.push_back(num(record.second.rawDps));
                addLine(lines, "sighting", cl);
            }
        }
        if(s.lastSpellTime >= 0.0)
        {
            std::vector<std::string> pl;
            pl.push_back("spell");
            pl.push_back(num(entry.first));
            pl.push_back(num(env.now - s.lastSpellTime));
            addLine(lines, "sighting", pl);
        }
    }
}

void importRows(Env& env, const std::vector<AiMath::AiStateLine>& lines)
{
    WarState& st = env.state;
    std::vector<Creature*> own = env.gameMap.getCreaturesBySeat(env.player.getSeat());
    for(const AiMath::AiStateLine& line : lines)
    {
        const std::vector<std::string>& k = line.tokens;
        if(k.empty())
            continue;
        if((line.tag == "war") && (k[0] == "tunnel"))
        {
            st.tunnel = (k[1] == "open") ? WarState::tunnelOpen : ((k[1] == "digging") ? WarState::tunnelDigging : WarState::tunnelNone);
            st.detour = std::atof(k[2].c_str());
            st.tunnelTarget = tileAt(env.gameMap, k[3], k[4]);
            st.breakthrough = tileAt(env.gameMap, k[5], k[6]);
            st.tunnelKnown = (st.tunnel != WarState::tunnelNone);
        }
        else if((line.tag == "war") && (k[0] == "assault"))
        {
            st.assault = (k[1] == "moving") ? WarState::assaultMoving : ((k[1] == "running") ? WarState::assaultRunning :
                         ((k[1] == "ending") ? WarState::assaultEnding : WarState::assaultNone));
            st.tactic = (k[2] == "-") ? -1 : std::atoi(k[2].c_str());
            double age = std::atof(k[3].c_str());
            st.contactTime = (age < 0.0) ? -1.0 : env.now - age;
            st.lastAssaultEnd = env.now + std::atof(k[4].c_str()) - key("RestSecondsAfterAssault");
        }
        else if((line.tag == "war") && (k[0] == "group"))
        {
            Group g;
            g.raid = (k[2] == "raid");
            g.targetIndex = static_cast<size_t>(std::atoi(k[3].c_str()));
            g.bannerTile = tileAt(env.gameMap, k[4], k[5]);
            g.bannerUntil = (g.bannerTile == nullptr) ? -1.0 : env.now + std::atof(k[6].c_str());
            g.dropTile = tileAt(env.gameMap, k[7], k[8]);
            for(size_t i = 10; i < k.size(); ++i)
            {
                for(Creature* creature : own)
                {
                    if(creature->getName() == k[i])
                        g.members.push_back(creature);
                }
            }
            size_t index = static_cast<size_t>(std::atoi(k[1].c_str()));
            if(st.groups.size() <= index)
                st.groups.resize(index + 1);
            st.groups[index] = g;
        }
        else if((line.tag == "war") && (k[0] == "target"))
        {
            size_t index = static_cast<size_t>(std::atoi(k[1].c_str()));
            if(index < st.groups.size())
            {
                Tile* tile = tileAt(env.gameMap, k[3], k[4]);
                if(tile != nullptr)
                    st.groups[index].targets.push_back(tile);
            }
        }
        else if((line.tag == "war") && (k[0] == "defence"))
        {
            st.defenceRallying = (k[1] == "rallying");
            st.defenceBanner = tileAt(env.gameMap, k[2], k[3]);
        }
        else if((line.tag == "sighting") && (k[0] == "seat"))
        {
            SeatSighting& s = st.sighting.seats[std::atoi(k[1].c_str())];
            s.time = env.now - std::atof(k[2].c_str());
            s.fHp = std::atof(k[3].c_str());
            s.fDps = std::atof(k[4].c_str());
            s.fGold = std::atof(k[5].c_str());
            s.fMana = std::atof(k[6].c_str());
            s.fTrap = std::atof(k[7].c_str());
            s.ready = (k[8] == "1");
            s.valid = true;
        }
        else if((line.tag == "sighting") && (k[0] == "creature"))
        {
            EnemyRecord record;
            record.hp = std::atof(k[3].c_str());
            record.rawDps = std::atof(k[4].c_str());
            record.tile = nullptr;
            st.sighting.seats[std::atoi(k[1].c_str())].records[k[2]] = record;
        }
        else if((line.tag == "sighting") && (k[0] == "spell"))
        {
            st.sighting.seats[std::atoi(k[1].c_str())].lastSpellTime = env.now - std::atof(k[2].c_str());
        }
    }
}
}
