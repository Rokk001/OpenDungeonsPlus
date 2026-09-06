# Configuring and compiling on Windows

The latest Release build adds the camera controls in
[the camera note](CAMERA-CONTROLS.md), retaining the complete room-lighting fork.
Built on September 6 at 20:08:51, its SHA-256 is
`06a56d3703419cfd5a83e5a52be110f6d14ebb093ea715746f175b2f476383ee`.
The Release build, runtime preparation, 278 camera checks, 84 GUI checks,
63 Escape checks and 227 hand-rotation checks pass. Manual gameplay and Linux
remain unverified. Logs use the `camera-controls`, `camera-probe` and
`camera-gui-probe` prefixes in `build/windows/`.

The latest Release executable includes the corrected hand orientation and tool
grip, picker counts and current parallel room/camera work. All 94 focused grip
checks pass with shadows off and on; six rendered layer comparisons verify
finger/shaft occlusion, and 11 other-pose images remain unchanged. The separate
orientation probe passes 39 checks; the earlier picker probe passes 911 checks.
After the parallel task corrected its camera compilation error, Release build
and runtime preparation pass in `build/windows/hand-grip-release-rebuild.log`
and `hand-grip-runtime.log`. The executable at `build/windows/opendungeons-plus.exe`
is dated September 6, 2026 at 20:04:49, size 4,170,752 bytes, SHA-256
`5c0a25e0fdff21d906bcb5e60a6e6c83b5d21513bbb6e74c39b02d2b3218a2ed`.
No game was launched; manual visual acceptance remains with the user. See
[hand orientation](HAND-ORIENTATION.md), [tool grip](HAND-TOOL-GRIP.md) and
[picker counts](CREATURE-PICKER-COUNTS.md) for scope and verification limits.

The preceding Release build adds local lighting to visible rooms and restores
overlapping light contributions and ambient colour on custom world materials.
All 18 focused room-lighting checks, 60 ambient/falloff checks, 73 shadow-receiver
cases, 146 settings checks and the instanced-fog/wall renders pass. Release
compilation and runtime preparation pass in `build/windows/room-lighting-build.log`
and `room-lighting-runtime.log`. The prepared executable is dated September 6,
2026 at 19:38:14, SHA-256
`26b63a78da44873fe3eb27c9dd843bb2305db2084bee434052a7da143ec0b187`.
It retains the complete hand-tool/navigation and shadow baseline. No game was
launched; manual appearance and Linux runtime remain unverified. See
[room lighting](ROOM-LIGHTING.md) for evidence and test boundaries.

The latest Release build adds texture mapping and separate wood/metal materials
to the existing hand tool. All 521 geometry/material checks and six isolated
GL3Plus render views pass; corresponding shadow-on/off images are identical.
Release compilation first used `build/windows/hand-tool-stage` while the user
was playing, then rebuilt the normal executable after the game closed.
Logs: `build/windows/hand-tool-build.log`, `hand-tool-runtime-build.log` and
`hand-tool-runtime.log`. The prepared executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 18:58:11;
SHA-256 `66d0f7d258b88525f892faa59c39fb43cb82314ee96fad54c6c244c72ee5e302`.
It preserves the full navigation/selling/query/hand and parallel shadow baseline.
No game was launched; manual visual acceptance remains open. See
[textured hand tool](HAND-TOOL-MATERIAL.md) for exact verification boundaries.

The preceding Release build requests the existing pointing hand over interface
controls and restores the world pose on exit. All 178 focused controller checks
pass, including 24 previously failing navigation scenarios; Release compilation
and runtime preparation pass in `build/windows/navigation-hand-build.log` and
`navigation-hand-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 18:39:33;
SHA-256 `2590b059ff405e0eba52b6b1d455112933f7481142605824876ac69bd1176226`.
It preserves the complete selling/query/hand and parallel shadow baseline. No
game was launched; visual acceptance remains with the user. See
[navigation hand feedback](NAVIGATION-HAND-FEEDBACK.md) for test boundaries.

The preceding Release build adds a common minimap Sell toggle for the pointed room
tile, trap or door. All 70 focused sale/packet checks, 3,643 installed CEGUI/Ogre
layout checks and 56 creature-query regression checks pass. Release compilation
and runtime preparation pass in `build/windows/contextual-selling-build.log`
and `contextual-selling-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 18:16:46;
SHA-256 `f09479c82a868637aa55a7978fdfdf66fd263036ce3a41d4e7c79090b192ead3`.
It preserves the full creature-query, hand and parallel lighting baseline.
No game was launched. See [selling from the minimap](CONTEXTUAL-SELLING.md) for
the manual check and verification limits; live sale/refund acceptance is open.

