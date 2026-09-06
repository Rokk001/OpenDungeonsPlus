# Hand and action-feedback specification (roadmap 2b)

## Status and scope

Specification in progress under [0b](DK2-REFERENCE-BASELINE.md), for a separate
`feature/dk2-hand-feedback` branch based on the complete 1b fork state.
The user authorized this correction; it must not resume the rejected permanent
label plan. Reference-version and exceptional-state evidence remain outstanding.

Use R1, R3 and R4 from the [roadmap](IMPROVEMENT-ROADMAP.md), the visually inspected
manual pages recorded in 0b, and identified runtime recordings. The manual's
general selection rule does not settle every simultaneous hand/action/UI state.

## Scenario register

For every row, record the reference input edge (press, held movement or release),
rendered state, sound, next state and matching fork observation before changing
that behavior. The starting conditions below define what to investigate; they
are not newly invented game rules.

| Scenario | Starting state and input sequence | Current fork evidence | Required reference comparison |
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

The following must be evidenced, not assigned convenient defaults:

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
The user supplies gameplay and visual/listening acceptance; no such acceptance
or new build exists for 2b at this specification stage.
