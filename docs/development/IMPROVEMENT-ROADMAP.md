# Product improvement roadmap: Dungeon Keeper 2 fidelity

## Binding product target

OpenDungeonsPlus is to become a Dungeon Keeper 2 clone. Dungeon Keeper 2 is the
binding reference for gameplay, controls, interface structure, feedback,
progression, presentation and sound. Every roadmap change must reproduce how the
reference solves the same situation. General usability improvements, contemporary
UI conventions and an implementer's preferred design are not substitutes for
that requirement.

This direction was clarified by the user on September 6, 2026 and supersedes the
previous roadmap's discretionary design proposals for future work. In particular,
a working implementation is not accepted merely because it explains an action:
its presentation and interaction must also match the reference.

The user's current complete fork remains the implementation baseline. Preserve
the existing Windows startup, live display settings, pointer alignment, scrolling
and GUI scaling work. Compatibility with current hardware and resolutions must
support the reference experience. It must not silently change its controls,
layout, pacing or game rules. Any unavoidable difference must be documented and
resolved with the user before implementing that difference.

The roadmap rewrite was a documentation-only task. The user subsequently
authorized implementation of **0b, 1b and 2b**, each on its own branch; see the
[current reference baseline](DK2-REFERENCE-BASELINE.md). Later roadmap items are
not automatically authorized except for prerequisites explicitly required by
those items.

## Status and preservation of completed work

The user identifies points **0, 1 and 2 as implemented**. Their original sections,
including the Gate 0 result and point 2's historical prototype status, are kept
verbatim below. They describe the work already performed, not the revised target.

Point 2's historical statement that the step was incomplete records the rejected
presentation at that time. The implementation is now a preserved checkpoint;
bringing it into line with the reference is **2b**, not an instruction to redo or
discard point 2. Functional implementation and reference fidelity are separate
acceptance questions.

| Item | Status for this roadmap |
| --- | --- |
| 0 | Completed upstream preparation; retain the original record and repeat upstream checks when starting later contributions. |
| 1 | Implemented GUI scaling; retain it as the technical foundation. |
| 2 | Implemented action-feedback prototype; preserve the checkpoint and its verification evidence. The permanent panel was rejected by the user. |
| 0b | Reference manual/gallery register and concrete contracts recorded; unresolved fidelity measurements remain explicit. |
| 1b | HUD composition implemented and technically checked; visual acceptance and listed fidelity differences remain open. |
| 2b | Hand feedback implemented and technically checked; gameplay/visual acceptance remains open. |
| 3 onward | Rewritten future work; implementation and reference acceptance remain outstanding. |

The previous permanent-label plan remains stopped; current authorized work is
the separate 0b/1b/2b sequence under this revised plan.

## Evidence and reference rules