The preceding Release build adds selectable creature inspection beside the minimap,
reusing the existing statistics windows. All 56 behavior checks and 3,563 installed
CEGUI/Ogre layout checks pass, as do Release compilation and runtime preparation.
Logs: `build/windows/entity-query-build.log` and `entity-query-runtime.log`.
The executable at `build/windows/opendungeons-plus.exe` is dated September 6, 2026
at 17:57:58; SHA-256
`c28f1b651dad76f4b848440d1b49964350bac75c108b996f8fbf7aa149ac6fb9`.
It preserves the complete hand-rotation and parallel lighting baseline. No game
was launched. See [entity information selection](ENTITY-QUERY.md) for the manual
check, test boundaries and the outstanding trap-range part of this tool.

The preceding Release build fixes held-object spacing after rotation and ensures
that drop requests/replies identify the selected object. All 227 focused checks
pass (164 failures before the correction), as do Release compilation and runtime
preparation. Logs: `build/windows/hand-rotation-build.log` and
`build/windows/hand-rotation-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` is dated September 6, 2026 at 17:34:49;
SHA-256 `e5db5cf2eb7d38b077f219c6d20aa3b51e4b79d26a1b1b3e2d345673315462c9`.
It preserves the full event-message, creature-selection and lighting work. No
game was launched. See [the hand-rotation note](HAND-ROTATION.md) for the manual
check and older-endpoint limitation; live gameplay/multiplayer acceptance remains
with the user.

The preceding Release build corrects lost path separators/bracketed names in event
messages, retaining the full creature-selection and lighting baseline. All 504
focused CEGUI rendering checks pass (156 failures before the correction), along
with Release compilation and runtime preparation. Logs:
`build/windows/event-message-paths-build.log` and
`build/windows/event-message-paths-runtime.log`. The prepared executable is
`build/windows/opendungeons-plus.exe`, September 6, 2026 at 17:18:02; SHA-256:
`71000f94b27c1406e4be50193c6b4924be748d5e331c38969ceb83ef6b1363d0`.
No game was launched. See [the display correction](EVENT-MESSAGE-PATHS.md) for
the exact evidence and manual check; this does not certify save/load behavior.

The preceding Release build adds highest/lowest eligible creature selection through
the documented portrait/count shortcuts, preserving the complete dialog/panel
and lighting work. Compilation and runtime preparation pass in
`build/windows/creature-level-selection-build.log` and
`creature-level-selection-runtime.log`. The prepared executable timestamp is
September 6, 2026 at 17:02:57; SHA-256:
`4f3a6b35d625897dcb66662bad4bc9a2aa15636869ab1b64237447e2bdf026dc`.
The real panel probe passes 847 checks, keyboard OIS 21 and SFML 324, and the
production SFML wrapper compiles with the installed SDK. User gameplay acceptance
of these gestures is still pending; no game was launched. See
[the selection note](CREATURE-LEVEL-SELECTION.md).

The subsequent `fix/quit-dialog-layout` correction widens only the exit dialog
and replay checkbox to prevent clipped text. All 260 focused CEGUI checks and
the isolated rendered preview pass. The prepared executable below loads this
XML directly through the verified `build/windows/gui` junction on its next start;
no additional compile is needed. See [the correction note](QUIT-DIALOG-LAYOUT.md).

