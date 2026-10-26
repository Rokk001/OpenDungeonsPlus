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

#ifndef ROOMWORKSHOP_H
#define ROOMWORKSHOP_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

enum class TrapType;
enum class TileVisual;
class GiftBoxItem;

class RoomWorkshopTileData : public TileData
{
public:
    RoomWorkshopTileData() :
        TileData(),
        mCanHaveCraftedTrap(true)
    {}

    RoomWorkshopTileData(const RoomWorkshopTileData* roomWorkshopTileData) :
        TileData(roomWorkshopTileData),
        mCanHaveCraftedTrap(roomWorkshopTileData->mCanHaveCraftedTrap)
    {}

    virtual ~RoomWorkshopTileData()
    {}

    virtual RoomWorkshopTileData* cloneTileData() const override
    { return new RoomWorkshopTileData(this); }

    bool mCanHaveCraftedTrap;
};

//! \brief Crafts traps and cracks researched item boxes using the existing workshop work cycle.
class RoomWorkshop: public Room{
public:
    RoomWorkshop(GameMap* gameMap);

    RoomType getType() const override
    { return mRoomType; }

    //! \brief Advances box cracking before starting the next trap job.
    void doUpkeep() override;
    //! \brief Accepts item boxes only when this workshop has tools and a centre spot.
    bool hasCarryEntitySpot(GameEntity* entity) override;
    //! \brief Returns an available centre tile for delivery of an item box.
    Tile* askSpotForCarriedEntity(GameEntity* entity) override;
    //! \brief Retains delivered boxes on the workshop floor for the next crack job.
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* entity) override;
    //! \brief Returns whether the current job cracks an item box.
    bool hasCrackJob() const { return mCrackBox != nullptr; }
    //! \brief Returns the configured crack effort with the matching researched tools multiplier.
    double getNeededCrackPoints() const;
    //! \brief Returns the trap type currently being crafted, or TrapType::nullTrapType if
    //! the workshop is idle.
    TrapType getCurrentProductionType() const { return mTrapType; }
    //! \brief Returns whole work points for the production display; fractional progress stays stored.
    int32_t getProductionPoints() const { return static_cast<int32_t>(mPoints); }
    //! \brief Allows work on trap or box jobs when a centre work spot is available.
    bool hasOpenCreatureSpot(Creature* c) override;
    bool addCreatureUsingRoom(Creature* c) override;
    void removeCreatureUsingRoom(Creature* c) override;
    //! \brief Combines workshop work progress and retains pending box ownership during room merging.
    void absorbRoom(Room *r) override;
    //! \brief Earns fractional workshop points using research and the wearer's Craftsman effect.
    bool useRoom(Creature& creature, bool forced) override;

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;
    
protected:
    //! \brief Saves trap work and optional pending box work after normal room data.
    void exportToStream(std::ostream& os) const override;
    //! \brief Reads workshop work while accepting old records without a box job.
    bool importFromStream(std::istream& is) override;

    RoomWorkshopTileData* createTileData(Tile* tile) override;
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
private:
    //!\brief checks if a tile is available in the workshop to place a new crafted trap
    uint32_t countCraftedItemsOnRoom();
    Tile* checkIfAvailableSpot();
    //! \brief Work points retain fractional research and equipment contributions.
    double mPoints;
    //! \brief The current box job, its stable save name and fractional work progress.
    GiftBoxItem* mCrackBox = nullptr;
    std::string mCrackBoxName;
    double mCrackPoints = 0.0;
    TrapType mTrapType;
    void getCreatureWantedPos(Creature* creature, Tile* tileSpot,
        Ogre::Real& wantedX, Ogre::Real& wantedY);
    std::vector<Tile*> mUnusedSpots;
    std::map<Creature*,Tile*> mCreaturesSpots;
};

#endif // ROOMWORKSHOP_H
