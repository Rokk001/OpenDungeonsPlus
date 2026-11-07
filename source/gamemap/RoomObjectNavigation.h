#ifndef ROOMOBJECTNAVIGATION_H
#define ROOMOBJECTNAVIGATION_H

#include "gamemap/RoomObjectPath.h"

#include <map>

class GameMap;
class Creature;
class BuildingObject;
class Tile;
class Room;

namespace RoomObjectNavigation
{
// Returns the radius of the circle that a creature needs around itself, including its level.
float clearance(const Creature& creature);
// Returns the furniture of all rooms as obstacles, widened by the clearance. The
// interaction object, which a creature may enter, and walkable landmarks are left out.
std::vector<RoomObjectPath::Obstacle> collect(GameMap& map, float clearance,
    const BuildingObject* interaction = nullptr);
// Like collect(), but with the real walking body of the creature instead of a plain clearance.
std::vector<RoomObjectPath::Obstacle> bodyObstacles(Creature& creature,
    const BuildingObject* interaction = nullptr);
// Finds the point nearest to the wanted one where nothing blocks a creature; returns
// false if there is none in the tile.
bool standingPosition(const std::vector<RoomObjectPath::Obstacle>& obstacles,
    const Ogre::Vector2& wanted, Ogre::Vector2& result);
//! \brief Tells whether the creature can stand somewhere in the tile without touching room furniture.
//! \param creature The creature whose walking body is used.
//! \param tile The tile to test.
bool hasStandingPosition(Creature& creature, const Tile& tile);
//! \brief Removes the tiles that are covered by furniture from a list of random walking targets.
//! If no tile of the list has a free standing position, the list stays as it is.
//! \param creature The creature whose walking body is used.
//! \param tiles The candidate tiles, reduced in place.
void keepTilesWithStandingPosition(Creature& creature, std::vector<Tile*>& tiles);
//! \brief Spaces a server destination; adjacent expands reachable tile rings, optionally restricted to the supplied room.
bool separate(Creature& creature, std::vector<Ogre::Vector2>& path, bool adjacent = false, const Room* room = nullptr);
// Searches a route to a point from which the creature can reach the food without
// furniture in between. The last point of the path is the position to eat at.
//! \brief Finds a reachable feeding stance, preferring measured body separation before crowded fallback.
bool foodApproach(Creature& creature, const Ogre::Vector2& food, std::vector<Ogre::Vector2>& path);
// Searches a route to the wanted working position at the object, facing it with the
// facing offset. An empty path means that the creature already stands there.
//! \brief Prefers clear working bodies, then retains the original valid room-reserved placement when crowded.
bool workApproach(Creature& creature, const BuildingObject& object, const Ogre::Vector2& wanted,
    const Ogre::Vector2& facingOffset, std::vector<Ogre::Vector2>& path);
//! \brief The failed route searches of one creature, kept for later refine() calls while the game state stays the
//! same: the creature does not move and no creature, tile or furniture changes in between (for example all the dig
//! places a worker is tested for in one go). A route search that they prove to fail is not run again, so testing
//! many places behind the same closed gap costs one failed search instead of one per place. Every answer of
//! refine() stays the same.
class RouteCache
{
public:
    //! \brief The failed searches of the creature around all furniture except the interaction object. A cache that
    //! was used for another creature forgets its searches.
    RoomObjectPath::RouteFailures& failures(const Creature& creature, const BuildingObject* interaction);

private:
    //! The creature the searches belong to
    const Creature* mCreature = nullptr;
    //! The failed searches per interaction object (left out of the obstacles)
    std::map<const BuildingObject*, RoomObjectPath::RouteFailures> mFailures;
};
// Replaces the path by one that leads around furniture, if the path crosses any. Returns
// true if the path was changed or removed (no route) and false if it can be walked as it is.
bool refine(Creature& creature, std::vector<Ogre::Vector2>& path);
//! \brief refine() that reuses and adds to the failed searches of the cache (see RouteCache).
bool refine(Creature& creature, std::vector<Ogre::Vector2>& path, RouteCache& cache);
// Tells whether the path crosses furniture. With includeWalkDistortion, the client jitter
// of the walk is taken into account as well.
bool blocked(Creature& creature, const std::vector<Ogre::Vector2>& path, bool includeWalkDistortion = false);
//! rief Tells whether the client jitter of the walk (each coordinate +/-0.3) could carry the body of the creature into
//! a tile it cannot walk on (a wall) next to the path. The server then sends the path without jitter (decision 727).
bool walkDistortionReachesWall(Creature& creature, const std::vector<Ogre::Vector2>& path);
}

#endif