The completed September 6 cursor-light correction on `fix/shadow-coverage` preserves
ambient illumination inside shadows and applies the existing light falloff to
custom materials. The user's 16:36 captures rejected the earlier solid-black
furniture shadows. All 60 new lighting checks, 73 receiver cases, 146 shadow
toggles and the 33-creature portrait regression pass. Release compilation and
runtime preparation pass at 16:51 in `build/windows/cursor-light-build.log` and
`cursor-light-runtime.log`. The shader/material-only correction loads directly
through the prepared runtime's resource junctions; the executable is still the
16:39:18 build with SHA-256
`141f56e38665bfab44df3741f82cbc46213637978990a4d256f7316129759024`.
The user's 18:18-18:19 screenshots confirm that the solid-black room shadows
are gone; additional instanced-fog and vertical-wall checks also pass.
The user requested local branch closure and a separate room-lighting follow-up;
the exact named-map and Linux verification limits remain recorded in
[shadow coverage](SHADOW-COVERAGE.md), together with the PR update status.

The creature-panel integration now passes the Release build and runtime preparation
in `build/windows/creature-panel-verified-build.log` and
`creature-panel-verified-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` has timestamp September 6, 2026 at 16:39:18
and SHA-256 `141f56e38665bfab44df3741f82cbc46213637978990a4d256f7316129759024`.
It includes portraits, four population views, worker counts, pickup/focus controls,
and the final connection/knockout corrections, alongside the separate shadow
checkpoint `99e80b2d`. The data probe passes 77 checks, state/negotiation 1,117,
and actual Ogre/CEGUI controls/scaling 830. The user accepted the appearance in
earlier 16:22 captures; detailed gameplay/network and remaining visual comparison
are still open. No game was launched by the assistant. See
[the creature panel note](CREATURE-PANEL.md) and AGENTS.md for branch ownership.

The preceding tested creature-panel checkpoint was `3de2e020` on
`feature/creature-panel`, retaining accepted Escape
checkpoint `2d3e79dc` and the subsequent mood/activity prerequisites. Cached
portraits now reuse all 33 existing creature meshes; the isolated Ogre/CEGUI
preview verifies rendering, caching, material isolation and cleanup. Panel
controls are not connected yet. Release compilation and runtime preparation pass
in `build/windows/creature-portrait-build.log` and `creature-portrait-runtime.log`.
The prepared `build/windows/opendungeons-plus.exe` has timestamp September 6,
2026 at 15:43:01 and SHA-256
`cb9421b005d5ca84cc463b73ea8702b33207ce53a71e48278dc641591bc25e40`.
No game was launched. See [the creature panel note](CREATURE-PANEL.md).
During this build checkpoint another session changed the shared checkout to
`fix/shadow-coverage`. The portrait commit was created separately without
switching that checkout; see AGENTS.md before further Git operations.

At the preceding activity checkpoint, full mood and activity transmission were implemented
as prerequisites for the creature-panel views; the views remain incomplete.
The focused packet/negotiation/state probe passes 1,049 checks. The clean Release
build, final incremental build and runtime preparation succeeded in
`build/windows/creature-activity-clean-build.log`, `creature-activity-final-build.log`
and `creature-activity-runtime.log`.
The prepared executable is `build/windows/opendungeons-plus.exe`, timestamp
September 6, 2026 at 15:16:16,
SHA-256 `667e5f70ebe7d9822a67f53b526e8ee02adcf5065c394f2c86cf50be30be806f`.
It retains all accepted Escape and marking corrections. No game was launched;
network/replay runtime acceptance and the broader panel work remain open. See
[the creature panel note](CREATURE-PANEL.md).

The preceding complete fork was `fix/escape-navigation`, continuing directly from
the user-confirmed Options checkpoint `32550ad8`. All 63 focused headless
navigation checks pass (49 failures against the preceding checkpoint).
Windows Release compilation and runtime preparation succeeded in
`build/windows/escape-navigation-build.log` and `escape-navigation-runtime.log`.
The prepared executable SHA-256 is
`53e580c640ffa264e6a4756322cd0bb8dc0d542f3e730d78c5780ee39dc42156`.
Open `build/windows/opendungeons-plus.exe` directly to test Escape in settings,
front-end submenus and game dialogs; see [Escape navigation](ESCAPE-NAVIGATION.md).
On September 6, the user confirmed Escape is fixed and works everywhere;
the separate hand-feedback and visual/display-change checks remain open.

