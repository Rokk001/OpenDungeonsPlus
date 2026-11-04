"""Checks without compiling that the furniture route search keeps its cost per tested step small.

Cause (turn stall of build 0.7.4.27, Skirmish Brackenford, turns 973 to 1012): a bed placed at the entry of a
dormitory closed the gap between a dig area and the dungeon heart for the quarter-tile furniture route search.
Every worker route and dig place check across that room then ran many grid searches
(RoomObjectNavigation::refine -> RoomObjectPath::routeToAny), and each tested grid step asked the creature for
every sampled tile (Creature::canGoThroughTile) and tested every obstacle near the path. The server turn took
1.8 to 4.1 seconds instead of 0.2 to 0.6.

The fix keeps every answer the same and makes each tested step cheap:
  1. RoomObjectNavigation.cpp: terrainClear() reads the passable tiles from PassableTiles, which asks each tile
     once per search. refine(), foodApproach() and workApproach() create one PassableTiles each (3 in total),
     and no terrain test asks the creature directly any more.
  2. RoomObjectPath.h: routeToAny() lists the obstacles per grid cell and tests an edge only against the
     obstacles listed for its cell (clearListedSegment), plus the obstacles without world bounds.

Usage: python -I source/tests/check_furniture_route_cost.py [--source-ref <git ref>]
Exit 0 only if every rule holds. With --source-ref the files are read from that commit.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NAVIGATION = 'source/gamemap/RoomObjectNavigation.cpp'
PATH_HEADER = 'source/gamemap/RoomObjectPath.h'
# Functions of RoomObjectNavigation.cpp that run terrain tests and each create one PassableTiles
SEARCH_FUNCTIONS = ('bool RoomObjectNavigation::refine(', 'bool RoomObjectNavigation::foodApproach(',
                    'bool RoomObjectNavigation::workApproach(')
# Number of PassableTiles objects in RoomObjectNavigation.cpp (one per function above)
EXPECTED_PASSABLE_TILES = 3


def read(relative, ref):
    """Returns the text of a repository file, from the work tree or from the given commit."""
    if ref:
        return subprocess.check_output(['git', 'show', ref + ':' + relative], cwd=REPO, text=True,
                                       encoding='utf-8', errors='replace')
    return (REPO / relative).read_text(encoding='utf-8', errors='replace')


def body(text, signature):
    """Returns the text of the function that starts with signature, up to its closing brace; '' if missing."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--source-ref', help='read the sources from this git commit instead of the work tree')
    args = parser.parse_args()
    navigation = read(NAVIGATION, args.source_ref)
    header = read(PATH_HEADER, args.source_ref)
    failures = []

    def require(condition, message):
        if not condition:
            failures.append(message)

    # 1. Terrain answers are remembered for one search
    passable_class = body(navigation, 'class PassableTiles')
    require(passable_class != '', NAVIGATION + ': class PassableTiles (terrain answers of one search) is missing')
    require('canGoThroughTile(tile)' in body(passable_class, 'bool askTile('),
            NAVIGATION + ': PassableTiles::askTile() must ask Creature::canGoThroughTile once per tile')
    is_passable = body(passable_class, 'bool isPassable(')
    require(re.search(r'if\(answer == TILE_NOT_ASKED\)\s*answer = askTile\(x, y\)', is_passable) is not None,
            NAVIGATION + ': PassableTiles::isPassable() must remember the answer of a tile it asked')
    terrain = body(navigation, 'bool terrainClear(')
    require(terrain.startswith('bool terrainClear(PassableTiles& passable,'),
            NAVIGATION + ': terrainClear() must read the terrain from PassableTiles')
    require(terrain != '' and 'canGoThroughTile' not in terrain and 'getTile(' not in terrain,
            NAVIGATION + ': terrainClear() must not ask the map or the creature for every sampled tile')
    require('terrainClear(creature,' not in navigation,
            NAVIGATION + ': a terrain test still asks the creature for every sampled tile')
    count = len(re.findall(r'\bPassableTiles passable\(creature\);', navigation))
    require(count == EXPECTED_PASSABLE_TILES,
            NAVIGATION + ': expected %d PassableTiles objects, found %d' % (EXPECTED_PASSABLE_TILES, count))
    for signature in SEARCH_FUNCTIONS:
        function = body(navigation, signature)
        require(function.count('PassableTiles passable(creature);') == 1,
                NAVIGATION + ': ' + signature + ' must create one PassableTiles for all its terrain tests')
    refine = body(navigation, 'bool RoomObjectNavigation::refine(')
    require('{ return terrainClear(passable, from, to); };' in refine,
            NAVIGATION + ': the route search terrain of refine() must use its PassableTiles')
    require(refine.count('smoothCorridor(creature, passable, obstacles,') == 2,
            NAVIGATION + ': both corridor smoothings of refine() must use its PassableTiles')

    # 2. An edge of the route search tests only the obstacles near it
    route = body(header, 'inline bool routeToAny(')
    require(route != '', PATH_HEADER + ': routeToAny() is missing')
    require('clearSegment(edgeObstacles[heading]' not in route,
            PATH_HEADER + ': routeToAny() still tests every obstacle for every edge')
    require('clearListedSegment(edgeObstacles[heading], unboundedObstacles, cellObstacles[cell], from, to)' in route,
            PATH_HEADER + ': routeToAny() must test an edge against the obstacles listed for its cell')
    require(re.search(r'if\(!edge\.hasWorldBounds\)\s*\{\s*bounded = false;', route) is not None and
            'unboundedObstacles.push_back(i);' in route,
            PATH_HEADER + ': an obstacle without world bounds must be tested for every edge')
    require('size_t(std::min(y, y + dy) / routeCellsPerTile) * size_t(cellsX) +' in route and
            'size_t(std::min(x, x + dx) / routeCellsPerTile);' in route,
            PATH_HEADER + ': an edge must use the cell of its lower node')
    margin = re.search(r'constexpr float routeCellListMargin = ([0-9.]+)f;', header)
    require(margin is not None and float(margin.group(1)) > 0.0,
            PATH_HEADER + ': the cell lists need a positive margin for the rounding of the node positions')
    listed = body(header, 'inline bool clearListedSegment(')
    require(listed.count('.intersects(from, to)') == 2,
            PATH_HEADER + ': clearListedSegment() must run the exact obstacle test on both lists')

    for failure in failures:
        print('FAIL ' + failure)
    if failures:
        print('check_furniture_route_cost: %d rule(s) broken' % len(failures))
        return 1
    print('check_furniture_route_cost: terrain answers per search, %d PassableTiles, edge obstacles per cell: ok'
          % EXPECTED_PASSABLE_TILES)
    return 0


if __name__ == '__main__':
    sys.exit(main())
