#!/usr/bin/env python3
"""Static check of the trap and door effect notification (no compiler needed).

    python source/tests/check_trap_effect_notification.py

Checks that the new server notification is inserted before timeLimit (which stays the last value, so
no existing value changes), that the packet fields are written and read in the same order, that the
trap effect kinds only grew at the end, and that every event the client raises has a handler in the
config and every event of the config is raised.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


problems = []
header = read("source", "network", "ServerNotification.h")
body = header[header.index("enum class ServerNotificationType"):]
body = body[:body.index("};")]
names = re.findall(r"^\s*([A-Za-z_]\w*)\s*,?\s*(?://.*)?$", body, re.M)
if names[-1] != "timeLimit":
    problems.append("timeLimit is not the last server notification")
if "trapEffect" not in names or names.index("trapEffect") != len(names) - 2:
    problems.append("trapEffect must be right before timeLimit")
if names[-3] != "relationshipTier":
    problems.append("trapEffect must follow relationshipTier")

if '"trapEffect"' not in read("source", "network", "ServerNotification.cpp"):
    problems.append("trapEffect has no name in ServerNotification.cpp")

trap_h = read("source", "traps", "Trap.h")
kinds = re.search(r"enum class TrapEffectKind[^{]*\{(.*?)\}", trap_h, re.S)
values = re.findall(r"(\w+)\s*=\s*(\d+)", kinds.group(1)) if kinds else []
if [name for name, _ in values] != ["fired", "linked", "doorHit", "doorWrecked"] or \
        [int(number) for _, number in values] != [0, 1, 2, 3]:
    problems.append("TrapEffectKind values changed: %s" % values)

trap_cpp = read("source", "traps", "Trap.cpp")
client = read("source", "network", "ODClient.cpp")
send = trap_cpp[trap_cpp.index("void Trap::fireTrapEffect"):]
send = send[:send.index("bool Trap::forceTrigger")]
if "static_cast<int32_t>(kind) << tile->getX() << tile->getY()" not in send or \
        "<< typeName << static_cast<float>(fraction)" not in send:
    problems.append("server packet order is not kind, x, y, type name, fraction")
handler = client[client.index("case ServerNotificationType::trapEffect:"):]
handler = handler[:handler.index("break;")]
if "packetReceived >> effectKind >> tileX >> tileY >> typeName >> fraction" not in handler:
    problems.append("client reads the packet in another order")

ambience = read("source", "render", "RoomAmbience.cpp")
door_entity = read("source", "entities", "DoorEntity.cpp")
raised = set(re.findall(r'triggerEvent\("((?:Trap|Door)\w+)"', ambience + door_entity))
# Events the scan of the entities raises (built, sold)
raised |= set(re.findall(r'mEvent = "(Trap\w+)"', ambience))
config = read("config", "roomAmbienceTraps.cfg")
configured = set(re.findall(r"^\s*Event\s+((?:Trap|Door)\w+)", config, re.M))
if raised != configured:
    problems.append("events raised %s, events configured %s" % (sorted(raised), sorted(configured)))

door = read("source", "traps", "TrapDoor.cpp")
if "TrapEffectKind::doorWrecked" not in door or "TrapEffectKind::doorHit" not in door:
    problems.append("doors do not send hit and wrecked effects")
if "TrapEffectKind::linked" not in read("source", "traps", "TrapTrigger.cpp"):
    problems.append("the trigger trap does not send the linked effect")

if problems:
    for problem in problems:
        print("PROBLEM: " + problem)
    sys.exit(1)
print("fine")
