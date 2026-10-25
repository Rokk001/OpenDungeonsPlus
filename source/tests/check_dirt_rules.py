"""Dirt rules: the real functions of the dirt model are cut out of the sources and run against small stubs.

What is run (the function bodies are taken from the source files, not copied by hand):
  Tile::canCarryDirt / addDirt / cleanDirt / setDirt   clamps 0 - 100, rock/water/lava/gold/walls carry nothing
  Room::getDirtMean / getDirtStage / getDirtOutputFactor / getDirtStageFactor   the stage thresholds and the output,
                                                      prison and torture factors
  Room::addUseDirt                                    the room key times the DirtFactor of the creature type
  DirtPileEntity::createOnTile / getEntityOnTile / doUpkeep / cleanBy   a pile sets 100 and is refreshed, blood
                                                      dries at BloodDryTurns and keeps the tile dirt
  CreatureMoodDirt (the stage and pile mood)          values per stage x Cleanliness, per pile in the radius, no mood
                                                      for seat-less heroes
  Creature::increaseUrge / foodEaten / setUrge / increaseCreatureDirt / upkeepCreatureDirt / dirtyEnteredTile and the
  two fight blocks (fight end +5, knock-out +25, never both)
The values come from config/global.cfg [Dirt] and config/rooms.cfg. The source wiring (where the urge thresholds, the
output factors and the room keys are used) is checked on the source text.

Calls (from the repository root):
  python source/tests/check_dirt_rules.py

The probe needs the MSVC compiler on the path (run it in a Visual Studio developer shell, like the other probes)."""
from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]


def read(path):
    return (root / path).read_text(encoding='utf-8')


# Returns the text of a function from its first line up to its closing brace (a brace in column 0).
def extract(text, header):
    start = text.index(header)
    end = text.index('\n}\n', start) + 2
    return text[start:end]


# Returns the key -> value words of the first block [tag]...[/tag] of a text (comments skipped).
def block_values(text, tag):
    match = re.search(r'^\[' + tag + r'\]\s*$(.*?)^\[/' + tag + r'\]', text, re.M | re.S)
    assert match is not None, 'block [' + tag + '] missing'
    values = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            values.setdefault(words[0], words[1])
    return values


tile_cpp = read('source/entities/Tile.cpp')
room_cpp = read('source/rooms/Room.cpp')
pile_cpp = read('source/entities/DirtPileEntity.cpp')
mood_cpp = read('source/creaturemood/CreatureMoodDirt.cpp')
creature_cpp = read('source/entities/Creature.cpp')
search_cpp = read('source/creatureaction/CreatureActionSearchDirtToClean.cpp')
library_cpp = read('source/rooms/RoomLibrary.cpp')
workshop_cpp = read('source/rooms/RoomWorkshop.cpp')
seat_cpp = read('source/game/Seat.cpp')

# ---- Source wiring -----------------------------------------------------------------------------------------------
# Urge: grows per turn for creatures with a seat that is not rogue, from UrgeSeek the creature looks for a toilet,
# from UrgeOnTheWay it uses a seat on its way, at UrgeRelieve it relieves itself
growth_at = creature_cpp.index('increaseUrge(mDefinition->getUrgeGrowthPerTurn());')
assert 'if(!getSeat()->isRogueSeat())' in creature_cpp[growth_at - 600:growth_at], 'urge growth must skip rogue creatures'
handle = extract(creature_cpp, 'void Creature::handleUrge()')
assert 'isWorker()' in handle and 'getDirtConfigDouble("UrgeOnTheWay")' in handle
assert 'getDirtConfigDouble("UrgeRelieve")' in handle and 'relieve();' in handle
for guard in ('mIsInHand', 'mIsBeingDragged', 'isKo()', 'isPossessed()', 'CreatureActionType::fight'):
    assert guard in handle, 'handleUrge must wait while ' + guard
assert 'getDirtConfigDouble("UrgeSeek")' in creature_cpp and 'CreatureActionSearchToilet' in creature_cpp
# The D6 exception rooms: a creature in a treasury, the heart room or a temple steps out before it relieves itself
toilet_cpp = read('source/creatureaction/CreatureActionUseToilet.cpp')
exempt = extract(toilet_cpp, 'bool CreatureActionUseToilet::isExemptRoomType(')
for room in ('RoomType::treasury', 'RoomType::dungeonTemple', 'RoomType::temple'):
    assert room in exempt, room + ' must be an exception room'
# Output factors: each production site multiplies by the room's factor
for path, token in [('source/rooms/RoomLibrary.cpp', 'getDirtOutputFactor()'), ('source/rooms/RoomWorkshop.cpp', 'getDirtOutputFactor()'),
                    ('source/rooms/RoomTrainingHall.cpp', 'getDirtOutputFactor()'), ('source/rooms/RoomCasino.cpp', 'getDirtOutputFactor()'),
                    ('source/rooms/RoomTemple.cpp', 'getDirtOutputFactor()'), ('source/rooms/RoomHatchery.cpp', 'getDirtOutputFactor()'),
                    ('source/creatureaction/CreatureActionSleep.cpp', 'getDirtOutputFactor()'),
                    ('source/rooms/RoomPrison.cpp', 'getDirtStageFactor("PrisonDirtDamageStage2", "PrisonDirtDamageStage3")'),
                    ('source/rooms/RoomTorture.cpp', 'getDirtStageFactor("TortureDirtConvertStage2", "TortureDirtConvertStage3")')]:
    assert token in read(path), path + ' must use ' + token
