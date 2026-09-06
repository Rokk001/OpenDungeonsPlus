# Escape navigation

## Existing behavior and authorized scope

The user confirmed the F10 Options fix, then reported the same missing
close/back behavior throughout game navigation and the main-menu settings,
skirmish and other submenus. The 13:21 captures show exit confirmation over
research, objectives and the event-message surface.

Work branch: `fix/escape-navigation`, from the complete, preserved fork at
`32550ad8`. The earlier Options-only correction is retained in its own checkpoint.

Most windows already bind their title-bar close button to the correct cancel
or back handler. Settings cancellation restores the controls and releases modal
input; research cancellation discards pending selection; seat configuration
performs connection cleanup before requesting the preceding mode. Reuse these
handlers rather than hiding every window without its cleanup.

The shared front-end keyboard handler previously only injected keys into CEGUI.
The game handled Escape as exit confirmation except for Options; the editor
returned early for save/load/new input modes before its Escape switch. The main
menu's three category submenus are unframed and use their own existing toggles.

The correction performs one close/back step per Escape: close transient lists and the frontmost
dialog through the existing close event, then use the existing menu back path
where no dialog handled it. Main-menu category panes close without leaving the
main menu. Chat/console keep ownership of their existing Escape handling; the
game event surface closes without deleting stored messages. No Escape path may
apply settings, start a level, confirm quitting or bypass lobby cleanup.

Upstream was fetched at `be44649f`; the open inventory remains 12 issues and
19 PRs. No upstream code was imported. The clipped confirmation text is a
separate visual finding, not part of this keyboard-navigation correction.

## Verification

The headless CEGUI probe loads the actual layouts and extracts the affected
production input, close, cancel and back functions. Against `32550ad8`, 49 of
63 checks fail; with the correction all 63 pass. The first corrected run exposed
a duplicate editor Options close subscription, which toggled the window twice
and reopened it; removing that duplicate makes Escape and the close button use
the existing toggle once.

Coverage includes game Options, objectives, help, player settings and research
at 800x600 and 3440x1440; frontmost and stacked dialogs; message preservation;
chat/console ownership; settings cancellation and modal confirmation order;
open dropdowns; main-menu category panes; eight front-end screens; lobby
cleanup; and editor save/load/new, help, portal waves and File menu closure.

The probe uses real CEGUI key dispatch, window ordering and modal state, with
test doubles for game state, connection endpoints and configuration reset.
It verifies existing cleanup callbacks are selected, not a live multiplayer
disconnect, saved configuration or complete gameplay session. Logs and local
diagnostic helpers are under `build/windows/`:

- `escape-navigation-before.log`: 63 checks, 49 failures.
- `escape-navigation-after.log`: 63 checks, zero failures.
- `generate-escape-navigation-probe.py` and `build-escape-navigation-probe.ps1`:
  generator and build helper, reusing the existing local layout probe setup.
- `escape-navigation-build.log`: Windows Release build succeeded.
- `escape-navigation-runtime.log`: runtime preparation succeeded.

The prepared executable is `build/windows/opendungeons-plus.exe`, SHA-256
`53e580c640ffa264e6a4756322cd0bb8dc0d542f3e730d78c5780ee39dc42156`.
The assistant did not launch the game. On September 6, the user explicitly
confirmed that Escape is fixed and works everywhere, following the request to
test game windows and main-menu settings/skirmish navigation. This completes
the reported Escape correction's user acceptance; it does not certify the
separate hand-feedback, visual-comparison or display-change test matrix.

README now describes the shared close/back control, and the development index
and current build record link this correction. Version remains 0.7.1 because
this is a development bug fix, not a release; the repository has no changelog.
No push or upstream PR was made for this task.
