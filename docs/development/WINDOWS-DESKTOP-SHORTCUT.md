# Windows desktop shortcut

## Cause and scope

The reported installation has fullscreen, Keyboard Grab and Mouse Grab enabled.
The existing input setup consequently requests foreground exclusive DirectInput
keyboard access. Microsoft documents that exclusive access passively disables
the Windows logo key's shell action; no game mode previously handled it.
The installed input library still delivers the corresponding key events.

Handle both Windows keys before menu, editor, chat or gameplay key processing.
Minimize only the current foreground game window using the ordinary Windows
window API, leaving the configured grab settings and display mode intact.
The existing foreground input policy releases capture on focus loss, and the
renderer restores the desktop display mode when fullscreen loses activation.
Do not synthesize shell shortcuts, change security policy or close the game.
Non-Windows input remains unchanged.

References: [DirectInput cooperative levels](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ee416848(v=vs.85))
and [window minimization](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindow).

The production handler passes 452 isolated checks across Windows/non-Windows,
left/right keys, unrelated keys, missing/foreground/background windows and
repeat/restore sequences. OS calls are stubbed: the test never changes focus.
All three entry points are checked for priority before GUI key processing.
The existing idle-hand probe compiles but execution is blocked by application
control (4551); no security settings were changed. Release compilation passes
in `build/review-followups/desktop-menu-build.log`; actual desktop switching and
restoration remain user tests.
