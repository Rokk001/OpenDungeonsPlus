# Map navigation

## Existing path and implementation boundary

The camera controls are committed on `fix/camera-controls`; full-map navigation
will use a separate functional branch after the menu-reset correction and the
parallel Windows build consistency correction are integrated.

GameEditorModeBase already owns the selectable minimap and routes its click
coordinates to CameraManager. Three renderers exist. MiniMapCamera has a fixed
30-tile view, MiniMapDrawn uses a fixed four-pixel tile grain, and MiniMapDrawnFull
already renders the entire map with tile-state listeners. There is no full-map
window, map toggle or minimap zoom interface. Reuse these paths, retaining live
GUI scaling and renderer selection; do not create another map data model.

Before reusing the full-map renderer, correct its existing vertical pixel
conversion: row zero currently writes at the texture height, one row beyond
the buffer. Both tile colours and the camera outline use that conversion.
Resource names also need an instance suffix for simultaneous minimap and map
views; preserve the default instance names for existing users.

The approved input behavior is a map toggle, left-click relocation and closure,
and right-click or the same toggle key to close without relocation. Minimap
zoom uses one button with opposite left/right actions, independently of world
zoom. The remaining focus shortcuts reuse existing room and fight-event data.
Detailed reference evidence remains in the private planning area.

Implementation continues on `feature/map-navigation` from camera follow-up
`abc19866`, retaining the complete parallel build correction. The full map
reuses MiniMapDrawnFull with a separate image/texture name. While it is open,
the one active minimap renderer is replaced by MiniMapCamera attached to a
pointer-following detail window, then restored with its previous zoom on close.
This avoids two cameras independently changing the shared minimap culling flags.
The existing frame/window input ownership blocks world actions and camera input;
closing the map must not release a world drag or drop held objects.

Minimap zoom scales the existing renderer's world span and matching click
conversion together, with the existing span as the initial level; a factor of
two per level is an implementation approximation, not a measured reference
constant. Keep the selected renderer and live GUI sizing. Full-map left click
and minimap left click relocate immediately while retaining the main view's
height and orientation; map cancellation preserves the current view.

Implementation and verification are in progress; no manual game test was started.

Tracing the focus shortcuts further shows that client entity loading does not
deserialize Room objects: room appearances arrive through Tile updates instead.
The server-side room list therefore cannot power client heart/portal focus.
Use connected, owned room-visual tiles from the existing client map, selecting
the tile nearest each component's centre; portal cycling follows their stable
map order and recomputes after ownership/removal updates. This needs no new
network message or duplicate persistent room model.

The isolated real-renderer check found that constructing a 100-by-60-tile
overview locks and uploads the full GPU texture separately for each tile patch:
opening took roughly 0.7-2.0 seconds depending on the selected minimap. Reuse
the existing pixel drawing and tile listeners with one CPU pixel image, then
upload once after construction or a dirty frame. This also lets the camera
outline be restored after tile/vision changes while the camera is stationary.

The culling lifecycle check uses the production CullingManager, Tile culling
flags and entity attachment transition with real Ogre scene nodes. Recreating
a minimap detached every tile parent child, including tiles still required by
the main view; unchanged attachment flags then prevented their reattachment.
192 of 384 checks fail before the fix. Clear only this culling manager's mask
through the existing per-tile attachment path, preserving the other view's nodes.

The normal minimap click handler bypasses the existing camera dialog/focus
guard. Move that unchanged guard into the shared game/editor base and apply it
only to game-mode minimap clicks; keep editor behavior intact. Dig-mark changes
also bypass tile-state listeners, so notify the existing listeners when a mark
is added or removed. The full-map image can then follow local mark changes
without polling or a second tile model.

The two drawn minimaps have duplicated, inconsistent terrain palettes; the
rotating renderer also omits room/creature states and paints unseen tiles grey.
Share their tile-colour selection through MiniMap, retaining both existing
projection/render paths and the separately selectable scene-camera renderer.
Use remembered terrain, current-vision creature markers, each owner's colour,
a lighter heart and animated unclaimed-room/own-creature markers. Only animated
overview patches need periodic refresh; stationary terrain remains event-driven.

