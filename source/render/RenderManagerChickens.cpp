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

// Looks and motion of the hatchery animals on the client: eggs in straw, chicks, the rooster, and the
// straw nests and loose feathers scattered over the hatchery. The egg, chick, rooster and nest have
// meshes of their own (ChickenEgg, ChickenEggCracked, ChickenChick, ChickenRooster, ChickenNest, made in Blender, the
// chick and rooster share the hen skeleton with its clips). The loose feathers are a mesh made in code. The motion
// comes from a pose name that the server sends as animation name (see ChickenPose.h), a little procedural motion is
// added on top.
// Nothing here changes the game state.

#include "render/RenderManager.h"

#include "entities/BuildingObject.h"
#include "entities/ChickenEntity.h"
#include "entities/ChickenPose.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "rooms/HatcheryCoopHouse.h"
#include "rooms/HatcheryNestField.h"
#include "rooms/Room.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

#include <OgreAnimationState.h>
#include <OgreCamera.h>
#include <OgreBone.h>
#include <OgreEntity.h>
#include <OgreManualObject.h>
#include <OgreMesh.h>
#include <OgreMeshManager.h>
#include <OgreParticleSystem.h>
#include <OgreSceneManager.h>
#include <OgreSceneNode.h>
#include <OgreSubEntity.h>
#include <OgreViewport.h>
#include <OgreSkeletonInstance.h>

#include <algorithm>
#include <cmath>

namespace
{
const std::string MeshEggCracked = "ChickenEggCracked";
const std::string MeshNest = "ChickenNest";
const std::string MeshFeathers = "ChickenLooseFeathers";
const std::string MaterialGroup = "Graphics";

//! Small deterministic random numbers so that the meshes look the same every time
class ShapeRandom
{
public:
    ShapeRandom(uint32_t seed) :
        mState(seed)
    {}

    //! A number in [0, 1)
    float next()
    {
        mState = mState * 1664525u + 1013904223u;
        return static_cast<float>((mState >> 8) & 0xFFFF) / 65536.0f;
    }

