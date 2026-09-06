# Hand feedback over navigation

Work branch: `fix/navigation-hand-feedback`, continuing from the complete
contextual-selling checkpoint and the parallel shadow documentation closure.

## Existing behavior and identified gap

`GameMode::refreshActionFeedback` already detects interface hover through the
same CEGUI hit test used by gameplay input. It clears world previews, creature
highlights and pointer messages, hides the action symbol and exposes the hovered
control's description. Returning to the world recomputes the current action.

The final pose decision nevertheless excludes interface hover from pointing,
so navigation always requests the restless idle hand, even on a clickable
control. `RenderManager` already provides a pointing pose on the existing
licensed hand rig; no new cursor asset or separate input path is needed.

## Scoped correction

Request the existing pointing pose over interface surfaces, independently of
the selected world action, held-object count or paused state. Preserve the
world pose decision, hidden world indicators and existing input ownership.
Retain pickup/drop/slap animation completion and the hand's current coordinates,
scale, held-object layout and visibility shortcut.

## Verification

All 178 focused controller checks pass, including 24 navigation combinations
that failed before the correction: empty/occupied hand, no action/build/dig,
paused/running and valid/invalid world targets. They verify the requested pose,
hidden world feedback, unchanged selection and inventory, no world command,
the control description and restoration on return to the world. The inherited
release guards also pass. These probes execute the production feedback/release
bodies with simulated GUI, map and renderer endpoints; they do not prove a
rendered pose or real mouse hit tests.

Release compilation and runtime preparation pass. Logs are
`build/windows/navigation-hand-probe-results.log`, `navigation-hand-build.log`
and `navigation-hand-runtime.log`. The prepared executable is dated September 6,
2026 at 18:39:33, SHA-256
`2590b059ff405e0eba52b6b1d455112933f7481142605824876ac69bd1176226`.
No game was launched. Manual visual acceptance belongs to the user, especially
entry/exit across navigation and after a display or UI scale change. This
correction does not claim new artwork, measured animation timing or a redesigned
cursor hotspot.

The README and development index describe the changed behavior. Version remains
0.7.1 because this is a development correction, not a release; the checkout has
no changelog. The task remains a separate functional contribution, with private
comparison evidence excluded from future upstream submissions.
