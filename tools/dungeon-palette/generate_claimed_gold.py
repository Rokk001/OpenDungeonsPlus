#!/usr/bin/env python3
"""Generates the claimed floor and the gold vein textures (materials/textures/Claimed.png, ClaimedNormal.png,
Gold.png, GoldNormal.png).

Original work of the project, licence CC0. Everything is procedural and seeded; running the script again gives
byte-identical files. Needs numpy and Pillow.

Claimed floor: dark, muted flagstone with hairline cracks. The tile is truly periodic and everything that is not a
flat colour is faded out in a thin strip along the tile border, so a border pixel does not depend on the rotation
of the piece (the claimed pieces are randomly rotated by 90 degrees) and neighbouring tiles continue without a
frame. The only trace of the tile grid is a very faint joint. The area under the ownership marker (ClaimedMask.png)
is kept dark, exactly as before, because the shader blends the seat colour into it.

Gold vein: dark rock with irregular veins and nuggets of gold. Periodic, so it tiles seamlessly both with the
world space UV of upward facing surfaces (one repeat per tile) and with the mesh UV of the side faces.

Both come with a tangent space normal map (red = -d height / dx, green = +d height / dy, image y pointing down).

Usage: python generate_claimed_gold.py [output folder] [--check]
"""

import os
import sys

import numpy as np
from PIL import Image

N = 512

# Target tones (8 bit) and the claimed floor tone.
CLAIMED_BASE = np.array([80.0, 73.0, 65.0])
ROCK_BASE = np.array([46.0, 41.0, 38.0])
GOLD_DARK = np.array([178.0, 124.0, 16.0])
GOLD_MID = np.array([246.0, 186.0, 38.0])
GOLD_GLINT = np.array([252.0, 208.0, 84.0])


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


_IDX = np.arange(N)
_EDGE = np.minimum(_IDX, N - 1 - _IDX)
_LO = np.minimum(_EDGE[:, None], _EDGE[None, :]).astype(float)
_YY, _XX = np.mgrid[0:N, 0:N]


def fbm(seed, fx, octaves=3):
    """Periodic noise with zero mean and unit variance; fx = feature count per tile."""
    rng = np.random.RandomState(seed)
    k = np.fft.fftfreq(N) * N
    total = np.zeros((N, N))
    for octave in range(octaves):
        white = rng.standard_normal((N, N))
        scale = 2.0 ** octave
        filt = np.exp(-(k[None, :] / (fx * scale)) ** 2 - (k[:, None] / (fx * scale)) ** 2)
        layer = np.fft.ifft2(np.fft.fft2(white) * filt).real
        layer /= layer.std() + 1e-9
        total += layer * 0.55 ** octave
    return total / (total.std() + 1e-9)


def blur(img, sigma):
    k = np.fft.fftfreq(N) * N
    filt = np.exp(-0.5 * (2 * np.pi * sigma / N) ** 2 * (k[None, :] ** 2 + k[:, None] ** 2))
    return np.fft.ifft2(np.fft.fft2(img) * filt).real


