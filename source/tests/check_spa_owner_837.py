"""Owner findings of decision 837 on the lava spa (shots ODscreenshot_2026-11-07_192431_0 to _192448_3, E4 against variant 1
of D-7-v2 and the spa plan). Python only: source text, the shipped binary meshes, the texture and small models.

1  The pool attendant crouched on the floor under the chair. Cause: GameEntity::addEntityToPositionTile writes the floor
   height of the tile over z whenever an entity enters a tile, so his seat height 1.13 was lost at the spawn (server) and at
   the first setPosition on the client. PoolAttendantEntity keeps its height. The chair also stood the wrong way (backrest
   and ladder to the pool): both chair and springboard face the pool now, the ladder is behind the chair, and a red and
   white lifebuoy hangs at the chair (variant 1). Towel and whistle are part of his mesh and show once he sits on the seat.
2  The mud was near black: SpaMud multiplied the dark ground texture Dirt.png by 0.4 0.25 0.13. It has its own painted hot
   liquid mud texture, a wet gloss and a faint lava warmth now; it stays opaque (the mud hides the bathers, plan D6).
3  The white rectangles were the lava seams of rim pieces that stood on the inner edges of the pool tiles (the side angles
   were turned by 180 degrees), whose ends stuck out of the pool sides; the seam itself was white without a texture unit
   (fixed in decision 830 a). The rim pieces stand on the outer edges now.
4  Creatures walked over the pool: the pool pieces are no furniture for the route search. The route search treats the mud
   as solid now, except the tile a creature stands in and the tile it walks to (bathers wade to their place and out); the
   creature wades only when there is no way around the pool. The attendant walks around the pool on the rim.
"""
from pathlib import Path
import hashlib
import math
import re
import struct
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]


def read(relative):
    return (root / relative).read_text(encoding='utf-8')


