# HUD reference specification (roadmap 1b)

## Status and dependency

Implemented composition on `feature/dk2-hud`, following the original manual and
publisher captures recorded in [0b](DK2-REFERENCE-BASELINE.md). The user delegated
reference interpretation; no edition or additional-window question is pending.
Build and headless results are recorded below. Visual/gameplay acceptance and
the explicitly listed fidelity differences remain open.

## Existing functions that must remain reachable

| Scenario | Preserved baseline UI / implementation | Reference comparison inventory |
| --- | --- | --- |
| HUD-01 resources | Gold, mana, territory and creature-pool displays in `ModeGame.layout`. | Reference placement, appearance, units, update behavior and counterpart for each value. |
| HUD-02 categories | `MainTabControl` and the four imported tab layouts. | R2 category structure and runtime order, selection, visibility, scrolling and resizing. |
| HUD-03 rooms | `WindowTabRooms.layout`: sell plus 16 room actions, including portals and wave portals. | Map each action to its reference counterpart; keep unmatched functions visible in the compatibility decision record. |
| HUD-04 traps | `WindowTabTraps.layout`: sell, cannon, spike, boulder and wooden-door actions. | Identify the reference item for each action and its availability/progress presentation. |
| HUD-05 spells | `WindowTabSpells.layout`: ten actions with progress children. | Individual reference spell mapping, icon states and what each progress indicator actually represents. |
| HUD-06 creatures | `WindowTabCreatures.layout`: worker and fighter pickup commands. | Reference selection categories, counts and filtering, including which current game data can supply them. |
| HUD-07 minimap | `MiniMap` in `ModeGame.layout`; currently a lower-right rectangle. | Measured map frame, shape and adjacent controls; navigation behavior stays in its own roadmap task unless required by the changed control. |
| HUD-08 objectives | HUD button, options-menu button and `WindowObjectives.layout`. | R2 counterpart and actual presentation/close behavior. |
| HUD-09 events | `WindowEvent.layout` and dynamically updated event text. | Event surfaces and opening/dismissal states; coordinate later event behavior with roadmap point 6. |
| HUD-10 help | HUD help button and `WindowHelp.layout`. | Record whether the current reference has a corresponding surface; retain access until compatibility is resolved. |
| HUD-11 research | HUD/options access plus `WindowSkillTree.layout` and its pending-selection controls. | Resolve the existing research interface's place in the reference-oriented UI; no silent removal or research-rule rewrite. |
| HUD-12 player options | `WindowPlayerSettings.layout`, seat information and knockout-creature option. | Resolve treatment of this existing additional window. |
| HUD-13 game options | `WindowGameOptions.layout`: objectives, research, save, load, settings, quit game and exit. | Map each command and its enabled state to the reference options flow. |
| HUD-14 settings | `WindowSettings.layout`, `SettingsWindow.cpp`: video, audio, input and game pages, including dynamic renderer options. | Compare organization and appearance while preserving live display changes, scale presets, settings persistence and cancel behavior. |
| HUD-15 confirmations | Quit and settings-confirmation layouts. | Reference presentation and focus/input behavior for the equivalent transition. |
| HUD-16 chat and statistics | `WindowChat.layout`; entity statistics opened through game input. | Preserve existing access and explicitly resolve unmatched surfaces before changing them. |
| HUD-17 tooltip/focus states | `OD.looknfeel`, `ODSkin.imageset` and CEGUI tooltip handling. | Capture hover delay, placement, typography, enabled/disabled/pressed/selected states and dismissal. |

This mapping is a work inventory: a same-looking name does not certify equivalent
gameplay. Inspect each action's handler before changing what its button does.

## Geometry evidence and scaling

Use one identified whole-viewport reference capture per scenario; record its
resolution and UI state. For each affected element, record the visible bounds,
interactive bounds, anchor, ordering and relation to the map. Store the reference
coordinates and the derivation of the fork's design coordinates together.

The following inventory was used to collect evidence; the measured values and
implemented decisions are now in 0b and the concrete contract below:

- Complete control-panel height and the area reserved for the world.
- Minimap dimensions, clipping shape and adjacent control offsets.
- Category/button sizes, rows, spacing and overflow behavior.
- Resource-counter locations and digit/icon metrics.
- Window, title, content and footer proportions.
- Tooltip bounds, delay and dismissal behavior.
- The correct placement of preserved additional fork functions.

Keep the existing automatic scale plus 80-120% user scale and the corrected font,
clipping and pointer paths. Measure reference proportions first; the existing
1024x768 layout design area is a technical scaling basis, not evidence of the
reference game's layout. Do not silently replace it with a new scale policy.

## Interface boundary contract with 2b

For each HUD/window state, identify exactly which displayed area consumes input,
which transparent area passes input to the world, which surface clips children
and which element owns hover/pressed state. The hand and its action indicator must
use the same display coordinates as hit testing after resize and scale changes.

Reference behavior for right-click over a category, button or open window must
be captured separately from world cancellation. Do not route every right-click
to the same action based only on a general manual rule.

## Acceptance evidence

