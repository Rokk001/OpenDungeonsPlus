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
    if(getMeshName()!="GhostWallGauges" || getEntityNode()==nullptr) return;
    const bool flash=mGhostAlarm>0.0 && std::fmod(mGhostAlarm/ODApplication::turnsPerSecond,0.5)<0.25;
    for(unsigned short index=0;index<getEntityNode()->numAttachedObjects();++index)
    {
        Ogre::MovableObject* object=getEntityNode()->getAttachedObject(index);
        if(object->getMovableType()!="Entity") continue;
        Ogre::Entity* entity=static_cast<Ogre::Entity*>(object);
        for(unsigned int sub=0;sub<entity->getNumSubEntities();++sub)
            if(entity->getSubEntity(sub)->getMaterialName()=="GhostLamps") entity->getSubEntity(sub)->setVisible(flash);
    }
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
    RenderedMovableEntity::destroyMeshLocal(type);
}
