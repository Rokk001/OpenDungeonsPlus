# Development documentation

Here we collect guides and findings on contributing to OpenDungeonsPlus,
with one Markdown file per topic.

For a new session, first read [Windows development environment](WINDOWS-DEV-SETUP.md)
and [Configuring and compiling](BUILDING.md); the entry point for agents
is also recorded in [AGENTS.md](../../AGENTS.md) at the project root.

## Available guides

- [Workshop order scheduling](WORKSHOP-ORDER-SCHEDULING.md): production order,
  save-order preservation and focused regression checks.

- [Creature portrait export](../../tools/portraits/README.md): tracked tooling to
  export and verify current creature portraits for asset work.

- [Minimap navigation stacking](MINIMAP-NAVIGATION-LAYER.md): preserving access
  to the corner controls after clicking the minimap.
- [Map navigation](MAP-NAVIGATION.md): full-map controls, pointer detail, minimap zoom,
  tile colours, focus shortcuts and verification limits.
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
- [Windows incremental build consistency](WINDOWS-INCREMENTAL-BUILD.md): a
  startup crash caused by incompatible virtual-call layouts and the verified
  complete rebuild with obsolete minimal rebuild disabled.
- [Windows startup errors and fixes](WINDOWS-STARTUP-FIXES.md): actual startup
  failures, runtime preparation, resource-path correction and outstanding verification.
- [Windows settings fixes](WINDOWS-SETTINGS-FIXES.md): duplicate colour-depth
  choices, their cause and verification status.
- [Live settings](LIVE-SETTINGS.md): applying settings without restarting,
  the fullscreen navigation report and completed Windows verification.
- [Local planning documentation](../internal/README.md): private roadmap,
  specifications and comparison evidence; available only in the local checkout.
- [Wall hover outline](WALL-HOVER-OUTLINE.md): model-derived preview height,
  cause, focused geometry checks and Windows build evidence.
- [Pickup target descriptions](PICKUP-TARGET-DESCRIPTION.md): readable chicken
  and gold labels instead of internal identifiers, with build evidence.
- [Hand rotation and selected-object drops](HAND-ROTATION.md): consistent held
  spacing and matching drop identities across client/server requests and replies.
- [Hand feedback over navigation](NAVIGATION-HAND-FEEDBACK.md): pointing over
  interface controls and restoring the current world pose on exit.
- [Textured hand tool](HAND-TOOL-MATERIAL.md): reusing existing wood/metal
  textures with preserved geometry and isolated render verification.
- [Hand orientation](HAND-ORIENTATION.md): rightward spatial inclination with
  preserved cursor coordinates and held-object placement.
- [Hand tool grip](HAND-TOOL-GRIP.md): a shaft enclosed by the fingers, an upright
  tool head and pose-specific depth occlusion, with render regression evidence.
- [Downward hand strike](HAND-DIG-ANIMATION.md): closed-grip motion on confirmed
  wall marking, input guards, existing animation reuse and verification limits.
- [Held-creature display](HELD-CREATURE-DISPLAY.md): one gripped creature and
  ordered square portraits, with transform, lifecycle and input verification.
- [Creature portrait clipping](CREATURE-PORTRAIT-CLIPPING.md): resetting leaked
  interface clipping before generating a cached portrait.
- [Closing Options with Escape](OPTIONS-ESCAPE.md): keyboard priority,
  retained confirmation cancellation and focused verification.
- [Escape navigation](ESCAPE-NAVIGATION.md): closing one dialog or returning
  from front-end screens through the existing cancel/back handlers.
- [Exit confirmation layout](QUIT-DIALOG-LAYOUT.md): complete title/replay text,
  scaled bounds and control-hit verification.
- [Community exit page](COMMUNITY-EXIT-PAGE.md): explicit Discord and close
  actions on the final community screen.
- [Literal paths in event messages](EVENT-MESSAGE-PATHS.md): preserving path
  separators and bracketed names alongside the existing notice icon and colour.
- [Save request payload](SAVE-REQUEST-PAYLOAD.md): matching three default-save
  callers to the existing server packet format, with before/after evidence.
- [Creature panel](CREATURE-PANEL.md): per-type portraits, activity/mood views,
  population transmission, pickup/focus controls and verification limits.
- [Creature health and needs](CREATURE-HEALTH-AND-NEEDS.md): persistent
  owner-coloured health rings with centred need and mood states over the
  existing autonomous behaviour paths.
- [Worker creation effect](WORKER-CREATION-EFFECT.md): a short networked magical
  spark burst for workers created by the summon-worker spell.
- [Creature selection by level](CREATURE-LEVEL-SELECTION.md): highest/lowest
  eligible selection through the existing keyboard and pickup paths.
- [Creature picker counts](CREATURE-PICKER-COUNTS.md): reducing counts after
  pickup, retaining empty type entries and restoring counts after drops.
- [Entity information selection](ENTITY-QUERY.md): selectable creature inspection,
  existing statistics-window reuse and the outstanding trap-range prerequisite.
- [Selling from the minimap](CONTEXTUAL-SELLING.md): one entry point for room,
  trap and door sales, reusing existing prices, permissions and requests.
- [Missile wall crash investigation](MISSILE-WALL-CRASH.md): existing null-tile
  correction, before/after regression evidence and limits of the Linux traces.
- [Shadow coverage](SHADOW-COVERAGE.md): PR #48's missing creature shadows,
  ground projection, receiver and cursor-light corrections, isolated rendering
  evidence, user screenshot review and local branch closure.
- [Camera controls](CAMERA-CONTROLS.md): continuous input, centred view changes,
  three persistent user orientations and keyboard/pointer/GUI verification.
- [Main-menu scene framing](MAIN-MENU-FRAMING.md): preserving the authored scene
  composition across standard, widescreen and ultrawide viewports.
- [Navigation appearance](NAVIGATION-APPEARANCE.md): a framed circular minimap
  and action-specific corner symbols with unchanged navigation behavior.
- [Room lighting](ROOM-LIGHTING.md): local visible-room illumination, overlapping
  light contributions, colour readability and rendering/lifecycle verification.
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
