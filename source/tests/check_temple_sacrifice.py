"""Check that the temple sacrifice follows the reference: no mana and no research points
for a sacrifice, a queue of the last three sacrifices, the first matching recipe wins and
the level of a new creature is the rounded down average of the inputs."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8").replace("\r\n", "\n")


rooms = read("config/rooms.cfg")
temple = read("source/rooms/RoomTemple.cpp")
header = read("source/rooms/RoomTemple.h")

for key in ("TempleSacrificeManaPerLevel", "TempleSacrificeWaitTurns", "TempleManaBoost", "TempleWorkersGiven"):
    assert key not in rooms and key not in temple, f"{key} must be gone"
assert not re.search(r"Temple\w*Research", rooms + temple), "no research points for sacrifices"

sacrifice = temple[temple.index("void RoomTemple::sacrificeCreature"):temple.index("void RoomTemple::giveSacrificeResult")]
assert "addManaToSeat" not in sacrifice, "a sacrifice gives no mana"
assert "TEMPLE_SACRIFICE_QUEUE_SIZE = 3" in temple and "mSacrificed.erase(mSacrificed.begin())" in sacrifice
assert "totalLevel / static_cast<uint32_t>(inputs.size())" in sacrifice and "+ 1" not in sacrifice.split("averageLevel")[1][:40]
assert "mTurnsSinceSacrifice" not in temple + header

values = dict(re.findall(r"^\s+(TempleRecipe\w+)\s+(\S+)\s*$", rooms, re.M))
count = int(values["TempleRecipeCount"])
creatures = set(re.findall(r"^\s+Name\s+(\w+)\s*$", read("config/creatures.cfg"), re.M))
for i in range(1, count + 1):
    recipe = values[f"TempleRecipe{i}"]
    inputs, result = recipe.split("=")
    assert 1 <= len(inputs.split("+")) <= 3, recipe
    for name in inputs.split("+"):
        assert name in creatures, f"{recipe}: unknown creature {name}"
    assert result == "ManaBoost" or result in creatures, recipe
assert values["TempleRecipe1"] == "DarkElf+DarkElf=Troll"
assert values["TempleRecipe2"] == "Monk+Monk+Monk=ManaBoost"

assert (repo / "docs/development/TEMPLE-SACRIFICE.md").exists()
print("CHECKS OK")
