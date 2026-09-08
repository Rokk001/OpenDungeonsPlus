# Project context for future sessions

## Mandatory contribution scope

Each pull request must deliver one coherent, independently reviewable product
outcome. Include the implementation, its required enabling work, tests and any
corrections needed to make that outcome meet its acceptance criteria. Do not
open separate pull requests for internal implementation steps, individual
commits or prerequisites that have no useful standalone result.

Keep unrelated features and unrelated bug fixes in separate branches and pull
requests. Do not mix an independent bug fix into a feature contribution. A fix
that only completes an unmerged feature belongs to that feature's pull request;
a pre-existing or separately releasable bug requires its own pull request.
Preserve the complete local fork while preparing focused contribution branches.

Before publishing, verify that the outcome is complete, review its dependency
and issue overlap, exclude private fork material and describe validation limits.
Internal documentation and agent rules must not receive upstream pull requests.

## Current workspace checkpoint

The user requested priority commits for all pending project changes. The complete
functional stack now includes minimap stacking `232ac515` and the accepted-marking/
unmarking-animation correction `711c694e`. Pending fork-only development notes,
the already requested private planning relocation and an existing line break are
preserved on `chore/fork-checkpoint`. The normal checkout/index are aligned to
that complete checkpoint without replacing working files; earlier instructions
to keep the checkout on the old shadow branch describe the preceding shared
work phase and are superseded by this checkpoint. Continue from this current
complete state plus every newer edit, preserving each separate functional branch.
The user's `.gitignore` is deliberately left outside these commits and unchanged.
Private planning files remain under ignored `docs/internal/`; do not delete them
or recreate the old public copies. No push or upstream PR was requested.

The hand-animation follow-up now also animates removing digging marks; the user
accepted the marking strike and reported its absence on unmarking. Removing the
single playback guard passes all 781 release/selection checks (two failures
before), Release compilation, runtime preparation and headless resource checks.
The executable is dated September 6 at 22:31:33 in BUILDING.md. Preserve current
parallel minimap stacking work; the unmarking retest remains with the user.

The latest hand follow-up is `feature/hand-dig-animation`, based on complete map
checkpoint `a4d1b0f5`, retaining held display `6b248742` and all newer local work.
It adds a downward closed-grip strike only after confirmed wall marking; 876
renderer and 781 release/selection checks pass, as do Release/runtime/resource
checks. The executable is dated September 6 at 22:21:21 in BUILDING.md.
See [the hand strike note](docs/development/HAND-DIG-ANIMATION.md). The user
accepted the static grip; the new animation's game acceptance remains pending.
Preserve the shared shadow checkout and its normal index; use an isolated index
for this branch. No push or game launch was made. The broader roadmap remains open.

## Language

Communicate with the user in German.
Write and maintain all project documentation in English.
Use English for Git-related text, including commit messages, pull request titles,
descriptions and review comments.

## User status-reporting and rule-persistence preferences

Maintain `docs/internal/OPEN-TASKS-OVERVIEW.md` as the concise, current task
overview throughout implementation. The user explicitly approved this workflow.
Use only the two-column task/status table, with short status labels.
Mark the currently worked task with `RUNNING` in its existing status cell.
Do not add a heading, introductory text, extra marker column, long explanations,
commit IDs or verification details to this overview. Keep the task order stable.
Update the marker when work changes or pauses; do not leave a stale active marker.
Reflect accepted completion and canceled work promptly instead of reopening
them or inventing additional verification tasks. Keep detailed evidence in the
linked internal task notes and this overview outside functional Git contributions.

The user explicitly requires progress reports as a table with one task and its
status per row, without replacing the table with prose. When asked for the status
of open tasks, include only open tasks; omit completed or accepted tasks.

Whenever the user provides a new working rule, save it during that same turn in
the relevant project instructions and the permitted cross-session memory notes;
do not merely acknowledge it in chat. Verify the write before claiming it was
saved. Keep these user preferences subject to higher-priority runtime instructions.

## Product specifications and documentation boundaries

For roadmap behavior and presentation questions, follow the sole original
reference specified in `docs/internal/README.md`; the user has delegated these
decisions to that reference. Research missing details independently instead of
asking the user to choose an alternative or whether to retain a competing fork
interaction. Missing evidence is a research gap, not a pending user preference.
Apply reference-required changes within the requested scope while preserving
unrelated completed work; record named comparisons only in the internal area.

