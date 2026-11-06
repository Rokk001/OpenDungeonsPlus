"""Load check: a save with [RelationshipState] lines naming existing creatures keeps those relationships.

Without arguments the check runs the static part only, which needs no game and no build: the committed fixture
source/tests/fixtures/relationship_state/RelationshipStateSmall.level must contain a [RelationshipState] block whose
creatures exist in the fixture's [Creatures] section, and the block must match the fixed expected values below.

The no-argument run also checks the seat-configured client protocol (check_relationship_state_seats_runtime.py,
static_protocol_check): the message names and the wire suffix must exist in the sources.

With --exe the runtime part is delegated to check_relationship_state_seats_runtime.py. The server restores saved
relationship state only after the seats are configured, so a bare server start (no client) cannot pass; the seat
client drives the normal loaded-save handshake instead. --version (the build version, for example 0.7.4.44) is
required with --exe and is not guessed. The run passes only when the game stays alive on a copy of the save in a new,
empty app-data folder (the original save is never opened for writing), the server reaches "Server connected and
listening", every creature of the [RelationshipState] block is logged as restored, and, for the committed fixture,
the restored values match the fixed expectations below.

Usage:
  check_relationship_state_load_headless.py                                  (static part, the normal runner)
  check_relationship_state_load_headless.py --exe PATH --version X.Y.Z.N [--save PATH] [--seconds 30]
The TestGhosts runtime test is run the same way with its own --save and --exe.
The check starts only its own process. It refuses to run while another opendungeons-plus.exe is running, so
that a game the owner is playing is never touched.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

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


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--exe", default=None, help="the game executable; without it only the static part runs")
    parser.add_argument("--save", default=str(FIXTURE),
                        help="the save with RelationshipState lines naming existing creatures")
    parser.add_argument("--seconds", type=int, default=30, help="how long the server must stay alive")
    parser.add_argument("--version", default=None,
                        help="the build version of the executable, required with --exe (for example 0.7.4.44)")
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

    sys.path.insert(0, str(HERE))  # the seat client is in this folder
    import check_relationship_state_seats_runtime as seats  # noqa: E402

    failures = seats.static_protocol_check()
    for failure in failures:
        print("FAILED static: " + failure)
    if failures:
        return 1
    if args.exe is None:
        print("relationship state static check: OK (%d creatures in the block); runtime load not run (no --exe)"
              % len(names))
        return 0
    if args.version is None:
        print("ERROR: --version is required with --exe (the build version, for example 0.7.4.44)")
        return 2
    return seats.run_with_exe(args.exe, args.save, args.seconds, seats.DEFAULT_PORT, args.version)


if __name__ == "__main__":
    sys.exit(main())
