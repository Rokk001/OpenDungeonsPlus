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

#include "ai/AiSpells.h"

#include "ai/AiActions.h"
#include "ai/AiMind.h"
#include "ai/AiSettings.h"
#include "ai/KeeperAI.h"

#include "creatureaction/CreatureAction.h"
#include "creaturemood/CreatureMood.h"
#include "creatureskill/CreatureSkill.h"
#include "entities/Building.h"
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
#include "spells/SpellSummonChampion.h"
#include "spells/SpellType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <sstream>
#include <string>

namespace
{
//! \brief One spell the casting loop can choose from.
struct SpellOption
{
    SpellType mType;
    double mPrice;
    //! \brief Damage per mana of the spell (0 for Heal).
    double mEfficiency;
};

//! \brief Returns the key of the price of a spell in the spell configuration.
const char* priceKey(SpellType type)
{
    switch(type)
    {
        case SpellType::callToWar: return "CallToWarPrice";
        case SpellType::creatureHeal: return "CreatureHealPrice";
        case SpellType::creatureExplosion: return "CreatureExplosionPrice";
        case SpellType::creatureHaste: return "CreatureHastePrice";
        case SpellType::creatureDefense: return "CreatureDefensePrice";
        case SpellType::creatureSlow: return "CreatureSlowPrice";
        case SpellType::creatureStrength: return "CreatureStrengthPrice";
        case SpellType::creatureWeak: return "CreatureWeakPrice";
        case SpellType::eyeEvil: return "EyeEvilPrice";
        case SpellType::lightning: return "LightningPrice";
        case SpellType::tremor: return "TremorPrice";
        case SpellType::defector: return "DefectorPrice";
        case SpellType::hexenHen: return "HexenHenPrice";
        case SpellType::inferno: return "InfernoPrice";
        case SpellType::summonChampion: return "SummonChampionPrice";
        default: return "";
    }
}

//! \brief Returns the mana price of a spell.
double spellPrice(SpellType type)
{
    return ConfigManager::getSingleton().getSpellConfigDouble(priceKey(type));
}

//! \brief Returns a value of the [KeeperAI] section of ai.cfg.
double aiKey(const std::string& key)
{
    return ConfigManager::getSingleton().getAiConfigDouble(key);
}

//! \brief Tells whether the AI can cast the spell now: researched, off cooldown and mana for the price plus a share
//! of the maximum mana.
//! \param reserveKey The key of the share of MaxManaPerSeat that stays free.
bool canCast(KeeperAI& ai, SpellType type, const std::string& reserveKey)
{
    Player& player = ai.getControlledPlayer();
    Seat* seat = player.getSeat();
    if(!SkillManager::isSpellAvailable(type, seat))
        return false;

    if(player.getSpellCooldownTurns(type) > 0)
        return false;

    double reserve = aiKey(reserveKey) * ConfigManager::getSingleton().getMaxManaPerSeat();
    return seat->getMana() >= (spellPrice(type) + reserve);
}

//! \brief Returns the HP share of a creature.
double hpShare(const Creature* creature)
{
    return creature->getHP() / std::max(1.0, creature->getMaxHp());
}

//! \brief Returns the strength of a creature: HP times raw damage per second.
double strength(const Creature* creature)
{
    return creature->getHP() * creature->getRawDamagePerSecond();
}

//! \brief Tells whether the creature stands on ground claimed for the seat.
bool onOwnGround(const Creature* creature, const Seat* seat)
{
    Tile* tile = creature->getPositionTile();
    return (tile != nullptr) && tile->isClaimedForSeat(seat);
}

//! \brief Returns the enemy fighters the AI sees now (the tile of the creature is in the vision of the AI's seat).
std::vector<Creature*> visibleEnemies(KeeperAI& ai)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    std::vector<Creature*> enemies;
    for(Creature* creature : ai.getGameMap().getCreatures())
    {
        if(!creature->isAlive() || creature->getDefinition()->isWorker())
            continue;

        Seat* creatureSeat = creature->getSeat();
        if((creatureSeat == nullptr) || (creatureSeat == seat) || seat->isAlliedSeat(creatureSeat))
            continue;

        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;

        const std::vector<Seat*>& seeing = tile->getSeatsWithVision();
        if(std::find(seeing.begin(), seeing.end(), seat) == seeing.end())
            continue;

        enemies.push_back(creature);
    }
    return enemies;
}

//! \brief Tells whether the creature takes part in a fight now (fighting, or fleeing from one).
bool inFight(const Creature* creature)
{
    return creature->isActionInList(CreatureActionType::fight) || creature->isActionInList(CreatureActionType::flee);
}

