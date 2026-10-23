"""Static check of the research effects: the [ResearchEffects] block of skills.cfg, the config values that moved out of
the code, the door health values and the places that apply each effect.

The expected lines are written out here independently of the config. Nothing is compiled.
Usage: python source/tests/check_world_balance_effects.py
"""
import re
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8")


def calls(text, name):
    """The argument text of every call of name(...) in text, with matching parentheses."""
    found = []
    for match in re.finditer(re.escape(name) + r"\(", text):
        index = match.end()
        depth = 1
        while depth:
            depth += (text[index] == "(") - (text[index] == ")")
            index += 1
        found.append(text[match.end():index - 1])
    return found


DAMAGE = ("4.50", "10.63", "18.86")
DOOR_HP = ("1.840", "2.882", "9.044")
# (skill type, effect, mode, level 1, level 2, level 3) in the order of the plan table
EXPECTED = [
    ("roomTreasury", "GoldPerTile", "mul", "1.0", "1.25", "1.5"),
    ("roomDormitory", "SleepRecovery", "mul", "1.0", "1.2", "1.4"),
    ("roomHatchery", "LayInterval", "mul", "1.0", "0.8", "0.8"),
    ("roomHatchery", "Capacity", "mul", "1.0", "1.0", "1.5"),
    ("roomLibrary", "PointsPerWork", "mul", "1.0", "1.2", "1.4"),
    ("roomTrainingHall", "XpPerHit", "mul", "1.0", "1.2", "1.4"),
    ("roomWorkshop", "PointsPerWork", "mul", "1.0", "1.2", "1.4"),
    ("roomGuardRoom", "WakefulnessPerDuty", "mul", "1.0", "0.8", "0.667"),
    ("roomCasino", "Fee", "mul", "1.0", "1.2", "1.4"),
    ("roomCasino", "Mood", "mul", "1.0", "1.2", "1.4"),
    ("roomArena", "LevelCap", "mul", "1.0", "1.25", "1.5"),
    ("roomPrison", "Capacity", "mul", "1.0", "1.5", "2.0"),
    ("roomPrison", "SkeletonLevel", "add", "0", "1", "2"),
    ("roomCrypt", "RotTime", "mul", "1.0", "0.8", "0.667"),
    ("roomBridgeWooden", "ClaimResistance", "mul", "1.0", "1.25", "1.5"),
    ("roomBridgeStone", "ClaimResistance", "mul", "1.0", "1.5", "2.0"),
    ("roomTorture", "ConversionSpeed", "mul", "1.0", "1.2", "1.4"),
    ("roomTemple", "PrayerMana", "mul", "1.0", "1.2", "1.4"),
    ("keeperDominion", "CreatureLimit", "add", "2", "4", "6"),
] + [(trap, "Damage", "mul") + DAMAGE for trap in
     ("trapCannon", "trapSpike", "trapBoulder", "trapGas", "trapLightning", "trapFireburst")] + [
    ("trapAlarm", "Reload", "mul", "1.0", "0.8", "0.667"),
    ("trapFear", "Duration", "mul", "1.0", "1.25", "1.5"),
    ("trapFreeze", "Duration", "mul", "1.0", "1.25", "1.5"),
    ("trapWatchBanner", "AuraRadius", "mul", "1.0", "1.25", "1.5"),
    ("trapTrigger", "Radius", "add", "0", "1", "2"),
] + [(door, "HP", "mul") + DOOR_HP for door in
     ("trapDoorWooden", "trapDoorIronbound", "trapDoorSteel", "trapDoorBarricade", "trapDoorSecret", "trapDoorRuned")] + [
    ("trapDoorRuned", "Damage", "mul") + DAMAGE,
    ("keeperHeartFortitude", "HeartHP", "mul", "1.698", "2.474", "6.0"),
    ("keeperHeartMending", "HeartHeal", "mul", "1.698", "2.474", "6.0"),
    ("keeperManaFlow", "HeartMana", "mul", "1.1", "1.2", "1.3"),
    ("spellSummonWorker", "Price", "mul", "1.0", "0.9", "0.8"),
    ("spellCreatureHeal", "HealPerTurn", "mul") + DAMAGE,
    ("spellCreatureHaste", "Speed", "mul", "1.0", "1.1", "1.2"),
    ("spellEyeEvil", "Duration", "mul", "1.0", "1.5", "2.0"),
    ("spellEyeEvil", "Radius", "add", "0", "1", "2"),
    ("spellCreatureDefense", "Bonus", "mul", "4.16", "8.91", "15.84"),
    ("spellCreatureStrength", "Factor", "dev", "1.0", "1.5", "2.0"),
    ("spellCreatureWeak", "Factor", "dev", "1.0", "1.5", "2.0"),
    ("spellCreatureSlow", "Factor", "mul", "1.0", "0.9", "0.8"),
    ("spellCallToWar", "Lifetime", "mul", "1.0", "1.3", "1.6"),
    ("spellLightning", "Damage", "mul") + DAMAGE,
    ("spellCreatureExplosion", "Damage", "mul") + DAMAGE,
    ("spellTremor", "Damage", "mul") + DAMAGE,
    ("spellInferno", "Damage", "mul") + DAMAGE,
    ("spellPossess", "ManaPerSecond", "mul", "1.0", "0.8", "0.667"),
    ("spellDefector", "Duration", "mul", "1.0", "1.25", "1.5"),
    ("spellHexenHen", "Duration", "mul", "1.0", "1.25", "1.5"),
    ("spellCreateGold", "Gold", "mul", "1.0", "1.25", "1.5"),
]
assert len(EXPECTED) == 58, "the plan table has 58 lines (rows with several skill types count once per skill type)"