    //! A number in [-1, 1)
    float nextSigned()
    { return next() * 2.0f - 1.0f; }

private:
    uint32_t mState;
};

void addQuad(Ogre::ManualObject* object, uint32_t& index, const Ogre::Vector3& p0, const Ogre::Vector3& p1,
    const Ogre::Vector3& p2, const Ogre::Vector3& p3, const Ogre::Vector3& normal)
{
    object->position(p0);
    object->normal(normal);
    object->textureCoord(0.0f, 0.0f);
    object->position(p1);
    object->normal(normal);
    object->textureCoord(1.0f, 0.0f);
    object->position(p2);
    object->normal(normal);
    object->textureCoord(1.0f, 1.0f);
    object->position(p3);
    object->normal(normal);
    object->textureCoord(0.0f, 1.0f);
    object->triangle(index, index + 1, index + 2);
    object->triangle(index, index + 2, index + 3);
    index += 4;
}

Ogre::ManualObject* beginShape(Ogre::SceneManager* sceneManager, const std::string& material)
{
    Ogre::ManualObject* object = sceneManager->createManualObject();
    object->begin(material, Ogre::RenderOperation::OT_TRIANGLE_LIST, MaterialGroup);
    return object;
}

void finishShape(Ogre::SceneManager* sceneManager, Ogre::ManualObject* object, const std::string& meshName)
{
    object->convertToMesh(meshName + ".mesh", MaterialGroup);
    sceneManager->destroyManualObject(object);
}

void buildFeathers(Ogre::SceneManager* sceneManager)
{
    Ogre::ManualObject* object = beginShape(sceneManager, "ChickenFeatherDecor");
    uint32_t index = 0;
    ShapeRandom random(5u);
    for(int i = 0; i < 3; ++i)
    {
        const Ogre::Vector3 center(0.12f * random.nextSigned(), 0.12f * random.nextSigned(), 0.004f);
        const float angle = Ogre::Math::TWO_PI * random.next();
        const Ogre::Vector3 direction(std::cos(angle), std::sin(angle), 0.0f);
        const Ogre::Vector3 side(-direction.y, direction.x, 0.0f);
        // A feather is a slim leaf of three pieces that is a little bent
        Ogre::Vector3 previous = center - direction * 0.05f;
        float previousWidth = 0.0f;
        for(int part = 1; part <= 3; ++part)
        {
            const float t = static_cast<float>(part) / 3.0f;
            const float width = 0.012f * std::sin(Ogre::Math::PI * (0.15f + 0.75f * t));
            const Ogre::Vector3 next = center - direction * 0.05f + direction * 0.1f * t + side * 0.01f * t * t;
            addQuad(object, index, previous - side * previousWidth, previous + side * previousWidth,
                next + side * width, next - side * width, Ogre::Vector3::UNIT_Z);
            previous = next;
            previousWidth = width;
        }
    }
    object->end();
    finishShape(sceneManager, object, MeshFeathers);
}

void ensureMesh(Ogre::SceneManager* sceneManager, const std::string& name, void (*build)(Ogre::SceneManager*))
{
    if(Ogre::MeshManager::getSingleton().resourceExists(name + ".mesh", MaterialGroup))
        return;

    build(sceneManager);
}

float configValue(const std::string& key, float defaultValue)
{
    return static_cast<float>(ConfigManager::getSingleton().getRoomConfigDoubleOrDefault(key, defaultValue));
}

//! Poses of the hatchery animals (look only): the numbers of the procedural motion, read once from the room config (HatcheryLook<Name>).
struct ChickenLookSettings
{
    ChickenLookSettings() :
        mCoopCheckSeconds(configValue("HatcheryLookCoopCheckSeconds", 1.5f)),
        mCoopShakeSeconds(configValue("HatcheryLookCoopShakeSeconds", 0.8f)),
        mCoopShakeSwing(configValue("HatcheryLookCoopShakeSwing", 3.0f)),
        mCoopShakeSpeed(configValue("HatcheryLookCoopShakeSpeed", 40.0f)),
        mStrutPitch(configValue("HatcheryLookStrutPitch", -8.0f)),
        mStrutStretchX(configValue("HatcheryLookStrutStretchX", 1.06f)),
        mStrutStretchZ(configValue("HatcheryLookStrutStretchZ", 1.05f)),
        mStrutLift(configValue("HatcheryLookStrutLift", 0.012f)),
        mStrutSpeed(configValue("HatcheryLookStrutSpeed", 9.0f)),
        mRunLift(configValue("HatcheryLookRunLift", 0.022f)),
        mRunLiftSpeed(configValue("HatcheryLookRunLiftSpeed", 16.0f)),
        mRunRoll(configValue("HatcheryLookRunRoll", 6.0f)),
        mRunRollSpeed(configValue("HatcheryLookRunRollSpeed", 8.0f)),
        mRunPitch(configValue("HatcheryLookRunPitch", 14.0f)),
        mRunStretch(configValue("HatcheryLookRunStretch", 0.2f)),
        mRunStretchSpeed(configValue("HatcheryLookRunStretchSpeed", 22.0f)),
        mCrowRamp(configValue("HatcheryLookCrowRamp", 4.0f)),
        mCrowLift(configValue("HatcheryLookCrowLift", 0.01f)),
        mCrowPitch(configValue("HatcheryLookCrowPitch", -38.0f)),
        mCrowStretch(configValue("HatcheryLookCrowStretch", 0.3f)),
        mCrowStretchSpeed(configValue("HatcheryLookCrowStretchSpeed", 14.0f)),
        mCrowStretchHeight(configValue("HatcheryLookCrowStretchHeight", 0.14f)),
        mPerchPitch(configValue("HatcheryLookPerchPitch", -6.0f)),
        mGuardPuff(configValue("HatcheryLookGuardPuff", 1.28f)),
        mGuardPuffWobble(configValue("HatcheryLookGuardPuffWobble", 0.03f)),
        mGuardPuffSpeed(configValue("HatcheryLookGuardPuffSpeed", 20.0f)),
        mGuardWing(configValue("HatcheryLookGuardWing", 0.15f)),
        mGuardWingSpeed(configValue("HatcheryLookGuardWingSpeed", 18.0f)),
        mGuardPitch(configValue("HatcheryLookGuardPitch", 10.0f)),
        mGuardPeckPitch(configValue("HatcheryLookGuardPeckPitch", 24.0f)),
        mGuardPeckSpeed(configValue("HatcheryLookGuardPeckSpeed", 7.0f)),
        mScratchPitch(configValue("HatcheryLookScratchPitch", 14.0f)),
        mScratchSwing(configValue("HatcheryLookScratchSwing", 10.0f)),
        mScratchSpeed(configValue("HatcheryLookScratchSpeed", 12.0f)),
        mScratchLift(configValue("HatcheryLookScratchLift", 0.003f)),
        mFlutterRiseRate(configValue("HatcheryLookFlutterRiseRate", 1.4f)),
        mFlutterLift(configValue("HatcheryLookFlutterLift", 0.14f)),
        mFlutterStretch(configValue("HatcheryLookFlutterStretch", 0.25f)),
        mFlutterSpeed(configValue("HatcheryLookFlutterSpeed", 30.0f)),
        mFlutterPitch(configValue("HatcheryLookFlutterPitch", -10.0f)),
        mFightPuff(configValue("HatcheryLookFightPuff", 1.15f)),
        mFightPuffWobble(configValue("HatcheryLookFightPuffWobble", 0.03f)),
        mFightPuffSpeed(configValue("HatcheryLookFightPuffSpeed", 20.0f)),
        mFightWing(configValue("HatcheryLookFightWing", 0.2f)),
        mFightWingSpeed(configValue("HatcheryLookFightWingSpeed", 19.0f)),
        mFightPitch(configValue("HatcheryLookFightPitch", 12.0f)),
        mFightPitchSwing(configValue("HatcheryLookFightPitchSwing", 16.0f)),
        mFightPitchSpeed(configValue("HatcheryLookFightPitchSpeed", 11.0f)),
        mFightRoll(configValue("HatcheryLookFightRoll", 9.0f)),
        mFightRollSpeed(configValue("HatcheryLookFightRollSpeed", 7.0f)),
        mFightLift(configValue("HatcheryLookFightLift", 0.035f)),
        mFightLiftSpeed(configValue("HatcheryLookFightLiftSpeed", 8.0f)),
        mLayFlatSeconds(configValue("HatcheryLookLayFlatSeconds", 1.2f)),
        mLayStretchX(configValue("HatcheryLookLayStretchX", 1.14f)),
        mLayStretchY(configValue("HatcheryLookLayStretchY", 1.1f)),
        mLayStretchZ(configValue("HatcheryLookLayStretchZ", 0.78f)),
        mLayWobble(configValue("HatcheryLookLayWobble", 0.03f)),
        mLayWobbleSpeed(configValue("HatcheryLookLayWobbleSpeed", 25.0f)),
        mLayRiseStretch(configValue("HatcheryLookLayRiseStretch", 1.12f)),
        mCackleRoll(configValue("HatcheryLookCackleRoll", 9.0f)),
        mCackleRollSpeed(configValue("HatcheryLookCackleRollSpeed", 28.0f)),
        mCackleLift(configValue("HatcheryLookCackleLift", 0.025f)),
        mCackleLiftSpeed(configValue("HatcheryLookCackleLiftSpeed", 11.0f)),
        mMountPitch(configValue("HatcheryLookMountPitch", 40.0f)),
        mMountLift(configValue("HatcheryLookMountLift", 0.07f)),
        mMountSpeed(configValue("HatcheryLookMountSpeed", 8.0f)),
        mMountBurstSeconds(configValue("HatcheryLookMountBurstSeconds", 1.0f)),
        mMountClimbSeconds(configValue("HatcheryLookMountClimbSeconds", 0.4f)),
        mMountSeconds(configValue("HatcheryLookMountSeconds", 1.9f)),
        mMountHeight(configValue("HatcheryLookMountHeight", 0.85f)),
        mMountCrouch(configValue("HatcheryLookMountCrouch", 0.6f)),
        mMountWing(configValue("HatcheryLookMountWing", 0.3f)),
        mMountWingSpeed(configValue("HatcheryLookMountWingSpeed", 20.0f)),
        mEmergeRate(configValue("HatcheryLookEmergeRate", 2.0f)),
        mEmergeStart(configValue("HatcheryLookEmergeStart", 0.5f)),
        mEmergeLift(configValue("HatcheryLookEmergeLift", 0.03f)),
        mWalkSpeedChick(configValue("HatcheryLookWalkSpeedChick", 14.0f)),
        mWalkSpeedAdult(configValue("HatcheryLookWalkSpeedAdult", 9.0f)),
        mWalkLiftChick(configValue("HatcheryLookWalkLiftChick", 0.01f)),
        mWalkLiftAdult(configValue("HatcheryLookWalkLiftAdult", 0.006f)),
        mWalkPitch(configValue("HatcheryLookWalkPitch", 3.0f)),
        mPeepSpeed(configValue("HatcheryLookPeepSpeed", 2.1f)),
        mPeepLift(configValue("HatcheryLookPeepLift", 0.012f)),
        mPeepSharpness(configValue("HatcheryLookPeepSharpness", 12.0f)),
        mEggCrackSeconds(configValue("HatcheryLookEggCrackSeconds", 0.8f)),
        mEggWobbleRate(configValue("HatcheryLookEggWobbleRate", 2.5f)),
        mEggRoll(configValue("HatcheryLookEggRoll", 11.0f)),
        mEggRollSpeed(configValue("HatcheryLookEggRollSpeed", 17.0f)),
        mEggPitch(configValue("HatcheryLookEggPitch", 7.0f)),
        mEggPitchSpeed(configValue("HatcheryLookEggPitchSpeed", 13.0f)),
        mEggLift(configValue("HatcheryLookEggLift", 0.004f)),
        mProtestPuff(configValue("HatcheryLookProtestPuff", 1.25f)),
        mProtestPuffWobble(configValue("HatcheryLookProtestPuffWobble", 0.05f)),
        mProtestPuffSpeed(configValue("HatcheryLookProtestPuffSpeed", 24.0f)),
        mProtestWing(configValue("HatcheryLookProtestWing", 0.3f)),
        mProtestWingSpeed(configValue("HatcheryLookProtestWingSpeed", 21.0f)),
        mProtestRoll(configValue("HatcheryLookProtestRoll", 14.0f)),
        mProtestRollSpeed(configValue("HatcheryLookProtestRollSpeed", 22.0f)),
        mProtestPitch(configValue("HatcheryLookProtestPitch", -12.0f)),
        mProtestLift(configValue("HatcheryLookProtestLift", 0.03f)),
        mProtestLiftSpeed(configValue("HatcheryLookProtestLiftSpeed", 14.0f))
    {}

