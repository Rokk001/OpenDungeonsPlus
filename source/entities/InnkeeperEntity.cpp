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

#include "entities/InnkeeperEntity.h"

#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

const std::string InnkeeperEntity::MESH_NAME = "Innkeeper";
const uint32_t InnkeeperEntity::CHEER_TURNS = 2;

//! \brief Name of the figure used for the unique entity name when the room name is empty.
static const std::string INNKEEPER_FALLBACK_NAME = "Innkeeper";
//! \brief Config key of the [Tavern] block with the turns a drink takes (and the pour clip plays).
static const std::string DRINK_TURNS_KEY = "DrinkTurns";

InnkeeperEntity::InnkeeperEntity(GameMap* gameMap, const std::string& roomName, Ogre::Real rotationAngle) :
    RenderedMovableEntity(gameMap, roomName.empty() ? INNKEEPER_FALLBACK_NAME : roomName + "_" + INNKEEPER_FALLBACK_NAME,
        MESH_NAME, rotationAngle, false),
    mPourTurns(0),
    mCheerTurns(0)
{
    // The figure starts standing; a client that sees it later is told this state with the entity
    mPrevAnimationState = EntityAnimation::idle_anim;
    mPrevAnimationStateLoop = true;
}

InnkeeperEntity::InnkeeperEntity(GameMap* gameMap) :
    RenderedMovableEntity(gameMap),
    mPourTurns(0),
    mCheerTurns(0)
{
    setMeshName(MESH_NAME);
}

GameEntityType InnkeeperEntity::getObjectType() const
{
    return GameEntityType::innkeeperEntity;
}

void InnkeeperEntity::doUpkeep()
{
    if(!getIsOnMap())
        return;

    const bool wasBusy = (mPourTurns > 0) || (mCheerTurns > 0);
    if(mPourTurns > 0)
        --mPourTurns;
    if(mCheerTurns > 0)
        --mCheerTurns;

    if(wasBusy && (mPourTurns == 0) && (mCheerTurns == 0))
        setAnimationState(EntityAnimation::idle_anim, true);
}

InnkeeperEntity* InnkeeperEntity::spawnOnTile(GameMap* gameMap, const std::string& roomName, Tile* tile, Ogre::Real rotationAngle)
{
    if((gameMap == nullptr) || (tile == nullptr))
        return nullptr;

    InnkeeperEntity* innkeeper = new InnkeeperEntity(gameMap, roomName, rotationAngle);
    innkeeper->addToGameMap();
    Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(tile->getX()), static_cast<Ogre::Real>(tile->getY()), 0.0f);
    innkeeper->createMesh();
    innkeeper->setPosition(spawnPosition);
    return innkeeper;
}

void InnkeeperEntity::removeFromRoom()
{
    removeFromGameMap();
    deleteYourself();
}

void InnkeeperEntity::onDrink()
{
    mPourTurns = static_cast<uint32_t>(ConfigManager::getSingleton().getTavernConfigDouble(DRINK_TURNS_KEY));
    mCheerTurns = 0;
    if(mPourTurns > 0)
        playPose(InnkeeperPose::pour);
}

void InnkeeperEntity::onCheer()
{
    mCheerTurns = CHEER_TURNS;
    mPourTurns = 0;
    playPose(InnkeeperPose::cheer);
}

void InnkeeperEntity::playPose(const std::string& pose)
{
    setAnimationState(pose, false, Ogre::Vector3::ZERO, true);
}

InnkeeperEntity* InnkeeperEntity::getInnkeeperEntityFromPacket(GameMap* gameMap, ODPacket& is)
{
    InnkeeperEntity* innkeeper = new InnkeeperEntity(gameMap);
    innkeeper->importFromPacket(is);
    return innkeeper;
}
