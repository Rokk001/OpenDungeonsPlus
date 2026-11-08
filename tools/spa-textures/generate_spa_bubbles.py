"""Paint an original expanding hot-mud bubble sprite; usage: script <output directory>."""
from pathlib import Path
import sys

import numpy as np
from PIL import Image


def main():
    """Write a deterministic 64 pixel bubble with a glossy rim and transparent exterior."""
    y, x = np.mgrid[:64, :64].astype(float)
    x = (x - 31.5) / 28
    y = (y - 31.5) / 28
    radius = np.sqrt(x * x + y * y)
    rim = np.exp(-((radius - .77) / .1) ** 2)
    highlight = np.exp(-((x + .35) ** 2 + (y + .4) ** 2) / .045)
    colour = np.empty((64, 64, 4), dtype=np.uint8)
    for channel, base, gloss in ((0, 87, 125), (1, 55, 110), (2, 32, 90)):
        colour[:, :, channel] = np.clip(base + rim * gloss * .55 + highlight * gloss, 0, 255)
    colour[:, :, 3] = np.clip((1 - radius) / .13, 0, 1) * 235
    Image.fromarray(colour).save(Path(sys.argv[1]) / 'SpaMudBubble.png', optimize=True)


if __name__ == '__main__':
    main()
