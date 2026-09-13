#include "gamemap/RoomObjectNavigation.h"
#include "gamemap/RoomObjectBounds.h"
#include "creatureaction/CreatureAction.h"
#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomPrison.h"
#include "rooms/RoomType.h"
#include "utils/Helper.h"

namespace
{
const BuildingObject* interactionObject(Creature& creature, const Ogre::Vector2& goal)
{
    Tile* tile = creature.getGameMap()->getTile(Helper::round(goal.x), Helper::round(goal.y));
    if(tile == nullptr || tile->getCoveringRoom() == nullptr)
        return nullptr;
    Room* room = tile->getCoveringRoom();
    bool entering = room->getType() == RoomType::dormitory &&
        tile == creature.getHomeTile() && creature.isActionInList(CreatureActionType::sleep);
    if(room->getType() == RoomType::portal && creature.isActionInList(CreatureActionType::leaveDungeon))
        entering = true;
    if(room->getType() == RoomType::torture && creature.isActionInList(CreatureActionType::useRoom))
        for(unsigned i = 0; room->getCreatureUsingRoom(i) != nullptr; ++i)
            if(room->getCreatureUsingRoom(i) == &creature)
                entering = true;
    if(!entering)
        return nullptr;
    const auto& objects = room->getBuildingObjects();
    const auto found = objects.find(tile);
    return found == objects.end() ? nullptr : found->second;
}

bool terrainClear(Creature& creature, const Ogre::Vector2& from, const Ogre::Vector2& to)
{
    GameMap& map = *creature.getGameMap();
    const auto passable = [&](int x, int y)
    {
        Tile* tile = map.getTile(x, y);
        return tile != nullptr && (creature.canGoThroughTile(tile) || tile == creature.getPositionTile());
    };
    int previousX = Helper::round(from.x), previousY = Helper::round(from.y);
    if(!passable(previousX, previousY))
        return false;
    const int steps = std::max(1, int(std::ceil(from.distance(to) * 16.0f)));
    for(int i = 1; i <= steps; ++i)
    {
        const auto point = from + (to - from) * (float(i) / steps);
        const int x = Helper::round(point.x), y = Helper::round(point.y);
        if(!passable(x, y))
            return false;
        if(x != previousX && y != previousY &&
            (!passable(x, previousY) || !passable(previousX, y)))
            return false;
        previousX = x;
        previousY = y;
    }
    return true;
}
}

float RoomObjectNavigation::clearance(const Creature& creature)
{
    const float scale = 1.0f + 0.02f * creature.getLevel();
    for(const auto& model : RoomObjectPath::walkingRadii)
        if(creature.getMeshName() == model.name)
            return model.radius * scale;
    return 0.2f * scale;
}

std::vector<RoomObjectPath::Obstacle> RoomObjectNavigation::collect(GameMap& map,
    float clearance, const BuildingObject* interaction)
{
    std::vector<RoomObjectPath::Obstacle> result;
    const auto append = [&](const BuildingObject* object)
    {
        // These walkable landmarks are not solid room furniture.
        if(object == interaction || object->getMeshName() == "PortalObject" ||
            object->getMeshName() == "DungeonTempleObject")
            return;
        for(const auto& bounds : RoomObjectPath::meshBounds)
        {
            if(object->getMeshName() != bounds.name)
                continue;
            const float angle = float(object->getRotationAngle()) * 0.01745329252f;
            const auto placedScale = object->getFurnitureScale();
            const auto scale = placedScale == Ogre::Vector2::ZERO ? RoomObjectPath::furnitureScale(bounds) :
                RoomObjectPath::FurnitureScale{placedScale.x, placedScale.y};
            result.push_back({{bounds.minX * scale.x - clearance, bounds.minY * scale.y - clearance},
                {bounds.maxX * scale.x + clearance, bounds.maxY * scale.y + clearance},
                {object->getPosition().x, object->getPosition().y}, std::cos(angle), std::sin(angle)});
            break;
        }
    };
    for(Room* room : map.getRooms())
    {
        for(const auto& entry : room->getBuildingObjects())
            append(entry.second);
        if(room->getType() == RoomType::prison)
            for(const auto& entry : static_cast<RoomPrison*>(room)->getFencingObjects())
                append(entry.second);
    }
    return result;
}

std::vector<RoomObjectPath::Obstacle> RoomObjectNavigation::bodyObstacles(Creature& creature,
    const BuildingObject* interaction)
{
    auto result = collect(*creature.getGameMap(), 0.0f, interaction);
    Ogre::Vector2 minimum(-0.2f), maximum(0.2f);
    for(const auto& model : RoomObjectPath::walkingRadii)
        if(creature.getMeshName() == model.name)
        {
            minimum = Ogre::Vector2(model.minX, model.minY);
            maximum = Ogre::Vector2(model.maxX, model.maxY);
            break;
        }
    const float scale = 1.0f + 0.02f * creature.getLevel();
    Ogre::Vector2 heading(creature.getWalkDirection().x, creature.getWalkDirection().y);
    if(heading.squaredLength() < 0.000001f)
        heading = Ogre::Vector2(0, -1);
    for(auto& obstacle : result)
    {
        obstacle.bodyMinimum = minimum * scale;
        obstacle.bodyMaximum = maximum * scale;
        obstacle.initialHeading = heading;
    }
    return result;
}

