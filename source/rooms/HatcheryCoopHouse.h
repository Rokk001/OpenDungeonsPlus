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

#ifndef HATCHERYCOOPHOUSE_H
#define HATCHERYCOOPHOUSE_H

#include <OgreVector3.h>

#include <cstdint>
#include <string>

//! \brief Fixed points of the coop mesh ChickenCoopHouse (models/ChickenCoopHouse.mesh, skeleton with the clips
//! Door and Idle). All offsets are in the frame of the coop: x and y from the center of the coop tile, z from the
//! floor, the coop is not rotated. The two nests lie on the ground next to the ramp, the roof lookout is a plank
//! over the roof ridge.
namespace HatcheryCoopHouse
{
    //! The mesh the hatchery puts on its center tiles, and the old coop mesh (kept for the editor and old data).
    static const std::string meshName = "ChickenCoopHouse";
    static const std::string oldMeshName = "ChickenCoop";

    //! The door clip of the skeleton, played once when an animal comes out.
    static const std::string doorClip = "Door";

    //! True for both coop meshes.
    inline bool isCoopMesh(const std::string& name)
    {
        return (name == meshName) || (name == oldMeshName);
    }

    //! The rooster's spot on the roof lookout: distance along the tile from the center and height above the floor.
    static const double roofPerchOffset = 0.3;
    static const double roofPerchHeight = 0.975;

    static const uint32_t nestCount = 2;
    static const uint32_t eggsPerNest = 3;

    //! Center of a nest (straw ring) on the floor, relative to the coop tile center.
    inline Ogre::Vector3 nestCenter(uint32_t nest)
    {
        return Ogre::Vector3(0.66f, (nest % nestCount == 0) ? -0.272f : 0.272f, 0.0f);
    }

    //! Where an egg lies in a nest (egg 0 .. eggsPerNest - 1), relative to the coop tile center. The height is the
    //! middle of an egg on the straw. The eggs of the hatchery can be put here.
    inline Ogre::Vector3 nestEggSpot(uint32_t nest, uint32_t egg)
    {
        static const float offsets[3][2] = {{-0.035f, -0.025f}, {0.04f, -0.02f}, {0.0f, 0.04f}};
        const uint32_t slot = egg % eggsPerNest;
        return nestCenter(nest) + Ogre::Vector3(offsets[slot][0], offsets[slot][1], 0.03f);
    }

    //! Same as nestEggSpot, in the world, for the coop on the tile at (tileX, tileY).
    inline Ogre::Vector3 nestEggSpotWorld(int tileX, int tileY, uint32_t nest, uint32_t egg)
    {
        return Ogre::Vector3(static_cast<Ogre::Real>(tileX), static_cast<Ogre::Real>(tileY), 0.0f) + nestEggSpot(nest, egg);
    }
}

#endif // HATCHERYCOOPHOUSE_H
