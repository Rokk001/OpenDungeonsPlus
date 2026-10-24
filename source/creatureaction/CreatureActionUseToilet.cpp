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

#include "creatureaction/CreatureActionUseToilet.h"

#include "entities/Creature.h"
#include "entities/DirtPileEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomToilet.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

CreatureActionUseToilet::CreatureActionUseToilet(Creature& creature, Tile* seatTile) :
    CreatureAction(creature),
    mSeatTile(seatTile),
    mPhase(Phase::approach),
    mTurnsLeft(0),
    mLastTurn(-1),
    mLeaveTried(false),
    mSeatLost(false)
{
    if(mSeatTile == nullptr)
        return;

    // The seat is reserved at once so that no other creature takes it while this one walks there
    RoomToilet* room = getSeatRoom();
    if((room == nullptr) || !room->reserveTile(mSeatTile, &mCreature))
        mSeatLost = true;
}

CreatureActionUseToilet::~CreatureActionUseToilet()
{
    releaseSeat();
}

std::function<bool()> CreatureActionUseToilet::action() // allowed-lambda: signature required by CreatureAction
{
    return std::bind(&CreatureActionUseToilet::handleUseToilet, this);
}

bool CreatureActionUseToilet::isExemptRoomType(const Room* room)
{
    if(room == nullptr)
        return false;

    RoomType type = room->getType();
    return (type == RoomType::treasury) || (type == RoomType::dungeonTemple) || (type == RoomType::temple);
}

RoomToilet* CreatureActionUseToilet::getSeatRoom() const
{
    if(mSeatTile == nullptr)
        return nullptr;

    Room* room = mSeatTile->getCoveringRoom();
    if((room == nullptr) || (room->getType() != RoomType::toilet))
        return nullptr;

    return static_cast<RoomToilet*>(room);
}

void CreatureActionUseToilet::releaseSeat()
{
    RoomToilet* room = getSeatRoom();
    if(room != nullptr)
        room->releaseTile(mSeatTile, &mCreature);
}

void CreatureActionUseToilet::finish()
{
    releaseSeat();
    mCreature.setAnimationState(EntityAnimation::idle_anim, true);
    mCreature.popAction();
}

void CreatureActionUseToilet::startSquat()
{
    mPhase = Phase::squat;
    mTurnsLeft = static_cast<int32_t>(ConfigManager::getSingleton().getDirtConfigDouble("ToiletUseTurns"));
    if(mCreature.isMoving())
        mCreature.clearDestinations(EntityAnimation::relieve_anim, true, false);
    mCreature.setAnimationState(EntityAnimation::relieve_anim, true, Ogre::Vector3::ZERO, false);
}

Tile* CreatureActionUseToilet::findTileOutsideExemptRoom() const
{
    Tile* myTile = mCreature.getPositionTile();
    if(myTile == nullptr)
        return nullptr;

    // The tiles within sight are sorted by distance, so the first one that fits is the nearest
    for(Tile* tile : mCreature.getTilesWithinSightRadius())
    {
        if(tile->isFullTile() || !mCreature.canGoThroughTile(tile))
            continue;

        if(isExemptRoomType(tile->getCoveringRoom()))
            continue;

        if(!mCreature.getGameMap()->pathExists(&mCreature, myTile, tile))
            continue;

        return tile;
    }

    return nullptr;
}

bool CreatureActionUseToilet::handleUseToilet()
{
    Tile* myTile = mCreature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + mCreature.getName());
        mCreature.popAction();
        return true;
    }

    // A gap in the turns means something else (a fight) ran in between: the use starts again
    int64_t turn = mCreature.getGameMap()->getTurnNumber();
    if((mPhase == Phase::squat) && ((mLastTurn < 0) || (turn - mLastTurn > 1)))
        mPhase = Phase::approach;
    mLastTurn = turn;

    if(mSeatTile != nullptr)
        return handleSeat(myTile);

    return handleFloor(myTile);
}

bool CreatureActionUseToilet::handleSeat(Tile* myTile)
{
    // The seat was taken, or the room is gone or was sold
    RoomToilet* room = getSeatRoom();
    if(mSeatLost || (room == nullptr) || !room->reserveTile(mSeatTile, &mCreature))
    {
        finish();
        return true;
    }

    if(mPhase == Phase::approach)
    {
        if((myTile != mSeatTile) || mCreature.isMoving())
        {
            if(!mCreature.setDestination(mSeatTile))
            {
                finish();
                return true;
            }

            return true;
        }

        startSquat();
    }

    --mTurnsLeft;
    if(mTurnsLeft > 0)
        return false;

    // Done: the urge is gone and the seat dirties the floor of the room
    mCreature.setUrge(0.0);
    Room::addUseDirt(mCreature, mSeatTile, "ToiletDirtPerUse");
    finish();
    return true;
}

bool CreatureActionUseToilet::handleFloor(Tile* myTile)
{
    if(mPhase == Phase::approach)
    {
        // In a treasury, the dungeon heart room or a temple the creature steps out of the room first
        if(isExemptRoomType(myTile->getCoveringRoom()) && !mLeaveTried)
        {
            mLeaveTried = true;
            Tile* outsideTile = findTileOutsideExemptRoom();
            if((outsideTile != nullptr) && mCreature.setDestination(outsideTile))
                return true;
        }

        startSquat();
    }

    --mTurnsLeft;
    if(mTurnsLeft > 0)
        return false;

    // Done: a pile of the creature's kind stays on the floor until a worker cleans it
    DirtPileEntity::createOnTile(mCreature.getGameMap(), myTile, DirtPileKind::pile,
        mCreature.getDefinition()->getClassName());
    mCreature.setUrge(0.0);

    // A human keeper is told that a creature found no toilet
    Seat* seat = mCreature.getSeat();
    Player* player = (seat == nullptr) ? nullptr : seat->getPlayer();
    if((player != nullptr) && player->getIsHuman())
        player->notifyDirtEvent(Player::DirtEventKind::relieved, "", &mCreature);

    finish();
    return true;
}
