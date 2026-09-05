# Windows x64 development

This guide describes the MSVC 2022 build with OGRE 13.6.5 and the project's
CEGUI fork. It includes the dependency patches required for live display settings
and correctly clipped GUI rendering. The scripts build a local development
installation; they do not create a standalone redistributable package.

## Tools and paths

Install Git, Visual Studio 2022 Build Tools with the Desktop development with C++
workload and a Windows SDK, and Python 3.10 with development headers, import
libraries and debug binaries. The tested versions are MSVC 14.44.35207,
Windows SDK 10.0.26100.0 and Python 3.10.11. Debug configuration requires
`libs/python310_d.lib` in addition to the Release import library.

The PowerShell scripts accept these installation paths:

| Parameter | Default | Used by |
| --- | --- | --- |
| `DependencyRoot` | `od-deps` in the current user's profile | All new Windows scripts |
| `PythonRoot` | `Programs/Python/Python310` in local application data | Environment, base libraries, CEGUI, game configuration and runtime preparation |
| `VsPath` | `Microsoft Visual Studio/2022/BuildTools` under Program Files (x86) | Environment, Boost and game configuration |

For another Visual Studio edition or installation location, pass `VsPath`
explicitly. Paths below are examples; use the same dependency and Python roots
throughout. The dependency root has `src`, `build`, `install`, `tools`,
`downloads` and `logs` subdirectories, which must exist before installing libraries.

```powershell
$dependencyRoot = Join-Path $env:USERPROFILE 'od-deps'
$pythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310'
$vsPath = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools'
foreach ($directory in @('src', 'build', 'install', 'tools', 'downloads', 'logs')) {
    New-Item -ItemType Directory -Path (Join-Path $dependencyRoot $directory) -Force | Out-Null
}
```

