#ifndef ROOMOBJECTNAVIGATION_H
#define ROOMOBJECTNAVIGATION_H

#include "gamemap/RoomObjectPath.h"

class GameMap;
class Creature;
class BuildingObject;
class Room;

namespace RoomObjectNavigation
{
float clearance(const Creature& creature);
std::vector<RoomObjectPath::Obstacle> collect(GameMap& map, float clearance,
    const BuildingObject* interaction = nullptr);
std::vector<RoomObjectPath::Obstacle> bodyObstacles(Creature& creature,
    const BuildingObject* interaction = nullptr);
bool standingPosition(const std::vector<RoomObjectPath::Obstacle>& obstacles,
    const Ogre::Vector2& wanted, Ogre::Vector2& result);
//! \brief Spaces a server destination; adjacent expands reachable tile rings, optionally restricted to the supplied room.
bool separate(Creature& creature, std::vector<Ogre::Vector2>& path, bool adjacent = false, const Room* room = nullptr);
//! \brief Finds a reachable feeding stance, preferring measured body separation before crowded fallback.
bool foodApproach(Creature& creature, const Ogre::Vector2& food, std::vector<Ogre::Vector2>& path);
//! \brief Prefers clear working bodies, then retains the original valid room-reserved placement when crowded.
bool workApproach(Creature& creature, const BuildingObject& object, const Ogre::Vector2& wanted,
    const Ogre::Vector2& facingOffset, std::vector<Ogre::Vector2>& path);
bool refine(Creature& creature, std::vector<Ogre::Vector2>& path);
bool blocked(Creature& creature, const std::vector<Ogre::Vector2>& path, bool includeWalkDistortion = false);
}

#endif