bool RoomObjectNavigation::standingPosition(const std::vector<RoomObjectPath::Obstacle>& obstacles,
    const Ogre::Vector2& wanted, Ogre::Vector2& result)
{
    if(RoomObjectPath::clearPoint(obstacles, wanted))
    {
        result = wanted;
        return true;
    }
    const Ogre::Vector2 center(float(Helper::round(wanted.x)), float(Helper::round(wanted.y)));
    float distance = std::numeric_limits<float>::infinity();
    for(int y = 0; y < 8; ++y)
        for(int x = 0; x < 8; ++x)
        {
            const auto point = center + Ogre::Vector2(-0.4375f + x * 0.125f, -0.4375f + y * 0.125f);
            if(point.squaredDistance(wanted) >= distance || !RoomObjectPath::clearPoint(obstacles, point))
                continue;
            distance = point.squaredDistance(wanted);
            result = point;
        }
    return std::isfinite(distance);
}

bool RoomObjectNavigation::refine(Creature& creature, std::vector<Ogre::Vector2>& path)
{
    if(path.empty())
        return false;
    GameMap& map = *creature.getGameMap();
    const auto* interaction = interactionObject(creature, path.back());
    const float radius = clearance(creature);
    // Each client jitter coordinate is +/-0.3, so a rotated object needs the
    // full diagonal displacement as well as the creature's walking radius.
    auto obstacles = collect(map, radius + 0.425f, interaction);
    const Ogre::Vector2 start(creature.getPosition().x, creature.getPosition().y);
    auto previous = start;
    bool nearby = false;
    for(const auto& point : path)
    {
        if(!RoomObjectPath::clearSegment(obstacles, previous, point))
            nearby = true;
        previous = point;
    }
    if(!nearby)
        return false;

    obstacles = bodyObstacles(creature, interaction);
    auto goal = path.back();
    if(!standingPosition(obstacles, goal, goal))
    {
        path.clear();
        return true;
    }
    const auto terrain = [&](const Ogre::Vector2& from, const Ogre::Vector2& to)
    { return terrainClear(creature, from, to); };
    std::vector<Ogre::Vector2> result;
    // Coarse tile centers bound the search; they are not mandatory stops inside
    // a furnished room. Refine once to the actual destination through its gaps.
    Ogre::Vector2 minimum = start, maximum = start;
    for(const auto& point : path)
    {
        minimum.makeFloor(point);
        maximum.makeCeil(point);
    }
    minimum.makeFloor(goal);
    maximum.makeCeil(goal);
    const int minX = std::max(0, int(std::floor(minimum.x)) - 2);
    const int minY = std::max(0, int(std::floor(minimum.y)) - 2);
    const int maxX = std::min(map.getMapSizeX() - 1, int(std::ceil(maximum.x)) + 2);
    const int maxY = std::min(map.getMapSizeY() - 1, int(std::ceil(maximum.y)) + 2);
    if(!RoomObjectPath::route(start, goal, obstacles, minX, minY, maxX, maxY, terrain, result) &&
        !RoomObjectPath::route(start, goal, obstacles, 0, 0,
            map.getMapSizeX() - 1, map.getMapSizeY() - 1, terrain, result))
    {
        path.clear();
        return true;
    }
    path.swap(result);
    return true;
}

