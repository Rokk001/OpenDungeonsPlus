"""Lava spa in saves and packets: the [Spa] block of a creature, the packet fields of the spa state and the lines of the
spa room stream, including bathers in every state and the pool attendant in the middle of an act.

The real functions are cut out of the sources and run against small stubs:
  Creature    the writing statement and the reading block of the optional "[Spa] <spaMood> <relaxTurns> <mudTilesLeft> [/Spa]"
              block (round trips, any order with another block, an old creature line without the block, broken blocks, values
              limited like the setters limit them), exportSpaStateToPacket / importSpaStateFromPacket
  RoomSpa     exportToStream / importFromStream with the helper functions of the stream: SpaPayer, PoolAttendant (all nine
              states, with and without the optional fields) and SpaBathers lines (all three states, the jump flag, fractional
              turns), bathers that are done are not written, a loaded room that waits for its bathers writes them again,
              lines in any order, an old room without the lines loads, the next token of the stream is put back, broken
              lines are refused
The packet order, the entity loading of the attendant and the place where a bather is bound again after loading are
checked on the source text.

Calls (from the repository root):
  python source/tests/check_spa_streams.py

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
room_cpp = read('source/rooms/RoomSpa.cpp')
room_h = read('source/rooms/RoomSpa.h')

# ---- Source wiring -----------------------------------------------------------------------------------------------
# The spa block is written after the thirst block, in the same function, and read in the same token loop
export_text = extract(creature_cpp, 'void Creature::exportToStream(')
assert export_text.index('THIRST_SAVE_OPEN') < export_text.index('SPA_SAVE_OPEN'), 'the spa block follows the thirst block'
assert creature_cpp.count('if(appearanceToken == SPA_SAVE_OPEN)') == 1
# The full packet and the update packet end with the thirst state and the spa state; the update packet sends zeros to
# the seats that do not own the creature (the same number of fields: urge, dirt, four thirst fields, two spa fields)
full_packet = extract(creature_cpp, 'void Creature::exportToPacket(')
assert re.search(r'exportThirstStateToPacket\(os\);\s*exportSpaStateToPacket\(os\);\s*\}', full_packet)
update_start = creature_cpp.index('os << mGoldCarried;\n    exportItemsToPacket(os, seat);\n    if(seat == getSeat())')
update_packet = creature_cpp[update_start:creature_cpp.index('\n}\n', update_start)]
assert re.search(r'exportThirstStateToPacket\(os\);\s*exportSpaStateToPacket\(os\);', update_packet)
assert update_packet.count('os << 0.0;') == 8, 'urge, dirt, four thirst fields and two spa fields as zeros for other seats'
spa_export = extract(creature_cpp, 'void Creature::exportSpaStateToPacket(')
assert re.findall(r'os << (m\w+);', spa_export) == ['mSpaMood', 'mRelaxTurns']
assert creature_cpp.count('importSpaStateFromPacket(is);') == 2, 'full and update packet read the spa state'
for text in (extract(creature_cpp, 'void Creature::importFromPacket('), extract(creature_cpp, 'void Creature::updateFromPacket(')):
    assert re.search(r'importThirstStateFromPacket\(is\);\s*importSpaStateFromPacket\(is\);', text)
# The attendant is a saved entity of the room: loaded like the chickens, found by name
assert 'poolAttendantEntity' in read('source/entities/EntityLoading.cpp') or 'PoolAttendantEntity' in read('source/entities/EntityLoading.cpp')
assert 'poolAttendantEntity' in read('source/entities/GameEntityType.h')
assert 'poolAttendantEntity' in read('source/gamemap/GameMap.cpp'), 'the map finds the attendant by name'
# A saved bather is bound again by name: the use of the room takes its saved place
add_user = extract(room_cpp, 'bool RoomSpa::addCreatureUsingRoom(')
assert 'mPendingBathers.find(creature->getName())' in add_user and 'mPendingBathers.erase(pending);' in add_user
assert 'bather.mBlock = pending->second.mBlock;' in add_user and 'bather.mTurnsDone = pending->second.mTurnsDone;' in add_user
assert 'bather.mState = pending->second.mState;' in add_user and 'bather.mJump = pending->second.mJump;' in add_user
resume = extract(room_cpp, 'void RoomSpa::resumeLoadedBathers(')
assert 'getGameMap()->getCreature(' in resume and 'CreatureActionUseRoom' in resume
# A load never resets a bath: no spa value is set to zero in the loading code
assert 'mSpaMood = 0' not in extract(creature_cpp, 'bool Creature::importFromStream(')
# A running bath after loading does not pay or start again: a loaded bathing bather goes straight on
assert 'creature->setSpaBathing(true);' in add_user and 'bathe_anim' in add_user

# ---- Probe -------------------------------------------------------------------------------------------------------
probe = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
#include "RoomSpaLayout.h"
#include "PoolAttendantState.h"

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

struct ConfigManager
{
    static ConfigManager& getSingleton() { static ConfigManager instance; return instance; }
    double getRoomConfigDouble(const std::string& key) const { return (key == "SpaMoodMax") ? 1500.0 : 0.0; }
};
@@STRINGS@@

struct Creature
{
    std::string mName;
    double mSpaMood, mRelaxTurns; int32_t mSpaMudTilesLeft; uint32_t mJumpTurnsLeft;
    std::string mOtherBlock;
    explicit Creature(const std::string& name) : mName(name), mSpaMood(0.0), mRelaxTurns(0.0), mSpaMudTilesLeft(0), mJumpTurnsLeft(0) {}
    const std::string& getName() const { return mName; }
    uint32_t getJumpTurnsLeft() const { return mJumpTurnsLeft; }
    void setSpaMood(double val);
    void setRelaxTurns(double turns);
    void setSpaMudTilesLeft(int32_t tiles);
    void exportSpaStateToPacket(ODPacket& os) const;
    void importSpaStateFromPacket(ODPacket& is);
    // The writing statement of Creature::exportToStream for the spa block
    void writeBlocks(std::ostream& os) const
    {
@@SPA_WRITE@@
    }
    // The token loop of Creature::importFromStream, reduced to the spa block and one other block
    bool readBlocks(std::istream& is)
    {
        std::string appearanceToken;
        while(is >> appearanceToken)
        {
            if(appearanceToken == "[Other]")
            {
                std::string value, close;
                if(!(is >> value >> close) || (close != "[/Other]"))
                    return false;
                mOtherBlock = value;
                continue;
            }

@@SPA_READ@@

            return false;
        }
        return true;
    }
};
@@CREATURE_FUNCTIONS@@

// ---- Creature: block and packet
static void checkSpaBlock()
{
    // Round trip with fractions
    Creature a("a"); a.setSpaMood(812.5); a.setRelaxTurns(302.4); a.setSpaMudTilesLeft(2);
    std::ostringstream out; a.writeBlocks(out);
    expect(out.str() == "\t[Spa] 812.5 302.4 2 [/Spa]", "written block: " + out.str());
    Creature b("b"); std::istringstream in(out.str());
    expect(b.readBlocks(in), "block read");
    expectNear(b.mSpaMood, 812.5, "spa mood"); expectNear(b.mRelaxTurns, 302.4, "relaxation"); expect(b.mSpaMudTilesLeft == 2, "mud tiles");
    // Nothing set: no block (an old creature line is the same)
    Creature z("z"); std::ostringstream none; z.writeBlocks(none);
    expect(none.str().empty(), "no block when all values are 0");
    Creature old("old"); std::istringstream oldIn("");
    expect(old.readBlocks(oldIn) && old.mSpaMood == 0.0 && old.mRelaxTurns == 0.0 && old.mSpaMudTilesLeft == 0, "old line loads with zeros");
    // Each value alone writes the block
    Creature r("r"); r.setRelaxTurns(5.0); std::ostringstream o2; r.writeBlocks(o2); expect(!o2.str().empty(), "relaxation alone");
    Creature m("m"); m.setSpaMudTilesLeft(1); std::ostringstream o3; m.writeBlocks(o3); expect(!o3.str().empty(), "mud counter alone");
    Creature s("s"); s.setSpaMood(1.0); std::ostringstream o4; s.writeBlocks(o4); expect(!o4.str().empty(), "mood alone");
    // Any order with another block
    Creature c1("c1"); std::istringstream first("[Other] x [/Other] [Spa] 10 20 1 [/Spa]");
    expect(c1.readBlocks(first) && c1.mSpaMood == 10.0 && c1.mOtherBlock == "x", "spa block after another block");
    Creature c2("c2"); std::istringstream second("[Spa] 10 20 1 [/Spa] [Other] y [/Other]");
    expect(c2.readBlocks(second) && c2.mRelaxTurns == 20.0 && c2.mOtherBlock == "y", "spa block before another block");
    // Limited like the setters limit them
    Creature l("l"); std::istringstream limited("[Spa] 99999 -4 -3 [/Spa]");
    expect(l.readBlocks(limited) && l.mSpaMood == 1500.0 && l.mRelaxTurns == 0.0 && l.mSpaMudTilesLeft == 0, "values limited");
    // Broken blocks are refused
    const char* broken[] = { "[Spa] 1 2 [/Spa]", "[Spa] 1 2 3", "[Spa] 1 2 3 [/Other]", "[Spa] a b c [/Spa]", "[Spa]" };
    for(unsigned i = 0; i < sizeof(broken) / sizeof(broken[0]); ++i)
    {
        Creature x("x"); std::istringstream bad(broken[i]);
        expect(!x.readBlocks(bad), std::string("broken block refused: ") + broken[i]);
    }
    // Packet: the spa state keeps its fractions, in the order mood, relaxation
    Creature p("p"); p.setSpaMood(333.25); p.setRelaxTurns(17.75);
    ODPacket packet; p.exportSpaStateToPacket(packet);
    Creature q("q"); q.importSpaStateFromPacket(packet);
    expectNear(q.mSpaMood, 333.25, "packet mood"); expectNear(q.mRelaxTurns, 17.75, "packet relaxation");
    expect(packet.data.str() == "333.25 17.75 ", "two fields: " + packet.data.str());
}

// ---- Room stream
struct Player { bool human; bool getIsHuman() const { return human; } };
struct Seat { Player* player; Player* getPlayer() const { return player; } };
struct Room
{
    Room() : mSeat(nullptr) {}
    Seat* mSeat;
    Seat* getSeat() const { return mSeat; }
    void exportToStream(std::ostream& os) const { os << "RoomHead" << std::endl; }
    bool importFromStream(std::istream& is) { std::string head; return static_cast<bool>(is >> head) && head == "RoomHead"; }
};
@@ROOM_TYPES@@
@@ROOM_HELPERS@@

struct PoolAttendantEntity
{
    PoolAttendantSave save;
    void exportSaveData(PoolAttendantSave& out) const { out = save; }
};

class RoomSpa : public Room
{
public:
    RoomSpa() : mPayer(SpaPayer::keeper), mAttendant(nullptr), mPendingAttendant() {}
    SpaPayer mPayer; PoolAttendantEntity* mAttendant; RoomSpaPendingAttendant mPendingAttendant;
    std::vector<RoomSpaBather> mBathers; std::map<std::string, RoomSpaPendingBather> mPendingBathers;
    void exportToStream(std::ostream& os) const;
    bool importFromStream(std::istream& is);
};
@@ROOM_FUNCTIONS@@

static std::string exported(const RoomSpa& room) { std::ostringstream os; room.exportToStream(os); return os.str(); }

static void checkRoomStream()
{
    // A full room: the attendant mid-act, a bather in each state
    Creature reserved("Orc1"), jumping("Troll1"), bathing("Goblin1"), done("Spider1");
    PoolAttendantEntity attendant;
    attendant.save.mX = 12.5; attendant.save.mY = 8.25; attendant.save.mState = PoolAttendantState::dozing; attendant.save.mTurnsLeft = 7.5;
    attendant.save.mHasCannonball = true; attendant.save.mCannonballTurnsLeft = 99.5; attendant.save.mHasPlace = true;
    attendant.save.mPlaceX = 16; attendant.save.mPlaceY = 9;
    RoomSpa room; room.mPayer = SpaPayer::creature; room.mAttendant = &attendant;
    RoomSpaBather b1(&reserved); b1.mBlock.mX = 16; b1.mBlock.mY = 8; b1.mBlock.mWidth = 1; b1.mBlock.mHeight = 2; b1.mState = SpaBatherState::reserved; b1.mJump = true;
    jumping.mJumpTurnsLeft = 1;
    RoomSpaBather b2(&jumping); b2.mBlock.mX = 17; b2.mBlock.mY = 9; b2.mBlock.mWidth = 2; b2.mBlock.mHeight = 2; b2.mState = SpaBatherState::jumping; b2.mJump = true;
    RoomSpaBather b3(&bathing); b3.mBlock.mX = 18; b3.mBlock.mY = 8; b3.mState = SpaBatherState::bathing; b3.mTurnsDone = 12.5;
    RoomSpaBather b4(&done); b4.mBlock.mX = 16; b4.mBlock.mY = 10; b4.mState = SpaBatherState::bathing; b4.mTurnsDone = 71.5; b4.mDone = true;
    room.mBathers.push_back(b1); room.mBathers.push_back(b2); room.mBathers.push_back(b3); room.mBathers.push_back(b4);
    const std::string text = exported(room);
    expect(text.find("SpaPayer 1") != std::string::npos, "payer line");
    expect(text.find("PoolAttendant 12.5 8.25 doze 7.5 99.5 1 16 9") != std::string::npos, "attendant line: " + text);
    expect(text.find("SpaBathers 3") != std::string::npos, "three bathers, the one that is done is not written: " + text);
    expect(text.find("Orc1 16 8 1 2 reserved 0 1") != std::string::npos, "reserved bather line: " + text);
    expect(text.find("Troll1 17 9 2 2 jumping 1 1") != std::string::npos, "jumping bather line keeps the turns of the jump that are left");
    expect(text.find("Goblin1 18 8 1 1 bathing 12.5 0") != std::string::npos, "bathing bather line");
    expect(text.find("Spider1") == std::string::npos, "finished bath not written");

    // Load it back into a fresh room: the places wait for their creatures, the stream continues with the next token
    RoomSpa loaded; std::istringstream in(text + "NextThing 7\n");
    expect(loaded.importFromStream(in), "room stream read");
    expect(loaded.mPayer == SpaPayer::creature, "payer");
    expect(loaded.mPendingAttendant.mPresent && loaded.mPendingAttendant.mSave.mState == PoolAttendantState::dozing, "attendant state");
    expectNear(loaded.mPendingAttendant.mSave.mTurnsLeft, 7.5, "attendant turns left");
    expectNear(loaded.mPendingAttendant.mSave.mCannonballTurnsLeft, 99.5, "attendant cannonball turns");
    expect(loaded.mPendingAttendant.mSave.mHasPlace && loaded.mPendingAttendant.mSave.mPlaceX == 16 && loaded.mPendingAttendant.mSave.mPlaceY == 9, "attendant place");
    expectNear(loaded.mPendingAttendant.mSave.mX, 12.5, "attendant x"); expectNear(loaded.mPendingAttendant.mSave.mY, 8.25, "attendant y");
    expect(loaded.mPendingBathers.size() == 3, "three pending bathers");
    expect(loaded.mPendingBathers["Orc1"].mState == SpaBatherState::reserved && loaded.mPendingBathers["Orc1"].mBlock.mHeight == 2 && loaded.mPendingBathers["Orc1"].mJump, "reserved bather");
    expect(loaded.mPendingBathers["Troll1"].mState == SpaBatherState::jumping && loaded.mPendingBathers["Troll1"].mBlock.mWidth == 2, "jumping bather");
    expectNear(loaded.mPendingBathers["Goblin1"].mTurnsDone, 12.5, "bathing turns done");
    expect(loaded.mPendingBathers["Goblin1"].mState == SpaBatherState::bathing && !loaded.mPendingBathers["Goblin1"].mJump, "bathing bather");
    std::string next; int value = 0;
    expect(static_cast<bool>(in >> next >> value) && next == "NextThing" && value == 7, "the next token is put back");
    // One to one: a loaded room writes the same lines again before its creatures are bound
    expect(exported(loaded).find("SpaPayer 1") != std::string::npos, "payer written again");
    RoomSpa again; std::istringstream in2(exported(loaded));
    expect(again.importFromStream(in2) && again.mPendingBathers.size() == 3 && again.mPayer == SpaPayer::creature, "second round trip");

    // All attendant states, with and without the optional fields
    const PoolAttendantState states[] = { PoolAttendantState::sitting, PoolAttendantState::whistling, PoolAttendantState::towelWaving,
        PoolAttendantState::dozing, PoolAttendantState::climbingDown, PoolAttendantState::walkingToBoard, PoolAttendantState::jumping,
        PoolAttendantState::walkingBack, PoolAttendantState::climbingUp };
    for(unsigned i = 0; i < 9; ++i)
    {
        PoolAttendantEntity a; a.save.mState = states[i]; a.save.mTurnsLeft = 1.5 + i; a.save.mX = 3.0 + i; a.save.mY = 4.0;
        RoomSpa r; r.mAttendant = &a;
        RoomSpa back; std::istringstream is(exported(r));
        expect(back.importFromStream(is) && back.mPendingAttendant.mPresent && back.mPendingAttendant.mSave.mState == states[i], "attendant state " + std::to_string(i));
        expectNear(back.mPendingAttendant.mSave.mTurnsLeft, 1.5 + i, "attendant turns " + std::to_string(i));
    }
    // A short line (the first four values only) loads with new jump timers and without a place
    RoomSpa shortLine; std::istringstream shortIn("RoomHead\nPoolAttendant 3 4 sit 5\n");
    expect(shortLine.importFromStream(shortIn) && shortLine.mPendingAttendant.mPresent && !shortLine.mPendingAttendant.mSave.mHasCannonball
           && !shortLine.mPendingAttendant.mSave.mHasPlace, "short attendant line");
    // A bather line without the jump flag (old or hand written)
    RoomSpa noJump; std::istringstream noJumpIn("RoomHead\nSpaBathers 1\nOrc1 16 8 1 2 bathing 3\n");
    expect(noJump.importFromStream(noJumpIn) && noJump.mPendingBathers["Orc1"].mJump == false, "bather line without the jump flag");
    // Without a SpaPayer line the payer depends on the kind of seat: the computer lets the creatures pay
    Player computer; computer.human = false; Player human; human.human = true;
    Seat computerSeat; computerSeat.player = &computer; Seat humanSeat; humanSeat.player = &human;
    RoomSpa aiRoom; aiRoom.mSeat = &computerSeat; std::istringstream aiIn("RoomHead\n");
    expect(aiRoom.importFromStream(aiIn) && aiRoom.mPayer == SpaPayer::creature, "no payer line, computer seat: the creatures pay");
    RoomSpa humanRoom; humanRoom.mSeat = &humanSeat; std::istringstream humanIn("RoomHead\n");
    expect(humanRoom.importFromStream(humanIn) && humanRoom.mPayer == SpaPayer::keeper, "no payer line, human seat: the keeper pays");
    RoomSpa savedRoom; savedRoom.mSeat = &computerSeat; std::istringstream savedIn("RoomHead\nSpaPayer 0\n");
    expect(savedRoom.importFromStream(savedIn) && savedRoom.mPayer == SpaPayer::keeper, "a saved payer line wins over the seat kind");
    // A room that was saved before the spa (tiles only) loads with the defaults
    RoomSpa plain; std::istringstream plainIn("RoomHead\n");
    expect(plain.importFromStream(plainIn) && plain.mPayer == SpaPayer::keeper && !plain.mPendingAttendant.mPresent && plain.mPendingBathers.empty(), "old room loads with defaults");
    RoomSpa plainNext; std::istringstream plainNextIn("RoomHead\n[Room]\n");
    std::string token;
    expect(plainNext.importFromStream(plainNextIn) && static_cast<bool>(plainNextIn >> token) && token == "[Room]", "the next tag is put back");
    // Lines in any order
    RoomSpa shuffled; std::istringstream order("RoomHead\nSpaBathers 1\nOrc1 1 2 1 1 reserved 0\nPoolAttendant 1 2 sit 3\nSpaPayer 1\n");
    expect(shuffled.importFromStream(order) && shuffled.mPayer == SpaPayer::creature && shuffled.mPendingAttendant.mPresent && shuffled.mPendingBathers.size() == 1, "any order");
    // Broken lines are refused
    const char* broken[] = {
        "RoomHead\nSpaPayer 2\n", "RoomHead\nSpaPayer x\n", "RoomHead\nPoolAttendant 1 2 flying 3\n", "RoomHead\nPoolAttendant 1 2\n",
        "RoomHead\nSpaBathers 1\nOrc1 1 2 0 1 reserved 0\n", "RoomHead\nSpaBathers 1\nOrc1 1 2 1 1 swimming 0\n",
        "RoomHead\nSpaBathers 2\nOrc1 1 2 1 1 reserved 0\n", "RoomHead\nSpaBathers\n" };
    for(unsigned i = 0; i < sizeof(broken) / sizeof(broken[0]); ++i)
    {
        RoomSpa x; std::istringstream bad(broken[i]);
        expect(!x.importFromStream(bad), std::string("broken room stream refused: ") + broken[i]);
    }
}

int main()
{
    checkSpaBlock();
    checkRoomStream();
    if(failures == 0) std::cout << "spa streams ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

strings = '\n'.join(find_line(creature_cpp, r'^static const std::string ' + name + r' = "[^"]+";$')
                    for name in ('SPA_SAVE_OPEN', 'SPA_SAVE_CLOSE'))
spa_read_start = creature_cpp.index('        if(appearanceToken == SPA_SAVE_OPEN)')
spa_read_end = 'setSpaMudTilesLeft(loadedMudTilesLeft);\n            continue;\n        }'
spa_read = creature_cpp[spa_read_start:creature_cpp.index(spa_read_end, spa_read_start) + len(spa_read_end)]
spa_write_start = creature_cpp.index('    if((mSpaMood > 0.0) || (mRelaxTurns > 0.0) || (mSpaMudTilesLeft > 0))')
spa_write = creature_cpp[spa_write_start:creature_cpp.index('\n    }\n', spa_write_start) + len('\n    }')]
creature_functions = '\n'.join(extract(creature_cpp, h) for h in [
    'void Creature::setSpaMood(', 'void Creature::setRelaxTurns(', 'void Creature::setSpaMudTilesLeft(',
    'void Creature::exportSpaStateToPacket(', 'void Creature::importSpaStateFromPacket('])

types_start = room_h.index('//! \\brief Who pays for the bath a lava spa gives.')
types_end = room_h.index('//! \\brief A piece of the pool rim')
room_types = 'struct Creature; struct Tile;\n' + room_h[types_start:types_end]
tags = '\n'.join(find_line(room_cpp, r'^const std::string STREAM_TAG_' + name + r' = "[^"]+";$')
                 for name in ('PAYER', 'BATHERS', 'ATTENDANT'))
helpers = tags + '\n' + '\n'.join(extract(room_cpp, h) for h in [
    'std::string batherStateToString(', 'bool batherStateFromString(', 'void writeAttendantLine('])
room_functions = '\n'.join(extract(room_cpp, h) for h in ['void RoomSpa::exportToStream(', 'bool RoomSpa::importFromStream('])

replacements = {
    '@@STRINGS@@': strings,
    '@@CREATURE_FUNCTIONS@@': creature_functions,
    '@@SPA_WRITE@@': spa_write,
    '@@SPA_READ@@': spa_read,
    '@@ROOM_TYPES@@': room_types,
    '@@ROOM_HELPERS@@': helpers,
    '@@ROOM_FUNCTIONS@@': room_functions,
}
for token, text in replacements.items():
    assert token in probe, token
    probe = probe.replace(token, text)

with tempfile.TemporaryDirectory(prefix='odp-spa-streams-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', '/I' + str(root / 'source' / 'rooms'),
                    '/I' + str(root / 'source' / 'entities'), 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('spa streams ok')