//! \brief Returns the enemy fighters in sight that take part in a fight: the enemies of the current fight.
std::vector<Creature*> fightEnemies(KeeperAI& ai)
{
    std::vector<Creature*> enemies;
    for(Creature* creature : visibleEnemies(ai))
    {
        if(inFight(creature))
            enemies.push_back(creature);
    }
    return enemies;
}

//! \brief Tells whether the first attack line of the creature's kind is a melee attack.
bool isMelee(const Creature* creature)
{
    const CreatureDefinition* definition = creature->getDefinition();
    for(const CreatureSkill* skill : definition->getCreatureSkills())
    {
        if(definition->isFirstAttackSkill(skill))
            return skill->getSkillName() == "Melee";
    }
    return false;
}

//! \brief Returns the own fighters that are alive and on the map.
std::vector<Creature*> ownFighters(KeeperAI& ai)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    std::vector<Creature*> fighters;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(seat))
    {
        if(!creature->isAlive() || creature->isKo() || creature->getDefinition()->isWorker() ||
           (creature->getPositionTile() == nullptr))
        {
            continue;
        }
        fighters.push_back(creature);
    }
    return fighters;
}

//! \brief Returns the own fighters that take part in a fight now: the own group of the current fight.
std::vector<Creature*> fightingOwn(KeeperAI& ai)
{
    std::vector<Creature*> fighters;
    for(Creature* creature : ownFighters(ai))
    {
        if(inFight(creature))
            fighters.push_back(creature);
    }
    return fighters;
}

//! \brief Returns the own fighters that stand on the tile (the drop tile of a launched group).
std::vector<Creature*> ownFightersOn(KeeperAI& ai, const Tile* tile)
{
    std::vector<Creature*> fighters;
    if(tile == nullptr)
        return fighters;

    for(Creature* creature : ownFighters(ai))
    {
        if(creature->getPositionTile() == tile)
            fighters.push_back(creature);
    }
    return fighters;
}

//! \brief Returns the creature of the list with the lowest HP share.
Creature* weakest(const std::vector<Creature*>& list)
{
    Creature* best = nullptr;
    for(Creature* creature : list)
    {
        if((best == nullptr) || (hpShare(creature) < hpShare(best)))
            best = creature;
    }
    return best;
}

//! \brief Returns the creature of the list with the highest strength.
Creature* strongest(const std::vector<Creature*>& list)
{
    Creature* best = nullptr;
    for(Creature* creature : list)
    {
        if((best == nullptr) || (strength(creature) > strength(best)))
            best = creature;
    }
    return best;
}

//! \brief Returns a random creature of the list, or nullptr for an empty list.
Creature* anyOf(const std::vector<Creature*>& list)
{
    if(list.empty())
        return nullptr;

    return list[Random::Int(0, static_cast<int>(list.size()) - 1)];
}

//! \brief Picks the target of a spell: the lowest-HP creature with the focus fire of the level, otherwise a random one.
Creature* focusTarget(KeeperAI& ai, const std::vector<Creature*>& list)
{
    if(Random::Double(0.0, 1.0) < ai.getSettings().focusFire)
    {
        // The lowest absolute HP, as the target a player would finish first
        Creature* best = nullptr;
        for(Creature* creature : list)
        {
            if((best == nullptr) || (creature->getHP() < best->getHP()))
                best = creature;
        }
        return best;
    }
    return anyOf(list);
}

//! \brief Returns how many of the creatures stand within the radius of the Tremor spell around the creature.
int creaturesAround(const std::vector<Creature*>& list, const Creature* center)
{
    int radius = static_cast<int>(ConfigManager::getSingleton().getSpellConfigUInt32("TremorRadiusTiles"));
    Tile* centerTile = center->getPositionTile();
    int count = 0;
    for(Creature* creature : list)
    {
        Tile* tile = creature->getPositionTile();
        int dx = tile->getX() - centerTile->getX();
        int dy = tile->getY() - centerTile->getY();
        if((dx * dx + dy * dy) <= (radius * radius))
            ++count;
    }
    return count;
}

//! \brief Returns the seconds the hand is busy with a spell cast.
double spellActionSeconds()
{
    const ConfigManager::AiAction* action = ConfigManager::getSingleton().getAiAction("spell");
    return (action == nullptr) ? 0.0 : action->mSeconds;
}

//! \brief Returns the creatures of the list that stand on ground claimed for the AI's seat.
std::vector<Creature*> onOwnGroundOnly(KeeperAI& ai, const std::vector<Creature*>& list)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    std::vector<Creature*> result;
    for(Creature* creature : list)
    {
        if(onOwnGround(creature, seat))
            result.push_back(creature);
    }
    return result;
}

