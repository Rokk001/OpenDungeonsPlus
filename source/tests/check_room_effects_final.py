#!/usr/bin/env python3
"""Static check of the heart, casino and arena effects (no compiler needed).

    python source/tests/check_room_effects_final.py

Checks the low health flare of the dungeon heart (condition, wiring, thresholds that get stronger), the casino
win and loss effects (events raised by the client, handled in the config, sounds with CREDITS entries), and the
cheering of the arena (spectator scan, config values, event and sound). No network value may have changed.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
problems = []


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as handle:
        return handle.read()


def need(condition, text):
    if not condition:
        problems.append(text)


def effects(path):
    """Returns the [Effect] blocks of a room ambience file as dictionaries of key -> words."""
    result = []
    current = None
    for raw in read(*path).splitlines():
        words = raw.split("#", 1)[0].split()
        if not words:
            continue
        if words[0] == "[Effect]":
            current = {}
        elif words[0] == "[/Effect]":
            result.append(current)
            current = None
        elif current is not None and len(words) > 1:
            current[words[0]] = words[1:]
    return result


ambience_cpp = read("source", "render", "RoomAmbience.cpp")
ambience_h = read("source", "render", "RoomAmbience.h")
config_h = read("source", "render", "RoomAmbienceConfig.h")
config_cpp = read("source", "render", "RoomAmbienceConfig.cpp")
reactions_cpp = read("source", "render", "CreatureReactions.cpp")
credits = read("CREDITS")
fx = effects(("config", "roomAmbienceRoomFx.cfg"))

# --- heart: low health
need("lowHealth" in config_h and "mBelow" in config_h, "AmbienceWhen::lowHealth or mBelow missing")
need('text == "LowHealth"' in config_cpp and 'key == "Below"' in config_cpp, "LowHealth / Below is not read by the config")
need("AmbienceWhen::lowHealth" in ambience_cpp and "isLocalHeartBelow" in ambience_cpp,
     "the scan does not use the low health condition")
need("getHeartBadge()" in ambience_cpp and "mFraction" in ambience_cpp, "the heart health is not read from the heart badge")
need("getSeat() != localPlayer->getSeat()" in ambience_cpp, "only the heart of the local keeper may use the badge")
heart = [e for e in fx if e.get("When") == ["LowHealth"]]
need(len(heart) >= 4, "too few low health heart effects")
for e in heart:
    need(e.get("Match") == ["DungeonTempleObject"], "%s: low health effect not on the heart" % e["Name"][0])
limits = sorted(set(float(e["Below"][0]) for e in heart))
need(len(limits) >= 3, "the low health flare needs at least three levels")
need(all(0.0 < v < 0.5 for v in limits), "low health levels must be below half health")
particles = [e for e in heart if e.get("Kind") == ["Particle"]]
need(len(set(e["System"][0] for e in particles)) == len(particles), "every flare level needs its own particle system")
pulses = sorted((float(e["Below"][0]), float(e["Amount"][0])) for e in heart if e.get("Kind") == ["Motion"])
need(len(pulses) >= 2 and pulses[0][1] > pulses[-1][1], "the pulse must be stronger at lower health")
need(any(e.get("Reduced") == ["yes"] for e in heart), "no low health effect in the mode reduced")
# the old effect of the heart stays
core = effects(("config", "roomAmbienceCoreObjects.cfg"))
need(any(e["Name"] == ["HeartFlare"] and e.get("When") == ["Occupied"] for e in core), "HeartFlare must stay as it was")

# --- casino
# The server tells the result (a small cosmetic event); the clients show the win and the loss only on it
client_cpp = read("source", "network", "ODClient.cpp")
casino_cpp = read("source", "rooms", "RoomCasino.cpp")
event_h = read("source", "network", "CosmeticEvent.h")
need("casinoResult = 15" in event_h, "the casino result is not a cosmetic event")
need("sendGameResult(*p.second.mCreature1.mCreature, *p.second.mCreature2.mCreature)" in casino_cpp and
     "sendGameResult(*p.second.mCreature2.mCreature, *p.second.mCreature1.mCreature)" in casino_cpp,
     "the casino does not send the result for both winners")
send = casino_cpp[casino_cpp.index("void RoomCasino::sendGameResult"):]
need("CosmeticEventType::casinoResult" in send and "sendCosmeticEvent" in send and "getSeatsWithVision()" in send,
     "the result is not sent to the keepers who see the winner")
need('event.is(CosmeticEventType::casinoResult)' in client_cpp and '"CasinoWin"' in client_cpp and '"CasinoLoss"' in client_cpp,
     "the client does not raise CasinoWin / CasinoLoss on the cosmetic event")
need('"CasinoWin"' not in ambience_cpp and '"CasinoLoss"' not in ambience_cpp and "CASINO_OPPONENT_RADIUS" not in ambience_cpp,
     "the casino is still detected by an animation")
need("mAttacking" not in ambience_h and "attack_anim" not in ambience_cpp, "the attack animation is still read for the casino")
for event in ("CasinoWin", "CasinoLoss"):
    mine = [e for e in fx if e.get("Event") == [event]]
    need(any(e.get("Kind") == ["Particle"] for e in mine), "%s has no particle effect" % event)
    need(any(e.get("Kind") == ["Sound"] for e in mine), "%s has no sound" % event)
    need(all(e.get("Match") == ["casinoRoom"] for e in mine), "%s must be limited to the casino" % event)
need(any(e.get("Event") == ["CasinoLoss"] and e.get("System") == ["RoomAmbCasinoLossSmoke"] for e in fx),
     "the loss needs the grey smoke")
need(any(e.get("Event") == ["CasinoWin"] and e.get("System") == ["RoomAmbCasinoWinCoins"] for e in fx),
     "the win needs the coin fountain")

# --- arena
need("scanArenaSpectators" in reactions_cpp and '"ArenaSpectator"' in reactions_cpp and '"ArenaCheer"' in reactions_cpp,
     "the arena spectator scan is not wired")
need('"PitSpectatorRadius"' in reactions_cpp, "the spectator distance must be the one of the server (PitSpectatorRadius)")
need("nbFighting < 2" in reactions_cpp, "cheering needs a bout of at least two fighters")
config_cpp_text = read("source", "render", "CreatureReactionConfig.cpp")
need("ArenaSpectatorInterval" in config_cpp_text, "ArenaSpectatorInterval is not read")
need("ArenaCheerPause" in config_cpp_text, "ArenaCheerPause is not read")
reactions_cfg = read("config", "creatureReactions.cfg")
need(re.search(r"^\s*ArenaSpectatorInterval\s+\S+", reactions_cfg, re.M) is not None, "ArenaSpectatorInterval not in config")
need(re.search(r"^\s*ArenaCheerPause\s+\S+", reactions_cfg, re.M) is not None, "ArenaCheerPause not in config")
need(re.search(r"Name\s+ArenaSpectator\b", reactions_cfg) is not None, "no ArenaSpectator event in the reactions config")
cheer = [e for e in fx if e.get("Event") == ["ArenaCheer"]]
need(any(e.get("Kind") == ["Particle"] for e in cheer), "ArenaCheer has no particles")
need(any(e.get("Kind") == ["Sound"] for e in cheer), "ArenaCheer has no sound")

# --- sounds and credits
families = set(e["Family"][0] for e in fx if e.get("Kind") == ["Sound"])
need(families == {"Rooms/Casino/Win", "Rooms/Casino/Loss", "Rooms/Arena/Cheer"}, "unexpected sound families %s" % families)
for family in families:
    folder = os.path.join(ROOT, "sounds", "Spatial", *family.split("/"))
    oggs = [f for f in os.listdir(folder) if f.endswith(".ogg")] if os.path.isdir(folder) else []
    need(len(oggs) >= 1, "no sound in %s" % family)
    for ogg in oggs:
        need(os.path.getsize(os.path.join(folder, ogg)) > 1000, "%s is nearly empty" % ogg)
        need("sounds/Spatial/%s/%s" % (family, ogg) in credits, "no CREDITS entry for %s/%s" % (family, ogg))
need("tools/gen_room_effect_sounds.py" in credits, "no CREDITS entry for the sound script")
need(re.search(r"^tools/gen_room_effect_sounds\.py\s+OD Team", credits, re.M) is not None, "script entry without author")

# --- no network change
notif = read("source", "network", "ServerNotification.h")
body = notif[notif.index("enum class ServerNotificationType"):]
body = body[:body.index("};")]
names = re.findall(r"^\s*([A-Za-z_]\w*)\s*,?\s*(?://.*)?$", body, re.M)
need(names[-1] == "timeLimit", "timeLimit must stay the last server notification")
need("casinoPayout" in names, "casinoPayout must stay")

if problems:
    for problem in problems:
        print("PROBLEM:", problem)
    sys.exit(1)
print("fine")
