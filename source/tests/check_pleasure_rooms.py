"""Pleasure rooms, pleasure buff, room locks and the special boxes of the creature mood (cases bath, buff_blocks, locks,
make_unhappy, make_happy (mood part), the save of the locks, and the edge rules E7-E11). Nothing is compiled: the values come
from the shipped configuration, the rules are worked out here with the same formulas as the sources (a small model of the
visit, the buff and the locks of Creature.cpp), and the source wiring is pinned by tokens.

What is checked
  rooms.cfg               PleasureVisitMax 200, PleasureBuffMood 100, SpaMoodJump 50, SpaMoodPerTurn 10.5, SpaBathTurns 14.2857,
                          SpaRelaxTurns 252, the lock keys of tavern / casino / temple / arena 600, the room rates (temple 10.5,
                          casino 14.7 / -2.25 per second, arena 14 / -11 per second), Make Unhappy -200 and -300 over 504, all
                          documented; global.cfg [Tavern] beer / games / no coin / hangover, BeerMoodTurns and NoCoinMoodTurns gone
  bath                    an Upset creature at 500 takes a bath: +50, +150 over the bath, +100 over 252 turns, 800 in total
  buff_blocks             a creature with a running pleasure buff uses, seeks and enters no pleasure room, gets no new mood from one
  locks                   after a visit that room is closed for 600 turns (the spa for 252), the other rooms are open to it
  make_unhappy            1500 -> 1300, then -300 over 504 turns; a second box 168 turns later acts fully again
  make_happy              the stored mood goes to the maximum, running effects keep running
  E7                      a thirsty creature enters the tavern despite the lock and the buff; a drink visit gives no buff, no lock
  E8                      a visit ends at PleasureVisitMax or by the end conditions; every visit that gained mood gives the full buff
  E9                      arena: the limit applies to spectators, the victor bonus is outside it
  E10                     tavern: beer, games and no coin of a leisure visit count toward the 200
  E11                     casino in mode Money: no buff, still the lock; Upset creatures do not look for it
  save                    the locks, the visit in progress and the buff are saved and loaded one to one

Calls (from the repository root):
  python source/tests/check_pleasure_rooms.py       plain file checks, no compiler, no game
"""
import math
import re
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def block(text, tag):
    match = re.search(r"(?ms)^\[" + tag + r"\]\s*$(.*?)^\[/" + tag + r"\]", text)
    assert match, "block [" + tag + "] missing"
    values = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith("#"):
            values.setdefault(words[0], words[1])
    return values


def extract(text, header):
    start = text.index(header)
    return text[start:text.index("\n}\n", start) + 2]


def check(cond, message):
    assert cond, message


def near(a, b, message, eps=1e-6):
    assert abs(a - b) <= eps, message + ": got " + repr(a) + ", expected " + repr(b)


glob = read("config/global.cfg")
rooms_cfg = read("config/rooms.cfg")
rooms = block(rooms_cfg, "Rooms")
tavern = block(glob, "Tavern")
creature_cpp = read("source/entities/Creature.cpp")
creature_h = read("source/entities/Creature.h")
spa_cpp = read("source/rooms/RoomSpa.cpp")
tavern_cpp = read("source/rooms/RoomTavern.cpp")
casino_cpp = read("source/rooms/RoomCasino.cpp")
temple_cpp = read("source/rooms/RoomTemple.cpp")
arena_cpp = read("source/rooms/RoomArena.cpp")
use_room_cpp = read("source/creatureaction/CreatureActionUseRoom.cpp")
search_job_cpp = read("source/creatureaction/CreatureActionSearchJob.cpp")
gift_cpp = read("source/giftboxes/GiftBoxBonus.cpp")
pleasure_h = read("source/creaturemood/CreatureMoodPleasure.h")

MAX_MOOD = float(re.search(r"(?m)^\s*CreatureBaseMood\s+(\S+)", glob).group(1))
TURNS_PER_SECOND = 1.4

# ---- Values (Global Constraint 13: every value is a documented config key) ------------------------------------------------
VALUES = {
    "PleasureVisitMax": 200.0, "PleasureBuffMood": 100.0, "SpaMoodJump": 50.0, "SpaMoodPerTurn": 10.5,
    "SpaBathTurns": 14.2857, "SpaRelaxTurns": 252.0, "TavernLeisureCooldownTurns": 600.0,
    "CasinoVisitLockTurns": 600.0, "TempleVisitLockTurns": 600.0, "ArenaVisitLockTurns": 600.0,
    "TemplePrayerReliefPerTurn": 10.5, "CasinoMoodSmiles": 14.7, "CasinoMoodMoney": -2.25,
    "PitMoodSpectator": 14.0, "PitMoodSolitary": -11.0, "PitMoodVictor": 250.0,
    "MakeUnhappyMoodJump": -200.0, "MakeUnhappyMoodFall": -300.0, "MakeUnhappyTurns": 504.0,
}
for key, value in VALUES.items():
    check(key in rooms, key + " missing in rooms.cfg [Rooms]")
    near(float(rooms[key]), value, key)
    check(re.search(r"(?m)^#\s*" + key + r"\s", rooms_cfg), key + " has no documentation line in rooms.cfg")
