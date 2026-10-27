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

#include "entities/PoolAttendantEntity.h"

#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "rooms/RoomSpa.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/Random.h"
#include "ODApplication.h"

#include <algorithm>
#include <vector>

const std::string PoolAttendantEntity::MESH_NAME = "PoolAttendant";

namespace
{
//! \brief Name of the figure used for the unique entity name when the room name is empty.
const std::string ATTENDANT_FALLBACK_NAME = "PoolAttendant";
//! \brief Sound family of the whistle.
const std::string SOUND_WHISTLE = "Rooms/Spa/Whistle";
//! \brief Length in seconds of each clip of the attendant (all of them are authored with this length).
const double CLIP_SECONDS = 2.0;
//! \brief Height of the top of the seat plate of the chair mesh (SpaChair) above the floor, in tiles.
const double CHAIR_SEAT_HEIGHT = 1.13;
//! \brief Distance in tiles from the middle of the chair tile to the foot of the ladder, which is in front of the chair
//! on the side of the pool (the chair is 0.6 tiles wide).
const double LADDER_FOOT_OFFSET = 0.4;
//! \brief The direction from the chair to the pool: the chair stands on the tile above (y - 1) the first pool tile.
const Ogre::Vector3 TOWARDS_POOL(0.0f, 1.0f, 0.0f);
//! \brief The direction the attendant faces while he climbs the ladder: to the chair, away from the pool.
const Ogre::Vector3 AWAY_FROM_POOL(0.0f, -1.0f, 0.0f);
//! \brief Factor of the parabola that gives the height of a jump: 4 x p x (1 - p) is 1 at the apex.
const Ogre::Real JUMP_ARC_FACTOR = 4.0f;
//! \brief Number of random acts the attendant can play while nobody bathes (towel and doze).
const uint32_t NB_ACTS_WITHOUT_BATHER = 2;
//! \brief Number of random acts when somebody bathes (towel, doze and whistle).
const uint32_t NB_ACTS_WITH_BATHER = 3;
//! \brief Number of the act "towel" in the random draw.
const uint32_t ACT_TOWEL = 0;
//! \brief Number of the act "doze" in the random draw.
const uint32_t ACT_DOZE = 1;

//! \brief Turns a clip of the attendant lasts.
double getClipTurns()
{
    return CLIP_SECONDS * ODApplication::turnsPerSecond;
}

//! \brief Turns that a number of seconds of the configuration last.
//! \param key The key of the [Spa] block with the seconds.
double getConfigTurns(const std::string& key)
{
    return ConfigManager::getSingleton().getRoomConfigDouble(key) * ODApplication::turnsPerSecond;
}
}

PoolAttendantEntity::PoolAttendantEntity(GameMap* gameMap, const std::string& roomName, Ogre::Real rotationAngle) :
    RenderedMovableEntity(gameMap, roomName.empty() ? ATTENDANT_FALLBACK_NAME : roomName + "_" + ATTENDANT_FALLBACK_NAME,
        MESH_NAME, rotationAngle, false),
    mRoom(nullptr),
    mChairTile(nullptr),
    mState(PoolAttendantState::sitting),
    mTurnsLeft(0.0),
    mActTurnsLeft(0.0),
    mCannonballTurnsLeft(0.0),
    mHasPlace(false),
    mPlaceX(0),
    mPlaceY(0),
    mJumpFrom(Ogre::Vector3::ZERO),
    mJumpTo(Ogre::Vector3::ZERO),
    mJumpTurns(0),
    mJumpTurnsLeft(0),
    mJumpElapsed(0.0f)
{
    // The figure starts sitting; a client that sees it later is told this state with the entity
    mPrevAnimationState = PoolAttendantPose::sit;
    mPrevAnimationStateLoop = true;
}

PoolAttendantEntity::PoolAttendantEntity(GameMap* gameMap) :
    RenderedMovableEntity(gameMap),
    mRoom(nullptr),
    mChairTile(nullptr),
    mState(PoolAttendantState::sitting),
    mTurnsLeft(0.0),
    mActTurnsLeft(0.0),
    mCannonballTurnsLeft(0.0),
    mHasPlace(false),
    mPlaceX(0),
    mPlaceY(0),
    mJumpFrom(Ogre::Vector3::ZERO),
    mJumpTo(Ogre::Vector3::ZERO),
    mJumpTurns(0),
    mJumpTurnsLeft(0),
    mJumpElapsed(0.0f)
{
    setMeshName(MESH_NAME);
}

