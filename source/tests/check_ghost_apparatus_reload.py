"""Check that the ghost room apparatuses of a loaded level or save are laid out new off the wall (owner decision 825).

Compiles nothing and never starts the game.
- The save keeps no apparatus place: RoomGhostRoom writes and reads only the counters of its GhostApparatus record, the
  apparatus objects are room furniture (BuildingObject) that no save section writes, and the place is reset at the
  start of every layout. On the server GameMap::createAllEntities lays out every loaded room again
  (updateActiveSpots -> layoutApparatuses -> createApparatusObjects), so a changed placement rule reaches the
  ghost rooms of every old save.
- The layout model of check_ghost_apparatus_placement.py runs on the ghost room of levels/skirmish/TestGhosts.level
  (the owner's [Test] Ghosts map): the three apparatuses stand off the wall, two of them in the middle row three
  tiles from both long walls (fixed values, decision 845).
- The same model runs on every ghost room of every save in the user's save folder (%APPDATA%/opendungeons/saves),
  when there is one: its GhostApparatus record holds twelve counters and no place, and a loaded room gets the places
  of the current rule (inner tiles first, an inner tile never touches a wall); the count off the wall is printed.
"""
import os
from pathlib import Path
import re
import sys

here = Path(__file__).resolve().parent
repo = here.parents[1]
sys.path.insert(0, str(here))
import check_ghost_apparatus_placement as placement  # noqa: E402


def read(path):
    return (repo / path).read_text(encoding="utf-8")


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def source_chain():
    room = strip_comments(read("source/rooms/RoomGhostRoom.cpp"))
    export = placement.body(room, "void RoomGhostRoom::exportToStream(")
    imported = placement.body(room, "bool RoomGhostRoom::importFromStream(")
    for text, name in ((export, "exportToStream"), (imported, "importFromStream")):
        # Only the counters of the record, never a tile, a position or an object of an apparatus
        for fragment in ("getX()", "getY()", "apparatus.tile", "apparatus.stand", "apparatus.object", "getTile("):
            assert fragment not in text, (name, "keeps no apparatus place", fragment)
    placement.has(export, "the record holds four counters per apparatus",
                  "os << ' ' << apparatus.pendingEctoplasm << ' ' << apparatus.working << ' ' << apparatus.workTurns << ' ' << apparatus.crystalEctoplasm;")
    placement.has(imported, "the record is read as four counters per apparatus",
                  "is >> apparatus.pendingEctoplasm >> apparatus.working >> apparatus.workTurns >> apparatus.crystalEctoplasm")
    layout = placement.body(room, "void RoomGhostRoom::layoutApparatuses(")
    assert layout.index("for(Apparatus& apparatus : mApparatuses) { apparatus.tile=nullptr;apparatus.stand=nullptr; }") < 200, \
        "every layout starts without a place"
    spots = placement.body(room, "void RoomGhostRoom::updateActiveSpots(")
    assert spots.index("layoutApparatuses();") < spots.index("clearWallObjects();") < spots.index("createApparatusObjects(map);"), \
        "the room lays out the apparatuses and rebuilds their objects"
    create = placement.body(room, "void RoomGhostRoom::createApparatusObjects(")
    placement.has(create, "the objects stand on the laid out tiles",
                  "Tile* tile=apparatus.tile;", "static_cast<float>(tile->getX()),static_cast<float>(tile->getY())")
    game_map = strip_comments(read("source/gamemap/GameMap.cpp"))
    entities = placement.body(game_map, "void GameMap::createAllEntities()")
    server = entities[entities.index("if(isServerGameMap())"):]
    placement.has(server, "every loaded room is laid out again on the server",
                  "for (Room* room : mRooms)\n        {\n            room->updateActiveSpots(this);\n        }")
    # No save section writes room furniture: the writer has no BuildingObject section
    handler = strip_comments(read("source/gamemap/MapHandler.cpp"))
    assert "buildingObject" not in handler and "BuildingObject" not in handler, "room furniture is not saved"
    print("loaded rooms keep no apparatus place and are laid out again: ok")