TAVERN_VALUES = {"BeerMood": 25.0, "NoCoinMood": -8.33, "HangoverMood": -16.67, "GameWinnerMood": 33.33,
                 "GameLoserMood": -16.67, "GameSpectatorMood": 16.67, "GameUnderdogMoodPerLevel": 8.3333,
                 "GameUnderdogMoodMax": 83.3333}
for key, value in TAVERN_VALUES.items():
    near(float(tavern[key]), value, key)
for gone in ("BeerMoodTurns", "NoCoinMoodTurns"):
    check(gone not in glob, gone + " must be removed with its documentation")
for gone in ("SpaMoodDecayPerTurn", "SpaMoodMax", "CasinoMoodDecay", "CasinoMoodMax", "PitMoodDecay", "PitMoodMax",
             "TemplePrayerReliefDecayPerTurn", "TemplePrayerReliefMax"):
    check(gone not in rooms_cfg, gone + " must stay removed")

# 50 + 14.2857 x 10.5 fills the visit limit; the visit and the buff make the 300 of the design (D6)
near(rooms_f := float(rooms["SpaMoodJump"]) + float(rooms["SpaMoodPerTurn"]) * float(rooms["SpaBathTurns"]), 200.0, "bath fills the limit", 0.01)
near(float(rooms["PleasureVisitMax"]) + float(rooms["PleasureBuffMood"]), 300.0, "visit plus buff")
# 10.5 per turn is the 14.7 per second of the casino at 1.4 turns per second
near(float(rooms["CasinoMoodSmiles"]) / TURNS_PER_SECOND, float(rooms["TemplePrayerReliefPerTurn"]), "casino rate per turn")


# ---- A small model of Creature.cpp: visit, buff, locks, effects, special boxes ---------------------------------------------
class Creature:
    SPA, TAVERN, CASINO, TEMPLE, ARENA = range(5)

    def __init__(self, stored=MAX_MOOD, thirst=0.0):
        self.stored = stored
        self.thirst = thirst
        self.effects = []            # [name, strength per turn, turns left]
        self.locks = {}              # casino / temple / arena locks, turns left
        self.relax = 0.0             # the lock of the spa
        self.tavern_cooldown = 0     # the lock of the tavern
        self.visit_kind = -1
        self.visit_gain = 0.0
        self.watch_turns = 0

    # one-time event, 0 .. maximum
    def event(self, points):
        self.stored = max(0.0, min(MAX_MOOD, self.stored + points))

    def add_effect(self, name, total, turns):
        if turns > 0:
            self.effects.append([name, total / turns, turns])

    def has_buff(self):
        return any(e[2] > 0 and e[0] in ("Relaxed", "Pleasure") for e in self.effects)

    def lock_turns(self, kind):
        if kind == self.SPA:
            return self.relax
        if kind == self.TAVERN:
            return float(self.tavern_cooldown)
        return self.locks.get(kind, 0.0)

    def can_use(self, kind):
        return not self.has_buff() and self.lock_turns(kind) <= 0

    def start_lock(self, kind, turns):
        if turns <= 0:
            return
        if kind == self.SPA:
            self.relax = max(self.relax, turns)
        elif kind == self.TAVERN:
            self.tavern_cooldown = max(self.tavern_cooldown, int(turns))
        else:
            self.locks[kind] = max(self.locks.get(kind, 0.0), turns)

    def begin(self, kind):
        self.visit_kind = kind
        self.visit_gain = 0.0

    def add_pleasure(self, kind, points):
        applied = points
        if points > 0:
            if self.visit_kind != kind or self.has_buff():
                return
            applied = max(0.0, min(points, float(rooms["PleasureVisitMax"]) - self.visit_gain))
        if self.visit_kind == kind:
            self.visit_gain += applied
        self.event(applied)

    def full(self, kind):
        return self.visit_kind == kind and self.visit_gain >= float(rooms["PleasureVisitMax"]) - 1e-9

    def finish(self, kind, buff_turns, lock_turns, lock_without_gain):
        if self.visit_kind != kind:
            return
        gain = self.visit_gain
        self.visit_kind, self.visit_gain = -1, 0.0
        if kind == self.ARENA:
            self.watch_turns = 0
        if gain > 0:
            self.add_effect("Relaxed" if kind == self.SPA else "Pleasure", float(rooms["PleasureBuffMood"]), buff_turns)
        if gain > 0 or lock_without_gain:
            self.start_lock(kind, lock_turns)

    def finish_default(self, kind, lock_without_gain):
        lock = {self.SPA: "SpaRelaxTurns", self.TAVERN: "TavernLeisureCooldownTurns", self.CASINO: "CasinoVisitLockTurns",
                self.TEMPLE: "TempleVisitLockTurns", self.ARENA: "ArenaVisitLockTurns"}[kind]
        self.finish(kind, float(rooms["SpaRelaxTurns"]), float(rooms[lock]), lock_without_gain)

    def turn(self):
        """One turn: the effects add their strength and run down, the locks run down."""
        for effect in self.effects:
            self.event(effect[1])
            effect[2] -= 1
        self.effects = [e for e in self.effects if e[2] > 0]
        self.relax = max(0.0, self.relax - 1)
        self.tavern_cooldown = max(0, self.tavern_cooldown - 1)
        for kind in list(self.locks):
            self.locks[kind] -= 1
            if self.locks[kind] <= 0:
                del self.locks[kind]

    # Make Unhappy / Make Happy (GiftBoxBonus.cpp, Creature::makeUnhappy / removeAnnoyance)
    def make_unhappy(self):
        self.event(float(rooms["MakeUnhappyMoodJump"]))
        self.add_effect("MakeUnhappy", float(rooms["MakeUnhappyMoodFall"]), float(rooms["MakeUnhappyTurns"]))

    def make_happy(self):
        self.stored = MAX_MOOD


