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

#ifndef ROOMTREASURY_H
#define ROOMTREASURY_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

#include <map>

enum class TileVisual;

//! \brief Per-tile treasury storage, including fractional admission gold.
class RoomTreasuryTileData : public TileData
{
public:
    RoomTreasuryTileData() :
        TileData(),
        mGoldInTile(0)
    {}

    RoomTreasuryTileData(const RoomTreasuryTileData* roomTreasuryTileData) :
        TileData(roomTreasuryTileData),
        mGoldInTile(roomTreasuryTileData->mGoldInTile),
        mMeshOfTile(roomTreasuryTileData->mMeshOfTile)
    {}

    virtual ~RoomTreasuryTileData()
    {}

    virtual RoomTreasuryTileData* cloneTileData() const override
    { return new RoomTreasuryTileData(this); }

    //! \brief Stored gold retains fractional infirmary admission payments.
    double mGoldInTile;
    std::string mMeshOfTile;
};

//! \brief Stores and transfers keeper gold without losing fractional payments.
class RoomTreasury: public Room
{
    friend class ODClient;
public:
    RoomTreasury(GameMap* gameMap);

    virtual RoomType getType() const override
    { return mRoomType; }


   
    // Functions overriding virtual functions in the Room base class.
    //! \brief Releases the removed tile's exact gold as a loose pile.
    bool removeCoveredTile(Tile* t) override;

    //! \brief The gold counted by a treasury is the gold in every tile it has data for,
    //! which includes the tiles it has handed over, so it has to let go of theirs.
    void splitRoom(Room& newRoom, const std::vector<Tile*>& tiles) override;

    // Functions specific to this class.
    virtual void doUpkeep() override;

    bool hasCarryEntitySpot(GameEntity* carriedEntity) override;
    Tile* askSpotForCarriedEntity(GameEntity* carriedEntity) override;
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* carriedEntity) override;

    virtual int getTotalGoldStorage() const override;
    //! \brief Returns all stored gold without truncating fractional payments.
    virtual double getTotalGoldStored() const override;
    //! \brief Deposits gold and returns the amount stored, including fractions.
    virtual double depositGold(double gold, Tile *tile) override;
    //! \brief Withdraws up to the requested gold, including fractions.
    virtual double withdrawGold(double gold) override;

    static int32_t getRoomCostForPlayer(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles);

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;
    
protected:
    RoomTreasuryTileData* createTileData(Tile* tile) override;
    // Because treasury do not use active spots, we don't want the default
    // behaviour (removing the active spot tile) as it could result in removing an
    // unwanted treasury
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override
    {}

private:
    int getGoldCapacityPerTile() const;
    //! \brief Fill step of the tile at the given position, 0 for tiles that are not part of this room
    int getLevelOfTile(const std::map<Tile*, int>& levels, int x, int y) const;
    //! \brief Refreshes a pile's visual tier without changing its exact stored value.
    void updateMeshesForTile(Tile* tile, RoomTreasuryTileData* roomTreasuryTileData,
        const std::map<Tile*, int>& levels);
    bool mGoldChanged;
    //! The clients were told that the treasury is full (cosmetic only, until room is not full again)
    bool mFullAnnounced;
};

#endif // ROOMTREASURY_H