# --- skills.cfg: the [ResearchEffects] block -------------------------------------------------------------------------
skills_cfg = read("config/skills.cfg")
block = skills_cfg[skills_cfg.index("\n[ResearchEffects]\n"):skills_cfg.index("\n[/ResearchEffects]\n")]
lines = [line.split() for line in block.splitlines()[2:] if line.strip() and not line.strip().startswith("#")]
assert len(lines) == 58, "one line per effect: %d" % len(lines)
for index, (line, expected) in enumerate(zip(lines, EXPECTED)):
    assert tuple(line) == expected, "line %d of [ResearchEffects]: %s, expected %s" % (index + 1, line, expected)
assert skills_cfg.index("\n[/FreeLevelOne]\n") < skills_cfg.index("\n[ResearchEffects]\n"), "the block follows the free level one block"
skill_names = set(re.findall(r"^\s+([A-Za-z]+)\t\d+\s*$", skills_cfg[:skills_cfg.index("\n[/Skills]\n")], re.M))
assert len(skill_names) == 53
assert {line[0] for line in lines} <= skill_names, "every line names one of the 53 skills"
header = skills_cfg[:skills_cfg.index("\n[Skills]\n")]
assert "[ResearchEffects]" in header and "mul" in header and "add" in header and "dev" in header, "the modes are documented"
for effect in sorted({line[1] for line in lines}):
    assert re.search(r"\b%s\b" % effect, header), "effect %s is documented in the header" % effect

# --- config values that moved out of the code ------------------------------------------------------------------------
rooms_cfg = read("config/rooms.cfg")
traps_cfg = read("config/traps.cfg")
global_cfg = read("config/global.cfg")


def value(text, key):
    matches = re.findall(r"^\s+%s\s+(\S+)\s*$" % key, text, re.M)
    assert len(matches) == 1, "%s must be set once" % key
    return float(matches[0])


def documented(text, key):
    return re.search(r"^#\s*%s\s+\(" % key, text, re.M) is not None


for key, expected in (("TreasuryGoldPerTile", 1000), ("DormitoryWakefulnessPerTurn", 1.5), ("PrisonSkeletonBaseLevel", 1),
                      ("DungeonHeartHealPerSecond", 3.775), ("DungeonHeartManaPerSecond", 30)):
    assert value(rooms_cfg, key) == expected, key
    assert documented(rooms_cfg, key), "%s is documented in the header of rooms.cfg" % key
assert value(global_cfg, "CreaturesPerPortal") == 5
assert re.search(r"^#.*CreaturesPerPortal", global_cfg, re.M), "CreaturesPerPortal is documented"
assert value(traps_cfg, "TriggerRadius") == 1
assert documented(traps_cfg, "TriggerRadius")
doors = {"WoodenDoorHP": 200, "IronboundDoorHP": 600, "SteelDoorHP": 800, "BarricadeDoorHP": 300, "SecretDoorHP": 300,
         "RunedDoorHP": 1200}
for key, expected in doors.items():
    assert value(traps_cfg, key) == expected, key
assert value(traps_cfg, "RunedDoorRegenPerTurn") == 1.4
assert abs(1.4 / 1200 - 0.07 / 60) < 1e-12, "the runed door regenerates the same share of its health as before"
# Expected (plan): a level 1 wooden door holds 368 health, a level 1 cannon shot does 92 to 138 damage
assert abs(doors["WoodenDoorHP"] * 1.840 - 368) < 1e-9
assert round(value(traps_cfg, "CannonDamagePerHitMin") * 4.50) == 92 and round(value(traps_cfg, "CannonDamagePerHitMax") * 4.50) == 138

