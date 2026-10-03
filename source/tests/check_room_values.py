"""Check the room values: prices, prison and torture
damage, arena damage, torture conversion times, library storage and the
room based creature attraction."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8")


rooms = read("config/rooms.cfg")
values = dict(re.findall(r"^\s+(\w+)\s+([\d.]+)\s*$", rooms, re.M))
expected = {
    "TreasuryCostPerTile": "67", "DormitoryCostPerTile": "100", "WorkshopCostPerTile": "200",
    "CryptCostPerTile": "667", "TortureCostPerTile": "500",
    "PrisonDamagePerTurn": "0.06", "ArenaDamageTakenPercent": "0.2",
    "TortureDamagePercentPerSecond": "0.0067",
}
for key, value in expected.items():
    assert values.get(key) == value, f"{key} is {values.get(key)}, expected {value}"
assert "TortureRallyPercent" not in rooms and "TortureDamagePerTurn" not in rooms

creature = read("source/entities/Creature.cpp")
assert "ArenaDamageTakenPercent" in creature
assert creature.count("RoomType::arena") >= 3, "pit damage checks the arena of both fighters"

torture = read("source/rooms/RoomTorture.cpp")
assert "TORTURE_LEVEL_PERCENT[] = {100.0, 105.0, 110.0, 115.0, 120.0, 130.0, 140.0, 150.0, 200.0, 300.0}" in torture
assert "getNbTurnsTorture()" in torture and "TortureRallyPercent" not in torture

creatures = read("config/creatures.cfg").replace("\r\n", "\n")
times = {"Goblin": 80, "DarkElf": 80, "Dwarf1": 80, "Dwarf2": 80, "Troll": 120, "Skeleton": 120,
         "Wizard": 120, "Monk": 240, "Knight": 240}
for name, seconds in times.items():
    block = creatures[creatures.index(f"    Name\t{name}\n"):]
    block = block[:block.index("[/Creature]")]
    assert f"    TortureTimeToConvert\t{seconds}\n" in block, f"{name} torture time"

library = read("source/rooms/RoomLibrary.cpp")
assert "countSkillItemsOnRoom" not in library
assert "getNumActiveSpots() - mCreaturesSpots.size()" not in library

spawn = read("config/spawnconditions.cfg").replace("\r\n", "\n")
for cls, line in (("Troll", "RoomTiles\tWorkshop\t9\t0"), ("DarkElf", "RoomTiles\tGuardRoom\t1\t0")):
    block = spawn[spawn.index(f"    CreatureClass\t{cls}\n"):]
    block = block[:block.index("[/SpawnCondition]")]
    assert line in block, f"{cls} spawn condition"
assert "RoomType::guardRoom" in read("source/ai/KeeperAI.cpp")
print("CHECKS OK")
