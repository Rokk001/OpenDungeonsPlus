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

    Obstacle forHeading(Ogre::Vector2 direction) const
    {
        Obstacle result = *this;
        if(bodyMinimum == Ogre::Vector2::ZERO && bodyMaximum == Ogre::Vector2::ZERO)
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
        result.bodyMinimum = result.bodyMaximum = Ogre::Vector2::ZERO;
        return result;
    }

    Ogre::Vector2 local(const Ogre::Vector2& point) const
    {
        const auto relative = point - position;
        return Ogre::Vector2(cosine * relative.x + sine * relative.y,
            -sine * relative.x + cosine * relative.y);
    }

    bool contains(const Ogre::Vector2& point, const Ogre::Vector2& heading = Ogre::Vector2::ZERO) const
    {
        const auto bounds = forHeading(heading);
        const auto p = local(point);
        return p.x > bounds.minimum.x && p.x < bounds.maximum.x &&
            p.y > bounds.minimum.y && p.y < bounds.maximum.y;
    }

    bool intersects(const Ogre::Vector2& from, const Ogre::Vector2& to) const
    {
        const auto bounds = forHeading(to - from);
        const auto a = local(from);
        const auto delta = local(to) - a;
        float enter = 0.0f, leave = 1.0f;
        for(int axis = 0; axis < 2; ++axis)
        {
            if(std::abs(delta[axis]) < 0.00001f)
            {
                if(a[axis] <= bounds.minimum[axis] || a[axis] >= bounds.maximum[axis])
                    return false;
                continue;
            }
            float low = (bounds.minimum[axis] - a[axis]) / delta[axis];
            float high = (bounds.maximum[axis] - a[axis]) / delta[axis];
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

inline bool route(const Ogre::Vector2& start, const Ogre::Vector2& goal,
    const std::vector<Obstacle>& obstacles, int minX, int minY, int maxX, int maxY,
    const TerrainSegment& terrain, std::vector<Ogre::Vector2>& result, bool allowStartExit = true)
{
    result.clear();
    if(!clearPoint(obstacles, goal) || !terrain(goal, goal))
        return false;
    if(clearSegment(obstacles, start, goal, allowStartExit) && terrain(start, goal))
    {
        result.push_back(goal);
        return true;
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
    using Entry = std::pair<float, int>;
    std::priority_queue<Entry, std::vector<Entry>, std::greater<Entry>> open;
    const auto position = [&](int index)
    {
        return Ogre::Vector2(minX + (index % width) * 0.25f,
            minY + (index / width) * 0.25f);
    };
    const auto add = [&](int index, float cost, int parent)
    {
        if(cost >= costs[index])
            return;
        costs[index] = cost;
        parents[index] = parent;
        open.emplace(cost + position(index).distance(start), index);
    };

    // Usually only the surrounding grid nodes are needed. If old save data or
    // newly placed furniture overlaps the start, connect an outward exit first.
    const auto initialHeading = obstacles.empty() ? Ogre::Vector2(0, -1) : obstacles.front().initialHeading;
    const float reach = !allowStartExit || clearPoint(obstacles, start, initialHeading) ? 0.4f : 3.0f;
    const int firstX = std::max(0, int(std::floor((start.x - reach - minX) * 4)));
    const int lastX = std::min(width - 1, int(std::ceil((start.x + reach - minX) * 4)));
    const int firstY = std::max(0, int(std::floor((start.y - reach - minY) * 4)));
    const int lastY = std::min(height - 1, int(std::ceil((start.y + reach - minY) * 4)));
    // Search backwards along valid forward movement edges: an enclosed room
    // destination then exhausts its small component instead of the whole map.
    const int goalFirstX = std::max(0, int(std::floor((goal.x - 0.5f - minX) * 4)));
    const int goalLastX = std::min(width - 1, int(std::ceil((goal.x + 0.5f - minX) * 4)));
    const int goalFirstY = std::max(0, int(std::floor((goal.y - 0.5f - minY) * 4)));
    const int goalLastY = std::min(height - 1, int(std::ceil((goal.y + 0.5f - minY) * 4)));
    for(int y = goalFirstY; y <= goalLastY; ++y)
        for(int x = goalFirstX; x <= goalLastX; ++x)
        {
            const int index = y * width + x;
            const auto point = position(index);
            if(point.squaredDistance(goal) <= 0.25f && clearSegment(obstacles, point, goal) && terrain(point, goal))
                add(index, point.distance(goal), -1);
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
    while(!open.empty())
    {
        const auto entry = open.top();
        open.pop();
        const int current = entry.second;
        const auto point = position(current);
        if(entry.first > costs[current] + point.distance(start) + 0.0001f)
            continue;
        const int x = current % width, y = current / width;
        if(x >= firstX && x <= lastX && y >= firstY && y <= lastY &&
            clearPoint(obstacles, point) && clearSegment(obstacles, start, point, allowStartExit) && terrain(start, point))
        {
            destination = current;
            break;
        }
        for(int dy = -1; dy <= 1; ++dy)
            for(int dx = -1; dx <= 1; ++dx)
            {
                if((dx == 0 && dy == 0) || x + dx < 0 || x + dx >= width || y + dy < 0 || y + dy >= height)
                    continue;
                const int next = (y + dy) * width + x + dx;
                const auto target = position(next);
                const float nextCost = costs[current] + point.distance(target);
                if(nextCost >= costs[next])
                    continue;
                if(clearSegment(edgeObstacles[(dy + 1) * 3 + dx + 1], target, point) && terrain(target, point))
                    add(next, nextCost, current);
            }
    }
    if(destination < 0)
        return false;
    for(int index = destination; index >= 0; index = parents[index])
        result.push_back(position(index));
    result.push_back(goal);

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
}

#endif
