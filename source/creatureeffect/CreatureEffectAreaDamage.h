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


#ifndef CREATUREEFFECTAREADAMAGE_H
#define CREATUREEFFECTAREADAMAGE_H

#include "creatureeffect/CreatureEffect.h"

#include <string>

//! \brief A zone of damage around a tile (gas cloud, hail storm). The effect sits on the caster
//! and, every turn while it lasts, hurts every enemy creature of the caster that stands within
//! the radius of the tile. The zone ends when the effect runs out or when the caster dies.
class CreatureEffectAreaDamage : public CreatureEffect
{
public:
    //! \brief Creates a fixed damage effect whose minimum may be supplied separately.
    CreatureEffectAreaDamage(double nbTurnsEffect, int32_t tileX, int32_t tileY, double radius,
            double damagePerTurn, const std::string& particleEffectName) :
        CreatureEffect(nbTurnsEffect, particleEffectName),
        mTileX(tileX),
        mTileY(tileY),
        mRadius(radius),
        mDamagePerTurn(damagePerTurn),
        mDamagePerTurnMin(damagePerTurn)
    {}

    //! \brief Creates an empty effect for loading.
    CreatureEffectAreaDamage() :
        CreatureEffect(),
        mTileX(0),
        mTileY(0),
        mRadius(0.0),
        mDamagePerTurn(0.0),
        mDamagePerTurnMin(0.0)
    {}

    //! \brief Sets the minimum damage used for each application of this effect.
    void setDamageMin(double value) { mDamagePerTurnMin = value; }

    //! \brief Destroys the effect.
    virtual ~CreatureEffectAreaDamage()
    {}

    //! \brief Returns the name under which the effect is registered.
    virtual const std::string& getEffectName() const override;

    //! \brief Writes the effect with both damage endpoints.
    virtual void exportToStream(std::ostream& os) const override;
    //! \brief Reads both endpoints, accepting legacy fixed damage effects.
    virtual bool importFromStream(std::istream& is) override;

    //! \brief Creates the effect from the stream (used when loading a saved game).
    static CreatureEffectAreaDamage* load(std::istream& is);

protected:
    //! \brief Rolls fresh damage for each target and turn with the caster's critical and hero-target item bonuses.
    virtual void applyEffect(Creature& creature) override;

private:
    int32_t mTileX;
    int32_t mTileY;
    double mRadius;
    double mDamagePerTurn;
    //! \brief Minimum damage, retained separately for a fresh roll every application.
    double mDamagePerTurnMin;
};

#endif // CREATUREEFFECTAREADAMAGE_H
