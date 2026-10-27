"""Tavern in saves and packets: the [Thirst] block of a creature, the packet fields of the thirst state and the lines of
the tavern room stream, including a running game and a knocked-out loser.

The real functions are cut out of the sources and run against small stubs:
  Creature    the writing statement and the reading block of the optional "[Thirst] ... [/Thirst]" block (round trips,
              any order with the [Needs] block, an old creature line without the block, broken blocks, a type without
              thirst stays at 0), exportThirstStateToPacket / importThirstStateFromPacket
  RoomTavern  exportToStream / importFromStream with the helper functions of the stream: TavernPayer, Innkeeper, Counter,
              Spot (all states, also the short old form) and Game lines (all three kinds, the turn, the slaps taken),
              a running game and a knocked-out loser keep their remaining turns, lines in any order, an old room without
              the lines loads, the next token of the stream is put back, broken lines are refused
The packet order, the notification types and the place where a guest is bound again after loading are checked on the
source text.

Calls (from the repository root):
  python source/tests/check_tavern_streams.py

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


# Returns the line of a text that holds a declaration (found by a regular expression).
def find_line(text, pattern):
    match = re.search(pattern, text, re.M)
    assert match is not None, pattern
    return match.group(0)


creature_cpp = read('source/entities/Creature.cpp')
room_cpp = read('source/rooms/RoomTavern.cpp')
room_h = read('source/rooms/RoomTavern.h')

# ---- Source wiring -----------------------------------------------------------------------------------------------
# The thirst block is written after the needs block, in the same function, and read in the same token loop
export_text = extract(creature_cpp, 'void Creature::exportToStream(')
assert export_text.index('NEEDS_SAVE_OPEN') < export_text.index('THIRST_SAVE_OPEN'), 'the thirst block follows the needs block'
assert creature_cpp.count('if(appearanceToken == THIRST_SAVE_OPEN)') == 1
# The full packet and the update packet retain the owner-only infirmary mood before urge, creature dirt and thirst; the update packet sends
# zeros to the seats that do not own the creature (the same number of fields)
full_packet = extract(creature_cpp, 'void Creature::exportToPacket(')
assert re.search(r'os << mGoldCarried;\s*exportItemsToPacket\(os, seat\);\s*os << \(seat == getSeat\(\) \? mInfirmaryMood : 0\.0\);\s*os << mUrge;\s*os << mCreatureDirt;\s*exportThirstStateToPacket\(os\);', full_packet)
update_packet = extract(creature_cpp, 'void Creature::exportToPacketForUpdate(') if 'void Creature::exportToPacketForUpdate(' in creature_cpp else None
if update_packet is None:
    update_start = creature_cpp.index('os << mGoldCarried;\n    if(seat == getSeat())')
    update_packet = creature_cpp[update_start:creature_cpp.index('\n}\n', update_start)]
assert 'exportThirstStateToPacket(os);' in update_packet and update_packet.count('os << 0.0;') == 6, \
    'the update packet sends urge, dirt and the four thirst fields as zeros to other seats'
thirst_export = extract(creature_cpp, 'void Creature::exportThirstStateToPacket(')
assert re.findall(r'os << (m\w+);', thirst_export) == ['mThirst', 'mTavernMood', 'mDrunk', 'mHangoverTurns']
assert creature_cpp.count('importThirstStateFromPacket(is);') == 2, 'full and update packet read the thirst state'
for notification, names in (('source/network/ServerNotification.h', ('tavernWindow', 'tavernPayer', 'infirmaryWindow', 'infirmarySettings', 'ghostRoomSettings')),
                            ('source/network/ClientNotification.h', ('askTavernWindow', 'askTavernPayer', 'askInfirmaryWindow', 'askInfirmarySettings', 'askGhostRoomSettings'))):
    text = read(notification)
    enum_body = text[text.index('enum class '):text.index('};', text.index('enum class '))]
    tail = [w for w in re.findall(r'^\s*(\w+),?\s*(?://.*)?$', enum_body, re.M) if w not in ('enum', 'class')][-5:]
    assert tail == list(names), notification + ' must end with ' + ', '.join(names) + ', found ' + ', '.join(tail)
for path, names in (('source/network/ServerNotification.cpp', ('tavernWindow', 'tavernPayer')),
                    ('source/network/ClientNotification.cpp', ('askTavernWindow', 'askTavernPayer'))):
    for name in names:
        assert 'return "' + name + '";' in read(path), name + ' has no typeString'
assert 'InnkeeperEntity' in read('source/entities/EntityLoading.cpp') or 'innkeeperEntity' in read('source/entities/EntityLoading.cpp'), \
    'the innkeeper is loaded like the other room figures'
# A saved guest is bound again by name: the use of the room takes its saved place, a missing partner ends the game
add_user = extract(room_cpp, 'bool RoomTavern::addCreatureUsingRoom(')
assert 'mPendingSpots.find(creature->getName())' in add_user and 'mPendingSpots.erase(pending);' in add_user
resume = extract(room_cpp, 'void RoomTavern::resumeLoadedGuests(')
assert 'getGameMap()->getCreature(' in resume and 'CreatureActionUseRoom' in resume
assert 'mGames[game.mTileA] = game;' in resume and 'game.mTurnsLeft = saved.mTurnsLeft;' in resume and 'game.mTurnIsA = saved.mTurnIsA;' in resume
assert 'game.mSlapsTakenA = saved.mSlapsTakenA;' in resume and 'game.mSlapsTakenB = saved.mSlapsTakenB;' in resume
# A load never resets a drink, a game or a thirst: the loading code names no reset of the thirst state
assert 'mThirst = 0' not in extract(creature_cpp, 'bool Creature::importFromStream(')

# ---- Probe -------------------------------------------------------------------------------------------------------
probe = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#define OD_LOG_WRN(x) do { } while(0)
#define OD_LOG_ERR(x) do { } while(0)

static int failures = 0;
static void expect(bool ok, const std::string& what) { if(!ok) { ++failures; std::cout << "FAIL: " << what << std::endl; } }
static void expectNear(double a, double b, const std::string& what)
{ if(std::fabs(a - b) > 1e-9) { ++failures; std::cout << "FAIL: " << what << " got " << a << " expected " << b << std::endl; } }
#define OD_ASSERT_TRUE(x) expect(static_cast<bool>(x), "packet read")

// A packet: values are written and read in the same order
struct ODPacket
{
    std::stringstream data;
    template<typename T> ODPacket& operator<<(const T& v) { data << v << ' '; return *this; }
    template<typename T> ODPacket& operator>>(T& v) { data >> v; return *this; }
    operator bool() const { return !data.fail(); }
};

struct InnkeeperEntity {};
struct CreatureDefinition
{
    bool thirsty;
    explicit CreatureDefinition(bool t) : thirsty(t) {}
    bool hasThirst() const { return thirsty; }
};
static const double THIRST_STATE_MAX = 100.0;
static const double NEED_MAX = 100.0;
@@STRINGS@@

struct Creature
{
    CreatureDefinition* mDefinition;
    std::string mName;
    double mUrge, mCreatureDirt, mThirst, mTavernMood, mTavernMoodTurns, mDrunk, mHangoverTurns;
    bool mVomited;
    Creature(const std::string& name, CreatureDefinition* def) : mDefinition(def), mName(name), mUrge(0.0), mCreatureDirt(0.0),
        mThirst(0.0), mTavernMood(0.0), mTavernMoodTurns(0.0), mDrunk(0.0), mHangoverTurns(0.0), mVomited(false) {}
    const std::string& getName() const { return mName; }
    void setUrge(double v) { mUrge = std::min(100.0, std::max(0.0, v)); }
    void setCreatureDirt(double v) { mCreatureDirt = std::min(100.0, std::max(0.0, v)); }
    void setVomited(bool vomited) { mVomited = vomited; }
    void setThirst(double val);
    void setDrunk(double val);
    void setHangoverTurns(double turns);
    void addTavernMood(double points, double turns);
    void exportThirstStateToPacket(ODPacket& os) const;
    void importThirstStateFromPacket(ODPacket& is);
    void writeBlocks(std::ostream& os) const;
    bool readBlocks(std::istream& is);
};
@@CREATURE_FUNCTIONS@@
void Creature::writeBlocks(std::ostream& os) const
{
@@NEEDS_WRITE@@
@@THIRST_WRITE@@
}
bool Creature::readBlocks(std::istream& is)
{
    std::string appearanceToken;
    while(is >> appearanceToken)
    {
@@NEEDS_READ@@

@@THIRST_READ@@
    }
    return true;
}

// ---- The tavern room
struct Tile
{
    int x, y;
    Tile(int ax, int ay) : x(ax), y(ay) {}
    int getX() const { return x; } int getY() const { return y; }
};
struct GameMap
{
    int sizeX, sizeY; std::vector<Tile> tiles;
    GameMap(int x, int y) : sizeX(x), sizeY(y) { for(int yy = 0; yy < y; ++yy) for(int xx = 0; xx < x; ++xx) tiles.push_back(Tile(xx, yy)); }
    Tile* getTile(int x, int y) { return ((x < 0) || (y < 0) || (x >= sizeX) || (y >= sizeY)) ? nullptr : &tiles[y * sizeX + x]; }
};
// The stream data of the base room is a single word here
struct Room
{
    GameMap* mMap; std::vector<Tile*> mCoveredTiles;
    Room(GameMap* map) : mMap(map) {}
    virtual ~Room() {}
    GameMap* getGameMap() const { return mMap; }
    virtual void exportToStream(std::ostream& os) const { os << "RoomData" << std::endl; }
    virtual bool importFromStream(std::istream& is) { std::string word; return (is >> word) && (word == "RoomData"); }
};
@@ROOM_TYPES@@
@@ROOM_HELPERS@@
class RoomTavern : public Room
{
public:
    RoomTavern(GameMap* gameMap) : Room(gameMap), mPayer(TavernPayer::keeper), mCounterTile(nullptr), mInnkeeper(nullptr) {}
    void exportToStream(std::ostream& os) const override;
    bool importFromStream(std::istream& is) override;
    TavernPayer mPayer;
    Tile* mCounterTile;
    InnkeeperEntity* mInnkeeper;
    std::map<Tile*, RoomTavernSpot> mSpots;
    std::map<Tile*, RoomTavernGame> mGames;
    std::map<std::string, RoomTavernPendingSpot> mPendingSpots;
    std::vector<RoomTavernPendingGame> mPendingGames;
};
@@ROOM_FUNCTIONS@@

static CreatureDefinition thirstyType(true);
static CreatureDefinition dryType(false);

static void checkThirstBlock()
{
    // A creature without any thirst state writes no block, and an old creature line loads with 0 everywhere
    Creature quiet("Quiet", &thirstyType);
    std::stringstream none; quiet.writeBlocks(none);
    expect(none.str().empty(), "no block for a creature without needs and thirst");
    Creature old("Old", &thirstyType); std::stringstream oldSave("Mana=5");
    expect(old.readBlocks(oldSave) && old.mThirst == 0.0 && old.mDrunk == 0.0 && old.mHangoverTurns == 0.0 && old.mTavernMoodTurns == 0.0,
           "an old creature line without the block loads with 0 everywhere");

    // Full round trip of every value
    Creature drunk("Drunk", &thirstyType);
    drunk.mThirst = 42.5; drunk.mTavernMood = -5.0; drunk.mTavernMoodTurns = 130.0; drunk.mDrunk = 77.25; drunk.mVomited = true; drunk.mHangoverTurns = 200.0;
    std::stringstream out; drunk.writeBlocks(out);
    expect(out.str().find("[Thirst]") != std::string::npos && out.str().find("[/Thirst]") != std::string::npos, "the thirst block is written");
    Creature loaded("Loaded", &thirstyType); std::stringstream in(out.str());
    expect(loaded.readBlocks(in), "the block is read");
    expectNear(loaded.mThirst, 42.5, "thirst round trip"); expectNear(loaded.mTavernMood, -5.0, "tavern mood round trip");
    expectNear(loaded.mTavernMoodTurns, 130.0, "tavern mood turns round trip"); expectNear(loaded.mDrunk, 77.25, "drunkenness round trip");
    expect(loaded.mVomited, "vomited round trip"); expectNear(loaded.mHangoverTurns, 200.0, "hangover round trip");

    // Each value alone is enough to write the block
    Creature onlyHangover("H", &thirstyType); onlyHangover.mHangoverTurns = 10.0;
    std::stringstream hangoverOut; onlyHangover.writeBlocks(hangoverOut);
    Creature hangoverLoaded("H2", &thirstyType); std::stringstream hangoverIn(hangoverOut.str());
    expect(hangoverLoaded.readBlocks(hangoverIn) && hangoverLoaded.mHangoverTurns == 10.0, "only the hangover is saved and loaded");
    Creature onlyVomit("V", &thirstyType); onlyVomit.mVomited = true;
    std::stringstream vomitOut; onlyVomit.writeBlocks(vomitOut);
    Creature vomitLoaded("V2", &thirstyType); std::stringstream vomitIn(vomitOut.str());
    expect(vomitLoaded.readBlocks(vomitIn) && vomitLoaded.mVomited, "only the vomit mark is saved and loaded");

    // With the needs block, in both orders, and with an unrelated block in between
    Creature both("Both", &thirstyType); both.mUrge = 37.5; both.mCreatureDirt = 12.25; both.mThirst = 80.0;
    std::stringstream bothOut; both.writeBlocks(bothOut);
    expect(bothOut.str().find("[Needs]") < bothOut.str().find("[Thirst]"), "the thirst block follows the needs block");
    Creature bothLoaded("Both2", &thirstyType); std::stringstream bothIn(bothOut.str());
    expect(bothLoaded.readBlocks(bothIn) && bothLoaded.mUrge == 37.5 && bothLoaded.mCreatureDirt == 12.25 && bothLoaded.mThirst == 80.0, "needs then thirst");
    Creature reversed("Rev", &thirstyType); std::stringstream reversedIn("[Thirst] 10 0 0 0 0 0 [/Thirst] [Needs] 20 30 [/Needs]");
    expect(reversed.readBlocks(reversedIn) && reversed.mThirst == 10.0 && reversed.mUrge == 20.0 && reversed.mCreatureDirt == 30.0, "thirst then needs");

    // Broken blocks are refused, loaded values are clamped
    Creature cut("Cut", &thirstyType); std::stringstream cutIn("[Thirst] 10 0 0 0 0");
    expect(!cut.readBlocks(cutIn), "a block without its end tag is refused");
    Creature wrong("Wrong", &thirstyType); std::stringstream wrongIn("[Thirst] 10 0 0 0 0 0 [/Needs]");
    expect(!wrong.readBlocks(wrongIn), "a block with a wrong end tag is refused");
    Creature clamp("Clamp", &thirstyType); std::stringstream clampIn("[Thirst] 500 0 0 -4 0 -9 [/Thirst]");
    expect(clamp.readBlocks(clampIn) && clamp.mThirst == 100.0 && clamp.mDrunk == 0.0 && clamp.mHangoverTurns == 0.0, "loaded values are clamped");

    // A type that cannot get thirsty stays at 0 (no hunger, no thirst): the reader keeps the value, the statement of
    // Creature::setupDefinition (checked in the python part) clears it once the definition is known
    Creature dry("Dry", &dryType); std::stringstream dryIn("[Thirst] 90 0 0 0 0 0 [/Thirst]");
    expect(dry.readBlocks(dryIn), "a block of a type without thirst is read");
    if(!dry.mDefinition->hasThirst())
        dry.mThirst = 0.0;
    expect(dry.mThirst == 0.0, "a type without thirst stays at 0");

    // Packet fields
    ODPacket packet; drunk.exportThirstStateToPacket(packet);
    Creature fromPacket("P", &thirstyType); fromPacket.importThirstStateFromPacket(packet);
    expectNear(fromPacket.mThirst, 42.5, "packet thirst"); expectNear(fromPacket.mTavernMood, -5.0, "packet tavern mood");
    expectNear(fromPacket.mDrunk, 77.25, "packet drunkenness"); expectNear(fromPacket.mHangoverTurns, 200.0, "packet hangover");
    expect(fromPacket.mTavernMoodTurns == 0.0 && !fromPacket.mVomited, "the timer and the vomit mark are not sent");
}

static std::string exportRoom(const RoomTavern& room)
{
    std::stringstream out; room.exportToStream(out); return out.str();
}

static void checkRoomStream()
{
    GameMap map(10, 10);
    Creature a("Anna", &thirstyType), b("Bert", &thirstyType), c("Cleo", &thirstyType), d("Dirk", &thirstyType);
    RoomTavern room(&map);
    for(int i = 1; i < 6; ++i) room.mCoveredTiles.push_back(map.getTile(i, 2));
    room.mPayer = TavernPayer::creature;
    room.mCounterTile = map.getTile(1, 2);
    room.mInnkeeper = reinterpret_cast<InnkeeperEntity*>(0x10);
    // A guest that drinks its third beer, a loser lying on the floor on its way to bed, and two running games
    room.mSpots.insert(std::make_pair(map.getTile(2, 2), RoomTavernSpot(&a)));
    RoomTavernSpot& drinking = room.mSpots.find(map.getTile(2, 2))->second;
    drinking.mState = TavernGuestState::drinking; drinking.mTurnsLeft = 3; drinking.mDrinks = 2;
    room.mSpots.insert(std::make_pair(map.getTile(3, 2), RoomTavernSpot(&b)));
    RoomTavernSpot& lying = room.mSpots.find(map.getTile(3, 2))->second;
    lying.mState = TavernGuestState::ko; lying.mTurnsLeft = 17; lying.mSleepAfter = true;
    RoomTavernGame duel;
    duel.mKind = TavernGameKind::slapDuel; duel.mTileA = map.getTile(4, 2); duel.mTileB = map.getTile(5, 2);
    duel.mCreatureA = &c; duel.mCreatureB = &d; duel.mTurnsLeft = 19; duel.mSlapsTakenA = 2; duel.mSlapsTakenB = 1; duel.mTurnIsA = false;
    room.mGames[duel.mTileA] = duel;
    RoomTavernGame dice;
    dice.mKind = TavernGameKind::dice; dice.mTileA = map.getTile(2, 4); dice.mTileB = map.getTile(3, 4);
    dice.mCreatureA = &a; dice.mCreatureB = &b; dice.mTurnsLeft = 5; dice.mTurnIsA = true;
    room.mGames[dice.mTileA] = dice;

    std::string text = exportRoom(room);
    expect(text.find("TavernPayer 1") != std::string::npos, "the payer is written");
    expect(text.find("Counter 1 2") != std::string::npos && text.find("Innkeeper 1 2") != std::string::npos, "counter and innkeeper are written");
    expect(text.find("Spot 3 2 Bert ko 17 0 1") != std::string::npos, "a lying loser keeps its remaining turns: " + text);
    expect(text.find("Spot 2 2 Anna drinking 3 2 0") != std::string::npos, "a drinking guest keeps its turns and drinks");
    expect(text.find("Game 2 4 2 5 2 Cleo Dirk 19 2 1 1") != std::string::npos, "a running duel keeps the turns, hits and whose turn it is: " + text);

    // Load: pending places and games hold every value, the next token of the stream is still there
    GameMap map2(10, 10);
    RoomTavern loaded(&map2);
    for(int i = 1; i < 6; ++i) loaded.mCoveredTiles.push_back(map2.getTile(i, 2));
    std::stringstream in(text + "NextRoom 5");
    expect(loaded.importFromStream(in), "the room stream is read");
    std::string next; in >> next; expect(next == "NextRoom", "the next token is put back, got " + next);
    expect(loaded.mPayer == TavernPayer::creature, "payer round trip");
    expect(loaded.mCounterTile == map2.getTile(1, 2), "counter round trip");
    expect(loaded.mPendingSpots.size() == 2, "two saved places");
    std::map<std::string, RoomTavernPendingSpot>::iterator spot = loaded.mPendingSpots.find("Bert");
    if(spot != loaded.mPendingSpots.end())
    {
        expect(spot->second.mState == TavernGuestState::ko && spot->second.mTurnsLeft == 17 && spot->second.mSleepAfter &&
               spot->second.mTile == map2.getTile(3, 2), "the knocked-out loser lies for the remaining turns and goes to bed");
    }
    else expect(false, "Bert has a saved place");
    spot = loaded.mPendingSpots.find("Anna");
    if(spot != loaded.mPendingSpots.end())
        expect(spot->second.mState == TavernGuestState::drinking && spot->second.mTurnsLeft == 3 && spot->second.mDrinks == 2 && !spot->second.mSleepAfter, "drinking state round trip");
    else expect(false, "Anna has a saved place");
    expect(loaded.mPendingGames.size() == 2, "two saved games");
    if(loaded.mPendingGames.size() == 2)
    {
        const RoomTavernPendingGame& g = loaded.mPendingGames[0];
        expect(g.mKind == TavernGameKind::slapDuel && g.mNameA == "Cleo" && g.mNameB == "Dirk" && g.mTurnsLeft == 19 && g.mSlapsTakenA == 2 &&
               g.mSlapsTakenB == 1 && !g.mTurnIsA && g.mTileA == map2.getTile(4, 2) && g.mTileB == map2.getTile(5, 2), "slap duel round trip");
        const RoomTavernPendingGame& h = loaded.mPendingGames[1];
        expect(h.mKind == TavernGameKind::dice && h.mTurnIsA && h.mTurnsLeft == 5 && h.mNameA == "Anna" && h.mNameB == "Bert", "dice game round trip");
    }
    // Exporting the loaded room again is not possible without the creatures, but the stream of an unchanged room is stable
    RoomTavern empty(&map); empty.mCoveredTiles.push_back(map.getTile(1, 2)); empty.mCounterTile = map.getTile(1, 2);
    std::string emptyText = exportRoom(empty);
    GameMap map3(10, 10); RoomTavern emptyLoaded(&map3); emptyLoaded.mCoveredTiles.push_back(map3.getTile(1, 2));
    std::stringstream emptyIn(emptyText);
    expect(emptyLoaded.importFromStream(emptyIn) && exportRoom(emptyLoaded) == emptyText, "an empty tavern keeps its stream");

    // Lines in any order, the short old Spot form, an old room without any tavern line
    GameMap map4(10, 10); RoomTavern shuffled(&map4); for(int i = 1; i < 6; ++i) shuffled.mCoveredTiles.push_back(map4.getTile(i, 2));
    std::stringstream shuffledIn("RoomData\nGame 0 2 4 3 4 Anna Bert 4 0 0 0\nSpot 3 2 Cleo drinking 2\nCounter 3 2\nTavernPayer 0\nTail");
    expect(shuffled.importFromStream(shuffledIn), "lines in any order are read");
    expect(shuffled.mCounterTile == map4.getTile(3, 2) && shuffled.mPayer == TavernPayer::keeper, "counter and payer in any order");
    expect(shuffled.mPendingSpots.size() == 1 && shuffled.mPendingSpots["Cleo"].mDrinks == 0 && shuffled.mPendingSpots["Cleo"].mTurnsLeft == 2, "the short Spot form loads");
    expect(shuffled.mPendingGames.size() == 1 && shuffled.mPendingGames[0].mKind == TavernGameKind::armWrestling, "arm wrestling game loads");
    std::string tail; shuffledIn >> tail; expect(tail == "Tail", "the token after the lines is put back");
    GameMap map5(10, 10); RoomTavern oldRoom(&map5);
    std::stringstream oldIn("RoomData\nNextRoom 1");
    expect(oldRoom.importFromStream(oldIn) && oldRoom.mPayer == TavernPayer::keeper && oldRoom.mPendingSpots.empty() && oldRoom.mPendingGames.empty(), "an old room loads with the defaults");
    std::string oldNext; oldIn >> oldNext; expect(oldNext == "NextRoom", "the old room leaves its next token");
    GameMap map6(10, 10); RoomTavern atEnd(&map6); std::stringstream atEndIn("RoomData\n");
    expect(atEnd.importFromStream(atEndIn), "a room at the end of the stream loads");

    // Broken lines are refused
    GameMap map7(10, 10);
    const char* broken[] = {
        "RoomData\nTavernPayer 7\n", "RoomData\nGame 9 1 1 2 1 A B 4 0 0 0\n", "RoomData\nSpot 1 1 A sitting 3\n",
        "RoomData\nSpot 1 1 A drinking\n", "RoomData\nCounter 3\n", "RoomData\nGame 0 1 1 2 1 A B\n" };
    for(unsigned i = 0; i < sizeof(broken) / sizeof(broken[0]); ++i)
    {
        RoomTavern bad(&map7); std::stringstream badIn(broken[i]);
        expect(!bad.importFromStream(badIn), std::string("a broken line is refused: ") + broken[i]);
    }
}

int main()
{
    checkThirstBlock();
    checkRoomStream();
    if(failures == 0) std::cout << "tavern streams ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

strings = '\n'.join(find_line(creature_cpp, r'^static const std::string ' + name + r' = "[^"]+";$')
                    for name in ('NEEDS_SAVE_OPEN', 'NEEDS_SAVE_CLOSE', 'THIRST_SAVE_OPEN', 'THIRST_SAVE_CLOSE'))

needs_read_start = creature_cpp.index('        if(appearanceToken == NEEDS_SAVE_OPEN)')
needs_read_end = 'setCreatureDirt(loadedDirt);\n            continue;\n        }'
needs_read = creature_cpp[needs_read_start:creature_cpp.index(needs_read_end, needs_read_start) + len(needs_read_end)]
thirst_read_start = creature_cpp.index('        if(appearanceToken == THIRST_SAVE_OPEN)')
thirst_read_end = 'setHangoverTurns(loadedHangoverTurns);\n            continue;\n        }'
thirst_read = creature_cpp[thirst_read_start:creature_cpp.index(thirst_read_end, thirst_read_start) + len(thirst_read_end)]
# The definition is not resolved while a creature is read from a level or save: the reader must not call setThirst
# (it dereferences mDefinition and crashed the loading of the tavern test levels)
assert 'setThirst(' not in thirst_read, 'the thirst reader must not use setThirst before the definition is set'
assert 'if(!mDefinition->hasThirst())\n            mThirst = 0.0;' in creature_cpp, 'setupDefinition must clear the thirst of a type without thirst'
needs_write_start = creature_cpp.index('    if((mUrge > 0.0) || (mCreatureDirt > 0.0))\n        os << "\\t" << NEEDS_SAVE_OPEN')
needs_write = creature_cpp[needs_write_start:creature_cpp.index('\n', creature_cpp.index('NEEDS_SAVE_CLOSE;', needs_write_start))]
thirst_write_start = creature_cpp.index('    if((mThirst > 0.0) || (mTavernMood != 0.0)')
thirst_write = creature_cpp[thirst_write_start:creature_cpp.index('\n    }\n', thirst_write_start) + len('\n    }')]

creature_functions = '\n'.join(extract(creature_cpp, h) for h in [
    'void Creature::setThirst(', 'void Creature::setDrunk(', 'void Creature::setHangoverTurns(', 'void Creature::addTavernMood(',
    'void Creature::exportThirstStateToPacket(', 'void Creature::importThirstStateFromPacket('])

# The enums and structs of the room header, up to the class itself
types_start = room_h.index('//! \\brief What a guest of a tavern is doing on its place.')
payer_start = room_h.index('//! \\brief Who pays for the beer a tavern serves.')
types_end = room_h.index('//! \\brief A room where creatures quench their thirst.')
room_types = room_h[payer_start:types_end]
# The helpers of the stream (anonymous namespace functions and tags of the room source)
tags = '\n'.join(find_line(room_cpp, r'^const std::string STREAM_TAG_' + name + r' = "[^"]+";$')
                 for name in ('PAYER', 'INNKEEPER', 'COUNTER', 'SPOT', 'GAME'))
helpers = tags + '\n' + '\n'.join(extract(room_cpp, h) for h in [
    'std::string guestStateToString(', 'bool guestStateFromString(', 'bool readTileFromStream('])
room_functions = '\n'.join(extract(room_cpp, h) for h in ['void RoomTavern::exportToStream(', 'bool RoomTavern::importFromStream('])

replacements = {
    '@@STRINGS@@': strings,
    '@@CREATURE_FUNCTIONS@@': creature_functions,
    '@@NEEDS_WRITE@@': needs_write,
    '@@THIRST_WRITE@@': thirst_write,
    '@@NEEDS_READ@@': needs_read,
    '@@THIRST_READ@@': thirst_read,
    '@@ROOM_TYPES@@': 'struct Creature; struct Tile;\n' + room_types,
    '@@ROOM_HELPERS@@': helpers,
    '@@ROOM_FUNCTIONS@@': room_functions,
}
for token, text in replacements.items():
    assert token in probe, token
    probe = probe.replace(token, text)

with tempfile.TemporaryDirectory(prefix='odp-tavern-streams-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('tavern streams ok')
