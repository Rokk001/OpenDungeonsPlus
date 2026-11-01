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

#ifndef CREATUREACTIONDIGTILE_H
#define CREATUREACTIONDIGTILE_H

#include "creatureaction/CreatureAction.h"

class Tile;

//! \brief Digs one marked target and retains any hand-drop override.
class CreatureActionDigTile : public CreatureAction
{
public:
    //! \brief Reserves a digging place and records a hand-drop override.
    CreatureActionDigTile(Creature& creature, Tile& tileDig, Tile& tilePos, bool forced = false);
    virtual ~CreatureActionDigTile();

    CreatureActionType getType() const override
    { return CreatureActionType::digTile; }

    //! \brief Advances the digging target while retaining its hand-drop origin.
    std::function<bool()> action() override;

    //! \brief Digs with unchanged timing and reports the actual stroke tile, next worker step and credited gold.
    //! \param forced Whether this target was forced by a hand drop.
    static bool handleDigTile(Creature& creature, Tile& tileDig, Tile& tilePos, bool forced);

private:
    Tile& mTileDig;
    Tile& mTilePos;
    bool mForced;
};

#endif // CREATUREACTIONDIGTILE_H