Use the approved specifications in the [local planning index](docs/internal/README.md)
for roadmap-driven work and preserve completed items. Keep detailed reference
comparisons, private product direction and associated evidence under `docs/internal/`.
Use neutral functional descriptions in public documentation, new branch names,
commit messages and pull requests; do not publish named reference comparisons
or clone positioning. The user maintains the ignore rules for the internal area.
Do not rewrite existing Git history without an explicit request.

## Project setup

When the user defines a new goal, identify its functional features and create one
separate work branch per feature before implementation begins. Perform the
implementation inside its assigned branch from the latest complete fork state.
Do not implement new goal work in a shared checkout and split it into branches
afterward.

Before implementing any request, inspect the current repository for an existing
solution and trace how it works, including its entry points, storage paths and
related documentation. Do not infer that a feature is missing from the request.
Reuse the existing implementation when it already satisfies the requirement;
otherwise identify the exact gap and extend it with the smallest necessary
change. Introduce a separate implementation only after establishing why reuse
or extension cannot meet the request. Document the finding and the chosen path
in the relevant development note before making dependent changes.

Always implement new requirements on the user's latest complete fork state,
including all newer fork commits, local work and project documentation. Never
start implementation work directly from `upstream` unless the user explicitly
overrides this rule. Use `upstream` only to compare changes and to assemble a
separate contribution branch after the fork implementation has been completed
and reviewed.

Before working on this project, read:

1. [Windows environment and current status](docs/development/WINDOWS-DEV-SETUP.md).
2. [Configure and build commands](docs/development/BUILDING.md).
3. [Development documentation index](docs/development/README.md); follow the
   workflow and task notes when relevant to the request.

The latest hand-display work is `feature/held-creature-display`, based on complete
map checkpoint `6310df83` (retaining camera `abc19866`) and `fix/creature-portrait-clipping`
prerequisite. It preserves newer parallel map-navigation edits in the shared
checkout. The renderer and interface changes pass 77 and 3,535 focused checks,
227 rotation/drop regression checks, 33 portrait renders and twelve grip-layer
comparisons. Release compilation, runtime preparation and resource checks pass;
the prepared executable is dated September 6 at 21:30:54 in BUILDING.md. User
gameplay acceptance remains pending; the static tool grip was separately
accepted. See [held-creature display](docs/development/HELD-CREATURE-DISPLAY.md).
Use isolated indexes to commit these separate functional branches without
switching the shared shadow checkout or changing its normal index. Preserve
all apparently modified/untracked cumulative feature files and newer map edits.
The suggested wall-click swing is a separate follow-up; inspect the authored
animations and current wall-selection path before any implementation.

The preceding combined work is `fix/windows-incremental-build`, checkpoint `c1937944`
after merge `e1276f81`,
retaining hand-grip checkpoint `9beb2ba8` and camera checkpoint `8c1410c3`.
The user's subsequent 20:06 crash revealed mismatched virtual-call layouts in
the incrementally built executable: an event notice was dispatched to chat.
The obsolete MSVC minimal-rebuild option is now disabled, all 248 translation
units rebuilt, and both linked-binary dispatch checks and runtime resource checks
pass; see [the diagnosis](docs/development/WINDOWS-INCREMENTAL-BUILD.md).
Keep shared game builds sequential across sessions; preserve the current local
camera-reset correction and every other newer edit. The normal shared checkout
and index remain unchanged. The prepared executable is dated September 6 at
20:30:04 in BUILDING.md; user startup and game acceptance remain pending.

The preceding hand work is on `fix/hand-tool-grip`, based on merge `7d534b4e`,
which preserves picker-count correction `505cbf97`, separate hand-orientation
checkpoint `efa8fa5d` and parallel room lighting `0c7d6234`. The isolated grip
commit changes the digging wrist, tool attachment and grip-only material,
with 94 focused checks passing with and without shadows and six render-layer
occlusion comparisons passing. Eleven other-pose images remain identical.
The Release executable is dated September 6 at 20:04:49 in BUILDING.md and also
contains current parallel camera work. Preserve that newer local work; it is
owned by `fix/camera-controls`, not the hand task. The shared checkout remains
on `fix/shadow-coverage`, and the normal index is untouched. Apparently modified
or untracked files on that checkout may already be committed on the feature
stack and must not be discarded. No push or game launch was made; user visual
acceptance and the remaining roadmap evidence are still open. See
[the grip correction](docs/development/HAND-TOOL-GRIP.md) and continue from this
complete combined state plus every newer local or committed change.

