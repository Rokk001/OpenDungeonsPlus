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

#ifndef CREATUREEFFECTCHICKEN_H
#define CREATUREEFFECTCHICKEN_H

#include "creatureeffect/CreatureEffect.h"

//! \brief Marks a creature that is temporarily turned into a chicken by the Chicken spell.
//! While the effect is active, the creature is harmless (see Creature::isChicken). When it ends,
//! the creature gets its normal form back.
class CreatureEffectChicken : public CreatureEffect
{
public:
    CreatureEffectChicken(int32_t nbTurnsEffect) :
        CreatureEffect(nbTurnsEffect, "")
    {}

    CreatureEffectChicken() :
        CreatureEffect()
    {}

    virtual ~CreatureEffectChicken()
    {}

    virtual const std::string& getEffectName() const override;

    static CreatureEffectChicken* load(std::istream& is);

protected:
    virtual void applyEffect(Creature& creature) override;
};

#endif // CREATUREEFFECTCHICKEN_H