# --- the mechanism ---------------------------------------------------------------------------------------------------
manager = read("source/game/SkillManager.cpp")
manager_header = read("source/game/SkillManager.h")
config_header = read("source/utils/ConfigManager.h")
config = read("source/utils/ConfigManager.cpp")
assert "double base, const std::string& effect)" in manager_header
assert "bool secondary" not in manager_header and "bool secondary" not in manager, "the secondary flag is gone"
value_function = manager[manager.index("double SkillManager::getResearchValue(SkillType type, uint32_t level"):
                         manager.index("namespace\n{\n//! \\brief The config file a base value")]
assert "case SkillType::" not in value_function, "the switch over the skills is replaced by the config lines"
assert "if(level == 0)" in value_function and "return base;" in value_function, "level 0 returns the base"
assert "line == nullptr" in value_function, "an effect without a line returns the base"
assert "base + value" in value_function and "1.0 + (base - 1.0) * value" in value_function and "base * value" in value_function
assert "return getResearchValue(type, seat == nullptr ? 0 : seat->getSkillLevel(type), base, effect);" in manager
assert '"[ResearchEffects]"' in config and '"[/ResearchEffects]"' in config and "mul" in config and "dev" in config
assert "ResearchEffectLine" in config_header and "getResearchEffect(" in config_header
assert "getResearchDescription(type, level)" in manager or "SkillManager::getResearchDescription(" in manager

# every effect name has a constant, and every line of the config is applied by the code that does the described job
effect_names = {line[1] for line in lines}
for effect in effect_names:
    assert 'static const std::string %s = "%s";' % (effect, effect) in manager_header, effect
sources = {}
for path in sorted((repo / "source").rglob("*.cpp")):
    if "tests" in path.parts or path.name == "SkillManager.cpp":
        continue
    sources[path] = path.read_text(encoding="utf-8", errors="replace")
applied = []
for text_path, text in sources.items():
    for arguments in calls(text, "SkillManager::getResearchValue"):
        applied.append((text_path, arguments))
# the skill of a bridge and of a door is picked by a helper in the file of the call
INDIRECT = {"roomBridgeWooden": "RoomBridge.cpp", "roomBridgeStone": "RoomBridge.cpp",
            "trapDoorWooden": "TrapDoor.cpp", "trapDoorIronbound": "TrapDoor.cpp", "trapDoorSteel": "TrapDoor.cpp",
            "trapDoorBarricade": "TrapDoor.cpp", "trapDoorSecret": "TrapDoor.cpp", "trapDoorRuned": "TrapDoor.cpp"}
for skill, effect, *_ in EXPECTED:
    direct = [path for path, arguments in applied if ("SkillType::" + skill) in arguments and ("ResearchEffect::" + effect) in arguments]
    if direct:
        continue
    assert skill in INDIRECT, "%s %s is not applied anywhere" % (skill, effect)
    assert any(path.name == INDIRECT[skill] and ("ResearchEffect::" + effect) in arguments for path, arguments in applied), \
        "%s %s is not applied by %s" % (skill, effect, INDIRECT[skill])
door = read("source/traps/TrapDoor.cpp")
for skill in ("trapDoorWooden", "trapDoorIronbound", "trapDoorSteel", "trapDoorBarricade", "trapDoorSecret", "trapDoorRuned"):
    assert "SkillType::" + skill in door[door.index("static SkillType getDoorSkill("):door.index("double TrapDoor::getHP(")], skill
get_hp = door[door.index("double TrapDoor::getHP("):door.index("double TrapDoor::takeDamage(")]
take_damage = door[door.index("double TrapDoor::takeDamage("):door.index("TrapDoor::TrapDoor(")]
assert "getDoorSkill(mDoorType)" in get_hp and "getDoorSkill(mDoorType)" in take_damage, "health and damage use the type of the door"
assert "trapDoorWooden" not in get_hp and "trapDoorWooden" not in take_damage, "not the wooden door level for every door"
bridge = read("source/rooms/RoomBridge.cpp")
assert "getResearchValue(getSeat(), research, 1.0, ResearchEffect::ClaimResistance)" in bridge
# nothing that was hard-coded is left behind in the code
treasury = read("source/rooms/RoomTreasury.cpp")
assert "maxGoldinTile" not in treasury and 'getRoomConfigDouble("TreasuryGoldPerTile")' in treasury
sleep = read("source/creatureaction/CreatureActionSleep.cpp")
assert 'getRoomConfigDouble("DormitoryWakefulnessPerTurn")' in sleep and ", 1.5" not in sleep
prison = read("source/rooms/RoomPrison.cpp")
assert 'getRoomConfigDouble("PrisonSkeletonBaseLevel")' in prison
assert "(mActualTiles.size() + 1)" in prison and "ResearchEffect::Capacity" in prison
temple = read("source/rooms/RoomDungeonTemple.cpp")
assert "HEART_HEAL_PER_SECOND" not in temple and "HEART_HEAL_PER_SECOND" not in read("source/rooms/RoomDungeonTemple.h")
assert 'getRoomConfigDouble("DungeonHeartHealPerSecond")' in temple
assert "mHeartHP * heartHPFactor / mHeartHPFactor" in temple, "the current health is multiplied by (new factor / old factor)"
game_map = read("source/gamemap/GameMap.cpp")
assert "MANA_HEART_INCOME_PER_SECOND" not in game_map and 'getRoomConfigDouble("DungeonHeartManaPerSecond")' in game_map
limit = game_map[game_map.index("uint32_t GameMap::getMaxNumberCreatures("):game_map.index("void GameMap::setSkirmishSettings(")]
assert limit.index("getNbCreatureMaxIncrease()") < limit.index("ResearchEffect::CreatureLimit") < limit.index("getMaxCreaturesPerSeatAbsolute()"), \
    "the default and the portals first, then the Dominion value, then the absolute limit"
