"""Check the arena mood factors (victor, spectator, alone) and the hated
company factor: raw values converted at 30 mood points per
annoyance point and 1.4 turns per second."""
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
# raw values 16400, 275, 275 over 328 raw units per point, times 30
assert abs(cfg_value(rooms, "PitMoodVictor") - 1500.0) < 1
assert abs(cfg_value(rooms, "PitMoodSpectator") - 275 / 328 * 30) < 1
assert abs(cfg_value(rooms, "PitMoodSolitary") + 275 / 328 * 30) < 1
creatures = read("config/creatures.cfg")
# raw 150 per second: 150 / 328 * 30 / 1.4 = 9.8 per turn
assert creatures.count("HatedCompany\t43\t-10") == creatures.count("Rested\t30\t43") > 0
arena = read("source/rooms/RoomArena.cpp")
for token in ("PitMoodVictor", "PitMoodSpectator", "PitMoodSolitary", "mFightOngoing"):
    assert token in arena, token
assert "getPitMood" in read("source/creaturemood/CreatureMoodManager.cpp")
assert "CreatureMoodHatedCompany.cpp" in read("CMakeLists.txt")
print("CHECKS OK")