The reference is the game identified on the
[official publisher page](https://www.ea.com/games/dungeon-keeper/dungeon-keeper-2).
The original
[player manual](https://retrogamer.biz/wp-content/uploads/2016/06/Dungeon-Keeper-2-Manual.pdf)
provides the initial behavior evidence. Page numbers below are the manual's
printed page numbers; PDF links point to the corresponding spread.

These are concise reference anchors, not a complete specification:

| Anchor | Documented reference behavior | Source |
| --- | --- | --- |
| R1: hand | Hover changes the hand; left-click picks up, right-click drops or slaps contextually. Digging uses a pickaxe and click/drag marking. Selected actions show an icon beside the hand; right-click cancels. Invalid locations show a prohibition symbol. | [Manual, pp. 12–13](https://retrogamer.biz/wp-content/uploads/2016/06/Dungeon-Keeper-2-Manual.pdf#page=7) |
| R2: panels | Creature, room, spell and workshop categories share the control panel. Objective, message and battle tabs have distinct interactions; new items flash. | [Manual, pp. 20–23](https://retrogamer.biz/wp-content/uploads/2016/06/Dungeon-Keeper-2-Manual.pdf#page=11) |
| R3: building | Room selection produces a world blueprint; click or drag builds. Insufficient gold makes the blueprint red. | [Manual, pp. 24–25](https://retrogamer.biz/wp-content/uploads/2016/06/Dungeon-Keeper-2-Manual.pdf#page=13) |
| R4: spells and workshop | Spells use selection then targeting. Workshop blueprints order manufacture followed by worker delivery and installation. | [Manual, pp. 26–27](https://retrogamer.biz/wp-content/uploads/2016/06/Dungeon-Keeper-2-Manual.pdf#page=14) |
| R5: map | On the full map, left-click closes and relocates the camera; right-click closes without relocation. | [Manual, pp. 28–29](https://retrogamer.biz/wp-content/uploads/2016/06/Dungeon-Keeper-2-Manual.pdf#page=15) |

For scripting research, the
[editor manual transcription](https://keeper.lubiki.pl/dk2_docs/dk2_editor_manual.htm)
describes GUI and area triggers, speech actions, interface flashing, camera
sequences and level win/loss actions in sections 8.2–8.3. The host labels this
copy as fan-modified; verify relevant details against the original editor data
or the chosen game version before treating them as exact implementation values.

The user subsequently delegated reference interpretation to the original game.
The manual and EA publisher gallery now supply the behavior and main-HUD
measurements recorded in [0b](DK2-REFERENCE-BASELINE.md). Their metadata does not
establish an executable patch number; no patch-specific claim is made. Static
images do not establish exact animation timing, sound selection, repeat intervals
or every exceptional input state. Do not reopen the resolved version/window
questions; research a real conflict if one affects implementation.

Use original documentation and directly observed reference behavior together.
Record edition, settings and the source or capture for each comparison. If sources
disagree, or a required detail cannot be verified, mark the affected requirement
**reference evidence missing** and resolve it before implementing that behavior.
Do not fill gaps with memories, generic game-design advice or an invented mockup.

## Current fork and upstream snapshot

The documentation rewrite starts from `feature/action-state-feedback` at
`11c4209e`, continuing from the accepted GUI-scaling state. Existing implementation
and verification records remain authoritative for what was actually tested:

- [Windows setup](WINDOWS-DEV-SETUP.md), [builds](BUILDING.md) and
  [startup corrections](WINDOWS-STARTUP-FIXES.md).
- [Settings choices](WINDOWS-SETTINGS-FIXES.md) and
  [live settings, pointer alignment and scrolling](LIVE-SETTINGS.md).
- [GUI scaling](GUI-SCALING.md).
- [Preserved action-feedback prototype](ACTION-STATE-FEEDBACK.md).

The preserved point-2 `gui/ModeGame.layout` contained `ActionFeedback` and
`MainTabControl`. Extension 2b removes the permanent panel; technical checks alone
do not demonstrate reference fidelity.
Likewise, room and spell enums in `source/rooms/RoomType.h` and
`source/spells/SpellType.h` are a starting inventory, not proof of matching
mechanics. Inspect the actual handlers and data before declaring a feature
equivalent or missing.

The earlier audit used six historical repository screenshots from 2021–2024;
they remain historical evidence, not current reference comparisons. Do not reuse
the former fixed-pixel measurements as a description of the now-scalable GUI.

On September 6, 2026, GitHub listed **12 open issues and 19 open pull requests**
in the original repository; all 19 PRs were ready for review. The coordination
tables below reflect that query. The older September 5 counts inside preserved
point 0 remain historical. Refresh individual PRs, commits and affected files
before relying on them; an open PR is neither a merged dependency nor evidence
that its design matches the reference.

## Required contract for every implementation item

Before coding, record the following in that item's development note:

| Field | Required evidence |
| --- | --- |
| Reference | Edition/settings, manual section or recording with timestamp, and the exact scenario being reproduced. |
| Starting state | Selected action, held objects, resources, ownership, research/availability, camera and open interface elements relevant to the scenario. |
| Input and transition | Exact buttons/keys, press/drag/release order, hover, cancellation and the resulting game state. |
| Visible and audible result | Where feedback appears, its appearance, duration, sound and disappearance conditions, supported by evidence. |
| Fork delta | Current code/data path, observed difference and the smallest necessary change. |
| Acceptance | The same scenario performed in both games, with matching behavior and presentation; list any unresolved difference explicitly. |

Use the same viewport aspect ratio and comparable world framing for visual
comparisons, then verify the fork's supported resolutions and 80–120% scale range.
Do not judge fidelity from a screenshot of an unrelated scene or from compilation
alone. Deterministic checks can verify state transitions; the user performs manual
gameplay, listening and visual acceptance.

## Ordered implementation roadmap


### Gate 0: refresh and reconcile upstream work

Before every feature branch:

1. Fetch `upstream` and re-query open issues and pull requests.
2. Check whether PR #29, #41, #45, #21, #16 or #15 has merged, changed scope or
   been replaced.
3. Compare the exact affected files before integrating an upstream dependency.
4. Create the implementation branch from the user's latest complete fork state
   and preserve all newer fork commits and documentation.

This gate prevents duplicate fixes and large avoidable merge conflicts.

#### Gate 0 result for `feature/gui-scaling`

Gate 0 was completed on September 5, 2026. After fetching `upstream`,
`upstream/shaders-improvement` still pointed to `be44649f`. GitHub still
reported 12 open issues and 13 open pull requests; none of the six pull
requests checked below had merged or been replaced, and none reported a formal
review decision or status check.

| PR | Verified state and file overlap | Decision for this branch |
| --- | --- | --- |
| [#29](https://github.com/tomluchowski/OpenDungeonsPlus/pull/29) | Open and mergeable at `bab847a6`; its single commit changes only `gui/WindowTabRooms.layout` and `gui/WindowTabSpells.layout` and is patch-equivalent to the corresponding change in PR #16. | Required dependency because GUI scaling must continue from the corrected two-row action layouts. |
| [#41](https://github.com/tomluchowski/OpenDungeonsPlus/pull/41) | Open and mergeable at `7f408353`; it changes `shaders/Cloud.frag` and `source/render/RenderManager.cpp`. | Excluded because fog rendering is independent of GUI scaling. |
| [#45](https://github.com/tomluchowski/OpenDungeonsPlus/pull/45) | Open and mergeable at `bcec307c`; its 34 files cover room materials, seat-mask textures, `shaders/Room.frag`, `source/entities/Tile.cpp` and `source/render/RenderManager.cpp`. It still explicitly supersedes PR #37. | Excluded because room ownership rendering is independent of GUI scaling. |
| [#21](https://github.com/tomluchowski/OpenDungeonsPlus/pull/21) | Open and conflicting at `2e2df09f`; its eight files cover CMake and platform/resource handling, with no GUI layout file. It remains a focused split from PR #16. | Excluded because it is not required for GUI scaling. |
| [#16](https://github.com/tomluchowski/OpenDungeonsPlus/pull/16) | Open and conflicting at `ab2858da`; its 101 files combine unrelated crash, gameplay, editor, portability and level work. Its spell/room layout change is already available separately in PR #29. | Excluded; use the focused PR #29 dependency instead. |
| [#15](https://github.com/tomluchowski/OpenDungeonsPlus/pull/15) | Open and mergeable at `efa47d31`, but based on an older upstream commit and changing 317 files for the Ogre 14 port. It also changes the settings window, dialogs, skill tree, `OD.looknfeel` and GUI/render code, and commit `27a6a9bb` implements settings-only automatic scaling from `1.0` to `1.5`. | Excluded because it would add the renderer port and silently choose the still-unresolved scale policy. Recheck and reconcile these GUI files if the port advances. |

The corrected local branch `feature/gui-scaling` starts at the complete fork
roadmap state `e9a62ce8`, which already contains the verified Windows,
live-settings and progressive edge-scrolling work and all development
documentation. The PR #29 commit was then cherry-picked as the focused layout
dependency, producing local commit `39c91a9a`. Both dependency layouts pass XML
parsing.

The existing live-settings path supplies the runtime render-window replacement
and display-size notification used by GUI scaling. Automatic resolution scaling
is combined with a user-selected scale from 80% through 120%.

### 1. `feature/gui-scaling`

**Goal:** make the HUD, dialogs, fonts, tooltips and hit targets readable and
clickable across supported window sizes and after live resolution changes.

**Scope:** establish one scale policy, scale the common fonts and skin metrics,
reflow the top bar and bottom action area, and adapt fixed dialogs without changing
their game behavior.

**Scale policy:** combine automatic resolution scaling with a user-selected
scale; the supported user range is 80% through 120% in 10% steps.

**Dependency and overlap:** resolve PR #29 first because it changes
`WindowTabSpells.layout`. Use the fork's live display update path where runtime
resize notification is required, but keep unrelated Windows setup out of the
eventual upstream contribution.

**Verification:** test every main menu, game HUD tab, settings page, help,
objectives, skill tree and exit dialog at representative small, full-HD and
high-resolution window sizes; verify no clipping, overlap, missed click target or
pointer offset.

### 2. `feature/action-state-feedback`

**Goal:** make every two-step action explain its current mode, valid target and
failure reason.

**Scope:** add a persistent active-action label near the action bar, strengthen
the selected state, distinguish valid and invalid world targets, and show one
specific reason when an attempted build, spell or placement cannot proceed.

**Dependency:** GUI scaling should land first so the feedback has a stable visual
location and text size.

**Verification:** a player must be able to select, cancel and complete digging,
room building, trap placement, summoning and a targeted spell without consulting
the help page, and an invalid click must explain why it failed.

**Status (September 6, 2026):** prototype checkpoint from the
accepted GUI-scaling fork baseline; Release compilation, 508 decision/input
checks and the headless CEGUI geometry checks pass. The user confirmed that the
label appears but rejected the permanent panel. The replacement presentation
has not yet been agreed; contextual pointer hints and brief failure messages
are a proposal, not an approved requirement. The user stopped the goal to redesign
the plan and requested a commit preserving this branch. This step is not complete;
do not resume the old plan without new instructions. See
[implementation and verification](ACTION-STATE-FEEDBACK.md).

### 0b. `docs/dk2-reference-baseline`

**Working specification and evidence:** [reference baseline](DK2-REFERENCE-BASELINE.md).

**Purpose:** add a fidelity gate to the completed upstream preparation.

**Deliverable:** an internal reference register under `docs/development/`, with
one entry per scenario in the implementation contract above. Establish the
reference edition and settings before resolving version-dependent behavior.
Populate the first entries for the HUD and action-feedback corrections, then
extend the register as later tasks approach implementation.

**Required work:**

1. Map each affected fork control, action and screen to its reference counterpart;
   mark missing counterparts and uncertain equivalence explicitly.
2. Capture or obtain traceable reference evidence for normal, selected, valid,
   invalid, cancelled and completed states. Include the state after an action,
   not just its initial appearance.
3. Measure the relevant layout, cursor hotspot, animation and feedback timing.
   Record measurements, not values chosen because they seem comfortable.
4. Compare pending upstream changes against both the current fork and the
   reference contract. Reuse compatible implementations without adopting their
   design automatically.
5. Record any conflict between fidelity and an existing fork feature for an
   explicit user decision; never silently remove existing functionality.

**Acceptance:** an implementer can identify the expected result and its evidence
without making a new UX or gameplay decision. Missing evidence blocks only the
affected implementation, not preservation of the user's working baseline.

This is internal documentation and receives no upstream PR.

### 1b. `feature/dk2-hud`

**Working specification:** [HUD comparison contract](DK2-HUD-SPEC.md).

**Purpose:** correct the interface built on point 1 to match the reference.

**Reference:** R2 and the reference captures established in 0b.

**Scope:**

- Inventory the current HUD and in-game windows against the reference; map every
  existing function before moving or replacing a control.
- Match the evidenced composition, panel hierarchy, category ordering, resource
  displays, minimap integration, icon states, tooltips and window presentation.
  Do not retain a layout merely because it is already implemented or fits a
  generic modern-game convention.
- Keep point 1's scale policy and the live display update path. Apply them to the
  reference proportions, including fonts, skin, controls and hit targets.
- Specify the exact interface/world boundary needed by 2b. Leave action execution
  and camera control changes to their own branches.

**Acceptance:** compare the same open categories and windows against the
reference captures. Every existing command remains reachable; every intentional
difference is resolved with the user. Repeat checks after changing resolution,
fullscreen and scale, including tooltip placement, clipping and pointer alignment.

**Dependencies and overlap:** 0b; existing point 1. PR #29 is already part of the
GUI baseline; inspect its actual current layout instead of applying it again.
Reconcile relevant PR #15 layout changes if that contribution advances.

### 2b. `feature/dk2-hand-feedback`

**Working specification:** [hand and action-feedback contract](DK2-HAND-FEEDBACK-SPEC.md).

**Purpose:** replace the rejected presentation from point 2 with the reference's
action interaction and feedback.

**Reference:** R1, R3 and R4, completed by scenario evidence from 0b.

**Scope:** remove the permanent `ActionFeedback` presentation from the normal
game HUD as this corrective task is implemented. Preserve the useful validation
and input fixes from the committed prototype where they agree with the reference.
Do not reset the branch or replace it with an older implementation.

The correction is not a proposal for a shorter label, a floating text banner or
an arbitrary three-second toast. Reproduce the evidenced hand, selected-action,
target and world-preview states. Reassess the prototype's button overlays,
colour-coded text and failure messages against the same evidence.

| Scenario to compare | Required correction and acceptance |
| --- | --- |
| Idle and world hover | Match R1 for every relevant target type, including transitions between world and GUI; no leftover active-action presentation. |
| Select, switch and cancel | Apply the evidenced R1 transitions; cancellation and action switching must leave the correct next state and must not accidentally execute another action. |
| Dig and undo marking | Compare the complete gesture against R1, including release, repeated marking and cancellation. |
| Build one tile or an area | Match R3, including preview geometry and affordability; measure mixed valid/invalid selections instead of inventing partial-build behavior. |
| Select and cast each supported spell | Match the applicable R1/R4 interaction; verify ownership, resources, availability and repeat attempts against the corresponding reference scenario. |
| Place, cancel or sell workshop items | Compare the applicable R4 lifecycle; do not disguise a missing production mechanic with a cursor-only change. |
| Pick up, hold, drop and contextual secondary actions | Record object ordering, target eligibility and button precedence from the reference before changing the current hand logic. |
| Invalid attempt | Reproduce the observed response, duration and recovery; do not invent a failure channel or claim that all invalid actions use the same feedback. |

**Acceptance:** the user can replay the recorded input sequence and see the same
feedback transitions as in the reference. Existing protection against stale
targets, unintended commands and pointer offsets remains intact. Automated
validation results from point 2 remain historical evidence until affected checks
are rerun; they do not establish visual fidelity.

**Dependencies:** 0b and the relevant 1b interface contract. If the comparison
exposes a required gameplay mechanic, give it a focused prerequisite under point
10 before claiming that scenario is equivalent. Do not expand this branch into
a general mechanics rewrite.

### 3. Camera and navigation parity

**Target:** reproduce the reference camera and navigation behavior, including its
default controls and their interaction with the interface.

**Evidence to complete:** the manual's command reference and recorded keyboard,
pointer, edge, minimap and full-map sequences; R5 supplies one initial map anchor.
Measure zoom origin, rotation, limits, acceleration and movement speed under
comparable conditions. Resolve conflicts with existing shortcuts explicitly.

Split confirmed differences into individual branches, such as
`fix/dk2-camera-zoom`, `fix/dk2-camera-controls` and
`fix/dk2-map-navigation`. The former freely proposed drag-pan alternative is not
an approved feature; add or change a gesture only when reference evidence requires
it.

**Acceptance:** the same input produces the same camera transition and final
framing, including at interface boundaries and after live display changes.
Preserve the functioning input/display foundation. Inspect PR #16's individual
camera commits before writing equivalent fixes; issue #11 is only partially
covered by the existing edge-scrolling work.

### 4. `feature/tutorial-level`: reference campaign onboarding

**Target:** reproduce how the reference introduces its gameplay through its
opening campaign experience.

**Required specification:** record the actual opening sequence, initial level
state, available actions, guidance, completion triggers, interruptions and
progression. Use that sequence as the specification; the previous proposed lesson
list and a newly invented onboarding overlay are withdrawn.

Map each observed step to the existing level, objective and scripting code.
Research editor-manual sections 8.2–8.3 alongside the relevant original level
data or recordings. A missing mechanic becomes an explicit prerequisite under
point 10; do not substitute a different lesson to hide the gap.

**Acceptance:** replay each evidenced step in order and test premature,
out-of-order and repeated actions, saving/loading where applicable. Guidance
appears and advances under the same conditions as the reference.

**Dependencies:** relevant 1b, 2b, 3 and 6 behavior plus the required mechanics.
Recheck PR #20 for level discovery and PR #30 for content overlap; extra maps
alone do not establish tutorial fidelity.

### 5. `feature/defeat-screen`: reference end-of-level flow

**Target:** reproduce the reference failure sequence and the subsequent player
flow for each affected game mode.

**Required specification:** obtain a complete recording from the loss trigger
through the presentation and the next reachable screen. Record input ownership,
camera, sound, timing, results and available actions; inspect victory transitions
where the implementation shares their code.

The branch name does not prescribe a modal dialog. The former proposal to choose
between retry, observation, menu and exit buttons is withdrawn: the actual
reference flow determines which controls exist and when they work.

**Acceptance:** the evidenced loss condition causes the matching sequence once;
input and all destinations behave as recorded. Do not claim issue #5 resolved
from adding a visible defeat message alone.

**Dependencies:** 0b, relevant interface/audio work and the game's actual loss
state. The exact reference sequence remains unverified in this rewrite.

### 6. Reference events, mentor feedback and captions

**Target:** match the reference's event presentation and audio behavior.

**Scope:** inventory current spoken events, text, notification interactions and
settings against the reference. R2 supplies the initial notification anchor.
Establish exact event triggers, priority, interruption, repetition and dismissal
from recordings. Text visibility and its relationship to speech follow that
evidence; neither "caption every line" nor "suppress until the state changes"
remains a default rule.

Split functional work into `feature/dk2-event-feedback` and, where the comparison
requires caption changes, `feature/voice-captions`. Replacement recordings belong
to the asset work in point 9.

**Acceptance:** replay matching event sequences, including repeated warnings and
competing events; compare the visible state and audio order. The user checks
readability and listening results. Issue #7 remains only partially covered until
its individual concerns have been verified.

**Dependencies:** 0b and the relevant 1b surfaces; coordinate the guidance triggers
with point 4 and end-state feedback with point 5.

### 7. Reference ownership, exploration and fog

**Target:** match how the reference distinguishes ownership, exploration and
visibility in the world.

**Required specification:** compare equivalent unexplored, revealed and currently
visible areas, room boundaries, ownership changes and camera distances. Record
the actual transitions and visual treatment before choosing shaders or markers.

Review PR #41 for issue #13 and PR #45 for ownership rendering against those
comparisons. PR #45 supersedes PR #37, but that does not make its visual design
automatically correct for this fork's target. Reuse compatible work; document any
remaining mismatch and keep the correction focused. Check the destination and
current state of the previously noted room-emblem follow-up branch before using
it. Reconcile renderer dependencies with PR #15 when necessary.

**Acceptance:** matched scenes show the evidenced ownership and visibility states
without exposing hidden information, seams or regressions. A generic readability
improvement is insufficient evidence of fidelity.

### 8. `docs/dk2-visual-reference`

**Target:** specify the reference appearance for subsequent asset work.

Replace the former discretionary visual-direction exercise with a comparison
catalog: reference scene, camera, proportions, geometry, materials, lighting,
animation/effect state, sound and the corresponding current fork scene. Record
concrete deltas for each asset family and the acceptance view used to judge them.

Do not choose a new art style, owner-colour scheme, silhouette language or effect
intensity independently. Higher-resolution assets must preserve the evidenced
design and proportions. Record source files, usage rights and export steps for
assets that will actually be used.

**Acceptance:** each planned asset change has a traceable target and comparable
before/reference views, with missing material identified instead of invented.

This is internal documentation, not an upstream PR. Prepare the relevant family
before its point 9 implementation; the entire catalog need not be finished first.

### 9. Visual and audio implementation branches

Implement one evidenced asset family or behavior per contribution, using point
8's comparisons.

| Branch family | Scope | Acceptance |
| --- | --- | --- |
| `feature/environment-material-variety` | Correct the measured corridor, wall, floor and room differences; introduce only the editor controls needed to reproduce the evidenced variants. | Matching scenes and geometry preserve the reference appearance; adding arbitrary texture variety does not satisfy issues #12/#14. |
| `feature/creature-readability` | Match the reference creature proportions and its selection/status presentation for the chosen family. | Compare idle, selected and crowded situations at equivalent camera framing; avoid arbitrary enlargement or permanent indicators. |
| `feature/character-animation-pass` | Reproduce the evidenced motion, transitions and action timing for one creature family. | Compare the same movement and action sequences; retain synchronization between animation and gameplay. |
| `feature/ambient-audio-pass` | Reproduce the measured atmosphere, loop behavior, transitions and relative mix using suitable source assets. | User listening comparisons cover repetition, transitions and interruptions; a randomly selected soundtrack is not the target. |

Track animation concerns against issue #8 and audio concerns against issue #9.
Maintain editable sources and reproducible exports for issue #10 alongside the
functional asset contributions. The former `docs/asset-source-workflow` work
remains internal documentation and never becomes a standalone upstream PR.

Art, animation, recordings and music still need the required source material and
user acceptance. This roadmap does not claim those prerequisites are already
available or that production can be guaranteed fully automatic.

### 10. Remaining gameplay, front-end and mode parity

A matching HUD and visual pass do not establish a complete clone. Extend 0b's
register to the remaining systems, then create one focused implementation task
for each verified difference. This is a coverage requirement, not permission to
bundle all mechanics into one branch.

| System to compare | Required evidence and boundary |
| --- | --- |
| Economy and worker tasks | Compare resource generation, costs, storage, task selection and timing; inspect the existing rules before changing values. |
| Rooms and production | Map the full reference catalog to current rooms, dimensions, capacity, placement and operation; include the workshop lifecycle required by R4. |
| Research, spells, traps and doors | Compare availability, progression, targeting, effects, costs and lifecycle; shared names do not establish equivalent behavior. |
| Creatures and combat | Compare recruitment, needs, jobs, training, mood, combat decisions and outcomes with controlled scenarios. |
| Direct creature control | Inspect the reference and the complete current code path for possession/control behavior; do not infer its presence or absence from the spell enum alone. |
| Front-end, campaign and persistence | Map menu hierarchy, campaign progression, save/load, level selection and transitions to the reference, while preserving existing user data. |
| Other game modes | Inventory the reference modes and current equivalents, then document their missing rules, controls, content and completion flows separately. |

The manual's contents and system chapters provide research entry points, and
editor configuration/data can help verify underlying rules; neither replaces
runtime evidence for interactions and timing. Exact catalogs, numerical values,
level content and AI equivalence have not been audited in this rewrite.

Promote a prerequisite ahead of the interface/tutorial task that needs it.
Reconcile gameplay PRs #28, #32 and #33 against the corresponding scenario before
implementing overlapping work. Do not remove fork-specific functionality or
silently change balance while preparing a parity contribution; resolve conflicts
explicitly with the user.

**Acceptance:** all identified systems have traceable coverage, individual
differences are implemented and verified, and remaining gaps are visible. Until
then, describe completed contributions by their actual scope rather than
claiming the entire game matches the reference.

## Open issue coordination

Issues identify reported problems; the reference contract determines the solution.
Use closing keywords only when every relevant part of an issue is demonstrably
resolved.

| Issue | Roadmap relationship |
| --- | --- |
| [#4 Gameplay discoverability](https://github.com/tomluchowski/OpenDungeonsPlus/issues/4) | 2b, 4 and 6; the committed label prototype alone does not resolve the reference interaction gap. |
| [#5 Failure sequence](https://github.com/tomluchowski/OpenDungeonsPlus/issues/5) | 5; reproduce and verify the full flow. |
| [#6 Interface and mouse](https://github.com/tomluchowski/OpenDungeonsPlus/issues/6) | Existing scaling/display fixes plus 1b, 2b and 3; track remaining concerns separately. |
| [#7 Voice and captions](https://github.com/tomluchowski/OpenDungeonsPlus/issues/7) | 6 and the relevant point 9 recordings; verify each concern. |
| [#8 Character animations](https://github.com/tomluchowski/OpenDungeonsPlus/issues/8) | 8–9; compare actual animation sequences. |
| [#9 Ambient music](https://github.com/tomluchowski/OpenDungeonsPlus/issues/9) | 8–9; include the reported playback defects and reference listening comparison. |
| [#10 Editable asset sources](https://github.com/tomluchowski/OpenDungeonsPlus/issues/10) | 8–9; internal workflow notes alone are not an upstream implementation. |
| [#11 Camera navigation](https://github.com/tomluchowski/OpenDungeonsPlus/issues/11) | Existing partial edge-scrolling work and 3; request-by-request coverage, subject to reference fidelity. |
| [#12 Hallway styles](https://github.com/tomluchowski/OpenDungeonsPlus/issues/12) | 8–9; only evidenced environmental variants. |
| [#13 Seamless fog](https://github.com/tomluchowski/OpenDungeonsPlus/issues/13) | 7; assess existing PR #41 before duplicating it. |
| [#14 Map materials](https://github.com/tomluchowski/OpenDungeonsPlus/issues/14) | 8–9; coordinate assets with necessary editor support. |
| [#42 Explicit variable types](https://github.com/tomluchowski/OpenDungeonsPlus/issues/42) | Outside this roadmap; never mix unrelated style changes into a contribution. |

## Open pull-request coordination

Snapshot: September 6, 2026, 19 open PRs, none marked draft. Read each current
diff before depending on it; no mergeability or test success is implied here.

| PR | Relationship and required action |
| --- | --- |
| [#15 Ogre v14.6 v3](https://github.com/tomluchowski/OpenDungeonsPlus/pull/15) | Reconcile affected GUI/render code when needed; an engine upgrade does not establish product fidelity. |
| [#16 Aggregate fixes and levels](https://github.com/tomluchowski/OpenDungeonsPlus/pull/16) | Inspect individual overlapping camera/input commits; never replace the user's complete fork with this aggregate. |
| [#20 User data folder](https://github.com/tomluchowski/OpenDungeonsPlus/pull/20) | Check level/configuration paths for points 4 and 10. |
| [#21 Cross-platform fixes](https://github.com/tomluchowski/OpenDungeonsPlus/pull/21) | Reconcile exact Windows contribution overlap; keep separate from new UX work. |
| [#28 Bridge rerouting](https://github.com/tomluchowski/OpenDungeonsPlus/pull/28) | Check point 10's movement/bridge scenarios before introducing overlapping fixes. |
| [#29 Two-row spell buttons](https://github.com/tomluchowski/OpenDungeonsPlus/pull/29) | Already included in the historical GUI baseline; evaluate the resulting layout under 1b, without reapplying the patch. |
| [#30 Additional levels](https://github.com/tomluchowski/OpenDungeonsPlus/pull/30) | Compare content and discovery overlap; not a substitute for the reference onboarding or campaign. |
| [#31 Integration-test launcher/macOS](https://github.com/tomluchowski/OpenDungeonsPlus/pull/31) | Independent validation/platform work; use when relevant without bundling it into product changes. |
| [#32 Destructible traps](https://github.com/tomluchowski/OpenDungeonsPlus/pull/32) | Compare the precise mechanic under point 10 before reuse. |
| [#33 Room hit points](https://github.com/tomluchowski/OpenDungeonsPlus/pull/33) | Compare rules under point 10; do not mix with room appearance. |
| [#37 Room ownership tint](https://github.com/tomluchowski/OpenDungeonsPlus/pull/37) | Superseded by #45; do not combine both treatments. |
| [#41 Fog tile overlap](https://github.com/tomluchowski/OpenDungeonsPlus/pull/41) | Candidate for point 7, subject to the reference comparison. |
| [#45 Room ownership emblems](https://github.com/tomluchowski/OpenDungeonsPlus/pull/45) | Candidate for point 7; its preferred upstream status does not override this roadmap's target. |
| [#47 Windows support](https://github.com/tomluchowski/OpenDungeonsPlus/pull/47) | Existing fork contribution; preserve the working baseline. |
| [#48 Dynamic shadows](https://github.com/tomluchowski/OpenDungeonsPlus/pull/48) | Existing fork contribution; preserve startup/render corrections during visual work. |
| [#49 Settings option deduplication](https://github.com/tomluchowski/OpenDungeonsPlus/pull/49) | Existing fork contribution; preserve corrected choices. |
| [#50 Live settings](https://github.com/tomluchowski/OpenDungeonsPlus/pull/50) | Existing fork contribution; retain display updates and pointer alignment. |
| [#51 Progressive edge scrolling](https://github.com/tomluchowski/OpenDungeonsPlus/pull/51) | Existing fork contribution; compare remaining navigation behavior under point 3. |
| [#53 GUI scaling](https://github.com/tomluchowski/OpenDungeonsPlus/pull/53) | Existing fork contribution for point 1; 1b is a separate correction, not a rewrite of its history. |

Implement every new task from the latest complete fork. Keep one work branch per
functional contribution and create separate PRs with explicit prerequisites.
Never combine unrelated branches or submit internal documentation as a PR.
For stacked work, disclose the cumulative comparison and verify that the eventual
merge diff contains only that contribution after its prerequisites land.
Follow [the contribution workflow](CONTRIBUTING-WORKFLOW.md).

## Execution order and definition of done

Start with **0b for the HUD and action scenarios**, then the required **1b and 2b**
corrections. Continue with reference camera/navigation and the event/mechanics
prerequisites needed by the campaign onboarding and end-state work. Prepare point
8 evidence before each point 9 asset family. Point 10 exposes further gaps and
supplies dependencies; it is not postponed when an earlier task needs it.

For each task, record the reference, implemented delta, actual verification and
remaining differences. A successful build, a visible label, an attractive
screenshot or a closed issue is not sufficient: the affected behavior and
presentation must match the evidenced reference, with user acceptance recorded.
Do not claim unsupported parity, silently accept deviations, or remove existing
fork work to obtain a cleaner starting point.

Current work begins with the authorized reference baseline in 0b and continues
through 1b and 2b on separate branches. Complete the necessary evidence and
specification before each implementation; do not resume the stopped
permanent-label design.