For HUD-01 through HUD-17, link a reference capture, the corresponding fork
capture and the result of the matching input sequence. Record any unresolved
counterpart explicitly; do not mark a row passed from layout XML alone.

Verify affected layouts at the existing geometry-probe sizes (800x600, 1280x720,
1920x1080, 3440x1440 and 3840x2160), including successive 80%, 100%, 120%, 100%
changes, and verify actual supported settings windows against their own matrix.
Preserve the live resize/fullscreen and clipping corrections. Build checks and
headless bounds tests support the user comparison; they do not replace it.

The build and geometry results below establish technical checks, not a passed
visual comparison of all seventeen scenarios.

## Implementation checkpoint, September 6, 2026

The initial HUD implementation is on `feature/dk2-hud`, based on `8141b5f1`.
The bottom-left circular map, category order, measured panel geometry, Options
access for additional functions and actual pickup counts are implemented.
The existing renderer choices remain selectable; editor map presentation stays
rectangular. A circular map rejects corner clicks before camera navigation.
Tab text padding now follows the same scale as tab height and icon sizes.

The regenerated headless CEGUI probe passes at 800x600, 1280x720, 1920x1080,
3440x1440 and 3840x2160 with 80%, 100%, 120%, 100% scale transitions. It loads
the actual layouts and checks action/category/utility hit targets, bounds,
collapsed-panel input and access to all Options commands. Evidence is in
`build/windows/dk2-hud-probe-results.log`; the initial Release compilation passes
in `build/windows/dk2-hud-build.log`. The subsequent clean Release build also
passes in `build/windows/dk2-hud-clean-build.log`; runtime preparation succeeded.
No game was launched and no new user acceptance is claimed.

Remaining differences and acceptance work for HUD-01..17: detailed
creature portrait/job/mood controls, final reference artwork, minimap corner
actions and complete popup visual comparison still need their own evidence and
implementation checks. The hand branch replaces the old action panel; it remains
in this intermediate checkpoint so the preserved prototype can still execute.
Version remains 0.7.1 because this is development work, not a release; README and
these development notes describe the implemented controls. No changelog exists
in the current checkout, and no upstream issue is claimed closed by this work.

## Concrete implementation contract

The decision record in 0b resolves reference interpretation and extra-window
placement under the user's explicit delegation.
Use gallery captures 2/3/5/6/8/9 and the measured design coordinates in 0b.

- HUD-01: mana, then gold at the upper left; context information occupies the
  remaining top strip. Preserve territory and creature-pool values in the player
  information surface instead of competing with the primary reference counters.
- HUD-02: Creatures, Rooms, Spells, Workshop; square icon categories at the top
  of the bottom panel; content immediately below. Add the reference's panel
  hide/reveal control without hiding the minimap or interrupting a selected action.
- HUD-03/04/05: retain all existing actions and availability/cooldown handlers;
  use framed icon cells in the bottom content region. Workshop contains both
  doors and traps. Preserve currently distinct room/trap sell commands.
- HUD-06: retain worker/fighter pickup access; show their actual available counts.
  Do not substitute pool capacity for the number of available creatures.
  Portrait/job/mood parity requires actual matching creature data and commands;
  report any remaining gap, never fabricate counters or claim equivalence.
- HUD-07: square 176-design-pixel map at bottom left with a circular aperture;
  input outside the aperture must not navigate the camera. Retain the existing
  renderer choices and live-size notification. Map movement itself belongs to 3.
- HUD-08/09: objective and event access beside the category row. Event text opens
  in its existing scrollable surface; no new event timing or mentor policy here.
- HUD-10/11/12: Help, research and player information move into Options, retaining
  F1/F4/F2 respectively. Their existing contents, apply/cancel and close actions
  stay functional; no invented replacement game rules.
- HUD-13/14/15: keep Options and its subordinate settings/confirmation flow;
  center the dialogs, preserve title/content/footer hierarchy and working scaling.
  Keep disabled Load disabled; this task does not implement saved-game loading.
- HUD-16: preserve chat and entity statistics access and close behavior.
- HUD-17: use the existing medieval font and framed dark panels for the measured
  hierarchy; contextual descriptions use the top strip, tooltips remain local.
  Publisher screenshots contain both; do not remove all text in the name of fidelity.

The bottom strip consumes input only where its displayed controls/content exist;
the hand indicator is always mouse-pass-through. Collapsing content must free
its former world area. Popup input and drag-release guards retain priority.
Scope is the existing fork's interface; missing creature filters, reference-only
actions and final artwork must be recorded as differences, not silently invented.

## Minimap resize correction

Review of the changed HUD found that all three minimap click handlers divided
by texture dimensions captured at construction. The displayed map can resize
without recreating that texture, so its center no longer selected the camera
center. The handlers now normalize against the current displayed size while
retaining the texture's world span and orientation. No camera controls changed.

A generated C++ probe exercises the actual three conversion methods at six map
sizes. Against `0f72cf3f`, 30 of 36 assertions fail; against the correction all
36 pass. Logs: `build/windows/dk2-minimap-before-results.log` and
`dk2-minimap-after-results.log`. This correction belongs to the HUD branch.