GameEntityType PoolAttendantEntity::getObjectType() const
{
    return GameEntityType::poolAttendantEntity;
}

PoolAttendantEntity* PoolAttendantEntity::spawnOnChair(GameMap* gameMap, RoomSpa* room, Tile* chairTile, Ogre::Real rotationAngle)
{
    if((gameMap == nullptr) || (room == nullptr) || (chairTile == nullptr))
        return nullptr;

    PoolAttendantEntity* attendant = new PoolAttendantEntity(gameMap, room->getName(), rotationAngle);
    attendant->mRoom = room;
    attendant->mChairTile = chairTile;
    attendant->setSeat(room->getSeat());
    attendant->mActTurnsLeft = attendant->rollActTurns();
    attendant->mCannonballTurnsLeft = attendant->rollCannonballTurns();
    attendant->addToGameMap();
    attendant->createMesh();
    attendant->setPosition(attendant->getSeatPosition());
    return attendant;
}

void PoolAttendantEntity::removeFromRoom()
{
    removeFromGameMap();
    deleteYourself();
}

void PoolAttendantEntity::setRoom(RoomSpa* room, Tile* chairTile)
{
    mRoom = room;
    mChairTile = chairTile;
    if(room != nullptr)
        setSeat(room->getSeat());
}

bool PoolAttendantEntity::getPlace(int32_t& x, int32_t& y) const
{
    if(!mHasPlace)
        return false;

    x = mPlaceX;
    y = mPlaceY;
    return true;
}

Ogre::Vector3 PoolAttendantEntity::getSeatPosition() const
{
    if(mChairTile == nullptr)
        return Ogre::Vector3::ZERO;

    return Ogre::Vector3(static_cast<Ogre::Real>(mChairTile->getX()), static_cast<Ogre::Real>(mChairTile->getY()),
        static_cast<Ogre::Real>(CHAIR_SEAT_HEIGHT));
}

Ogre::Vector3 PoolAttendantEntity::getLadderFootPosition() const
{
    if(mChairTile == nullptr)
        return Ogre::Vector3::ZERO;

    return Ogre::Vector3(static_cast<Ogre::Real>(mChairTile->getX()),
        static_cast<Ogre::Real>(mChairTile->getY()) + static_cast<Ogre::Real>(LADDER_FOOT_OFFSET), 0.0f);
}

double PoolAttendantEntity::rollActTurns() const
{
    return Random::Double(getConfigTurns("SpaAttendantActMinSeconds"), getConfigTurns("SpaAttendantActMaxSeconds"));
}

double PoolAttendantEntity::rollCannonballTurns() const
{
    return Random::Double(getConfigTurns("SpaAttendantCannonballMinSeconds"),
        getConfigTurns("SpaAttendantCannonballMaxSeconds"));
}

void PoolAttendantEntity::moveTo(const Ogre::Vector3& position)
{
    setPosition(position);
    if(!getIsOnServerMap())
        return;

    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if((seat->getPlayer() == nullptr) || !seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* notification = new ServerNotification(ServerNotificationType::entityTeleported, seat->getPlayer());
        notification->mPacket << getName() << position;
        ODServer::getSingleton().queueServerNotification(notification);
    }
}

void PoolAttendantEntity::sendJumpNotification()
{
    for(Seat* seat : mSeatsWithVisionNotified)
        sendJumpNotificationTo(seat);
}

void PoolAttendantEntity::sendJumpNotificationTo(Seat* seat)
{
    if((seat->getPlayer() == nullptr) || !seat->getPlayer()->getIsHuman())
        return;

    ServerNotification* notification = new ServerNotification(ServerNotificationType::creatureJump, seat->getPlayer());
    notification->mPacket << getName() << mJumpFrom << mJumpTo << mJumpTurns << mJumpElapsed;
    ODServer::getSingleton().queueServerNotification(notification);
}

