#!/usr/bin/env python3
"""Static check of the last room, trap, door and spell effects (no compiler needed).

    python source/tests/check_effects_gaps.py

Checks that the events HeartHit, CryptRaised, PrisonerArrived, TortureConverted, BannerAlert and SpellFxHandCast are
raised by the client from what it already knows (no new network value), that the declarations in RoomAmbience.h match
the definitions, that every effect of config/roomAmbienceFixEffects.cfg exists with the right event, match and kind,
that its particle systems and sounds exist and have CREDITS entries, and that the watch banner still never fires.
"""

import glob
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
    """Returns the [Effect] blocks of a room ambience file as a dictionary name -> {key: words}."""
    result = {}
    current = None
    for raw in read(*path).splitlines():
        words = raw.split("#", 1)[0].split()
        if not words:
            continue
        if words[0] == "[Effect]":
            current = {}
        elif words[0] == "[/Effect]":
            result[current["Name"][0]] = current
            current = None
        elif current is not None and len(words) > 1:
            current[words[0]] = words[1:]
    return result


header = read("source", "render", "RoomAmbience.h")
source = read("source", "render", "RoomAmbience.cpp")
client = read("source", "network", "ODClient.cpp")
render_h = read("source", "render", "RenderManager.h")
render_cpp = read("source", "render", "RenderManager.cpp")
banner = read("source", "traps", "TrapWatchBanner.cpp")
banner_h = read("source", "traps", "TrapWatchBanner.h")
notification = read("source", "network", "ServerNotification.h")
credits = read("CREDITS")
main_cfg = read("config", "roomAmbience.cfg")
fx = effects(("config", "roomAmbienceFixEffects.cfg"))
systems = {}
for path in glob.glob(os.path.join(ROOT, "particles", "*.particle")):
    for match in re.finditer(r"particle_system\s+(\S+)", open(path, encoding="utf-8").read()):
        systems[match.group(1)] = os.path.basename(path)

need("Include roomAmbienceFixEffects.cfg" in main_cfg, "roomAmbienceFixEffects.cfg is not included")

# --- code: declared and defined, wired into the scan
for decl in ("scanHeartHit", "scanBannerAlerts", "noteHandCast"):
    need(re.search(r"\b%s\(" % decl, header), "%s not declared" % decl)
    need("RoomAmbience::%s(" % decl in source, "%s not defined" % decl)
need(source.index("scanHeartHit();") < source.index("scanObjects(camera, cameraPosition);"),
     "scanHeartHit must run before scanObjects (the hit pulse starts in the same scan)")
need("scanBannerAlerts();" in source, "scanBannerAlerts is not called")

# --- heart: hit found from the badge of the local keeper, never from the network
heart = source[source.index("void RoomAmbience::scanHeartHit"):source.index("void RoomAmbience::scanBannerAlerts")]
need("getHeartBadge().mHP" in heart and "mLastHeartHP" in heart, "the hit must come from the health of the heart badge")
need("getSeat() != localPlayer->getSeat()" in heart, "only the heart of the local keeper may be hit")
need('"HeartHit"' in heart and "mHitUntil" in heart, "HeartHit and the state for When Hit must be set together")
need("mLastHeartHP = -1.0;" in source, "mLastHeartHP must be reset by stopAll")

# --- creatures: crypt, prison, torture chamber
need('"CryptRaised"' in source and "TileVisual::cryptRoom" in source, "CryptRaised is not raised on a crypt tile")
need("arrivalTile->getSeat() == creature->getSeat()" in source, "a raised creature must belong to the crypt's keeper")
need('"PrisonerArrived"' in source and "isInContainment()" in source, "PrisonerArrived is not found from the jail state")
need('visual == "prisonRoom"' in source, "PrisonerArrived must be limited to the prison")
need('"TortureConverted"' in source and "snapshot.mSeat != creatureSeat" in source, "TortureConverted is not found from a seat change")
need('visual == "tortureRoom"' in source, "TortureConverted must be limited to the torture chamber")
need("mPrisoner" in header and "mSeat" in header, "the creature snapshot must remember the jail state and the seat")

