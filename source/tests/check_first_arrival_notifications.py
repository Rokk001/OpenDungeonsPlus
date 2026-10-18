"""Static guards for one first-arrival notice per class, preserved across saves.

No compiler or game is launched. Runtime save round trips remain integration checks.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# Read one C++ function for the notification and save-path checks.
def function(source, signature):
    body = source[source.index(signature):]
    return body[:body.index("\n}\n")]


seat = (ROOT / "source/game/Seat.cpp").read_text(encoding="utf-8")
portal = (ROOT / "source/rooms/RoomPortal.cpp").read_text(encoding="utf-8")
arrival = function(seat, "void Seat::notifyCreatureArrival(")
pick = function(seat, "const CreatureDefinition* Seat::getNextFighterClassToSpawn(")
spawn = function(portal, "void RoomPortal::spawnCreature()")
load = function(seat, "bool Seat::importSeatFromStream(")
save = function(seat, "bool Seat::exportSeatToStream(")
assert "notifyNewCreatureType" not in pick
assert "ServerNotificationType::chatServer" not in pick
assert "SoundRelativeKeeperStatements::CreatureNew" not in pick
assert spawn.index("newCreature->addToGameMap();") < spawn.index("notifyCreatureArrival(")
assert spawn.index("newCreature->setPosition(") < spawn.index("notifyCreatureArrival(")
assert arrival.count("notifyNewCreatureType(") == 1
assert arrival.index("std::find(") < arrival.index("mAnnouncedCreatureClasses.push_back(")
assert arrival.index("mAnnouncedCreatureClasses.push_back(") < arrival.index("notifyNewCreatureType(")
assert "getHasLost()" in arrival and "getIsHuman()" in arrival
assert 'if(str == "[AnnouncedCreatureClasses]")' in load
assert "NameAliases::resolve(str)" in load
assert "mAnnouncedCreatureClasses.push_back(className)" in load
assert "[/AnnouncedCreatureClasses]" in load and "[/AnnouncedCreatureClasses]" in save
assert "for(const std::string& className : mAnnouncedCreatureClasses)" in save
assert save.index("[AnnouncedCreatureClasses]") < save.index("[SkillNotAllowed]")
assert load.index("[AnnouncedCreatureClasses]") < load.index('if(str != "[SkillNotAllowed]")')
print("First-arrival notification and optional saved-history guards: PASS (static only)")

crypt = (ROOT / "source/rooms/RoomCrypt.cpp").read_text(encoding="utf-8")
raise_creature = function(crypt, "void RoomCrypt::doUpkeep()")
assert "A creature has raised in your crypt" not in raise_creature
assert raise_creature.count("notifyCreatureArrival(className)") == 1
assert raise_creature.index("newCreature->addToGameMap();") < raise_creature.index("notifyCreatureArrival(className)")
assert raise_creature.index("newCreature->setPosition(") < raise_creature.index("notifyCreatureArrival(className)")
print("Crypt and portal share successful first-class arrival history: PASS (static only)")
