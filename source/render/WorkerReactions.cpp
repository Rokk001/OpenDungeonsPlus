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

#include "render/WorkerReactions.h"

#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntity.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/CosmeticEvent.h"
#include "render/CreatureReactions.h"
#include "render/RenderManager.h"
#include "render/WorkerExtras.h"
#include "utils/Helper.h"

#include <OgreAnimationState.h>
#include <OgreAxisAlignedBox.h>
#include <OgreEntity.h>
#include <OgreSceneManager.h>
#include <OgreSceneNode.h>
#include <OgreVector3.h>

#include <algorithm>
#include <cmath>
#include <map>
#include <random>
#include <vector>

namespace
{

//! Seconds between two looks at the workers
const double TICK_INTERVAL = 0.5;
//! A worker that digs this long without a break is tired
const double EXHAUST_AFTER = 24.0;
//! A break in the digging that is shorter than this does not count as a break
const double DIG_BREAK = 6.0;
//! Seconds between two hit effects of a digger, least and most
const double DIG_HIT_MIN = 2.0;
const double DIG_HIT_MAX = 3.5;
//! Seconds between two claiming reactions of a claimer, least and most
const double CLAIM_MIN = 3.0;
const double CLAIM_MAX = 5.0;
//! A worker that stands idle this long may start a habit
const double IDLE_AFTER = 9.0;
//! Seconds between two repeats of the heavy gait
const double GAIT_INTERVAL = 2.5;
//! Seconds between two looks for enemies and for creatures in the way
const double DANGER_INTERVAL = 1.0;
//! An enemy fighter this close (world units) frightens a worker
const double DANGER_RADIUS = 5.5;
//! A creature this close (world units) in front of a moving worker makes it step aside
const double YIELD_RADIUS = 1.0;
//! Gold from a vein or a defeated enemy is the gold of a pile that appears this lately (seconds) and this close
const double SOURCE_MEMORY = 8.0;
const double LOOT_MEMORY = 25.0;
const double SOURCE_RADIUS = 3.0;
//! The share of the carry capacity that is a big find when it comes in one go
const double BIG_FIND_SHARE = 0.1;
//! The share of the width of a worker that the gold on its body takes
const double GOLD_BODY_WIDTH = 0.6;
//! How often a reaction that did not start is tried again, and for how long
const double RETRY_INTERVAL = 0.7;
const double RETRY_MAX = 4.0;
const size_t MAX_LATER = 64;

const std::string GOLD_BODY_PREFIX = "WorkerGoldBody_";

//! Cosmetic dice of their own: the game logic must not see them
std::mt19937& workerRng()
{
    static std::mt19937 rng(std::random_device{}());
    return rng;
}

double workerRandom(double min, double max)
{
    std::uniform_real_distribution<double> distribution(min, max);
    return distribution(workerRng());
}

bool contains(const std::string& text, const std::string& part)
{
    return text.find(part) != std::string::npos;
}

bool startsWith(const std::string& text, const std::string& prefix)
{
    return text.compare(0, prefix.size(), prefix) == 0;
}

//! What the client remembers of one worker
struct WorkerState
{
    WorkerState() :
        mDigSince(-1.0),
        mDigLast(-1.0),
        mNextHit(0.0),
        mNextClaim(0.0),
        mIdleSince(-1.0),
        mNextGait(0.0),
        mNextDanger(0.0),
        mGold(0),
        mMaxGold(0),
        mGoldLevel(0)
    {}

