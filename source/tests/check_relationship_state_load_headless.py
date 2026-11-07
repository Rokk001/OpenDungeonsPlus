"""Load check: a save with [RelationshipState] lines naming existing creatures keeps those relationships.

Without arguments the check runs the static part only, which needs no game and no build: the [RelationshipState] block
of the committed fixture source/tests/fixtures/relationship_state/RelationshipStateSmall.level must be accepted by the
same rules as readRelationshipCreatureStates (source/game/CreatureRelationships.cpp), and the restored values derived
from it by the rules of Creature::setRelationshipState must match the fixed expected values below.

The no-argument run also checks the seat-configured client protocol (check_relationship_state_seats_runtime.py,
static_protocol_check): the message names and the wire suffix must exist in the sources.

With --exe the runtime part is delegated to check_relationship_state_seats_runtime.py. The server restores saved
relationship state only after the seats are configured, so a bare server start (no client) cannot pass; the seat
client drives the normal loaded-save handshake instead. --version (the build version, for example 0.7.4.44) is
required with --exe and is not guessed. The run passes only when the game stays alive on a copy of the save in a new,
empty app-data folder (the original save is never opened for writing), the server reaches "Server connected and
listening", and for every creature of the block the "Restored relationship state" log line matches the restored values
derived from the save (rage turns, rage seat, brawl opponent, brawl turns, captor names). Creatures that are not in the
level are logged as unknown, as the loader does, and are not failures for a save other than the committed fixture.

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
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "relationship_state" / "RelationshipStateSmall.level"

LISTENING = "Server connected and listening"
BAD_SECTION = "Invalid RelationshipState section"
RESTORED = "Restored relationship state of %s, "
UNKNOWN = "Saved relationship state of unknown creature %s"
MAX_CAPTORS = 8  # RelationshipCreatureState::MAX_CAPTORS
INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1

# The fields of the restored log line, after the name (GameMap::applyPendingRelationshipStates, read back from the
# creature). Grief is restored as a record (Creature::setRelationshipState keeps it, without applying the mood again).
# Captor names contain no comma, so the captor group stops before the grief field that follows it.
RESTORED_LINE = re.compile(
    r"Restored relationship state of (?P<name>.+?), rageTurns=(?P<rage>-?\d+), captors=(?P<count>\d+), "
    r"rageSeat=(?P<seat>-?\d+), brawlOpponent=(?P<opponent>[^,]*), brawlTurns=(?P<brawl>-?\d+), "
    r"captorNames=(?P<captors>[^,\r\n]*), grief=(?P<grief>-?\d+)")

# Expected restored values of the committed fixture, written by hand from its block (not derived from the game).
# Each creature must be in a seat that allows relationships (a seat that exists, not rogue, not Hero, not a worker, not
# in prison), because Creature::setRelationshipState keeps the rage and the brawl only then; the fixture has only
# seat 1 (Keeper), so all of them are in it. The expectations are compared with the rules derived from the block (no
# game). The runtime comparison with the game log is run only by the --exe part, and was not run in this change (no
# build).
FIXTURE_EXPECTED = {
    "Knight1": {"grief": 0, "rageTurns": 5, "rageSeat": 0, "brawlOpponent": "", "captors": []},
    "Knight3": {"grief": 0, "rageTurns": 0, "rageSeat": -1, "brawlOpponent": "", "captors": ["Knight4"]},
}
# The loader keeps the grief within this many points in both directions (CreatureRelationships.cpp, STATE_GRIEF_LIMIT)
GRIEF_LIMIT = 100000


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


def loader_int(text):
    """Mirror of the loader's parseInt: one integer (sign allowed), surrounding white space allowed, int64 range only."""
    match = re.fullmatch(r"[ \t\n\v\f\r]*([+-]?[0-9]+)[ \t\n\v\f\r]*", text)
    return match is not None and INT64_MIN <= int(match.group(1)) <= INT64_MAX


