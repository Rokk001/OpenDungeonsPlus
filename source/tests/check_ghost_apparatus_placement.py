"""Check the hardened ghost room apparatus placement without compiling (GHOST-APPARATUS-PLAN, decision 731).

The apparatuses stand only on wall tiles outside door openings, every free room tile stays reachable, there is no
fallback to any free floor tile or into a door opening, and a missing apparatus stays unplaced with one log line that
names the room size, its layout and the missing apparatus. A line-by-line model of layoutApparatuses runs over every
rectangular legal room from 4x4 to 8x8 with up to two doors and with open sides; the expected results are fixed
values, counted once on this branch."""
from itertools import combinations
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
D4 = [(0, 1), (-1, 0), (1, 0), (0, -1)]


# Read a tracked source using the repository root rather than the caller's directory.
def read(path):
    return (repo / path).read_text(encoding="utf-8")


# Return a complete brace-delimited body that starts at the signature.
def body(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


# Assert that every fragment occurs in the text, naming the rule it proves.
def has(text, rule, *fragments):
    for fragment in fragments:
        assert fragment in text, (rule, fragment)


# The source keeps only the wall passes, the exhaustive wall search and the log line; the model below mirrors these lines.
def source_rules():
    room = read("source/rooms/RoomGhostRoom.cpp")
    layout = body(room, "void RoomGhostRoom::layoutApparatuses(")
    has(layout, "two wall passes, no third pass", "for(int pass=0;pass<2 && chosen.size()<APPARATUS_COUNT;++pass)",
        "if(!atWall(tile) || inOpening(tile)) continue;", "if(pass==0 && beside) continue;", "if(!keepsReachable(taken)) continue;")
    for removed in ("pass<3", "if(pass<2 && (", "any free floor tile"):
        assert removed not in layout, ("fallback removed", removed)
    has(layout, "exhaustive search over the same wall tiles",
        "if(blocked.count(tile)==0 && atWall(tile) && !inOpening(tile)) candidates.push_back(tile);",
        "if(picked.size()==wanted) return keepsReachable(picked);", "if(spaced && beside) continue;",
        "for(size_t wanted=APPARATUS_COUNT;wanted>chosen.size() && !found;--wanted)",
        "for(int spaced=1;spaced>=0 && !found;--spaced)", "if(search(0,wanted,spaced==1)) { chosen=picked;found=true; }")
    # Only these two places add an apparatus tile
    assert layout.count("chosen.push_back(") == 1 and layout.count("chosen=") == 1, "no other placement path"
    assert layout.count("candidates.push_back(") == 1
    has(layout, "connected free tiles", "if(blocked.count(tile)==0 && std::find(taken.begin(),taken.end(),tile)==taken.end()) open.insert(tile);",
        "return reached.size()==open.size();")
    has(layout, "door opening", "if(neighbor!=nullptr && floor.count(neighbor)==0 && !neighbor->isFullTile()) return true;")
    has(layout, "wall", "if(neighbor==nullptr || neighbor->isFullTile()) return true;")
    has(layout, "one log line for a missing apparatus", "if(chosen.size()<APPARATUS_COUNT && !mCoveredTiles.empty())",
        "const char* names[APPARATUS_COUNT]={\"mana still\",\"ghost press\",\"soul forge\"};",
        "for(size_t index=chosen.size();index<APPARATUS_COUNT;++index)",
        "for(int y=maxY+1;y>=minY-1;--y)", "for(int x=minX-1;x<=maxX+1;++x)",
        "layout+=tile==nullptr || tile->isFullTile()?'#':floor.count(tile)==0?'o':blocked.count(tile)!=0?'C':",
        "std::find(chosen.begin(),chosen.end(),tile)!=chosen.end()?'A':'.';",
        "std::to_string(maxX-minX+1) + \"x\" + std::to_string(maxY-minY+1)",
        "\": no wall place outside the door openings for \" + missing + \"; layout \" + layout);")
    assert layout.count("OD_LOG_WRN(") == 1, "exactly one log line"
    has(room, "log header", "#include \"utils/LogManager.h\"")
    has(read("source/tests/check_ghost_rules.py"), "probe stub for the log line", "#define OD_LOG_WRN(x) ((void)0)")
    # The order and the stand search after the placement are unchanged
    has(layout, "order", "const GhostProduct order[APPARATUS_COUNT]={GhostProduct::mana,GhostProduct::research,GhostProduct::crystal};")
    print("placement source rules: ok")


# Model layoutCauldrons: 2x2 anchors on inner tiles, more than two tiles apart, in tile order.
def cauldrons(room):
    inner = {t for t in room if all((t[0] + x, t[1] + y) in room for x in (-1, 0, 1) for y in (-1, 0, 1))}
    anchors = []
    for a in sorted(inner, key=lambda t: (t[1], t[0])):
        if all((a[0] + x, a[1] + y) in inner for x in (0, 1) for y in (0, 1)) and \
                all(abs(a[0] - p[0]) > 2 or abs(a[1] - p[1]) > 2 for p in anchors):
            anchors.append(a)
    return anchors


# Model layoutApparatuses; walls are the full tiles, every other tile outside the room is walkable floor.
def layout(room, walls):
    blocked = {(a[0] + x, a[1] + y) for a in cauldrons(room) for x in (0, 1) for y in (0, 1)}
    at_wall = lambda t: any((t[0] + dx, t[1] + dy) in walls for dx, dy in D4)
    opening = lambda t: any((t[0] + dx, t[1] + dy) not in room and (t[0] + dx, t[1] + dy) not in walls for dx, dy in D4)
    beside = lambda picked, t: any(abs(c[0] - t[0]) <= 1 and abs(c[1] - t[1]) <= 1 for c in picked)

    def reachable(taken):
        free = {t for t in room if t not in blocked and t not in taken}
        if not free:
            return True
        start = next(iter(free))
        seen, pending = {start}, [start]
        while pending:
            t = pending.pop()
            for dx, dy in D4:
                n = (t[0] + dx, t[1] + dy)
                if n in free and n not in seen:
                    seen.add(n)
                    pending.append(n)
        return len(seen) == len(free)

    ordered = sorted(room, key=lambda t: (t[1], t[0]))
    candidates = [t for t in ordered if t not in blocked and at_wall(t) and not opening(t)]
    chosen = []
    for spaced in (True, False):
        for t in candidates:
            if len(chosen) >= 3:
                break
            if t in chosen or (spaced and beside(chosen, t)) or not reachable(chosen + [t]):
                continue
            chosen.append(t)
    fallback = False
    if len(chosen) < 3:
        for wanted in range(3, len(chosen), -1):
            found = None
            for spaced in (True, False):
                for picked in combinations(candidates, wanted):
                    if spaced and any(beside(picked[:i], picked[i]) for i in range(1, wanted)):
                        continue
                    if reachable(list(picked)):
                        found = list(picked)
                        break
                if found:
                    break
            if found:
                chosen, fallback = found, True
                break
    # Every placed apparatus obeys the rule
    for t in chosen:
        assert t in room and t not in blocked and at_wall(t) and not opening(t), t
    assert reachable(chosen)
    return chosen, fallback, blocked


# Model the reproduction layout of the log line.
def log_layout(room, walls, chosen, blocked):
    xs, ys = [t[0] for t in room], [t[1] for t in room]
    rows = []
    for y in range(max(ys) + 1, min(ys) - 2, -1):
        row = ""
        for x in range(min(xs) - 1, max(xs) + 2):
            t = (x, y)
            row += "#" if t in walls else "o" if t not in room else "C" if t in blocked else "A" if t in chosen else "."
        rows.append(row)
    return "/".join(rows)


# A w x h room at the origin; doors are ring tiles left open, open sides a bit mask (1 low y, 2 high y, 4 low x, 8 high x).
def rect(w, h, doors=(), mask=0):
    room = {(x, y) for x in range(w) for y in range(h)}
    ring = {(x, y) for x in range(-1, w + 1) for y in range(-1, h + 1)} - room
    walls = set(ring) - set(doors)
    for t in ring:
        if (mask & 1 and t[1] == -1) or (mask & 2 and t[1] == h) or (mask & 4 and t[0] == -1) or (mask & 8 and t[0] == w):
            walls.discard(t)
    return room, walls, ring


def rooms_with_doors():
    rooms, placed, fallbacks = 0, 0, []
    for w in range(4, 9):
        for h in range(4, 9):
            _, _, ring = rect(w, h)
            sides = sorted(t for t in ring if not (t[0] in (-1, w) and t[1] in (-1, h)))
            for count in (0, 1, 2):
                if count == 2 and w * h > 36:
                    continue
                for doors in combinations(sides, count):
                    room, walls, _ = rect(w, h, doors)
                    chosen, fallback, _ = layout(room, walls)
                    rooms += 1
                    placed += len(chosen) == 3
                    if fallback:
                        fallbacks.append((w, h, doors))
    # Fixed values counted once on this branch: every walled room with up to two doors gets all three apparatuses;
    # nine 4x4 rooms with two doors need the exhaustive search, the greedy passes alone left one or two out there
    assert rooms == 3925, rooms
    assert placed == rooms, (placed, rooms)
    assert len(fallbacks) == 9 and {f[:2] for f in fallbacks} == {(4, 4)}, fallbacks
    assert ((4, 4, ((-1, 0), (2, -1))) in fallbacks)
    print("walled rooms 4x4 to 8x8 with up to two doors: all three apparatuses placed: ok")


def fixed_layouts():
    room, walls, _ = rect(4, 4)
    assert layout(room, walls)[0] == [(0, 0), (1, 0), (2, 0)]
    room, walls, _ = rect(6, 6)
    assert layout(room, walls)[0] == [(0, 0), (4, 0), (5, 2)]
    # The exhaustive search keeps the doors free: doors left of (0,0) and below (2,0)
    room, walls, _ = rect(4, 4, ((-1, 0), (2, -1)))
    chosen = layout(room, walls)[0]
    assert chosen == [(3, 0), (3, 1), (3, 2)], chosen
    print("fixed placements: ok")


def rooms_without_place():
    short = {}
    for w in range(4, 9):
        for h in range(4, 9):
            for mask in range(16):
                room, walls, _ = rect(w, h, mask=mask)
                n = len(layout(room, walls)[0])
                if n < 3:
                    short.setdefault((bin(mask).count("1"), n), []).append((w, h, mask))
    # Fixed values: a 4x4 room open on two opposite sides and every room open on three sides keeps only two places;
    # a free-standing room (open on all four sides) has none. Walled rooms and rooms open on one side or two
    # adjoining sides always get all three.
    counts = {key: len(value) for key, value in short.items()}
    assert counts == {(2, 2): 2, (3, 2): 20, (4, 0): 25}, counts
    assert short[(2, 2)] == [(4, 4, 3), (4, 4, 12)]
    # Reproductions as the log line prints them
    room, walls, _ = rect(4, 4, mask=15)
    chosen, _, blocked = layout(room, walls)
    assert chosen == []
    assert log_layout(room, walls, chosen, blocked) == "oooooo/o....o/o.CC.o/o.CC.o/o....o/oooooo"
    room, walls, _ = rect(4, 4, mask=3)
    chosen, _, blocked = layout(room, walls)
    assert chosen == [(0, 1), (0, 2)], chosen
    assert log_layout(room, walls, chosen, blocked) == "oooooo/#....#/#ACC.#/#ACC.#/#....#/oooooo"
    print("legal rooms without a valid place for every apparatus, reproduced: ok")


def main():
    source_rules()
    fixed_layouts()
    rooms_with_doors()
    rooms_without_place()
    print("ghost apparatus placement: ok")


if __name__ == "__main__":
    main()
