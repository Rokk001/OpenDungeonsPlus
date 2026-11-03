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

#ifndef CREATUREMOODMANAGER_H
#define CREATUREMOODMANAGER_H

#include <cstdint>
#include <iosfwd>
#include <string>

class Creature;
class CreatureMood;

enum class CreatureMoodLevel;

//! \brief Factory class to register a new mood modifier
class CreatureMoodFactory
{
public:
    virtual ~CreatureMoodFactory()
    {}

    virtual CreatureMood* createCreatureMood() const = 0;

    virtual const std::string& getCreatureMoodName() const = 0;
};

//! \brief Combines the configured and temporary mood modifiers of a creature.
class CreatureMoodManager
{
friend class CreatureMoodRegister;

public:
    CreatureMoodManager()
    {}

    virtual ~CreatureMoodManager()
    {}

    //! \brief Maps the effective mood (the stored mood plus the Charisma of the worn items) to a mood level with the
    //! ranges of the global configuration (Happy, Neutral, Upset, Angry, Furious).
    //! \param effectiveMood The effective mood, 0 and more.
    static CreatureMoodLevel getCreatureMoodLevel(double effectiveMood);

    //! \brief Maps the mood of an old save, which had no stored mood, to the stored scale, range to range: 1000 and
    //! above is kept (at most CreatureBaseMood), 0 .. 999 goes to 500 .. 999, -1000 .. -1 to 100 .. 499 and -2000 ..
    //! -1001 to 0 .. 99 (linear inside each range, no rounding, -2000 and below is 0).
    //! \param oldMood The mood of an old save: the old base mood plus all its modifiers.
    static double mapOldSaveMood(double oldMood);

    //! \brief Sums the old mood modifiers of a creature loaded from a save without stored mood with the old formula
    //! (the values of the [LegacyMood] block of the global configuration) and the old temporary moods the save held.
    //! The result is the old mood (base mood included) that mapOldSaveMood maps to the stored scale.
    //! \param creature The loaded creature.
    //! \param savedTemporaryMood The sum of the temporary mood points the old save held (tavern, spa, infirmary,
    //! merchant, prison and torture).
    static double computeOldSaveMood(const Creature& creature, double savedTemporaryMood);

    static CreatureMood* clone(const CreatureMood* mood);

    static CreatureMood* load(std::istream& defFile);

    static void dispose(const CreatureMood* mood);

    static void write(const CreatureMood& mood, std::ostream& os);

    static void getFormatString(const CreatureMood& mood, std::string& format);

    static bool areEqual(const CreatureMood& mood1, const CreatureMood& mood2);

private:
    static void registerFactory(const CreatureMoodFactory* factory);
    static void unregisterFactory(const CreatureMoodFactory* factory);
};

class CreatureMoodRegister
{
public:
    CreatureMoodRegister(const CreatureMoodFactory* factoryToRegister) :
        mCreatureMoodFactory(factoryToRegister)
    {
        CreatureMoodManager::registerFactory(mCreatureMoodFactory);
    }
    ~CreatureMoodRegister()
    {
        CreatureMoodManager::unregisterFactory(mCreatureMoodFactory);
        delete mCreatureMoodFactory;
    }

private:
    const CreatureMoodFactory* mCreatureMoodFactory;
};

#endif // CREATUREMOODMANAGER_H
