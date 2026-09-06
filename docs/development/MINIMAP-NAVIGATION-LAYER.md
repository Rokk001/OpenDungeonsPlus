# Minimap navigation stacking

## Report and existing path

The user's September 6 capture at 22:25:59 shows the minimap covering its corner
controls after a click. The user reports that those controls become unclickable.
The existing `ModeGame.layout` gives both the minimap and its four corner controls
the same always-on-top group, but the minimap retains CEGUI's default rise-on-click
behavior. CEGUI handles the left-button press by moving that window in front of
siblings in the same group before the existing camera-click callback runs.
The circular camera check only rejects world navigation outside the circle; it
cannot restore the covered sibling controls or change their input ordering.

Reuse the existing layout setting already used by the adjacent category panel:
disable rise-on-click on the minimap, retaining its camera callback, rendering,
initial stacking and corner actions. Verify actual injected mouse clicks with
the installed CEGUI layouts before and after the change. Broader navigation
artwork/layout differences are a separate functional task; do not bundle them
into this click regression.

## Verification

The production layout and existing GUI scaling code were loaded with the
installed CEGUI runtime. Injecting a minimap click followed by corner-control
clicks reproduced 640 failures in 680 checks before the correction; all 680
checks pass afterward. The matrix covers five resolutions from 800x600 through
3840x2160, 80/100/120/100 percent scale transitions, expanded/collapsed content,
three hit positions per corner control and actual click-event delivery.
The minimap still receives its own click. Logs and generator are under
`build/windows`, using `minimap-layer`; the failure log is
`minimap-layer-before.log`. No game was launched; the user must confirm the
reported interaction in the game.

Only the minimap's click stacking changes. Version 0.7.1 stays unchanged because
no release is requested; README controls remain accurate and need no new binding
description, and there is no changelog. The development index and build record
are updated with this functional fix.
