#!/usr/bin/env python3
"""Gold density rebalance of the levels: every keeper seat gets GOLD_TARGET_PER_KEEPER_SEAT gold in reach.

Rules (deterministic):
  1. Keeper seats are the [Seat] blocks with faction Keeper or Choice; the start is startingX/startingY.
  2. The distance of a tile is the 4-neighbour BFS step count from the nearest keeper start through every tile except
     rock, water and lava; tiles not listed in [Tiles] are full dirt.
  3. Gold tiles (type 2, fullness > 0, finite distance) are sorted by (distance, x, y); the first third gets density 50,
     the next third 100, the rest 150.
  4. Target = GOLD_TARGET_PER_KEEPER_SEAT x keeper seats; level gold = sum of GOLD_PER_SEAM_TILE x density / 100.
  5. Below the target, walk the gold tiles from the farthest to the nearest and raise 50 -> 100 until the target is
     reached, then again raise 100 -> 150.
  6. Still below: full dirt tiles next to a gold tile (or an added tile) become gold with fullness 100 and density 150,
     farthest first (ties: larger x, then larger y), until the target is reached.
  7. Levels: levels/*/*.level except the excluded names and levels without a keeper seat.
  8. Writing: a changed gold line becomes x, y, 2, fullness, seat or -1, density (tab separated); an added tile is
     appended at the end of the [Tiles] block; nothing else changes.

Usage:
  rebalance_gold_density.py [--root DIR]               rewrite the level files in DIR (run once)
  rebalance_gold_density.py --check [BASE_COMMIT]      recompute from the levels at the commit and compare only the
                                                       gold lines (type 2) of [Tiles] with the files; prints one
                                                       summary line per level; a level that does not exist
                                                       at BASE_COMMIT is read from NEW_LEVELS_BASE_COMMIT
                                                       (2ad2f5762, where the community levels lie unchanged)
"""

import argparse
from collections import deque
from pathlib import Path
import re
import subprocess
import sys

# Merge base of the branch with origin/integration/all at branch creation; used by --check without an argument.
BASE_COMMIT = "ed7f0db36cb0a9b9943753be38eb60ab2bfb68d0"
# Commit of origin/integration/all that holds the levels which do not exist at BASE_COMMIT in their original state
# (the community levels that arrived with the upstream ports); --check reads those levels from here.
NEW_LEVELS_BASE_COMMIT = "2ad2f576294eaf429d8aaf7a1b3a354633d3476d"

GOLD_TARGET_PER_KEEPER_SEAT = 300000
GOLD_PER_SEAM_TILE = 3000
DENSITY_LOW = 50
DENSITY_DEFAULT = 100
DENSITY_HIGH = 150
FULL_FULLNESS = 100.0
TYPE_DIRT = 1
TYPE_GOLD = 2
TYPE_ROCK = 3
TYPE_WATER = 4
TYPE_LAVA = 5
BLOCKED_TYPES = (TYPE_ROCK, TYPE_WATER, TYPE_LAVA)
KEEPER_FACTIONS = ("Keeper", "Choice")
EXCLUDED_NAMES = ("Test", "/aa.", "/ab.", "Sandbox", "Showcase")
GIT_TIMEOUT_SECONDS = 600
NO_SEAT = "-1"
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


# One tile line of the [Tiles] block: position, type, fullness text, seat text (or None) and the line index.
class TileEntry:
    def __init__(self, x, y, tile_type, fullness_text, seat_text, line_index):
        self.x = x
        self.y = y
        self.tile_type = tile_type
        self.fullness_text = fullness_text
        self.seat_text = seat_text
        self.line_index = line_index

    # Numeric fullness of the tile.
    def fullness(self):
        return float(self.fullness_text)


# Parsed level: all lines, the [Tiles] block range, map size, tile entries by position and keeper starts.
class Level:
    def __init__(self, lines):
        self.lines = lines
        self.tiles_begin = lines.index("[Tiles]") + 1
        self.tiles_end = lines.index("[/Tiles]")
        self.size_x = 0
        self.size_y = 0
        self.entries = {}
        self.starts = parse_keeper_starts(lines)
        self.parse_tiles()

    # Reads the map size and the tile lines of the [Tiles] block.
    def parse_tiles(self):
        sizes = []
        for index in range(self.tiles_begin, self.tiles_end):
            content = self.lines[index].split("#", 1)[0].strip()
            if not content:
                continue
            fields = content.split("\t")
            if len(sizes) < 2 and len(fields) == 1:
                sizes.append(int(fields[0]))
                continue
            seat_text = fields[4].strip() if len(fields) >= 5 else None
            self.entries[(int(fields[0]), int(fields[1]))] = TileEntry(
                int(fields[0]), int(fields[1]), int(fields[2]), fields[3].strip(), seat_text, index)
        self.size_x, self.size_y = sizes[0], sizes[1]

    # Type of a position: listed type, or dirt for tiles that are not listed.
    def tile_type(self, position):
        entry = self.entries.get(position)
        if entry is None:
            return TYPE_DIRT
        return entry.tile_type

    # True for a dirt tile that is full (listed with fullness 100 or more, or not listed).
    def is_full_dirt(self, position):
        entry = self.entries.get(position)
        if entry is None:
            return True
        return entry.tile_type == TYPE_DIRT and entry.fullness() >= FULL_FULLNESS

    # True when the position lies inside the map.
    def inside(self, x, y):
        return 0 <= x < self.size_x and 0 <= y < self.size_y


