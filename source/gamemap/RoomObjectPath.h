#ifndef ROOMOBJECTPATH_H
#define ROOMOBJECTPATH_H

#include <OgreVector2.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <functional>
#include <limits>
#include <queue>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace RoomObjectPath
{
// The route search places its nodes on a grid of this many cells per tile.
constexpr int routeCellsPerTile = 4;
constexpr float routeCellSize = 0.25f;
// Distance around the start within which the first nodes of a route are tried:
// normally, and when the start itself is inside furniture and needs a way out.
constexpr float routeStartReach = 0.4f;
constexpr float routeEscapeReach = 3.0f;
// A node is linked to a goal if it is closer than this to it.
constexpr float routeGoalReach = 0.5f;
// Tolerance when old entries of the search queues are discarded.
constexpr float routeQueueTolerance = 0.0001f;
// Extra reach of a grid cell when the route search lists the obstacles near it. It only has to cover the rounding of
// the node positions; a larger value lists more obstacles but never changes a result.
constexpr float routeCellListMargin = 0.05f;

// Furniture bounds are expressed in mesh-local XY, before the placed object's
// rotation. Clearance belongs to the moving creature, not to the mesh asset.
struct Obstacle
{
    Ogre::Vector2 minimum, maximum, position;
    float cosine, sine;
    // XY bounds of the moving body, in its own space; forHeading() turns them into the
    // bodyAxis values below.
    Ogre::Vector2 bodyMinimum = Ogre::Vector2::ZERO;
    Ogre::Vector2 bodyMaximum = Ogre::Vector2::ZERO;
    // Direction the body faces when it has no walking direction.
    Ogre::Vector2 initialHeading = Ogre::Vector2(0, -1);
    // A nonnegative radius is a logical circular footprint with moving-body
    // clearance already included; negative retains the oriented-box geometry.
    float radius = -1.0f;
    // Bounds along the axes of the body, and the rotation of those axes. They are only
    // set (hasBodyAxes) for an obstacle returned by forHeading().
    Ogre::Vector2 bodyAxisMinimum = Ogre::Vector2::ZERO;
    Ogre::Vector2 bodyAxisMaximum = Ogre::Vector2::ZERO;
    float bodyCosine = 1.0f, bodySine = 0.0f;
    bool hasBodyAxes = false;
    // Axis-aligned bounds in the world, used to skip distant obstacles quickly; only
    // valid if hasWorldBounds is set by forHeading().
    Ogre::Vector2 worldMinimum, worldMaximum;
    bool hasWorldBounds = false;
    // Top of the furniture; a creature that is higher walks over it.
    float maximumHeight = std::numeric_limits<float>::infinity();

    // Returns a circular obstacle around the center.
    static Obstacle circle(const Ogre::Vector2& center, float clearanceRadius)
    {
        Obstacle result{Ogre::Vector2(-clearanceRadius), Ogre::Vector2(clearanceRadius), center, 1, 0};
        result.radius = clearanceRadius;
        return result;
    }

    // Returns the obstacle widened by the body of a creature that walks in the direction.
    Obstacle forHeading(Ogre::Vector2 direction) const
    {
        Obstacle result = *this;
        if(radius >= 0.0f || (bodyMinimum == Ogre::Vector2::ZERO && bodyMaximum == Ogre::Vector2::ZERO))
            return result;
        if(direction.squaredLength() < 0.000001f)
            direction = initialHeading;
        direction.normalise();
        Ogre::Vector2 low(std::numeric_limits<float>::infinity()), high(-std::numeric_limits<float>::infinity());
        for(float x : {bodyMinimum.x, bodyMaximum.x})
            for(float y : {bodyMinimum.y, bodyMaximum.y})
            {
                // The renderer turns native -Y toward the travel direction.
                const Ogre::Vector2 world(-direction.y * x - direction.x * y,
                    direction.x * x - direction.y * y);
                const Ogre::Vector2 point(cosine * world.x + sine * world.y,
                    -sine * world.x + cosine * world.y);
                low.makeFloor(point);
                high.makeCeil(point);
            }
        result.minimum -= high;
        result.maximum -= low;
        // Both rectangles contribute separating axes. Expanding only in the
        // furniture axes fills empty corners when furniture and body differ
        // in orientation, incorrectly sealing real gaps between rotated props.
        result.bodyCosine = -direction.y;
        result.bodySine = direction.x;
        low = Ogre::Vector2(std::numeric_limits<float>::infinity());
        high = -low;
        for(float x : {minimum.x, maximum.x})
            for(float y : {minimum.y, maximum.y})
            {
                const Ogre::Vector2 world(cosine * x - sine * y, sine * x + cosine * y);
                const Ogre::Vector2 point(result.bodyCosine * world.x + result.bodySine * world.y,
                    -result.bodySine * world.x + result.bodyCosine * world.y);
                low.makeFloor(point);
                high.makeCeil(point);
            }
        result.bodyAxisMinimum = low - bodyMaximum;
        result.bodyAxisMaximum = high - bodyMinimum;
        result.hasBodyAxes = true;
        result.bodyMinimum = result.bodyMaximum = Ogre::Vector2::ZERO;
        const Ogre::Vector2 center = (result.minimum + result.maximum) * 0.5f;
        const Ogre::Vector2 half = (result.maximum - result.minimum) * 0.5f;
        const Ogre::Vector2 worldCenter = position + Ogre::Vector2(cosine * center.x - sine * center.y,
            sine * center.x + cosine * center.y);
        const Ogre::Vector2 extent(std::abs(cosine) * half.x + std::abs(sine) * half.y + 0.00001f,
            std::abs(sine) * half.x + std::abs(cosine) * half.y + 0.00001f);
        result.worldMinimum = worldCenter - extent;
        result.worldMaximum = worldCenter + extent;
        result.hasWorldBounds = true;
        return result;
    }

    // Returns the point in the space of the furniture.
    Ogre::Vector2 local(const Ogre::Vector2& point) const
    {
        const Ogre::Vector2 relative = point - position;
        return Ogre::Vector2(cosine * relative.x + sine * relative.y,
            -sine * relative.x + cosine * relative.y);
    }

    // Returns the point in the space of the body.
    Ogre::Vector2 bodyLocal(const Ogre::Vector2& point) const
    {
        const Ogre::Vector2 relative = point - position;
        return Ogre::Vector2(bodyCosine * relative.x + bodySine * relative.y,
            -bodySine * relative.x + bodyCosine * relative.y);
    }

    // Tells whether a creature standing at the point and facing the heading touches the obstacle.
    bool contains(const Ogre::Vector2& point, const Ogre::Vector2& heading = Ogre::Vector2::ZERO) const
    {
        if(radius >= 0.0f)
            return point.squaredDistance(position) < radius * radius;
        const Obstacle bounds = forHeading(heading);
        const Ogre::Vector2 p = local(point);
        if(p.x <= bounds.minimum.x || p.x >= bounds.maximum.x ||
           p.y <= bounds.minimum.y || p.y >= bounds.maximum.y)
            return false;
        const Ogre::Vector2 bodyPoint = bounds.bodyLocal(point);
        return !bounds.hasBodyAxes || (bodyPoint.x > bounds.bodyAxisMinimum.x &&
            bodyPoint.x < bounds.bodyAxisMaximum.x && bodyPoint.y > bounds.bodyAxisMinimum.y &&
            bodyPoint.y < bounds.bodyAxisMaximum.y);
    }

    // Tells whether a creature walking from one point to the other touches the obstacle.
    bool intersects(const Ogre::Vector2& from, const Ogre::Vector2& to) const
    {
        // Cached for each grid heading: distant furniture cannot intersect the
        // segment, so reserve the exact oriented-body test for nearby objects.
        if(hasWorldBounds && ((from.x < worldMinimum.x && to.x < worldMinimum.x) ||
            (from.x > worldMaximum.x && to.x > worldMaximum.x) ||
            (from.y < worldMinimum.y && to.y < worldMinimum.y) ||
            (from.y > worldMaximum.y && to.y > worldMaximum.y)))
            return false;
        if(radius >= 0.0f)
        {
            const Ogre::Vector2 delta = to - from;
            const float lengthSquared = delta.squaredLength();
            const float along = lengthSquared > 0.0f ?
                std::max(0.0f, std::min(1.0f, (position - from).dotProduct(delta) / lengthSquared)) : 0.0f;
            return contains(from + delta * along);
        }
        const Obstacle bounds = forHeading(to - from);
        const Ogre::Vector2 localFrom = local(from), localDelta = local(to) - localFrom;
        const Ogre::Vector2 bodyFrom = bounds.bodyLocal(from), bodyDelta = bounds.bodyLocal(to) - bodyFrom;
        const std::array<float, 4> a{{localFrom.x, localFrom.y, bodyFrom.x, bodyFrom.y}};
        const std::array<float, 4> delta{{localDelta.x, localDelta.y, bodyDelta.x, bodyDelta.y}};
        const std::array<float, 4> minimum{{bounds.minimum.x, bounds.minimum.y,
            bounds.bodyAxisMinimum.x, bounds.bodyAxisMinimum.y}};
        const std::array<float, 4> maximum{{bounds.maximum.x, bounds.maximum.y,
            bounds.bodyAxisMaximum.x, bounds.bodyAxisMaximum.y}};
        float enter = 0.0f, leave = 1.0f;
        for(int axis = 0; axis < (bounds.hasBodyAxes ? 4 : 2); ++axis)
        {
            if(std::abs(delta[axis]) < 0.00001f)
            {
                if(a[axis] <= minimum[axis] || a[axis] >= maximum[axis])
                    return false;
                continue;
            }
            float low = (minimum[axis] - a[axis]) / delta[axis];
            float high = (maximum[axis] - a[axis]) / delta[axis];
            if(low > high)
                std::swap(low, high);
            enter = std::max(enter, low);
            leave = std::min(leave, high);
            if(enter >= leave)
                return false;
        }
        return enter < leave;
    }
};

// Tells whether no obstacle touches a creature at the point. Without heading, it is
// enough that one of the eight walking headings is free.
inline bool clearPoint(const std::vector<Obstacle>& obstacles, const Ogre::Vector2& point,
    const Ogre::Vector2& heading = Ogre::Vector2::ZERO)
{
    if(heading == Ogre::Vector2::ZERO)
    {
        for(int y = -1; y <= 1; ++y)
            for(int x = -1; x <= 1; ++x)
                if((x != 0 || y != 0) && clearPoint(obstacles, point, Ogre::Vector2(float(x), float(y))))
                    return true;
        return false;
    }
    for(const Obstacle& obstacle : obstacles)
        if(obstacle.contains(point, heading))
            return false;
    return true;
}

// Tells whether no obstacle touches a creature that walks from one point to the other.
// With allowExit, a start inside furniture may be left.
inline bool clearSegment(const std::vector<Obstacle>& obstacles,
    const Ogre::Vector2& from, const Ogre::Vector2& to, bool allowExit = false)
{
    for(const Obstacle& obstacle : obstacles)
    {
        // A creature loaded/dropped into furniture must be able to leave it,
        // but no subsequent waypoint may re-enter that furniture.
        if(allowExit && obstacle.contains(from, obstacle.initialHeading) && !obstacle.contains(to, to - from))
            continue;
        if(obstacle.intersects(from, to))
            return false;
    }
    return true;
}

//! \brief Tells whether none of the obstacles given by index in the two lists touches a creature that walks from one
//! point to the other. This is clearSegment() without start exit, for the obstacles of the lists only.
inline bool clearListedSegment(const std::vector<Obstacle>& obstacles, const std::vector<size_t>& always,
    const std::vector<size_t>& listed, const Ogre::Vector2& from, const Ogre::Vector2& to)
{
    for(size_t index : always)
        if(obstacles[index].intersects(from, to))
            return false;
    for(size_t index : listed)
        if(obstacles[index].intersects(from, to))
            return false;
    return true;
}

// The existing map supplies terrain/door checks for an entire segment. Furniture
// is checked analytically, so even thin and rotated objects cannot be skipped.
using TerrainSegment = std::function<bool(const Ogre::Vector2&, const Ogre::Vector2&)>;

// Returns the length of the path that starts at the start point.
inline float pathLength(const Ogre::Vector2& start, const std::vector<Ogre::Vector2>& path)
{
    float cost = 0.0f;
    Ogre::Vector2 previous = start;
    for(const Ogre::Vector2& point : path)
    {
        cost += previous.distance(point);
        previous = point;
    }
    return cost;
}

// Number of a grid node that is the same in every search area: the grid lines are counted from tile 0, not from the
// corner of the area.
inline int64_t routeNodeKey(int gridX, int gridY)
{
    return (static_cast<int64_t>(gridX) << 32) ^ static_cast<int64_t>(static_cast<uint32_t>(gridY));
}

// One side of a failed route search that ran out of nodes without being stopped by the border of its search area.
// A goal side holds every grid node from which the goal can be reached, a start side every grid node that can be
// reached from the start. Neither node set depends on the search area, so no route exists on that grid in any area:
// - start side: for a goal none of whose first nodes is in the set (the start side has all nodes the start reaches),
// - goal side: for a goal all of whose first nodes are in the set (every node that reaches them is in the set, and
//   the search found none of the first nodes of the start in it).
struct ClosedSearchSide
{
    // Start, grid offset and start exit of the search: a later search uses the side only if they are the same
    Ogre::Vector2 start;
    Ogre::Vector2 gridOffset;
    bool allowStartExit;
    // The nodes the search tried as first nodes of the start (counted as in routeNodeKey): a later search uses the
    // side only if it tries no other ones
    int seedGridFirstX, seedGridLastX, seedGridFirstY, seedGridLastY;
    // True for a goal side, false for a start side
    bool goalSide;
    // The nodes of the side (routeNodeKey)
    std::unordered_set<int64_t> nodes;
};

// The closed sides of the failed searches of one creature, for one set of obstacles and one terrain in one unchanged
// game state. A search that is given them is not run when they prove that it fails, and adds its own closed side
// when it fails; its answer is always the one of the full search.
struct RouteFailures
{
    std::vector<ClosedSearchSide> sides;
};

// Searches the shortest route from the start to the nearest of the goals around the
// obstacles, within the given tile range, and returns the index of the goal in
// chosenGoal. Routes longer than maximumCost are not accepted.
// failures (single goal only, may be null): failed searches with the same obstacles and terrain, see RouteFailures.
inline bool routeToAny(const Ogre::Vector2& start, const std::vector<Ogre::Vector2>& goals,
    const std::vector<Obstacle>& obstacles, int minX, int minY, int maxX, int maxY,
    const TerrainSegment& terrain, std::vector<Ogre::Vector2>& result, size_t& chosenGoal, bool allowStartExit = true,
    const Ogre::Vector2& gridOffset = Ogre::Vector2::ZERO,
    float maximumCost = std::numeric_limits<float>::infinity(), RouteFailures* failures = nullptr)
{
    result.clear();
    if(goals.empty())
        return false;
    if(goals.size() == 1 && start.distance(goals.front()) >= maximumCost)
        return false;
    for(size_t i = 0; i < goals.size(); ++i)
    {
        const Ogre::Vector2& goal = goals[i];
        if(start.distance(goal) < maximumCost && clearPoint(obstacles, goal) && terrain(goal, goal) && clearSegment(obstacles, start, goal, allowStartExit) && terrain(start, goal))
        {
            chosenGoal = i;
            result.push_back(goal);
            return true;
        }
    }

    if(goals.size() == 1 && std::isfinite(maximumCost))
    {
        // Any improving route lies inside the start/goal distance ellipse.
        // Cropping its bounding box avoids allocating a whole-map grid for
        // every short lane comparison without imposing a search budget.
        const Ogre::Vector2 center = (start + goals.front()) * 0.5f;
        const Ogre::Vector2 delta = goals.front() - start;
        const float halfX = 0.5f * std::sqrt(std::max(0.0f, maximumCost * maximumCost - delta.y * delta.y));
        const float halfY = 0.5f * std::sqrt(std::max(0.0f, maximumCost * maximumCost - delta.x * delta.x));
        minX = std::max(minX, int(std::floor(center.x - halfX - gridOffset.x)));
        minY = std::max(minY, int(std::floor(center.y - halfY - gridOffset.y)));
        maxX = std::min(maxX, int(std::ceil(center.x + halfX - gridOffset.x)));
        maxY = std::min(maxY, int(std::ceil(center.y + halfY - gridOffset.y)));
    }
    // Quarter-tile nodes refine the existing tile path only where furniture
    // obstructs it; endpoints retain the precise room-interaction offsets.
    const int width = (maxX - minX) * routeCellsPerTile + 1;
    const int height = (maxY - minY) * routeCellsPerTile + 1;
    if(width <= 0 || height <= 0)
        return false;
    struct SearchNode
    {
        float cost = std::numeric_limits<float>::infinity();
        float forwardCost = std::numeric_limits<float>::infinity();
        int parent = -1, forwardParent = -1;
        size_t terminal = 0;
    };
    // A local or enclosed approach visits only a small fraction of a large map.
    // Store visited nodes rather than initialize whole-map arrays per lane.
    std::unordered_map<int, SearchNode> nodes;
    using Entry = std::pair<float, int>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> open;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> forwardOpen;
    const std::function<Ogre::Vector2(int)> position = [&](int index)
    {
        return Ogre::Vector2(minX + (index % width) * routeCellSize,
            minY + (index / width) * routeCellSize) + gridOffset;
    };
    // Opposite consistent potentials keep the two A* frontiers comparable;
    // their sum is a lower bound on the remaining complete route cost.
    const std::function<float(int)> potential = [&](int index)
    { return goals.size() == 1 ? 0.5f * (position(index).distance(goals.front()) - position(index).distance(start)) : 0.0f; };
    const std::function<void(int, float, int)> add = [&](int index, float cost, int parent)
    {
        if(cost >= nodes[index].cost)
            return;
        nodes[index].cost = cost;
        nodes[index].parent = parent;
        open.emplace(cost - potential(index), index);
    };

    // Usually only the surrounding grid nodes are needed. If old save data or
    // newly placed furniture overlaps the start, connect an outward exit first.
    const Ogre::Vector2 initialHeading = obstacles.empty() ? Ogre::Vector2(0, -1) : obstacles.front().initialHeading;
    const float reach = !allowStartExit || clearPoint(obstacles, start, initialHeading) ? routeStartReach : routeEscapeReach;
    const int seedFirstX = int(std::floor((start.x - reach - minX - gridOffset.x) * routeCellsPerTile));
    const int seedLastX = int(std::ceil((start.x + reach - minX - gridOffset.x) * routeCellsPerTile));
    const int seedFirstY = int(std::floor((start.y - reach - minY - gridOffset.y) * routeCellsPerTile));
    const int seedLastY = int(std::ceil((start.y + reach - minY - gridOffset.y) * routeCellsPerTile));
    const int firstX = std::max(0, seedFirstX);
    const int lastX = std::min(width - 1, seedLastX);
    const int firstY = std::max(0, seedFirstY);
    const int lastY = std::min(height - 1, seedLastY);
    // The nodes tried as first nodes of the start, counted from tile 0 (see routeNodeKey)
    const int seedGridFirstX = minX * routeCellsPerTile + seedFirstX, seedGridLastX = minX * routeCellsPerTile + seedLastX;
    const int seedGridFirstY = minY * routeCellsPerTile + seedFirstY, seedGridLastY = minY * routeCellsPerTile + seedLastY;
    // Failed searches are only remembered without a cost limit: with one, a route that is too long also fails
    const bool useFailures = failures != nullptr && goals.size() == 1;
    const bool rememberFailure = useFailures && !std::isfinite(maximumCost);
    if(useFailures && clearPoint(obstacles, goals.front()) && terrain(goals.front(), goals.front()))
    {
        // The first nodes of the goal, chosen exactly as the search below chooses them
        const Ogre::Vector2& goal = goals.front();
        std::vector<int64_t> goalNodes;
        const int goalFirstX = std::max(0, int(std::floor((goal.x - routeGoalReach - minX - gridOffset.x) * routeCellsPerTile)));
        const int goalLastX = std::min(width - 1, int(std::ceil((goal.x + routeGoalReach - minX - gridOffset.x) * routeCellsPerTile)));
        const int goalFirstY = std::max(0, int(std::floor((goal.y - routeGoalReach - minY - gridOffset.y) * routeCellsPerTile)));
        const int goalLastY = std::min(height - 1, int(std::ceil((goal.y + routeGoalReach - minY - gridOffset.y) * routeCellsPerTile)));
        for(int y = goalFirstY; y <= goalLastY; ++y)
            for(int x = goalFirstX; x <= goalLastX; ++x)
            {
                const Ogre::Vector2 point = position(y * width + x);
                if(point.squaredDistance(goal) <= routeGoalReach * routeGoalReach && clearSegment(obstacles, point, goal) && terrain(point, goal))
                    goalNodes.push_back(routeNodeKey(minX * routeCellsPerTile + x, minY * routeCellsPerTile + y));
            }
        for(const ClosedSearchSide& side : failures->sides)
        {
            // The first nodes of the start of this search must be among those the failed search tried
            if(side.start != start || side.gridOffset != gridOffset || side.allowStartExit != allowStartExit ||
               seedGridFirstX < side.seedGridFirstX || seedGridLastX > side.seedGridLastX ||
               seedGridFirstY < side.seedGridFirstY || seedGridLastY > side.seedGridLastY)
                continue;
            bool inside = false, outside = false;
            for(int64_t node : goalNodes)
            {
                if(side.nodes.count(node) > 0)
                    inside = true;
                else
                    outside = true;
            }
            // A goal side holding all first nodes of the goal, or a start side holding none of them
            if((side.goalSide && !outside) || (!side.goalSide && !inside))
                return false;
        }
    }
    // A side is closed while the border of the area has not stopped it; the start side also needs all its first nodes
    bool startClosed = seedFirstX >= 0 && seedLastX <= width - 1 && seedFirstY >= 0 && seedLastY <= height - 1;
    bool goalClosed = true;
    for(int y = firstY; y <= lastY; ++y)
        for(int x = firstX; x <= lastX; ++x)
        {
            const int index = y * width + x;
            const Ogre::Vector2 point = position(index);
            if(clearPoint(obstacles, point) && clearSegment(obstacles, start, point, allowStartExit) && terrain(start, point))
            {
                nodes[index].forwardCost = start.distance(point);
                forwardOpen.emplace(nodes[index].forwardCost + potential(index), index);
            }
        }
    if(forwardOpen.empty())
        return false;
    // Connect both endpoints: either may be isolated by furniture, independently
    // of the terrain-only coarse route. Exhausting either frontier proves failure.
    for(size_t i = 0; i < goals.size(); ++i)
    {
        const Ogre::Vector2& goal = goals[i];
        if(!clearPoint(obstacles, goal) || !terrain(goal, goal))
            continue;
        const int goalFirstX = std::max(0, int(std::floor((goal.x - routeGoalReach - minX - gridOffset.x) * routeCellsPerTile)));
        const int goalLastX = std::min(width - 1, int(std::ceil((goal.x + routeGoalReach - minX - gridOffset.x) * routeCellsPerTile)));
        const int goalFirstY = std::max(0, int(std::floor((goal.y - routeGoalReach - minY - gridOffset.y) * routeCellsPerTile)));
        const int goalLastY = std::min(height - 1, int(std::ceil((goal.y + routeGoalReach - minY - gridOffset.y) * routeCellsPerTile)));
        for(int y = goalFirstY; y <= goalLastY; ++y)
            for(int x = goalFirstX; x <= goalLastX; ++x)
            {
                const int index = y * width + x;
                const Ogre::Vector2 point = position(index);
                if(point.distance(goal) < nodes[index].cost && point.squaredDistance(goal) <= routeGoalReach * routeGoalReach && clearSegment(obstacles, point, goal) && terrain(point, goal))
                {
                    nodes[index].terminal = i;
                    add(index, point.distance(goal), -1);
                }
            }
    }

    if(open.empty())
        return false;
    // A grid edge has only eight headings; project a creature's walking body
    // once per heading, not once per obstacle for every expanded search node.
    std::array<std::vector<Obstacle>, 9> edgeObstacles;
    for(int dy = -1; dy <= 1; ++dy)
        for(int dx = -1; dx <= 1; ++dx)
        {
            if(dx == 0 && dy == 0)
                continue;
            std::vector<Obstacle>& edge = edgeObstacles[(dy + 1) * 3 + dx + 1];
            edge.reserve(obstacles.size());
            for(const Obstacle& obstacle : obstacles)
                edge.push_back(obstacle.forHeading(Ogre::Vector2(float(-dx), float(-dy))));
        }
    // Most furniture is far from a grid edge, yet every edge used to test all of it, and a search across a furnished
    // room tests hundreds of thousands of edges. An edge joins two neighbouring nodes, so it lies inside the tile-sized
    // cell (routeCellsPerTile nodes per side) of its lower node, widened by one node step. Each obstacle is listed for
    // the cells that its bounds for the eight headings can reach. An obstacle that is not listed for a cell is one that
    // intersects() rejects by these bounds for every edge of the cell, and obstacles without such bounds are tested
    // for every edge, so each edge test gives the same answer as testing all obstacles.
    const int cellsX = (width + routeCellsPerTile - 1) / routeCellsPerTile;
    const int cellsY = (height + routeCellsPerTile - 1) / routeCellsPerTile;
    const Ogre::Vector2 gridOrigin = Ogre::Vector2(float(minX), float(minY)) + gridOffset;
    std::vector<std::vector<size_t>> cellObstacles(size_t(cellsX) * size_t(cellsY));
    std::vector<size_t> unboundedObstacles;
    for(size_t i = 0; i < obstacles.size(); ++i)
    {
        Ogre::Vector2 low(std::numeric_limits<float>::infinity()), high(-std::numeric_limits<float>::infinity());
        bool bounded = true;
        for(int heading = 0; heading < 9; ++heading)
        {
            // The middle entry is no heading and stays empty
            if(heading == 4)
                continue;
            const Obstacle& edge = edgeObstacles[heading][i];
            if(!edge.hasWorldBounds)
            {
                bounded = false;
                break;
            }
            low.makeFloor(edge.worldMinimum);
            high.makeCeil(edge.worldMaximum);
        }
        // The comparisons also fail for bounds that are not numbers
        if(!bounded || !(low.x <= high.x) || !(low.y <= high.y))
        {
            unboundedObstacles.push_back(i);
            continue;
        }
        // Cell c of an axis holds the edges between gridOrigin + c and gridOrigin + c + 1 on that axis
        const int firstX = std::max(0, int(std::floor(std::max(-1.0f,
            std::min(float(cellsX), low.x - gridOrigin.x - 1.0f - routeCellListMargin)))));
        const int lastX = std::min(cellsX - 1, int(std::floor(std::max(-1.0f,
            std::min(float(cellsX), high.x - gridOrigin.x + routeCellListMargin)))));
        const int firstY = std::max(0, int(std::floor(std::max(-1.0f,
            std::min(float(cellsY), low.y - gridOrigin.y - 1.0f - routeCellListMargin)))));
        const int lastY = std::min(cellsY - 1, int(std::floor(std::max(-1.0f,
            std::min(float(cellsY), high.y - gridOrigin.y + routeCellListMargin)))));
        for(int cellY = firstY; cellY <= lastY; ++cellY)
            for(int cellX = firstX; cellX <= lastX; ++cellX)
                cellObstacles[size_t(cellY) * size_t(cellsX) + size_t(cellX)].push_back(i);
    }
    int destination = -1;
    float best = maximumCost;
    bool forward = false;
    while(!open.empty() && !forwardOpen.empty())
    {
        while(!open.empty() && open.top().first > nodes[open.top().second].cost - potential(open.top().second) + routeQueueTolerance)
            open.pop();
        while(!forwardOpen.empty() && forwardOpen.top().first > nodes[forwardOpen.top().second].forwardCost + potential(forwardOpen.top().second) + routeQueueTolerance)
            forwardOpen.pop();
        if(open.empty() || forwardOpen.empty() ||
            open.top().first + forwardOpen.top().first >= best)
            break;
        forward = !forward;
        std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>>& frontier = forward ? forwardOpen : open;
        float SearchNode::* const distance = forward ? &SearchNode::forwardCost : &SearchNode::cost;
        int SearchNode::* const link = forward ? &SearchNode::forwardParent : &SearchNode::parent;
        const Entry entry = frontier.top();
        frontier.pop();
        const int current = entry.second;
        const Ogre::Vector2 point = position(current);
        const int x = current % width, y = current / width;
        if(nodes[current].forwardCost + nodes[current].cost < best)
        {
            destination = current;
            best = nodes[current].forwardCost + nodes[current].cost;
        }
        for(int dy = -1; dy <= 1; ++dy)
            for(int dx = -1; dx <= 1; ++dx)
            {
                if(dx == 0 && dy == 0)
                    continue;
                if(x + dx < 0 || x + dx >= width || y + dy < 0 || y + dy >= height)
                {
                    // A free edge out of the area: in a larger area this side would go on
                    bool& closed = forward ? startClosed : goalClosed;
                    if(rememberFailure && closed)
                    {
                        const Ogre::Vector2 outside = Ogre::Vector2(minX + (x + dx) * routeCellSize,
                            minY + (y + dy) * routeCellSize) + gridOffset;
                        const Ogre::Vector2 from = forward ? point : outside;
                        const Ogre::Vector2 to = forward ? outside : point;
                        const int heading = forward ? (1 - dy) * 3 + 1 - dx : (dy + 1) * 3 + dx + 1;
                        // The node is in no cell of the area, so the edge is tested against all obstacles
                        bool free = true;
                        for(const Obstacle& obstacle : edgeObstacles[heading])
                            if(obstacle.intersects(from, to))
                            {
                                free = false;
                                break;
                            }
                        if(free && terrain(from, to))
                            closed = false;
                    }
                    continue;
                }
                const int next = (y + dy) * width + x + dx;
                const Ogre::Vector2 target = position(next);
                const float nextCost = nodes[current].*distance + point.distance(target);
                if(nextCost >= nodes[next].*distance)
                    continue;
                const Ogre::Vector2 from = forward ? point : target;
                const Ogre::Vector2 to = forward ? target : point;
                const int heading = forward ? (1 - dy) * 3 + 1 - dx : (dy + 1) * 3 + dx + 1;
                // The cell of the lower of the two nodes holds the obstacles this edge can touch
                const size_t cell = size_t(std::min(y, y + dy) / routeCellsPerTile) * size_t(cellsX) +
                    size_t(std::min(x, x + dx) / routeCellsPerTile);
                if(!clearListedSegment(edgeObstacles[heading], unboundedObstacles, cellObstacles[cell], from, to) ||
                    !terrain(from, to))
                    continue;
                nodes[next].*distance = nextCost;
                nodes[next].*link = current;
                frontier.emplace(nextCost + (forward ? potential(next) : -potential(next)), next);
                if(nodes[next].forwardCost + nodes[next].cost < best)
                {
                    destination = next;
                    best = nodes[next].forwardCost + nodes[next].cost;
                }
            }
    }
    if(destination < 0)
    {
        // The side that ran out of nodes proves the failure for any area if the border never stopped it
        const bool goalSide = open.empty() && goalClosed;
        if(rememberFailure && (goalSide || (forwardOpen.empty() && startClosed)))
        {
            ClosedSearchSide side{start, gridOffset, allowStartExit, seedGridFirstX, seedGridLastX, seedGridFirstY,
                seedGridLastY, goalSide, {}};
            for(const std::pair<const int, SearchNode>& entry : nodes)
                if(std::isfinite(goalSide ? entry.second.cost : entry.second.forwardCost))
                    side.nodes.insert(routeNodeKey(minX * routeCellsPerTile + entry.first % width,
                        minY * routeCellsPerTile + entry.first / width));
            failures->sides.push_back(std::move(side));
        }
        return false;
    }
    for(int index = destination; index >= 0; index = nodes[index].forwardParent)
        result.push_back(position(index));
    std::reverse(result.begin(), result.end());
    for(int index = nodes[destination].parent; index >= 0; index = nodes[index].parent)
        result.push_back(position(index));
    int terminal = destination;
    while(nodes[terminal].parent >= 0)
        terminal = nodes[terminal].parent;
    chosenGoal = nodes[terminal].terminal;
    result.push_back(goals[chosenGoal]);

    // Collapse only collinear runs: a visual/client interpolation must not cut a
    // corner through an obstacle or silently bypass an existing terrain rule.
    for(size_t i = 1; i + 1 < result.size();)
    {
        const Ogre::Vector2 a = result[i] - result[i - 1];
        const Ogre::Vector2 b = result[i + 1] - result[i];
        if(std::abs(a.crossProduct(b)) < 0.00001f && a.dotProduct(b) >= 0.0f)
            result.erase(result.begin() + i);
        else
            ++i;
    }
    return true;
}

// Like routeToAny(), but also tries grids that are shifted to the centre of the body and
// of the furniture, so that narrow lanes between furniture are found.
// failures (may be null): failed searches with the same obstacles and terrain, see RouteFailures.
inline bool routeToAnyAligned(const Ogre::Vector2& start, const std::vector<Ogre::Vector2>& goals,
    const std::vector<Obstacle>& obstacles, int minX, int minY, int maxX, int maxY,
    const TerrainSegment& terrain, std::vector<Ogre::Vector2>& result, size_t& chosenGoal, bool allowStartExit = true,
    RouteFailures* failures = nullptr)
{
    bool found = routeToAny(start, goals, obstacles, minX, minY, maxX, maxY,
        terrain, result, chosenGoal, allowStartExit, Ogre::Vector2::ZERO, std::numeric_limits<float>::infinity(),
        failures);
    if(found && result.size() == 1)
        return true;
    // Mesh roots are not necessarily centered on the body or furniture. A valid
    // narrow lane can fall between every root-aligned quarter-tile node even
    // though a body-centered lane fits. Keep the same exact edge/terrain checks.
    if(obstacles.empty() || goals.empty())
        return found;
    const Ogre::Vector2 goal = found ? goals[chosenGoal] : *std::min_element(goals.begin(), goals.end(),
        [&](const Ogre::Vector2& a, const Ogre::Vector2& b)
        { return start.squaredDistance(a) < start.squaredDistance(b); });
    float bestCost = found ? pathLength(start, result) : std::numeric_limits<float>::infinity();
    // Once a shared search selects a safe interaction endpoint, compare lane
    // alternatives to that endpoint with A*, not repeated multi-goal Dijkstra.
    Ogre::Vector2 center = (obstacles.front().bodyMinimum + obstacles.front().bodyMaximum) * 0.5f;
    Ogre::Vector2 furnitureCenter = Ogre::Vector2::ZERO;
    float nearest = std::numeric_limits<float>::infinity();
    for(const Obstacle& obstacle : obstacles)
    {
        if(!obstacle.intersects(start, goal) || obstacle.position.squaredDistance(start) >= nearest)
            continue;
        nearest = obstacle.position.squaredDistance(start);
        center = (obstacle.bodyMinimum + obstacle.bodyMaximum) * 0.5f;
        const Ogre::Vector2 localCenter = (obstacle.minimum + obstacle.maximum) * 0.5f;
        furnitureCenter = obstacle.position + Ogre::Vector2(
            localCenter.x * obstacle.cosine - localCenter.y * obstacle.sine,
            localCenter.x * obstacle.sine + localCenter.y * obstacle.cosine);
    }
    furnitureCenter.x -= std::round(furnitureCenter.x * routeCellsPerTile) * routeCellSize;
    furnitureCenter.y -= std::round(furnitureCenter.y * routeCellsPerTile) * routeCellSize;
    if(center.squaredLength() < 0.000001f && furnitureCenter.squaredLength() < 0.000001f)
        return found;
    for(int y = -1; y <= 1; ++y)
        for(int x = -1; x <= 1; ++x)
        {
            if(x == 0 && y == 0)
                continue;
            const Ogre::Vector2 heading = Ogre::Vector2(float(x), float(y)).normalisedCopy();
            const Ogre::Vector2 offset = furnitureCenter + Ogre::Vector2(center.x * heading.y + center.y * heading.x,
                -center.x * heading.x + center.y * heading.y);
            std::vector<Ogre::Vector2> candidate;
            // A valid outside route must not suppress a shorter usable lane.
            // Bound each alternative by the best complete route already found.
            size_t candidateGoal = 0;
            const bool selectedEndpoint = found && goals.size() > 1;
            const size_t selectedGoal = chosenGoal;
            const std::vector<Ogre::Vector2> targets = selectedEndpoint ? std::vector<Ogre::Vector2>{goals[chosenGoal]} : goals;
            if(routeToAny(start, targets, obstacles, minX, minY, maxX, maxY,
                terrain, candidate, candidateGoal, allowStartExit, offset, bestCost, failures))
            {
                bestCost = pathLength(start, candidate);
                result.swap(candidate);
                chosenGoal = selectedEndpoint ? selectedGoal : candidateGoal;
                found = true;
            }
        }
    return found;
}

// Searches the shortest route from the start to a single goal.
// failures (may be null): failed searches with the same obstacles and terrain, see RouteFailures.
inline bool route(const Ogre::Vector2& start, const Ogre::Vector2& goal,
    const std::vector<Obstacle>& obstacles, int minX, int minY, int maxX, int maxY,
    const TerrainSegment& terrain, std::vector<Ogre::Vector2>& result, bool allowStartExit = true,
    RouteFailures* failures = nullptr)
{
    size_t chosenGoal = 0;
    return routeToAnyAligned(start, {goal}, obstacles, minX, minY, maxX, maxY,
        terrain, result, chosenGoal, allowStartExit, failures);
}
}

#endif
