#!/usr/bin/env python3
"""Draws the crown that is shown instead of the level number of the champion.

Everything is drawn from simple shapes by this script, nothing is taken from another
work. The output is deterministic. Run it from the repository root to write the
pictures again:

    python tools/gen_champion_crown.py

Output (the same 64x64 RGBA picture under two names, so that the Ogre texture of the
overhead material and the GUI texture never share a name):
    materials/textures/ChampionCrown.png
    gui/ChampionCrownIcon.png

Needs numpy and Pillow.
"""

import os

import numpy
from PIL import Image, ImageDraw

SIZE = 64
SUPER = 4
CANVAS = SIZE * SUPER  # drawn on a 256x256 canvas and scaled down

CROWN_POINTS = ((8, 52), (8, 22), (20, 36), (32, 14), (44, 36), (56, 22), (56, 52))
CROWN_FILL = (246, 186, 38, 255)
CROWN_OUTLINE = (120, 80, 10, 255)
CROWN_OUTLINE_WIDTH = 3
JEWEL_CENTRES = ((20, 44), (32, 44), (44, 44))
JEWEL_RADIUS = 4
JEWEL_COLOUR = (180, 30, 30, 255)

OUTPUT_FILES = (
    os.path.join("materials", "textures", "ChampionCrown.png"),
    os.path.join("gui", "ChampionCrownIcon.png"),
)


def scaled(points):
    """Returns the points of the 64x64 design scaled to the supersampled canvas."""
    return [(x * SUPER, y * SUPER) for x, y in points]


def draw_crown():
    """Returns the 64x64 RGBA picture of the crown."""
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    points = scaled(CROWN_POINTS)
    draw.polygon(points, fill=CROWN_FILL)
    # The outline is a closed line; the first point is repeated to close it
    draw.line(points + [points[0]], fill=CROWN_OUTLINE, width=CROWN_OUTLINE_WIDTH * SUPER, joint="curve")
    for cx, cy in JEWEL_CENTRES:
        radius = JEWEL_RADIUS * SUPER
        draw.ellipse((cx * SUPER - radius, cy * SUPER - radius, cx * SUPER + radius, cy * SUPER + radius),
                     fill=JEWEL_COLOUR)
    small = image.resize((SIZE, SIZE), Image.LANCZOS)
    # Round trip through numpy keeps the data exactly as an 8 bit RGBA array
    return Image.fromarray(numpy.asarray(small, dtype=numpy.uint8), "RGBA")


def main():
    """Writes the picture to every output file."""
    picture = draw_crown()
    for path in OUTPUT_FILES:
        picture.save(path)
        print("wrote " + path)


if __name__ == "__main__":
    main()
