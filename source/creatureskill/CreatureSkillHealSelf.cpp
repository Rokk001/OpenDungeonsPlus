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

#include "creatureskill/CreatureSkillHealSelf.h"

#include "creatureeffect/CreatureEffectHeal.h"
#include "creatureskill/CreatureSkillManager.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "spells/Spell.h"
#include "utils/ConfigManager.h"

#include <istream>

const std::string CreatureSkillHealSelfName = "HealSelf";

namespace
{
class CreatureSkillHealSelfFactory : public CreatureSkillFactory
{
    CreatureSkill* createCreatureSkill() const override
    { return new CreatureSkillHealSelf; }

    const std::string& getCreatureSkillName() const override
    { return CreatureSkillHealSelfName; }
};

// Register the factory
static CreatureSkillRegister reg(new CreatureSkillHealSelfFactory);
}

const std::string& CreatureSkillHealSelf::getSkillName() const
{
    return CreatureSkillHealSelfName;
}

bool CreatureSkillHealSelf::canBeUsedBy(const Creature* creature) const
{
    if(creature->getLevel() < mCreatureLevelMin)
        return false;

    return true;
}

//! \brief Heals the creature over time when it is hurt (a skill of the skill tree: when its health share is below
//! the limit of the config); the percent form heals a share of the MinHP times the damage multiplier of the Mana level.
bool CreatureSkillHealSelf::tryUseSupport(GameMap& gameMap, Creature* creature) const
{
    if(!creature->isAlive())
        return false;

    if(isTreeSkill())
    {
        // A skill of the skill tree heals when the health share is low
        if(creature->getMaxHp() <= 0.0 ||
           creature->getHP() / creature->getMaxHp() >= ConfigManager::getSingleton().getSkillHealSelfBelow())
        {
            return false;
        }
    }
    else if(!creature->isHurt())
        return false;

    // The percent form heals a share of the MinHP in total, evenly over the duration
    double healPerTurn = mEffectValue;
    if(mHealPercent > 0.0 && mEffectDuration > 0)
        healPerTurn = mHealPercent / 100.0 * creature->getHealBase() / static_cast<double>(mEffectDuration);

    CreatureEffectHeal* effect = new CreatureEffectHeal(mEffectDuration, healPerTurn, "SpellCreatureHeal");
    creature->addCreatureEffect(effect);

    for(Tile* tile : creature->getCoveredTiles())
    {
        Spell::fireSpellEffect(*tile, "Heal", "HealCast");
    }

    return true;
}

CreatureSkillHealSelf* CreatureSkillHealSelf::clone() const
{
    return new CreatureSkillHealSelf(*this);
}

//! \brief Appends the names of the columns of the skill line (the percent column is optional).
void CreatureSkillHealSelf::getFormatString(std::string& format) const
{
    CreatureSkill::getFormatString(format);
    if(!format.empty())
        format += "\t";

    format += "LevelMin\tEffectDuration\tEffectValue\tHealPercent";
}

//! \brief Writes the columns of the skill line, the percent column included.
void CreatureSkillHealSelf::exportToStream(std::ostream& os) const
{
    CreatureSkill::exportToStream(os);
    os << "\t" << mCreatureLevelMin;
    os << "\t" << mEffectDuration;
    os << "\t" << mEffectValue;
    os << "\t" << mHealPercent;
}

//! \brief Reads the columns of the skill line; the percent column is optional and 0 when it is missing.
bool CreatureSkillHealSelf::importFromStream(std::istream& is)
{
    if(!CreatureSkill::importFromStream(is))
        return false;

    if(!(is >> mCreatureLevelMin))
        return false;
    if(!(is >> mEffectDuration))
        return false;
    if(!(is >> mEffectValue))
        return false;
    // The percent column is optional: lines written before it existed end after EffectValue
    mHealPercent = 0.0;
    is >> std::ws;
    if(is.eof())
        is.clear();
    else if(!(is >> mHealPercent))
        return false;

    return true;
}

//! \brief Tells whether the other skill is a HealSelf with the same values, the percent included.
bool CreatureSkillHealSelf::isEqual(const CreatureSkill& creatureSkill) const
{
    if(!CreatureSkill::isEqual(creatureSkill))
        return false;

    const CreatureSkillHealSelf* skill = dynamic_cast<const CreatureSkillHealSelf*>(&creatureSkill);
    if(skill == nullptr)
        return false;

    if(mCreatureLevelMin != skill->mCreatureLevelMin)
        return false;
    if(mEffectDuration != skill->mEffectDuration)
        return false;
    if(mEffectValue != skill->mEffectValue)
        return false;
    if(mHealPercent != skill->mHealPercent)
        return false;

    return true;
}
