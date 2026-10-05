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

#include "render/WorkerExtras.h"

#include "entities/Creature.h"
#include "gamemap/GameMap.h"
#include "sound/SoundEffectsManager.h"

#include <OgreMath.h>
#include <OgreQuaternion.h>
#include <OgreSceneNode.h>
#include <OgreVector3.h>

#include <algorithm>
#include <cmath>
#include <map>
#include <random>
#include <vector>

namespace
{

const double PI_VALUE = 3.14159265358979323846;
//! Least time (seconds) between two worker sounds
const double SOUND_INTERVAL = 0.1;
//! How far the carried body moves (node units) and how far it tilts (radians) at full strength
const double STRUGGLE_SWAY = 0.05;
const double STRUGGLE_BOB = 0.07;
const double STRUGGLE_TILT = 0.45;
//! Seconds between two changes of strength and beat, least and most
const double RETARGET_MIN = 0.8;
const double RETARGET_MAX = 2.2;
//! Beat of the struggling (radians per second), least and most
const double BEAT_MIN = 7.0;
const double BEAT_MAX = 17.0;
//! How fast strength and beat follow their new values (per second)
const double FOLLOW_SPEED = 3.0;

//! Cosmetic dice of their own: the game logic must not see them
std::mt19937& extrasRng()
{
    static std::mt19937 rng(std::random_device{}());
    return rng;
}

double extrasRandom(double min, double max)
{
    std::uniform_real_distribution<double> distribution(min, max);
    return distribution(extrasRng());
}

//! What the client remembers of one body that is carried and struggles
struct Struggle
{
    Struggle() :
        mApplied(false),
        mRetarget(0.0),
        mStrength(0.0),
        mStrengthTarget(0.0),
        mBeat(BEAT_MIN),
        mBeatTarget(BEAT_MIN),
        mPhaseBob(0.0),
        mPhaseSway(0.0),
        mPhaseTilt(0.0)
    {}

    std::string mCarrierName;
    //! The node was moved by us at least once, the following four fields are valid
    bool mApplied;
    Ogre::Vector3 mBasePosition;
    Ogre::Quaternion mBaseOrientation;
    //! What we left in the node the last time, to see whether someone else changed it since
    Ogre::Vector3 mLastPosition;
    Ogre::Quaternion mLastOrientation;
    double mRetarget;
    double mStrength;
    double mStrengthTarget;
    double mBeat;
    double mBeatTarget;
    double mPhaseBob;
    double mPhaseSway;
    double mPhaseTilt;
};

std::map<std::string, Struggle> sStruggles;
double sLastSound = -1000.0;

//! True if the node still is the way the struggling left it
bool isUntouched(const Ogre::SceneNode* node, const Struggle& struggle)
{
    return ((node->getPosition() - struggle.mLastPosition).squaredLength() < 0.00000001) &&
        node->getOrientation().equals(struggle.mLastOrientation, Ogre::Radian(0.001f));
}

//! Puts the node of the body back the way it was before the struggling, as far as nobody else changed it meanwhile
void restoreBody(GameMap* gameMap, const std::string& bodyName, const Struggle& struggle)
{
    if(!struggle.mApplied)
        return;

    Creature* body = gameMap->getCreature(bodyName);
    if(body == nullptr)
        return;

    // Position and turn are put back each on its own: when the body is put down the game sets its position
    Ogre::SceneNode* node = body->getEntityNode();
    if(node == nullptr)
        return;

    if((node->getPosition() - struggle.mLastPosition).squaredLength() < 0.00000001)
        node->setPosition(struggle.mBasePosition);

    if(node->getOrientation().equals(struggle.mLastOrientation, Ogre::Radian(0.001f)))
        node->setOrientation(struggle.mBaseOrientation);
}

}

void WorkerExtras::startStruggle(GameMap* gameMap, Creature* carrier, Creature* body)
{
    if((gameMap == nullptr) || (carrier == nullptr) || (body == nullptr) || !body->isAlive())
        return;

    endStruggle(gameMap, body->getName());

    Struggle struggle;
    struggle.mCarrierName = carrier->getName();
    struggle.mPhaseBob = extrasRandom(0.0, 2.0 * PI_VALUE);
    struggle.mPhaseSway = extrasRandom(0.0, 2.0 * PI_VALUE);
    struggle.mPhaseTilt = extrasRandom(0.0, 2.0 * PI_VALUE);
    struggle.mBeat = extrasRandom(BEAT_MIN, BEAT_MAX);
    struggle.mBeatTarget = struggle.mBeat;
    sStruggles[body->getName()] = struggle;
}

void WorkerExtras::endStruggle(GameMap* gameMap, const std::string& bodyName)
{
    std::map<std::string, Struggle>::iterator it = sStruggles.find(bodyName);
    if(it == sStruggles.end())
        return;

    if(gameMap != nullptr)
        restoreBody(gameMap, bodyName, it->second);

    sStruggles.erase(it);
}