The real scene/detail probe reproduces a lighting mismatch: the reused minimap
render hook hides every world light, reducing a green lit surface to ambient
only (green channel 0.063). Allow only the full-map detail view to retain world
lighting, while still hiding the hand light and tile preview; leave the normal
scene minimap's existing lighting policy unchanged. Two of five rendering
assertions fail before this correction.

## Checkpoint verification

The current implementation passes 1,163 installed-CEGUI controller/layout checks,
84 camera-dialog checks, 10 production dig-mark notification checks, 331 pixel
buffer checks, 138 real map-renderer checks, 28 palette/animation checks and five
real scene/detail lighting checks. Earlier unchanged focus/culling/jump checks
pass 12, 384 and 36 assertions respectively; the latter are included in the
576 native / 575 SFML camera/input results. The 63 Escape regressions pass.
The detail green-channel result is now 0.863 with world lighting, and the
normal scene minimap retains its previous lighting policy. Rendered map colours
were inspected in `map-palette-preview.png`; this is an isolated colour-key
fixture, not user gameplay or visual acceptance.

Logs and generators are under `build/windows`, using `map-gui`, `map-mark`,
`map-buffer`, `map-render`, `map-palette`, `map-detail`, `map-focus` and
`map-culling` prefixes. GUI/controller probes use real CEGUI with adapter map
objects; renderer probes use real Ogre textures/cameras and fixture tile data;
the separate culling probe uses production attachment/culling logic. None is a
manual game run. The Release rebuild and runtime preparation after these changes pass; the
September 6, 21:33:40 executable is recorded in BUILDING.md.

This is a functional checkpoint on the dedicated map branch, not completion
of the full navigation acceptance matrix. Direction markers and the default
presentation are addressed by the follow-up below; recorded interaction/framing
comparisons, game appearance and startup acceptance remain with the user.
README documents the new controls. Version 0.7.1 remains unchanged because no
release was requested; the project has no changelog. Internal comparison details
remain under `docs/internal/`, outside the contribution.

## Direction and default presentation follow-up

The drawn renderers already distinguish fortified wall tiles with the owner's
darkened colour, forming strips around claimed ground. The remaining direction
indicator belongs to the circular minimap image, shared by all three renderers;
extend that image with a clipped dotted line from the viewed location to the
first owned heart tile. Each renderer supplies its displayed centre, span and
rotation, so live resizing and camera rotation preserve the matching coordinates.
Show the direction in overview zoom levels and hide it in the closer view and
full-map detail window. Keep resource ownership with the image.

Use the existing rotating drawn map as the default colour-coded presentation;
retain explicitly saved renderer preferences and all three selectable renderers.
The pointer detail remains a scene-camera view. No separate map implementation
or new rendering dependency is needed.

The direction follow-up passes 667 checks with real image geometry and all three
map renderers: 132/176/352-pixel display sizes, five zoom levels, four rotations,
circle clipping, removed/enemy/unseen hearts, texture cleanup and retained saved
renderer selection. The composed Ogre/CEGUI check uses the actual map layout,
pointer controller and both map/detail renderers; its 11 assertions cover lit
scene detail, placement at the centre and opposite corners, and restored light
visibility. The rendered centre/corner images were inspected. Fixtures establish
rendering and ownership behavior, not original gameplay fidelity.

Evidence: `map-direction-probe-results.log`, `map-direction-preview.png`,
`map-composed-probe-results.log` and `map-composed-{1,50,99}.png` under
`build/windows`. The new Release build and runtime preparation pass for the September 6,
21:49:44 executable recorded in BUILDING.md. The follow-up retains
parallel held-creature checkpoint `6b248742` and its portrait-clipping parent
`d018f545`, both based on map checkpoint `6310df83`. No shared checkout or
index switch and no push are required. Version remains 0.7.1, with no release
requested; README and the camera shortcut note now describe the final controls.