The preceding `fix/options-escape` build continued from pickup-label
checkpoint `9ae03c54`. The focused keyboard/window probe passes all 32 checks;
Release compilation and runtime preparation pass in
`build/windows/options-escape-build.log` and `options-escape-runtime.log`.
The executable SHA-256 is
`991829f9116aff7b7a5bb325ee49b1d193e6a174c46b0cf589ed8ecb7e2b3292`.
Open `build/windows/opendungeons-plus.exe` directly and test F10 followed by
Escape; see [the Options correction](OPTIONS-ESCAPE.md).

The preceding `fix/pickup-target-description` build continued from
wall-outline checkpoint `fcb9714c`. Release compilation and runtime preparation
succeeded in `build/windows/pickup-description-build.log` and
`pickup-description-runtime.log`. The executable SHA-256 is
`3c4989a48148e88f23b4ba2c3a6d1453c5fe3f139d36388c118ef6774ce6e4e8`.
Open `build/windows/opendungeons-plus.exe` directly. The user test of object
descriptions is pending; the user's 13:07 captures show visible wall-hover/drag
outlines, without establishing mark completion or cancellation; see
[pickup target descriptions](PICKUP-TARGET-DESCRIPTION.md).

The preceding `fix/wall-hover-outline` build started from the accepted
HUD checkpoint `c450a6cc`. Release compilation and runtime preparation succeeded
in `build/windows/wall-outline-build.log` and `wall-outline-runtime.log`.
The wall geometry probe passes all 187 checks. Open
`build/windows/opendungeons-plus.exe` directly. The later 13:07 user captures
show visible outlines during hover and dragging; complete gesture and display
change checks remain pending. See [wall hover outline](WALL-HOVER-OUTLINE.md).
That build's executable SHA-256 was
`53dda20bd04dc7548ccb4b8d79237359536dd321801e03bdfcc4d3d41a7e7f5a`.

The preceding `fix/hud-interaction-regressions` build started from
the full hand-feedback checkpoint `c6cbb259`. The September 6 clean Release
build, final incremental build and runtime preparation succeeded. This build
corrects HUD edge scrolling, save/message visibility and square buttons while
retaining all preceding fork features. Logs: `build/windows/hud-regressions-clean-build.log`,
`hud-regressions-final-build.log` and `hud-regressions-runtime.log`.
The CEGUI interaction probe passes 357 checks; the layout/scaling probe reports
zero failures. See [the HUD correction record](../internal/README.md).
Open `build/windows/opendungeons-plus.exe` directly. On September 6, the user
confirmed the reported HUD issues are fixed; see the scoped acceptance record
in the HUD note. No game was launched by the assistant.
The executable SHA-256 is
`09b145a07c1a7eb648e8294b58c6b1cc12ed0ce6f789c43efe5725cff1712462`.

Earlier interface build checkpoints are retained in the [local planning index](../internal/README.md).

For the preserved `feature/action-state-feedback` prototype, the September 6 Release
build and runtime preparation succeeded; see [action feedback](ACTION-STATE-FEEDBACK.md)
for the executable location, headless evidence and the prototype stopped by the
user pending a redesigned plan.

For the completed `feature/live-settings` work, see [LIVE-SETTINGS.md](LIVE-SETTINGS.md)
for its build and runtime evidence. The baseline startup verification below
predates those settings changes.

As of September 5, 2026. The [prerequisites](WINDOWS-DEV-SETUP.md) are installed
and CMake and the Windows x64 game builds in Release and Debug have
completed successfully; the user's startup attempts exposed a resource-path error,
which has been corrected and rebuilt; a subsequent run reached the main-menu scene
and shut down normally, and the user confirmed that Release starts without errors.
The four resolved build errors and their evidence are recorded in
[WINDOWS-BUILD-FIXES.md](WINDOWS-BUILD-FIXES.md).
The startup evidence and subsequent correction are recorded in
[WINDOWS-STARTUP-FIXES.md](WINDOWS-STARTUP-FIXES.md).