void WorkerExtras::update(GameMap* gameMap, double timeSinceLastFrame, bool enabled)
{
    if(sStruggles.empty())
        return;

    if(!enabled || (gameMap == nullptr))
    {
        stopAll(gameMap);
        return;
    }

    std::vector<std::string> finished;
    for(std::map<std::string, Struggle>::iterator it = sStruggles.begin(); it != sStruggles.end(); ++it)
    {
        Struggle& struggle = it->second;
        Creature* body = gameMap->getCreature(it->first);
        Creature* carrier = gameMap->getCreature(struggle.mCarrierName);
        Ogre::SceneNode* node = (body == nullptr) ? nullptr : body->getEntityNode();
        if((body == nullptr) || (node == nullptr) || !body->isAlive() || (carrier == nullptr) ||
           (carrier->getCarriedEntity() != body))
        {
            finished.push_back(it->first);
            continue;
        }

        if(!struggle.mApplied)
        {
            struggle.mBasePosition = node->getPosition();
            struggle.mBaseOrientation = node->getOrientation();
            struggle.mLastPosition = struggle.mBasePosition;
            struggle.mLastOrientation = struggle.mBaseOrientation;
            struggle.mApplied = true;
        }
        else if(!isUntouched(node, struggle))
        {
            // Someone else moved the body: it is theirs now, we let go of it
            struggle.mApplied = false;
            finished.push_back(it->first);
            continue;
        }

        // Strength and beat change by chance now and then: a quiet moment, a heave, a fit of shaking
        struggle.mRetarget -= timeSinceLastFrame;
        if(struggle.mRetarget <= 0.0)
        {
            struggle.mRetarget = extrasRandom(RETARGET_MIN, RETARGET_MAX);
            struggle.mStrengthTarget = (extrasRandom(0.0, 1.0) < 0.25) ? extrasRandom(0.1, 0.25) :
                extrasRandom(0.5, 1.0);
            struggle.mBeatTarget = extrasRandom(BEAT_MIN, BEAT_MAX);
        }

        double follow = std::min(1.0, timeSinceLastFrame * FOLLOW_SPEED);
        struggle.mStrength += (struggle.mStrengthTarget - struggle.mStrength) * follow;
        struggle.mBeat += (struggle.mBeatTarget - struggle.mBeat) * follow;
        struggle.mPhaseBob += struggle.mBeat * timeSinceLastFrame;
        struggle.mPhaseSway += struggle.mBeat * 0.6 * timeSinceLastFrame;
        struggle.mPhaseTilt += struggle.mBeat * 0.8 * timeSinceLastFrame;

        double strength = struggle.mStrength;
        Ogre::Vector3 offset(
            static_cast<Ogre::Real>(STRUGGLE_SWAY * strength * std::sin(struggle.mPhaseSway)),
            static_cast<Ogre::Real>(STRUGGLE_SWAY * 0.6 * strength * std::sin(struggle.mPhaseSway * 0.7 + 1.0)),
            static_cast<Ogre::Real>(STRUGGLE_BOB * strength * std::fabs(std::sin(struggle.mPhaseBob))));
        double tiltX = STRUGGLE_TILT * strength * std::sin(struggle.mPhaseTilt);
        double tiltY = STRUGGLE_TILT * 0.6 * strength * std::sin(struggle.mPhaseTilt * 1.3 + 0.5);
        Ogre::Quaternion tilt = Ogre::Quaternion(Ogre::Radian(static_cast<Ogre::Real>(tiltX)), Ogre::Vector3::UNIT_X) *
            Ogre::Quaternion(Ogre::Radian(static_cast<Ogre::Real>(tiltY)), Ogre::Vector3::UNIT_Y);

        node->setPosition(struggle.mBasePosition + offset);
        node->setOrientation(tilt * struggle.mBaseOrientation);
        struggle.mLastPosition = node->getPosition();
        struggle.mLastOrientation = node->getOrientation();
    }

    for(const std::string& name : finished)
        endStruggle(gameMap, name);
}

void WorkerExtras::stopAll(GameMap* gameMap)
{
    std::vector<std::string> names;
    for(std::map<std::string, Struggle>::const_iterator it = sStruggles.begin(); it != sStruggles.end(); ++it)
        names.push_back(it->first);

    for(const std::string& name : names)
        endStruggle(gameMap, name);

    sStruggles.clear();
    sLastSound = -1000.0;
}

std::string WorkerExtras::getSoundFamily(const std::string& eventName)
{
    static const std::string PREFIX = "Creatures/Worker/";
    if((eventName == "DigHitDirt") || (eventName == "DigFinishDirt"))
        return PREFIX + "DigDirt";
    if((eventName == "DigHitRock") || (eventName == "DigFinishRock"))
        return PREFIX + "DigRock";
    if((eventName == "DigHitGold") || (eventName == "DigFinishGold"))
        return PREFIX + "DigGold";
    if((eventName == "DigHitGem") || (eventName == "DigFinishGem"))
        return PREFIX + "DigGem";
    if((eventName == "GoldCloud") || (eventName == "TreasuryToss") || (eventName == "WorkerDeathCoins"))
        return PREFIX + "CoinJingle";
    if((eventName == "ClaimStomp") || (eventName == "ClaimStompEnemy"))
        return PREFIX + "Stomp";
    if((eventName == "ReinforceWork") || (eventName == "TrapKnock"))
        return PREFIX + "Knock";
    if(eventName == "GoldCheer")
        return PREFIX + "Cheer";

    return std::string();
}

void WorkerExtras::playSound(const std::string& eventName, const Creature* creature, double now)
{
    if((creature == nullptr) || (SoundEffectsManager::getSingletonPtr() == nullptr))
        return;

    std::string family = getSoundFamily(eventName);
    if(family.empty() || ((now - sLastSound) < SOUND_INTERVAL))
        return;

    sLastSound = now;
    Ogre::Vector3 position = creature->getPosition();
    SoundEffectsManager::getSingleton().playSpatialSound(family, static_cast<float>(position.x),
        static_cast<float>(position.y));
}
