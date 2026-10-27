#!/usr/bin/env python3
"""Static check that durations, reloads, radii and the portal cooldown keep their fractions (no compiler needed).

    python source/tests/check_decimal_config_parsing.py

Checks that no integer getter is left for the spell durations, the trap reload turns and radii, the portal
cooldown and the lightning stun of the spells, and that the counters that use them are doubles.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


problems = []

# Keys whose value may have decimals: no UInt32/Int32 getter may read them any more
KEYS = {
    "spells": ["CreatureDefenseDuration", "CreatureHasteDuration", "CreatureSlowDuration", "CreatureStrengthDuration",
               "CreatureWeakDuration", "CreatureExplosionDuration", "CreatureHealDuration", "CallToWarNbTurnsMax",
               "EyeEvilNbTurns", "InfernoRadiusTiles", "InfernoNbTurns", "TremorRadiusTiles", "TremorNbTurns",
               "LightningStunTurns"],
    "traps": ["BoulderReloadTurns", "CannonReloadTurns", "RunedDoorReloadTurns", "FearReloadTurns", "FearRadius",
              "FireburstReloadTurns", "FireburstRadius", "FreezeReloadTurns", "GasReloadTurns", "GasRadius",
              "LightningReloadTurns", "SpikeReloadTurns", "TriggerReloadTurns", "AlarmRadius"],
    "room": ["PortalCooldownSpawnMin", "PortalCooldownSpawnMax"],
}
GETTER = re.compile(r'get(Spell|Trap|Room)Config(UInt32|Int32)\(\s*"(\w+)"')
SOURCES = []
for folder in ("spells", "traps", "rooms"):
    base = os.path.join(ROOT, "source", folder)
    for name in sorted(os.listdir(base)):
        if name.endswith(".cpp"):
            SOURCES.append(os.path.join("source", folder, name))
KIND = {"Spell": "spells", "Trap": "traps", "Room": "room"}
for path in SOURCES:
    for match in GETTER.finditer(read(path)):
        if match.group(3) in KEYS[KIND[match.group(1)]]:
            problems.append(path + " still reads " + match.group(3) + " with an integer getter")

portal = read("source", "rooms", "RoomPortal.cpp")
if "getRoomConfigUInt32(key)" in portal or "Random::Uint(getResearchedCooldown" in portal:
    problems.append("the portal cooldown is still rounded to whole turns")
if "static double getResearchedCooldown" not in portal:
    problems.append("getResearchedCooldown must return a double")
if "double mSpawnCreatureCountdown;" not in read("source", "rooms", "RoomPortal.h"):
    problems.append("the portal spawn countdown must be a double")

# The counters that hold the values keep the fraction
for path, token in (("source/spells/Spell.h", "double mNbTurns;"), ("source/spells/SpellEyeEvil.h", "double mFreeTurns;"),
                    ("source/traps/TrapDoor.h", "double mFireCooldownTurns;"), ("source/traps/TrapFear.h", "double mRadius;"),
                    ("source/traps/TrapGas.h", "double mRadius;"), ("source/traps/TrapFireburst.h", "double mRadius;")):
    if token not in read(*path.split("/")):
        problems.append(path + " must hold " + token)

# The lightning spell stun is the config value, not the target's own value
lightning = read("source", "spells", "SpellLightning.cpp")
if "getSpellConfigDouble(\"LightningStunTurns\")" not in lightning or "getTurnsStunDropped" in lightning:
    problems.append("SpellLightning must stun for LightningStunTurns")

# Portal and trap values really carry decimals in the shipped config
rooms = read("config", "rooms.cfg")
for key in KEYS["room"]:
    if not re.search(r"^\s+" + key + r"\s+\d+\.\d+\s*$", rooms, re.M):
        problems.append("rooms.cfg " + key + " must carry its decimals")

if problems:
    print("\n".join("FAIL: " + p for p in problems))
    sys.exit(1)
print("OK: durations, reloads, radii and the portal cooldown keep their fractions")