The creature-panel work branch is `feature/creature-panel`, checkpoint `d892374c`,
retaining accepted Escape checkpoint `2d3e79dc`, all earlier fork work and local
documentation, and the parallel shadow checkpoint `99e80b2d` via merge `29e4b4b1`.
The panel's full mood and activity transmission prerequisites are implemented with optional
connection negotiation. Per-type portraits, four views, worker counts and pickup/focus
controls are now connected, using an owner-only population snapshot. The focused
packet/activity probe passes 1,117 checks, aggregate data 77, and real Ogre/CEGUI
UI/scaling 830; gameplay/network acceptance remains scoped in
[the creature panel note](docs/development/CREATURE-PANEL.md). Release compilation
and runtime preparation pass; the latest executable is the September 6, 16:39:18
build recorded in BUILDING.md, including the separate shadow checkpoint `99e80b2d`.
Portrait checkpoint `3de2e020` was committed with an isolated index after another
session switched the shared checkout to `fix/shadow-coverage` on September 6 at
15:45. The normal checkout and index were not switched or reset. Its working files
still contain the portrait changes, including two files shown as untracked relative
to the shadow branch. They are committed on `feature/creature-panel`; do not discard
them or mix them into the shadow task. Verify both current branches before further
Git operations and preserve the parallel task's work. The panel integration was
also committed using an isolated index; the normal index and shared checkout
remain on `fix/shadow-coverage`. Its apparently untracked panel/portrait source
files are committed on `feature/creature-panel` and must not be discarded.
The subsequent `fix/quit-dialog-layout` checkpoint `6eeb4885` retains that complete
panel/shadow baseline. It changes only two horizontal layout areas; 260 CEGUI
checks and an isolated rendered preview pass. Its XML and technical note also
remain as local changes relative to the shared shadow checkout. Do not discard
them or return to an older branch to begin the next task. Additional material/
lighting edits currently belong to the parallel session and must be preserved.
The subsequent `feature/creature-level-selection` checkpoint `ed56e5d2` preserves
both the dialog/panel work and parallel lighting checkpoint `fe86bf03` via merge
`85674960`. Portrait/count shortcuts select the highest/lowest eligible level;
847 panel checks, 21 OIS and 324 SFML keyboard checks, the Release build and
runtime preparation pass. Its executable is the September 6, 17:02:57 build in
BUILDING.md. This commit also used an isolated index and did not switch the
shared checkout. Continue from this combined checkpoint for subsequent work.
The preceding combined checkpoint is `fix/event-message-paths` at `8fcfde02`,
which adds only literal event-text escaping and its technical note on top of
`ed56e5d2`. All 504 installed-parser checks and the Windows Release build pass;
the prepared executable is the September 6, 17:18:02 build in BUILDING.md.
This commit also preserves the shared checkout/index. Manual confirmation and
the broader roadmap gates remain open; do not discard apparently untracked
files that are already committed on the feature stack.
The preceding combined checkpoint is `fix/hand-rotation` at `c245acfa`, directly
after `8fcfde02`. Rotation reuses the existing hand layout, and drop request/reply
identities keep selection consistent despite intervening input. All 227 focused
checks and the Release build pass; the prepared executable is the September 6,
17:34:49 build in BUILDING.md. The isolated commit preserves the shared shadow
checkout/index. The local RenderManager, Player, game/editor and network changes
belong to this hand correction; preserve them alongside the parallel task.
Manual game/multiplayer acceptance and the remaining roadmap evidence are open.
The preceding combined checkpoint is `feature/entity-query` at `a0d0335a`, directly
after `c245acfa`. A minimap Query button enters selectable creature inspection,
reusing the middle-click statistics target and window paths. All 56 controller
checks, 3,563 installed HUD/layout checks, Release compilation and runtime
preparation pass; the prepared executable is dated September 6, 17:57:58 in
BUILDING.md. This is the creature portion of the information tool; trap range
and user game acceptance remain open. See
[entity information selection](docs/development/ENTITY-QUERY.md). The isolated
commit preserved the shared shadow checkout/index. Query changes in GameMode,
PlayerSelection, SkillManager and ModeGame.layout belong to this task; retain
them along with the earlier feature stack and parallel work. No push was made.
The preceding combined checkpoint is `feature/contextual-selling` at `0f4d2404`,
directly after `a0d0335a`. A common minimap Sell control uses the existing room/
trap validators with exactly the pointed tile; separate area-sale commands and
server rules remain unchanged. All 70 sale/packet checks, 3,643 installed HUD
checks and 56 query regression checks pass, with Release/runtime preparation.
The executable is dated September 6, 18:16:46 in BUILDING.md. See
[selling from the minimap](docs/development/CONTEXTUAL-SELLING.md). Manual
sale/refund acceptance, trap-query range, minimap zoom and broader roadmap
evidence remain open. The isolated commit preserved the shared shadow checkout
and normal index. Preserve its GameMode, selection, skill mapping, room/trap
validator and layout edits alongside all preceding and parallel work. No push
was made; this checkpoint is retained by the subsequent work below.
The preceding combined checkpoint is `fix/navigation-hand-feedback` at `84f9eae3`,
preserving `0f4d2404` and parallel shadow documentation closure `09d7e5e1`
through merge `5e4da30e`. Its single pose-condition correction reuses the existing
pointing hand over GUI surfaces. All 178 controller checks pass (24 failed before),
as do Release compilation and runtime preparation; the executable is dated
September 6, 18:39:33 in BUILDING.md. See
[navigation hand feedback](docs/development/NAVIGATION-HAND-FEEDBACK.md).
The isolated commit changes only GameMode, its README description and its task
note; it preserves the shared shadow checkout and normal index. The working
files still look modified/untracked relative to that checkout and must not be
discarded. Manual navigation/pose acceptance and the remaining roadmap gaps
remain open. No push was made; this checkpoint is retained below.
The preceding combined checkpoint is `fix/hand-tool-material` at `65506edf`,
preserving `84f9eae3` and parallel shadow contribution documentation `ba245257`
through merge `199e20ab`. Its isolated commit changes only the procedural tool's
texture coordinates, a separate material script and the task note. All 521
geometry/material checks and six isolated GL3Plus views pass; Release compilation
and runtime preparation pass. The ready executable is dated September 6,
18:58:11 in BUILDING.md, replacing the staged build after the user closed the
game. See [textured hand tool](docs/development/HAND-TOOL-MATERIAL.md).
The shared checkout remains on `fix/shadow-coverage`, and its normal index is
untouched. Preserve the apparently untracked material/note and all earlier
feature files. No push or game launch was made. Manual appearance and the full
remaining roadmap scope remain open; continue from this latest combined state.
The subsequent camera branch is `fix/camera-controls`, based on the complete
room-lighting checkpoint `0c7d6234`. It adds continuous camera input, default
view shortcuts and three persistent user orientations. All 278 camera, 84 GUI,
63 Escape and 227 hand-rotation checks pass, together with the Release build
and runtime preparation. The prepared executable is the September 6, 20:08:51
build in BUILDING.md. Manual acceptance remains pending; the shared checkout
and index are preserved. Full-map navigation follows on its own branch.

