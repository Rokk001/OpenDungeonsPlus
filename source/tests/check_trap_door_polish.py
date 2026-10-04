#!/usr/bin/env python3
"""Static check of the trap and door sounds, the lock glow and the build and sell effects (no compiler needed).

    python source/tests/check_trap_door_polish.py

Checks that every sound family of the config has a sound file, that every synthesized sound file is used by the
config and has a CREDITS line, that the config reader knows the new keys, and that the declarations in the
headers match the definitions in the sources.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


problems = []
config = read("config", "roomAmbienceTraps.cfg")
families = set(re.findall(r"^\s*Family\s+(\S+)", config, re.M))
for family in sorted(families):
    folder = os.path.join(ROOT, "sounds", "Spatial", *family.split("/"))
    if not glob.glob(os.path.join(folder, "*.ogg")):
        problems.append("no sound file for family %s" % family)

credits = read("CREDITS")
for kind in ("Traps", "Doors"):
    for path in sorted(glob.glob(os.path.join(ROOT, "sounds", "Spatial", kind, "*", "*", "Fx*.ogg"))):
        relative = os.path.relpath(path, ROOT).replace(os.sep, "/")
        family = "/".join(relative.split("/")[2:5])
        if family not in families:
            problems.append("sound %s is not used by the config" % relative)
        if relative not in credits:
            problems.append("sound %s has no CREDITS line" % relative)

# The cannon fires with a sound of the server, everything else has a Fire sound or is listed here
for name in ("Spike", "Boulder", "Alarm", "Fear", "Gas", "Lightning", "Fireburst", "Freeze", "Trigger"):
    for role in ("Fire", "Idle", "Reload"):
        if "Traps/%s/%s" % (name, role) not in families:
            problems.append("trap %s has no %s sound in the config" % (name, role))
for name in ("Wooden", "Ironbound", "Steel", "Secret", "Runed"):
    for role in ("Open", "Close", "Hit", "Break"):
        if "Doors/%s/%s" % (name, role) not in families:
            problems.append("door %s has no %s sound in the config" % (name, role))
for role in ("Hit", "Break"):
    if "Doors/Barricade/%s" % role not in families:
        problems.append("barricade has no %s sound in the config" % role)

reader = read("source", "render", "RoomAmbienceConfig.cpp")
for text in ('"Locked"', '"Sound"', '"Family"', '"Delay"'):
    if text not in reader:
        problems.append("the config reader does not know %s" % text)

ambience_h = read("source", "render", "RoomAmbience.h")
ambience = read("source", "render", "RoomAmbience.cpp")
for text in ("void playSound(", "void updatePendingSounds();", "mPendingSounds;", "mWreckedUntil;"):
    if text not in ambience_h:
        problems.append("RoomAmbience.h lacks %s" % text)
for text in ("void RoomAmbience::playSound(", "void RoomAmbience::updatePendingSounds()", "updatePendingSounds();",
             "AmbienceWhen::locked", "AmbienceKind::sound", '"TrapBuilt"', '"TrapSold"', "getAnimationStateName()"):
    if text not in ambience:
        problems.append("RoomAmbience.cpp lacks %s" % text)
if '#include "sound/SoundEffectsManager.h"' not in ambience:
    problems.append("RoomAmbience.cpp does not include the sound manager")

door_h = read("source", "entities", "DoorEntity.h")
door = read("source", "entities", "DoorEntity.cpp")
if "setAnimationState(const std::string& state" not in door_h or "using MovableGameEntity::setAnimationState;" not in door_h:
    problems.append("DoorEntity.h does not declare the setAnimationState override")
if "void DoorEntity::setAnimationState(" not in door or '"DoorOpen"' not in door or '"DoorClose"' not in door:
    problems.append("DoorEntity.cpp does not raise DoorOpen and DoorClose")
if "getAnimationStateName()" not in read("source", "entities", "MovableGameEntity.h"):
    problems.append("MovableGameEntity.h has no getAnimationStateName")

# Particle systems of the new effects exist
particles = read("particles", "RoomAmbienceTraps.particle")
for system in ("RoomAmbLockGlow", "RoomAmbRevealGlow"):
    if "particle_system %s" % system not in particles:
        problems.append("particle system %s is missing" % system)

# Own meshes of the door types: file, assignment in TrapDoor.cpp, materials and textures
trap_door = read("source", "traps", "TrapDoor.cpp")
material_text = read("materials", "scripts", "DoorTypes.material")
for mesh in ("DoorIronbound", "DoorSteel", "DoorBarricade", "DoorSecret", "DoorRune"):
    if not os.path.exists(os.path.join(ROOT, "models", mesh + ".mesh")):
        problems.append("models/%s.mesh is missing" % mesh)
    if ('std::string mesh%s = "%s"' % (mesh[4:], mesh)) not in trap_door:
        problems.append("TrapDoor.cpp does not use the mesh %s" % mesh)
for material in ("DoorIronboundWood", "DoorMetal", "DoorSteel", "DoorBarricade", "DoorSecret", "DoorRune", "DoorRuneGlow"):
    if "material %s" % material not in material_text:
        problems.append("material %s is not defined" % material)
    if "textures/%s.png" % material not in credits:
        problems.append("texture %s has no CREDITS line" % material)
for texture in re.findall(r"^\s*texture\s+(\S+)", material_text, re.M):
    if not os.path.exists(os.path.join(ROOT, "materials", "textures", texture)):
        problems.append("texture %s is missing" % texture)

if problems:
    for problem in problems:
        print("PROBLEM: " + problem)
    sys.exit(1)
print("fine")
