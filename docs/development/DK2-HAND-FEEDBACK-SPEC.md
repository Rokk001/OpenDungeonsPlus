# Hand and action-feedback specification (roadmap 2b)

## Status and scope

Implementation on `feature/dk2-hand-feedback`, based on the complete 1b fork
state and the original evidence in [0b](DK2-REFERENCE-BASELINE.md).
The user authorized this correction; it must not resume the rejected permanent
label plan. Reference interpretation is delegated to the original-game evidence; exceptional-state evidence must be distinguished from implementation checks.

Use R1, R3 and R4 from the [roadmap](IMPROVEMENT-ROADMAP.md), the visually inspected
manual pages recorded in 0b, and identified runtime recordings. The manual's
general selection rule does not settle every simultaneous hand/action/UI state.

## Scenario register

For every row, record the reference input edge (press, held movement or release),
rendered state, sound, next state and matching fork observation before changing
that behavior. The starting conditions below define what to investigate; they
are not newly invented game rules.

| Scenario | Starting state and input sequence | Preserved prototype evidence (before 2b) | Reference comparison inventory |
| --- | --- | --- | --- |
| HAND-01 idle | Empty hand, no selected action; move over open ground, a creature, an object, a diggable wall and undiggable terrain. | `handlePlayerActionNone` clears pointer text when the hand is empty; renderer creates the idle hand mesh. | R1 hover forms, exact targeting/highlight, hotspot and all transitions. |
| HAND-02 select | No active action; choose each supported room, trap or spell, then enter the world. | Skill buttons set the selected action; frame refresh adds a button colour and permanent description. | R1 selected-state rendering and R3/R4 target preview for that specific action. |
| HAND-03 switch | Action A selected; choose B, including a different category and an unavailable item. | Current action descriptions and selected-button properties are updated per frame. | Whether selection changes, remains or clears in each reference case, plus exact visual transition. |
| HAND-04 cancel | Active action, with and without a drag; right-click valid world, invalid world, outside map and over GUI. | World cancellation clears left-drag state, selection and pointer text; GUI and paused input return earlier. | Cancellation precedence and the resulting hand state for every location; no blanket GUI-cancellation assumption. |
| HAND-05 dig | Start on marked/unmarked wall, drag over mixed terrain, release or cancel; repeat the same area. | First tile determines mark/unmark; eligible tiles are previewed; the confirmed request carries rectangle and desired mark state. | R1 gesture and exact behavior on mixed areas, repeated marking and interrupted drag. |
| HAND-06 build | Select one room; hover and confirm one tile or an area, with enough/insufficient gold and mixed validity. | `RoomManager` validates the selection; preview validity controls selected-tile flags through `GameMode`. | R3 blueprint appearance, costs, partial-area handling and state after success/failure. |
| HAND-07 cast | Select each of the ten current spells; exercise valid, wrong-owner, wrong-target, no-resource and cooldown states. | Individual client handlers validate against current game rules; some spells support area selection. | Establish each reference counterpart and its targeting/feedback; do not assume all current spells have equivalent reference mechanics. |
| HAND-08 workshop | Select each trap/door, place one or multiple orders, cancel, sell, allow manufacture and delivery. | Production and delivery exist; next required trap type is currently selected randomly. | R4 order lifecycle, preview, cancellation/refund, completion state and verified scheduling prerequisite. |
| HAND-09 pickup/drop | Pick up A then B; drop without rotation; repeat after explicit hand rotation and over invalid terrain. | New objects insert at index zero and default drop removes index zero; explicit rotation reorders the hand. | Retain the documented default order; compare held-object rendering, capacity, rotation and drop eligibility separately. |
| HAND-10 secondary action | Empty/occupied hand over a slappable creature, with and without another action selected. | Active action cancels first in the world; otherwise held objects try to drop; otherwise the closest eligible entity may be slapped. | Exact precedence, hand animation and response for the matching reference state. |
| HAND-11 invalid attempt | Attempt an action, then keep pointer still, move to valid ground, retry, switch or cancel. | Failure text persists for three seconds; fresh previews run each frame without confirming a command. | Evidence for the actual failure channel, duration, recovery and whether invalid feedback is hover-driven or click-driven. |
| HAND-12 interrupted input | Begin a world drag, release over GUI, lose a valid map position, pause or disconnect. | Release guards prevent confirmation; interrupted digging returns to no selected action. | Preserve unintended-command protection and specify the reference's remaining visible and selection state. |

