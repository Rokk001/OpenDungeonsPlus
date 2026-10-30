# Machine-specific locations shared by the Windows scripts. Set BUILD_DEPS_ROOT,
# BUILD_PYTHON_ROOT or BUILD_VS_PATH to override the defaults below.
# BUILD_MP_JOBS (default 0 = off) sets the number of parallel MSVC compiler processes (/MP) per build.
# The default dependency root is build-deps in the user profile.
$taskDependencyRoot = if ($env:BUILD_DEPS_ROOT) { $env:BUILD_DEPS_ROOT } else { Join-Path $env:USERPROFILE 'build-deps' }
$taskPythonRoot = if ($env:BUILD_PYTHON_ROOT) { $env:BUILD_PYTHON_ROOT } else { Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314' }
$taskVsPath = if ($env:BUILD_VS_PATH) { $env:BUILD_VS_PATH } else { 'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools' }
$taskMpJobs = if ($env:BUILD_MP_JOBS) { [int]$env:BUILD_MP_JOBS } else { 0 }
# CMake arguments use forward slashes.
$taskPythonCmakeRoot = $taskPythonRoot.Replace('\', '/')
$taskCmakeExe = "$taskDependencyRoot\tools\cmake-4.4.1-windows-x86_64\bin\cmake.exe"
