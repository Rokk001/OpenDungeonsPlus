# Shadow coverage correction

## PR #48 update delivered on September 6, 2026

The user explicitly authorized pushing this correction to their fork and updating
the existing PR #48. The contribution is assembled in the isolated worktree
`build/pr48-shadow-update`, branch `pr/shadow-coverage-update`, based on the
published PR head `dbae842197c299cdf18c8d5d86d9c15ec2cfa54f`. It contains 90
functional files only: the 88 reviewed shader/material/camera files match
`fe86bf03`, and the existing shadow-settings helper is reused in the older PR's
RenderManager initialization. The initialization occurs after resource groups
are initialized, as in the full fork. No later fork features or internal notes
are added to this contribution.

The probes rebuilt against the actual contribution resources and helper pass
all 73 receiver cases, 146 repeated settings checks, 60 lighting checks and the
instanced-fog/vertical-wall renders. Logs are `build/windows/pr48-coverage-*.log`,
`pr48-light-results.log` and `pr48-surface-*.log`. The full isolated Windows
Release build passes in `pr48-shadow-build.log`, with successful configuration
in `pr48-shadow-configure.log`. Its executable is dated September 6 at 18:46:34,
SHA-256 `fd7c41efff5359da76e17c9079945a11e77b61c71b933ee2b6f27d5acdb6be35`.
The current full-fork runtime and unrelated shared working changes are preserved.
This remains a bug fix without a version bump or a new README feature; there is
no changelog file.

