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

#ifndef BUILDINGOBJECT_H
#define BUILDINGOBJECT_H

#include "entities/RenderedMovableEntity.h"
#include "entities/ItemDefinition.h"
#include <OgreVector2.h>

#include <string>
#include <iosfwd>

class Building;
class Creature;
class Room;
class GameMap;
class Tile;
class ODPacket;

//! \brief Renders room furniture and decorative goods with their transmitted appearance.
class BuildingObject: public RenderedMovableEntity
{
public:
    BuildingObject(GameMap* gameMap, Building& building, const std::string& meshName, Tile* targetTile,
        Ogre::Real x, Ogre::Real y, Ogre::Real z, Ogre::Real rotationAngle, bool hideCoveredTile,
        float opacity = 1.0f, const std::string& initialAnimationState = "", bool initialAnimationLoop = true);
    BuildingObject(GameMap* gameMap, Building& building, const std::string& meshName,
        Tile& targetTile, Ogre::Real rotationAngle, bool hideCoveredTile, float opacity = 1.0f,
        const std::string& initialAnimationState = "", bool initialAnimationLoop = true);
    BuildingObject(GameMap* gameMap);

    virtual GameEntityType getObjectType() const override;

    void doUpkeep() override;

    void addParticleEffect(const std::string& effectScript, uint32_t nbTurns);

    void fireRefresh();

    //! \brief Sends this object and the previous identity together to current tile viewers only.
    virtual void notifyReplacement(BuildingObject& previous);

    const Ogre::Vector2& getFurnitureScale() const { return mFurnitureScale; }
    void setFurnitureScale(const Ogre::Vector2& scale) { mFurnitureScale = scale; }
    //! \brief Marks a decorative table bag for the shared quality and wax-seal material treatment.
    void setItemBagAppearance(Quality quality, bool sealed)
    { mItemBagQuality = static_cast<int32_t>(quality); mItemBagSealed = sealed; }
    //! \brief Writes furniture scale and optional decorative bag presentation.
    void exportToPacket(ODPacket& os, const Seat* seat) const override;
    //! \brief Reads furniture scale and optional decorative bag presentation.
    void importFromPacket(ODPacket& is) override;

    static BuildingObject* getBuildingObjectFromPacket( GameMap* gameMap,   ODPacket& is);

protected:
    //! \brief Builds normal furniture, then styles any decorative merchant bag using the shared renderer.
    void createMeshLocal(NodeType type = NodeType::MTILES_NODE) override;

private:
    Ogre::Vector2 mFurnitureScale = Ogre::Vector2::ZERO;
    //! \brief Negative means ordinary furniture; otherwise this is a decorative bag quality.
    int32_t mItemBagQuality = -1;
    bool mItemBagSealed = false;
};

#endif // BUILDINGOBJECT_H
