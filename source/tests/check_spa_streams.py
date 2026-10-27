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
# The full packet and the update packet end with the thirst state and the spa state; the spa fields (and in the update packet
# also urge, dirt and the thirst fields) are zeros for the seats that do not own the creature (the same number of fields)
full_packet = extract(creature_cpp, 'void Creature::exportToPacket(')
full_tail_start = full_packet.index('    exportThirstStateToPacket(os);\n    // The lava spa state is only sent to the own seat')
full_tail = full_packet[full_tail_start:full_packet.index('    os << mCorpseTurns')]
assert re.search(r'exportThirstStateToPacket\(os\);\s*//[^\n]*\n\s*//[^\n]*\n\s*if\(seat == getSeat\(\)\)\s*exportSpaStateToPacket\(os\);\s*else', full_tail)
assert full_tail.count('os << 0.0;') == 2
update_start = creature_cpp.index('os << mGoldCarried;\n    exportItemsToPacket(os, seat);\n    os << (seat == getSeat() ? mInfirmaryMood : 0.0);\n    if(seat == getSeat())')
update_packet = creature_cpp[update_start:creature_cpp.index('\n}\n', update_start)]
assert re.search(r'exportThirstStateToPacket\(os\);\s*exportSpaStateToPacket\(os\);', update_packet)
assert update_packet.count('os << 0.0;') == 8, 'urge, dirt, four thirst fields and two spa fields as zeros for other seats'
spa_export = extract(creature_cpp, 'void Creature::exportSpaStateToPacket(')
assert re.findall(r'os << (m\w+);', spa_export) == ['mSpaMood', 'mRelaxTurns']
assert creature_cpp.count('importSpaStateFromPacket(is);') == 2, 'full and update packet read the spa state'
for text in (extract(creature_cpp, 'void Creature::importFromPacket('), extract(creature_cpp, 'void Creature::updateFromPacket(')):
    assert re.search(r'importThirstStateFromPacket\(is\);\s*importSpaStateFromPacket\(is\);', text)
# The effect line of the creature page (relaxation, hangover) is bound to the own seat, not to the allies
profile_page = extract(creature_cpp, 'float Creature::fillProfilePage(')
assert 'const bool isOwn = (localSeat != nullptr) && (getSeat() == localSeat);' in profile_page
assert 'effectsText->setVisible(isOwn && !effects.empty());' in profile_page
# The restored acts and climbs go on at the reached turn of their clip instead of starting it again
attendant_restore = extract(read('source/entities/PoolAttendantEntity.cpp'), 'void PoolAttendantEntity::restoreFromSave(')
assert attendant_restore.count('setAnimationTime(save.mHasClipTime ? save.mClipTime : getClipTurns() - mTurnsLeft);') == 4
assert attendant_restore.count('if(save.mHasClipTime') == 3, 'sitting, walk to the board and walk back also use the saved clip time'
# The jump of the attendant shows its clip at the phase of the arc, when it starts and in every frame
attendant_source = read('source/entities/PoolAttendantEntity.cpp')
for jump_text in (extract(attendant_source, 'void PoolAttendantEntity::startJumpFromServer('), extract(attendant_source, 'void PoolAttendantEntity::update(')):
    assert 'getAnimationName() == EntityAnimation::jump_anim' in jump_text and 'setTimePosition(' in jump_text
# The jump of a creature shows its clip at the phase of the arc too (loaded game, seat that gains sight, every frame)
jump_clip_phase = extract(creature_cpp, 'void Creature::showJumpClipPhase(')
assert 'getAnimationName() == EntityAnimation::jump_anim' in jump_clip_phase and 'setTimePosition(' in jump_clip_phase and 'mJumpElapsed' in jump_clip_phase
assert 'showJumpClipPhase();' in extract(creature_cpp, 'void Creature::startJumpFromServer(')
assert 'showJumpClipPhase();' in extract(creature_cpp, 'void Creature::update(')
# The attendant whistles only for a guest who bathes in the mud, not for one that still jumps
assert 'SpaBatherState::jumping' not in extract(read('source/rooms/RoomSpa.cpp'), 'bool RoomSpa::hasBatherInPool(')
assert 'SpaBatherState::bathing' in extract(read('source/rooms/RoomSpa.cpp'), 'bool RoomSpa::hasBatherInPool(')
assert 'save.mClipTime = getAnimationTime();' in extract(read('source/entities/PoolAttendantEntity.cpp'), 'void PoolAttendantEntity::exportSaveData(')
assert 'double MovableGameEntity::getAnimationTime() const' in read('source/entities/MovableGameEntity.cpp')
assert 'void MovableGameEntity::setAnimationTime(' in read('source/entities/MovableGameEntity.cpp')
# A seat that gains sight in the middle of a jump gets the running arc after the entity data, for creature and attendant
# (the notification of the jump goes to the seats that already see the entity, so the new seat needs its own message)
attendant_cpp = read('source/entities/PoolAttendantEntity.cpp')
for text, name in ((extract(creature_cpp, 'void Creature::fireAddEntity('), 'creature'), (extract(attendant_cpp, 'void PoolAttendantEntity::fireAddEntity('), 'attendant')):
    assert 'if(isJumping())' in text and 'sendJumpNotificationTo(seat);' in text, 'the ' + name + ' sends the running jump to a new seat'
