/*
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

#include "creaturemood/CreatureMoodManager.h"

#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/ItemEffects.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

#include <algorithm>
#include <istream>
#include <vector>

namespace
{
    static std::vector<const CreatureMoodFactory*>& getFactories()
    {
        static std::vector<const CreatureMoodFactory*> factory;
        return factory;
    }
}

void CreatureMoodManager::registerFactory(const CreatureMoodFactory* factory)
{
    std::vector<const CreatureMoodFactory*>& factories = getFactories();
    factories.push_back(factory);
}

void CreatureMoodManager::unregisterFactory(const CreatureMoodFactory* factory)
{
    std::vector<const CreatureMoodFactory*>& factories = getFactories();
    std::vector<const CreatureMoodFactory*>::iterator it = std::find(factories.begin(), factories.end(), factory);
    if(it == factories.end())
    {
        OD_LOG_ERR("Trying to unregister unknown factory=" + factory->getCreatureMoodName());
        return;
    }
    factories.erase(it);
}

//! \brief Maps the effective mood to a mood level with the ranges of the global configuration.
CreatureMoodLevel CreatureMoodManager::getCreatureMoodLevel(double effectiveMood)
{
    double mood = effectiveMood;
    if(mood >= ConfigManager::getSingleton().getCreatureMoodHappy())
        return CreatureMoodLevel::Happy;

    if(mood >= ConfigManager::getSingleton().getCreatureMoodUpset())
        return CreatureMoodLevel::Neutral;

    if(mood >= ConfigManager::getSingleton().getCreatureMoodAngry())
        return CreatureMoodLevel::Upset;

    if(mood >= ConfigManager::getSingleton().getCreatureMoodFurious())
        return CreatureMoodLevel::Angry;

    return CreatureMoodLevel::Furious;
}

//! \brief Maps the mood of an old save to the stored scale, range to range, linear inside each range, no rounding.
double CreatureMoodManager::mapOldSaveMood(double oldMood)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    const double maxMood = config.getCreatureBaseMood();
    const double upset = config.getCreatureMoodUpset();
    const double angry = config.getCreatureMoodAngry();
    const double furious = config.getCreatureMoodFurious();
    // The old ranges: Neutral and Happy from 1000, Upset from 0, Angry from -1000, Furious below
    const double oldUpsetFrom = 0.0;
    const double oldAngryFrom = -1000.0;
    const double oldFuriousFrom = -2000.0;

    if(oldMood >= upset)
        return std::min(maxMood, oldMood);

    if(oldMood >= oldUpsetFrom)
        return angry + (oldMood - oldUpsetFrom) / (upset - 1.0 - oldUpsetFrom) * (upset - 1.0 - angry);

    if(oldMood >= oldAngryFrom)
        return furious + (oldMood - oldAngryFrom) / (oldUpsetFrom - 1.0 - oldAngryFrom) * (angry - 1.0 - furious);

    if(oldMood > oldFuriousFrom)
        return (oldMood - oldFuriousFrom) / (oldAngryFrom - oldFuriousFrom) * (furious - 1.0);

    return 0.0;
}

//! \brief Sums the old modifiers a loaded creature still shows and the temporary moods the old save held.
double CreatureMoodManager::computeOldSaveMood(const Creature& creature, double savedTemporaryMood)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    double points = 0.0;
    // Hunger, thirst and wakefulness grew per point beyond their start values
    if(creature.getHunger() >= config.getLegacyMoodConfigDouble("HungerStart"))
        points += ItemEffects::moodModifier(creature, (creature.getHunger() - config.getLegacyMoodConfigDouble("HungerStart"))
            * config.getLegacyMoodConfigDouble("HungerPerPoint"));
    if(creature.getThirst() >= config.getLegacyMoodConfigDouble("ThirstStart"))
        points += ItemEffects::moodModifier(creature, (creature.getThirst() - config.getLegacyMoodConfigDouble("ThirstStart"))
            * config.getLegacyMoodConfigDouble("ThirstPerPoint"));
    if(creature.getWakefulness() <= config.getLegacyMoodConfigDouble("WakefulnessStart"))
        points += ItemEffects::moodModifier(creature, (config.getLegacyMoodConfigDouble("WakefulnessStart") - creature.getWakefulness())
            * config.getLegacyMoodConfigDouble("WakefulnessPerPoint"));

    // Missed wages, wounds and a missing lair
    points += ItemEffects::moodModifier(creature, creature.getMissedWages() * config.getLegacyMoodConfigDouble("FeePerWage"));
    if(creature.getMaxHp() > 0.0)
        points += ItemEffects::moodModifier(creature, (creature.getMaxHp() - creature.getHP()) / creature.getMaxHp()
            * config.getLegacyMoodConfigDouble("HpLossFull"));
    // A missing lair is not counted: the beds of a loaded dungeon are restored after the creatures, so a creature without a
    // home tile here may still get its bed, and a level creature must not start low; a real lack of a bed starts the problem
    // without a jump after the load.

    // The temporary moods the old save held (tavern, spa, infirmary, merchant, prison and torture)
    points += savedTemporaryMood;
    return config.getCreatureBaseMood() + points;
}

CreatureMood* CreatureMoodManager::clone(const CreatureMood* mood)
{
    return mood->clone();
}

CreatureMood* CreatureMoodManager::load(std::istream& defFile)
{
    if(!defFile.good())
        return nullptr;

    std::vector<const CreatureMoodFactory*>& factories = getFactories();
    std::string nextParam;
    OD_ASSERT_TRUE(defFile >> nextParam);
    const CreatureMoodFactory* factoryToUse = nullptr;
    for(const CreatureMoodFactory* factory : factories)
    {
        if(factory == nullptr)
            continue;

        if(factory->getCreatureMoodName().compare(nextParam) != 0)
            continue;

        factoryToUse = factory;
        break;
    }

    if(factoryToUse == nullptr)
    {
        OD_LOG_ERR("Unknown mood modifier=" + nextParam);
        return nullptr;
    }

    CreatureMood* mood = factoryToUse->createCreatureMood();
    if(!mood->importFromStream(defFile))
    {
        OD_LOG_ERR("Couldn't load creature mood modifier=" + nextParam);
        delete mood;
        return nullptr;
    }

    return mood;
}

void CreatureMoodManager::dispose(const CreatureMood* mood)
{
    delete mood;
}

void CreatureMoodManager::write(const CreatureMood& mood, std::ostream& os)
{
    os << mood.getModifierName();
    mood.exportToStream(os);
}

void CreatureMoodManager::getFormatString(const CreatureMood& mood, std::string& format)
{
    format = "# MoodModifierName";
    mood.getFormatString(format);
}

bool CreatureMoodManager::areEqual(const CreatureMood& mood1, const CreatureMood& mood2)
{
    return mood1.isEqual(mood2);
}
