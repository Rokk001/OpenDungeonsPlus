# Project context for future sessions

## Language

Communicate with the user in German.
Write and maintain all project documentation in English.
Use English for Git-related text, including commit messages, pull request titles,
descriptions and review comments.

## Product reference

Dungeon Keeper 2 is the binding reference for all roadmap-driven gameplay,
controls, interface, feedback, visual and audio changes. Read the
[improvement roadmap](docs/development/IMPROVEMENT-ROADMAP.md) before planning or
implementing them. Reproduce evidenced reference behavior; do not invent a modern
alternative or fill missing evidence with assumptions. Preserve completed points
0, 1 and 2; their corrective extensions are 0b, 1b and 2b.

The user explicitly delegated reference interpretation on September 6, 2026:
derive edition-independent behavior and the treatment of additional windows from
the original game, its manual and publisher evidence. Do not ask the user to
choose a reference version or design the treatment of extra windows again.
Research actual differences; preserve fork commands through the corresponding
reference interface flow without claiming that fork-only mechanics are identical.

## Project setup

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

The user has now authorized roadmap items 0b, 1b and 2b as the new work scope,
with a separate branch per item. The active complete fork is now
`feature/dk2-hand-feedback`, following `docs/dk2-reference-baseline` and
`feature/dk2-hud` from the preserved `feature/action-state-feedback` checkpoint
`11c4209e`. The hand branch includes both predecessors and subsequent work; do
not switch back to a predecessor to begin a new task. Build and technical checks
are recorded in the linked feature notes; visual/gameplay acceptance is pending. Read the
[reference baseline](docs/development/DK2-REFERENCE-BASELINE.md),
[HUD specification](docs/development/DK2-HUD-SPEC.md) and
[hand-feedback specification](docs/development/DK2-HAND-FEEDBACK-SPEC.md).
Reference evidence and compatibility decisions must be resolved before dependent
implementation; do not invent the missing details. The earlier prototype stays
preserved in [action feedback](docs/development/ACTION-STATE-FEEDBACK.md); its
permanent-label design is not the target for the new work.

The separate lighting branch is `fix/room-lighting`, based on complete hand-tool
checkpoint `65506edf`, which already retains shadow closure `ba245257`.
It adds local visible-room illumination and corrects custom material light
accumulation and ambient colour. All 18 focused room checks, the existing
shadow/falloff regressions and the Release build pass; the prepared executable
is dated September 6 at 19:38:14 in BUILDING.md. Manual visual acceptance remains
with the user. Preserve its shader/material and renderer changes while the
authorized camera-control and map-navigation tasks proceed on separate branches.
The shared checkout/index remain on the shadow branch; no new push is authorized.

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