Use [CMake 3.31.8](https://github.com/Kitware/CMake/releases/tag/v3.31.8), extracted
under `tools/cmake-3.31.8-windows-x86_64` in the dependency root. The older project
configuration has not been validated with arbitrary newer CMake versions.

## Dependency sources

Prepare these source trees under the dependency root before running the installers;
the scripts do not download sources. Clone each repository at the listed tag and
verify its commit. Preserve an existing source directory instead of cloning over it.

| Source | Tag | Directory | Commit |
| --- | --- | --- | --- |
| [OGRE](https://github.com/OGRECave/ogre) | `v13.6.5` | `src/ogre` | `856cf743ebcce8250d181a621ee47a70b12ed17e` |
| [CEGUI project fork](https://github.com/tomluchowski/cegui) | `scissors_test_disabled` | `src/cegui` | `d8c7290c0eabc62e4319af4168a81757c6267403` |
| [OIS](https://github.com/wgois/OIS) | `v1.5.1` | `src/ois` | `6edb487cccb54d59e5b0fff86549d5eef475dea6` |
| [SFML](https://github.com/SFML/SFML) | `2.5.1` | `src/sfml` | `2f11710abc5aa478503a7ff3f9e654bd2078ebab` |
| [FreeType](https://github.com/freetype/freetype) | `VER-2-12-1` | `src/freetype` | `e8ebfe988b5f57bfb9a3ecb13c70d9791bce9ecf` |
| [Expat](https://github.com/libexpat/libexpat) | `R_2_8_4` | `src/expat` | `12cf0b1f25f026a022fe728ad8f7e3d017285b80` |
| [pybind11](https://github.com/pybind/pybind11) | `v2.10.4` | `src/pybind11` | `5b0a6fc2017fcc176545afe3e09c9f9885283242` |

Expat's CMake source directory is `src/expat/expat`. Additionally extract
[Boost 1.82.0](https://archives.boost.io/release/1.82.0/source/boost_1_82_0.zip)
into `src/boost_1_82_0` and
[PCRE 8.45](https://sourceforge.net/projects/pcre/files/pcre/8.45/pcre-8.45.zip/download)
into `src/pcre-8.45`. Store archives under `downloads` and verify the checksums
before extraction:

| Archive | Algorithm | Verified checksum |
| --- | --- | --- |
| `cmake-3.31.8-windows-x86_64.zip` | SHA-256 | `81aa9964dbabd71fe02e7ec50472fd3ad56138c49944515ece9001efbff8d719` |
| `boost_1_82_0.zip` | SHA-256 | `f7c9e28d242abcd7a2c1b962039fcdd463ca149d1883c3a950bbcc0ce6f7c6d9` |
| `pcre-8.45.zip` | SHA-512 | `71f246c0abbf356222933ad1604cab87a1a2a3cd8054a0b9d6deb25e0735ce9f40f923d14cbd21f32fdac7283794270afcb0f221ad24662ac35934fcb73675cd` |

## Build the libraries

From the repository root, run the installers in this order:

```powershell
$scriptRoot = Join-Path $PWD.Path 'scripts\win32'
& powershell.exe -NoProfile -File (Join-Path $scriptRoot 'install-base-prereqs.ps1') -DependencyRoot $dependencyRoot -PythonRoot $pythonRoot
if ($LASTEXITCODE -ne 0) { throw 'Base library installation failed' }
& powershell.exe -NoProfile -File (Join-Path $scriptRoot 'install-boost-prereq.ps1') -DependencyRoot $dependencyRoot -VsPath $vsPath
if ($LASTEXITCODE -ne 0) { throw 'Boost installation failed' }
& powershell.exe -NoProfile -File (Join-Path $scriptRoot 'install-ogre-prereq.ps1') -DependencyRoot $dependencyRoot
if ($LASTEXITCODE -ne 0) { throw 'OGRE installation failed' }
& powershell.exe -NoProfile -File (Join-Path $scriptRoot 'install-cegui-prereq.ps1') -DependencyRoot $dependencyRoot -PythonRoot $pythonRoot
if ($LASTEXITCODE -ne 0) { throw 'CEGUI installation failed' }
```

The separate processes preserve the calling shell's directory and environment. The
scripts build and install Release and Debug libraries into `install` and replace
their per-library logs in `logs`. The base installer supports `-Only` for a
specific dependency. Preserve its SFML-before-FreeType order: SFML's bundled
FreeType otherwise overwrites the independently built library and causes link
failures in OgreOverlay.

The installers apply the following repository-managed patches idempotently:

- [cegui-msvc-snprintf.patch](../scripts/win32/patches/cegui-msvc-snprintf.patch)
  limits the legacy `snprintf` macro to older MSVC versions, avoiding corruption
  of current Boost headers.
- [cegui-ogre-clipping.patch](../scripts/win32/patches/cegui-ogre-clipping.patch)
  restores each GUI batch's scissor flag in the project's CEGUI fork, keeping
  rendered controls within the same clip area used for hit testing.
- [ogre-multiwindow-settings.patch](../scripts/win32/patches/ogre-multiwindow-settings.patch)
  corrects OGRE 13.6.5 GL3Plus context-local program pipelines, gamma detection,
  live renderer options and Win32 fullscreen frame/viewport updates.

The game changes require these library changes; merely placing patch files in
the game checkout does not patch a prebuilt OGRE or CEGUI installation. Rebuild
the affected library and refresh the game's runtime DLLs after applying a patch.
The OGRE patch is version-specific and is not an OGRE 14 port.

## Configure and build the game

From the repository root, load the environment into the current PowerShell session
and configure the game:

```powershell
. .\scripts\win32\Enter-OpenDungeonsPlus.ps1 -DependencyRoot $dependencyRoot -PythonRoot $pythonRoot -VsPath $vsPath
& .\scripts\win32\configure-windows-prereqs.ps1 -DependencyRoot $dependencyRoot -PythonRoot $pythonRoot -VsPath $vsPath
```

The script uses the Visual Studio 2022 x64 generator and writes its log to
`build/windows/configure.log`. It finds libraries in the configured dependency
prefix and explicitly selects the Python 3.10 headers and Release/Debug import
libraries. Tests are disabled in this game-build configuration.

```powershell
cmake --build .\build\windows --config Release --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'Release game build failed' }
& .\scripts\win32\prepare-windows-runtime.ps1 -DependencyRoot $dependencyRoot -PythonRoot $pythonRoot
```

Keep the game closed while replacing runtime files. Run runtime preparation
after every successful Release build: CMake can regenerate `resources.cfg` with
the installation template's media paths, which differ from this Windows prefix.
The preparation script restores existing OGRE media directories, including the
internal shadow programs, and stages the required Release DLLs and Python paths.

If a branch switch or header change modifies a C++ class layout, rebuild with
`--target opendungeons-plus --clean-first` before runtime preparation to prevent
mixed object files from retaining incompatible layouts.

The Release executable is `build/windows/opendungeons-plus.exe`; start it directly
from File Explorer with its DLLs, configuration and resource links in place. OGRE
media and the Python standard library still reside in the external installation.
This directory is a development runtime, not a portable distribution.

Debug compilation uses `cmake --build .\build\windows --config Debug --parallel 4`.
Its output is `build/windows/opendungeons-plus_d.exe`. Automatic direct-start
runtime preparation currently covers Release only; Debug plugin configuration and
runtime staging require separate verification.

If an automated shell supplies both `PATH` and `Path`, MSBuild can fail before
launching the compiler because its environment dictionary contains a duplicate
key. Normalize that process environment before loading the helper:

```powershell
$currentPath = $env:Path
[Environment]::SetEnvironmentVariable('PATH', $null, 'Process')
[Environment]::SetEnvironmentVariable('Path', $currentPath, 'Process')
```

## Validation scope

The development work was compiled with Windows x64 MSVC in Release and Debug;
the final GUI corrections were rebuilt in Release. Windows Release startup,
live resolution/fullscreen changes, corrected pointer alignment and bottom-edge
rendering, progressive edge scrolling and the GUI corrections were accepted by
the user in the running game. Isolated packet, OGRE and CEGUI checks provided
additional regression evidence, as summarized in [UI and settings](UI-AND-SETTINGS.md).

This is not Linux, macOS, MinGW, multi-monitor, mixed-version multiplayer or
standalone-package certification. Existing compiler warnings remain. The version
stays at 0.7.1 because these are unreleased changes; historical release notes are
unchanged.
