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

#ifndef CREATUREACTIONCLEANTILE_H
#define CREATUREACTIONCLEANTILE_H

#include "creatureaction/CreatureAction.h"

class Tile;

//! \brief (worker only) Walks to a tile and wipes off what lies there: a pile first, then a blood stain, then the
//! dirt of the floor. Ends when the tile is clean or after CleaningMaxTurnsPerTile turns.
class CreatureActionCleanTile : public CreatureAction
{
public:
    //! \brief Creates the cleaning of the given tile.
    CreatureActionCleanTile(Creature& creature, Tile& tileClean);
    virtual ~CreatureActionCleanTile();

    CreatureActionType getType() const override
    { return CreatureActionType::cleanTile; }

    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction

    //! \brief Returns the tile reserved by this cleaning action.
    Tile& getTileClean() const { return mTileClean; }
    //! \brief Returns whether this action reserved a pile rather than room dirt.
    bool cleansPile() const { return mCleansPile; }

    //! \brief Walks to the tile and does one cleaning step on it per turn.
    //! \param nbTurns The turns this cleaning has been the running action (the walk to the tile does not count).
    //! \param pileTarget Whether the action ends once its pile or vomit is gone.
    //! \return False if the worker did its work this turn, true if the action ended and the next one runs now.
    static bool handleCleanTile(Creature& creature, Tile& tileClean, int32_t nbTurns, bool pileTarget);

private:
    Tile& mTileClean;
    bool mCleansPile;
};

#endif // CREATUREACTIONCLEANTILE_H