    float mCoopCheckSeconds;
    float mCoopShakeSeconds;
    float mCoopShakeSwing;
    float mCoopShakeSpeed;
    float mStrutPitch;
    float mStrutStretchX;
    float mStrutStretchZ;
    float mStrutLift;
    float mStrutSpeed;
    float mRunLift;
    float mRunLiftSpeed;
    float mRunRoll;
    float mRunRollSpeed;
    float mRunPitch;
    float mRunStretch;
    float mRunStretchSpeed;
    float mCrowRamp;
    float mCrowLift;
    float mCrowPitch;
    float mCrowStretch;
    float mCrowStretchSpeed;
    float mCrowStretchHeight;
    float mPerchPitch;
    float mGuardPuff;
    float mGuardPuffWobble;
    float mGuardPuffSpeed;
    float mGuardWing;
    float mGuardWingSpeed;
    float mGuardPitch;
    float mGuardPeckPitch;
    float mGuardPeckSpeed;
    float mScratchPitch;
    float mScratchSwing;
    float mScratchSpeed;
    float mScratchLift;
    float mFlutterRiseRate;
    float mFlutterLift;
    float mFlutterStretch;
    float mFlutterSpeed;
    float mFlutterPitch;
    float mFightPuff;
    float mFightPuffWobble;
    float mFightPuffSpeed;
    float mFightWing;
    float mFightWingSpeed;
    float mFightPitch;
    float mFightPitchSwing;
    float mFightPitchSpeed;
    float mFightRoll;
    float mFightRollSpeed;
    float mFightLift;
    float mFightLiftSpeed;
    float mLayFlatSeconds;
    float mLayStretchX;
    float mLayStretchY;
    float mLayStretchZ;
    float mLayWobble;
    float mLayWobbleSpeed;
    float mLayRiseStretch;
    float mCackleRoll;
    float mCackleRollSpeed;
    float mCackleLift;
    float mCackleLiftSpeed;
    float mMountPitch;
    float mMountLift;
    float mMountSpeed;
    float mMountBurstSeconds;
    float mMountClimbSeconds;
    float mMountSeconds;
    float mMountHeight;
    float mMountCrouch;
    float mMountWing;
    float mMountWingSpeed;
    float mEmergeRate;
    float mEmergeStart;
    float mEmergeLift;
    float mWalkSpeedChick;
    float mWalkSpeedAdult;
    float mWalkLiftChick;
    float mWalkLiftAdult;
    float mWalkPitch;
    float mPeepSpeed;
    float mPeepLift;
    float mPeepSharpness;
    float mEggCrackSeconds;
    float mEggWobbleRate;
    float mEggRoll;
    float mEggRollSpeed;
    float mEggPitch;
    float mEggPitchSpeed;
    float mEggLift;
    float mProtestPuff;
    float mProtestPuffWobble;
    float mProtestPuffSpeed;
    float mProtestWing;
    float mProtestWingSpeed;
    float mProtestRoll;
    float mProtestRollSpeed;
    float mProtestPitch;
    float mProtestLift;
    float mProtestLiftSpeed;
};

//! The look numbers, read from the config at the first use
const ChickenLookSettings& lookSettings()
{
    static const ChickenLookSettings settings;
    return settings;
}

//! Scale of the animal by kind
float kindScale(ChickenKind kind)
{
    switch(kind)
    {
        case ChickenKind::chick:
            return configValue("HatcheryChickScale", 0.5f);
        case ChickenKind::rooster:
            return configValue("HatcheryRoosterScale", 1.25f);
        default:
            return 1.0f;
    }
}

//! The particle system of the feathers of an animal: the colours of its plumage
const std::string& featherSystem(ChickenKind kind)
{
    static const std::string rooster = "ChickenFeathersRooster";
    static const std::string hen = "ChickenFeathers";
    return (kind == ChickenKind::rooster) ? rooster : hen;
}

//! An egg in a nest lies on the straw of the nest: the straw of the egg mesh is hidden
void hideEggStraw(Ogre::Entity* entity)
{
    for(unsigned int i = 0; i < entity->getNumSubEntities(); ++i)
    {
        Ogre::SubEntity* part = entity->getSubEntity(i);
        if(part->getMaterialName() == "ChickenStraw")
            part->setVisible(false);
    }
}

} // namespace

void RenderManager::rrEnsureChickenMesh(const std::string& meshName)
{
    if(meshName == MeshFeathers)
        ensureMesh(mSceneManager, MeshFeathers, buildFeathers);
}

void RenderManager::rrCreateChickenLook(ChickenEntity* chicken)
{
    Ogre::SceneNode* node = chicken->getEntityNode();
    const std::string entityName = chicken->getOgreNamePrefix() + chicken->getName();
    if((node == nullptr) || !mSceneManager->hasEntity(entityName))
        return;

    rrDestroyChickenLook(chicken);

    // The entity moves to a child node: the parent follows the server (position, turning), the child
    // carries the scale and the little procedural motions
    ChickenLook look;
    Ogre::Entity* entity = mSceneManager->getEntity(entityName);
    look.mNode = node->createChildSceneNode(entityName + "_look");
    node->detachObject(entity);
    look.mNode->attachObject(entity);
    look.mEntity = entity;
    look.mTime = 0.0f;
    look.mPoseTime = 0.0f;
    look.mPhase = static_cast<Ogre::Real>(++mChickenLookNumber % 97) * 0.37f;
    look.mFeatherBursts = 0;
    look.mEmergeFeathersPending = false;
    look.mCoopDoorReplayPending = false;
    look.mCoopExitWalking = false;
    look.mFightPartner = nullptr;
    look.mFightLeader = false;
    look.mFightTimer = 0.0f;
    look.mMountPartner = nullptr;
    look.mMountCrouch = 0.0f;
    look.mMountPhase = 0;
    look.mNestEgg = false;
    mChickenLooks[chicken] = look;
    applyChickenKindLook(chicken);
}

