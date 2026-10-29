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
#include "entities/Building.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "gamemap/GameMap.h"
#include "ODApplication.h"
#include "spells/SpellSummonChampion.h"
#include "spells/SpellType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cstdint>
#include <map>
#include <set>
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

//! \brief The game turn of the last Eye of Evil cast of each seat (row E04).
std::map<int, int64_t> lastEyeTurn;
//! \brief The seats whose Defense cast was drawn as a mistake and is made after the fight (row E05).
std::set<int> lateDefense;

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

//! \brief Returns the enemies in sight that stand on ground claimed for the AI's seat.
std::vector<Creature*> enemiesOnOwnGround(KeeperAI& ai)
{
    Seat* seat = ai.getControlledPlayer().getSeat();
    std::vector<Creature*> result;
    for(Creature* creature : visibleEnemies(ai))
    {
        if(onOwnGround(creature, seat))
            result.push_back(creature);
    }
    return result;
}

//! \brief Casts a spell on the tile of the creature.
void castOnTileOf(KeeperAI& ai, SpellType type, Creature* creature)
{
    ACTS::castSpell(ai, type, creature->getPositionTile());
}
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

    // The heal reaches only own creatures on claimed ground, so an assault on enemy land has none
    std::vector<Creature*> hurt;
    if(!enemyGround && canCast(ai, SpellType::creatureHeal, "SpellManaReserve"))
    {
        for(Creature* creature : ownFighters(ai))
        {
            // Never a creature above HealNeverAbove: the heal would be wasted
            if((hpShare(creature) < aiKey("HealBelow")) && (hpShare(creature) <= aiKey("HealNeverAbove")) &&
               onOwnGround(creature, seat))
                hurt.push_back(creature);
        }
    }

    std::vector<Creature*> enemies = enemyGround ? visibleEnemies(ai) : enemiesOnOwnGround(ai);
    std::vector<Creature*> allEnemies = visibleEnemies(ai);
    bool slipped = ai.getMind().slip("E19");
    if((damage.empty() && hurt.empty()) || (enemies.empty() && allEnemies.empty() && hurt.empty()))
    {
        nextCast = now + aiKey("CastRecheckSeconds");
        return false;
    }

    // The choice: a mistake picks a random spell and wastes it, otherwise heal or the best damage per mana
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

    Seat* seat = ai.getControlledPlayer().getSeat();
    int64_t turn = ai.getGameMap().getTurnNumber();
    std::map<int, int64_t>::iterator it = lastEyeTurn.find(seat->getId());
    double minTurns = aiKey("EyeCastIntervalMinutes") * 60.0 * ODApplication::turnsPerSecond;
    if((it != lastEyeTurn.end()) && (static_cast<double>(turn - it->second) < minTurns))
        return false;

    // The mistake: the AI never casts it and attacks blind
    if(ai.getMind().slip("E04"))
        return false;

    lastEyeTurn[seat->getId()] = turn;
    ACTS::castSpell(ai, SpellType::eyeEvil, tile);
    return true;
}

bool SPELL::castDefense(KeeperAI& ai, const std::vector<Creature*>& holders, bool fightOver)
{
    // AI row E05
    Seat* seat = ai.getControlledPlayer().getSeat();
    if(fightOver)
    {
        // The late cast of the mistake: after the fight
        if(lateDefense.erase(seat->getId()) == 0)
            return false;
    }
    else if(ai.getMind().slip("E05"))
    {
        lateDefense.insert(seat->getId());
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

    // The mistake: the banner is cast for too few creatures
    if(!assault && (creaturesToGather <= static_cast<int>(aiKey("CallToWarMinCreatures"))) && !ai.getMind().slip("E07"))
        return false;

    ACTS::castSpell(ai, SpellType::callToWar, tile);
    return true;
}

bool SPELL::castSlow(KeeperAI& ai)
{
    // AI row E08
    if(!canCast(ai, SpellType::creatureSlow, "SpellManaReserve"))
        return false;

    std::vector<Creature*> enemies = enemiesOnOwnGround(ai);
    // The mistake: the weakest enemy instead of the strongest
    Creature* target = ai.getMind().slip("E08") ? weakest(enemies) : strongest(enemies);
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

    // The mood of an enemy is not visible to a keeper, so the best rule takes the strongest enemy that is already
    // hurt; the mistake takes the strongest one at full health, which resists
    bool slipped = ai.getMind().slip("E17");
    std::vector<Creature*> candidates;
    for(Creature* creature : enemiesOnOwnGround(ai))
    {
        if(slipped == (hpShare(creature) >= 1.0))
            candidates.push_back(creature);
    }
    Creature* target = strongest(candidates);
    if(target == nullptr)
        return false;

    castOnTileOf(ai, SpellType::defector, target);
    return true;
}

bool SPELL::castHexenHen(KeeperAI& ai)
{
    // AI row E18
    if(!canCast(ai, SpellType::hexenHen, "SpellManaReserve"))
        return false;

    Seat* seat = ai.getControlledPlayer().getSeat();
    // An enemy that attacks a room or the heart stands on a building tile of the AI
    bool slipped = ai.getMind().slip("E18");
    std::vector<Creature*> candidates;
    for(Creature* creature : enemiesOnOwnGround(ai))
    {
        Building* building = creature->getPositionTile()->getCoveringBuilding();
        bool attacksBuilding = (building != nullptr) && (building->getSeat() == seat);
        if(slipped != attacksBuilding)
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
