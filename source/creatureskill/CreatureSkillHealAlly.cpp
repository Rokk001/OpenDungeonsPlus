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

#include "creatureskill/CreatureSkillHealAlly.h"

#include "creatureskill/CreatureSkillManager.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "spells/Spell.h"
#include "utils/ConfigManager.h"

#include <vector>

#include <istream>

const std::string CreatureSkillHealAllyName = "HealAlly";

namespace
{
class CreatureSkillHealAllyFactory : public CreatureSkillFactory
{
    CreatureSkill* createCreatureSkill() const override
    { return new CreatureSkillHealAlly; }

    const std::string& getCreatureSkillName() const override
    { return CreatureSkillHealAllyName; }
};

// Register the factory
static CreatureSkillRegister reg(new CreatureSkillHealAllyFactory);
}

//! \brief Returns the name of the skill class used in skill lines.
const std::string& CreatureSkillHealAlly::getSkillName() const
{
    return CreatureSkillHealAllyName;
}

//! \brief Tells whether the creature has the level the skill needs (0 is reached with rank 1).
bool CreatureSkillHealAlly::canBeUsedBy(const Creature* creature) const
{
    if(creature->getLevel() < mCreatureLevelMin)
        return false;

    return true;
}

//! \brief Heals the own creature within the range with the lowest health share when that share is below the
//! limit of the config (SkillHealAllyBelow).
bool CreatureSkillHealAlly::tryUseSupport(GameMap& gameMap, Creature* creature) const
{
    if(!creature->isAlive())
        return false;

    const double below = ConfigManager::getSingleton().getSkillHealAllyBelow();
    const std::vector<Creature*> allies = creature->getOwnCreaturesWithin(mRange);
    Creature* weakest = nullptr;
    double weakestShare = below;
    for(Creature* ally : allies)
    {
        if(ally->getMaxHp() <= 0.0)
            continue;

        const double share = ally->getHP() / ally->getMaxHp();
        if(share >= weakestShare)
            continue;

        weakest = ally;
        weakestShare = share;
    }

    if(weakest == nullptr)
        return false;

    weakest->heal(mHealPercent / 100.0 * creature->getHealBase());
    for(Tile* tile : weakest->getCoveredTiles())
    {
        Spell::fireSpellEffect(*tile, "Heal", "HealCast");
    }

    return true;
}

//! \brief Returns a copy of the skill.
CreatureSkillHealAlly* CreatureSkillHealAlly::clone() const
{
    return new CreatureSkillHealAlly(*this);
}

//! \brief Appends the names of the columns of the skill line to the format string.
void CreatureSkillHealAlly::getFormatString(std::string& format) const
{
    CreatureSkill::getFormatString(format);
    if(!format.empty())
        format += "\t";

    format += "LevelMin\tRange\tHealPercent";
}

//! \brief Writes the columns of the skill line.
void CreatureSkillHealAlly::exportToStream(std::ostream& os) const
{
    CreatureSkill::exportToStream(os);
    os << "\t" << mCreatureLevelMin;
    os << "\t" << mRange;
    os << "\t" << mHealPercent;
}

//! \brief Reads the columns of the skill line; returns false when one is missing or malformed.
bool CreatureSkillHealAlly::importFromStream(std::istream& is)
{
    if(!CreatureSkill::importFromStream(is))
        return false;

    if(!(is >> mCreatureLevelMin))
        return false;
    if(!(is >> mRange))
        return false;
    if(!(is >> mHealPercent))
        return false;

    return true;
}

//! \brief Tells whether the other skill is the same class with the same values.
bool CreatureSkillHealAlly::isEqual(const CreatureSkill& creatureSkill) const
{
    if(!CreatureSkill::isEqual(creatureSkill))
        return false;

    const CreatureSkillHealAlly* skill = dynamic_cast<const CreatureSkillHealAlly*>(&creatureSkill);
    if(skill == nullptr)
        return false;

    if(mCreatureLevelMin != skill->mCreatureLevelMin)
        return false;
    if(mRange != skill->mRange)
        return false;
    if(mHealPercent != skill->mHealPercent)
        return false;

    return true;
}
