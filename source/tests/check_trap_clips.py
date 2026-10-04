#!/usr/bin/env python3
"""Static check of the cannon recoil clip and the barricade collapse clip (no compiler needed).

    python source/tests/check_trap_clips.py

Checks that the cannon mesh is linked to its skeleton with the clip Triggered, that the shared door
skeleton has the new clip Collapse next to Open, Close and Destroyed, that the cannon plays its clip when
it fires, that the client lets a destroyed barricade collapse, and that the new files are in CREDITS.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts, binary=False):
    with open(os.path.join(ROOT, *parts), "rb" if binary else "r", **({} if binary else {"encoding": "utf-8"})) as handle:
        return handle.read()


problems = []
if b"Cannon.skeleton" not in read("models", "Cannon.mesh", binary=True):
    problems.append("Cannon.mesh has no link to Cannon.skeleton")
skeleton = read("models", "Cannon.skeleton", binary=True)
for name in (b"Triggered", b"Barrel", b"Root"):
    if name not in skeleton:
        problems.append("Cannon.skeleton lacks " + name.decode())
door = read("models", "WoodenDoor.skeleton", binary=True)
for name in (b"Open", b"Close", b"Destroyed", b"Collapse", b"RootBone", b"LeftDoorBone", b"RigthDoorBone"):
    if name not in door:
        problems.append("WoodenDoor.skeleton lacks " + name.decode())

cannon = read("source", "traps", "TrapCannon.cpp")
shoot = cannon[cannon.index("bool TrapCannon::shoot"):cannon.index("TrapEntity* TrapCannon::getTrapEntity")]
if 'setAnimationState("Triggered", false)' not in shoot:
    problems.append("the cannon does not play its clip when it fires")

ambience = read("source", "render", "RoomAmbience.cpp")
if 'startCollapse(tileX, tileY)' not in ambience or '"Collapse"' not in ambience or "updateCollapses(dt)" not in ambience:
    problems.append("the client does not let a destroyed barricade collapse")
if "destroyCollapse(collapse)" not in ambience[ambience.index("void RoomAmbience::stopAll"):ambience.index("void RoomAmbience::update(")]:
    problems.append("stopAll does not remove the collapsing barricades")

credits = read("CREDITS")
for name in ("models/Cannon.skeleton", "models/WoodenDoor.skeleton"):
    if name not in credits:
        problems.append(name + " is not in CREDITS")

if problems:
    for problem in problems:
        print("PROBLEM: " + problem)
    sys.exit(1)
print("fine")
