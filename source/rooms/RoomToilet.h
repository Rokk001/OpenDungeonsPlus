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

#ifndef ROOMTOILET_H
#define ROOMTOILET_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

#include <cstdint>
#include <map>
#include <vector>

class Creature;
class Tile;
enum class TileVisual;

//! \brief A room with one toilet seat on every tile. A creature that has to relieve itself reserves a free
//! seat, uses it for a few turns and leaves the room a little dirtier. The creatures do not work in this room:
//! they are sent here by their urge (see CreatureActionSearchToilet and CreatureActionUseToilet).
class RoomToilet: public Room
{
public:
    //! \brief Creates an empty toilet room on the given map.
    RoomToilet(GameMap* gameMap);

    //! \brief Returns the type of this room (RoomType::toilet).
    RoomType getType() const override
    { return mRoomType; }

    //! \brief True when at least one seat of the room is free for the creature.
    bool hasOpenCreatureSpot(Creature* c) override;

    //! \brief Makes sure every covered tile has a toilet seat and removes the seats of tiles the room lost.
    //! Reservations of tiles that are no longer part of the room are dropped.
    void updateActiveSpots(GameMap* gameMap = nullptr) override;

    //! \brief True when the seat on the tile is not reserved by another creature (a reservation also ends after
    //! ToiletUseTurns times ToiletReserveFactor turns without being renewed).
    //! \param tile The tile of the seat.
    //! \param user The creature that wants the seat; its own reservation does not count.
    bool isTileFree(const Tile* tile, const Creature* user) const;

    //! \brief Reserves (or renews the reservation of) the seat on the tile for the creature.
    //! \return False if the tile is not a seat of this room or another creature holds it.
    bool reserveTile(const Tile* tile, const Creature* user);

    //! \brief Drops the reservation of the tile when the given creature holds it.
    void releaseTile(const Tile* tile, const Creature* user);

    //! \brief True when the creature may use the seats of this room: the room belongs to its seat, or its
    //! seat has no toilet room at all (then any toilet room will do).
    bool canBeUsedBy(const Creature& creature) const;

    //! \brief Finds the toilet seat nearest by path that the creature may use and that is free.
    //! \return The tile of the seat, nullptr if there is none or none can be reached.
    static Tile* findFreeToiletTile(Creature& creature);

    //! \brief Tells whether the creature has a toilet room it may use at all (free seats or not).
    static bool hasToiletRoomFor(const Creature& creature);

    //! \brief Finds the tile where a creature waits when every seat is busy: a reachable tile within
    //! ToiletWaitRadius tiles of a toilet room, outside the room when possible.
    //! \param waiting Set to true when the creature already stands within that distance.
    //! \return The tile to walk to, nullptr if there is none or the creature already waits.
    static Tile* findWaitTile(Creature& creature, bool& waiting);

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;

private:
    //! \brief The reservation of a seat.
    struct Reservation
    {
        Reservation() :
            mUser(nullptr),
            mExpireTurn(0)
        {}

        //! The creature that holds the seat; only compared, never dereferenced.
        const Creature* mUser;
        //! First turn on which the reservation no longer counts.
        int64_t mExpireTurn;
    };

    //! \brief Returns the turn on which a reservation made now ends.
    int64_t getReservationEndTurn() const;

    //! \brief The angle (degrees) of the seat on the tile so that its back is at the nearest wall.
    double getSeatAngle(const Tile* tile) const;

    //! \brief The reservations by tile.
    std::map<const Tile*, Reservation> mReserved;
};

#endif // ROOMTOILET_H