The separate lighting branch is `fix/room-lighting`, based on complete hand-tool
checkpoint `65506edf`, which already retains shadow closure `ba245257`.
It adds local visible-room illumination and corrects custom material light
accumulation and ambient colour. All 18 focused room checks, the existing
shadow/falloff regressions and the Release build pass; the prepared executable
is dated September 6 at 19:38:14 in BUILDING.md. Manual visual acceptance remains
with the user. Preserve its shader/material and renderer changes while the
authorized camera-control and map-navigation tasks proceed on separate branches.
The shared checkout/index remain on the shadow branch; no new push is authorized.

The user confirmed the three reported HUD regressions are fixed; subsequent
screenshots show visible wall outlines during hover and dragging. The reported
F10/Escape issue and the broader Escape navigation correction are confirmed fixed
by the user. The latter also passes 63 headless checks and the Release build.
Pickup-label verification and the broader gameplay/visual matrix
remain pending. Read the current build notes before using an older executable hash.
Read the [local planning index](docs/internal/README.md) for the detailed task
specifications, evidence, branch history and remaining acceptance requirements.
Never return to an older checkpoint to begin a new task.

Windows development is organized on `feature/windows-support` in this fork.
The related work is split into a local branch stack: `feature/windows-support`,
`fix/dynamic-shadows`, `fix/settings-option-duplicates`, `feature/live-settings`,
`feature/progressive-edge-scrolling`, `docs/improvement-roadmap`, then
`feature/gui-scaling`. Continue each task from the latest complete fork state; see
[live settings and verification](docs/development/LIVE-SETTINGS.md).
Read the current setup in [the contribution workflow](docs/development/CONTRIBUTING-WORKFLOW.md)
before Git operations: `origin` is the fork and `upstream` is the original project.
Preserve the existing default branch; continue each task on its own work branch.
The work branch includes local notes and is not the final upstream PR branch;
assemble that separate contribution branch later using only the reviewed,
reusable changes.
Do not push without explicit user authorization.

