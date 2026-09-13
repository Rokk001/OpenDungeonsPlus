# Navigation around room objects

## Observed path and gap

Creature tile pathfinding checks terrain and building movement permissions, but
does not inspect the room's placed furniture. Its final walk queue is sent to
clients, which independently jitter each waypoint by up to 0.3 tiles. Hatchery
chickens are spawned at the coop origin and wander without furniture checks.
Workshop, library and training interactions first route through the furniture's
central tile before appending their existing working-position offset.

The September 13 screenshot shows creatures overlapping chicken coops. Inspection
of the actual mesh bounds confirms that the coop is not centered on its tile:
its local footprint extends from -0.203275 to 0.796725 in X and -0.4 to 0.4 in Y.
Blocking only its tile center, or retaining client-side random offsets on a
corrected route, would therefore leave the reported failure possible.

## Implementation boundary

Retain the existing terrain/door rules and room actions. Refine creature walk
queues against placed, rotated furniture footprints, including crossings between
waypoints, and send the resulting clearance route without independent client
jitter. Preserve intentional entry into a creature's own bed and assigned room
interaction positions; other creatures must route around those objects.
Use the same footprint check for chicken spawning and wandering. No change to
accepted feeding or sleeping skeletal animations is required.

## Body clearance and interaction access

The 41 furniture footprints come from the shipped mesh bounds. Creature walking
envelopes come from skinned Walk vertices for all 33 models, scaled by the existing
level factor; the directional envelope follows the renderer's native-negative-Y
orientation. A circle is used only for the broad-phase/jitter guard, not as an
artificial forward reach. Independent client offsets are disabled near furniture,
including their diagonal displacement around rotated objects. New furniture and
the separately stored prison fences invalidate affected existing routes.

Food consumption requires clear body placement and an unobstructed line to the
actual chicken. A straight final approach preserves the required facing. The
existing same-tile/cardinal-neighbor eating range, rewards and accepted animation
remain unchanged. At maximum level, Defender and Dragon cannot physically fit in
that range while facing a chicken immediately against the coop wall: an independent
8x8/64x64 oriented-box check found no valid point, even without the conservative
projection. These targets are released without consumption; all 33 models at
levels 1 and 30 reach and eat food after it moves clear of the coop. The tests
retain both the obstructed-target rejection and subsequent successful feeding;
neither the measured bodies nor the eating range was changed to make them pass.

Workshop, library, training and casino arrival gates use a body-clear position on
the assigned side of their object, increasing stand-off only as necessary. They
recognize the adjusted endpoint instead of repeatedly returning to an obstructed
tile center, and release physically inaccessible work. Existing work rewards,
assignments and animation selection remain unchanged. Own-bed entry, portal exit
and assigned torture occupancy retain their intentional interaction exceptions.

## Slow-turn regression and correction

The user's September 13 15:10-15:13 run exposed an incomplete navigation build:
server upkeep took approximately 1.6-10.0 seconds and workers hit the existing
20-action-loop safeguard. Notifications and wall-mark confirmations share that
server loop, explaining delayed creature appearance and input acknowledgements.

The initial furniture A* searched outward from the creature even when furniture
enclosed the destination, and optional coarse tile centers could each trigger
another full-map fallback. The corrected search follows valid movement edges
backwards from the destination and precomputes the eight grid-heading envelopes;
optional centers use only the local search, while the actual destination retains
the full-map fallback. This is not a search-budget cutoff or a collision bypass.
An enclosed destination on a 128x128 map took 83 ms before and under 1 ms after;
the regression also checks that rejection does not traverse the whole map.

The existing log ends in normal shutdown after a slow server turn, with no new
native crash dump or matching recent Application Error event found during this
check. This proves neither the absence nor the cause of the reported crash;
crash diagnosis is tracked separately after this task's requested checkpoint.

## Verification

### Open regression: fully furnished dormitory transit

`check_room_object_navigation.py --packed-beds` now exercises a 3x3 dormitory
with all nine worker beds present, surrounding walls and opposing doorways.
It checks both travel directions at levels 1 and 30, confirms the underlying
terrain route exists, and requires arrival without removing beds or crossing
walls. This is an isolated fixture using the actual navigation implementation,
not a manual game run or an exact reconstruction of the user's save.