def bath(c, relax_turns=252.0):
    """RoomSpa: the jump when the bath starts, then SpaMoodPerTurn per counted turn until SpaBathTurns is reached."""
    c.begin(Creature.SPA)
    c.add_pleasure(Creature.SPA, float(rooms["SpaMoodJump"]))
    turns = 0
    done = 0.0
    while done < float(rooms["SpaBathTurns"]):
        c.add_pleasure(Creature.SPA, float(rooms["SpaMoodPerTurn"]))
        done += 1
        turns += 1
    c.finish(Creature.SPA, relax_turns, relax_turns, True)
    c.relax = max(c.relax, relax_turns)
    return turns


# ---- bath ------------------------------------------------------------------------------------------------------------------
c = Creature(stored=500.0)
c.begin(Creature.SPA)
c.add_pleasure(Creature.SPA, float(rooms["SpaMoodJump"]))
near(c.stored, 550.0, "bath: the jump when it starts")
c = Creature(stored=500.0)
check(bath(c) == 15, "the counted turns reach 14.2857 in the 15th turn")
near(c.stored, 700.0, "bath: 200 inside the room (the 15th turn is cut at the limit)")
check(c.visit_kind == -1, "the visit ends with the bath")
check(len(c.effects) == 1 and c.effects[0][0] == "Relaxed", "the buff Relaxed starts at the end of the bath")
near(c.effects[0][1] * c.effects[0][2], 100.0, "the buff gives 100 in total")
near(c.effects[0][2], float(rooms["SpaRelaxTurns"]), "the buff runs over SpaRelaxTurns")
near(c.relax, float(rooms["SpaRelaxTurns"]), "the spa lock is the relaxation")
for _ in range(252):
    c.turn()
near(c.stored, 800.0, "bath: 500 + 50 + 150 + 100 = 800, a gain of 300")
check(not c.effects and c.relax == 0, "the buff and the lock are over after 252 turns")
# the research lengthens buff and lock together (RelaxTime x1.4)
c = Creature(stored=500.0)
bath(c, 252.0 * 1.4)
near(c.effects[0][2], 352.8, "research level 3: buff over 352.8 turns")
near(c.relax, 352.8, "research level 3: the lock lasts as long")
# a bath that is broken off after ten turns keeps its mood and, as every visit that gained mood, gives buff and lock
c = Creature(stored=500.0)
c.begin(Creature.SPA)
c.add_pleasure(Creature.SPA, 50.0)
for _ in range(10):
    c.add_pleasure(Creature.SPA, 10.5)
c.finish(Creature.SPA, 252.0, 252.0, False)
near(c.stored, 655.0, "broken bath: the mood so far stays")
check(c.has_buff() and c.relax == 252.0, "broken bath: buff and lock as after a bath that gained mood")
c = Creature(stored=500.0)
c.begin(Creature.SPA)
c.finish(Creature.SPA, 252.0, 252.0, False)
check(not c.has_buff() and c.relax == 0, "a visit that gained nothing gives no buff and no lock")

# the source: SpaMoodJump when the bath starts, the buff and the lock at its end, broken baths end the visit
start_bath = extract(spa_cpp, "void RoomSpa::startBath(")
check("beginPleasureVisit(PleasureRoomKind::spa)" in start_bath and 'getRoomConfigDouble("SpaMoodJump")' in start_bath, "startBath")
check("finishPleasureVisit(PleasureRoomKind::spa, relaxTurns, relaxTurns, true)" in extract(spa_cpp, "void RoomSpa::finishBath("), "finishBath")
check("finishBrokenVisit(" in extract(spa_cpp, "void RoomSpa::abortDisturbedBathers(") and
      "finishBrokenVisit(" in extract(spa_cpp, "void RoomSpa::removeCreatureUsingRoom("), "a broken bath ends the visit")
check("addSpaMood(moodPerTurn)" in extract(spa_cpp, "void RoomSpa::upkeepBathers("), "the bath adds SpaMoodPerTurn per turn")

