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

#ifndef TREASURYOBJECT_H
#define TREASURYOBJECT_H

#include "entities/RenderedMovableEntity.h"

#include <string>
#include <iosfwd>

class Creature;
class GameMap;
class ODPacket;
class Room;

//! \brief A carried or loose gold pile whose value retains fractional payments.
class TreasuryObject: public RenderedMovableEntity
{
public:
    //! \brief Creates a loose pile retaining fractional admission gold.
    TreasuryObject(GameMap* gameMap, double goldValue);
    TreasuryObject(GameMap* gameMap);

    virtual void doUpkeep() override;

    virtual GameEntityType getObjectType() const override;

    virtual bool tryPickup(Seat* seat) override;
    virtual bool tryDrop(Seat* seat, Tile* tile) override;
    virtual void drop(const Ogre::Vector3& v) override;

    //! \brief Sets the seat of the player who dropped this gold from the hand. If an own
    //! creature owed a wage is on the tile, the gold pays that wage during the next upkeep.
    void setDropSeat(Seat* seat)
    { mDropSeat = seat; }
    void mergeGold(TreasuryObject* obj);

    //! \brief Called when a creature tries to steal gold. value represents
    //! the amount the creature wants to steal.
    //! Returns the gold stolen
    double stealGold(Creature& creature, double value);

    virtual EntityCarryType getEntityCarryType(Creature* carrier) override;
    virtual void notifyEntityCarryOn(Creature* carrier) override;
    virtual void notifyEntityCarryOff(const Ogre::Vector3& position) override;

    //! \brief Selects the existing visual tier for a possibly fractional gold amount.
    static const char* getMeshNameForGold(double gold);

    static std::string getTreasuryObjectStreamFormat();
    static TreasuryObject* getTreasuryObjectFromStream(GameMap* gameMap, std::istream& is);
    static TreasuryObject* getTreasuryObjectFromPacket(GameMap* gameMap, ODPacket& is);

    virtual void addEntityToPositionTile(GameMap *gameMap = nullptr) override;

protected:
    //! \brief Writes the pile with enough precision to restore its exact value.
    virtual void exportToStream(std::ostream& os) const override;
    virtual bool importFromStream(std::istream& is) override;
    virtual void exportToPacket(ODPacket& os, const Seat* seat) const override;
    virtual void importFromPacket(ODPacket& is) override;

private:
    //! \brief The exact gold in this pile.
    double mGoldValue;
    bool mHasGoldValueChanged;
    Seat* mDropSeat;
    bool mDroppedByHand;
};

#endif // TREASURYOBJECT_H
 