assert 'receiveExp(1.5 * attackRoom->getDirtOutputFactor() * getHangoverWorkFactor())' in creature_cpp, 'arena experience per hit'
# Piles in rooms workers never clean: the search and the seat check use the same rule
assert 'isPileCleanable(*tile)' in extract(search_cpp, 'static Tile* findPileTile('), 'the pile search must use the shared rule'
assert 'isPileCleanable(*tile)' in extract(seat_cpp, 'bool Seat::hasDirtToClean() const'), 'hasDirtToClean must use the shared rule'
# Library and workshop points keep the fraction of the dirt factor
for text, member in [(library_cpp, 'mSkillPointsRemainder'), (workshop_cpp, 'mPointsRemainder')]:
    assert 'takeWholeWorkPoints(' in text and member in text, 'work points must carry the remainder in ' + member
# Rooms without output effect do not read the factor (crypt, treasury, portals, heart, bridges, toilet)
for path in ('RoomCrypt', 'RoomTreasury', 'RoomPortal', 'RoomPortalWave', 'RoomDungeonTemple', 'RoomBridge', 'RoomToilet'):
    candidate = root / 'source' / 'rooms' / (path + '.cpp')
    if candidate.exists():
        assert 'getDirtOutputFactor' not in candidate.read_text(encoding='utf-8'), path + ' has no output effect'
# Every per-room dirt key of rooms.cfg is used by a room or an action
rooms_values = block_values(read('config/rooms.cfg'), 'Rooms')
sources = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'source').rglob('*.cpp'))
for key in [k for k in rooms_values if 'DirtPer' in k]:
    assert '"' + key + '"' in sources, key + ' is not used in the source'

# ---- Probe -------------------------------------------------------------------------------------------------------
dirt = block_values(read('config/global.cfg'), 'Dirt')
config_entries = [(k, v) for k, v in dirt.items()] + [(k, v) for k, v in rooms_values.items() if 'DirtPer' in k]
config_table = ',\n'.join('    {"%s", %s}' % (k, v) for k, v in config_entries)

probe = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace Ogre { typedef float Real; struct Vector3 { Real x, y, z; Vector3(Real ax, Real ay, Real az) : x(ax), y(ay), z(az) {} }; }

static int failures = 0;
static void expect(bool ok, const std::string& what)
{
    if(!ok) { ++failures; std::cout << "FAIL: " << what << std::endl; }
}
static void expectNear(double a, double b, const std::string& what)
{
    if(std::fabs(a - b) > 1e-9) { ++failures; std::cout << "FAIL: " << what << " got " << a << " expected " << b << std::endl; }
}

// ---- Configuration: the real values of the config files, an unknown key is a failure
struct ConfigManager
{
    std::map<std::string, double> values;
    static ConfigManager& getSingleton() { static ConfigManager instance; return instance; }
    double lookup(const std::string& key) const
    {
        std::map<std::string, double>::const_iterator it = values.find(key);
        if(it == values.end()) { ++failures; std::cout << "FAIL: unknown config key " << key << std::endl; return 0.0; }
        return it->second;
    }
    double getDirtConfigDouble(const std::string& key) const { return lookup(key); }
    double getRoomConfigDoubleOrDefault(const std::string& key, double def) const
    {
        std::map<std::string, double>::const_iterator it = values.find(key);
        return (it == values.end()) ? def : it->second;
    }
};
static void loadConfig()
{
    static const struct { const char* key; double value; } table[] = {
@@CONFIG@@
    };
    for(unsigned i = 0; i < sizeof(table) / sizeof(table[0]); ++i)
        ConfigManager::getSingleton().values[table[i].key] = table[i].value;
}

enum class RoomType { dungeonTemple, treasury, crypt, workshop, prison, torture, temple, library, nbRooms };
enum class TileType { dirt, water, lava, gold, rock };
enum class GameEntityType { creature, dirtPileEntity, other };
enum class DirtPileKind { pile, blood, vomit };

struct Room; struct GameMap; struct Tile; struct Creature;

// ---- Entities on a tile
struct GameEntity
{
    virtual ~GameEntity() {}
    virtual GameEntityType getObjectType() const = 0;
};

struct Tile
{
    static const double MAX_DIRT;
    int mX, mY;
    double mDirt, mFullness;
    TileType mType;
    Room* mRoom;
    bool mClaimed;
    GameMap* mMap;
    int dirtChanges;
    std::vector<GameEntity*> mEntities;
    Tile(int x, int y) : mX(x), mY(y), mDirt(0.0), mFullness(0.0), mType(TileType::dirt), mRoom(nullptr), mClaimed(false), mMap(nullptr), dirtChanges(0) {}
    int getX() const { return mX; }
    int getY() const { return mY; }
    double getDirt() const { return mDirt; }
    Room* getCoveringRoom() const { return mRoom; }
    bool isClaimed() const { return mClaimed; }
    GameMap* getGameMap() const { return mMap; }
    const std::vector<GameEntity*>& getEntitiesInTile() const { return mEntities; }
    void noteDirtChange() { ++dirtChanges; }
    bool canCarryDirt() const;
    void addDirt(double amount);
    void cleanDirt(double amount);
    void setDirt(double dirt);
};

struct Seat
{
    bool rogue; std::string faction;
    Seat() : rogue(false), faction("Keeper") {}
    bool isRogueSeat() const { return rogue; }
    const std::string& getFaction() const { return faction; }
};

