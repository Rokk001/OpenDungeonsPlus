"""Check the arena mood factors (victor, spectator, alone) and the hated
company factor. The values are our own scale: the victor bonus is the whole pit mood cap (1000), the
spectator and solitary rates move a creature by about 2.8 and 2.2 percent of the cap per second, and the hated
company factor is -10 mood points per turn (14 per second at 1.4 turns per second)."""
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
cap = cfg_value(rooms, "PitMoodMax")
assert cap == 1000.0
assert cfg_value(rooms, "PitMoodVictor") == 1000.0 and abs(cfg_value(rooms, "PitMoodVictor") / cap - 1.0) < 0.01
assert cfg_value(rooms, "PitMoodSpectator") == 28.0 and abs(cfg_value(rooms, "PitMoodSpectator") / cap - 0.028) < 0.001
assert cfg_value(rooms, "PitMoodSolitary") == -22.0 and abs(cfg_value(rooms, "PitMoodSolitary") / cap + 0.022) < 0.001
creatures = read("config/creatures.cfg")
assert creatures.count("HatedCompany\t40\t-10") == creatures.count("Rested\t40\t10") > 0
arena = read("source/rooms/RoomArena.cpp")
for token in ("PitMoodVictor", "PitMoodSpectator", "PitMoodSolitary", "mFightOngoing"):
    assert token in arena, token
assert "getPitMood" in read("source/creaturemood/CreatureMoodManager.cpp")
assert "CreatureMoodHatedCompany.cpp" in read("CMakeLists.txt")
print("CHECKS OK")
