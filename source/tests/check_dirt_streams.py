"""Dirt in saves: the [Needs] block of a creature, the [Dirt] and [DirtPiles] sections and the old CleanOrder line of a room, which is read and ignored.

The real write and read functions are cut out of the sources and run against small stubs:
  MapHandler  writeDirtSections / readDirtSections (tile dirt and piles round trip, a level without the sections loads,
              the next section is left untouched)
  DirtPileEntity  exportToSaveStream / importFromSaveStream / kindToString / kindFromString
  Creature    the writing statement and the reading block of the optional "[Needs] urge dirt [/Needs]" block
  Room        skipLegacyCleanOrderLine (an old line is read and ignored, a missing line is not an error)
The order of the sections in the level file and the rooms that read the old line are checked on the source text.

Calls (from the repository root):
  python source/tests/check_dirt_streams.py

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


map_cpp = read('source/gamemap/MapHandler.cpp')
pile_cpp = read('source/entities/DirtPileEntity.cpp')
creature_cpp = read('source/entities/Creature.cpp')
room_cpp = read('source/rooms/Room.cpp')

# ---- Source wiring -----------------------------------------------------------------------------------------------
# The sections follow the gift boxes in the level file, in the same order when reading and writing, before the missiles
read_order = [map_cpp.index(t) for t in ('readGameEntity(gameMap, "GiftBoxEntity"', 'readDirtSections(gameMap, levelFile)', 'readGameEntity(gameMap, "Missiles"')]
assert read_order == sorted(read_order), 'level reading order: gift boxes, dirt sections, missiles'
write_order = [map_cpp.index(t) for t in ('levelFile << "[/GiftBoxEntity]" << std::endl;', 'writeDirtSections(levelFile, gameMap);', 'levelFile << "\\n[Missiles]\\n";')]
assert write_order == sorted(write_order), 'level writing order: gift boxes, dirt sections, missiles'
# Prison and torture rooms write no order line any more and skip an old one as the last item; the toilet writes nothing of its own
for path in ('source/rooms/RoomPrison.cpp', 'source/rooms/RoomTorture.cpp'):
    text = read(path)
    assert 'return skipLegacyCleanOrderLine(is);' in text and 'exportCleanOrder' not in text, path
assert 'skipLegacyCleanOrderLine' not in read('source/rooms/RoomToilet.cpp'), 'toilet reservations are rebuilt, not saved'
assert 'mCleanOrder' not in read('source/rooms/Room.h') and 'getCleanOrder' not in read('source/rooms/Room.h'), 'the clean order is gone'
# Creature: the needs block is written after the skill build (last), and read in the token loop
export_text = extract(creature_cpp, 'void Creature::exportToStream(')
assert export_text.index('SKILL_BUILD_MARKER') < export_text.index('NEEDS_SAVE_OPEN'), 'needs block comes after the skill block'

# ---- Probe -------------------------------------------------------------------------------------------------------
probe = r'''
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace Ogre { typedef float Real; struct Vector3 { Real x, y, z; Vector3() : x(0), y(0), z(0) {} Vector3(Real ax, Real ay, Real az) : x(ax), y(ay), z(az) {} }; }
#define OD_LOG_WRN(x) do { } while(0)
#define OD_LOG_ERR(x) do { } while(0)

static int failures = 0;
static void expect(bool ok, const std::string& what) { if(!ok) { ++failures; std::cout << "FAIL: " << what << std::endl; } }
static void expectNear(double a, double b, double eps, const std::string& what)
{ if(std::fabs(a - b) > eps) { ++failures; std::cout << "FAIL: " << what << " got " << a << " expected " << b << std::endl; } }

namespace Helper { int toInt(const std::string& s) { return std::atoi(s.c_str()); } std::string toString(int v) { return std::to_string(v); } }

enum class DirtPileKind { pile, blood, vomit };
struct GameMap; struct DirtPileEntity;
struct Tile
{
    int x, y; double dirt;
    Tile(int ax, int ay) : x(ax), y(ay), dirt(0.0) {}
    int getX() const { return x; } int getY() const { return y; }
    double getDirt() const { return dirt; }
    void setDirt(double d) { dirt = std::min(100.0, std::max(0.0, d)); }
};
enum class GameEntityType { dirtPileEntity, other };
struct RenderedMovableEntity
{
    virtual ~RenderedMovableEntity() {}
    virtual GameEntityType getObjectType() const { return GameEntityType::other; }
};
struct DirtPileEntity : public RenderedMovableEntity
{
    GameMap* mMap; DirtPileKind mKind; std::string mCreatureClass; double mDirtLeft, mAgeTurns; Ogre::Vector3 mPosition;
    DirtPileEntity(GameMap* map, DirtPileKind kind, const std::string& creatureClass)
      : mMap(map), mKind(kind), mCreatureClass(creatureClass), mDirtLeft(100.0), mAgeTurns(0.0) {}
    void restoreState(double dirtLeft, double ageTurns) { mDirtLeft = dirtLeft; mAgeTurns = ageTurns; }
    GameEntityType getObjectType() const { return GameEntityType::dirtPileEntity; }
    void addToGameMap();
    const Tile* getPositionTile() const;
    void exportToSaveStream(std::ostream& os) const;
    static bool importFromSaveStream(GameMap* gameMap, std::istream& is);
    static std::string kindToString(DirtPileKind kind);
    static bool kindFromString(const std::string& text, DirtPileKind& kind);
};
struct GameMap
{
    int sizeX, sizeY; std::vector<Tile> tiles; std::vector<DirtPileEntity*> piles; std::vector<RenderedMovableEntity*> rendereds;
    GameMap(int x, int y) : sizeX(x), sizeY(y) { for(int yy = 0; yy < y; ++yy) for(int xx = 0; xx < x; ++xx) tiles.push_back(Tile(xx, yy)); }
    int getMapSizeX() const { return sizeX; } int getMapSizeY() const { return sizeY; }
    Tile* getTile(int x, int y) { return ((x < 0) || (y < 0) || (x >= sizeX) || (y >= sizeY)) ? nullptr : &tiles[y * sizeX + x]; }
    const std::vector<RenderedMovableEntity*>& getRenderedMovableEntities() const { return rendereds; }
};
void DirtPileEntity::addToGameMap()
{
    mMap->piles.push_back(this);
    mMap->rendereds.push_back(this);
}
const Tile* DirtPileEntity::getPositionTile() const { return mMap->getTile(static_cast<int>(mPosition.x), static_cast<int>(mPosition.y)); }
@@PILE_STRINGS@@
@@PILE_FUNCTIONS@@

// The dirt sections of the map handler
namespace MapHandler {
@@MAP_FUNCTIONS@@
}

// The old clean order line of a room
struct Room
{
    bool skipLegacyCleanOrderLine(std::istream& is);
};
@@ROOM_FUNCTIONS@@

// The creature's needs block
struct Creature
{
    double mUrge, mCreatureDirt;
    Creature() : mUrge(0.0), mCreatureDirt(0.0) {}
    void setUrge(double v) { mUrge = std::min(100.0, std::max(0.0, v)); }
    void setCreatureDirt(double v) { mCreatureDirt = std::min(100.0, std::max(0.0, v)); }
    std::string getName() const { return "Creature"; }
    void writeNeeds(std::ostream& os) const;
    bool readNeeds(std::istream& is);
};
@@NEEDS_STRINGS@@
void Creature::writeNeeds(std::ostream& os) const
{
@@NEEDS_WRITE@@
}
bool Creature::readNeeds(std::istream& is)
{
    std::string appearanceToken;
    while(is >> appearanceToken)
    {
@@NEEDS_READ@@
    }
    return true;
}

// Like Helper::readFile(..., true): everything from a '#' to the end of the line is dropped before the level is parsed
static std::string withoutComments(const std::string& text)
{
    std::stringstream in(text); std::stringstream out; std::string line;
    while(std::getline(in, line)) out << line.substr(0, line.find('#')) << "\n";
    return out.str();
}

static std::string writeSections(GameMap& map)
{
    std::stringstream out;
    MapHandler::writeDirtSections(out, map);
    return out.str();
}

static void checkSections()
{
    GameMap map(8, 6);
    map.getTile(1, 1)->setDirt(12.5);
    map.getTile(7, 5)->setDirt(100.0);
    map.getTile(3, 4)->setDirt(0.0625);
    DirtPileEntity* pile = new DirtPileEntity(&map, DirtPileKind::pile, "Orc");
    pile->mPosition = Ogre::Vector3(2, 3, 0); pile->restoreState(60.0, 0.0); pile->addToGameMap();
    DirtPileEntity* blood = new DirtPileEntity(&map, DirtPileKind::blood, "DwarfWorker");
    blood->mPosition = Ogre::Vector3(4, 2, 0); blood->restoreState(100.0, 45.5); blood->addToGameMap();

    std::string text = writeSections(map);
    expect(text.find("[Dirt]") != std::string::npos && text.find("[/Dirt]") != std::string::npos, "the [Dirt] section is written");
    expect(text.find("[DirtPiles]") != std::string::npos && text.find("[/DirtPiles]") != std::string::npos, "the [DirtPiles] section is written");
    expect(text.find("[Dirt]") < text.find("[DirtPiles]"), "[Dirt] comes before [DirtPiles]");

    GameMap loaded(8, 6);
    std::stringstream in(withoutComments(text + "\n[Missiles]\n# next section\n[/Missiles]\n"));
    expect(MapHandler::readDirtSections(loaded, in), "the sections are read");
    expectNear(loaded.getTile(1, 1)->getDirt(), 12.5, 1e-4, "tile dirt round trip");
    expectNear(loaded.getTile(7, 5)->getDirt(), 100.0, 1e-4, "full dirt round trip");
    expectNear(loaded.getTile(3, 4)->getDirt(), 0.0625, 1e-4, "small dirt round trip");
    expectNear(loaded.getTile(0, 0)->getDirt(), 0.0, 1e-9, "tiles without dirt stay clean");
    expect(loaded.piles.size() == 2, "both piles are loaded");
    if(loaded.piles.size() == 2)
    {
        expect(loaded.piles[0]->mKind == DirtPileKind::pile && loaded.piles[0]->mCreatureClass == "Orc", "pile kind and creature class");
        expect(loaded.piles[0]->getPositionTile() == loaded.getTile(2, 3), "pile tile");
        expectNear(loaded.piles[0]->mDirtLeft, 60.0, 1e-4, "pile dirt left");
        expect(loaded.piles[1]->mKind == DirtPileKind::blood && loaded.piles[1]->mCreatureClass == "DwarfWorker", "blood kind and creature class");
        expectNear(loaded.piles[1]->mAgeTurns, 45.5, 1e-4, "blood age");
        expect(loaded.piles[1]->getPositionTile() == loaded.getTile(4, 2), "blood tile");
    }
    std::string next; in >> next;
    expect(next == "[Missiles]", "the next section is left for the next reader, got " + next);

    // A map without dirt writes nothing, and a level without the sections loads and is not consumed
    GameMap clean(4, 4);
    expect(writeSections(clean).empty(), "a clean map writes no dirt section");
    GameMap old(4, 4);
    std::stringstream oldLevel(withoutComments("[Missiles]\n# format\n[/Missiles]\n"));
    expect(MapHandler::readDirtSections(old, oldLevel), "an old level without the sections loads");
    std::string first; oldLevel >> first;
    expect(first == "[Missiles]", "an old level is not consumed, got " + first);
    // Only piles, no [Dirt]
    GameMap onlyPiles(4, 4);
    std::stringstream pilesOnly(withoutComments("[DirtPiles]\n# header\npile\tRat\t1\t1\t100\t0\n[/DirtPiles]\n[Missiles]"));
    expect(MapHandler::readDirtSections(onlyPiles, pilesOnly) && onlyPiles.piles.size() == 1, "only the pile section");
    // Broken input is refused
    GameMap broken(4, 4);
    std::stringstream badPile(withoutComments("[DirtPiles]\n# header\nslime\tRat\t1\t1\t100\t0\n[/DirtPiles]\n"));
    expect(!MapHandler::readDirtSections(broken, badPile), "an unknown pile kind is refused");
    std::stringstream cutOff("[Dirt]\n1 1 20\n");
    GameMap cut(4, 4);
    expect(!MapHandler::readDirtSections(cut, cutOff), "a section without its end tag is refused");
}

static void checkCleanOrder()
{
    // An old save or level has the line after the prison and torture data: it is read and ignored
    Room on; std::stringstream in("CleanOrder 1\nNextToken 5");
    expect(on.skipLegacyCleanOrderLine(in), "CleanOrder 1 is skipped");
    std::string after; in >> after; expect(after == "NextToken", "the token after the line is still there, got " + after);
    Room zero; std::stringstream inZero("CleanOrder 0\nNextToken 5");
    expect(zero.skipLegacyCleanOrderLine(inZero), "CleanOrder 0 is skipped");
    std::string afterZero; inZero >> afterZero; expect(afterZero == "NextToken", "the token after CleanOrder 0 is still there, got " + afterZero);
    // A new save has no line: the stream is put back for the next reader
    Room old; std::stringstream oldSave("NextToken 5");
    expect(old.skipLegacyCleanOrderLine(oldSave), "a save without the line loads");
    std::string next; oldSave >> next; expect(next == "NextToken", "the next token is still there, got " + next);
    Room empty; std::stringstream nothing("");
    expect(empty.skipLegacyCleanOrderLine(nothing), "an empty rest loads");
    Room bad; std::stringstream invalid("CleanOrder 2");
    expect(!bad.skipLegacyCleanOrderLine(invalid), "a value other than 0 and 1 is refused");
}

static void checkNeeds()
{
    Creature quiet;
    std::stringstream none; quiet.writeNeeds(none);
    expect(none.str().empty(), "a creature without needs writes no block");
    Creature needy; needy.mUrge = 37.5; needy.mCreatureDirt = 12.25;
    std::stringstream out; needy.writeNeeds(out);
    expect(out.str().find("[Needs]") != std::string::npos && out.str().find("[/Needs]") != std::string::npos, "the needs block is written");
    Creature loaded; std::stringstream in(out.str() + " [Items] 3");
    expect(loaded.readNeeds(in), "the needs block is read");
    expectNear(loaded.mUrge, 37.5, 1e-9, "urge round trip"); expectNear(loaded.mCreatureDirt, 12.25, 1e-9, "creature dirt round trip");
    Creature onlyDirt; onlyDirt.mCreatureDirt = 80.0; std::stringstream outDirt; onlyDirt.writeNeeds(outDirt);
    Creature loadedDirt; std::stringstream inDirt(outDirt.str());
    expect(loadedDirt.readNeeds(inDirt) && loadedDirt.mUrge == 0.0 && loadedDirt.mCreatureDirt == 80.0, "only dirt round trip");
    Creature oldCreature; std::stringstream oldSave("Mana=5");
    expect(oldCreature.readNeeds(oldSave) && oldCreature.mUrge == 0.0 && oldCreature.mCreatureDirt == 0.0, "an old creature line without the block loads with 0 / 0");
    Creature broken; std::stringstream cut("[Needs] 10 20");
    expect(!broken.readNeeds(cut), "a block without its end tag is refused");
    Creature wrongClose; std::stringstream wrong("[Needs] 10 20 [/Item]");
    expect(!wrongClose.readNeeds(wrong), "a block with a wrong end tag is refused");
    Creature clamp; std::stringstream big("[Needs] 500 -3 [/Needs]");
    expect(clamp.readNeeds(big) && clamp.mUrge == 100.0 && clamp.mCreatureDirt == 0.0, "loaded values are clamped to 0 - 100");
}

int main()
{
    checkSections();
    checkCleanOrder();
    checkNeeds();
    if(failures == 0) std::cout << "dirt streams ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

needs_read_start = creature_cpp.index('        if(appearanceToken == NEEDS_SAVE_OPEN)')
needs_read_end_text = 'setCreatureDirt(loadedDirt);\n            continue;\n        }'
needs_read = creature_cpp[needs_read_start:creature_cpp.index(needs_read_end_text, needs_read_start) + len(needs_read_end_text)]
needs_write_start = creature_cpp.index('    if((mUrge > 0.0) || (mCreatureDirt > 0.0))\n        os << "\\t" << NEEDS_SAVE_OPEN')
needs_write = creature_cpp[needs_write_start:creature_cpp.index('\n', creature_cpp.index('NEEDS_SAVE_CLOSE;', needs_write_start))]
needs_strings = '\n'.join(re.search(r'^static const std::string ' + name + r' = "[^"]+";$', creature_cpp, re.M).group(0)
                          for name in ('NEEDS_SAVE_OPEN', 'NEEDS_SAVE_CLOSE'))

pile_strings = '\n'.join(re.search(r'^[^\n]*' + name + r' = "[^"]*";$', pile_cpp, re.M).group(0)
                         for name in ('KIND_PILE_TEXT', 'KIND_BLOOD_TEXT', 'KIND_VOMIT_TEXT', 'NO_CLASS_TEXT'))

section_start = map_cpp.index('//! \\brief Section tag that opens the dirt of the tiles')
section_end = map_cpp.index('bool readGameEntity(GameMap& gameMap, const std::string& item')
map_part = map_cpp[section_start:section_end]
write_start = map_cpp.index('static void writeDirtSections(')
write_part = map_cpp[write_start:map_cpp.index('\n}\n', write_start) + 2]

replacements = {
    '@@PILE_STRINGS@@': pile_strings,
    '@@PILE_FUNCTIONS@@': '\n'.join(extract(pile_cpp, h) for h in [
        'std::string DirtPileEntity::kindToString(', 'bool DirtPileEntity::kindFromString(',
        'void DirtPileEntity::exportToSaveStream(', 'bool DirtPileEntity::importFromSaveStream(']),
    '@@MAP_FUNCTIONS@@': map_part + '\n' + write_part.replace('static void writeDirtSections(', 'void writeDirtSections('),
    '@@ROOM_FUNCTIONS@@': '\n'.join(extract(room_cpp, h) for h in [
        'bool Room::skipLegacyCleanOrderLine(']),
    '@@NEEDS_STRINGS@@': needs_strings,
    '@@NEEDS_WRITE@@': needs_write,
    '@@NEEDS_READ@@': needs_read,
}
for token, text in replacements.items():
    assert token in probe, token
    probe = probe.replace(token, text)

with tempfile.TemporaryDirectory(prefix='odp-dirt-streams-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('dirt streams ok')