# Returns the start positions of the keeper seats of a level.
def parse_keeper_starts(lines):
    starts = []
    block = None
    for line in lines:
        if line == "[Seat]":
            block = {}
        elif line == "[/Seat]":
            if block is not None and block.get("faction") in KEEPER_FACTIONS:
                starts.append((int(block["startingX"]), int(block["startingY"])))
            block = None
        elif block is not None:
            words = line.split("\t")
            if len(words) >= 2:
                block[words[0]] = words[1].strip()
    return starts


# BFS distances from all keeper starts through every tile except rock, water and lava.
def compute_distances(level):
    distances = {}
    queue = deque()
    for start in level.starts:
        distances[start] = 0
        queue.append(start)
    while queue:
        x, y = queue.popleft()
        for dx, dy in NEIGHBOURS:
            neighbour = (x + dx, y + dy)
            if neighbour in distances or not level.inside(neighbour[0], neighbour[1]):
                continue
            if level.tile_type(neighbour) in BLOCKED_TYPES:
                continue
            distances[neighbour] = distances[(x, y)] + 1
            queue.append(neighbour)
    return distances


# Gold of a density value in gold units.
def gold_of(density):
    return GOLD_PER_SEAM_TILE * density // 100


# Result of the rebalance of one level: densities per gold position, added positions and the line rewrites.
class Result:
    def __init__(self):
        self.densities = {}
        self.added = []
        self.seats = 0
        self.gold_before = 0


# Applies rules 1-6 to a parsed level.
def rebalance(level):
    result = Result()
    result.seats = len(level.starts)
    distances = compute_distances(level)
    gold = [e for e in level.entries.values()
            if e.tile_type == TYPE_GOLD and e.fullness() > 0 and (e.x, e.y) in distances]
    gold.sort(key=lambda e: (distances[(e.x, e.y)], e.x, e.y))
    result.gold_before = len(gold)
    count = len(gold)
    order = []
    for index, entry in enumerate(gold):
        position = (entry.x, entry.y)
        if index * 3 < count:
            result.densities[position] = DENSITY_LOW
        elif index * 3 < 2 * count:
            result.densities[position] = DENSITY_DEFAULT
        else:
            result.densities[position] = DENSITY_HIGH
        order.append(position)
    target = GOLD_TARGET_PER_KEEPER_SEAT * result.seats
    total = sum(gold_of(d) for d in result.densities.values())
    for old, new in ((DENSITY_LOW, DENSITY_DEFAULT), (DENSITY_DEFAULT, DENSITY_HIGH)):
        for position in reversed(order):
            if total >= target:
                break
            if result.densities[position] == old:
                result.densities[position] = new
                total += gold_of(new) - gold_of(old)
    if total < target:
        grow_with_added_tiles(level, result, distances, total, target)
    return result


# Rule 6: adds full dirt tiles next to gold tiles as density 150 gold, farthest first, until the target is reached.
def grow_with_added_tiles(level, result, distances, total, target):
    candidates = set()
    for position in list(result.densities):
        add_candidates(level, position, distances, candidates, result.densities)
    while total < target and candidates:
        best = max(candidates, key=lambda p: (distances[p], p[0], p[1]))
        candidates.discard(best)
        result.densities[best] = DENSITY_HIGH
        result.added.append(best)
        total += gold_of(DENSITY_HIGH)
        add_candidates(level, best, distances, candidates, result.densities)


# Puts the full dirt 4-neighbours of a gold position with a finite distance into the candidate set; positions in
# taken (gold tiles of rule 3 and added tiles) are skipped.
def add_candidates(level, position, distances, candidates, taken):
    for dx, dy in NEIGHBOURS:
        neighbour = (position[0] + dx, position[1] + dy)
        if neighbour not in distances or neighbour in candidates or neighbour in taken:
            continue
        if level.is_full_dirt(neighbour):
            candidates.add(neighbour)


# Formats a gold tile line with a density column.
def format_gold_line(x, y, fullness_text, seat_text, density):
    return "\t".join([str(x), str(y), str(TYPE_GOLD), fullness_text, seat_text, str(density)])