# ---- buff_blocks -----------------------------------------------------------------------------------------------------------
c = Creature(stored=600.0)       # Upset
check(all(c.can_use(k) for k in range(5)), "control: an Upset creature without buff and locks may use every pleasure room")
c.add_effect("Pleasure", 100.0, 252.0)
check(not any(c.can_use(k) for k in range(5)), "a running pleasure buff keeps the creature from every pleasure room")
c.begin(Creature.CASINO)
before = c.stored
c.add_pleasure(Creature.CASINO, 10.5)
near(c.stored, before, "no room gives new mood while the buff runs")
c.add_effect("MakeUnhappy", -300.0, 504.0)
c2 = Creature()
c2.add_effect("MakeUnhappy", -300.0, 504.0)
check(all(c2.can_use(k) for k in range(5)), "a debuff is no pleasure buff")
# wiring: every way into a pleasure room asks the creature
check("canUsePleasureRoom(PleasureRoomKind::spa)" in extract(spa_cpp, "bool RoomSpa::canAccept("), "spa canAccept")
check("canUsePleasureRoom(PleasureRoomKind::spa)" in extract(creature_cpp, "bool Creature::wantsSpaBath("), "wantsSpaBath")
check("canUsePleasureRoom(PleasureRoomKind::tavern)" in extract(tavern_cpp, "bool RoomTavern::hasOpenCreatureSpot("), "tavern")
check("canUsePleasureRoom(PleasureRoomKind::casino)" in extract(casino_cpp, "bool RoomCasino::hasOpenCreatureSpot("), "casino")
check("canUsePleasureRoom(PleasureRoomKind::temple)" in extract(temple_cpp, "bool RoomTemple::hasOpenCreatureSpot("), "temple")
check("canUsePleasureRoom(PleasureRoomKind::arena)" in extract(creature_cpp, "void Creature::addPitSpectatorMood("), "arena spectators")
check("hasOpenCreatureSpot(&creature)" in search_job_cpp, "the job search takes only rooms that have an open spot for the creature")
check("!hasPleasureBuff() && !isRoomLocked(kind)" in extract(creature_cpp, "bool Creature::canUsePleasureRoom("), "buff and lock")
check("isBuffName" in extract(creature_cpp, "bool Creature::hasPleasureBuff(") and "(effect.mTurnsLeft > 0.0)" in extract(creature_cpp, "bool Creature::hasPleasureBuff("), "hasPleasureBuff")
check('"Relaxed"' in pleasure_h and '"Pleasure"' in pleasure_h, "the names of the pleasure buffs")
# an Upset creature with a buff still eats, sleeps, walks and idles: the search takes hunger and tiredness before the pleasure rooms
job = extract(search_job_cpp, "bool CreatureActionSearchJob::handleSearchJob(")
check(job.index("creature.isTired()") < job.index("pleasureRooms") and job.index("creature.isHungry()") < job.index("pleasureRooms"),
      "needs before pleasure rooms")

# ---- locks -----------------------------------------------------------------------------------------------------------------
LOCK_KEYS = {Creature.TAVERN: "TavernLeisureCooldownTurns", Creature.CASINO: "CasinoVisitLockTurns",
             Creature.TEMPLE: "TempleVisitLockTurns", Creature.ARENA: "ArenaVisitLockTurns"}
for kind, key in LOCK_KEYS.items():
    c = Creature()
    c.begin(kind)
    c.add_pleasure(kind, 30.0)
    c.finish_default(kind, False)
    check(c.has_buff(), "a visit that gained mood starts the buff")
    near(c.lock_turns(kind), 600.0, key + ": the room is closed for 600 turns")
    check(all(c.lock_turns(other) == 0 for other in range(5) if other != kind), "each lock blocks only its own room")
    for _ in range(252):
        c.turn()
    check(not c.has_buff(), "the buff is over after 252 turns")
    check(not c.can_use(kind), "after the buff the room is still closed")
    check(all(c.can_use(other) for other in range(5) if other != kind), "the other rooms are open again")
    for _ in range(600 - 252 - 1):
        c.turn()
    check(not c.can_use(kind), "one turn before the end the room is closed")
    c.turn()
    check(c.can_use(kind) and c.lock_turns(kind) == 0, "after 600 turns the room is open")
near(float(rooms["SpaRelaxTurns"]), 252.0, "the spa lock is 252 turns")
for key in LOCK_KEYS.values():
    check(re.search(r"(?m)^\s+" + key + r"\s+600\s*$", rooms_cfg), key + " is 600 in rooms.cfg")
# wiring of the end of each visit
check("finishPleasureVisit(PleasureRoomKind::tavern, true)" in extract(tavern_cpp, "void RoomTavern::removeCreatureUsingRoom("), "tavern visit end")
check("finishPleasureVisit(PleasureRoomKind::casino, mPayout == CasinoPayout::money)" in extract(casino_cpp, "void RoomCasino::removeCreatureUsingRoom("), "casino visit end")
check("beginPleasureVisit(PleasureRoomKind::casino)" in extract(casino_cpp, "bool RoomCasino::addCreatureUsingRoom("), "casino visit start")
check("finishPleasureVisit(PleasureRoomKind::temple, false)" in extract(temple_cpp, "void RoomTemple::removeCreatureUsingRoom("), "temple visit end")
check("beginPleasureVisit(PleasureRoomKind::temple)" in extract(temple_cpp, "bool RoomTemple::addCreatureUsingRoom("), "temple visit start")
check("RoomType::temple" in use_room_cpp and "isPleasureVisitFull(PleasureRoomKind::temple)" in use_room_cpp and
      "isPleasureVisitFull(PleasureRoomKind::casino)" in use_room_cpp, "a casino or temple visit ends at the limit")
