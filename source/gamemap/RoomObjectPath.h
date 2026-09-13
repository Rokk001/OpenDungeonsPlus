#ifndef ROOMOBJECTPATH_H
#define ROOMOBJECTPATH_H

#include <OgreVector2.h>
#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <limits>
#include <queue>
#include <vector>

namespace RoomObjectPath
{
// Furniture bounds are expressed in mesh-local XY, before the placed object's
// rotation. Clearance belongs to the moving creature, not to the mesh asset.
struct Obstacle
{
    Ogre::Vector2 minimum, maximum, position;
    float cosine, sine;
    Ogre::Vector2 bodyMinimum = Ogre::Vector2::ZERO;
    Ogre::Vector2 bodyMaximum = Ogre::Vector2::ZERO;
    Ogre::Vector2 initialHeading = Ogre::Vector2(0, -1);
    // A nonnegative radius is a logical circular footprint with moving-body
    // clearance already included; negative retains the oriented-box geometry.
    float radius = -1.0f;
    Ogre::Vector2 bodyAxisMinimum = Ogre::Vector2::ZERO;
    Ogre::Vector2 bodyAxisMaximum = Ogre::Vector2::ZERO;
    float bodyCosine = 1.0f, bodySine = 0.0f;
    bool hasBodyAxes = false;
    Ogre::Vector2 worldMinimum, worldMaximum;
    bool hasWorldBounds = false;

    static Obstacle circle(const Ogre::Vector2& center, float clearanceRadius)
    {
        Obstacle result{Ogre::Vector2(-clearanceRadius), Ogre::Vector2(clearanceRadius), center, 1, 0};
        result.radius = clearanceRadius;
        return result;
    }

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
        const auto center = (result.minimum + result.maximum) * 0.5f;
        const auto half = (result.maximum - result.minimum) * 0.5f;
        const auto worldCenter = position + Ogre::Vector2(cosine * center.x - sine * center.y,
            sine * center.x + cosine * center.y);
        const Ogre::Vector2 extent(std::abs(cosine) * half.x + std::abs(sine) * half.y + 0.00001f,
            std::abs(sine) * half.x + std::abs(cosine) * half.y + 0.00001f);
        result.worldMinimum = worldCenter - extent;
        result.worldMaximum = worldCenter + extent;
        result.hasWorldBounds = true;
        return result;
    }

    Ogre::Vector2 local(const Ogre::Vector2& point) const
    {
        const auto relative = point - position;
        return Ogre::Vector2(cosine * relative.x + sine * relative.y,
            -sine * relative.x + cosine * relative.y);
    }

    Ogre::Vector2 bodyLocal(const Ogre::Vector2& point) const
    {
        const auto relative = point - position;
        return Ogre::Vector2(bodyCosine * relative.x + bodySine * relative.y,
            -bodySine * relative.x + bodyCosine * relative.y);
    }

    bool contains(const Ogre::Vector2& point, const Ogre::Vector2& heading = Ogre::Vector2::ZERO) const
    {
        if(radius >= 0.0f)
            return point.squaredDistance(position) < radius * radius;
        const auto bounds = forHeading(heading);
        const auto p = local(point);
        if(p.x <= bounds.minimum.x || p.x >= bounds.maximum.x ||
           p.y <= bounds.minimum.y || p.y >= bounds.maximum.y)
            return false;
        const auto bodyPoint = bounds.bodyLocal(point);
        return !bounds.hasBodyAxes || (bodyPoint.x > bounds.bodyAxisMinimum.x &&
            bodyPoint.x < bounds.bodyAxisMaximum.x && bodyPoint.y > bounds.bodyAxisMinimum.y &&
            bodyPoint.y < bounds.bodyAxisMaximum.y);
    }

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
            const auto delta = to - from;
            const float lengthSquared = delta.squaredLength();
            const float along = lengthSquared > 0.0f ?
                std::max(0.0f, std::min(1.0f, (position - from).dotProduct(delta) / lengthSquared)) : 0.0f;
            return contains(from + delta * along);
        }
        const auto bounds = forHeading(to - from);
        const auto localFrom = local(from), localDelta = local(to) - localFrom;
        const auto bodyFrom = bounds.bodyLocal(from), bodyDelta = bounds.bodyLocal(to) - bodyFrom;
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
    for(const auto& obstacle : obstacles)
        if(obstacle.contains(point, heading))
            return false;
    return true;
}

