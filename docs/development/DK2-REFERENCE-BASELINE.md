# Reference baseline for roadmap items 0b, 1b and 2b

## Authorization and working state

On September 6, 2026, the user explicitly requested implementation of all three
items, each on its own branch, from the latest complete fork. This replaces the
stopped permanent-label task as the current work scope.

| Item | Branch | Current state |
| --- | --- | --- |
| 0b | `docs/dk2-reference-baseline` | Created from `11c4209e`, retaining the uncommitted roadmap and agent-rule changes; reference collection and source comparison in progress. |
| 1b | `feature/dk2-hud` | Planned successor of the completed 0b branch; detailed contract in [HUD specification](DK2-HUD-SPEC.md). |
| 2b | `feature/dk2-hand-feedback` | Planned successor of the completed 1b state; detailed contract in [hand-feedback specification](DK2-HAND-FEEDBACK-SPEC.md). |

Do not create successors from upstream or from an older fork snapshot. Preserve
the original action-feedback checkpoint and all previous Windows/display fixes.
No push or PR is authorized by this implementation request. Item 0b is internal
documentation and must never be submitted as a standalone upstream PR.

The goal service still holds the earlier objective for point 2: attempting to
create the newly requested goal returned `cannot create a new goal because this
thread has an unfinished goal; complete the existing goal first`. This technical
tracking limitation does not authorize resuming the rejected plan or marking it
complete. The user's newer scope is 0b, 1b and 2b.

## Reference identity and evidence status

The binding game edition, patch level and settings are awaiting the user's
answer. No reference installation or gameplay recording has been supplied in
this task. Do not silently select a patch, mod, widescreen treatment or control
configuration.

