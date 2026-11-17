#!/usr/bin/env python3
"""Guard the outside arrival flight: it descends from the raised view outside the yard straight onto the overview."""

from pathlib import Path
import sys


def main():
    """Check the authored arrival: centred, outside and above the yard, descending and levelling out onto the overview.

    The raised start looks down past the walls; that it then sees scenery and no sky below the horizon is checked by
    check_menu_sky_below_horizon, its clearance by check_menu_flight_geometry.
    """
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
    assert poses["overview"] == (0.0, -29.0, 5.2, 93.5, 0.0, 0.0), "overview"
    route = [poses[name] for name in ("arrival", "arrival_approach", "overview")]
    for name, (x, y, z, pitch, yaw, roll) in zip(("arrival", "arrival_approach", "overview"), route):
        assert (x, yaw, roll) == (0.0, 0.0, 0.0), name
    # Outside the yard (courtyard paving ends at y -29.9) and moving towards the gate.
    assert route[0][1] < route[1][1] < route[2][1] and route[1][1] < -29.9
    # Raised start that descends onto the overview height.
    assert route[0][2] > route[1][2] > route[2][2] and route[0][2] >= 20.0
    # Looking down at the start and levelling out to the overview pitch.
    assert route[0][3] < route[1][3] < route[2][3] and route[0][3] <= 70.0
    print("OK: arrival descends from the raised view outside the yard onto the overview")


if __name__ == "__main__":
    main()