//! \brief Returns the fighting enemies in sight that stand on ground claimed for the AI's seat.
std::vector<Creature*> enemiesOnOwnGround(KeeperAI& ai)
{
    return onOwnGroundOnly(ai, fightEnemies(ai));
}

//! \brief Casts a spell on the tile of the creature.
void castOnTileOf(KeeperAI& ai, SpellType type, Creature* creature)
{
    ACTS::castSpell(ai, type, creature->getPositionTile());
}

//! \brief Tells whether the tile is covered by the heart room of the seat.
bool isHeartTile(const Tile* tile, const Seat* seat)
{
    if(tile == nullptr)
        return false;

    Room* room = tile->getCoveringRoom();
    return (room != nullptr) && (room->getType() == RoomType::dungeonTemple) && (room->getSeat() == seat);
}

//! \brief Returns a claimed, not full tile of the own land next to the own heart, or nullptr.
Tile* tileNextToHeart(KeeperAI& ai)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::dungeonTemple, seat))
    {
        for(Tile* heartTile : room->getCoveredTiles())
        {
            for(Tile* neighbor : heartTile->getAllNeighbors())
            {
                if(!neighbor->isFullTile() && neighbor->isClaimedForSeat(seat) && (neighbor->getCoveringBuilding() == nullptr))
                    return neighbor;
            }
        }
    }
    return nullptr;
}

//! \brief Writes a number with full double precision for a draw line.
std::string numberToken(double value)
{
    std::ostringstream os;
    os.precision(17);
    os << value;
    return os.str();
}

//! \brief Splits a comma separated draw value into its parts.
std::vector<std::string> splitValue(const std::string& value)
{
    std::vector<std::string> parts;
    std::string::size_type start = 0;
    while(true)
    {
        std::string::size_type comma = value.find(',', start);
        parts.push_back(value.substr(start, (comma == std::string::npos) ? std::string::npos : comma - start));
        if(comma == std::string::npos)
            return parts;
        start = comma + 1;
    }
}

//! \brief Reads the spell draws of a loaded game from the mind once: the turn of the last Eye of Evil cast (E04), the
//! pending late Defense (E05) and a running fight session (E19). The mind imports its state at its first turn, at mind
//! time 0, so a saved time relative to the save is the mind time itself.
void restoreDraws(KeeperAI& ai)
{
    SPELL::State& state = ai.getSpellState();
    if(state.mRestored)
        return;

    state.mRestored = true;
    for(const AiMath::AiStateLine& line : ai.getMind().savedRows())
    {
        if((line.tag != "draw") || (line.tokens.size() != 3))
            continue;

        if((line.tokens[0] == "E04") && (line.tokens[1] == "eyeTurn"))
            state.mLastEyeTurn = std::atoll(line.tokens[2].c_str());
        else if((line.tokens[0] == "E05") && (line.tokens[1] == "lateDefense"))
            state.mLateDefense = (line.tokens[2] == "1");
        else if((line.tokens[0] == "E19") && (line.tokens[1] == "session"))
        {
            // start,lastFight,x,y,nextCast,haste
            std::vector<std::string> parts = splitValue(line.tokens[2]);
            if(parts.size() != 6)
                continue;

            state.mInSession = true;
            state.mSessionStart = std::atof(parts[0].c_str());
            state.mLastFight = std::atof(parts[1].c_str());
            state.mFightX = std::atoi(parts[2].c_str());
            state.mFightY = std::atoi(parts[3].c_str());
            state.mNextCast = std::atof(parts[4].c_str());
            state.mSessionHaste = (parts[5] == "1");
        }
    }
}

