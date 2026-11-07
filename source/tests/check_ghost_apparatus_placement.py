"""Check the ghost room apparatus placement on floor stands without compiling (GHOST-APPARATUS-PLAN, decision 793).

The three apparatuses stand on floor stands inside the room like the furniture of other rooms, not bound to the wall:
inner tiles first, then edge tiles at a wall, then edge tiles at an open room side. They never stand on a cauldron or in
a door opening (a walkable gap that a wall closes on at least one end before the room side ends; a whole open room side
is no door). Every free room tile stays connected, a room with an entrance keeps a free tile at it, and every apparatus
keeps a free neighbour for the ectoplasm. A missing apparatus stays unplaced with one log line that names
the room size, its layout and the missing apparatus. A line-by-line model of layoutApparatuses runs over every
rectangular legal room from 4x4 to 8x8 with up to two doors, with every combination of open sides, with open sides and
one door, and over 4x4 and 5x5 rooms with three and four doors; the expected results are fixed values, counted once on
this branch."""
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


# The source keeps the floor-stand ranks, the door rule, the two passes, the bounded exhaustive search and the log line;
# the model below mirrors these lines.
def source_rules():
    room = read("source/rooms/RoomGhostRoom.cpp")
    layout = body(room, "void RoomGhostRoom::layoutApparatuses(")
    has(layout, "floor stands ranked inner, wall edge, open edge", "for(int rank=0;rank<3;++rank)",
        "if(blocked.count(tile)!=0 || inOpening(tile)) continue;",
        "if((inner?0:openSide?2:1)==rank) candidates.push_back(tile);",
        "if(floor.count(getGameMap()->getTile(tile->getX()+x,tile->getY()+y))==0) inner=false;")
    # The old wall binding is gone: no wall test decides a place
    for removed in ("atWall", "pass<3", "any free floor tile", "no wall place"):
        assert removed not in layout, ("wall binding removed", removed)
    has(layout, "door opening: a walkable gap closed by a wall before the room side ends",
        "{ return tile!=nullptr && floor.count(tile)==0 && !tile->isFullTile(); };",
        "const int px=dy[i],py=dx[i];", "if(side==nullptr || floor.count(side)==0) break;",
        "if(walkableOutside(beside)) continue;", "framed=true;break;", "if(framed) return true;")
    has(layout, "two greedy passes", "for(int pass=0;pass<2 && chosen.size()<APPARATUS_COUNT;++pass)",
        "if(pass==0 && beside) continue;", "if(!keepsReachable(taken)) continue;")
    has(layout, "bounded exhaustive search over the same candidates", "const size_t searchLimit=40;",
        "if(candidates.size()>searchLimit) candidates.resize(searchLimit);",
        "if(picked.size()==wanted) return keepsReachable(picked);", "if(spaced && beside) continue;",
        "for(size_t wanted=APPARATUS_COUNT;wanted>chosen.size() && !found;--wanted)",
        "for(int spaced=1;spaced>=0 && !found;--spaced)", "if(search(0,wanted,spaced==1)) { chosen=picked;found=true; }")
    # Only these two places add an apparatus tile
    assert layout.count("chosen.push_back(") == 1 and layout.count("chosen=") == 1, "no other placement path"
    assert layout.count("candidates.push_back(") == 1
    has(layout, "connected free tiles, an entrance, a stand per apparatus",
        "if(blocked.count(tile)==0 && std::find(taken.begin(),taken.end(),tile)==taken.end()) open.insert(tile);",
        "if(open.empty()) return taken.empty();", "if(walkableOutside(neighbor)) entrance=true;",
        "if(reached.size()!=open.size() || (hasEntrance && !entrance)) return false;",
        "if(open.count(getGameMap()->getTile(placed->getX()+x,placed->getY()+y))!=0) stand=true;",
        "if(!stand) return false;")
    has(layout, "one log line for a missing apparatus", "if(chosen.size()<APPARATUS_COUNT && !mCoveredTiles.empty())",
        "const char* names[APPARATUS_COUNT]={\"mana still\",\"ghost press\",\"soul forge\"};",
        "for(size_t index=chosen.size();index<APPARATUS_COUNT;++index)",
        "for(int y=maxY+1;y>=minY-1;--y)", "for(int x=minX-1;x<=maxX+1;++x)",
        "layout+=tile==nullptr || tile->isFullTile()?'#':floor.count(tile)==0?'o':blocked.count(tile)!=0?'C':",
        "std::find(chosen.begin(),chosen.end(),tile)!=chosen.end()?'A':'.';",
        "std::to_string(maxX-minX+1) + \"x\" + std::to_string(maxY-minY+1)",
        "\": no floor place outside the door openings for \" + missing + \"; layout \" + layout);")
    assert layout.count("OD_LOG_WRN(") == 1, "exactly one log line"
    has(room, "log header", "#include \"utils/LogManager.h\"")
    has(read("source/tests/check_ghost_rules.py"), "probe stub for the log line", "#define OD_LOG_WRN(x) ((void)0)")
    # Mana still, ghost press, soul forge in tile order; the stand is a free orthogonal neighbour
    has(layout, "order", "std::sort(chosen.begin(),chosen.end(),tileOrder);",
        "const GhostProduct order[APPARATUS_COUNT]={GhostProduct::mana,GhostProduct::research,GhostProduct::crystal};")
    # The furniture stands in the middle of its tile like the furniture of other rooms, not pushed to the wall
    create = body(room, "void RoomGhostRoom::createApparatusObjects(")
    has(create, "centred floor stand", "static_cast<float>(tile->getX()),static_cast<float>(tile->getY()),0.0f,static_cast<float>(rotation),false);",
        "if(neighbor==nullptr || neighbor->getCoveringRoom()!=this) { rotation=rotations[i];break; }")
    assert "forward=0.5-depth/2.0" not in create, "no push to the wall"
    # The cauldron layout runs first and keeps its place
    update = body(room, "void RoomGhostRoom::updateActiveSpots(")
    has(update, "cauldrons first", "layoutCauldrons();\n    layoutApparatuses();")
    has(update, "no rack on an apparatus tile", "if(apparatusTile) continue;\n                walls.push_back(")
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
    walkable = lambda t: t not in room and t not in walls
    beside = lambda picked, t: any(abs(c[0] - t[0]) <= 1 and abs(c[1] - t[1]) <= 1 for c in picked)

    def opening(t):
        for dx, dy in D4:
            n = (t[0] + dx, t[1] + dy)
            if not walkable(n):
                continue
            px, py = dy, dx
            for sign in (-1, 1):
                step = 1
                while True:
                    side = (t[0] + sign * step * px, t[1] + sign * step * py)
                    if side not in room:
                        break
                    if walkable((n[0] + sign * step * px, n[1] + sign * step * py)):
                        step += 1
                        continue
                    return True
        return False

    has_entrance = any(walkable((t[0] + dx, t[1] + dy)) for t in room for dx, dy in D4)

    def reachable(taken):
        free = {t for t in room if t not in blocked and t not in taken}
        if not free:
            return not taken
        start = min(free)
        seen, pending, entrance = {start}, [start], False
        while pending:
            t = pending.pop()
            for dx, dy in D4:
                n = (t[0] + dx, t[1] + dy)
                entrance |= walkable(n)
                if n in free and n not in seen:
                    seen.add(n)
                    pending.append(n)
        if len(seen) != len(free) or (has_entrance and not entrance):
            return False
        return all(any((p[0] + x, p[1] + y) in free for x in (-1, 0, 1) for y in (-1, 0, 1)) for p in taken)

    def rank(t):
        inner = all((t[0] + x, t[1] + y) in room for x in (-1, 0, 1) for y in (-1, 0, 1))
        open_side = any(walkable((t[0] + dx, t[1] + dy)) for dx, dy in D4)
        return 0 if inner else 2 if open_side else 1

    ordered = sorted(room, key=lambda t: (t[1], t[0]))
    candidates = [t for r in range(3) for t in ordered if t not in blocked and not opening(t) and rank(t) == r]
    chosen = []
    for spaced in (True, False):
        for t in candidates:
            if len(chosen) >= 3:
                break
            if t in chosen or (spaced and beside(chosen, t)) or not reachable(chosen + [t]):
                continue
            chosen.append(t)
    searched = False
    if len(chosen) < 3:
        limited = candidates[:40]
        for wanted in range(3, len(chosen), -1):
            found = None
            for spaced in (True, False):
                for picked in combinations(limited, wanted):
                    if spaced and any(beside(picked[:i], picked[i]) for i in range(1, wanted)):
                        continue
                    if reachable(list(picked)):
                        found = list(picked)
                        break
                if found:
                    break
            if found:
                chosen, searched = found, True
                break
    chosen.sort(key=lambda t: (t[1], t[0]))
    # Every placed apparatus obeys the rule
    for t in chosen:
        assert t in room and t not in blocked and not opening(t), t
    assert reachable(chosen)
    return chosen, searched, blocked, {t for t in room if opening(t)}


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