## 1. Prepare the PowerShell session

In a new PowerShell console:

```powershell
Set-Location -LiteralPath 'C:\Users\mario\GitHub\OpenDungeonsPlus'
. .\scripts\win32\Enter-OpenDungeonsPlus.ps1
```

The dot at the start loads the compiler and search paths into the same session;
then configure and build in this console. CMake 3.31.8,
Python 3.10.11 and the x64 compiler from Visual Studio 2022 Build Tools are expected.

Some automated shells provide both `PATH` and `Path`. MSBuild then fails before
starting `CL.exe` with `System.ArgumentException: An item with the same key has
already been added`. Normalize the process environment before loading the helper:

```powershell
$taskCurrentPath = $env:Path
[System.Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
[System.Environment]::SetEnvironmentVariable('Path', $taskCurrentPath, 'Process')
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. .\scripts\win32\Enter-OpenDungeonsPlus.ps1
```

This changes only the current build process. A normal PowerShell console with one
path variable does not need this step.
If needed, check without building:

```powershell
Get-Command cl.exe, cmake.exe, python.exe | Select-Object Name, Source
cmake --version
python --version
```

## 2. Configure CMake

```powershell
& .\scripts\win32\configure-windows-prereqs.ps1
```

The script also loads the environment helper itself and uses:

- Source: project root, derived from the script path.
- Build directory: `build\windows`.
- Generator: `Visual Studio 17 2022`, architecture `x64`.
- `OD_BUILD_TESTING=OFF` and `BUILD_TESTING=OFF`.
- Installation target: `build\windows\install`.
- Python under `C:\Users\mario\AppData\Local\Programs\Python\Python310`:
  `python.exe`, `include`, `libs\python310.lib`, `libs\python310_d.lib`.

The configuration log is replaced on every invocation:
`C:\Users\mario\od-deps\logs\opendungeons-configure.log`.
On errors, the script prints the last lines and aborts.
Reconfigure after changes to CMake files or source lists;
for ordinary changes to existing C++ files, use the existing build.

## 3. Build the game

Release from the same prepared console:

```powershell
cmake --build .\build\windows --config Release --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Release game build failed' }
& .\scripts\win32\prepare-windows-runtime.ps1
```

After changing a class layout in a header, or after an interrupted rebuild, create
the next test executable with a clean build so that no object file can retain the
previous layout:

```powershell
cmake --build .\build\windows --config Release --target opendungeons-plus --clean-first --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Clean Release game build failed' }
& .\scripts\win32\prepare-windows-runtime.ps1
```