upkeep = extract(creature_cpp, "void Creature::upkeepRoomLocks(")
check("it->second -= 1.0;" in upkeep and "mRoomLockTurns.erase(it)" in upkeep, "the locks run down by 1 per turn and end at 0")
check("upkeepRoomLocks();" in creature_cpp[creature_cpp.index("upkeepSpaState();"):][:300], "the locks are counted down every turn")
check("--mTavernCooldownTurns" in extract(creature_cpp, "void Creature::upkeepTavernState("), "the tavern lock runs down")
get_lock = extract(creature_cpp, "double Creature::getRoomLockTurns(")
check("return mRelaxTurns;" in get_lock and "mTavernCooldownTurns" in get_lock and "mRoomLockTurns.find" in get_lock, "spa lock, tavern lock, the others")

# ---- make_unhappy ----------------------------------------------------------------------------------------------------------
c = Creature(stored=1500.0)
c.make_unhappy()
near(c.stored, 1300.0, "Make Unhappy: -200 at once")
check(len(c.effects) == 1, "and a debuff")
near(c.effects[0][1] * c.effects[0][2], -300.0, "-300 in total")
near(c.effects[0][2], 504.0, "over 504 turns")
for _ in range(168):
    c.turn()
near(c.stored, 1300.0 - 168 * 300.0 / 504.0, "after 168 turns the debuff took 100")
second = c.stored
c.make_unhappy()
near(c.stored, second - 200.0, "the second box acts fully: -200 again")
check(len(c.effects) == 2, "a second debuff runs next to the first")
for _ in range(504):
    c.turn()
near(c.stored, max(0.0, second - 200.0 - (504 - 168) * 300.0 / 504.0 - 300.0), "both debuffs run to their end (not below 0)")
c = Creature(stored=100.0)
c.make_unhappy()
check(c.stored == 0.0, "the stored mood does not go below 0")
make_unhappy = extract(creature_cpp, "void Creature::makeUnhappy(")
check('getRoomConfigDouble("MakeUnhappyMoodJump")' in make_unhappy and 'addMoodEffect("MakeUnhappy"' in make_unhappy and
      '"MakeUnhappyMoodFall"' in make_unhappy and '"MakeUnhappyTurns"' in make_unhappy, "makeUnhappy uses the three keys")
box = gift_cpp[gift_cpp.index("case GiftBoxType::makeUnhappy:\n        {"):]
box = box[:box.index("case GiftBoxType::killCreatures")]
check("isRogueSeat()" in box and "isAlliedSeat(seat)" in box and "creature->makeUnhappy()" in box and "isAlive()" in box,
      "every living enemy creature, allied and rogue excepted")
check("MakeUnhappyMoodJump" in rooms_cfg and "every box acts fully" in rooms_cfg, "documented: every box acts fully")

# ---- make_happy (the mood part; the leave clock and the rampage belong to the leave package) --------------------------------
c = Creature(stored=50.0)
c.add_effect("MakeUnhappy", -300.0, 504.0)
c.add_effect("Pleasure", 100.0, 252.0)
c.make_happy()
near(c.stored, MAX_MOOD, "Make Happy: the stored mood is the maximum")
check(len(c.effects) == 2, "running effects keep running")
remove = extract(creature_cpp, "void Creature::removeAnnoyance(")
check("setStoredMood(ConfigManager::getSingleton().getCreatureBaseMood())" in remove and "mMoodEffects" not in remove,
      "removeAnnoyance sets the maximum and leaves the effects alone")
happy = gift_cpp[gift_cpp.index("case GiftBoxType::makeHappy:\n        {"):]
happy = happy[:happy.index("case GiftBoxType::makeUnhappy")]
check("getCreaturesBySeat(seat)" in happy and "isAlive()" in happy and "removeAnnoyance()" in happy, "all own living creatures")

# ---- E7: thirst is a need -------------------------------------------------------------------------------------------------
open_spot = extract(tavern_cpp, "bool RoomTavern::hasOpenCreatureSpot(")
check('getThirst() < getTavernValue("ThirstSeek")' in open_spot and "canUsePleasureRoom(PleasureRoomKind::tavern)" in open_spot,
      "only a creature that is not thirsty is held back by the buff and the lock")
for path in ("source/creatureaction/CreatureActionSearchJob.cpp", "source/creatureaction/CreatureActionUseRoom.cpp"):
    check("getTavernCooldownTurns" not in read(path), path + " must not look at the tavern lock when a thirsty creature seeks a drink")
