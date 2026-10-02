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

#ifndef TRAPLIGHTNING_H
#define TRAPLIGHTNING_H

#include "Trap.h"
#include "traps/TrapType.h"

//! \brief A trap that strikes one enemy creature in range with a lightning bolt. The bolt damages and stuns it.
class TrapLightning : public Trap
{
public:
    TrapLightning(GameMap* gameMap);

    virtual const TrapType getType() const override
    { return TrapType::lightning; }

    virtual bool shoot(Tile* tile) override;
    virtual bool isAttackable(Tile* tile, Seat* seat) const override
    {
        return false;
    }

    virtual bool displayTileMesh() const override
    { return true; }

    //! \brief The trap object covers the whole tile under
    //! but while it built, the ground tile still must be shown.
    virtual bool shouldDisplayGroundTile() const override
    { return true; }

    virtual TrapEntity* getTrapEntity(Tile* tile) override;

    static const TrapType mTrapType;

private:
    //! \brief Range in tiles in which the trap sees its targets
    uint32_t mRange;
    //! \brief How many turns the struck creature stays stunned
    uint32_t mStunTurns;
};

#endif // TRAPLIGHTNING_H