inline bool clearSegment(const std::vector<Obstacle>& obstacles,
    const Ogre::Vector2& from, const Ogre::Vector2& to, bool allowExit = false)
{
    for(const auto& obstacle : obstacles)
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

// The existing map supplies terrain/door checks for an entire segment. Furniture
// is checked analytically, so even thin and rotated objects cannot be skipped.
using TerrainSegment = std::function<bool(const Ogre::Vector2&, const Ogre::Vector2&)>;

inline bool routeToAny(const Ogre::Vector2& start, const std::vector<Ogre::Vector2>& goals,
    const std::vector<Obstacle>& obstacles, int minX, int minY, int maxX, int maxY,
    const TerrainSegment& terrain, std::vector<Ogre::Vector2>& result, size_t& chosenGoal, bool allowStartExit = true,
    const Ogre::Vector2& gridOffset = Ogre::Vector2::ZERO,
    float maximumCost = std::numeric_limits<float>::infinity())
{
    result.clear();
    if(goals.empty())
        return false;
    if(goals.size() == 1 && start.distance(goals.front()) >= maximumCost)
        return false;
    for(size_t i = 0; i < goals.size(); ++i)
    {
        const auto& goal = goals[i];
        if(clearPoint(obstacles, goal) && terrain(goal, goal) && clearSegment(obstacles, start, goal, allowStartExit) && terrain(start, goal))
        {
            chosenGoal = i;
            result.push_back(goal);
            return true;
        }
    }

    // Quarter-tile nodes refine the existing tile path only where furniture
    // obstructs it; endpoints retain the precise room-interaction offsets.
    const int width = (maxX - minX) * 4 + 1;
    const int height = (maxY - minY) * 4 + 1;
    if(width <= 0 || height <= 0)
        return false;
    const int count = width * height;
    std::vector<float> costs(count, std::numeric_limits<float>::infinity());
    std::vector<int> parents(count, -1);
    std::vector<size_t> terminals(count, 0);
    std::vector<float> forwardCosts(count, std::numeric_limits<float>::infinity());
    std::vector<int> forwardParents(count, -1);
    using Entry = std::pair<float, int>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> open;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> forwardOpen;
    const auto position = [&](int index)
    {
        return Ogre::Vector2(minX + (index % width) * 0.25f,
            minY + (index / width) * 0.25f) + gridOffset;
    };
    // Opposite consistent potentials keep the two A* frontiers comparable;
    // their sum is a lower bound on the remaining complete route cost.
    const auto potential = [&](int index)
    { return goals.size() == 1 ? 0.5f * (position(index).distance(goals.front()) - position(index).distance(start)) : 0.0f; };
    const auto add = [&](int index, float cost, int parent)
    {
        if(cost >= costs[index])
            return;
        costs[index] = cost;
        parents[index] = parent;
        open.emplace(cost - potential(index), index);
    };

    // Usually only the surrounding grid nodes are needed. If old save data or
    // newly placed furniture overlaps the start, connect an outward exit first.
    const auto initialHeading = obstacles.empty() ? Ogre::Vector2(0, -1) : obstacles.front().initialHeading;
    const float reach = !allowStartExit || clearPoint(obstacles, start, initialHeading) ? 0.4f : 3.0f;
    const int firstX = std::max(0, int(std::floor((start.x - reach - minX - gridOffset.x) * 4)));
    const int lastX = std::min(width - 1, int(std::ceil((start.x + reach - minX - gridOffset.x) * 4)));
    const int firstY = std::max(0, int(std::floor((start.y - reach - minY - gridOffset.y) * 4)));
    const int lastY = std::min(height - 1, int(std::ceil((start.y + reach - minY - gridOffset.y) * 4)));
    for(int y = firstY; y <= lastY; ++y)
        for(int x = firstX; x <= lastX; ++x)
        {
            const int index = y * width + x;
            const auto point = position(index);
            if(clearPoint(obstacles, point) && clearSegment(obstacles, start, point, allowStartExit) && terrain(start, point))
            {
                forwardCosts[index] = start.distance(point);
                forwardOpen.emplace(forwardCosts[index] + potential(index), index);
            }
        }
    if(forwardOpen.empty())
        return false;
    // Connect both endpoints: either may be isolated by furniture, independently
    // of the terrain-only coarse route. Exhausting either frontier proves failure.
    for(size_t i = 0; i < goals.size(); ++i)
    {
        const auto& goal = goals[i];
        if(!clearPoint(obstacles, goal) || !terrain(goal, goal))
            continue;
        const int goalFirstX = std::max(0, int(std::floor((goal.x - 0.5f - minX - gridOffset.x) * 4)));
        const int goalLastX = std::min(width - 1, int(std::ceil((goal.x + 0.5f - minX - gridOffset.x) * 4)));
        const int goalFirstY = std::max(0, int(std::floor((goal.y - 0.5f - minY - gridOffset.y) * 4)));
        const int goalLastY = std::min(height - 1, int(std::ceil((goal.y + 0.5f - minY - gridOffset.y) * 4)));
        for(int y = goalFirstY; y <= goalLastY; ++y)
            for(int x = goalFirstX; x <= goalLastX; ++x)
            {
                const int index = y * width + x;
                const auto point = position(index);
                if(point.distance(goal) < costs[index] && point.squaredDistance(goal) <= 0.25f && clearSegment(obstacles, point, goal) && terrain(point, goal))
                {
                    terminals[index] = i;
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
            auto& edge = edgeObstacles[(dy + 1) * 3 + dx + 1];
            edge.reserve(obstacles.size());
            for(const auto& obstacle : obstacles)
                edge.push_back(obstacle.forHeading(Ogre::Vector2(float(-dx), float(-dy))));
        }
    int destination = -1;
    float best = maximumCost;
    bool forward = false;
    while(!open.empty() && !forwardOpen.empty())
    {
        while(!open.empty() && open.top().first > costs[open.top().second] - potential(open.top().second) + 0.0001f)
            open.pop();
        while(!forwardOpen.empty() && forwardOpen.top().first > forwardCosts[forwardOpen.top().second] + potential(forwardOpen.top().second) + 0.0001f)
            forwardOpen.pop();
        if(open.empty() || forwardOpen.empty() ||
            open.top().first + forwardOpen.top().first >= best)
            break;
        forward = !forward;
        auto& frontier = forward ? forwardOpen : open;
        auto& distances = forward ? forwardCosts : costs;
        auto& links = forward ? forwardParents : parents;
        const auto entry = frontier.top();
        frontier.pop();
        const int current = entry.second;
        const auto point = position(current);
        const int x = current % width, y = current / width;
        if(forwardCosts[current] + costs[current] < best)
        {
            destination = current;
            best = forwardCosts[current] + costs[current];
        }
        for(int dy = -1; dy <= 1; ++dy)
            for(int dx = -1; dx <= 1; ++dx)
            {
                if((dx == 0 && dy == 0) || x + dx < 0 || x + dx >= width || y + dy < 0 || y + dy >= height)
                    continue;
                const int next = (y + dy) * width + x + dx;
                const auto target = position(next);
                const float nextCost = distances[current] + point.distance(target);
                if(nextCost >= distances[next])
                    continue;
                const auto from = forward ? point : target;
                const auto to = forward ? target : point;
                const int heading = forward ? (1 - dy) * 3 + 1 - dx : (dy + 1) * 3 + dx + 1;
                if(!clearSegment(edgeObstacles[heading], from, to) || !terrain(from, to))
                    continue;
                distances[next] = nextCost;
                links[next] = current;
                frontier.emplace(nextCost + (forward ? potential(next) : -potential(next)), next);
                if(forwardCosts[next] + costs[next] < best)
                {
                    destination = next;
                    best = forwardCosts[next] + costs[next];
                }
            }
    }
    if(destination < 0)
        return false;
    for(int index = destination; index >= 0; index = forwardParents[index])
        result.push_back(position(index));
    std::reverse(result.begin(), result.end());
    for(int index = parents[destination]; index >= 0; index = parents[index])
        result.push_back(position(index));
    int terminal = destination;
    while(parents[terminal] >= 0)
        terminal = parents[terminal];
    chosenGoal = terminals[terminal];
    result.push_back(goals[chosenGoal]);

    // Collapse only collinear runs: a visual/client interpolation must not cut a
    // corner through an obstacle or silently bypass an existing terrain rule.
    for(size_t i = 1; i + 1 < result.size();)
    {
        const auto a = result[i] - result[i - 1];
        const auto b = result[i + 1] - result[i];
        if(std::abs(a.crossProduct(b)) < 0.00001f && a.dotProduct(b) >= 0.0f)
            result.erase(result.begin() + i);
        else
            ++i;
    }
    return true;
}

inline bool route(const Ogre::Vector2& start, const Ogre::Vector2& goal,
    const std::vector<Obstacle>& obstacles, int minX, int minY, int maxX, int maxY,
    const TerrainSegment& terrain, std::vector<Ogre::Vector2>& result, bool allowStartExit = true)
{
    size_t chosenGoal = 0;
    bool found = routeToAny(start, {goal}, obstacles, minX, minY, maxX, maxY,
        terrain, result, chosenGoal, allowStartExit);
    if(found && result.size() == 1)
        return true;
    // Mesh roots are not necessarily centered on the body or furniture. A valid
    // narrow lane can fall between every root-aligned quarter-tile node even
    // though a body-centered lane fits. Keep the same exact edge/terrain checks.
    if(obstacles.empty())
        return found;
    const auto length = [&](const std::vector<Ogre::Vector2>& path)
    {
        float cost = 0;
        auto previous = start;
        for(const auto& point : path)
        {
            cost += previous.distance(point);
            previous = point;
        }
        return cost;
    };
    float bestCost = found ? length(result) : std::numeric_limits<float>::infinity();
    const auto center = (obstacles.front().bodyMinimum + obstacles.front().bodyMaximum) * 0.5f;
    Ogre::Vector2 furnitureCenter = Ogre::Vector2::ZERO;
    float nearest = std::numeric_limits<float>::infinity();
    for(const auto& obstacle : obstacles)
    {
        if(!obstacle.intersects(start, goal) || obstacle.position.squaredDistance(start) >= nearest)
            continue;
        nearest = obstacle.position.squaredDistance(start);
        const auto localCenter = (obstacle.minimum + obstacle.maximum) * 0.5f;
        furnitureCenter = obstacle.position + Ogre::Vector2(
            localCenter.x * obstacle.cosine - localCenter.y * obstacle.sine,
            localCenter.x * obstacle.sine + localCenter.y * obstacle.cosine);
    }
    furnitureCenter.x -= std::round(furnitureCenter.x * 4.0f) * 0.25f;
    furnitureCenter.y -= std::round(furnitureCenter.y * 4.0f) * 0.25f;
    if(center.squaredLength() < 0.000001f && furnitureCenter.squaredLength() < 0.000001f)
        return found;
    for(int y = -1; y <= 1; ++y)
        for(int x = -1; x <= 1; ++x)
        {
            if(x == 0 && y == 0)
                continue;
            const auto heading = Ogre::Vector2(float(x), float(y)).normalisedCopy();
            const auto offset = furnitureCenter + Ogre::Vector2(center.x * heading.y + center.y * heading.x,
                -center.x * heading.x + center.y * heading.y);
            std::vector<Ogre::Vector2> candidate;
            // A valid outside route must not suppress a shorter usable lane.
            // Bound each alternative by the best complete route already found.
            if(routeToAny(start, {goal}, obstacles, minX, minY, maxX, maxY,
                terrain, candidate, chosenGoal, allowStartExit, offset, bestCost))
            {
                bestCost = length(candidate);
                result.swap(candidate);
                found = true;
            }
        }
    return found;
}
}

#endif