//! \brief Replaces the spell draw lines of the saved AI state with the current ones.
void saveDraws(KeeperAI& ai, std::vector<AiMath::AiStateLine>& lines)
{
    restoreDraws(ai);
    std::vector<AiMath::AiStateLine> kept;
    for(const AiMath::AiStateLine& line : lines)
    {
        bool own = (line.tag == "draw") && !line.tokens.empty() &&
                   ((line.tokens[0] == "E04") || (line.tokens[0] == "E05") || (line.tokens[0] == "E19"));
        if(!own)
            kept.push_back(line);
    }
    lines.swap(kept);

    const SPELL::State& state = ai.getSpellState();
    if(state.mLastEyeTurn >= 0)
    {
        AiMath::AiStateLine line;
        line.tag = "draw";
        line.tokens.push_back("E04");
        line.tokens.push_back("eyeTurn");
        line.tokens.push_back(std::to_string(state.mLastEyeTurn));
        lines.push_back(line);
    }
    if(state.mLateDefense)
    {
        AiMath::AiStateLine line;
        line.tag = "draw";
        line.tokens.push_back("E05");
        line.tokens.push_back("lateDefense");
        line.tokens.push_back("1");
        lines.push_back(line);
    }
    if(state.mInSession)
    {
        // The times relative to the save
        double now = ai.getMind().now();
        AiMath::AiStateLine line;
        line.tag = "draw";
        line.tokens.push_back("E19");
        line.tokens.push_back("session");
        line.tokens.push_back(numberToken(state.mSessionStart - now) + "," + numberToken(state.mLastFight - now) + "," +
                              std::to_string(state.mFightX) + "," + std::to_string(state.mFightY) + "," +
                              numberToken(state.mNextCast - now) + "," + (state.mSessionHaste ? "1" : "0"));
        lines.push_back(line);
    }
}

//! \brief The casting loop of the fight session: a cast as soon as the previous one allows it, and the end of the
//! session once no Fight event came for FightOverSeconds. Run by the mind every AiPollSeconds; it never raises an event,
//! so the loop needs no hand time of its own.
//! \return Always false.
bool sessionStep(KeeperAI& ai)
{
    restoreDraws(ai);
    SPELL::State& state = ai.getSpellState();
    if(!state.mInSession)
        return false;

    double now = ai.getMind().now();
    if((now - state.mLastFight) >= aiKey("FightOverSeconds"))
    {
        state.mInSession = false;
        return false;
    }

    // On ground not claimed for the AI (an assault) only Inferno and Tremor reach the enemy
    Tile* tile = ai.getGameMap().getTile(state.mFightX, state.mFightY);
    bool enemyGround = (tile != nullptr) && !tile->isClaimedForSeat(ai.getControlledPlayer().getSeat());
    SPELL::chooseSpell(ai, enemyGround, now, state.mNextCast);
    return false;
}

//! \brief The reaction to a Fight event after its alert delay: starts or extends the fight session and makes the
//! decisions of the single-target and support spells of this fight.
void onFight(KeeperAI& ai, const AiEvent& event)
{
    restoreDraws(ai);
    SPELL::State& state = ai.getSpellState();
    Seat* seat = ai.getControlledPlayer().getSeat();
    double now = ai.getMind().now();
    bool first = !state.mInSession;
    if(first)
    {
        state.mInSession = true;
        state.mSessionStart = now;
        state.mNextCast = now;
        state.mSessionHaste = false;
    }
    state.mLastFight = now;
    if(event.tile != nullptr)
    {
        state.mFightX = event.tile->getX();
        state.mFightY = event.tile->getY();
    }

    // Defense on the group that holds the entrance, at the first Fight of the session
    if(first)
        SPELL::castDefense(ai, onOwnGroundOnly(ai, fightingOwn(ai)), false);

    // Haste once the fight lasts longer than HasteFightSeconds
    if(!state.mSessionHaste && ((now - state.mSessionStart) > aiKey("HasteFightSeconds")))
    {
        state.mSessionHaste = true;
        SPELL::castHaste(ai, fightingOwn(ai), false, now - state.mSessionStart);
    }

    SPELL::castSlow(ai);
    SPELL::castWeak(ai);
    SPELL::castDefector(ai);
    SPELL::castHexenHen(ai, event.tile);

    // A fight on a heart tile is an attack on the heart
    bool heart = isHeartTile(event.tile, seat);
    SPELL::castChampion(ai, tileNextToHeart(ai), heart);

    // The first cast of the session follows this same alert delay
    sessionStep(ai);
}

//! \brief The late Defense cast of the E05 mistake when the fight is over.
void onFightOver(KeeperAI& ai, const AiEvent& event)
{
    restoreDraws(ai);
    SPELL::castDefense(ai, onOwnGroundOnly(ai, ownFighters(ai)), true);
}

//! \brief Haste on the main group when it starts the march; the March event carries the drop tile of the main group.
void onMarch(KeeperAI& ai, const AiEvent& event)
{
    SPELL::castHaste(ai, ownFightersOn(ai, event.tile), true, 0.0);
}

//! \brief Strength on the main group while it stands on its drop tile, and the champion of an assault. The Launch event
//! carries the drop tile of the main group and the tactic index as amount (raid 3 gets no champion).
void onLaunch(KeeperAI& ai, const AiEvent& event)
{
    SPELL::castStrength(ai, ownFightersOn(ai, event.tile));
    if(static_cast<int>(event.amount) != 3)
        SPELL::castChampion(ai, event.tile, true);
}

