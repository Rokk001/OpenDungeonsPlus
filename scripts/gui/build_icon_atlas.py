#!/usr/bin/env python3
"""Assemble the painted icon slots and existing runtime navigation images."""

import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets-src/gui/icons"
SKIN = ROOT / "assets-src/gui/skin"
NAVIGATION_RECTS = {
    "MiniMapRim": (0, 0, 768, 768),
    "ManaBadge": (768, 0, 256, 256),
    "GoldBadge": (768, 256, 256, 256),
    "MiniMapNorth": (768, 512, 128, 128),
    "NavHelp": (768, 640, 128, 128),
    "NavSell": (896, 512, 128, 128),
    "NavOptions": (896, 640, 128, 128),
    "MapZoom": (0, 768, 128, 128),
}


# Cut one exact source-grid cell, retaining its original painted alpha.
def source_cell(sheet, index):
    col, row = index % 4, index // 4
    return sheet.crop((col * sheet.width // 4, row * sheet.height // 4,
                       (col + 1) * sheet.width // 4, (row + 1) * sheet.height // 4))


# Fit an isolated painted sprite without distorting its silhouette.
def fit_sprite(sprite, size):
    bounds = sprite.getbbox()
    if bounds:
        sprite = sprite.crop(bounds)
    sprite.thumbnail((size, size), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", (size, size))
    result.alpha_composite(sprite, ((size - sprite.width) // 2, (size - sprite.height) // 2))
    return result


# Keep only the existing circular well when combining painted medallion pieces.
def circular_part(sprite, radius):
    result = sprite.copy()
    alpha = result.getchannel("A")
    pixels = alpha.load()
    centre = sprite.width * 0.5
    for y in range(sprite.height):
        for x in range(sprite.width):
            distance = math.hypot(x + 0.5 - centre, y + 0.5 - centre)
            coverage = min(1.0, max(0.0, radius * centre - distance + 0.5))
            pixels[x, y] = round(pixels[x, y] * coverage)
    result.putalpha(alpha)
    return result


# Use the quiet ring with an isolated heart or a painted gold centre, never baked health segments.
def badge_sprite(sprite, ring, heart=False):
    result = ring.resize((256, 256), Image.Resampling.LANCZOS)
    if heart:
        well = Image.new("RGBA", (256, 256))
        well.alpha_composite(fit_sprite(sprite, 154), (51, 51))
    else:
        well = circular_part(fit_sprite(sprite, 256), 0.795)
    result.alpha_composite(well)
    return result


# Preserve the established minimap corner hit geometry while cutting the painted plates.
def corner_plate(corner, state):
    result = Image.open(SKIN / f"frame-0-{state}.png").convert("RGBA").resize((256, 256), Image.Resampling.LANCZOS)
    alpha = result.getchannel("A")
    pixels = alpha.load()
    for y in range(256):
        for x in range(256):
            screen_x = (x + 0.5) * 44.0 / 256
            screen_y = (y + 0.5) * 44.0 / 256
            u = 44.0 - screen_x if corner & 1 else screen_x
            v = 44.0 - screen_y if corner & 2 else screen_y
            distance = math.hypot(u - 88.0, v - 88.0)
            coverage = min(1.0, max(0.0, (distance - 88.0) * 256 / 44.0 + 0.5))
            pixels[x, y] = round(pixels[x, y] * coverage)
    result.putalpha(alpha)
    return result


# Write the source rectangles in the CEGUI schema without changing their registered names.
def write_imageset(path, imagefile, name, entries):
    root = ET.Element("Imageset", autoScaled="true", imagefile=imagefile, name=name,
                      nativeHorzRes="2048", nativeVertRes="1536", version="2")
    for attrs in entries:
        ET.SubElement(root, "Image", attrs)
    ET.indent(root, space="    ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


# Rebuild all original slots at twice their source resolution and the navigation source atlas.
def main():
    slots = json.loads((SOURCE / "slots.json").read_text(encoding="utf-8"))
    sheets = [Image.open(SOURCE / f"icons-{i}.png").convert("RGBA") for i in range(1, 8)]
    (SOURCE / "tiles").mkdir(exist_ok=True)
    (SOURCE / "navigation").mkdir(exist_ok=True)
    atlas = Image.new("RGBA", (2048, 2560))
    entries = []
    for index, slot in enumerate(slots):
        attrs = dict(slot)
        for key in ("xPos", "yPos", "width", "height", "xOffset", "yOffset"):
            if key in attrs:
                attrs[key] = str(int(attrs[key]) * 2)
        tile = source_cell(sheets[index // 16], index % 16).resize(
            (int(attrs["width"]), int(attrs["height"])), Image.Resampling.LANCZOS)
        if slot["name"] == "MapLightButton":
            source = Image.open(SOURCE / "overrides/MapLightButton.png").convert("RGBA")
            tile = Image.new("RGBA", (int(attrs["width"]), int(attrs["height"])))
            lantern = fit_sprite(source, int(attrs["width"]) * 4 // 5)
            tile.alpha_composite(lantern, ((tile.width - lantern.width) // 2, (tile.height - lantern.height) // 2))
        tile.save(SOURCE / "tiles" / (slot["name"] + ".png"))
        atlas.paste(tile, (int(attrs["xPos"]), int(attrs["yPos"])))
        entries.append(attrs)
    atlas.save(ROOT / "gui/ODIcons.png")
    write_imageset(ROOT / "gui/ODIcons.imageset", "ODIcons.png", "OpenDungeonsIcons", entries)

    navigation = Image.new("RGBA", (2048, 2048))
    ring = Image.open(SKIN / "glyph-3-3.png").convert("RGBA")
    ring = ring.crop(ring.getbbox())
    sprites = {"MiniMapRim": ring.resize((768, 768), Image.Resampling.LANCZOS)}
    source_names = ("ManaBadge", "GoldBadge", "NavHelp", "NavSell", "NavOptions", "MapZoom", "MiniMapNorth")
    for index, name in enumerate(source_names):
        source = source_cell(sheets[6], index + 3)
        if name == "ManaBadge":
            source = Image.open(SOURCE / "overrides/ManaBadge.png").convert("RGBA")
            sprite = badge_sprite(source, ring, heart=True)
        elif name == "GoldBadge":
            sprite = badge_sprite(source, ring)
        else:
            sprite = fit_sprite(source, 128)
            if name == "MiniMapNorth":
                sprite = circular_part(sprite, 0.76)
        sprites[name] = sprite
    for corner in range(4):
        for state, suffix in enumerate(("", "Hover", "Pressed")):
            name = f"MiniMapCorner{corner}{suffix}"
            NAVIGATION_RECTS[name] = (1024 + corner * 256, state * 256, 256, 256)
            sprites[name] = corner_plate(corner, state)
    nav_entries = []
    for name, sprite in sprites.items():
        x, y, width, height = NAVIGATION_RECTS[name]
        sprite.save(SOURCE / "navigation" / (name + ".png"))
        navigation.paste(sprite, (x, y))
        nav_entries.append({"name": name, "xPos": str(x), "yPos": str(y), "width": str(width), "height": str(height)})
    navigation.save(ROOT / "gui/ODNavigation.png")
    write_imageset(ROOT / "gui/ODNavigation.imageset", "ODNavigation.png", "OpenDungeonsNavigation", nav_entries)
    print(f"Painted icons: {len(slots)} slots at 2048x2560; navigation: {len(sprites)} sprites at 2048x2048")


if __name__ == "__main__":
    main()
