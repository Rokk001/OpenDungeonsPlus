# Development documentation

Here we collect guides and findings on contributing to OpenDungeonsPlus,
with one Markdown file per topic.

For a new session, first read [Windows development environment](WINDOWS-DEV-SETUP.md)
and [Configuring and compiling](BUILDING.md); the entry point for agents
is also recorded in [AGENTS.md](../../AGENTS.md) at the project root.

## Available guides

- [Contributing to the original project](CONTRIBUTING-WORKFLOW.md): fork, synchronization,
  the configured Windows work branch, separate commits and the path to a later
  pull request to the original project.
- [Tasks and division of work](TASKS.md): assessment so far of autonomous
  implementation, participation in testing and the suggested starting point.
- [Windows development environment](WINDOWS-DEV-SETUP.md): installed versions,
  exact locations, connections to the project and verified status.
- [Configuring and compiling](BUILDING.md): load the environment, run CMake,
  build Release/Debug and find logs.
- [Windows build errors and fixes](WINDOWS-BUILD-FIXES.md): confirmed
  compiler errors, their causes, targeted fixes and build evidence.
- [Windows startup errors and fixes](WINDOWS-STARTUP-FIXES.md): actual startup
  failures, runtime preparation, resource-path correction and outstanding verification.
- [Windows settings fixes](WINDOWS-SETTINGS-FIXES.md): duplicate colour-depth
  choices, their cause and verification status.
- [Live settings](LIVE-SETTINGS.md): applying settings without restarting,
  the fullscreen navigation report and completed Windows verification.
- [Product improvement roadmap](IMPROVEMENT-ROADMAP.md): binding Dungeon Keeper 2
  reference, preserved points 0–2, corrective extensions 0b/1b/2b, evidence and
  acceptance requirements, and coordination with upstream issues and pull requests.
- [Reference baseline (0b)](DK2-REFERENCE-BASELINE.md): current authorization,
  separate branch sequence, inspected sources, code findings and unresolved evidence.
- [HUD specification (1b)](DK2-HUD-SPEC.md): existing-function inventory,
  measured composition, minimap resize correction, interface boundaries and
  outstanding reference acceptance scenarios.
- [Hand-feedback specification (2b)](DK2-HAND-FEEDBACK-SPEC.md): input-state
  scenarios, hand/icon/outline implementation, regenerated checks and mechanics
  differences; the latest complete fork is on this feature branch.
- [Shadow coverage](SHADOW-COVERAGE.md): PR #48's missing creature shadows,
  ground projection, receiver and cursor-light corrections, isolated rendering
  evidence, user screenshot review and local branch closure.
- [GUI scaling](GUI-SCALING.md): scale policy, implementation details,
  automated checks and the required manual verification matrix.
- [Action state and target feedback](ACTION-STATE-FEEDBACK.md): current action,
  selected buttons, valid targets, failure reasons, build/probe evidence and the
  prototype checkpoint stopped by the user pending a redesigned plan.
- [Restoring prerequisites](WINDOWS-PREREQUISITES.md): sources,
  checksums, installation scripts, order and resolved installation problems.

## Adding further notes

Add new files here as needed and link them above, for example:

- `DEBUGGING.md`: traceable error analyses and solutions.
- `ARCHITECTURE-NOTES.md`: findings about the existing code and its relationships.
- `VISUAL-DIRECTION.md`: approved visual targets and asset constraints.

For technical findings, record the affected code, verification steps and
open questions; label statements that have not yet been verified accordingly.

This collection is internal documentation for our own fork and is not an upstream
contribution. Pull requests are reserved for functional implementations; never
create a documentation-only PR for these notes or the roadmap.
