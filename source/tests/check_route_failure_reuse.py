"""Checks without compiling that a failed furniture route search is not run again where it is proven to fail.

Cause (slow server turns right after loading the save 2026-11-04_204357-SK-Brackenford.level with build 0.7.4.30,
turns 999 to 1016: 0.5 to 1.0 s upkeep instead of below 0.1 s): the walls north of Dormitory_4 are marked for
digging, and their dig places lie in a small pocket that is reached only through the dormitory entry next to the
bed of Goblin3. Every turn, refreshWorkerTargets (collectDig) and the dig search of each worker test every dig place
(Creature::wallDigPath -> RoomObjectNavigation::refine). With the bed solid, refine runs RoomObjectPath::route on
the area around the path and then on the wider area, each with nine grid offsets, and all eighteen searches fail
before the route over the bed (the low step) is found. This repeats for every dig place, slot and worker.

The fix keeps every answer the same:
  1. RoomObjectPath.h: when a search fails because one of its two sides ran out of nodes and no free edge left its
     area (a closed side), routeToAny() records that side (ClosedSearchSide in RouteFailures). The node set of a
     closed side does not depend on the area, so a later search of the same creature with the same start, grid
     offset and start nodes is not run when the side proves that it fails: a goal side that holds all first nodes of
     the goal, or a start side that holds none of them. Sides are recorded only without a cost limit.
  2. RoomObjectNavigation: refine() gives the failures to both route() calls, so the wider search is skipped when
     the first one failed closed. RouteCache keeps them per creature and interaction object for refine() calls in
     one unchanged game state: collectDig keeps one per worker for a refresh, the dig search one for its loop.
  3. A model of the two-sided search in this file checks the rule on random grids: a search the recorded sides
     declare failed has no route, and the recorded sides never change the answer of a search.

Usage: python -I source/tests/check_route_failure_reuse.py [--source-ref <git ref>]
Exit 0 only if every rule holds. With --source-ref the files are read from that commit.
"""
import argparse
import random
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PATH_HEADER = 'source/gamemap/RoomObjectPath.h'
NAVIGATION = 'source/gamemap/RoomObjectNavigation.cpp'
NAVIGATION_HEADER = 'source/gamemap/RoomObjectNavigation.h'
CREATURE = 'source/entities/Creature.cpp'
TILE = 'source/entities/Tile.cpp'
TARGETS = 'source/game/WorkerTargets.cpp'
DIG_SEARCH = 'source/creatureaction/CreatureActionSearchTileToDig.cpp'
# Random grids of the model: count, size and share of blocked edges
MODEL_GRIDS = 120
MODEL_SIZE = 14
MODEL_QUERIES = 30


def read(relative, ref):
    """Returns the text of a repository file, from the work tree or from the given commit."""
    if ref:
        return subprocess.check_output(['git', 'show', ref + ':' + relative], cwd=REPO, text=True,
                                       encoding='utf-8', errors='replace')
    return (REPO / relative).read_text(encoding='utf-8', errors='replace')


def body(text, signature):
    """Returns the text of the function or type that starts with signature, up to its closing brace; '' if missing."""
    start = text.find(signature)
    if start < 0:
        return ''
    opening = text.find('{', start)
    if opening < 0:
        return ''
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == '{':
            depth += 1
        elif text[index] == '}':
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return ''


