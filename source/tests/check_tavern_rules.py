"""Tavern and thirst rules: the real functions of the thirst model and of the tavern are cut out of the sources and run
against small stubs; the random rolls are scripted so that every threshold is hit from both sides.

What is run (the function bodies are taken from the source files, not copied by hand):
  Creature::increaseThirst / setThirst / drinkTaken / increaseUrge / setDrunk / setHangoverTurns / addTavernMood /
  isStaggering / getHangoverWorkFactor / sleepStarted / sleepEnded / upkeepTavernState
                      thirst growth and the clamp at 100, rogue creatures and types without thirst (no hunger, no thirst),
                      the notice at 100, a drink sets thirst 0 and raises the urge (beer 15, water 5), beer adds 25
                      drunkenness (cap 100) and water none, decay 0.5 per turn, stagger at 50, the vomit mark is reset
                      below 75, a hangover of 252 turns after a sleep that started above 50 (not shortened, mood -10,
                      half work), the tavern mood value and its timer
  RoomTavern::servesBeer / payForBeer / finishDrink / tryStartGame / startGame / playContestTurn / playDuelTurn /
  cheerSpectators / concludeGame / abortGame / abortDisturbedGuests / knockOut / upkeepSpots / addDrinkDirt
                      beer only with the research, both payment paths and their fallbacks to water, the drink chain
                      50 / 25 / 12.5 / 6.25 percent with the cap of five, the 50 percent game chance and the neighbour
                      rule, the draw of the three games (the slap duel only with beer), the underdog chances with the
                      floor of 5 percent, underdog mood and double experience, spectators, the slap duel (10 HP per hit,
                      critical chance 10 +- 0.25 per level, knock-out at a critical or below 30 HP, HP never below 1,
                      the time limit), 42 turns lying then getting up, a fight, a flight, a knock-out or a pick-up ends a
                      game without effects
  CreatureMoodThirst::computeMood      the same numbers as the hunger mood, for prisoners as for every seat creature
  RoomPortal getResearchedCooldown     the portal cooldown factors 1.0 / 0.9 / 0.8 per Beer level
The values come from config/global.cfg [Tavern] and config/rooms.cfg. The source wiring (where thirst is sought, where the
hangover factor is used, the vomit pile) is checked on the source text.

Calls (from the repository root):
  python source/tests/check_tavern_rules.py

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


# Returns the line of a text that matches a regular expression.
def find_line(text, pattern):
    match = re.search(pattern, text, re.M)
    assert match is not None, pattern
    return match.group(0)


creature_cpp = read('source/entities/Creature.cpp')
room_cpp = read('source/rooms/RoomTavern.cpp')
portal_cpp = read('source/rooms/RoomPortal.cpp')
mood_thirst_cpp = read('source/creaturemood/CreatureMoodThirst.cpp')
mood_hunger_cpp = read('source/creaturemood/CreatureMoodHunger.cpp')
global_cfg = read('config/global.cfg')
rooms_cfg = read('config/rooms.cfg')
skills_cfg = read('config/skills.cfg')

# ---- Source wiring -----------------------------------------------------------------------------------------------
# Thirst grows where hunger grows (rogue creatures are skipped by the same condition) and the idle decision seeks a tavern
growth_at = creature_cpp.index('increaseThirst(mDefinition->getThirstGrowthPerTurn());')
assert 'increaseHunger(mDefinition->getHungerGrowthPerTurn());' in creature_cpp[growth_at - 400:growth_at]
assert 'if(getSeat()->isRogueSeat())' in creature_cpp[growth_at - 800:growth_at], 'thirst growth is split for rogue creatures (they grow directly)'
seek = creature_cpp[creature_cpp.index('// If we are thirsty, we go to a tavern'):]
seek = seek[:seek.index('return true;')]
assert 'getTavernConfigDouble("ThirstSeek")' in seek and 'isWorker()' in seek and 'hasThirst()' in seek, 'seek at ThirstSeek, never for workers or types without thirst'
food_at = creature_cpp.index('pushAction(Utils::make_unique<CreatureActionSearchFood>')
assert food_at < creature_cpp.index('CreatureActionSearchDrink>(*this'), 'the thirst check follows the hunger check'
# The upkeep of the tavern state runs every turn; a staggering creature is slower
assert 'upkeepTavernState();' in creature_cpp
assert creature_cpp.count('getTavernConfigDouble("StaggerSpeedFactor")') == 2 and creature_cpp.count('if(isStaggering())') == 2
# One vomit per drunk episode at VomitAt, with a vomit pile of the dirt model
vomit_check = creature_cpp[creature_cpp.index('// If we are drunk enough, we vomit once per drunk episode'):]
vomit_check = vomit_check[:vomit_check.index('return true;')]
assert '!mVomited' in vomit_check and 'getTavernConfigDouble("VomitAt")' in vomit_check and 'mVomited = true;' in vomit_check
vomit_action = read('source/creatureaction/CreatureActionVomit.cpp')
assert 'DirtPileEntity::createOnTile(mCreature.getGameMap(), myTile, DirtPileKind::vomit' in vomit_action
assert 'vomit_anim' in vomit_action and '"DrinkTurns"' in vomit_action
# A hangover halves the room points and the experience of the library, the workshop, the training hall and the arena
for path, token in (('source/rooms/RoomLibrary.cpp', 'creature.getHangoverWorkFactor()'), ('source/rooms/RoomWorkshop.cpp', 'creature.getHangoverWorkFactor()'),
                    ('source/rooms/RoomTrainingHall.cpp', 'creature.getHangoverWorkFactor()')):
    assert token in read(path), path + ' must use the hangover work factor'
assert 'getHangoverWorkFactor()' in creature_cpp[creature_cpp.index('attackRoom->getDirtOutputFactor()') - 200:creature_cpp.index('attackRoom->getDirtOutputFactor()') + 200]
# The sleep start and end notes are called by the sleep action
sleep_cpp = read('source/creatureaction/CreatureActionSleep.cpp')
assert 'sleepStarted()' in sleep_cpp and 'sleepEnded()' in sleep_cpp
# The tavern mood is summed with the other mood parts, the thirst mood has the same numbers as the hunger mood and checks
# neither a seat nor a prison: prisoners get the malus like every seat creature, seat-less heroes have no mood at all
assert 'getTavernMood()' in read('source/creaturemood/CreatureMoodManager.cpp')
for text in (mood_thirst_cpp, mood_hunger_cpp):
    compute = extract(text, 'double CreatureMood' + ('Thirst' if text is mood_thirst_cpp else 'Hunger') + '::computeMood(')
    assert 'getSeat' not in compute and 'Prison' not in compute and 'isPrisoner' not in compute, 'the thirst/hunger mood is the same for every creature'
# Games end without effects on a fight, a flight, a knock-out, a pick-up
disturbed = extract(room_cpp, 'bool RoomTavern::isGuestDisturbed(')
for token in ('isKo()', 'isBeingDragged()', 'CreatureActionType::fight', 'CreatureActionType::flee'):
    assert token in disturbed, token
# The loser of a slap duel goes to its bed after the visit, whatever its wakefulness
assert 'CreatureActionSleep' in extract(room_cpp, 'bool RoomTavern::useRoom(') and 'goToBed' in room_cpp

# ---- Probe -------------------------------------------------------------------------------------------------------
tavern = block_values(global_cfg, 'Tavern')
rooms = block_values(rooms_cfg, 'Rooms')
config_entries = [(k, v) for k, v in tavern.items()] + [('Room' + k, rooms[k]) for k in ('TavernDirtPerDrink', 'PortalCooldownSpawnMin', 'PortalCooldownSpawnMax',
    'TavernDuelMaxTurnsFactor', 'TavernDrinkChainHalving')]
config_table = ',\n'.join('    {"%s", %s}' % (k, v) for k, v in config_entries)
effect_line = re.search(r'^\s*tavernBeer\s+PortalCooldown\s+mul\s+(\S+)\s+(\S+)\s+(\S+)\s*$', skills_cfg, re.M)
assert effect_line is not None, 'the portal cooldown effect line is missing'
effect_table = ', '.join(effect_line.groups())

probe = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <string>
#include <vector>

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
    Real squaredLength() const { return x * x + y * y + z * z; }
    void normalise() { Real l = std::sqrt(squaredLength()); if(l > 0) { x /= l; y /= l; z /= l; } }
    static const Vector3 ZERO;
};
const Vector3 Vector3::ZERO(0, 0, 0);
}

// ---- Scripted random numbers: a roll takes the next scripted value; without one a double roll fails every chance
// (100) and an integer roll takes its lower bound
namespace Random
{
static std::vector<double> doubles; static std::vector<uint32_t> uints; static unsigned doublePos = 0, uintPos = 0;
static uint32_t lastUintMax = 0;
static void script(const std::vector<double>& d, const std::vector<uint32_t>& u) { doubles = d; uints = u; doublePos = 0; uintPos = 0; lastUintMax = 0; }
static double Double(double a, double b) { return (doublePos < doubles.size()) ? doubles[doublePos++] : 100.0; }
static uint32_t Uint(uint32_t a, uint32_t b) { lastUintMax = b; return (uintPos < uints.size()) ? uints[uintPos++] : a; }
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
    double getTavernConfigDouble(const std::string& key) const { return lookup(key); }
    double getRoomConfigDouble(const std::string& key) const { return lookup("Room" + key); }
    uint32_t getRoomConfigUInt32(const std::string& key) const { return static_cast<uint32_t>(lookup("Room" + key)); }
    //! \brief Returns the shipped room value; the probe needs every key in the config, so the default is not used.
    double getRoomConfigDoubleOrDefault(const std::string& key, double) const { return lookup("Room" + key); }
    double getDirtConfigDouble(const std::string& key) const { return lookup(key); }
};
static void loadConfig()
{
    static const struct { const char* key; double value; } table[] = {
@@CONFIG@@
    };
    for(unsigned i = 0; i < sizeof(table) / sizeof(table[0]); ++i)
        ConfigManager::getSingleton().values[table[i].key] = table[i].value;
}

enum class SkillType { tavernBeer, other };
enum class CreatureActionType { fight, fightFriendly, flee, other };
enum class ResearchEffect { PortalCooldown };
struct EntityAnimation { static const std::string idle_anim; static const std::string slap_anim; };
const std::string EntityAnimation::idle_anim = "Idle";
const std::string EntityAnimation::slap_anim = "Slap";
@@DRINKKIND@@
static const double THIRST_STATE_MAX = 100.0;
static const double NEED_MAX = 100.0;

struct Creature; struct Tile; struct GameMap; struct Seat;

struct Tile
{
    int x, y; double dirt;
    Tile(int ax, int ay) : x(ax), y(ay), dirt(0.0) {}
    int getX() const { return x; } int getY() const { return y; }
    void addDirt(double amount) { dirt += amount; }
};

struct Player
{
    int notices; bool human;
    Player() : notices(0), human(true) {}
    void notifyTavernEvent() { ++notices; }
    bool getIsHuman() const { return human; }
};

// The seat: rogue flag, id, level of the Beer research and the player
struct Seat
{
    bool rogue; int id; uint32_t beerLevel; Player* player;
    Seat() : rogue(false), id(1), beerLevel(0), player(nullptr) {}
    bool isRogueSeat() const { return rogue; }
    int getId() const { return id; }
    uint32_t getSkillLevel(SkillType type) const { return (type == SkillType::tavernBeer) ? beerLevel : 0; }
    Player* getPlayer() const { return player; }
};

struct CreatureDefinition
{
    bool thirsty;
    explicit CreatureDefinition(bool t) : thirsty(t) {}
    bool hasThirst() const { return thirsty; }
};

//! \brief Supplies tavern creature state with the production fractional purse API.
struct Creature
{
    CreatureDefinition* mDefinition; Seat* mSeat; std::string mName; Tile* mTile; Ogre::Vector3 mPos;
    double mUrge, mThirst, mTavernMood, mTavernMoodTurns, mDrunk, mHangoverTurns, mHp, mExp;
    bool mVomited, mHangoverPending, mOnMap, mAlive, mKo, mDragged, mPossessed, mFighting, mFleeing, mHit;
    uint32_t mLevel; double mGold; int takeDamageCalls;
    //! \brief Initializes the tavern creature with the production fractional gold balance.
    Creature(const std::string& name, CreatureDefinition* def, Seat* seat, uint32_t level)
      : mDefinition(def), mSeat(seat), mName(name), mTile(nullptr), mUrge(0.0), mThirst(0.0), mTavernMood(0.0), mTavernMoodTurns(0.0), mDrunk(0.0),
        mHangoverTurns(0.0), mHp(100.0), mExp(0.0), mVomited(false), mHangoverPending(false), mOnMap(true), mAlive(true), mKo(false),
        mDragged(false), mPossessed(false), mFighting(false), mFleeing(false), mHit(true), mLevel(level), mGold(0), takeDamageCalls(0) {}
    Seat* getSeat() const { return mSeat; }
    CreatureDefinition* getDefinition() const { return mDefinition; }
    const std::string& getName() const { return mName; }
    bool getIsOnServerMap() const { return true; }
    bool getIsOnMap() const { return mOnMap; }
    bool isAlive() const { return mAlive; }
    bool isKo() const { return mKo; }
    bool isBeingDragged() const { return mDragged; }
    bool isPossessed() const { return mPossessed; }
    bool isActionInList(CreatureActionType type) const
    { return ((type == CreatureActionType::fight) && mFighting) || ((type == CreatureActionType::flee) && mFleeing); }
    uint32_t getLevel() const { return mLevel; }
    double getHP() const { return mHp; }
    double getAttackRating() const { return 300.0; }
    bool rollAttackHit(double attackRating, uint32_t attackerLevel, bool possessed) const { return mHit; }
    double takeDamage(Creature* attacker, double absoluteDamage, double a, double b, double c, Tile* tile, bool d)
    { ++takeDamageCalls; mHp -= absoluteDamage; return absoluteDamage; }
    void receiveExp(double xp) { mExp += xp; }
    //! \brief Returns the full production purse balance without narrowing.
    double getGoldCarried() const { return mGold; }
    //! \brief Applies the production fractional purse charge.
    void addGoldCarried(double gold) { mGold += gold; }
    Tile* getPositionTile() const { return mTile; }
    const Ogre::Vector3& getPosition() const { return mPos; }
    void setAnimationState(const std::string& state, bool loop = true, const Ogre::Vector3& direction = Ogre::Vector3::ZERO, bool idle = true) {}
    void increaseUrge(double value);
    void increaseThirst(double value);
    void setThirst(double val);
    void setDrunk(double val);
    void setHangoverTurns(double turns);
    void addTavernMood(double points, double turns);
    void drinkTaken(DrinkKind kind);
    bool isStaggering() const;
    double getHangoverWorkFactor() const;
    void sleepStarted();
    void sleepEnded();
    void upkeepTavernState();
};
@@CREATURE_FUNCTIONS@@

//! \brief Supplies tavern tiles and production fractional keeper balances.
struct GameMap
{
    int sizeX, sizeY; std::vector<Tile> tiles; double treasury, seatGold; std::vector<Creature*> creatures;
    //! \brief Initializes the tavern map with fractional treasury and seat balances.
    GameMap(int x, int y) : sizeX(x), sizeY(y), treasury(0), seatGold(0) { for(int yy = 0; yy < y; ++yy) for(int xx = 0; xx < x; ++xx) tiles.push_back(Tile(xx, yy)); }
    Tile* getTile(int x, int y) { return ((x < 0) || (y < 0) || (x >= sizeX) || (y >= sizeY)) ? nullptr : &tiles[y * sizeX + x]; }
    //! \brief Withdraws the complete production amount from the treasury fixture.
    bool withdrawFromTreasuries(double gold, Seat* seat) { if(treasury < gold) return false; treasury -= gold; return true; }
    //! \brief Credits the complete production amount to the seat fixture.
    void addGoldToSeat(double gold, int seatId) { seatGold += gold; }
    const std::vector<Creature*>& getCreaturesBySeat(Seat* seat) const { return creatures; }
};

struct InnkeeperEntity { int drinks, cheers; InnkeeperEntity() : drinks(0), cheers(0) {} void onDrink() { ++drinks; } void onCheer() { ++cheers; } };

struct Room
{
    GameMap* mMap; Seat* mSeat; std::vector<Tile*> mCoveredTiles;
    Room(GameMap* map, Seat* seat) : mMap(map), mSeat(seat) {}
    GameMap* getGameMap() const { return mMap; }
    Seat* getSeat() const { return mSeat; }
};
@@ROOM_TYPES@@
@@ROOM_CONSTANTS@@
@@ROOM_HELPERS@@

enum class CosmeticTavernKind { beer = 0, water = 1, duelWon = 2, duelLost = 3, vomit = 4 };

class RoomTavern : public Room
{
public:
    RoomTavern(GameMap* map, Seat* seat) : Room(map, seat), mPayer(TavernPayer::keeper), mCounterTile(nullptr), mInnkeeper(nullptr), events(0), lastKind(-1) {}
    bool servesBeer() const;
    static void addDrinkDirt(Tile* tile);
    void sendTavernEvent(Creature& creature, int32_t kind, const Creature* opponent) { ++events; lastKind = kind; kinds.push_back(kind); }
    void playSoundAt(Tile* tile, const std::string& family) {}
    void showSpotState(Tile* tile, RoomTavernSpot& spot) {}
    std::map<Tile*, RoomTavernSpot>::iterator findSpotOf(const Creature* creature);
    void setSpotDone(RoomTavernSpot& spot, int32_t turns);
    void setSpotState(RoomTavernSpot& spot, TavernGuestState state, int32_t turns);
    void upkeepSpots();
    void abortDisturbedGuests();
    void finishDrink(Tile* tile, RoomTavernSpot& spot);
    bool payForBeer(Creature& creature, bool& noCoin);
    bool isFreeSpotTile(Tile* tile) const;
    Tile* pickFreeSpotTile(const Creature& creature) const;
    void tryStartGame(Tile* tile);
    void startGame(Tile* tileA, Tile* tileB);
    void playContestTurn(std::map<Tile*, RoomTavernGame>::iterator it);
    void playDuelTurn(std::map<Tile*, RoomTavernGame>::iterator it);
    void concludeGame(std::map<Tile*, RoomTavernGame>::iterator it, Creature* winner, uint32_t underdogLevels);
    void abortGame(std::map<Tile*, RoomTavernGame>::iterator it);
    void knockOut(RoomTavernSpot& spot);
    void cheerSpectators(const RoomTavernGame& game);
    static bool isGuestDisturbed(const Creature& creature);
    TavernPayer mPayer;
    Tile* mCounterTile;
    InnkeeperEntity* mInnkeeper;
    std::map<Tile*, RoomTavernSpot> mSpots;
    std::map<Tile*, RoomTavernGame> mGames;
    int events; int lastKind; std::vector<int> kinds;
};
@@ROOM_FUNCTIONS@@

// ---- Portal cooldown: the research factor of the Beer levels
struct SkillManager
{
    static double getResearchValue(const Seat* seat, SkillType type, double base, ResearchEffect effect)
    {
        static const double factors[] = { @@EFFECTS@@ };
        uint32_t level = seat->getSkillLevel(type);
        return (level == 0) ? base : base * factors[std::min<uint32_t>(level, 3) - 1];
    }
};
@@PORTAL_FUNCTION@@

// ---- A tavern with guests for the tests
struct Fixture
{
    GameMap map; Seat seat; Player player; CreatureDefinition thirsty; RoomTavern room; InnkeeperEntity innkeeper;
    std::vector<Creature*> guests;
    Fixture() : map(12, 12), thirsty(true), room(&map, &seat)
    {
        seat.player = &player; room.mInnkeeper = &innkeeper;
        for(int i = 1; i < 10; ++i) room.mCoveredTiles.push_back(map.getTile(i, 5));
        room.mCounterTile = map.getTile(1, 5);
    }
    ~Fixture() { for(unsigned i = 0; i < guests.size(); ++i) delete guests[i]; }
    // Adds a guest on the tile (x, 5) with the given level and state
    Creature* guest(const std::string& name, int x, uint32_t level, TavernGuestState state, int32_t turns)
    {
        Creature* c = new Creature(name, &thirsty, &seat, level);
        c->mTile = map.getTile(x, 5); c->mPos = Ogre::Vector3(static_cast<float>(x), 5.0f, 0.0f);
        guests.push_back(c); map.creatures.push_back(c);
        RoomTavernSpot spot(c); spot.mState = state; spot.mTurnsLeft = turns;
        room.mSpots.insert(std::make_pair(c->mTile, spot));
        return c;
    }
    // Starts a game of the given kind between two guests that stand next to each other
    std::map<Tile*, RoomTavernGame>::iterator game(Creature* a, Creature* b, TavernGameKind kind, int32_t turns)
    {
        RoomTavernGame g; g.mKind = kind; g.mTileA = a->mTile; g.mTileB = b->mTile; g.mCreatureA = a; g.mCreatureB = b; g.mTurnsLeft = turns;
        room.mSpots.find(a->mTile)->second.mState = TavernGuestState::game; room.mSpots.find(b->mTile)->second.mState = TavernGuestState::game;
        room.mGames[a->mTile] = g; return room.mGames.find(a->mTile);
    }
    TavernGuestState stateOf(Creature* c) { return room.mSpots.find(c->mTile)->second.mState; }
};

// ---- Thirst, drunkenness, hangover
static void checkThirst()
{
    Seat seat; Player player; seat.player = &player; CreatureDefinition thirsty(true), dry(false);
    Creature c("C", &thirsty, &seat, 1);
    for(int i = 0; i < 800; ++i) c.increaseThirst(0.1);
    expectNear(c.mThirst, 80.0, "0.1 per turn reaches the seek value after 800 turns", 1e-6);
    expect(player.notices == 0, "no notice below 100");
    for(int i = 0; i < 300; ++i) c.increaseThirst(0.1);
    expectNear(c.mThirst, 100.0, "thirst is clamped at 100");
    expect(player.notices > 0, "the keeper is told at thirst 100");
    c.setThirst(250.0); expectNear(c.mThirst, 100.0, "setThirst clamps up"); c.setThirst(-3.0); expectNear(c.mThirst, 0.0, "setThirst clamps down");
    Seat rogue; rogue.rogue = true; Creature wild("W", &thirsty, &rogue, 1); wild.increaseThirst(50.0);
    expectNear(wild.mThirst, 0.0, "rogue creatures never get thirsty");
    Creature noHunger("Skeleton", &dry, &seat, 1); noHunger.increaseThirst(50.0); noHunger.setThirst(70.0);
    expectNear(noHunger.mThirst, 0.0, "a type without thirst never gets thirsty and a load cannot set it");
    Seat plain; Creature other("O", &thirsty, &plain, 1); other.setThirst(100.0); other.increaseThirst(1.0);
    expectNear(other.mThirst, 100.0, "no keeper, no notice, no crash");

    // A drink sets the thirst to 0 and raises the urge: beer 15 and water 5
    Creature d("D", &thirsty, &seat, 1); d.setThirst(95.0);
    d.drinkTaken(DrinkKind::water);
    expectNear(d.mThirst, 0.0, "water quenches"); expectNear(d.mUrge, 5.0, "water urge 5"); expectNear(d.mDrunk, 0.0, "water adds no drunkenness");
    d.setThirst(95.0); d.drinkTaken(DrinkKind::beer);
    expectNear(d.mThirst, 0.0, "beer quenches"); expectNear(d.mUrge, 20.0, "beer urge 15 on top"); expectNear(d.mDrunk, 25.0, "beer adds 25 drunkenness");
    for(int i = 0; i < 6; ++i) d.drinkTaken(DrinkKind::beer);
    expectNear(d.mDrunk, 100.0, "drunkenness is capped at 100");

    // Drunkenness falls by 0.5 per turn; stagger at 50; the vomit mark is reset below 75
    Creature s("S", &thirsty, &seat, 1); s.mDrunk = 49.5;
    expect(!s.isStaggering(), "49.5 does not stagger"); s.mDrunk = 50.0; expect(s.isStaggering(), "50 staggers"); s.mDrunk = 0.0; expect(!s.isStaggering(), "sober");
    s.mDrunk = 80.0; s.mVomited = true;
    for(int i = 0; i < 9; ++i) s.upkeepTavernState();
    expectNear(s.mDrunk, 75.5, "decay 0.5 per turn"); expect(s.mVomited, "still marked at 75.5");
    s.upkeepTavernState(); s.upkeepTavernState();
    expectNear(s.mDrunk, 74.5, "74.5"); expect(!s.mVomited, "the mark is reset below 75, so the next episode vomits again");
    s.mDrunk = 25.0; for(int i = 0; i < 50; ++i) s.upkeepTavernState();
    expectNear(s.mDrunk, 0.0, "25 drunkenness are gone after 50 turns");

    // Tavern mood: value and timer, a new drink refreshes both, 0 when the timer ends
    Creature m("M", &thirsty, &seat, 1); m.addTavernMood(15.0, 168.0);
    for(int i = 0; i < 167; ++i) m.upkeepTavernState();
    expectNear(m.mTavernMood, 15.0, "the mood holds for 167 turns");
    m.addTavernMood(15.0, 168.0);
    for(int i = 0; i < 167; ++i) m.upkeepTavernState();
    expectNear(m.mTavernMood, 15.0, "a new drink refreshes the timer");
    m.upkeepTavernState(); expectNear(m.mTavernMood, 0.0, "the mood is gone after 168 turns"); expectNear(m.mTavernMoodTurns, 0.0, "timer 0");

    // Hangover: only after a sleep that started above 50, 252 turns, half work, mood -10, not shortened
    Creature h("H", &thirsty, &seat, 1); h.mDrunk = 50.0; h.sleepStarted(); h.sleepEnded();
    expectNear(h.mHangoverTurns, 0.0, "exactly 50 does not give a hangover"); expectNear(h.getHangoverWorkFactor(), 1.0, "no hangover, full work");
    h.mDrunk = 50.5; h.sleepStarted(); h.sleepEnded();
    expectNear(h.mHangoverTurns, 252.0, "a hangover lasts 252 turns"); expectNear(h.mTavernMood, -66.6667, "hangover mood -66.6667");
    expectNear(h.mTavernMoodTurns, 252.0, "the mood lasts as long"); expectNear(h.getHangoverWorkFactor(), 0.5, "half work and experience");
    h.sleepEnded(); expectNear(h.mHangoverTurns, 252.0, "a second wake-up without drunk sleep changes nothing");
    h.mHangoverTurns = 300.0; h.mDrunk = 60.0; h.sleepStarted(); h.sleepEnded();
    expectNear(h.mHangoverTurns, 300.0, "sleeping again does not shorten the hangover");
    for(int i = 0; i < 300; ++i) h.upkeepTavernState();
    expectNear(h.mHangoverTurns, 0.0, "the hangover runs out one turn at a time");
}

// ---- Drinks, payment, the chain
//! \brief Tests the original drink rules and preserves fractional balances through both payment paths.
static void checkDrinks()
{
    // Without the research the tavern serves water: nothing is paid, no mood
    { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.map.treasury = 50; c->mThirst = 90.0;
      expect(!f.room.servesBeer(), "no beer without the research");
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.mSpots.find(c->mTile)->second);
      expect(f.map.treasury == 50 && c->mDrunk == 0.0 && c->mTavernMood == 0.0 && c->mThirst == 0.0, "water: free, no mood, thirst 0");
      expect(f.room.lastKind == 1, "a water event is sent"); expect(f.innkeeper.drinks == 1, "the innkeeper pours");
      expectNear(f.map.getTile(2, 5)->dirt, 0.29, "every drink dirties the tile", 1e-9); }
    // Beer paid by the keeper
    { Fixture f; f.seat.beerLevel = 1; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.map.treasury = 50;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.mSpots.find(c->mTile)->second);
      expect(f.map.treasury == 45 && c->mGold == 0, "the keeper pays 5 from the treasury");
      expectNear(c->mDrunk, 25.0, "beer: 25 drunkenness"); expectNear(c->mTavernMood, 100.0, "beer: mood +100"); expectNear(c->mTavernMoodTurns, 168.0, "beer: mood for 168 turns");
      expect(f.room.lastKind == 0, "a beer event is sent"); }
    // The keeper cannot pay: water, no malus
    { Fixture f; f.seat.beerLevel = 1; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.map.treasury = 4;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.mSpots.find(c->mTile)->second);
      expect(f.map.treasury == 4 && c->mDrunk == 0.0 && c->mTavernMood == 0.0, "an empty treasury gives water and no mood malus"); expect(f.room.lastKind == 1, "water event"); }
    // The creature pays from its purse; the gold goes to the treasury of the seat
    { Fixture f; f.seat.beerLevel = 1; f.room.mPayer = TavernPayer::creature; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); c->mGold = 12; f.map.treasury = 0;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.mSpots.find(c->mTile)->second);
      expect(c->mGold == 7 && f.map.seatGold == 5 && f.map.treasury == 0, "the creature pays 5 from its purse to the seat");
      expectNear(c->mTavernMood, 100.0, "beer mood"); expectNear(c->mDrunk, 25.0, "beer drunkenness"); }
    // Keep the original integer payment cases and preserve existing fractional balances as well.
    { Fixture f; Creature* c = f.guest("Fractional", 2, 1, TavernGuestState::drinking, 0); bool noCoin = true;
      f.map.treasury = 50.625; c->mGold = 12.375;
      expect(f.room.payForBeer(*c, noCoin) && !noCoin, "fractional treasury can pay the unchanged beer price");
      expect(f.map.treasury == 45.625 && c->mGold == 12.375, "keeper payment retains both gold fractions");
      f.room.mPayer = TavernPayer::creature; f.map.seatGold = 0.625;
      expect(f.room.payForBeer(*c, noCoin) && !noCoin, "fractional purse can pay the unchanged beer price");
      expect(c->mGold == 7.375 && f.map.seatGold == 5.625 && f.map.treasury == 45.625, "purse payment retains purse, seat and treasury fractions"); }
    // The creature cannot pay: water and mood -5 for 168 turns
    { Fixture f; f.seat.beerLevel = 1; f.room.mPayer = TavernPayer::creature; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); c->mGold = 4; f.map.treasury = 100;
      Random::script({ 99.0, 99.0 }, {});
      f.room.finishDrink(c->mTile, f.room.mSpots.find(c->mTile)->second);
      expect(c->mGold == 4 && f.map.seatGold == 0 && f.map.treasury == 100 && c->mDrunk == 0.0, "an empty purse gives water and costs nothing");
      expectNear(c->mTavernMood, -33.3333, "no coin: mood -33.3333"); expectNear(c->mTavernMoodTurns, 168.0, "no coin: for 168 turns"); }

    // The drink chain: 50, 25, 12.5 and 6.25 percent after the 1st to the 4th drink, never more than five
    const double thresholds[] = { 50.0, 25.0, 12.5, 6.25 };
    for(int n = 1; n <= 4; ++n)
    {
        { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); RoomTavernSpot& spot = f.room.mSpots.find(c->mTile)->second; spot.mDrinks = n - 1;
          Random::script({ thresholds[n - 1] - 0.01 }, {});
          f.room.finishDrink(c->mTile, spot);
          expect(spot.mState == TavernGuestState::drinking && spot.mTurnsLeft == 4, "drink " + std::to_string(n) + ": a roll just below " + std::to_string(thresholds[n - 1]) + " takes another drink for 4 turns"); }
        { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); RoomTavernSpot& spot = f.room.mSpots.find(c->mTile)->second; spot.mDrinks = n - 1;
          Random::script({ thresholds[n - 1] + 0.01 }, {});
          f.room.finishDrink(c->mTile, spot);
          expect(spot.mState == TavernGuestState::done, "drink " + std::to_string(n) + ": a roll just above " + std::to_string(thresholds[n - 1]) + " ends the visit"); }
    }
    { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); RoomTavernSpot& spot = f.room.mSpots.find(c->mTile)->second; spot.mDrinks = 4;
      Random::script({ 0.0 }, {});
      f.room.finishDrink(c->mTile, spot);
      expect(spot.mState == TavernGuestState::done && spot.mDrinks == 5, "the fifth drink is the last whatever the roll says"); }
    { Fixture f; Creature* c = f.guest("A", 2, 1, TavernGuestState::drinking, 0); c->mThirst = 0.0; RoomTavernSpot& spot = f.room.mSpots.find(c->mTile)->second;
      Random::script({ 10.0 }, {});
      f.room.finishDrink(c->mTile, spot);
      expect(spot.mState == TavernGuestState::drinking, "a creature without thirst still drinks when the roll says so"); }
}

// ---- Games
static void checkGameStart()
{
    // 50 percent chance after the last drink, a neighbour of the same seat that is done and waits
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.guest("B", 3, 1, TavernGuestState::done, 2);
      RoomTavernSpot& spot = f.room.mSpots.find(a->mTile)->second; spot.mDrinks = 4;
      Random::script({ 49.9 }, { 0 }); f.room.finishDrink(a->mTile, spot);
      expect(f.room.mGames.size() == 1, "a roll below 50 starts a game with the neighbour");
      expect(f.stateOf(a) == TavernGuestState::game, "both guests are in the game"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::drinking, 0); f.guest("B", 3, 1, TavernGuestState::done, 2);
      RoomTavernSpot& spot = f.room.mSpots.find(a->mTile)->second; spot.mDrinks = 4;
      Random::script({ 50.0 }, { 0 }); f.room.finishDrink(a->mTile, spot);
      expect(f.room.mGames.empty() && !spot.mWantsGame, "a roll of 50 starts no game and the guest wants none"); }
    // Without a neighbour the guest waits DrinkTurns (4) turns for one and starts the game when one is done
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::drinking, 0);
      RoomTavernSpot& spot = f.room.mSpots.find(a->mTile)->second; spot.mDrinks = 4;
      Random::script({ 1.0 }, { 0 }); f.room.finishDrink(a->mTile, spot);
      expect(f.room.mGames.empty() && spot.mWantsGame && spot.mState == TavernGuestState::done && spot.mTurnsLeft == 4, "a guest that wants a game waits for 4 turns");
      f.guest("B", 3, 1, TavernGuestState::done, 2);
      Random::script({}, { 0 }); f.room.tryStartGame(a->mTile);
      expect(f.room.mGames.size() == 1 && !spot.mWantsGame, "the waiting guest starts the game when a neighbour is done"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2);
      f.room.mSpots.find(a->mTile)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(a->mTile);
      expect(f.room.mGames.empty(), "no neighbour, no game"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); f.guest("B", 5, 1, TavernGuestState::done, 2);
      f.room.mSpots.find(a->mTile)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(a->mTile);
      expect(f.room.mGames.empty(), "a guest two tiles away is no neighbour"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 0); (void)b;
      f.room.mSpots.find(a->mTile)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(a->mTile);
      expect(f.room.mGames.empty(), "a neighbour whose waiting turns ran out is gone"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 2); Seat other; b->mSeat = &other;
      f.room.mSpots.find(a->mTile)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(a->mTile);
      expect(f.room.mGames.empty(), "a guest of another seat is no partner"); }
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); f.guest("B", 3, 1, TavernGuestState::drinking, 2);
      f.room.mSpots.find(a->mTile)->second.mWantsGame = true; Random::script({ 1.0 }, { 0 }); f.room.tryStartGame(a->mTile);
      expect(f.room.mGames.empty(), "a neighbour that still drinks is no partner"); }

    // The draw: arm wrestling and dice without beer, the slap duel joins with beer
    { Fixture f; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 2);
      Random::script({}, { 1 }); f.room.startGame(a->mTile, b->mTile);
      expect(Random::lastUintMax == 1, "without beer two games are drawn");
      expect(f.room.mGames.begin()->second.mKind == TavernGameKind::dice && f.room.mGames.begin()->second.mTurnsLeft == 8, "dice take 8 turns"); }
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 1, TavernGuestState::done, 2); Creature* b = f.guest("B", 3, 1, TavernGuestState::done, 2);
      Random::script({}, { 2 }); f.room.startGame(a->mTile, b->mTile);
      expect(Random::lastUintMax == 2, "with beer three games are drawn");
      expect(f.room.mGames.begin()->second.mKind == TavernGameKind::slapDuel && f.room.mGames.begin()->second.mTurnsLeft == 32, "the duel ends after 4 x 8 turns at the latest"); }

    // A new guest takes the free place next to a guest, not the one nearest to it
    { Fixture f; f.guest("G", 8, 1, TavernGuestState::drinking, 2); Creature* n = f.guest("N", 3, 1, TavernGuestState::arriving, 0);
      f.room.mSpots.erase(n->mTile);
      Tile* picked = f.room.pickFreeSpotTile(*n);
      expect((picked != nullptr) && (picked->x == 7), "a new guest takes the place next to a guest"); }
    { Fixture f; Creature* n = f.guest("N", 4, 1, TavernGuestState::arriving, 0);
      f.room.mSpots.erase(n->mTile);
      Tile* picked = f.room.pickFreeSpotTile(*n);
      expect((picked != nullptr) && (picked->x == 4), "without guests the nearest place is taken"); }
}

static void checkContest()
{
    // Level 12 against level 10: the weaker wins with 50 - 2.5 x 2 = 45 percent
    { Fixture f; Creature* a = f.guest("A", 2, 12, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::armWrestling, 2);
      Random::script({ 44.9 }, {});
      f.room.playContestTurn(g); expect(f.room.mGames.size() == 1, "the game runs while turns are left");
      f.room.playContestTurn(f.room.mGames.begin());
      expect(f.room.mGames.empty() && b->mExp == 5.72 && a->mExp == 0.0, "44.9: the weaker wins and gets double experience");
      expectNear(b->mTavernMood, 199.9999, "underdog mood 133.3333 + 33.3333 x 2"); expectNear(a->mTavernMood, 0.0, "the loser gets nothing"); expect(f.innkeeper.cheers == 1, "the innkeeper cheers"); }
    { Fixture f; Creature* a = f.guest("A", 2, 12, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 45.1 }, {});
      f.room.playContestTurn(g);
      expect(f.room.mGames.empty() && a->mExp == 2.86 && b->mExp == 0.0, "45.1: the stronger wins with normal experience");
      expectNear(a->mTavernMood, 133.3333, "winner mood 133.3333"); expectNear(a->mTavernMoodTurns, 168.0, "winner mood for 168 turns"); }
    // Equal levels: 50 / 50 and normal values for the winner
    { Fixture f; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 49.9 }, {}); f.room.playContestTurn(g);
      expect(a->mExp == 2.86 && a->mTavernMood == 133.3333 && b->mExp == 0.0, "equal levels: 49.9 wins for the first guest with normal values"); }
    // The floor: 20 levels of difference would give 0 percent, the weaker still wins with 5 percent
    { Fixture f; Creature* a = f.guest("A", 2, 25, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 5, TavernGuestState::game, 0);
      std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 4.9 }, {}); f.room.playContestTurn(g);
      expect(b->mExp == 5.72, "20 levels: 4.9 still lets the weaker win (floor 5 percent)"); expectNear(b->mTavernMood, 333.3333, "underdog mood is capped at 333.3333"); }
    { Fixture f; Creature* a = f.guest("A", 2, 25, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 5, TavernGuestState::game, 0);
      std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 5.1 }, {}); f.room.playContestTurn(g);
      expect(a->mExp == 2.86 && b->mExp == 0.0, "20 levels: 5.1 is a win of the stronger"); }
    // Spectators: own creatures within 2 tiles (Chebyshev) of a player, not the players, not a possessed one
    { Fixture f; Creature* a = f.guest("A", 4, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 5, 10, TavernGuestState::game, 0);
      Creature* near = f.guest("Near", 7, 1, TavernGuestState::done, 0); Creature* far = f.guest("Far", 8, 1, TavernGuestState::done, 0);
      Creature* up = f.guest("Up", 4, 1, TavernGuestState::done, 0); up->mTile = f.map.getTile(4, 7);
      Creature* possessed = f.guest("Possessed", 3, 1, TavernGuestState::done, 0); possessed->mPossessed = true;
      Creature* off = f.guest("Off", 3, 1, TavernGuestState::done, 0); off->mOnMap = false;
      std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::dice, 1);
      Random::script({ 10.0 }, {}); f.room.playContestTurn(g);
      expectNear(near->mTavernMood, 66.6667, "a spectator 2 tiles from a player gets +66.6667"); expectNear(near->mTavernMoodTurns, 168.0, "spectator mood for 168 turns");
      expectNear(far->mTavernMood, 0.0, "3 tiles away is no spectator"); expectNear(up->mTavernMood, 66.6667, "2 tiles away on the other axis is a spectator");
      expectNear(possessed->mTavernMood, 0.0, "a possessed creature does not cheer"); expectNear(off->mTavernMood, 0.0, "a creature off the map does not cheer"); }
}

static void checkDuel()
{
    // The critical chance is 10 percent at equal level and 0.25 points per level of difference
    struct Case { uint32_t slapper, target; double roll; bool crit; const char* what; };
    const Case cases[] = {
        { 10, 10, 9.99, true, "equal level: 9.99 is critical" }, { 10, 10, 10.01, false, "equal level: 10.01 is not" },
        { 11, 10, 10.24, true, "one level above: 10.24 is critical" }, { 11, 10, 10.26, false, "one level above: 10.26 is not" },
        { 9, 10, 9.74, true, "one level below: 9.74 is critical" }, { 9, 10, 9.76, false, "one level below: 9.76 is not" },
    };
    for(unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i)
    {
        Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, cases[i].slapper, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, cases[i].target, TavernGuestState::game, 0);
        std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 32);
        Random::script({ cases[i].roll }, {}); f.room.playDuelTurn(g);
        if(cases[i].crit)
        {
            expect(f.room.mGames.empty() && b->mHp == 100.0, std::string(cases[i].what) + ": the duel is decided, no damage");
            expect(f.stateOf(b) == TavernGuestState::ko && f.room.mSpots.find(b->mTile)->second.mTurnsLeft == 42 && f.room.mSpots.find(b->mTile)->second.mSleepAfter, "a critical slap knocks the loser out for 42 turns and sends it to bed");
        }
        else expect(f.room.mGames.size() == 1 && b->mHp == 90.0, std::string(cases[i].what) + ": a normal slap takes 10 HP");
    }

    // A normal hit: 10 HP, the loser is the one who falls below 30, HP never below 1
    struct HpCase { double hp; bool decided; double after; const char* what; };
    const HpCase hpCases[] = { { 100.0, false, 90.0, "100 HP -> 90" }, { 45.0, false, 35.0, "45 HP -> 35" }, { 40.0, false, 30.0, "40 HP -> 30 is not below 30" },
                               { 39.9, true, 29.9, "39.9 HP -> 29.9 is below 30" }, { 31.0, true, 21.0, "31 HP -> 21" }, { 5.0, true, 1.0, "5 HP -> 1, never below 1" },
                               { 1.0, true, 1.0, "1 HP stays 1" } };
    for(unsigned i = 0; i < sizeof(hpCases) / sizeof(hpCases[0]); ++i)
    {
        Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0); b->mHp = hpCases[i].hp;
        std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 32);
        Random::script({ 50.0 }, {}); f.room.playDuelTurn(g);
        expectNear(b->mHp, hpCases[i].after, hpCases[i].what, 1e-9);
        expect(f.room.mGames.empty() == hpCases[i].decided, std::string(hpCases[i].what) + ": decided = " + (hpCases[i].decided ? "yes" : "no"));
        if(hpCases[i].decided)
        {
            expect(f.stateOf(b) == TavernGuestState::ko && f.stateOf(a) == TavernGuestState::done, "the loser goes down, the winner is done");
            expectNear(a->mTavernMood, 133.3333, "winner mood 133.3333"); expect(a->mExp == 2.86, "winner experience 2.86"); expectNear(b->mTavernMood, -66.6667, "loser mood -66.6667 for the duel");
            expect(f.room.kinds.size() == 2 && f.room.kinds[0] == 2 && f.room.kinds[1] == 3, "winner and loser are told to the clients");
        }
    }
    // A miss passes the turn and does no damage
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0); a->mHit = true; b->mHit = false;
      std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 32);
      b->mHit = false;   // the target rolls the hit: a miss
      Random::script({}, {}); f.room.playDuelTurn(g);
      expect(g->second.mTurnIsA == false && b->mHp == 100.0 && g->second.mTurnsLeft == 31, "a miss passes the turn without damage"); }
    // After 4 x 8 turns without a decision the one with more HP left wins; a tie is decided by chance
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0); a->mHp = 80.0; b->mHp = 60.0;
      b->mHit = false; std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 1);
      Random::script({}, {}); f.room.playDuelTurn(g);
      expect(f.room.mGames.empty() && a->mExp == 2.86 && f.stateOf(b) == TavernGuestState::ko, "no decision: the one with more HP wins and the other goes down"); }
    { Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
      b->mHit = false; std::map<Tile*, RoomTavernGame>::iterator g = f.game(a, b, TavernGameKind::slapDuel, 1);
      Random::script({}, { 1 }); f.room.playDuelTurn(g);
      expect(f.room.mGames.empty() && b->mExp == 2.86, "a tie is decided by chance"); }
}

static void checkKnockOutAndAbort()
{
    // 42 turns lying, then 2 turns getting up, then done (the room sends the loser to bed in useRoom)
    { Fixture f; f.seat.beerLevel = 1; Creature* b = f.guest("B", 3, 10, TavernGuestState::done, 0);
      f.room.knockOut(f.room.mSpots.find(b->mTile)->second);
      for(int i = 0; i < 41; ++i) f.room.upkeepSpots();
      expect(f.stateOf(b) == TavernGuestState::ko, "still lying after 41 turns");
      f.room.upkeepSpots(); expect(f.stateOf(b) == TavernGuestState::getUp && f.room.mSpots.find(b->mTile)->second.mTurnsLeft == 2, "after 42 turns the loser gets up for 2 turns");
      f.room.upkeepSpots(); f.room.upkeepSpots(); expect(f.stateOf(b) == TavernGuestState::done, "then it is done"); }
    // A fight, a flight, a knock-out or a pick-up ends a game without effects
    for(int reason = 0; reason < 4; ++reason)
    {
        Fixture f; f.seat.beerLevel = 1; Creature* a = f.guest("A", 2, 10, TavernGuestState::game, 0); Creature* b = f.guest("B", 3, 10, TavernGuestState::game, 0);
        Creature* spectator = f.guest("S", 4, 1, TavernGuestState::done, 0);
        f.game(a, b, TavernGameKind::slapDuel, 20);
        if(reason == 0) b->mFighting = true; else if(reason == 1) a->mFleeing = true; else if(reason == 2) b->mKo = true; else a->mDragged = true;
        f.room.abortDisturbedGuests();
        expect(f.room.mGames.empty(), "reason " + std::to_string(reason) + ": the game ends");
        expect(a->mExp == 0.0 && b->mExp == 0.0 && a->mTavernMood == 0.0 && b->mTavernMood == 0.0 && spectator->mTavernMood == 0.0 && f.innkeeper.cheers == 0 && f.room.events == 0,
               "reason " + std::to_string(reason) + ": no effects (no experience, no mood, no cheer, no event)");
        expect(f.stateOf(a) == TavernGuestState::done && f.stateOf(b) == TavernGuestState::done, "both guests are done");
    }
    // A fight nearby ends the lying at once, without the walk to bed
    { Fixture f; Creature* b = f.guest("B", 3, 10, TavernGuestState::ko, 30); f.room.mSpots.find(b->mTile)->second.mSleepAfter = true; b->mFighting = true;
      f.room.abortDisturbedGuests();
      expect(f.stateOf(b) == TavernGuestState::done && !f.room.mSpots.find(b->mTile)->second.mSleepAfter, "a fight ends the lying and the way to bed"); }
}

// ---- Mood of thirst and the portal cooldown
struct CreatureS { double thirst; double getThirst() const { return thirst; } double getHunger() const { return thirst; } };
@@MOOD_FUNCTIONS@@

static void checkMoodAndPortal()
{
    // The thirst mood is the hunger mood with the same numbers: nothing below the start, then (value - start) x modifier
    struct M { int start; int modifier; };
    const M moods[] = { { 80, -60 }, { 80, -40 }, { 80, -20 } };
    for(unsigned i = 0; i < 3; ++i)
        for(int v = 0; v <= 100; v += 5)
        {
            CreatureS c; c.thirst = v;
            expect(thirstMood(c, moods[i].start, moods[i].modifier) == hungerMood(c, moods[i].start, moods[i].modifier), "thirst mood equals hunger mood");
        }
    CreatureS full; full.thirst = 100.0;
    expect(thirstMood(full, 80, -60) == -1200, "thirst 100 with 80 / -60");
    CreatureS below; below.thirst = 79.9;
    expect(thirstMood(below, 80, -60) == 0, "no malus below the start");

    // Portal cooldown: both bounds times the factor of the Beer level
    Seat seat; const double factors[] = { 1.0, 0.9, 0.8 };
    for(uint32_t level = 0; level <= 3; ++level)
    {
        seat.beerLevel = level;
        const double factor = (level == 0) ? 1.0 : factors[level - 1];
        expect(std::fabs(getResearchedCooldown(&seat, "PortalCooldownSpawnMin") - 230.15307692307692 * factor) < 1e-9, "portal min cooldown at Beer level " + std::to_string(level));
        expect(std::fabs(getResearchedCooldown(&seat, "PortalCooldownSpawnMax") - ConfigManager::getSingleton().values["RoomPortalCooldownSpawnMax"] * factor) < 1e-9, "portal max cooldown at Beer level " + std::to_string(level));
    }
}

int main()
{
    loadConfig();
    checkThirst();
    checkDrinks();
    checkGameStart();
    checkContest();
    checkDuel();
    checkKnockOutAndAbort();
    checkMoodAndPortal();
    if(failures == 0) std::cout << "tavern rules ok" << std::endl;
    return failures == 0 ? 0 : 1;
}
'''

# The pieces of the sources
drink_kind = room_h = read('source/entities/Creature.h')
drink_kind = drink_kind[drink_kind.index('enum class DrinkKind'):]
drink_kind = drink_kind[:drink_kind.index('};') + 2]
creature_functions = '\n'.join(extract(creature_cpp, h) for h in [
    'void Creature::increaseUrge(', 'void Creature::increaseThirst(', 'void Creature::setThirst(', 'void Creature::setDrunk(',
    'void Creature::setHangoverTurns(', 'void Creature::addTavernMood(', 'void Creature::drinkTaken(', 'bool Creature::isStaggering(',
    'double Creature::getHangoverWorkFactor(', 'void Creature::sleepStarted(', 'void Creature::sleepEnded(', 'void Creature::upkeepTavernState('])
tavern_h = read('source/rooms/RoomTavern.h')
types_start = tavern_h.index('//! \\brief Who pays for the beer a tavern serves.')
types_end = tavern_h.index('//! \\brief A room where creatures quench their thirst.')
room_types = tavern_h[types_start:types_end]
constants = '\n'.join(find_line(room_cpp, r'^const (?:int32_t|uint32_t|double) ' + name + r' = [^;]+;$') for name in (
    'GET_UP_TURNS', 'DONE_WAIT_TURNS', 'PERCENT_SCALE', 'DIRECTION_EPSILON', 'NB_GAMES_WITHOUT_BEER', 'NB_GAMES_WITH_BEER'))
constants += '\n' + '\n'.join(find_line(room_cpp, r'^const std::string ' + name + r' = "[^"]+";$') for name in ('SOUND_POUR', 'SOUND_SLAP', 'SOUND_CHEER'))
helpers = '\n'.join(extract(room_cpp, h) for h in ['double getTavernValue(', 'Ogre::Vector3 directionTo('])
room_functions = '\n'.join(extract(room_cpp, h) for h in [
    'bool RoomTavern::servesBeer(', 'bool RoomTavern::isFreeSpotTile(', 'Tile* RoomTavern::pickFreeSpotTile(', 'void RoomTavern::addDrinkDirt(', 'std::map<Tile*, RoomTavernSpot>::iterator RoomTavern::findSpotOf(',
    'void RoomTavern::setSpotState(', 'void RoomTavern::setSpotDone(', 'bool RoomTavern::isGuestDisturbed(', 'void RoomTavern::upkeepSpots(',
    'void RoomTavern::abortDisturbedGuests(', 'bool RoomTavern::payForBeer(', 'void RoomTavern::finishDrink(', 'void RoomTavern::tryStartGame(',
    'void RoomTavern::startGame(', 'void RoomTavern::playContestTurn(', 'void RoomTavern::playDuelTurn(', 'void RoomTavern::cheerSpectators(',
    'void RoomTavern::concludeGame(', 'void RoomTavern::abortGame(', 'void RoomTavern::knockOut('])
portal_function = extract(portal_cpp, 'static double getResearchedCooldown(')


# The mood function bodies, taken from the mood classes and renamed to free functions on the small stub
def mood_function(text, name, free_name):
    compute = extract(text, 'double CreatureMood' + name + '::computeMood(')
    body = compute[compute.index('{'):]
    getter = 'creature.get' + name + '()'
    assert getter in body, name
    start_name = 'mStart' + name
    return ('static int32_t ' + free_name + '(const CreatureS& creature, int32_t ' + start_name + ', int32_t mMoodModifier)\n' + body)


mood_functions = mood_function(mood_thirst_cpp, 'Thirst', 'thirstMood') + '\n' + mood_function(mood_hunger_cpp, 'Hunger', 'hungerMood')

replacements = {
    '@@CONFIG@@': config_table,
    '@@DRINKKIND@@': drink_kind,
    '@@CREATURE_FUNCTIONS@@': creature_functions,
    '@@ROOM_TYPES@@': 'struct Creature; struct Tile;\n' + room_types,
    '@@ROOM_CONSTANTS@@': constants,
    '@@ROOM_HELPERS@@': helpers,
    '@@ROOM_FUNCTIONS@@': room_functions,
    '@@EFFECTS@@': effect_table,
    '@@PORTAL_FUNCTION@@': portal_function,
    '@@MOOD_FUNCTIONS@@': mood_functions,
}
for token, text in replacements.items():
    assert token in probe, token
    probe = probe.replace(token, text)

with tempfile.TemporaryDirectory(prefix='odp-tavern-rules-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++17', '/W3', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
print('tavern rules ok')