# --- banner: the same test as the server, a flag mesh with its Loop clip, never a reload look
alert = source[source.index("void RoomAmbience::scanBannerAlerts"):source.index("void RoomAmbience::noteHandCast")]
need("WatchBannerAuraTiles" in alert and "GuardRoomDistressSeconds" in alert, "the banner alert must use the aura and the distress time")
need("isAlliedSeat" in alert and "mBannerAlertUntil" in alert, "the banner alert needs the ally test and a cooldown")
need('"WarBanner"' in banner and os.path.exists(os.path.join(ROOT, "models", "WarBanner.mesh")),
     "the watch banner must use the flag mesh")
need("virtual bool shoot(Tile* tile) override\n    { return false; }" in banner_h.replace("\r\n", "\n"), "the watch banner must still never fire")
need(not re.search(r"WatchBanner\s+When\s+Reloading", read("config", "roomAmbienceTraps.cfg") + read("config", "roomAmbienceFixEffects.cfg")),
     "no reload look for the watch banner")
skeleton = open(os.path.join(ROOT, "models", "WarBanner.skeleton"), "rb").read()
need(b"Loop" in skeleton, "WarBanner.skeleton has no clip Loop")

# --- hand: sent with the local cast, no network value
need("ClientNotificationType::askCastSpell" in client and "noteHandCast" in client, "the hand cast is not hooked to the cast")
need("getKeeperHandPosition" in render_h and "getKeeperHandPosition" in render_cpp, "RenderManager::getKeeperHandPosition missing")

# --- no new network value: the last value stays timeLimit
need("timeLimit" in notification, "ServerNotificationType::timeLimit missing")
need(not re.search(r"HeartHit|CryptRaised|PrisonerArrived|TortureConverted|BannerAlert|HandCast", notification),
     "a new network value was added for an effect that is found on the client")

# --- effects
EXPECTED = (
    # name, Target, Event or Object match, Kind
    ("HeartHitBurst", "Event", "HeartHit", "Particle"),
    ("HeartHitFlash", "Event", "HeartHit", "Particle"),
    ("HeartHitSound", "Event", "HeartHit", "Sound"),
    ("WaveSurgeLight", "Event", "CreatureArrived", "Particle"),
    ("WaveSurgeShockwave", "Event", "CreatureArrived", "Particle"),
    ("WaveSurgeShake", "Event", "CreatureArrived", "Shake"),
    ("WaveSurgeSound", "Event", "CreatureArrived", "Sound"),
    ("CryptRaiseEarth", "Event", "CryptRaised", "Particle"),
    ("CryptRaiseClods", "Event", "CryptRaised", "Particle"),
    ("CryptRaiseSpirit", "Event", "CryptRaised", "Particle"),
    ("CryptRaiseSound", "Event", "CryptRaised", "Sound"),
    ("PrisonerDoorDust", "Event", "PrisonerArrived", "Particle"),
    ("PrisonerDoorSparks", "Event", "PrisonerArrived", "Particle"),
    ("PrisonerDoorClang", "Event", "PrisonerArrived", "Sound"),
    ("TortureConvertFlash", "Event", "TortureConverted", "Particle"),
    ("TortureConvertShackles", "Event", "TortureConverted", "Particle"),
    ("TortureConvertSound", "Event", "TortureConverted", "Sound"),
    ("CannonMuzzleFlash", "Event", "TrapFired", "Particle"),
    ("CannonSmokeRing", "Event", "TrapFired", "Particle"),
    ("SpikeShootDust", "Event", "TrapFired", "Particle"),
    ("LightningTrapBolt", "Event", "TrapFired", "Beam"),
    ("WatchBannerFlare", "Event", "BannerAlert", "Particle"),
    ("WatchBannerAlertSound", "Event", "BannerAlert", "Sound"),
    ("RuneDoorCracks", "Event", "DoorHurt", "Particle"),
    ("RuneDoorFlickerRunes", "Event", "DoorHurt", "Particle"),
    ("SteelDoorHitDust", "Event", "DoorHit", "Particle"),
    ("SecretDoorOpenGlow", "Event", "DoorOpen", "Particle"),
    ("SpellHandCastSpark", "Event", "SpellFxHandCast", "Particle"),
    ("HeartHitPulse", "Object", "DungeonTempleObject", "Motion"),
    ("WaveRumbleDust", "Tile", "portalWaveRoom", "Particle"),
    ("WatchBannerWave", "Object", "trap:WatchBanner", "Clip"),
    ("RuneDoorFlicker", "Object", "trap:DoorRuned", "Motion"),
    ("SteelDoorDent", "Object", "trap:DoorSteel", "Motion"),
)
for name, target, wanted, kind in EXPECTED:
    e = fx.get(name)
    if e is None:
        problems.append("effect %s missing" % name)
        continue
    need(e.get("Target") == [target], "%s: Target must be %s" % (name, target))
    need(e.get("Kind") == [kind], "%s: Kind must be %s" % (name, kind))
    if target == "Event":
        need(e.get("Event") == [wanted], "%s: Event must be %s" % (name, wanted))
    else:
        need(wanted in e.get("Match", []), "%s: must match %s" % (name, wanted))

