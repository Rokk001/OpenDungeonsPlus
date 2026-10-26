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

#ifndef CREATUREEFFECTSPEEDCHANGE_H
#define CREATUREEFFECTSPEEDCHANGE_H

#include "creatureeffect/CreatureEffect.h"

//! \brief Maintains a speed contribution and applies equipment resistance to newly inflicted slows.
class CreatureEffectSpeedChange : public CreatureEffect
{
public:
    //! \brief Creates a speed effect whose slowing duration is reduced when it first reaches the wearer.
    CreatureEffectSpeedChange(double nbTurnsEffect, double effectValue, const std::string& particleEffectName) :
        CreatureEffect(nbTurnsEffect, particleEffectName),
        mEffectValue(effectValue),
        mItemResistanceApplied(false)
    {}

    //! \brief Creates a saved effect whose remaining duration already includes item resistance.
    CreatureEffectSpeedChange() :
        CreatureEffect(),
        mEffectValue(0.0),
        mItemResistanceApplied(true)
    {}

    virtual ~CreatureEffectSpeedChange()
    {}

    virtual const std::string& getEffectName() const override;

    virtual void exportToStream(std::ostream& os) const override;
    virtual bool importFromStream(std::istream& is) override;

    static CreatureEffectSpeedChange* load(std::istream& is);

    //! \brief Shortens a newly applied slowing effect by the wearer's Sure Footing.
    void startEffect(Creature& creature) override;

protected:
    //! \brief Maintains this effect's speed factor while the wearer lives.
    virtual void applyEffect(Creature& creature) override;
    virtual void releaseEffect(Creature& creature) override;

private:
    double mEffectValue;
    //! \brief Saved durations are already shortened; loading must not shorten them again.
    bool mItemResistanceApplied;
};

#endif // CREATUREEFFECTSPEEDCHANGE_H
