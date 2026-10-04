#!/usr/bin/env python3
"""Static check of the door skeletons, the look of the secret door and the sold sounds (no compiler needed).

    python source/tests/check_door_final.py

Checks that every door model links to its own skeleton with the right clips, that the closed secret door gets
a wall material for players who are not allied with its owner, that the barricade collapse takes the length of its
clip from the skeleton, and that the sold sounds exist, are used by the config and are in CREDITS.
"""

import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts, binary=False):
    with open(os.path.join(ROOT, *parts), "rb" if binary else "r", **({} if binary else {"encoding": "utf-8"})) as handle:
        return handle.read()


problems = []
credits = read("CREDITS")

DOORS = {
    "DoorIronbound": (b"Open", b"Close", b"Destroyed"),
    "DoorSteel": (b"Open", b"Close", b"Destroyed"),
    "DoorSecret": (b"Open", b"Close", b"Destroyed"),
    "DoorRune": (b"Open", b"Close", b"Destroyed"),
    "DoorBarricade": (b"Collapse", b"Destroyed"),
}
for name, clips in DOORS.items():
    mesh = read("models", name + ".mesh", binary=True)
    if (name + ".skeleton").encode() not in mesh:
        problems.append("%s.mesh does not link to its own skeleton" % name)
    if b"WoodenDoor.skeleton" in mesh:
        problems.append("%s.mesh still uses the shared wooden door skeleton" % name)
    skeleton_path = os.path.join(ROOT, "models", name + ".skeleton")
    if not os.path.exists(skeleton_path):
        problems.append("models/%s.skeleton is missing" % name)
        continue
    skeleton = read("models", name + ".skeleton", binary=True)
    for clip in clips:
        if clip not in skeleton:
            problems.append("%s.skeleton lacks the clip %s" % (name, clip.decode()))
    if "models/%s.skeleton" % name not in credits:
        problems.append("models/%s.skeleton is not in CREDITS" % name)
if "tools/blender-assets/door_skeletons.py" not in credits:
    problems.append("door_skeletons.py is not in CREDITS")
if b"Collapse" not in read("models", "WoodenDoor.skeleton", binary=True):
    problems.append("WoodenDoor.skeleton lost its clips")

# The look of the secret door
materials = read("materials", "scripts", "DoorTypes.material")
for material, texture in (("DoorSecretWall", "DirtWall.png"), ("DoorSecretWallClaimed", "DungeonClaimedWall0000.png")):
    if "material " + material + "\n" not in materials.replace("\r\n", "\n"):
        problems.append("material %s is missing" % material)
    if not os.path.exists(os.path.join(ROOT, "materials", "textures", texture)):
        problems.append("texture %s of %s is missing" % (texture, material))
render = read("source", "render", "RenderManager.cpp")
if "void RenderManager::rrUpdateSecretDoorLook(DoorEntity* door)" not in render:
    problems.append("RenderManager has no rrUpdateSecretDoorLook")
else:
    body = render[render.index("void RenderManager::rrUpdateSecretDoorLook"):]
    body = body[:body.index("\n}\n")]
    for text in ("isAlliedSeat", '"Close"', "DoorSecretWallClaimed", "DoorSecretWall", "isInEditorMode", "setMaterialOpacity"):
        if text not in body:
            problems.append("rrUpdateSecretDoorLook does not use " + text)
if 'meshName == "DoorSecret"' not in render or "rrUpdateSecretDoorLook(static_cast<DoorEntity*>" not in render:
    problems.append("a new secret door entity does not get its look")
if "rrUpdateSecretDoorLook(this)" not in read("source", "entities", "DoorEntity.cpp"):
    problems.append("the secret door does not change its look when it opens or closes")
if "rrUpdateSecretDoorLook" not in read("source", "render", "RenderManager.h"):
    problems.append("RenderManager.h does not declare rrUpdateSecretDoorLook")

# The collapse takes its length from the clip
ambience = read("source", "render", "RoomAmbience.cpp")
update = ambience[ambience.index("void RoomAmbience::updateCollapses"):ambience.index("void RoomAmbience::destroyCollapse")]
if 'getAnimationState("Collapse")->getLength()' not in update or "clipLength = 0.7" in update:
    problems.append("updateCollapses does not take the clip length from the skeleton")

# The sold sounds
config = read("config", "roomAmbienceTraps.cfg")
for family, names in (("Doors/Door/Sold", "DoorWooden"), ("Traps/Trap/Sold", "Spike")):
    block = re.search(r"\[Effect\]((?:(?!\[/Effect\]).)*?Family\s+%s\s(?:(?!\[/Effect\]).)*)\[/Effect\]" % re.escape(family), config, re.S)
    if block is None:
        problems.append("no effect with the family " + family)
        continue
    text = block.group(1)
    if "Event       TrapSold" not in text or "Kind        Sound" not in text or names not in text:
        problems.append("the effect of %s is not a sound for TrapSold of %s" % (family, names))
    ogg = "sounds/Spatial/%s/Fx%sSold01.ogg" % (family, family.split("/")[1])
    if not os.path.exists(os.path.join(ROOT, *ogg.split("/"))):
        problems.append("sound file %s is missing" % ogg)
    elif ogg not in credits:
        problems.append("sound file %s is not in CREDITS" % ogg)
    elif read(*ogg.split("/"), binary=True)[:4] != b"OggS":
        problems.append("%s is not an Ogg file" % ogg)
generator = read("tools", "gen_trap_door_sounds.py")
for text in ('("Door", "Sold", door_sold)', '("Trap", "Sold", trap_sold)'):
    if text not in generator:
        problems.append("the sound generator lacks " + text)

if problems:
    for problem in problems:
        print("PROBLEM: " + problem)
    sys.exit(1)
print("fine")
