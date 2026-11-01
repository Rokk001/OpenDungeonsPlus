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

#ifndef CREATURESKILLAURAALLY_H
#define CREATURESKILLAURAALLY_H

#include "creatureskill/CreatureSkill.h"

#include <cstdint>
#include <iosfwd>
#include <string>

class Creature;
class GameMap;

//! \brief Gives the strength change effect to every own creature within a radius (the creature itself included).
class CreatureSkillAuraAlly : public CreatureSkill
{
public:
    //! \brief Creates the skill with neutral values; the values come from the loaded skill line.
    CreatureSkillAuraAlly() :
        mCreatureLevelMin(0),
        mRadius(0.0),
        mEffectDuration(0),
        mEffectValue(1.0),
        mMinAllies(2)
    {}

    //! \brief Destroys the skill.
    virtual ~CreatureSkillAuraAlly()
    {}

    //! \brief Returns the name of the skill class used in skill lines.
    virtual const std::string& getSkillName() const override;

    //! \brief Tells whether the creature has the level the skill needs.
    virtual bool canBeUsedBy(const Creature* creature) const override;

    //! \brief Uses the skill at the start of a turn when its conditions are met.
    virtual bool tryUseSupport(GameMap& gameMap, Creature* creature) const override;

    //! \brief The skill is never used against a target, so this always returns false.
    virtual bool tryUseFight(GameMap& gameMap, Creature* creature, float range,
        GameEntity* attackedObject, Tile* attackedTile, bool ko, bool notifyPlayerIfHit) const override
    { return false; }

    //! \brief Returns a copy of the skill.
    virtual CreatureSkillAuraAlly* clone() const override;

    //! \brief Tells whether the other skill is the same class with the same values.
    virtual bool isEqual(const CreatureSkill& creatureSkill) const override;

    //! \brief Appends the names of the columns of the skill line to the format string.
    virtual void getFormatString(std::string& format) const override;
    //! \brief Writes the columns of the skill line.
    virtual void exportToStream(std::ostream& os) const override;
    //! \brief Reads the columns of the skill line; returns false when one is missing or malformed.
    virtual bool importFromStream(std::istream& is) override;

private:
    //! \brief Creature level needed to use the skill (0: reached with rank 1)
    uint32_t mCreatureLevelMin;
    //! \brief Radius in tiles around the creature
    double mRadius;
    //! \brief Turns the effect lasts (a fraction of a turn is possible)
    double mEffectDuration;
    //! \brief Damage factor of the effect
    double mEffectValue;
    //! \brief Fewest allies inside the aura radius.
    uint32_t mMinAllies;
};

#endif // CREATURESKILLAURAALLY_H