bool RoomObjectNavigation::foodApproach(Creature& creature, const Ogre::Vector2& food,
    std::vector<Ogre::Vector2>& path)
{
    path.clear();
    GameMap& map = *creature.getGameMap();
    const auto furniture = collect(map, 0.0f);
    const auto body = bodyObstacles(creature);
    const Ogre::Vector2 start(creature.getPosition().x, creature.getPosition().y);
    const int foodX = Helper::round(food.x), foodY = Helper::round(food.y);
    std::vector<Ogre::Vector2> candidates;
    // Preserve the food action's same-tile/cardinal-neighbor reach, but require
    // an unobstructed approach on the chicken's side of the furniture.
    for(int dy = -1; dy <= 1; ++dy)
        for(int dx = -1; dx <= 1; ++dx)
        {
            if(std::abs(dx) + std::abs(dy) > 1)
                continue;
            Tile* tile = map.getTile(foodX + dx, foodY + dy);
            if(!creature.canGoThroughTile(tile))
                continue;
            for(int y = 0; y < 8; ++y)
                for(int x = 0; x < 8; ++x)
                {
                    const Ogre::Vector2 point(foodX + dx - 0.4375f + x * 0.125f,
                        foodY + dy - 0.4375f + y * 0.125f);
                    if(RoomObjectPath::clearPoint(body, point, food - point) &&
                        RoomObjectPath::clearSegment(furniture, point, food))
                        candidates.push_back(point);
                }
        }
    std::stable_sort(candidates.begin(), candidates.end(), [&](const Ogre::Vector2& a, const Ogre::Vector2& b)
    {
        const float da = a.squaredDistance(food), db = b.squaredDistance(food);
        return da == db ? a.squaredDistance(start) < b.squaredDistance(start) : da < db;
    });
    std::vector<Ogre::Vector2> stagingPoints, standingPoints;
    for(const auto& point : candidates)
    {
        Ogre::Vector2 direction = food - point;
        if(direction.squaredLength() < 0.000001f)
            direction = Ogre::Vector2(0, -1);
        direction.normalise();
        // The last leg approaches in the orientation that made this standing
        // point usable; arbitrary grid diagonals can otherwise clip a wide body.
        const auto staging = point - direction * (clearance(creature) + 0.5f);
        Tile* tile = map.getTile(Helper::round(staging.x), Helper::round(staging.y));
        if(!creature.canGoThroughTile(tile) || !terrainClear(creature, staging, point) ||
            !RoomObjectPath::clearSegment(body, staging, point))
            continue;
        stagingPoints.push_back(staging);
        standingPoints.push_back(point);
    }
    // These are alternatives for one food target, not independent jobs. Search
    // their shared movement graph once instead of retrying it for every offset.
    size_t chosen = 0;
    const auto terrain = [&](const Ogre::Vector2& from, const Ogre::Vector2& to)
    { return terrainClear(creature, from, to); };
    if(!RoomObjectPath::routeToAny(start, stagingPoints, body, 0, 0,
        map.getMapSizeX() - 1, map.getMapSizeY() - 1, terrain, path, chosen))
        return false;
    path.push_back(standingPoints[chosen]);
    return true;
}

bool RoomObjectNavigation::workApproach(Creature& creature, const BuildingObject& object,
    const Ogre::Vector2& wanted, const Ogre::Vector2& facingOffset, std::vector<Ogre::Vector2>& path)
{
    path.clear();
    GameMap& map = *creature.getGameMap();
    const Ogre::Vector2 objectPosition(object.getPosition().x, object.getPosition().y);
    Tile* objectTile = map.getTile(Helper::round(objectPosition.x), Helper::round(objectPosition.y));
    if(objectTile == nullptr)
        return false;
    const auto* room = objectTile->getCoveringRoom();
    const auto body = bodyObstacles(creature);
    const auto facing = objectPosition + facingOffset;
    Ogre::Vector2 away = wanted - facing;
    if(away.squaredLength() < 0.000001f)
        away = Ogre::Vector2(0, -1);
    away.normalise();
    const Ogre::Vector2 start(creature.getPosition().x, creature.getPosition().y);
    // Preserve the assigned side of the workstation. Only increase its stand-
    // off enough for this creature; work cannot require standing inside it.
    const int steps = int(std::ceil((2.0f * clearance(creature) + 1.0f) * 8.0f));
    for(int step = 0; step <= steps; ++step)
    {
        const auto point = wanted + away * (step * 0.125f);
        Tile* tile = map.getTile(Helper::round(point.x), Helper::round(point.y));
        if(!creature.canGoThroughTile(tile) || tile->getCoveringRoom() != room ||
            !RoomObjectPath::clearPoint(body, point, facing - point))
            continue;
        if(start.squaredDistance(point) < 0.0025f &&
            RoomObjectPath::clearPoint(body, start, facing - start))
            return true;
        for(float distance : {clearance(creature) + 0.5f, 0.5f})
        {
            const auto staging = point + away * distance;
            Tile* stagingTile = map.getTile(Helper::round(staging.x), Helper::round(staging.y));
            if(!creature.canGoThroughTile(stagingTile) || !terrainClear(creature, staging, point) ||
                !RoomObjectPath::clearSegment(body, staging, point))
                continue;
            const auto tiles = map.path(&creature, stagingTile);
            if(tiles.empty())
                continue;
            Creature::tileToVector2(tiles, path, true, 0.0f);
            path.push_back(staging);
            refine(creature, path);
            // The final leg was checked with the actual working direction.
            // Generic endpoint refinement tests eight walking headings and
            // must not displace this precise, already valid interaction point.
            if(!path.empty() && path.back() == staging)
            {
                path.push_back(point);
                return true;
            }
            path.clear();
        }
    }
    return false;
}

bool RoomObjectNavigation::blocked(Creature& creature, const std::vector<Ogre::Vector2>& path,
    bool includeWalkDistortion)
{
    if(path.empty())
        return false;
    const auto* interaction = interactionObject(creature, path.back());
    const auto obstacles = includeWalkDistortion ? collect(*creature.getGameMap(), clearance(creature) + 0.425f, interaction) :
        bodyObstacles(creature, interaction);
    Ogre::Vector2 previous(creature.getPosition().x, creature.getPosition().y);
    bool first = true;
    for(const auto& point : path)
    {
        if(!RoomObjectPath::clearSegment(obstacles, previous, point, first && !includeWalkDistortion))
            return true;
        first = false;
        previous = point;
    }
    return false;
}
