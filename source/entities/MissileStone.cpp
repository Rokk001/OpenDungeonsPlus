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

#include "entities/MissileStone.h"

#include "network/ODPacket.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"

#include <iostream>

MissileStone::MissileStone(GameMap* gameMap, Seat* seat, const std::string& meshName) :
    MissileObject(gameMap, seat, "PortalStone", meshName, Ogre::Vector3::ZERO, 0.0, nullptr, false, false)
{
    // The stone lies still
    stopMissile();
}

MissileStone::MissileStone(GameMap* gameMap) :
    MissileObject(gameMap)
{
}

//! \brief Configures an actual mission object without assigning it to a non-worker creature.
void MissileStone::configureTransport(const std::string& identity, int32_t seatId, int32_t x, int32_t y)
{
    mMissionIdentity = identity;
    mDeliverySeat = seatId;
    mDeliveryX = x;
    mDeliveryY = y;
    mDelivered = false;
}

//! \brief Resolves the configured destination for its own living worker, never a fighter.
Tile* MissileStone::getDeliveryTile(Creature& carrier) const
{
    if(mMissionIdentity.empty() || mDelivered || !carrier.isAlive() ||
       !carrier.getDefinition()->isWorker() || carrier.getSeat() == nullptr ||
       carrier.getSeat()->getId() != mDeliverySeat)
        return nullptr;
    return getGameMap()->getTile(mDeliveryX, mDeliveryY);
}

//! \brief Uses the established bonus-object pickup priority only for an available worker transport.
EntityCarryType MissileStone::getEntityCarryType(Creature* carrier)
{
    if(carrier == nullptr || mCarried || getDeliveryTile(*carrier) == nullptr)
        return EntityCarryType::notCarryable;
    return EntityCarryType::giftBox;
}

//! \brief Keeps one physical item while handing its mesh to the worker's normal carry node.
void MissileStone::notifyEntityCarryOn(Creature* carrier)
{
    if(carrier == nullptr || getEntityCarryType(carrier) == EntityCarryType::notCarryable)
        return;
    removeEntityFromPositionTile();
    setSeat(carrier->getSeat());
    mCarried = true;
}

//! \brief Re-enables ground pickup after interruption and records delivery only at the configured tile.
void MissileStone::notifyEntityCarryOff(const Ogre::Vector3& position)
{
    mPosition = position;
    mCarried = false;
    addEntityToPositionTile();
    Tile* tile = getPositionTile();
    mDelivered = tile != nullptr && tile->getX() == mDeliveryX && tile->getY() == mDeliveryY;
}

//! \brief Persists identity, destination and real delivery; an in-flight item reloads at its current tile.
void MissileStone::exportToStream(std::ostream& os) const
{
    MissileObject::exportToStream(os);
    if(!mMissionIdentity.empty())
        os << "MissionTransport\t" << mMissionIdentity << "\t" << mDeliverySeat << "\t"
           << mDeliveryX << "\t" << mDeliveryY << "\t" << mDelivered << "\t";
}

//! \brief Accepts old stones and validates optional mission transport data without recreating a carrier.
bool MissileStone::importFromStream(std::istream& is)
{
    if(!MissileObject::importFromStream(is))
        return false;
    is >> std::ws;
    if(is.eof())
    {
        is.clear(is.rdstate() & ~std::ios::eofbit);
        return true;
    }
    std::string marker;
    int32_t delivered;
    if(!(is >> marker >> mMissionIdentity >> mDeliverySeat >> mDeliveryX >> mDeliveryY >> delivered) ||
       marker != "MissionTransport" || mDeliverySeat < 0 || mDeliveryX < 0 || mDeliveryY < 0 ||
       (delivered != 0 && delivered != 1))
        return false;
    mDelivered = delivered != 0;
    mCarried = false;
    return true;
}

MissileStone* MissileStone::getMissileStoneFromStream(GameMap* gameMap, std::istream& is)
{
    MissileStone* obj = new MissileStone(gameMap);
    obj->importFromStream(is);
    return obj;
}

MissileStone* MissileStone::getMissileStoneFromPacket(GameMap* gameMap, ODPacket& is)
{
    MissileStone* obj = new MissileStone(gameMap);
    obj->importFromPacket(is);
    return obj;
}
