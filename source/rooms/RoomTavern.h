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

#ifndef ROOMTAVERN_H
#define ROOMTAVERN_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

#include <cstdint>
#include <iosfwd>
#include <string>
#include <vector>

class Creature;
class InnkeeperEntity;
class Tile;
enum class TileVisual;

//! \brief Who pays for the beer a tavern serves. The keeper sets it per tavern.
enum class TavernPayer
{
    //! The beer is paid from the treasuries of the keeper.
    keeper = 0,
    //! The beer is paid from the purse of the creature that drinks it.
    creature = 1
};

//! \brief A room where creatures quench their thirst. The first tile of the room is the counter, where the innkeeper
//! stands; every other tile is a place to drink (one creature per tile), decorated with a keg when it lies next to a
//! wall and with a table otherwise. The drinks and the games of the guests are not part of this class yet: it keeps the
//! room itself (counter, decoration, innkeeper, who pays for the beer) and saves it.
class RoomTavern: public Room
{
public:
    //! \brief Creates an empty tavern on the given map. The beer is paid by the keeper until it is set otherwise.
    RoomTavern(GameMap* gameMap);

    //! \brief Returns the type of this room (RoomType::tavern).
    RoomType getType() const override
    { return mRoomType; }

    //! \brief True when at least one place to drink is free: the tiles of the room without the counter tile, one per
    //! creature using the room.
    bool hasOpenCreatureSpot(Creature* c) override;

    //! \brief Called while a creature uses the room. The drinking and the games are not part of the room yet, so the
    //! creature leaves again at once.
    bool useRoom(Creature& creature, bool forced) override;

    //! \brief Sets the name, seat and tiles. The first tile is the counter tile. A tavern of a seat that is played by
    //! the computer lets the creatures pay for the beer.
    void setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles) override;

    //! \brief Joins an adjacent tavern of the same seat into this room. The room that already has its counter keeps it
    //! (and its payer setting); the innkeeper of the other room goes away.
    void absorbRoom(Room* r) override;

    //! \brief Called on the room the tiles are leaving. The new room gets the payer setting and, when the counter tile
    //! goes over with the tiles, keeps the counter where it was.
    void splitRoom(Room& newRoom, const std::vector<Tile*>& tiles) override;

    //! \brief Removes a tile from the room. A creature drinking on the tile stops (its action queue is cleared); when
    //! the tile was the counter tile, the first remaining tile becomes the counter.
    bool removeCoveredTile(Tile* t) override;

    //! \brief Takes the room off the map together with the innkeeper.
    void removeFromGameMap(GameMap* gameMap = nullptr) override;

    //! \brief Makes sure the counter tile, the decoration of every tile and the innkeeper are right for the tiles the
    //! room covers now: the object of a tile whose kind changed is replaced, the objects of tiles the room lost are
    //! removed and the innkeeper stands on the counter tile (it is spawned again when the counter moved).
    void updateActiveSpots(GameMap* gameMap = nullptr) override;

    //! \brief Writes the room, then the lines TavernPayer, Innkeeper and Counter.
    void exportToStream(std::ostream& os) const override;

    //! \brief Reads the room and the lines written by exportToStream. A save without these lines loads with the beer
    //! paid by the keeper and the counter on the first tile.
    bool importFromStream(std::istream& is) override;

    //! \brief Returns who pays for the beer.
    inline TavernPayer getPayer() const
    { return mPayer; }

    //! \brief Sets who pays for the beer.
    inline void setPayer(TavernPayer payer)
    { mPayer = payer; }

    //! \brief Returns the counter tile, nullptr while the room has no tile.
    inline Tile* getCounterTile() const
    { return mCounterTile; }

    //! \brief Returns the innkeeper (server side), nullptr while it is not on the map.
    inline InnkeeperEntity* getInnkeeper() const
    { return mInnkeeper; }

    //! \brief True when the tile is the counter tile of this room.
    //! \param tile The tile to test.
    inline bool isCounterTile(const Tile* tile) const
    { return (tile != nullptr) && (tile == mCounterTile); }

    //! \brief True when this tavern serves beer: the seat that owns it has researched Beer. Without it only water is
    //! served.
    bool servesBeer() const;

    //! \brief Server side. A drink was served on the tile: the tile gets TavernDirtPerDrink of rooms.cfg (the same for
    //! every creature, no DirtFactor), so the tavern is cleaned by the workers like the other rooms.
    //! \param tile The tile the creature drinks on; nothing happens if it is null.
    static void addDrinkDirt(Tile* tile);

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;

private:
    //! \brief Number of places to drink: the covered tiles without the counter tile.
    uint32_t getNbDrinkingTiles() const;

    //! \brief True when the counter object already stands on the counter tile, which tells an older room that has
    //! been through updateActiveSpots from a room that was only just set up.
    bool hasPlacedCounter() const;

    //! \brief The angle (degrees) of an object on the tile that has its back to the wall, and whether the tile lies
    //! next to a wall at all (a neighbour in the four directions that is not part of this room).
    //! \param tile The tile of the object.
    //! \param isNextToWall Set to true when the tile lies next to a wall.
    //! \return The angle; 0 for a tile that lies next to no wall.
    double getBackToWallAngle(const Tile* tile, bool& isNextToWall) const;

    //! \brief Server side. Removes the innkeeper from the map; does nothing without one.
    void removeInnkeeper();

    //! \brief Server side. Makes sure there is an innkeeper on the counter tile, turned like the counter.
    void placeInnkeeper();

    //! \brief Who pays for the beer.
    TavernPayer mPayer;
    //! \brief The tile with the counter and the innkeeper, nullptr while the room has no tile. Not owned.
    Tile* mCounterTile;
    //! \brief The figure behind the counter (server side only), nullptr while it is not on the map. Not owned: the
    //! entity is removed by removeInnkeeper.
    InnkeeperEntity* mInnkeeper;
};

#endif // ROOMTAVERN_H