    //! The animation the worker was told to play last (the one asked for, not a fallback of the model)
    std::string mClip;
    double mDigSince;
    double mDigLast;
    double mNextHit;
    double mNextClaim;
    double mIdleSince;
    double mNextGait;
    double mNextDanger;
    //! The gold on the body as far as the server told, and the most it can carry
    int32_t mGold;
    int32_t mMaxGold;
    //! The model of gold shown on the body (0: none)
    int32_t mGoldLevel;
};

//! A reaction that is shown a bit later
struct LaterReaction
{
    std::string mCreatureName;
    std::string mEventName;
    double mDelay;
    double mWaited;
};

//! A place and a time, remembered for a while
struct Spot
{
    double mX;
    double mY;
    double mTime;
};

std::map<std::string, WorkerState> sStates;
std::vector<LaterReaction> sLater;
//! Where a tile with gold or gems was dug away lately
std::vector<Spot> sVeins;
//! Where a creature died lately
std::vector<Spot> sDeaths;
double sTickTimer = 0.0;

WorkerState& getState(const std::string& name)
{
    return sStates[name];
}

void addSpot(std::vector<Spot>& spots, double x, double y, double now)
{
    Spot spot;
    spot.mX = x;
    spot.mY = y;
    spot.mTime = now;
    spots.push_back(spot);
    if(spots.size() > 32)
        spots.erase(spots.begin());
}

bool isSpotNear(const std::vector<Spot>& spots, double x, double y, double now, double memory)
{
    for(std::vector<Spot>::const_iterator it = spots.begin(); it != spots.end(); ++it)
    {
        if((now - it->mTime) > memory)
            continue;

        double dx = it->mX - x;
        double dy = it->mY - y;
        if(std::sqrt(dx * dx + dy * dy) <= SOURCE_RADIUS)
            return true;
    }
    return false;
}

//! The model of gold that shows how much a worker carries: 0 if none
int32_t goldLevelOf(int32_t gold, int32_t maxGold)
{
    if(gold <= 0)
        return 0;

    if(maxGold <= 0)
        return 1;

    double share = static_cast<double>(gold) / static_cast<double>(maxGold);
    if(share < 0.25)
        return 1;
    if(share < 0.5)
        return 2;
    if(share < 0.8)
        return 3;
    return 4;
}

}

bool WorkerReactions::isActive(const CreatureReactions& reactions)
{
    return (reactions.mMode != CreatureReactions::Mode::off) && reactions.mConfigLoaded;
}

bool WorkerReactions::isWorker(const Creature* creature)
{
    return (creature != nullptr) && (creature->getDefinition() != nullptr) && creature->getDefinition()->isWorker();
}

bool WorkerReactions::show(CreatureReactions& reactions, Creature* creature, const std::string& eventName)
{
    if((creature == nullptr) || !creature->isAlive() || !creature->getIsOnMap())
        return false;

    bool started = reactions.trigger(creature, eventName);
    if(started && (reactions.mMode == CreatureReactions::Mode::full))
        WorkerExtras::playSound(eventName, creature, reactions.mTime);

    return started;
}

void WorkerReactions::later(CreatureReactions& reactions, Creature* creature, const std::string& eventName,
        double delay)
{
    if(!isActive(reactions) || (creature == nullptr) || (sLater.size() >= MAX_LATER))
        return;

    // One waiting reaction of a kind for each creature is enough
    for(std::vector<LaterReaction>::const_iterator it = sLater.begin(); it != sLater.end(); ++it)
    {
        if((it->mCreatureName == creature->getName()) && (it->mEventName == eventName))
            return;
    }

    LaterReaction reaction;
    reaction.mCreatureName = creature->getName();
    reaction.mEventName = eventName;
    reaction.mDelay = delay;
    reaction.mWaited = 0.0;
    sLater.push_back(reaction);
}

void WorkerReactions::processLater(CreatureReactions& reactions)
{
    for(std::vector<LaterReaction>::iterator it = sLater.begin(); it != sLater.end();)
    {
        // The step of this frame is not known here, the retry interval is counted down by update()
        if(it->mDelay > 0.0)
        {
            ++it;
            continue;
        }

        Creature* creature = reactions.mGameMap->getCreature(it->mCreatureName);
        bool done = (creature == nullptr) || !creature->isAlive() || !creature->getIsOnMap() ||
            show(reactions, creature, it->mEventName);
        if(!done)
        {
            it->mWaited += RETRY_INTERVAL;
            done = (it->mWaited >= RETRY_MAX);
            it->mDelay = RETRY_INTERVAL;
        }

        if(done)
            it = sLater.erase(it);
        else
            ++it;
    }
}

