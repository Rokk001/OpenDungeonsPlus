"""Static check: every saved game in the user's saves folder can be read by the level loader.

Pure Python, needs no compiler and never starts the game. The folder %APPDATA%/opendungeons/saves (or
~/.config/opendungeons/saves on other systems) is only read, nothing is copied. Without that folder, or without
any save in it, the check is skipped and reports OK.

The reader of MapHandler::readGameMapFromFile is mirrored section by section with its own rules: the version gate,
the section order, the field counts and the required keys and ranges of the seats, tiles, rooms, traps, lights,
creatures, the entity sections and the level script. For every save the first reason why the loader would refuse
it is printed. It also reports the places where the loader could crash instead of refusing (a reference to a seat
that does not exist, a tile outside of the map, a truncated section).

Usage: check_save_games_load.py [--dir FOLDER] [--verbose]
"""
import argparse
from decimal import Context, Decimal
import math
import os
from pathlib import Path
import re
import sys

# Smallest magnitude that rounds to infinity as a 32-bit float (FLT_MAX plus half a unit in the last place)
FLOAT32_OVERFLOW = Decimal(2 ** 128 - 2 ** 103)
# Smallest magnitude that rounds to infinity as a 64-bit double (DBL_MAX plus half a unit in the last place)
DOUBLE_OVERFLOW = Decimal(2 ** 1024 - 2 ** 970)
# Largest magnitude that rounds to zero (half of the smallest denormal, a tie that rounds to the even zero).
# Exact: the context is wide enough for every digit of 2^-150 and 2^-1075.
_EXACT = Context(prec=1200, Emax=10 ** 6, Emin=-10 ** 6)
FLOAT32_UNDERFLOW = _EXACT.power(Decimal(2), -150)
DOUBLE_UNDERFLOW = _EXACT.power(Decimal(2), -1075)
# The white space of operator>> in the C locale (isspace); Python's str.isspace also takes other characters
WHITESPACE = " \t\n\v\f\r"

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dir", default=None)
parser.add_argument("--verbose", action="store_true")
args = parser.parse_args()

if args.dir:
    saves_dir = Path(args.dir)
elif os.environ.get("APPDATA"):
    saves_dir = Path(os.environ["APPDATA"]) / "opendungeons" / "saves"
else:
    saves_dir = Path.home() / ".config" / "opendungeons" / "saves"
files = sorted(saves_dir.glob("*.level")) if saves_dir.is_dir() else []
if not files:
    print("SKIPPED: no saved games in " + str(saves_dir))
    sys.exit(0)


def read_source(relative):
    return (root / relative).read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- facts taken from the sources
map_handler = read_source("source/gamemap/MapHandler.cpp")
releases = re.search(r"const char\* releases\[\] = \{([^}]*)\}", map_handler)
RELEASES = re.findall(r'"([^"]+)"', releases.group(1)) if releases else []
GAME_VERSION = re.search(r'const std::string ODApplication::VERSION = "([^"]+)"', read_source("source/ODApplication.cpp"))
GAME_HEADER = "OpenDungeons_Version:" + (GAME_VERSION.group(1) if GAME_VERSION else "0")

skill_source = read_source("source/game/SkillType.cpp")
SKILLS = set(re.findall(r'return "(\w+)";', skill_source.split("std::string toString(SkillType type)")[1]))
alias_source = read_source("source/utils/NameAliases.cpp")
ALIAS_HASHES = {int(h, 16): n for h, n in re.findall(r'\{\s*(0x[0-9a-fA-F]+)ULL,\s*"(\w+)"\s*\}', alias_source)}
tile_header = read_source("source/entities/Tile.h")
VISUALS = [v for v in re.findall(r"\w+", re.search(r"enum class TileVisual\s*\{([^}]*)\}", tile_header).group(1))
           if v not in ("nullTileVisual", "countTileVisual")]
creature_cfg = read_source("config/creatures.cfg")
CLASSES = set(re.findall(r"^\s*Name\s+(\S+)", creature_cfg, re.M))
ROOM_TYPE_MAX = 26
TRAP_TYPE_MAX = 17


def alias(name):
    """Mirror of NameAliases::resolve."""
    h = 14695981039346656037
    for ch in name:
        h ^= ord(ch.lower()) & 0xFF
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return ALIAS_HASHES.get(h, name)


class LoadFailure(Exception):
    pass


def fail(message):
    raise LoadFailure(message)


class Stream:
    """Character stream with the operations of a std::stringstream (token, line, peek, seek)."""

    def __init__(self, text):
        self.text = text
        self.pos = 0

    def tok(self):
        n = len(self.text)
        while self.pos < n and self.text[self.pos] in WHITESPACE:
            self.pos += 1
        if self.pos >= n:
            return None
        start = self.pos
        while self.pos < n and self.text[self.pos] not in WHITESPACE:
            self.pos += 1
        return self.text[start:self.pos]

    def need(self, what):
        t = self.tok()
        if t is None:
            fail("unexpected end of file while reading " + what)
        return t

    def line(self):
        if self.pos >= len(self.text):
            return None
        end = self.text.find("\n", self.pos)
        if end < 0:
            end = len(self.text)
        line = self.text[self.pos:end]
        self.pos = min(len(self.text), end + 1)
        return line

    def peek(self):
        return self.text[self.pos] if self.pos < len(self.text) else ""

    def integer(self, what):
        t = self.need(what)
        if not is_int(t):
            fail("%s is not an integer: '%s'" % (what, t[:40]))
        return int(t)

    def number(self, what):
        # operator>> reads a double only in the decimal form of is_num; Python's float() also takes inf, nan and underscores
        t = self.need(what)
        if not is_num(t) or abs(Decimal(t)) >= DOUBLE_OVERFLOW or rounds_to_zero(t, DOUBLE_UNDERFLOW):
            fail("%s is not a number: '%s'" % (what, t[:40]))
        return float(t)

    def real32(self, what):
        # An Ogre::Real (float) read: operator>> also fails when the value does not fit a float (rounds to infinity)
        t = self.need(what)
        if not is_num(t) or abs(Decimal(t)) >= FLOAT32_OVERFLOW or rounds_to_zero(t, FLOAT32_UNDERFLOW):
            fail("%s is not a float: '%s'" % (what, t[:40]))
        return float(t)


