"""Check the room values: prices, prison and torture
damage, arena damage, torture conversion, library storage and the
room based creature attraction."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8")


rooms = read("config/rooms.cfg")
values = dict(re.findall(r"^\s+(\w+)\s+(-?[\d.]+)\s*$", rooms, re.M))
expected = {
    "TreasuryCostPerTile": "72", "DormitoryCostPerTile": "92", "WorkshopCostPerTile": "215",
    "CryptCostPerTile": "620", "TortureCostPerTile": "470",
    "HatcheryCostPerTile": "110", "TrainHallCostPerTile": "165", "TrainHallCostPerSecond": "0.6214694818076253",
    "LibraryCostPerTile": "190", "PrisonCostPerTile": "240", "WoodenBridgeCostPerTile": "180",
    "StoneBridgeCostPerTile": "540", "ArenaCostPerTile": "230", "CasinoCostPerTile": "290",
    "GuardRoomCostPerTile": "210", "TempleCostPerTile": "930",
    "ArenaDamageTakenPercent": "0.2", "DungeonHeartHP": "15100",
    "HatcheryGiftHpRecoveredPerChicken": "4.1",
    "TortureDamagePercentPerSecond": "0.00275",
}
for key, value in expected.items():
    assert values.get(key) == value, f"{key} is {values.get(key)}, expected {value}"
assert "TortureRallyPercent" not in rooms and "TortureDamagePerTurn" not in rooms
# The flat prison damage and the flat chicken heal are gone
for key in ("PrisonDamagePerTurn", "PrisonDamagePerTurnMin", "HatcheryHpRecoveredPerChicken"):
    assert key not in values, f"{key} must be removed"

creature = read("source/entities/Creature.cpp")
assert "ArenaDamageTakenPercent" in creature
assert creature.count("RoomType::arena") >= 3, "pit damage checks the arena of both fighters"

torture = read("source/rooms/RoomTorture.cpp")
# The conversion follows the mood and a chance per second, there is no conversion time any more
assert "TORTURE_LEVEL_PERCENT" not in torture and "tortureTurnsToConvert" not in torture
assert "TortureRallyPercent" not in torture

creatures = read("config/creatures.cfg").replace("\r\n", "\n")
assert "TortureTimeToConvert" not in creatures, "the per-type torture time is removed"

library = read("source/rooms/RoomLibrary.cpp")
assert "countSkillItemsOnRoom" not in library
assert "getNumActiveSpots() - mCreaturesSpots.size()" not in library

spawn = read("config/spawnconditions.cfg").replace("\r\n", "\n")
for cls, line in (("Troll", "RoomTiles\tWorkshop\t9\t0"), ("DarkElf", "RoomTiles\tGuardRoom\t1\t0")):
    block = spawn[spawn.index(f"    CreatureClass\t{cls}\n"):]
    block = block[:block.index("[/SpawnCondition]")]
    assert line in block, f"{cls} spawn condition"
assert "RoomType::guardRoom" in read("source/ai/KeeperAI.cpp")
# Every hatchery key the code reads is in the config with a value and a documentation line in the file header, and
# the default of the client look numbers is the value of the config
hatchery_code = read("source/rooms/RoomHatchery.cpp") + read("source/render/RenderManagerChickens.cpp") +     read("source/entities/ChickenEntity.cpp")
used = set(re.findall(r'"(Hatchery[A-Za-z0-9]+)"', hatchery_code))  # a name ending in "_" is the prefix of an entity name
used -= {"HatcheryWaits", "HatcheryDay", "HatcheryLays", "HatcheryNestLays", "HatcheryGrain"}  # tags of the save game, not config keys
assert len(used) > 100, len(used)
documented = set(re.findall(r"^# (Hatchery\w+)\s", rooms, re.M))
for key in sorted(used):
    assert key in values, f"{key} is read by the code but has no value in config/rooms.cfg"
    assert key in documented, f"{key} is not documented in the header of config/rooms.cfg"
look_defaults = re.findall(r'configValue\("(HatcheryLook\w+)", (-?[\d.]+)f\)', read("source/render/RenderManagerChickens.cpp"))
assert len(look_defaults) > 80, len(look_defaults)
for key, default in look_defaults:
    assert abs(float(values[key]) - float(default)) < 1e-6, f"{key}: config {values[key]}, default in the code {default}"
print("CHECKS OK")