check("mTavernCooldownTurns <= 0" not in creature_cpp, "no drink search looks at the tavern lock")
add_guest = extract(tavern_cpp, "bool RoomTavern::addCreatureUsingRoom(")
check("beginPleasureVisit(PleasureRoomKind::tavern)" in add_guest and 'getThirst() < getTavernValue("ThirstSeek")' in add_guest,
      "only a creature that is not thirsty starts a leisure visit")
finish_drink = extract(tavern_cpp, "void RoomTavern::finishDrink(")
check("isPleasureVisitFull(PleasureRoomKind::tavern)" in finish_drink and finish_drink.index("isPleasureVisitFull") < finish_drink.index("MaxDrinksPerVisit"),
      "a tavern leisure visit that gained PleasureVisitMax ends before the next drink or game")
# a drink visit: no visit is running, the beer is a plain event of BeerMood, no buff and no lock
c = Creature(stored=800.0, thirst=90.0)
check(c.visit_kind == -1, "a drink visit starts no pleasure visit")
for _ in range(5):
    c.event(float(tavern["BeerMood"]))
c.finish_default(Creature.TAVERN, True)
near(c.stored, 925.0, "five beers of a drink visit give 5 x 25, outside the limit")
check(not c.has_buff() and c.lock_turns(Creature.TAVERN) == 0, "a drink visit gives no pleasure buff and no lock")
add_tavern = extract(creature_cpp, "void Creature::addTavernMood(")
check("mPleasureVisitKind == static_cast<int32_t>(PleasureRoomKind::tavern)" in add_tavern and "applyMoodEvent(points, false)" in add_tavern,
      "beer counts toward the limit only inside a leisure visit")
# a thirsty creature enters the tavern while locked and while buffed: the room asks only the creature that is not thirsty
c = Creature(stored=800.0, thirst=90.0)
c.add_effect("Pleasure", 100.0, 252.0)
c.tavern_cooldown = 500
check(not c.can_use(Creature.TAVERN), "control: the lock and the buff close the tavern for leisure")
thirsty_may_enter = c.thirst >= float(tavern["ThirstSeek"]) or c.can_use(Creature.TAVERN)
check(thirsty_may_enter, "a thirsty creature may enter")

# ---- E8: the visit ends at the limit, every visit that gained mood gives the full buff -------------------------------------
c = Creature(stored=500.0)
c.begin(Creature.CASINO)
turns = 0
per_turn = float(rooms["CasinoMoodSmiles"]) / TURNS_PER_SECOND
while not c.full(Creature.CASINO):
    c.add_pleasure(Creature.CASINO, per_turn)
    turns += 1
check(turns == 20, "the casino fills the limit in 20 turns (19.05 turns of 10.5)")
near(c.stored, 700.0, "200 inside the room")
c.finish_default(Creature.CASINO, False)
near(c.effects[0][1] * c.effects[0][2], 100.0, "the full buff, however long the visit was")
c = Creature(stored=500.0)
c.begin(Creature.TEMPLE)
c.add_pleasure(Creature.TEMPLE, 1.0)
c.finish_default(Creature.TEMPLE, False)
near(c.effects[0][1] * c.effects[0][2], 100.0, "a visit that gained one point gives the full buff")
check(c.stored == 501.0, "and only that point")
c = Creature(stored=1400.0)
c.begin(Creature.TEMPLE)
for _ in range(30):
    c.add_pleasure(Creature.TEMPLE, 10.5)
near(c.stored, 1500.0, "the stored mood stays within the maximum")
check(c.full(Creature.TEMPLE) is False or c.visit_gain <= 200.0, "the gain counts what the room gave, not what the maximum took")
# an Upset creature leaves at Neutral: that end is the one of today (the use of the room pops its action)
check("creature.getMoodValue() <= CreatureMoodLevel::Neutral" in use_room_cpp, "an Upset creature leaves a pleasure room at Neutral")
visit_end = use_room_cpp[use_room_cpp.index("isPleasureVisitFull(PleasureRoomKind::casino)") - 200:]
check("creature.popAction();" in visit_end[:600], "the visit ends at the limit by popping the action")
add_pleasure = extract(creature_cpp, "void Creature::addPleasureMood(")
check('getRoomConfigDouble("PleasureVisitMax")' in add_pleasure and "hasPleasureBuff()" in add_pleasure, "the limit is a key, a buff stops the gain")
finish = extract(creature_cpp, "void Creature::finishPleasureVisit(PleasureRoomKind kind, double buffTurns")
check('getRoomConfigDouble("PleasureBuffMood")' in finish and "if(gain > 0.0)" in finish and "lockWithoutGain" in finish, "buff for a gain, lock")
check('getRoomConfigDouble("SpaRelaxTurns")' in extract(creature_cpp, "void Creature::finishPleasureVisit(PleasureRoomKind kind, bool lockWithoutGain)"),
      "the buff of every room runs over SpaRelaxTurns")

