#!/usr/bin/env python3
"""Print the build number N for the next integrator release build (version major.minor.patch.N).

N is the last deployed number plus one. If OD_MAJOR_VERSION, OD_MINOR_VERSION or OD_PATCH_LEVEL in
CMakeLists.txt differ from the last deployed state (the base ref, normally origin/integration/all
before the merges), the numbering starts again and N is 1.

Usage: python -I scripts/next-build-number.py --counter <BUILD-NUMBER.txt> [--base origin/integration/all]
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_version(cmake_text):
    """Return (major, minor, patch) read from the text of CMakeLists.txt."""
    parts = []
    for name in ('OD_MAJOR_VERSION', 'OD_MINOR_VERSION', 'OD_PATCH_LEVEL'):
        match = re.search(r'set\(' + name + r'\s+(\d+)\)', cmake_text)
        if match is None:
            raise ValueError(name + ' not found in CMakeLists.txt')
        parts.append(int(match.group(1)))
    return tuple(parts)


def next_build_number(last_number, deployed_cmake_text, new_cmake_text):
    """Return 1 if major, minor or patch changed against the deployed state, else last_number + 1."""
    if read_version(deployed_cmake_text) != read_version(new_cmake_text):
        return 1
    return last_number + 1


def main():
    """Read the counter file and both CMakeLists.txt states and print N."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--counter', required=True)
    parser.add_argument('--base', default='origin/integration/all')
    args = parser.parse_args()
    with open(args.counter, 'r') as counter_file:
        last_number = int(counter_file.readline().strip())
    deployed = subprocess.check_output(['git', '-C', ROOT, 'show', args.base + ':CMakeLists.txt']).decode('utf-8')
    with open(os.path.join(ROOT, 'CMakeLists.txt'), 'r') as cmake_file:
        current = cmake_file.read()
    print(next_build_number(last_number, deployed, current))
    return 0


if __name__ == '__main__':
    sys.exit(main())
