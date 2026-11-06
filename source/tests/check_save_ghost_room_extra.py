"""Static check: the save reader accepts the optional 'GhostApparatus' tail of a ghost room (room type 25) as the loader.

Pure Python, needs no compiler and never starts the game. It loads check_save_games_load.py without a save folder
and runs its read_room_extra for room type 25 on small texts. The expected results follow
RoomGhostRoom::importFromStream: the marker is optional; a written marker is followed by three apparatuses of
queue (uint32), working (bool 0/1), workTurns (finite double) and crystalEctoplasm (uint32); any other token is
left for the [/Room] check.
"""
import os
from pathlib import Path
import sys
import tempfile

here = Path(__file__).resolve().parent
source = (here / "check_save_games_load.py").read_text(encoding="utf-8")
# Load only the definitions: the module exits when there is no save and runs its save loop after them.
head = source.split("\nbad = 0\n", 1)[0].replace("    sys.exit(0)\n", "    pass\n", 1)
empty = tempfile.mkdtemp(prefix="ghost-room-check-")
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
read_room_extra = ns["read_room_extra"]

failures = []

ZEROS = "0 0 0 0 0 0 0 0 0 0 0 0"


def expect(name, text, ok_end):
    """Runs the type 25 tail on text; ok_end is the token that must follow it, or None when a refusal is expected."""
    s = Stream(text)
    try:
        read_room_extra(s, 25, "GhostRoom1", 0)
        token = s.tok()
        if ok_end is None:
            failures.append("%s: expected a refusal, got token %r" % (name, token))
        elif token != ok_end:
            failures.append("%s: expected %r after the tail, got %r" % (name, ok_end, token))
    except LoadFailure as e:
        if ok_end is not None:
            failures.append("%s: refused (%s)" % (name, e))


# Old saves end the room at [/Room]: the apparatuses start idle and empty.
expect("no marker", "[/Room]\n", "[/Room]")
# The shape written by exportToStream: the marker and 3 x (queue working workTurns crystal) on one line.
expect("idle marker", "GhostApparatus " + ZEROS + "\n[/Room]\n", "[/Room]")
expect("running values", "GhostApparatus 5 1 2.5 7 0 0 -0.25 3 1 0 1e2 9\n[/Room]\n", "[/Room]")
expect("full precision", "GhostApparatus 4294967295 0 0.10000000000000001 0 0 1 0 0 0 0 0 0\n[/Room]\n", "[/Room]")
expect("marker split over lines", "GhostApparatus\n" + "\n".join(ZEROS.split()) + "\n[/Room]\n", "[/Room]")
# A different token is not consumed; the [/Room] check then reports it.
expect("other token left alone", "GhostApparatus2 " + ZEROS + "\n[/Room]\n", "GhostApparatus2")
# Refused like operator>> of the loader: missing values, a bad bool, a non-finite double, out-of-range unsigned ints.
expect("marker alone", "GhostApparatus\n[/Room]\n", None)
expect("one value missing", "GhostApparatus 0 0 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("working is 2", "GhostApparatus 0 2 0 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("working is true", "GhostApparatus 0 true 0 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("work turns nan", "GhostApparatus 0 0 nan 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("work turns inf", "GhostApparatus 0 0 0 0 0 inf 0 0 0 0 0 0\n[/Room]\n", None)
expect("work turns overflow", "GhostApparatus 0 0 1e999 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("queue above uint32", "GhostApparatus 4294967296 0 0 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("crystal not a number", "GhostApparatus 0 0 0 abc 0 0 0 0 0 0 0 0\n[/Room]\n", None)
# A minus sign is accepted by operator>> into a uint32_t and wraps (-1 reads as 4294967295); the magnitude must fit 32 bits.
expect("queue -1 wraps as the loader", "GhostApparatus -1 0 0 0 0 0 0 0 0 0 0 0\n[/Room]\n", "[/Room]")
expect("crystal -2 wraps as the loader", "GhostApparatus 0 0 0 -2 0 0 0 0 0 0 0 0\n[/Room]\n", "[/Room]")
expect("queue magnitude above uint32", "GhostApparatus -4294967296 0 0 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("queue with underscore", "GhostApparatus 1_0 0 0 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
# operator>> of a double: a value that rounds to zero is refused (the writer never writes one); the smallest denormal is kept.
expect("work turns underflows to zero", "GhostApparatus 0 0 1e-400 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("work turns half the smallest denormal", "GhostApparatus 0 0 2e-324 0 0 0 0 0 0 0 0 0\n[/Room]\n", None)
expect("work turns smallest denormal", "GhostApparatus 0 0 5e-324 0 0 0 0 0 0 0 0 0\n[/Room]\n", "[/Room]")
expect("work turns zero", "GhostApparatus 0 0 0.0e-5 0 0 0 0 0 0 0 0 0\n[/Room]\n", "[/Room]")

if failures:
    for f in failures:
        print("FAILED " + f)
    print("check_save_ghost_room_extra: %d failure(s)" % len(failures))
    sys.exit(1)
print("check_save_ghost_room_extra: OK")
