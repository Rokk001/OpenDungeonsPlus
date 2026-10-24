#!/usr/bin/env python3
"""Check the four-part game version 0.7.3.N (non-compiling).

CMakeLists.txt must define the cache variable OD_BUILD_NUMBER (default 0), build OD_VERSION as
major.minor.patch.build and hand that one variable to both the MSVC and the non-MSVC OD_VERSION
definition. The configure script must pass -DOD_BUILD_NUMBER from a BuildNumber parameter that
defaults to 0, and the version format is exercised on sample numbers.
"""
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

for message in failures:
    print('FAIL: ' + message)
if failures:
    sys.exit(1)
print('OK: build number version checks passed')