# ---- E9: arena ----------------------------------------------------------------------------------------------------------
pit = extract(arena_cpp, "void RoomArena::updatePitMood(")
check("addPitSpectatorMood(moodPerTurn)" in pit, "spectators go through the visit limit")
check('addPitMood(config.getRoomConfigDoubleOrDefault("PitMoodVictor"' in pit, "the victor bonus is a plain event outside the limit")
check('addPitMood(solitary / ODApplication::turnsPerSecond)' in pit, "a solitary fighter's loss runs while it fights alone, outside the limit")
spectator = extract(creature_cpp, "void Creature::addPitSpectatorMood(")
check("beginPleasureVisit(PleasureRoomKind::arena)" in spectator and "finishPleasureVisit(PleasureRoomKind::arena, false)" in spectator,
      "watching is a visit that ends when the limit is reached")
check("ARENA_WATCH_GRACE_TURNS" in spectator and "finishPleasureVisit(PleasureRoomKind::arena, false)" in upkeep, "and when the creature stopped watching")
c = Creature(stored=600.0)
spectated = 0
while c.can_use(Creature.ARENA) and spectated < 100:
    if c.visit_kind != Creature.ARENA:
        c.begin(Creature.ARENA)
    c.add_pleasure(Creature.ARENA, float(rooms["PitMoodSpectator"]) / TURNS_PER_SECOND)
    spectated += 1
    if c.full(Creature.ARENA):
        c.finish_default(Creature.ARENA, False)
check(spectated == 20, "a spectator is full after 20 turns of 10 (200 / 10)")
near(c.stored, 800.0, "200 from watching")
check(c.has_buff() and c.lock_turns(Creature.ARENA) == 600.0, "the buff and the arena lock follow")
before = c.stored
c.event(float(rooms["PitMoodVictor"]))
near(c.stored, before + 250.0, "the victor bonus is outside the limit and the lock")
# Upset creatures still do not use the arena for their mood (today's rule)
check("roomType == RoomType::arena" in use_room_cpp or "RoomType::arena ||" in use_room_cpp, "Upset creatures do not train in the arena")

# ---- E10: tavern -----------------------------------------------------------------------------------------------------------
c = Creature(stored=600.0)
c.begin(Creature.TAVERN)
for _ in range(5):
    c.add_pleasure(Creature.TAVERN, float(tavern["BeerMood"]))
near(c.stored, 725.0, "five beers of a leisure visit")
c.add_pleasure(Creature.TAVERN, float(tavern["GameUnderdogMoodMax"]))
near(c.stored, 800.0, "the game win is cut at the 200 of the visit")
c = Creature(stored=600.0)
c.begin(Creature.TAVERN)
c.add_pleasure(Creature.TAVERN, float(tavern["NoCoinMood"]))
near(c.visit_gain, -8.33, "no coin lowers what the visit gained")
c.add_pleasure(Creature.TAVERN, float(tavern["BeerMood"]))
near(c.visit_gain, 16.67, "and the next beer counts on from there")
check(float(tavern["GameUnderdogMoodPerLevel"]) == 8.3333 and float(tavern["GameUnderdogMoodMax"]) == 83.3333, "underdog values (today x 0.25)")
check("addTavernMood(getTavernValue(\"BeerMood\"))" in tavern_cpp and "addTavernMood(getTavernValue(\"NoCoinMood\"))" in tavern_cpp, "beer and no coin")
check("addTavernMood(winnerMood)" in tavern_cpp and "addTavernMood(getTavernValue(\"GameLoserMood\"))" in tavern_cpp and
      "addTavernMood(getTavernValue(\"GameSpectatorMood\"))" in tavern_cpp, "games")
check("BeerMoodTurns" not in tavern_cpp and "NoCoinMoodTurns" not in tavern_cpp, "no code reads the removed keys")
check("void addTavernMood(double points);" in creature_h, "addTavernMood takes only the mood")
# a leisure visit ends with the buff and the lock, also without mood, so the job search does not send the guest back in at once
c = Creature(stored=600.0)
c.begin(Creature.TAVERN)
c.finish_default(Creature.TAVERN, True)
check(not c.has_buff() and c.lock_turns(Creature.TAVERN) == 600.0, "an empty leisure visit still closes the tavern")

# ---- E11: casino in mode Money ---------------------------------------------------------------------------------------------
c = Creature(stored=900.0)
c.begin(Creature.CASINO)
for _ in range(100):
    c.add_pleasure(Creature.CASINO, float(rooms["CasinoMoodMoney"]) / TURNS_PER_SECOND)
check(c.stored < 900.0, "the loss per second applies")
c.finish_default(Creature.CASINO, True)
check(not c.has_buff(), "a visit in mode Money gives no pleasure buff")
near(c.lock_turns(Creature.CASINO), 600.0, "but starts the lock")
check("mPayout == CasinoPayout::money" in extract(casino_cpp, "void RoomCasino::removeCreatureUsingRoom("), "the casino passes the mode")
check("CasinoPayout::money" in search_job_cpp and "continue;" in search_job_cpp[search_job_cpp.index("CasinoPayout::money"):][:80],
      "Upset creatures do not look for a casino in mode Money")
check("addPleasureMood(PleasureRoomKind::casino, points)" in extract(creature_cpp, "void Creature::addCasinoMood("), "casino mood through the visit")
check("addPleasureMood(PleasureRoomKind::temple, relief)" in extract(creature_cpp, "void Creature::addPrayerRelief("), "prayer relief through the visit")

