/*!
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

#include "ai/AiKnowledge.h"

#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"

AiKnowledge::AiKnowledge(GameMap& gameMap, Seat* seat) :
    mGameMap(gameMap),
    mSeat(seat)
{
}

bool AiKnowledge::isKnown(Tile* tile) const
{
    // AI row L03: hard limit, an AI seat reads only tiles it has seen
    if(tile == nullptr)
        return false;

    if(!mGameMap.getIsFOWActivated())
        return true;

    if(tile->getSeat() == mSeat)
        return true;

    if(mGameMap.everVisitedFlagPool == nullptr)
        return false;

    return mGameMap.everVisitedFlagPool[tile->getX()][tile->getY()][mSeat->getId()];
}
