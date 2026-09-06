# Action state and target feedback

## Baseline and status

September 6, 2026: this prototype checkpoint is preserved on
`feature/action-state-feedback`, based on the user's accepted GUI-scaling commit
`e21d08ea`. The complete Windows, display-settings, camera and GUI-scaling work
and the internal documentation are preserved. No upstream baseline was used to
recreate the implementation.

The current Windows x64 Release executable was rebuilt successfully at 01:27:58
local time and its runtime files were prepared. The headless checks below pass.
The user confirmed that the new label appears, but rejected its permanent
presence and reported that it does not match the intended interaction style.
Roadmap step 2 therefore remains incomplete and is not visually accepted.
Contextual hints at the pointer with a short message for invalid actions have
been proposed as an alternative, but the user has not confirmed that proposal.
Do not implement this unresolved presentation decision or treat the current
panel as accepted merely because the automated checks pass.

The user subsequently stopped the goal to redesign the plan and explicitly
requested a commit of this branch. Preserve this checkpoint and its documentation;
do not continue implementing the old plan or the proposed replacement without
new instructions. Committing this work is not acceptance of its UX or completion
of roadmap step 2.

During the resumed session at 09:44, the
already-running game process was responsive and its client/server log had reached
turn 137. This establishes startup and an active simulation, not acceptance of
the new action controls or their appearance; the assistant did not launch it.

The same run later logged digging, spell and room-build requests reaching the
server, followed by normal game shutdown at 09:44:52 and OGRE shutdown at 09:44:53.
The game process was no longer present when checked afterward. The game log
contained no `[ERROR]` or exception entry; the OGRE log still contains asset and
shader warnings, including a missing `Panels_Diffuse.png` texture. These logs
establish an active game session and orderly shutdown, not visual correctness or
completion of every acceptance case. Runtime logs are
`build/windows/Ogre.log` and `%APPDATA%/opendungeons/{opendungeons,CEGUI}.log`.

This commit preserves the unfinished prototype and the internal workflow notes;
no push or PR was requested for this checkpoint. The version remains 0.7.1
because this is development work, not a release; the main README
describes the new action feedback and this document records verification limits.

## Implemented behavior

- A persistent panel directly above the action bar names the current action and
  explains its mouse controls, including confirmation and cancellation.
- The selected room, trap, spell or sell button has a persistent gold highlight;
  selecting another action or cancelling clears the previous highlight.
- Target feedback refreshes while the pointer is stationary, including camera
  movement, resource changes and spell cooldowns. Valid targets show a green
  `Ready:` message; invalid targets show a red `Unavailable:` message and do not
  receive the valid-tile selection highlight.
- A failed confirmation keeps one concrete `Cannot complete:` explanation in
  the panel for three seconds. A successful retry or action cancellation clears
  the old failure. Paused gameplay and remaining cooldown time have explicit text.
- The existing build and spell checks now provide reasons for unclaimed ground,
  occupied or solid tiles, insufficient gold/mana, missing or unsuitable creature
  targets, unsupported bridge terrain/connections and invalid door placement.
- Digging distinguishes marking from unmarking and previews only eligible walls;
  invalid selections explain whether the ground is already dug out, a wall belongs
  to an enemy, the wall cannot be dug, or no digging marks were selected.
- Hand placement uses the existing drop permission and explains blocked ground,
  missing vision, a full arena or unsuitable ownership. Room/trap selling explains
  empty selections; unsellable portals are excluded from the preview and request.
- Area spell previews highlight eligible creature tiles rather than the entire
  rectangle. The existing partial-affordability behavior and random choice at
  confirmation remain; the preview identifies eligible candidates, not a guarantee
  that every candidate will be affected when mana covers only some of them.
- Preview updates cannot issue a confirmed command or consume the random state
  used to choose area-spell targets. Confirmation requires an accepted world
  mouse press, and releasing over the UI does not execute the world action.
  Right-click cancellation also works when the pointer is outside the map;
  an interrupted digging drag returns to the default action.

## Code paths

`gui/ModeGame.layout` contains the feedback panel. It participates in the existing
GUI scaling and passes mouse input through to the map. `gui/OD.looknfeel` adds a
selection-colour layer to the existing game action buttons without changing their
hover, pressed or disabled states.

`source/modes/GameMode.cpp` owns action descriptions, selection highlighting,
per-frame previews, failure retention, hand/dig feedback and mouse confirmation.
`source/game/SkillManager.cpp` resolves the selected action to its existing button.
`source/modes/InputCommand.cpp` supplies the shared room/trap terrain explanation;
the build target includes that new source file.

The room and trap managers, bridge and door factories and the ten spell client
handlers use their existing target/cost checks for hover and drag feedback as well
as confirmation. The spell manager reports cooldowns. Server action rules, packet
formats, prices, spell effects and the installed dependency versions are unchanged.

## Automated evidence

