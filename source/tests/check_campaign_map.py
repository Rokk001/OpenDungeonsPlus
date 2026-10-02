"""Static checks of the campaign map (layout, menu code and the map data of the campaign definition).

Run from any directory. It does not start a game.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
layout = ET.fromstring((root / "gui/MenuCampaign.layout").read_text(encoding="utf-8"))
mode = (root / "source/modes/MenuModeCampaign.cpp").read_text(encoding="utf-8")
campaign_cpp = (root / "source/game/Campaign.cpp").read_text(encoding="utf-8")
definition = (root / "levels/campaign/Campaign.cfg").read_text(encoding="utf-8")
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


windows = {w.get("name"): w for w in layout.iter("Window")}

# Every window the campaign page code looks up exists in the layout; the level list is gone
for path in re.findall(r'const std::string CMP_\w+ = "CampaignWindowFrame/(\w+)";', mode):
    check(path in windows, "missing in layout: " + path)
check("LoadingText" in windows, "missing in layout: LoadingText")
check("LevelSelect" not in windows, "the level list must be replaced by the map")
check("DifficultyButton" in windows, "the difficulty button must stay")

# Only levels that can be started react to the mouse; the others let it pass
fill = mode[mode.index("void MenuModeCampaign::fillMap"):mode.index("void MenuModeCampaign::updateTerritoryColour")]
check(re.search(r"if\(startable\)\s*\{[^}]*EventMouseEntersArea[^}]*EventMouseLeavesArea[^}]*EventMouseClick", fill, re.S),
      "hover and click handlers must only be connected for levels that can be started")
check("setMousePassThroughEnabled(true)" in fill, "levels that cannot be started must not react to the mouse")
check("level.mBonus && !campaign.isUnlocked(i)" in fill, "hidden bonus levels must not be drawn")
colour = mode[mode.index("void MenuModeCampaign::updateTerritoryColour"):mode.index("bool MenuModeCampaign::territoryEntered")]
check(all(token in colour for token in ["COLOUR_LOCKED", "COLOUR_HOVER", "COLOUR_COMPLETED", "COLOUR_AVAILABLE"]),
      "locked, hovered, completed and available territories need their own colour")
check("startLevel(" in mode[mode.index("bool MenuModeCampaign::territoryClicked"):], "a click must start the level")
check('key == "Map"' in campaign_cpp, "the campaign definition reader must know the Map setting")

# Map data: every level has blocks inside the map and the territories of different levels do not overlap
levels = []
for part in definition.replace("\r", "").split("[Level]")[1:]:
    fields = dict(line.split("=", 1) for line in part.splitlines() if "=" in line and not line.startswith("#"))
    blocks = []
    for text in fields.get("Map", "").split(";"):
        if text.strip():
            blocks.append([float(v) for v in text.split(",")])
    if "File" in fields:
        levels.append((fields["File"], blocks))
check(len(levels) > 0, "no levels in the campaign definition")
for name, blocks in levels:
    check(len(blocks) > 0, name + " has no Map setting")
    for x, y, w, h in blocks:
        check(x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= 100 and y + h <= 100, name + " has a block outside the map")
for i, (name_a, blocks_a) in enumerate(levels):
    for name_b, blocks_b in levels[i + 1:]:
        for ax, ay, aw, ah in blocks_a:
            for bx, by, bw, bh in blocks_b:
                overlap = ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
                check(not overlap, name_a + " and " + name_b + " overlap on the map")

# The map is an image, the territories are tinted images sized by width and height (not by their far corner)
gui_cpp = (root / "source/render/Gui.cpp").read_text(encoding="utf-8")
props = {p.get("name"): p.get("value") for p in windows["CampaignMap"].iter("Property")}
check(windows["CampaignMap"].get("type") == "OD/StaticImage", "the map must be an image window")
check(props.get("Image") == "OpenDungeonsIcons/CampaignMap", "the map window needs the map image")
check('"OpenDungeonsIcons/CampaignMap"' in gui_cpp and '"OpenDungeonsIcons/CampaignSolid"' in gui_cpp,
      "the map and tint images must be created in Gui.cpp")
check("block.mX + block.mWidth" not in fill, "the territory area must use width and height, not the far corner")
check('"ImageColours"' in colour, "territories are tinted through ImageColours")

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("campaign map checks passed")