void PoolAttendantEntity::fireAddEntity(Seat* seat, bool async, NodeType nt)
{
    RenderedMovableEntity::fireAddEntity(seat, async, nt);

    // The jump that is running is sent after the entity data (queued: the attendant is on the client by then)
    if(isJumping())
        sendJumpNotificationTo(seat);
}

void PoolAttendantEntity::doUpkeep()
{
    if(!getIsOnMap() || !getIsOnServerMap())
        return;

    // Without a room or a chair there is nothing to do (a loaded attendant waits for the room)
    if((mRoom == nullptr) || (mChairTile == nullptr))
        return;

    switch(mState)
    {
        case PoolAttendantState::sitting:
            upkeepSitting();
            break;
        case PoolAttendantState::whistling:
        case PoolAttendantState::towelWaving:
        case PoolAttendantState::dozing:
            upkeepAct();
            break;
        case PoolAttendantState::climbingDown:
        case PoolAttendantState::climbingUp:
            upkeepClimb();
            break;
        case PoolAttendantState::walkingToBoard:
            upkeepWalkToBoard();
            break;
        case PoolAttendantState::jumping:
            upkeepJump();
            break;
        case PoolAttendantState::walkingBack:
            upkeepWalkBack();
            break;
    }
}

void PoolAttendantEntity::upkeepSitting()
{
    mActTurnsLeft -= 1.0;
    mCannonballTurnsLeft -= 1.0;

    // A jump that is due waits for a free place in the pool and tries again in every turn
    if((mCannonballTurnsLeft <= 0.0) && startCannonball())
        return;

    if(mActTurnsLeft <= 0.0)
        startAct();
}

void PoolAttendantEntity::startAct()
{
    const bool canWhistle = mRoom->hasBatherInPool();
    const uint32_t nbActs = canWhistle ? NB_ACTS_WITH_BATHER : NB_ACTS_WITHOUT_BATHER;
    const uint32_t act = Random::Uint(0, nbActs - 1);

    std::string clip;
    if(act == ACT_TOWEL)
    {
        mState = PoolAttendantState::towelWaving;
        clip = PoolAttendantPose::towelWave;
    }
    else if(act == ACT_DOZE)
    {
        mState = PoolAttendantState::dozing;
        clip = PoolAttendantPose::doze;
    }
    else
    {
        mState = PoolAttendantState::whistling;
        clip = PoolAttendantPose::whistle;
        RoomSpa::playSoundAt(mChairTile, SOUND_WHISTLE);
    }

    mTurnsLeft = getClipTurns();
    setAnimationState(clip, false, Ogre::Vector3::ZERO, false);
}

void PoolAttendantEntity::upkeepAct()
{
    mTurnsLeft -= 1.0;
    if(mTurnsLeft > 0.0)
        return;

    // The act is over: back to sitting, the next act is counted from now
    mState = PoolAttendantState::sitting;
    mActTurnsLeft = rollActTurns();
    setAnimationState(PoolAttendantPose::sit, true, Ogre::Vector3::ZERO, false);
}

bool PoolAttendantEntity::startCannonball()
{
    if(mRoom->getSpringboardTile() == nullptr)
        return false;

    int32_t x = 0;
    int32_t y = 0;
    if(!mRoom->findAttendantPlace(x, y))
        return false;

    mHasPlace = true;
    mPlaceX = x;
    mPlaceY = y;
    startClimb(true);
    return true;
}

void PoolAttendantEntity::startClimb(bool down)
{
    mState = down ? PoolAttendantState::climbingDown : PoolAttendantState::climbingUp;
    mTurnsLeft = getClipTurns();
    setAnimationState(PoolAttendantPose::climb, true, AWAY_FROM_POOL, false);
}

void PoolAttendantEntity::placeOnLadder(double progress)
{
    const double clamped = std::min(1.0, std::max(0.0, progress));
    const Ogre::Vector3 seatPosition = getSeatPosition();
    const Ogre::Vector3 footPosition = getLadderFootPosition();
    moveTo(seatPosition + (footPosition - seatPosition) * static_cast<Ogre::Real>(clamped));
}

