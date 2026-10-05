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
if 'getAnimationState(it->mClip)->getLength()' not in update or "clipLength = 0.7" in update:
    problems.append("updateCollapses does not take the clip length from the skeleton")

# Every door type shows its wreck on a ghost copy: the barricade with Collapse, all others with Destroyed
start = ambience[ambience.index("void RoomAmbience::startCollapse"):ambience.index("void RoomAmbience::updateCollapses")]
if '(typeName == "DoorBarricade") ? "Collapse" : "Destroyed"' not in start:
    problems.append("startCollapse does not pick Collapse for the barricade and Destroyed for every other door")
if "entityPrefix" not in start or '"DoorBarricade_"' in start:
    problems.append("startCollapse still only finds barricade entities")
if "hasAnimationState(clipName)" not in start or "createEntity(name, entity->getMeshName()" not in start:
    problems.append("startCollapse does not check the clip on the ghost copy of the door mesh")
if "state = ghost->getAnimationState(clipName)" not in start or "collapse.mClip = clipName" not in start:
    problems.append("startCollapse does not play the picked clip on the ghost copy")
wrecked = ambience[ambience.index("case 3:", ambience.index("void RoomAmbience::notifyTrapEffect")):]
wrecked = wrecked[:wrecked.index("break;")]
if "startCollapse(tileX, tileY, typeName)" not in wrecked or 'typeName == "DoorBarricade"' in wrecked:
    problems.append("doorWrecked does not start the wreck for every door type")
if "std::string mClip;" not in read("source", "render", "RoomAmbience.h"):
    problems.append("Collapse does not remember its clip")

# The glint of a secret door is shown to its keeper only (it must not give the door away to the enemy)
config = read("config", "roomAmbienceTraps.cfg")
# (the lock glow and the opening and closing sounds too; the hit dust and the wrecking stay for everybody)
for secret_effect in ("SecretDoorGlint", "SecretDoorDust", "SecretDoorLockGlow", "DoorSecretOpenSound", "DoorSecretCloseSound"):
    found = re.search(r"Name\s+" + secret_effect + r"\s(.*?)\[/Effect\]", config, re.S)
    if found is None or not re.search(r"^\s*OwnerOnly\s+yes\s*$", found.group(1), re.M):
        problems.append("the effect " + secret_effect + " is not OwnerOnly")
for open_effect in ("DoorLockGlow", "DoorHitDust", "DoorSecretHitSound", "DoorSecretBreakSound", "SecretDoorRevealed"):
    found = re.search(r"Name\s+" + open_effect + r"\s(.*?)\[/Effect\]", config, re.S)
    if found is not None and re.search(r"^\s*OwnerOnly\s", found.group(1), re.M):
        problems.append("the effect " + open_effect + " must stay visible to everybody")
lock = re.search(r"Name\s+DoorLockGlow\s(.*?)\[/Effect\]", config, re.S)
if lock is None or "trap:DoorSecret" in lock.group(1) or "trap:DoorRuned" not in lock.group(1):
    problems.append("DoorLockGlow must keep the other doors and not the secret door")
split = re.search(r"Name\s+SecretDoorLockGlow\s(.*?)\[/Effect\]", config, re.S)
if split is None or "Match       trap:DoorSecret\n" not in split.group(1) or "When        Locked" not in split.group(1):
    problems.append("SecretDoorLockGlow is not the locked glow of the secret door")
ambience = read("source", "render", "RoomAmbience.cpp")
if "effect.mOwnerOnly" not in ambience or "entity->getSeat() != localPlayer->getSeat()" not in ambience:
    problems.append("scanObjects does not filter OwnerOnly effects by the seat")
if "const Seat* owner" not in ambience or "localPlayer->getSeat() != owner" not in ambience or "(owner == nullptr)" not in ambience:
    problems.append("triggerEvent does not filter OwnerOnly effects by the owner")
door_entity = read("source", "entities", "DoorEntity.cpp")
if door_entity.count("false, getSeat())") != 2:
    problems.append("the door open and close events do not pass the owner")
if "effect.mOwnerOnly" not in read("source", "render", "RoomAmbienceConfig.cpp"):
    problems.append("the config parser does not read OwnerOnly")

# The sold sounds
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