Commit `6862d3b63c507c4ad94d2580632d7b0a3149ee2b` was pushed normally to the
user's `origin` branch `fix/dynamic-shadows`, advancing it from `dbae8421`.
GitHub confirms that [PR #48](https://github.com/tomluchowski/OpenDungeonsPlus/pull/48)
now points to that exact commit and remains open and ready for review.
The isolated contribution worktree is clean; the shared checkout remains on
`fix/shadow-coverage`. No other branch was pushed, and no PR comment was posted.
A separate maintainer reply must still be shown to the user and approved before
it is posted. Linux runtime and the original full-map reproduction remain
unverified; the local shadow work is closed and room lighting is a separate task.

## Local branch closure on September 6, 2026

The user requested closing the shadow work after the final review and handling
room lighting separately. The review found no new blocking defects in the
shadow correction; no further production changes were necessary.
Functional commits are `99e80b2d` and `fe86bf03`. Verification comprises 60
lighting checks, 73 receiver cases, 146 settings checks, 33 portraits, the
additional instanced-fog/wall renders, the Release build and the user's
18:18-18:19 screenshots. The named-map and Linux verification limits below
remain accurately recorded; they are not reported as tested.

The functional work is closed locally on `fix/shadow-coverage`; room lighting
is a separate follow-up. PR #48 is already open and ready for review, with
published head `dbae8421`; the two local correction commits have not been
pushed at that checkpoint. The subsequent push authorization and contribution
preparation are recorded above; reply approval is still separate.
The final checkpoint changes only this task's development note, build-history
entry and documentation-index link. The game version and root README need no
additional change for this bug fix; no release or new player-facing feature
was introduced and this repository has no changelog file.

## User screenshot review at 18:18-18:19

The user supplied `ODscreenshot_2026-09-06_181846_0.png`,
`ODscreenshot_2026-09-06_181848_1.png` and
`ODscreenshot_2026-09-06_181905_2.png` and requested their comparison with the
reference. All three were inspected. The earlier solid-black floor wedges are
absent, surface detail remains visible and the hand illuminates a local area;
the library and dormitory furniture still cast visible shadows. This supports
the reported shadow correction in an actual user game. The remaining visual
difference is the dark, uniform illumination outside that local area.

The current game log identifies the loaded save as
`saves/2026-09-06_134654-SK-DuelToDeath.level`. Its `[Lights]` section contains
no entries, and the run logs no added map lights. The room implementations do
not create map lights; the renderer creates the hand point light and renders
map lights supplied by the level. Thus changing how additional existing lights
are accumulated would not brighten this particular save. The configured ambient
slider value is 100, and constructing the settings window applies that value
through the existing ambient-light setter; this is not evidence of an ignored
brightness setting.

Reference-like room-local lighting would require an additional lighting feature
or level light placement, beyond repairing shadow reception and preserving
ambient light. No such source, placement or intensity has been invented or
added to the shadow contribution. The screenshot comparison does not establish
complete lighting parity; the user subsequently deferred room lighting to a
separate task and requested closure of the shadow branch.

The live PR #48 comment was rechecked after this review: the maintainer's
request remains missing creature shadows and missing receiving surfaces, with
Forgotten Treasures as the suggested reproduction. The local rendering checks
cover those receiver paths, but the user's latest captures are from the save
identified above, not that named map. Do not describe them as confirmation of
the maintainer's exact full-map reproduction. No reply or push had been made at
that review; subsequent delivery is recorded above.

### Prepared maintainer reply, not posted

I've pushed the shadow projection and receiver fix and corrected the solid-black
shadows. The Windows build and isolated rendering checks pass; the original
Forgotten Treasures reproduction still needs a manual retest.

## User rejection: cursor-light shadows on September 6

The user's 16:36:21, 16:36:27, 16:36:32 and 16:36:35 captures in the
Windows user-data directory show long, fully black shadows from room furniture
as the cursor moves. The earlier isolated coverage checks did not exercise
crowded rooms or assert that ambient illumination survives occlusion; their
passing results do not establish visual acceptance.

The existing hand light is a point light at height 2 with attenuation
`(500, 1, 0.09, 0.032)`. Custom floor, wall and creature shaders ignore that
attenuation and multiply ambient illumination by the shadow comparison.
Consequently a distant occluder can erase all floor detail even where little
cursor illumination should reach. Generated Ogre materials already separate
ambient illumination and apply distance attenuation.

Extend the existing custom lighting path: leave ambient illumination outside
the shadow multiplier and consume the existing light's attenuation parameters,
preserving its position, colour and configured falloff. Verify a furnished room,
ambient-only controls and near/far cursor positions in addition to coverage and
settings restoration. Reference appearance evidence is kept in the internal
reference baseline; it does not establish original engine constants.

The correction now separates ambient light in all seven affected custom
fragment shaders and adds one attenuation binding to each of their 73 material
program definitions. The shared calculation uses Ogre's existing range,
constant, linear and quadratic parameters; directional lights bypass it.
No light position, light colour, ambient setting or shadow projection changed.

Verification on September 6 at 16:51:

- The furnished-room control with nine actual Bookshelf meshes and a Wizard
  failed all 48 initial checks before the correction. Depending on cursor
  position, roughly 31,000-60,000 floor pixels lost their ambient illumination.
- All 60 final checks pass: six surface materials at four near/far cursor
  positions retain ambient illumination while receiving shadows and obeying
  the configured falloff. Additional range and directional-light checks pass.
  The falloff test independently doubles all attenuation coefficients and
  compares the rendered direct-light contribution; low-light pixels are
  included with two-channel-value quantization tolerance.
- 73 existing receiver cases and 146 settings-toggle checks pass, as does the
  real 33-creature portrait/cache/material-isolation/cleanup probe.
- Before/after images confirm visible floor detail instead of solid black
  wedges. Physically projected shadows remain; distant hand-light influence
  now fades with the already configured distance attenuation.
- Release compilation and runtime preparation pass in `cursor-light-build.log`
  and `cursor-light-runtime.log`. The executable remains the 16:39:18 build,
  SHA-256 `141f56e38665bfab44df3741f82cbc46213637978990a4d256f7316129759024`;
  this correction changes shader/material resources, which the prepared
  runtime loads directly from the repository through existing junctions.
  Initial runtime staging collided with this task's still-running Ogre probe;
  it completed successfully after that probe exited normally.

Evidence is retained under `build/windows/cursor-light-*`; regenerate/rebuild
the probe with `make-cursor-light-probe.py` and `build-cursor-light-probe.ps1`.
The shadow coverage and portrait probe sources remain as described below.
The additional surface probe now renders 49 actual hardware-instanced
`FogOfWarDirt.mesh` instances with the game's material and custom-colour path.
It passes the nonempty-image, ambient-preservation and attenuation checks:
330,969 evaluated channels, zero falloff mismatches and zero pixels below
ambient. A row of actual `Claimed_fl_0000.mesh` walls using `DCW0000` passes
the same checks and receives 2,809 shadow pixels outside the projected
bookshelf bounds; the measurement excludes the caster itself. This closes
the earlier planar-wall and unrendered-instancing verification gaps.
Sources, logs and images: `build/windows/make-cursor-surface-probe.py`,
`cursor-surface-probe.cpp`, `cursor-surface-instanced.log`,
`cursor-surface-wall.log` and `cursor-surface-*.png`.
These checks required no further production changes.

No version bump or new README feature entry is required for this shader bug
fix; no changelog exists here.

The subsequent user captures and their scoped review are recorded above.
No game was launched by the assistant, and reference parity or the original
full-map reproduction are not claimed from isolated renders.

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

- The disabled-receiver control fails all eight floor cases with zero shadow pixels:
  `build/windows/shadow-coverage-pr48-final-results.log`. This control uses the
  current resource files with their default shadow uniforms disabled; it is not
  the submitted PR's full initialization or a rebuilt Linux PR binary. The
  submitted constructor does attempt to enable receivers on its selected pass;
  this control alone does not establish how every original PR receiver behaves.
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
unverified. The authorized PR update is recorded above; no GitHub reply has
been posted.
