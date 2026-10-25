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

#ifndef CREATUREACTIONUSETOILET_H
#define CREATUREACTIONUSETOILET_H

#include "creatureaction/CreatureAction.h"

#include <cstdint>

class Room;
class RoomToilet;
class Tile;

//! \brief A creature relieves itself. With a seat tile it reserves that seat of a toilet room, walks to it, squats
//! there for ToiletUseTurns turns and leaves the room a little dirtier. Without a seat tile (nullptr) it relieves
//! itself where it stands and leaves a pile on the floor; in a treasury, the dungeon heart room or a temple it
//! first steps out of the room. Either way the urge is 0 afterwards. A fight on top of this action interrupts it:
//! the seat is given back at once (see interrupt) and the urge stays.
class CreatureActionUseToilet : public CreatureAction
{
public:
    //! \brief Creates the action and reserves the seat.
    //! \param creature The creature that has to go.
    //! \param seatTile The tile of the toilet seat to use, nullptr to relieve itself on the spot.
    CreatureActionUseToilet(Creature& creature, Tile* seatTile);

    //! \brief Releases the seat.
    virtual ~CreatureActionUseToilet();

    CreatureActionType getType() const override
    { return CreatureActionType::useToilet; }

    //! \brief Returns the seat tile of this action, nullptr when the creature relieves itself on the floor.
    Tile* getSeatTile() const
    { return mSeatTile; }

    //! \brief Gets the function that runs this action.
    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction

    //! \brief Called when another action (a fight) takes over: gives the seat back at once and starts the use again
    //! when the creature gets control back. The urge stays. Does not touch a seat reserved by somebody else.
    void interrupt();

    //! \brief True for the rooms where a creature must not relieve itself (treasury, dungeon heart room, temple).
    static bool isExemptRoomType(const Room* room);

private:
    //! \brief The steps of the action.
    enum class Phase
    {
        //! Walking to the seat, or (on the floor) getting out of an exempt room.
        approach,
        //! Squatting.
        squat
    };

    //! \brief One turn of the action.
    //! \return True when the creature may go on in the same turn (the action ended or started a walk).
    bool handleUseToilet();

    //! \brief One turn of the use of a toilet seat.
    bool handleSeat(Tile* myTile);

    //! \brief One turn of relieving itself on the floor.
    bool handleFloor(Tile* myTile);

    //! \brief Ends the action: releases the seat, stops the squat and removes the action from the creature.
    //! The action is deleted by this call, so nothing of it may be used afterwards.
    void finish();

    //! \brief Gives the seat back (when the creature holds it).
    void releaseSeat();

    //! \brief Returns the toilet room of the seat tile, nullptr if the tile is no longer part of a toilet room.
    RoomToilet* getSeatRoom() const;

    //! \brief Starts the squat: the animation and the countdown of ToiletUseTurns turns.
    void startSquat();

    //! \brief Finds the nearest reachable tile that is not in an exempt room (nullptr if there is none).
    Tile* findTileOutsideExemptRoom() const;

    //! \brief Tile of the seat, nullptr for the floor.
    Tile* mSeatTile;
    //! \brief Current step.
    Phase mPhase;
    //! \brief Turns of squatting that are left.
    int32_t mTurnsLeft;
    //! \brief The last turn this action ran on; a gap means a fight interrupted it.
    int64_t mLastTurn;
    //! \brief True once the creature tried to step out of an exempt room (it tries only once).
    bool mLeaveTried;
    //! \brief True when the seat could not be reserved.
    bool mSeatLost;
};

#endif // CREATUREACTIONUSETOILET_H