//! \brief The champion when the heart is critical.
void onHeartCritical(KeeperAI& ai, const AiEvent& event)
{
    SPELL::castChampion(ai, tileNextToHeart(ai), true);
}
}

SPELL::State::State() :
    mLastEyeTurn(-1),
    mLateDefense(false),
    mInSession(false),
    mSessionStart(0.0),
    mLastFight(0.0),
    mFightX(-1),
    mFightY(-1),
    mNextCast(0.0),
    mSessionHaste(false),
    mRestored(false)
{
}

void SPELL::bindRows(KeeperAI& ai)
{
    Mind& mind = ai.getMind();
    KeeperAI* self = &ai;
    std::function<void(const AiEvent&)> fight = [self](const AiEvent& event) { onFight(*self, event); };
    std::function<void(const AiEvent&)> fightOver = [self](const AiEvent& event) { onFightOver(*self, event); };
    std::function<void(const AiEvent&)> march = [self](const AiEvent& event) { onMarch(*self, event); };
    std::function<void(const AiEvent&)> launch = [self](const AiEvent& event) { onLaunch(*self, event); };
    std::function<void(const AiEvent&)> heart = [self](const AiEvent& event) { onHeartCritical(*self, event); };
    std::function<bool()> session = [self]() { return sessionStep(*self); };
    std::function<void(std::vector<AiMath::AiStateLine>&)> save = [self](std::vector<AiMath::AiStateLine>& lines) { saveDraws(*self, lines); };

    mind.onEvent("E19", std::vector<AiEventType>(1, AiEventType::Fight), fight);
    mind.onEvent("E05", std::vector<AiEventType>(1, AiEventType::FightOver), fightOver);
    mind.onEvent("E03", std::vector<AiEventType>(1, AiEventType::March), march);
    mind.onEvent("E06", std::vector<AiEventType>(1, AiEventType::Launch), launch);
    mind.onEvent("E20", std::vector<AiEventType>(1, AiEventType::HeartCritical), heart);
    mind.onPoll("E19", AiEventType::Fight, session);
    mind.onSave(save);
}