def is_int(t):
    # ASCII digits only: \d also matches other Unicode digits, which the loader does not read
    return re.fullmatch(r"[+-]?[0-9]+", t) is not None


def is_num(t):
    return re.fullmatch(r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?", t) is not None


def rounds_to_zero(t, threshold):
    """A nonzero decimal text whose magnitude is at most the threshold reads as zero. Refused: the writer never writes
    such a value, and whether the loader's stream then fails is not verified for the Windows build (see the report)."""
    d = abs(Decimal(t))
    return d != 0 and d <= threshold


def read_relationship_states(s):
    """Mirror of readRelationshipCreatureStates, read after the [RelationshipState] tag.

    readFile has already removed one trailing carriage return and the comment of each line; the reader then removes
    one more trailing carriage return (getline), splits on tabs only, and reads each number like operator>> int64.
    A line naming an existing creature is restored by GameMap::createAllEntities, so it must parse exactly as the
    loader does."""
    while True:
        ln = s.line()
        if ln is None:
            fail("[RelationshipState] has no end")
        if ln.endswith("\r"):
            ln = ln[:-1]
        if ln == "[/RelationshipState]":
            return
        if not ln or ln[0] == "#":
            continue
        f = ln.split("\t")
        if len(f) < 6 or not f[0] or not loader_int(f[1]) or not loader_int(f[2]) or not loader_int(f[3]) \
                or not loader_int(f[5]):
            fail("relationship state line invalid: " + ln[:60])


def loader_int(t):
    """Mirror of the loader's parseInt: istringstream >> int64_t, then nothing but white space may follow.

    Leading white space and a sign are accepted, a value outside int64 is refused (the stream fails on overflow)."""
    m = re.fullmatch(r"[ \t\n\v\f\r]*([+-]?[0-9]+)[ \t\n\v\f\r]*", t)
    return m is not None and -(1 << 63) <= int(m.group(1)) <= (1 << 63) - 1


# ---------------------------------------------------------------- the mirror of the loader
def loader_text(raw):
    """The text the level loader reads from a save: the file is opened in text mode on Windows (CRLF becomes LF), then
    Helper::readFile(withoutComments) removes one trailing carriage return of each line and everything from the first
    '#'. A carriage return that is not at the end of a line stays in the text, where operator>> reads it as white space.
    Each line of the file gives one line of the result, and the last getline that fails adds one more empty line."""
    lines = []
    for ln in raw.replace("\r\n", "\n").split("\n"):
        if ln.endswith("\r"):
            ln = ln[:-1]
        lines.append(ln.split("#", 1)[0])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- the mirror of the loader
class Save:
    def __init__(self, path):
        raw = path.read_bytes().decode("utf-8", errors="replace")
        self.text = loader_text(raw)
        self.name = path.name
        self.seat_ids = set()
        self.width = self.height = 0

    def supported_header(self, header):
        if header == GAME_HEADER:
            return True
        for base in RELEASES:
            if header == base:
                return True
            if len(header) > len(base) + 1 and header.startswith(base) and header[len(base)] == "." \
                    and header[len(base) + 1:].isdigit():
                return True
        return False


def read_seat(s, save):
    """Mirror of Seat::importSeatFromStream."""
    if s.need("seatId key") != "seatId":
        fail("seat: expected seatId")
    seat_id = s.integer("seatId")
    if seat_id == 0:
        fail("seat: forbidden seatId 0")
    if seat_id in save.seat_ids:
        fail("seat: duplicated seat id %d" % seat_id)
    save.seat_ids.add(seat_id)
    if s.need("teamId") != "teamId":
        fail("seat %d: expected teamId" % seat_id)
    s.need("team value")
    if s.need("player key") != "player":
        fail("seat %d: expected player" % seat_id)
    s.need("player type")
    t = s.tok()
    if t == "aiLevel":
        name = s.need("aiLevel value")
        if name == "Wrong":
            rest = s.need("aiLevel rest")
            if rest != "value":
                t = rest
            else:
                t = s.need("faction")
        else:
            t = s.need("faction")
    if t != "faction":
        fail("seat %d: expected faction and read %s" % (seat_id, t))
    s.need("faction value")
    for key, kind in (("startingX", "i"), ("startingY", "i"), ("colorId", "i"), ("gold", "n"), ("goldMined", "n"),
                      ("mana", "n")):
        if s.need(key) != key:
            fail("seat %d: expected %s" % (seat_id, key))
        s.integer(key) if kind == "i" else s.number(key)
    if s.need("[SkillDone]") != "[SkillDone]":
        fail("seat %d: expected [SkillDone]" % seat_id)
    done = []
    while True:
        t = s.tok()
        if t is None:
            fail("seat %d: [SkillDone] has no end (the loader would loop forever)" % seat_id)
        if t == "[/SkillDone]":
            break
        if alias(t) in SKILLS and alias(t) not in done:
            done.append(alias(t))
    t = s.need("seat block")
    while t in ("[ResearchProgress]", "[HadLibrary]", "[StoredSpecials]", "[AnnouncedCreatureClasses]", "[Infirmary]",
                "[SpellCooldowns]", "[Merchant]", "[MerchantBalance]", "[GhostRoom]", "[GhostBells]",
                "[ResearchRemainder]", "[WorkerJobs]"):
        if t == "[SpellCooldowns]":
            count = s.integer("cooldown count")
            for _ in range(count):
                s.need("cooldown name")
                s.integer("cooldown turns")
            if s.need("[/SpellCooldowns]") != "[/SpellCooldowns]":
                fail("seat %d: spell cooldown block not closed" % seat_id)
        elif t == "[WorkerJobs]":
            v = [s.integer("worker jobs") for _ in range(6 + 1 + 6 + 7 + 1)]
            if s.need("[/WorkerJobs]") != "[/WorkerJobs]":
                fail("seat %d: worker jobs block not closed" % seat_id)
            if v[6] > 1 or v[-1] > 1 or sorted(v[7:13]) != list(range(6)) or sorted(v[13:20]) != list(range(7)):
                fail("seat %d: invalid worker job settings" % seat_id)
        elif t == "[ResearchRemainder]":
            r = s.number("research remainder")
            if r < 0.0 or r >= 1.0:
                fail("seat %d: research remainder out of range" % seat_id)
        elif t == "[GhostBells]":
            for _ in range(s.integer("bell count")):
                s.need("bell")
            if s.need("[/GhostBells]") != "[/GhostBells]":
                fail("seat %d: ghost bells not closed" % seat_id)
        elif t == "[GhostRoom]":
            s.number("ecto")
            product = s.integer("ghost product")
            s.integer("ghost revive")
            if product > 2 or s.need("[/GhostRoom]") != "[/GhostRoom]":
                fail("seat %d: ghost room block invalid" % seat_id)
        elif t == "[Infirmary]":
            s.integer("payer")
            s.integer("threshold")
            if s.integer("heal on") not in (0, 1) or s.need("[/Infirmary]") != "[/Infirmary]":
                fail("seat %d: infirmary block invalid" % seat_id)
        elif t == "[ResearchProgress]":
            points = s.integer("skill points")
            count = s.integer("research count")
            if points < 0 or count >= len(SKILLS) + 1:
                fail("seat %d: research progress header invalid" % seat_id)
            seen = set()
            for _ in range(count):
                name = alias(s.need("research name"))
                level = s.integer("research level")
                if name not in SKILLS or name not in done or level < 1 or level > 3 or name in seen:
                    fail("seat %d: research progress entry '%s' %d is not a finished skill of level 1-3"
                         % (seat_id, name, level))
                seen.add(name)
            if s.need("[/ResearchProgress]") != "[/ResearchProgress]":
                fail("seat %d: research progress not closed" % seat_id)
        elif t == "[HadLibrary]":
            s.integer("had library")
        elif t == "[StoredSpecials]":
            for _ in range(s.integer("special count")):
                s.integer("special type")
                s.integer("special amount")
            if s.need("[/StoredSpecials]") != "[/StoredSpecials]":
                fail("seat %d: stored specials not closed" % seat_id)
        elif t == "[AnnouncedCreatureClasses]":
            while True:
                n = s.tok()
                if n is None:
                    fail("seat %d: announced classes not closed" % seat_id)
                if n == "[/AnnouncedCreatureClasses]":
                    break
        elif t == "[Merchant]":
            margin = s.integer("merchant margin")
            mode = s.need("merchant mode")
            lab = s.integer("lab mode")
            if margin < 0 or mode not in ("fair", "profit") or lab < 0 or lab > 2 or \
                    s.need("[/Merchant]") != "[/Merchant]":
                fail("seat %d: merchant block invalid" % seat_id)
        elif t == "[MerchantBalance]":
            v = s.number("merchant balance")
            if v < 0.0 or v >= 1.0 or s.need("[/MerchantBalance]") != "[/MerchantBalance]":
                fail("seat %d: merchant balance invalid" % seat_id)
        t = s.need("seat block")
    if t != "[SkillNotAllowed]":
        fail("seat %d: expected [SkillNotAllowed] and read %s" % (seat_id, t))
    for tag in ("[/SkillNotAllowed]", None):
        pass
    while True:
        n = s.tok()
        if n is None:
            fail("seat %d: [SkillNotAllowed] has no end (the loader would loop forever)" % seat_id)
        if n == "[/SkillNotAllowed]":
            break
    if s.need("[SkillPending]") != "[SkillPending]":
        fail("seat %d: expected [SkillPending]" % seat_id)
    while True:
        n = s.tok()
        if n is None:
            fail("seat %d: [SkillPending] has no end (the loader would loop forever)" % seat_id)
        if n == "[/SkillPending]":
            break
    # tile visuals, each one optional, in the order of the enum
    finished = False
    for visual in VISUALS:
        pos = s.pos
        t = s.need("tile visual tag")
        if t == "[/Seat]":
            finished = True
            break
        tag = t
        m = re.fullmatch(r"\[(/?)(\w+)\]", t)
        if m:
            tag = "[" + m.group(1) + alias(m.group(2)) + "]"
        if tag != "[" + visual + "]":
            s.pos = pos
            continue
        while True:
            n = s.tok()
            if n is None:
                fail("seat %d: [%s] has no end (the loader would loop forever)" % (seat_id, visual))
            m = re.fullmatch(r"\[(/?)(\w+)\]", n)
            if m and m.group(1) == "/" and alias(m.group(2)) == visual:
                break
            x = int(n) if is_int(n) else 0
            y = s.integer("visual y")
            s.integer("visual seat")
            if not (0 <= x < save.width and 0 <= y < save.height):
                fail("seat %d: tile visual [%s] outside the map (%s,%s)" % (seat_id, visual, x, y))
    if finished:
        return seat_id
    if s.need("[markedTiles]") != "[markedTiles]":
        fail("seat %d: expected [markedTiles] (a tile visual block is out of the order the loader reads)" % seat_id)
    while True:
        n = s.tok()
        if n is None:
            fail("seat %d: [markedTiles] has no end (the loader would loop forever)" % seat_id)
        if n == "[/markedTiles]":
            break
        s.need("marked y")
    t = s.need("seat block")
    if t == "[EverVisitedTiles]":
        while True:
            n = s.tok()
            if n is None:
                fail("seat %d: [EverVisitedTiles] has no end (the loader would loop forever)" % seat_id)
            if n == "[/EverVisitedTiles]":
                t = s.need("seat block")
                break
            x = int(n) if is_int(n) else -1
            y = s.integer("visited y")
            if not (0 <= x < save.width and 0 <= y < save.height):
                fail("seat %d: ever visited tile (%s,%s) is outside the map (the loader writes past its array)"
                     % (seat_id, n, y))
    if t == "[OwnCreatureSightAges]":
        while True:
            n = s.tok()
            if n is None:
                fail("seat %d: [OwnCreatureSightAges] has no end (the loader would loop forever)" % seat_id)
            if n == "[/OwnCreatureSightAges]":
                break
            s.integer("sight y")
            s.integer("sight age")
        t = s.need("seat block")
    if t == "[AIState]":
        while True:
            ln = s.line()
            if ln is None:
                fail("seat %d: [AIState] has no end" % seat_id)
            if ln.strip() == "[/AIState]":
                break
        t = s.need("[/Seat]")
    elif t != "[/Seat]":
        # older saves: the lines of the AI state follow without tags (readUntaggedBlockLines)
        s.line()
        while True:
            ln = s.line()
            if ln is None:
                fail("seat %d: the AI state lines have no [/Seat]" % seat_id)
            if ln.strip() == "[/Seat]":
                t = "[/Seat]"
                break
    if t != "[/Seat]":
        fail("seat %d: expected [/Seat] and read %s" % (seat_id, t))
    return seat_id


GOALS = ("KillAllEnemies", "ProtectCreature", "ClaimNTiles", "MineNGold", "ProtectDungeonTemple")


def read_goal(s, name, depth=0):
    """Mirror of Goals::loadGoalFromStream."""
    if depth > 20:
        fail("goal nesting too deep")
    s.line()
    known = name in GOALS
    c = s.peek()
    if c in ("+", "-"):
        s.pos += 1
        n = s.integer("sub goal count")
        sub = s.need("sub goal name")
        if not known:
            fail("goal '%s' is unknown and has sub goals (the loader dereferences a null goal)" % name)
        for _ in range(n):
            read_goal(s, sub, depth + 1)
    if not known:
        pass
    return known


def read_rooms(s, save):
    tok = s.need("[Rooms]")
    if tok != "[Rooms]":
        fail("expected [Rooms] but found " + tok)
    while True:
        t = s.tok()
        if t is None:
            fail("[Rooms] has no end")
        if t == "[/Rooms]":
            return
        if t != "[Room]":
            fail("expected [Room] but got " + t)
        rtype = s.integer("room type")
        if rtype < 1 or rtype > ROOM_TYPE_MAX:
            fail("unknown room type %d" % rtype)
        header = (s.line() or "").split()
        if len(header) < 3 or not is_int(header[1]) or not is_int(header[2]):
            fail("room header invalid: " + " ".join(header))
        rname, seat, ntiles = header[0], int(header[1]), int(header[2])
        if seat != 0 and seat not in save.seat_ids:
            fail("room %s: seat %d does not exist (the loader dereferences a null seat)" % (rname, seat))
        tiles = []
        for _ in range(ntiles):
            ln = s.line()
            if ln is None:
                fail("room %s: tile lines are missing" % rname)
            f = ln.split()
            if len(f) < 2 or not is_int(f[0]) or not is_int(f[1]):
                fail("room %s: tile line invalid '%s'" % (rname, ln[:40]))
            x, y = int(f[0]), int(f[1])
            if not (0 <= x < save.width and 0 <= y < save.height):
                pass  # the loader logs the missing tile and skips it
            tiles.append((x, y))
            if rtype == 6 and "TrainingRack" in f:
                f = f[:f.index("TrainingRack")]
            if len(f) > 2:
                if len(f) < 4 or not is_num(f[2]) or not is_int(f[3]) or len(f) < 4 + int(f[3]):
                    fail("room %s: tile data invalid '%s'" % (rname, ln[:60]))
        read_room_extra(s, rtype, rname, len(tiles))
        t = s.tok()
        if t != "[/Room]":
            fail("room %s (type %d): expected [/Room] but got %s" % (rname, rtype, t))


def read_ghost_uint(s, what):
    """Mirror of operator>> into a uint32_t field. The writer never writes a negative value, but the loader accepts
    one: the magnitude must fit 32 bits and the value wraps modulo 2^32 (so -1 reads as 4294967295)."""
    t = s.need(what)
    if not is_int(t):
        fail("%s is not a uint32: '%s'" % (what, t[:40]))
    v = int(t)
    if v < 0:
        if -v > 0xFFFFFFFF:
            fail("%s is below uint32: '%s'" % (what, t[:40]))
        v += 1 << 32
    if v > 0xFFFFFFFF:
        fail("%s is above uint32: '%s'" % (what, t[:40]))


def read_room_extra(s, rtype, rname, ntiles):
    """Mirror of the importFromStream of every room type (what follows the tile lines)."""
    if rtype == 1:
        s.line() if False else None
        pos = s.pos
        t = s.tok()
        if t is not None and t.startswith("H"):
            v = s.number("heart health")
            if v < 0 or not (t == "HeartHealthShare" or t == "HeartHealth10000" or t == "HeartHealth" or t == "HeartHP"):
                fail("room %s: heart marker %s invalid" % (rname, t))
        else:
            s.pos = pos
    elif rtype == 2:
        for _ in range(s.integer("bed count")):
            s.need("bed creature")
            s.integer("bed x")
            s.integer("bed y")
            s.number("bed angle")
    elif rtype == 4:
        s.number("claimed")
        s.integer("max increase")
        rest = (s.line() or "").split()
        if rest and (rest[0] != "SpawnCountdown" or len(rest) != 2 or not is_num(rest[1])):
            fail("room %s: portal tail invalid" % rname)
    elif rtype == 5:
        s.integer("points")
        s.integer("trap type")
        rest = (s.line() or "").split()
        if rest and (rest[0] != "Crack" or len(rest) != 3):
            fail("room %s: workshop tail invalid" % rname)
    elif rtype == 7:
        s.number("library points")
    elif rtype == 8:
        pos = s.pos
        if s.tok() != "HatcheryWaits":
            s.pos = pos
            return
        for _ in range(3):
            s.integer("hatchery wait")
        while True:
            pos = s.pos
            t = s.tok()
            if t is None:
                s.pos = pos
                return
            if t == "HatcheryDay":
                s.integer("day")
            elif t in ("HatcheryLays", "HatcheryNestLays"):
                for _ in range(s.integer("lays")):
                    for _ in range(4):
                        s.number("lay")
                    if t == "HatcheryNestLays":
                        s.need("hen")
            elif t == "HatcheryGrain":
                for _ in range(s.integer("grain")):
                    for _ in range(3):
                        s.integer("grain value")
            else:
                s.pos = pos
                return
    elif rtype == 9:
        s.integer("crypt points")
        while True:
            pos = s.pos
            t = s.tok()
            if t not in ("CorpseLevels", "CryptSpots"):
                s.pos = pos
                return
            for _ in range(s.integer("crypt count")):
                if t == "CorpseLevels":
                    s.integer("level")
                else:
                    s.integer("x")
                    s.integer("y")
                    s.need("name")
    elif rtype == 10:
        s.number("claimed")
        s.integer("turns between waves")
        s.integer("strategy")
        s.integer("range")
        s.need("teams")
        t = s.need("wave section")
        if t != "[Waves]":
            if not is_int(t):
                fail("room %s: portal wave expected [Waves] got %s" % (rname, t))
            t = s.need("[Waves]")
        if t != "[Waves]":
            fail("room %s: portal wave expected [Waves] got %s" % (rname, t))
        while True:
            t = s.need("wave")
            if t == "[/Waves]":
                break
            if t != "[Wave]":
                fail("room %s: portal wave expected [Wave] got %s" % (rname, t))
            for key in ("SpawnTurnMin", "SpawnTurnMax"):
                if s.need(key) != key:
                    fail("room %s: portal wave expected %s" % (rname, key))
                s.integer(key)
            if s.need("[Creatures]") != "[Creatures]":
                fail("room %s: portal wave expected [Creatures]" % rname)
            while True:
                n = s.need("wave creature")
                if n == "[/Creatures]":
                    break
                s.integer("wave creature count")
            if s.need("[/Wave]") != "[/Wave]":
                fail("room %s: portal wave expected [/Wave]" % rname)
    elif rtype in (11, 16):
        for _ in range(s.integer("prisoner count")):
            s.need("prisoner")
        pos = s.pos
        ln = s.line()
        # skipLegacyCleanOrderLine: an empty rest of the line or the legacy order line
        s.pos = pos if (ln or "").strip() and (ln or "").split()[0] not in ("CleanOrder",) else s.pos
    elif rtype in (12, 13):
        s.number("bridge claimed")
    elif rtype == 15:
        pos = s.pos
        if s.tok() == "CasinoPayout":
            if s.integer("payout") > 2:
                fail("room %s: casino payout invalid" % rname)
        else:
            s.pos = pos
    elif rtype == 20:
        # RoomMerchant::importFromStream: an optional 'Merchant <x> <y>' line before [/Room]; any other token is left
        # for the [/Room] check. A written marker needs two numbers (Ogre::Vector3 x and y, read with operator>>).
        pos = s.pos
        if s.tok() != "Merchant":
            s.pos = pos
        else:
            s.real32("merchant x")
            s.real32("merchant y")
    elif rtype == 25:
        # RoomGhostRoom::importFromStream: an optional 'GhostApparatus' marker before [/Room]; a written marker is
        # followed by APPARATUS_COUNT (3) apparatuses of queue (uint32), working (bool, 0 or 1), workTurns (finite
        # double) and crystalEctoplasm (uint32). Any other token is left for the [/Room] check.
        pos = s.pos
        if s.tok() != "GhostApparatus":
            s.pos = pos
        else:
            for _ in range(3):
                read_ghost_uint(s, "apparatus queue")
                t = s.need("apparatus working")
                if not is_int(t) or int(t) not in (0, 1):
                    fail("apparatus working is not 0 or 1: '%s'" % t[:40])
                s.number("apparatus work turns")  # a finite double: overflow and underflow refused as operator>> does
                read_ghost_uint(s, "apparatus crystal ectoplasm")
    elif rtype == 23:
        tags = ("TavernPayer", "Innkeeper", "Counter", "SeatLayout", "Furniture", "Spot", "Game")
        while True:
            pos = s.pos
            t = s.tok()
            if t not in tags:
                s.pos = pos
                return
            if t in ("Spot", "Game"):
                s.line()
            elif t in ("TavernPayer", "SeatLayout"):
                s.integer(t)
            elif t in ("Innkeeper", "Counter"):
                s.integer("x")
                s.integer("y")
            else:
                s.integer("x")
                s.integer("y")
                s.need("mesh")
                s.number("angle")


def read_traps(s, save):
    tok = s.need("[Traps]")
    if tok != "[Traps]":
        fail("expected [Traps] but found " + tok)
    while True:
        t = s.need("[Trap]")
        if t == "[/Traps]":
            return
        if t != "[Trap]":
            fail("expected [Trap] but got " + t)
        ttype = s.integer("trap type")
        if ttype < 1 or ttype > TRAP_TYPE_MAX:
            fail("unknown trap type %d" % ttype)
        header = (s.line() or "").split()
        if len(header) < 3 or not is_int(header[1]) or not is_int(header[2]):
            fail("trap header invalid: " + " ".join(header))
        seat, n = int(header[1]), int(header[2])
        if seat not in save.seat_ids and seat != 0:
            fail("trap %s: seat %d does not exist (the loader dereferences a null seat)" % (header[0], seat))
        for _ in range(n):
            ln = s.line()
            if ln is None:
                fail("trap %s: tile lines are missing" % header[0])
            f = ln.split()
            if len(f) < 3 or not all(is_num(x) for x in f):
                fail("trap %s: tile line invalid '%s'" % (header[0], ln[:50]))
            if len(f) > 3:
                if len(f) < 8 or len(f) < 8 + int(float(f[7])):
                    fail("trap %s: tile data too short '%s'" % (header[0], ln[:60]))
        if ttype in (4, 5, 6, 7, 14, 15):
            # TrapDoor::importFromStream: the lock flag, then the optional KeyLock and FireCooldown markers
            s.integer("door lock")
            extra = (s.line() or "").split()
            i = 0
            while i < len(extra):
                if extra[i] == "KeyLock" and i + 1 < len(extra) and extra[i + 1] == "1":
                    i += 2
                elif extra[i] == "FireCooldown" and ttype == 15 and i + 1 < len(extra) and is_num(extra[i + 1]):
                    i += 2
                else:
                    fail("trap %s: door tail invalid '%s'" % (header[0], " ".join(extra)))
        if s.need("[/Trap]") != "[/Trap]":
            fail("trap %s: expected [/Trap]" % header[0])


def count_fields(line):
    return len(line.split())


def read_entity_section(s, save, name, min_fields, positions=True, first_is_type=False, numeric_to=None):
    """Mirror of readGameEntity: every line must hold the fields of the entity reader."""
    if s.need("[" + name + "]") != "[" + name + "]":
        fail("expected [%s]" % name)
    while True:
        t = s.tok()
        if t is None:
            fail("[%s] has no end" % name)
        if t == "[/" + name + "]":
            return
        line = t + (s.line() or "")
        f = line.split()
        if len(f) < min_fields:
            fail("%s: line has %d fields but the reader needs %d: '%s'" % (name, len(f), min_fields, line[:70]))
        base = 1 if first_is_type else 0
        seat = f[base]
        if not is_int(seat):
            fail("%s: seat id is not a number: '%s'" % (name, line[:60]))
        if numeric_to:
            for idx in numeric_to:
                if idx < len(f) and not is_num(f[idx]):
                    fail("%s: field %d is not a number: '%s'" % (name, idx + 1, line[:70]))
        if int(seat) != -1 and int(seat) not in save.seat_ids and int(seat) != 0:
            fail("%s: seat %s does not exist" % (name, seat))


def read_creatures(s, save):
    n = 0
    while True:
        t = s.tok()
        if t is None:
            fail("[Creatures] has no end")
        if t == "[/Creatures]":
            return
        line = t + (s.line() or "")
        f = line.split()
        n += 1
        if len(f) < 18 or not is_int(f[0]):
            fail("creature %d: only %d fields (reader needs 18): '%s'" % (n, len(f), line[:70]))
        if int(f[0]) not in save.seat_ids and int(f[0]) not in (0, -1):
            fail("creature %d (%s): seat %s does not exist" % (n, f[1], f[0]))
        for idx in (3, 4, 5, 7, 8, 10, 11, 12, 17):
            if not is_num(f[idx]):
                fail("creature %d (%s): field %d is not a number: '%s'" % (n, f[1], idx + 1, f[idx]))
        if f[9] != "max" and not is_num(f[9]):
            fail("creature %d (%s): hit points '%s' invalid" % (n, f[1], f[9]))
        if f[6] not in CLASSES:
            fail("creature %d (%s): class %s is not in config/creatures.cfg (the loader has no definition)"
                 % (n, f[1], f[6]))
        x, y = float(f[3]), float(f[4])
        if not (-1 <= x <= save.width and -1 <= y <= save.height):
            fail("creature %d (%s): position outside the map" % (n, f[1]))
        # tokens that belong to the effects: nbEffects groups, the loader reads on in any case


def read_triggers(s):
    """Mirror of LevelScript::importFromStream."""
    in_trigger = False
    cond_n = act_n = 0
    sizes = {"MinedGold": 5, "DeathTile": 4, "SpawnObservation": 6, "FatalShot": 3, "CrossingProgress": 8,
             "VictoryRequest": 2, "ObjectiveState": 4, "Flag": 3, "Timer": 4, "PortalOff": 2, "Block": 3, "Event": 4,
             "Member": 3, "TimeLimit": 2, "Countdown": 2, "WaveCountdown": 2, "SlapLimit": 2, "Slaps": 3, "Order": 6,
             "Region": 6}
    cond_ok = check_condition
    while True:
        raw = s.line()
        if raw is None:
            fail("[Triggers] has no [/Triggers]")
        line = raw.strip()
        if not line:
            continue
        if line == "[/Triggers]":
            if in_trigger:
                fail("[Triggers] ends inside a trigger")
            return
        if line == "[Trigger]":
            if in_trigger:
                fail("nested [Trigger]")
            in_trigger, cond_n, act_n = True, 0, 0
            continue
        if line == "[/Trigger]":
            if not in_trigger or cond_n == 0 or act_n == 0:
                fail("trigger without conditions or without actions")
            in_trigger = False
            continue
        t = line.split()
        key = t[0]
        if key in sizes:
            if in_trigger or len(t) != sizes[key]:
                fail("trigger data line '%s' has %d fields instead of %d" % (key, len(t), sizes[key]))
        elif key == "Stone":
            if in_trigger or len(t) not in (2, 4):
                fail("Stone line invalid")
        elif key == "FreePossession":
            if in_trigger or len(t) != 1:
                fail("FreePossession line invalid")
        elif not in_trigger:
            fail("unknown level script line '%s'" % key)
        elif key == "Name":
            if len(t) != 2:
                fail("trigger name invalid: " + line[:50])
        elif key == "Mode":
            if not ((len(t) == 2 and t[1] == "once") or (len(t) == 3 and t[1] == "repeat" and is_int(t[2]))):
                fail("trigger mode invalid: " + line[:50])
        elif key == "Cond":
            if not cond_ok(t):
                fail("trigger condition invalid: " + line[:80])
            cond_n += 1
        elif key == "Action":
            if not check_action(t):
                fail("trigger action invalid: " + line[:80])
            act_n += 1
        elif key == "State":
            if len(t) != 3 or not is_int(t[1]) or not is_int(t[2]):
                fail("trigger state invalid: " + line[:50])
        else:
            fail("unknown trigger line '%s'" % key)


OPS = ("<", "<=", ">", ">=", "==", "=", "!=", "at_least", "atleast")


def check_condition(t):
    """Field counts of LevelScript parseCondition (the operator spelling is checked loosely)."""
    if len(t) < 2:
        return False
    kind, n = t[1], len(t)
    exact = {"time": (3,), "creatures": (5, 6), "gold": (5,), "mana": (5,), "kills": (5,), "mined": (5,),
             "happy": (5,), "angry": (5,), "lost": (5,), "pickedup": (5,), "dropped": (5,), "slapped": (5,),
             "atlevel": (6,), "claimed": (5,), "room": (5, 6), "groundconnected": (7,), "roomclaimed": (7,),
             "groundclaimed": (7,), "minedregion": (6,), "killedin": (4,), "trapgone": (3,), "spawncleared": (4, 6),
             "trigger": (3, 4), "objective": (5,), "creaturesatheart": (5,), "goal": (4,), "goalmet": (4, 5),
             "flag": (4, 5), "boulder": (5,), "shotkilled": (4,), "attackedregion": (5,), "crossed": (5, 7),
             "deliveredstone": (3,), "carryingstone": (3,), "possessed": (4, 5), "slabs": (7,), "tagged": (5, 6),
             "event": (4, 6), "slaps": (5,), "furniture": (6,), "breached": (3,), "portal": (4,), "alive": (3, 4),
             "reached": (5,), "stone": (5,), "defeated": (3,), "held": (4,), "owns": (4,), "spell": (4,),
             "health": (5,), "built": (6,), "roomtiles": (6,), "roomsize": (6,), "timer": (5,), "region": (4, 6, 7)}
    if kind not in exact or n not in exact[kind]:
        return False
    if kind in ("groundconnected", "roomclaimed", "groundclaimed"):
        return all(is_int(x) and int(x) >= 0 for x in t[2:7])
    if kind == "region" and n == 7:
        return all(is_int(x) for x in t[2:7]) or not is_int(t[3])
    return True


def check_action(t):
    """Field counts of LevelScript parseAction."""
    if len(t) < 2:
        return False
    kind, n = t[1], len(t)
    if kind in ("objectiveid", "mainobjectiveid", "optionalobjectiveid", "conditionalobjectiveid"):
        return n >= 5 and is_int(t[2])
    if kind == "objectivestate":
        return n == 5 and is_int(t[2]) and t[4] in ("reached", "failed")
    if kind == "hint":
        return n >= 4 and is_int(t[2])
    if kind in ("message", "objective"):
        return n >= 4 and is_int(t[2])
    if kind == "spawn":
        return n >= 7 and all(is_int(x) for x in t[2:6]) and all(":" in x or x.startswith("party=") for x in t[6:])
    fixed = {"gold": 4, "setflag": 4, "addflag": 4, "win": 3, "lose": 3, "reveal": 4, "make": 4, "timelimit": 3,
             "countdown": 3, "wavecountdown": 3, "keydoor": 4, "portal": 4, "available": 5, "golfball": 5,
             "stoneattach": 3, "keepminion": 3, "possess": 3, "remove": 3, "alliance": 5, "generate": 4,
             "roomowner": 5, "slaplimit": 3, "discover": 3}
    if kind in fixed:
        return n == fixed[kind]
    if kind == "terrain":
        return n in (7, 8)
    if kind == "stonecreate":
        return n in (4, 8)
    if kind == "stonedrop":
        return n in (4, 7)
    if kind == "order":
        return n >= 6
    if kind == "speed":
        return n >= 4
    if kind == "timer":
        return n in (3, 4)
    return False


def read_save(path):
    save = Save(path)
    s = Stream(save.text)
    # getXandYandSeatsNumber: the map size of the last [Tiles] and the number of [Seat] tokens
    toks = save.text.split()
    seats_in_file = toks.count("[Seat]")
    sizes = [i for i, x in enumerate(toks) if x == "[Tiles]"]
    if not sizes or len(toks) < sizes[-1] + 3 or not is_int(toks[sizes[-1] + 1]) or not is_int(toks[sizes[-1] + 2]) \
            or int(toks[sizes[-1] + 1]) <= 0 or int(toks[sizes[-1] + 2]) <= 0:
        fail("the map size after [Tiles] is missing or not positive (the loader asserts and allocates a negative array)")
    save.width, save.height = int(toks[sizes[-1] + 1]), int(toks[sizes[-1] + 2])
    header = s.need("version header")
    if not save.supported_header(header):
        fail("Unsupported file version '%s' (this game is %s)" % (header, GAME_HEADER))
    if s.need("[Info]") != "[Info]":
        fail("expected [Info]")
    s.line()
    while True:
        ln = s.line()
        if ln is None:
            fail("[Info] has no end")
        if ln == "[/Info]":
            break
    if s.need("[Seats]") != "[Seats]":
        fail("expected [Seats]")
    while True:
        t = s.need("[Seat]")
        if t == "[/Seats]":
            break
        if t != "[Seat]":
            fail("expected a Seat tag but got " + t)
        read_seat(s, save)
    if max(save.seat_ids or {0}) > seats_in_file:
        fail("seat id %d is larger than the number of seats %d (the ever-visited array is too small)"
             % (max(save.seat_ids), seats_in_file))
    if s.need("[Goals]") != "[Goals]":
        fail("expected [Goals]")
    while True:
        t = s.need("goal")
        if t == "[/Goals]":
            break
        read_goal(s, t)
    if s.need("[Tiles]") != "[Tiles]":
        fail("expected [Tiles]")
    if (s.integer("map width"), s.integer("map height")) != (save.width, save.height):
        fail("the map size of the first [Tiles] differs from the one the loader scanned in the whole file")
    seen = set()
    while True:
        t = s.need("tile")
        if t == "[/Tiles]":
            break
        line = t + (s.line() or "")
        f = line.split("\t")
        if len(f) < 3 or not is_int(f[0]) or not is_int(f[1]) or not is_int(f[2].strip()):
            fail("tile line invalid (needs x y type fullness separated by tabs): '%s'" % line[:60])
        ttype = int(f[2])
        if ttype not in (4, 5, 7) and (len(f) < 4 or not is_num(f[3].strip())):
            fail("tile line without fullness: '%s'" % line[:60])
        x, y = int(f[0]), int(f[1])
        if not (0 <= x < save.width and 0 <= y < save.height):
            fail("tile (%d,%d) is outside the %dx%d map" % (x, y, save.width, save.height))
        if ttype < 0 or ttype > 7:
            fail("tile (%d,%d) has the unknown type %d" % (x, y, ttype))
        seen.add((x, y))
    read_rooms(s, save)
    read_traps(s, save)
    if s.need("[Lights]") != "[Lights]":
        fail("expected [Lights]")
    while True:
        t = s.need("light")
        if t == "[/Lights]":
            break
        f = (t + (s.line() or "")).split()
        if len(f) < 13 or not all(is_num(x) for x in f[:13]):
            fail("light line invalid: " + " ".join(f)[:60])
    t = s.need("section")
    if t == "[CreatureDefinitions]":
        while True:
            t = s.need("creature definition")
            if t == "[/CreatureDefinitions]":
                break
            if t == "[/Creature]":
                continue
            if t != "[Creature]":
                fail("invalid creature definition start: " + t)
            t = s.need("creature definition name")
            if t == "Name":
                name = s.need("class name")
                while True:
                    x = s.tok()
                    if x is None:
                        fail("creature definition of %s has no end" % name)
                    if x in ("[/Creature]", "[/CreatureDefinitions]"):
                        break
                if x == "[/CreatureDefinitions]":
                    fail("creature definition of %s ends the section early" % name)
        t = s.need("section")
    if t == "[EquipmentDefinitions]":
        while True:
            t = s.need("equipment definition")
            if t == "[/EquipmentDefinitions]":
                break
            if t == "[/Equipment]":
                continue
            if t != "[Equipment]":
                fail("invalid equipment definition start: " + t)
            t = s.need("equipment name")
            if t == "Name":
                s.need("equipment name")
                while True:
                    x = s.tok()
                    if x is None:
                        fail("equipment definition has no end")
                    if x in ("[/Equipment]", "[/EquipmentDefinitions]"):
                        break
                if x == "[/EquipmentDefinitions]":
                    fail("equipment definition ends the section early")
        t = s.need("section")
    if t != "[Creatures]":
        fail("invalid Creatures start: " + t)
    read_creatures(s, save)
    pos = s.pos
    # entity sections: seat, name, mesh, x, y, z (+ opacity, rotation for rendered entities) and the entity fields
    read_entity_section(s, save, "Spells", 9, first_is_type=True)
    # CraftedTrap::importFromStream also takes the older form without a tab after the trap type (11 fields)
    read_entity_section(s, save, "CraftedTraps", 11, numeric_to=[0, 3, 4, 5, 6, 7, 8, 9, 10])
    read_entity_section(s, save, "SkillEntity", 12, numeric_to=[0, 3, 4, 5, 6, 7, 8, 9, 10, 11])
    read_entity_section(s, save, "GiftBoxEntity", 8)
    for tag, minimum in (("ItemBags", 9), ("Ghosts", 9), ("GhostBoxes", 9)):
        pos = s.pos
        if s.tok() == "[" + tag + "]":
            s.pos = pos
            read_entity_section(s, save, tag, minimum)
        else:
            s.pos = pos
    # Dirt and DirtPiles
    pos = s.pos
    if s.tok() == "[Dirt]":
        while True:
            t = s.need("dirt line")
            if t == "[/Dirt]":
                break
            s.integer("dirt y")
            s.number("dirt")
        pos = s.pos
        t = s.tok()
        if t == "[DirtPiles]":
            while s.need("pile") != "[/DirtPiles]":
                s.line()
        else:
            s.pos = pos
    else:
        s.pos = pos
        pos = s.pos
        t = s.tok()
        if t == "[DirtPiles]":
            while s.need("pile") != "[/DirtPiles]":
                s.line()
        else:
            s.pos = pos
    if s.need("[Missiles]") != "[Missiles]":
        fail("expected [Missiles]")
    while True:
        t = s.need("missile")
        if t == "[/Missiles]":
            break
        line = t + (s.line() or "")
        f = line.split()
        # type seat name mesh x y z opacity rotation dx dy dz alive damageAllies ko speed phys magic element nbEffects
        # GameEntity::importFromStream keeps an empty mesh name (two tabs in a row) as a field
        parts = line.split("\t")
        if len(parts) > 3 and parts[3] == "":
            f.insert(3, "")
        if len(f) < 20:
            fail("missile line has %d fields but the reader needs 20" % len(f))
    read_entity_section(s, save, "TreasuryObject", 9, numeric_to=[0, 3, 4, 5, 6, 7, 8])
    read_entity_section(s, save, "Chickens", 11, numeric_to=[0, 3, 4, 5, 6, 7, 8, 9, 10])
    t = s.tok()
    if t == "[HerbBundles]":
        while s.need("herb bundle") != "[/HerbBundles]":
            s.line()
        t = s.tok()
    if t == "[Scripts]":
        while s.need("script") != "[/Scripts]":
            s.line()
        t = s.tok()
    if t == "[Triggers]":
        read_triggers(s)
        t = s.tok()
    if t == "[Relationships]":
        while True:
            ln = s.line()
            if ln is None:
                fail("[Relationships] has no end")
            ln = ln.strip()
            if ln == "[/Relationships]":
                break
            if not ln:
                continue
            f = ln.split("\t")
            if len(f) not in (4, 5) or not f[0] or not f[1] or f[0] == f[1] or not is_int(f[2]) or not is_int(f[3]) \
                    or (len(f) == 5 and not is_int(f[4])):
                fail("relationship line invalid: " + ln[:60])
        t = s.tok()
    if t == "[RelationshipState]":
        read_relationship_states(s)
    return seen


bad = 0
for f in files:
    try:
        read_save(f)
        if args.verbose:
            print("ok     " + f.name)
    except LoadFailure as e:
        bad += 1
        print("FAILED %s: %s" % (f.name, e))
    except Exception as e:  # a bug of this script must not hide the other saves
        bad += 1
        print("ERROR  %s: %s: %s" % (f.name, type(e).__name__, e))
print("%d of %d saves would be refused" % (bad, len(files)))
if bad:
    sys.exit(1)
print("OK")
