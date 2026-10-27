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

#ifndef ROOMTORTURE_H
#define ROOMTORTURE_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

class Creature;
class Seat;
class Tile;

enum class TileVisual;

class RoomTortureCreatureInfo
{
public:
    RoomTortureCreatureInfo() :
        mCreature(nullptr),
        mIsReady(false),
        mState(0)
    {}

    Creature* mCreature;
    bool mIsReady;
    uint32_t mState;
};

class RoomTorture: public Room
{
public:
    RoomTorture(GameMap* gameMap);

    RoomType getType() const override
    { return mRoomType; }

    bool shouldStopUseIfHungrySleepy(Creature& creature, bool forced) override
    { return false; }
    bool shouldNotUseIfBadMood(Creature& creature, bool forced) override
    { return false; }

    void doUpkeep() override;
    bool hasOpenCreatureSpot(Creature* creature) override;
    bool addCreatureUsingRoom(Creature* creature) override;
    void removeCreatureUsingRoom(Creature* creature) override;
    void absorbRoom(Room* room) override;
    //! \brief Uses the torture station and announces a converted class only on its first arrival.
    bool useRoom(Creature& creature, bool forced) override;

    bool isInContainment(Creature& creature) override;

    void creatureDropped(Creature& creature) override;

    void restoreInitialEntityState() override;

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;
    
    //! \brief A tortured or betraying enemy creature gives away one room of its owner that the keeper has not seen yet.
    //! \param keeperSeat The seat that tortures or imprisons the creature and learns the room
    //! \param creature The tortured or imprisoned creature
    static void revealEnemyInformation(Seat& keeperSeat, Creature& creature);

protected:
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
    void exportToStream(std::ostream& os) const override;
    bool importFromStream(std::istream& is) override;

private:
    //! \brief The broken enemy victim changes side: it joins the torturing seat and its captivity moods end.
    //! \param creature The victim that is converted
    void convertVictim(Creature& creature);

    std::map<Tile*,RoomTortureCreatureInfo> mCreaturesSpots;
    std::vector<std::string> mPrisonersLoad;
};

#endif // ROOMTORTURE_H