# Door places of a w x h room: the ring tiles beside a room side, without the four corners.
def door_sides(w, h):
    _, _, ring = rect(w, h)
    return sorted(t for t in ring if not (t[0] in (-1, w) and t[1] in (-1, h)))


# Every walled legal room with up to two doors gets all three apparatuses, none in a door opening.
def rooms_with_doors():
    rooms, placed, searched = 0, 0, []
    for w in range(4, 9):
        for h in range(4, 9):
            for count in (0, 1, 2):
                if count == 2 and w * h > 36:
                    continue
                for doors in combinations(door_sides(w, h), count):
                    room, walls, _ = rect(w, h, doors)
                    chosen, search, _, openings = layout(room, walls)
                    rooms += 1
                    placed += len(chosen) == 3
                    # Every door makes exactly its own room tile a door opening
                    assert len(openings) == len({(min(max(d[0], 0), w - 1), min(max(d[1], 0), h - 1)) for d in doors}), (w, h, doors)
                    if search:
                        searched.append((w, h, doors))
    # Fixed values counted once on this branch: all 3925 rooms get all three; 23 4x4 rooms with two doors need the
    # bounded exhaustive search, the greedy passes alone block themselves there
    assert rooms == 3925, rooms
    assert placed == rooms, (placed, rooms)
    assert len(searched) == 23 and {s[:2] for s in searched} == {(4, 4)}, (len(searched), {s[:2] for s in searched})
    print("walled rooms 4x4 to 8x8 with up to two doors: all three apparatuses on floor stands: ok")


