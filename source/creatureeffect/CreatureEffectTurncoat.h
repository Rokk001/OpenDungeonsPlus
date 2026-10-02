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

#ifndef CREATUREEFFECTTURNCOAT_H
#define CREATUREEFFECTTURNCOAT_H

#include "creatureeffect/CreatureEffect.h"

//! \brief Marks a creature that was temporarily converted to another seat by the Turncoat spell.
//! When the effect ends, the creature returns to its original seat (unless its seat was changed
//! by something else in the meantime).
class CreatureEffectTurncoat : public CreatureEffect
{
public:
    CreatureEffectTurncoat(int32_t nbTurnsEffect, int originalSeatId, int newSeatId) :
        CreatureEffect(nbTurnsEffect, ""),
        mOriginalSeatId(originalSeatId),
        mNewSeatId(newSeatId)
    {}

    CreatureEffectTurncoat() :
        CreatureEffect(),
        mOriginalSeatId(-1),
        mNewSeatId(-1)
    {}

    virtual ~CreatureEffectTurncoat()
    {}

    virtual const std::string& getEffectName() const override;

    virtual void exportToStream(std::ostream& os) const override;
    virtual bool importFromStream(std::istream& is) override;

    static CreatureEffectTurncoat* load(std::istream& is);

protected:
    virtual void applyEffect(Creature& creature) override;

private:
    int mOriginalSeatId;
    int mNewSeatId;
};

#endif // CREATUREEFFECTTURNCOAT_H