creature_add = extract(creature_cpp, 'void Creature::fireAddEntity(')
assert creature_add.count('sendJumpNotificationTo(seat);') == 2, 'queued and async path of the creature'
assert creature_add.index('exportToPacket(serverNotification.mPacket, seat);') < creature_add.index('sendJumpNotificationTo(seat);')
assert creature_add.rindex('exportToPacket(serverNotification->mPacket, seat);') < creature_add.rindex('sendJumpNotificationTo(seat);')
assert 'RenderedMovableEntity::fireAddEntity(seat, async, nt);' in extract(attendant_cpp, 'void PoolAttendantEntity::fireAddEntity(').split('sendJumpNotificationTo')[0]
for text in (extract(creature_cpp, 'void Creature::sendJumpNotificationTo('), extract(attendant_cpp, 'void PoolAttendantEntity::sendJumpNotificationTo(')):
    assert 'getName() << mJumpFrom << mJumpTo << mJumpTurns << mJumpElapsed;' in text and 'ServerNotificationType::creatureJump' in text
    assert 'getIsHuman()' in text
for text in (extract(creature_cpp, 'void Creature::sendJumpNotification('), extract(attendant_cpp, 'void PoolAttendantEntity::sendJumpNotification(')):
    assert 'sendJumpNotificationTo(seat);' in text and 'mSeatsWithVisionNotified' in text, 'the seats that see the jump begin still get it'
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
    double getRoomConfigDouble(const std::string& key) const { return (key == "SpaMoodMax") ? 300.0 : 0.0; }
};
@@STRINGS@@

