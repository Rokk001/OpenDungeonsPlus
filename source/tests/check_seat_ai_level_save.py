"""Static check: seats without an AI level (hero seats) are saved and loaded without breaking the seat header.

Pure Python, needs no compiler. Cause of the failure: KeeperAITypes::toString(nbAI) gave the two-word text
"Wrong value", which the writer put after "aiLevel"; the reader took only one word and then saw "value"
instead of "faction". Mirrors the reader of readOptionalAiLevel, checks the writer guard in the source,
and runs the reader on the real seat header format and on any --save files.
"""
import argparse
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--save", action="append", default=[])
args = parser.parse_args()
failures = []
LEVELS = ["easy", "normal", "hard", "medium", "hell"]


def check(condition, label):
    if not condition:
        failures.append(label)


def read_seat_header(tokens):
    """Mirror of Seat::importSeatFromStream from 'player' to 'faction'; returns (level, ok)."""
    if tokens.pop(0) != "player":
        return None, False
    tokens.pop(0)
    nxt = tokens.pop(0)
    level = None
    if nxt == "aiLevel":
        name = tokens.pop(0)
        if name == "Wrong":
            rest = tokens.pop(0)
            if rest != "value":
                return None, rest == "faction"
        nxt = tokens.pop(0)
        if name in LEVELS:
            level = name
    return level, nxt == "faction"


fmt = "player AI aiLevel %s faction Hero startingX 47"
check(read_seat_header((fmt % "hell").split()) == ("hell", True), "valid level not read")
check(read_seat_header((fmt % "Wrong value").split()) == (None, True), "old 'Wrong value' placeholder breaks the seat")
check(read_seat_header("player AI faction Hero".split()) == (None, True), "seat without aiLevel breaks")

reader = (root / "source/ai/AiSaveFormat.cpp").read_text(encoding="utf-8")
seat = (root / "source/game/Seat.cpp").read_text(encoding="utf-8")
check('name == "Wrong"' in reader and '"value"' in reader, "reader no longer skips the 'Wrong value' placeholder")
check("mAiLevel < KeeperAIType::nbAI)\n            os << \"aiLevel" in seat, "writer writes aiLevel for seats without a level")

for path in args.save:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == "[Seat]":
            block = []
            j = i + 1
            while j < len(lines) and len(block) < 20:
                block += lines[j].split()
                j += 1
            k = block.index("player")
            level, ok = read_seat_header(block[k:])
            check(ok, "%s: seat header unreadable near line %d" % (path, i + 1))
        i += 1

if failures:
    print("FAILED:\n" + "\n".join(failures))
    sys.exit(1)
print("OK")
