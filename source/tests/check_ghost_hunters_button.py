"""Check the ghost hunters button, the removed ghost room tile click and the start choice without compiling
(GHOST-APPARATUS-PLAN G2, owner decision 800).

- The ghost room window is opened only by its own icon button GhostHuntersButton in the icon row above the minimap,
  directly next to MerchantButton, shown while the keeper owns a ghost room, tooltip "Ghost hunters", its painted icon a
  capture trap in the reskin frame of the row; it stays on screen and overlaps nothing from 640x480 to 8K at UI scale
  80 to 120 percent.
- Clicking a ghost room tile no longer opens the window.
- A new game starts on the apparatus that makes research points (the ghost press) when it is unlocked, otherwise on the
  mana still until it is; the stored choice is never overwritten while it is locked, and the AI follows the same rule.
Expected values are fixed, counted once on this branch. Every part fails on base 636e678c8 (no button, the tile click
branch, the mana still start rule)."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image

repo = Path(__file__).resolve().parents[2]
DESIGN_W, DESIGN_H = 1024.0, 768.0


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


# Return the properties of a layout window.
def props(node):
    return {p.get("name"): p.get("value") for p in node.findall("Property")}


# Parse a CEGUI area into four (scale, offset) pairs.
def udims(value):
    return [(float(a), float(b)) for a, b in re.findall(r"\{([-\d.]+),([-\d.]+)\}", value)]


# The button in the layout: its kind, picture, tooltip and place next to the merchant button.
def layout_button():
    gui = read("source/render/Gui.cpp")
    assert float(re.search(r"LAYOUT_DESIGN_WIDTH = ([0-9.]+)f", gui)[1]) == DESIGN_W
    assert float(re.search(r"LAYOUT_DESIGN_HEIGHT = ([0-9.]+)f", gui)[1]) == DESIGN_H
    root = ET.parse(repo / "gui/ModeGame.layout").getroot()
    nodes = {n.get("name"): n for n in root.iter("Window")}
    button = nodes["GhostHuntersButton"]
    p = props(button)
    assert button.get("type") == "OD/GameTabButton", "an icon button like the merchant button"
    assert p["TooltipText"] == "Ghost hunters"
    assert p["NormalImage"] == "OpenDungeonsIcons/GhostHuntersButton"
    assert p["Visible"] == "False", "hidden until the keeper owns a ghost room"
    assert p["NavigationFrame"] == "True" and p["AlwaysOnTop"] == "True"
    assert "Text" not in p, "the icon button draws no text"
    # Fixed place: the slot right of the merchant button in the icon row above the minimap
    assert p["Area"] == "{{0,340},{1,-224},{0,380},{1,-184}}", p["Area"]
    merchant = udims(props(nodes["MerchantButton"])["Area"])
    mine = udims(p["Area"])
    assert mine[0][1] == merchant[2][1] + 8 and mine[1] == merchant[1] and mine[3] == merchant[3], "next to the merchant button"
    # The whole row: every icon on its own 48 unit slot, ten icons, the alchemy lab and sandbox icons moved one slot on
    row = {}
    for node in root.iter("Window"):
        q = props(node)
        if node.get("type") == "OD/GameTabButton" and "Area" in q:
            area = udims(q["Area"])
            if area[1] == (1.0, -224.0):
                row[node.get("name")] = area
    assert {name: area[0][1] for name, area in row.items()} == {
        "GoalsButton": 4, "ResearchButton": 52, "ProductionButton": 100, "SocialButton": 148, "WorkersButton": 196,
        "InfirmaryButton": 244, "MerchantButton": 292, "GhostHuntersButton": 340, "LabButton": 388,
        "SandboxButton": 436}, row
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
            mine = rect(row["GhostHuntersButton"], screen_w, screen_h, scale)
            assert 0 <= mine[0] < mine[2] <= screen_w and 0 <= mine[1] < mine[3] <= screen_h, (screen_w, screen_h, user, mine)
            assert mine[2] - mine[0] >= 40 * 0.8 * 0.625 - 1e-6, "large enough to click at the smallest screen"
            for name, area in others.items():
                if name == "GhostHuntersButton":
                    continue
                other = rect(area, screen_w, screen_h, scale)
                apart = other[2] <= mine[0] or mine[2] <= other[0] or other[3] <= mine[1] or mine[3] <= other[1]
                assert apart, ("overlaps", name, screen_w, screen_h, user)
            checked += 1
    assert checked == 24
    print("ghost hunters button next to the merchant button, no overlap at 8 screens x 3 UI scales: ok")


# The painted icon: its own atlas cell, a copy of its 256 pixel tile, the iron frame of the row tiles, a green-white trap glow.
def icon():
    imageset = read("gui/ODIcons.imageset")
    entry = re.search(r'<Image height="(\d+)" name="GhostHuntersButton" width="(\d+)" xPos="(\d+)" yPos="(\d+)" />', imageset)
    assert entry and entry.groups() == ("256", "256", "1280", "4352"), entry and entry.groups()
    assert re.search(r'name="MerchantButton" width="256"', imageset), "same size as the merchant button"
    x, y = 1280, 4352
    tile = Image.open(repo / "assets-src/gui/icons/tiles/GhostHuntersButton.png").convert("RGBA")
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
    frame = Image.open(repo / "assets-src/gui/icons/tiles/MerchantButton.png").convert("RGBA")
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
    slots = read("assets-src/gui/icons/slots.json")
    assert re.search(r'"name": "GhostHuntersButton",\s*"width": "128",\s*"xPos": "640",\s*"yPos": "2176",\s*"source": "tiles/GhostHuntersButton.png"', slots)
    credits = read("CREDITS")
    for name in ("assets-src/gui/icons/tiles/GhostHuntersButton.png", "gui/ODIcons.png (GhostHuntersButton)"):
        assert any(row.startswith(name) and "GPLv3+" in row for row in credits.splitlines()), name
    print("ghost hunters icon: own atlas cell, iron row frame, green-white trap light: ok")


# The game code: the button opens the window like the merchant button, follows the ghost rooms, and the tile click is gone.
def game_code():
    game = read("source/modes/GameMode.cpp")
    has(game, "the button opens and closes the window",
        'guiSheet->getChild("GhostHuntersButton")->subscribeEvent(\n        CEGUI::PushButton::EventClicked, CEGUI::Event::Subscriber(&GameMode::toggleGhostRoomWindow, this)));')
    toggle = body(game, "bool GameMode::toggleGhostRoomWindow(")
    has(toggle, "toggle like the merchant window", 'if(mRootWindow->getChild("GhostRoomWindow")->isVisible())\n        return hideGhostRoomWindow();',
        "player->getSeat()->getNbRooms(RoomType::ghostRoom) == 0)", "showGhostRoomWindow(findOwnGhostRoomTile());")
    frame = body(game, "void GameMode::onFrameStarted(")
    has(frame, "the button follows the keeper's ghost rooms",
        "merchantPlayer->getSeat()->getNbRooms(RoomType::ghostRoom) > 0;",
        'mRootWindow->getChild("GhostHuntersButton")->setVisible(hasGhostRoom);',
        'if(!hasGhostRoom && mRootWindow->getChild("GhostRoomWindow")->isVisible()) hideGhostRoomWindow();')
    has(game, "hidden at mode start", 'guiSheet->getChild("GhostHuntersButton")->hide();')
    find = body(game, "Tile* GameMode::findOwnGhostRoomTile() const")
    has(find, "an own ghost room tile, the remembered one first",
        "tileMatchesRoomType(*remembered, RoomType::ghostRoom)", "tile->getSeat() == player->getSeat() && tileMatchesRoomType(*tile, RoomType::ghostRoom)")
    refresh = body(game, "void GameMode::refreshGhostRoomWindow()")
    has(refresh, "a lost room hands the window on", "Tile* tile = findOwnGhostRoomTile();", "mGhostRoomX = tile->getX();")
    has(read("source/modes/GameMode.h"), "declarations", "bool toggleGhostRoomWindow(const CEGUI::EventArgs& = {});",
        "Tile* findOwnGhostRoomTile() const;")
    # The click on a ghost room tile is removed: the window opens from the toggle only
    assert "tileMatchesRoomType(*tileClicked, RoomType::ghostRoom)" not in game, "no ghost room tile click"
    assert "showGhostRoomWindow(tileClicked)" not in game, "no ghost room tile click"
    assert len(re.findall(r"\bshowGhostRoomWindow\(", game)) == 2, "only the definition and the toggle"
    print("button opens the window, follows the ghost rooms, tile click removed: ok")


# The start choice of decision 800, read from the code and replayed for every room research level.
def start_choice():
    seat = read("source/game/SeatData.h")
    assert "GhostProduct mGhostProduct = GhostProduct::research;" in seat, "a new game starts on the ghost press"
    assert re.search(r"enum class GhostProduct : uint32_t \{ research = 0, mana = 1, crystal = 2 \};", seat)
    room = read("source/rooms/RoomGhostRoom.cpp")
    has(body(room, "GhostProduct RoomGhostRoom::getChosenApparatus("), "a locked choice works as the mana still",
        "isApparatusUnlocked(seat,seat.getGhostProduct())?seat.getGhostProduct():GhostProduct::mana")
    has(body(room, "uint32_t RoomGhostRoom::getUnlockLevel("), "unlock levels", "kind==GhostProduct::mana?1:kind==GhostProduct::research?2:3")
    assert "setGhostProduct(" not in body(room, "void RoomGhostRoom::doUpkeep("), "the stored choice is kept while locked"
    ai = body(read("source/ai/AiRooms.cpp"), "void ghostProduct(KeeperAI& ai)")
    has(ai, "the AI never picks a locked apparatus and keeps the start rule",
        "if(!RoomGhostRoom::isApparatusUnlocked(*seat, product))\n        product = RoomGhostRoom::getChosenApparatus(*seat);")
    assert "product = GhostProduct::mana;" in ai and ai.count("product = GhostProduct::mana;") == 1, "mana only for scarce mana"
    # Replay: unlock level 1 mana still, 2 ghost press, 3 soul forge; a new game stores the ghost press
    unlock = {"mana": 1, "research": 2, "crystal": 3}
    chosen = lambda stored, level: stored if level >= unlock[stored] else "mana"
    assert [chosen("research", level) for level in (0, 1, 2, 3)] == ["mana", "mana", "research", "research"]
    # An old save keeps its stored choice: a locked soul forge works as the mana still until room research 3
    assert [chosen("crystal", level) for level in (1, 2, 3)] == ["mana", "mana", "crystal"]
    print("start choice: ghost press when unlocked, mana still until then: ok")


def main():
    root, nodes, row = layout_button()
    resolutions(root, nodes, row)
    icon()
    game_code()
    start_choice()
    print("ghost hunters button: ok")


if __name__ == "__main__":
    main()