## Presentation to replace

The permanent `ActionFeedback` panel, gold selection overlay, validity text and
three-second message retention belong to the old prototype. They are not accepted
reference requirements. Remove or replace only the parts made obsolete by the
evidenced correction; retain working validation and input handling.

Before changing the presentation, record the actual source of target validity.
Currently `GameMode::displayText` derives validity from colour, updates the
pointer overlay and stores failed-confirmation text; callers depend on that
contract. Removing the text call without preserving its validation effect would
change preview/confirmation behavior. Choose the smallest code change after the
reference states are specified, rather than redesigning the entire input system.

The relevant existing rendering paths are:

- `source/render/RenderManager.cpp`: keeper-hand mesh, animation and held objects.
- `source/render/TextRenderer.cpp`: existing pointer overlay.
- `source/modes/GameMode.cpp`: selection, per-frame preview, input and feedback.
- `source/game/Player.cpp`: hand ordering and drop permissions.
- `source/game/SkillManager.cpp`: selected-action button mapping.
- Room, trap and spell handlers: current eligibility and confirmation requests.

## Unresolved measurements and decisions

The following fidelity measurements are distinguished from technical asset
construction values. Publisher stills and the manual support the implemented
forms and gestures; they do not prove original frame timing or exact asset parity:

- Hand asset forms, pose transitions, animation durations and cursor hotspot.
- Selected-action/prohibition icon artwork, dimensions, attachment point and
  coexistence with held objects or a world preview.
- Valid, invalid, unaffordable and partially valid preview geometry and colours.
- Feedback sound, timing, cooldown response and success/failure cleanup.
- GUI/right-click priority, action persistence after confirmation and relevant
  press-versus-release behavior.
- Reference counterpart and allowed treatment of current fork-only actions.

The user's rejection already authorizes replacing the permanent panel, but
does not select arbitrary replacement artwork, toast timing or mechanics.

## Identified mechanics prerequisite

`RoomWorkshop::doUpkeep` selects randomly among required trap types. The inspected
manual states an order-by-receipt policy. Confirm the chosen version's behavior
with multiple distinct orders before implementing a correction. If confirmed,
track this as a focused `fix/dk2-workshop-order` prerequisite under roadmap point
10, preserving the existing manufacturing and delivery code; do not hide it in
the hand-rendering branch or claim its lifecycle scenario already matches.

## Acceptance

HAND-01 through HAND-12 must each link the reference evidence, actual fork result
and any outstanding difference. Confirm no repeated command from a stationary
preview, no unintended release over the GUI, correct pointer alignment and the
retained default hand order. Exercise live resolution/fullscreen and 80-120%
scale changes across the affected presentation states.

Regenerate affected decision/input/layout probes from the modified source before
using their results. Old prototype checks do not certify the new rendering.
The user supplies gameplay and visual/listening acceptance. The implementation
and headless evidence below do not certify that acceptance.

## Concrete interaction contract

The 0b clarification supersedes pending version/window decisions. Manual hand,
room and spell sections plus publisher captures 2/3/5/6/8/9 define these changes:

1. Remove the permanent panel, Ready/Unavailable prefixes and three-second failure
   retention. Context descriptions belong to the top strip; the active icon and
   prohibition sign belong beside the hand. No replacement toast is introduced.
2. With no selection/held object, show the idle hand over open ground, pointing
   over pickup targets and pickaxe over a diggable wall. Re-evaluate on camera
   movement as well as pointer movement; clear stale highlights on GUI entry.
3. Selecting a room/spell/workshop item shows its own existing icon beside the
   hand. Switching replaces it; right-click cancellation removes it and clears
   the drag before any drop/slap can execute. Successful repeatable actions stay
   selected as in the manual's repeated building/casting flow.
4. Invalid action targets show the prohibition sign in the same attachment area;
   returning to a valid target restores the selected icon immediately. Existing
   resource/ownership/cooldown validation remains authoritative. Keep the actual
   reason in the context strip without a fabricated timer.