bool SPELL::chooseSpell(KeeperAI& ai, bool enemyGround, double now, double& nextCast)
{
    // AI row E02
    // AI row E09
    // AI row E11
    // AI row E15
    // AI row E16
    // AI row E19
    // AI row J04
    // AI row K06
    if(now < nextCast)
        return false;

    Seat* seat = ai.getControlledPlayer().getSeat();
    ConfigManager& config = ConfigManager::getSingleton();

    // The spells the AI may use here: on ground not claimed for the caster only Inferno and Tremor reach the enemy
    std::vector<SpellOption> damage;
    std::vector<SpellType> candidates;
    if(!enemyGround)
    {
        candidates.push_back(SpellType::lightning);
        candidates.push_back(SpellType::creatureExplosion);
    }
    candidates.push_back(SpellType::inferno);
    candidates.push_back(SpellType::tremor);
    for(SpellType type : candidates)
    {
        const std::string reserveKey = (type == SpellType::lightning) ? "LightningManaReserve" : "SpellManaReserve";
        if(!canCast(ai, type, reserveKey))
            continue;

        double amount = 0.0;
        double targets = 1.0;
        switch(type)
        {
            case SpellType::lightning:
                amount = (config.getSpellConfigDouble("LightningDamageMin") + config.getSpellConfigDouble("LightningDamage")) / 2.0;
                targets = aiKey("SpellTargetsLightning");
                break;
            case SpellType::creatureExplosion:
                amount = config.getSpellConfigDouble("CreatureExplosionValue") * config.getSpellConfigDouble("CreatureExplosionDuration");
                break;
            case SpellType::inferno:
                amount = (config.getSpellConfigDouble("InfernoDamagePerTurnMin") + config.getSpellConfigDouble("InfernoDamagePerTurn")) / 2.0
                         * config.getSpellConfigDouble("InfernoNbTurns");
                targets = aiKey("SpellTargetsInferno");
                break;
            default:
                amount = (config.getSpellConfigDouble("TremorDamageMin") + config.getSpellConfigDouble("TremorDamage")) / 2.0;
                targets = aiKey("SpellTargetsTremor");
                break;
        }
        SpellOption option;
        option.mType = type;
        option.mPrice = spellPrice(type);
        option.mEfficiency = amount * targets / std::max(1.0, option.mPrice);
        damage.push_back(option);
    }

    // The heal reaches only own creatures of the fight on claimed ground, so an assault on enemy land has none
    std::vector<Creature*> hurt;
    if(!enemyGround && canCast(ai, SpellType::creatureHeal, "SpellManaReserve"))
    {
        for(Creature* creature : fightingOwn(ai))
        {
            // Never a creature above HealNeverAbove: the heal would be wasted
            if((hpShare(creature) < aiKey("HealBelow")) && (hpShare(creature) <= aiKey("HealNeverAbove")) &&
               onOwnGround(creature, seat))
                hurt.push_back(creature);
        }
    }

    // Only the enemies of the fight count; without an enemy in sight nothing is cast, also no heal
    std::vector<Creature*> allEnemies = fightEnemies(ai);
    std::vector<Creature*> enemies = enemyGround ? allEnemies : onOwnGroundOnly(ai, allEnemies);
    if((damage.empty() && hurt.empty()) || allEnemies.empty())
    {
        nextCast = now + aiKey("CastRecheckSeconds");
        return false;
    }

    // The choice: a mistake picks a random spell and wastes it, otherwise heal or the best damage per mana
    bool slipped = ai.getMind().slip("E19");
    SpellType chosen = SpellType::nullSpellType;
    if(slipped)
    {
        std::vector<SpellType> all;
        for(const SpellOption& option : damage)
            all.push_back(option.mType);
        if(!hurt.empty())
            all.push_back(SpellType::creatureHeal);
        chosen = all[Random::Int(0, static_cast<int>(all.size()) - 1)];
    }
    else
    {
        const SpellOption* best = nullptr;
        for(const SpellOption& option : damage)
        {
            // Tremor only against intruders standing together
            if(option.mType == SpellType::tremor)
            {
                bool together = false;
                for(Creature* creature : allEnemies)
                    together = together || (creaturesAround(allEnemies, creature) >= static_cast<int>(aiKey("TremorMinTargets")));
                if(!together)
                    continue;
            }
            // Lightning and Explosion need a target on claimed ground
            if((option.mType != SpellType::inferno) && (option.mType != SpellType::tremor) && enemies.empty())
                continue;

            if((best == nullptr) || (option.mEfficiency > best->mEfficiency))
                best = &option;
        }
        if(!hurt.empty() && ((best == nullptr) || (Random::Double(0.0, 1.0) < aiKey("HealCastChance"))))
            chosen = SpellType::creatureHeal;
        else if(best != nullptr)
            chosen = best->mType;
    }

    if(chosen == SpellType::nullSpellType)
    {
        nextCast = now + aiKey("CastRecheckSeconds");
        return false;
    }

    // The target: a wasted cast goes to an own creature, which no attack spell of the AI harms
    if(chosen == SpellType::creatureHeal)
    {
        Creature* target = slipped ? anyOf(ownFighters(ai)) : weakest(hurt);
        if(target == nullptr)
        {
            nextCast = now + aiKey("CastRecheckSeconds");
            return false;
        }
        ACTS::castSpell(ai, chosen, target);
    }
    else
    {
        std::vector<Creature*>& pool = (chosen == SpellType::inferno || chosen == SpellType::tremor) ? allEnemies : enemies;
        Creature* target = nullptr;
        if(slipped)
        {
            target = anyOf(ownFighters(ai));
        }
        else if(chosen == SpellType::inferno)
        {
            // Inferno burns an area: the strongest intruder
            target = strongest(pool);
        }
        else if(chosen == SpellType::tremor)
        {
            // Tremor shakes an area: the intruder with the most others around
            for(Creature* creature : pool)
            {
                if((target == nullptr) || (creaturesAround(pool, creature) > creaturesAround(pool, target)))
                    target = creature;
            }
        }
        else
        {
            target = focusTarget(ai, pool);
        }
        if(target == nullptr)
        {
            nextCast = now + aiKey("CastRecheckSeconds");
            return false;
        }

        if(chosen == SpellType::creatureExplosion)
            ACTS::castSpell(ai, chosen, target);
        else
            castOnTileOf(ai, chosen, target);
    }

    nextCast = now + std::max(spellActionSeconds(), aiKey("MinRecastSeconds"));
    return true;
}