| Check | Result | Scope and limits |
| --- | --- | --- |
| Windows x64 Release build | Passed; exit 0 | A clean build covered the changed class layout; the final incremental build includes the subsequent input and feedback corrections. Existing compiler/linker warnings remain. |
| Runtime preparation | Passed | Existing script staged Release DLLs, checked resource directories and restored the installed OGRE/Python paths after the build. This does not launch the game. |
| Client decision-path probe | 481 checks passed | Compiles 14 actual production methods with small world/network doubles; covers default rooms/traps, ten spells, failure reasons, free workers, insufficient resources, confirmation-only requests and area-preview random-state preservation. It does not validate real world selection predicates or server execution. |
| Frame/input probe | 27 checks passed | Compiles the actual frame-feedback, text-feedback and mouse-release methods with UI/world/action doubles; covers stationary previews, no repeated confirmation, highlight changes, retained/cleared failures, pause feedback, release guards and interrupted dragging. |
| CEGUI layout probe | No failures | Uses the installed CEGUI NullRenderer and actual GUI-scaling methods, layout and look. Checks 27 action-button properties, selected-button geometry/restoration, panel bounds, text fit and mouse pass-through at five resolutions and four successive scale settings. It does not certify rendered appearance. |
| Whitespace diff check | Passed | `git diff --check`; existing line-ending conversion notices are not test failures. |

The layout matrix uses 800x600, 1280x720, 1920x1080, 3440x1440 and 3840x2160,
with 80%, 100%, 120%, then 100% scaling, and five representative action/error
texts per setting. The initial panel failed small-window text/bounds checks;
its corrected geometry passes. The frame/input probe reproduced the interrupted
digging-mode failure before the release cleanup and passed after that correction.

Local evidence is under `build/windows/` (ignored generated artifacts):

- `action-feedback-build.log`: clean Release build.
- `action-feedback-final-build.log`: final incremental Release build.
- `generate-action-validation-probe.py`, `action-validation-probe.cpp`,
  `action-validation-probe.log`, `action-validation-probe-sources.json`:
  source extraction, generated fixture, results and tested source hashes.
- `generate-action-input-probe.py`, `action-input-probe.cpp`,
  `action-input-probe-before.log`, `action-input-probe.log`,
  `action-input-probe-source.sha256`: release regression and final evidence.
- `generate-action-layout-probe.py`, `action-layout-probe.cpp`,
  `action-layout-probe.log`: the generated CEGUI geometry probe and results.

The probes are local diagnostics, not installed game components or a replacement
for the user's play test. Regenerate them after changing their source methods;
do not treat an old executable or source hash as evidence for newer code.

## Rebuild and test location

Use the maintained environment helper and build commands in [BUILDING.md](BUILDING.md):

```powershell
Set-Location -LiteralPath 'C:\Users\mario\GitHub\OpenDungeonsPlus'
. .\scripts\win32\Enter-OpenDungeonsPlus.ps1
cmake --build .\build\windows --config Release --target opendungeons-plus --parallel 4
if ($LASTEXITCODE -eq 0) { .\scripts\win32\prepare-windows-runtime.ps1 }
```

The user can open
`C:\Users\mario\GitHub\OpenDungeonsPlus\build\windows\opendungeons-plus.exe`
directly, with its prepared files left beside it. No dependency installation or
separate launch environment is needed for this existing local Release setup.

## Required user acceptance

Start a playable level and use only the displayed action feedback:

| Action | Verify in the running game |
| --- | --- |
| Digging | Mark and unmark a wall area, cancel with right-click, and try an undiggable or already open tile. Releasing a drag over the HUD must not leave digging mode active. |
| Room construction | Select a room, identify the selected button and valid ground, build it, then try occupied/unclaimed ground and an unaffordable selection. |
| Trap placement | Place a trap, cancel another placement, and attempt an invalid target; for a door, check the opposing-wall explanation. |
| Worker summoning | Select the spell, see that a second click is needed, summon on valid ground and verify an invalid target or insufficient-mana reason. |
| Targeted spell | Select an available spell, identify a valid creature, cast once, try an invalid target and check the live cooldown message. |
| Hand placement | Pick up and drop an object; invalid ground must explain the rejection. |
| Existing UI behavior | Change resolution/UI scale and check readable panel text, click alignment, dragging, no covered action buttons, and edge scrolling near/over the HUD. |

Manual gameplay, final visual appearance and other-platform runtime behavior are
unverified. The assistant has not started the game. Step 2 remains incomplete
and the user has stopped the goal to redesign the plan. The matrix above records
the original verification scope, not an instruction to continue the stopped goal.
The goal's technical status is blocked; resume work only after new user instructions
and continue from this preserved fork state.

## Upstream coordination

GitHub was rechecked on September 6, 2026: [issue #4](https://github.com/tomluchowski/OpenDungeonsPlus/issues/4)
and [issue #6](https://github.com/tomluchowski/OpenDungeonsPlus/issues/6) remain open.
This task addresses their action-mode, target-validity and silent-click feedback
items. It does not resolve their tutorial, economy, creature-needs or broader
navigation/cursor requests; do not use issue-closing keywords for either issue.

[PR #29](https://github.com/tomluchowski/OpenDungeonsPlus/pull/29), the two-row
spell-button layout, remains open upstream; its existing layout is already in
the accepted fork baseline and is preserved here. GUI scaling is the preceding
fork dependency, submitted separately as [PR #53](https://github.com/tomluchowski/OpenDungeonsPlus/pull/53).
Any later action-feedback PR must be a separate functional contribution and
exclude this internal documentation and the roadmap.
