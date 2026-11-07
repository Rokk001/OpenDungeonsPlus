"""Static check: the save reader accepts and refuses [RelationshipState] lines exactly as the loader does.

Pure Python, needs no compiler and never starts the game. It loads check_save_games_load.py without a save folder
and runs its read_relationship_states on small texts. The expected results follow readRelationshipCreatureStates
(source/game/CreatureRelationships.cpp): lines are split on tabs only, the numbers are read like operator>> int64
(leading white space and a sign are accepted, trailing white space is accepted, overflow is refused), and the name
must not be empty. Lines that name an existing creature are restored by GameMap::createAllEntities, so they must
be accepted or refused the same way the loader does.
"""
import os
from pathlib import Path
import sys
import tempfile

here = Path(__file__).resolve().parent
source = (here / "check_save_games_load.py").read_text(encoding="utf-8")
# Load only the definitions: the module exits when there is no save and runs its save loop after them.
head = source.split("\nbad = 0\n", 1)[0].replace("    sys.exit(0)\n", "    pass\n", 1)
empty = tempfile.mkdtemp(prefix="relationship-state-check-")
saved_argv = sys.argv
sys.argv = [str(here / "check_save_games_load.py"), "--dir", empty]
ns = {"__name__": "check_save_games_load_module", "__file__": str(here / "check_save_games_load.py")}
try:
    exec(compile(head, str(here / "check_save_games_load.py"), "exec"), ns)
finally:
    sys.argv = saved_argv
    os.rmdir(empty)

Stream = ns["Stream"]
LoadFailure = ns["LoadFailure"]
read_relationship_states = ns["read_relationship_states"]

failures = []


loader_text = ns["loader_text"]


def expect(name, text, accepted):
    """Runs the reader on text (the lines after the [RelationshipState] tag); accepted says whether it must pass."""
    s = Stream(text)
    try:
        read_relationship_states(s)
        if not accepted:
            failures.append("%s: expected a refusal, but the block was accepted" % name)
        elif s.tok() is not None:
            failures.append("%s: the block did not end at [/RelationshipState]" % name)
    except LoadFailure as e:
        if accepted:
            failures.append("%s: refused (%s)" % (name, e))


def expect_file(name, raw, accepted):
    """Same as expect, but the text first goes through loader_text, as a save file does before the reader."""
    expect(name, loader_text(raw), accepted)


END = "[/RelationshipState]\n"

# Accepted: the shape written by writeRelationshipCreatureStates, with and without a captor, as in the TestGhosts save.
expect("existing creature with captor", "EnemyRat1\t0\t0\t-1\t\t0\tOrc1\n" + END, True)
expect("two existing creatures", "EnemyRat1\t0\t0\t-1\t\t0\tOrc1\nEnemyOrc1\t0\t0\t-1\t\t0\tPitDemon1\n" + END, True)
expect("existing creature without captor", "EnemyRat1\t0\t0\t-1\t\t0\n" + END, True)
expect("grief rage and brawl", "Orc1\t-40\t12\t3\tRat1\t20\n" + END, True)
expect("creature name not on the map", "NoSuchCreature1\t0\t0\t-1\t\t0\tOrc1\n" + END, True)
expect("empty block", END, True)
expect("comment line skipped", "# written by hand\nEnemyRat1\t0\t0\t-1\t\t0\n" + END, True)
expect("empty line skipped", "\nEnemyRat1\t0\t0\t-1\t\t0\n\n" + END, True)
# operator>> skips leading white space and accepts a sign; trailing white space after a number is accepted.
expect("leading white space in a number", "EnemyRat1\t 0\t0\t-1\t\t 0\n" + END, True)
expect("sign and trailing white space", "EnemyRat1\t+0\t0 \t-1\t\t0 \n" + END, True)
expect("int64 limits", "Orc1\t0\t9223372036854775807\t-9223372036854775808\t\t0\n" + END, True)

# Refused: each case is refused by readRelationshipCreatureStates.
expect("too few fields", "EnemyRat1\t0\t0\t-1\t\n" + END, False)
expect("empty name", "\t0\t0\t-1\t\t0\n" + END, False)
expect("grief not a number", "EnemyRat1\tx\t0\t-1\t\t0\n" + END, False)
expect("two numbers in one field", "EnemyRat1\t1 2\t0\t-1\t\t0\n" + END, False)
expect("rage turns overflow int64", "EnemyRat1\t0\t9223372036854775808\t-1\t\t0\n" + END, False)
expect("brawl turns not a number", "EnemyRat1\t0\t0\t-1\t\t1.5\n" + END, False)
expect("space-only line is not empty for the loader", "  \n" + END, False)
expect("end tag missing", "EnemyRat1\t0\t0\t-1\t\t0\n", False)

# Carriage returns, through loader_text (the file path): CRLF lines are read as LF lines, one more trailing carriage
# return is removed by the reader, and a carriage return inside a line stays there.
expect_file("CRLF file", "EnemyRat1\t0\t0\t-1\t\t0\r\n[/RelationshipState]\r\n", True)
expect_file("two trailing carriage returns", "EnemyRat1\t0\t0\t-1\t\t0\r\r\n[/RelationshipState]\n", True)
expect_file("carriage return before a comment", "EnemyRat1\t0\t0\t-1\t\t0\r# written by hand\n[/RelationshipState]\n", True)
expect_file("carriage return inside a number", "EnemyRat1\t0\r0\t-1\t\t0\n[/RelationshipState]\n", False)
expect_file("carriage return inside the name", "Enemy\rRat1\t0\t0\t-1\t\t0\n[/RelationshipState]\n", True)
expect_file("carriage return after the end tag", "[/RelationshipState]\r\n", True)

if failures:
    for f in failures:
        print("FAILED " + f)
    print("check_save_relationship_state_extra: %d failure(s)" % len(failures))
    sys.exit(1)
print("check_save_relationship_state_extra: OK")
