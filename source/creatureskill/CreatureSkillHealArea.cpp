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

#include "creatureskill/CreatureSkillHealArea.h"

#include "creatureskill/CreatureSkillManager.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "spells/Spell.h"
#include "utils/ConfigManager.h"

#include <vector>

#include <istream>

const std::string CreatureSkillHealAreaName = "HealArea";

namespace
{
class CreatureSkillHealAreaFactory : public CreatureSkillFactory
{
    CreatureSkill* createCreatureSkill() const override
    { return new CreatureSkillHealArea; }

    const std::string& getCreatureSkillName() const override
    { return CreatureSkillHealAreaName; }
};

// Register the factory
static CreatureSkillRegister reg(new CreatureSkillHealAreaFactory);
}

//! \brief Returns the name of the skill class used in skill lines.
const std::string& CreatureSkillHealArea::getSkillName() const
{
    return CreatureSkillHealAreaName;
}

//! \brief Tells whether the creature has the level the skill needs (0 is reached with rank 1).
bool CreatureSkillHealArea::canBeUsedBy(const Creature* creature) const
{
    if(creature->getLevel() < mCreatureLevelMin)
        return false;

    return true;
}

//! \brief Heals every own creature within the radius when enough of them (the creature itself included) are below
//! the health share of the config (SkillHealAreaBelow, SkillHealAreaMinCreatures).
bool CreatureSkillHealArea::tryUseSupport(GameMap& gameMap, Creature* creature) const
{
    if(!creature->isAlive())
        return false;

    ConfigManager& config = ConfigManager::getSingleton();
    const std::vector<Creature*> allies = creature->getOwnCreaturesWithin(mRadius);
    uint32_t nbHurt = 0;
    for(Creature* ally : allies)
    {
        if(ally->getMaxHp() > 0.0 && ally->getHP() / ally->getMaxHp() < config.getSkillHealAreaBelow())
            ++nbHurt;
    }

    if(nbHurt < config.getSkillHealAreaMinCreatures())
        return false;

    const double amount = mHealPercent / 100.0 * creature->getHealBase();
    for(Creature* ally : allies)
    {
        ally->heal(amount);
        for(Tile* tile : ally->getCoveredTiles())
        {
            Spell::fireSpellEffect(*tile, "Heal", "HealCast");
        }
    }

    return true;
}

//! \brief Returns a copy of the skill.
CreatureSkillHealArea* CreatureSkillHealArea::clone() const
{
    return new CreatureSkillHealArea(*this);
}

//! \brief Appends the names of the columns of the skill line to the format string.
void CreatureSkillHealArea::getFormatString(std::string& format) const
{
    CreatureSkill::getFormatString(format);
    if(!format.empty())
        format += "\t";

    format += "LevelMin\tRadius\tHealPercent";
}

//! \brief Writes the columns of the skill line.
void CreatureSkillHealArea::exportToStream(std::ostream& os) const
{
    CreatureSkill::exportToStream(os);
    os << "\t" << mCreatureLevelMin;
    os << "\t" << mRadius;
    os << "\t" << mHealPercent;
}

//! \brief Reads the columns of the skill line; returns false when one is missing or malformed.
bool CreatureSkillHealArea::importFromStream(std::istream& is)
{
    if(!CreatureSkill::importFromStream(is))
        return false;

    if(!(is >> mCreatureLevelMin))
        return false;
    if(!(is >> mRadius))
        return false;
    if(!(is >> mHealPercent))
        return false;

    return true;
}

//! \brief Tells whether the other skill is the same class with the same values.
bool CreatureSkillHealArea::isEqual(const CreatureSkill& creatureSkill) const
{
    if(!CreatureSkill::isEqual(creatureSkill))
        return false;

    const CreatureSkillHealArea* skill = dynamic_cast<const CreatureSkillHealArea*>(&creatureSkill);
    if(skill == nullptr)
        return false;

    if(mCreatureLevelMin != skill->mCreatureLevelMin)
        return false;
    if(mRadius != skill->mRadius)
        return false;
    if(mHealPercent != skill->mHealPercent)
        return false;

    return true;
}