void WorkerReactions::noteAnimation(CreatureReactions& reactions, Creature* creature, const std::string& clip)
{
    if(!isActive(reactions))
        return;

    double now = reactions.mTime;
    if((clip == "Die") || (clip == "die"))
    {
        addSpot(sDeaths, creature->getPosition().x, creature->getPosition().y, now);

        // A worker that dies with gold on its body loses a cloud of coins where it falls (the gold itself is
        // dropped by the server as before)
        std::map<std::string, WorkerState>::iterator itDead = sStates.find(creature->getName());
        if(isWorker(creature) && (itDead != sStates.end()) && (itDead->second.mGold > 0))
        {
            itDead->second.mGold = 0;
            if(reactions.isCreatureNearCamera(creature) && reactions.trigger(creature, "WorkerDeathCoins", true) &&
               (reactions.mMode == CreatureReactions::Mode::full))
                WorkerExtras::playSound("WorkerDeathCoins", creature, now);
        }
        return;
    }

    if(!isWorker(creature))
        return;

    WorkerState& state = getState(creature->getName());
    state.mClip = clip;

    if(clip == "Claim")
    {
        state.mNextClaim = now + workerRandom(CLAIM_MIN, CLAIM_MAX);
        later(reactions, creature, "ClaimStomp", 0.4);
    }
    else if(startsWith(clip, "Attack") && !creature->isInContainment())
    {
        // The workers dig and claim with the attack animation when their model has no animation of its own: it is
        // a fight only if an enemy fighter is close
        Ogre::Vector3 position = creature->getPosition();
        for(Creature* other : reactions.mGameMap->getCreatures())
        {
            if((other == creature) || !other->getIsOnMap() || !other->isAlive() || isWorker(other) ||
               other->getSeat()->isAlliedSeat(creature->getSeat()))
            {
                continue;
            }

            Ogre::Vector3 difference = other->getPosition() - position;
            difference.z = 0.0f;
            if(difference.length() <= 3.0)
            {
                later(reactions, creature, "WorkerWeakFight", 0.1);
                break;
            }
        }
    }
}

void WorkerReactions::noteCosmeticEvent(CreatureReactions& reactions, const CosmeticEvent& event)
{
    if(!isActive(reactions))
        return;

    double now = reactions.mTime;
    Creature* worker = reactions.mGameMap->getCreature(event.mSubject);
    if(!isWorker(worker))
        return;

    if(event.is(CosmeticEventType::digFinished))
    {
        TileType type = static_cast<TileType>(event.mValue);
        std::string eventName;
        if(type == TileType::dirt)
            eventName = "DigFinishDirt";
        else if(type == TileType::rock)
            eventName = "DigFinishRock";
        else if(type == TileType::gold)
            eventName = "DigFinishGold";
        else if(type == TileType::gem)
            eventName = "DigFinishGem";

        if((type == TileType::gold) || (type == TileType::gem))
            addSpot(sVeins, event.mPosition.x, event.mPosition.y, now);

        if(!eventName.empty())
            show(reactions, worker, eventName);
    }
    else if(event.is(CosmeticEventType::carriedGold))
    {
        WorkerState& state = getState(worker->getName());
        int32_t oldGold = state.mGold;
        state.mGold = event.mValue;
        state.mMaxGold = event.mValue2;

        // A big find in one go
        int32_t threshold = static_cast<int32_t>(static_cast<double>(std::max(event.mValue2, 1)) * BIG_FIND_SHARE);
        if((event.mValue - oldGold) >= std::max(threshold, 1))
            later(reactions, worker, "GoldCheer", 0.4);
        // The gold is gone but not put into a treasury: it was thrown off
        else if((event.mValue == 0) && (oldGold > 0) && (reactions.getRoomName(worker) != "Treasury"))
            later(reactions, worker, "GoldCloud", 0.1);
    }
}