void RenderManager::rrDestroyChickenLook(ChickenEntity* chicken)
{
    std::map<ChickenEntity*, ChickenLook>::iterator it = mChickenLooks.find(chicken);
    if(it == mChickenLooks.end())
        return;

    ChickenLook& look = it->second;
    for(std::map<ChickenEntity*, ChickenLook>::iterator other = mChickenLooks.begin(); other != mChickenLooks.end(); ++other)
    {
        if(other->second.mFightPartner == chicken)
            other->second.mFightPartner = nullptr;
        if(other->second.mMountPartner == chicken)
            other->second.mMountPartner = nullptr;
    }
    for(Ogre::Entity* accessory : look.mAccessories)
    {
        look.mNode->detachObject(accessory);
        mSceneManager->destroyEntity(accessory);
    }

    // The entity goes back to the node of the animal, which destroys it
    Ogre::SceneNode* node = chicken->getEntityNode();
    look.mNode->detachObject(look.mEntity);
    if(node != nullptr)
    {
        node->attachObject(look.mEntity);
        node->removeAndDestroyChild(look.mNode->getName());
    }
    mChickenLooks.erase(it);
}

void RenderManager::clearChickenLooks()
{
    mChickenLooks.clear();
    mCoopDecors.clear();
    mNestFields.clear();
    mServerNests.clear();
}

void RenderManager::applyChickenKindLook(ChickenEntity* chicken)
{
    std::map<ChickenEntity*, ChickenLook>::iterator it = mChickenLooks.find(chicken);
    if(it == mChickenLooks.end())
        return;

    ChickenLook& look = it->second;
    const ChickenKind kind = chicken->getKind();

    // The shell of a cracked egg is gone
    for(Ogre::Entity* accessory : look.mAccessories)
    {
        look.mNode->detachObject(accessory);
        mSceneManager->destroyEntity(accessory);
    }
    look.mAccessories.clear();
    look.mEntity->setVisible(true);
    look.mNode->setScale(Ogre::Vector3::UNIT_SCALE * kindScale(kind));
}

void RenderManager::rrUpdateChickenLook(ChickenEntity* chicken)
{
    applyChickenKindLook(chicken);
}

bool RenderManager::chickenClipVisible(ChickenEntity* chicken, const std::string& clip) const
{
    std::map<ChickenEntity*, ChickenLook>::const_iterator it = mChickenLooks.find(chicken);
    if(it == mChickenLooks.end() || it->second.mEntity == nullptr || !it->second.mEntity->isVisible() ||
       it->second.mNode == nullptr || !it->second.mNode->isInSceneGraph() || mViewport == nullptr ||
       mViewport->getCamera() == nullptr || !mViewport->getCamera()->isVisible(it->second.mNode->_getDerivedPosition()) ||
       !it->second.mEntity->hasAnimationState(clip))
        return false;

    const Ogre::AnimationState* animation = it->second.mEntity->getAnimationState(clip);
    return animation->getEnabled() && !animation->hasEnded();
}

void RenderManager::rrChickenHatched(ChickenEntity* chicken)
{
    createChickenFeatherEffect(chicken->getPosition() + Ogre::Vector3(0.0f, 0.0f, 0.05f), "ChickenEggShell");
}

void RenderManager::rrEggTrampled(const Ogre::Vector3& position)
{
    // Shell pieces and yolk have no chicken feather trigger.
    createChickenFeatherEffect(position + Ogre::Vector3(0.0f, 0.0f, 0.04f), "ChickenEggTrample");
}

void RenderManager::rrSetHatcheryNests(const std::string& roomName, const std::vector<HatcheryNestField::Place>& places,
    const std::vector<HatcheryNestField::Place>& feathers)
{
    if(places.empty())
    {
        std::map<std::string, NestField>::iterator field = mNestFields.find(roomName);
        if(field != mNestFields.end())
        {
            destroyNestField(field->second);
            mNestFields.erase(field);
        }
        mServerNests.erase(roomName);
        return;
    }
    ServerNests& nests = mServerNests[roomName];
    nests.mPlaces = places;
    nests.mFeathers = feathers;
    ++nests.mVersion;
}

void RenderManager::rrChickenMount(ChickenEntity* rooster, ChickenEntity* hen)
{
    std::map<ChickenEntity*, ChickenLook>::iterator look = mChickenLooks.find(rooster);
    if(look != mChickenLooks.end())
        look->second.mMountPartner = hen;
}

void RenderManager::rrChickenFight(ChickenEntity* first, ChickenEntity* second, uint32_t phase)
{
    std::map<ChickenEntity*, ChickenLook>::iterator firstLook = mChickenLooks.find(first);
    std::map<ChickenEntity*, ChickenLook>::iterator secondLook = mChickenLooks.find(second);
    if(firstLook != mChickenLooks.end())
    {
        firstLook->second.mFightPartner = (phase == 0) ? second : nullptr;
        firstLook->second.mFightLeader = true;
        firstLook->second.mFightTimer = 0.0f;
    }
    if(secondLook != mChickenLooks.end())
    {
        secondLook->second.mFightPartner = (phase == 0) ? first : nullptr;
        secondLook->second.mFightLeader = false;
        secondLook->second.mFightTimer = 0.0f;
    }
}

