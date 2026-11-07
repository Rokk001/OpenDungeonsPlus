"""Paint the original textures of the worn ghost-hunter backpack and the capture cannon (owner decision 791).

The worn pack was an almost black leather block (GhostLeather, luminance about 20). These textures give it a readable
olive canvas with a visible weave, seams and wear, a light brushed steel for frame, plates and cannon barrel, and a
ribbed rubber for hose and grip. Run with Python 3 and Pillow from the repository root; the output is deterministic:

    python assets-src/rooms/ghostroom/paint_hunter_gear.py

Run it before assets-src/rooms/ghostroom/create_models.py, which loads these PNGs as the base colour of its materials.
"""
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFilter

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / 'materials' / 'textures'
SIZE = 512


# Clamp one channel value to the 8-bit range.
def clamp(value):
    return max(0, min(255, int(round(value))))


# Add fine per-pixel grain of the given strength to an RGB image.
def grain(image, strength, seed):
    rng = random.Random(seed)
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = pixels[x, y]
            n = rng.uniform(-strength, strength)
            pixels[x, y] = (clamp(r + n), clamp(g + n), clamp(b + n * 0.8))
    return image


# Darken soft irregular blotches (wear, grime) into the image.
def blotches(image, count, radius, depth, seed):
    rng = random.Random(seed)
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    for _ in range(count):
        x, y = rng.uniform(0, image.width), rng.uniform(0, image.height)
        r = rng.uniform(radius * 0.4, radius)
        draw.ellipse((x - r, y - r * rng.uniform(0.5, 1.0), x + r, y + r), fill=rng.randint(depth // 2, depth))
    mask = mask.filter(ImageFilter.GaussianBlur(radius * 0.45))
    dark = Image.new('RGB', image.size, (30, 26, 16))
    return Image.composite(dark, image, mask)


# Olive canvas: crossing warp and weft threads, double stitched seams and a darker worn edge.
def canvas():
    image = Image.new('RGB', (SIZE, SIZE), (118, 116, 74))
    pixels = image.load()
    for y in range(SIZE):
        for x in range(SIZE):
            # Plain weave: alternating raised warp (vertical) and weft (horizontal) threads, 4 px each.
            cell = ((x // 4) + (y // 4)) % 2
            along = (y % 4) if cell else (x % 4)
            shade = 14 if along in (1, 2) else -10
            shade += -8 if cell else 6
            r, g, b = pixels[x, y]
            pixels[x, y] = (clamp(r + shade), clamp(g + shade), clamp(b + shade * 0.7))
    image = grain(image, 9, 791)
    image = blotches(image, 26, 46, 110, 7911)
    draw = ImageDraw.Draw(image)
    # Seams around the panel and across its middle with light stitches.
    for offset in (14, SIZE - 15):
        draw.line((0, offset, SIZE, offset), fill=(70, 66, 40), width=3)
        draw.line((offset, 0, offset, SIZE), fill=(70, 66, 40), width=3)
    draw.line((0, SIZE // 2, SIZE, SIZE // 2), fill=(70, 66, 40), width=3)
    draw.line((SIZE // 2, 0, SIZE // 2, SIZE), fill=(70, 66, 40), width=3)
    for position in range(6, SIZE, 16):
        for offset in (22, SIZE - 23, SIZE // 2 + 8):
            draw.line((position, offset, position + 8, offset), fill=(214, 200, 150), width=2)
            draw.line((offset, position, offset, position + 8), fill=(214, 200, 150), width=2)
    return image


# Light brushed steel with horizontal brush strokes, scratches and a few small dents.
def steel():
    rng = random.Random(7912)
    image = Image.new('RGB', (SIZE, SIZE), (150, 154, 156))
    draw = ImageDraw.Draw(image)
    for y in range(SIZE):
        value = 150 + rng.uniform(-16, 16)
        draw.line((0, y, SIZE, y), fill=(clamp(value), clamp(value + 4), clamp(value + 7)))
    image = image.filter(ImageFilter.GaussianBlur(0.6))
    draw = ImageDraw.Draw(image)
    for _ in range(140):
        x, y = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
        length, slope = rng.uniform(10, 70), rng.uniform(-0.5, 0.5)
        tone = rng.choice(((205, 208, 210), (88, 90, 92)))
        draw.line((x, y, x + length, y + length * slope), fill=tone, width=1)
    image = grain(image, 7, 7913)
    return blotches(image, 10, 34, 70, 7914)


# Black-brown ribbed rubber for the hose and the cannon grip: light ribs keep it readable at a distance.
def rubber():
    image = Image.new('RGB', (SIZE, SIZE), (62, 58, 52))
    draw = ImageDraw.Draw(image)
    for y in range(0, SIZE, 16):
        draw.rectangle((0, y, SIZE, y + 5), fill=(112, 106, 96))
        draw.line((0, y + 6, SIZE, y + 6), fill=(34, 32, 28), width=2)
    image = image.filter(ImageFilter.GaussianBlur(1.0))
    return grain(image, 10, 7915)


# Write all hunter gear textures.
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, paint in (('GhostPackCanvas', canvas), ('GhostPackSteel', steel), ('GhostPackRubber', rubber)):
        paint().save(OUT / (name + '.png'), optimize=True)
        print('painted', name)


if __name__ == '__main__':
    main()
