# Projectile collision and flight path

The current missile upkeep continues into the general creature loop after
applying a targeted hit, so one projectile may damage its target twice or also
hit a second creature on the same tile. The isolated current-code diagnosis
reproduced two damage callbacks where one was expected.

The traversal also computes segment distances using 3D vectors whose z values
are never initialized. Use initialized 2D coordinates for this tile calculation.
For incidental impacts, stop the visible path on the actual collision tile,
matching the existing targeted-hit endpoint, rather than subtracting a remaining
distance affected by grid traversal. Disable creature-style random destination
offsets for projectile paths so client flight uses the authoritative endpoint.

Keep configured ranges, speeds, damage values, ownership, piercing behavior,
wall handling and accepted creature animations unchanged. This is a separately
releasable projectile correction; ranged attack animation remains a combat
feature follow-up. No version, save or packet-layout change is required.

The committed `source/tests/check_projectile_collision.py` extracts production
upkeep, destination calculation, wall policy and tile traversal and executes
them against Ogre with map/entity test doubles. All 75 checks pass; the preceding
commit produces 28 failures. Coverage includes targeted and incidental hits,
shared-tile bystanders, interception, ally policy, piercing, diagonal endpoints,
walls, map edges and post-impact visual-flight lifetime.

Release compilation/linking passes to `opendungeons-plus-pending.exe` beside the
existing prepared runtime because the user is running the normal executable.
No game was stopped or launched. The normal executable is not yet replaced;
BUILDING.md records the pending binary and its verification boundary.