## Pull requests: one work branch per contribution

Never combine multiple work branches or unrelated tasks into one pull request.
Create pull requests only for functional implementations: features and bug fixes.
Never submit a documentation-only PR. Internal development notes, agent rules and
the product improvement roadmap remain in the fork, outside upstream contributions.
Create a separate pull request for each completed implementation branch and explicitly
link prerequisite PRs. Never present multiple tasks as one combined contribution.
Completed contributions should be ready for review when the user requests
finalization; dependency alone is not a reason to leave them as drafts.
For branches that build on earlier work, disclose the cumulative comparison and
link the individual changes against the preceding work branch. Before merging,
verify that the remaining diff contains only the PR's own functional contribution
and excludes internal documentation; merge prerequisites separately first.
Do not silently rewrite accepted implementation work merely to rearrange PRs;
preserve the user's complete working branch and all local changes.
Recovery/backup branches are not additional contributions, and unfinished work
must not be included in a PR for a completed task.
Record relevant issue coverage separately in each PR and only use automatic
issue-closing keywords when the entire issue is demonstrably resolved.

## Installed development environment

The Windows prerequisites are already installed in `C:\Users\mario\od-deps`;
their sources, binaries and logs deliberately live outside the repository.
The maintained instructions and scripts live in this repository under
`docs/development/` and `scripts/win32/`.
Do not rely on the old copies in `build/` or `od-deps/setup-scripts/`.

At the verified state on 2026-09-05, dependency builds, game CMake configuration
and both Windows x64 game builds (Release and Debug) succeeded.
User startup attempts exposed a Windows resource-path bug; both binaries now
include its correction. A subsequent Release run loaded the main-menu scene and
shut down normally without the earlier loading errors; the user subsequently
confirmed that the Release executable starts without errors.
That confirmation predates enabling dynamic shadows: a later startup failure was
traced to OGRE's internal shadow programs being registered only in Graphics.
The resource template now also exposes Media/Main through OgreInternal while
retaining Graphics access for shader includes; the headless OGRE resource test
fails before and passes after this correction, and the user's 14:52 run reached
the main menu with shadows enabled. That run later failed while entering
TestLegacyNoScripts.level. Added exception logging captured the cause during the
user's 15:05 reproduction: automatic additive illumination splitting removed
DirtInstanced's fragment shader, which GL3Plus requires. RenderManager now uses
integrated additive texture shadows to retain the custom shader passes. Release
and Debug rebuilt successfully; the isolated OGRE pass test fails with splitting
and passes without it. The user must still retest the map and shadow appearance
with the rebuilt executable; check the latest evidence in the startup notes.
Read [startup failures and verification](docs/development/WINDOWS-STARTUP-FIXES.md)
before investigating further startup issues; broader gameplay tests and packaging
remain unverified.
The Release executable now has its runtime DLLs staged beside it for direct
File Explorer startup; the configuration script maintains this through
`scripts/win32/prepare-windows-runtime.ps1`. Python's standard library and OGRE
media still use the external installation. Read BUILDING.md for the static
verification results and the remaining Debug runtime/plugin limitations.
Read the [Windows build fixes](docs/development/WINDOWS-BUILD-FIXES.md) for the four
diagnosed failures and verification logs; the CEGUI source now includes a
repository-managed compatibility patch applied by its installation script.
Read the current status document and check the actual files before making claims.
Do not reinstall dependencies or switch versions just because a new session starts.
Use the repository's environment helper and configuration script; the scripts
currently target Mario's Windows installation, with paths recorded in the docs.

Keep changes within the user's request and preserve existing work.
Do not read `.env` or other secret files.
Manual game tests, QA and visual acceptance are performed by the user.
When changing setup paths, versions, commands or verified build status, update the
linked documentation in the same task so the next session has the current state.
