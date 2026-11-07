"""Owner decision 847 (merchant room, build 0.7.4.49): the MerchantShelf stood with its open side to the wall and the
merchant stood in front of a wall and stared at it. No compiler, no game.

One check per fault
  shelf rotation      RoomMerchant::notifyActiveSpotCreated turns wall shelves by place: left 90, right 270,
                      bottom 180, top 0 (the convention of Library, Casino, Crypt, Alchemy lab ...), not a fixed 0
  other wall objects  every room that places objects on wall spots (left/right/top/bottom) turns them per place
  merchant facing     MerchantEntity turns to the open room side (back to the wall) while it idles at a table

Call (from the repository root): python source/tests/check_merchant_wall_facing.py
"""
import re, sys, pathlib

root = pathlib.Path(__file__).resolve().parents[2]
fails = []

def text(rel):
    return (root / rel).read_text(encoding="utf-8", errors="replace")

merchant = text("source/rooms/RoomMerchant.cpp")
m = re.search(r"RoomMerchant::notifyActiveSpotCreated.*?\n\}", merchant, re.S)
body = m.group(0) if m else ""
for place, angle in (("activeSpotLeft", "90"), ("activeSpotRight", "270"), ("activeSpotBottom", "180")):
    if not re.search(place + r"\)\s*angle\s*=\s*" + angle, body):
        fails.append("shelf rotation: %s must give %s degrees" % (place, angle))
if not re.search(r'"MerchantShelf"[^;]*angle', body):
    fails.append("shelf rotation: MerchantShelf is not created with the per-place angle")

for rel in ("RoomLibrary", "RoomCasino", "RoomCrypt", "RoomPrison", "RoomTorture", "RoomAlchemyLab",
            "RoomInfirmary", "RoomGhostRoom", "RoomTrainingHall", "RoomArena"):
    t = text("source/rooms/%s.cpp" % rel)
    for place, angle in (("Left", "90"), ("Right", "270"), ("Bottom", "180")):
        if place == "Bottom" and rel == "RoomWorkshop":
            continue
        if not re.search(r"activeSpot%s\b.{0,260}?\b%s(\.0)?f?\b" % (place, angle), t, re.S):
            fails.append("other wall objects: %s lacks %s degrees for the %s wall" % (rel, angle, place))

ent = text("source/entities/MerchantEntity.cpp")
if "getRoomFacing" not in ent or not re.search(r"setAnimationState\(\"CountGold\",\s*true,\s*facing\)", ent):
    fails.append("merchant facing: the idling merchant is not turned to the open room side")
if not re.search(r"!open\[index\]\s*&&\s*open\[opposite\]", ent):
    fails.append("merchant facing: the back to the wall rule is missing")

if fails:
    print("FAIL"); [print(" -", f) for f in fails]; sys.exit(1)
print("OK check_merchant_wall_facing")