void WorkerReactions::noteCarry(CreatureReactions& reactions, Creature* carrier, GameEntity* carried)
{
    if(!isActive(reactions) || !isWorker(carrier))
        return;

    double now = reactions.mTime;
    GameEntityType type = carried->getObjectType();
    if(type == GameEntityType::treasuryObject)
    {
        Ogre::Vector3 position = carried->getPosition();
        if(isSpotNear(sVeins, position.x, position.y, now, SOURCE_MEMORY))
            show(reactions, carrier, "PickGoldVein");
        else if(isSpotNear(sDeaths, position.x, position.y, now, LOOT_MEMORY))
            show(reactions, carrier, "PickGoldLoot");
        else
            show(reactions, carrier, "PickGoldFloor");
    }
    else if(type == GameEntityType::creature)
    {
        Creature* body = static_cast<Creature*>(carried);
        show(reactions, carrier, body->isAlive() ? "PickPrisoner" : "PickBody");
        if(body->isAlive())
            WorkerExtras::startStruggle(reactions.mGameMap, carrier, body);
    }
    else if((type == GameEntityType::craftedTrap) || (type == GameEntityType::giftBoxEntity) ||
            (type == GameEntityType::skillEntity))
    {
        show(reactions, carrier, "PickItem");
    }
}

void WorkerReactions::noteRelease(CreatureReactions& reactions, Creature* carrier, GameEntity* carried)
{
    if(!isActive(reactions) || !isWorker(carrier))
        return;

    std::string room = reactions.getRoomName(carrier);
    GameEntityType type = carried->getObjectType();
    if(type == GameEntityType::treasuryObject)
    {
        if(room == "Treasury")
        {
            later(reactions, carrier, "TreasuryToss", 0.3);
            later(reactions, carrier, "TreasurySmooth", 3.5);
        }
    }
    else if(type == GameEntityType::creature)
    {
        Creature* body = static_cast<Creature*>(carried);
        WorkerExtras::endStruggle(reactions.mGameMap, body->getName());
        if(body->isAlive() && ((room == "Prison") || (room == "Torture")))
            later(reactions, carrier, "PrisonerShove", 0.1);
        else if(!body->isAlive() && (room == "Crypt"))
            later(reactions, carrier, "CorpseLookBack", 0.6);
    }
    else if((type == GameEntityType::craftedTrap) || (type == GameEntityType::giftBoxEntity))
    {
        later(reactions, carrier, "TrapKnock", 0.4);
    }
}

void WorkerReactions::noteHandled(CreatureReactions& reactions, Creature* creature)
{
    if(!isActive(reactions) || !isWorker(creature))
        return;

    std::map<std::string, WorkerState>::const_iterator it = sStates.find(creature->getName());
    if((it != sStates.end()) && (it->second.mGold > 0))
        later(reactions, creature, "GoldCloud", 0.15);
}

void WorkerReactions::noteParticleEffect(CreatureReactions& reactions, Creature* creature, const std::string& script)
{
    if(!isActive(reactions) || !isWorker(creature))
        return;

    if(contains(script, "Haste"))
        later(reactions, creature, "WorkerHasty", 1.0);
}

void WorkerReactions::showDigHit(CreatureReactions& reactions, Creature* worker)
{
    Tile* tile = worker->getPositionTile();
    if(tile == nullptr)
        return;

    Player* localPlayer = reactions.mGameMap->getLocalPlayer();

    // The wall that is marked for digging is the one hit. Without a mark (the marks of the others are not known)
    // the first wall around is taken.
    Tile* target = nullptr;
    for(int dx = -1; dx <= 1; ++dx)
    {
        for(int dy = -1; dy <= 1; ++dy)
        {
            Tile* neighbour = reactions.mGameMap->getTile(tile->getX() + dx, tile->getY() + dy);
            if((neighbour == nullptr) || (neighbour->getFullness() <= 0.0))
                continue;

            TileType type = neighbour->getType();
            if((type != TileType::dirt) && (type != TileType::rock) && (type != TileType::gold) &&
               (type != TileType::gem))
            {
                continue;
            }

            if((localPlayer != nullptr) && neighbour->getMarkedForDigging(localPlayer))
            {
                target = neighbour;
                break;
            }

            if(target == nullptr)
                target = neighbour;
        }
    }

    if(target == nullptr)
        return;

    TileType type = target->getType();
    if(type == TileType::gold)
        show(reactions, worker, "DigHitGold");
    else if(type == TileType::gem)
        show(reactions, worker, "DigHitGem");
    else if(type == TileType::rock)
        show(reactions, worker, "DigHitRock");
    else
        show(reactions, worker, "DigHitDirt");
}