5. Digging previews eligible walls; first-tile state determines mark/unmark on
   release. Cancelling and release over UI send no command. A frame preview must
   never repeat a confirmed command.
6. Room/trap previews use world outlines, including red unaffordable placement;
   the server still validates actual placement and costs. Retain mixed-area
   eligibility behavior unless direct reference evidence requires a separate fix.
7. Held objects retain existing LIFO pickup/drop order and explicit rotation;
   right-click drops before attempting an empty-hand slap. Selection cancellation
   precedes both. Preserve existing pickup/drop/slap animations and timing until
   a measured replacement exists; do not invent extra confirmation audio.
8. Over interface controls, world previews/indicators are hidden and UI owns input;
   return to the world restores the current selection. Display changes use the
   same scaled coordinates for the hand attachment and GUI hit tests.

The ten spells keep their real current rules; none is relabelled as an unrelated
reference spell. Workshop manufacturing and delivery already exist; the known
random-vs-FIFO difference is a mechanics prerequisite under point 10, not a
cursor rendering fix. These contracts enable implementation; acceptance still
requires the user's matching gameplay/visual sequences, with remaining asset,
mechanics or source limitations stated explicitly.

## Implementation and evidence, September 6, 2026

The permanent panel, gold selection overlay updates and timed failure retention
are removed. The top context strip describes the actual current target; a selected
action icon or prohibition sign follows the hand. Returning to a valid target
restores its icon immediately. Interface hover hides world indicators, clears a
stale creature highlight and lets the open event surface consume its own input.

The existing hand asset has Idle, Pickup, Drop and Slap animations. Two additional
static poses reuse its own rig: pointing curls the other fingers while leaving
the index extended; digging also curls the index and shows an original procedural
pickaxe. The sampled finger rotations come from the existing Pickup midpoint,
0.825 seconds. The one-second pose clips are constant technical containers, not
a claimed reference animation duration. Existing one-shot animations finish
before returning to the current hover pose. No new confirmation sound is added.

The prohibition sign is generated from geometric primitives. Current action
artwork and the existing licensed hand are reused; no publisher screenshot or
proprietary game asset is shipped. The 50-design-pixel symbol follows the measured
reference size. Its current attachment is 90 design pixels right and 8 below the
existing pointer hotspot; that adaptation to the fork hand still needs visual
comparison, especially at screen edges and after scale changes.

World previews use outlines instead of the previous water-material selector.
Walls receive top, bottom and vertical edges, as visible in publisher capture 9;
ground receives a tile outline. Unaffordable room/trap areas remain visible in
red. The existing eligibility, mixed-area selection and server request paths
remain authoritative. Preview geometry is cleared when leaving the game and
excluded from minimap rendering. No workshop scheduling or spell-rule rewrite
is included in this branch.

| Scenarios | Implemented / retained behavior | Reference evidence | Verification / remaining comparison |
| --- | --- | --- | --- |
| HAND-01 | Idle, pickup-pointing and dig hover; target recomputed under a stationary pointer. | Manual R1; gallery 5/6/9. | Actual hand mesh and skeleton load headlessly; new states resolve on existing and subsequent entities. Visual pose/grip comparison remains open. |
| HAND-02/03 | Current selected icon; immediate replacement on switching or validity change. | R1; gallery 2/3/8. | Generated input checks and actual CEGUI image/layout checks pass. |
| HAND-04/12 | Existing cancel and release guards retained; GUI hides previews and owns event-window input. | R1 plus preserved input protections. | Frame previews cannot resend a confirmed action; interrupted release sends no command. Full gameplay sequences remain for the user. |
| HAND-05 | First-tile mark/unmark and eligible region retained; outlined wall preview. | R1; gallery 5/9. | Source-derived validation and geometry checks pass. Actual dig gesture acceptance remains open. |
| HAND-06 | Buildable area outlined; unaffordable area red; existing repeatable selection retained. | R3. | Source-derived room/resource checks pass. Original blueprint asset parity is not claimed. |
| HAND-07 | Existing ten spell rules and cooldowns retained; current icon and prohibition feedback. | R4; gallery 3/8. | Source-derived spell validation checks pass. Fork-only spells have no invented equivalence. |
| HAND-08 | Existing order, manufacture and delivery retained; outlined placement feedback. | R4. | Placement checks pass. Random-versus-FIFO scheduling remains a separate mechanics difference. |
| HAND-09/10 | Existing LIFO order, explicit rotation, cancel/drop/slap precedence and one-shot clips retained. | R1. | Original clip durations preserved by the asset probe. Gameplay, held-object appearance and listening acceptance remain open. |
| HAND-11 | Hover validity controls the sign; no three-second stale failure. | R1; gallery 3. | Invalid-to-valid, switching and cancellation checks pass. No unsupported sound/timing claim. |