need(fx["HeartHitPulse"].get("When") == ["Hit"], "the heart pulse must run When Hit")
need(fx["RuneDoorFlicker"].get("Motion") == ["Flicker"], "the rune door must flicker")
need(fx["SteelDoorDent"].get("When") == ["Hit"], "the dent must run When Hit")
need(fx["WatchBannerWave"].get("Clips") == ["Loop"], "the banner plays the clip Loop")
need(fx["LightningTrapBolt"].get("Mesh") == ["SpellBolt"], "the lightning trap bolt uses the bolt mesh")
need(fx["CannonMuzzleFlash"].get("Match") == ["Cannon"] and fx["CannonSmokeRing"].get("Match") == ["Cannon"],
     "the muzzle effects belong to the cannon")
need(fx["SpikeShootDust"].get("System") == ["RoomAmbHitDust"], "the spike dust is RoomAmbHitDust")
need(fx["RuneDoorCracks"].get("Match") == ["DoorRuned"], "the cracks belong to the rune door")
need(fx["SecretDoorOpenGlow"].get("System") == ["RoomAmbRevealGlow"], "the secret door opens with the reveal glow")
for name in ("WaveSurgeLight", "WaveSurgeShockwave", "WaveSurgeShake", "WaveSurgeSound"):
    need(fx[name].get("Match") == ["portalWaveRoom"], "%s must be limited to the wave portal" % name)
need(any(e.get("Reduced") == ["yes"] for e in fx.values()), "no effect in the mode reduced")
for e in fx.values():
    system = e.get("System", [None])[0]
    if system is not None:
        need(system in systems, "%s: unknown particle system %s" % (e["Name"][0], system))

# --- new particle systems and sounds with CREDITS
for system in ("RoomAmbHeartHitBurst", "RoomAmbWaveRumble", "RoomAmbWaveSurgeLight", "RoomAmbWaveShockRing",
               "RoomAmbCryptEarth", "RoomAmbCryptClods", "RoomAmbCryptSpirit", "RoomAmbTortureFlash",
               "RoomAmbTortureLinks", "RoomAmbCannonMuzzle", "RoomAmbCannonSmokeRing", "RoomAmbDoorRuneCracks",
               "RoomAmbDoorRuneFlicker", "RoomAmbHandCastSpark"):
    need(systems.get(system) == "RoomAmbienceFixEffects.particle", "particle system %s missing" % system)
for family, name in (("Prison/Clang", "FxPrisonClang01"), ("Torture/Shackles", "FxTortureShackles01"),
                     ("Crypt/Raise", "FxCryptRaise01"), ("WavePortal/Surge", "FxWavePortalSurge01"),
                     ("Heart/Hit", "FxHeartHit01")):
    path = os.path.join(ROOT, "sounds", "Spatial", "Rooms", *family.split("/")) + os.sep + name + ".ogg"
    need(os.path.exists(path) and os.path.getsize(path) > 1000, "sound %s missing" % family)
    need("sounds/Spatial/Rooms/%s/%s.ogg" % (family, name) in credits, "CREDITS entry for %s missing" % name)
    need(any(e.get("Family") == ["Rooms/" + family] for e in fx.values()), "no effect plays Rooms/%s" % family)
need(re.search(r"AI-assisted", credits[credits.index("FxHeartHit01"):credits.index("FxHeartHit01") + 400]) is not None,
     "the new sounds must be marked as AI-assisted in CREDITS")
generator = read("tools", "gen_room_effect_sounds.py")
for function in ("prison_clang", "torture_shackles", "crypt_raise", "wave_portal_surge", "heart_hit"):
    need("def %s(" % function in generator, "tools/gen_room_effect_sounds.py lacks %s" % function)

if problems:
    for problem in problems:
        print("PROBLEM:", problem)
    sys.exit(1)
print("fine")
