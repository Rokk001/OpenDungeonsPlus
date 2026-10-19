"""Noncompiling spacing contracts and measured-body placement counterexamples.

Executes the production rectangle rejection and candidate-coordinate expressions.
This does not execute the C++ simulation or replace integration gameplay checks.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import itertools
import math
import re

ROOT = Path(__file__).resolve().parents[2]


# Read one production source without starting any external program.
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# Isolate a C++ function at its existing unindented closing brace.
def body(source, signature):
    part = source[source.index(signature):]
    return part[:part.index("\n}\n")]


navigation = read("source/gamemap/RoomObjectNavigation.cpp")
separate = body(navigation, "bool RoomObjectNavigation::separate(")
occupancy = body(navigation, "bool interactionPositionClear(")
bodies = body(navigation, "std::vector<RoomObjectPath::Obstacle> standingBodies(")
footprint = body(navigation, "RoomObjectPath::Obstacle interactionFootprint(")
assert "RoomObjectPath::walkingRadii" in footprint and "creature.getLevelScale()" in footprint
assert "minimum = {model.minX, model.minY}" in footprint and "maximum = {model.maxX, model.maxY}" in footprint
assert "return {minimum * scale, maximum * scale, position, -direction.y, direction.x};" in footprint
for token in ("other == &creature", "!other->getIsOnMap()", "!other->isAlive()",
              "other->getWalkQueue()", "queue.back()", "other->getPosition()"):
    assert token in bodies
assert "other.bodyMinimum = footprint.minimum" in occupancy
assert "other.bodyMaximum = footprint.maximum" in occupancy
assert "other.contains(point, direction)" in occupancy
assert "getInteractionPositions()" in occupancy and "standingBodies(creature)" in occupancy
assert "CreatureActionType::digTile" in separate and "CreatureActionType::parkToTile" in separate
for token in ("!creature.getIsOnServerMap()", "obstacle.forHeading(heading)",
              "candidates.emplace(point.squaredDistance(wanted), point)", "!creature.canGoThroughTile(tile)",
              "route.back() != point", "blocked(creature, route)", "interactionPositionClear(creature, point, arrival)"):
    assert token in separate
walk = body(read("source/entities/MovableGameEntity.cpp"), "void MovableGameEntity::setWalkPath(")
assignment = walk[walk.index("if(spaceDestination)"):walk.index("mWalkQueue.clear();")]
assert "RoomObjectNavigation::separate(" in assignment and "walkDistortion = false;" in assignment
assert "if(spaceDestination &&" not in walk
assert walk.index("RoomObjectNavigation::separate(") < walk.index("serverNotification->mPacket << walkDistortion")
assert "walkDistortion && !pathAlreadyRefined && getIsOnServerMap()" in walk
work = body(navigation, "bool RoomObjectNavigation::workApproach(")
assert "for(bool includeBodies : {true, false})" in work
assert "interactionPositionClear(creature, point, facing - point, includeBodies)" in work
assert "tile->getCoveringRoom() != room" in work and "!terrainClear(creature, staging, point)" in work
assert occupancy.index("getInteractionPositions()") < occupancy.index("if(!includeBodies)")
creature = read("source/entities/Creature.cpp")
for action in ("fight", "fightFriendly", "watchBanner"):
    assert "standingAction == CreatureActionType::" + action in creature
for room in ("temple", "guardRoom", "arena", "hatchery"):
    assert "standingRoom->getType() == RoomType::" + room in creature
assert "!isMoving() && (mActions.empty()" in creature
food = body(navigation, "bool RoomObjectNavigation::foodApproach(")
assert "for(bool includeBodies : {true, false})" in food
assert "includeBodies && !interactionPositionClear(creature, point, direction)" in food
assert "const bool adjacentStand = mActions.empty() || (freeRoomStand &&" in creature
assert "RoomObjectNavigation::separate(*this, path, adjacentStand, freeRoomStand ? standingRoom : nullptr)" in creature
assert "(room != nullptr && tile->getCoveringRoom() != room)" in separate
assert "path, false, true);" in body(creature, "bool Creature::parkToWallTile(")
heart = body(read("source/creatureaction/CreatureActionGoDefendHeart.cpp"),
             "bool CreatureActionGoDefendHeart::handleDefendHeart(")
assert "std::abs(myTile->getX() - targetTile->getX()) <= 1" in heart
assert "std::abs(myTile->getY() - targetTile->getY()) <= 1" in heart
assert "if(standing.back() == position)" in heart and "standing, false, true);" in heart
assert "if(action->mTargetTile != targetTile)" in heart and "action->mStandingTile = nullptr;" in heart
assert "myTile == action->mStandingTile" in heart and "action->mStandingTile = creature.getGameMap()->getTile(" in heart
assert "ring <= lastRing" in separate
assert separate.index("interactionPositionClear(creature, wanted, heading)") < separate.index("if(adjacent)")
assert "(room == nullptr || wantedTile->getCoveringRoom() == room)" in separate
assert "map.getMapSizeX() - 1 - centerX" in separate and "map.getMapSizeY() - 1 - centerY" in separate
assert separate.index("if(!separate(creature, probe, false, room))") < separate.index("const std::list<Tile*> tiles = map.path(&creature, tile);")
assert "if(tiles.empty())" in separate and "nearestPath.empty()" in separate
assert "setPosition(" not in separate and "setPosition(" not in heart
combat = body(creature, "bool Creature::searchBestTargetInList(")
assert "const bool inRange = rangeTarget <= (skillRangeMax * skillRangeMax);" in combat
assert "const bool freeTile = RoomObjectNavigation::separate(*this, standing);" in combat
assert "if(!freeTile && (freePosition || inRange))" in combat
assert combat.index("if(freeTile && !freePosition)") < combat.index("bestScoreAttack = scoreAttack;")
assert "if(RoomObjectNavigation::separate(*this, standing))\n                 continue;" in combat

# Evaluate the actual axis-separation condition; touching measured bounds is allowed.
path_source = read("source/gamemap/RoomObjectPath.h")
for token in ("result.minimum -= high;", "result.maximum -= low;",
              "result.bodyAxisMinimum = low - bodyMaximum;", "result.bodyAxisMaximum = high - bodyMinimum;"):
    assert token in path_source
expression = re.search(r"if\((p.x <= bounds.minimum.x.*?)\)\s*return false;", path_source, re.S)[1]
expression = " ".join(expression.replace("||", " or ").split())
axes_expression = re.search(r"return (!bounds.hasBodyAxes.*?)\;", path_source, re.S)[1]
axes_expression = " ".join(axes_expression.replace("||", " or ").replace("&&", " and ").replace("!", " not ").split())
models = re.findall(r'\{"([^"\n]+\.mesh)",\s*([-.\d]+)f,\s*([-.\d]+)f,\s*([-.\d]+)f,\s*([-.\d]+)f,\s*([-.\d]+)f\}',
                    read("source/gamemap/RoomObjectBounds.h"))
assert len(models) >= 30
walking_table = read("source/gamemap/RoomObjectBounds.h").split("walkingRadii[] = {", 1)[1].split("};", 1)[0]
assert len(models) == walking_table.count('{"'), "Every measured walking body must be tested"


# Execute the production axis test with the sum of two measured, scaled body extents.
def overlaps(point, other, own, peer, own_angle=0., peer_angle=0.):
    relative = (point[0]-other[0], point[1]-other[1])
    angle = own_angle-peer_angle
    corners = [(math.cos(angle)*x-math.sin(angle)*y, math.sin(angle)*x+math.cos(angle)*y)
               for x, y in itertools.product((own[0], own[2]), (own[1], own[3]))]
    inverse = [(math.cos(angle)*x+math.sin(angle)*y, -math.sin(angle)*x+math.cos(angle)*y)
               for x, y in itertools.product((peer[0], peer[2]), (peer[1], peer[3]))]
    bounds = NS(minimum=NS(x=peer[0]-max(p[0] for p in corners), y=peer[1]-max(p[1] for p in corners)),
                maximum=NS(x=peer[2]-min(p[0] for p in corners), y=peer[3]-min(p[1] for p in corners)),
                hasBodyAxes=True,
                bodyAxisMinimum=NS(x=min(p[0] for p in inverse)-own[2], y=min(p[1] for p in inverse)-own[3]),
                bodyAxisMaximum=NS(x=max(p[0] for p in inverse)-own[0], y=max(p[1] for p in inverse)-own[1]))
    point_peer = NS(x=math.cos(peer_angle)*relative[0]+math.sin(peer_angle)*relative[1],
                    y=-math.sin(peer_angle)*relative[0]+math.cos(peer_angle)*relative[1])
    point_own = NS(x=math.cos(own_angle)*relative[0]+math.sin(own_angle)*relative[1],
                   y=-math.sin(own_angle)*relative[0]+math.cos(own_angle)*relative[1])
    separated = eval(expression, {"__builtins__": {}}, {"p": point_peer, "bounds": bounds})
    return not separated and eval(axes_expression, {"__builtins__": {}}, {"bodyPoint": point_own, "bounds": bounds})


# Use the production lattice and tangency expressions for axis-aligned placement fixtures.
def candidates(own, peers, adjacent, edges=True):
    result = [(0., 0.)]
    coordinate = re.search(r"Helper::round\(wanted.x\) \+ dx (.*?)\,", separate)[1]
    coordinate = re.sub(r"(\d)f\b", r"\1", coordinate)
    for dx, dy, x, y in itertools.product(range(-adjacent, adjacent+1), range(-adjacent, adjacent+1), range(8), range(8)):
        result.append((dx+eval("0"+coordinate, {"__builtins__": {}}, {"x": x}),
                       dy+eval("0"+coordinate, {"__builtins__": {}}, {"x": y})))
    if edges:
        assert "expanded.minimum.x - 0.00001f" in separate and "expanded.maximum.y + 0.00001f" in separate
        for position, peer in peers:
            low = (position[0]+peer[0]-own[2], position[1]+peer[1]-own[3])
            high = (position[0]+peer[2]-own[0], position[1]+peer[3]-own[1])
            result.extend(itertools.product((low[0]-.00001, max(low[0], min(0., high[0])), high[0]+.00001),
                                            (low[1]-.00001, max(low[1], min(0., high[1])), high[1]+.00001)))
    return sorted((p for p in result if abs(p[0]) < adjacent+.5 and abs(p[1]) < adjacent+.5),
                  key=lambda p: p[0]*p[0]+p[1]*p[1])


# Choose the nearest free candidate, or keep the original position only after exhausting free candidates.
def choose(own, peers, adjacent=0, edges=True):
    return next((p for p in candidates(own, peers, adjacent, edges)
                 if all(not overlaps(p, pos, own, peer) for pos, peer in peers)), None)


for left, right, level in itertools.product(models, models, (1, 30)):
    scale = 1.+.10*(level-1)/29.
    own = tuple(float(v)*scale for v in left[2:])
    peer = tuple(float(v)*scale for v in right[2:])
    distance = peer[2]-own[0]
    assert not overlaps((distance+1.e-8, 0.), (0., 0.), own, peer)
    assert overlaps((distance-1.e-8, 0.), (0., 0.), own, peer)
    for own_angle, peer_angle in ((0., math.pi/4), (math.pi/2, 0.), (math.pi/4, -math.pi/4)):
        assert overlaps((0., 0.), (0., 0.), own, peer, own_angle, peer_angle)
        assert not overlaps((10., 0.), (0., 0.), own, peer, own_angle, peer_angle)
square = (-.1, -.1, .1, .1)
# A real .02-wide center gap between bodies falls between every original .125 lattice point.
peers = [((-.19, 0.), square), ((.23, 0.), square)]
assert choose(square, peers, edges=False) is not None  # Other Y positions remain free in open floor.
gap = [p for p in candidates(square, peers, 0) if .01 < p[0] < .03 and abs(p[1]) < .001
       and all(not overlaps(p, pos, square, peer) for pos, peer in peers)]
assert gap, "Measured tangencies must find the sub-grid gap"
assert not any(.01 < p[0] < .03 for p in candidates(square, peers, 0, edges=False))
# Ten overlapping humanoid arrivals can occupy the surrounding open gathering floor without overlap.
humanoid = tuple(float(v) for v in next(m for m in models if m[0] == "Wizard.mesh")[2:])
placed = []
for index in range(10):
    point = choose(humanoid, placed, 1)
    assert point is not None
    assert all(not overlaps(point, pos, humanoid, peer) for pos, peer in placed)
    placed.append((point, humanoid))
assert choose(square, [((0., 0.), (-2., -2., 2., 2.))]) is None
assert choose(square, []) == (0., 0.)

# Execute the production crowded-candidate guard and preference reset over already legal combat tiles.
def attack_position(in_range, current_free, tiles):
    if in_range and current_free:
        return "current"
    result, best_score, free_position = ("current" if in_range else None), math.inf, False
    guard = re.search(r"if\((!freeTile && \(freePosition \|\| inRange\))\)", combat)[1]
    guard = guard.replace("!", " not ").replace("&&", " and ").replace("||", " or ")
    for name, score, free_tile in tiles:
        if eval(guard.strip(), {"__builtins__": {}},
                {"freeTile": free_tile, "freePosition": free_position, "inRange": in_range}):
            continue
        if free_tile and not free_position:
            best_score = math.inf
        if score < best_score:
            result, best_score, free_position = name, score, free_tile
    return result


assert attack_position(True, False, [("crowded", 0, False), ("free adjacent in range", 5, True)]) == "free adjacent in range"
assert attack_position(True, False, [("crowded", 0, False)]) == "current"
assert attack_position(True, True, [("free adjacent in range", 5, True)]) == "current"
assert attack_position(False, False, [("crowded", 0, False), ("free legal", 5, True), ("crowded", -1, False)]) == "free legal"


# Exercise the production ring bound/order over finite floor/room/reachability fixtures.
def spread(width, height, origin, own, peers, floor=None, room=None):
    floor = set(itertools.product(range(width), range(height))) if floor is None else floor
    reachable, pending = {origin}, [origin]
    while pending:
        x, y = pending.pop()
        for tile in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if tile in floor and tile not in reachable:
                reachable.add(tile)
                pending.append(tile)
    bounds = re.search(r"lastRing = std::max\(\{(.*?)\}\);", separate, re.S)[1]
    bounds = bounds.replace("map.getMapSizeX()", "width").replace("map.getMapSizeY()", "height")
    values = {"centerX": origin[0], "centerY": origin[1], "width": width, "height": height}
    last_ring = max(eval(value.strip(), {"__builtins__": {}}, values) for value in bounds.split(','))
    best, distance, visited, paths = None, math.inf, 0, 0
    for ring in range(last_ring+1):
        for dy, dx in itertools.product(range(-ring, ring+1), repeat=2):
            if max(abs(dx), abs(dy)) != ring:
                continue
            tile = (origin[0]+dx, origin[1]+dy)
            if tile not in floor or (room is not None and tile not in room):
                continue
            visited += 1
            shifted = [((pos[0]-tile[0], pos[1]-tile[1]), peer) for pos, peer in peers]
            point = choose(own, shifted)
            if point is None:
                continue
            paths += 1
            if tile not in reachable:
                continue
            point = (point[0]+tile[0], point[1]+tile[1])
            current = (point[0]-origin[0])**2+(point[1]-origin[1])**2
            if current < distance:
                best, distance = point, current
        if distance <= (ring+.5)**2:
            break
    return best, visited, paths


large = tuple(float(v) for v in next(m for m in models if m[0] == "LavaSpawn.mesh")[2:])
origin = (3, 3)
crowd = [((3.+x, 3.+y), large) for x, y in itertools.product(range(-1, 2), repeat=2)]
old_local = [((pos[0]-3, pos[1]-3), peer) for pos, peer in crowd]
assert choose(humanoid, old_local, 1) is None, "Reproduce the old premature 3x3 crowded fallback"
free, count, paths = spread(7, 7, origin, humanoid, crowd)
assert free is not None and max(abs(free[0]-3), abs(free[1]-3)) > 1.5 and count < 49 and paths > 0
full = [((float(x), float(y)), large) for x, y in itertools.product(range(7), repeat=2)]
assert spread(7, 7, origin, humanoid, full) == (None, 49, 0), "Full floor terminates without path searches for occupied tiles"
assert spread(7, 7, origin, humanoid, crowd, room={origin, (4, 3)})[0] is None
assert spread(7, 7, origin, humanoid, [(origin, large)], floor={origin, (6, 6)})[0] is None
# A remote assigned defence stand stays valid, a changed target invalidates it, and occupied stands are rechecked.
assert "std::vector<Ogre::Vector2> standing{position};" in heart
assert "if(!RoomObjectNavigation::separate(creature, standing))" in heart
hold = re.search(r"if\((myTile == action->mStandingTile.*?)\)\s*\{", heart, re.S)[1]
hold = hold.replace("action->mStandingTile", "assigned").replace("||", " or ").replace("&&", " and ")
hold = hold.replace("std::abs", "abs").replace("myTile->getX()", "x").replace("myTile->getY()", "y")
hold = hold.replace("targetTile->getX()", "target_x").replace("targetTile->getY()", "target_y")
hold = " ".join(hold.split())
values = {"myTile": (5, 3), "assigned": (5, 3), "x": 5, "y": 3, "target_x": 3, "target_y": 3, "abs": abs}
assert eval(hold, {"__builtins__": {}}, values)
values["assigned"] = None
assert not eval(hold, {"__builtins__": {}}, values)
print("Spacing: measured pair extents, 10-body gathering, sub-grid tangency, exhausted-space fallback and server/action contracts PASS")
