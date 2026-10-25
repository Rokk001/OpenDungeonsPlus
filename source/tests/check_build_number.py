#!/usr/bin/env python3
"""Check the four-part game version 0.7.3.N (non-compiling).

CMakeLists.txt must define the cache variable OD_BUILD_NUMBER (default 0), build OD_VERSION as
major.minor.patch.build and hand that one variable to both the MSVC and the non-MSVC OD_VERSION
definition. The configure script must pass -DOD_BUILD_NUMBER from a BuildNumber parameter that
defaults to 0, and the version format is exercised on sample numbers.
"""
import importlib.util
from pathlib import Path
import re
import sys

repo = Path(__file__).resolve().parents[2]
cmake = (repo / 'CMakeLists.txt').read_text()
script = (repo / 'scripts/win32/configure-windows-prereqs.ps1').read_text()
failures = []


# Records a failure message when the condition does not hold.
def check(condition, message):
    if not condition:
        failures.append(message)


check(re.search(r'set\(OD_BUILD_NUMBER 0 CACHE STRING', cmake), 'OD_BUILD_NUMBER cache variable with default 0 is missing')
check('set(OD_VERSION "${OD_MAJOR_VERSION}.${OD_MINOR_VERSION}.${OD_PATCH_LEVEL}.${OD_BUILD_NUMBER}")' in cmake,
      'OD_VERSION is not major.minor.patch.build')
check('add_definitions(-DOD_VERSION="${OD_VERSION}")' in cmake, 'non-MSVC OD_VERSION definition does not use OD_VERSION')
check('add_definitions(/DOD_VERSION="${OD_VERSION}")' in cmake, 'MSVC OD_VERSION definition does not use OD_VERSION')
check(len(re.findall(r'OD_VERSION="', cmake)) == 2, 'unexpected number of OD_VERSION definitions')
check(re.search(r'param\(\[int\]\$BuildNumber = 0\)', script), 'configure script lacks BuildNumber parameter defaulting to 0')
check('"-DOD_BUILD_NUMBER=$BuildNumber"' in script, 'configure script does not pass -DOD_BUILD_NUMBER')

major = int(re.search(r'set\(OD_MAJOR_VERSION (\d+)\)', cmake).group(1))
minor = int(re.search(r'set\(OD_MINOR_VERSION (\d+)\)', cmake).group(1))
patch = int(re.search(r'set\(OD_PATCH_LEVEL\s+(\d+)\)', cmake).group(1))
for number in (0, 1, 42):
    version = '%d.%d.%d.%d' % (major, minor, patch, number)
    check(re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version) is not None, 'bad version format ' + version)

# The reset rule: next-build-number.py returns 1 when major, minor or patch changed, else last + 1.
spec = importlib.util.spec_from_file_location('next_build_number', repo / 'scripts/next-build-number.py')
next_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(next_build)
sample = ' '.join(['set(OD_MAJOR_VERSION 0)', 'set(OD_MINOR_VERSION 7)', 'set(OD_PATCH_LEVEL   3)'])
check(next_build.read_version(sample) == (0, 7, 3), 'read_version does not read the sample version')
check(next_build.next_build_number(5, sample, sample) == 6, 'unchanged version must give last + 1')
check(next_build.next_build_number(5, sample, sample.replace('LEVEL   3', 'LEVEL   4')) == 1, 'patch change must restart at 1')
check(next_build.next_build_number(5, sample, sample.replace('MINOR_VERSION 7', 'MINOR_VERSION 8')) == 1, 'minor change must restart at 1')
check(next_build.next_build_number(5, sample, sample.replace('MAJOR_VERSION 0', 'MAJOR_VERSION 1')) == 1, 'major change must restart at 1')
real = (repo / 'CMakeLists.txt').read_text()
check(next_build.read_version(real) == (major, minor, patch), 'read_version disagrees with CMakeLists.txt')
claude = (repo / 'CLAUDE.md').read_text()
check('starts again at 1' in claude and 'next-build-number.py' in claude, 'CLAUDE.md lacks the build number reset rule')

# The integrator build script computes the number itself and hands it to the configure script.
build_script = (repo / 'scripts/win32/integrator-release-build.ps1').read_text()
check('next-build-number.py' in build_script, 'integrator build script does not call next-build-number.py')
check('configure-windows-prereqs.ps1" -BuildNumber $buildNumber' in build_script, 'integrator build script does not pass -BuildNumber to the configure script')
check('--parallel 1' in build_script, 'integrator build script does not build with --parallel 1')
check('build-start-$Run.txt' in build_script, 'integrator build script does not record the build start time')
check('Feature and fix windows never run a full build' in claude, 'CLAUDE.md lacks the rule that only the integrator builds')
check('Kein Release- oder Abschlussbuild' not in claude, 'CLAUDE.md still allows a full build after a release')

for message in failures:
    print('FAIL: ' + message)
if failures:
    sys.exit(1)
print('OK: build number version checks passed')