The [original player manual](https://retrogamer.biz/wp-content/uploads/2016/06/Dungeon-Keeper-2-Manual.pdf)
was downloaded and visually inspected for the relevant hand and interface pages.

| Evidence field | Verified value |
| --- | --- |
| Local inspection copy | `build/reference-audit/original-player-manual.pdf` |
| SHA-256 | `30a2dce213907a9573eba7fadf1d5afb9475a884f1a9737df5e26fc4bc166ad8` |
| PDF pages | 45 |
| Inspected PDF pages, one-based | 7, 11, 12, 13, 14, 15 |
| Corresponding printed pages | 12-13, 20-21, 22-23, 24-25, 26-27, 28-29 |
| PDF rendering | PyMuPDF 1.26.4, scale 1.5; inspected page size 842 x 595 PDF points, rendered as 1263 x 893 pixels |
| Local page images | `build/reference-audit/manual-page-07.png` and corresponding `11` through `15` files |
| Inspection tool location | `build/reference-audit/pdf-tools`; imported with the existing Python 3.10 executable, without changing the game's dependencies |

These dimensions describe the document, not the game's viewport or cursor
hotspot. Several HUD illustrations are low-resolution crops; their enlargement
on a printed page is not a valid measurement of the runtime UI. Do not implement
pixel sizes, colours or timing from those crops.

The manual anchors R1-R5 remain in the [roadmap](IMPROVEMENT-ROADMAP.md).
The inspected figures add these bounded observations:

- Printed page 22 places the circular map at the left of the illustrated panel.
- Printed page 13 illustrates distinct relaxed, pointing and pickaxe hand forms,
  plus action and prohibition symbols beside the hand.
- Printed page 23 documents last-picked-first-dropped ordering.
- Printed page 27 describes workshop orders being fulfilled in received order.

These observations do not resolve button precedence over the GUI, mixed-area
placement, failure timing, precise geometry or patch-specific differences.

## Current-fork findings

These are code findings at `11c4209e`, not new runtime acceptance results.

| Area | Actual current path and behavior | Consequence for the new task |
| --- | --- | --- |
| HUD composition | `gui/ModeGame.layout` places resource values at the top, action tabs at the bottom and the minimap at the lower right. | 1b needs a measured reference composition, not a tab-only rearrangement. |
| Categories | Layout imports are rooms, traps, spells, creatures. | Map categories and all existing commands before changing the panel. |
| Creature selection | `WindowTabCreatures.layout` provides worker and fighter pickup buttons. | The reference creature-panel figures expose a larger interaction surface; data and command mappings must be specified before claiming equivalence. |
| Persistent feedback | `GameMode::refreshActionFeedback` updates `ActionFeedback` and selected-button colours every frame. | 2b replaces this rejected presentation while retaining necessary input validation. |
| Pointer text | `GameMode::displayText` assigns validity from the supplied colour, writes `Ready`/`Unavailable` text and retains failures for three seconds. | The presentation and the existing validity contract must be separated carefully; hiding text alone is not a full correction. |
| Hand rendering | `RenderManager` creates `Keeperhand.mesh` with an idle animation and uses pickup/drop animation states. | Inspect existing mesh states before deciding what additional assets are needed; an idle mesh alone does not establish reference hover behavior. |
| Hand ordering | `Player::addEntityToHand` inserts at index zero; `Player::dropHand` defaults to index zero. | The default order is already last-picked-first-dropped; preserve it. Explicit hand rotation is a separate existing function. |
| Cancellation | `GameMode::mousePressed` cancels an active world action before finding a valid map tile, but returns earlier for GUI input and paused gameplay. | Record and compare each precedence case; do not assume cancellation over the GUI behaves like cancellation outside the map. |
| Confirmation | `GameMode::mouseReleased` requires a world press, a world release, a live connection and unpaused gameplay before confirming. | Preserve the stale-input and unintended-command protections while comparing exact reference press/release behavior. |
| Idle hover | `handlePlayerActionNone` clears pointer text with an empty hand; a held object triggers drop checks and target text. | Trace and specify neutral hover separately from held-object validity. |
| Workshop lifecycle | `RoomWorkshop::doUpkeep` creates needed crafted traps; `Trap::notifyCarryingStateChanged` activates a tile after delivery. | Production and delivery already exist; do not recreate them based on a visual assumption. |
| Workshop scheduling | `RoomWorkshop::doUpkeep` aggregates required trap types and randomly chooses a type when starting new work. | This differs from the documented order policy and requires a focused mechanics prerequisite if confirmed for the chosen version. |

## Required evidence packages

Each package must identify the chosen version, starting state, input sequence,
reference frame/time, resulting game state, visual/audio result and current-fork
comparison. Use the scenario identifiers in the two linked specifications.

| Package | Required coverage | Current status |
| --- | --- | --- |
| Reference identity | Edition, patch, mods, language, resolution, camera and input settings. | User answer pending. |
| HUD composition | Whole viewport with each category and every affected window open; enabled/disabled, selected and tooltip states. | Manual figures inspected; runtime captures and measurements missing. |
| Hand transitions | Empty/occupied hand, hover types, selection, switching, cancellation, completion and invalid attempts. | Manual rules plus current code mapped; complete runtime sequence missing. |
| Geometry | Interface/world boundary, reference proportions, cursor hotspot and icon offsets. | Not measured from runtime evidence. |
| Timing and sound | Animation start/end, tooltip delay, failed-action response and recovery. | Not established. |
| Compatibility decisions | Treatment of existing fork functions with no verified reference counterpart. | User answer pending for keeping existing additional windows. |

The user performs manual gameplay and visual/listening acceptance; the assistant
does not start either game for QA. Reference recordings, once available, can be
inspected without changing the current game or its saved data.

## Upstream reconciliation

`git fetch upstream` completed for this task; `upstream/shaders-improvement`
remains at `be44649fac6d388dde669598130f85ceb5a33be5`. The refreshed query returned
12 open issues and 19 open PRs, none draft.

| PR | Queried head | Decision for 0b/1b/2b |
| --- | --- | --- |
| [29](https://github.com/tomluchowski/OpenDungeonsPlus/pull/29) | `bab847a6` | Already incorporated in the fork; its two affected layout files are included in the current UI inventory. Do not apply again. |
| [15](https://github.com/tomluchowski/OpenDungeonsPlus/pull/15) | `efa47d31` | Full paginated file list checked: 317 files, including GUI skin, settings/skill/confirmation layouts, game input, GUI and renderer code. Reconcile individual overlaps; do not adopt the port as a new base. |
| [16](https://github.com/tomluchowski/OpenDungeonsPlus/pull/16) | `ab2858da` | Remains open; inspect only an individual dependency if the reference comparison requires it. |
| [21](https://github.com/tomluchowski/OpenDungeonsPlus/pull/21) | `2e2df09f` | Remains open; no portability integration is required for this reference-documentation stage. |
| [41](https://github.com/tomluchowski/OpenDungeonsPlus/pull/41) | `7f408353` | Fog work remains separate from the HUD/hand changes. |
| [45](https://github.com/tomluchowski/OpenDungeonsPlus/pull/45) | `bcec307c` | Ownership materials remain separate from the HUD/hand changes. |

No upstream implementation was merged or cherry-picked in this task.

## Completion gate

0b is not complete until the chosen reference and the necessary scenario evidence
allow implementation without inventing UI or gameplay decisions. Missing values
remain missing; a filled template or a source link does not prove the gate passed.

1b and 2b must each receive their own implementation, build evidence and user
acceptance on the designated branch. The original points 0, 1 and 2 remain
unchanged historical sections in the roadmap.

For this documentation stage, the game remains version 0.7.1: there is no runtime
change or release. The development index and agent entry point are updated;
the root README and a game changelog need no new behavior entry yet.