The current implementation fails all four transit attempts: 2,967 checks,
four failures. The existing open-map furniture benchmark permits routing around
the room and does not cover this acceptance requirement. The normal regression
suite remains separate; passing it does not establish packed-room passability.
No production behavior has been changed by this diagnostic checkpoint, and the
navigation task is not ready for acceptance.

### Follow-up: stalls during combat testing

The subsequent 15:56 user run still takes 4.1-4.4 seconds in upkeep and repeatedly
exhausts the 20-action loop guard. The new furniture approach retries up to 320
standing offsets independently. A start-connectivity precheck alone did not fix
the slow saved-food cases; searching from both ends alone was also insufficient.
Food offsets now share one search, with their checked, facing-aligned final leg
retained. Single-destination searches use balanced bidirectional A*; alternative
food destinations use bidirectional Dijkstra, without a search-budget cutoff.
Either enclosed endpoint component can terminate failure without flooding the
other component. Terrain, measured body clearance and legacy-overlap exit rules
remain unchanged, and no persistent cache can retain stale furniture pointers.

The same log shows carrying/claiming destinations and library use repeatedly
failing and immediately returning to selection. The failed approach branches
now release their assignments and finish the current action tick; successful
walk dispatch, later retries, food/work rewards and combat rules are unchanged.

With the same save and 15:57 log fixture, the committed old navigation reached
277 of 375 food cases, total 1,482.060 ms, worst 642.864 ms. The corrected code
reaches the same 277 cases, total 823.591 ms, worst 5.853 ms; every returned path
is checked for body/furniture overlap. The retry probe reproduces nine failures
before and passes all 12 checks after; four room gates and the food gate also
reproduce immediate-retry failures before and pass after. This is an isolated
production-code/terrain fixture, not a whole-game responsiveness measurement.
Packed-bed passability and visual combat acceptance remain unresolved and are
not claimed fixed by these performance corrections.

Final follow-up verification passes 3,187 geometry/shared-search checks, 3,385
navigation/benchmark/saved-food checks and 12 failed-destination checks, with
feeding 109, projectile 75, ranged dispatch 15, workshop 13 and shutdown 31.
The optional saved-food fixture enforces a 100-ms per-call local regression
ceiling; its final observed maximum is 5.684 ms and total is 820.368 ms.
The older counts and measurements below document the preceding checkpoint.

- `check_room_object_path.py`: 3,199 geometry, Ogre-orientation, terrain/door,
  legacy-overlap exit and enclosed-destination checks.
- `check_room_object_bounds.py`: 166 checks against 41 real furniture meshes
  and two elevated wall decorations.
- `check_creature_walking_bounds.py`: 3,993 real-Ogre checks, covering 121 Walk
  poses for every creature mesh and the measured radial/XY envelopes.
- `check_room_object_navigation.py`: 2,950 production-navigation and extracted
  food/room-arrival checks, including all models at levels 1 and 30, placement,
  rotated-object client offsets, prison fencing and inaccessible-job release.
- Its `--benchmark` option passes 2,970 checks; 20 routes among 100 furniture
  objects took 42 ms in the optimized fixture after the search correction.
- Its `--saved-terrain` / `--furniture-log` fixture passes 2,990 checks using the
  user's 120x151 save terrain, logged worker position/level and 24 logged objects
  with source-defined orientations: 39 searches totaled 3.002 ms, maximum 0.152 ms.
  It deliberately excludes unknown randomized object angles and is not a complete
  game simulation or a measurement of save-load/render responsiveness.
- Related regressions passed: feeding limb 109, research 411, trap production 41,
  workshop scheduling 13, projectile collision 75, ranged dispatch 15 and menu
  cursor 60 checks.

Release compilation/runtime preparation and executable metadata are recorded in
[BUILDING.md](BUILDING.md). Gameplay/visual acceptance remains with the user; no
game was launched or stopped by the agent. No version bump is required: saved
data and network packet layouts are unchanged, and controlled movement uses the
existing waypoint and distortion fields. This branch remains separate from the
accepted animation, research and production branches; no push was requested.
