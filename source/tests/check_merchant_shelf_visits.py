"""Owner decision 866 (1): the merchant also walks to the wall shelves of his room and arranges goods there, so he
moves around even with a single sales table. No compiler, no game.

Call (from the repository root): python source/tests/check_merchant_shelf_visits.py
"""
import re, sys, pathlib

root = pathlib.Path(__file__).resolve().parents[2]
fails = []

def text(rel):
    return (root / rel).read_text(encoding="utf-8", errors="replace")

room_h = text("source/rooms/RoomMerchant.h")
ent = text("source/entities/MerchantEntity.cpp")
m = re.search(r"getShelfTiles\(\) const.*?\n    \}", room_h, re.S)
body = m.group(0) if m else ""
for wall in ("Left", "Right", "Top", "Bottom"):
    if "m%sWallsActiveSpotTiles" % wall not in body:
        fails.append("shelf tiles: %s wall shelves are not collected" % wall)
if "getShelfTiles()" not in ent or "stops.insert" not in ent:
    fails.append("walk targets: shelves are not added to the table stops")
if not re.search(r"next != start", ent):
    fails.append("walk targets: the current tile is not skipped, a single table would not move him")
if not re.search(r'mAtShelf \? "Idle" : "CountGold"', ent):
    fails.append("animation: shelf stops use Idle, table stops CountGold (no new clip)")
if not re.search(r"setAnimationState\(mAtShelf \? \"Idle\" : \"CountGold\", true, facing\)", ent):
    fails.append("facing: the shelf stop is not turned with the room facing (back to the wall)")
for bad in ("RubHands2", "Arrange"):
    if bad in ent:
        fails.append("no new clip allowed: " + bad)
if any(ord(c) < 32 and c not in "\n\r\t" for c in ent + room_h):
    fails.append("control characters in source")

if fails:
    print("FAIL"); [print(" -", f) for f in fails]; sys.exit(1)
print("OK check_merchant_shelf_visits")
