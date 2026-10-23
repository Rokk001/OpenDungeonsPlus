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

#ifndef CREATURESKILLSTRIKE_H
#define CREATURESKILLSTRIKE_H

#include "creatureskill/CreatureSkill.h"

#include <cstdint>
#include <iosfwd>
#include <string>

class Creature;
class GameMap;

//! \brief Arms the next melee blow of the creature against a creature: that blow does its damage times the multiplier.
class CreatureSkillStrike : public CreatureSkill
{
public:
    //! \brief Creates the skill with neutral values; the values come from the loaded skill line.
    CreatureSkillStrike() :
        mCreatureLevelMin(0),
        mMultiplier(1.0)
    {}

    //! \brief Destroys the skill.
    virtual ~CreatureSkillStrike()
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
    virtual CreatureSkillStrike* clone() const override;

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
    //! \brief Factor on the damage (before defense) of the armed blow
    double mMultiplier;
};

#endif // CREATURESKILLSTRIKE_H
