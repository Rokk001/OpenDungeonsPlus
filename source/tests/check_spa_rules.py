"""Lava spa rules: the real functions of the spa mood, of the bath and of the room are cut out of the sources and run
against small stubs; the numbers come from config/rooms.cfg, config/global.cfg and config/skills.cfg.

What is run (the function bodies are taken from the source files, not copied by hand):
  Creature::wantsSpaBath             a bath is wanted for Upset, Angry and Furious with the relaxation run out, or with a hangover
                                     (also when relaxed); never for workers, rogue creatures, prisoners and creatures in the hand
  Creature::addSpaMood / setSpaMood / setRelaxTurns / setSpaMudTilesLeft / getRelaxWorkFactor / upkeepSpaState
                                     the clamp 0..SpaMoodMax, no fading while the creature sits in the bath, then 0.4 per turn
                                     (750 turns from the full value 300), the relaxation counts down by 1 and never below 0,
                                     the work factor 1.0567 only while relaxed
  Creature mud trail                 the code of Creature::dirtyEnteredTile that spreads the mud: not on pool tiles, the
                                     next 3 tiles outside the pool each get SpaDirtPerBath / 3 times the DirtFactor, the
                                     creature dirt does not change
  RoomSpa::canPay / payForBath / canAccept / getPoolSet / getTakenSet / getCoveredSet / findBatherOf
                                     both payment paths with the price BeerPrice (a changed key is followed), "no coin, no
                                     bath" (the creature is not accepted, nothing is paid), workers, other seats and a full
                                     pool are refused, so nobody queues
  RoomSpa::startBath / upkeepBathers / finishBath / isBatherDisturbed / abortDisturbedBathers
                                     the bath lasts 15 turns (the counted turns reach 14.2857), +21 mood per turn up to 300,
                                     at the end the relaxation is 252 / 302.4 / 352.8 by research level, the hangover is 0,
                                     the post is sent once, the creature dirt is untouched, the mud counter is 3; a fight, a
                                     flight, a knock-out, a pick-up or a missing creature breaks the bath off: the mood stays,
                                     no relaxation, the hangover stays, no refund, a running jump is cancelled
The source wiring (where the bath is sought, where the work factor is used, the mood sum, the "no spa" path of the search) is
checked on the source text.

Calls (from the repository root):
  python source/tests/check_spa_rules.py

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


creature_cpp = read('source/entities/Creature.cpp')
room_cpp = read('source/rooms/RoomSpa.cpp')
room_h = read('source/rooms/RoomSpa.h')
search_cpp = read('source/creatureaction/CreatureActionSearchSpa.cpp')
job_cpp = read('source/creatureaction/CreatureActionSearchJob.cpp')
mood_cpp = read('source/creaturemood/CreatureMoodManager.cpp')
rooms_cfg = read('config/rooms.cfg')
global_cfg = read('config/global.cfg')
skills_cfg = read('config/skills.cfg')

# ---- Source wiring -----------------------------------------------------------------------------------------------
# The idle decision follows the thirst check and goes before the toilet check; the job search asks again after the hunger check
idle = creature_cpp[creature_cpp.index('// If we are thirsty, we go to a tavern'):]
idle = idle[:idle.index('// If we have to relieve ourselves')]
assert 'CreatureActionSearchDrink>' in idle and 'wantsSpaBath()' in idle
assert idle.index('CreatureActionSearchDrink>') < idle.index('CreatureActionSearchSpa>'), 'the spa check follows the thirst check'
assert '!hasActionBeenTried(CreatureActionType::searchSpa)' in idle, 'one try per search, no loop'
job_spa = job_cpp[job_cpp.index('creature.wantsSpaBath()'):]
job_spa = job_spa[:job_spa.index('return true;')]
assert 'hasActionBeenTried(CreatureActionType::searchSpa)' in job_spa and 'CreatureActionSearchSpa>' in job_spa
assert job_cpp.index('CreatureActionSearchFood>') < job_cpp.index('creature.wantsSpaBath()'), 'the bath is sought after the hunger check'
# The search: no spa that can take the creature, no action (no queue); the nearest is chosen; the room reserves the place
assert 'canAccept(creature)' in search_cpp and 'if(spaTiles.empty())' in search_cpp
assert re.search(r'if\(spaTiles\.empty\(\)\)\s*\{\s*creature\.popAction\(\);\s*return true;', search_cpp)
assert 'findBestPath(&creature, myTile, spaTiles, chosenTile)' in search_cpp and 'getRoomsByTypeAndSeat(RoomType::spa, creature.getSeat())' in search_cpp
# The spa mood is one more mood part, summed after the pit mood
assert mood_cpp.index('creature.getPitMood()') < mood_cpp.index('creature.getSpaMood()')
# The relaxation work factor stands exactly where the hangover factor stands: library, workshop, training hall, arena experience
for path in ('source/rooms/RoomLibrary.cpp', 'source/rooms/RoomWorkshop.cpp', 'source/rooms/RoomTrainingHall.cpp'):
    assert 'creature.getHangoverWorkFactor() * creature.getRelaxWorkFactor()' in read(path), path
assert 'getHangoverWorkFactor() * getRelaxWorkFactor()' in creature_cpp
every_use = ''.join(read(str(p.relative_to(root))) for p in (root / 'source').rglob('*.cpp') if 'tests' not in p.parts)
assert every_use.count('getRelaxWorkFactor()') == 5, 'one definition and four uses (library, workshop, training hall, arena)'
# No combat value is touched: the relaxation is not used in the fight code
for path in ('source/entities/Creature.cpp',):
    for name in ('Creature::getAttackRating', 'Creature::getPhysicalDefense', 'Creature::getMagicalDefense', 'Creature::computeAttack'):
        if name + '(' in read(path):
            assert 'Relax' not in extract(read(path), name + '('), name + ' must not use the relaxation'
# A broken-off bath: the room code that ends it neither gives relaxation nor money back
for function in ('void RoomSpa::abortDisturbedBathers(', 'void RoomSpa::removeCreatureUsingRoom('):
    body = extract(room_cpp, function)
    for forbidden in ('setRelaxTurns', 'setHangoverTurns', 'addTavernMood', 'addGoldCarried', 'addGoldToSeat', 'addTreasury', 'setCreatureDirt', 'washed'):
        assert forbidden not in body, function + ' must not call ' + forbidden
finish = extract(room_cpp, 'void RoomSpa::finishBath(')
assert 'washed(' not in finish and 'setCreatureDirt' not in finish and 'mCreatureDirt' not in finish, 'the bath does not clean the creature'
assert 'washed()' not in room_cpp, 'the spa never washes a creature'
# The fee is paid when the bath starts: at the landing after a jump, in the middle of the place after a walk; never at the board
assert room_cpp.count('payForBath(creature)') == 1 and room_cpp.count('payForBath(*creature)') == 1
assert 'payForBath' in extract(room_cpp, 'bool RoomSpa::landJump(') and 'payForBath' not in extract(room_cpp, 'void RoomSpa::startBath(')
# The jump: the arc, the notification and the landing with splash and sound
assert 'creature.startJump(getBlockCentre(bather));' in room_cpp and 'SPA_SPLASH_EFFECT' in extract(room_cpp, 'bool RoomSpa::landJump(')
assert 'Rooms/Spa/Splash' in room_cpp

# ---- Probe -------------------------------------------------------------------------------------------------------
rooms = block_values(rooms_cfg, 'Rooms')
tavern = block_values(global_cfg, 'Tavern')
room_keys = ['SpaMoodMax', 'SpaMoodPerTurn', 'SpaMoodDecayPerTurn', 'SpaBathTurns', 'SpaRelaxTurns', 'SpaRelaxWorkFactor',
             'SpaDirtPerBath', 'SpaMudTrailTiles', 'SpaJumpTurns', 'SpaJumpHeight', 'SpaCannonballChance']
room_table = ',\n'.join('    {"%s", %s}' % (k, rooms[k]) for k in room_keys)
tavern_table = ',\n'.join('    {"%s", %s}' % (k, tavern[k]) for k in ('BeerPrice', 'HangoverTurns'))
effect_line = re.search(r'^\s*roomSpa\s+RelaxTime\s+mul\s+(\S+)\s+(\S+)\s+(\S+)\s*$', skills_cfg, re.M)
assert effect_line is not None, 'the relaxation effect line is missing'
effect_table = ', '.join(effect_line.groups())

probe = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>
#include "RoomSpaLayout.h"

#define OD_LOG_WRN(x) do { } while(0)
#define OD_LOG_ERR(x) do { } while(0)

static int failures = 0;
static void expect(bool ok, const std::string& what) { if(!ok) { ++failures; std::cout << "FAIL: " << what << std::endl; } }
static void expectNear(double a, double b, const std::string& what, double eps = 1e-9)
{ if(std::fabs(a - b) > eps) { ++failures; std::cout << "FAIL: " << what << " got " << a << " expected " << b << std::endl; } }

namespace Ogre
{
typedef float Real;
struct Vector3
{
    Real x, y, z;
    Vector3() : x(0), y(0), z(0) {}
    Vector3(Real ax, Real ay, Real az) : x(ax), y(ay), z(az) {}
    static const Vector3 ZERO;
};
const Vector3 Vector3::ZERO(0, 0, 0);
}

// ---- Configuration: the real values of the config files, an unknown key is a failure
struct ConfigManager
{
    std::map<std::string, double> room, tavern;
    static ConfigManager& getSingleton() { static ConfigManager instance; return instance; }
    static double lookup(const std::map<std::string, double>& table, const std::string& key)
    {
        std::map<std::string, double>::const_iterator it = table.find(key);
        if(it == table.end()) { ++failures; std::cout << "FAIL: unknown config key " << key << std::endl; return 0.0; }
        return it->second;
    }
    double getRoomConfigDouble(const std::string& key) const { return lookup(room, key); }
    uint32_t getRoomConfigUInt32(const std::string& key) const { return static_cast<uint32_t>(lookup(room, key)); }
    double getTavernConfigDouble(const std::string& key) const { return lookup(tavern, key); }
};
static void loadConfig()
{
    static const struct { const char* key; double value; } roomTable[] = {
@@ROOM_CONFIG@@
    };
    static const struct { const char* key; double value; } tavernTable[] = {
@@TAVERN_CONFIG@@
    };
    for(unsigned i = 0; i < sizeof(roomTable) / sizeof(roomTable[0]); ++i)
        ConfigManager::getSingleton().room[roomTable[i].key] = roomTable[i].value;
    for(unsigned i = 0; i < sizeof(tavernTable) / sizeof(tavernTable[0]); ++i)
        ConfigManager::getSingleton().tavern[tavernTable[i].key] = tavernTable[i].value;
}

@@MOOD_LEVEL@@
enum class SkillType { roomSpa, other };
enum class CreatureActionType { fight, fightFriendly, flee, useRoom, other };
namespace ResearchEffect { static const std::string RelaxTime = "RelaxTime"; }
struct EntityAnimation { static const std::string idle_anim; static const std::string bathe_anim; };
const std::string EntityAnimation::idle_anim = "Idle";
const std::string EntityAnimation::bathe_anim = "Bathe";

struct Creature; struct Tile; struct GameMap; struct Seat;

struct Tile
{
    int x, y; double dirt; bool pool;
    Tile(int ax, int ay) : x(ax), y(ay), dirt(0.0), pool(false) {}
    int getX() const { return x; } int getY() const { return y; }
    void addDirt(double amount) { dirt += amount; }
};

// The seat: rogue flag, id, treasury gold and the research level of the spa
struct Seat
{
    bool rogue; int id; int gold; uint32_t spaLevel;
    Seat() : rogue(false), id(1), gold(0), spaLevel(0) {}
    bool isRogueSeat() const { return rogue; }
    int getId() const { return id; }
    int getGold() const { return gold; }
    uint32_t getSkillLevel(SkillType) const { return spaLevel; }
};

// The research value: the level picks the factor of the effect line of skills.cfg (level 0 = base value)
namespace SkillManager
{
static double getResearchValue(const Seat* seat, SkillType type, double base, const std::string& effect)
{
    static const double factors[] = { @@EFFECTS@@ };
    const uint32_t level = seat->getSkillLevel(type);
    return (level == 0) ? base : base * factors[std::min<uint32_t>(level, 3) - 1];
}
}

struct CreatureDefinition
{
    bool worker; int bed1, bed2; double dirtFactor;
    CreatureDefinition(bool w, int b1, int b2) : worker(w), bed1(b1), bed2(b2), dirtFactor(1.0) {}
    bool isWorker() const { return worker; }
    int getBedDim1() const { return bed1; }
    int getBedDim2() const { return bed2; }
    double getDirtFactor() const { return dirtFactor; }
};

class RoomSpa;
struct Creature
{
    CreatureDefinition* mDefinition; Seat* mSeat; std::string mName; Tile* mTile;
    double mHangoverTurns, mTavernMood, mTavernMoodTurns, mSpaMood, mRelaxTurns, mCreatureDirt; int32_t mSpaMudTilesLeft; bool mSpaBathing;
    bool mIsInHand, mPrison, mOnMap, mAlive, mKo, mDragged, mFighting, mFriendlyFight, mFleeing, mJumping;
    CreatureMoodLevel mMood; int32_t mGold; int cancelJumpCalls; int splashes; int clearCalls;
    Creature(const std::string& name, CreatureDefinition* def, Seat* seat)
      : mDefinition(def), mSeat(seat), mName(name), mTile(nullptr), mHangoverTurns(0.0), mTavernMood(0.0), mTavernMoodTurns(0.0), mSpaMood(0.0), mRelaxTurns(0.0),
        mCreatureDirt(7.0), mSpaMudTilesLeft(0), mSpaBathing(false), mIsInHand(false), mPrison(false), mOnMap(true), mAlive(true),
        mKo(false), mDragged(false), mFighting(false), mFriendlyFight(false), mFleeing(false), mJumping(false),
        mMood(CreatureMoodLevel::Neutral), mGold(0), cancelJumpCalls(0), splashes(0), clearCalls(0) {}
    Seat* getSeat() const { return mSeat; }
    CreatureDefinition* getDefinition() const { return mDefinition; }
    const std::string& getName() const { return mName; }
    bool isInPrison() const { return mPrison; }
    CreatureMoodLevel getMoodValue() const { return mMood; }
    bool getIsOnMap() const { return mOnMap; }
    bool isAlive() const { return mAlive; }
    bool isKo() const { return mKo; }
    bool isBeingDragged() const { return mDragged; }
    bool isActionInList(CreatureActionType type) const
    { return ((type == CreatureActionType::fight) && mFighting) || ((type == CreatureActionType::fightFriendly) && mFriendlyFight) ||
             ((type == CreatureActionType::flee) && mFleeing); }
    int32_t getGoldCarried() const { return mGold; }
    void addGoldCarried(int32_t gold) { mGold += gold; }
    Tile* getPositionTile() const { return mTile; }
    void setAnimationState(const std::string& state, bool loop = true, const Ogre::Vector3& direction = Ogre::Vector3::ZERO, bool idle = true) {}
    void continueJump() {}
    void addParticleEffect(const std::string& effect, int32_t turns) { ++splashes; }
    void clearActionQueue() { ++clearCalls; }
    bool isJumping() const { return mJumping; }
    void cancelJump() { ++cancelJumpCalls; mJumping = false; }
    void setSpaBathing(bool bathing) { mSpaBathing = bathing; }
    void setHangoverTurns(double turns);
    void addTavernMood(double points, double turns);
    void addSpaMood(double points);
    void setSpaMood(double val);
    void setRelaxTurns(double turns);
    double getRelaxWorkFactor() const;
    void setSpaMudTilesLeft(int32_t tiles);
    bool wantsSpaBath() const;
    void upkeepSpaState();
    void testMudTrail(Tile* tile);
};

// The mud trail of Creature::dirtyEnteredTile, cut from the source
struct RoomSpaPool { static bool isPoolTile(const Tile* tile) { return tile->pool; } };
#define RoomSpa RoomSpaPool
@@CREATURE_FUNCTIONS@@
void Creature::testMudTrail(Tile* tile)
{
@@MUD_TRAIL@@
}
#undef RoomSpa

struct GameMap
{
    int treasury, seatGold;
    GameMap() : treasury(0), seatGold(0) {}
    bool withdrawFromTreasuries(int gold, Seat* seat) { if(seat->gold < gold) return false; seat->gold -= gold; return true; }
    void addGoldToSeat(int gold, int seatId) { seatGold += gold; }
};

static const std::string SPA_SPLASH_EFFECT = "SpaMudSplash";
static const int32_t SPA_SPLASH_TURNS = 1;
static const std::string SOUND_SPLASH = "Rooms/Spa/Splash";
struct PoolAttendantEntity { bool getPlace(int32_t& x, int32_t& y) const { return false; } };

struct Room
{
    GameMap* mMap; Seat* mSeat; std::vector<Tile*> mCoveredTiles;
    Room(GameMap* map, Seat* seat) : mMap(map), mSeat(seat) {}
    GameMap* getGameMap() const { return mMap; }
    Seat* getSeat() const { return mSeat; }
};
@@ROOM_TYPES@@
@@ROOM_HELPERS@@

class RoomSpa : public Room
{
public:
    RoomSpa(GameMap* map, Seat* seat) : Room(map, seat), mPayer(SpaPayer::keeper), mAttendant(nullptr), posts(0) {}
    SpaPayer mPayer; PoolAttendantEntity* mAttendant; std::vector<RoomSpaBather> mBathers;
    std::map<std::string, RoomSpaPendingBather> mPendingBathers; int posts;
    void sendBathFinished(Creature& creature) { ++posts; }
    void playSoundAt(Tile* tile, const std::string& family) {}
    SpaTileSet getCoveredSet() const;
    SpaTileSet getPoolSet() const;
    SpaTileSet getTakenSet() const;
    std::vector<RoomSpaBather>::iterator findBatherOf(const Creature* creature);
    bool canPay(const Creature& creature) const;
    bool payForBath(Creature& creature);
    bool canAccept(const Creature& creature) const;
    void startBath(RoomSpaBather& bather);
    bool landJump(RoomSpaBather& bather);
    void finishBath(RoomSpaBather& bather);
    void upkeepBathers();
    static bool isBatherDisturbed(const Creature& creature);
    void abortDisturbedBathers();
};
@@ROOM_FUNCTIONS@@

// ---- The fixture: a 5x5 room (pool 3x3) of a seat with a worker-free dungeon
struct Fixture
{
    GameMap map; Seat seat; std::vector<Tile> tiles; RoomSpa* room;
    CreatureDefinition small, medium, big, worker;
    Fixture() : small(false, 1, 1), medium(false, 1, 2), big(false, 2, 2), worker(true, 1, 1)
    {
        for(int y = 0; y < 5; ++y) for(int x = 0; x < 5; ++x) tiles.push_back(Tile(x, y));
        room = new RoomSpa(&map, &seat);
        for(std::size_t i = 0; i < tiles.size(); ++i) room->mCoveredTiles.push_back(&tiles[i]);
        seat.gold = 100;
    }
    ~Fixture() { delete room; }
    // Puts the creature into a bathing place and the bath on its first turn
    RoomSpaBather& startBathFor(Creature& c)
    {
        RoomSpaBather bather(&c);
        SpaLayout::findFreeBlock(room->getPoolSet(), room->getTakenSet(), c.mDefinition->getBedDim1(), c.mDefinition->getBedDim2(), bather.mBlock);
        room->mBathers.push_back(bather);
        room->startBath(room->mBathers.back());
        return room->mBathers.back();
    }
};

// ---- Trigger
static void checkTrigger()
{
    Fixture f; Creature c("c", &f.small, &f.seat);
    const CreatureMoodLevel moods[] = { CreatureMoodLevel::Happy, CreatureMoodLevel::Neutral, CreatureMoodLevel::Upset,
                                        CreatureMoodLevel::Angry, CreatureMoodLevel::Furious, CreatureMoodLevel::Unknown };
    const bool bad[] = { false, false, true, true, true, false };
    for(int i = 0; i < 6; ++i)
    {
        c.mMood = moods[i];
        expect(c.wantsSpaBath() == bad[i], "mood " + std::to_string(i) + " without hangover or relaxation");
        // The relaxation of the last bath blocks the bath for a bad mood
        c.mRelaxTurns = 0.5;
        expect(!c.wantsSpaBath(), "relaxed creature does not bathe for the mood, mood " + std::to_string(i));
        // A hangover is not blocked by the relaxation and works at any mood
        c.mHangoverTurns = 10.0;
        expect(c.wantsSpaBath(), "hangover bathes although relaxed, mood " + std::to_string(i));
        c.mRelaxTurns = 0.0;
        expect(c.wantsSpaBath(), "hangover bathes at any mood, mood " + std::to_string(i));
        c.mHangoverTurns = 0.0;
    }
    c.mMood = CreatureMoodLevel::Furious; c.mHangoverTurns = 5.0;
    Creature w("w", &f.worker, &f.seat); w.mMood = CreatureMoodLevel::Furious; w.mHangoverTurns = 5.0;
    expect(!w.wantsSpaBath(), "workers never bathe");
    Creature h("h", &f.small, &f.seat); h.mMood = CreatureMoodLevel::Furious; h.mHangoverTurns = 5.0; h.mIsInHand = true;
    expect(!h.wantsSpaBath(), "no bath in the hand");
    Creature p("p", &f.small, &f.seat); p.mMood = CreatureMoodLevel::Furious; p.mHangoverTurns = 5.0; p.mPrison = true;
    expect(!p.wantsSpaBath(), "no bath in prison");
    Seat rogue; rogue.rogue = true;
    Creature r("r", &f.small, &rogue); r.mMood = CreatureMoodLevel::Furious; r.mHangoverTurns = 5.0;
    expect(!r.wantsSpaBath(), "rogue creatures never bathe");
    expect(c.wantsSpaBath(), "control: the same creature without the exclusions bathes");
}

// ---- Payment, acceptance, no queue
static void checkPayment()
{
    Fixture f; Creature c("c", &f.small, &f.seat);
    ConfigManager::getSingleton().tavern["BeerPrice"] = 5;
    f.room->mPayer = SpaPayer::keeper;
    f.seat.gold = 4; expect(!f.room->canPay(c), "keeper short of 4 gold"); expect(!f.room->canAccept(c), "no coin, no bath (keeper)");
    expect(!f.room->payForBath(c) && f.seat.gold == 4, "failed payment takes nothing (keeper)");
    f.seat.gold = 5; expect(f.room->canPay(c) && f.room->canAccept(c), "keeper pays with exactly 5 gold");
    expect(f.room->payForBath(c) && f.seat.gold == 0, "keeper payment takes the beer price from the treasury");
    f.room->mPayer = SpaPayer::creature;
    f.seat.gold = 1000; c.mGold = 4;
    expect(!f.room->canPay(c) && !f.room->canAccept(c), "no coin, no bath (creature), the treasury does not help");
    expect(!f.room->payForBath(c) && c.mGold == 4 && f.map.seatGold == 0, "failed payment takes nothing (creature)");
    c.mGold = 5; expect(f.room->canAccept(c), "creature pays with exactly 5 gold");
    expect(f.room->payForBath(c) && c.mGold == 0 && f.map.seatGold == 5 && f.seat.gold == 1000, "the purse pays into the seat");
    // The price follows the key
    ConfigManager::getSingleton().tavern["BeerPrice"] = 8; c.mGold = 7;
    expect(!f.room->canPay(c), "the price follows BeerPrice"); c.mGold = 8; expect(f.room->canPay(c), "price 8");
    ConfigManager::getSingleton().tavern["BeerPrice"] = 5;
    // Workers and creatures of another seat are refused
    f.room->mPayer = SpaPayer::keeper; f.seat.gold = 100;
    Creature w("w", &f.worker, &f.seat); expect(!f.room->canAccept(w), "no worker");
    Seat other; other.gold = 100; Creature o("o", &f.small, &other); expect(!f.room->canAccept(o), "no creature of another seat");
    // A full pool takes nobody, no queue: nine 1x1 bathers fill the pool, the tenth is refused, the 2x2 is refused earlier
    std::vector<Creature*> bathers;
    for(int i = 0; i < 9; ++i)
    {
        Creature* b = new Creature("b" + std::to_string(i), &f.small, &f.seat);
        expect(f.room->canAccept(*b), "free place " + std::to_string(i));
        f.startBathFor(*b); bathers.push_back(b);
    }
    Creature tenth("t", &f.small, &f.seat); expect(!f.room->canAccept(tenth), "full pool, no queue");
    for(std::size_t i = 0; i < bathers.size(); ++i) delete bathers[i];
    // A 2x2 body needs a free 2x2 block: one bather in the middle of the pool blocks it
    Fixture g; Creature mid("mid", &g.small, &g.seat); g.seat.gold = 100;
    RoomSpaBather b(&mid); b.mBlock.mX = 2; b.mBlock.mY = 2; g.room->mBathers.push_back(b);
    Creature giant("giant", &g.big, &g.seat); expect(!g.room->canAccept(giant), "2x2 body refused while the middle is taken");
    Creature small("small", &g.small, &g.seat); expect(g.room->canAccept(small), "1x1 still fits");
}

// ---- The bath, the end of the bath and the fading
static void checkBath(uint32_t level, double expectedRelax)
{
    Fixture f; f.seat.spaLevel = level; Creature c("c", &f.medium, &f.seat);
    c.mMood = CreatureMoodLevel::Upset; c.mHangoverTurns = 100.0; c.mSpaMood = 0.0; c.mCreatureDirt = 7.0;
    c.mTavernMood = -10.0; c.mTavernMoodTurns = 200.0;
    f.room->mPayer = SpaPayer::keeper; f.seat.gold = 50;
    expect(f.room->payForBath(c) && f.seat.gold == 45, "the bath costs 5");
    f.startBathFor(c);
    expect(c.mSpaBathing, "the bath marks the creature as bathing (no fading)");
    int turns = 0; double moodAfter14 = 0.0;
    while(!f.room->mBathers.empty() && !f.room->mBathers.back().mDone && turns < 500)
    {
        c.upkeepSpaState(); f.room->upkeepBathers(); ++turns;
        if(turns == 14) moodAfter14 = c.mSpaMood;
        if(turns < 15) expectNear(c.mSpaMood, std::min(300.0, 21.0 * turns), "mood +21 per turn, turn " + std::to_string(turns));
    }
    expect(turns == 15, "the bath lasts 15 turns (14.2857 counted), took " + std::to_string(turns));
    expectNear(moodAfter14, 294.0, "mood after 14 turns");
    expectNear(c.mSpaMood, 300.0, "mood limited to 300");
    expectNear(c.mRelaxTurns, expectedRelax, "relaxation at research level " + std::to_string(level));
    expectNear(c.mHangoverTurns, 0.0, "the hangover ends at once");
    expectNear(c.mTavernMood, 0.0, "the tavern mood malus ends at once"); expectNear(c.mTavernMoodTurns, 0.0, "its timer too");
    expect(f.room->posts == 1, "one post written");
    expectNear(c.mCreatureDirt, 7.0, "the bath does not change the creature dirt");
    expect(c.mSpaMudTilesLeft == 3, "three mud tiles to go");
    expect(!c.mSpaBathing && f.room->mBathers.back().mDone, "bath over");
    expect(f.seat.gold == 45, "no second payment");
    // The mood fades by 0.4 per turn, the relaxation by 1 per turn, 750 turns from the full value
    int fade = 0;
    while(c.mSpaMood > 0.0 && fade < 2000) { c.upkeepSpaState(); ++fade; }
    expect(fade == 750, "the spa mood fades in 750 turns, took " + std::to_string(fade));
    // The relaxation runs out after ceil(relax) turns and never goes below 0; the work factor follows it
    Creature d("d", &f.small, &f.seat); d.setRelaxTurns(expectedRelax);
    expectNear(d.getRelaxWorkFactor(), 1.0567, "work factor while relaxed");
    int relaxed = 0;
    while(d.mRelaxTurns > 0.0 && relaxed < 2000) { d.upkeepSpaState(); ++relaxed; }
    expect(relaxed == static_cast<int>(std::ceil(expectedRelax - 1e-9)), "relaxation lasts " + std::to_string(relaxed) + " turns");
    expectNear(d.mRelaxTurns, 0.0, "relaxation never negative"); expectNear(d.getRelaxWorkFactor(), 1.0, "work factor 1 when the relaxation is over");
}

// ---- Clamp
static void checkMoodClamp()
{
    Fixture f; Creature c("c", &f.small, &f.seat);
    c.addSpaMood(21.0); expectNear(c.mSpaMood, 21.0, "add");
    c.addSpaMood(5000.0); expectNear(c.mSpaMood, 300.0, "clamped to SpaMoodMax");
    c.addSpaMood(-9000.0); expectNear(c.mSpaMood, 0.0, "clamped to 0");
    c.setSpaMood(-3.0); expectNear(c.mSpaMood, 0.0, "set below 0");
    c.setSpaMood(2000.0); expectNear(c.mSpaMood, 300.0, "set above the maximum");
    c.setRelaxTurns(-4.0); expectNear(c.mRelaxTurns, 0.0, "relaxation not below 0");
    c.setSpaMudTilesLeft(-2); expect(c.mSpaMudTilesLeft == 0, "mud counter not below 0");
    // A creature outside the bath fades, a bathing creature does not
    c.setSpaMood(100.0); c.upkeepSpaState(); expectNear(c.mSpaMood, 99.6, "fading by 0.4 per turn");
    c.mSpaBathing = true; c.upkeepSpaState(); expectNear(c.mSpaMood, 99.6, "no fading in the bath");
    // The mood bonus is a mood part: at 300 the mood sum is raised by that much (the sum is the mood manager's job)
}

// ---- Mud trail
static void checkMudTrail()
{
    Fixture f; Creature c("c", &f.small, &f.seat); c.mCreatureDirt = 7.0; f.small.dirtFactor = 1.5;
    c.mSpaMudTilesLeft = 3;
    std::vector<Tile> path; for(int i = 0; i < 6; ++i) path.push_back(Tile(i, 0));
    path[0].pool = true; path[1].pool = true; // two pool tiles first: nothing happens, the counter stays
    for(int i = 0; i < 6; ++i) c.testMudTrail(&path[i]);
    expectNear(path[0].dirt, 0.0, "no mud on a pool tile"); expectNear(path[1].dirt, 0.0, "no mud on the second pool tile");
    for(int i = 2; i < 5; ++i) expectNear(path[i].dirt, 4.4252 / 3.0 * 1.5, "mud on the tile " + std::to_string(i), 1e-9);
    expectNear(path[5].dirt, 0.0, "the fourth tile outside the pool stays clean");
    expect(c.mSpaMudTilesLeft == 0, "counter used up");
    expectNear(c.mCreatureDirt, 7.0, "creature dirt unchanged");
    expectNear(path[2].dirt + path[3].dirt + path[4].dirt, 4.4252 * 1.5, "the three tiles hold SpaDirtPerBath times the DirtFactor", 1e-9);
}

// ---- A bath that is broken off
static void checkBrokenOff()
{
    for(int cause = 0; cause < 6; ++cause)
    {
        Fixture f; Creature c("c", &f.small, &f.seat); c.mHangoverTurns = 90.0; f.seat.gold = 50;
        f.room->payForBath(c);
        RoomSpaBather& bather = f.startBathFor(c);
        for(int i = 0; i < 10; ++i) { c.upkeepSpaState(); f.room->upkeepBathers(); }
        expectNear(c.mSpaMood, 210.0, "mood so far");
        if(cause == 0) c.mFighting = true;
        if(cause == 1) c.mFriendlyFight = true;
        if(cause == 2) c.mFleeing = true;
        if(cause == 3) c.mKo = true;
        if(cause == 4) c.mDragged = true;
        if(cause == 5) c.mOnMap = false;
        (void)bather;
        f.room->abortDisturbedBathers();
        expect(f.room->mBathers.empty(), "the place is released, cause " + std::to_string(cause));
        expectNear(c.mSpaMood, 210.0, "the mood gained so far stays, cause " + std::to_string(cause));
        expectNear(c.mRelaxTurns, 0.0, "no relaxation, cause " + std::to_string(cause));
        expectNear(c.mHangoverTurns, 90.0, "the hangover stays, cause " + std::to_string(cause));
        expect(f.seat.gold == 45 && f.map.seatGold == 0 && c.mGold == 0, "no refund, cause " + std::to_string(cause));
        expect(!c.mSpaBathing && f.room->posts == 0 && c.mSpaMudTilesLeft == 0, "nothing else happens, cause " + std::to_string(cause));
        // A normal bather stays
    }
    Fixture f; Creature c("c", &f.small, &f.seat);
    f.startBathFor(c); f.room->abortDisturbedBathers();
    expect(f.room->mBathers.size() == 1, "an undisturbed bather stays");
    // A running jump is cancelled
    Creature j("j", &f.small, &f.seat); RoomSpaBather b(&j); b.mState = SpaBatherState::jumping; b.mBlock.mX = 3; b.mBlock.mY = 3;
    f.room->mBathers.push_back(b); j.mJumping = true; j.mFighting = true;
    f.room->abortDisturbedBathers();
    expect(j.cancelJumpCalls == 1 && f.room->mBathers.size() == 1, "a jump is cancelled when the bather is disturbed");
    // A jump in the air lands, the bath starts: after the jump ends the state is bathing
    Fixture g; Creature k("k", &g.small, &g.seat); RoomSpaBather jb(&k); jb.mState = SpaBatherState::jumping; jb.mBlock.mX = 1; jb.mBlock.mY = 1;
    g.room->mBathers.push_back(jb); k.mJumping = false;
    g.room->upkeepBathers();
    expect(g.room->mBathers.back().mState == SpaBatherState::bathing && k.mSpaBathing, "the landing starts the bath");
    expect(g.seat.gold == 95 && k.splashes == 1 && k.clearCalls == 0, "the landing pays the bath once");
    for(int i = 0; i < 5; ++i) g.room->upkeepBathers();
    expect(g.seat.gold == 95, "a running bath is never paid again");
    // A jump that is broken off before the landing was never paid: nothing is lost
    Fixture h; Creature m("m", &h.small, &h.seat); RoomSpaBather mb(&m); mb.mState = SpaBatherState::jumping; mb.mBlock.mX = 1; mb.mBlock.mY = 1;
    h.room->mBathers.push_back(mb); m.mJumping = true; m.mFighting = true;
    h.room->abortDisturbedBathers();
    expect(h.room->mBathers.empty() && h.seat.gold == 100 && h.map.seatGold == 0, "a jump broken off before the landing costs nothing");
    // A payment that fails at the landing releases the place and ends the visit without a bath
    Fixture n; Creature o("o", &n.small, &n.seat); RoomSpaBather ob(&o); ob.mState = SpaBatherState::jumping; ob.mBlock.mX = 1; ob.mBlock.mY = 1;
    n.room->mBathers.push_back(ob); o.mJumping = false; n.seat.gold = 4;
    n.room->upkeepBathers();
    expect(n.room->mBathers.back().mState == SpaBatherState::jumping && !o.mSpaBathing && o.clearCalls == 1 && n.seat.gold == 4,
           "a failed payment at the landing starts no bath and releases the place");
    // The creature pays itself: a purse that was emptied during the jump fails at the landing
    Fixture q; q.room->mPayer = SpaPayer::creature; Creature r("r", &q.small, &q.seat); r.mGold = 50; RoomSpaBather rb(&r);
    rb.mState = SpaBatherState::jumping; rb.mBlock.mX = 1; rb.mBlock.mY = 1; q.room->mBathers.push_back(rb); r.mJumping = true;
    r.mGold = 0; r.mJumping = false; q.room->upkeepBathers();
    expect(!r.mSpaBathing && r.clearCalls == 1 && q.map.seatGold == 0, "a purse emptied in the air fails at the landing");
}

int main()
{
    loadConfig();
    checkTrigger();
    checkPayment();
    checkBath(0, @@RELAX0@@);
    checkBath(1, @@RELAX1@@);
    checkBath(2, @@RELAX2@@);
    checkBath(3, @@RELAX3@@);
    checkMoodClamp();
    checkMudTrail();
    checkBrokenOff();
    if(failures == 0) std::cout << "spa rules ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

# The pieces of the sources
mood_h = read('source/creaturemood/CreatureMood.h')
mood_level = mood_h[mood_h.index('enum class CreatureMoodLevel'):]
mood_level = mood_level[:mood_level.index('};') + 2]
creature_functions = '\n'.join(extract(creature_cpp, h) for h in [
    'void Creature::setHangoverTurns(', 'void Creature::addTavernMood(', 'void Creature::addSpaMood(', 'void Creature::setSpaMood(', 'void Creature::setRelaxTurns(',
    'double Creature::getRelaxWorkFactor(', 'void Creature::setSpaMudTilesLeft(', 'bool Creature::wantsSpaBath(',
    'void Creature::upkeepSpaState('])
trail_start = creature_cpp.index('    if((mSpaMudTilesLeft > 0) && !RoomSpa::isPoolTile(tile))')
trail_end = creature_cpp.index('\n    }\n', trail_start) + len('\n    }')
mud_trail = creature_cpp[trail_start:trail_end]
types_start = room_h.index('//! \\brief Who pays for the bath a lava spa gives.')
types_end = room_h.index('//! \\brief The pool attendant read from a saved room')
room_types = room_h[types_start:types_end]
helpers = extract(room_cpp, 'double getTavernValue(')
room_functions = '\n'.join(extract(room_cpp, h) for h in [
    'SpaTileSet RoomSpa::getCoveredSet(', 'SpaTileSet RoomSpa::getPoolSet(', 'SpaTileSet RoomSpa::getTakenSet(',
    'std::vector<RoomSpaBather>::iterator RoomSpa::findBatherOf(', 'bool RoomSpa::canPay(', 'bool RoomSpa::payForBath(',
    'bool RoomSpa::canAccept(', 'void RoomSpa::startBath(', 'bool RoomSpa::landJump(', 'void RoomSpa::finishBath(', 'void RoomSpa::upkeepBathers(',
    'bool RoomSpa::isBatherDisturbed(', 'void RoomSpa::abortDisturbedBathers('])
assert 'mCreatureDirt' not in room_functions and 'washed' not in room_functions, 'the cut-out room code never touches the creature dirt'

relax_base = float(rooms['SpaRelaxTurns'])
factors = [float(v) for v in effect_line.groups()]
replacements = {
    '@@ROOM_CONFIG@@': room_table,
    '@@TAVERN_CONFIG@@': tavern_table,
    '@@EFFECTS@@': effect_table,
    '@@MOOD_LEVEL@@': mood_level,
    '@@CREATURE_FUNCTIONS@@': creature_functions,
    '@@MUD_TRAIL@@': mud_trail,
    '@@ROOM_TYPES@@': 'struct Creature; struct Tile;\n' + room_types,
    '@@ROOM_HELPERS@@': helpers,
    '@@ROOM_FUNCTIONS@@': room_functions,
    '@@RELAX0@@': repr(relax_base),
    '@@RELAX1@@': repr(relax_base * factors[0]),
    '@@RELAX2@@': repr(relax_base * factors[1]),
    '@@RELAX3@@': repr(relax_base * factors[2]),
}
for token, text in replacements.items():
    assert token in probe, token
    probe = probe.replace(token, text)

with tempfile.TemporaryDirectory(prefix='odp-spa-rules-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', '/I' + str(root / 'source' / 'rooms'),
                    'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('spa rules ok')
