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

#include "creaturemood/CreatureMoodCreature.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "gamemap/GameMap.h"
#include "utils/LogManager.h"

static const std::string CreatureMoodCreatureName = "Creature";

namespace
{
class CreatureMoodCreatureFactory : public CreatureMoodFactory
{
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodCreature; }

    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodCreatureName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodCreatureFactory);
}

const std::string& CreatureMoodCreature::getModifierName() const
{
    return CreatureMoodCreatureName;
}

//! \brief Returns the number of creatures of the natural enemy class in sight of the creature.
double CreatureMoodCreature::getAmount(const Creature& creature) const
{
    std::vector<GameEntity*> alliedCreatures = creature.getGameMap()->getVisibleCreatures(creature.getVisibleTiles(),
        creature.getSeat(), false);
    int nbCreatures = 0;
    for(GameEntity* entity : alliedCreatures)
    {
        if(entity->getObjectType() != GameEntityType::creature)
            continue;

        if(&creature == entity)
            continue;

        Creature* alliedCreature = static_cast<Creature*>(entity);
        if(alliedCreature->getDefinition()->getClassName() != mCreatureClass)
            continue;

        ++nbCreatures;
    }
    return static_cast<double>(nbCreatures);
}

//! \brief Returns a copy of this modifier.
CreatureMoodCreature* CreatureMoodCreature::clone() const
{
    return new CreatureMoodCreature(*this);
}

//! \brief Reads the creature class and then the fall per turn from the configuration stream.
bool CreatureMoodCreature::importFromStream(std::istream& is)
{
    if(!(is >> mCreatureClass))
        return false;

    return CreatureMood::importFromStream(is);
}

//! \brief Writes the creature class and then the fall per turn.
void CreatureMoodCreature::exportToStream(std::ostream& os) const
{
    os << "\t" << mCreatureClass;
    CreatureMood::exportToStream(os);
}

//! \brief Appends the names of the creature class and of the fall column to the format string.
void CreatureMoodCreature::getFormatString(std::string& format) const
{
    if(!format.empty())
        format += "\t";

    format += "CreatureClass";
    CreatureMood::getFormatString(format);
}
