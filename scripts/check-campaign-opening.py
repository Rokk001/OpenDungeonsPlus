#!/usr/bin/env python3
"""Opening check for campaign levels: the first minute must not be decided by the layout.

For every level the state at the START of the game is checked (no trigger has fired yet):

1. Enemy walk path. The sources of the enemy team are the creatures of other teams, their
   wave portals, their portals and their dungeon temples. For every source the walk path
   to the dungeon temple of the human seat is measured (4-neighbourhood, like the game):
   only over tiles that can be walked right now (open dirt, claimed or built tiles, rooms,
   bridges, doors; doors count as walkable). Every such connection is a FAIL, whatever its
   length: a source must always have to dig to reach the temple. Solid rock, water and lava
   never count as passable. A tile that is rock at the start and opened later by a trigger
   therefore separates, as it should. The shortest path that may also cross solid dirt,
   gold and gem tiles is only reported (shortest_dig_path) and has no threshold. Levels
   outside the campaign (skirmish, realms) are exempt from this part.

2. Open areas between the rooms of the human seat. Within OPEN_RADIUS tiles of the temple
   and within the bounding box of all rooms of the human seat, a square of at least
   OPEN_SQUARE x OPEN_SQUARE walkable (not dug) tiles that belong to no room, i.e. an open
   area larger than 4x4, is a large empty hall: FAIL (the largest one is reported with
   its corner). Furthermore, rooms
   placed for the human seat must be separated from each other by rock: two such rooms
   that touch each other, or a block of WIDE_PASSAGE x WIDE_PASSAGE open non-room tiles
   next to one of them (passage wider than MAX_PASSAGE_WIDTH), is a FAIL.

Output is one line per level (PASS or FAIL, file, numbers). Levels listed in
scripts/check-campaign-opening.allowlist report FAIL but do not change the exit code
("known, to be fixed"); the exit code is 0 only if every level passes or is allowlisted.
This script contains no level data.

Usage:
  check-campaign-opening.py [--no-allowlist] [<file> ...]
  check-campaign-opening.py --self-test

Without files all levels of levels/campaign/Campaign.cfg are checked.
"""

import os
import shutil
import sys
import tempfile
from collections import deque

# --- Constants ---------------------------------------------------------------------------
OPEN_RADIUS = 12
OPEN_SQUARE = 5
MAX_PASSAGE_WIDTH = 3
WIDE_PASSAGE = MAX_PASSAGE_WIDTH + 1
# A room of the human seat counts as "next to" a wide passage within this many tiles.
PASSAGE_ROOM_DISTANCE = 2

TILE_DIRT = 1
TILE_GOLD = 2
TILE_ROCK = 3
TILE_WATER = 4
TILE_LAVA = 5
TILE_GEM = 6
DIGGABLE_TYPES = (TILE_DIRT, TILE_GOLD, TILE_GEM)

ROOM_TEMPLE = 1
ROOM_PORTAL = 4
ROOM_PORTAL_WAVE = 10

NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Level(object):
    def __init__(self, path):
        self.path = path
        self.width = 0
        self.height = 0
        self.types = {}
        self.fullness = {}
        self.seats = {}          # seatId -> dict of fields
        self.rooms = []          # (roomType, seatId, [(x, y)])
        self.doors = []          # (x, y)
        self.creatures = []      # (seatId, x, y)


def to_int(text):
    try:
        return int(float(text))
    except ValueError:
        return None


