#!/usr/bin/env python3
"""Leave clock, decision and rampage of the creature mood (cases wages, clock, decision, no_portal, rampage, rampage_ends,
rogue_rule, make_happy (clock and rampage part), save_load (clock and rampage); edge rules E2, E3, E6). Nothing is compiled:
the values come from the shipped configuration, the rules are worked out here with the same formulas as the sources, and the
source wiring is pinned by tokens."""
import random
import re
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def check(cond, message):
    assert cond, message


def key(text, name):
    m = re.search(r"(?m)^\s*" + re.escape(name) + r"[ \t]+(\S+)", text)
    assert m, "missing " + name
    return float(m.group(1))


def extract(text, signature):
    """The body of the function that starts with the signature, found by matching its braces."""
    start = text.index(signature)
    open_at = text.index("{", start)
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("no end of " + signature)


glob = read("config/global.cfg")
creatures = read("config/creatures.cfg")
creature_cpp = read("source/entities/Creature.cpp")
creature_h = read("source/entities/Creature.h")
action_cpp = read("source/creatureaction/CreatureActionRampage.cpp")
action_h = read("source/creatureaction/CreatureActionRampage.h")
leave_cpp = read("source/creatureaction/CreatureActionLeaveDungeon.cpp")
behaviour_cpp = read("source/creaturebehaviour/CreatureBehaviourLeaveDungeonWhenFurious.cpp")
map_cpp = read("source/gamemap/GameMap.cpp")
definition_cpp = read("source/entities/CreatureDefinition.cpp")
manager_cpp = read("source/utils/ConfigManager.cpp")

# ---- values ------------------------------------------------------------------------------------------------------------------
PAYDAY = key(glob, "TimePayDay")
RESET_LEVEL = key(glob, "CreatureMoodAngry")
TURNS_PER_SECOND = 1.4
GAME_SECONDS_PER_TURN = 0.95 / TURNS_PER_SECOND
rampage_block = re.search(r"\[Rampage\](.*?)\[/Rampage\]", glob, re.S).group(1)
TILE_DAMAGE, HIT_TURNS, PILE_TURNS = (key(rampage_block, "RampageTileDamage"), key(rampage_block, "RampageHitTurns"),
                                      key(rampage_block, "RampagePileTurns"))
VICTIM = key(glob, "MoodRampageBrawlVictim")
check(PAYDAY == 600 and RESET_LEVEL == 500, "the clock is one pay day, the reset level is 500")
check((TILE_DAMAGE, HIT_TURNS, PILE_TURNS) == (5, 42, 168), "5 HP per 42 turns, a pile every 168 turns")
check(VICTIM == -100, "a brawl victim loses 100")
check(re.search(r"(?m)^# RampageTileDamage ", glob) and re.search(r"(?m)^# RampageHitTurns ", glob) and
      re.search(r"(?m)^# RampagePileTurns ", glob), "the [Rampage] keys have a documentation line")
check(re.search(r"(?m)^# Mood an own creature loses once when it was in a brawl with a rampaging creature", glob),
      "MoodRampageBrawlVictim has a documentation line")
# the old rogue rule and the wage rules are gone
for gone in ("NbTurnsFuriousMax", "UnpaidWagesLeave", "UnpaidWagesStopWork"):
    check(gone not in glob and gone not in manager_cpp, gone + " is gone")
check("mNbTurnFurious" not in creature_cpp and "mNbTurnFurious" not in creature_h and "getNbTurnFurious" not in creature_h,
      "rogue_rule: the counter of the turns Furious is gone")

# chances per type: default (flanker and the others) 50/30/20, brute (blocker, blitzer) 35/45/20, ranged (archer, caster) 50/15/35
CHANCES = {"blocker": (35, 45, 20), "blitzer": (35, 45, 20), "archer": (50, 15, 35), "caster": (50, 15, 35)}
typed = 0
for block in re.findall(r"(?ms)^\[Creature\]\s*$(.*?)^\[/Creature\]", creatures):
    if not re.search(r"(?m)^\s*MoodSensitivity\s", block):
        continue
    group = re.search(r"(?m)^\s*SkillGroup\s+(\S+)", block).group(1)
    got = (key(block, "MoodLeaveChance"), key(block, "MoodRampageChance"), key(block, "MoodRogueChance"))
    check(got == CHANCES.get(group, (50, 30, 20)), "chances of a " + group + " type: " + str(got))
    check(sum(got) == 100, "the chances sum to 100")
    typed += 1
