#!/usr/bin/env python3
"""Automated level load test.

Runs the game executable once per level with the debug parameters
`--run-level <file> --seconds <N>`. The game starts a local game on the level,
lets it run for N seconds of game time, sets all main goals of the level as reached, fires the win
(a refused win is a failure; a campaign level must also show the victory message and the campaign
map with the next level) and exits with a code:

    0  PASS (level loaded, time ran, no error logged, win reported, campaign map shown for campaign levels)
    1  usage error (for example --seconds 0)
    2  load error (level not found/rejected, game did not start in time)
    3  error during the run (error logged, exception, game ended without result)
    4  no victory (player seat defeated, win not reported)
    5  timeout (the watchdog of the game ended a hanging run)

The game also prints "FRAMETIME frames=<n> avg_ms=<x>" before its result line; the script prints that line
after the level's result line (the result line itself is unchanged).

Any other exit code (for example a crash) counts as FAIL "crash". The script
also kills a game that outlives its own limit. Exit code of the script: 0 only
if all levels passed.

Usage:
    python scripts/run-level-test.py --exe build/windows/Release/opendungeons-plus.exe
    python scripts/run-level-test.py --exe ... --seconds 60 levels/campaign/Mossgate.level
    python scripts/run-level-test.py --exe ... --markdown   # result paragraph as markdown
    python scripts/run-level-test.py --exe ... --port 31301   # own server port, for parallel instances
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CODE_NAMES = {
    0: "PASS",
    1: "usage error",
    2: "load error",
    3: "error during the run",
    4: "no victory",
    5: "timeout",
}


def campaign_levels():
    """Level files listed in levels/campaign/Campaign.cfg, in order."""
    cfg = os.path.join(REPO, "levels", "campaign", "Campaign.cfg")
    levels = []
    with open(cfg, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"\s*File\s*=\s*(\S+)", line)
            if match:
                levels.append(os.path.join(REPO, "levels", match.group(1)))
    return levels


FRAME_LINE = re.compile(r"^FRAMETIME frames=(\d+) avg_ms=([0-9.eE+-]+)")


def parse_frame_time(output):
    """Returns (frames, avg_ms) of the last FRAMETIME line of the game output, or None."""
    result = None
    for text in (output or "").splitlines():
        match = FRAME_LINE.match(text.strip())
        if match:
            result = (int(match.group(1)), float(match.group(2)))
    return result


# Engine log lines that mean a resource was not found; such a line naming a menu scene resource fails the run.
RESOURCE_ERRORS = ("Cannot locate resource", "Texture layer will be blank", "Can't assign material")
# Name prefix shared by all menu scene textures and materials; other missing-resource lines are not judged here.
MENU_RESOURCE_PREFIX = "Menu"


def find_resource_errors(log_path):
    """Returns the distinct engine log lines (time stamp removed) that report a missing menu scene resource."""
    found = []
    if not os.path.exists(log_path):
        return found
    with open(log_path, encoding="utf-8", errors="replace") as handle:
        for text in handle:
            if MENU_RESOURCE_PREFIX in text and any(marker in text for marker in RESOURCE_ERRORS):
                entry = re.sub(r"^\d\d:\d\d:\d\d: ", "", text.strip())
                if entry not in found:
                    found.append(entry)
    return found


MENU_TEST_NAME = "MainMenu"
MENU_FRAME_LINE = re.compile(r"^MENUTEST frames=(\d+)")


def port_arguments(port):
    """Returns the game arguments that select the server port; empty if no port is requested (game default)."""
    return [] if port is None else ["--port", str(port)]


def run_menu_test(exe, seconds, port=None):
    """Starts the game once with --menu-test, so that the main menu scene is really rendered, and checks Ogre.log.

    A --run-level run starts its level while the menu opens, before a single menu frame is rendered, so
    the menu textures and materials are never loaded there. Returns (passed, text); the text is
    "PASS MainMenu ..." or "FAIL MainMenu : reason" (it does not end in .level). port selects the server
    port of the game (None = game default).
    """
    appdata = tempfile.mkdtemp(prefix="od-menu-test-")
    limit = 2 * seconds + 120
    command = [exe, "--menu-test", str(seconds), "--appData", appdata] + port_arguments(port)
    process = subprocess.Popen(command, cwd=os.path.dirname(os.path.abspath(exe)),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True)
    try:
        output, _ = process.communicate(timeout=limit)
        code = process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()
        code = None
    shutil.rmtree(appdata, ignore_errors=True)

    frames = 0
    for text in (output or "").splitlines():
        match = MENU_FRAME_LINE.match(text.strip())
        if match:
            frames = int(match.group(1))
    resource_errors = find_resource_errors(os.path.join(os.path.dirname(os.path.abspath(exe)), "Ogre.log"))
    if code is None:
        return False, "FAIL %s : timeout: the script killed the game after %d s" % (MENU_TEST_NAME, limit)
    if code != 0:
        return False, "FAIL %s : crash: exit code %d" % (MENU_TEST_NAME, code)
    if frames <= 0:
        return False, "FAIL %s : the menu rendered no frame (no MENUTEST line)" % MENU_TEST_NAME
    if resource_errors:
        return False, "FAIL %s : missing menu scene resources in Ogre.log (%d): %s" % (
            MENU_TEST_NAME, len(resource_errors), "; ".join(resource_errors[:5]))
    return True, "PASS %s : %d frames rendered, no missing menu resources" % (MENU_TEST_NAME, frames)


def run_level(exe, level, seconds, port=None):
    """Runs one level. Returns (passed, text)."""
    passed, text, _ = run_level_with_frame_time(exe, level, seconds, port)
    return passed, text


def run_level_with_frame_time(exe, level, seconds, port=None):
    """Runs one level. Returns (passed, text, frame_time), frame_time is (frames, avg_ms) or None.

    port selects the server port of the game (None = game default); parallel instances need different ports.
    """
    appdata = tempfile.mkdtemp(prefix="od-run-level-")
    limit = 2 * seconds + 400
    command = [exe, "--run-level", level, "--seconds", str(seconds), "--appData", appdata] + port_arguments(port)
    process = subprocess.Popen(command, cwd=os.path.dirname(os.path.abspath(exe)),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               universal_newlines=True)
    try:
        output, _ = process.communicate(timeout=limit)
        code = process.returncode
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate()
        code = None

    frame_time = parse_frame_time(output)
    resource_errors = find_resource_errors(os.path.join(os.path.dirname(os.path.abspath(exe)), "Ogre.log"))
    line = ""
    for text in (output or "").splitlines():
        if text.startswith("PASS ") or text.startswith("FAIL "):
            line = text.strip()
    if not line:
        result_file = os.path.join(appdata, "run-level-result.txt")
        if os.path.exists(result_file):
            with open(result_file, encoding="utf-8") as handle:
                line = handle.readline().strip()
    shutil.rmtree(appdata, ignore_errors=True)

    name = os.path.basename(level)
    if code is None:
        return False, "FAIL %s : timeout: the script killed the game after %d s" % (name, limit), frame_time
    if code == 0 and line.startswith("PASS ") and resource_errors:
        return False, "FAIL %s : missing menu scene resources in Ogre.log (%d): %s" % (
            name, len(resource_errors), "; ".join(resource_errors[:5])), frame_time
    if code == 0 and line.startswith("PASS "):
        return True, line, frame_time
    if code not in CODE_NAMES:
        return False, "FAIL %s : crash: exit code %d (%s)" % (name, code, line or "no result line"), frame_time
    if code == 0:
        return False, "FAIL %s : exit code 0 without a PASS line" % name, frame_time
    return (False, line or "FAIL %s : %s (exit code %d, no result line)" % (name, CODE_NAMES[code], code),
            frame_time)


def main():
    """Parses the command line, runs the requested levels and exits with 0 only if all passed."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--exe", required=True, help="built game executable")
    parser.add_argument("--seconds", type=int, default=120, help="game time per level (default 120)")
    parser.add_argument("--menu-seconds", type=int, default=8,
                        help="seconds the main menu test shows the menu once per run (0 = skip, default 8)")
    parser.add_argument("--markdown", action="store_true", help="print the results as a markdown paragraph")
    parser.add_argument("--port", type=int, default=None,
                        help="server port of the game (default: the game default); parallel instances need different ports")
    parser.add_argument("--progress-file", help="append one progress line per finished level to this file")
    parser.add_argument("levels", nargs="*", help="level files (default: all levels of Campaign.cfg)")
    args = parser.parse_args()

    exe = os.path.abspath(args.exe)
    if not os.path.exists(exe):
        print("exe not found: " + exe)
        return 2
    levels = [os.path.abspath(level) for level in args.levels] or campaign_levels()

    # The main menu is tested once per run, before the levels (its own PASS/FAIL line, not counted as a level)
    menu_passed = True
    menu_text = ""
    if args.menu_seconds > 0:
        menu_passed, menu_text = run_menu_test(exe, args.menu_seconds, args.port)
        print(menu_text, flush=True)

    results = []
    for level in levels:
        passed, text, frame_time = run_level_with_frame_time(exe, level, args.seconds, args.port)
        print(text, flush=True)
        if frame_time is not None:
            print("FRAMETIME frames=%d avg_ms=%s" % frame_time, flush=True)
        results.append((passed, text))
        pass_count = len([1 for ok, _ in results if ok])
        progress = "%d/%d Maps getestet – %d PASS, %d FAIL – zuletzt: %s %s" % (
            len(results), len(levels), pass_count, len(results) - pass_count,
            os.path.splitext(os.path.basename(level))[0], "PASS" if passed else "FAIL")
        print(progress, flush=True)
        if args.progress_file:
            with open(args.progress_file, "a", encoding="utf-8") as handle:
                handle.write(progress + "\n")

    failed = [text for passed, text in results if not passed]
    if failed:
        print("FAIL:")
        for text in failed:
            print("  " + text.splitlines()[0])
    print("%d of %d levels PASS" % (len(results) - len(failed), len(results)))
    if not menu_passed:
        print("FAIL: the main menu test failed")
    if args.markdown:
        print()
        print("- Load test (`--run-level <file> --seconds %d`, %d levels): %d PASS, %d FAIL."
              % (args.seconds, len(results), len(results) - len(failed), len(failed)))
        for passed, text in results:
            print("  - " + text)
        if args.menu_seconds > 0:
            print("  - " + menu_text)
    return 0 if (not failed and menu_passed) else 1


if __name__ == "__main__":
    sys.exit(main())
