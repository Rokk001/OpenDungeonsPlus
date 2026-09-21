# Research progression

## Research-tree readability follow-up

The September 21 visual revision replaces the rejected text-heavy main view
with symbol nodes and permanent prerequisite paths. Remove node-name/status
paragraphs, the separate activity banner and the details panel; retain optional
hover descriptions. Use coloured node backgrounds and a bright on-node progress
strip for current research, keeping grey unreached icons and silver/gold level
frames. Shared prerequisite buses join at an ampersand to communicate that all
connected predecessors are required. Do not hide unrelated links on hover or
change any dependency, cost, effect or queue control.

The revised installed-CEGUI fixture passes 50,113 checks across nine viewport/UI
scale combinations, including all actual prerequisite edges, mixed prerequisite
completion, non-overlapping square nodes, paths outside symbol interiors,
permanent visibility, on-node progress, retained frames and optional hover help.
All 411 research-rule regressions pass. The same fixture also runs with an actual
Ogre renderer and produces an inspected 1280x960 offscreen preview containing
locked, unlocked, queued, active, silver and gold nodes. The render run passed
49,807 checks before the final 306 mixed-prerequisite assertions were added.
Preview: `build/review-followups/research-visual-graph-preview.png`.
Windows Release compilation and runtime/resource validation pass; the normal
executable is recorded in BUILDING.md. No game was launched, and appearance
acceptance remains with the user. Controls and research rules are unchanged;
no release version, root README or release-changelog update is required.

September 21 rejected presentation: the actual screenshot shows overlapping
same-row bus segments with mixed completion colours, unnamed icons, a faint
current-work symbol and a long description clipped in the global help strip.
Keep research rules and selection semantics unchanged. Add named nodes, explicit
researching/queued/locked states, an always-visible current-research banner and
progress bar, and a wrapped in-window detail panel listing each required item
as ready or missing. Show only the inspected node's direct incoming connections,
with direction arrows and an explicit ALL-required explanation; this removes
ambiguous overlapping unrelated paths without hiding prerequisites from details.
Inspecting changes only presentation, never the pending research queue.
Keep grey unresearched icons and the requested silver/gold upgrade frames.
No version bump or release changelog is needed for this unreleased correction.
The overview keeps neutral connections until an icon is inspected; inspection
isolates that node's incoming paths, with green ready predecessors and amber
missing predecessors, plus downward arrows. Full details remain in the window
after the pointer leaves, including each prerequisite and its completion state.
Labels and compact status badges are separate from the unchanged upgrade frames.

The expanded installed-CEGUI fixture passes 8,884 checks, including actual hover
dispatch, all 27 names, active/idle research, all four completion levels, exact
incoming-edge filtering, retained queue/cast rules and formatted text extents at
800x600, 1280x720 and 1920x1200 with 80%, 100% and 120% UI scale. It initially
found clipped labels at small sizes; the final layout passes those same checks.
Some intermediate native runs were blocked by Windows application control;
the final recorded run executed successfully without changing security settings.
Release compilation and deployment are recorded in BUILDING.md; user visual
acceptance is still required, and the fixture does not launch the game.

The tree currently overlays both Roman level numbers and queue positions on
each button, while the fixed three-column layout never draws dependencies.
`Skill::canBeSkilled` requires every direct prerequisite, not merely one;
connections must represent those actual edges rather than inferred row order.
Keep existing research, queue editing and cast-button availability unchanged.
Replace numeric overlays with unresearched grey icons and level frames (none,
silver, gold at levels 1, 2, 3), keeping queue position/cost in the tooltip and
the existing current/queued state symbols. Reuse the existing layout and
draw non-interactive connections behind its buttons. No save/protocol or version
change is required. The 27 research buttons use a scoped look, with dim grey
tint for level zero and thick proportional silver/gold frames; unrelated buttons
retain their existing look. Tooltips explicitly list all immediate prerequisites.
Connections use the actual dependency lists and remain behind clickable buttons.
All 2,592 installed-CEGUI checks and 411 research-rule checks pass; the cumulative
Release build passes. No manual game session was launched; appearance acceptance
remains with the user. These controls do not change the underlying research queue.

## Exclusive research navigation

The minimap research handler already toggles visibility, but opening the tree
does not close production or other dialogs, and the F10 entry always opens it.
Reuse the existing Escape close dispatcher before opening the tree and route
F10 through the same toggle as the minimap. Closing research continues to cancel
unapplied changes through its existing controller. This client-only correction
does not change save data, packets or the application version.

The installed-CEGUI navigation probe passes 504 checks using real mouse events
at four resolutions and three UI scales: repeated minimap clicks, F10 toggles,
and repeated alternating research/production selection leave only the selected
dialog visible. The 411 research/save/packet regressions also pass, as does
Release compilation. User gameplay acceptance remains pending.

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