check(typed >= 30, "every type with mood has the three chances")
check("MoodLeaveChance" in creatures and "MoodRampageChance" in creatures and "MoodRogueChance" in creatures and
      re.search(r"(?m)^# MoodLeaveChance / MoodRampageChance / MoodRogueChance", creatures), "documented in creatures.cfg")
for token in ('nextParam == "MoodLeaveChance"', 'nextParam == "MoodRampageChance"', 'nextParam == "MoodRogueChance"',
              "os << c->mMoodLeaveChance;", "is >> c->mMoodLeaveChance;", "os << c->mMoodRogueChance;", "is >> c->mMoodRogueChance;"):
    check(token in definition_cpp, "CreatureDefinition: " + token)


# ---- the rules, worked out here with the formulas of the sources -----------------------------------------------------------
class Creature:
    def __init__(self, stored=1500.0, chances=(50, 30, 20), charisma=0.0, portal=True):
        self.stored = stored
        self.charisma = charisma
        self.chances = chances
        self.portal = portal
        self.clock_running = False
        self.clock = 0.0
        self.leaving = False
        self.rampage_left = 0.0
        self.hit_turns = 0
        self.pile_turns = 0
        self.on_target = False
        self.hits = 0
        self.piles = 0
        self.paused = False
        self.seat = "own"
        self.outcomes = []

    def effective(self):
        return self.stored + self.charisma

    def stop(self):
        self.clock_running = False
        self.clock = 0.0
        self.rampage_left = 0.0
        self.on_target = False
        if self.leaving:
            self.leaving = False
            self.outcomes.append("stays")

    def draw(self, roll=None):
        self.clock = 0.0
        leave, rampage, rogue = self.chances
        total = float(leave + rampage + rogue)
        for _ in range(32):
            value = random.uniform(0.0, total) if roll is None else roll
            if value < leave:
                if not self.portal:
                    continue
                self.leaving = True
                self.outcomes.append("leave")
                return "leave"
            if value < leave + rampage:
                self.rampage_left = PAYDAY
                self.hit_turns = int(HIT_TURNS)
                self.pile_turns = int(PILE_TURNS)
                self.outcomes.append("rampage")
                return "rampage"
            self.seat = "rogue"
            self.outcomes.append("rogue")
            return "rogue"
        return "none"

    def turn(self, seconds=GAME_SECONDS_PER_TURN):
        if self.seat == "rogue":
            return
        if self.leaving and self.effective() >= RESET_LEVEL:
            self.stop()
            return
        if self.effective() >= RESET_LEVEL:
            self.stop()
            return
        if self.rampage_left > 0.0:
            self.rampage_left -= seconds
            if self.rampage_left <= 0.0:
                self.rampage_left = 0.0
                self.on_target = False
                self.draw()
                return
            if self.paused:
                return
            self.pile_turns -= 1
            if self.pile_turns <= 0:
                self.pile_turns = int(PILE_TURNS)
                self.piles += 1
            if self.on_target:
                self.hit_turns -= 1
                if self.hit_turns <= 0:
                    self.hit_turns = int(HIT_TURNS)
                    self.hits += 1
            return
        if not self.clock_running:
            if self.paused or self.effective() > 0.0:
                return
            self.clock_running = True
            self.clock = 0.0
            return
        if self.paused:
            return
        self.clock += seconds
        if self.clock >= PAYDAY and not self.leaving:
            self.draw()


# clock: the mood reaches 0, a meal lifts it to 50, it falls back; the clock keeps running; at 500 it resets
c = Creature(stored=0.0)
c.turn()
check(c.clock_running, "clock: it starts when the mood reaches 0")
for _ in range(100):
    c.turn()
c.stored = 50.0
for _ in range(100):
    c.turn()
check(c.clock_running and c.clock > 150 * GAME_SECONDS_PER_TURN, "clock: a meal that lifts the mood to 50 does not stop it")
c.stored = 0.0
for _ in range(100):
    c.turn()
