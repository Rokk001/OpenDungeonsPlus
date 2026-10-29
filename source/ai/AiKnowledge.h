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

#ifndef AIKNOWLEDGE_H
#define AIKNOWLEDGE_H

class GameMap;
class Seat;
class Tile;

//! \brief What one AI seat knows of the map. An AI may only read the type, fullness, owner and
//! rooms of a tile (and of the enemy buildings on it) when this class reports the tile as known.
class AiKnowledge
{
public:
    //! \brief Creates the knowledge view of the given seat on the given map. Neither pointer is owned.
    AiKnowledge(GameMap& gameMap, Seat* seat);

    //! \brief True if the seat knows the tile. With fog of war off every tile is known; otherwise
    //! a tile is known when it is owned by the seat or when it was ever in the seat's vision.
    //! \param tile The tile to test. A null tile is never known.
    bool isKnown(Tile* tile) const;

private:
    GameMap& mGameMap;
    Seat* mSeat;
};

#endif // AIKNOWLEDGE_H
