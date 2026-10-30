#!/usr/bin/env python3
"""Static check that the code fallbacks equal the shipped config values (no compiler needed).

    python source/tests/check_config_fallbacks.py

Checks the ConfigManager constructor defaults, the room config fallbacks of the arena, the hatchery and the
chicken gift, and the hatchery cycle defaults against the shipped config files, and that the new mana and gift box
keys exist with the shipped value as their default.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def cfg_value(text, key):
    match = re.search(r"^\s+" + re.escape(key) + r"\s+(\S+)\s*$", text, re.M)
    return float(match.group(1)) if match else None


problems = []
global_cfg = read("config", "global.cfg")
rooms_cfg = read("config", "rooms.cfg")
manager = read("source", "utils", "ConfigManager.cpp")

# ConfigManager constructor defaults: member -> global.cfg key
DEFAULTS = {
    "mCreatureDeathCounter": "CreatureDeathCounter", "mCreatureBaseMood": "CreatureBaseMood",
    "mSlapEffectDuration": "SlapEffectDuration", "mTimePayDay": "TimePayDay",
    "mClaimingWallPenalty": "ClaimingWallPenalty", "mDigCoefClaimedWall": "DigCoefClaimedWall",
    "mNbTurnsKoCreatureAttacked": "NbTurnsKoCreatureAttacked", "mCorpseLieSeconds": "CorpseLieSeconds",
    "mCorpseDecaySeconds": "CorpseDecaySeconds", "mManaIncomeTilesCap": "ManaIncomeTilesCap",
    "mManaPerClaimedTilePerSecond": "ManaPerClaimedTilePerSecond", "mWorkerManaUpkeepPerSecond": "WorkerManaUpkeepPerSecond",
    "mWorkerManaShortageSeconds": "WorkerManaShortageSeconds", "mWorkerPopCountdownSeconds": "WorkerPopCountdownSeconds",
    "mAutoWorkerIntervalSeconds": "AutoWorkerIntervalSeconds", "mGiftBoxMana": "GiftBoxMana", "mGiftBoxGold": "GiftBoxGold",
    "mGiftBoxLevels": "GiftBoxLevels", "mGiftBoxWorkers": "GiftBoxWorkers", "mGiftBoxStunSeconds": "GiftBoxStunSeconds",
    "mGhostAiGoldPerResearchPoint": "GhostAiGoldPerResearchPoint", "mGhostAiGoldPerXp": "GhostAiGoldPerXp",
    "mSoulCrystalNormalXpPerSecond": "SoulCrystalNormalXpPerSecond", "mCreatureMoodUpset": "CreatureMoodUpset",
    "mCreatureMoodAngry": "CreatureMoodAngry", "mCreatureMoodFurious": "CreatureMoodFurious",
    "mNbTurnsFuriousMax": "NbTurnsFuriousMax",
}
for member, key in DEFAULTS.items():
    shipped = cfg_value(global_cfg, key)
    match = re.search(r"^\s+" + member + r"\(([-0-9.]+)\)", manager, re.M)
    if shipped is None:
        problems.append("global.cfg has no " + key)
    elif match is None:
        problems.append("ConfigManager has no default for " + member)
    elif abs(float(match.group(1)) - shipped) > 1e-9:
        problems.append(member + " defaults to " + match.group(1) + ", global.cfg " + key + " is " + str(shipped))

well = re.search(r"DEFAULT_MANA_WELL_BONUS_PER_TILE = ([-0-9.]+);", manager)
if well is None or abs(float(well.group(1)) - cfg_value(global_cfg, "ManaWellBonusPerTile")) > 1e-9:
    problems.append("the mana well default must equal global.cfg ManaWellBonusPerTile")

# getRoomConfigDoubleOrDefault fallbacks: file -> keys
for path, keys in (("source/entities/Creature.cpp", ["ArenaDirtPerHit", "CasinoMoodMax"]),
                   ("source/rooms/RoomArena.cpp", ["PitMoodSolitary", "PitMoodSpectator", "PitMoodVictor"]),
                   ("source/rooms/RoomHatchery.cpp", ["HatcheryDirtPerHenTurn"]),
                   ("source/creatureaction/CreatureActionEatChicken.cpp", ["HatcheryGiftHpRecoveredPerChicken"])):
    text = read(*path.split("/"))
    for key in keys:
        match = re.search(r'getRoomConfigDoubleOrDefault\("' + key + r'",\s*([-0-9.]+)\)', text)
        shipped = cfg_value(rooms_cfg, key)
        if match is None:
            problems.append(path + " has no fallback for " + key)
        elif abs(float(match.group(1)) - shipped) > 1e-9:
            problems.append(path + " falls back to " + match.group(1) + " for " + key + ", rooms.cfg has " + str(shipped))

for path, constant, key, cfg in (
    ("source/entities/Creature.cpp", "DEFAULT_PIT_MOOD_MAX", "PitMoodMax", rooms_cfg),
    ("source/rooms/Room.cpp", "DEFAULT_ROOM_CONVERT_NEUTRAL_SECONDS_PER_TILE", "RoomConvertNeutralSecondsPerTile", rooms_cfg),
    ("source/rooms/Room.cpp", "DEFAULT_ROOM_CONVERT_SECONDS_PER_TILE", "RoomConvertSecondsPerTile", rooms_cfg),
    ("source/rooms/RoomPortal.cpp", "DEFAULT_PORTAL_FIRST_SPAWN_SECONDS", "PortalFirstSpawnSeconds", rooms_cfg),
    ("source/creatureaction/CreatureActionReloadTrap.cpp", "DEFAULT_RELOAD_EXPERIENCE", "TrapReloadExperience", read("config", "traps.cfg")),
):
    match = re.search(r'\b' + constant + r'\s*=\s*([-0-9.]+)', read(*path.split('/')))
    shipped = cfg_value(cfg, key)
    if match is None or shipped is None or abs(float(match.group(1)) - shipped) > 1e-9:
        problems.append(path + " default " + constant + " must equal " + key)

cycle = read("source", "rooms", "HatcheryCycle.h")
for member, key in (("mLayMax", "HatcheryLayMax"), ("mLayFactor", "HatcheryLayFactor")):
    match = re.search(member + r"\(([-0-9.]+)\)", cycle)
    shipped = cfg_value(rooms_cfg, key)
    if match is None or abs(float(match.group(1)) - shipped) > 1e-9:
        problems.append("HatcheryCycle.h default " + member + " must equal rooms.cfg " + key)

# A missing room key is logged
if "Missing room parameter" not in manager:
    problems.append("getRoomConfigDoubleOrDefault must log a missing key")

if problems:
    print("\n".join("FAIL: " + p for p in problems))
    sys.exit(1)
print("OK: every fallback equals the shipped config value")
