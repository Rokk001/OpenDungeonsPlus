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

#ifndef DIRTPILEENTITY_H
#define DIRTPILEENTITY_H

#include "entities/RenderedMovableEntity.h"

#include <iosfwd>
#include <string>

class GameMap;
class ODPacket;
class Tile;

//! \brief The kinds of dirt that lie on a tile as an entity of their own.
enum class DirtPileKind
{
    //! A creature relieved itself here. Stays until a worker cleans it.
    pile,
    //! A creature died here. Dries by itself after BloodDryTurns (global.cfg).
    blood,
    //! A drunk creature vomited here. One mesh for every creature type; stays until a worker cleans it like a pile.
    vomit,
    //! A collapsed skeleton, retained until a worker cleans it.
    bones
};

//! \brief A pile or blood stain on the floor of a tile. It is not pickable, not carryable, has no health and
//! blocks nothing; workers remove it by cleaning. Creating a pile sets the dirt of its tile to the maximum.
//! A tile holds at most one entity per kind, except for collapsed skeletons.
class DirtPileEntity: public RenderedMovableEntity
{
public:
    //! \brief Prefix of the mesh name of a pile; the class name of the creature that left it follows.
    static const std::string PILE_MESH_PREFIX;
    //! \brief Mesh name of a blood stain.
    static const std::string BLOOD_MESH_NAME;
    //! \brief Mesh name of vomit.
    static const std::string VOMIT_MESH_NAME;
    //! \brief The value of mDirtLeft a new or refreshed pile or stain starts with.
    static const double DIRT_LEFT_START;

    //! \brief Creates a pile or blood stain that is not on the map yet.
    //! \param kind Pile, blood, vomit or collapsed skeleton.
    //! \param creatureClass Class name of the creature that left it (selects the mesh of a pile).
    //! \param rotationAngle Facing in degrees; used for a collapsed skeleton.
    //! \param scale Size of a collapsed skeleton.
    DirtPileEntity(GameMap* gameMap, DirtPileKind kind, const std::string& creatureClass,
                   Ogre::Real rotationAngle = 0.0f, double scale = 1.0);
    //! \brief Creates an empty entity that is filled from a packet or a stream.
    DirtPileEntity(GameMap* gameMap);

    virtual GameEntityType getObjectType() const override;

    //! \brief Server side. Ages a blood stain and removes it when it has dried; removes an emptied pile.
    virtual void doUpkeep() override;

    //! \brief Puts a pile or stain of the given kind on the tile (server side). When the tile already has one of that
    //! kind, its dirt left is set back to the start value instead. A new pile sets the dirt of the tile to the maximum.
    //! \return The new or refreshed entity, nullptr if the tile is missing.
    static DirtPileEntity* createOnTile(GameMap* gameMap, Tile* tile, DirtPileKind kind, const std::string& creatureClass);

    //! \brief Leaves a cleanable skeleton at its final position, facing and size.
    static DirtPileEntity* createBones(GameMap* gameMap, Tile* tile, const Ogre::Vector3& position,
                                       Ogre::Real rotationAngle, double scale);

    //! \brief Returns the scale of the collapsed skeleton.
    double getBoneScale() const { return mBoneScale; }

    //! \brief Returns the pile or stain of the given kind that lies on the tile, nullptr if there is none.
    static DirtPileEntity* getEntityOnTile(const Tile* tile, DirtPileKind kind);

    //! \brief Returns the kind of this entity.
    inline DirtPileKind getKind() const
    { return mKind; }

    //! \brief Returns the class name of the creature that left this entity.
    inline const std::string& getCreatureClass() const
    { return mCreatureClass; }

    //! \brief Returns how much of this pile or stain is left to clean (0 - DIRT_LEFT_START).
    inline double getDirtLeft() const
    { return mDirtLeft; }

    //! \brief Returns the turns a blood stain has lain here.
    inline double getAgeTurns() const
    { return mAgeTurns; }

    //! \brief Server side. Removes cleaning work from this entity. The entity removes itself from the map when nothing
    //! is left to clean.
    //! \param amount The cleaning work done.
    //! \return True if the entity is gone now (the caller must not use it anymore).
    bool cleanBy(double amount);

    //! \brief Sets the values read from a saved game.
    void restoreState(double dirtLeft, double ageTurns);

    //! \brief Returns the mesh name for an entity of the given kind and creature class.
    static std::string getMeshNameFor(DirtPileKind kind, const std::string& creatureClass);

    //! \brief Saves dirt state, including the position, rotation and scale of a collapsed skeleton.
    void exportToSaveStream(std::ostream& os) const;
    //! \brief Reads a line written by exportToSaveStream and puts the entity on the map (server side).
    //! \return False if the line is malformed or its tile does not exist.
    static bool importFromSaveStream(GameMap* gameMap, std::istream& is);

    //! \brief Returns the text of a kind as used in the saved dirt piles.
    static std::string kindToString(DirtPileKind kind);
    //! \brief Reads the text of a kind; returns false if it is unknown.
    static bool kindFromString(const std::string& text, DirtPileKind& kind);

    static DirtPileEntity* getDirtPileEntityFromPacket(GameMap* gameMap, ODPacket& is);

protected:
    //! \brief Sends dirt state and the size of a collapsed skeleton to a client.
    virtual void exportToPacket(ODPacket& os, const Seat* seat) const override;
    //! \brief Restores dirt state and skeleton size from a server packet.
    virtual void importFromPacket(ODPacket& is) override;

private:
    //! \brief Pile, blood, vomit or collapsed skeleton.
    DirtPileKind mKind;
    //! \brief Class name of the creature that left this entity.
    std::string mCreatureClass;
    //! \brief What is left to clean; starts at DIRT_LEFT_START.
    double mDirtLeft;
    //! \brief Turns this entity lay on the map (counted for blood only).
    double mAgeTurns;
    //! \brief The size of a collapsed skeleton, matching its former creature.
    double mBoneScale;
};

#endif // DIRTPILEENTITY_H
