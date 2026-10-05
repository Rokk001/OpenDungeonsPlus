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

#include "render/RoomAmbienceExtras.h"

#include "entities/Creature.h"
#include "entities/CreatureMoodValues.h"
#include "entities/GameEntityType.h"
#include "entities/RenderedMovableEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODClient.h"
#include "render/RoomAmbience.h"

#include <algorithm>
#include <cmath>

namespace
{

//! Seconds before a creature can ring the temple bell or flash again
const double CREATURE_EVENT_COOLDOWN = 4.0;
//! A chicken is startled by a hungry creature closer than this (tiles)
const double CHICKEN_FLEE_RADIUS = 2.4;
const double CHICKEN_FLEE_COOLDOWN = 12.0;
//! The rooster crows only when a coop is this close to the camera
const double CROW_DISTANCE = 30.0;
const double CROW_MIN_PAUSE = 55.0;
const double CROW_MAX_PAUSE = 120.0;
//! Below this heart health fraction the heart shows its wounds
const double HEART_HURT_FRACTION = 0.5;

int32_t toTileCoordinate(double value)
{
    return static_cast<int32_t>(std::floor(value + 0.5));
}

} // namespace

RoomAmbienceExtras::RoomAmbienceExtras() :
    mNextCrow(0.0),
    mNextHeartBeat(0.0),
    mGeneration(0),
    mInitialized(false),
    mRandom(54321)
{
}

void RoomAmbienceExtras::reset()
{
    mCreatures.clear();
    mHungryPositions.clear();
    mChickenFlee.clear();
    mNextCrow = 0.0;
    mNextHeartBeat = 0.0;
    mInitialized = false;
}

bool RoomAmbienceExtras::isTempleTile(GameMap* gameMap, const Ogre::Vector3& position) const
{
    Tile* tile = gameMap->getTile(toTileCoordinate(position.x), toTileCoordinate(position.y));
    if(tile == nullptr)
        return false;

    return Tile::tileVisualToString(tile->getTileVisual()) == "templeRoom";
}

void RoomAmbienceExtras::scan(RoomAmbience& ambience, GameMap* gameMap, double clock, const Ogre::Vector3& cameraPosition)
{
    if(gameMap == nullptr)
        return;

    ++mGeneration;
    scanCreatures(ambience, gameMap, clock);
    scanObjects(ambience, gameMap, clock, cameraPosition);
    mInitialized = true;
}

void RoomAmbienceExtras::scanCreatures(RoomAmbience& ambience, GameMap* gameMap, double clock)
{
    mHungryPositions.clear();
    for(Creature* creature : gameMap->getCreatures())
    {
        if(!creature->getIsOnMap())
            continue;

        uint32_t health = creature->getOverlayHealthValue();
        bool prisoner = (creature->getSeatPrison() != nullptr);
        const Seat* seat = creature->getSeat();
        if((creature->getOverlayMoodValue() & CreatureMoodValues::Hungry) != 0)
            mHungryPositions.push_back(creature->getPosition());

        std::map<std::string, CreatureSnapshot>::iterator it = mCreatures.find(creature->getName());
        if(it == mCreatures.end())
        {
            // A creature seen for the first time only teaches its state
            CreatureSnapshot snapshot;
            snapshot.mHealth = health;
            snapshot.mSeat = seat;
            snapshot.mPrisoner = prisoner;
            snapshot.mGeneration = mGeneration;
            mCreatures.insert(std::make_pair(creature->getName(), snapshot));
            continue;
        }

        CreatureSnapshot& snapshot = it->second;
        snapshot.mGeneration = mGeneration;
        if(mInitialized && ((clock - snapshot.mLastEvent) >= CREATURE_EVENT_COOLDOWN))
        {
            const Ogre::Vector3& position = creature->getPosition();
            if((health < snapshot.mHealth) && isTempleTile(gameMap, position))
            {
                // Getting better in the temple: a bell rings and a ring of light spreads
                snapshot.mLastEvent = clock;
                ambience.triggerEvent("TempleHealed", position, false, "templeRoom");
            }
            else if(snapshot.mPrisoner && !prisoner && (seat != snapshot.mSeat))
            {
                // A prisoner now serves another keeper: it was converted
                snapshot.mLastEvent = clock;
                ambience.triggerEvent("ConvertedFlash", position, false);
            }
        }

        snapshot.mHealth = health;
        snapshot.mSeat = seat;
        snapshot.mPrisoner = prisoner;
    }

    for(std::map<std::string, CreatureSnapshot>::iterator it = mCreatures.begin(); it != mCreatures.end();)
    {
        if(it->second.mGeneration == mGeneration)
            ++it;
        else
            mCreatures.erase(it++);
    }
}

