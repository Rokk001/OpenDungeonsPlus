#ifndef COMBATDAMAGE_H
#define COMBATDAMAGE_H

#include "entities/Creature.h"
#include "entities/CreatureProgression.h"
#include "entities/Weapon.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <istream>
#include <string>

//! \brief Shared creature damage range parsing and the single roll used by all damage channels.
namespace CombatDamage
{
//! \brief Reads a marked minimum without consuming the next effect or a legacy save suffix.
inline bool readEffectMinimum(std::istream& is, double& minimum)
{
    const std::streampos position = is.tellg();
    std::string marker;
    if(!(is >> marker))
    {
        is.clear();
        return true;
    }
    if(marker != "DamageRangeMin")
    {
        is.seekg(position);
        return static_cast<bool>(is);
    }
    return static_cast<bool>(is >> minimum);
}

//! \brief Applies the creature curve at the given attribute level, the damage passives and the carried weapon ranges
//! before any target defenses are subtracted. The passives (the given stat plus alldmg%) multiply the line damage only,
//! not the weapon ranges.
//! \param damageLevel The level of the curve: the Strength attribute level for melee, the Dexterity attribute level
//! for bow and crossbow lines, the creature level for every other line.
//! \param passiveStat The damage passive stat of the line: "dmg%" or "spell%".
inline void scale(const Creature& attacker, double& phyMin, double& phyMax,
    double& magMin, double& magMax, double& eleMin, double& eleMax, double damageLevel,
    const std::string& passiveStat)
{
    const double passiveFactor = 1.0 + (attacker.getSkillPassive(passiveStat) + attacker.getSkillPassive("alldmg%")) / 100.0;
    const double multiplier = CreatureProgression::damageMultiplierAt(damageLevel) * passiveFactor;
    phyMin *= multiplier;
    phyMax *= multiplier;
    magMin *= multiplier;
    magMax *= multiplier;
    eleMin *= multiplier;
    eleMax *= multiplier;
    const Weapon* weapons[] = {attacker.getWeaponL(), attacker.getWeaponR()};
    for(const Weapon* weapon : weapons)
    {
        if(weapon == nullptr)
            continue;
        phyMin += weapon->getPhysicalDamageMin();
        phyMax += weapon->getPhysicalDamage();
        magMin += weapon->getMagicalDamageMin();
        magMax += weapon->getMagicalDamage();
        eleMin += weapon->getElementDamageMin();
        eleMax += weapon->getElementDamage();
    }
}

//! \brief Rolls a critical hit for a chance in percent (a chance of 0 or less never rolls). Used by shots that carry
//! the chance of their shooter from the launch.
inline bool rollCriticalChance(double chancePercent)
{
    if(chancePercent <= 0.0)
        return false;
    return Random::Double(0.0, 100.0) < chancePercent;
}

//! \brief Multiplies every damage value by CritDamageMultiplier plus the attacker's equipment bonus. Called for a critical hit
//! before the defense of the target is subtracted (see roll()).
//! \param extraMultiplier Executioner bonus, zero for sources without item effects.
inline void applyCriticalToRange(double& phyMin, double& phyMax, double& magMin, double& magMax,
    double& eleMin, double& eleMax, double extraMultiplier = 0.0)
{
    const double factor = ConfigManager::getSingleton().getCritDamageMultiplier() + extraMultiplier;
    phyMin *= factor;
    phyMax *= factor;
    magMin *= factor;
    magMax *= factor;
    eleMin *= factor;
    eleMax *= factor;
}

//! \brief Reads an optional appended six-column range, retaining the legacy values at end of line.
inline bool readRange(std::istream& is, double& phyMin, double& phyMax,
    double& magMin, double& magMax, double& eleMin, double& eleMax)
{
    is >> std::ws;
    if(is.eof())
    {
        is.clear();
        return true;
    }
    return static_cast<bool>(is >> phyMin >> phyMax >> magMin >> magMax >> eleMin >> eleMax);
}

//! \brief Rolls damage after subtracting each channel defense, sharing one random fraction across channels.
//! \param rawDamage Optional output receiving pre-defense damage from the same roll.
inline double roll(const Creature& target, double phyMin, double phyMax,
    double magMin, double magMax, double eleMin, double eleMax, double* rawDamage = nullptr)
{
    const double u = Random::Double(0.0, 1.0);
    if(rawDamage != nullptr)
        *rawDamage = phyMin + magMin + eleMin
            + u * (phyMax + magMax + eleMax - phyMin - magMin - eleMin);
    const double physicalLo = std::max(phyMin - target.getPhysicalDefense(), 0.0);
    const double magicalLo = std::max(magMin - target.getMagicalDefense(), 0.0);
    const double elementalLo = std::max(eleMin - target.getElementDefense(), 0.0);
    const double lo = physicalLo + magicalLo + elementalLo;
    const double hi = std::max(phyMax - target.getPhysicalDefense(), 0.0)
        + std::max(magMax - target.getMagicalDefense(), 0.0)
        + std::max(eleMax - target.getElementDefense(), 0.0);
    return lo + u * (hi - lo);
}
}

#endif // COMBATDAMAGE_H
