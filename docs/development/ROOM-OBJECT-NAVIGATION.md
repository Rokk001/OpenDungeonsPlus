# Navigation around room objects

## Current corner-bed and walkable-landmark checkpoint

The September 13 23:05 screenshot shows the small centered beds from the older
normal executable. The existing corner placement is reused for new and restored
beds. The requested 70% now applies to the final rotated footprint in both map
axes, leaving full 30% lanes on the right and bottom of each allocation (including
1x1, 2x1 and 1x2 beds). Scaling native dimensions alone lets the existing small
angular variation encroach on those lanes; adjust that scale, not the allocation,
corner anchor, saved orientation or creature-specific variation.

The latest actual beds use a corner anchor and stable small angular variation;
portals and dungeon hearts are
excluded from furniture obstacles. This supersedes the earlier centered-bed
sizes below. The packed-bed test still has 156 failed passage assertions and
the full navigation task is not ready for acceptance. Current executable and
protocol compatibility details are in [BUILDING.md](BUILDING.md).

The rotated-lane regression reproduces 576 failures before the scale correction
and passes all 1,635 actual-mesh checks after it, covering all configured bed
dimensions, both allocation orientations and 24 stable creature angles. Default
navigation passes 4,737 checks and geometry passes 3,283; packed bedrooms still
fail 156 of 5,343 checks because a 30% free lane cannot accommodate every full
walking-body envelope. The authorized visible low-bed stepping remains open;
no collision exemption was introduced to hide these failures. Action retries
pass 24 checks in current source and fail two against the older normal executable's
source checkpoint. Version, README and save/network layouts are unchanged by
this sizing correction; the existing navigation entry remains applicable.

The September 13 follow-up fixes failed idle wandering repeating within one
tick (24 retry checks pass; two failed before). With the actual last-loaded
September 7 22:12 save and the 18:52 log, the saved fixture reconstructs 30 beds
and 53 known objects: 84 routes take 296.092 ms total, 28.394 ms worst, and 213
food searches reach 131 targets in 890.903 ms total, 37.045 ms worst; all 5,036
checks pass. Unknown randomized furniture and original room identity are not
reconstructed by this fixture, so this is not full-game or full-map validation.

The extended dense-library benchmark samples all 33 creature models at levels
1 and 30 against an edge and central workstation among 100 objects, with the
source-defined 0.3-tile library placement offset. Its 132 work calls reach 66
targets, take 6.052 ms total and 0.254 ms worst; all 5,021 checks pass. This
measurement does not reproduce a slow work search and does not justify changing
work selection or cooldowns. Live turn timing after the idle fix is unverified.

An optional `check_creature_walking_bounds.py --height-profile` diagnostic clips
animated mesh triangles at five local Z heights for all 121 sampled Walk poses.
It reports unscaled envelopes, not new collision rules. For example, Kobold
width below Z=0.05 is 0.222524, but below Z=0.10 it is already 0.311854; Spider
width is 0.771187 even below Z=0.05. The GoblinBed asset ends at Z=0.073801,
whereas Bed and ImpBed reach Z=0.686023 and 0.893739. Height-only clearance
therefore cannot be assumed to make every 0.25-tile lane passable. These are
sampled envelope measurements, not proof of exact per-pose mesh intersections;
no body bounds, bed heights or traversal permissions were changed.

These diagnostic extensions do not change runtime code or data; no additional
version bump, README feature entry or executable rebuild is needed.

## Earlier centered furniture-footprint checkpoint

Visible room furniture and navigation now share the same mesh-local XY scale.
Workstations and decorations are capped at 0.6 tiles per axis without enlarging
already compact meshes. Full-capacity one-tile beds are narrower (0.4 tiles),
leaving a 0.6-tile gap for the existing level-scaled worker body; long and large
beds retain up to 1.2 tiles along their allocated long axes. Treasury piles use
a 0.4-tile diagonal cap so arbitrary rotation does not consume that margin.
Object height, anchors, rotation, bed reservations, room capacity and rewards
are unchanged. Prison fencing, portals and the dungeon heart are not resized.

Directional collision checks now use both furniture and body separating axes;
the previous furniture-axis-only expansion filled empty corners around rotated
objects. If root-aligned quarter-tile routing misses a narrow lane, bounded
alternative grid alignments account for the asymmetric furniture/body centers,
retaining the exact same segment and terrain checks. Work approaches refine
the staging route and then append the already checked, precisely facing final
leg; generic endpoint selection no longer displaces a valid work position.

Verification of this checkpoint:

- 3,283 geometry checks, including independent Ogre rotation of both rectangles
  and explicit free-corner/crossing regressions.
- 459 real-mesh/render-scale checks over all 41 furniture assets and six angles,
  including unchanged heights and shared visual/navigation bounds.
- 7,630 navigation/room-layout/benchmark checks: twelve bed models, both bed
  orientations, both corridor axes, both travel directions and worker levels
  1/30; nineteen further furniture layouts, including offset/rotated treasury
  piles. Every returned segment retains terrain and full walking-body clearance.
- The unchanged 33 walking-model envelopes pass 3,993 skinned-pose checks.
- The existing real-Ogre renderer fixture, with the new actual bed scales,
  passes 10,136 animation, bed-support, culling and cleanup checks; representative
  resulting sleep renders were inspected. Feeding limb checks pass 109 and
  failed-action retry checks pass 12.
