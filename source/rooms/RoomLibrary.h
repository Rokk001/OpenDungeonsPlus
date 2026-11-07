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

#ifndef ROOMLIBRARY_H
#define ROOMLIBRARY_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

class Tile;

enum class TileVisual;
enum class SkillType;

//! \brief Stores tile state for a library.
class RoomLibraryTileData : public TileData
{
public:
    //! \brief Creates default library tile state.
    RoomLibraryTileData() :
        TileData()
    {}

    //! \brief Copies existing library tile state.
    RoomLibraryTileData(const RoomLibraryTileData* roomLibraryTileData) :
        TileData(roomLibraryTileData)
    {}

    virtual ~RoomLibraryTileData()
    {}

    virtual RoomLibraryTileData* cloneTileData() const override
    { return new RoomLibraryTileData(this); }

};

class RoomLibrary: public Room
{
public:
    RoomLibrary(GameMap* gameMap);

    RoomType getType() const override
    { return mRoomType; }

    void doUpkeep() override;
    bool hasOpenCreatureSpot(Creature* c) override;
    bool addCreatureUsingRoom(Creature* c) override;
    void removeCreatureUsingRoom(Creature* c) override;
    void absorbRoom(Room *r) override;
    //! \brief Earns research points using room research and the wearer's Scholar effect.
    bool useRoom(Creature& creature, bool forced) override;
    //! \brief Takes a research book only if the library has a bookshelf; it stays on the shelf until a researcher opens it.
    bool hasCarryEntitySpot(GameEntity* carriedEntity) override;
    //! \brief Directs the worker to a bookshelf of the library, never to a plain tile.
    Tile* askSpotForCarriedEntity(GameEntity* carriedEntity) override;
    //! \brief Puts a delivered research book onto the shelf.
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* carriedEntity) override;
    //! \brief Opens one research book on this library's shelves and credits its research points.
    //! \return true if a book was opened
    bool openResearchBook();

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;

    
protected:
    void exportToStream(std::ostream& os) const override;
    bool importFromStream(std::istream& is) override;

    RoomLibraryTileData* createTileData(Tile* tile) override;
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
private:
    //! \brief Returns the first tile carrying a bookshelf, or nullptr if the library has none.
    Tile* bookshelfTile();
    void getCreatureWantedPos(Creature* creature, Tile* tileSpot,
        Ogre::Real& wantedX, Ogre::Real& wantedY);
    std::vector<Tile*> mUnusedSpots;
    std::map<Creature*,Tile*> mCreaturesSpots;
    //! \brief Research points retain fractional work and equipment contributions.
    double mSkillPoints;
};

#endif // ROOMLIBRARY_H