def source_rules(ref):
    """Returns the broken source rules of the fix."""
    header = read(PATH_HEADER, ref)
    navigation = read(NAVIGATION, ref)
    navigation_header = read(NAVIGATION_HEADER, ref)
    creature = read(CREATURE, ref)
    tile = read(TILE, ref)
    targets = read(TARGETS, ref)
    dig_search = read(DIG_SEARCH, ref)
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    # 1. The search records closed sides and skips searches they prove to fail
    side = body(header, 'struct ClosedSearchSide')
    require(side != '' and 'std::unordered_set<int64_t> nodes;' in side and 'bool goalSide;' in side,
            PATH_HEADER + ': struct ClosedSearchSide (nodes of a closed side of a failed search) is missing')
    require('int seedGridFirstX, seedGridLastX, seedGridFirstY, seedGridLastY;' in side,
            PATH_HEADER + ': a closed side must keep the first nodes its search tried for the start')
    require('std::vector<ClosedSearchSide> sides;' in body(header, 'struct RouteFailures'),
            PATH_HEADER + ': struct RouteFailures is missing')
    route = body(header, 'inline bool routeToAny(')
    require('RouteFailures* failures = nullptr)' in route,
            PATH_HEADER + ': routeToAny() must take the failed searches')
    require('const bool rememberFailure = useFailures && !std::isfinite(maximumCost);' in route,
            PATH_HEADER + ': routeToAny() may record failures only without a cost limit')
    require('if((side.goalSide && !outside) || (!side.goalSide && !inside))\n                return false;' in route,
            PATH_HEADER + ': routeToAny() must skip a search that a goal side or a start side proves to fail')
    require('seedGridFirstX < side.seedGridFirstX || seedGridLastX > side.seedGridLastX ||' in route and
            'seedGridFirstY < side.seedGridFirstY || seedGridLastY > side.seedGridLastY)' in route,
            PATH_HEADER + ': a side may only be used when the search tries no other first nodes of the start')
    require('side.start != start || side.gridOffset != gridOffset || side.allowStartExit != allowStartExit' in route,
            PATH_HEADER + ': a side may only be used for the same start, grid offset and start exit')
    require('bool startClosed = seedFirstX >= 0 && seedLastX <= width - 1 && seedFirstY >= 0 && seedLastY <= height - 1;'
            in route, PATH_HEADER + ': a start side is closed only if all its first nodes are inside the area')
    border = route[route.find('if(x + dx < 0 || x + dx >= width || y + dy < 0 || y + dy >= height)'):]
    require(re.search(r'for\(const Obstacle& obstacle : edgeObstacles\[heading\]\)\s*if\(obstacle\.intersects\(from, to\)\)',
                      border) is not None and 'if(free && terrain(from, to))\n                            closed = false;'
            in border, PATH_HEADER + ': a free edge out of the area must open the side of the search')
    require('const bool goalSide = open.empty() && goalClosed;' in route and
            'if(rememberFailure && (goalSide || (forwardOpen.empty() && startClosed)))' in route,
            PATH_HEADER + ': only a side that ran out of nodes and stayed closed may be recorded')
    aligned = body(header, 'inline bool routeToAnyAligned(')
    require(aligned.count('failures);') == 1 and 'offset, bestCost, failures))' in aligned,
            PATH_HEADER + ': routeToAnyAligned() must give the failures to all its searches')
    require('terrain, result, chosenGoal, allowStartExit, failures);' in body(header, 'inline bool route('),
            PATH_HEADER + ': route() must give the failures to routeToAnyAligned()')

    # 2. refine() and the dig place tests share the failures
    require('class RouteCache' in navigation_header and
            'bool refine(Creature& creature, std::vector<Ogre::Vector2>& path, RouteCache& cache);' in navigation_header,
            NAVIGATION_HEADER + ': RouteCache and refine() with a cache are missing')
    refine = body(navigation, 'bool RoomObjectNavigation::refine(Creature& creature, std::vector<Ogre::Vector2>& path, RouteCache& cache)')
    require('RoomObjectPath::RouteFailures& furnitureFailures = cache.failures(creature, interaction);' in refine,
            NAVIGATION + ': refine() must use the failures of the cache for the furniture without its interaction object')
    require(refine.count('terrain, route, true, &failures)') == 2,
            NAVIGATION + ': both route searches of refine() must use the failures')
    require('findRoute(obstacles, result, furnitureFailures)' in refine and
            'findRoute(solid, crossing, stepFailures)' in refine,
            NAVIGATION + ': the searches without low steps need their own failures')
    plain = body(navigation, 'bool RoomObjectNavigation::refine(Creature& creature, std::vector<Ogre::Vector2>& path)\n')
    require('RouteCache cache;' in plain and 'return refine(creature, path, cache);' in plain,
            NAVIGATION + ': refine() without a cache must keep the failures of its own call')
    cache = body(navigation, 'RoomObjectPath::RouteFailures& RoomObjectNavigation::RouteCache::failures(')
    require('if(mCreature != &creature)' in cache and 'mFailures.clear();' in cache,
            NAVIGATION + ': a RouteCache must forget the failures of another creature')
    dig = creature[creature.find('bool Creature::wallDigPath('):creature.find('bool Creature::parkToWallTile(')]
    require('RoomObjectNavigation::RouteCache* routeCache)' in dig and
            'RoomObjectNavigation::refine(*this, path, *routeCache);' in dig,
            CREATURE + ': wallDigPath() must give its cache to refine()')
    require('worker.wallDigPath(this, neigh, slot, path, routeCache)' in body(tile, 'void Tile::canWorkerDig('),
            TILE + ': canWorkerDig() must give its cache to wallDigPath()')
    require('std::map<const Creature*, RoomObjectNavigation::RouteCache> routeCaches;' in body(targets, 'void refreshWorkerTargets(')
            and 'collectDig(targets, seat, *tile, workers, routeCaches);' in targets and
            'worker->wallDigPath(&tile, standing, slot, path, &routeCaches[worker])' in targets,
            TARGETS + ': refreshWorkerTargets() must keep one cache per worker for all dig places')
    require('RoomObjectNavigation::RouteCache routeCache;' in dig_search and
            'tile->canWorkerDig(creature, positions, &routeCache);' in dig_search,
            DIG_SEARCH + ': the dig search must keep one cache for all its dig places')
    return failures