- Preserved feature regressions pass: research 411, production 41, workshop
  scheduling 13, projectile collision 75, ranged dispatch 15 and shutdown 31.
- The saved-terrain fixture passes 3,617 checks: 39 routes total 4.367 ms,
  maximum 0.252 ms; 375 food searches total 853.726 ms, maximum 6.738 ms,
  with 258 reachable cases under the new footprints and exact geometry.
  These are isolated measurements, not a live-game performance claim.

Release compilation and prepared runtime are recorded in BUILDING.md; no game
was launched or stopped. Manual game appearance and navigation acceptance stay
with the user. No save/network/version change is required: transforms are
derived from existing mesh identities and movement uses existing packet fields.
The historical diagnostics below describe their respective earlier checkpoints.

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

The route geometry now also supports circular logical footprints in the same
search, with exact finite-segment intersection and the existing terrain/escape
rules retained. Tangency, zero-length segments, legacy-overlap exits, direction
independence and mixed circle/rectangle barriers pass the geometry regression.
Six enclosed-room routes using circular clearance radii pass without changing
the room layout. These are geometry fixtures, not assigned game profiles.
The 3,280 geometry and 2,975 existing navigation/benchmark checks pass; 20 dense
room routes take 63 ms in the local isolated probe. Release compilation passes
to the separate pending executable; the normal executable is unchanged.
Profile integration and the packed-room acceptance test remain required before
the gameplay regression can be called fixed. Animation, interaction clearances
and current furniture assignments are unchanged; no save/network version change
is needed for this internal geometry extension.

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

### Follow-up: visible furniture footprint correction (initial inspection)

The September 13 screenshot at 18:53:47 shows the portal and dungeon-heart
landmarks occupying their connecting rooms. The shared obstacle collector
incorrectly treated their complete meshes as solid furniture. At the user's
explicit request, both mesh types are now excluded from furniture collision;
terrain/door rules and their rendered geometry remain unchanged. The focused
navigation probe reproduces 1,596 failed assertions before this correction
across all 33 creature models, levels 1/30 and six landmark rotations.

The user subsequently rejected the 0.4-tile one-cell bed footprint and requested
75% allocated width/depth, corner placement and a small creature-specific angle.
The current creation path centers bed roots and only uses allocation rotations
0/90; both loaded and new beds pass through `RoomDormitory::createBed`.
Implement the visual placement there with shared mesh bounds, preserving the
saved allocation rotation and deriving the slight visual angle from the stable
creature name. Rendered and navigation objects then share the same actual root
position/angle. This does not authorize traversal through or over beds; dense
room passability remains unresolved under the existing full-animation envelope.
The shared `Bed` mesh is configured as 1x1 for the dwarf worker and 1x2 for other
creatures, so bed scale must be instance-specific. Creation transmits the two
scale components with the building object; rendering and navigation use those
same components. Network version 0.7.3 is required on both peers; the unchanged
map-data layout still accepts 0.7.1 and 0.7.2 saves and reconstructs bed scale
from the creature definition. Allocation and saved base rotation are retained.

The subsequent September 13 load-hang investigation extends the saved-terrain
fixture to include exact saved bed centers/rotations and the source-defined
library/workshop placement offsets. The worker destination retry probe also
exposes the same immediate retry defect in ground claiming and digging (six
failed assertions). Those failed assignments now end the tick, like the already
corrected carrying, wall claiming and room-entry branches. Successful dispatch
and later retry remain unchanged. No save/network version or README behavior
change is needed for this completion of the navigation feature.

The generated Windows Release project separately disables optimization despite
the isolated navigation fixture using `/O2`; this pre-existing build defect is
being investigated on its own branch. The load-hang report remains unresolved
until that correction is built and retested; isolated tests are not gameplay
acceptance.

The user has authorized narrower visible furniture together with matching
collision bounds, retaining room capacity, tile reservations, placement and
interaction behavior. The renderer currently creates these objects at unit
scale while navigation uses their raw mesh bounds; reducing collision alone
would therefore allow creatures through visible furniture. A shared mesh-local
XY scale was selected for both paths, without changing object height, saved
positions or packet formats. Existing compact furniture will not be enlarged;
fences, portals and the dungeon heart are excluded. Bed support positioning
already uses the actual scene-node scale and must retain that behavior.

The reference screenshots establish free floor beside objects, not an exact
measured percentage. Packed-room traversal, transformed bounds, work/food
approaches and sleeping support were the required verification gates; current
results are recorded above.

### Follow-up: stalls during combat testing

The later idle-wandering regression reproduces two failures in 24 destination-
retry checks: a failed destination returns to the same upkeep loop without
adding an action, repeating wandering selection/pathfinding up to twenty times.
The failed attempt now ends that tick; later-tick selection and successful
walking remain unchanged. All 24 retry checks and 4,737 default navigation
checks pass. This completes the unmerged furniture-navigation failure handling
without changing hunger cooldowns or collision policy. It does not establish
that all observed multi-second turns have the same cause. No save/protocol
version, README or changelog change is required for this correction.

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
