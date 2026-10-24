#include "entities/ItemEffects.h"

#include "creatureeffect/CreatureEffectBleed.h"
#include "creatureeffect/CreatureEffectSpeedChange.h"
#include "creatureeffect/CreatureEffectStrengthChange.h"
#include "entities/Creature.h"
#include "entities/GameEntity.h"
#include "entities/GameEntityType.h"
#include "entities/MissileOneHit.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/SandboxMode.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace
{
static const double PERCENT = 100.0;
static const double CHILL_FACTOR = 0.9;
static const double WEAKEN_FACTOR = 0.95;
static const double ADJACENT_DISTANCE = 1.0;

//! \brief Effect names used by tooltips and definition validation.
struct EffectName
{
    //! \brief Configuration id of the effect.
    const char* mId;
    //! \brief Tooltip name chosen for the effect.
    const char* mDisplay;
};

static const EffectName EFFECT_NAMES[] =
{
    {"SwiftStep", "Swift Step"}, {"Wader", "Wader"}, {"SecondWind", "Second Wind"},
    {"LightStep", "Light Step"}, {"Tireless", "Tireless"}, {"QuickRise", "Quick Rise"},
    {"SureFooting", "Sure Footing"}, {"LavaStride", "Lava Stride"},
    {"ClearMind", "Clear Mind"}, {"Focus", "Focus"}, {"KeenEye", "Keen Eye"},
    {"ThickSkull", "Thick Skull"}, {"FarSight", "Far Sight"}, {"Scholar", "Scholar"},
    {"IronWill", "Iron Will"}, {"Craftsman", "Craftsman"},
    {"ThickPlates", "Thick Plates"}, {"Spiked", "Spiked"}, {"Mending", "Mending"},
    {"FireWard", "Fire Ward"}, {"SpellWard", "Spell Ward"}, {"LastStand", "Last Stand"},
    {"Lifeblood", "Lifeblood"}, {"Unyielding", "Unyielding"},
    {"Block", "Block"}, {"Spikes", "Spikes"}, {"Brace", "Brace"},
    {"GuardWall", "Guard Wall"}, {"Deflect", "Deflect"}, {"Steadfast", "Steadfast"},
    {"Bulwark", "Bulwark"}, {"Rally", "Rally"},
    {"Bleed", "Bleed"}, {"Chill", "Chill"}, {"Weaken", "Weaken"},
    {"Vampiric", "Vampiric"}, {"Executioner", "Executioner"}, {"Swift", "Swift"},
    {"Breaker", "Breaker"}, {"ManaLeech", "Mana Leech"}, {"Cleave", "Cleave"},
    {"HeroBane", "Hero Bane"},
    {"GoldNose", "Gold Nose"}, {"ManaSpring", "Mana Spring"}, {"Stamina", "Stamina"},
    {"Charisma", "Charisma"}, {"Thrift", "Thrift"}, {"Trainer", "Trainer"}, {"Fortune", "Fortune"}
};

//! \brief Applies cleave to enemy creatures on the eight tiles surrounding the struck target.
void cleave(Creature& attacker, const Creature& target, double damage)
{
    const double cleaveDamage = damage * attacker.getItemEffect("Cleave") / PERCENT;
    if(cleaveDamage <= 0.0 || attacker.getSeat() == nullptr)
        return;

    const std::vector<Creature*> creatures = attacker.getGameMap()->getCreatures();
    for(Creature* other : creatures)
    {
        if(other == nullptr || other == &target || other == &attacker || !other->isAlive()
            || !other->getIsOnMap() || other->getSeat() == nullptr
            || attacker.getSeat()->isAlliedSeat(other->getSeat()))
            continue;
        const Ogre::Vector3 delta = other->getPosition() - target.getPosition();
        if(std::abs(delta.x) > ADJACENT_DISTANCE || std::abs(delta.y) > ADJACENT_DISTANCE)
            continue;
        other->takeDamage(&attacker, cleaveDamage, 0.0, 0.0, 0.0, other->getPositionTile(), false);
    }
}
}

//! \brief Validates an id against the complete equipment effect name table.
bool ItemEffects::exists(const std::string& id)
{
    for(const EffectName& effect : EFFECT_NAMES)
        if(id == effect.mId)
            return true;
    return false;
}

//! \brief Looks up the player-visible effect name without creating new names.
std::string ItemEffects::getName(const std::string& id)
{
    for(const EffectName& effect : EFFECT_NAMES)
        if(id == effect.mId)
            return effect.mDisplay;
    return id;
}

