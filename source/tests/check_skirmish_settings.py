"""Static checks of the skirmish Game settings (layout, seat page code and the packet layout).

Run from any directory. It does not start a game.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
layout = ET.fromstring((root / "gui/MenuConfigureSeats.layout").read_text(encoding="utf-8"))
mode = (root / "source/modes/MenuModeConfigureSeats.cpp").read_text(encoding="utf-8")
server = (root / "source/network/ODServer.cpp").read_text(encoding="utf-8")
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


windows = {w.get("name"): w for w in layout.iter("Window")}


def area(name):
    value = windows[name].find("Property[@name='Area']").get("value")
    numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", value)]
    # {{sx,ox},{sy,oy},{sx,ox},{sy,oy}}
    return [(numbers[i], numbers[i + 1]) for i in range(0, 8, 2)]


# Every window the seat page code looks up exists in the layout
for constant in re.findall(r'const std::string (?:COMBOBOX|SPINNER)_\w+ = "(\w+)";', mode):
    if constant.startswith("ComboPlayer") or constant.startswith("ComboTeam"):
        continue
    check(constant in windows, "missing in layout: " + constant)
for name in ["GameSettingsWindow", "SettingsTabs", "General", "Creatures", "Rooms", "Spells", "Traps", "Doors",
             "CreaturesSP", "RoomsSP", "SpellsSP", "TrapsSP", "DoorsSP", "CloseSettingsButton",
             "GameSettingsButton", "BackButton", "LaunchGameButton"]:
    check(name in windows, "missing in layout: " + name)

# The three buttons of the seat page do not overlap (the drop-down lists of the settings are in their own window)
buttons = sorted((area(n)[0][1], area(n)[2][1], n) for n in ["BackButton", "GameSettingsButton", "LaunchGameButton"])
for first, second in zip(buttons, buttons[1:]):
    check(first[1] <= second[0], first[2] + " overlaps " + second[2])
check("ComboMaxCreatures" not in windows and "TextGoldDensity" in windows, "settings must be in the settings window")
check("Default (" not in mode, "the max creatures choices must be sorted, not a list that starts with Default")

# The order of the values in the packet is the same on the server and on the client
write_order = ["getGoldDensityPercent", "getManaRegenerationPercent", "getMaxCreaturesSetting", "getGameSpeedPercent",
               "getGameDurationMinutes", "getIsFOWActivated", "getHeartDestroyedReward", "getCreatureClassLimit",
               "SkirmishSkillStates"]
positions = [server.index(token, server.index("void ODServer::fireSeatConfigurationRefresh")) for token in write_order]
check(positions == sorted(positions), "ODServer::fireSeatConfigurationRefresh writes the settings in another order")
read_order = ["goldDensityPercent", "manaRegenerationPercent", "maxCreaturesSetting", "gameSpeedPercent",
              "gameDurationMinutes", "fogOfWar", "heartDestroyedReward", "nbCreatureLimits", "nbSkillStates"]
for source, start, label in [(server, "case ClientNotificationType::seatConfigurationRefresh", "server read"),
                             (mode, "void MenuModeConfigureSeats::refreshSeatConfiguration", "client read")]:
    base = source.index(start)
    reads = [source.index(">> " + token, base) for token in read_order]
    check(reads == sorted(reads), label + " reads the settings in another order")
send = mode[mode.index("void MenuModeConfigureSeats::fireSeatConfigurationToServer"):]
send_tokens = ["COMBOBOX_GOLD_DENSITY", "COMBOBOX_MANA_REGENERATION", "SPINNER_MAX_CREATURES", "SPINNER_GAME_SPEED",
               "SPINNER_GAME_DURATION", "COMBOBOX_FOG_OF_WAR", "COMBOBOX_HEART_DESTROYED", "nbCreatureLimits",
               "nbSkillStates"]
sends = [send.index(token) for token in send_tokens]
check(sends == sorted(sends), "the client sends the settings in another order")

# The new availability state is appended after the existing ones, the limit and speed bounds are the reference ones
header = (root / "source/gamemap/GameMap.h").read_text(encoding="utf-8")
states = re.search(r"enum class SkirmishItemState[^{]*\{([^}]*)\}", header).group(1)
names = [re.sub(r"//.*", "", n).strip() for n in states.split(",")]
names = [n for n in names if n]
check(names[:3] == ["notAvailable", "availableAtStart", "needsResearch"], "item state order changed")
check("SKIRMISH_CREATURE_LIMIT_NONE = 32" in header, "creature limit range is 0 to 32")
gamemap = (root / "source/gamemap/GameMap.cpp").read_text(encoding="utf-8")
check("std::max<uint32_t>(gameSpeedPercent, 25), 400" in gamemap, "game speed range is 25 to 400 percent")

# When the game time runs out every seat with a player loses (no winner), through the shared defeat path
duration = gamemap[gamemap.index("void GameMap::checkGameDuration"):]
duration = duration[:duration.index("\nvoid GameMap::")]
check('"Time is up!' in duration, "the time-out message is gone")
check("getPlayer()->notifyTimeUp()" in duration, "checkGameDuration does not defeat the seats")
check(duration.index("Time is up!") < duration.index("notifyTimeUp"), "the message must come before the defeat")
player = (root / "source/game/Player.cpp").read_text(encoding="utf-8")
time_up = player[player.index("void Player::notifyTimeUp"):]
time_up = time_up[:time_up.index("\nvoid Player::")]
check("if(mHasLost)" in time_up and "mHasLost = true" in time_up, "notifyTimeUp must lose only once")
check("notifyDefeat(true)" in time_up, "notifyTimeUp must use the shared defeat part")
check("mConquerorSeatId" not in time_up and "addMana" not in time_up, "notifyTimeUp must not touch the conqueror mana")
check("notifyDefeat(hasTeamLost)" in player, "the heart loss must use the shared defeat part")
# The unknown heart position (-1) is the default and the client defeat sequence handles it
check("mDefeatHeartTileX(-1)" in player and "mDefeatHeartTileY(-1)" in player, "heart tile default is not -1")
check("isHeartKnown()" in (root / "source/modes/GameMode.cpp").read_text(encoding="utf-8"),
      "the defeat sequence must handle an unknown heart")

# The destroyed heart reward of the skirmish setting: captions, specials around the heart, rooms and land
check('"Gain mana", 0' in mode and '"Gain mana and specials", 1' in mode and '"Gain mana, rooms and land", 2' in mode,
      "the heart reward captions are not the reference ones")
temple = (root / "source/rooms/RoomDungeonTemple.cpp").read_text(encoding="utf-8")
reward_code = temple[temple.index("void placeHeartRewardSpecials"):temple.index("class DungeonHeartObject")]
check("revealMapPermanently" not in reward_code and "addSkill" not in reward_code,
      "the reward must not reveal the map or give researched rooms")
check("HEART_REWARD_SPECIAL_DISTANCE = 2" in temple, "the specials lie 2 tiles from the heart centre")
offsets = re.search(r"offsetX\[4\] = \{([^}]*)\}.*?offsetY\[4\] = \{([^}]*)\}", reward_code, re.S)
check(offsets is not None and len(offsets.group(1).split(",")) == 4 and len(offsets.group(2).split(",")) == 4,
      "four special objects (north, east, south, west) are expected")
check("setSeat(winnerSeat)" in reward_code, "the specials belong to the winner")
check("if(reward == 1)" in reward_code and "else if(reward >= 2)" in reward_code,
      "specials only for value 1, rooms and land only for value 2")
check("candidate->getType() == RoomType::dungeonTemple" in reward_code, "the dungeon heart must stay with its owner")
check("claimForSeat(winnerSeat, tile," in reward_code, "rooms must change hands through the room's own claim")
check("getCoveringBuilding() != nullptr" in reward_code and "claimTile(winnerSeat)" in reward_code,
      "the remaining land of the loser must become the winner's")
check("loserSeat->getMana()" in reward_code and "addManaToSeat(-mana, loserSeat->getId())" in reward_code,
      "the winner takes all mana of the loser")
# The random pool holds only types the gift box code can apply
pool = re.search(r"HEART_REWARD_SPECIALS\[\] =\s*\{([^}]*)\}", temple).group(1)
bonus = (root / "source/giftboxes/GiftBoxBonus.cpp").read_text(encoding="utf-8")
for entry in re.findall(r"GiftBoxType::(\w+)", pool):
    check("case GiftBoxType::" + entry + ":" in bonus, "no gift box effect for the special " + entry)

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("skirmish settings checks passed")