void WorkerReactions::showClaim(CreatureReactions& reactions, Creature* worker)
{
    Tile* tile = worker->getPositionTile();
    if(tile == nullptr)
        return;

    bool enemyTile = false;
    bool wall = false;
    for(int dx = -1; dx <= 1; ++dx)
    {
        for(int dy = -1; dy <= 1; ++dy)
        {
            Tile* neighbour = reactions.mGameMap->getTile(tile->getX() + dx, tile->getY() + dy);
            if(neighbour == nullptr)
                continue;

            if(neighbour->getFullness() > 0.0)
            {
                wall = true;
                continue;
            }

            Seat* owner = neighbour->getSeat();
            if((owner != nullptr) && (worker->getSeat() != nullptr) && !worker->getSeat()->isAlliedSeat(owner))
                enemyTile = true;
        }
    }

    if(enemyTile)
        show(reactions, worker, "ClaimStompEnemy");
    else if(wall && tile->isClaimedForSeat(worker->getSeat()))
        show(reactions, worker, "ReinforceWork");
    else
        show(reactions, worker, "ClaimStomp");
}

void WorkerReactions::tickWorker(CreatureReactions& reactions, Creature* worker)
{
    double now = reactions.mTime;
    WorkerState& state = getState(worker->getName());
    GameEntity* carried = worker->getCarriedEntity();
    bool moving = worker->isMoving();
    bool isNear = reactions.isCreatureNearCamera(worker);

    // The gold on the body is kept up to date for every worker, it is cheap
    updateGoldBody(reactions, worker, (carried == nullptr) && !worker->isInContainment());

    if(!isNear)
        return;

    if(state.mClip == "Dig")
    {
        if(state.mDigSince < 0.0)
        {
            state.mDigSince = now;
            state.mNextHit = now + workerRandom(0.5, 1.5);
        }
        state.mDigLast = now;

        if(now >= state.mNextHit)
        {
            state.mNextHit = now + workerRandom(DIG_HIT_MIN, DIG_HIT_MAX);
            showDigHit(reactions, worker);
        }

        if((now - state.mDigSince) >= EXHAUST_AFTER)
        {
            state.mDigSince = now;
            show(reactions, worker, "DigExhausted");
        }
    }
    else if((state.mDigSince >= 0.0) && ((now - state.mDigLast) > DIG_BREAK))
    {
        state.mDigSince = -1.0;
    }

    if((state.mClip == "Claim") && (now >= state.mNextClaim))
    {
        state.mNextClaim = now + workerRandom(CLAIM_MIN, CLAIM_MAX);
        showClaim(reactions, worker);
    }

    // Walking with a load
    if((carried != nullptr) && moving && (now >= state.mNextGait))
    {
        state.mNextGait = now + GAIT_INTERVAL;
        show(reactions, worker, "WorkerHeavyGait");
    }

    // Standing without work
    if((state.mClip == "Idle") && !moving && (carried == nullptr) && !worker->isInContainment())
    {
        if(state.mIdleSince < 0.0)
        {
            state.mIdleSince = now;
        }
        else if((now - state.mIdleSince) >= IDLE_AFTER)
        {
            state.mIdleSince = now;
            show(reactions, worker, "WorkerIdle");
        }
    }
    else
    {
        state.mIdleSince = -1.0;
    }

    if(now < state.mNextDanger)
        return;

    state.mNextDanger = now + DANGER_INTERVAL + workerRandom(0.0, 0.5);
    if(worker->isInContainment())
        return;

    Ogre::Vector3 position = worker->getPosition();
    for(Creature* other : reactions.mGameMap->getCreatures())
    {
        if((other == worker) || !other->getIsOnMap() || !other->isAlive())
            continue;

        Ogre::Vector3 difference = other->getPosition() - position;
        difference.z = 0.0f;
        double distance = difference.length();

        // An enemy fighter close by frightens the worker
        if((distance <= DANGER_RADIUS) && !isWorker(other) && !other->isKo() &&
           !other->getSeat()->isAlliedSeat(worker->getSeat()))
        {
            show(reactions, worker, "WorkerPanic");
            return;
        }

        // Two creatures that walk towards each other in a narrow passage: the worker with the lesser name steps aside
        if(moving && (distance <= YIELD_RADIUS) && other->isMoving() && (worker->getName() < other->getName()) &&
           CreatureReactions::areFacingEachOther(worker, other))
        {
            show(reactions, worker, "WorkerYield");
            return;
        }
    }
}