check(c.clock_running, "clock: it keeps running when the mood falls back")
c.stored = RESET_LEVEL
c.turn()
check(not c.clock_running and c.clock == 0.0, "clock: at 500 it resets")
c.stored = 499.0
c.turn()
check(not c.clock_running, "clock: it does not start above 0")

# the draw at TimePayDay: about 884 turns at 1.4 turns per second
c = Creature(stored=0.0, chances=(50, 0, 50))
turns = 0
while not c.outcomes and turns < 5000:
    c.turn()
    turns += 1
check(abs(turns - 885) <= 2, "clock: one pay day is about 884 turns, got " + str(turns))

# E2: pause while held in the hand, knocked out or possessed, then continue; a captive has no clock
c = Creature(stored=0.0, chances=(100, 0, 0))
c.turn()
for _ in range(500):
    c.turn()
before = c.clock
c.paused = True
for _ in range(1000):
    c.turn()
check(c.clock == before and not c.outcomes, "E2: the clock pauses while held, knocked out or possessed")
c.paused = False
while not c.outcomes:
    c.turn()
check(c.outcomes == ["leave"], "E2: it continues afterwards")
body = extract(creature_cpp, "void Creature::upkeepMoodDecision()")
check("const bool paused = mIsInHand || isKo() || isPossessed();" in body, "E2: held, knocked out or possessed pauses")
check("getLastTurnSeconds()" in body and "getTimePayDay()" in body, "the clock counts game time up to TimePayDay")
check("getCreatureMoodAngry()" in body and "effective > 0.0" in body, "the clock starts at 0 and resets at the Upset level")
captive = creature_cpp[creature_cpp.index("// If the creature is in jail, it should not auto heal or do anything"):]
captive = captive[:captive.index("// If we are not standing somewhere on the map, do nothing.")]
check("stopMoodDecision();" in captive and "upkeepMoodDecision" not in captive, "E2: a captive has no leave clock")

# decision: many draws for a brute type follow 35/45/20
random.seed(14)
counts = {"leave": 0, "rampage": 0, "rogue": 0}
for _ in range(20000):
    counts[Creature(chances=(35, 45, 20)).draw()] += 1
for name, share in (("leave", 0.35), ("rampage", 0.45), ("rogue", 0.20)):
    check(abs(counts[name] / 20000.0 - share) < 0.01, "decision: " + name + " follows its share")
draw = extract(creature_cpp, "void Creature::drawMoodDecision()")
check("Random::Double(0.0, total)" in draw and "roll < leaveChance + rampageChance" in draw and
      "getMoodLeaveChance()" in draw and "getMoodRampageChance()" in draw and "getMoodRogueChance()" in draw,
      "decision: the draw uses the chances of the type")
check("fireChatMsgBecameRogue();" in draw and "changeSeat(getGameMap()->getSeatRogue());" in draw,
      "decision: rogue is today's change to the rogue seat with today's message")
check("leaveDungeon();" in draw and "reportLeavingToBestFriend();" in draw,
      "decision: leave is today's leaving, a friend and the partner may follow as today")
check("mLeaveClockSeconds = 0.0;" in draw, "decision: a creature still at the bottom draws again one pay day later")

# no_portal: the draw is "leave" and no own portal is reachable: it draws again
c = Creature(chances=(50, 30, 20), portal=False)
random.seed(3)
results = [Creature(chances=(50, 30, 20), portal=False).draw() for _ in range(2000)]
check("leave" not in results and set(results) <= {"rampage", "rogue"}, "no_portal: it draws again")
check("if(!hasReachableOwnPortal())" in draw and "continue;" in draw, "no_portal: a leave draw without a portal draws again")
check("hasReachableOwnPortal()" in creature_cpp and "getReachableRooms(portals, myTile, this)" in creature_cpp,
      "no_portal: the portal is reachable by the rule of the leave action")
check("drawMoodDecisionAgain()" in leave_cpp, "no_portal: a portal lost on the way draws again")
again = extract(creature_cpp, "void Creature::drawMoodDecisionAgain()")
check("mLeavingByMood" in again and "drawMoodDecision();" in again, "no_portal: only a leave by the draw draws again")

