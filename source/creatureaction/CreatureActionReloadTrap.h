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

#ifndef CREATUREACTIONRELOADTRAP_H
#define CREATUREACTIONRELOADTRAP_H

#include "creatureaction/CreatureAction.h"

class Tile;

//! \brief (worker only) Walks to a trap tile of its seat that used up its shots and arms it again
//! with a short work, for a price per trap type (configuration: TrapReload..., <Trap>ReloadCost).
class CreatureActionReloadTrap : public CreatureAction
{
public:
    CreatureActionReloadTrap(Creature& creature, Tile& tileReload);
    virtual ~CreatureActionReloadTrap();

    CreatureActionType getType() const override
    { return CreatureActionType::reloadTrap; }

    std::function<bool()> action() override;

    static bool handleReloadTrap(Creature& creature, Tile& tileReload, int32_t& workTurns);

    //! \brief Looks for the closest trap tile of the worker's seat that needs a reload and, if there is one the
    //! seat can pay, pushes the action. Returns true if the action was pushed.
    static bool tryStart(Creature& creature);

private:
    Tile& mTileReload;
    int32_t mWorkTurns;
};

#endif // CREATUREACTIONRELOADTRAP_H