void WorkerReactions::tick(CreatureReactions& reactions)
{
    // Workers that are gone are forgotten
    for(std::map<std::string, WorkerState>::iterator it = sStates.begin(); it != sStates.end();)
    {
        Creature* creature = reactions.mGameMap->getCreature(it->first);
        if(creature == nullptr)
        {
            removeGoldBody(it->first);
            sStates.erase(it++);
        }
        else
        {
            ++it;
        }
    }

    for(Creature* creature : reactions.mGameMap->getCreatures())
    {
        if(!isWorker(creature) || !creature->getIsOnMap() || !creature->isAlive())
        {
            // A worker that is in the hand or dead shows no gold on its body
            if(isWorker(creature) && (sStates.find(creature->getName()) != sStates.end()))
                updateGoldBody(reactions, creature, false);

            continue;
        }

        tickWorker(reactions, creature);
    }
}

void WorkerReactions::updateGoldBody(CreatureReactions& reactions, Creature* worker, bool visible)
{
    RenderManager* renderManager = RenderManager::getSingletonPtr();
    if((renderManager == nullptr) || (reactions.mMode != CreatureReactions::Mode::full))
    {
        removeGoldBody(worker->getName());
        return;
    }

    std::map<std::string, WorkerState>::iterator itState = sStates.find(worker->getName());
    if(itState == sStates.end())
        return;

    WorkerState& state = itState->second;
    int32_t level = goldLevelOf(state.mGold, state.mMaxGold);
    Ogre::SceneManager* sceneManager = renderManager->getSceneManager();
    std::string entityName = GOLD_BODY_PREFIX + worker->getName();

    if(level == 0)
    {
        removeGoldBody(worker->getName());
        return;
    }

    if((state.mGoldLevel == level) && sceneManager->hasEntity(entityName))
    {
        sceneManager->getEntity(entityName)->setVisible(visible);
        return;
    }

    removeGoldBody(worker->getName());

    Ogre::SceneNode* parent = worker->getEntityNode();
    std::string workerEntityName = worker->getOgreNamePrefix() + worker->getName();
    if((parent == nullptr) || !sceneManager->hasEntity(workerEntityName))
        return;

    Ogre::Entity* workerEntity = sceneManager->getEntity(workerEntityName);
    std::string meshName = "GoldstackLv" + Helper::toString(level) + ".mesh";
    Ogre::Entity* goldEntity = sceneManager->createEntity(entityName, meshName);
    goldEntity->setCastShadows(false);
    goldEntity->setVisible(visible);

    // The gold rests on the back of the worker: as wide as part of the body, its lowest point just inside the top
    Ogre::AxisAlignedBox workerBox = workerEntity->getBoundingBox();
    Ogre::AxisAlignedBox goldBox = goldEntity->getBoundingBox();
    Ogre::Real workerWidth = std::max(workerBox.getMaximum().x - workerBox.getMinimum().x,
        workerBox.getMaximum().y - workerBox.getMinimum().y);
    Ogre::Real goldWidth = std::max(goldBox.getMaximum().x - goldBox.getMinimum().x,
        goldBox.getMaximum().y - goldBox.getMinimum().y);
    Ogre::Real scale = 1.0f;
    if(goldWidth > 0.0001f)
        scale = static_cast<Ogre::Real>(GOLD_BODY_WIDTH) * workerWidth / goldWidth;

    scale = std::min(std::max(scale, 0.05f), 4.0f);
    Ogre::Vector3 goldCenter = (goldBox.getMaximum() + goldBox.getMinimum()) * 0.5f;
    Ogre::Real top = workerBox.getMaximum().z * 0.92f;

    Ogre::SceneNode* node = parent->createChildSceneNode(entityName + "_node");
    node->attachObject(goldEntity);
    node->setScale(scale, scale, scale);
    node->setPosition(-goldCenter.x * scale, -goldCenter.y * scale, top - goldBox.getMinimum().z * scale);

    state.mGoldLevel = level;
}

