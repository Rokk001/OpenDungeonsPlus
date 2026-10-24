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

#include "creatureskill/CreatureSkillStrike.h"

#include "creatureaction/CreatureAction.h"
#include "creatureskill/CreatureSkillManager.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "spells/Spell.h"

#include <istream>

const std::string CreatureSkillStrikeName = "Strike";

namespace
{
class CreatureSkillStrikeFactory : public CreatureSkillFactory
{
    CreatureSkill* createCreatureSkill() const override
    { return new CreatureSkillStrike; }

    const std::string& getCreatureSkillName() const override
    { return CreatureSkillStrikeName; }
};

// Register the factory
static CreatureSkillRegister reg(new CreatureSkillStrikeFactory);
}

//! \brief Returns the name of the skill class used in skill lines.
const std::string& CreatureSkillStrike::getSkillName() const
{
    return CreatureSkillStrikeName;
}

//! \brief Tells whether the creature has the level the skill needs (0 is reached with rank 1).
bool CreatureSkillStrike::canBeUsedBy(const Creature* creature) const
{
    if(creature->getLevel() < mCreatureLevelMin)
        return false;

    return true;
}

//! \brief Arms the next melee blow while the creature fights and no blow is armed yet.
bool CreatureSkillStrike::tryUseSupport(GameMap& gameMap, Creature* creature) const
{
    if(!creature->isAlive())
        return false;

    // To not waste the skill, we only use it during a fight
    if(!creature->isActionInList(CreatureActionType::fight))
        return false;

    if(creature->isStrikeArmed())
        return false;

    creature->armStrike(mMultiplier);

    for(Tile* tile : creature->getCoveredTiles())
    {
        Spell::fireSpellSound(*tile, "Heal");
    }

    return true;
}

//! \brief Returns a copy of the skill.
CreatureSkillStrike* CreatureSkillStrike::clone() const
{
    return new CreatureSkillStrike(*this);
}

//! \brief Appends the names of the columns of the skill line to the format string.
void CreatureSkillStrike::getFormatString(std::string& format) const
{
    CreatureSkill::getFormatString(format);
    if(!format.empty())
        format += "\t";

    format += "LevelMin\tMultiplier";
}

//! \brief Writes the columns of the skill line.
void CreatureSkillStrike::exportToStream(std::ostream& os) const
{
    CreatureSkill::exportToStream(os);
    os << "\t" << mCreatureLevelMin;
    os << "\t" << mMultiplier;
}

//! \brief Reads the columns of the skill line; returns false when one is missing or malformed.
bool CreatureSkillStrike::importFromStream(std::istream& is)
{
    if(!CreatureSkill::importFromStream(is))
        return false;

    if(!(is >> mCreatureLevelMin))
        return false;
    if(!(is >> mMultiplier))
        return false;

    return true;
}

//! \brief Tells whether the other skill is the same class with the same values.
bool CreatureSkillStrike::isEqual(const CreatureSkill& creatureSkill) const
{
    if(!CreatureSkill::isEqual(creatureSkill))
        return false;

    const CreatureSkillStrike* skill = dynamic_cast<const CreatureSkillStrike*>(&creatureSkill);
    if(skill == nullptr)
        return false;

    if(mCreatureLevelMin != skill->mCreatureLevelMin)
        return false;
    if(mMultiplier != skill->mMultiplier)
        return false;

    return true;
}
