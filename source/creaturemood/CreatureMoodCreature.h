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

#ifndef CREATUREMOODCREATURE_H
#define CREATUREMOODCREATURE_H

#include "creaturemood/CreatureMood.h"

#include <string>

class CreatureDefinition;

//! \brief Problem that comes and goes: creatures of a natural enemy class in sight of the creature annoy it, per creature.
class CreatureMoodCreature : public CreatureMood
{
public:
    //! \brief Creates the modifier with empty parameters (they are read from the configuration).
    CreatureMoodCreature() :
        CreatureMood(CreatureMoodKind::ComeAndGo, CreatureMoodColumns::Fall)
    {}

    virtual ~CreatureMoodCreature() {}

    const std::string& getModifierName() const override;

    //! \brief Returns the number of creatures of the natural enemy class in sight of the creature.
    //! \param creature The creature to look at.
    virtual double getAmount(const Creature& creature) const override;

    CreatureMoodCreature* clone() const override;

    virtual bool importFromStream(std::istream& is) override;
    virtual void exportToStream(std::ostream& os) const override;
    virtual void getFormatString(std::string& format) const override;

private:
    //! \brief The class name of the creatures that annoy the creature
    std::string mCreatureClass;
};

#endif // CREATUREMOODCREATURE_H
