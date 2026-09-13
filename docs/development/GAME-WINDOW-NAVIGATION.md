# Exclusive in-game window navigation

The September 13 screenshots show the options menu and then level objectives
over an already-open production window. Research and production already close
existing dialogs when selected, but the other navigation entry points do not.
The earlier fixture bypassed the real options-opening handler and consequently
did not cover the reported production -> F10 -> objectives sequence.

Apply the existing close dispatcher when opening objectives, options, help,
player information, camera definitions and settings navigation as well. Preserve
their existing close/cancel callbacks and submenu return behavior. Reset the
options page before closing windows so the end-game Back handler cannot recurse
into reopening the same end-game page. Production ordering and the accepted
sleep/cursor behavior remain unchanged. This client-only correction needs no
save, packet or version change.

Verification on September 13: the isolated installed-CEGUI fixture executes the
real opening handlers and close dispatcher at four resolutions and three UI
scales. The original 576-check matrix passes after the correction; the baseline
had 48 failures. Expanded coverage also invokes the actual settings Back and
camera-return callbacks: all 624 checks pass. Settings contents and camera
movement are stubbed; navigation uses the real layouts and mouse events.
Reproduce with `build/windows/build-production-ui-probe.ps1`; the generator and
logs remain local build artifacts. Release compilation and runtime preparation
pass. The game was not launched; user acceptance remains pending.
