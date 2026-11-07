"""Decision 727, case walls: no step of a walk path goes over a wall tile.

Root cause for the part that is a path property (found by reading the history): the server only sent smoothed or
searched paths without client jitter. Every other path kept walkDistortion, and the client moves each coordinate of
every walk point of such a path by up to +/-0.3 (ODClient animatedObjectSetWalkPath -> correctEntityMovePosition). The
walls were never part of that decision: the furniture test (collect with WALK_DISTORTION_REACH) looks at objects only. A
creature with walking radius r > 0.2 therefore walked with its body over the wall tiles next to its path (a 1-wide
corridor, a room edge). RoomObjectNavigation::walkDistortionReachesWall now switches the jitter off for such a path in
MovableGameEntity::setWalkPath. The wide-creature kicks onto steppable ghost room apparatuses and graves are the lifted
cases (see check_path_not_over_ghost_apparatus.py and check_path_not_over_graves.py), Creature::keepOffWalls stays only
the safety net.
Also checks the route search: every grid edge, start and goal connection of RoomObjectPath::routeToAny and every leg of
smoothCorridor is tested against the terrain, with a model of that test on random maps.
No compiler needed."""
from pathlib import Path
import math
import random
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def between(text, start, end):
    assert start in text, start
    part = text.split(start, 1)[1]
    assert end in part, end
    return part.split(end, 1)[0]


nav = read('source/gamemap/RoomObjectNavigation.cpp')
path_header = read('source/gamemap/RoomObjectPath.h')
movable = read('source/entities/MovableGameEntity.cpp')
client = read('source/network/ODClient.cpp')

# --- the route search never takes a step that the terrain test rejects --------------------------------------------
search = between(path_header, 'inline bool routeToAny(', 'inline bool routeToAnyAligned(')
assert 'terrain(start, point)' in search            # first node of the start
assert 'terrain(point, goal)' in search             # first node of the goal
assert '!terrain(from, to)' in search               # every edge between two grid nodes
assert 'terrain(goal, goal)' in search and 'terrain(start, goal)' in search
refine = between(nav, 'static bool refineAround(Creature& creature, std::vector<Ogre::Vector2>& path, RoomObjectNavigation::RouteCache& cache,',
                 'bool RoomObjectNavigation::refine(Creature& creature, std::vector<Ogre::Vector2>& path)\n')
assert '{ return terrainClear(passable, from, to); }' in refine
smooth = between(nav, 'bool smoothCorridor(', 'void keepObstaclesNear')
assert 'terrainClearForBody(passable, from, to, bodyRadius)' in smooth
terrain_fn = between(nav, 'bool terrainClear(PassableTiles& passable', '//! Largest margin a smoothed path')
assert terrain_fn.count('passable.isPassable(') >= 4  # start tile, every sample, both side tiles at a corner
samples = float(between(nav, 'const float TERRAIN_SAMPLES_PER_TILE = ', 'f;'))


def round_half_up(value):
    return int(math.floor(value + 0.5))


def terrain_clear(wall, p, q):
    """Model of terrainClear: wall(x, y) is True for a tile that cannot be walked on."""
    px, py = round_half_up(p[0]), round_half_up(p[1])
    if wall(px, py):
        return False
    steps = max(1, int(math.ceil(math.dist(p, q) * samples)))
    for i in range(1, steps + 1):
        point = (p[0] + (q[0] - p[0]) * i / steps, p[1] + (q[1] - p[1]) * i / steps)
        x, y = round_half_up(point[0]), round_half_up(point[1])
        if wall(x, y):
            return False
        if x != px and y != py and (wall(x, py) or wall(px, y)):
            return False
        px, py = x, y
    return True


random.seed(727)
accepted = 0
for _ in range(300):
    size = 12
    walls = {(x, y) for x in range(size) for y in range(size) if random.random() < 0.3}
    wall = lambda x, y: (x, y) in walls or not (0 <= x < size and 0 <= y < size)
    for _ in range(40):
        p = (random.uniform(0, size - 1), random.uniform(0, size - 1))
        direction = random.choice([(1, 0), (0, 1), (1, 1), (1, -1), (-1, 1), (-1, -1), (-1, 0), (0, -1)])
        q = (p[0] + direction[0] * 0.25, p[1] + direction[1] * 0.25)  # one edge of the quarter-tile grid
        if not terrain_clear(wall, p, q):
            continue
        accepted += 1
        for i in range(0, 65):  # dense samples, 64 per edge: no point goes deeper than 1/16 into a wall tile
            point = (p[0] + (q[0] - p[0]) * i / 64, p[1] + (q[1] - p[1]) * i / 64)
            x, y = round_half_up(point[0]), round_half_up(point[1])
            if wall(x, y):
                depth = min(0.5 - abs(point[0] - x), 0.5 - abs(point[1] - y))
                assert depth <= 1.0 / samples + 1e-6, (p, q, point, depth)
assert accepted > 1000, accepted

# --- the client jitter cannot carry the body over a wall -----------------------------------------------------------
assert 'static const double offset = 0.3;' in read('source/entities/Creature.cpp')
assert 'if(walkDistortion)\n                    tempAnimatedObject->correctEntityMovePosition(dest);' in client
guard = between(movable, 'RoomObjectNavigation::refine(static_cast<Creature&>(*this), walkPath))', 'mWalkQueue.clear();')
assert 'RoomObjectNavigation::separate(static_cast<Creature&>(*this), walkPath);' in guard
assert ('if(walkDistortion && getIsOnServerMap() && getObjectType() == GameEntityType::creature &&\n'
        '        RoomObjectNavigation::walkDistortionReachesWall(static_cast<Creature&>(*this), walkPath))\n'
        '        walkDistortion = false;') in guard
assert guard.index('separate(') < guard.index('walkDistortionReachesWall(')  # the destination spreading still sees the flag
assert 'bool walkDistortionReachesWall(Creature& creature, const std::vector<Ogre::Vector2>& path);' in read('source/gamemap/RoomObjectNavigation.h')
body = between(nav, 'bool RoomObjectNavigation::walkDistortionReachesWall(', 'bool RoomObjectNavigation::blocked(')
assert 'canGoThroughTile(neighbour)' in body and 'dx == 0 && dy == 0' in body
jitter = float(between(nav, 'const float WALK_DISTORTION_JITTER = ', 'f;'))
half = float(between(nav, 'const float HALF_TILE = ', 'f;'))
assert jitter == 0.3 and half == 0.5


def reaches_wall(wall, radius, path):
    """Model of walkDistortionReachesWall."""
    if radius + jitter <= half:
        return False
    return any(wall(round_half_up(x) + dx, round_half_up(y) + dy)
               for x, y in path for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


checked = 0
for _ in range(2000):
    size = 10
    walls = {(x, y) for x in range(size) for y in range(size) if random.random() < 0.25}
    wall = lambda x, y: (x, y) in walls
    radius = random.choice([0.2, 0.3, 0.42, 0.64])
    free = [(x, y) for x in range(size) for y in range(size) if (x, y) not in walls]
    if len(free) < 3:
        continue
    path = [random.choice(free) for _ in range(3)]
    if reaches_wall(wall, radius, path):
        continue
    checked += 1
    for _ in range(20):  # any jitter of the client: the body (a square of the walking radius) stays off wall tiles
        for x, y in path:
            jx, jy = x + random.uniform(-jitter, jitter), y + random.uniform(-jitter, jitter)
            for cx in (jx - radius, jx + radius):
                for cy in (jy - radius, jy + radius):
                    assert not wall(round_half_up(cx), round_half_up(cy)), (radius, path)
assert checked > 100, checked
print('ok')
