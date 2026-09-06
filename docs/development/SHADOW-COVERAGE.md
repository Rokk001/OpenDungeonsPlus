# Shadow coverage correction

## Report, baseline and existing path

PR #48's maintainer reports missing creature shadows and shadow reception on
many surfaces, using Forgotten Treasures with a large excavated room as the
reproduction case:
https://github.com/tomluchowski/OpenDungeonsPlus/pull/48#issuecomment-5558874885

Work branch: `fix/shadow-coverage`, from the complete fork at `3511b86e`, retaining
the uncommitted creature portrait work and all existing local documentation.
PR #48 remains at `dbae8421`; changes will first be verified on the current fork.

The submitted PR switches to integrated texture shadows to retain the custom
fragment shaders and avoid the diagnosed GL3Plus crash. Integrated shadows
require the receiving material to consume the shadow texture. Most custom
materials default their `shadowingEnabled` uniform to false in the submitted
PR. Later live-settings work already enables that uniform through
`RenderManager::setDynamicShadowsEnabled()`, invoked after resource initialization;
reuse that path instead of adding another settings mechanism.

An additional concrete gap remains in the current fork: every `dirtGround`
entry in `config/tilesets.cfg` uses `Room.mesh` with material `Dirt`, whose vertex
shader does not output a shadow coordinate, whose fragment shader always uses
an all-white shadow multiplier, and whose material does not bind a shadow map.
Consequently this excavated surface cannot receive creature shadows even when
the setting is enabled. Existing room and claimed-tile receivers will serve as
comparison paths during the focused rendering checks.

The correction will extend the existing integrated-shadow receiver path for
the demonstrated gaps while preserving the crash fix, current lighting and
live settings. Further changes require evidence from the affected render path.

## Verification status

The isolated render probe uses the real Wizard mesh, an excavated grid of
Room.mesh tiles, the game's 0.02 near clip and a point light at hand height 2.
The default shadow camera aims above the floor because its target distance is
derived from the near clip. Raising shadow distance alone also clips casters
and produces stretched border shadows with the existing clamped samplers.
Ogre's existing plane-optimal projection covers the visible ground, provided
its separate culling frustum uses the same view/projection matrices; the camera's
own view matrix must be requested explicitly, otherwise Ogre returns the old
culling view. This restores projected creature silhouettes on Claimed and Farm.

Dirt, GoldGround and Gold had no receiver implementation. Their existing
shaders/materials now bind the shadow texture, using the deformed
world position for projection and rejecting coordinates outside the texture.
Ogre-generated room materials additionally need its integrated shadow render
state; the probe demonstrates shadows on Treasury and GemGround with that state.
Their ambient light remains visible inside shadows, so a fixed absolute image
brightness threshold is insufficient for dark textures.

Restoring the projection also exposes an existing receiver defect: colour masks
darken the caster itself and any surface in front of it. The Wizard becomes
black when its caster flag is enabled. The correction uses Ogre's existing
16-bit depth shadow texture support and compares receiver depth in the shared
custom fragment path, keeping the current lighting outside shadowed pixels.
Claimed/Room/DCW shadow coordinates now use their deformed vertex positions and reject samples
outside the light frustum to prevent border streaks.

The settings helper only enables a custom receiver when its pass actually binds
a shadow texture; the fog material does not bind one. The integrated Ogre render
state is added/removed on settings changes without duplicating it.

## Automated evidence on September 6, 2026

- The PR #48 settings path fails all eight floor cases with zero shadow pixels:
  `build/windows/shadow-coverage-pr48-final-results.log`. This control uses the
  current resource files with their default shadow uniforms disabled, matching
  the submitted PR's initialization; it is not a rebuilt Linux PR binary.
- The corrected path passes 73 receiver cases: eight materials over five
  camera/light placements, a second-light case, and Wizard/Dragon/Slime at
  Forgotten Treasures' first starting position (85,60), plus the DCW wall shader.
  The wall shader was exercised on the same planar test geometry; a complete
  walled room is still part of the user acceptance test.
- Image checks exclude the creature, project its bounds from the selected light
  onto the ground, and require shadow pixels inside that envelope without streaks
  outside it. Dark textures are checked by relative brightness as well as a
  minimum two-channel-sum change. All cases report zero unexpected shadow pixels.
- 82 repeated settings checks pass: shadows disappear, reappear identically,
  and only one integrated render state remains after enabling twice. With one
  light, the disabled image also matches the non-casting control; with two
  lights, Ogre's existing light reordering prevents that exact comparison, so
  that case checks restoration and state count instead.
- The existing isolated portrait check, copied with shadow initialization and
  a main-scene point light, renders all 33 creature portraits and passes cache,
  material isolation and cleanup checks: `shadow-coverage-portrait-results.log`.
- Windows Release compilation and runtime preparation pass in
  `shadow-coverage-build.log` and `shadow-coverage-runtime.log`.
  The executable timestamp is September 6, 2026 at 16:21:10, SHA-256
  `b77a3ddbc2755808f760cdf854b00164bbad823b28165f421a2df3dbf0452aa5`.
  It contains the current shared fork, including the parallel creature-panel
  work; that work is not part of this shadow contribution.
- The probe still reports the pre-existing missing Panels_Diffuse texture in
  inherited materials; this task does not replace unrelated texture assets.

Probe sources, commands, logs and before/after PNGs are retained under
`build/windows/shadow-coverage-*`. Rebuild the isolated probe with
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File build/windows/build-shadow-coverage-probe.ps1`,
then run `shadow-coverage-probe.exe current 6 Dragon.mesh` from `build/windows`.
The generated probe header extracts the actual production settings helper and
includes the production shadow-camera setup directly.

No game was launched. Manual acceptance remains with the user: open the prepared
Release executable, enable shadows, load Forgotten Treasures, excavate a large
room and check moving creatures across dirt/claimed/room floors while moving the
hand light, zooming and rotating the camera; also toggle shadows off and back on.
Linux runtime and the maintainer's original full-map reproduction remain
unverified. No push or GitHub reply has been made for this correction.
