"""Pin the rule that a worker puts carried gold on the nearest own gold tile with room (treasury tiles and
heart ring tiles together) instead of one fixed tile of a room.

Without --probe only the source wiring is checked (nothing is compiled). With --probe the real
functions findNearestGoldTile, handleCarryGold, getOwnGoldSpace and the two getGoldSpaceInTile
functions are cut out of the sources and run against small stand-ins for the map, the rooms and the
worker, covering the acceptance cases that depend on the walking way and on the gold in the tiles."""
from pathlib import Path
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


carry = read('source/creatureaction/CreatureActionCarryEntity.cpp')
carry_header = read('source/creatureaction/CreatureActionCarryEntity.h')
grab = read('source/creatureaction/CreatureActionGrabEntity.cpp')
treasury = read('source/rooms/RoomTreasury.cpp')
temple = read('source/rooms/RoomDungeonTemple.cpp')
room_header = read('source/rooms/Room.h')

# Source wiring ---------------------------------------------------------------------------------------------
# The room reports the room left in one tile; treasury tiles use the research capacity, ring tiles the heart value.
assert 'virtual double getGoldSpaceInTile(Tile* tile) const' in room_header
get_space_treasury = function(treasury, 'double RoomTreasury::getGoldSpaceInTile(')
get_space_temple = function(temple, 'double RoomDungeonTemple::getGoldSpaceInTile(')
assert 'getGoldCapacityPerTile()' in get_space_treasury and 'mHP <= 0' in get_space_treasury
assert 'isTreasuryTile(tile)' in get_space_temple and 'DungeonHeartGoldPerTile' in get_space_temple
assert 'mHP <= 0' in get_space_temple
# A room accepts a gold pile as long as one of its tiles has room (not by its summed storage).
for body in (function(treasury, 'bool RoomTreasury::hasCarryEntitySpot('),
             function(temple, 'bool RoomDungeonTemple::hasCarryEntitySpot(')):
    assert 'getGoldSpaceInTile(tile) > 0.0' in body
    assert 'getTotalGoldStored() >= getTotalGoldStorage()' not in body
# Every gold delivery (carrying workers and the digger hauling its full pocket) is a grab that now picks the
# nearest gold tile and hands it to the carry action.
grab_body = function(grab, 'bool CreatureActionGrabEntity::handleGrabEntity(')
assert 'GameEntityType::treasuryObject' in grab_body
assert 'CreatureActionCarryEntity::findNearestGoldTile(creature, myTile)' in grab_body
assert 'forced, digGold, goldTile' in grab_body
assert 'CreatureActionGrabEntity>(creature, *obj, forced, true)' in read('source/creatureaction/CreatureActionDigTile.cpp')
# The carry action re-checks the target every time and puts gold down where the worker stands if nothing has room.
assert 'handleCarryGold' in function(carry, 'std::function<bool()> CreatureActionCarryEntity::action(')
assert 'Tile* goldTile = nullptr' in carry_header
# Unchanged storage: the arrival drops the gold on the tile, the covering room stores it as before.
assert 'depositGold(mGoldValue, tile)' in read('source/entities/TreasuryObject.cpp')
# Gold lying on a gold room tile that can absorb it is still not carried (hand drop, digger standing on the room).
assert 'getTotalGoldStorage() <= 0' in function(read('source/entities/TreasuryObject.cpp'),
                                                'EntityCarryType TreasuryObject::getEntityCarryType(')

if '--probe' not in sys.argv:
    print('Source checks passed; compiled probe requires --probe')
    raise SystemExit(0)