struct CreatureDefinition
{
    double dirtFactor, cleanliness, urgeGrowth;
    CreatureDefinition() : dirtFactor(1.0), cleanliness(1.0), urgeGrowth(0.1) {}
    double getDirtFactor() const { return dirtFactor; }
    double getCleanliness() const { return cleanliness; }
    double getUrgeGrowthPerTurn() const { return urgeGrowth; }
};

struct Room
{
    std::vector<Tile*> mCoveredTiles;
    RoomType mType;
    double notified;
    Room() : mType(RoomType::workshop), notified(0.0) {}
    bool isCleanableByWorkers() const;
    RoomType getType() const { return mType; }
    void notifyDirtAdded(double added) { notified += added; }
    double getDirtMean() const;
    uint32_t getDirtStage() const;
    double getDirtOutputFactor() const;
    double getDirtStageFactor(const std::string& stage2Key, const std::string& stage3Key) const;
    static void addUseDirt(const Creature& creature, Tile* tile, const std::string& key);
};

struct CreatureActionSearchDirtToClean { static bool isPileCleanable(const Tile& tile); };

struct GameMap
{
    int sizeX, sizeY;
    std::vector<Tile> tiles;
    GameMap(int x, int y) : sizeX(x), sizeY(y) { for(int yy = 0; yy < y; ++yy) for(int xx = 0; xx < x; ++xx) tiles.push_back(Tile(xx, yy)); }
    void link() { for(unsigned i = 0; i < tiles.size(); ++i) tiles[i].mMap = this; }
    Tile* getTile(int x, int y) const
    {
        if((x < 0) || (y < 0) || (x >= sizeX) || (y >= sizeY)) return nullptr;
        return const_cast<Tile*>(&tiles[y * sizeX + x]);
    }
    bool isServerGameMap() const { return true; }
};

// ---- Pile / blood entity
struct DirtPileEntity : public GameEntity
{
    static const double DIRT_LEFT_START;
    GameMap* mMap; DirtPileKind mKind; std::string mCreatureClass; double mDirtLeft, mAgeTurns;
    bool onMap; Tile* mTile; int removed;
    DirtPileEntity(GameMap* gameMap, DirtPileKind kind, const std::string& creatureClass)
      : mMap(gameMap), mKind(kind), mCreatureClass(creatureClass), mDirtLeft(DIRT_LEFT_START), mAgeTurns(0.0), onMap(false), mTile(nullptr), removed(0) {}
    GameEntityType getObjectType() const { return GameEntityType::dirtPileEntity; }
    bool getIsOnMap() const { return onMap; }
    void addToGameMap() { onMap = true; }
    void createMesh() {}
    void setPosition(const Ogre::Vector3& position)
    {
        mTile = mMap->getTile(static_cast<int>(position.x), static_cast<int>(position.y));
        mTile->mEntities.push_back(this);
    }
    void removeFromGameMap()
    {
        onMap = false;
        mTile->mEntities.erase(std::find(mTile->mEntities.begin(), mTile->mEntities.end(), static_cast<GameEntity*>(this)));
    }
    void deleteYourself() { ++removed; }
    void doUpkeep();
    static DirtPileEntity* createOnTile(GameMap* gameMap, Tile* tile, DirtPileKind kind, const std::string& creatureClass);
    static DirtPileEntity* getEntityOnTile(const Tile* tile, DirtPileKind kind);
    bool cleanBy(double amount);
};
const double DirtPileEntity::DIRT_LEFT_START = 100.0;

// ---- Creature
static const double NEED_MAX = 100.0;
static const double CREATURE_DIRT_SHARE_DIVISOR = NEED_MAX;
struct Creature
{
    Seat* mSeat; CreatureDefinition* mDefinition; GameMap* mMap; Tile* mTile;
    double mUrge, mCreatureDirt, mHunger;
    double mDragDirtFactor; bool mFoughtSinceFightEnd;
    bool mDirtKoThisFight, mIsBeingDragged, mTorturedThisTurn, inPrison, inContainment, koTemp, koDeath;
    int mNbTurnsWithoutBattle; GameEntity* mCarriedEntity;
    Creature(Seat* seat, CreatureDefinition* definition, GameMap* map, Tile* tile)
      : mSeat(seat), mDefinition(definition), mMap(map), mTile(tile), mUrge(0.0), mCreatureDirt(0.0), mHunger(50.0), mDragDirtFactor(1.0), mFoughtSinceFightEnd(false),
        mDirtKoThisFight(false), mIsBeingDragged(false), mTorturedThisTurn(false), inPrison(false), inContainment(false),
        koTemp(false), koDeath(false), mNbTurnsWithoutBattle(5), mCarriedEntity(nullptr) {}
    Seat* getSeat() const { return mSeat; }
    const CreatureDefinition* getDefinition() const { return mDefinition; }
    GameMap* getGameMap() const { return mMap; }
    Tile* getPositionTile() const { return mTile; }
    bool isInPrison() const { return inPrison; }
    bool isInContainment() const { return inContainment; }
    bool getIsOnServerMap() const { return true; }
    bool isKoTemp() const { return koTemp; }
    bool isKoDeath() const { return koDeath; }
    void increaseUrge(double value);
    void setUrge(double val);
    void foodEaten(double val);
    void increaseCreatureDirt(double value);
    void setCreatureDirt(double val);
    void upkeepCreatureDirt();
    void dirtyEnteredTile(Tile* tile);
    void washed();
    void fightEndBlock();
    void koBlock(bool wasKo);
};
@@MAXDIRT@@
@@TILE_FUNCTIONS@@
@@ROOM_FUNCTIONS@@
@@SEARCH_FUNCTIONS@@
@@WORKPOINT_FUNCTIONS@@
@@PILE_FUNCTIONS@@
@@CREATURE_FUNCTIONS@@
void Creature::fightEndBlock()
{
@@FIGHT_END_BLOCK@@
}
void Creature::koBlock(bool wasKo)
{
@@KO_BLOCK@@
}

