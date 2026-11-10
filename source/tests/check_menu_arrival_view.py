#!/usr/bin/env python3
"""Guard the return flight against the elevated view behind the menu scenery."""

from pathlib import Path
import sys


def main():
    """Check the authored arrival poses keep the overview horizon throughout the flight."""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "config/mainmenuscene.cfg"
    poses = {}
    flights = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        words = line.split()
        if words and words[0] == "Pose":
            poses[words[1]] = tuple(float(value) for value in words[2:])
        elif words and words[0] == "Flight":
            flights[words[1]] = words[3:]

    assert flights["arrival"] == ["arrival_approach", "overview"]
    for name in ("arrival", "arrival_approach", "overview"):
        x, y, z, pitch, yaw, roll = poses[name]
        assert (x, z, pitch, yaw, roll) == (0.0, 5.2, 93.5, 0.0, 0.0), name
    assert poses["arrival"][1] < poses["arrival_approach"][1] < poses["overview"][1]
    print("OK: arrival approaches the gate at the overview horizon")


if __name__ == "__main__":
    main()
