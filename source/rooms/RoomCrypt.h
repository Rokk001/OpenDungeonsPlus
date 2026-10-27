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

#ifndef ROOMCRYPT_H
#define ROOMCRYPT_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

class InputCommand;
class InputManager;

enum class TileVisual;

//! \brief Holds delivered bodies and raises liches from FIFO groups of fully decayed corpse levels.
class RoomCrypt: public Room
{
public:
    //! \brief Creates an empty crypt with no accumulated corpse levels.
    RoomCrypt(GameMap* gameMap);

    virtual RoomType getType() const override
    { return mRoomType; }

    //! \brief Combines grave reservations and FIFO corpse levels when crypts join.
    void absorbRoom(Room *r) override;

    //! \brief Maintains the crypt and its existing ambient spiders; bodies own their decay clocks.
    void doUpkeep() override;

    //! \brief Tests for a reachable free grave accepting an intact dead non-worker.
    bool hasCarryEntitySpot(GameEntity* carriedEntity) override;
    //! \brief Reserves a reachable grave and returns its worker delivery tile.
    Tile* askSpotForCarriedEntity(GameEntity* carriedEntity) override;
    //! \brief Confirms delivery or releases an interrupted reservation without restarting corpse time.
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* carriedEntity) override;

    //! \brief Returns the reserved grave for a delivered uncarried corpse, or nullptr.
    Tile* getCorpseSpot(const Creature& creature) const;
    //! \brief Frees a corpse reservation and restores its tile registration, also used by revival.
    void removeCorpse(Creature& creature);
    //! \brief Removes a decayed body and raises any affordable FIFO groups at its released grave.
    void notifyCorpseDecayed(Creature& creature);
    //! \brief Rebinds saved grave occupants by name after all creatures and furniture exist.
    void restoreInitialEntityState() override;

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;
protected:
    //! \brief Writes the legacy zero followed by optional FIFO levels and grave occupants.
    virtual void exportToStream(std::ostream& os) const override;
    //! \brief Reads legacy crypts and optional tags without consuming the next room record.
    virtual bool importFromStream(std::istream& is) override;

    //! \brief Creates crypt furniture and an empty grave reservation for each central spot.
    virtual BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Releases a removed grave while leaving its body in its current phase.
    virtual void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
private:
    //! \brief Gets the tile where a worker delivers a corpse for the given grave spot.
    //! \param spot The grave spot.
    //! \return The default delivery tile, or the first free neighbouring tile of this crypt if a
    //! building object stands on it. nullptr if no such tile exists.
    Tile* getDeliveryTile(Tile* spot);
    std::map<Tile*, Creature*> mRottingCreatures;
    std::vector<unsigned int> mCorpseLevels;
    std::map<std::pair<int, int>, std::string> mCorpseSpotNames;
};

#endif // ROOMCRYPT_H