// ---- Mood
struct CreatureMoodDirt { int32_t computeMood(const Creature& creature) const; };
namespace {
@@MOOD_FUNCTIONS@@
}
@@MOOD_COMPUTE@@

// ---- Fixtures and checks
static Room* makeRoom(GameMap& map, int x0, int y0, int w, int h, RoomType type)
{
    Room* room = new Room();
    room->mType = type;
    for(int y = y0; y < y0 + h; ++y)
        for(int x = x0; x < x0 + w; ++x)
        {
            Tile* tile = map.getTile(x, y);
            tile->mRoom = room;
            room->mCoveredTiles.push_back(tile);
        }
    return room;
}

static void checkTile()
{
    GameMap map(12, 12); map.link();
    Room* room = makeRoom(map, 1, 1, 2, 2, RoomType::workshop);
    Tile* tile = map.getTile(1, 1);
    tile->addDirt(30.0); expectNear(tile->getDirt(), 30.0, "addDirt adds");
    tile->addDirt(80.0); expectNear(tile->getDirt(), 100.0, "addDirt clamps at 100");
    tile->cleanDirt(40.0); expectNear(tile->getDirt(), 60.0, "cleanDirt subtracts");
    tile->cleanDirt(500.0); expectNear(tile->getDirt(), 0.0, "cleanDirt clamps at 0");
    tile->setDirt(-5.0); expectNear(tile->getDirt(), 0.0, "setDirt clamps below");
    tile->setDirt(500.0); expectNear(tile->getDirt(), 100.0, "setDirt clamps above");
    tile->setDirt(0.0); tile->addDirt(-3.0); tile->addDirt(0.0); expectNear(tile->getDirt(), 0.0, "non-positive amounts are ignored");
    expectNear(room->notified, 100.0, "the room is told the dirt that was really added (30 + 70)");
    // Tiles that carry no dirt
    Tile* rock = map.getTile(8, 8); rock->mType = TileType::rock; rock->mClaimed = true; rock->addDirt(10.0);
    expectNear(rock->getDirt(), 0.0, "rock carries no dirt");
    Tile* water = map.getTile(9, 8); water->mType = TileType::water; water->mClaimed = true; water->addDirt(10.0);
    expectNear(water->getDirt(), 0.0, "water carries no dirt");
    Tile* lava = map.getTile(10, 8); lava->mType = TileType::lava; lava->mClaimed = true; lava->addDirt(10.0);
    expectNear(lava->getDirt(), 0.0, "lava carries no dirt");
    Tile* gold = map.getTile(8, 9); gold->mType = TileType::gold; gold->mClaimed = true; gold->addDirt(10.0);
    expectNear(gold->getDirt(), 0.0, "gold carries no dirt");
    Tile* wall = map.getTile(9, 9); wall->mFullness = 100.0; wall->mClaimed = true; wall->addDirt(10.0);
    expectNear(wall->getDirt(), 0.0, "a wall carries no dirt");
    Tile* corridor = map.getTile(5, 5); corridor->mClaimed = true; corridor->addDirt(10.0);
    expectNear(corridor->getDirt(), 10.0, "a claimed corridor tile carries dirt");
    Tile* bare = map.getTile(6, 6); bare->addDirt(10.0);
    expectNear(bare->getDirt(), 0.0, "an unclaimed tile outside a room carries no dirt");
}