void WorkerReactions::removeGoldBody(const std::string& workerName)
{
    std::map<std::string, WorkerState>::iterator itState = sStates.find(workerName);
    if(itState != sStates.end())
        itState->second.mGoldLevel = 0;

    RenderManager* renderManager = RenderManager::getSingletonPtr();
    if(renderManager == nullptr)
        return;

    Ogre::SceneManager* sceneManager = renderManager->getSceneManager();
    std::string entityName = GOLD_BODY_PREFIX + workerName;
    if(sceneManager->hasEntity(entityName))
    {
        Ogre::Entity* entity = sceneManager->getEntity(entityName);
        if(entity->getParentSceneNode() != nullptr)
            entity->detachFromParent();

        sceneManager->destroyEntity(entity);
    }

    std::string nodeName = entityName + "_node";
    if(sceneManager->hasSceneNode(nodeName))
        sceneManager->destroySceneNode(nodeName);
}

void WorkerReactions::removeAllGoldBodies()
{
    std::vector<std::string> names;
    for(std::map<std::string, WorkerState>::const_iterator it = sStates.begin(); it != sStates.end(); ++it)
        names.push_back(it->first);

    for(const std::string& name : names)
        removeGoldBody(name);
}

void WorkerReactions::update(CreatureReactions& reactions, double timeSinceLastFrame)
{
    if(!isActive(reactions))
    {
        WorkerExtras::update(reactions.mGameMap, timeSinceLastFrame, false);
        if(!sStates.empty() || !sLater.empty())
            stopAll(reactions);

        return;
    }

    // The carried prisoners struggle in the full mode only
    WorkerExtras::update(reactions.mGameMap, timeSinceLastFrame, reactions.mMode == CreatureReactions::Mode::full);

    for(std::vector<LaterReaction>::iterator it = sLater.begin(); it != sLater.end(); ++it)
        it->mDelay -= timeSinceLastFrame;

    processLater(reactions);

    sTickTimer += timeSinceLastFrame;
    if(sTickTimer >= TICK_INTERVAL)
    {
        sTickTimer = 0.0;
        tick(reactions);
    }

    double now = reactions.mTime;
    while(!sVeins.empty() && ((now - sVeins.front().mTime) > SOURCE_MEMORY))
        sVeins.erase(sVeins.begin());

    while(!sDeaths.empty() && ((now - sDeaths.front().mTime) > LOOT_MEMORY))
        sDeaths.erase(sDeaths.begin());
}

void WorkerReactions::stopAll(CreatureReactions& reactions)
{
    WorkerExtras::stopAll(reactions.mGameMap);
    removeAllGoldBodies();
    sStates.clear();
    sLater.clear();
    sVeins.clear();
    sDeaths.clear();
    sTickTimer = 0.0;
}
