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

#include "entities/BuildingObject.h"
#include "render/RenderManager.h"

#include "entities/Building.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "network/ODPacket.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "ODApplication.h"
#include <OgreSubEntity.h>
#include "gamemap/GameMap.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "traps/TrapBoulder.h"
#include "traps/TrapCannon.h"
#include "traps/TrapSpike.h"
#include "utils/Random.h"
#include "utils/LogManager.h"

#include <algorithm>
#include <iostream>

BuildingObject::BuildingObject(GameMap* gameMap, Building& building, const std::string& meshName, Tile* targetTile,
        Ogre::Real x, Ogre::Real y, Ogre::Real z, Ogre::Real rotationAngle, bool hideCoveredTile, float opacity,
        const std::string& initialAnimationState, bool initialAnimationLoop) :
    RenderedMovableEntity(
        gameMap,
        targetTile == nullptr ? building.getName() : building.getName() + "_" + Tile::displayAsString(targetTile),
        meshName,
        rotationAngle,
        hideCoveredTile,
        opacity)
{
    mPosition = Ogre::Vector3(x, y, z);
    mPrevAnimationState = initialAnimationState;
    mPrevAnimationStateLoop = initialAnimationLoop;
}

BuildingObject::BuildingObject(GameMap* gameMap, Building& building, const std::string& meshName,
        Tile& targetTile, Ogre::Real rotationAngle, bool hideCoveredTile, float opacity,
        const std::string& initialAnimationState, bool initialAnimationLoop) :
    RenderedMovableEntity(
        gameMap,
        building.getName() + "_" + Tile::displayAsString(&targetTile),
        meshName,
        rotationAngle,
        hideCoveredTile,
        opacity)
{
    mPosition = Ogre::Vector3(targetTile.getX(), targetTile.getY(), 0);
    mPrevAnimationState = initialAnimationState;
    mPrevAnimationStateLoop = initialAnimationLoop;
}


BuildingObject::BuildingObject(GameMap* gameMap) :
    RenderedMovableEntity(gameMap)
{
}

GameEntityType BuildingObject::getObjectType() const
{
    return GameEntityType::buildingObject;
}

void BuildingObject::doUpkeep()
{
    RenderedMovableEntity::doUpkeep();

    for(std::vector<EntityParticleEffect*>::iterator it = mEntityParticleEffects.begin(); it != mEntityParticleEffects.end();)
    {
        EntityParticleEffect* effect = *it;
        if(effect->mNbTurnsEffect < 0)
        {
            ++it;
            continue;
        }

        if(effect->mNbTurnsEffect > 0)
        {
            --effect->mNbTurnsEffect;
            ++it;
            continue;
        }

        it = mEntityParticleEffects.erase(it);
        delete effect;
    }
}

BuildingObject* BuildingObject::getBuildingObjectFromPacket(GameMap* gameMap, ODPacket& is)
{
    BuildingObject* obj = new BuildingObject(gameMap);
    obj->importFromPacket(is);
    return obj;
}

void BuildingObject::addParticleEffect(const std::string& effectScript, uint32_t nbTurns)
{
    EntityParticleEffect* effect = new EntityParticleEffect(nextParticleSystemsName(), effectScript, nbTurns);
    mEntityParticleEffects.push_back(effect);
}

