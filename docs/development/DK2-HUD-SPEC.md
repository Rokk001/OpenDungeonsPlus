# HUD reference specification (roadmap 1b)

## Status and dependency

Specification in progress under [0b](DK2-REFERENCE-BASELINE.md); this is not an
approved set of invented coordinates. The user has authorized implementation,
but the required reference version, runtime captures and compatibility decisions
remain open. Implementation belongs on `feature/dk2-hud` after the relevant gate.

## Existing functions that must remain reachable

| Scenario | Current UI / implementation | Comparison required before changing it |
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

## Geometry contract to measure

Use one identified whole-viewport reference capture per scenario; record its
resolution and UI state. For each affected element, record the visible bounds,
interactive bounds, anchor, ordering and relation to the map. Store the reference
coordinates and the derivation of the fork's design coordinates together.

The following values are deliberately not assigned without reference evidence:

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

No new game build or user acceptance has been performed for 1b at this stage.
