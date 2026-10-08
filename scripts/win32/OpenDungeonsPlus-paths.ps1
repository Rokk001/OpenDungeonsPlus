# Locations shared by the Windows scripts. Each one can be overridden with an
# environment variable; the defaults follow the usual per-user layout.
# $taskRoot: dependency tree (sources, builds, logs, install prefix)
# $taskVsPath: Visual Studio Build Tools installation
# $taskPythonRoot: Python installation (and the same path with forward slashes for CMake)
if ($env:OD_DEPS_ROOT) { $taskRoot = $env:OD_DEPS_ROOT } else { $taskRoot = Join-Path $env:USERPROFILE 'od-deps' }
if ($env:OD_VS_PATH) { $taskVsPath = $env:OD_VS_PATH } else { $taskVsPath = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\2022\BuildTools' }
if ($env:OD_PYTHON_ROOT) { $taskPythonRoot = $env:OD_PYTHON_ROOT } else { $taskPythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310' }
$taskPythonRootSlash = $taskPythonRoot.Replace('\', '/')