def normal_map(height, strength):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    gx *= strength / (gx.std() + 1e-9) * 0.30
    gy *= strength / (gy.std() + 1e-9) * 0.30
    nrm = np.stack([-gx, gy, np.ones_like(gx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return nrm * 0.5 + 0.5


def save(path, arr):
    img = Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8), 'RGB')
    img.save(path, optimize=True)


def claimed():
    border = smoothstep(2.0, 30.0, _LO)  # 0 at the tile border, 1 inside
    # broad, low contrast mottling and fine grain, both gone at the border
    mottle = fbm(11, 3.0, 3)
    grain = fbm(12, 70.0, 2)
    lum = 1.0 + border * (0.07 * mottle + 0.045 * grain)
    # hairline cracks: zero level lines of a smooth random field, about two thirds of them open
    field = fbm(14, 2.6, 4)
    gy = (np.roll(field, -1, 0) - np.roll(field, 1, 0)) * 0.5
    gx = (np.roll(field, -1, 1) - np.roll(field, 1, 1)) * 0.5
    dist_px = np.abs(field) / np.maximum(np.hypot(gx, gy), 1e-4)
    keep = smoothstep(-0.7, -0.2, fbm(15, 2.5, 2))
    crack = (1.0 - smoothstep(0.5, 1.7, dist_px)) * keep * border
    lum = lum - 0.32 * crack
    # very faint joint along the tile border (same pixels on every side, rotation safe)
    joint = 1.0 - smoothstep(0.0, 3.0, _LO)
    lum = lum - 0.08 * joint
    rgb = CLAIMED_BASE[None, None, :] * lum[..., None]
    # the ownership marker area stays dark (the shader blends the seat colour into it)
    mask = np.asarray(Image.open(os.path.join(os.path.dirname(__file__), '..', '..', 'materials', 'textures',
                                               'ClaimedMask.png')).convert('L').resize((N, N), Image.BILINEAR),
                      dtype=float) / 255.0
    rgb = rgb * (1.0 - mask[..., None])
    height = 0.6 * border * (0.5 * mottle + 0.4 * grain) - 1.4 * crack - 0.3 * joint
    return rgb, normal_map(height, 0.8) * 255.0


def gold():
    # rock: dark, cool, rough
    rock_lum = 1.0 + 0.16 * fbm(21, 5.0, 3) + 0.10 * fbm(22, 60.0, 2)
    cracks = 1.0 - smoothstep(0.0, 0.05, np.abs(fbm(23, 7.0, 2)))
    rock = ROCK_BASE[None, None, :] * (rock_lum - 0.25 * cracks)[..., None]
    # gold: ragged clumps and veins (many octaves give a jagged edge), about half of the area
    clump = fbm(24, 7.0, 5) + 0.6 * fbm(31, 18.0, 3)
    vein = 1.0 - smoothstep(0.04, 0.20, np.abs(fbm(32, 5.0, 4)))
    cover = np.maximum(smoothstep(0.05, 0.25, clump), vein * smoothstep(-0.4, 0.2, fbm(33, 5.0, 2)))
    shade = np.clip(0.5 + 0.25 * fbm(27, 18.0, 3) + 0.18 * fbm(28, 70.0, 2), 0.0, 1.0)
    gold_rgb = GOLD_DARK[None, None, :] * (1.0 - shade[..., None]) + GOLD_MID[None, None, :] * shade[..., None]
    glint = smoothstep(1.3, 1.9, fbm(29, 60.0, 2)) * cover
    gold_rgb = gold_rgb * (1.0 - glint[..., None]) + GOLD_GLINT[None, None, :] * glint[..., None]
    rim = np.clip(blur(cover, 1.6), 0, 1)
    rgb = rock * (1.0 - cover[..., None]) + gold_rgb * cover[..., None]
    rgb = rgb * (1.0 - 0.35 * (rim * (1.0 - rim) * 4.0)[..., None])
    height = 1.0 * blur(cover, 1.2) + 0.30 * fbm(30, 40.0, 3) - 0.6 * cracks
    return rgb, normal_map(height, 1.0) * 255.0


def main():
    out = 'materials/textures'
    check = False
    for arg in sys.argv[1:]:
        if arg == '--check':
            check = True
        else:
            out = arg
    os.makedirs(out, exist_ok=True)
    jobs = (('Claimed', claimed), ('Gold', gold))
    for name, fn in jobs:
        rgb, nrm = fn()
        save(os.path.join(out, name + '.png'), rgb)
        save(os.path.join(out, name + 'Normal.png'), nrm)
        if check:
            a = np.clip(rgb, 0, 255)
            y = a @ [0.299, 0.587, 0.114]
            mx, mn = a.max(2), a.min(2)
            sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0).mean()
            print('%-8s mean rgb %s  Y %.1f  sat %.2f  max %d' % (name, a.reshape(-1, 3).mean(0).round(1), y.mean(), sat,
                                                               a.max()))


if __name__ == '__main__':
    main()
