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

#ifndef MISSILESTONE_H
#define MISSILESTONE_H

#include "entities/MissileObject.h"

#include <string>
#include <iosfwd>

class GameMap;
class ODPacket;

//! \brief The portal stone of a level: an object that lies on a tile. A level script puts it
//! where the creature that carried it died, or where the quest ends. It is stored with the
//! missiles of a level; configured mission items use the existing visible worker carry node.
class MissileStone: public MissileObject
{
public:
    //! \brief Creates a stationary stone without inventing a transport destination.
    MissileStone(GameMap* gameMap, Seat* seat, const std::string& meshName);
    //! \brief Creates a legacy-compatible stone for stream or packet loading.
    MissileStone(GameMap* gameMap);

    virtual MissileObjectType getMissileType() const override
    { return MissileObjectType::stone; }

    virtual bool staysWhenStopped() const override
    { return true; }

    //! \brief Assigns the exact mission identity, receiving seat and destination tile.
    void configureTransport(const std::string& identity, int32_t seatId, int32_t x, int32_t y);
    //! \brief Returns the configured tile only for a living worker of the receiving seat.
    Tile* getDeliveryTile(Creature& carrier) const;
    //! \brief Allows loose configured items to use the existing worker transport priority.
    EntityCarryType getEntityCarryType(Creature* carrier) override;
    //! \brief Removes a transported item from ground selection while the worker visibly carries it.
    void notifyEntityCarryOn(Creature* carrier) override;
    //! \brief Drops the same item at the current worker position, preserving identity and destination.
    void notifyEntityCarryOff(const Ogre::Vector3& position) override;
    //! \brief Returns the stable mission identity, independent of carrier names.
    const std::string& getMissionIdentity() const { return mMissionIdentity; }
    //! \brief Reports actual delivery of this item rather than arrival of a marked creature.
    bool isDelivered() const { return mDelivered; }

    static MissileStone* getMissileStoneFromStream(GameMap* gameMap, std::istream& is);
    static MissileStone* getMissileStoneFromPacket(GameMap* gameMap, ODPacket& is);
protected:
    //! \brief Saves optional transport metadata; carried objects retain their current ground coordinates.
    void exportToStream(std::ostream& os) const override;
    //! \brief Loads optional transport metadata while accepting old stationary stones.
    bool importFromStream(std::istream& is) override;

private:
    std::string mMissionIdentity;
    int32_t mDeliverySeat = -1;
    int32_t mDeliveryX = -1;
    int32_t mDeliveryY = -1;
    bool mCarried = false;
    bool mDelivered = false;
};

#endif // MISSILESTONE_H
