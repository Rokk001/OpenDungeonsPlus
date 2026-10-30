#ifndef CREATUREPROGRESSION_H
#define CREATUREPROGRESSION_H

#include <algorithm>
#include <cstdint>
#include <cmath>

#include "utils/ConfigManager.h"

namespace CreatureProgression
{
//! The growth coefficients and exponents of the curves (CreatureDamageGrowth, CreatureDamageExponent,
//! CreatureHpGrowthPerLevel, CooldownReductionPerLevel) are read from global.cfg through the ConfigManager;
//! this header only holds the formulas.
//! Highest creature level; the power curve is spread over the levels 1 to this value.
const uint32_t MAX_POWER_LEVEL = 30;

//! \brief Returns the creature damage and defense multiplier, clamped to levels 1 through 30:
//! 1 + CreatureDamageGrowth x (level - 1) ^ CreatureDamageExponent.
inline double damageMultiplier(uint32_t level)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    return 1.0 + config.getCreatureDamageGrowth() *
        std::pow(std::max(1u, std::min(MAX_POWER_LEVEL, level)) - 1, config.getCreatureDamageExponent());
}

//! \brief Returns the creature health multiplier, clamped to levels 1 through 30: the damage multiplier times
//! 1 + CreatureHpGrowthPerLevel x (level - 1), so health grows slightly faster than damage.
inline double hpMultiplier(uint32_t level)
{
    const double steps = std::max(1u, std::min(MAX_POWER_LEVEL, level)) - 1;
    return damageMultiplier(level) * (1.0 + ConfigManager::getSingleton().getCreatureHpGrowthPerLevel() * steps);
}

//! \brief Returns the attack rating multiplier, which is the level clamped to 1 through 30 (as the defense rating).
inline double attackRatingMultiplier(uint32_t level)
{
    return std::max(1u, std::min(MAX_POWER_LEVEL, level));
}

//! \brief Returns the defense rating multiplier, clamped to levels 1 through 30.
inline double defenseRatingMultiplier(uint32_t level)
{
    return std::max(1u, std::min(MAX_POWER_LEVEL, level));
}

//! \brief Returns the larger of linear growth and the supplied combat curve at the clamped level.
//! \param multiplier The health, damage or rating multiplier to apply to the base stat.
inline double combatStat(double base, double perLevel, uint32_t level, double (*multiplier)(uint32_t))
{
    level = std::max(1u, std::min(MAX_POWER_LEVEL, level));
    return std::max(base + (level - 1) * perLevel, base * multiplier(level));
}

//! \brief Returns the damage multiplier for a fractional attribute level: the same curve as damageMultiplier, but
//! without the upper limit of level 30 (a level below 1 counts as 1).
//! \param level The attribute level LA (may be fractional and above 30).
inline double damageMultiplierAt(double level)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    return 1.0 + config.getCreatureDamageGrowth() *
        std::pow(std::max(1.0, level) - 1.0, config.getCreatureDamageExponent());
}

//! \brief Returns the health multiplier for a fractional attribute level: the same curve as hpMultiplier, but
//! without the upper limit of level 30 (a level below 1 counts as 1).
//! \param level The attribute level LA (may be fractional and above 30).
inline double hpMultiplierAt(double level)
{
    const double steps = std::max(1.0, level) - 1.0;
    return damageMultiplierAt(level) * (1.0 + ConfigManager::getSingleton().getCreatureHpGrowthPerLevel() * steps);
}

//! \brief Returns the attack rating multiplier for a fractional attribute level, without the upper limit of level 30
//! (a level below 1 counts as 1).
//! \param level The attribute level LA (may be fractional and above 30).
inline double attackRatingMultiplierAt(double level)
{
    return std::max(1.0, level);
}

//! \brief Returns the defense rating multiplier for a fractional attribute level, without the upper limit of level 30
//! (a level below 1 counts as 1).
//! \param level The attribute level LA (may be fractional and above 30).
inline double defenseRatingMultiplierAt(double level)
{
    return std::max(1.0, level);
}

//! \brief Returns the larger of linear growth and the supplied combat curve at a fractional attribute level, without
//! the upper limit of level 30 (a level below 1 counts as 1); at whole levels 1 to 30 it equals combatStat.
//! \param base The stat at level 1.
//! \param perLevel The linear growth per level.
//! \param level The attribute level LA (may be fractional and above 30).
//! \param multiplier The curve to apply to the base stat (damageMultiplierAt, hpMultiplierAt, ...).
inline double combatStatAt(double base, double perLevel, double level, double (*multiplier)(double))
{
    level = std::max(1.0, level);
    return std::max(base + (level - 1.0) * perLevel, base * multiplier(level));
}

//! Returns the factor by which a creature's base power grows at the given level: 1 at level 1 and
//! 6 at the highest level. The levels are clamped to 1..MAX_POWER_LEVEL.
inline double powerMultiplier(uint32_t level)
{
    // Power factors at evenly spaced levels; the levels in between are interpolated linearly.
    const std::vector<double>& anchors = ConfigManager::getSingleton().getBuildingDamageCurve();
    const uint32_t lastAnchor = static_cast<uint32_t>(anchors.size()) - 1;
    const double position = (std::max(1u, std::min(MAX_POWER_LEVEL, level)) - 1) * static_cast<double>(lastAnchor) /
        (MAX_POWER_LEVEL - 1);
    const uint32_t index = static_cast<uint32_t>(position);
    if(index == lastAnchor)
        return anchors[lastAnchor];
    return anchors[index] + (anchors[index + 1] - anchors[index]) * (position - index);
}

//! Returns a stat at the given level: the larger of the configured linear growth
//! (base + perLevel for every level above 1) and the base scaled by the shared power curve.
inline double stat(double base, double perLevel, uint32_t level)
{
    // Retain explicitly configured growth above the shared power curve.
    return std::max(base + (std::max(1u, level) - 1) * perLevel,
        base * powerMultiplier(level));
}

//! Returns the cooldown of an attack at the given level: the base cooldown times
//! 1 - CooldownReductionPerLevel x (level - 1) (global.cfg, 0 = the same cooldown at every level),
//! not rounded to whole turns, but never below 1 turn.
//! A base cooldown of 0 stays 0.
//! \param baseTurns The cooldown at level 1 in turns.
//! \param level The creature level.
//! \return The cooldown in turns, possibly a fraction of a turn.
inline double cooldownAtLevel(uint32_t baseTurns, uint32_t level)
{
    if(baseTurns == 0)
        return 0.0;

    const double factor = 1.0 - ConfigManager::getSingleton().getCooldownReductionPerLevel() * (std::max(1u, level) - 1);
    return std::max(1.0, baseTurns * factor);
}
}

#endif