struct Seat;
struct Creature
{
    std::string mName;
    double mSpaMood, mRelaxTurns; int32_t mSpaMudTilesLeft; uint32_t mJumpTurnsLeft;
    double mThirst, mTavernMood, mDrunk, mHangoverTurns; Seat* mSeat;
    std::string mOtherBlock;
    explicit Creature(const std::string& name) : mName(name), mSpaMood(0.0), mRelaxTurns(0.0), mSpaMudTilesLeft(0), mJumpTurnsLeft(0),
        mThirst(0.0), mTavernMood(0.0), mDrunk(0.0), mHangoverTurns(0.0), mSeat(nullptr) {}
    Seat* getSeat() const { return mSeat; }
    void exportThirstStateToPacket(ODPacket& os) const;
    void writeFullTail(ODPacket& os, const Seat* seat) const;
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
// The end of Creature::exportToPacket, cut from the source
void Creature::writeFullTail(ODPacket& os, const Seat* seat) const
{
@@FULL_TAIL@@
}

// ---- Creature: block and packet
static void checkSpaBlock()
{
    // Round trip with fractions
    Creature a("a"); a.setSpaMood(212.5); a.setRelaxTurns(302.4); a.setSpaMudTilesLeft(2);
    std::ostringstream out; a.writeBlocks(out);
    expect(out.str() == "\t[Spa] 212.5 302.4 2 [/Spa]", "written block: " + out.str());
    Creature b("b"); std::istringstream in(out.str());
    expect(b.readBlocks(in), "block read");
    expectNear(b.mSpaMood, 212.5, "spa mood"); expectNear(b.mRelaxTurns, 302.4, "relaxation"); expect(b.mSpaMudTilesLeft == 2, "mud tiles");
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
    expect(l.readBlocks(limited) && l.mSpaMood == 300.0 && l.mRelaxTurns == 0.0 && l.mSpaMudTilesLeft == 0, "values limited");
    // Broken blocks are refused
    const char* broken[] = { "[Spa] 1 2 [/Spa]", "[Spa] 1 2 3", "[Spa] 1 2 3 [/Other]", "[Spa] a b c [/Spa]", "[Spa]" };
    for(unsigned i = 0; i < sizeof(broken) / sizeof(broken[0]); ++i)
    {
        Creature x("x"); std::istringstream bad(broken[i]);
        expect(!x.readBlocks(bad), std::string("broken block refused: ") + broken[i]);
    }
    // Packet: the spa state keeps its fractions, in the order mood, relaxation
    Creature p("p"); p.setSpaMood(233.25); p.setRelaxTurns(17.75);
    ODPacket packet; p.exportSpaStateToPacket(packet);
    Creature q("q"); q.importSpaStateFromPacket(packet);
    expectNear(q.mSpaMood, 233.25, "packet mood"); expectNear(q.mRelaxTurns, 17.75, "packet relaxation");
    expect(packet.data.str() == "233.25 17.75 ", "two fields: " + packet.data.str());
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
    attendant.save.mPlaceX = 16; attendant.save.mPlaceY = 9; attendant.save.mHasClipTime = true; attendant.save.mClipTime = 12.25;
    RoomSpa room; room.mPayer = SpaPayer::creature; room.mAttendant = &attendant;
    RoomSpaBather b1(&reserved); b1.mBlock.mX = 16; b1.mBlock.mY = 8; b1.mBlock.mWidth = 1; b1.mBlock.mHeight = 2; b1.mState = SpaBatherState::reserved; b1.mJump = true;
    jumping.mJumpTurnsLeft = 1;
    RoomSpaBather b2(&jumping); b2.mBlock.mX = 17; b2.mBlock.mY = 9; b2.mBlock.mWidth = 2; b2.mBlock.mHeight = 2; b2.mState = SpaBatherState::jumping; b2.mJump = true;
    RoomSpaBather b3(&bathing); b3.mBlock.mX = 18; b3.mBlock.mY = 8; b3.mState = SpaBatherState::bathing; b3.mTurnsDone = 12.5;
    RoomSpaBather b4(&done); b4.mBlock.mX = 16; b4.mBlock.mY = 10; b4.mState = SpaBatherState::bathing; b4.mTurnsDone = 71.5; b4.mDone = true;
    room.mBathers.push_back(b1); room.mBathers.push_back(b2); room.mBathers.push_back(b3); room.mBathers.push_back(b4);
    const std::string text = exported(room);
    expect(text.find("SpaPayer 1") != std::string::npos, "payer line");
    expect(text.find("PoolAttendant 12.5 8.25 doze 7.5 99.5 1 16 9 12.25") != std::string::npos, "attendant line: " + text);
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
    expect(loaded.mPendingAttendant.mSave.mHasClipTime, "attendant clip time present");
    expectNear(loaded.mPendingAttendant.mSave.mClipTime, 12.25, "attendant clip time");
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
    // An older line with the place but without the clip time loads, the time is then worked out from the turns left
    RoomSpa noClip; std::istringstream noClipIn("RoomHead\nPoolAttendant 3 4 doze 5 9 1 2 3\n");
    expect(noClip.importFromStream(noClipIn) && noClip.mPendingAttendant.mSave.mHasPlace && !noClip.mPendingAttendant.mSave.mHasClipTime, "attendant line without the clip time");
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

// ---- The full creature packet: the spa state only for the own seat, the same number of fields for every seat
static void checkFullPacketPrivacy()
{
    Seat own = { nullptr }, ally = { nullptr }, enemy = { nullptr };
    Creature c("c"); c.mSeat = &own; c.mThirst = 11.0; c.mTavernMood = 22.0; c.mDrunk = 33.0; c.mHangoverTurns = 44.0;
    c.setSpaMood(55.0); c.setRelaxTurns(66.0);
    ODPacket forOwn; c.writeFullTail(forOwn, &own);
    ODPacket forAlly; c.writeFullTail(forAlly, &ally);
    ODPacket forEnemy; c.writeFullTail(forEnemy, &enemy);
    expect(forOwn.data.str() == "11 22 33 44 55 66 ", "the own seat gets the real values: " + forOwn.data.str());
    expect(forAlly.data.str() == "11 22 33 44 0 0 ", "an allied foreign seat gets the tavern fields and zeros for the spa: " + forAlly.data.str());
    expect(forEnemy.data.str() == "11 22 33 44 0 0 ", "an enemy seat gets the tavern fields and zeros for the spa: " + forEnemy.data.str());
    // The client reads the same six fields from every packet: the four tavern fields, then the two spa fields
    Creature reader("r"); double tavernField = 0.0;
    for(int field = 0; field < 4; ++field)
        forAlly >> tavernField;
    reader.importSpaStateFromPacket(forAlly);
    expectNear(reader.mSpaMood, 0.0, "zero spa mood arrives"); expectNear(reader.mRelaxTurns, 0.0, "zero relaxation arrives");
}

// ---- The attendant after loading: the real restoreFromSave against a stub of the attendant and its room. A clip that was
// saved in the middle goes on from the reached turn; the stub resets the clip time in setAnimationState like the entity.
namespace Ogre { typedef float Real; struct Vector3 { Real x, y, z; Vector3(Real a = 0, Real b = 0, Real c = 0) : x(a), y(b), z(c) {} static const Vector3 ZERO; }; const Vector3 Vector3::ZERO(0.0f, 0.0f, 0.0f); }
namespace PoolAttendantPose
{
    static const std::string sit = "Sit"; static const std::string whistle = "Whistle"; static const std::string towelWave = "TowelWave";
    static const std::string doze = "Doze"; static const std::string climb = "Climb";
}
static const Ogre::Vector3 AWAY_FROM_POOL(0.0f, -1.0f, 0.0f);
struct Tile { };
static double getClipTurns() { return 40.0; }
struct RenderedMovableEntity { static void setPosition(const Ogre::Vector3& position) { } };
struct ProbeRoom
{
    Tile board; bool hasBoard, poolOk;
    ProbeRoom() : hasBoard(true), poolOk(true) {}
    bool isPoolPosition(int32_t x, int32_t y) const { return poolOk; }
    Tile* getSpringboardTile() { return hasBoard ? &board : nullptr; }
};
struct AttendantProbe
{
    ProbeRoom* mRoom; Tile* mChairTile; PoolAttendantState mState; double mActTurnsLeft, mTurnsLeft, mCannonballTurnsLeft;
    bool mHasPlace; int32_t mPlaceX, mPlaceY; uint32_t mJumpTurns, mJumpTurnsLeft; Ogre::Real mJumpElapsed; Ogre::Vector3 mJumpFrom, mJumpTo;
    std::string clip; double clipTime; int aborts; double ladderProgress;
    AttendantProbe(ProbeRoom* room, Tile* chair) : mRoom(room), mChairTile(chair), mState(PoolAttendantState::sitting), mActTurnsLeft(0.0), mTurnsLeft(0.0),
        mCannonballTurnsLeft(0.0), mHasPlace(false), mPlaceX(0), mPlaceY(0), mJumpTurns(0), mJumpTurnsLeft(0), mJumpElapsed(0.0f), clipTime(-1.0), aborts(0), ladderProgress(-1.0) {}
    void setAnimationState(const std::string& state, bool loop, const Ogre::Vector3& direction, bool idle) { clip = state; clipTime = 0.0; }
    void setAnimationTime(double time) { clipTime = (time < 0.0) ? 0.0 : time; }
    double getAnimationTime() const { return clipTime; }
    void moveTo(const Ogre::Vector3& position) { }
    void placeOnLadder(double progress) { ladderProgress = progress; }
    void abortToChair() { ++aborts; mState = PoolAttendantState::sitting; }
    void startWalkToBoard() { mState = PoolAttendantState::walkingToBoard; clip = "Walk"; clipTime = 0.0; }
    void startWalkBack() { mState = PoolAttendantState::walkingBack; clip = "Walk"; clipTime = 0.0; }
    void startJump() { mState = PoolAttendantState::jumping; mJumpTurns = 20; mJumpTurnsLeft = 20; mJumpElapsed = 0.0f; clip = "Jump"; clipTime = 0.0; }
    void sendJumpNotification() { }
    static Ogre::Vector3 jumpPosition(const Ogre::Vector3& from, const Ogre::Vector3& to, Ogre::Real progress) { return from; }
    void restoreFromSave(const PoolAttendantSave& save);
};
#define PoolAttendantEntity AttendantProbe
@@RESTORE@@
#undef PoolAttendantEntity

static void checkAttendantRestore()
{
    Tile chair; ProbeRoom room;
    const PoolAttendantState acts[] = { PoolAttendantState::whistling, PoolAttendantState::towelWaving, PoolAttendantState::dozing };
    const char* clips[] = { "Whistle", "TowelWave", "Doze" };
    for(int i = 0; i < 3; ++i)
    {
        // An act of 2 seconds (40 turns) with 30 turns left was played for 10 turns: the clip goes on there, not from 0
        AttendantProbe a(&room, &chair); PoolAttendantSave save; save.mState = acts[i]; save.mTurnsLeft = 30.0;
        a.restoreFromSave(save);
        expect(a.mState == acts[i] && a.clip == clips[i], std::string("the act is restored: ") + clips[i]);
        expectNear(a.clipTime, 10.0, std::string("the act clip goes on at the reached turn: ") + clips[i]);
        AttendantProbe b(&room, &chair); save.mTurnsLeft = 40.0; b.restoreFromSave(save);
        expectNear(b.clipTime, 0.0, std::string("an act that had just begun starts at 0: ") + clips[i]);
    }
    // A saved clip time that differs from the turns (the clip runs on the frame clock) wins and survives a save of the restored attendant
    for(int i = 0; i < 3; ++i)
    {
        AttendantProbe a(&room, &chair); PoolAttendantSave save; save.mState = acts[i]; save.mTurnsLeft = 30.0; save.mHasClipTime = true; save.mClipTime = 13.25;
        a.restoreFromSave(save);
        expectNear(a.clipTime, 13.25, std::string("the saved clip time is used: ") + clips[i]);
    }
    // The saved clip time of a climb is used for the clip, the height follows the turns left
    AttendantProbe timedClimb(&room, &chair); PoolAttendantSave timed; timed.mState = PoolAttendantState::climbingUp; timed.mTurnsLeft = 10.0;
    timed.mHasClipTime = true; timed.mClipTime = 27.5; timedClimb.restoreFromSave(timed);
    expectNear(timedClimb.clipTime, 27.5, "the saved clip time of the climb is used");
    // The climb: the clip and the height are set from the same reached turn
    AttendantProbe down(&room, &chair); PoolAttendantSave climb; climb.mState = PoolAttendantState::climbingDown; climb.mTurnsLeft = 10.0;
    climb.mHasPlace = true; down.restoreFromSave(climb);
    expect(down.mState == PoolAttendantState::climbingDown && down.clip == "Climb", "the climb down is restored");
    expectNear(down.clipTime, 30.0, "the climb clip goes on at the reached turn"); expectNear(down.ladderProgress, 0.75, "the height follows the same turn");
    AttendantProbe up(&room, &chair); climb.mState = PoolAttendantState::climbingUp; up.restoreFromSave(climb);
    expectNear(up.clipTime, 30.0, "the climb up goes on at the reached turn"); expectNear(up.ladderProgress, 0.25, "the height of the climb up");
    // Sitting and both walks go on at the saved clip time; an old save without it starts at 0
    const PoolAttendantState others[] = { PoolAttendantState::sitting, PoolAttendantState::walkingToBoard, PoolAttendantState::walkingBack };
    for(int i = 0; i < 3; ++i)
    {
        AttendantProbe a(&room, &chair); PoolAttendantSave save; save.mState = others[i]; save.mTurnsLeft = 5.0; save.mHasPlace = true;
        save.mHasClipTime = true; save.mClipTime = 17.5; a.restoreFromSave(save);
        expect(a.mState == others[i], "the state is restored");
        expectNear(a.clipTime, 17.5, "the saved clip time of sitting and walking is used");
        AttendantProbe b(&room, &chair); save.mHasClipTime = false; b.restoreFromSave(save);
        expect(b.clipTime < 0.5, "a save without the clip time starts the clip at 0");
    }
    // A climb down without its place only goes back to the chair
    AttendantProbe lost(&room, &chair); PoolAttendantSave noPlace = climb; noPlace.mState = PoolAttendantState::climbingDown; noPlace.mHasPlace = false;
    lost.restoreFromSave(noPlace);
    expect(lost.aborts == 1 && lost.mState == PoolAttendantState::sitting, "a climb down without a place ends on the chair");
}

int main()
{
    checkAttendantRestore();
    checkSpaBlock();
    checkFullPacketPrivacy();
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
    'void Creature::exportThirstStateToPacket(', 'void Creature::exportSpaStateToPacket(',
    'void Creature::importSpaStateFromPacket('])

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
    '@@FULL_TAIL@@': full_tail,
    '@@RESTORE@@': extract(read('source/entities/PoolAttendantEntity.cpp'), 'void PoolAttendantEntity::restoreFromSave('),
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
