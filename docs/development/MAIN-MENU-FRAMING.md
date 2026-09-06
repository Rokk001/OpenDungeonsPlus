# Main-menu scene framing

## Existing path and diagnosed gap

`MenuModeMain::activate` loads the existing menu layout and starts the existing
scripted 3D scene through `ODFrameListener::createMainMenuScene`. The scene file
sets one fixed camera position and orientation. The renderer then gives that
camera the full window aspect ratio while retaining its vertical field of view.

The scene and GUI assets use an 800-by-600 design plane. At that authored 4:3
aspect ratio, the scripted camera framing is unchanged. A 3440-by-1440 viewport
is about 1.79 times wider, so the current projection exposes about 79 percent
more scene horizontally and makes the intended menu composition appear much
farther away. Resetting inherited camera motion does not correct that projection.

Reuse the existing camera and scene. While the main-menu scene is active, derive
the vertical field of view from the actual viewport aspect ratio so the authored
horizontal field of view remains constant. Restore the previous field of view
before entering the game or editor, and reapply the menu projection after a live
window resize. This changes only the menu scene framing.

## Verification

The real Ogre camera probe passes all 339 checks. It keeps the horizontal field
of view constant at 800x600, 1280x1024, 1920x1080, 2560x1080, 3440x1440 and
3840x2160, handles resize transitions, treats repeated activation idempotently,
restores both the default and a customized gameplay field of view, and retains
all existing movement, zoom, rotation, preset, map-jump and scripted-reset checks.

The Windows Release build and runtime preparation pass. The executable is dated
September 6, 2026 at 22:50:03, is 4,197,888 bytes and has SHA-256
`f9ef830a6eeb858db7e4abc667488f27f437a0b1504b60b8db84f3aca10f2350`.
Evidence is in `build/windows/camera-probe-results.log`,
`main-menu-framing-build.log` and `main-menu-framing-runtime.log`. No manual game
test was performed; the user still needs to confirm the menu composition visually.

The game remains version 0.7.1 because no release was requested. No public
controls or settings change, and the project has no changelog.