//! \brief Adds Executioner to the global critical multiplier.
double ItemEffects::criticalMultiplier(const Creature& wearer)
{
    return ConfigManager::getSingleton().getCritDamageMultiplier() + wearer.getItemEffect("Executioner");
}

//! \brief Applies Breaker to structures and Hero Bane to creatures belonging to hero seats.
double ItemEffects::targetDamageFactor(const Creature& wearer, const GameEntity& target)
{
    if(target.getObjectType() != GameEntityType::creature)
        return increaseFactor(wearer, "Breaker");
    const Seat* targetSeat = target.getSeat();
    const bool waveSeat = targetSeat != nullptr && target.getGameMap() != nullptr &&
        !target.getGameMap()->getRoomsByTypeAndSeat(RoomType::portalWave, targetSeat).empty();
    if(SandboxMode::isHeroSeat(targetSeat) || waveSeat)
        return increaseFactor(wearer, "HeroBane");
    return 1.0;
}

//! \brief Applies effects only after a landed blow; retaliation never recursively triggers weapon effects.
void ItemEffects::onHit(Creature& attacker, Creature& target, double damage, bool melee, double retaliationPercent)
{
    const double healing = attacker.getItemEffect("Vampiric");
    if(damage > 0.0 && healing > 0.0)
        attacker.heal(damage * healing / PERCENT);
    attacker.setCurrentMana(attacker.getCurrentMana() + attacker.getItemEffect("ManaLeech"));

    if(target.isAlive())
    {
        const double bleed = attacker.getItemEffect("Bleed");
        if(bleed > 0.0 && damage > 0.0)
            target.addCreatureEffect(new CreatureEffectBleed(damage * bleed / PERCENT, attacker.getName()));

        const double chill = attacker.getItemEffect("Chill");
        if(chill > 0.0)
        {
            CreatureEffectSpeedChange* effect = new CreatureEffectSpeedChange(chill, CHILL_FACTOR, "");
            effect->setSourceId("item:Chill");
            target.addCreatureEffect(effect);
        }

        const double weaken = attacker.getItemEffect("Weaken");
        if(weaken > 0.0)
        {
            CreatureEffectStrengthChange* effect = new CreatureEffectStrengthChange(weaken, WEAKEN_FACTOR, "");
            effect->setSourceId("item:Weaken");
            target.addCreatureEffect(effect);
        }
    }

    cleave(attacker, target, damage);
    if(melee && attacker.isAlive() && damage > 0.0)
    {
        if(retaliationPercent > 0.0)
            attacker.takeDamage(&target, damage * retaliationPercent / PERCENT,
                0.0, 0.0, 0.0, attacker.getPositionTile(), false);
    }
}

//! \brief Uses creature or projectile provenance to apply Lifeblood on the actual damage path once.
void ItemEffects::onDamageDealt(GameEntity* source, Creature& target, double damage)
{
    if(source == nullptr || damage <= 0.0)
        return;
    Creature* wearer = nullptr;
    if(source->getObjectType() == GameEntityType::creature)
        wearer = static_cast<Creature*>(source);
    else if(source->getObjectType() == GameEntityType::missileObject)
    {
        const MissileOneHit* missile = dynamic_cast<const MissileOneHit*>(source);
        if(missile != nullptr)
            wearer = target.getGameMap()->getCreature(missile->getShooterName());
    }
    if(wearer == nullptr || !wearer->isAlive())
        return;
    const double healing = wearer->getItemEffect("Lifeblood");
    if(healing > 0.0)
        wearer->heal(damage * healing / PERCENT);
}

//! \brief Scales each negative mood modifier before it is added to the other moods.
double ItemEffects::moodModifier(const Creature& wearer, double points)
{
    if(points < 0.0)
        return points * remainingFactor(wearer, "IronWill");
    return points;
}

//! \brief Converts summed positive percentage points into a multiplicative increase.
double ItemEffects::increaseFactor(const Creature& wearer, const std::string& id)
{
    return 1.0 + wearer.getItemEffect(id) / PERCENT;
}

//! \brief Prevents a summed duration or strength resistance from turning negative.
double ItemEffects::remainingFactor(const Creature& wearer, const std::string& id)
{
    return std::max(0.0, 1.0 - wearer.getItemEffect(id) / PERCENT);
}
