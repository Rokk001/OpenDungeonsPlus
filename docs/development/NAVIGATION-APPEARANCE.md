# Navigation appearance

## Existing path and diagnosed gap

The existing game layout already places the 176-square circular minimap at the
lower left, with Query, Sell, Options and minimap zoom in its four corners. The
adjacent category row and content panel also occupy the measured design-plane
positions. Their callbacks, hit targets, scaling and keyboard alternatives are
already implemented and must be preserved.

The user's September 6 capture shows the remaining visual gap: the rendered map
ends as an unframed black circle, Sell uses a coin that describes payment rather
than removal, and the map zoom control displays `+/-` text. The accepted target
uses a substantial circular metal boundary, a destructive-action symbol for
Sell and a magnifier for the single two-direction zoom control. Moving controls
or adding new actions would not correct this gap.

Reuse the custom minimap image renderer to draw a scale-independent layered rim
inside the existing circular hit area. Reuse the existing crossed-tools removal
art for Sell. Create the simple magnifier through the same in-memory CEGUI image
path already used for generated hand feedback, then use the existing framed game
button style. This adds no copied reference asset, dependency or second control.

## Verification

The circular frame passes 1,027 renderer/scale/zoom/orientation checks. The
viewport overlay passes its 1,028 checks, while the map controller and camera
dialog retain all behavior across 1,163 and 84 checks. The four corner controls
pass 684 post-map-click hit-target checks, including registration and dimensions
of the generated zoom texture. The full interface matrix also passes at five
representative resolutions and 80%, 100% and 120% user scale.

The Windows Release build and runtime preparation pass. The executable is dated
September 6 at 23:05:49, is 4,201,984 bytes and has SHA-256
`a72e1ef155a17c76e0bf517947980480ee1b00aa890e72844cb4b6bca864071e`.
The generated circular-map preview was inspected and retains the existing map,
direction and viewport layers inside the new four-layer frame. The user already
accepted the underlying map controls; the new frame and symbols still require
visual acceptance. No game was launched by the assistant.