def parse_block(block):
    """Applies the loader's accept or refuse rule to each line. Returns (failures, entries)."""
    failures = []
    entries = []
    for line in block:
        fields = line.split("\t")
        if len(fields) < 6 or not fields[0] or not all(loader_int(fields[i]) for i in (1, 2, 3, 5)):
            failures.append("the loader refuses the whole section on this line: %r" % line)
            continue
        entries.append({
            "name": fields[0], "grief": int(fields[1]), "rage": int(fields[2]), "seat": int(fields[3]),
            "brawl": fields[4], "brawlTurns": int(fields[5]), "captors": fields[6:],
        })
    return failures, entries


def int32(value):
    """Two's complement wrap to 32 bits: the loader stores a rage seat id in an int32_t (static_cast)."""
    return ((value + (1 << 31)) % (1 << 32)) - (1 << 31)


def restored_values(entry, existing):
    """The values the loader restores (Creature::setRelationshipState), read back as the log line prints them."""
    name = entry["name"]
    # The loader keeps the first MAX_CAPTORS non-empty captor fields; setRelationshipState then keeps the ones that exist
    named = [captor for captor in entry["captors"] if captor][:MAX_CAPTORS]
    captors = [captor for captor in named if captor in existing][:MAX_CAPTORS]
    seat = int32(entry["seat"])  # the seat test is made on the stored int32 value
    rage_kept = max(0, entry["rage"]) > 0 and seat >= 0
    opponent = entry["brawl"] if (entry["brawl"] and max(0, entry["brawlTurns"]) > 0 and entry["brawl"] != name) else ""
    return {
        "grief": max(-GRIEF_LIMIT, min(GRIEF_LIMIT, entry["grief"])),
        "rageTurns": max(0, entry["rage"]) if rage_kept else 0,
        "rageSeat": seat if rage_kept else -1,
        "brawlOpponent": opponent,
        # The restored brawl turns are capped by the level settings (mBrawlMaxTurns), which are not read here: the
        # log must show a positive value no larger than the saved one.
        "brawlTurnsAtMost": max(0, entry["brawlTurns"]) if opponent else 0,
        "captors": captors,
    }


def static_check(save_path, expect_fixture):
    """Checks the block of the save without the game.

    Returns (failures, entries, existing): the failures, the parsed entries of the block, and the names of the creatures
    of the level. Unknown creatures and captors are a failure only for the committed fixture; the loader accepts them
    (it warns, and drops the unknown captors).
    """
    text = save_path.read_text(encoding="utf-8", errors="replace")
    block = read_block(text)
    if block is None:
        return ["no closed [RelationshipState] block in %s" % save_path], [], set()
    existing = creatures_in(text)
    if existing is None:
        return ["no closed [Creatures] section in %s" % save_path], [], set()
    failures, entries = parse_block(block)
    if expect_fixture:
        for entry in entries:
            if entry["name"] not in existing:
                failures.append("%s is not a creature of the level" % entry["name"])
            for captor in entry["captors"]:
                if captor and captor not in existing:
                    failures.append("captor %s of %s is not a creature of the level" % (captor, entry["name"]))
        names = sorted(entry["name"] for entry in entries)
        if names != sorted(FIXTURE_EXPECTED):
            failures.append("fixture block names %s, expected %s" % (names, sorted(FIXTURE_EXPECTED)))
        for entry in entries:
            expected = FIXTURE_EXPECTED.get(entry["name"])
            if expected is None:
                continue
            derived = restored_values(entry, existing)
            for key in ("grief", "rageTurns", "rageSeat", "brawlOpponent", "captors"):
                if derived[key] != expected[key]:
                    failures.append("fixture %s: derived %s is %r, expected %r"
                                    % (entry["name"], key, derived[key], expected[key]))
    return failures, entries, existing


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
    failures, entries, _ = static_check(save, is_fixture)
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
              % len(entries))
        return 0
    if args.version is None:
        print("ERROR: --version is required with --exe (the build version, for example 0.7.4.44)")
        return 2
    return seats.run_with_exe(args.exe, args.save, args.seconds, seats.DEFAULT_PORT, args.version)


if __name__ == "__main__":
    sys.exit(main())