void RoomAmbienceExtras::scanObjects(RoomAmbience& ambience, GameMap* gameMap, double clock,
        const Ogre::Vector3& cameraPosition)
{
    const Player* localPlayer = gameMap->getLocalPlayer();
    const Seat* localSeat = (localPlayer != nullptr) ? localPlayer->getSeat() : nullptr;
    bool heartFound = false;
    bool coopNear = false;
    Ogre::Vector3 coopPosition = Ogre::Vector3::ZERO;
    double coopDistance = CROW_DISTANCE;
    double radiusSquared = CHICKEN_FLEE_RADIUS * CHICKEN_FLEE_RADIUS;

    for(RenderedMovableEntity* entity : gameMap->getRenderedMovableEntities())
    {
        const Ogre::Vector3& position = entity->getPosition();
        if(entity->getObjectType() == GameEntityType::chickenEntity)
        {
            // A chicken that a hungry creature comes close to is startled
            if(!mInitialized || mHungryPositions.empty())
                continue;

            // With cosmetic events the server tells when a chicken really hops (ChickenFlee event)
            if((ODClient::getSingletonPtr() != nullptr) && ODClient::getSingleton().supportsCosmeticEvents())
                continue;

            for(const Ogre::Vector3& hungry : mHungryPositions)
            {
                double dx = hungry.x - position.x;
                double dy = hungry.y - position.y;
                if((dx * dx + dy * dy) > radiusSquared)
                    continue;

                std::map<std::string, double>::iterator fleeIt = mChickenFlee.find(entity->getName());
                if((fleeIt == mChickenFlee.end()) || ((clock - fleeIt->second) >= CHICKEN_FLEE_COOLDOWN))
                {
                    mChickenFlee[entity->getName()] = clock;
                    ambience.triggerEvent("ChickenFlee", position, false);
                }
                break;
            }
            continue;
        }

        const std::string& meshName = entity->getMeshName();
        if((meshName == "ChickenCoop") || (meshName == "ChickenCoopHouse"))
        {
            double distance = (position - cameraPosition).length();
            if(distance < coopDistance)
            {
                coopDistance = distance;
                coopPosition = position;
                coopNear = true;
            }
        }
        else if((meshName == "DungeonTempleObject") && !heartFound && (localSeat != nullptr)
            && (ODClient::getSingletonPtr() != nullptr))
        {
            Tile* tile = gameMap->getTile(toTileCoordinate(position.x), toTileCoordinate(position.y));
            if((tile != nullptr) && (tile->getSeat() == localSeat))
            {
                heartFound = true;
                HeartHealthRing::BadgeState& badge = ODClient::getSingleton().getHeartBadge();
                double fraction = static_cast<double>(badge.mFraction);
                // The beat gets faster the more the heart is hurt, and a bit faster again while it is attacked
                double factor = 1.0 + 1.6 * (1.0 - fraction) + (badge.mGlow ? 0.3 : 0.0);
                ambience.setHeartRateFactor(factor);
                if(mInitialized && (fraction < HEART_HURT_FRACTION) && (clock >= mNextHeartBeat))
                {
                    mNextHeartBeat = clock + 0.7 + 0.8 * fraction;
                    ambience.triggerEvent("HeartHurt", position, false);
                }
            }
        }
    }

    if(!heartFound)
        ambience.setHeartRateFactor(1.0);

    // The rooster crows now and then when the camera is near a hatchery
    if(clock >= mNextCrow)
    {
        if(coopNear && mInitialized)
        {
            std::uniform_real_distribution<double> pause(CROW_MIN_PAUSE, CROW_MAX_PAUSE);
            mNextCrow = clock + pause(mRandom);
            ambience.triggerEvent("RoosterCrow", coopPosition, false);
        }
        else
        {
            mNextCrow = clock + 8.0;
        }
    }
}