def parse_level(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        lines = [l.rstrip("\r") for l in handle.read().split("\n")]
    level = Level(path)
    section = ""
    seat = None
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        stripped = line.strip()
        if stripped == "":
            continue
        if stripped.startswith("["):
            if stripped == "[Seat]":
                seat = {}
                section = "Seat"
            elif stripped == "[/Seat]":
                if seat is not None and "seatId" in seat:
                    level.seats[seat["seatId"]] = seat
                seat = None
                section = "Seats"
            elif stripped in ("[/Tiles]", "[/Rooms]", "[/Traps]", "[/Creatures]"):
                section = ""
            elif stripped in ("[Tiles]", "[Rooms]", "[Traps]", "[Creatures]"):
                section = stripped[1:-1]
            continue
        if stripped.startswith("#") and section != "Tiles":
            continue
        if section == "Seat":
            fields = line.split("\t")
            if len(fields) == 2:
                if fields[0] == "seatId" or fields[0] == "teamId":
                    value = to_int(fields[1])
                    if value is not None:
                        seat[fields[0]] = value
                elif fields[0] in ("player", "faction"):
                    seat[fields[0]] = fields[1].strip()
                elif fields[0] in ("startingX", "startingY"):
                    value = to_int(fields[1])
                    if value is not None:
                        seat[fields[0]] = value
        elif section == "Tiles":
            body = line.split("#", 1)[0].strip()
            if body == "":
                continue
            fields = body.split()
            if len(fields) == 1 and level.width == 0:
                level.width = int(fields[0])
            elif len(fields) == 1 and level.height == 0:
                level.height = int(fields[0])
            elif len(fields) >= 4:
                x = int(fields[0])
                y = int(fields[1])
                level.types[(x, y)] = int(fields[2])
                level.fullness[(x, y)] = float(fields[3])
        elif section in ("Rooms", "Traps"):
            fields = line.split("\t")
            if len(fields) == 4 and to_int(fields[0]) is not None:
                count = to_int(fields[3])
                tiles = []
                for _ in range(count):
                    if index >= len(lines):
                        break
                    tile = lines[index].split("\t")
                    index += 1
                    if len(tile) >= 2:
                        tiles.append((int(tile[0]), int(tile[1])))
                if section == "Rooms":
                    level.rooms.append((to_int(fields[0]), to_int(fields[2]), tiles))
                elif "Door" in fields[1]:
                    level.doors.extend(tiles)
        elif section == "Creatures":
            fields = line.split("\t")
            if len(fields) >= 6 and to_int(fields[0]) is not None:
                x = to_int(fields[3])
                y = to_int(fields[4])
                if x is not None and y is not None:
                    level.creatures.append((to_int(fields[0]), x, y))
    if level.width <= 0 or level.height <= 0:
        return None
    return level


def human_seat(level):
    for seat_id in sorted(level.seats):
        if level.seats[seat_id].get("player") == "Human":
            return seat_id
    return None


def build_grids(level):
    """Returns (walkable, digpassable, room_tiles) as sets of (x, y)."""
    walkable = set()
    passable = set()
    for pos, tile_type in level.types.items():
        if tile_type in DIGGABLE_TYPES:
            passable.add(pos)
            if level.fullness.get(pos, 100.0) <= 0:
                walkable.add(pos)
    room_tiles = set()
    for room_type, _, tiles in level.rooms:
        for pos in tiles:
            walkable.add(pos)
            passable.add(pos)
            room_tiles.add(pos)
    for pos in level.doors:
        walkable.add(pos)
        passable.add(pos)
    return walkable, passable, room_tiles


def bfs(sources, allowed, width, height):
    dist = {}
    queue = deque()
    for pos in sources:
        if pos in allowed and pos not in dist:
            dist[pos] = 0
            queue.append(pos)
    while queue:
        x, y = queue.popleft()
        d = dist[(x, y)]
        for dx, dy in NEIGHBOURS:
            nxt = (x + dx, y + dy)
            if 0 <= nxt[0] < width and 0 <= nxt[1] < height and nxt in allowed \
                    and nxt not in dist:
                dist[nxt] = d + 1
                queue.append(nxt)
    return dist


def nearest(dist, tiles):
    best = None
    for pos in tiles:
        if pos in dist and (best is None or dist[pos] < best):
            best = dist[pos]
    return best


def heart_tiles(level, seat_id):
    tiles = []
    for room_type, owner, room in level.rooms:
        if room_type == ROOM_TEMPLE and owner == seat_id:
            tiles.extend(room)
    if not tiles:
        seat = level.seats[seat_id]
        if "startingX" in seat and "startingY" in seat:
            tiles.append((seat["startingX"], seat["startingY"]))
    return tiles


def enemy_sources(level, seat_id):
    team = level.seats[seat_id].get("teamId")
    sources = []
    for other_id, seat in level.seats.items():
        if other_id == seat_id or seat.get("teamId") == team:
            continue
        for room_type, owner, tiles in level.rooms:
            if owner == other_id and room_type in (ROOM_TEMPLE, ROOM_PORTAL) and tiles:
                sources.append(("seat %d room type %d" % (other_id, room_type), tiles[0]))
    for room_type, owner, tiles in level.rooms:
        if room_type == ROOM_PORTAL_WAVE and tiles:
            owner_team = level.seats.get(owner, {}).get("teamId")
            if owner_team != team:
                sources.append(("wave portal of seat %d" % owner, tiles[0]))
    for owner, x, y in level.creatures:
        owner_team = level.seats.get(owner, {}).get("teamId")
        if owner in level.seats and owner_team != team:
            sources.append(("creature of seat %d at %d,%d" % (owner, x, y), (x, y)))
    return sources


def check_enemy_distance(level, seat_id):
    walkable, passable, _ = build_grids(level)
    hearts = heart_tiles(level, seat_id)
    walk = bfs(hearts, walkable, level.width, level.height)
    dig = bfs(hearts, passable, level.width, level.height)
    reasons = []
    shortest = None
    connected = []
    for name, pos in enemy_sources(level, seat_id):
        if pos in walk:
            connected.append((walk[pos], name))
        d = dig.get(pos)
        if d is not None:
            if shortest is None or d < shortest:
                shortest = d
    if connected:
        connected.sort()
        reasons.append("%d enemy source(s) walk to the heart without digging, nearest: %s "
                       "in %d tiles" % (len(connected), connected[0][1], connected[0][0]))
    return reasons, shortest


def largest_open_square(open_tiles, x0, y0, x1, y1):
    """Largest all-open square inside the box; returns (size, x, y) of its corner."""
    best = (0, 0, 0)
    side = {}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (x, y) not in open_tiles:
                side[(x, y)] = 0
                continue
            value = 1 + min(side.get((x - 1, y), 0), side.get((x, y - 1), 0),
                            side.get((x - 1, y - 1), 0))
            side[(x, y)] = value
            if value > best[0]:
                best = (value, x - value + 1, y - value + 1)
    return best


def check_open_areas(level, seat_id):
    walkable, _, room_tiles = build_grids(level)
    hearts = heart_tiles(level, seat_id)
    cx = sum(p[0] for p in hearts) // len(hearts)
    cy = sum(p[1] for p in hearts) // len(hearts)
    x0 = max(0, cx - OPEN_RADIUS)
    x1 = min(level.width - 1, cx + OPEN_RADIUS)
    y0 = max(0, cy - OPEN_RADIUS)
    y1 = min(level.height - 1, cy + OPEN_RADIUS)
    own_tiles = [pos for room_type, owner, tiles in level.rooms
                 if owner == seat_id for pos in tiles]
    if own_tiles:
        x0 = min(x0, min(p[0] for p in own_tiles) - 1)
        x1 = max(x1, max(p[0] for p in own_tiles) + 1)
        y0 = min(y0, min(p[1] for p in own_tiles) - 1)
        y1 = max(y1, max(p[1] for p in own_tiles) + 1)
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(level.width - 1, x1)
        y1 = min(level.height - 1, y1)
    open_tiles = set(p for p in walkable if p not in room_tiles
                     and x0 <= p[0] <= x1 and y0 <= p[1] <= y1)
    size, sx, sy = largest_open_square(open_tiles, x0, y0, x1, y1)
    reasons = []
    if size >= OPEN_SQUARE:
        reasons.append("open area %dx%d at %d,%d" % (size, size, sx, sy))
    own_rooms = [tiles for room_type, owner, tiles in level.rooms
                 if owner == seat_id]
    # rooms that touch each other
    owner_of = {}
    for number, tiles in enumerate(own_rooms):
        for pos in tiles:
            owner_of[pos] = number
    touching = set()
    for pos, number in owner_of.items():
        for dx, dy in NEIGHBOURS:
            other = owner_of.get((pos[0] + dx, pos[1] + dy))
            if other is not None and other != number:
                touching.add((min(number, other), max(number, other)))
    if touching:
        reasons.append("%d room pair(s) touch without rock" % len(touching))
    # wide passage next to an own room
    wide = 0
    wide_at = None
    for (x, y) in open_tiles:
        block = [(x + i, y + j) for i in range(WIDE_PASSAGE) for j in range(WIDE_PASSAGE)]
        if not all(p in open_tiles for p in block):
            continue
        near = False
        for bx, by in block:
            for ox in range(-PASSAGE_ROOM_DISTANCE, PASSAGE_ROOM_DISTANCE + 1):
                for oy in range(-PASSAGE_ROOM_DISTANCE, PASSAGE_ROOM_DISTANCE + 1):
                    if (bx + ox, by + oy) in owner_of:
                        near = True
        if near:
            wide += 1
            if wide_at is None or (y, x) < (wide_at[1], wide_at[0]):
                wide_at = (x, y)
    if wide:
        reasons.append("wide passage (>%d) next to a room, first at %d,%d"
                       % (MAX_PASSAGE_WIDTH, wide_at[0], wide_at[1]))
    return reasons, size, (sx, sy)


def check_level(path, campaign_index):
    level = parse_level(path)
    if level is None:
        return "SKIP", ["no tiles"], ""
    seat_id = human_seat(level)
    if seat_id is None or not heart_tiles(level, seat_id):
        return "SKIP", ["no human seat"], ""
    reasons = []
    shortest = None
    if campaign_index is not None:
        found, shortest = check_enemy_distance(level, seat_id)
        reasons.extend(found)
    found, size, corner = check_open_areas(level, seat_id)
    reasons.extend(found)
    numbers = "shortest_dig_path=%s largest_open=%dx%d@%d,%d" % (
        "none" if shortest is None else shortest, size, size, corner[0], corner[1])
    return ("FAIL" if reasons else "PASS"), reasons, numbers


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def campaign_files(root):
    cfg = os.path.join(root, "levels", "Campaign.cfg")
    if not os.path.isfile(cfg):
        cfg = os.path.join(root, "levels", "campaign", "Campaign.cfg")
    result = []
    with open(cfg, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line.startswith("File="):
                result.append(os.path.join(root, "levels", line[5:].replace("/", os.sep)))
    return result


def read_allowlist(root):
    names = set()
    path = os.path.join(root, "scripts", "check-campaign-opening.allowlist")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.split("#", 1)[0].strip()
                if line:
                    names.add(line)
    return names


def run(files, root, use_allowlist, order):
    allow = read_allowlist(root) if use_allowlist else set()
    failed = 0
    for path in files:
        name = os.path.basename(path)
        norm = os.path.normcase(os.path.abspath(path))
        index = order.get(norm)
        if index is None and os.path.basename(os.path.dirname(norm)) == "campaign":
            index = len(order)
        status, reasons, numbers = check_level(path, index)
        text = "; ".join(reasons)
        if status == "FAIL" and name in allow:
            print("FAIL (known, to be fixed) %s %s | %s" % (name, numbers, text))
        elif status == "FAIL":
            failed += 1
            print("FAIL %s %s | %s" % (name, numbers, text))
        elif status == "SKIP":
            print("SKIP %s %s" % (name, text))
        else:
            note = " (allowlist entry obsolete)" if name in allow else ""
            print("PASS %s %s%s" % (name, numbers, note))
    return 1 if failed else 0


# --- Self test ---------------------------------------------------------------------------
def synthetic_level(path, heart_x, enemy_x, rooms_gap, open_hall):
    """40x20 map, rock border, human temple around (heart_x, 10), enemy at enemy_x."""
    width, height = 80, 20
    lines = ["OpenDungeons_Version:0.7.1", "", "[Seats]"]
    for seat_id, team, player, x in ((1, 1, "Human", heart_x), (2, 2, "Inactive", enemy_x)):
        lines += ["[Seat]", "seatId\t%d" % seat_id, "teamId\t%d" % team, "player\t%s" % player,
                  "startingX\t%d" % x, "startingY\t10", "[/Seat]"]
    lines += ["[/Seats]", "", "[Tiles]", "%d # MapSizeX" % width, "%d # MapSizeY" % height]
    open_tiles = set()
    for x in range(heart_x - 2, heart_x + 3):
        for y in range(8, 13):
            open_tiles.add((x, y))
    for x in range(enemy_x - 1, enemy_x + 2):
        for y in range(9, 12):
            open_tiles.add((x, y))
    if enemy_x - heart_x < 20:
        for x in range(heart_x, enemy_x):
            open_tiles.add((x, 10))
    room2 = [(heart_x - 3 - rooms_gap - i, y) for i in range(3) for y in range(8, 11)]
    if open_hall:
        for x in range(heart_x - 12, heart_x - 6):
            for y in range(4, 16):
                open_tiles.add((x, y))
    open_tiles.update(room2)
    for y in range(height):
        for x in range(width):
            if (x, y) in open_tiles:
                lines.append("%d\t%d\t1\t0" % (x, y))
            elif x in (0, width - 1) or y in (0, height - 1):
                lines.append("%d\t%d\t3\t100" % (x, y))
            else:
                lines.append("%d\t%d\t1\t100" % (x, y))
    lines += ["[/Tiles]", "", "[Rooms]", "[Room]", "1\tDungeonTemple1\t1\t25"]
    for x in range(heart_x - 2, heart_x + 3):
        for y in range(8, 13):
            lines.append("%d\t%d" % (x, y))
    lines += ["[/Room]", "[Room]", "2\tDormitory1\t1\t9"]
    for pos in room2:
        lines.append("%d\t%d" % pos)
    lines += ["[/Room]", "[/Rooms]", "", "[Traps]", "[/Traps]", "", "[Creatures]",
              "2\tHero1\tKnight.mesh\t%d\t10\t0\tKnight\t1\t0\tmax\t100\t0\t0" % enemy_x,
              "[/Creatures]", ""]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def self_test():
    directory = tempfile.mkdtemp()
    try:
        good = os.path.join(directory, "good.level")
        near = os.path.join(directory, "near.level")
        open_area = os.path.join(directory, "open.level")
        touching = os.path.join(directory, "touch.level")
        synthetic_level(good, 60, 4, 1, False)
        synthetic_level(near, 14, 30, 1, False)
        synthetic_level(open_area, 60, 4, 1, True)
        synthetic_level(touching, 60, 4, 0, False)
        expectations = [(good, 5, "PASS"), (near, 5, "FAIL"), (open_area, 5, "FAIL"),
                        (touching, 5, "FAIL")]
        ok = True
        for path, index, expected in expectations:
            status, reasons, numbers = check_level(path, index)
            print("%s (expected %s) %s | %s" % (status, expected, os.path.basename(path),
                                                  "; ".join(reasons)))
            if status != expected:
                ok = False
        # the connected variant must report the walk and the distance reason
        status, reasons, _ = check_level(near, 5)
        if not any("walk to the heart" in r for r in reasons):
            ok = False
        status, reasons, _ = check_level(open_area, 5)
        if not any("open area" in r for r in reasons):
            ok = False
        status, reasons, _ = check_level(touching, 5)
        if not any("touch" in r for r in reasons):
            ok = False
        print("self-test %s" % ("passed" if ok else "FAILED"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def main(argv):
    if "--self-test" in argv:
        return self_test()
    use_allowlist = "--no-allowlist" not in argv
    files = [a for a in argv if not a.startswith("--")]
    root = repo_root()
    order = {}
    for number, path in enumerate(campaign_files(root)):
        order[os.path.normcase(os.path.abspath(path))] = number
    if not files:
        files = campaign_files(root)
    return run(files, root, use_allowlist, order)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