# Returns the new lines of a level: changed gold lines replaced, added tiles appended before [/Tiles].
def apply_result(level, result):
    lines = list(level.lines)
    for position, density in result.densities.items():
        entry = level.entries.get(position)
        if entry is None or density == DENSITY_DEFAULT:
            continue
        seat_text = entry.seat_text if entry.seat_text is not None else NO_SEAT
        lines[entry.line_index] = format_gold_line(position[0], position[1], entry.fullness_text, seat_text, density)
    added_lines = []
    for position in result.added:
        line = format_gold_line(position[0], position[1], str(int(FULL_FULLNESS)), NO_SEAT, DENSITY_HIGH)
        entry = level.entries.get(position)
        if entry is None:
            added_lines.append(line)
        else:
            lines[entry.line_index] = line   # a full dirt tile that is listed: replace its line, no duplicate
    return lines[:level.tiles_end] + added_lines + lines[level.tiles_end:]


# Lists the level files below the root, minus the excluded names (paths with "/" separators).
def level_paths(root):
    paths = []
    for path in sorted(root.glob("levels/*/*.level")):
        name = path.relative_to(root).as_posix()
        if any(excluded in name for excluded in EXCLUDED_NAMES):
            continue
        paths.append(name)
    return paths


# Reads a level file of the work tree as lines without line ends.
def read_lines(path):
    return path.read_text(encoding="utf-8").split("\n")


# True when the level file exists at the commit.
def exists_at(root, commit, name):
    return subprocess.run(["git", "--no-pager", "cat-file", "-e", commit + ":" + name], cwd=str(root),
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          timeout=GIT_TIMEOUT_SECONDS).returncode == 0


# Reads a level as it was at a commit.
def read_lines_at(root, commit, name):
    output = subprocess.run(["git", "--no-pager", "show", commit + ":" + name], cwd=str(root), check=True,
                            stdout=subprocess.PIPE, timeout=GIT_TIMEOUT_SECONDS).stdout.decode("utf-8")
    return output.split("\n")


# Gold lines (type 2) of the [Tiles] block, comments removed, in file order.
def gold_lines(lines):
    level_begin = lines.index("[Tiles]") + 1
    level_end = lines.index("[/Tiles]")
    found = []
    for line in lines[level_begin:level_end]:
        content = line.split("#", 1)[0].strip()
        fields = content.split("\t")
        if len(fields) >= 4 and re.fullmatch(r"-?\d+", fields[0]) and fields[2] == str(TYPE_GOLD):
            found.append("\t".join(fields))
    return found


# One summary line of a level: seats, gold tiles before, gold per seat, density counts, added tiles.
def summary(name, level, result):
    counts = {DENSITY_LOW: 0, DENSITY_DEFAULT: 0, DENSITY_HIGH: 0}
    total = 0
    for density in result.densities.values():
        counts[density] += 1
        total += gold_of(density)
    return "%s | %d | %d | %d | %d/%d/%d | %d" % (
        name, result.seats, result.gold_before, total // result.seats, counts[DENSITY_LOW], counts[DENSITY_DEFAULT],
        counts[DENSITY_HIGH], len(result.added))


# Rewrites the level files of the work tree (run once).
def run_apply(root):
    for name in level_paths(root):
        path = root / name
        lines = read_lines(path)
        level = Level(lines)
        if not level.starts:
            continue
        if any(len(g.split("\t")) >= 6 for g in gold_lines(lines)):
            print("skipped (already has density columns): " + name)
            continue
        result = rebalance(level)
        path.write_text("\n".join(apply_result(level, result)), encoding="utf-8", newline="")
        print(summary(name, level, result))
    return 0


# Recomputes every level from the commit and compares only the gold lines with the files; returns the exit code.
def run_check(root, commit):
    failures = 0
    for name in level_paths(root):
        # A level that did not exist at the base commit is read from the commit that introduced it
        source_commit = commit if exists_at(root, commit, name) else NEW_LEVELS_BASE_COMMIT
        base_lines = read_lines_at(root, source_commit, name)
        level = Level(base_lines)
        if not level.starts:
            continue
        result = rebalance(level)
        expected = gold_lines(apply_result(level, result))
        found = gold_lines(read_lines(root / name))
        print(summary(name, level, result))
        if expected != found:
            failures += 1
            print("MISMATCH " + name)
    return 1 if failures else 0


# Command line entry point.
def main():
    parser = argparse.ArgumentParser(description="Gold density rebalance of the levels")
    parser.add_argument("--check", nargs="?", const=BASE_COMMIT, default=None, metavar="BASE_COMMIT")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    arguments = parser.parse_args()
    root = Path(arguments.root)
    if arguments.check is not None:
        return run_check(root, arguments.check)
    return run_apply(root)


if __name__ == "__main__":
    sys.exit(main())