portal = read("source/rooms/RoomPortal.cpp")
assert "getCreaturesPerPortal()" in portal and "mNbCreatureMaxIncrease = 5" not in portal
trigger = read("source/traps/TrapTrigger.cpp")
assert 'getTrapConfigDouble("TriggerRadius")' in trigger and "dx = -radius; dx <= radius" in trigger and "dy = -radius; dy <= radius" in trigger
# fractional values: the timers and the readers of the plan are doubles
assert "double mReloadTime;" in read("source/traps/Trap.h") and 'getTrapConfigDouble("AlarmReloadTurns")' in read("source/traps/TrapAlarm.cpp")
assert "double mFearTurns;" in read("source/traps/TrapFear.h") and "double mFreezeTurns;" in read("source/traps/TrapFreeze.h")
assert "std::pair<Creature*, double>" in read("source/rooms/RoomCrypt.h")
assert 'getRoomConfigDouble("CryptRotNbTurns")' in read("source/rooms/RoomCrypt.cpp")
assert "double getHeartMaxHP() const;" in read("source/rooms/RoomDungeonTemple.h")
assert "mCapacityFactor" in read("source/rooms/HatcheryCycle.cpp")

# --- tooltips --------------------------------------------------------------------------------------------------------
texts = {"GoldPerTile": "Storage per tile", "SleepRecovery": "Sleep recovery", "LayInterval": "Egg laying time", "Capacity": "Capacity",
         "PointsPerWork": "Points per work", "XpPerHit": "Experience per hit", "WakefulnessPerDuty": "Tiredness per duty turn",
         "Fee": "Keeper fee", "Mood": "Mood gain", "LevelCap": "Level cap", "SkeletonLevel": "Skeleton level", "RotTime": "Rot time",
         "ClaimResistance": "Claim resistance", "ConversionSpeed": "Conversion speed", "PrayerMana": "Prayer mana",
         "CreatureLimit": "Creature limit", "Damage": "Damage", "Reload": "Reload time", "Duration": "Duration",
         "AuraRadius": "Alarm radius", "Radius": "Radius", "HP": "Health", "HeartHP": "Heart health",
         "HeartHeal": "Heart healing per second", "HeartMana": "Heart mana per second", "Price": "Price",
         "HealPerTurn": "Healing per turn", "Speed": "Speed", "Bonus": "Defense bonus", "Factor": "Factor",
         "Lifetime": "Duration", "ManaPerSecond": "Mana per second", "Gold": "Gold"}
assert set(texts) == effect_names, "the plan names a text for every effect"
for effect, text in texts.items():
    assert 'texts[ResearchEffect::%s] = "%s";' % (effect, text) in manager, effect
for sentence in ("More creatures in your dungeon.", "Your dungeon heart has more health.",
                 "Your dungeon heart heals faster.", "Your dungeon heart gives more mana."):
    assert '"%s"' % sentence in manager, sentence
description = manager[manager.index("std::string SkillManager::getResearchDescription("):manager.index("void SkillManager::buildRandomPendingSkillsForSeat(")]
assert 'getResearchEffectText(line.first) + ": " + value' in description, "every line prints <effect text>: <value at that level>"
assert "getResearchValue(type, level," in description, "the tooltip uses the same call as the game"
# every effect line has a base value for the tooltip
bases = manager[manager.index("static const ResearchBase RESEARCH_BASES[]"):manager.index("//! \\brief Reads the base value")]
for skill, effect, *_ in EXPECTED:
    assert '{SkillType::%s, "%s",' % (skill, effect) in bases, "%s %s has no base value for the tooltip" % (skill, effect)
print("research effect checks passed")