def body(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError('unbalanced ' + signature)


def read_mesh(path):
    """Submeshes (material, positions) and the bounds of an Ogre binary mesh (MeshSerializer v1.100 chunk layout)."""
    d = path.read_bytes()
    p = 0

    def u16():
        nonlocal p
        v = struct.unpack_from('<H', d, p)[0]; p += 2; return v

    def u32():
        nonlocal p
        v = struct.unpack_from('<I', d, p)[0]; p += 4; return v

    def string():
        nonlocal p
        e = d.index(b'\n', p); s = d[p:e].decode(); p = e + 1; return s

    def geometry(end):
        nonlocal p
        n = u32(); elements = []; buffers = {}
        while p < end:
            cid = u16(); length = u32(); chunk_end = p - 6 + length
            if cid == 0x5100:
                while p < chunk_end:
                    u16(); element_length = u32()
                    source, _, semantic, offset, _ = struct.unpack_from('<5H', d, p); p += element_length - 6
                    elements.append((source, semantic, offset))
            elif cid == 0x5200:
                bind = u16(); size = u16(); u16(); data_length = u32()
                buffers[bind] = (size, p); p += data_length - 6
            p = chunk_end
        for source, semantic, offset in elements:
            if semantic == 1:
                size, start = buffers[source]
                return [struct.unpack_from('<3f', d, start + i * size + offset) for i in range(n)]
        return []

    assert u16() == 0x1000 and string().startswith('[MeshSerializer_v1.')
    submeshes, shared, bounds = [], None, None
    while p < len(d):
        cid = u16(); length = u32(); end = p - 6 + length
        if cid == 0x3000:
            p += 1
            continue
        if cid == 0x5000:
            shared = geometry(end)
        elif cid == 0x4000:
            material = string(); p += 1; count = u32(); wide = d[p]; p += 1
            indices = struct.unpack_from('<%d%s' % (count, 'I' if wide else 'H'), d, p); p += count * (4 if wide else 2)
            own = None
            while p < end:
                sub = u16(); sub_length = u32(); sub_end = p - 6 + sub_length
                if sub == 0x5000:
                    own = geometry(sub_end)
                p = sub_end
            positions = own if own else shared
            submeshes.append((material, [positions[i] for i in sorted(set(indices))]))
        elif cid == 0x9000:
            bounds = struct.unpack_from('<6f', d, p)
        p = end
    return submeshes, bounds


def span(points, axis):
    values = [q[axis] for q in points]
    return min(values), max(values)


game_entity = read('source/entities/GameEntity.cpp')
attendant_h = read('source/entities/PoolAttendantEntity.h')
attendant_cpp = read('source/entities/PoolAttendantEntity.cpp')
room_cpp = read('source/rooms/RoomSpa.cpp')
layout_h = read('source/rooms/RoomSpaLayout.h')
bounds_h = read('source/gamemap/RoomObjectBounds.h')
navigation = read('source/gamemap/RoomObjectNavigation.cpp')
navigation_h = read('source/gamemap/RoomObjectNavigation.h')
spa_material = read('materials/scripts/Spa.material')

# ---- 1  The attendant sits on the seat -----------------------------------------------------------------------------
# The cause: entering a tile writes the floor height over z
assert 'setEntityHeight(gameMap->getHeightFromTile(tile));' in body(game_entity, 'void GameEntity::addEntityToPositionTile(')
assert 'virtual void addEntityToPositionTile(GameMap* gameMap = nullptr) override;' in attendant_h
keep = body(attendant_cpp, 'void PoolAttendantEntity::addEntityToPositionTile(')
assert keep.index('const float height = getPosition().z;') < keep.index('RenderedMovableEntity::addEntityToPositionTile(gameMap);') \
    < keep.index('setEntityHeight(height);'), 'the attendant must keep the height he was given when he enters a tile'
seat_height = float(re.search(r'const double CHAIR_SEAT_HEIGHT = ([0-9.]+);', attendant_cpp).group(1))
chair, chair_bounds = read_mesh(root / 'models/SpaChair.mesh')
wood = [q for material, points in chair if material == 'SpaWood' for q in points]
seat_top = max(q[2] for q in wood if q[2] < 1.2)  # the seat plate is the highest part below the armrests (1.28)
assert abs(seat_top - seat_height) < 0.01, 'CHAIR_SEAT_HEIGHT %.3f must be the top of the seat plate %.3f' % (seat_height, seat_top)
# The chair: backrest (and the ladder under it) on -y, the seat front on +y; it stands at y - 1 of the pool with angle 0,
# so its seat faces the pool; the ladder is behind it, the attendant (mesh looks along -y) is turned 180 to the pool
backrest = [q for q in wood if q[2] > 1.45]
assert backrest and max(q[1] for q in backrest) < 0.0, 'the backrest of SpaChair is on its -y side'
assert re.search(r'const double CHAIR_ANGLE = 0\.0;', room_cpp) and re.search(r'const double SPRINGBOARD_ANGLE = 180\.0;', room_cpp)
assert re.search(r'const double ATTENDANT_ANGLE = 180\.0;', room_cpp) and \
    'spawnOnChair(getGameMap(), this, chair, static_cast<Ogre::Real>(ATTENDANT_ANGLE))' in room_cpp
assert re.search(r'const double LADDER_FOOT_OFFSET = -0\.4;', attendant_cpp), 'the foot of the ladder is behind the chair'
assert 'const Ogre::Vector3 TOWARDS_CHAIR = TOWARDS_POOL;' in attendant_cpp and 'AWAY_FROM_POOL' not in attendant_cpp
assert attendant_cpp.count('setAnimationState(PoolAttendantPose::climb, true, TOWARDS_CHAIR, false);') == 2
springboard, _ = read_mesh(root / 'models/SpaSpringboard.mesh')
board = [q for material, points in springboard if material == 'SpaWood' for q in points]
stone = [q for material, points in springboard if material == 'SpaStone' for q in points]
assert span(board, 1)[1] > 0.45 and span(stone, 1)[1] < 0.0, 'the board of SpaSpringboard reaches out on +y (180: over the pool)'
# The lifebuoy of variant 1 hangs on the +x side of the chair, outside the frame and below the seat
ring = [q for material, points in chair if material.startswith('SpaLifebuoy') for q in points]
assert {m for m, _ in chair} >= {'SpaLifebuoyRed', 'SpaLifebuoyWhite', 'SpaWood', 'SpaIron'}
assert span(ring, 0)[0] > 0.258 and span(ring, 2)[1] < seat_top - 0.1, 'the lifebuoy hangs beside the frame, below the seat'
for material in ('SpaLifebuoyRed', 'SpaLifebuoyWhite'):
    assert re.search(r'^material ' + material + r' : RTSS/PerPixel_SinglePass', spa_material, re.M), material
row = re.search(r'\{"SpaChair", ([-.0-9]+)f, ([-.0-9]+)f, ([-.0-9]+)f, ([-.0-9]+)f\}', bounds_h)
assert row and all(abs(float(a) - b) < 0.00002 for a, b in zip(row.groups(), (chair_bounds[0], chair_bounds[1],
                                                                            chair_bounds[3], chair_bounds[4]))), \
    'the SpaChair row of meshBounds must be the bounds of the mesh with the lifebuoy'
# Towel and whistle are parts of his mesh
attendant_mesh = (root / 'models/PoolAttendant.mesh').read_bytes()
assert b'SpaLinen' in attendant_mesh and b'SpaWhistle' in attendant_mesh
assert (root / 'tools/spa-meshes/add_chair_lifebuoy.py').is_file()

# ---- 2  The mud looks like hot liquid mud -------------------------------------------------------------------------------
mud = spa_material[spa_material.index('material SpaMud '):]
mud = mud[:mud.index('\n}\n')]
assert 'texture SpaMud.png' in mud and 'Dirt.png' not in mud, 'the mud has its own texture'
assert 'scroll_anim 0.02 0.01' in mud, 'the slow scroll of the plan stays'
specular = re.search(r'specular ([0-9.]+) ([0-9.]+) ([0-9.]+) 1 ([0-9.]+)', mud)
assert specular and float(specular.group(1)) >= 0.3 and float(specular.group(4)) >= 16, 'the mud is wet and glossy'
assert 'scene_blend' not in mud and 'depth_write off' not in mud, 'the mud stays opaque, it hides the bathers'
texture = root / 'materials/textures/SpaMud.png'
try:
    from PIL import Image
    image = Image.open(texture).convert('RGB')
    assert image.size == (256, 256)
    mean = [sum(c) / (256 * 256) for c in zip(*list(image.getdata()))]
    assert 0.299 * mean[0] + 0.587 * mean[1] + 0.114 * mean[2] > 55 and mean[0] > mean[2] * 1.8, \
        'the mud is a warm brown, not the old near black (about 16 9 4)'
    pixels = image.load()
    seam = sum(abs(pixels[0, y][c] - pixels[255, y][c]) + abs(pixels[y, 0][c] - pixels[y, 255][c])
               for y in range(256) for c in range(3)) / (256 * 6)
    assert seam < 12, 'the mud texture tiles without seams (mean edge step %.1f)' % seam
except ImportError:
    print('Pillow missing: the texture colour is not checked')
with tempfile.TemporaryDirectory() as folder:
    subprocess.run([sys.executable, str(root / 'tools/spa-textures/generate_spa_mud.py'), folder], check=True)
    assert hashlib.md5((Path(folder) / 'SpaMud.png').read_bytes()).digest() == hashlib.md5(texture.read_bytes()).digest(), \
        'SpaMud.png is the output of tools/spa-textures/generate_spa_mud.py'
assert 'materials/textures/SpaMud.png' in read('CREDITS')

# ---- 3  The rim stands on the outer edges ------------------------------------------------------------------------------
rim, _ = read_mesh(root / 'models/SpaPoolRim.mesh')
rim_points = [q for _, points in rim for q in points]
assert span(rim_points, 1)[1] < -0.4, 'SpaPoolRim lies on the -y edge of its tile'
angles = {name: float(value) for name, value in re.findall(r'const double OBJECT_ANGLE_SIDE_(\w+) = ([0-9.]+);', room_cpp)}
rim_body = body(room_cpp, 'void RoomSpa::updateRimObjects(')
dx = [int(v) for v in re.search(r'SIDE_DX\[\] = \{ ([^}]*) \}', rim_body).group(1).split(',')]
dy = [int(v) for v in re.search(r'SIDE_DY\[\] = \{ ([^}]*) \}', rim_body).group(1).split(',')]
order = re.search(r'SIDE_ANGLE\[\] = \{ ([^}]*) \}', rim_body).group(1).replace('\n', ' ')
names = [n.strip().replace('OBJECT_ANGLE_SIDE_', '') for n in order.split(',')]
for side_dx, side_dy, name in zip(dx, dy, names):
    angle = math.radians(angles[name])
    # The engine turns counter-clockwise: the middle of the rim (0, -0.5) goes to the side the neighbour is on
    x = 0.5 * math.sin(angle)
    y = -0.5 * math.cos(angle)
    assert abs(x - 0.5 * side_dx) < 1e-6 and abs(y - 0.5 * side_dy) < 1e-6, \
        'the rim piece for the side %d %d must stand on that side (angle %s)' % (side_dx, side_dy, angles[name])
# The seam of 830 a stays coloured by a texture unit
glow = spa_material[spa_material.index('material SpaLavaGlow'):]
assert re.search(r'texture_unit\s*\{\s*colour_op_ex source1 src_manual', glow)

# ---- 4  Nobody walks over the pool -------------------------------------------------------------------------------------
assert 'std::vector<RoomObjectPath::Obstacle> spaPoolObstacles(GameMap& map, float clearance' in navigation_h
pool_obstacles = body(navigation, 'std::vector<RoomObjectPath::Obstacle> RoomObjectNavigation::spaPoolObstacles(')
assert 'room->getType() != RoomType::spa' in pool_obstacles and 'RoomObjectPath::SPA_POOL_MESH' in pool_obstacles
assert '(tile->getX() == startX) && (tile->getY() == startY)' in pool_obstacles and \
    '(tile->getX() == goalX) && (tile->getY() == goalY)' in pool_obstacles, 'bathers wade into their place and out'
wrapper = body(navigation, 'bool RoomObjectNavigation::refine(Creature& creature, std::vector<Ogre::Vector2>& path, RouteCache& cache)')
assert wrapper.index('refineAround(creature, around, poolCache, pool)') < \
    wrapper.index('return refineAround(creature, path, cache, std::vector<RoomObjectPath::Obstacle>());'), \
    'refine() tries the way around the pool first and wades only when there is none'
around = body(navigation, 'static bool refineAround(')
assert 'for(RoomObjectPath::Obstacle piece : pool)' in around and 'withWalkingBody(creature, pool)' in around, \
    'the pool pieces are solid in the nearby test and in the route search'

# The attendant walks around the pool on the rim: a model of SpaLayout::rimWalk on a 5x5 spa (pool 3x3)
assert 'const int32_t POOL_STEP_COST = 100;' in layout_h and 'inline bool rimWalk(' in layout_h
assert 'mRoom->getAttendantWalk(start, std::make_pair(board->getX(), board->getY()), tiles)' in attendant_cpp
assert 'mRoom->getAttendantWalk(start, std::make_pair(chair.first + candidate, chair.second), walk)' in attendant_cpp


def rim_walk(covered, pool, start, goal):
    import heapq
    queue, cost, previous = [(0, start)], {start: 0}, {}
    while queue:
        c, tile = heapq.heappop(queue)
        if tile == goal:
            path = []
            while tile != start:
                path.insert(0, tile); tile = previous[tile]
            return path
        if c > cost[tile]:
            continue
        for ndx, ndy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            nxt = (tile[0] + ndx, tile[1] + ndy)
            if nxt in covered:
                step = 100 if nxt in pool else 1
                if c + step < cost.get(nxt, 1 << 30):
                    cost[nxt] = c + step; previous[nxt] = tile; heapq.heappush(queue, (c + step, nxt))
    return None


covered = {(x, y) for x in range(15, 20) for y in range(7, 12)}
pool = {(x, y) for x in range(16, 19) for y in range(8, 11)}
chair_tile, board_tile, first_place = (16, 7), (18, 11), (16, 8)
to_board = rim_walk(covered, pool, chair_tile, board_tile)
assert to_board and not (set(to_board) & pool), 'the walk to the springboard stays on the rim'
back = min((rim_walk(covered, pool, first_place, (chair_tile[0] + s, chair_tile[1])) for s in (-1, 1)), key=len)
assert not (set(back) & pool), 'after the landing he wades out of his own tile only'
print('check_spa_owner_837 ok')
