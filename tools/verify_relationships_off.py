#!/usr/bin/env python3
"""Seeded comparison: with the creature relationships option off the game must behave like
the classic game.

Runs the same level twice headless with the debug parameters `--run-level <file> --seconds <N>
--seed <S>`: once with a build that has no relationship code (--exe-base) and once with the
current build and the level file switched to "Relationships Off" (--exe-current). After the
run time the game writes its state (seats, every creature with class, level, health and
position) to run-level-state.txt. Both state files must be identical.

Exit code 0: identical. 1: the states differ (a diff is printed). 2: a run failed.
Both builds need the --seed parameter (see source/utils/RunLevelTest.cpp).

Usage:
    python tools/verify_relationships_off.py --exe-base BASE.exe --exe-current CURRENT.exe
        [--level levels/skirmish/DuelToDeath.level] [--seconds 60] [--seed 12345]
        [--repeat-base]   # also run the base twice first to prove the run is repeatable
"""

import argparse
import difflib
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def switch_option_off(level, target):
    """Copies the level and adds the line `Relationships<TAB>Off` at the end of its [Info] block."""
    with open(level, encoding="utf-8", newline="") as handle:
        text = handle.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    marker = "[/Info]"
    if marker not in text:
        raise SystemExit("level has no [Info] block: " + level)
    text = text.replace(marker, "Relationships\tOff" + newline + marker, 1)
    with open(target, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def run(exe, level, seconds, seed):
    """Runs the game once. Returns (result line, state text) or raises SystemExit on failure."""
    appdata = tempfile.mkdtemp(prefix="od-verify-")
    command = [exe, "--run-level", level, "--seconds", str(seconds), "--seed", str(seed), "--appData", appdata]
    limit = 2 * seconds + 400
    process = subprocess.Popen(command, cwd=os.path.dirname(os.path.abspath(exe)),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    try:
        output, _ = process.communicate(timeout=limit)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        shutil.rmtree(appdata, ignore_errors=True)
        raise SystemExit("run failed: timeout (%s)" % exe)
    result = [line for line in (output or "").splitlines() if line.startswith(("PASS ", "FAIL "))]
    state_file = os.path.join(appdata, "run-level-state.txt")
    state = ""
    if os.path.exists(state_file):
        with open(state_file, encoding="utf-8") as handle:
            state = handle.read()
    shutil.rmtree(appdata, ignore_errors=True)
    if process.returncode != 0 or not result or not state:
        raise SystemExit("run failed (exit %s): %s" % (process.returncode, result[-1] if result else "no result line"))
    return result[-1], state


def compare(name_a, state_a, name_b, state_b):
    """Prints the differences. Returns True if the states are equal."""
    if state_a == state_b:
        return True
    diff = difflib.unified_diff(state_a.splitlines(), state_b.splitlines(), name_a, name_b, lineterm="", n=0)
    lines = list(diff)
    print("\n".join(lines[:60]))
    if len(lines) > 60:
        print("... %d more diff lines" % (len(lines) - 60))
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exe-base", required=True, help="build without the relationship code")
    parser.add_argument("--exe-current", required=True, help="current build (option switched off in the level)")
    parser.add_argument("--level", default=os.path.join(REPO, "levels", "skirmish", "DuelToDeath.level"))
    parser.add_argument("--seconds", type=int, default=60)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--repeat-base", action="store_true", help="run the base build twice first")
    args = parser.parse_args()

    level = os.path.abspath(args.level)
    exe_base = os.path.abspath(args.exe_base)
    exe_current = os.path.abspath(args.exe_current)
    for path in (level, exe_base, exe_current):
        if not os.path.exists(path):
            print("not found: " + path)
            return 2

    workdir = tempfile.mkdtemp(prefix="od-verify-level-")
    off_level = os.path.join(workdir, os.path.basename(level))
    switch_option_off(level, off_level)
    try:
        result_base, state_base = run(exe_base, level, args.seconds, args.seed)
        print("base:    " + result_base)
        if args.repeat_base:
            result_again, state_again = run(exe_base, level, args.seconds, args.seed)
            print("base #2: " + result_again)
            if not compare("base", state_base, "base #2", state_again):
                print("FAIL: the base build is not repeatable with this seed, the comparison is not meaningful")
                return 1
            print("base build repeatable: identical state")
        result_current, state_current = run(exe_current, off_level, args.seconds, args.seed)
        print("current: " + result_current)
    except SystemExit as error:
        print(error)
        return 2
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    creatures = len([1 for line in state_base.splitlines() if line.startswith("creature ")])
    if not compare("base", state_base, "current (option off)", state_current):
        print("FAIL: state with the option off differs from the base build")
        return 1
    print("OK: identical state (%d creatures, %s)" % (creatures, state_base.splitlines()[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
