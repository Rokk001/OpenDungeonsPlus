#!/usr/bin/env python3
"""Generates the textures of the dungeon heart (materials/textures/DungeonHeart*.png).

The heart mesh is mapped with a spherical projection (see tools/heart-on-temple), so the images are
seamless on all edges and are twice as wide as high. Everything is procedural and seeded, running the
script again gives byte-identical files.

  DungeonHeartHealthy.png   colour of the healthy heart: violet, mottled, with dark-indigo veins
  DungeonHeartDamaged.png   the same surface faded to a grey-mauve
  DungeonHeartCritical.png  the same surface almost black, veins with a faint red glow
  DungeonHeartNormal.png    tangent space normal map of the surface (bumps, veins, creases), shared by the tiers

Usage: python generate_heart_textures.py [output folder]
Needs numpy and Pillow.
"""

import os
import sys

import numpy as np
from PIL import Image

WIDTH = 512
HEIGHT = 256
SEED = 7


def smooth(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def periodic_noise(rng, cells_x, cells_y):
    """Value noise in [0, 1] that repeats every WIDTH x HEIGHT pixels."""
    lattice = rng.random((cells_y, cells_x))
    ys = np.arange(HEIGHT) * cells_y / HEIGHT
    xs = np.arange(WIDTH) * cells_x / WIDTH
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    fy = smooth(ys - y0)[:, None]
    fx = smooth(xs - x0)[None, :]
    y1 = (y0 + 1) % cells_y
    x1 = (x0 + 1) % cells_x
    top = lattice[np.ix_(y0, x0)] * (1.0 - fx) + lattice[np.ix_(y0, x1)] * fx
    bottom = lattice[np.ix_(y1, x0)] * (1.0 - fx) + lattice[np.ix_(y1, x1)] * fx
    return top * (1.0 - fy) + bottom * fy


def fbm(rng, base_x, octaves, gain=0.5):
    total = np.zeros((HEIGHT, WIDTH))
    amplitude = 1.0
    norm = 0.0
    for octave in range(octaves):
        cells_x = base_x * 2 ** octave
        total += amplitude * periodic_noise(rng, cells_x, max(cells_x // 2, 1))
        norm += amplitude
        amplitude *= gain
    return total / norm


def warp(field, dx, dy, amount):
    """Shifts the field by (dx, dy) * amount pixels, wrapping around."""
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
    sx = (xs + (dx - 0.5) * amount).astype(int) % WIDTH
    sy = (ys + (dy - 0.5) * amount).astype(int) % HEIGHT
    return field[sy, sx]


def mix(a, b, t):
    return a[None, None, :] * (1.0 - t[:, :, None]) + b[None, None, :] * t[:, :, None]


def build_surface():
    rng = np.random.default_rng(SEED)
    mottle = fbm(rng, 6, 5)
    fine = fbm(rng, 32, 3)
    # Muscle fibres: noise stretched along the heart's height
    fibres = 0.6 * periodic_noise(rng, 64, 4) + 0.4 * periodic_noise(rng, 128, 8)
    # Veins: thin curved lines where a warped noise field crosses 0.5, a coarse and a fine network
    net = warp(fbm(rng, 5, 4), fbm(rng, 4, 2), fbm(rng, 4, 2), 70.0)
    net_fine = warp(fbm(rng, 9, 4), fbm(rng, 6, 2), fbm(rng, 6, 2), 40.0)
    veins = smooth(np.clip(1.0 - np.abs(net - 0.5) / 0.018, 0.0, 1.0))
    veins = np.maximum(veins, 0.7 * smooth(np.clip(1.0 - np.abs(net_fine - 0.5) / 0.012, 0.0, 1.0)))
    # Broad creases between the muscle bulges
    net2 = warp(fbm(rng, 3, 3), fbm(rng, 3, 2), fbm(rng, 3, 2), 110.0)
    creases = smooth(np.clip(1.0 - np.abs(net2 - 0.5) / 0.035, 0.0, 1.0))
    height = 0.55 * mottle + 0.25 * fine + 0.30 * fibres + 0.40 * veins - 0.60 * creases
    return mottle, fine + 0.6 * (fibres - 0.5), veins, creases, height


def colours(mottle, fine, veins, creases, tint_mask, dark, light, tint, vein, crease, glow=None):
    t = np.clip((mottle - 0.25) / 0.5, 0.0, 1.0) * 0.8 + 0.2 * fine
    image = mix(np.array(dark), np.array(light), t)
    image = mix_layer(image, np.array(tint), tint_mask * 0.6)
    image = mix_layer(image, np.array(crease), creases * 0.85)
    image = mix_layer(image, np.array(vein), veins * 0.9)
    if glow is not None:
        image = mix_layer(image, np.array(glow), (veins ** 2) * 0.7)
    return image


def mix_layer(image, colour, amount):
    return image * (1.0 - amount[:, :, None]) + colour[None, None, :] * amount[:, :, None]


def to_png(array, path):
    data = (np.clip(array, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(data, 'RGB').save(path, optimize=True)


def normal_map(height, strength=10.0):
    """Tangent space normal map, +Y (green) points towards larger v of the image (down)."""
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    nx = -dx * strength
    ny = dy * strength
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / length, ny / length, nz / length], axis=2) * 0.5 + 0.5


def main():
    if len(sys.argv) > 1:
        out = sys.argv[1]
    else:
        out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'materials', 'textures')
    mottle, fine, veins, creases, height = build_surface()
    tint_mask = smooth(np.clip((fbm(np.random.default_rng(SEED + 1), 4, 3) - 0.45) / 0.25, 0.0, 1.0))

    healthy = colours(mottle, fine, veins, creases, tint_mask,
        dark=(0.20, 0.03, 0.32), light=(0.58, 0.22, 0.72),
        tint=(0.66, 0.16, 0.50), vein=(0.10, 0.03, 0.28), crease=(0.09, 0.01, 0.15))
    damaged = colours(mottle, fine, veins, creases, tint_mask,
        dark=(0.19, 0.17, 0.20), light=(0.46, 0.43, 0.47),
        tint=(0.50, 0.42, 0.44), vein=(0.11, 0.10, 0.13), crease=(0.08, 0.07, 0.09))
    critical = colours(mottle, fine, veins, creases, tint_mask,
        dark=(0.05, 0.03, 0.055), light=(0.24, 0.15, 0.22),
        tint=(0.26, 0.10, 0.12), vein=(0.10, 0.03, 0.05), crease=(0.015, 0.008, 0.015),
        glow=(0.65, 0.05, 0.06))

    to_png(healthy, os.path.join(out, 'DungeonHeartHealthy.png'))
    to_png(damaged, os.path.join(out, 'DungeonHeartDamaged.png'))
    to_png(critical, os.path.join(out, 'DungeonHeartCritical.png'))
    to_png(normal_map(height), os.path.join(out, 'DungeonHeartNormal.png'))


if __name__ == '__main__':
    main()