class ModelGrid:
    """Directed grid graph: an edge may be free in one direction only, as edges of the search depend on the heading."""

    def __init__(self, rng):
        self.blocked = {(x, y) for x in range(-2, MODEL_SIZE + 2) for y in range(-2, MODEL_SIZE + 2)
                        if rng.random() < 0.42}
        self.closed_edges = set()
        for x in range(-2, MODEL_SIZE + 2):
            for y in range(-2, MODEL_SIZE + 2):
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if (dx or dy) and rng.random() < 0.12:
                            self.closed_edges.add(((x, y), (x + dx, y + dy)))
        self.seed_free = {node for node in self.nodes() if rng.random() < 0.8}

    @staticmethod
    def nodes():
        return [(x, y) for x in range(-2, MODEL_SIZE + 2) for y in range(-2, MODEL_SIZE + 2)]

    def free(self, a, b):
        """The edge test of the search: the same for a pair of nodes in every area."""
        inside = all(-2 <= c < MODEL_SIZE + 2 for c in a + b)
        return inside and a not in self.blocked and b not in self.blocked and (a, b) not in self.closed_edges


def neighbours(node):
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                yield (node[0] + dx, node[1] + dy)


def model_search(grid, area, seed_rect, goal_rect, failures):
    """Mirrors routeToAny(): returns (found, skipped). failures is the list of recorded closed sides."""
    x0, y0, x1, y1 = area

    def in_area(node):
        return x0 <= node[0] <= x1 and y0 <= node[1] <= y1

    def rect_nodes(rect):
        return [(x, y) for x in range(max(rect[0], x0), min(rect[2], x1) + 1)
                for y in range(max(rect[1], y0), min(rect[3], y1) + 1)]

    goal_nodes = [node for node in rect_nodes(goal_rect) if node in grid.seed_free]
    for side in failures:
        if not (seed_rect[0] >= side['seed'][0] and seed_rect[2] <= side['seed'][2] and
                seed_rect[1] >= side['seed'][1] and seed_rect[3] <= side['seed'][3]):
            continue
        inside = any(node in side['nodes'] for node in goal_nodes)
        outside = any(node not in side['nodes'] for node in goal_nodes)
        if (side['goal'] and not outside) or (not side['goal'] and not inside):
            return False, True
    start_nodes = [node for node in rect_nodes(seed_rect) if node in grid.seed_free]
    start_closed = seed_rect[0] >= x0 and seed_rect[2] <= x1 and seed_rect[1] >= y0 and seed_rect[3] <= y1
    goal_closed = True
    forward_seen, backward_seen = set(start_nodes), set(goal_nodes)
    if not forward_seen:
        return False, False
    if not backward_seen:
        return False, False
    if forward_seen & backward_seen:
        return True, False
    forward_open, backward_open = deque(start_nodes), deque(goal_nodes)
    forward = False
    while forward_open and backward_open:
        forward = not forward
        frontier, seen, other = ((forward_open, forward_seen, backward_seen) if forward else
                                 (backward_open, backward_seen, forward_seen))
        current = frontier.popleft()
        for target in neighbours(current):
            edge = (current, target) if forward else (target, current)
            if not in_area(target):
                if grid.free(*edge):
                    if forward:
                        start_closed = False
                    else:
                        goal_closed = False
                continue
            if target in seen or not grid.free(*edge):
                continue
            if target in other:
                return True, False
            seen.add(target)
            frontier.append(target)
    goal_side = not backward_open and goal_closed
    if goal_side or (not forward_open and start_closed):
        failures.append({'seed': seed_rect, 'goal': goal_side,
                         'nodes': set(backward_seen if goal_side else forward_seen)})
    return False, False


