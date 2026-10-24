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

#include "creatureeffect/CreatureEffectSpeedChange.h"

#include "creatureeffect/CreatureEffectManager.h"
#include "entities/Creature.h"
#include "utils/LogManager.h"

static const std::string CreatureEffectSpeedChangeName = "SpeedChange";

namespace
{
class CreatureEffectSpeedChangeFactory : public CreatureEffectFactory
{
    CreatureEffect* createCreatureEffect() const override
    { return new CreatureEffectSpeedChange; }

    const std::string& getCreatureEffectName() const override
    {
        return CreatureEffectSpeedChangeName;
    }
};

// Register the factory
static CreatureEffectRegister reg(new CreatureEffectSpeedChangeFactory);
}

const std::string& CreatureEffectSpeedChange::getEffectName() const
{
    return CreatureEffectSpeedChangeName;
}

//! \brief Keeps the factor of this effect in the speed modifier of the creature (the modifier is the product of the
//! factors of all running speed effects, so effects from different sources add up and end on their own).
void CreatureEffectSpeedChange::applyEffect(Creature& creature)
{
    if(!creature.isAlive())
        return;

    creature.setSpeedContribution(this, mEffectValue);
}

//! \brief Takes only the factor of this effect out of the speed modifier of the creature.
void CreatureEffectSpeedChange::releaseEffect(Creature& creature)
{
    creature.removeSpeedContribution(this);
}

CreatureEffectSpeedChange* CreatureEffectSpeedChange::load(std::istream& is)
{
    CreatureEffectSpeedChange* effect = new CreatureEffectSpeedChange;
    effect->importFromStream(is);
    return effect;
}

void CreatureEffectSpeedChange::exportToStream(std::ostream& os) const
{
    CreatureEffect::exportToStream(os);
    os << "\t" << mEffectValue;
}

bool CreatureEffectSpeedChange::importFromStream(std::istream& is)
{
    if(!CreatureEffect::importFromStream(is))
        return false;
    if(!(is >> mEffectValue))
        return false;

    return true;
}