# Every legal room open on any sides, also with one door in a walled side, gets all three apparatuses.
def rooms_with_open_sides():
    rooms = 0
    for w in range(4, 9):
        for h in range(4, 9):
            for mask in range(16):
                room, walls, _ = rect(w, h, mask=mask)
                chosen, _, _, openings = layout(room, walls)
                rooms += 1
                assert len(chosen) == 3, (w, h, mask, chosen)
                # A whole open side is no door
                assert not openings, (w, h, mask, openings)
                if w * h <= 25:
                    for door in door_sides(w, h):
                        if door in walls:
                            room, walls2, _ = rect(w, h, (door,), mask)
                            assert len(layout(room, walls2)[0]) == 3, (w, h, mask, door)
                            rooms += 1
    # Fixed value: 400 rooms with open sides, plus the walled-side doors of the 4x4 to 5x5 ones
    assert rooms == 1296, rooms
    print("rooms with open sides, free-standing rooms, open sides with a door: all three apparatuses: ok")


def fixed_layouts():
    # Walled 4x4: the cauldron fills the inner tiles, the three stand side by side on the low edge
    room, walls, _ = rect(4, 4)
    chosen = layout(room, walls)[0]
    assert chosen == [(0, 0), (1, 0), (2, 0)], chosen
    # Walled 6x6: inner tiles beside the cauldron first, a free tile between them
    room, walls, _ = rect(6, 6)
    chosen = layout(room, walls)[0]
    assert chosen == [(3, 1), (1, 3), (3, 3)], chosen
    # Walled 7x7 with four cauldrons: the stands keep the passages between the cauldrons free
    room, walls, _ = rect(7, 7)
    chosen = layout(room, walls)[0]
    assert chosen == [(3, 1), (1, 3), (4, 3)], chosen
    # Free-standing 4x4 room (decision 790 left it empty): now all three stand on its open edge
    room, walls, _ = rect(4, 4, mask=15)
    chosen, _, blocked, _ = layout(room, walls)
    assert chosen == [(0, 0), (1, 0), (2, 0)], chosen
    assert log_layout(room, walls, chosen, blocked) == "oooooo/o....o/o.CC.o/o.CC.o/oAAA.o/oooooo"
    # 4x4 open on two opposite sides (decision 790 gave it two): now three
    room, walls, _ = rect(4, 4, mask=3)
    chosen, _, blocked, _ = layout(room, walls)
    assert chosen == [(0, 0), (0, 1), (0, 2)], chosen
    assert log_layout(room, walls, chosen, blocked) == "oooooo/#....#/#ACC.#/#ACC.#/#A...#/oooooo"
    # Doors left of (0,0) and below (2,0): the door tiles stay free
    room, walls, _ = rect(4, 4, ((-1, 0), (2, -1)))
    chosen, searched, blocked, openings = layout(room, walls)
    assert openings == {(0, 0), (2, 0)} and searched, openings
    assert chosen == [(3, 0), (3, 1), (3, 2)], chosen
    assert log_layout(room, walls, chosen, blocked) == "######/#....#/#.CCA#/#.CCA#/o...A#/###o##"
    print("fixed placements: ok")


# Only a 4x4 room with four single doors, one on each side beside a corner, can leave one apparatus out: the ring
# around its cauldron then has no three free tiles in a row, so a third apparatus would cut a room tile off.
def rooms_beyond_two_doors():
    short = {}
    for w, h in ((4, 4), (5, 5)):
        for count in (3, 4):
            for doors in combinations(door_sides(w, h), count):
                room, walls, _ = rect(w, h, doors)
                n = len(layout(room, walls)[0])
                if n < 3:
                    short.setdefault((w, h, count, n), []).append(doors)
    counts = {key: len(value) for key, value in short.items()}
    # Fixed values counted once on this branch
    assert counts == EXPECTED_SHORT, counts
    doors = short[(4, 4, 4, 2)][0]
    assert doors == ((-1, 0), (-1, 3), (3, -1), (3, 4)), doors
    room, walls, _ = rect(4, 4, doors)
    chosen, _, blocked, _ = layout(room, walls)
    assert log_layout(room, walls, chosen, blocked) == EXPECTED_LOG, log_layout(room, walls, chosen, blocked)
    print("rooms with three or four doors: only 32 4x4 rooms with four doors keep two, pinned: ok")


EXPECTED_SHORT = {(4, 4, 4, 2): 32}
EXPECTED_LOG = "####o#/o....#/#.CC.#/#.CC.#/o.AA.#/####o#"


def main():
    source_rules()
    fixed_layouts()
    rooms_with_doors()
    rooms_with_open_sides()
    rooms_beyond_two_doors()
    print("ghost apparatus placement: ok")


if __name__ == "__main__":
    main()