def model_truth(grid, area, seed_rect, goal_rect):
    """Plain reachability inside the area from the first nodes of the start to those of the goal."""
    x0, y0, x1, y1 = area

    def rect_nodes(rect):
        return [(x, y) for x in range(max(rect[0], x0), min(rect[2], x1) + 1)
                for y in range(max(rect[1], y0), min(rect[3], y1) + 1)]

    goals = {node for node in rect_nodes(goal_rect) if node in grid.seed_free}
    seen = {node for node in rect_nodes(seed_rect) if node in grid.seed_free}
    queue = deque(seen)
    while queue:
        current = queue.popleft()
        if current in goals:
            return True
        for target in neighbours(current):
            if x0 <= target[0] <= x1 and y0 <= target[1] <= y1 and target not in seen and grid.free(current, target):
                seen.add(target)
                queue.append(target)
    return False


def model_rules():
    """Runs the model on random grids; returns the broken rules and the number of skipped searches."""
    rng = random.Random(20261105)
    failures = []
    skipped = 0
    for _ in range(MODEL_GRIDS):
        grid = ModelGrid(rng)
        # One creature: the same start and first start nodes for all searches of the grid, as in one RouteCache
        sx, sy = rng.randrange(MODEL_SIZE), rng.randrange(MODEL_SIZE)
        seed_rect = (sx - 1, sy - 1, sx + 1, sy + 1)
        recorded = []
        for _ in range(MODEL_QUERIES):
            # The rounding of the area corner may move a border of the first start nodes by one node
            if rng.random() < 0.3:
                grow = rng.randrange(4)
                seed_rect = tuple(value - (index == grow) if index < 2 else value + (index == grow)
                                  for index, value in enumerate((sx - 1, sy - 1, sx + 1, sy + 1)))
            else:
                seed_rect = (sx - 1, sy - 1, sx + 1, sy + 1)
            gx, gy = rng.randrange(MODEL_SIZE), rng.randrange(MODEL_SIZE)
            goal_rect = (gx - 1, gy - 1, gx + 1, gy + 1)
            # The narrow area around start and goal, then the wider one, as refine() searches them
            narrow = (min(sx, gx) - 2, min(sy, gy) - 2, max(sx, gx) + 2, max(sy, gy) + 2)
            wide = (narrow[0] - 3, narrow[1] - 3, narrow[2] + 3, narrow[3] + 3)
            for area in (narrow, wide):
                truth = model_truth(grid, area, seed_rect, goal_rect)
                fresh, _ = model_search(grid, area, seed_rect, goal_rect, [])
                reused, skip = model_search(grid, area, seed_rect, goal_rect, recorded)
                skipped += skip
                if fresh != truth:
                    failures.append('model: the two-sided search answers %s, the route exists: %s' % (fresh, truth))
                if reused != truth:
                    failures.append('model: with recorded sides the search answers %s, the route exists: %s'
                                    % (reused, truth))
                    return failures, skipped
    if skipped == 0:
        failures.append('model: no search was skipped, the recorded sides are never used')
    return failures, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source-ref', help='read the sources from this git commit instead of the work tree')
    args = parser.parse_args()
    failures = source_rules(args.source_ref)
    model_failures, skipped = model_rules()
    failures += model_failures
    for failure in failures:
        print('FAIL ' + failure)
    if failures:
        print('check_route_failure_reuse: %d rule(s) broken' % len(failures))
        return 1
    print('check_route_failure_reuse: closed sides of failed searches recorded and reused, refine() and the dig '
          'place tests share them, model: %d searches skipped without a changed answer: ok' % skipped)
    return 0


if __name__ == '__main__':
    sys.exit(main())