static void checkStages()
{
    GameMap map(12, 12); map.link();
    Room* room = makeRoom(map, 1, 1, 2, 2, RoomType::workshop);
    expect(room->getDirtStage() == 1, "stage 1 when clean");
    Room empty; expectNear(empty.getDirtMean(), 0.0, "mean of an empty room is 0"); expect(empty.getDirtStage() == 1, "empty room is stage 1");
    struct Case { double mean; uint32_t stage; double output; };
    static const Case cases[] = {
        {33.3332, 1, 1.0}, {33.3333, 2, 0.75}, {66.6666, 2, 0.75}, {66.6667, 3, 0.5}, {100.0, 3, 0.5}};
    for(unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
    {
        for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mDirt = cases[i].mean;
        expectNear(room->getDirtMean(), cases[i].mean, "mean of equal tiles");
        expect(room->getDirtStage() == cases[i].stage, "stage at mean " + std::to_string(cases[i].mean));
        expectNear(room->getDirtOutputFactor(), cases[i].output, "output factor at mean " + std::to_string(cases[i].mean));
    }
    // A mean over unequal tiles
    room->mCoveredTiles[0]->mDirt = 100.0; room->mCoveredTiles[1]->mDirt = 100.0; room->mCoveredTiles[2]->mDirt = 0.0; room->mCoveredTiles[3]->mDirt = 0.0;
    expectNear(room->getDirtMean(), 50.0, "mean of unequal tiles"); expect(room->getDirtStage() == 2, "stage 2 at mean 50");
    // Prison and torture factors by stage
    for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mDirt = 0.0;
    expectNear(room->getDirtStageFactor("PrisonDirtDamageStage2", "PrisonDirtDamageStage3"), 1.0, "prison factor at stage 1");
    expectNear(room->getDirtStageFactor("TortureDirtConvertStage2", "TortureDirtConvertStage3"), 1.0, "torture factor at stage 1");
    for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mDirt = 50.0;
    expectNear(room->getDirtStageFactor("PrisonDirtDamageStage2", "PrisonDirtDamageStage3"), 1.25, "prison factor at stage 2");
    expectNear(room->getDirtStageFactor("TortureDirtConvertStage2", "TortureDirtConvertStage3"), 0.9, "torture factor at stage 2");
    for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mDirt = 90.0;
    expectNear(room->getDirtStageFactor("PrisonDirtDamageStage2", "PrisonDirtDamageStage3"), 1.5, "prison factor at stage 3");
    expectNear(room->getDirtStageFactor("TortureDirtConvertStage2", "TortureDirtConvertStage3"), 0.8, "torture factor at stage 3");
}

static void checkUseDirt()
{
    GameMap map(6, 6); map.link();
    makeRoom(map, 1, 1, 2, 2, RoomType::workshop);
    Seat seat; CreatureDefinition definition; definition.dirtFactor = 1.75;
    Tile* tile = map.getTile(1, 1);
    Creature creature(&seat, &definition, &map, tile);
    Room::addUseDirt(creature, tile, "WorkshopDirtPerWork");
    expectNear(tile->getDirt(), 1.5922 * 1.75, "room use dirt = key x DirtFactor");
    double before = tile->getDirt();
    Room::addUseDirt(creature, tile, "CryptDirtPerNothing");
    expectNear(tile->getDirt(), before, "a room without a key makes no dirt");
    Room::addUseDirt(creature, nullptr, "WorkshopDirtPerWork");
}

static void checkPileCleaningRule()
{
    GameMap map(12, 12); map.link();
    RoomType blocked[] = {RoomType::prison, RoomType::torture, RoomType::crypt};
    for(unsigned i = 0; i < 3; ++i)
    {
        Room* room = makeRoom(map, 1, 1, 2, 2, blocked[i]);
        Tile* tile = map.getTile(1, 1);
        expect(!CreatureActionSearchDirtToClean::isPileCleanable(*tile), "a pile in prison, torture chamber or crypt is not cleaned");
        for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mRoom = nullptr;
    }
    makeRoom(map, 4, 4, 2, 2, RoomType::workshop);
    expect(CreatureActionSearchDirtToClean::isPileCleanable(*map.getTile(4, 4)), "a pile in a workshop is cleaned");
    expect(CreatureActionSearchDirtToClean::isPileCleanable(*map.getTile(8, 8)), "a pile in a corridor is cleaned");
}

static void checkWorkPoints()
{
    // Stage 2 and stage 3 factors over four work turns of 5.0 base points lose no fraction
    double factors[] = {0.75, 0.5};
    int expected[] = {15, 10};
    for(unsigned f = 0; f < 2; ++f)
    {
        double remainderLibrary = 0.0, remainderWorkshop = 0.0;
        int totalLibrary = 0, totalWorkshop = 0;
        for(int turn = 0; turn < 4; ++turn)
        {
            totalLibrary += libraryTakeWholeWorkPoints(5.0, factors[f], remainderLibrary);
            totalWorkshop += workshopTakeWholeWorkPoints(5.0, factors[f], remainderWorkshop);
        }
        expect(totalLibrary == expected[f], "library points over 4 turns at factor " + std::to_string(factors[f]) + " got " + std::to_string(totalLibrary));
        expect(totalWorkshop == expected[f], "workshop points over 4 turns at factor " + std::to_string(factors[f]) + " got " + std::to_string(totalWorkshop));
    }
    // Stage 1 keeps the plain truncation without carrying anything
    double remainder = 0.0;
    expect(libraryTakeWholeWorkPoints(2.9, 1.0, remainder) == 2 && remainder == 0.0, "library stage 1 truncates as before");
    expect(workshopTakeWholeWorkPoints(2.9, 1.0, remainder) == 2 && remainder == 0.0, "workshop stage 1 truncates as before");
}

static void checkPiles()
{
    GameMap map(8, 8); map.link();
    makeRoom(map, 1, 1, 3, 3, RoomType::workshop);
    Tile* tile = map.getTile(2, 2);
    DirtPileEntity* pile = DirtPileEntity::createOnTile(&map, tile, DirtPileKind::pile, "Orc");
    expect(pile != nullptr && DirtPileEntity::getEntityOnTile(tile, DirtPileKind::pile) == pile, "pile lies on the tile");
    expectNear(tile->getDirt(), 100.0, "a pile sets the tile dirt to 100");
    expect(DirtPileEntity::getEntityOnTile(tile, DirtPileKind::blood) == nullptr, "no blood yet");
    expect(!pile->cleanBy(40.0), "cleanBy keeps a pile with dirt left");
    expectNear(pile->mDirtLeft, 60.0, "cleanBy lowers dirt left");
    tile->setDirt(20.0);
    DirtPileEntity* again = DirtPileEntity::createOnTile(&map, tile, DirtPileKind::pile, "Orc");
    expect(again == pile && tile->mEntities.size() == 1, "a second pile refreshes the first one");
    expectNear(pile->mDirtLeft, 100.0, "refresh sets dirt left back to 100");
    expectNear(tile->getDirt(), 100.0, "refresh sets the tile dirt to 100 again");
    for(int i = 0; i < 1000; ++i) pile->doUpkeep();
    expect(pile->onMap, "a pile never dries");
    // Blood: no tile dirt of its own, dries at BloodDryTurns, keeps the dirt of its tile
    Tile* other = map.getTile(3, 3);
    DirtPileEntity* blood = DirtPileEntity::createOnTile(&map, other, DirtPileKind::blood, "Orc");
    expectNear(other->getDirt(), 0.0, "blood does not set the tile dirt");
    other->setDirt(12.0);
    int dry = static_cast<int>(ConfigManager::getSingleton().getDirtConfigDouble("BloodDryTurns"));
    for(int i = 0; i < dry - 1; ++i) blood->doUpkeep();
    expect(blood->onMap, "blood is still there one turn before it dries");
    blood->doUpkeep();
    expect(!blood->onMap && DirtPileEntity::getEntityOnTile(other, DirtPileKind::blood) == nullptr, "blood dries at BloodDryTurns");
    expectNear(other->getDirt(), 12.0, "the tile keeps its dirt when blood dries");
    // A pile and a stain share a tile
    DirtPileEntity* both = DirtPileEntity::createOnTile(&map, tile, DirtPileKind::blood, "Orc");
    expect(both != nullptr && both != pile && tile->mEntities.size() == 2, "pile and stain can share a tile");
    // cleanBy removes the entity and tells the caller
    expect(pile->cleanBy(1000.0), "cleanBy returns true when the pile is gone");
    expect(DirtPileEntity::getEntityOnTile(tile, DirtPileKind::pile) == nullptr, "the cleaned pile is off the tile");
}

static int mood(Creature& creature) { CreatureMoodDirt m; return m.computeMood(creature); }

static void checkMood()
{
    GameMap map(12, 12); map.link();
    Room* room = makeRoom(map, 1, 1, 3, 3, RoomType::workshop);
    Room* crypt = makeRoom(map, 8, 8, 2, 2, RoomType::crypt);
    Seat seat; CreatureDefinition definition;
    Tile* tile = map.getTile(2, 2);
    Creature creature(&seat, &definition, &map, tile);
    struct Case { double dirtValue; double cleanliness; int expected; };
    static const Case cases[] = {
        {0.0, 1.0, 0}, {50.0, 1.0, -30}, {90.0, 1.0, -60}, {50.0, 0.25, -8}, {90.0, 0.25, -15}, {50.0, 0.5, -15},
        {90.0, 0.5, -30}, {50.0, 1.5, -45}, {90.0, 1.5, -90}, {50.0, 2.0, -60}, {90.0, 2.0, -120}};
    for(unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
    {
        for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mDirt = cases[i].dirtValue;
        definition.cleanliness = cases[i].cleanliness;
        expect(mood(creature) == cases[i].expected, "stage mood at dirt " + std::to_string(cases[i].dirtValue) + " x " + std::to_string(cases[i].cleanliness) + " got " + std::to_string(mood(creature)));
    }
    // Piles within the radius, once per pile, Cleanliness applies; blood gives nothing; stage 1 room
    for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mDirt = 0.0;
    definition.cleanliness = 1.0;
    expect(mood(creature) == 0, "no dirt, no mood");
    DirtPileEntity::createOnTile(&map, map.getTile(4, 4), DirtPileKind::pile, "Orc");   // distance 2: inside
    expect(mood(creature) == -30, "one pile at distance 2 gives DirtPileMood");
    DirtPileEntity::createOnTile(&map, map.getTile(5, 5), DirtPileKind::pile, "Orc");   // distance 3: outside
    expect(mood(creature) == -30, "a pile at distance 3 gives nothing");
    DirtPileEntity::createOnTile(&map, map.getTile(2, 1), DirtPileKind::pile, "Rat");
    expect(mood(creature) == -60, "every pile counts once");
    DirtPileEntity::createOnTile(&map, map.getTile(1, 2), DirtPileKind::blood, "Orc");
    expect(mood(creature) == -60, "blood gives no mood");
    definition.cleanliness = 2.0;
    expect(mood(creature) == -120, "piles times Cleanliness");
    definition.cleanliness = 1.0;
    // Crypt: no stage mood at stage 3
    Tile* cryptTile = map.getTile(8, 8);
    for(unsigned t = 0; t < crypt->mCoveredTiles.size(); ++t) crypt->mCoveredTiles[t]->mDirt = 90.0;
    Creature inCrypt(&seat, &definition, &map, cryptTile);
    expect(mood(inCrypt) == 0, "a crypt gives no dirt mood");
    DirtPileEntity::createOnTile(&map, map.getTile(9, 9), DirtPileKind::vomit, "Orc");
    expect(mood(inCrypt) == -30, "a vomit puddle counts like a pile");
    // No mood without a seat, none for a free hero or rogue creature, but a captured hero is a prisoner
    for(unsigned t = 0; t < room->mCoveredTiles.size(); ++t) room->mCoveredTiles[t]->mDirt = 90.0;
    Creature seatless(nullptr, &definition, &map, tile);
    expect(mood(seatless) == 0, "no seat, no mood");
    Seat heroSeat; heroSeat.faction = "Hero";
    Creature hero(&heroSeat, &definition, &map, tile);
    expect(mood(hero) == 0, "a free hero has no mood");
    hero.inPrison = true;
    // The stage mood -60 plus the two piles that still lie within the radius (-30 each)
    expect(mood(hero) == -120, "a hero in prison feels the dirt");
    hero.inPrison = false; hero.inContainment = true;
    expect(mood(hero) == -120, "a hero in containment feels the dirt");
    Seat rogueSeat; rogueSeat.rogue = true;
    Creature rogue(&rogueSeat, &definition, &map, tile);
    expect(mood(rogue) == 0, "a rogue creature has no mood");
}

static void checkUrgeAndCreatureDirt()
{
    GameMap map(8, 8); map.link();
    makeRoom(map, 1, 1, 3, 3, RoomType::workshop);
    Seat seat; CreatureDefinition definition; definition.dirtFactor = 1.5;
    Tile* tile = map.getTile(2, 2);
    Creature creature(&seat, &definition, &map, tile);
    // Urge: +20 per chicken, 80 after four (seek), 100 after five (relieve), clamped
    for(int i = 0; i < 4; ++i) creature.foodEaten(10.0);
    expectNear(creature.mUrge, ConfigManager::getSingleton().getDirtConfigDouble("UrgeSeek"), "four chickens reach UrgeSeek");
    expectNear(creature.mHunger, 10.0, "hunger fell by 4 x 10");
    creature.foodEaten(10.0);
    expectNear(creature.mUrge, ConfigManager::getSingleton().getDirtConfigDouble("UrgeRelieve"), "five chickens reach UrgeRelieve");
    creature.foodEaten(10.0);
    expectNear(creature.mUrge, 100.0, "the urge is clamped at 100"); expectNear(creature.mHunger, 0.0, "hunger does not go below 0");
    creature.setUrge(-4.0); expectNear(creature.mUrge, 0.0, "setUrge clamps below"); creature.setUrge(400.0); expectNear(creature.mUrge, 100.0, "setUrge clamps above");
    creature.setUrge(0.0);
    for(int i = 0; i < 10; ++i) creature.increaseUrge(definition.getUrgeGrowthPerTurn());
    expectNear(creature.mUrge, 1.0, "ten turns of growth 0.1");
    Seat rogueSeat; rogueSeat.rogue = true; Creature rogue(&rogueSeat, &definition, &map, tile);
    rogue.increaseUrge(50.0); expectNear(rogue.mUrge, 0.0, "a rogue creature gets no urge");
    // Creature dirt: fight end +5, knock-out +25 and then nothing at the fight end, then +5 for the next fight
    creature.setCreatureDirt(0.0);
    creature.mNbTurnsWithoutBattle = 0; creature.fightEndBlock();
    expectNear(creature.mCreatureDirt, 0.0, "no fight, no dirt: a creature that never fought gets nothing at the first count");
    creature.mNbTurnsWithoutBattle = 0; creature.mFoughtSinceFightEnd = true; creature.fightEndBlock();
    expectNear(creature.mCreatureDirt, 5.0, "a fight won adds CreatureDirtPerFightWon"); expect(!creature.mFoughtSinceFightEnd, "the fight flag is cleared at the fight end");
    creature.mNbTurnsWithoutBattle = 5; creature.fightEndBlock();
    expectNear(creature.mCreatureDirt, 5.0, "only the turn the counter reaches 1 counts");
    creature.mNbTurnsWithoutBattle = 0; creature.mFoughtSinceFightEnd = true; creature.koTemp = true; creature.koBlock(false);
    expectNear(creature.mCreatureDirt, 30.0, "a knock-out adds CreatureDirtPerKo"); expect(creature.mDirtKoThisFight, "the knock-out is remembered");
    creature.koBlock(true);
    expectNear(creature.mCreatureDirt, 30.0, "a creature that was KO already adds nothing again");
    creature.fightEndBlock();
    expectNear(creature.mCreatureDirt, 30.0, "the fight end after a knock-out adds nothing"); expect(!creature.mDirtKoThisFight, "the flag is reset at the fight end");
    creature.mNbTurnsWithoutBattle = 0; creature.mFoughtSinceFightEnd = true; creature.koTemp = false; creature.fightEndBlock();
    expectNear(creature.mCreatureDirt, 35.0, "the next fight adds again");
    creature.setCreatureDirt(500.0); expectNear(creature.mCreatureDirt, 100.0, "creature dirt is clamped");
    // Decay 0.1 per turn, prison and torture hold it at 100
    creature.setCreatureDirt(10.0); creature.upkeepCreatureDirt(); expectNear(creature.mCreatureDirt, 9.9, "decay per turn");
    creature.setCreatureDirt(0.05); creature.upkeepCreatureDirt(); expectNear(creature.mCreatureDirt, 0.0, "decay stops at 0");
    creature.setCreatureDirt(0.0); creature.inPrison = true; creature.upkeepCreatureDirt();
    expectNear(creature.mCreatureDirt, 99.9, "prison sets the dirt to 100 before the decay"); creature.inPrison = false;
    creature.setCreatureDirt(0.0); creature.mTorturedThisTurn = true; creature.upkeepCreatureDirt();
    expectNear(creature.mCreatureDirt, 99.9, "torture sets the dirt to 100 before the decay"); creature.mTorturedThisTurn = false;
    creature.washed();
    // Trail: creature dirt / 100 x TrailDirtPerTile x DirtFactor, a load or a pulled creature adds a full share
    Tile* entered = map.getTile(3, 3);
    creature.setCreatureDirt(0.0); creature.dirtyEnteredTile(entered);
    expectNear(entered->getDirt(), 0.0, "a clean creature leaves no trail");
    creature.setCreatureDirt(50.0); creature.dirtyEnteredTile(entered);
    expectNear(entered->getDirt(), 0.1448 * 0.5 * 1.5, "creature dirt trail");
    entered->setDirt(0.0); creature.setCreatureDirt(0.0); creature.mIsBeingDragged = true; creature.mDragDirtFactor = 1.5; creature.dirtyEnteredTile(entered);
    expectNear(entered->getDirt(), 0.1448 * 1.0 * 1.5, "a pulled creature leaves a full trail");
    entered->setDirt(0.0); creature.mDragDirtFactor = 3.0; creature.dirtyEnteredTile(entered);
    expectNear(entered->getDirt(), 0.1448 * 1.0 * 3.0, "a pulled creature leaves the trail with the DirtFactor of the pulling worker");
    entered->setDirt(0.0); creature.mIsBeingDragged = false; creature.mDragDirtFactor = 1.0;
    struct Load : GameEntity { GameEntityType getObjectType() const { return GameEntityType::other; } } load;
    creature.mCarriedEntity = &load; creature.dirtyEnteredTile(entered);
    expectNear(entered->getDirt(), 0.1448 * 1.0 * 1.5, "a worker with a load leaves a full trail");
}

int main()
{
    loadConfig();
    checkTile();
    checkStages();
    checkPileCleaningRule();
    checkWorkPoints();
    checkUseDirt();
    checkPiles();
    checkMood();
    checkUrgeAndCreatureDirt();
    if(failures == 0) std::cout << "dirt rules ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

# The statements of the fight blocks as they stand in Creature::doUpkeep and Creature::takeDamage
fight_start = creature_cpp.index('    ++mNbTurnsWithoutBattle;')
fight_end_text = 'mFoughtSinceFightEnd = false;\n    }'
fight_block = creature_cpp[fight_start:creature_cpp.index(fight_end_text, fight_start) + len(fight_end_text)]
ko_start = creature_cpp.index('    if(!wasKo && getIsOnServerMap() && (isKoTemp() || isKoDeath()))')
ko_end_text = 'mDirtKoThisFight = true;\n    }'
ko_block = creature_cpp[ko_start:creature_cpp.index(ko_end_text, ko_start) + len(ko_end_text)]

mood_start = mood_cpp.index('bool canFeelDirt(const Creature& creature)')
mood_end = mood_cpp.index('\n}\n\n//! \\brief Returns the name under which this modifier')
mood_functions = mood_cpp[mood_start:mood_end]

replacements = {
    '@@CONFIG@@': config_table,
    '@@MAXDIRT@@': re.search(r'^const double Tile::MAX_DIRT = [0-9.]+;$', tile_cpp, re.M).group(0),
    '@@TILE_FUNCTIONS@@': '\n'.join(extract(tile_cpp, h) for h in [
        'bool Tile::canCarryDirt() const', 'void Tile::addDirt(double amount)', 'void Tile::cleanDirt(double amount)',
        'void Tile::setDirt(double dirt)']),
    '@@ROOM_FUNCTIONS@@': '\n'.join(extract(room_cpp, h) for h in [
        'bool Room::isCleanableByWorkers() const', 'void Room::addUseDirt(', 'double Room::getDirtMean() const', 'uint32_t Room::getDirtStage() const',
        'double Room::getDirtOutputFactor() const', 'double Room::getDirtStageFactor(']),
    '@@SEARCH_FUNCTIONS@@': extract(search_cpp, 'bool CreatureActionSearchDirtToClean::isPileCleanable('),
    '@@WORKPOINT_FUNCTIONS@@': extract(library_cpp, 'static int32_t takeWholeWorkPoints(').replace('takeWholeWorkPoints', 'libraryTakeWholeWorkPoints') + '\n' +
        extract(workshop_cpp, 'static int32_t takeWholeWorkPoints(').replace('takeWholeWorkPoints', 'workshopTakeWholeWorkPoints'),
    '@@PILE_FUNCTIONS@@': '\n'.join(extract(pile_cpp, h) for h in [
        'void DirtPileEntity::doUpkeep()', 'DirtPileEntity* DirtPileEntity::getEntityOnTile(',
        'DirtPileEntity* DirtPileEntity::createOnTile(', 'bool DirtPileEntity::cleanBy(']),
    '@@CREATURE_FUNCTIONS@@': '\n'.join(extract(creature_cpp, h) for h in [
        'void Creature::foodEaten(double val)', 'void Creature::increaseUrge(double value)', 'void Creature::setUrge(double val)',
        'void Creature::increaseCreatureDirt(double value)', 'void Creature::setCreatureDirt(double val)',
        'void Creature::upkeepCreatureDirt()', 'void Creature::dirtyEnteredTile(Tile* tile)']) + '\nvoid Creature::washed() { mCreatureDirt = 0.0; }',
    '@@FIGHT_END_BLOCK@@': fight_block,
    '@@KO_BLOCK@@': ko_block,
    '@@MOOD_FUNCTIONS@@': mood_functions,
    '@@MOOD_COMPUTE@@': extract(mood_cpp, 'int32_t CreatureMoodDirt::computeMood(const Creature& creature) const'),
}
for token, text in replacements.items():
    assert token in probe, token
    probe = probe.replace(token, text)
# The washed() hook is one line in the source; assert it still sets the dirt to 0
assert 'void Creature::washed()\n{\n    mCreatureDirt = 0.0;\n}' in creature_cpp.replace('\r\n', '\n')
# The real code reads the trail share through the divisor and the carried entity / dragged flag
assert 'mIsBeingDragged' in creature_cpp and 'CREATURE_DIRT_SHARE_DIVISOR' in creature_cpp

with tempfile.TemporaryDirectory(prefix='odp-dirt-rules-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('dirt rules ok')
