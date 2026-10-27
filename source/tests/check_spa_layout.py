"""Lava spa layout: the pure layout rules of source/rooms/RoomSpaLayout.h are compiled and run, the wiring of the room
(rim pieces, chair, springboard, walkability, kept places) is checked on the source text.

What is run (the real header, no copy)
  SpaLayout::poolTiles / hasSquareBlock   pool tiles and the 4x4 build rule on 3x3, 3x4, 4x3, 3x5 (refused, pool 1 / 2 / 2 / 3
                                          tiles, no 2x2 pool block), 4x4 (pool 4), 5x5 (9), 5x7 (15), 7x7 (25), an L shaped
                                          room and a room made of two blocks that touch
  SpaLayout::findFreeBlock                bath places by bed size (1x1, 1x2 in both orientations with the unrotated one first,
                                          2x2) in the order smaller y, then smaller x; taken tiles are skipped; a full pool
                                          has no place; a place that is taken stays taken when the pool grows
  SpaLayout::chairTile / springboardTile  the chair directly above the pool tile with the smallest y (then smallest x), the
                                          springboard directly below the pool tile with the largest y (then largest x), a
                                          room without a pool has neither
What is checked on the source text
  RoomSpa.cpp             one mud piece per pool tile, a rim piece on every side of a pool tile that borders a non-pool tile
                          turned to that side, the chair (180) and the springboard (0) on the rim, recomputation after the tiles
                          change, places of bathers are kept by a recomputation and released only by a lost tile
  RoomObjectBounds.h      a bounds row for each of the four meshes, the mud and the rim are walkable, the chair and the
                          springboard are not
  RoomObjectNavigation.cpp the pool and the rim are skipped as obstacles, the chair and the springboard are not

Calls (from the repository root):
  python source/tests/check_spa_layout.py

The probe needs the MSVC compiler on the path (run it in a Visual Studio developer shell, like the other probes)."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]


# Returns the text of a repository file.
def read(path):
    return (root / path).read_text(encoding='utf-8')


# Returns the text of a function from its first line up to its closing brace (a brace in column 0).
def extract(text, header):
    start = text.index(header)
    end = text.index('\n}\n', start) + 2
    return text[start:end]


room_cpp = read('source/rooms/RoomSpa.cpp')
bounds_h = read('source/gamemap/RoomObjectBounds.h')
navigation_cpp = read('source/gamemap/RoomObjectNavigation.cpp')
layout_h = read('source/rooms/RoomSpaLayout.h')
assert 'class Tile' not in layout_h and '#include "' not in layout_h, 'the layout rules stay free of the map classes'

# ---- Source wiring -----------------------------------------------------------------------------------------------
update = extract(room_cpp, 'void RoomSpa::updateActiveSpots(')
assert 'SpaLayout::chairTile(pool, chair)' in update and 'SpaLayout::springboardTile(pool, springboard)' in update
assert 'wantedMesh = SPA_POOL_MESH;' in update, 'every pool tile gets a mud piece'
assert 'wantedMesh = SPA_CHAIR_MESH;\n            angle = CHAIR_ANGLE;' in update
assert 'wantedMesh = SPA_SPRINGBOARD_MESH;\n            angle = SPRINGBOARD_ANGLE;' in update
assert 'updateRimObjects(pool, gameMap);' in update and 'placeAttendant();' in update
assert re.search(r'const double CHAIR_ANGLE = 180\.0;', room_cpp) and re.search(r'const double SPRINGBOARD_ANGLE = 0\.0;', room_cpp)
rim = extract(room_cpp, 'void RoomSpa::updateRimObjects(')
assert 'pool.find(std::make_pair(it->first + SIDE_DX[i], it->second + SIDE_DY[i])) == pool.end()' in rim, \
    'a rim piece stands on every side of a pool tile that borders a non-pool tile'
assert 'SIDE_DX[] = { 0, -1, 0, 1 }' in rim and 'SIDE_DY[] = { 1, 0, -1, 0 }' in rim and 'NB_SIDES = 4' in rim
# The angles: the side +y 0, -x 90, -y 180, +x 270 (the engine turns counter-clockwise, like the tavern)
for name, value in (('TOP', '0.0'), ('LEFT', '90.0'), ('BOTTOM', '180.0'), ('RIGHT', '270.0')):
    assert re.search(r'const double OBJECT_ANGLE_SIDE_' + name + r' = ' + re.escape(value) + ';', room_cpp), name
# A recomputation runs after the tiles change and never moves a place: the places are stored in the bathers, only a lost
# tile releases them
for function in ('void RoomSpa::setupRoom(', 'void RoomSpa::absorbRoom(', 'bool RoomSpa::removeCoveredTile('):
    body = extract(room_cpp, function)
    assert 'mBathers.clear' not in body and 'mBlock =' not in body, function + ' must not move a place'
assert 'updateActiveSpots' in read('source/rooms/Room.cpp'), 'the base room calls the recomputation after tile changes'
for token in ('mBlock.mX = ', 'mBlock = block', 'mBlock = '):
    assert room_cpp.count(token) <= 2, 'a place is set once when it is reserved: ' + token
lost = extract(room_cpp, 'void RoomSpa::releaseBathersOnLostTiles(')
assert 'getCoveredTileAt(' in lost and 'clearActionQueue()' in lost, 'a removed tile under a place ends that bath'

# Bounds rows and walkability
for mesh in ('SpaChair', 'SpaMudPool', 'SpaPoolRim', 'SpaSpringboard'):
    assert re.search(r'\{"' + mesh + r'", ', bounds_h), mesh + ' has no meshBounds row'
walk = extract(bounds_h[bounds_h.index('inline bool isWalkableSpaMesh'):] + '\n}\n', 'inline bool isWalkableSpaMesh')
assert 'SPA_POOL_MESH' in walk and 'SPA_RIM_MESH' in walk and 'SpaChair' not in walk and 'SpringBoard' not in walk
assert 'SpaChair' not in bounds_h[bounds_h.index('static const std::string SPA_POOL_MESH'):bounds_h.index('inline bool isWalkableSpaMesh')]
collect = extract(navigation_cpp, 'std::vector<RoomObjectPath::Obstacle> RoomObjectNavigation::collect(')
assert 'RoomObjectPath::isWalkableSpaMesh(object->getMeshName())' in collect and 'SpaChair' not in collect and 'SpaSpringboard' not in collect
assert 'object->getMeshName() == "PortalObject"' in collect, 'the portal stays walkable as before'

# ---- Probe -------------------------------------------------------------------------------------------------------
probe = r'''
#include "RoomSpaLayout.h"
#include <iostream>
#include <string>
#include <vector>

static int failures = 0;
static void expect(bool ok, const std::string& what) { if(!ok) { ++failures; std::cout << "FAIL: " << what << std::endl; } }

static SpaTileSet rect(int x0, int y0, int w, int h)
{
    SpaTileSet s;
    for(int x = x0; x < x0 + w; ++x) for(int y = y0; y < y0 + h; ++y) s.insert(std::make_pair(x, y));
    return s;
}

static SpaTileSet blockTiles(const SpaBlock& b) { return rect(b.mX, b.mY, b.mWidth, b.mHeight); }

static void addAll(SpaTileSet& to, const SpaTileSet& from) { to.insert(from.begin(), from.end()); }

// Pool size and build rule for the sizes of the design
static void checkPoolAndRule()
{
    struct Row { int w, h, pool; bool allowed; };
    static const Row rows[] = { {3, 3, 1, false}, {3, 4, 2, false}, {4, 3, 2, false}, {3, 5, 3, false}, {4, 4, 4, true},
                                {5, 5, 9, true}, {5, 7, 15, true}, {7, 7, 25, true}, {2, 2, 0, false}, {1, 1, 0, false} };
    for(const Row& r : rows)
    {
        SpaTileSet pool = SpaLayout::poolTiles(rect(10, 20, r.w, r.h));
        expect(static_cast<int>(pool.size()) == r.pool, std::to_string(r.w) + "x" + std::to_string(r.h) + " pool size");
        // The build rule asks for a full 4x4 block of covered tiles; the pool of an allowed room holds a 2x2 block
        expect(SpaLayout::hasSquareBlock(rect(10, 20, r.w, r.h), 4) == r.allowed, std::to_string(r.w) + "x" + std::to_string(r.h) + " build rule");
        expect(SpaLayout::hasSquareBlock(pool, 2) == r.allowed, std::to_string(r.w) + "x" + std::to_string(r.h) + " 2x2 pool block");
    }
    // The pool never reaches the outer ring of the room
    SpaTileSet five = rect(0, 0, 5, 5);
    SpaTileSet pool = SpaLayout::poolTiles(five);
    for(SpaTileSet::const_iterator it = pool.begin(); it != pool.end(); ++it)
        expect(it->first >= 1 && it->first <= 3 && it->second >= 1 && it->second <= 3, "pool inside the ring");
    // An L shaped room of a 4x4 block and a 2 wide arm: the arm adds no pool tile that has an uncovered neighbour
    SpaTileSet l = rect(0, 0, 4, 4);
    addAll(l, rect(4, 0, 2, 2));
    expect(SpaLayout::hasSquareBlock(l, 4), "L shaped room holds the block");
    expect(SpaLayout::poolTiles(l).size() == 4, "L shaped room pool");
    // A room that is made of two separate blocks of 3x3 does not hold the block
    SpaTileSet two = rect(0, 0, 3, 3);
    addAll(two, rect(5, 0, 3, 3));
    expect(!SpaLayout::hasSquareBlock(two, 4), "two blocks");
    // Two 3x3 rooms that touch side by side make a 6x3 room, which is too small too
    expect(!SpaLayout::hasSquareBlock(rect(0, 0, 6, 3), 4), "6x3");
}

// Bath places by bed size in the order of the design
static void checkPlaces()
{
    SpaTileSet pool = SpaLayout::poolTiles(rect(0, 0, 5, 5));   // pool x 1..3, y 1..3
    SpaTileSet taken;
    SpaBlock b;
    expect(SpaLayout::findFreeBlock(pool, taken, 1, 1, b) && b.mX == 1 && b.mY == 1 && b.mWidth == 1 && b.mHeight == 1, "first 1x1");
    // The unrotated 1x2 first (width 1, height 2), the rotated one when the unrotated does not fit
    expect(SpaLayout::findFreeBlock(pool, taken, 1, 2, b) && b.mX == 1 && b.mY == 1 && b.mWidth == 1 && b.mHeight == 2, "first 1x2 unrotated");
    expect(SpaLayout::findFreeBlock(pool, taken, 2, 1, b) && b.mX == 1 && b.mY == 1 && b.mWidth == 2 && b.mHeight == 1, "first 2x1");
    expect(SpaLayout::findFreeBlock(pool, taken, 2, 2, b) && b.mX == 1 && b.mY == 1 && b.mWidth == 2 && b.mHeight == 2, "first 2x2");
    // Taking tiles moves the next place: a 2x2 at (1,1) leaves (3,1) first for a 1x1
    taken = blockTiles(b);
    expect(SpaLayout::findFreeBlock(pool, taken, 1, 1, b) && b.mX == 3 && b.mY == 1, "1x1 after a 2x2 (smaller y, then smaller x)");
    // Row y 1 is x 1..3: take (1,1),(2,1) and the unrotated 1x2 at x 3 is the first, the rotated one never goes before it
    taken.clear(); taken.insert(std::make_pair(1, 1)); taken.insert(std::make_pair(2, 1));
    expect(SpaLayout::findFreeBlock(pool, taken, 1, 2, b) && b.mX == 3 && b.mY == 1 && b.mWidth == 1 && b.mHeight == 2, "1x2 skips taken tiles");
    // A 1x2 bed that only fits rotated: only the horizontal pair (2,3),(3,3) remains free in a pool of one row
    SpaTileSet row = rect(5, 5, 2, 1);
    expect(SpaLayout::findFreeBlock(row, SpaTileSet(), 1, 2, b) && b.mWidth == 2 && b.mHeight == 1, "1x2 rotated when the unrotated does not fit");
    // A 2x2 needs a free 2x2 block: fill the middle and the bodies do not fit any more
    SpaTileSet middle; middle.insert(std::make_pair(2, 2));
    expect(!SpaLayout::findFreeBlock(pool, middle, 2, 2, b), "2x2 blocked by the middle tile of a 3x3 pool");
    // A full pool has no place
    expect(!SpaLayout::findFreeBlock(pool, pool, 1, 1, b), "full pool");
    expect(!SpaLayout::findFreeBlock(SpaTileSet(), SpaTileSet(), 1, 1, b), "no pool");
    // An occupied place is kept when the room grows: the taken tiles stay, the new pool tiles are free
    SpaTileSet big = SpaLayout::poolTiles(rect(0, 0, 7, 7));
    SpaTileSet kept = blockTiles(SpaBlock());
    SpaBlock mine; mine.mX = 3; mine.mY = 3; mine.mWidth = 2; mine.mHeight = 2;
    SpaTileSet mineTiles = blockTiles(mine);
    SpaBlock next;
    expect(SpaLayout::findFreeBlock(big, mineTiles, 2, 2, next), "place after growing");
    SpaTileSet nextTiles = blockTiles(next);
    for(SpaTileSet::const_iterator it = nextTiles.begin(); it != nextTiles.end(); ++it)
        expect(mineTiles.find(*it) == mineTiles.end(), "the next place does not overlap the kept place");
    // A taken tile that is not pool any more (the room shrank) does not make a block free
    SpaTileSet shrunk = SpaLayout::poolTiles(rect(0, 0, 4, 4));
    expect(!SpaLayout::isBlockFree(shrunk, SpaTileSet(), mine), "a block outside the pool is not free");
    (void)kept;
}

// Chair above and springboard below the pool
static void checkFurniture()
{
    std::pair<int, int> t;
    SpaTileSet pool = SpaLayout::poolTiles(rect(10, 20, 5, 5));   // pool x 11..13, y 21..23
    expect(SpaLayout::chairTile(pool, t) && t.first == 11 && t.second == 20, "chair above the first pool tile");
    expect(SpaLayout::springboardTile(pool, t) && t.first == 13 && t.second == 24, "springboard below the last pool tile");
    // The chair tile and the springboard tile are rim tiles of the room (covered, not pool)
    SpaTileSet covered = rect(10, 20, 5, 5);
    SpaLayout::chairTile(pool, t);
    expect(covered.count(t) == 1 && pool.count(t) == 0, "chair on the rim");
    SpaLayout::springboardTile(pool, t);
    expect(covered.count(t) == 1 && pool.count(t) == 0, "springboard on the rim");
    // Smallest y first, then smallest x; largest y first, then largest x
    SpaTileSet odd;
    odd.insert(std::make_pair(5, 9)); odd.insert(std::make_pair(3, 9)); odd.insert(std::make_pair(8, 4)); odd.insert(std::make_pair(2, 4));
    odd.insert(std::make_pair(7, 12)); odd.insert(std::make_pair(9, 12));
    expect(SpaLayout::chairTile(odd, t) && t.first == 2 && t.second == 3, "chair order");
    expect(SpaLayout::springboardTile(odd, t) && t.first == 9 && t.second == 13, "springboard order");
    expect(!SpaLayout::chairTile(SpaTileSet(), t) && !SpaLayout::springboardTile(SpaTileSet(), t), "no pool, no furniture");
    // A 4x4 room: pool 2x2 at (1,1), chair at (1,0), springboard at (2,3)
    SpaTileSet small = SpaLayout::poolTiles(rect(0, 0, 4, 4));
    expect(SpaLayout::chairTile(small, t) && t.first == 1 && t.second == 0, "4x4 chair");
    expect(SpaLayout::springboardTile(small, t) && t.first == 2 && t.second == 3, "4x4 springboard");
}

int main()
{
    checkPoolAndRule();
    checkPlaces();
    checkFurniture();
    if(failures == 0) std::cout << "spa layout ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

with tempfile.TemporaryDirectory(prefix='odp-spa-layout-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', '/I' + str(root / 'source' / 'rooms'),
                    'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('spa layout ok')