bool SPELL::castHaste(KeeperAI& ai, const std::vector<Creature*>& group, bool march, double fightSeconds)
{
    // AI row E03
    if(!march && (fightSeconds <= aiKey("HasteFightSeconds")))
        return false;

    if(!canCast(ai, SpellType::creatureHaste, "SpellManaReserve"))
        return false;

    Seat* seat = ai.getControlledPlayer().getSeat();
    // The target must stand on ground claimed for the caster; the mistake casts it on idle creatures at home
    std::vector<Creature*> targets;
    bool slipped = ai.getMind().slip("E03");
    const std::vector<Creature*> source = slipped ? ownFighters(ai) : group;
    for(Creature* creature : source)
    {
        if(!onOwnGround(creature, seat))
            continue;

        if(slipped && creature->isActionInList(CreatureActionType::fight))
            continue;

        targets.push_back(creature);
    }
    Creature* target = slipped ? anyOf(targets) : strongest(targets);
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::creatureHaste, target);
    return true;
}

bool SPELL::castEye(KeeperAI& ai, Tile* tile)
{
    // AI row E04
    if((tile == nullptr) || !canCast(ai, SpellType::eyeEvil, "SpellManaReserve"))
        return false;

    restoreDraws(ai);
    State& state = ai.getSpellState();
    int64_t turn = ai.getGameMap().getTurnNumber();
    double minTurns = aiKey("EyeCastIntervalMinutes") * 60.0 * ODApplication::turnsPerSecond;
    if((state.mLastEyeTurn >= 0) && (static_cast<double>(turn - state.mLastEyeTurn) < minTurns))
        return false;

    // The mistake: the AI never casts it and attacks blind
    if(ai.getMind().slip("E04"))
        return false;

    state.mLastEyeTurn = turn;
    ACTS::castSpell(ai, SpellType::eyeEvil, tile);
    return true;
}

bool SPELL::castDefense(KeeperAI& ai, const std::vector<Creature*>& holders, bool fightOver)
{
    // AI row E05
    restoreDraws(ai);
    State& state = ai.getSpellState();
    Seat* seat = ai.getControlledPlayer().getSeat();
    if(fightOver)
    {
        // The late cast of the mistake: after the fight
        if(!state.mLateDefense)
            return false;

        state.mLateDefense = false;
    }
    else if(ai.getMind().slip("E05"))
    {
        state.mLateDefense = true;
        return false;
    }

    if(!canCast(ai, SpellType::creatureDefense, "SpellManaReserve"))
        return false;

    std::vector<Creature*> targets;
    for(Creature* creature : holders)
    {
        if(onOwnGround(creature, seat))
            targets.push_back(creature);
    }
    Creature* target = strongest(targets);
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::creatureDefense, target);
    return true;
}

bool SPELL::castStrength(KeeperAI& ai, const std::vector<Creature*>& group)
{
    // AI row E06
    if(!canCast(ai, SpellType::creatureStrength, "SpellManaReserve"))
        return false;

    Seat* seat = ai.getControlledPlayer().getSeat();
    // The mistake: Strength on a creature that is leaving
    bool slipped = ai.getMind().slip("E06");
    std::vector<Creature*> targets;
    for(Creature* creature : (slipped ? ownFighters(ai) : group))
    {
        if(!onOwnGround(creature, seat))
            continue;

        if(slipped != creature->isActionInList(CreatureActionType::flee))
            continue;

        targets.push_back(creature);
    }
    Creature* target = slipped ? anyOf(targets) : strongest(targets);
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::creatureStrength, target);
    return true;
}

bool SPELL::castCallToWar(KeeperAI& ai, Tile* tile, int creaturesToGather, bool assault)
{
    // AI row E07
    if((tile == nullptr) || !canCast(ai, SpellType::callToWar, "SpellManaReserve"))
        return false;

    // The defence rally: only for more than CallToWarMinCreatures creatures; the complex mistake rallies them by hand
    // instead of the banner. The banners of an assault are always cast (drawLaunchGathering is the launch's draw)
    if(!assault)
    {
        if(creaturesToGather <= static_cast<int>(aiKey("CallToWarMinCreatures")))
            return false;

        if(ai.getMind().slip("E07"))
            return false;
    }

    ACTS::castSpell(ai, SpellType::callToWar, tile);
    return true;
}

bool SPELL::drawLaunchGathering(KeeperAI& ai)
{
    // The mistake of the launch: the groups are not carried to the tunnel end and walk from home to their banners
    return ai.getMind().slip("E07");
}

bool SPELL::castSlow(KeeperAI& ai)
{
    // AI row E08
    if(!canCast(ai, SpellType::creatureSlow, "SpellManaReserve"))
        return false;

    std::vector<Creature*> enemies = enemiesOnOwnGround(ai);
    std::vector<Creature*> melee;
    for(Creature* creature : enemies)
    {
        if(isMelee(creature))
            melee.push_back(creature);
    }
    // The mistake: the weakest enemy instead of the strongest melee enemy
    Creature* target = ai.getMind().slip("E08") ? weakest(enemies) : strongest(melee);
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::creatureSlow, target);
    return true;
}

