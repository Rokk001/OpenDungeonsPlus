# Research progression

## Existing implementation and remaining scope

The current skill tree already covers 13 buildable rooms, four traps and ten
spells. The client edits its ordered selection; Seat validates allowed skills
and dependencies, selects the first pending skill and applies library points.
Existing completion unlocks the item once. F10 already has a Skill entry.

Reuse those paths. The first checkpoint adds the requested research minimap
button beside production, retaining the four existing corner buttons for six
controls total. This is navigation only, not completion of upgrade progression.

The user approved the separate three-level balancing proposal after reviewing
it. Implement per-seat levels through the existing dependency tree, library
points, save and network paths, preserving map grants and initial free access.
Each completed upgrade applies its approved item-specific effect; navigation
alone does not complete the task. The feature branch retains the complete newer
fork, including the sleep-arrival correction.

The navigation checkpoint passes 348 installed-CEGUI layout/controller checks,
including the production regressions, all six independent button hit targets,
non-overlap, and the actual research-button subscription opening and closing the
existing tree. Real Ogre views at 800x600 and 1280x720 were inspected. This does
not verify the subsequent research upgrades.

## Three-level progression

All 27 entries retain their existing level-I effects and dependencies, with
two separately researched upgrades. The existing free initial unlocks remain
map-controlled. Upgrades cost twice and four times the original research cost;
free entries use a 100-point anchor (150 for Library and Summon Worker).
The tree displays level, next benefit/cost, ordered selection and progress.
Already unlocked actions remain available while their upgrade is researched.

Effects are evaluated for the owning seat at room work, trap attack or spell
creation. Existing projectiles and spell effects keep their original values;
work in progress and trap charges are retained. Door health remains stored in
base units, preserving its health fraction on upgrades and ownership changes.
Treasury capacity changes do not discard existing gold or allow negative deposits.
Research levels, points and pending order survive save/load; legacy completed
skills load as level I. Target levels on requests prevent stale edits from
silently ordering a later upgrade. Network version 0.7.2 is required on both
ends; the map loader accepts 0.7.1 files, but old network replays are incompatible.
The initial update changed only map listing's version check and accidentally
left actual loading blocked; the [compatibility correction](LEGACY-SAVE-VERSION.md)
aligns both gates and tests the two reported saved-game headers.

Verification: 411 extracted production research, save and real-codec checks
pass, covering every item and all approved effect values; 364 installed-CEGUI
controller/layout checks pass, including level/action visibility, costs,
progress and exclusions. Release compilation passes. These isolated checks do
not replace the user's gameplay, multiplayer and visual acceptance.