void PoolAttendantEntity::upkeepClimb()
{
    mTurnsLeft -= 1.0;
    const double done = 1.0 - mTurnsLeft / getClipTurns();

    // The way from the seat to the foot of the ladder is 0 to 1; the climb up goes it backwards
    const bool down = (mState == PoolAttendantState::climbingDown);
    placeOnLadder(down ? done : 1.0 - done);
    if(mTurnsLeft > 0.0)
        return;

    if(down)
        startWalkToBoard();
    else
        sitDown();
}

void PoolAttendantEntity::startWalkToBoard()
{
    Tile* board = mRoom->getSpringboardTile();
    if(board == nullptr)
    {
        abortToChair();
        return;
    }

    mState = PoolAttendantState::walkingToBoard;
    std::vector<Ogre::Vector2> path;
    path.push_back(Ogre::Vector2(static_cast<Ogre::Real>(board->getX()), static_cast<Ogre::Real>(board->getY())));
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::walk_anim, true, false, path, false);
}

void PoolAttendantEntity::upkeepWalkToBoard()
{
    if(isMoving())
        return;

    startJump();
}

void PoolAttendantEntity::startJump()
{
    Tile* board = mRoom->getSpringboardTile();
    if((board == nullptr) || !mHasPlace || !mRoom->isPoolPosition(mPlaceX, mPlaceY))
    {
        abortToChair();
        return;
    }

    // The jump starts on the springboard tile and ends in the middle of the reserved pool tile
    moveTo(Ogre::Vector3(static_cast<Ogre::Real>(board->getX()), static_cast<Ogre::Real>(board->getY()), 0.0f));
    const uint32_t turns = static_cast<uint32_t>(std::max(1.0,
        ConfigManager::getSingleton().getRoomConfigDouble("SpaJumpTurns")));
    mJumpFrom = getPosition();
    mJumpTo = Ogre::Vector3(static_cast<Ogre::Real>(mPlaceX), static_cast<Ogre::Real>(mPlaceY), 0.0f);
    mJumpTurns = turns;
    mJumpTurnsLeft = turns;
    mJumpElapsed = 0.0f;
    mState = PoolAttendantState::jumping;
    clearDestinations(EntityAnimation::jump_anim, false, false);
    sendJumpNotification();
}

void PoolAttendantEntity::upkeepJump()
{
    if(mJumpTurnsLeft > 0)
    {
        --mJumpTurnsLeft;
        mJumpElapsed = static_cast<Ogre::Real>(mJumpTurns - mJumpTurnsLeft);
        RenderedMovableEntity::setPosition(jumpPosition(mJumpFrom, mJumpTo, mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns)));
    }

    if(mJumpTurnsLeft == 0)
        land();
}

void PoolAttendantEntity::land()
{
    if(!mRoom->isPoolPosition(mPlaceX, mPlaceY))
    {
        abortToChair();
        return;
    }

    mRoom->playSplashAt(mPlaceX, mPlaceY);
    startWalkBack();
}

void PoolAttendantEntity::startWalkBack()
{
    mState = PoolAttendantState::walkingBack;
    const Ogre::Vector3 foot = getLadderFootPosition();
    std::vector<Ogre::Vector2> path;
    path.push_back(Ogre::Vector2(foot.x, foot.y));
    setWalkPath(EntityAnimation::walk_anim, PoolAttendantPose::climb, true, false, path, false);
}

void PoolAttendantEntity::upkeepWalkBack()
{
    if(isMoving())
        return;

    // He has left the pool: the place is free for the bathers again
    mHasPlace = false;
    startClimb(false);
}

void PoolAttendantEntity::sitDown()
{
    mJumpTurnsLeft = 0;
    mHasPlace = false;
    mState = PoolAttendantState::sitting;
    mActTurnsLeft = rollActTurns();
    mCannonballTurnsLeft = rollCannonballTurns();
    clearDestinations(PoolAttendantPose::sit, true, false);
    moveTo(getSeatPosition());
    setAnimationState(PoolAttendantPose::sit, true, TOWARDS_POOL, false);
}

void PoolAttendantEntity::abortToChair()
{
    sitDown();
}