//! \brief Builds the furniture and applies a decorative bag's shared quality materials.
void BuildingObject::createMeshLocal(NodeType type)
{
    RenderedMovableEntity::createMeshLocal(type);
    if(!getIsOnServerMap() && getMeshName()=="GhostCauldron" && getEntityNode()!=nullptr)
    {
        Ogre::Entity* fill=RenderManager::getSingleton().getSceneManager()->createEntity(getName()+"_GhostFill","GhostCauldronFill.mesh");
        fill->setCastShadows(false);fill->setQueryFlags(0);
        mGhostFillNode=getEntityNode()->createChildSceneNode(getName()+"_GhostFillNode",Ogre::Vector3(0.0f,0.69f,0.35f));
        mGhostFillNode->attachObject(fill);
        mGhostFillNode->setScale(1.0f,1.0f,static_cast<float>(std::max(0.0,mGhostFill)));
    }
    if(!getIsOnServerMap() && getMeshName()=="GhostHook" && getEntityNode()!=nullptr)
    {
        // The pack on the wall hook is the textured pack the hunters wear (decision 798): the renderer draws the bare
        // hook (GhostHookEmpty) for a full hook, and the worn GhostBackpack with its holstered capture cannon hangs on it.
        // In the hook's frame the wall bolts lie at -y and the hook tip at about y 0.075, z 0.49 to 0.64.
        const Ogre::Real packHeight=0.30f,packBackY=0.03f,packTopZ=0.56f;
        Ogre::SceneManager* scene=RenderManager::getSingleton().getSceneManager();
        Ogre::Entity* pack=scene->createEntity(getName()+"_GhostHookPack","GhostBackpack.mesh");
        pack->setCastShadows(true);pack->setQueryFlags(0);
        const Ogre::AxisAlignedBox packBounds=pack->getMesh()->getBounds();
        const Ogre::Vector3 packSize=packBounds.getSize();
        const Ogre::Real fit=packHeight/packSize.z;
        // Half a turn round the vertical axis: the straps (+y of the pack) lie against the hook and the wall, the
        // generator plate with its power cells faces the room as on the hunter's back
        mGhostHookPackNode=getEntityNode()->createChildSceneNode(getName()+"_GhostHookPackNode",
            Ogre::Vector3(fit*0.5f*(packBounds.getMinimum().x+packBounds.getMaximum().x),
                packBackY+fit*packBounds.getMaximum().y,packTopZ-fit*packBounds.getMaximum().z),
            Ogre::Quaternion(Ogre::Degree(180.0f),Ogre::Vector3::UNIT_Z));
        mGhostHookPackNode->setScale(Ogre::Vector3(fit,fit,fit));
        mGhostHookPackNode->attachObject(pack);
        // The capture cannon waits upright in its holster on the pack's side, exactly as on the worn pack
        // (Creature::updateGhostHuntVisuals)
        Ogre::Entity* gun=scene->createEntity(getName()+"_GhostHookPackGun","GhostCaptureGun.mesh");
        gun->setCastShadows(true);gun->setQueryFlags(0);
        const Ogre::Real holster=0.85f*packSize.z/gun->getMesh()->getBounds().getSize().z;
        Ogre::SceneNode* holsterNode=mGhostHookPackNode->createChildSceneNode(getName()+"_GhostHookHolsterNode",
            Ogre::Vector3(-0.5f*packSize.x-0.045f,0.0f,0.05f*packSize.z));
        holsterNode->setScale(Ogre::Vector3(holster,holster,holster));
        holsterNode->attachObject(gun);
    }
    if(!getIsOnServerMap() && mItemBagQuality >= 0)
        RenderManager::getSingleton().rrRefreshItemBagAppearance(this, static_cast<Quality>(mItemBagQuality), mItemBagSealed);
}

//! \brief Sends the furniture footprint and decorative merchant bag properties.
void BuildingObject::exportToPacket(ODPacket& os, const Seat* seat) const
{
    RenderedMovableEntity::exportToPacket(os, seat);
    os << mFurnitureScale.x << mFurnitureScale.y;
    os << mItemBagQuality << mItemBagSealed;
    os << mGhostFill << mGhostAlarm;
}

//! \brief Reads the furniture footprint and decorative merchant bag properties.
void BuildingObject::importFromPacket(ODPacket& is)
{
    RenderedMovableEntity::importFromPacket(is);
    OD_ASSERT_TRUE(is >> mFurnitureScale.x >> mFurnitureScale.y);
    OD_ASSERT_TRUE(is >> mItemBagQuality >> mItemBagSealed);
    OD_ASSERT_TRUE(is >> mGhostFill >> mGhostAlarm);
}

void BuildingObject::fireRefresh()
{
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr)
            continue;
        if(!seat->getPlayer()->getIsHuman())
            continue;

        const std::string& name = getName();
        ServerNotification *serverNotification = new ServerNotification(
            ServerNotificationType::entitiesRefresh, seat->getPlayer());
        uint32_t nb = 1;
        GameEntityType entityType = getObjectType();
        serverNotification->mPacket << nb;
        serverNotification->mPacket << entityType;
        serverNotification->mPacket << name;
        exportToPacketForUpdate(serverNotification->mPacket, seat);
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

//! \brief Sends one add packet per current viewer, carrying the old identity for removal after mesh creation.
void BuildingObject::notifyReplacement(BuildingObject& previous)
{
    mSeatsWithVisionNotified = getPositionTile()->getSeatsWithVision();
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        std::vector<Seat*>::iterator oldSeat = std::find(previous.mSeatsWithVisionNotified.begin(),
            previous.mSeatsWithVisionNotified.end(), seat);
        if(oldSeat != previous.mSeatsWithVisionNotified.end())
            previous.mSeatsWithVisionNotified.erase(oldSeat);
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* notification = new ServerNotification(ServerNotificationType::addEntity, seat->getPlayer());
        notification->mPacket << getGameMap()->getNodeType();
        exportHeadersToPacket(notification->mPacket);
        exportToPacket(notification->mPacket, seat);
        notification->mPacket << previous.getObjectType() << previous.getName();
        ODServer::getSingleton().queueServerNotification(notification);
    }
}