void RenderManager::rrSetChickenPose(ChickenEntity* chicken, const std::string& pose)
{
    std::map<ChickenEntity*, ChickenLook>::iterator it = mChickenLooks.find(chicken);
    if(it == mChickenLooks.end())
        return;

    ChickenLook& look = it->second;
    if(look.mPose == pose)
        return;

    look.mPose = pose;
    look.mPoseTime = 0.0f;
    look.mFeatherBursts = 0;
    if((pose != ChickenPose::emerge) && !pose.empty())
    {
        look.mEmergeFeathersPending = false;
        look.mCoopDoorReplayPending = false;
        look.mCoopExitWalking = false;
    }
    const Ogre::Vector3 position = chicken->getPosition();

    look.mMountPartner = nullptr;
    look.mMountPhase = 0;
    if(pose == ChickenPose::mount)
    {
        // The Mount clip is started with the pose
        look.mMountPhase = 1;
        // The hen he caught is the nearest one; he climbs on her back (the feathers fly when he is up)
        Ogre::Real nearestDistance = 2.25f;
        for(std::map<ChickenEntity*, ChickenLook>::iterator other = mChickenLooks.begin(); other != mChickenLooks.end(); ++other)
        {
            if((other->first == chicken) || (other->first->getKind() != ChickenKind::hen))
                continue;

            if(!chicken->getMountHenName().empty() && other->first->getName() != chicken->getMountHenName())
                continue;
            const Ogre::Real distance = other->first->getPosition().squaredDistance(position);
            if(distance < nearestDistance)
            {
                nearestDistance = distance;
                look.mMountPartner = other->first;
            }
        }
    }
    else if(pose == ChickenPose::emerge)
    {
        look.mEmergeFeathersPending = true;
        look.mCoopDoorReplayPending = true;
        look.mCoopExitWalking = false;
        // The door of the closest coop swings
        std::map<BuildingObject*, CoopDecor>::iterator nearest = mCoopDecors.end();
        Ogre::Real nearestDistance = 4.0f;
        for(std::map<BuildingObject*, CoopDecor>::iterator coop = mCoopDecors.begin(); coop != mCoopDecors.end(); ++coop)
        {
            Ogre::Real distance = coop->first->getPosition().squaredDistance(position);
            if(distance < nearestDistance)
            {
                nearest = coop;
                nearestDistance = distance;
            }
        }
        if(nearest != mCoopDecors.end())
        {
            if(nearest->second.mDoor != nullptr)
            {
                // The door of the coop mesh swings once
                nearest->second.mDoor->setTimePosition(0.0f);
                nearest->second.mDoor->setLoop(false);
                nearest->second.mDoor->setEnabled(true);
            }
            else
                nearest->second.mShake = lookSettings().mCoopShakeSeconds;
        }
    }
}

void RenderManager::rrCreateCoopDecor(BuildingObject* coop)
{
    Ogre::SceneNode* node = coop->getEntityNode();
    if((node == nullptr) || (mCoopDecors.count(coop) > 0))
        return;

    const std::string name = coop->getOgreNamePrefix() + coop->getName() + "_decor";
    CoopDecor decor;
    decor.mShake = 0.0f;
    decor.mDoor = nullptr;

    // The coop mesh with a skeleton has a door of its own, the old mesh shakes
    if((node->numAttachedObjects() > 0) && (node->getAttachedObject(0)->getMovableType() == "Entity"))
    {
        Ogre::Entity* body = static_cast<Ogre::Entity*>(node->getAttachedObject(0));
        if(body->hasSkeleton() && body->getSkeleton()->hasAnimation(HatcheryCoopHouse::doorClip))
        {
            decor.mDoor = body->getAnimationState(HatcheryCoopHouse::doorClip);
            decor.mDoor->setLoop(false);
            decor.mDoor->setEnabled(false);
        }
    }

    decor.mNode = node->createChildSceneNode(name + "_node", Ogre::Vector3(0.9f, 0.0f, 0.0f));
    mCoopDecors[coop] = decor;
    // The first check is done at once
    mCoopDecorTimer = 10.0f;
}

void RenderManager::rrDestroyCoopDecor(BuildingObject* coop)
{
    std::map<BuildingObject*, CoopDecor>::iterator it = mCoopDecors.find(coop);
    if(it == mCoopDecors.end())
        return;

    CoopDecor& decor = it->second;
    if(coop->getEntityNode() != nullptr)
    {
        coop->getEntityNode()->removeAndDestroyChild(decor.mNode->getName());
    }
    mCoopDecors.erase(it);
}