bool SPELL::castWeak(KeeperAI& ai)
{
    // AI row E10
    if(!canCast(ai, SpellType::creatureWeak, "SpellManaReserve"))
        return false;

    std::vector<Creature*> enemies = enemiesOnOwnGround(ai);
    Creature* target = nullptr;
    if(ai.getMind().slip("E10"))
    {
        // The mistake: a nearly dead enemy
        target = weakest(enemies);
    }
    else
    {
        for(Creature* creature : enemies)
        {
            if((target == nullptr) || (creature->getRawDamagePerSecond() > target->getRawDamagePerSecond()))
                target = creature;
        }
    }
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::creatureWeak, target);
    return true;
}

bool SPELL::castDefector(KeeperAI& ai)
{
    // AI row E17
    if(!canCast(ai, SpellType::defector, "SpellManaReserve"))
        return false;

    // The AI needs room for the new fighter
    Seat* seat = ai.getControlledPlayer().getSeat();
    if(seat->getNumCreaturesFighters() >= seat->getNumCreaturesFightersMax())
        return false;

    // The best rule takes the strongest enemy whose mood is low (Upset or worse; the creature window shows the mood of
    // any creature); the mistake takes a strong one at full health, which resists
    bool slipped = ai.getMind().slip("E17");
    std::vector<Creature*> candidates;
    for(Creature* creature : enemiesOnOwnGround(ai))
    {
        CreatureMoodLevel mood = creature->getMoodValue();
        bool lowMood = (mood != CreatureMoodLevel::Unknown) && (static_cast<int>(mood) >= static_cast<int>(CreatureMoodLevel::Upset));
        if(slipped ? (hpShare(creature) >= 1.0) : lowMood)
            candidates.push_back(creature);
    }
    Creature* target = strongest(candidates);
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::defector, target);
    return true;
}

bool SPELL::castHexenHen(KeeperAI& ai, Tile* fightTile)
{
    // AI row E18
    if(!canCast(ai, SpellType::hexenHen, "SpellManaReserve"))
        return false;

    Seat* seat = ai.getControlledPlayer().getSeat();
    // An attack on a room or the heart: the Fight event came from a tile of an own room, and the attacker fights on or
    // next to that tile
    Room* room = (fightTile == nullptr) ? nullptr : fightTile->getCoveringRoom();
    bool roomAttacked = (room != nullptr) && (room->getSeat() == seat);
    bool slipped = ai.getMind().slip("E18");
    std::vector<Creature*> candidates;
    for(Creature* creature : fightEnemies(ai))
    {
        Tile* tile = creature->getPositionTile();
        bool atRoom = false;
        if(roomAttacked)
        {
            int dx = std::abs(tile->getX() - fightTile->getX());
            int dy = std::abs(tile->getY() - fightTile->getY());
            atRoom = (dx <= 1) && (dy <= 1);
        }
        Room* standing = tile->getCoveringRoom();
        bool attacksBuilding = atRoom || ((standing != nullptr) && (standing->getSeat() == seat));
        // The mistake: a random enemy that attacks no building
        if(slipped ? !attacksBuilding : atRoom)
            candidates.push_back(creature);
    }
    Creature* target = anyOf(candidates);
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::hexenHen, target);
    return true;
}

bool SPELL::castChampion(KeeperAI& ai, Tile* tile, bool heartOrLaunch)
{
    // AI row E20
    if((tile == nullptr) || !SkillManager::isSpellAvailable(SpellType::summonChampion, ai.getControlledPlayer().getSeat()))
        return false;

    Player& player = ai.getControlledPlayer();
    if((player.getSpellCooldownTurns(SpellType::summonChampion) > 0) ||
       SpellSummonChampion::hasChampion(&ai.getGameMap(), player.getSeat()))
    {
        return false;
    }

    // The mana for the price and the first seconds of the upkeep after the free period
    ConfigManager& config = ConfigManager::getSingleton();
    double needed = spellPrice(SpellType::summonChampion) +
                    config.getSpellConfigDouble("SummonChampionDrainPerSecond") * aiKey("ChampionExtraSeconds");
    if(player.getSeat()->getMana() < needed)
        return false;

    // The mistake: the champion is summoned at any fight, also a trivial one
    if(!heartOrLaunch && !ai.getMind().slip("E20"))
        return false;

    ACTS::castSpell(ai, SpellType::summonChampion, tile);
    return true;
}
