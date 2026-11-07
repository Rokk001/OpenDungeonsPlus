"""Static check: the save reader accepts the optional 'Merchant <x> <y>' line of a merchant room exactly as the loader.

Pure Python, needs no compiler and never starts the game. It loads check_save_games_load.py without a save folder
and runs its read_room_extra for room type 20 on small texts. The expected results follow
RoomMerchant::importFromStream: the marker is optional, a written marker needs two numbers, and any other token is
left for the [/Room] check.
"""
import os
from pathlib import Path
import runpy
import sys
import tempfile

here = Path(__file__).resolve().parent
source = (here / "check_save_games_load.py").read_text(encoding="utf-8")
# Load only the definitions: the module exits when there is no save and runs its save loop after them.
head = source.split("\nbad = 0\n", 1)[0].replace("    sys.exit(0)\n", "    pass\n", 1)
empty = tempfile.mkdtemp(prefix="merchant-room-check-")
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


def expect(name, text, ok_end, ok_token=None):
    """Runs the type 20 tail on text; ok_end is the token that must follow it, or None when a failure is expected."""
    s = Stream(text)
    try:
        read_room_extra(s, 20, "Merchant1", 0)
        token = s.tok()
        if ok_end is None:
            failures.append("%s: expected a refusal, got token %r" % (name, token))
        elif token != ok_end:
            failures.append("%s: expected %r after the tail, got %r" % (name, ok_end, token))
    except LoadFailure as e:
        if ok_end is not None:
            failures.append("%s: refused (%s)" % (name, e))


# Without the optional marker the reader stays where it was (the saved shape of every merchant room before f867bb35b).
expect("no marker", "[/Room]\n", "[/Room]")
# The marker is written by exportToStream on its own line before [/Room].
expect("marker", "Merchant 3 4\n[/Room]\n", "[/Room]")
expect("marker with fractions and negative values", "Merchant 3.5 -2\n[/Room]\n", "[/Room]")
expect("marker split over lines", "Merchant\n3\n4\n[/Room]\n", "[/Room]")
# operator>> needs both numbers; a marker with one number or a non-number is refused.
expect("marker with one number", "Merchant 3\n[/Room]\n", None)
expect("marker with text", "Merchant abc 4\n[/Room]\n", None)
expect("marker with no numbers", "Merchant\n[/Room]\n", None)
# A different token is not consumed; the [/Room] check then reports it.
expect("other token left alone", "Merchant2 3 4\n[/Room]\n", "Merchant2")
# Numeric edge cases: operator>> reads no inf, nan or underscores, and an Ogre::Real (float) fails above FLT_MAX.
expect("infinity is not a number", "Merchant inf 4\n[/Room]\n", None)
expect("nan is not a number", "Merchant 3 nan\n[/Room]\n", None)
expect("underscore is not a digit separator", "Merchant 1_0 4\n[/Room]\n", None)
expect("value above float range", "Merchant 1e39 4\n[/Room]\n", None)
expect("value at the largest float", "Merchant 3.4028234e38 4\n[/Room]\n", "[/Room]")
# Carriage returns: a file read in text mode keeps a carriage return inside a line, and operator>> reads it as white space.
expect("carriage return between the numbers", "Merchant 3\r4\n[/Room]\n", "[/Room]")
expect("carriage return before the end tag", "Merchant 3 4\r\n[/Room]\n", "[/Room]")
# Underflow: a nonzero value that rounds to zero is refused; the smallest denormal float is kept.
expect("value below the smallest float", "Merchant 7e-46 4\n[/Room]\n", None)
expect("value at the smallest denormal float", "Merchant 1.4e-45 4\n[/Room]\n", "[/Room]")
expect("zero", "Merchant 0 0.0\n[/Room]\n", "[/Room]")

if failures:
    for f in failures:
        print("FAILED " + f)
    print("check_save_merchant_room_extra: %d failure(s)" % len(failures))
    sys.exit(1)
print("check_save_merchant_room_extra: OK")