Keep the game and its error dialogs closed while preparing the runtime. CMake
can regenerate `resources.cfg` during a build and restore paths that do not exist
in this local Windows installation. Run runtime preparation after the successful
Release build, including a clean build, before handing the executable to the user.
The September 5 GUI-scaling startup failure from this omitted step is recorded in
[startup fixes](WINDOWS-STARTUP-FIXES.md#resource-path-regression-after-the-gui-scaling-clean-build).

For Debug instead:

```powershell
cmake --build .\build\windows --config Debug --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Debug game build failed' }
```

The successfully generated output files are
`build\windows\opendungeons-plus.exe` and `build\windows\opendungeons-plus_d.exe`,
directly in the build directory. Both files were checked for their AMD64 PE signature and
the corresponding Python DLL without starting the game.
The build output appears in the console; if an error occurs, record the first specific
compiler/linker message and the configuration used.
The logged successful verification runs for this setup are located
under `build\windows\game-Release-pass3.log` and `game-Debug-pass3.log`.

## 4. Direct Release startup and manual verification

For the current local setup, double-click
`C:\Users\mario\GitHub\OpenDungeonsPlus\build\windows\opendungeons-plus.exe`
in File Explorer; no PowerShell session is needed to test the Release build.
Keep the executable in that directory with its DLLs, configuration and resource links.
The files have been prepared and checked, and the executable includes the fix for
absolute Windows resource paths. The 14:07 startup logs confirm main-menu scene
loading and normal shutdown without the earlier loading errors; the user then
confirmed an error-free direct startup on September 5, 2026.
That confirmation predates the dynamic-shadow startup failure. The resource
template now also registers OGRE's `Media/Main` in `OgreInternal`, while retaining
its `Graphics` entry for game shader includes; the user's subsequent run reached
the main menu with shadows enabled, as recorded in
[startup fixes](WINDOWS-STARTUP-FIXES.md).
The corrected configuration has been generated beside the executable and passed
the isolated OGRE resource test; no C++ rebuild is needed for this template change.
The user's later Legacy test-map reproduction identified a fragment shader removed
by OGRE's automatic illumination splitting. RenderManager now selects integrated
additive texture shadows, preserving the existing custom shader passes. Release
and Debug rebuilt successfully; the isolated OGRE pass test reproduces the missing
fragment programs with splitting and retains the original pass without it.
The Release executable is ready for the user to retest the same map with shadows
enabled; gameplay and shadow appearance have not yet been verified after this fix.
Build logs: `game-Release-integrated-shadows.log` and
`game-Debug-integrated-shadows.log` under `build/windows`.

The configuration script now calls
[prepare-windows-runtime.ps1](../../scripts/win32/prepare-windows-runtime.ps1).
It copies 20 installed Release library/plugin DLLs and the two Python runtime DLLs
next to the executable, and replaces the generated Unix-style OGRE media paths
with the existing Windows installation's `Media/RTShaderLib`,
`Media/RTShaderLib/GLSL` and `Media/Main` directories.
The missing HLSL, HLSL_Cg and materials subdirectories are not registered.
The other game resource entries and their existing junctions are preserved.

The generated `python310._pth` points to the existing Python installation, its
`Lib` and `DLLs` directories and the executable directory, with `import site` enabled;
Python documents this application-local module path mechanism in
[Finding modules on Windows](https://docs.python.org/3.10/using/windows.html#finding-modules).
This is a local development setup: OGRE media and the Python standard library
still reside outside the repository, and the installed Visual C++ runtime is used.
It is not a standalone distribution package.

If dependencies change or CMake regenerates the resource configuration outside
the configuration script, refresh the prepared files with:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\win32\prepare-windows-runtime.ps1
```

The execution-policy option applies only to that process; it does not change the
system's policy. The setup has already been performed for the current Release executable.

As of September 5, 2026, static checks covered the executable and 22 DLLs,
all four configured OGRE plugins and all 14 resource directories, with no missing
DLL dependencies or incorrect CPU architectures; evidence is stored in
`build\windows\runtime-validation.json`. These checks do not start the game.

Debug still requires the prepared development environment; its direct-start
runtime files have not been staged. An optional console startup from the loaded
environment is:

```powershell
Push-Location -LiteralPath .\build\windows
try {
    & .\opendungeons-plus_d.exe
} finally {
    Pop-Location
}
```

The Debug startup command has not been verified in practice; its generated
`plugins_d.cfg` still names the Release variants of Codec_STBI and RenderSystem_GL3Plus,
so Debug plugin selection needs correction before its startup can be considered ready.
If a startup error occurs, record the actual message for diagnosis.
The user performs manual game tests and visual acceptance.

## Logs and resuming work

- Current installation and verification status: [WINDOWS-DEV-SETUP.md](WINDOWS-DEV-SETUP.md).
- Library logs: `C:\Users\mario\od-deps\logs\<name>-configure.log`,
  `<name>-Release.log`, `<name>-Debug.log`; Boost uses
  `boost-bootstrap.log` and `boost-build.log`.
- Rebuild dependencies only when actually needed, following
  [WINDOWS-PREREQUISITES.md](WINDOWS-PREREQUISITES.md).

`build` is excluded from Git and contains generated files;
`build\windows` also contains directory junctions to project resources.
Take these junctions into account when cleaning up and do not delete source directories through them.
After a new result, add the date, configuration used, error or success
and remaining checks to the Windows status document.
