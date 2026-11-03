"""Stored creature mood (cases range, start, no_lair, solved, sensitivity, dirt, hated, slap, charisma, captive,
save_load, old_save, ai_keeper). Nothing is compiled: the values come from the shipped configuration, the rules are
worked out here with the same formulas as the sources, and the source wiring is pinned by tokens."""
import re
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def key(text, name):
    m = re.search(r"(?m)^\s*" + re.escape(name) + r"[ \t]+(\S+)", text)
    assert m, "missing " + name
    return float(m.group(1))


def check(cond, message):
    assert cond, message


glob = read("config/global.cfg")
creatures = read("config/creatures.cfg")
rooms = read("config/rooms.cfg")
creature_cpp = read("source/entities/Creature.cpp")
creature_h = read("source/entities/Creature.h")
manager = read("source/creaturemood/CreatureMoodManager.cpp")

MAX = key(glob, "CreatureBaseMood")
HAPPY, NEUTRAL, UPSET, ANGRY = (key(glob, "CreatureMoodHappy"), key(glob, "CreatureMoodUpset"),
                                key(glob, "CreatureMoodAngry"), key(glob, "CreatureMoodFurious"))


def level(mood):
    if mood >= HAPPY:
        return "Happy"
    if mood >= NEUTRAL:
        return "Neutral"
    if mood >= UPSET:
        return "Upset"
    if mood >= ANGRY:
        return "Angry"
    return "Furious"


def clamp(mood, bonus=0.0):
    return max(0.0, min(MAX + bonus, mood))


def creature_block(name):
    start = re.search(r"(?m)^\s*Name\s+" + name + r"\s*$", creatures)
    check(start, "type " + name)
    nxt = re.search(r"(?m)^\s*Name\s+\S+\s*$", creatures[start.end():])
    return creatures[start.start():start.end() + (nxt.start() if nxt else len(creatures))]


def modifier(block, name):
    m = re.search(r"(?m)^\s*" + name + r"\t([^\n]*)$", block)
    check(m, "modifier " + name)
    return [float(v) for v in m.group(1).split() if re.match(r"-?[\d.]+$", v)]


def sensitivity(block):
    return key(block, "MoodSensitivity")


# range and start: the level bounds sit inside 0..max, a new creature starts at the maximum
check((HAPPY, NEUTRAL, UPSET, ANGRY) == (1200, 1000, 500, 100) and MAX == 1500, "level ranges")
check(clamp(-5000) == 0 and clamp(99999) == MAX and clamp(99999, 200) == MAX + 200, "range")
check(level(MAX) == "Happy" and level(0) == "Furious" and level(99.9) == "Furious" and level(100) == "Angry", "levels")
check("mStoredMood              (ConfigManager::getSingleton().getCreatureBaseMood())" in creature_cpp, "start at the maximum")
check("std::max(0.0, std::min(static_cast<double>(ConfigManager::getSingleton().getCreatureBaseMood())" in creature_cpp,
      "range clamp in the creature")

# no_lair, solved, sensitivity
wizard = creature_block("Wizard")
jump, fall, reward = modifier(wizard, "NoLair")
check((jump, fall, reward) == (-300.0, -1.1905, 300.0), "NoLair line")
sens = sensitivity(wizard)
check(sens == 1.0, "Wizard sensitivity")
mood = MAX + jump * sens
check(mood == 1200 and level(mood) == "Happy", "no_lair jump to 1200")
turns = 0
while level(mood) != "Upset":
    mood += fall * sens
    turns += 1
check(abs(turns - 168) <= 1, "Upset after about 168 turns, got " + str(turns))
check(clamp(900 + reward * sens) == 1200, "solved: the lair comes back at 900")
rat, dragon = creature_block("Rat"), creature_block("Dragon")
check(sensitivity(rat) == 0.8 and sensitivity(dragon) == 1.25, "type sensitivities")
check(modifier(rat, "NoLair")[0] * sensitivity(rat) == -240.0 and modifier(dragon, "NoLair")[0] * sensitivity(dragon) == -375.0,
      "sensitivity jumps -240 / -375")
