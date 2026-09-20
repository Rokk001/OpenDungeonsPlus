# Direct movement through stair-shaped corridors

The coarse map path permits centre-to-centre diagonals only when both adjacent
cardinal tiles are passable. In an excavated staircase one of those tiles is a
wall, so the path alternates horizontal/vertical tile centres. The existing
room-object refinement returns immediately when no furniture is nearby, leaving
that zigzag and client-side random waypoint offsets untouched.

Smooth repeated cardinal turns through checked edge midpoints and visible later
waypoints; do not relax wall, door, terrain or furniture traversal rules.
The existing segment validator must approve every shortcut. Keep the destination
and movement speed and disable random waypoint offsets on a refined corridor.
Apply the same checked smoothing after furniture refinement where it fits.

This reuses the current waypoint/network path; no new navigation system,
creature blocking, speed reduction, protocol or release change is required.
The expanded production-navigation fixture reproduces 24 failures before the
change across four corridor rotations and both travel directions. It also
checks exact destination, diagonal distance, dense wall samples and client
offset suppression, alongside the existing furniture regressions.
The final ordinary production-navigation run passes 6,678 checks, including the
eight stair-corridor cases that previously failed. The separately expanded
packed-bedroom/full-room run is still blocked by Windows application control
(4551), so that expanded run is not counted as a pass. Security is unchanged.
The September 20 Release build succeeds and is deployed; game acceptance remains
with the user. See BUILDING.md for the current executable and validation limits.
