"""Check ghost-room integration after room controls moved into Room Manager.

The former ghost hunters HUD button is removed, and the shared Room Manager button
uses the navigation icon and compacts with the rest of the row. The retained ghost
icon asset, room tile ownership transport and apparatus start choices are still
checked; dedicated Room Manager navigation probes cover opening and selection.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image

repo = Path(__file__).resolve().parents[2]
import sys
# ODP_ASSETS_SRC (else <repo>/assets-src) holds the asset sources, see scripts/assets_src.py
sys.path.insert(0, str(repo / 'scripts'))
from assets_src import assets_src_dir, resolve  # noqa: E402
DESIGN_W, DESIGN_H = 1024.0, 768.0


# Read a tracked source using the repository root rather than the caller's directory.
def read(path):
    return resolve(repo, path).read_text(encoding="utf-8")


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


# Remove C++ comments so that only code is matched.
def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


# Return the properties of a layout window.
def props(node):
    return {p.get("name"): p.get("value") for p in node.findall("Property")}


# Parse a CEGUI area into four (scale, offset) pairs.
def udims(value):
    return [(float(a), float(b)) for a, b in re.findall(r"\{([-\d.]+),([-\d.]+)\}", value)]


# The single manager replaces the separate room buttons at the original production slot.
def layout_button():
    gui = read("source/render/Gui.cpp")
    assert float(re.search(r"LAYOUT_DESIGN_WIDTH = ([0-9.]+)f", gui)[1]) == DESIGN_W
    assert float(re.search(r"LAYOUT_DESIGN_HEIGHT = ([0-9.]+)f", gui)[1]) == DESIGN_H
    root = ET.parse(repo / "gui/ModeGame.layout").getroot()
    nodes = {n.get("name"): n for n in root.iter("Window")}
    button = nodes["RoomManagerButton"]
    p = props(button)
    assert button.get("type") == "OD/GameTabButton"
    assert p["TooltipText"] == "Room Manager"
    assert p["NormalImage"] == "OpenDungeonsIcons/NavigationRooms"
    assert p["Visible"] == "False"
    assert p["NavigationFrame"] == "True" and p["AlwaysOnTop"] == "True"
    assert "Text" not in p
    assert p["Area"] == "{{0,100},{1,-224},{0,140},{1,-184}}"
    for removed in ("ProductionButton", "InfirmaryButton", "MerchantButton", "GhostHuntersButton", "LabButton"):
        # The options Production button and room construction controls are independent of the HUD row.
        assert all(n.get("name") != removed for n in root.find("Window").findall("Window")), removed
    row = {}
    for node in root.iter("Window"):
        q = props(node)
        if node.get("type") == "OD/GameTabButton" and "Area" in q:
            area = udims(q["Area"])
            if area[1] == (1.0, -224.0):
                row[node.get("name")] = area
    assert {name: area[0][1] for name, area in row.items()} == {
        "GoalsButton": 4, "ResearchButton": 52, "RoomManagerButton": 100,
        "SocialButton": 148, "WorkersButton": 196, "SandboxButton": 244}, row
    return root, nodes, row


# Screen rectangle of a window anchored like the HUD row: relative part times the screen plus the scaled offsets.
def rect(area, screen_w, screen_h, scale):
    return tuple(area[i][0] * (screen_w if i % 2 == 0 else screen_h) + area[i][1] * scale for i in range(4))


# No overlap and on screen from 640x480 to 8K at UI scale 80 to 120 percent (Gui::applyScaleToWindow).
def resolutions(root, nodes, row):
    others = dict(row)
    for name in ("MiniMap", "MainTabControl", "PanelToggleButton", "MessageQueue"):
        if name in nodes and "Area" in props(nodes[name]):
            others[name] = udims(props(nodes[name])["Area"])
    assert {"MiniMap", "MainTabControl", "PanelToggleButton", "MessageQueue"} <= set(others), sorted(others)
    checked = 0
    for screen_w, screen_h in ((640, 480), (800, 600), (1024, 768), (1280, 720), (1920, 1080), (2560, 1440),
                               (3840, 2160), (7680, 4320)):
        for user in (0.8, 1.0, 1.2):
            scale = min(screen_w / DESIGN_W, screen_h / DESIGN_H) * user
            mine = rect(row["RoomManagerButton"], screen_w, screen_h, scale)
            assert 0 <= mine[0] < mine[2] <= screen_w and 0 <= mine[1] < mine[3] <= screen_h, (screen_w, screen_h, user, mine)
            assert mine[2] - mine[0] >= 40 * 0.8 * 0.625 - 1e-6, "large enough to click at the smallest screen"
            for name, area in others.items():
                if name == "RoomManagerButton":
                    continue
                other = rect(area, screen_w, screen_h, scale)
                apart = other[2] <= mine[0] or mine[2] <= other[0] or other[3] <= mine[1] or mine[3] <= other[1]
                assert apart, ("overlaps", name, screen_w, screen_h, user)
            checked += 1
    assert checked == 24
    print("room manager button in the navigation row, no overlap at 8 screens x 3 UI scales: ok")


# The painted icon: its own atlas cell, a copy of its 256 pixel tile, the iron frame of the row tiles, a green-white trap glow.
def icon():
    imageset = read("gui/ODIcons.imageset")
    entry = re.search(r'<Image height="(\d+)" name="GhostHuntersButton" width="(\d+)" xPos="(\d+)" yPos="(\d+)" />', imageset)
    assert entry and entry.groups() == ("256", "256", "1280", "4352"), entry and entry.groups()
    assert re.search(r'name="MerchantButton" width="256"', imageset), "same size as the merchant button"
    x, y = 1280, 4352
    tile = Image.open(assets_src_dir(repo) / "gui/icons/tiles/GhostHuntersButton.png").convert("RGBA")
    assert tile.size == (256, 256)
    atlas = Image.open(repo / "gui/ODIcons.png").convert("RGBA")
    assert atlas.crop((x, y, x + 256, y + 256)).tobytes() == tile.tobytes(), "the atlas cell is the painted tile"
    # No other imageset entry shares the cell
    for other in re.finditer(r'name="(\w+)" width="(\d+)" xPos="(\d+)" yPos="(\d+)"', imageset):
        name, w, ox, oy = other.group(1), int(other.group(2)), int(other.group(3)), int(other.group(4))
        h = int(re.search(r'height="(\d+)" name="%s"' % name, imageset).group(1))
        if name != "GhostHuntersButton":
            assert ox + w <= x or x + 256 <= ox or oy + h <= y or y + 256 <= oy, ("atlas cell shared with", name)
    # The reskin frame of the row: the outer 13 pixels are the painted iron frame of the merchant tile
    frame = Image.open(assets_src_dir(repo) / "gui/icons/tiles/MerchantButton.png").convert("RGBA")
    same = total = 0
    for py in range(256):
        for px in range(256):
            if px < 13 or px > 242 or py < 13 or py > 242:
                total += 1
                same += tile.getpixel((px, py)) == frame.getpixel((px, py))
    assert same == total == 13 * 256 * 4 - 13 * 13 * 4, (same, total)
    # The motif: the green-white light of the open trap fills a clear share of the inset
    green = sum(1 for py in range(20, 236) for px in range(20, 236)
                if (lambda c: c[1] >= 110 and c[1] >= c[0] + 25 and c[1] >= c[2] + 10)(tile.getpixel((px, py))))
    assert green >= 0.08 * 216 * 216, green
    # Decision 825: painted in the row style, not a render. The free top corners of the inset are the painted cracked
    # stone of the row tiles (tiles/ItemSlotEmpty.png, the stone without a motif), and the trap carries the warm bronze
    # of the row's painted metal. The Blender render of decision 800 fails both (correlation below 0.3, bronze 0.4 %).
    stone = Image.open(assets_src_dir(repo) / "gui/icons/tiles/ItemSlotEmpty.png").convert("L")
    grey = tile.convert("L")

    def correlation(x0, y0, size=38):
        a = list(stone.crop((x0, y0, x0 + size, y0 + size)).tobytes())
        b = list(grey.crop((x0, y0, x0 + size, y0 + size)).tobytes())
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        cov = sum((u - ma) * (v - mb) for u, v in zip(a, b))
        return cov / (sum((u - ma) ** 2 for u in a) * sum((v - mb) ** 2 for v in b)) ** 0.5

    for corner in ((18, 18), (200, 18)):
        assert correlation(*corner) >= 0.85, ("painted stone inset", corner, correlation(*corner))
    bronze = sum(1 for py in range(20, 236) for px in range(20, 236)
                 if (lambda c: c[0] >= 120 and c[0] >= c[1] + 25 and c[1] >= c[2] + 10)(tile.getpixel((px, py))))
    assert bronze >= 0.02 * 216 * 216, bronze
    slots = read("assets-src/gui/icons/slots.json")
    assert re.search(r'"name": "GhostHuntersButton",\s*"width": "128",\s*"xPos": "640",\s*"yPos": "2176",\s*"source": "tiles/GhostHuntersButton.png"', slots)
    credits = read("CREDITS")
    for name in ("assets-src/gui/icons/tiles/GhostHuntersButton.png", "gui/ODIcons.png (GhostHuntersButton)"):
        assert any(row.startswith(name) and "GPLv3+" in row for row in credits.splitlines()), name
    print("ghost hunters icon: own atlas cell, iron row frame, painted stone and bronze, green-white trap light: ok")


# The ghost room keeps its tile ownership transport, while neither tiles nor figures open room controls.
def game_code():
    game = read("source/modes/GameMode.cpp")
    assert "showGhostRoomWindow(tileClicked)" not in game
    assert "tileMatchesRoomType(*tileClicked, RoomType::ghostRoom)" not in game
    # Decision 825: the click opened nothing because a human client never knew the owner of a ghost room tile
    # (findOwnGhostRoomTile compares tile->getSeat()), so the toggle had no tile to open. The server now sends the
    # owner of ghost room tiles like that of the other rooms, and always the keeper's own tiles.
    seat = strip_comments(read("source/game/Seat.cpp"))
    export = body(seat, "void Seat::exportTileToPacket(")
    owner_switch = export[export.index("switch(tileState.mTileVisual)"):export.index("default:")]
    ghost_case = owner_switch[owner_switch.index("case TileVisual::ghostRoom:"):]
    ghost_case = ghost_case[:ghost_case.index("break;")]
    has(ghost_case, "the owner of a ghost room tile is sent, the own one always", "tileSeatId = tileState.mSeatIdOwner;",
        "if(tileSeatId == -1 && tile->getSeat() == this && tile->getTileVisual() == TileVisual::ghostRoom)",
        "tileSeatId = getId();")
    update = body(seat, "void Seat::updateTileStateForSeat(")
    remembered = update[update.index("switch(jj->second.mTileVisual)"):]
    first = remembered[:remembered.index("jj->second.mSeatIdOwner = tile->getSeat()->getId();")]
    assert "case TileVisual::ghostRoom:" in first, "the ghost room owner is remembered for humans too"
    ai_only = remembered[remembered.index("case TileVisual::merchantRoom:"):]
    ai_only = ai_only[:ai_only.index("break;")]
    assert "TileVisual::ghostRoom" not in ai_only, "no longer only for AI seats"
    reader = body(strip_comments(read("source/entities/Tile.cpp")), "void Tile::updateFromPacket(")
    has(reader, "the client takes the sent owner", "Seat* seat = getGameMap()->getSeatById(seatId);", "setSeat(seat);")
    # Replay: an own ghost room tile now reaches findOwnGhostRoomTile with its seat; before, the seat was always -1
    def sent(visual, stored, own, fixed):
        if not fixed:
            return -1 if visual == "ghostRoom" else stored
        return 1 if visual == "ghostRoom" and stored == -1 and own else stored
    assert [sent("ghostRoom", -1, True, False), sent("ghostRoom", -1, True, True), sent("ghostRoom", 2, False, True),
            sent("ghostRoom", -1, False, True)] == [-1, 1, 2, -1]
    print("ghost room tile click removed and own tiles known: ok")


# One tooltip and context help line now describe the single room navigation entry point.
def merchant_and_tooltips():
    root = ET.parse(repo / "gui/ModeGame.layout").getroot()
    nodes = {n.get("name"): n for n in root.iter("Window")}
    button = nodes["RoomManagerButton"]
    assert props(button)["TooltipText"] == "Room Manager"
    help_lines = {u.get("name"): u.get("value") for u in button.findall("UserString")}
    assert help_lines.get("ContextHelp", "").startswith("Room Manager:")
    assert "case ClientNotificationType::askMerchantWindow:" in read("source/network/ODServer.cpp")
    level = read("levels/skirmish/TestGhosts.level")
    assert re.search(r"\[Room\]\n20\tMerchant1\t1\t16\n", level)
    print("room manager tooltip and merchant stock transport retained: ok")


# The start choice of decision 800, read from the code and replayed for every room research level.
def start_choice():
    seat = read("source/game/SeatData.h")
    assert "GhostProduct mGhostProduct = GhostProduct::research;" in seat, "a new game starts on the ghost press"
    assert re.search(r"enum class GhostProduct : uint32_t \{ research = 0, mana = 1, crystal = 2 \};", seat)
    room = read("source/rooms/RoomGhostRoom.cpp")
    has(body(room, "GhostProduct RoomGhostRoom::getChosenApparatus("), "a locked choice works as the mana still",
        "isApparatusUnlocked(seat,seat.getGhostProduct())?seat.getGhostProduct():GhostProduct::mana")
    has(body(room, "uint32_t RoomGhostRoom::getUnlockLevel("), "unlock levels", "kind==GhostProduct::mana?1:kind==GhostProduct::research?2:3")
    upkeep = body(room, "void RoomGhostRoom::doUpkeep(")
    # The stored choice is kept while locked; only an old save (plan constraint 4) replaces a locked choice by the mana still
    assert upkeep.count("setGhostProduct(") == 1, "the stored choice is kept while locked outside the old save conversion"
    has(upkeep, "only the old save conversion overwrites the choice",
        "if(mOldSaveChoice)",
        "if(!isApparatusUnlocked(*getSeat(),getSeat()->getGhostProduct())) getSeat()->setGhostProduct(GhostProduct::mana);")
    assert "mOldSaveChoice=getGameMap()->getSavedTurnNumber()>0;" in body(room, "bool RoomGhostRoom::importFromStream("), \
        "a new game (level file, saved turn 0) is never converted"
    ai = body(read("source/ai/AiRooms.cpp"), "void ghostProduct(KeeperAI& ai)")
    has(ai, "the AI never picks a locked apparatus and keeps the start rule",
        "if(!RoomGhostRoom::isApparatusUnlocked(*seat, product))\n        product = RoomGhostRoom::getChosenApparatus(*seat);")
    assert "product = GhostProduct::mana;" in ai and ai.count("product = GhostProduct::mana;") == 1, "mana only for scarce mana"
    # Replay: unlock level 1 mana still, 2 ghost press, 3 soul forge; a new game stores the ghost press
    unlock = {"mana": 1, "research": 2, "crystal": 3}
    chosen = lambda stored, level: stored if level >= unlock[stored] else "mana"
    assert [chosen("research", level) for level in (0, 1, 2, 3)] == ["mana", "mana", "research", "research"]
    # An old save with a locked soul forge stores the mana still after loading (plan constraint 4); it then stays there
    stored = lambda choice, level: "mana" if level < unlock[choice] else choice
    assert [chosen(stored("crystal", level), level) for level in (1, 2, 3)] == ["mana", "mana", "crystal"]
    assert [stored("crystal", level) for level in (1, 2, 3)] == ["mana", "mana", "crystal"]
    print("start choice: ghost press when unlocked, mana still until then: ok")


def main():
    root, nodes, row = layout_button()
    resolutions(root, nodes, row)
    icon()
    game_code()
    merchant_and_tooltips()
    start_choice()
    print("ghost room manager integration: ok")


if __name__ == "__main__":
    main()