def parse_map(text):
    """Full tiles and ghost rooms (room type 25) of a level or save file."""
    lines = text.split("\n")
    walls, rooms = set(), []
    start = lines.index("[Tiles]")
    for line in lines[start + 1:]:
        if line.startswith("[/Tiles]"):
            break
        fields = line.split("#")[0].split()
        if len(fields) >= 4 and all(re.fullmatch(r"-?\d+", f) for f in fields[:3]):
            if float(fields[3]) > 0:
                walls.add((int(fields[0]), int(fields[1])))
    index = 0
    while index < len(lines):
        if lines[index].startswith("[Room]"):
            header = lines[index + 1].split()
            tiles, records = set(), []
            index += 2
            while not lines[index].startswith("[/Room]"):
                fields = lines[index].split()
                if len(fields) >= 2 and re.fullmatch(r"\d+", fields[0]) and re.fullmatch(r"\d+", fields[1]):
                    tiles.add((int(fields[0]), int(fields[1])))
                elif fields and fields[0] == "GhostApparatus":
                    records.append(fields[1:])
                index += 1
            if header and header[0] == "25":
                rooms.append((header[1], tiles, records))
        index += 1
    return walls, rooms


def off_wall(tile, walls):
    return all((tile[0] + x, tile[1] + y) not in walls for x in (-1, 0, 1) for y in (-1, 0, 1))


def test_level():
    walls, rooms = parse_map(read("levels/skirmish/TestGhosts.level"))
    assert [name for name, _, _ in rooms] == ["GhostRoom1"], rooms
    _, room, _ = rooms[0]
    assert room == {(x, y) for x in range(15, 20) for y in range(7, 12)}, sorted(room)
    chosen, _, blocked, openings = placement.layout(room, walls)
    # Fixed values (mana still, ghost press, soul forge in tile order). Build 0.7.4.49 put all three one row in front of
    # a long wall (18, 8), (16, 10), (18, 10), which the owner still saw as at the wall (decision 845). Now two stand
    # in the middle row of the room, three tiles from both long walls, one on the open edge, and the third one row
    # off the wall: the whole middle row cannot be taken, it would cut the room in two.
    assert blocked == {(16, 8), (17, 8), (16, 9), (17, 9)}, blocked
    assert chosen == [(18, 8), (15, 9), (18, 9)], chosen
    assert not openings
    assert all(off_wall(t, walls) for t in chosen), chosen
    distance = lambda t: min(max(abs(t[0] - w[0]), abs(t[1] - w[1])) for w in walls)
    assert [distance(t) for t in chosen] == [2, 3, 3], [distance(t) for t in chosen]
    assert placement.log_layout(room, walls, chosen, blocked) == "o#####o/o.....o/o.....o/oACCA.o/o.CCA.o/o.....o/o######"
    print("[Test] Ghosts room: three apparatuses off the wall, two in the middle row: ok")


def user_saves():
    base = os.environ.get("APPDATA")
    folder = Path(base) / "opendungeons" / "saves" if base else Path.home() / ".config" / "opendungeons" / "saves"
    saves = sorted(folder.glob("*.level")) if folder.is_dir() else []
    checked = off = placed = 0
    for save in saves:
        text = save.read_text(encoding="utf-8", errors="replace")
        if "[Tiles]" not in text:
            continue
        walls, rooms = parse_map(text)
        for name, room, records in rooms:
            for record in records:
                assert len(record) == 12, (save.name, name, "twelve counters, no place", record)
            if not room:
                continue
            # The model asserts the rule for every place (inside the room, no cauldron, no door opening, every tile
            # reachable); an inner tile never touches a wall, and inner tiles are taken first
            chosen, _, blocked, _ = placement.layout(room, walls)
            inner = [t for t in chosen if all((t[0] + x, t[1] + y) in room for x in (-1, 0, 1) for y in (-1, 0, 1))]
            assert all(off_wall(t, walls) for t in inner), (save.name, name, chosen)
            off += sum(off_wall(t, walls) for t in chosen)
            placed += len(chosen)
            checked += 1
    print("user saves: %d ghost rooms laid out by the current rule, %d of %d apparatuses off the wall%s: ok"
          % (checked, off, placed, "" if saves else " (no save folder)"))


def main():
    source_chain()
    test_level()
    user_saves()
    print("ghost apparatus reload: ok")


if __name__ == "__main__":
    main()