void RenderManager::updateChickenLooks(Ogre::Real timeSinceLastFrame)
{
    const Ogre::Real pi = Ogre::Math::PI;
    const ChickenLookSettings& values = lookSettings();
    for(std::map<ChickenEntity*, ChickenLook>::iterator it = mChickenLooks.begin(); it != mChickenLooks.end(); ++it)
    {
        ChickenEntity* chicken = it->first;
        ChickenLook& look = it->second;
        look.mTime += timeSinceLastFrame;
        look.mPoseTime += timeSinceLastFrame;
        const Ogre::Real t = look.mTime + look.mPhase;
        const Ogre::Real p = look.mPoseTime;
        const ChickenKind kind = chicken->getKind();
        const std::string& pose = look.mPose;
        const bool moving = chicken->isMoving();

        Ogre::Real lift = 0.0f;
        Ogre::Real pitch = 0.0f;
        Ogre::Real roll = 0.0f;
        Ogre::Vector3 shift = Ogre::Vector3::ZERO;
        Ogre::Vector3 stretch = Ogre::Vector3::UNIT_SCALE;

        if(kind == ChickenKind::egg)
        {
            // An egg a little above the ground lies in a nest (the server puts it there)
            if(!look.mNestEgg && (chicken->getPosition().z > 0.01f))
            {
                look.mNestEgg = true;
                hideEggStraw(look.mEntity);
            }

            // The egg rocks from side to side and gets more restless until it breaks
            if(pose == ChickenPose::wobble)
            {
                // Shortly before it hatches the shell shows its cracks
                if(look.mAccessories.empty() && (p > values.mEggCrackSeconds))
                {
                    Ogre::Entity* cracked = mSceneManager->createEntity(
                        look.mNode->getName() + "_" + MeshEggCracked, MeshEggCracked + ".mesh");
                    cracked->setQueryFlags(0);
                    if(look.mNestEgg)
                        hideEggStraw(cracked);
                    look.mNode->attachObject(cracked);
                    look.mAccessories.push_back(cracked);
                    look.mEntity->setVisible(false);
                }
                const Ogre::Real strength = std::min(1.0f, p * values.mEggWobbleRate);
                roll = values.mEggRoll * strength * std::sin(p * values.mEggRollSpeed);
                pitch = values.mEggPitch * strength * std::cos(p * values.mEggPitchSpeed);
                lift = values.mEggLift * strength * std::fabs(std::sin(p * values.mEggRollSpeed));
            }
        }
        else
        {
            if(pose == ChickenPose::strut)
            {
                // Chest out, head up, a proud little bounce with each step
                pitch = values.mStrutPitch;
                stretch = Ogre::Vector3(values.mStrutStretchX, 1.0f, values.mStrutStretchZ);
                lift = values.mStrutLift * std::fabs(std::sin(t * values.mStrutSpeed));
            }
            else if(pose == ChickenPose::chase || pose == ChickenPose::flee)
            {
                if(look.mEntity->getSkeleton()->hasAnimation("Run"))
                {
                    // The run clip leans forward and spreads the wings, only the hops are added
                    lift = values.mRunLift * std::fabs(std::sin(t * values.mRunLiftSpeed));
                    roll = values.mRunRoll * std::sin(t * values.mRunRollSpeed);
                }
                else
                {
                    // Head forward, wings out, quick hops
                    pitch = values.mRunPitch;
                    stretch = Ogre::Vector3(1.0f + values.mRunStretch * std::fabs(std::sin(t * values.mRunStretchSpeed)), 1.0f, 1.0f);
                    lift = values.mRunLift * std::fabs(std::sin(t * values.mRunLiftSpeed));
                    roll = values.mRunRoll * std::sin(t * values.mRunRollSpeed);
                }
            }
            else if(pose == ChickenPose::crow)
            {
                const Ogre::Real strength = std::min(1.0f, p * values.mCrowRamp);
                if(look.mEntity->getSkeleton()->hasAnimation("Crow"))
                {
                    // The crow clip throws the head back and beats the wings, the body only rises a little
                    lift = values.mCrowLift * strength;
                }
                else
                {
                    // Head thrown back, the body stretches, the wings beat
                    pitch = values.mCrowPitch * strength;
                    stretch = Ogre::Vector3(1.0f + values.mCrowStretch * std::fabs(std::sin(t * values.mCrowStretchSpeed)) * strength,
                        1.0f, 1.0f + values.mCrowStretchHeight * strength);
                    lift = values.mCrowLift * strength;
                }
            }
            else if(pose == ChickenPose::perch)
                pitch = values.mPerchPitch;
            else if(pose == ChickenPose::guard)
            {
                // Puffed up and flapping
                const Ogre::Real puff = values.mGuardPuff + values.mGuardPuffWobble * std::sin(t * values.mGuardPuffSpeed);
                stretch = Ogre::Vector3(puff + values.mGuardWing * std::fabs(std::sin(t * values.mGuardWingSpeed)), puff, puff);
                // He pecks at the creature in front of him: a lunge of the head, then back
                pitch = values.mGuardPitch + values.mGuardPeckPitch * std::max(0.0f, std::sin(t * values.mGuardPeckSpeed));
            }
            else if(pose == ChickenPose::scratch)
            {
                // A hen scratches the ground with quick strokes, then pecks
                pitch = values.mScratchPitch + values.mScratchSwing * std::sin(p * values.mScratchSpeed);
                lift = values.mScratchLift * std::fabs(std::sin(p * values.mScratchSpeed));
            }
            else if(pose == ChickenPose::flutter)
            {
                // The flutter clip lifts the hen and beats the wings, without it she is stretched and lifted here
                if(!look.mEntity->getSkeleton()->hasAnimation("Flutter"))
                {
                    // Flaps up for a moment with the wings out and settles down again
                    const Ogre::Real rise = std::sin(std::min(1.0f, p * values.mFlutterRiseRate) * pi);
                    lift = values.mFlutterLift * rise;
                    stretch = Ogre::Vector3(1.0f + values.mFlutterStretch * std::fabs(std::sin(p * values.mFlutterSpeed)) * rise, 1.0f, 1.0f);
                    pitch = values.mFlutterPitch * rise;
                }
            }
            else if(pose == ChickenPose::fight)
            {
                // Puffed up, wings beating, pecking and lunging at the other rooster, little hops
                const Ogre::Real puff = values.mFightPuff + values.mFightPuffWobble * std::sin(t * values.mFightPuffSpeed);
                stretch = Ogre::Vector3(puff + values.mFightWing * std::fabs(std::sin(t * values.mFightWingSpeed)), puff, puff);
                pitch = values.mFightPitch + values.mFightPitchSwing * std::sin(t * values.mFightPitchSpeed);
                roll = values.mFightRoll * std::sin(t * values.mFightRollSpeed);
                lift = values.mFightLift * std::fabs(std::sin(t * values.mFightLiftSpeed));
            }
            else if(pose == ChickenPose::protest)
            {
                // Held in the hand: puffed up, wings beating, kicking and rolling about
                const Ogre::Real puff = values.mProtestPuff + values.mProtestPuffWobble * std::sin(t * values.mProtestPuffSpeed);
                stretch = Ogre::Vector3(puff + values.mProtestWing * std::fabs(std::sin(t * values.mProtestWingSpeed)), puff, puff);
                pitch = values.mProtestPitch;
                roll = values.mProtestRoll * std::sin(t * values.mProtestRollSpeed);
                lift = values.mProtestLift * std::fabs(std::sin(t * values.mProtestLiftSpeed));
            }
            else if(pose == ChickenPose::lay)
            {
                // The lay clip sits down, fluffs up and stands up, without it the body is squashed here
                if(look.mEntity->getSkeleton()->hasAnimation("Lay"))
                {
                    // Nothing to add
                }
                else if(p < values.mLayFlatSeconds)
                    stretch = Ogre::Vector3(values.mLayStretchX, values.mLayStretchY,
                        values.mLayStretchZ + values.mLayWobble * std::sin(p * values.mLayWobbleSpeed));
                else
                    stretch = Ogre::Vector3(1.0f, 1.0f, values.mLayRiseStretch);
            }
            else if(pose == ChickenPose::cackle)
            {
                if((look.mMountCrouch > 0.0f) && look.mEntity->getSkeleton()->hasAnimation("Duck"))
                {
                    // The duck clip ducks her under him, nothing is added
                }
                else if(look.mMountCrouch > 0.0f)
                {
                    // The rooster sits on her: she ducks down under him and quivers
                    stretch = Ogre::Vector3(1.0f + 0.1f * look.mMountCrouch, 1.0f + 0.1f * look.mMountCrouch,
                        1.0f - (1.0f - values.mMountCrouch) * look.mMountCrouch);
                    roll = values.mCackleRoll * 0.4f * look.mMountCrouch * std::sin(p * values.mCackleRollSpeed);
                }
                else
                {
                    roll = values.mCackleRoll * std::sin(p * values.mCackleRollSpeed);
                    lift = values.mCackleLift * std::fabs(std::sin(p * values.mCackleLiftSpeed));
                }
            }
            else if(pose == ChickenPose::mount)
            {
                // A hen that becomes visible later still resolves to the server-selected partner.
                if(look.mMountPartner == nullptr && !chicken->getMountHenName().empty())
                    for(std::map<ChickenEntity*, ChickenLook>::iterator other = mChickenLooks.begin(); other != mChickenLooks.end(); ++other)
                        if(other->first->getName() == chicken->getMountHenName())
                            look.mMountPartner = other->first;
                // He climbs on the back of the hen he caught, treads and beats his wings there, and climbs down
                std::map<ChickenEntity*, ChickenLook>::iterator hen = (look.mMountPartner != nullptr) ?
                    mChickenLooks.find(look.mMountPartner) : mChickenLooks.end();
                const Ogre::Real climb = std::max(0.05f, values.mMountClimbSeconds);
                const Ogre::Real upRatio = std::min(1.0f, p / climb);
                const Ogre::Real downRatio = std::min(1.0f, std::max(0.0f, (values.mMountSeconds - p) / climb));
                const Ogre::Real on = std::min(upRatio * upRatio * (3.0f - 2.0f * upRatio),
                    downRatio * downRatio * (3.0f - 2.0f * downRatio));
                if(look.mEntity->getSkeleton()->hasAnimation("Tread"))
                {
                    // The clips follow the phases: Mount (climb), Tread (looped), Dismount (climb down); their lengths
                    // are the climb time and the rest of the 1.9 s of the pose. Tread follows 0.05 s before the Mount
                    // clip ends: an ended clip would send the animal to idle and end the pose
                    const int phase = (p < climb - 0.05f) ? 1 : ((p < values.mMountSeconds - climb) ? 2 : 3);
                    if(phase != look.mMountPhase)
                    {
                        look.mMountPhase = phase;
                        const char* const clips[3] = {"Mount", "Tread", "Dismount"};
                        chicken->setAnimationState(setEntityAnimation(look.mEntity, clips[phase - 1], phase == 2));
                    }
                }
                // Beating the wings and treading only while he sits on her
                const Ogre::Real sitting = std::max(0.0f, on * 2.0f - 1.0f);
                pitch = values.mMountPitch * on;
                stretch = Ogre::Vector3(1.0f + values.mMountWing * std::fabs(std::sin(p * values.mMountWingSpeed)) * sitting,
                    1.0f, 1.0f);
                lift = values.mMountLift * std::fabs(std::sin(p * values.mMountSpeed)) * sitting;
                if(hen != mChickenLooks.end())
                {
                    // The back of the hen is as high as she is when she is ducked; he jumps up in an arc
                    const Ogre::Real henHeight = hen->second.mEntity->getBoundingBox().getMaximum().z *
                        kindScale(ChickenKind::hen) * values.mMountCrouch;
                    lift += henHeight * values.mMountHeight * on + 0.08f * std::sin(std::min(upRatio, 1.0f) * pi) *
                        (p < climb ? 1.0f : 0.0f);
                    hen->second.mMountCrouch = on;

                    // He moves over her: the way from his place to hers in the frame of his node
                    Ogre::SceneNode* parent = look.mNode->getParentSceneNode();
                    Ogre::SceneNode* henParent = hen->second.mNode->getParentSceneNode();
                    if((parent != nullptr) && (henParent != nullptr))
                    {
                        look.mEntity->_updateAnimation();
                        hen->second.mEntity->_updateAnimation();
                        const Ogre::Vector3 henHead = hen->second.mEntity->getSkeleton()->getBone("Head")->_getDerivedPosition();
                        const Ogre::Vector3 roosterHead = look.mEntity->getSkeleton()->getBone("Head")->_getDerivedPosition();
                        const Ogre::Vector3 targetHead = parent->convertWorldToLocalPosition(
                            hen->second.mNode->convertLocalToWorldPosition(henHead));
                        const Ogre::Quaternion lean = Ogre::Quaternion(Ogre::Degree(pitch), Ogre::Vector3::UNIT_X);
                        const Ogre::Vector3 headOffset = lean * (roosterHead * kindScale(kind) * stretch);
                        shift = (targetHead - headOffset) * on;
                        shift.z = 0.0f;
                    }
                }
                if((look.mFeatherBursts == 0) && (p > climb) && (look.mMountPartner != nullptr) &&
                   chickenClipVisible(chicken, "Tread") && chickenClipVisible(look.mMountPartner, "Duck"))
                {
                    // He has landed: the feathers of both fly
                    look.mFeatherBursts = 1;
                    Ogre::SceneNode* parent = look.mNode->getParentSceneNode();
                    if(parent != nullptr)
                        createChickenFeatherEffect(parent->convertLocalToWorldPosition(shift + Ogre::Vector3(0.0f, 0.0f, lift + 0.25f)),
                            featherSystem(kind));
                    if((look.mMountPartner != nullptr) && chickenClipVisible(look.mMountPartner, "Duck"))
                    {
                        createChickenFeatherEffect(look.mMountPartner->getPosition() + Ogre::Vector3(0.0f, 0.0f, 0.15f),
                            featherSystem(ChickenKind::hen));
                    }
                }
                else if((look.mFeatherBursts == 1) && (p > values.mMountBurstSeconds) &&
                    (look.mMountPartner != nullptr) && chickenClipVisible(chicken, "Tread") &&
                    chickenClipVisible(look.mMountPartner, "Duck"))
                {
                    look.mFeatherBursts = 2;
                    createChickenFeatherEffect(look.mMountPartner->getPosition() + Ogre::Vector3(0.0f, 0.0f, 0.2f),
                        featherSystem(ChickenKind::hen));
                }
            }
            else if(pose == ChickenPose::emerge)
            {
                // Pops out of the coop
                const Ogre::Real grow = std::min(1.0f, p * values.mEmergeRate);
                stretch = Ogre::Vector3::UNIT_SCALE * (values.mEmergeStart + (1.0f - values.mEmergeStart) * grow);
                lift = values.mEmergeLift * std::sin(grow * pi);
            }
            else if(moving)
            {
                // Walking: a small bob, chicks hop more
                const Ogre::Real speed = (kind == ChickenKind::chick) ? values.mWalkSpeedChick : values.mWalkSpeedAdult;
                lift = ((kind == ChickenKind::chick) ? values.mWalkLiftChick : values.mWalkLiftAdult) * std::fabs(std::sin(t * speed));
                pitch = values.mWalkPitch * std::sin(t * speed);
            }
            else if(kind == ChickenKind::chick)
            {
                // A chick peeps now and then with a little hop
                const Ogre::Real peep = std::max(0.0f, std::sin(t * values.mPeepSpeed));
                lift = values.mPeepLift * std::pow(peep, values.mPeepSharpness);
            }
        }

        if((kind == ChickenKind::hen) && (pose == ChickenPose::flutter) && (look.mFeatherBursts == 0) &&
           chickenClipVisible(chicken, "Flutter"))
        {
            look.mFeatherBursts = 1;
            createChickenFeatherEffect(chicken->getPosition() + Ogre::Vector3(0.0f, 0.0f, 0.1f), featherSystem(kind));
        }
        if((look.mEmergeFeathersPending || look.mCoopDoorReplayPending) && moving)
        {
            look.mCoopExitWalking = true;
            for(std::map<BuildingObject*, CoopDecor>::iterator coop = mCoopDecors.begin(); coop != mCoopDecors.end(); ++coop)
            {
                const Ogre::Vector3 door = coop->first->getPosition() + Ogre::Vector3(0.9f, 0.0f, 0.0f);
                if(chicken->getPosition().squaredDistance(door) > 0.16f)
                    continue;
                if(look.mCoopDoorReplayPending && chicken->getPosition().x >= door.x - 0.2f)
                {
                    look.mCoopDoorReplayPending = false;
                    if(coop->second.mDoor != nullptr)
                    {
                        coop->second.mDoor->setTimePosition(0.0f);
                        coop->second.mDoor->setEnabled(true);
                    }
                }
                if(look.mEmergeFeathersPending && chicken->getPosition().x >= door.x &&
                   chickenClipVisible(chicken, EntityAnimation::walk_anim))
                {
                    look.mEmergeFeathersPending = false;
                    createChickenFeatherEffect(chicken->getPosition() + Ogre::Vector3(0.0f, 0.0f, 0.1f), featherSystem(kind));
                }
                if(!look.mEmergeFeathersPending && !look.mCoopDoorReplayPending)
                    break;
            }
        }

        if(look.mCoopExitWalking && !moving)
        {
            look.mEmergeFeathersPending = false;
            look.mCoopDoorReplayPending = false;
            look.mCoopExitWalking = false;
        }

        // The duck of a hen under a rooster is set again by him in every frame
        look.mMountCrouch = 0.0f;
        look.mNode->setPosition(shift.x, shift.y, lift);
        look.mNode->setScale(Ogre::Vector3::UNIT_SCALE * kindScale(kind) * stretch);
        look.mNode->setOrientation(Ogre::Quaternion(Ogre::Degree(pitch), Ogre::Vector3::UNIT_X) *
            Ogre::Quaternion(Ogre::Degree(roll), Ogre::Vector3::UNIT_Y));
    }

    // Coops: a shaking door. The straw nests of the hatchery show while it lives.
    mCoopDecorTimer += timeSinceLastFrame;
    const bool check = mCoopDecorTimer >= values.mCoopCheckSeconds;
    if(check)
        mCoopDecorTimer = 0.0f;
    for(std::map<BuildingObject*, CoopDecor>::iterator it = mCoopDecors.begin(); it != mCoopDecors.end(); ++it)
    {
        BuildingObject* coop = it->first;
        CoopDecor& decor = it->second;
        // The door clip of the coop mesh plays once and then rests closed
        if((decor.mDoor != nullptr) && decor.mDoor->getEnabled())
        {
            decor.mDoor->addTime(timeSinceLastFrame);
            if(decor.mDoor->hasEnded())
            {
                decor.mDoor->setEnabled(false);
                decor.mDoor->setTimePosition(0.0f);
            }
            continue;
        }

        // The coop shakes for a moment when an animal comes out
        Ogre::SceneNode* node = coop->getEntityNode();
        if(node == nullptr)
            continue;

        const Ogre::Quaternion base(Ogre::Degree(coop->getRotationAngle()), Ogre::Vector3::UNIT_Z);
        if(decor.mShake > 0.0f)
        {
            decor.mShake = std::max(0.0f, decor.mShake - timeSinceLastFrame);
            const Ogre::Real swing = values.mCoopShakeSwing * decor.mShake * std::sin(decor.mShake * values.mCoopShakeSpeed);
            node->setOrientation(base * Ogre::Quaternion(Ogre::Degree(swing), Ogre::Vector3::UNIT_X));
        }
        else if(decor.mShake == 0.0f)
        {
            node->setOrientation(base);
            decor.mShake = -1.0f;
        }
        else if(decor.mShake < 0.0f)
        {
            // Resting
        }
    }

    if(check)
        updateNestFields();
}