# ---- save: the locks, the visit in progress and the buff ------------------------------------------------------------------
def write_locks(c):
    """The layout of the block [RoomLocks] of Creature::exportToStream."""
    if c.visit_kind < 0 and c.watch_turns <= 0 and not c.locks:
        return ""
    out = "[RoomLocks] %d %r %d %d" % (c.visit_kind, c.visit_gain, c.watch_turns, len(c.locks))
    for kind, turns in sorted(c.locks.items()):
        out += " %s %r" % ({2: "Casino", 3: "Temple", 4: "Arena"}[kind], turns)
    return out + " [/RoomLocks]"


def read_locks(c, text):
    words = text.split()
    check(words[0] == "[RoomLocks]" and words[-1] == "[/RoomLocks]", "block tags")
    c.visit_kind, c.visit_gain, c.watch_turns = int(words[1]), float(words[2]), int(words[3])
    count = int(words[4])
    c.locks = {}
    for index in range(count):
        c.locks[{"Casino": 2, "Temple": 3, "Arena": 4}[words[5 + 2 * index]]] = float(words[6 + 2 * index])


c = Creature(stored=640.0)
c.begin(Creature.CASINO)
c.add_pleasure(Creature.CASINO, 63.0)
c.locks = {Creature.TEMPLE: 411.0, Creature.ARENA: 12.5}
c.relax = 30.0
c.tavern_cooldown = 77
c.add_effect("Pleasure", 100.0, 252.0)
text = write_locks(c)
d = Creature()
read_locks(d, text)
check((d.visit_kind, d.visit_gain, d.watch_turns) == (Creature.CASINO, 63.0, 0), "the running visit loads one to one")
check(d.locks == {Creature.TEMPLE: 411.0, Creature.ARENA: 12.5}, "the locks of temple and arena load one to one with their turns")
check(write_locks(Creature()) == "", "nothing to keep: no block (old saves have none)")
# the other locks and the buff have their own saved places
check("TAVERN_COOLDOWN_SAVE_OPEN << \" \" << mTavernCooldownTurns" in creature_cpp, "the tavern lock is saved")
check("SPA_SAVE_OPEN << \" \" << mSpaMood << \" \" << mRelaxTurns" in creature_cpp, "the spa lock (the relaxation) is saved")
check("effect.mName << \" \" << effect.mStrength << \" \" << effect.mTurnsLeft" in creature_cpp, "the running buff is saved with strength and turns")
export = creature_cpp[creature_cpp.index("if(hasPleasureState())"):][:700]
check(re.search(r'ROOM_LOCKS_SAVE_OPEN << " " << mPleasureVisitKind << " " << mPleasureVisitGain << " "\s+<< mArenaWatchTurns << " " << mRoomLockTurns.size\(\);', export),
      "the writer: visit kind, gain, watch turns, number of locks")
check('os << " " << lock.first << " " << lock.second;' in export and "ROOM_LOCKS_SAVE_CLOSE" in export, "the writer: name and turns of every lock")
load = creature_cpp[creature_cpp.index("if(appearanceToken == ROOM_LOCKS_SAVE_OPEN)"):][:2400]
check("is >> loadedVisitKind >> loadedVisitGain >> loadedWatchTurns >> nbLocks" in load, "the reader takes the same order")
check("is >> lockName >> lockTurns" in load and "mRoomLockTurns = loadedLocks;" in load and "mPleasureVisitGain = kindKnown" in load, "the reader")
check("return false;" in load, "a damaged block is refused like the other blocks")
check('"[RoomLocks]"' in creature_cpp and '"[/RoomLocks]"' in creature_cpp, "the tags")
state = extract(creature_cpp, "bool Creature::hasPleasureState(")
check("mPleasureVisitKind >= 0" in state and "mArenaWatchTurns > 0" in state and "!mRoomLockTurns.empty()" in state, "hasPleasureState")
# a save without the block loads without a visit and with the locks the save already held (the relaxation, the tavern cooldown)
check("mPleasureVisitKind       (-1)" in creature_cpp and creature_cpp.count("mPleasureVisitKind       (-1)") == 2, "both constructors start without a visit")
# the members stand before the action list (a member declared first is destroyed last), so that they are still alive when the
# actions of a creature end its visit; the running effects too, because the buff starts then
actions = creature_h.index("std::vector<std::unique_ptr<CreatureAction>>    mActions;")
for member in ("double          mPleasureVisitGain;", "int32_t         mPleasureVisitKind;", "std::map<std::string, double> mRoomLockTurns;",
               "std::vector<CreatureMoodEffect> mMoodEffects;"):
    check(0 <= creature_h.index(member) < actions, member + " must be declared before the actions")

# ---- profile line: the buff Relaxed is listed once -----------------------------------------------------------------------
effects = extract(creature_cpp, "static std::string getProfileEffectsText(")
check("relaxedEffect" in effects and "(relaxTurns > 0.0) && !relaxedEffect" in effects, "Relaxed is not listed twice")

print("pleasure rooms ok")