Ogre::Vector3 PoolAttendantEntity::jumpPosition(const Ogre::Vector3& from, const Ogre::Vector3& to, Ogre::Real progress)
{
    const Ogre::Real clamped = std::min(1.0f, std::max(0.0f, progress));
    Ogre::Vector3 position = from + (to - from) * clamped;
    const Ogre::Real height = static_cast<Ogre::Real>(ConfigManager::getSingleton().getRoomConfigDouble("SpaJumpHeight"));
    position.z += height * JUMP_ARC_FACTOR * clamped * (1.0f - clamped);
    return position;
}

void PoolAttendantEntity::startJumpFromServer(const Ogre::Vector3& from, const Ogre::Vector3& to, uint32_t turns, Ogre::Real elapsed)
{
    mJumpFrom = from;
    mJumpTo = to;
    mJumpTurns = std::max<uint32_t>(1, turns);
    mJumpElapsed = elapsed;
    mJumpTurnsLeft = 1;
    setAnimationState(EntityAnimation::jump_anim, false, Ogre::Vector3::ZERO, false);
    RenderedMovableEntity::setPosition(jumpPosition(from, to, elapsed / static_cast<Ogre::Real>(mJumpTurns)));
    // A jump that is already running (loaded game, seat that gains sight) shows the clip at the phase of the arc
    if((getAnimationState() != nullptr) && (getAnimationState()->getAnimationName() == EntityAnimation::jump_anim))
        getAnimationState()->setTimePosition(static_cast<Ogre::Real>(CLIP_SECONDS) * elapsed / static_cast<Ogre::Real>(mJumpTurns));
}

void PoolAttendantEntity::update(Ogre::Real timeSinceLastFrame)
{
    RenderedMovableEntity::update(timeSinceLastFrame);
    if(getIsOnServerMap() || (mJumpTurnsLeft == 0))
        return;

    mJumpElapsed = std::min(static_cast<Ogre::Real>(mJumpTurns), mJumpElapsed +
        static_cast<Ogre::Real>(ODApplication::turnsPerSecond * timeSinceLastFrame * getGameMap()->getGameSpeedFactor()));
    RenderedMovableEntity::setPosition(jumpPosition(mJumpFrom, mJumpTo, mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns)));
    if((getAnimationState() != nullptr) && (getAnimationState()->getAnimationName() == EntityAnimation::jump_anim))
        getAnimationState()->setTimePosition(static_cast<Ogre::Real>(CLIP_SECONDS) * mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns));
    if(mJumpElapsed >= static_cast<Ogre::Real>(mJumpTurns))
        mJumpTurnsLeft = 0;
}

void PoolAttendantEntity::setPosition(const Ogre::Vector3& position, GameMap* gameMap)
{
    // An authoritative position (a teleport of the server) cancels the cosmetic jump a client is showing
    if(!getIsOnServerMap())
        mJumpTurnsLeft = 0;

    RenderedMovableEntity::setPosition(position, gameMap);
}

void PoolAttendantEntity::exportSaveData(PoolAttendantSave& save) const
{
    const Ogre::Vector3 position = getPosition();
    save.mX = static_cast<double>(position.x);
    save.mY = static_cast<double>(position.y);
    save.mState = mState;
    if(mState == PoolAttendantState::sitting)
        save.mTurnsLeft = mActTurnsLeft;
    else if(mState == PoolAttendantState::jumping)
        save.mTurnsLeft = static_cast<double>(mJumpTurnsLeft);
    else
        save.mTurnsLeft = mTurnsLeft;
    save.mHasCannonball = true;
    save.mCannonballTurnsLeft = mCannonballTurnsLeft;
    save.mHasPlace = mHasPlace;
    save.mPlaceX = mPlaceX;
    save.mPlaceY = mPlaceY;
    // The clip time the server really reached, so that an act or a climb goes on at the same picture after loading
    save.mHasClipTime = true;
    save.mClipTime = getAnimationTime();
}

