"""Load check: a save with [RelationshipState] lines naming existing creatures keeps those relationships.

Without arguments the check runs the static part only, which needs no game and no build: the committed fixture
source/tests/fixtures/relationship_state/RelationshipStateSmall.level must contain a [RelationshipState] block whose
creatures exist in the fixture's [Creatures] section, and the block must match the fixed expected values below.

With --exe the check also starts the game on a copy of a save in a new, empty app-data folder (never the owner's
%APPDATA% folder; the original save is never opened for writing). The run passes only when:
  - the process is still alive after --seconds (an early exit is an access violation of the save load),
  - the log has no invalid RelationshipState section,
  - the server reached "Server connected and listening",
  - every creature named in the save's [RelationshipState] block is logged as restored, with no
    "unknown creature" warning for it, and
  - for the committed fixture, the restored values match the fixed expectations below.

Usage:
  check_relationship_state_load_headless.py                      (static part, the normal runner)
  check_relationship_state_load_headless.py --exe PATH [--save PATH] [--seconds 30]
The TestGhosts runtime test is run the same way with its own --save and --exe.
The check starts only its own process. It refuses to run while another opendungeons-plus.exe is running, so
that a game the owner is playing is never touched.
"""
import argparse
import glob
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "relationship_state" / "RelationshipStateSmall.level"

LISTENING = "Server connected and listening"
BAD_SECTION = "Invalid RelationshipState section"
RESTORED = "Restored relationship state of %s, "
UNKNOWN = "Saved relationship state of unknown creature %s"

# Fixed expected values of the committed fixture: restored rage turns and number of captors per creature.
# They are written by hand from the fixture block and are not derived from the game. Each creature must be in a seat
# that allows relationships (a seat that exists, not rogue, not Hero, not a worker, not in prison), because
# Creature::setRelationshipState keeps the rage only then; the fixture has only seat 1 (Keeper), so all of them are in it.
# Not verified by a run: the runtime part was not executed in this change (no build).
FIXTURE_EXPECTED = {
    "Knight1": "rageTurns=5, captors=0",
    "Knight3": "rageTurns=0, captors=1",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_block(text):
    """Returns the lines of the first [RelationshipState] block (CRLF safe), or None when there is none."""
    lines = [line.rstrip("\r") for line in text.split("\n")]
    if "[RelationshipState]" not in lines:
        return None
    start = lines.index("[RelationshipState]") + 1
    if "[/RelationshipState]" not in lines[start:]:
        return None
    end = lines.index("[/RelationshipState]", start)
    return [line for line in lines[start:end] if line and not line.startswith("#")]


def creatures_in(text):
    """Names of the creatures in the [Creatures] section (second column), or None when the section is not closed."""
    lines = [line.rstrip("\r") for line in text.split("\n")]
    if "[Creatures]" not in lines or "[/Creatures]" not in lines[lines.index("[Creatures]"):]:
        return None
    start = lines.index("[Creatures]") + 1
    end = lines.index("[/Creatures]", start)
    return {line.split("\t")[1] for line in lines[start:end] if line and not line.startswith("#") and "\t" in line}


def static_check(save_path, expect_fixture):
    """Checks the block of the save without the game. Returns (failures, names of the creatures in the block)."""
    text = save_path.read_text(encoding="utf-8", errors="replace")
    block = read_block(text)
    if block is None:
        return ["no closed [RelationshipState] block in %s" % save_path], []
    names = [line.split("\t")[0] for line in block]
    existing = creatures_in(text)
    if existing is None:
        return ["no closed [Creatures] section in %s" % save_path], []
    failures = []
    for line in block:
        fields = line.split("\t")
        if len(fields) < 6:
            failures.append("short RelationshipState line: %r" % line)
            continue
        if fields[0] not in existing:
            failures.append("%s is not a creature of the level" % fields[0])
        for captor in fields[6:]:
            if captor not in existing:
                failures.append("captor %s of %s is not a creature of the level" % (captor, fields[0]))
    if expect_fixture and sorted(names) != sorted(FIXTURE_EXPECTED):
        failures.append("fixture block names %s, expected %s" % (sorted(names), sorted(FIXTURE_EXPECTED)))
    return failures, names


def game_running():
    """True when an opendungeons-plus.exe process exists (tasklist, no kill)."""
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq opendungeons-plus.exe", "/NH"], capture_output=True)
    return "opendungeons-plus.exe" in result.stdout.decode("utf-8", errors="replace").lower()


def runtime_check(exe, save, seconds, names, is_fixture):
    """Starts the game on a copy of the save. Returns a list of failures, or None when the check was skipped."""
    if game_running():
        print("SKIPPED: an opendungeons-plus.exe process is running; this check does not touch it")
        return None
    before = sha256(save)
    appdata = Path(tempfile.mkdtemp(prefix="relstate-load-"))
    (appdata / "saves").mkdir()
    shutil.copyfile(save, appdata / "saves" / save.name)

    proc = subprocess.Popen([str(exe), "--appData", str(appdata), "--serversave", save.name],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + seconds
    while time.time() < deadline and proc.poll() is None:
        time.sleep(0.5)
    exited = proc.poll() is not None
    if not exited:
        proc.kill()  # our own process, started above
        proc.wait()

    log = ""
    for path in glob.glob(os.path.join(str(appdata), "**", "*.log"), recursive=True):
        log += Path(path).read_text(encoding="utf-8", errors="replace")

    failures = []
    if exited:
        failures.append("the game exited with code %d before %d s" % (proc.returncode, seconds))
    if BAD_SECTION in log:
        failures.append("the log reports an invalid RelationshipState section")
    if LISTENING not in log:
        failures.append("the server did not reach '%s'" % LISTENING)
    for name in names:
        if (RESTORED % name) not in log:
            failures.append("no restore line for %s in the log" % name)
        if (UNKNOWN % name) in log:
            failures.append("the log reports %s as an unknown creature" % name)
    if is_fixture:
        for name, expected in FIXTURE_EXPECTED.items():
            if ((RESTORED % name) + expected) not in log:
                failures.append("restored values of %s differ from '%s'" % (name, expected))
    if sha256(save) != before:
        failures.append("the original save changed")
    shutil.rmtree(appdata, ignore_errors=True)
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--exe", default=None, help="the game executable; without it only the static part runs")
    parser.add_argument("--save", default=str(FIXTURE),
                        help="the save with RelationshipState lines naming existing creatures")
    parser.add_argument("--seconds", type=int, default=30, help="how long the server must stay alive")
    args = parser.parse_args()

    save = Path(args.save)
    if not save.is_file():
        print("ERROR: the save does not exist: %s" % save)
        return 2
    is_fixture = save.resolve() == FIXTURE.resolve()
    failures, names = static_check(save, is_fixture)
    for failure in failures:
        print("FAILED static: " + failure)
    if failures:
        return 1
    if args.exe is None:
        print("relationship state static check: OK (%d creatures in the block); runtime load not run (no --exe)"
              % len(names))
        return 0

    if os.name != "nt":
        print("ERROR: the runtime part runs the Windows game and the tasklist check; it does not run on this system")
        return 2
    exe = Path(args.exe)
    if not exe.is_file():
        print("ERROR: the executable does not exist: %s" % exe)
        return 2
    runtime = runtime_check(exe, save, args.seconds, names, is_fixture)
    if runtime is None:
        return 2
    for failure in runtime:
        print("FAILED runtime: " + failure)
    if runtime:
        return 1
    print("relationship state load: OK (%d creatures restored, listening, alive for %d s)" % (len(names), args.seconds))
    return 0


if __name__ == "__main__":
    sys.exit(main())
