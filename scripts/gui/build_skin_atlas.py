#!/usr/bin/env python3
"""Assemble the painted skin sources without changing their design-pixel sizes."""

import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "assets-src/gui/skin"
SCALE = 4
STATES = {"Hover": 1, "Pushed": 2, "Disabled": 3}
PIECES = {
    "TopLeft": (0, 0, 88, 88), "TopRight": (424, 0, 512, 88),
    "BottomLeft": (0, 424, 88, 512), "BottomRight": (424, 424, 512, 512),
    "Top": (88, 0, 424, 88), "Bottom": (88, 424, 424, 512),
    "Left": (0, 88, 88, 424), "Right": (424, 88, 512, 424),
    "Middle": (88, 88, 424, 424), "Whole": (0, 0, 512, 512),
}


# Split the generated grid into separately committed frame and glyph source tiles.
def extract_tiles():
    for filename, prefix in (("frames.png", "frame"), ("glyphs.png", "glyph")):
        sheet = Image.open(SOURCES / filename).convert("RGBA")
        for row in range(4):
            for col in range(4):
                box = (col * sheet.width // 4, row * sheet.height // 4,
                       (col + 1) * sheet.width // 4, (row + 1) * sheet.height // 4)
                tile = sheet.crop(box).resize((512, 512), Image.Resampling.LANCZOS)
                tile.save(SOURCES / f"{prefix}-{row}-{col}.png")
    sheet = Image.open(SOURCES / "controls.png").convert("RGBA")
    # The painter left extra transparent space above the first row; use actual sprite bounds.
    for row, (top, bottom) in enumerate(((170, 415), (460, 735), (750, 985), (1035, 1135))):
        for col in range(4):
            box = (col * sheet.width // 4, top * sheet.height // 1254,
                   (col + 1) * sheet.width // 4, bottom * sheet.height // 1254)
            sheet.crop(box).save(SOURCES / f"control-{row}-{col}.png")


# Return the physical painted state, retaining the existing image naming contracts.
def image_state(name):
    if "__" in name and name.rsplit("__", 1)[1] in STATES:
        return STATES[name.rsplit("__", 1)[1]]
    if "Disabled" in name or "Locked" in name:
        return 3
    if any(word in name for word in ("Pushed", "Pressed", "Working")):
        return 2
    if any(word in name for word in ("Hover", "Highlight", "Selected", "Focus", "Learned")):
        return 1
    return 0


# Select the source family and actual asymmetric corner or edge of a named slice.
def frame_recipe(name):
    name = name.split("__", 1)[0]
    family = 3 if any(x in name for x in ("Button", "Thumb", "ResearchTile", "Checkbox", "IconSlot")) else 2
    if name.startswith(("Window", "TitleBar", "SysArea", "Menu", "PopupMenuFrame")):
        family = 1
    if name.startswith(("Forged", "HorizontalPipe", "VerticalPipe", "HudPlate")):
        family = 0
    plain = re.sub(r"Normal|Highlight|Hover|Pushed|Pressed|Selected", "", name)
    plain = plain.replace("Upper", "Top").replace("Lower", "Bottom")
    for piece in ("TopLeft", "TopRight", "BottomLeft", "BottomRight", "Top", "Bottom", "Left", "Right"):
        if piece in plain:
            return family, piece
    if any(x in plain for x in ("Middle", "Backdrop", "Background", "Brush", "Segment")):
        return family, "Middle"
    return family, "Whole"


# Identify glyphs whose silhouettes must survive the repaint rather than become panels.
def glyph_index(name):
    if name == "CheckboxMark":
        return 0
    if name.startswith("CloseButton"):
        return 1
    if name.startswith("RadioButton"):
        return 8 if name.endswith("Mark") else 9
    if name in ("ProgressBarLitSegment", "AltProgressBarLight"):
        return 10
    if name == "SelectionBrush":
        return 11
    if name == "MouseArrow":
        return 12
    if name in ("MouseTextBar", "EditBoxCaret"):
        return 13
    if name.startswith("Mouse"):
        return 14
    if name in ("OrbRing", "MinimapRing"):
        return 15
    if any(x in name for x in ("Scroll", "Spinner", "Sort", "PopupMenuArrow")) and "Thumb" not in name:
        for word, index in (("Up", 4), ("Down", 5), ("Left", 6), ("Right", 7)):
            if word in name:
                return index
    return None


# Mirror four stone quadrants so opposing centre-tile boundaries meet without seams.
def seamless_stone():
    tile = Image.open(SOURCES / "stone.png").convert("RGBA").resize((256, 256), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", (512, 512))
    result.paste(tile, (0, 0))
    result.paste(tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (256, 0))
    result.paste(tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM), (0, 256))
    result.paste(tile.transpose(Image.Transpose.ROTATE_180), (256, 256))
    return result


# Cut painted sprites and frame parts; no procedural drawing substitutes for the artwork.
def render_tile(name, size, stone):
    base = name.split("__", 1)[0]
    state = image_state(name)
    family, piece = frame_recipe(base)
    frame = Image.open(SOURCES / f"frame-{family}-{state}.png").convert("RGBA")
    glyph = glyph_index(base)
    if glyph is not None:
        sprite = Image.open(SOURCES / f"glyph-{glyph // 4}-{glyph % 4}.png").convert("RGBA")
        control = None
        if base.startswith("RadioButton"):
            control = 1 if base.endswith("Mark") else 0
        elif base == "CheckboxMark":
            control = 2
        elif base in ("ProgressBarLitSegment", "AltProgressBarLight"):
            control = 3
        if control is not None:
            sprite = Image.open(SOURCES / f"control-{control}-{state}.png").convert("RGBA")
        bounds = sprite.getbbox()
        if bounds:
            sprite = sprite.crop(bounds)
        if base == "ProgressBarLitSegment":
            sprite = sprite.crop((0, 0, sprite.width // 5, sprite.height))
        if base.startswith("CloseButton") or ("Scroll" in base and "Thumb" not in base) or base.startswith("Spinner"):
            result = frame.resize(size, Image.Resampling.LANCZOS)
            sprite.thumbnail((max(1, size[0] * 3 // 5), max(1, size[1] * 3 // 5)), Image.Resampling.LANCZOS)
            result.alpha_composite(sprite, ((size[0] - sprite.width) // 2, (size[1] - sprite.height) // 2))
            return result
        return sprite.resize(size, Image.Resampling.LANCZOS)
    if base in ("ButtonFrame", "ButtonHoverEffect", "ButtonPushedEffect", "ButtonDisabledEffect") or base.startswith("ResearchTile"):
        frame.paste((0, 0, 0, 0), PIECES["Middle"])
    if piece == "Middle" and not base.startswith(("TitleBar", "SysArea")):
        return stone.resize(size, Image.Resampling.LANCZOS)
    if base.startswith("TitleBar") or base.startswith("SysArea"):
        end = "TopLeft" if base.endswith("Left") else "TopRight" if base.endswith("Right") else "Top"
        return frame.crop(PIECES[end]).resize(size, Image.Resampling.LANCZOS)
    if base == "ForgedBar":
        return frame.crop((0, 0, 512, 88)).resize(size, Image.Resampling.LANCZOS)
    box = PIECES[piece]
    # Two separately damaged stretches of each painted edge avoid repeating the same chips.
    if piece in ("Top", "Bottom"):
        left, top, right, bottom = box
        middle = (left + right) // 2
        box = (middle, top, right, bottom) if "__Edge2" in name else (left, top, middle, bottom)
    elif piece in ("Left", "Right"):
        left, top, right, bottom = box
        middle = (top + bottom) // 2
        box = (left, middle, right, bottom) if "__Edge2" in name else (left, top, right, middle)
    return frame.crop(box).resize(size, Image.Resampling.LANCZOS)


# Place all rectangles in a deterministic skyline, sharing identical source recipes.
def pack_tiles(tiles):
    skyline = [(0, 0, 2048)]
    placements = {}
    for name, tile in sorted(tiles.items(), key=lambda item: (-item[1].height, -item[1].width, item[0])):
        width, height = tile.size
        candidates = []
        for index, (x, y, _) in enumerate(skyline):
            if x + width > 2048:
                continue
            span, top, end = 0, y, index
            while span < width and end < len(skyline):
                top = max(top, skyline[end][1])
                span += skyline[end][2]
                end += 1
            if span >= width and top + height <= 2048:
                candidates.append((top + height, x, index, top))
        if not candidates:
            raise ValueError(f"Painted atlas exceeds 2048x2048 at {name}")
        _, x, index, y = min(candidates)
        right = x + width
        remainder = []
        for sx, sy, sw in skyline:
            if sx + sw <= x or sx >= right:
                remainder.append((sx, sy, sw))
            elif sx + sw > right:
                remainder.append((right, sy, sx + sw - right))
        remainder.append((x, y + height, width))
        skyline = sorted(remainder)
        placements[name] = (x, y)
    return placements


# Build the atlas, image rectangles and doubled HUD surface from committed source PNGs.
def main():
    extract_tiles()
    slots = json.loads((SOURCES / "slots.json").read_text(encoding="utf-8"))
    definitions = {entry["name"]: entry for entry in slots}
    # Complete named nine-slice sets remain available for each shared frame role.
    families = ("HudPlate", "WindowFrame", "InsetPanel", "Button", "TabButton", "Checkbox",
                "Combobox", "EditBox", "Listbox", "ScrollbarTrack", "ScrollbarThumb",
                "ProgressBar", "Tooltip", "IconSlot")
    for family in families:
        for piece in PIECES:
            if piece == "Whole":
                continue
            width = 32 if piece in ("Top", "Bottom", "Middle") else 8
            height = 32 if piece in ("Left", "Right", "Middle") else 8
            base = family + piece
            for suffix in ("", "__Hover", "__Pushed", "__Disabled"):
                name = base + suffix
                if name not in definitions:
                    definitions[name] = {"name": name, "width": str(width), "height": str(height)}
                if piece in ("Top", "Bottom", "Left", "Right"):
                    definitions[base + "__Edge2" + suffix] = dict(definitions[name], name=base + "__Edge2" + suffix)
    for entry in slots:
        name = entry["name"]
        if frame_recipe(name)[1] in ("Top", "Bottom", "Left", "Right") and glyph_index(name) is None:
            definitions[name + "__Edge2"] = dict(entry, name=name + "__Edge2")
    look = (ROOT / "gui/OD.looknfeel").read_text(encoding="utf-8")
    for name in sorted(set(re.findall(r"OpenDungeonsSkin/([A-Za-z0-9_]+)", look))):
        if "__" in name:
            definitions[name] = dict(definitions[name.split("__", 1)[0]], name=name)
    for name, dimension in (("OrbRing", 256), ("MinimapRing", 512)):
        definitions[name] = {"name": name, "width": str(dimension // SCALE), "height": str(dimension // SCALE)}
    stone = seamless_stone()
    tiles, aliases, recipes = {}, {}, {}
    for name, entry in definitions.items():
        size = (int(entry["width"]) * SCALE, int(entry["height"]) * SCALE)
        recipe = (frame_recipe(name), image_state(name), glyph_index(name.split("__", 1)[0]), size, "__Edge2" in name)
        base = name.split("__", 1)[0]
        # Shared seamless centres need one rectangle per size, while painted rims retain their states.
        if frame_recipe(name)[1] == "Middle" and glyph_index(base) is None and not base.startswith(("TitleBar", "SysArea")):
            recipe = ("stone", size)
        # Whole frames have different compositing semantics, so retain their names.
        if base in ("ButtonFrame", "ButtonHoverEffect", "ButtonPushedEffect", "ButtonDisabledEffect", "ForgedBar") or base.startswith(("TitleBar", "SysArea", "ResearchTile")):
            recipe += (name.split("__", 1)[0],)
        if recipe in recipes:
            aliases[name] = recipes[recipe]
        else:
            recipes[recipe] = name
            tiles[name] = render_tile(name, size, stone)
    positions = pack_tiles(tiles)
    atlas = Image.new("RGBA", (2048, 2048))
    for name, tile in tiles.items():
        atlas.paste(tile, positions[name])
    atlas.save(ROOT / "gui/ODSkin.png")
    imageset = ET.Element("Imageset", autoScaled="true", imagefile="ODSkin.png", name="OpenDungeonsSkin",
                          nativeHorzRes="3200", nativeVertRes="2400", version="2")
    for name, entry in definitions.items():
        actual = aliases.get(name, name)
        x, y = positions[actual]
        attrs = {"name": name, "xPos": str(x), "yPos": str(y),
                 "width": str(int(entry["width"]) * SCALE), "height": str(int(entry["height"]) * SCALE)}
        for offset in ("xOffset", "yOffset"):
            if offset in entry:
                attrs[offset] = str(int(entry[offset]) * SCALE)
        ET.SubElement(imageset, "Image", attrs)
    ET.indent(imageset, space="    ")
    ET.ElementTree(imageset).write(ROOT / "gui/ODSkin.imageset", encoding="utf-8", xml_declaration=True)
    Image.open(SOURCES / "stone.png").convert("RGBA").resize((3548, 1774), Image.Resampling.LANCZOS).save(ROOT / "gui/ODHudSurface.png")
    hud = ET.Element("Imageset", autoScaled="true", imagefile="ODHudSurface.png", name="ODHudSurface",
                     nativeHorzRes="2048", nativeVertRes="1536", version="2")
    ET.SubElement(hud, "Image", name="Stone", xPos="0", yPos="0", width="3548", height="1774")
    ET.indent(hud, space="    ")
    ET.ElementTree(hud).write(ROOT / "gui/ODHudSurface.imageset", encoding="utf-8", xml_declaration=True)
    print(f"Painted skin: {len(definitions)} named images, 2048x2048; HUD Stone: 3548x1774")


if __name__ == "__main__":
    main()