Regenerated evidence from the modified production source:

- `build/windows/dk2-validation-probe-results.log`: 481 decision assertions pass
  for current room, trap and spell validation using world/network doubles.
- `build/windows/dk2-input-probe-results.log`: 30 assertions pass for frame/input
  transitions, symbol switching, immediate failure recovery and release guards.
- `build/windows/dk2-hand-asset-probe-results.log`: 100 assertions pass using the
  real OGRE hand mesh/skeleton and CPU geometry buffers, including pose creation,
  unchanged existing durations, outward tool faces, outlined tiles and cleanup.
- `build/windows/dk2-hud-probe-results.log`: actual CEGUI layouts/images pass at
  five resolutions and successive 80/100/120/100 percent scales; the permanent
  panel is absent and the hand image cannot intercept input.

These checks do not exercise GPU appearance, live gameplay, server responses or
audio. The user's manual comparison is still required. Remaining reference-only
mechanics and artwork are explicit differences, not certified matches.

The final clean Windows Release build and subsequent compilation of the last
context-text correction pass. Runtime preparation also succeeds. Evidence:
`build/windows/dk2-final-clean-build.log`, `dk2-final-build.log` and
`dk2-final-runtime.log`. The executable is
`C:\Users\mario\GitHub\OpenDungeonsPlus\build\windows\opendungeons-plus.exe`.
This build's SHA-256 is
`d0ec5998e4c4819bc18ad94fe8e036d64722b0bda033a8402b4e082983e25573`.
No game was launched by the assistant. Version remains 0.7.1; README and the
development index describe the new controls. No upstream issue is claimed closed.

For user acceptance, compare idle/creature/wall hover, room and spell selection,
an unaffordable build followed by a valid target, cancellation during dragging,
pickup/drop/slap and release over an open interface. Repeat after a live resolution
change and 80/100/120 percent UI scaling; check the hand attachment, outlined walls,
minimap center click and all Options commands. This is pending acceptance, not
a request to choose a different reference or redesign the interface.

## Follow-up: stationary-pointer creature highlighting

The completion audit found an incomplete part of HAND-01: during a selected
action or while holding an object, creature highlighting was still updated only
by mouse-movement events. Camera movement refreshed the target tile and action
icon, but left the old creature highlighted. Moving to empty terrain without
moving the pointer could leave that highlight behind as well.

The existing highlight update now runs after the per-frame world-position query
for selected-action, held-object and paused states. Empty-hand hover continues to
use the actual eligible pickup target. Interface entry clears highlighting;
target selection and command confirmation rules are unchanged.

The extended input probe reproduces three failures against `f2bdfd56` and passes
all 34 assertions after the correction. Evidence:
`build/windows/dk2-highlight-before-results.log` and
`build/windows/dk2-highlight-after-results.log`. Release compilation and runtime
preparation pass in `dk2-highlight-build.log` and `dk2-highlight-runtime.log`.
This build supersedes the executable fingerprint recorded above; its SHA-256 is
`a3abc957d16efcd256889b9273ed01b14a7086eb4481bd312ed8c580bcd38345`.

Version remains 0.7.1; the README already describes the intended hover behavior,
so this corrective follow-up needs no additional user-facing feature entry.
Screenshot comparison and gameplay acceptance remain outstanding; the screenshot
folder currently contains its README only. The proposed screenshot hotkey is a
separate feature and has not been implemented by this correction.
