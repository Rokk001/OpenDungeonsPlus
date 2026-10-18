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

temple = (ROOT / "source/rooms/RoomTemple.cpp").read_text(encoding="utf-8")
reward = function(temple, "void RoomTemple::giveSacrificeResult(")
assert "The gods accepted your sacrifice and send you a new creature" not in reward
assert reward.index("newCreature->addToGameMap();") < reward.index("notifyCreatureArrival(classToSpawn->getClassName())")
assert reward.index("newCreature->setPosition(") < reward.index("notifyCreatureArrival(classToSpawn->getClassName())")
assert 'if(!message.empty() &&' in reward
assert 'message = "The gods accepted your sacrifice and send you a special";' in reward
print("Creature sacrifice rewards share first-arrival history; real special rewards remain announced: PASS (static only)")

prison = (ROOT / "source/rooms/RoomPrison.cpp").read_text(encoding="utf-8")
prison_upkeep = function(prison, "void RoomPrison::doUpkeep()")
assert prison_upkeep.count("notifyCreatureArrival(className)") == 1
assert prison_upkeep.index("newCreature->addToGameMap();") < prison_upkeep.index("notifyCreatureArrival(className)")
assert prison_upkeep.index("newCreature->setPosition(") < prison_upkeep.index("notifyCreatureArrival(className)")
assert "A creature died starving in your prison" in prison_upkeep
print("Prison offspring use shared first-arrival history while starvation losses remain visible: PASS (static only)")

# Summoning announces only after the creature exists at its valid destination.
for spell, actor, definition in (("Worker", "newCreature", "classToSpawn"),
                                  ("Champion", "champion", "definition")):
    source = (ROOT / f"source/spells/SpellSummon{spell}.cpp").read_text(encoding="utf-8")
    method = "summonWorkersOnTiles" if spell == "Worker" else "castSpell"
    summon = function(source, f"bool SpellSummon{spell}::{method}(")
    notice = f"notifyCreatureArrival({definition}->getClassName())"
    assert summon.count(notice) == 1
    assert summon.index(f"{actor}->addToGameMap();") < summon.index(notice)
    assert summon.index(f"{actor}->setPosition(spawnPosition);") < summon.index(notice)
    assert summon.index("takeMana(") < summon.index(notice)
print("Successful worker and champion summons share saved first-arrival history: PASS (static only)")

# Ownership acquisition counts only after the conversion actually succeeds.
torture = (ROOT / "source/rooms/RoomTorture.cpp").read_text(encoding="utf-8")
conversion = function(torture, "bool RoomTorture::useRoom(")
notice = "notifyCreatureArrival(creature.getDefinition()->getClassName())"
assert conversion.count(notice) == 1
assert conversion.index("creature.changeSeat(getSeat());") < conversion.index(notice)
assert "Your tormentors have convinced another creature" in conversion
source = (ROOT / "source/spells/SpellDefector.cpp").read_text(encoding="utf-8")
conversion = function(source, "bool SpellDefector::castSpell(")
notice = "notifyCreatureArrival(creature->getDefinition()->getClassName())"
assert conversion.count(notice) == 1
assert conversion.index("creature->changeSeat(player->getSeat());") < conversion.index(notice)
assert conversion.index("creature->addCreatureEffect(") < conversion.index(notice)
assert conversion.index("takeMana(") < conversion.index(notice)
print("Successful conversions share saved first-arrival history: PASS (static only)")
