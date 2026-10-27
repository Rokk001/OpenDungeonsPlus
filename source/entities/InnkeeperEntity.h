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

#ifndef INNKEEPERENTITY_H
#define INNKEEPERENTITY_H

#include "entities/RenderedMovableEntity.h"

#include <cstdint>
#include <string>

class GameMap;
class ODPacket;
class Tile;

//! \brief The clips of the innkeeper (besides the idle clip every entity has).
namespace InnkeeperPose
{
    //! The innkeeper pours a drink (plays for DrinkTurns turns).
    static const std::string pour = "Pour";
    //! The innkeeper cheers when a game in the tavern ends (plays for CHEER_TURNS turns).
    static const std::string cheer = "Cheer";
}

//! \brief The figure behind the counter of a tavern. It is not a creature: it has no wage, no hit points, cannot be
//! fought, picked up or slapped and blocks nothing. The tavern spawns it on its counter tile, tells it when a drink is
//! poured (onDrink) or a game ended (onCheer) and removes it with the room. The gold of a drink is booked by the tavern,
//! not by the figure. It is not saved by itself: the tavern saves where it stands and spawns it again when it is loaded.
class InnkeeperEntity: public RenderedMovableEntity
{
public:
    //! \brief Name of the mesh of the innkeeper.
    static const std::string MESH_NAME;
    //! \brief Number of turns the cheer clip plays when a game ends.
    static const uint32_t CHEER_TURNS;

    //! \brief Creates an innkeeper that is not on the map yet.
    //! \param gameMap The map the figure belongs to.
    //! \param roomName The name of the tavern; it is the base of the unique name of the figure.
    //! \param rotationAngle The angle (degrees) the figure is turned by, the same as the counter it stands behind.
    InnkeeperEntity(GameMap* gameMap, const std::string& roomName, Ogre::Real rotationAngle);
    //! \brief Creates an empty entity that is filled from a packet.
    InnkeeperEntity(GameMap* gameMap);

    //! \brief Returns GameEntityType::innkeeperEntity.
    virtual GameEntityType getObjectType() const override;

    //! \brief Server side. Counts down the pour and cheer clips and goes back to the idle clip when they are over.
    virtual void doUpkeep() override;

    //! \brief Server side. Puts a new innkeeper on the middle of the tile.
    //! \param gameMap The map to put the figure on.
    //! \param roomName The name of the tavern (see the constructor).
    //! \param tile The counter tile of the tavern; nothing happens if it is null.
    //! \param rotationAngle The angle (degrees) the figure is turned by.
    //! \return The new figure, nullptr if the tile is missing.
    static InnkeeperEntity* spawnOnTile(GameMap* gameMap, const std::string& roomName, Tile* tile, Ogre::Real rotationAngle);

    //! \brief Server side. Takes the figure off the map and deletes it. The caller must not use it afterwards.
    void removeFromRoom();

    //! \brief Server side. A drink is served: the figure pours for DrinkTurns turns.
    void onDrink();

    //! \brief Server side. A game ended: the figure cheers for CHEER_TURNS turns.
    void onCheer();

    //! \brief Creates the figure on a client from the packet of the server.
    static InnkeeperEntity* getInnkeeperEntityFromPacket(GameMap* gameMap, ODPacket& is);

private:
    //! \brief Server side. Plays a clip once and goes back to the idle clip afterwards.
    //! \param pose The clip to play.
    void playPose(const std::string& pose);

    //! \brief Turns the pour clip still has to play.
    uint32_t mPourTurns;
    //! \brief Turns the cheer clip still has to play.
    uint32_t mCheerTurns;
};

#endif // INNKEEPERENTITY_H