for token in ("changeStoredMoodBySensitivity(mood->getJump() * (amount - previous))",
              "changeStoredMoodBySensitivity(mood->getReward() * (previous - amount))",
              "changeStoredMoodBySensitivity(mood->getFall() * turns)",
              "if(mMoodPrimed)"):
    check(token in creature_cpp, token)

# dirt: stage 3 for 84 turns, then cleaned from stage 3
cleanliness = key(wizard, "Cleanliness")
check(cleanliness == 1.5, "Wizard Cleanliness")
fall3 = key(glob, "DirtMoodFallPerTurnStage3")
check(abs(fall3 * cleanliness * 84 - (-7.5)) < 0.1, "dirt fall in one minute")
check(key(glob, "DirtCleanedMoodStage3") * cleanliness == 75.0, "dirt cleaning reward")

# hated company: 84 turns near a creature
check(abs(modifier(wizard, "HatedCompany")[0] * 84 - (-10.0)) < 0.01, "hated: -10 in a minute, no jump")
check("HatedCompany" in creatures and modifier(wizard, "HatedCompany").__len__() == 1, "hated has only a fall")

# slap
slap = modifier(wizard, "Slapped")
check(slap[2] == -100.0 and slap[1] == 10.0, "slap -100, at most 10 slaps")
check("getNbRecentSlaps(slapped->getDurationTurns()) < slapped->getMaxSlaps()" in creature_cpp, "slap limit")

# charisma: effective mood is the stored mood plus the Charisma, the floor follows from the stored minimum 0
check("return mStoredMood + std::max(0.0, getItemEffect(\"Charisma\"));" in creature_cpp, "charisma adds to the effective mood")
check(MAX + 200 == 1700 and 0 + 200 == 200, "charisma 200: maximum 1700, never below 200")
check(level(0 + 200) == "Angry", "charisma wearer can still be angry")

# captive: no charisma floor, conversion and betrayal in the Furious range
check("if(isInContainment())\n        return mStoredMood;" in creature_cpp, "captive has no charisma floor")
for room in ("RoomPrison", "RoomTorture"):
    check("getMoodPoints() < " in read("source/rooms/" + room + ".cpp"), room + " Furious range gate")

# save_load: everything is written and read back
for token in ("[Mood] ", "mMoodEffects", "mMoodProblems", "mMoodDirtRooms", "mMoodRelationPairs", "\"[/Mood]\""):
    check(token in creature_cpp, "mood block " + token)
check("if(appearanceToken == \"[Mood]\")" in creature_cpp and "mMoodFromOldSave = false;" in creature_cpp, "mood block is read")


# old_save: -500 maps to 299.7 (Angry), -2500 to 0
def old_map(v):
    if v >= NEUTRAL:
        return min(MAX, v)
    if v >= 0:
        return UPSET + v / (NEUTRAL - 1) * (NEUTRAL - 1 - UPSET)
    if v >= -1000:
        return ANGRY + (v + 1000) / 999 * (UPSET - 1 - ANGRY)
    if v > -2000:
        return (v + 2000) / 1000 * (ANGRY - 1)
    return 0.0


check(abs(old_map(-500) - 299.7) < 0.05 and level(old_map(-500)) == "Angry", "old save -500")
check(old_map(-2500) == 0.0 and old_map(1300) == 1300 and old_map(1800) == MAX, "old save -2500 / high")
check(abs(old_map(0) - 500) < 1e-9 and abs(old_map(999) - 999) < 1e-9, "old save Upset range")
for token in ("return furious + (oldMood - oldAngryFrom) / (oldUpsetFrom - 1.0 - oldAngryFrom) * (angry - 1.0 - furious);",
              "return (oldMood - oldFuriousFrom) / (oldAngryFrom - oldFuriousFrom) * (furious - 1.0);"):
    check(token in manager, token)

# ai_keeper: the same creature code runs for every seat, the AI reads the levels
for name in ("AiCare.cpp", "AiWar.cpp"):
    check("getMoodPoints" not in read("source/ai/" + name), name + " reads levels only")
check("isHumanSeat" not in creature_cpp[creature_cpp.index("void Creature::computeMood()"):
                                         creature_cpp.index("void Creature::computeMood()") + 2500],
      "no seat type in the mood computation")
print("CHECKS OK")
