#!/usr/bin/env python3
"""Pack the original item, potion and herb icons into their CEGUI imageset."""

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image


ICON_SIZE = 128
ATLAS_COLUMNS = 16
SOURCE_DIRECTORIES = ("items", "potions", "herbs")
EXPECTED_ICON_COUNT = 768


def build_imageset(root):
    """Pack all required transparent icons and write their named atlas entries."""
    gui = root / "gui"
    sources = sorted(path for directory in SOURCE_DIRECTORIES
                     for path in (gui / directory).glob("*.png"))
    if len(sources) != EXPECTED_ICON_COUNT:
        raise ValueError("Expected {} icons, found {}".format(EXPECTED_ICON_COUNT, len(sources)))
    names = [path.stem for path in sources]
    if len(set(names)) != len(names):
        raise ValueError("Item images must have distinct names")
    rows = int(math.ceil(len(sources) / ATLAS_COLUMNS))
    atlas = Image.new("RGBA", (ATLAS_COLUMNS * ICON_SIZE, rows * ICON_SIZE), (0, 0, 0, 0))
    imageset = ET.Element("Imageset", {"autoScaled": "false", "imagefile": "Items.png",
                                     "name": "ItemImages", "nativeHorzRes": "1024",
                                     "nativeVertRes": "768", "version": "2"})
    for index, path in enumerate(sources):
        with Image.open(path) as source:
            if source.size != (ICON_SIZE, ICON_SIZE) or source.mode != "RGBA":
                raise ValueError("Icon must be 128 x 128 RGBA: {}".format(path))
            if source.getchannel("A").getextrema()[0] != 0:
                raise ValueError("Icon must have a transparent background: {}".format(path))
            x = index % ATLAS_COLUMNS * ICON_SIZE
            y = index // ATLAS_COLUMNS * ICON_SIZE
            atlas.paste(source, (x, y))
        ET.SubElement(imageset, "Image", {"height": str(ICON_SIZE), "name": path.stem,
                                        "width": str(ICON_SIZE), "xPos": str(x), "yPos": str(y)})
    atlas.save(gui / "Items.png", optimize=True)
    ET.indent(imageset, space="    ")
    ET.ElementTree(imageset).write(gui / "Items.imageset", encoding="utf-8", xml_declaration=False)
    with (gui / "Items.imageset").open("a", encoding="utf-8", newline="\n") as target:
        target.write("\n")


def main():
    """Read the repository location and generate its item atlas and imageset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()
    build_imageset(arguments.repo)


if __name__ == "__main__":
    main()