void RenderManager::destroyNestField(NestField& field)
{
    for(uint32_t i = 0; i < field.mEntities.size(); ++i)
    {
        field.mNodes[i]->detachObject(field.mEntities[i]);
        mSceneManager->destroyEntity(field.mEntities[i]);
        mSceneManager->destroySceneNode(field.mNodes[i]);
    }
    field.mEntities.clear();
    field.mNodes.clear();
    for(uint32_t i = 0; i < field.mFeatherEntities.size(); ++i)
    {
        field.mFeatherNodes[i]->detachObject(field.mFeatherEntities[i]);
        mSceneManager->destroyEntity(field.mFeatherEntities[i]);
        mSceneManager->destroySceneNode(field.mFeatherNodes[i]);
    }
    field.mFeatherEntities.clear();
    field.mFeatherNodes.clear();
}

void RenderManager::updateNestFields()
{
    if(mGameMap == nullptr)
        return;

    for(std::map<std::string, ServerNests>::const_iterator sent = mServerNests.begin(); sent != mServerNests.end(); ++sent)
    {
        const uint32_t key = sent->second.mVersion;
        std::map<std::string, NestField>::iterator existing = mNestFields.find(sent->first);
        if((existing != mNestFields.end()) && (existing->second.mKey != key))
        {
            destroyNestField(existing->second);
            mNestFields.erase(existing);
            existing = mNestFields.end();
        }
        if(existing == mNestFields.end())
        {
            NestField created;
            created.mKey = key;
            const std::vector<HatcheryNestField::Place>& places = sent->second.mPlaces;
            for(uint32_t i = 0; i < places.size(); ++i)
            {
                const std::string name = "HatcheryNest_" + sent->first + "_" + std::to_string(i);
                Ogre::SceneNode* node = mSceneManager->getRootSceneNode()->createChildSceneNode(name + "_node",
                    Ogre::Vector3(static_cast<Ogre::Real>(places[i].mX), static_cast<Ogre::Real>(places[i].mY), 0.0f));
                node->setOrientation(Ogre::Quaternion(Ogre::Degree(static_cast<Ogre::Real>(places[i].mAngle)),
                    Ogre::Vector3::UNIT_Z));
                Ogre::Entity* entity = mSceneManager->createEntity(name, MeshNest + ".mesh");
                entity->setQueryFlags(0);
                entity->setVisible(false);
                node->attachObject(entity);
                created.mNodes.push_back(node);
                created.mEntities.push_back(entity);
            }
            existing = mNestFields.insert(std::make_pair(sent->first, created)).first;
        }
        for(uint32_t i = 0; i < existing->second.mEntities.size(); ++i)
        {
            const HatcheryNestField::Place& place = sent->second.mPlaces[i];
            Tile* tile = mGameMap->getTile(static_cast<int>(std::floor(place.mX + 0.5)),
                static_cast<int>(std::floor(place.mY + 0.5)));
            existing->second.mEntities[i]->setVisible((tile != nullptr) && tile->getLocalPlayerHasVision() &&
                (tile->getTileVisual() == TileVisual::hatcheryRoom));
        }
    }
}
