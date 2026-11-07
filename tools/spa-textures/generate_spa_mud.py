#!/usr/bin/env python3
"""Paints SpaMud.png, the surface of the hot mud bath of the lava spa (materials/textures/).

Decision 837: the pool showed an opaque near-black surface, because SpaMud multiplied the regraded dark ground texture
Dirt.png (mean about 41 35 29) by the diffuse 0.4 0.25 0.13. The spa plan (D6, 13.1) asks for a hot mud bath of dark
brown mud with a few bubble domes, heated by lava below. This texture gives the mud a liquid look: a warm wet brown with
slow flow swirls, glossy light streaks where the surface catches the light, bubble rings and a faint orange warmth in the
deep folds. It tiles seamlessly (all noise is periodic over the tile), so the slow scroll_anim of the material moves it.

Deterministic (fixed seed): every run gives byte-identical output. Original work of the project, licence GPLv3+
(procedurally painted). Needs numpy and Pillow.

Usage: python generate_spa_mud.py <materials/textures folder>
"""

import os
import sys

import numpy as np
from PIL import Image

SIZE = 256
SEED = 837
# Colours (sRGB 0-255): the deep warm brown of the mud, the lighter wet top of the folds, the gloss of the streaks and
# the faint glow of the lava heat in the deepest folds
DEEP = np.array([58.0, 36.0, 22.0])
TOP = np.array([118.0, 80.0, 50.0])
GLOSS = np.array([186.0, 150.0, 112.0])
HEAT = np.array([150.0, 62.0, 22.0])
# Bubble rings: how many, their radius range in pixels
BUBBLES = 14
BUBBLE_RADIUS = (4.0, 11.0)


def periodic_noise(rng, octaves):
    """Sum of random periodic sine waves: smooth, seamless over the tile, values about -1 to 1."""
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64) / SIZE
    total = np.zeros((SIZE, SIZE))
    weight = 0.0
    for octave in range(octaves):
        frequency = 2 ** octave
        amplitude = 0.55 ** octave
        for _ in range(3):
            kx = rng.integers(-frequency - 1, frequency + 2)
            ky = rng.integers(-frequency - 1, frequency + 2)
            if kx == 0 and ky == 0:
                ky = 1
            phase = rng.uniform(0.0, 2.0 * np.pi)
            total += amplitude * np.sin(2.0 * np.pi * (kx * x + ky * y) + phase)
            weight += amplitude
    return total / weight * 2.0


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    rng = np.random.default_rng(SEED)
    # Flow: the folds of the mud, warped by a second noise so they swirl instead of running in straight bands
    warp = periodic_noise(rng, 3)
    folds = periodic_noise(rng, 5)
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(np.float64) / SIZE
    swirl = np.sin(2.0 * np.pi * (2.0 * x + 1.0 * y) + 2.4 * warp + 1.6 * folds)
    height = np.clip(0.5 + 0.32 * folds + 0.18 * swirl, 0.0, 1.0)

    colour = DEEP[None, None, :] * (1.0 - height[..., None]) + TOP[None, None, :] * height[..., None]
    # The lava heat shows faintly in the deepest folds
    heat = np.clip((0.22 - height) / 0.22, 0.0, 1.0) ** 2
    colour = colour * (1.0 - 0.35 * heat[..., None]) + HEAT[None, None, :] * (0.35 * heat[..., None])
    # Wet gloss: thin light streaks along the crests of the swirl
    gloss = np.clip((swirl - 0.82) / 0.18, 0.0, 1.0) * np.clip(height * 1.4 - 0.3, 0.0, 1.0)
    colour = colour * (1.0 - 0.7 * gloss[..., None]) + GLOSS[None, None, :] * (0.7 * gloss[..., None])

    # Bubble domes: a light ring with a darker wet middle and a small highlight, wrapped around the tile edges
    for _ in range(BUBBLES):
        cx, cy = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
        radius = rng.uniform(*BUBBLE_RADIUS)
        dx = (np.arange(SIZE)[None, :] - cx + SIZE / 2) % SIZE - SIZE / 2
        dy = (np.arange(SIZE)[:, None] - cy + SIZE / 2) % SIZE - SIZE / 2
        distance = np.sqrt(dx * dx + dy * dy) / radius
        ring = np.clip(1.0 - np.abs(distance - 1.0) / 0.25, 0.0, 1.0)
        inside = np.clip(1.0 - distance, 0.0, 1.0)
        spot = np.clip(1.0 - np.sqrt((dx + radius * 0.35) ** 2 + (dy + radius * 0.35) ** 2) / (radius * 0.28), 0.0, 1.0)
        colour = colour * (1.0 - 0.45 * ring[..., None]) + TOP[None, None, :] * 1.25 * (0.45 * ring[..., None])
        colour = colour * (1.0 - 0.25 * inside[..., None]) + DEEP[None, None, :] * 1.1 * (0.25 * inside[..., None])
        colour = colour * (1.0 - 0.8 * spot[..., None]) + GLOSS[None, None, :] * (0.8 * spot[..., None])

    # A little grain so the surface does not look like plastic
    grain = rng.normal(0.0, 3.0, (SIZE, SIZE, 1))
    image = np.clip(colour + grain, 0, 255).astype(np.uint8)
    Image.fromarray(image, 'RGB').save(os.path.join(sys.argv[1], 'SpaMud.png'), optimize=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
