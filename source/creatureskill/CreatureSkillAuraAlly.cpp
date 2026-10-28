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

#include "creatureskill/CreatureSkillAuraAlly.h"

#include "utils/LogManager.h"

#include "creatureaction/CreatureAction.h"
#include "creatureeffect/CreatureEffectStrengthChange.h"
#include "creatureskill/CreatureSkillManager.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "spells/Spell.h"

#include <vector>

#include <istream>

const std::string CreatureSkillAuraAllyName = "AuraAlly";

namespace
{
class CreatureSkillAuraAllyFactory : public CreatureSkillFactory
{
    CreatureSkill* createCreatureSkill() const override
    { return new CreatureSkillAuraAlly; }

    const std::string& getCreatureSkillName() const override
    { return CreatureSkillAuraAllyName; }
};

// Register the factory
static CreatureSkillRegister reg(new CreatureSkillAuraAllyFactory);
}

//! \brief Returns the name of the skill class used in skill lines.
const std::string& CreatureSkillAuraAlly::getSkillName() const
{
    return CreatureSkillAuraAllyName;
}

//! \brief Tells whether the creature has the level the skill needs (0 is reached with rank 1).
bool CreatureSkillAuraAlly::canBeUsedBy(const Creature* creature) const
{
    if(creature->getLevel() < mCreatureLevelMin)
        return false;

    return true;
}

//! \brief Strengthens the own creatures within the radius while the creature fights and at least one other own
//! creature is within the radius.
bool CreatureSkillAuraAlly::tryUseSupport(GameMap& gameMap, Creature* creature) const
{
    if(!creature->isAlive())
        return false;

    if(!creature->isActionInList(CreatureActionType::fight))
        return false;

    const std::vector<Creature*> allies = creature->getOwnCreaturesWithin(mRadius);
    if(allies.size() < mMinAllies)
        return false;

    for(Creature* ally : allies)
    {
        CreatureEffectStrengthChange* effect = new CreatureEffectStrengthChange(mEffectDuration, mEffectValue,
            "SpellCreatureStrength");
        tagEffect(effect);
        ally->addCreatureEffect(effect);
    }

    for(Tile* tile : creature->getCoveredTiles())
    {
        Spell::fireSpellSound(*tile, "Heal");
    }

    return true;
}

//! \brief Returns a copy of the skill.
CreatureSkillAuraAlly* CreatureSkillAuraAlly::clone() const
{
    return new CreatureSkillAuraAlly(*this);
}

//! \brief Appends the names of the columns of the skill line to the format string.
void CreatureSkillAuraAlly::getFormatString(std::string& format) const
{
    CreatureSkill::getFormatString(format);
    if(!format.empty())
        format += "\t";

    format += "LevelMin\tRadius\tEffectDuration\tEffectValue\tMinAllies";
}

//! \brief Writes the columns of the skill line.
void CreatureSkillAuraAlly::exportToStream(std::ostream& os) const
{
    CreatureSkill::exportToStream(os);
    os << "\t" << mCreatureLevelMin;
    os << "\t" << mRadius;
    os << "\t" << mEffectDuration;
    os << "\t" << mEffectValue;
    os << "\t" << mMinAllies;
}

//! \brief Reads the columns of the skill line; returns false when one is missing or malformed.
bool CreatureSkillAuraAlly::importFromStream(std::istream& is)
{
    if(!CreatureSkill::importFromStream(is))
        return false;

    if(!(is >> mCreatureLevelMin))
        return false;
    if(!(is >> mRadius))
        return false;
    if(!(is >> mEffectDuration))
        return false;
    if(!(is >> mEffectValue))
        return false;
    if(!(is >> mMinAllies))
    {
        mMinAllies = 2;
        is.clear();
        OD_LOG_ERR("Missing aura MinAllies; using shipped default 2");
    }

    return true;
}

//! \brief Tells whether the other skill is the same class with the same values.
bool CreatureSkillAuraAlly::isEqual(const CreatureSkill& creatureSkill) const
{
    if(!CreatureSkill::isEqual(creatureSkill))
        return false;

    const CreatureSkillAuraAlly* skill = dynamic_cast<const CreatureSkillAuraAlly*>(&creatureSkill);
    if(skill == nullptr)
        return false;

    if(mCreatureLevelMin != skill->mCreatureLevelMin)
        return false;
    if(mRadius != skill->mRadius)
        return false;
    if(mEffectDuration != skill->mEffectDuration)
        return false;
    if(mMinAllies != skill->mMinAllies)
        return false;
    if(mEffectValue != skill->mEffectValue)
        return false;

    return true;
}