void PoolAttendantEntity::restoreFromSave(const PoolAttendantSave& save)
{
    if((mRoom == nullptr) || (mChairTile == nullptr))
        return;

    if(save.mHasCannonball)
        mCannonballTurnsLeft = save.mCannonballTurnsLeft;

    mHasPlace = save.mHasPlace && mRoom->isPoolPosition(save.mPlaceX, save.mPlaceY);
    mPlaceX = save.mPlaceX;
    mPlaceY = save.mPlaceY;
    const Ogre::Vector3 savedPosition(static_cast<Ogre::Real>(save.mX), static_cast<Ogre::Real>(save.mY), 0.0f);

    switch(save.mState)
    {
        case PoolAttendantState::sitting:
            mActTurnsLeft = save.mTurnsLeft;
            // The sit loop goes on at the time that was reached, it does not start again
            if(save.mHasClipTime)
                setAnimationTime(save.mClipTime);
            break;
        case PoolAttendantState::whistling:
            mState = save.mState;
            mTurnsLeft = save.mTurnsLeft;
            setAnimationState(PoolAttendantPose::whistle, false, Ogre::Vector3::ZERO, false);
            // The saved clip time is used; an old save without it gets the time worked out from the turns left
            setAnimationTime(save.mHasClipTime ? save.mClipTime : getClipTurns() - mTurnsLeft);
            break;
        case PoolAttendantState::towelWaving:
            mState = save.mState;
            mTurnsLeft = save.mTurnsLeft;
            setAnimationState(PoolAttendantPose::towelWave, false, Ogre::Vector3::ZERO, false);
            setAnimationTime(save.mHasClipTime ? save.mClipTime : getClipTurns() - mTurnsLeft);
            break;
        case PoolAttendantState::dozing:
            mState = save.mState;
            mTurnsLeft = save.mTurnsLeft;
            setAnimationState(PoolAttendantPose::doze, false, Ogre::Vector3::ZERO, false);
            setAnimationTime(save.mHasClipTime ? save.mClipTime : getClipTurns() - mTurnsLeft);
            break;
        case PoolAttendantState::climbingDown:
        case PoolAttendantState::climbingUp:
        {
            // A climb without its place in the pool is only the way back up
            const bool down = (save.mState == PoolAttendantState::climbingDown);
            if(down && !mHasPlace)
            {
                abortToChair();
                break;
            }
            mState = save.mState;
            mTurnsLeft = save.mTurnsLeft;
            setAnimationState(PoolAttendantPose::climb, true, AWAY_FROM_POOL, false);
            // The clip goes on at the time that was reached, it does not start again
            setAnimationTime(save.mHasClipTime ? save.mClipTime : getClipTurns() - mTurnsLeft);
            const double done = 1.0 - mTurnsLeft / getClipTurns();
            placeOnLadder(down ? done : 1.0 - done);
            break;
        }
        case PoolAttendantState::walkingToBoard:
            if(!mHasPlace)
            {
                abortToChair();
                break;
            }
            moveTo(savedPosition);
            startWalkToBoard();
            // The walk clip goes on at the time that was reached
            if(save.mHasClipTime && (mState == PoolAttendantState::walkingToBoard))
                setAnimationTime(save.mClipTime);
            break;
        case PoolAttendantState::jumping:
        {
            Tile* board = mRoom->getSpringboardTile();
            if(!mHasPlace || (board == nullptr))
            {
                abortToChair();
                break;
            }

            // The arc is worked out again from the springboard and the place; the jump goes on at the saved turn
            startJump();
            const uint32_t turnsLeft = static_cast<uint32_t>(std::max(0.0, save.mTurnsLeft));
            if((mState == PoolAttendantState::jumping) && (turnsLeft > 0) && (turnsLeft < mJumpTurns))
            {
                mJumpTurnsLeft = turnsLeft;
                mJumpElapsed = static_cast<Ogre::Real>(mJumpTurns - mJumpTurnsLeft);
                RenderedMovableEntity::setPosition(jumpPosition(mJumpFrom, mJumpTo, mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns)));
                sendJumpNotification();
            }
            break;
        }
        case PoolAttendantState::walkingBack:
            moveTo(savedPosition);
            startWalkBack();
            // The walk clip goes on at the time that was reached
            if(save.mHasClipTime)
                setAnimationTime(save.mClipTime);
            break;
    }
}

PoolAttendantEntity* PoolAttendantEntity::getPoolAttendantEntityFromPacket(GameMap* gameMap, ODPacket& is)
{
    PoolAttendantEntity* attendant = new PoolAttendantEntity(gameMap);
    attendant->importFromPacket(is);
    return attendant;
}
