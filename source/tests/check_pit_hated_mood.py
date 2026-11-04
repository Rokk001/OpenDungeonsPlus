"""Check the arena mood factors (victor, spectator, alone) and the hated
company factor. The stored mood of a creature runs from 0 to CreatureBaseMood (1500). The arena values are one-time
or per-second amounts added to the stored mood through Creature::addPitMood: the victor gets 250 once when the fight
ends, a spectator gets 14 per second, a creature alone in the pit loses 11 per second. There is no pit mood cap or
decay any more (PitMoodMax and PitMoodDecay are gone). The hated company is a fall of 0.119 mood points per turn
while a creature of the opposite alignment is near, and a rested creature gets 100 once."""
import re
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8")


def cfg_value(text, key):
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == key:
            return float(parts[1])
    raise AssertionError("missing " + key)


rooms = read("config/rooms.cfg")
for gone in ("PitMoodMax", "PitMoodDecay"):
    assert not re.search(r"^\s*" + gone + r"\b", rooms, re.M), gone + " must be gone"
assert cfg_value(read("config/global.cfg"), "CreatureBaseMood") == 1500.0
assert cfg_value(rooms, "PitMoodVictor") == 250.0
assert cfg_value(rooms, "PitMoodSpectator") == 14.0
assert cfg_value(rooms, "PitMoodSolitary") == -11.0
creatures = read("config/creatures.cfg")
assert creatures.count("HatedCompany\t-0.119") == creatures.count("Rested\t100") > 0
arena = read("source/rooms/RoomArena.cpp")
for token in ("PitMoodVictor", "PitMoodSpectator", "PitMoodSolitary", "mFightOngoing", "addPitMood"):
    assert token in arena, token
creature = read("source/entities/Creature.cpp")
assert re.search(r"void Creature::addPitMood\(double points\)\s*\{\s*applyMoodEvent\(points,\s*false\);", creature)
assert "getPitMood" not in read("source/creaturemood/CreatureMoodManager.cpp")
assert "CreatureMoodHatedCompany.cpp" in read("CMakeLists.txt")
print("CHECKS OK")