void BuildingObject::setGhostRoomState(double fill,double alarm)
{
    if(mGhostFill==fill && mGhostAlarm==alarm) return;
    mGhostFill=fill;mGhostAlarm=alarm;
    fireRefresh();
}
void BuildingObject::exportToPacketForUpdate(ODPacket& packet,Seat* seat)
{
    RenderedMovableEntity::exportToPacketForUpdate(packet,seat);
    packet << mGhostFill << mGhostAlarm;
}
void BuildingObject::updateFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::updateFromPacket(packet);
    OD_ASSERT_TRUE(packet >> mGhostFill >> mGhostAlarm);
}
void BuildingObject::update(Ogre::Real seconds)
{
    RenderedMovableEntity::update(seconds);
    if(getIsOnServerMap()) return;
    if(mGhostFillNode!=nullptr) mGhostFillNode->setScale(1.0f,1.0f,static_cast<float>(std::max(0.0,std::min(1.0,mGhostFill))));
    mGhostAlarm=std::max(0.0,mGhostAlarm-seconds*ODApplication::turnsPerSecond*getGameMap()->getGameSpeedFactor());
    if(getMeshName()!="GhostBell" || getEntityNode()==nullptr) return;
    // While the bell rings (GhostBellSeconds) a red and a green alarm lamp beside it blink; no wall panel carries them.
    const bool flash=mGhostAlarm>0.0 && std::fmod(mGhostAlarm/ODApplication::turnsPerSecond,0.5)<0.25;
    if(mGhostLampNode==nullptr)
    {
        Ogre::SceneManager* scene=RenderManager::getSingleton().getSceneManager();
        Ogre::BillboardSet* lamps=scene->createBillboardSet(getOgreNamePrefix()+getName()+"_AlarmLamps",2);
        lamps->setMaterialName("ReactionParticleGlow");lamps->setDefaultDimensions(0.16f,0.16f);
        lamps->setCastShadows(false);lamps->setQueryFlags(0);
        lamps->createBillboard(Ogre::Vector3(-0.24f,0.06f,0.80f),Ogre::ColourValue(1.0f,0.12f,0.08f));
        lamps->createBillboard(Ogre::Vector3(0.24f,0.06f,0.80f),Ogre::ColourValue(0.2f,1.0f,0.3f));
        mGhostLampNode=getEntityNode()->createChildSceneNode();mGhostLampNode->attachObject(lamps);
    }
    mGhostLampNode->setVisible(flash);
}
void BuildingObject::destroyMeshLocal(NodeType type)
{
    if(mGhostFillNode!=nullptr)
    {
        Ogre::SceneManager* scene=RenderManager::getSingleton().getSceneManager();
        while(mGhostFillNode->numAttachedObjects()>0)
        {
            Ogre::MovableObject* object=mGhostFillNode->getAttachedObject(static_cast<unsigned short>(0));
            mGhostFillNode->detachObject(object);scene->destroyMovableObject(object);
        }
        scene->destroySceneNode(mGhostFillNode);mGhostFillNode=nullptr;
    }
    if(mGhostLampNode!=nullptr)
    {
        Ogre::SceneManager* scene=RenderManager::getSingleton().getSceneManager();
        while(mGhostLampNode->numAttachedObjects()>0)
        {
            Ogre::MovableObject* object=mGhostLampNode->getAttachedObject(static_cast<unsigned short>(0));
            mGhostLampNode->detachObject(object);scene->destroyMovableObject(object);
        }
        scene->destroySceneNode(mGhostLampNode);mGhostLampNode=nullptr;
    }
    if(mGhostHookPackNode!=nullptr)
    {
        // The holster node with the cannon first, then the pack itself
        Ogre::SceneManager* scene=RenderManager::getSingleton().getSceneManager();
        while(mGhostHookPackNode->numChildren()>0)
        {
            Ogre::SceneNode* child=static_cast<Ogre::SceneNode*>(mGhostHookPackNode->getChild(static_cast<unsigned short>(0)));
            while(child->numAttachedObjects()>0)
            {
                Ogre::MovableObject* object=child->getAttachedObject(static_cast<unsigned short>(0));
                child->detachObject(object);scene->destroyMovableObject(object);
            }
            scene->destroySceneNode(child);
        }
        while(mGhostHookPackNode->numAttachedObjects()>0)
        {
            Ogre::MovableObject* object=mGhostHookPackNode->getAttachedObject(static_cast<unsigned short>(0));
            mGhostHookPackNode->detachObject(object);scene->destroyMovableObject(object);
        }
        scene->destroySceneNode(mGhostHookPackNode);mGhostHookPackNode=nullptr;
    }
    RenderedMovableEntity::destroyMeshLocal(type);
}