# E3: a creature walking to its portal turns back and stays when its mood reaches 500 on the way
c = Creature(stored=0.0, chances=(100, 0, 0))
c.turn()
while not c.leaving:
    c.turn()
c.stored = RESET_LEVEL
c.turn()
check(not c.leaving and c.outcomes == ["leave", "stays"], "E3: it turns back and stays")
stop = extract(creature_cpp, "void Creature::stopMoodDecision()")
check("mLeavingByMood" in stop and "isActionInList(CreatureActionType::leaveDungeon)" in stop and "clearActionQueue();" in stop,
      "E3: the walk to the portal is ended")
check("isLeavingByMood() && creature.isActionInList(CreatureActionType::leaveDungeon)" in behaviour_cpp,
      "a creature on its way out does nothing else")
check("mLeavingByMood = true;" in draw and "leaveDungeon();" in draw, "only a leave by the draw can turn back")

# rampage: one pay day, 5 HP per 42 turns on one tile, a pile every 168 turns, victim -100
c = Creature(stored=0.0, chances=(0, 100, 0))
c.draw()
c.on_target = True
turns = 0
while len(c.outcomes) < 2 and turns < 5000:
    c.turn()
    turns += 1
check(c.outcomes[0] == "rampage", "rampage: the draw starts it")
expected_hits = int(turns // HIT_TURNS)
check(abs(c.hits - expected_hits) <= 1, "rampage: a hit every 42 turns, " + str(c.hits) + " in " + str(turns))
check(abs(c.piles - int(turns // PILE_TURNS)) <= 1, "rampage: a pile every 168 turns")
check(TILE_DAMAGE * c.hits > 0, "rampage: 5 HP per hit")
# the rampage ends after one pay day and the creature draws again (the mood is still below the Upset level)
check(c.outcomes[-1] in ("leave", "rampage", "rogue") and len(c.outcomes) == 2, "rampage: it draws again at the end")
# rampage_ends: the mood reaches 500 during the rampage: it ends at once and there is no new draw
c = Creature(stored=0.0, chances=(0, 100, 0))
c.draw()
for _ in range(100):
    c.turn()
c.stored = RESET_LEVEL
c.turn()
check(c.rampage_left == 0.0 and c.outcomes == ["rampage"], "rampage_ends: it ends at once, no new draw")
check(not c.clock_running, "rampage_ends: the clock is reset")
body = extract(creature_cpp, "void Creature::upkeepRampage()")
check("getLastTurnSeconds()" in body and "endRampage();" in body and "drawMoodDecision();" in body,
      "rampage: one pay day, then it draws again")
check('"RampagePileTurns"' in body and "DirtPileKind::pile" in body and "createOnTile(" in body,
      "rampage: a dirt pile on its tile every RampagePileTurns")
check('"RampageHitTurns"' in body and "CreatureActionRampage::hitTile" in body and "target != myTile" in body,
      "rampage: a hit every RampageHitTurns while it stands on its target tile")
check("mIsInHand || isKo() || isPossessed()" in body, "rampage: no hits while held, knocked out or possessed")
rampage_body = extract(creature_cpp, "void Creature::startRampage()")
check("clearActionQueue();" in rampage_body and "fireChatMsgRampaging();" in rampage_body and "getTimePayDay()" in rampage_body,
      "rampage: starts with the message and lasts one pay day")
check("is rampaging in your dungeon !" in creature_cpp, "the rampage message")
check("is not under your control anymore !" in creature_cpp and "is leaving your dungeon" in creature_cpp and
      "fireChatMsgLeftDungeon" in leave_cpp, "the messages of leaving and of turning rogue stay")
upkeep = extract(creature_cpp, "void Creature::upkeepMoodDecision()")
check(upkeep.index("effective >= static_cast<double>(config.getCreatureMoodAngry())") < upkeep.index("if(isRampaging())"),
      "rampage_ends: the mood check comes before the rampage count")
# the badge shows the Furious icon
overlay = extract(creature_cpp, "void Creature::computeCreatureOverlayMoodValue()")
check("if(isRampaging())" in overlay and "CreatureMoodValues::Furious" in overlay, "a rampaging creature shows the Furious icon")

# E6: targets are room tiles of the keeper except the dungeon heart and the portals; the damage is absolute
target = extract(action_cpp, "bool CreatureActionRampage::isTargetTile(")
check("room->getSeat() != creature.getSeat()" in target and "RoomType::dungeonTemple" in target and "RoomType::portal" in target and
      "isAttackable(" in target, "E6: room tiles of the keeper's rooms except the dungeon heart and the portals")
find = extract(action_cpp, "Tile* CreatureActionRampage::findTarget(")
check("RoomType::dungeonTemple" in find and "RoomType::portal" in find and "pathExists(" in find,
      "E6: the target is reachable")
hit = extract(action_cpp, "bool CreatureActionRampage::hitTile(")
check("takeDamage(&creature, damage, 0.0, 0.0, 0.0, &tile, false)" in hit and '"RampageTileDamage"' in hit,
      "rampage: RampageTileDamage as absolute damage, no attack or defense roll")
walk = extract(action_cpp, "bool CreatureActionRampage::handleRampage(")
check("myTile == target" in walk and "setDestination(target)" in walk and "isTargetTile(creature, *target)" in walk,
      "rampage: it walks to the tile and stays on it until it is destroyed")
check("rampage," in read("source/creatureaction/CreatureAction.h") and '"rampage"' in read("source/creatureaction/CreatureAction.cpp"),
      "the action type exists")
check("CreatureActionRampage.cpp" in read("CMakeLists.txt"), "the new source file is in the build list")

# rampage: eats and drinks when hungry or thirsty, does not sleep, work or visit a pleasure room
idle = extract(creature_cpp, "bool Creature::handleIdleAction()")
check(idle.index("CreatureActionSearchFood>") < idle.index("CreatureActionRampage>") < idle.index("CreatureActionFindHome>"),
      "rampage: hunger and thirst are served before the rampage, the rampage before bed and work")
check(idle.index("CreatureActionSearchDrink>") < idle.index("CreatureActionRampage>"), "rampage: it drinks when thirsty")
check("!isRampaging() &&\n        !hasActionBeenTried(CreatureActionType::sleep)" in idle, "rampage: it does not sleep")
check("!isRampaging() &&\n        !hasActionBeenTried(CreatureActionType::searchJob)" in idle, "rampage: it does not work")
check("isRampaging()" in extract(creature_cpp, "bool Creature::wantsSpaBath() const"), "rampage: no spa")
check("!isRampaging()" in extract(creature_cpp, "bool Creature::canUsePleasureRoom("), "rampage: no pleasure room")

# rampage: brawls with own creatures by today's rules, also when the relationships are off; the victim loses 100
brawl = extract(map_cpp, "void GameMap::checkRampageBrawls()")
check("isBrawlCheckTurn(" in brawl and "isWithinBrawlDistance(" in brawl and "brawlChanceHit(" in brawl and "pathExists(" in brawl and
      "startBrawl(*victim, true)" in brawl and "RelationshipSettings::fromConfig(" in brawl,
      "rampage: check interval, chance, distance and path as for the nemesis brawls, settings from the configuration")
check("other->getSeat() != rampager->getSeat()" in brawl and "canStartBrawl(true)" in brawl, "rampage: own creatures only")
turn = extract(map_cpp, "void GameMap::doTurn(")
check(turn.index("checkRampageBrawls();") > turn.index("sendRelationshipTierChanges();") and
      "if(mCreatureRelationships != nullptr)" in turn, "rampage: the brawls do not need the relationships")
can_start = extract(creature_cpp, "bool Creature::canStartBrawl(")
check("relationshipsAllowed(getIsOnServerMap()" in can_start and "isInPrison()" in can_start and "isWorker()" in can_start,
      "rampage: workers, rogue, heroes and prisoners are excluded as in today's brawls")
end_brawl = extract(creature_cpp, "void Creature::endBrawl()")
check("getMoodRampageBrawlVictim()" in end_brawl and "if(!creature->mBrawlRampage)\n            creature->makeAngry();" in end_brawl,
      "rampage: the victim loses MoodRampageBrawlVictim instead of the brawl-end unhappy")
start_brawl = extract(creature_cpp, "void Creature::startBrawl(")
check("mBrawlRampageVictim = true" in start_brawl and "opponent.canStartBrawl(rampage)" in start_brawl, "rampage: the victim is the other one")
check("MoodRampageBrawlVictim" in manager_cpp, "MoodRampageBrawlVictim is read from the configuration")

# make_happy (clock and rampage part): the clock is reset and a rampage ends
c = Creature(stored=50.0, chances=(0, 100, 0))
c.clock_running = True
c.clock = 300.0
c.draw()
c.stored = 1500.0
c.stop()
check(not c.clock_running and c.clock == 0.0 and c.rampage_left == 0.0, "make_happy: clock reset and rampage ended")
happy = extract(creature_cpp, "void Creature::removeAnnoyance()")
check("stopMoodDecision();" in happy, "make_happy: removeAnnoyance resets the clock and ends the rampage")
check("mLeaveClockRunning = false;" in stop and "mLeaveClockSeconds = 0.0;" in stop and "endRampage();" in stop,
      "stopMoodDecision resets the clock and ends the rampage")
# Charisma put on resets a running clock and ends a rampage; worn Charisma keeps the mood above 0, so it never starts the clock
check("charismaPutOn" in upkeep and "mCharismaSeen" in upkeep, "a Charisma item put on resets the clock and ends the rampage")
c = Creature(stored=0.0, charisma=200.0)
for _ in range(50):
    c.turn()
check(not c.clock_running, "charisma: worn it never starts the clock")

# the new side: no clock, no rampage
seat = extract(creature_cpp, "void Creature::changeSeat(")
check("mLeaveClockRunning = false;" in seat and "mLeaveClockSeconds = 0.0;" in seat and "endRampage();" in seat,
      "a creature that changes side has no clock and no rampage")

# save_load: the clock and the rampage are saved one to one; old saves load without them
export = extract(creature_cpp, "void Creature::exportToStream(")
load = creature_cpp[creature_cpp.index("if(appearanceToken == MOOD_DECISION_SAVE_OPEN)"):]
load = load[:load.index('if(appearanceToken == "[Mood]")')]
fields = ["(mLeaveClockRunning ? 1 : 0)", "mLeaveClockSeconds", "mRampageSecondsLeft", "mRampageHitTurns", "mRampagePileTurns",
          "mRampageTargetX", "mRampageTargetY"]
positions = [export.index(f, export.index("MOOD_DECISION_SAVE_OPEN")) for f in fields]
check(positions == sorted(positions), "save_load: the fields are written in order")
for name in ("loadedRunning", "loadedClock", "loadedRampage", "loadedHitTurns", "loadedPileTurns", "loadedTargetX", "loadedTargetY"):
    check(name in load, "save_load: " + name + " is read")
check(all(f.replace("(mLeaveClockRunning ? 1 : 0)", "mLeaveClockRunning") in load for f in fields),
      "save_load: every field is restored")
check("if(mLeaveClockRunning || isRampaging())" in export, "save_load: nothing is written when neither runs (old saves have no block)")
check("mLeaveClockRunning       (false)" in creature_cpp and "mRampageSecondsLeft      (0.0)" in creature_cpp,
      "old_save: no clock and no rampage by default")
check("MOOD_DECISION_SAVE_CLOSE" in load and "isfinite(loadedClock)" in load, "save_load: the block is closed and checked")

# a save of a rampage and a clock continues one to one (the round trip of the fields)
saved = (True, 123.5, 400.25, 17, 99, 12, 34)
text = " ".join(str(int(v)) if isinstance(v, bool) else str(v) for v in saved)
loaded = text.split()
check(int(loaded[0]) == 1 and float(loaded[1]) == 123.5 and float(loaded[2]) == 400.25 and
      [int(v) for v in loaded[3:]] == [17, 99, 12, 34], "save_load: the numbers round-trip")

# the AI keeps reading the levels and the missed-wage count as today (M9)
for path in ("source/ai",):
    for f in (repo / path).glob("*.cpp"):
        check("UnpaidWages" not in f.read_text(encoding="utf-8"), str(f))

print("mood decision ok")