probe = r"""
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <list>
#include <map>
#include <queue>
#include <set>
#include <string>
#include <vector>

#define OD_LOG_ERR(x)

struct Seat {};
struct TileData { double mHP = 10.0; virtual ~TileData() = default; };
struct RoomTreasuryTileData : TileData { double mGoldInTile = 0; };
enum class RoomType { dungeonTemple, treasury };
struct GameEntityListener {};
struct Room;
struct Building;
//! \brief Map tile with its covering room.
struct Tile {
    int mX, mY; Room* room = nullptr;
    Tile(int x, int y) : mX(x), mY(y) {}
    int getX() const { return mX; }
    int getY() const { return mY; }
    Room* getCoveringRoom() const { return room; }
    Building* getCoveringBuilding() const;
};
//! \brief Room stand-in: owner, tiles and the per-tile gold space.
struct Building {
    int listeners = 0;
    void addGameEntityListener(GameEntityListener*) { ++listeners; }
    void removeGameEntityListener(GameEntityListener*) { --listeners; }
    virtual ~Building() = default;
};
struct Room : Building {
    Seat* seat; RoomType type; std::vector<Tile*> tiles; std::map<Tile*, TileData*> mTileData;
    Room(Seat* s, RoomType t) : seat(s), type(t) {}
    Seat* getSeat() const { return seat; }
    std::vector<Tile*> getCoveredTiles() { return tiles; }
    virtual double getGoldSpaceInTile(Tile*) const { return 0; }
    void add(Tile* t) { tiles.push_back(t); t->room = this; mTileData[t] = new RoomTreasuryTileData; }
    double& gold(Tile* t) { return static_cast<RoomTreasuryTileData*>(mTileData[t])->mGoldInTile; }
};
Building* Tile::getCoveringBuilding() const { return room; }
struct ConfigManager {
    static ConfigManager& getSingleton() { static ConfigManager c; return c; }
    double getRoomConfigDoubleOrDefault(const char*, double d) const { return d; }
};
struct RoomTreasury : Room {
    double research = 1.0;
    RoomTreasury(Seat* s) : Room(s, RoomType::treasury) {}
    int getGoldCapacityPerTile() const { return static_cast<int>(1000 * research); }
    double getGoldSpaceInTile(Tile* tile) const override;
};
__SPACE_TREASURY__
struct RoomDungeonTemple : Room {
    Tile* heart = nullptr;
    RoomDungeonTemple(Seat* s) : Room(s, RoomType::dungeonTemple) {}
    bool isTreasuryTile(Tile* t) const {
        return std::abs(t->mX - heart->mX) > 1 || std::abs(t->mY - heart->mY) > 1;
    }
    double getGoldSpaceInTile(Tile* tile) const override;
};
__SPACE_TEMPLE__

struct Creature;
//! \brief Walkable grid with an 8-neighbour way search.
struct GameMap {
    std::set<std::pair<int, int>> blocked; std::vector<Room*> rooms;
    std::list<Tile*> path(Tile* a, Tile* b, const Creature*, Seat*, bool);
    bool pathExists(const Creature* c, Tile* a, Tile* b) { return !path(a, b, c, nullptr, false).empty(); }
    std::vector<Room*> getRoomsByTypeAndSeat(RoomType type, const Seat* seat) {
        std::vector<Room*> out;
        for(Room* r : rooms) if(r->type == type && r->seat == seat) out.push_back(r);
        return out;
    }
    std::map<std::pair<int, int>, Tile*> grid;
};
struct Creature {
    GameMap* map; Seat* seat; Tile* pos; int pops = 0;
    GameMap* getGameMap() const { return map; }
    Seat* getSeat() const { return seat; }
    Tile* getPositionTile() const { return pos; }
    void popAction() { ++pops; }
};
std::list<Tile*> GameMap::path(Tile* a, Tile* b, const Creature*, Seat*, bool) {
    std::map<Tile*, Tile*> from; std::queue<Tile*> q; q.push(a); from[a] = a;
    while(!q.empty()) {
        Tile* t = q.front(); q.pop();
        if(t == b) break;
        for(int dx = -1; dx <= 1; ++dx) for(int dy = -1; dy <= 1; ++dy) {
            std::pair<int, int> p(t->mX + dx, t->mY + dy);
            std::map<std::pair<int, int>, Tile*>::iterator it = grid.find(p);
            if((dx == 0 && dy == 0) || it == grid.end() || blocked.count(p) || from.count(it->second)) continue;
            from[it->second] = t; q.push(it->second);
        }
    }
    std::list<Tile*> way;
    if(!from.count(b)) return way;
    for(Tile* t = b; ; t = from[t]) { way.push_front(t); if(t == a) break; }
    return way;
}
struct GameEntity {};
//! \brief Carry action stand-in around the extracted functions.
struct CreatureActionCarryEntity : GameEntityListener {
    Creature& mCreature; GameEntity* mEntityToCarry; Tile* mTileDest; Building* mBuildingDest; Tile* walkedTo = nullptr;
    CreatureActionCarryEntity(Creature& c, GameEntity* e, Tile* t, Building* b) : mCreature(c), mEntityToCarry(e), mTileDest(t), mBuildingDest(b) {}
    static Tile* findNearestGoldTile(Creature& creature, Tile* from);
    bool handleCarryGold();
    static bool handleCarryEntity(Creature&, GameEntity*, Tile*);
};
Tile* g_walkedTo = nullptr;
bool CreatureActionCarryEntity::handleCarryEntity(Creature&, GameEntity*, Tile* dest) { g_walkedTo = dest; return true; }
__OWN_SPACE__
__NEAREST__
__CARRY_GOLD__

int checks = 0, failures = 0;
void check(bool ok, const std::string& what) { ++checks; if(!ok) { ++failures; std::cout << "FAIL: " << what << '\n'; } }

//! \brief One test world: an open grid, one worker with the pile at (0,0).
struct World {
    Seat seat; Seat other; GameMap map; Creature worker; std::vector<Room*> owned;
    World() { for(int x = 0; x < 30; ++x) for(int y = 0; y < 6; ++y) map.grid[std::make_pair(x, y)] = new Tile(x, y);
              worker.map = &map; worker.seat = &seat; worker.pos = at(0, 0); }
    Tile* at(int x, int y) { return map.grid[std::make_pair(x, y)]; }
    RoomTreasury* treasury(int x0, int n, int y = 0) {
        RoomTreasury* r = new RoomTreasury(&seat);
        for(int i = 0; i < n; ++i) r->add(at(x0 + i, y));
        map.rooms.push_back(r); return r;
    }
    //! \brief 5x5 heart around (cx, cy); the ring tiles hold gold.
    RoomDungeonTemple* heart(int cx, int cy) {
        RoomDungeonTemple* r = new RoomDungeonTemple(&seat); r->heart = at(cx, cy);
        for(int x = cx - 2; x <= cx + 2; ++x) for(int y = cy - 2; y <= cy + 2; ++y) r->add(at(x, y));
        map.rooms.push_back(r); return r;
    }
    Tile* nearest() { return CreatureActionCarryEntity::findNearestGoldTile(worker, worker.pos); }
};

int main() {
    // far_corner / ai_keeper: the tile nearest by walking wins, not the first tile of the room (any keeper's worker)
    { World w; w.worker.pos = w.at(10, 0); RoomTreasury* t = w.treasury(3, 3);
      check(w.nearest() == w.at(5, 0) && w.at(5, 0) != t->tiles[0], "far_corner: the nearest tile wins, not the first one"); }
    // tile_full: a full nearest tile is skipped
    { World w; w.worker.pos = w.at(10, 0); RoomTreasury* t = w.treasury(3, 6); t->gold(w.at(8, 0)) = 1000;
      check(w.nearest() == w.at(7, 0), "tile_full: the next tile with room wins"); }
    // treasury_before_heart: treasury 3 steps, heart ring 8 steps
    { World w; w.worker.pos = w.at(0, 2); w.treasury(3, 1, 2); w.heart(10, 2);
      check(w.nearest() == w.at(3, 2), "treasury_before_heart"); }
    // heart_before_far_treasury
    { World w; w.worker.pos = w.at(5, 2); w.heart(3, 2); w.treasury(13, 1, 2);
      Tile* t = w.nearest(); check(t != nullptr && t->room->type == RoomType::dungeonTemple && t == w.at(5, 2), "heart_before_far_treasury"); }
    // tie: equally near heart ring tile and treasury tile -> heart ring tile
    { World w; w.worker.pos = w.at(10, 2); w.treasury(15, 1, 2); RoomDungeonTemple* h = w.heart(3, 2);
      // heart ring tiles are 5 steps away, the treasury tile (15,2) is 5 steps away too
      check(w.nearest()->room == h, "tie: the heart ring tile wins"); }
    // tie independent of the order the rooms are registered in
    { World w; w.worker.pos = w.at(10, 2); RoomDungeonTemple* h = w.heart(3, 2); w.treasury(15, 1, 2);
      check(w.nearest()->room == h, "tie: the heart ring tile wins in any room order"); }
    // all_full: every tile holds its capacity -> no destination
    { World w; RoomTreasury* t = w.treasury(3, 3); for(Tile* x : t->tiles) t->gold(x) = 1000; RoomDungeonTemple* h = w.heart(10, 2);
      for(Tile* x : h->tiles) if(h->isTreasuryTile(x)) h->gold(x) = 1000;
      check(w.nearest() == nullptr, "all_full: no tile with room"); }
    // research_capacity: 1.25 research lets a tile with 1000 take more
    { World w; RoomTreasury* t = w.treasury(3, 1); t->research = 1.25; t->gold(w.at(3, 0)) = 1000;
      check(w.nearest() == w.at(3, 0) && t->getGoldSpaceInTile(w.at(3, 0)) == 250, "research_capacity"); }
    // unreachable: the nearest tile cannot be reached, a farther one can
    { World w; w.treasury(8, 1, 0); w.treasury(14, 1, 0);
      for(int y = 0; y < 6; ++y) w.map.blocked.insert(std::make_pair(9, y)); // a wall between the tile at x=8 and the worker
      w.worker.pos = w.at(11, 0);
      check(w.nearest() == w.at(14, 0), "unreachable: the farther reachable tile wins"); }
    // no_hp_tile: a tile without hit points is no candidate
    { World w; w.worker.pos = w.at(10, 0); RoomTreasury* t = w.treasury(3, 6); t->mTileData[w.at(8, 0)]->mHP = 0;
      check(w.nearest() == w.at(7, 0), "no_hp_tile"); }
    // small_heart: a 3x3 heart (all core) takes no gold, the treasury farther away does
    { World w; w.worker.pos = w.at(1, 1); RoomDungeonTemple* h = new RoomDungeonTemple(&w.seat); h->heart = w.at(2, 2);
      for(int x = 1; x <= 3; ++x) for(int y = 1; y <= 3; ++y) h->add(w.at(x, y));
      w.map.rooms.push_back(h); w.treasury(12, 1, 2);
      check(w.nearest() == w.at(12, 2), "small_heart"); }
    // a foreign keeper's gold room is no candidate
    { World w; RoomTreasury* t = w.treasury(3, 1); t->seat = &w.other;
      check(w.nearest() == nullptr, "foreign treasury is no candidate"); }

    // filled_on_the_way / target_lost / all_full_on_the_way: the carry action decides again from where the worker stands
    { World w; RoomTreasury* t = w.treasury(3, 1); RoomTreasury* t2 = w.treasury(8, 1); GameEntity gold;
      CreatureActionCarryEntity act(w.worker, &gold, w.at(3, 0), t);
      act.handleCarryGold();
      check(g_walkedTo == w.at(3, 0) && w.worker.pops == 0, "the worker walks to its tile while it has room");
      t->gold(w.at(3, 0)) = 1000; // another delivery filled the target
      w.worker.pos = w.at(6, 0);
      act.handleCarryGold();
      check(g_walkedTo == w.at(8, 0) && act.mTileDest == w.at(8, 0) && act.mBuildingDest == t2, "filled_on_the_way: carries on to the nearest tile with room");
      t2->gold(w.at(8, 0)) = 1000; // everything full now
      act.handleCarryGold();
      check(w.worker.pops == 1, "all_full_on_the_way: the gold is put down where the worker stands"); }
    { World w; RoomTreasury* t = w.treasury(3, 1); RoomTreasury* t2 = w.treasury(9, 1); GameEntity gold;
      CreatureActionCarryEntity act(w.worker, &gold, w.at(3, 0), t);
      t->tiles.clear(); t->mTileData.clear(); w.at(3, 0)->room = nullptr; // target_lost: the tile was sold
      w.worker.pos = w.at(5, 0);
      act.handleCarryGold();
      check(g_walkedTo == w.at(9, 0) && act.mBuildingDest == t2, "target_lost: carries on to the tile with room"); }

    std::cout << "CHECKS=" << checks << " FAILURES=" << failures << '\n';
    return failures == 0 ? 0 : 1;
}
"""

probe = probe.replace('__SPACE_TREASURY__', get_space_treasury)
probe = probe.replace('__SPACE_TEMPLE__', get_space_temple)
probe = probe.replace('__OWN_SPACE__', function(carry, 'static double getOwnGoldSpace('))
probe = probe.replace('__NEAREST__', function(carry, 'Tile* CreatureActionCarryEntity::findNearestGoldTile('))
probe = probe.replace('__CARRY_GOLD__', function(carry, 'bool CreatureActionCarryEntity::handleCarryGold('))

with tempfile.TemporaryDirectory(prefix='odp-gold-nearest-') as tmp:
    probe_path = Path(tmp) / 'check.cpp'
    probe_path.write_text(probe)
    exe = Path(tmp) / 'check.exe'
    cmd = 'cl /nologo /EHsc /MD /std:c++17 /Fo"{}" {} /Fe"{}"'.format(
        str(Path(tmp) / 'check.obj'), str(probe_path), str(exe))
    build = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if build.returncode != 0:
        print(build.stdout)
        print(build.stderr)
        raise SystemExit(1)
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    print(run.stdout)
    if run.returncode != 0:
        print(run.stderr)
        raise SystemExit(1)

print('check_gold_nearest_tile ok')
