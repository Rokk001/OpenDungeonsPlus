# Research progression

## Existing implementation and remaining scope

The current skill tree already covers 13 buildable rooms, four traps and ten
spells. The client edits its ordered selection; Seat validates allowed skills
and dependencies, selects the first pending skill and applies library points.
Existing completion unlocks the item once. F10 already has a Skill entry.

Reuse those paths. The first checkpoint adds the requested research minimap
button beside production, retaining the four existing corner buttons for six
controls total. This is navigation only, not completion of upgrade progression.

Successive levels require new maximum levels, costs and per-item benefits.
Neither this request nor the inspected approved specifications define them.
The user has been asked whether to delegate balancing or supply values; that
decision remains pending. Do not invent these values or mark the full research
task ready for test based only on working navigation.

The navigation checkpoint passes 348 installed-CEGUI layout/controller checks,
including the production regressions, all six independent button hit targets,
non-overlap, and the actual research-button subscription opening and closing the
existing tree. Real Ogre views at 800x600 and 1280x720 were inspected. This does
not verify unimplemented research upgrades. Release compilation and runtime
preparation pass; the full research task remains awaiting its balancing decision.
