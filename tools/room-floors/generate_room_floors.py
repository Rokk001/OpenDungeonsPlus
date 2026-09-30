#!/usr/bin/env python3
"""Generates the floor textures of the hatchery, library, dormitory, dungeon temple, treasury, crypt, training hall,
casino, prison, arena, torture chamber, workshop, portal and portal wave, plus the UV atlas of the wooden bridge
(materials/textures/).

Original work of the project, licence CC0. Everything is procedural and seeded; running the script again gives
byte-identical files. Needs numpy and Pillow.

Every room is built from one base field (the open floor) plus decoration bands that are laid along the exposed
(wall) sides of a piece. All pieces of a room therefore share the very same base pixels, so the seams between
pieces match. The tile borders are made seam-free in two ways:
  - library and dormitory: slabs / planks are separated by gaps that run along the tile border and the tile
    centre lines, the gaps are the same on both sides of a border;
  - hatchery, training hall, casino, prison: every layer is truly periodic (FFT noise on a wrapping grid, loose
    objects are drawn with all tile offsets so they continue on the opposite side), so there is no border band at
    all; the seamless wrap is checked with --check and --seamcheck (texture rolled by half a tile);
  - dungeon temple and treasury: irregular slabs (random rectangle subdivision) inside a gap that runs along
    the tile border, so nothing but the constant gap colour touches the border;
  - crypt: derived from the original cobble texture (Yughues, CC0) read from git history (commit 2ac74a729^);
    darkened, moss and lichen and cracks are added with periodic noise that fades out at the tile border;
  - prison: derived from the original Prison.png read from git history (commit 6db9aa611), mortar turned to mud,
    plus rust and straw;
  - arena, torture, workshop: every layer is truly periodic (see training hall); the torture slabs and the
    workshop planks come from a wrapping row layout with warped joints.
  - portal, portal wave: every layer is truly periodic (see training hall); slabs from a wrapping row layout with
    hairline rune grooves (portal) or concentric wave grooves on the torus (portal wave);
  - wooden bridge: the UV atlas WoodBridge.png is painted from scratch (one plank per mesh UV quad, nail heads,
    dirt, cracks); the UV layout is read from models/WoodBridge.mesh, WoodBridgeMask.png is not touched.
The room shader has no specular term, so only a diffuse texture and a matching tangent space normal map
(red = -d height / dx, green = +d height / dy, image y pointing down) are written.

Usage: python generate_room_floors.py [output folder] [--check] [--seamcheck=<folder for the rolled previews>]
"""

import os
import sys

import numpy as np
from PIL import Image, ImageDraw

N = 512
SUPER = 2
MARGIN = 26


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def mix(a, b, t):
    if np.ndim(t) == 2 and np.ndim(a) == 3:
        t = t[..., None]
    return a * (1.0 - t) + b * t


_IDX = np.arange(N)
_EDGE = np.minimum(_IDX, N - 1 - _IDX)
_LO = np.minimum(_EDGE[:, None], _EDGE[None, :])
_HI = np.maximum(_EDGE[:, None], _EDGE[None, :])
_BORDER_W = 1.0 - smoothstep(2.0, 28.0, _LO.astype(float))
_YY, _XX = np.mgrid[0:N, 0:N]


def fbm(seed, fx, fy=None, octaves=3):
    """Periodic noise with zero mean and unit variance; fx/fy are the feature counts per tile."""
    if fy is None:
        fy = fx
    rng = np.random.RandomState(seed)
    k = np.fft.fftfreq(N) * N
    kx = k[None, :]
    ky = k[:, None]
    total = np.zeros((N, N))
    for octave in range(octaves):
        white = rng.standard_normal((N, N))
        scale = 2.0 ** octave
        filt = np.exp(-(kx / (fx * scale)) ** 2 - (ky / (fy * scale)) ** 2)
        layer = np.fft.ifft2(np.fft.fft2(white) * filt).real
        layer /= layer.std() + 1e-9
        total += layer * 0.55 ** octave
    return total / (total.std() + 1e-9)


def nz(seed, fx, fy=None, octaves=3):
    """fbm that is mirror and transpose symmetric at the tile border (see module docstring)."""
    n = fbm(seed, fx, fy, octaves)
    return n * (1.0 - _BORDER_W) + n[_LO, _HI] * _BORDER_W


_FADE = smoothstep(0.0, 6.0, _LO.astype(float))


def pn(seed, fx, fy=None, octaves=3):
    """Truly periodic noise (no mirroring) that is faded to zero in a thin strip along the tile border, so that
    border pixels do not depend on the rotation of the piece."""
    return fbm(seed, fx, fy, octaves) * _FADE


def normal_map(height, strength):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    gx *= strength / (gx.std() + 1e-9) * 0.30
    gy *= strength / (gy.std() + 1e-9) * 0.30
    nrm = np.stack([-gx, gy, np.ones_like(gx)], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return nrm * 0.5 + 0.5


def to_image(arr):
    return Image.fromarray((np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), 'RGB')


# ---------------------------------------------------------------------------------------------------------------
# loose objects (straw, feathers), drawn supersampled with Pillow

class Sprites(object):
    def __init__(self, wrap=False):
        # wrap: objects crossing a tile edge continue on the opposite side (drawn with all tile offsets)
        self.offsets = [(dx, dy) for dx in (-N, 0, N) for dy in (-N, 0, N)] if wrap else [(0, 0)]
        self.colour = Image.new('RGBA', (N * SUPER, N * SUPER), (0, 0, 0, 0))
        self.height = Image.new('L', (N * SUPER, N * SUPER), 0)
        self.cdraw = ImageDraw.Draw(self.colour)
        self.hdraw = ImageDraw.Draw(self.height)

    def line(self, p0, p1, width, rgb, lift):
        for ox, oy in self.offsets:
            pts = [((p0[0] + ox) * SUPER, (p0[1] + oy) * SUPER), ((p1[0] + ox) * SUPER, (p1[1] + oy) * SUPER)]
            self.cdraw.line(pts, fill=tuple(int(c * 255) for c in rgb) + (255,), width=max(1, int(width * SUPER)))
            self.hdraw.line(pts, fill=int(lift * 255), width=max(1, int(width * SUPER)))

    def polygon(self, pts, rgb, lift):
        for ox, oy in self.offsets:
            shifted = [((x + ox) * SUPER, (y + oy) * SUPER) for x, y in pts]
            self.cdraw.polygon(shifted, fill=tuple(int(c * 255) for c in rgb) + (255,))
            self.hdraw.polygon(shifted, fill=int(lift * 255))

    def result(self):
        rgba = np.asarray(self.colour.resize((N, N), Image.BOX)).astype(float) / 255.0
        hgt = np.asarray(self.height.resize((N, N), Image.BOX)).astype(float) / 255.0
        return rgba[..., :3], rgba[..., 3], hgt


def straw_segments(seed, count, box, length, angle=None, spread=0.5):
    """Random straw segments inside box=(x0, y0, x1, y1) (canonical, before mapping to a side)."""
    rng = np.random.RandomState(seed)
    segs = []
    for _ in range(count):
        cx = rng.uniform(box[0], box[2])
        cy = rng.uniform(box[1], box[3])
        ang = rng.uniform(0, np.pi) if angle is None else angle + rng.uniform(-spread, spread)
        half = rng.uniform(length[0], length[1]) * 0.5
        dx, dy = np.cos(ang) * half, np.sin(ang) * half
        segs.append((cx - dx, cy - dy, cx + dx, cy + dy, rng.uniform(0.85, 1.25), rng.uniform(0.75, 1.15)))
    return segs


def draw_straws(sprites, segs, rgb, mapper=None):
    for x0, y0, x1, y1, width, tone in segs:
        p0, p1 = (x0, y0), (x1, y1)
        if mapper is not None:
            p0, p1 = mapper(*p0), mapper(*p1)
        tint = np.array(rgb) * tone
        sprites.line(p0, p1, width * 1.6, np.clip(tint, 0, 1), 0.55 + 0.3 * tone)
        sprites.line(p0, p1, width * 0.5, np.clip(tint * 1.25, 0, 1), 0.85)


def side_mapper(side):
    """Maps canonical band coordinates (along, depth from the wall) to tile pixels for one exposed side."""
    return {'T': lambda a, d: (a, d), 'B': lambda a, d: (a, N - 1 - d),
            'L': lambda a, d: (d, a), 'R': lambda a, d: (N - 1 - d, a)}[side]


def depth_map(side):
    return {'T': _YY, 'B': N - 1 - _YY, 'L': _XX, 'R': N - 1 - _XX}[side].astype(float)


def overlay(col, hgt, sprites, height_gain):
    sc, sa, sh = sprites.result()
    col = mix(col, sc, sa)
    hgt = hgt + (sh - 0.0) * sa * height_gain
    return col, hgt


# ---------------------------------------------------------------------------------------------------------------
# dormitory: dark oak planks in a basket weave, straw and fur

OAK = np.array([0.33, 0.245, 0.18])
GAP = np.array([0.05, 0.035, 0.025])
Q = N // 2
PLANK = 64
GW = 3


def dormitory_field():
    rng = np.random.RandomState(101)
    qi, qj = _YY // Q, _XX // Q
    ly, lx = _YY % Q, _XX % Q
    horiz = (qi + qj) % 2 == 0
    across = np.where(horiz, ly, lx)
    along = np.where(horiz, lx, ly)
    pidx = across // PLANK
    acr = across % PLANK
    plank_id = (qi * 2 + qj) * 4 + pidx
    joint = rng.uniform(70, Q - 70, 32)
    has_joint = rng.uniform(0, 1, 32) < 0.45
    jpos = np.where(has_joint, joint, -1000.0)[plank_id]
    half = (along > jpos).astype(int)
    piece = plank_id * 2 + half
    bright = rng.uniform(0.80, 1.18, 64)[piece]
    warm = rng.uniform(-0.04, 0.04, 64)[piece]
    dg = np.minimum(acr, PLANK - 1 - acr).astype(float)
    de = np.minimum(along, Q - 1 - along).astype(float)
    dj = np.abs(along - jpos).astype(float)
    dd = np.minimum(np.minimum(dg, de), dj)
    g_h = fbm(11, 3.0, 70.0, 2)
    g_v = fbm(12, 70.0, 3.0, 2)
    grain = np.where(horiz, g_h, g_v)
    fine = nz(13, 150.0, 150.0, 2)
    col = OAK[None, None, :] * bright[..., None]
    col = col + warm[..., None] * np.array([0.6, 0.2, -0.3])[None, None, :]
    col = col * (1.0 + 0.07 * grain[..., None] + 0.04 * fine[..., None])
    streak = smoothstep(0.7, 1.9, grain)
    col = col * (1.0 - 0.30 * streak[..., None])
    hgt = 0.12 * grain + 0.05 * fine + 0.06 * (bright - 1.0)
    # knots
    kn = np.random.RandomState(102)
    for pid in range(32):
        if kn.uniform() < 0.4:
            orient = None
            qrow = pid // 8
            q_i, q_j = qrow // 2, qrow % 2
            is_h = (q_i + q_j) % 2 == 0
            pi = pid % 4
            a = kn.uniform(50, Q - 50)
            c = pi * PLANK + PLANK / 2.0 + kn.uniform(-8, 8)
            ox, oy = q_j * Q, q_i * Q
            cx, cy = (ox + a, oy + c) if is_h else (ox + c, oy + a)
            ra = kn.uniform(9, 16)
            rc = ra * 0.65
            dx, dy = (_XX - cx), (_YY - cy)
            ux, uy = (dx / ra, dy / rc) if is_h else (dx / rc, dy / ra)
            r = np.sqrt(ux ** 2 + uy ** 2)
            ring = 0.5 + 0.5 * np.sin(r * 9.0)
            area = 1.0 - smoothstep(0.7, 1.5, r)
            col = col * (1.0 - area[..., None] * (0.25 + 0.25 * ring[..., None]))
            hgt = hgt - 0.25 * area
    # worn walkways: lighter and smoother
    wear = smoothstep(0.55, 1.25, nz(14, 2.4, 2.4, 2))
    col = mix(col, np.clip(col * 1.14 + 0.012, 0, 1), wear * 0.75)
    # dirt in the gaps and bevels
    t = smoothstep(GW - 1.0, GW + 1.5, dd)
    col = mix(np.broadcast_to(GAP, col.shape), col, t)
    col = col * (0.78 + 0.22 * smoothstep(GW, GW + 9.0, dd))[..., None]
    hgt = hgt * 0.6 + 1.6 * smoothstep(GW - 1.0, GW + 5.0, dd)
    # fur patches
    fr = np.random.RandomState(103)
    fur_n = nz(15, 160.0, 25.0, 2)
    for i in range(2):
        cx, cy = fr.uniform(120, N - 120, 2)
        rad = fr.uniform(45, 70)
        wob = 14.0 * nz(40 + i, 6.0, 6.0, 2)
        r = np.sqrt((_XX - cx) ** 2 + ((_YY - cy) * 1.3) ** 2) + wob
        a = 1.0 - smoothstep(rad * 0.6, rad, r)
        fur = np.array([0.135, 0.095, 0.065]) * (1.0 + 0.30 * fur_n[..., None])
        col = mix(col, np.clip(fur, 0, 1), a * 0.88)
        hgt = hgt + a * (0.8 + 0.25 * fur_n)
    # scattered straw
    sp = Sprites()
    segs = straw_segments(104, 70, (MARGIN + 6, MARGIN + 6, N - MARGIN - 6, N - MARGIN - 6), (22, 40))
    draw_straws(sp, segs, (0.62, 0.50, 0.24))
    col, hgt = overlay(col, hgt, sp, 0.8)
    return col, hgt


def dormitory_band(col, hgt, side):
    d = depth_map(side)
    wob = 9.0 * nz(51, 10.0, 10.0, 2)
    dw = d + wob
    # dirty wall contact: darker, packed floor against the wall
    dark = 0.46 * (1.0 - smoothstep(2.0, 70.0, dw)) + 0.12 * (1.0 - smoothstep(0.0, 130.0, dw))
    col = col * (1.0 - dark)[..., None]
    dirt = (1.0 - smoothstep(10.0, 46.0, dw + 16.0 * nz(52, 14.0, 14.0, 2))) * 0.55
    col = mix(col, np.array([0.14, 0.10, 0.07])[None, None, :] * (1.0 + 0.3 * nz(53, 90.0, 90.0, 2)[..., None]), dirt)
    hgt = hgt + 0.4 * dirt
    # straw tufts gathered at the wall
    sp = Sprites()
    segs = straw_segments(60 + ord(side), 44, (MARGIN + 8, 10, N - MARGIN - 8, 92), (22, 44), 0.0, 0.9)
    draw_straws(sp, segs, (0.64, 0.51, 0.25), side_mapper(side))
    col, hgt = overlay(col, hgt, sp, 0.8)
    return col, hgt


# ---------------------------------------------------------------------------------------------------------------
# library: worn dark stone slabs, ink stains, burgundy dust next to the shelves

STONE = np.array([0.245, 0.25, 0.285])


def library_field():
    rng = np.random.RandomState(201)
    qi, qj = _YY // Q, _XX // Q
    ly, lx = _YY % Q, _XX % Q
    slab = qi * 2 + qj
    bright = rng.uniform(0.86, 1.14, 4)[slab]
    tintb = rng.uniform(-0.03, 0.03, 4)[slab]
    wobble = 2.2 * nz(21, 18.0, 18.0, 2)
    dd = np.minimum(np.minimum(lx, Q - 1 - lx), np.minimum(ly, Q - 1 - ly)).astype(float)
    dd = dd + wobble * smoothstep(3.0, 12.0, dd)
    mott = nz(22, 5.0, 5.0, 3)
    grit = nz(23, 140.0, 140.0, 2)
    col = STONE[None, None, :] * bright[..., None]
    col = col + tintb[..., None] * np.array([-0.5, 0.0, 0.8])[None, None, :]
    col = col * (1.0 + 0.11 * mott[..., None] + 0.05 * grit[..., None])
    hgt = 0.22 * mott + 0.08 * grit
    # scuffed, rubbed paths
    wear = smoothstep(0.6, 1.4, nz(24, 2.2, 2.2, 2))
    col = mix(col, np.clip(col * 1.16 + 0.01, 0, 1), wear * 0.8)
    hgt = hgt - 0.12 * wear
    # cracks and chips
    crack = 1.0 - smoothstep(0.0, 0.085, np.abs(nz(25, 9.0, 9.0, 3)))
    crack = crack * smoothstep(0.1, 0.6, np.abs(nz(26, 3.0, 3.0, 1)))
    col = col * (1.0 - 0.55 * crack)[..., None]
    hgt = hgt - 0.9 * crack
    # inky dust stains
    ink = smoothstep(0.3, 2.3, nz(27, 3.2, 3.2, 3))
    col = mix(col, np.array([0.075, 0.08, 0.115])[None, None, :] * (1.0 + 0.3 * grit[..., None]), ink * 0.6)
    # gaps and bevels
    t = smoothstep(GW - 1.0, GW + 1.5, dd)
    col = mix(np.broadcast_to(np.array([0.045, 0.045, 0.06]), col.shape), col, t)
    col = col * (0.7 + 0.3 * smoothstep(GW, GW + 10.0, dd))[..., None]
    hgt = hgt * 0.7 + 2.2 * smoothstep(GW - 1.0, GW + 6.0, dd)
    return col, hgt


def library_band(col, hgt, side):
    d = depth_map(side)
    dw = d + 14.0 * nz(61, 12.0, 12.0, 2)
    a = 1.0 - smoothstep(4.0, 130.0, dw)
    col = col * (1.0 - 0.34 * (1.0 - smoothstep(0.0, 80.0, dw)))[..., None]
    tint = np.array([0.30, 0.125, 0.165])
    lum = col.mean(-1, keepdims=True)
    col = mix(col, tint[None, None, :] * (lum / 0.23) * 0.95, a * 0.24)
    dust = smoothstep(0.4, 1.4, nz(62, 9.0, 9.0, 2)) * (1.0 - smoothstep(10.0, 100.0, dw))
    col = mix(col, np.array([0.12, 0.085, 0.10])[None, None, :], dust * 0.5)
    hgt = hgt + 0.25 * dust
    return col, hgt


# ---------------------------------------------------------------------------------------------------------------
# hatchery: trodden earth, mud, straw and feathers

EARTH = np.array([0.315, 0.235, 0.155])
MUD = np.array([0.165, 0.115, 0.08])


def feather(sp, cx, cy, ang, length, rgb):
    ca, sa = np.cos(ang), np.sin(ang)
    pts = []
    for t, w in ((0.0, 0.0), (0.2, 0.22), (0.5, 0.30), (0.8, 0.2), (1.0, 0.0)):
        pts.append((t, w))
    poly = []
    for t, w in pts:
        along, across = (t - 0.5) * length, w * length * 0.42
        poly.append((cx + ca * along - sa * across, cy + sa * along + ca * across))
    for t, w in reversed(pts[1:-1]):
        along, across = (t - 0.5) * length, -w * length * 0.42
        poly.append((cx + ca * along - sa * across, cy + sa * along + ca * across))
    sp.polygon(poly, rgb, 0.6)
    sp.line((cx - ca * length * 0.5, cy - sa * length * 0.5), (cx + ca * length * 0.5, cy + sa * length * 0.5),
            1.0, tuple(c * 0.75 for c in rgb), 0.8)


def hatchery_field():
    lump = fbm(31, 34.0, 34.0, 3)
    grit = fbm(32, 170.0, 170.0, 2)
    tone = fbm(33, 4.0, 4.0, 3)
    col = EARTH[None, None, :] * (1.0 + 0.085 * tone[..., None] + 0.085 * lump[..., None] + 0.05 * grit[..., None])
    hgt = 0.6 * lump + 0.25 * grit + 0.15 * tone
    # dark mud patches, flat and damp
    mud = smoothstep(0.55, 1.35, fbm(34, 4.4, 4.4, 3))
    mudcol = MUD[None, None, :] * (1.0 + 0.10 * lump[..., None])
    col = mix(col, mudcol, mud * 0.82)
    hgt = mix(hgt, hgt * 0.35 - 0.5, mud)
    # trodden, pale dust
    dust = smoothstep(0.9, 1.8, fbm(35, 6.0, 6.0, 2))
    col = mix(col, np.clip(col * 1.12 + 0.015, 0, 1), dust * 0.6)
    sp = Sprites(wrap=True)
    box = (0, 0, N, N)
    draw_straws(sp, straw_segments(301, 90, box, (22, 42)), (0.60, 0.48, 0.23))
    fr = np.random.RandomState(302)
    for _ in range(4):
        feather(sp, fr.uniform(0, N), fr.uniform(0, N), fr.uniform(0, np.pi), fr.uniform(22, 30),
                (0.66, 0.63, 0.56))
    col, hgt = overlay(col, hgt, sp, 0.9)
    return col, hgt


def hatchery_band(col, hgt, side):
    d = depth_map(side)
    fringe = 1.0 - smoothstep(18.0, 84.0, d + 22.0 * fbm(71, 13.0, 13.0, 3))
    dirt = np.array([0.205, 0.15, 0.10])[None, None, :] * (1.0 + 0.12 * fbm(72, 110.0, 110.0, 2)[..., None])
    col = mix(col, dirt, fringe * 0.62)
    col = col * (1.0 - 0.22 * (1.0 - smoothstep(0.0, 40.0, d)))[..., None]
    hgt = hgt - 0.45 * fringe
    sp = Sprites(wrap=True)
    segs = straw_segments(80 + ord(side), 34, (0, 8, N, 72), (26, 46), 0.0, 0.45)
    draw_straws(sp, segs, (0.62, 0.49, 0.235), side_mapper(side))
    col, hgt = overlay(col, hgt, sp, 0.9)
    return col, hgt


# ---------------------------------------------------------------------------------------------------------------
# dungeon temple and treasury: irregular slabs inside a gap along the tile border

def bsp_rects(seed, min_size, max_size, p_split):
    """Random rectangle subdivision of the whole tile; returns a list of (x0, y0, x1, y1)."""
    rng = np.random.RandomState(seed)
    rects = []

    def split(x0, y0, x1, y1):
        w, h = x1 - x0, y1 - y0
        can_v, can_h = w >= 2 * min_size, h >= 2 * min_size
        want = w > max_size or h > max_size or rng.uniform() < p_split
        if not (can_v or can_h) or not want:
            rects.append((x0, y0, x1, y1))
            return
        if can_v and (w >= h or not can_h):
            cut = x0 + int(np.clip(rng.uniform(0.36, 0.64) * w, min_size, w - min_size))
            split(x0, y0, cut, y1)
            split(cut, y0, x1, y1)
        else:
            cut = y0 + int(np.clip(rng.uniform(0.36, 0.64) * h, min_size, h - min_size))
            split(x0, y0, x1, cut)
            split(x0, cut, x1, y1)

    split(0, 0, N, N)
    return rects


def slab_maps(rects):
    """Slab index and distance (pixels) to the nearest slab edge for every pixel."""
    ids = np.zeros((N, N), dtype=int)
    dd = np.zeros((N, N))
    for i, (x0, y0, x1, y1) in enumerate(rects):
        ly = (_YY[y0:y1, x0:x1] - y0)
        lx = (_XX[y0:y1, x0:x1] - x0)
        ids[y0:y1, x0:x1] = i
        dd[y0:y1, x0:x1] = np.minimum(np.minimum(lx, x1 - x0 - 1 - lx), np.minimum(ly, y1 - y0 - 1 - ly))
    return ids, dd


BASALT = np.array([0.150, 0.136, 0.162])
TEMPLE_GAP = np.array([0.215, 0.052, 0.046])


def temple_field():
    rects = bsp_rects(401, 175, 360, 0.0)
    ids, dd = slab_maps(rects)
    rng = np.random.RandomState(402)
    bright = rng.uniform(0.86, 1.14, len(rects))[ids]
    tintb = rng.uniform(-0.03, 0.03, len(rects))[ids]
    gw = 12
    dd = dd + 3.0 * pn(41, 14.0, 14.0, 2) * smoothstep(4.0, 14.0, dd)
    mott = fbm(42, 4.0, 4.0, 3)
    grit = fbm(43, 150.0, 150.0, 2)
    col = BASALT[None, None, :] * bright[..., None]
    col = col + tintb[..., None] * np.array([0.6, 0.0, 0.5])[None, None, :] * 0.6
    col = col * (1.0 + 0.10 * mott[..., None] + 0.06 * grit[..., None])
    hgt = 0.2 * mott + 0.1 * grit
    # slightly polished worn centres
    wear = smoothstep(0.6, 1.5, fbm(44, 2.3, 2.3, 2))
    col = mix(col, np.clip(col * 1.18 + 0.008, 0, 1), wear * 0.7)
    # fine cracks
    crack = 1.0 - smoothstep(0.0, 0.05, np.abs(fbm(45, 11.0, 11.0, 3)))
    crack = crack * smoothstep(0.2, 0.9, np.abs(fbm(46, 3.0, 3.0, 1)))
    col = mix(col, np.broadcast_to(np.array([0.045, 0.02, 0.02]), col.shape), crack[..., None] * 0.8)
    hgt = hgt - 0.8 * crack
    # worn chips
    chip = smoothstep(2.3, 2.9, fbm(47, 70.0, 70.0, 1))
    col = col * (1.0 - 0.35 * chip)[..., None]
    hgt = hgt - 0.6 * chip
    # warm grout in the gaps, bevels
    t = smoothstep(gw - 1.0, gw + 1.5, dd)
    col = mix(np.broadcast_to(TEMPLE_GAP, col.shape), col, t)
    col = col * (0.72 + 0.28 * smoothstep(gw, gw + 10.0, dd))[..., None]
    hgt = hgt * 0.7 + 2.4 * smoothstep(gw - 1.0, gw + 6.0, dd)
    return col, hgt


SLATE = np.array([0.255, 0.272, 0.312])
TREASURY_GAP = np.array([0.050, 0.055, 0.070])


def treasury_field():
    rects = bsp_rects(411, 70, 190, 0.45)
    ids, dd = slab_maps(rects)
    rng = np.random.RandomState(412)
    bright = rng.uniform(0.84, 1.16, len(rects))[ids]
    tintb = rng.uniform(-0.04, 0.04, len(rects))[ids]
    gw = 2
    dd = dd + 2.0 * pn(51, 20.0, 20.0, 2) * smoothstep(3.0, 10.0, dd)
    mott = fbm(52, 6.0, 6.0, 3)
    grit = fbm(53, 150.0, 150.0, 2)
    col = SLATE[None, None, :] * bright[..., None]
    col = col + tintb[..., None] * np.array([-0.6, 0.0, 0.8])[None, None, :]
    col = col * (1.0 + 0.09 * mott[..., None] + 0.05 * grit[..., None])
    hgt = 0.2 * mott + 0.08 * grit
    # chalky wear
    chalk = smoothstep(0.5, 1.6, fbm(54, 3.0, 3.0, 3))
    col = mix(col, np.array([0.40, 0.41, 0.44])[None, None, :] * (1.0 + 0.1 * grit[..., None]), chalk * 0.30)
    hgt = hgt - 0.12 * chalk
    # hairline cracks
    crack = 1.0 - smoothstep(0.0, 0.04, np.abs(fbm(55, 10.0, 10.0, 3)))
    crack = crack * smoothstep(0.3, 1.0, np.abs(fbm(56, 3.0, 3.0, 1)))
    col = col * (1.0 - 0.5 * crack)[..., None]
    hgt = hgt - 0.6 * crack
    # thin dark joints, bevels
    t = smoothstep(gw - 1.0, gw + 1.2, dd)
    col = mix(np.broadcast_to(TREASURY_GAP, col.shape), col, t)
    col = col * (0.76 + 0.24 * smoothstep(gw, gw + 8.0, dd))[..., None]
    hgt = hgt * 0.7 + 2.0 * smoothstep(gw - 1.0, gw + 5.0, dd)
    return col, hgt


# ---------------------------------------------------------------------------------------------------------------
def git_source(path, commit):
    """Reads a file from git history (so the original does not have to be committed a second time)."""
    import io
    import subprocess
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    data = subprocess.check_output(['git', 'show', '%s:%s' % (commit, path)], cwd=root)
    return Image.open(io.BytesIO(data)).convert('RGB')


# crypt: the original cobbles, darkened, with moss and lichen in the joints and a few cracks

def blur(img, sigma):
    k = np.fft.fftfreq(N)
    filt = np.exp(-2.0 * (np.pi * sigma) ** 2 * (k[None, :] ** 2 + k[:, None] ** 2))
    return np.fft.ifft2(np.fft.fft2(img) * filt).real


def crypt_field():
    # the original Crypt.png (before F2 batch 2)
    col = np.asarray(git_source('materials/textures/Crypt.png', '2ac74a729^')).astype(float) / 255.0
    col = col * 0.85
    lum = col.mean(-1)
    low = blur(lum, 2.2)
    joint = 1.0 - smoothstep(0.12, 0.27, low)
    moss_n = pn(61, 6.0, 6.0, 3)
    grit = pn(62, 120.0, 120.0, 2)
    moss = smoothstep(-0.1, 1.0, moss_n) * joint
    mosscol = np.array([0.15, 0.19, 0.10])[None, None, :] * (0.75 + 0.45 * (grit[..., None] * 0.5 + 0.5))
    col = mix(col, mosscol, np.clip(moss * 0.9, 0, 0.85))
    # grey-green lichen speckles on the stones
    patch = smoothstep(0.7, 1.6, pn(63, 4.0, 4.0, 2))
    speck = smoothstep(1.4, 2.2, pn(64, 55.0, 55.0, 1)) * patch * (1.0 - joint)
    col = mix(col, np.array([0.36, 0.40, 0.32])[None, None, :] * (0.8 + 0.3 * grit[..., None]), speck * 0.55)
    # cracks
    crack = 1.0 - smoothstep(0.0, 0.05, np.abs(pn(65, 9.0, 9.0, 3)))
    crack = crack * smoothstep(0.3, 1.0, np.abs(pn(66, 3.0, 3.0, 1)))
    col = col * (1.0 - 0.6 * crack)[..., None]
    return col, None


# ---------------------------------------------------------------------------------------------------------------
# training hall, casino, prison (F2 batch 3): every layer is truly periodic (objects wrap around the tile edge)

class Layer(object):
    """Wrapping greyscale mask drawn supersampled (objects crossing a tile edge continue on the other side)."""

    def __init__(self):
        self.img = Image.new('L', (N * SUPER, N * SUPER), 0)
        self.draw = ImageDraw.Draw(self.img)

    def _each(self, pts):
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                yield [((x + ox) * SUPER, (y + oy) * SUPER) for x, y in pts]

    def polygon(self, pts, val=255):
        for shifted in self._each(pts):
            self.draw.polygon(shifted, fill=val)

    def line(self, pts, width, val=255):
        for shifted in self._each(pts):
            self.draw.line(shifted, fill=val, width=max(1, int(width * SUPER)))

    def ellipse(self, cx, cy, rx, ry, ang, val=255):
        ca, sa = np.cos(ang), np.sin(ang)
        pts = []
        for t in np.linspace(0.0, 2.0 * np.pi, 28, endpoint=False):
            ex, ey = rx * np.cos(t), ry * np.sin(t)
            pts.append((cx + ca * ex - sa * ey, cy + sa * ex + ca * ey))
        self.polygon(pts, val)

    def result(self):
        return np.asarray(self.img.resize((N, N), Image.BOX)).astype(float) / 255.0


SAND = np.array([0.300, 0.284, 0.256])
SAND_DARK = np.array([0.185, 0.172, 0.150])


def training_hall_field():
    tone = fbm(401, 4.0, 4.0, 3)
    lump = fbm(402, 30.0, 30.0, 3)
    grit = fbm(403, 170.0, 170.0, 2)
    col = SAND[None, None, :] * (1.0 + 0.07 * tone[..., None] + 0.055 * lump[..., None] + 0.06 * grit[..., None])
    hgt = 0.5 * lump + 0.35 * grit + 0.15 * tone
    # pale sawdust flecks and dark damp grains
    fleck = smoothstep(1.5, 2.4, fbm(404, 110.0, 110.0, 1))
    col = mix(col, np.array([0.44, 0.42, 0.37])[None, None, :], fleck * 0.55)
    damp = smoothstep(1.6, 2.5, fbm(405, 100.0, 100.0, 1))
    col = mix(col, SAND_DARK[None, None, :], damp * 0.5)
    rng = np.random.RandomState(406)
    # worn, compacted circles (darker, smoother)
    worn = Layer()
    for _ in range(6):
        worn.ellipse(rng.uniform(0, N), rng.uniform(0, N), rng.uniform(55, 95), rng.uniform(50, 90),
                     rng.uniform(0, np.pi), 255)
    worn_m = np.clip(blur(worn.result(), 10.0), 0.0, 1.0)
    worn_m = worn_m * (0.65 + 0.35 * smoothstep(-0.8, 0.8, fbm(407, 9.0, 9.0, 2)))
    col = col * (1.0 - 0.17 * worn_m)[..., None]
    hgt = mix(hgt, hgt * 0.4 - 0.3, worn_m)
    # scuff marks: short curved drag lines
    scuff = Layer()
    for _ in range(46):
        x, y = rng.uniform(0, N), rng.uniform(0, N)
        ang = rng.uniform(0, 2 * np.pi)
        curve = rng.uniform(-0.05, 0.05)
        length = rng.uniform(30, 95)
        pts = []
        for t in np.linspace(0.0, 1.0, 10):
            a = ang + curve * t * length * 0.1
            pts.append((x + np.cos(a) * length * t, y + np.sin(a) * length * t))
        scuff.line(pts, rng.uniform(1.6, 3.6), 255)
    scuff_m = np.clip(blur(scuff.result(), 0.9) * 1.4, 0.0, 1.0)
    col = mix(col, SAND_DARK[None, None, :] * (0.9 + 0.2 * grit[..., None]), scuff_m * 0.55)
    hgt = hgt - 0.9 * scuff_m
    # boot prints: sole and heel pairs
    prints = Layer()
    for _ in range(16):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        ang = rng.uniform(0, 2 * np.pi)
        ca, sa = np.cos(ang), np.sin(ang)
        for k in range(2):
            side = (k - 0.5) * 22.0
            px, py = cx - sa * side, cy + ca * side
            prints.ellipse(px + ca * 12, py + sa * 12, 15, 8.5, ang, 255)
            prints.ellipse(px - ca * 12, py - sa * 12, 7.5, 7, ang, 255)
    pm = np.clip(blur(prints.result(), 0.8), 0.0, 1.0)
    col = mix(col, SAND_DARK[None, None, :] * 0.9, pm * 0.45)
    hgt = hgt - 1.6 * pm
    return col, hgt


WOOD = np.array([0.255, 0.170, 0.150])
WOOD_GAP = np.array([0.045, 0.03, 0.026])
HB_W = 32
HB_L = 4
HB_T = N // HB_W  # 16 cells per tile


def herringbone_ids():
    """Plank id, orientation (0 = along x, 1 = along y) and position inside the plank for every cell [x][y]."""
    cell_id = -np.ones((HB_T, HB_T), dtype=int)
    cell_dir = np.zeros((HB_T, HB_T), dtype=int)
    cell_pos = np.zeros((HB_T, HB_T), dtype=int)
    anchors = sorted({((i + 4 * j) % HB_T, (i - 4 * j) % HB_T) for i in range(-20, 21) for j in range(-20, 21)})
    for index, (ax, ay) in enumerate(anchors):
        for k in range(HB_L):
            for (x, y, d) in ((ax + k, ay, 0), (ax + 4, ay - 3 + k, 1)):
                cell_id[x % HB_T, y % HB_T] = index * 2 + d
                cell_dir[x % HB_T, y % HB_T] = d
                cell_pos[x % HB_T, y % HB_T] = k
    return cell_id, cell_dir, cell_pos


def casino_field():
    cell_id, cell_dir, cell_pos = herringbone_ids()
    cx = _XX // HB_W
    cy = _YY // HB_W
    pid = cell_id[cx, cy]
    direction = cell_dir[cx, cy]
    along_cells = cell_pos[cx, cy]
    lx = _XX % HB_W
    ly = _YY % HB_W
    u = np.where(direction == 0, along_cells * HB_W + lx, along_cells * HB_W + ly).astype(float)  # along plank
    v = np.where(direction == 0, ly, lx).astype(float)  # across plank
    length = HB_L * HB_W
    dist = np.minimum(np.minimum(u, length - 1 - u), np.minimum(v, HB_W - 1 - v))
    rng = np.random.RandomState(501)
    ptone = rng.uniform(0.80, 1.22, pid.max() + 1)
    phue = rng.uniform(-0.03, 0.03, pid.max() + 1)
    pt = ptone[pid]
    ph = phue[pid]
    grain_h = fbm(502, 5.0, 100.0, 3)
    grain = np.where(direction == 0, grain_h, grain_h.T)
    col = WOOD[None, None, :] * pt[..., None]
    col = col + np.stack([ph, ph * 0.3, -ph * 0.5], -1)
    col = col * (1.0 + 0.11 * grain)[..., None]
    col = col * (1.0 + 0.05 * fbm(503, 160.0, 160.0, 2))[..., None]
    hgt = 0.35 * grain + 0.3 * fbm(504, 40.0, 40.0, 2)
    # worn, sanded spots in front of the tables (lighter, smoother)
    worn = smoothstep(0.85, 1.9, fbm(505, 3.5, 3.5, 2))
    col = col * (1.0 + 0.22 * worn)[..., None]
    # spilled drinks: dark reddish blotches with a drying rim
    sn = fbm(506, 6.0, 6.0, 3)
    stain = smoothstep(1.25, 1.55, sn)
    rim = np.clip(1.0 - np.abs(sn - 1.25) / 0.09, 0.0, 1.0) * 0.6
    col = mix(col, col * np.array([0.52, 0.40, 0.36])[None, None, :], np.clip(stain * 0.8 + rim * 0.3, 0, 1))
    # dark joints and bevels
    t = smoothstep(0.6, 2.2, dist)
    col = mix(np.broadcast_to(WOOD_GAP, col.shape), col, t)
    col = col * (0.82 + 0.18 * smoothstep(1.0, 6.0, dist))[..., None]
    hgt = hgt * 0.6 + 2.2 * smoothstep(0.6, 4.5, dist) - 0.4 * stain
    return col, hgt


MUD_BROWN = np.array([0.175, 0.135, 0.098])
RUST = np.array([0.30, 0.17, 0.10])


def prison_field():
    # the original Prison.png (commit 6db9aa611): dark blue-grey cobbles with light mortar
    col = np.asarray(git_source('materials/textures/Prison.png', '6db9aa611')).astype(float) / 255.0
    lum = col.mean(-1)
    low = blur(lum, 1.6)
    # mortar = the light parts between the cobbles
    mortar = smoothstep(0.30, 0.42, low)
    grit = fbm(601, 130.0, 130.0, 2)
    mud = MUD_BROWN[None, None, :] * (0.85 + 0.25 * lum[..., None] / 0.3) * (1.0 + 0.08 * grit[..., None])
    col = mix(col, np.clip(mud, 0, 1), mortar * 0.92)
    # damp darkening on the cobbles
    damp = smoothstep(0.2, 1.4, fbm(602, 5.0, 5.0, 3))
    col = col * (1.0 - 0.18 * damp)[..., None]
    # rust stains
    rn = fbm(603, 4.5, 4.5, 3)
    rust = smoothstep(0.85, 1.6, rn) * (0.6 + 0.4 * smoothstep(-1.0, 1.0, fbm(604, 40.0, 40.0, 2)))
    col = mix(col, RUST[None, None, :] * (0.7 + 0.5 * lum[..., None] / 0.3), rust * 0.32)
    # straw wisps
    sp = Sprites(wrap=True)
    draw_straws(sp, straw_segments(605, 34, (0, 0, N, N), (22, 42)), (0.50, 0.40, 0.20))
    sc, sa, _ = sp.result()
    col = mix(col, sc, sa * 0.92)
    return col, None


# ---------------------------------------------------------------------------------------------------------------
# arena, torture, workshop (F2 batch 4): every layer is truly periodic

def wrap_dist(a, b):
    d = np.abs(a - b) % N
    return np.minimum(d, N - d)


def row_layout(seed, rows, min_w, max_w, warp_amp, warp_seed):
    """Wrapping rows of slabs / planks. Every row is cut into pieces of random width (min_w..max_w, wrapping
    around the tile), the coordinates are warped by periodic noise so the joints are not ruler straight.
    Returns piece id, distance to the nearest joint in pixels and the number of pieces."""
    rng = np.random.RandomState(seed)
    row_h = N // rows
    xw = (_XX + warp_amp * fbm(warp_seed, 7.0, 7.0, 2)) % N
    yw = (_YY + warp_amp * fbm(warp_seed + 1, 7.0, 7.0, 2)) % N
    row = np.minimum((yw // row_h).astype(int), rows - 1)
    ry = yw - row * row_h
    dist = np.minimum(ry, row_h - ry)
    pid = np.zeros((N, N), dtype=int)
    count = 0
    for r in range(rows):
        widths = []
        total = 0.0
        while total < N:
            widths.append(rng.uniform(min_w, max_w))
            total += widths[-1]
        widths = np.array(widths) * N / total
        cuts = (rng.uniform(0, N) + np.concatenate([[0.0], np.cumsum(widths)[:-1]])) % N
        cuts.sort()
        mask = row == r
        xs = xw[mask]
        idx = np.searchsorted(cuts, xs, 'right') - 1
        pid[mask] = count + idx % len(cuts)
        dx = np.min(wrap_dist(xs[:, None], cuts[None, :]), axis=1)
        dist[mask] = np.minimum(dist[mask], dx)
        count += len(cuts)
    return pid, dist, count


ARENA_SAND = np.array([0.345, 0.283, 0.212])
BLOOD = np.array([0.155, 0.055, 0.045])


def arena_field():
    tone = fbm(701, 3.5, 3.5, 3)
    lump = fbm(702, 24.0, 24.0, 3)
    grit = fbm(703, 190.0, 190.0, 2)
    col = ARENA_SAND[None, None, :] * (1.0 + 0.07 * tone[..., None] + 0.05 * lump[..., None] + 0.06 * grit[..., None])
    hgt = 0.45 * lump + 0.4 * grit + 0.15 * tone
    rng = np.random.RandomState(704)
    # gravel: small pebbles, lighter and darker
    light = Layer()
    dark = Layer()
    for k in range(1100):
        r = rng.uniform(1.6, 4.6)
        target = light if k % 2 == 0 else dark
        target.ellipse(rng.uniform(0, N), rng.uniform(0, N), r, r * rng.uniform(0.6, 1.0), rng.uniform(0, np.pi), 255)
    lm = np.clip(blur(light.result(), 0.5) * 1.3, 0.0, 1.0)
    dm = np.clip(blur(dark.result(), 0.5) * 1.3, 0.0, 1.0)
    col = mix(col, np.array([0.47, 0.39, 0.29])[None, None, :] * (0.9 + 0.2 * grit[..., None]), lm * 0.6)
    col = mix(col, np.array([0.20, 0.15, 0.11])[None, None, :], dm * 0.6)
    hgt = hgt + 1.3 * lm + 0.9 * dm
    # raked / scratched grooves: groups of parallel lines
    scratch = Layer()
    for _ in range(14):
        x, y = rng.uniform(0, N), rng.uniform(0, N)
        ang = rng.uniform(0, 2 * np.pi)
        curve = rng.uniform(-0.04, 0.04)
        length = rng.uniform(90, 230)
        for k in range(rng.randint(2, 5)):
            off = (k - 1.0) * rng.uniform(5.0, 8.0)
            pts = []
            for t in np.linspace(0.0, 1.0, 12):
                a = ang + curve * t * length * 0.1
                pts.append((x - np.sin(ang) * off + np.cos(a) * length * t,
                            y + np.cos(ang) * off + np.sin(a) * length * t))
            scratch.line(pts, rng.uniform(1.4, 2.4), 255)
    sm = np.clip(blur(scratch.result(), 0.8) * 1.3, 0.0, 1.0)
    col = mix(col, np.array([0.19, 0.145, 0.105])[None, None, :], sm * 0.6)
    hgt = hgt - 1.8 * sm
    # worn, packed ground
    worn = smoothstep(0.7, 1.8, fbm(705, 3.0, 3.0, 2))
    col = col * (1.0 - 0.10 * worn)[..., None]
    # blood: dark brown-red stains with a drying rim, plus a few drag smears
    bn = fbm(706, 5.5, 5.5, 3)
    stain = smoothstep(1.3, 1.6, bn)
    rim = np.clip(1.0 - np.abs(bn - 1.3) / 0.1, 0.0, 1.0)
    col = mix(col, BLOOD[None, None, :] * (0.85 + 0.3 * grit[..., None]), np.clip(stain * 0.78 + rim * 0.22, 0, 0.85))
    hgt = hgt - 0.5 * stain
    smear = Layer()
    for _ in range(9):
        x, y = rng.uniform(0, N), rng.uniform(0, N)
        ang = rng.uniform(0, 2 * np.pi)
        smear.line([(x, y), (x + np.cos(ang) * 60, y + np.sin(ang) * 60)], rng.uniform(5, 9), 255)
    smm = np.clip(blur(smear.result(), 2.5) * 1.2, 0.0, 1.0)
    col = mix(col, BLOOD[None, None, :] * 1.1, smm * 0.4)
    return col, hgt


SLAB = np.array([0.238, 0.196, 0.186])


def torture_field():
    pid, dist, count = row_layout(801, 4, 120, 230, 7.0, 802)
    rng = np.random.RandomState(803)
    tone = rng.uniform(0.82, 1.18, count)[pid]
    hue = rng.uniform(-0.02, 0.025, count)[pid]
    mottle = fbm(804, 14.0, 14.0, 3)
    grit = fbm(805, 170.0, 170.0, 2)
    col = SLAB[None, None, :] * tone[..., None] + np.stack([-hue * 0.3, hue * 0.1, hue * 0.5], -1) * 0.5
    col = col * (1.0 + 0.10 * mottle + 0.07 * grit)[..., None]
    hgt = 0.5 * mottle + 0.4 * grit
    # wet patches: darker, a little bluer
    wet = smoothstep(0.1, 1.3, fbm(806, 4.0, 4.0, 3))
    col = col * (1.0 - 0.22 * wet)[..., None] * np.array([0.98, 1.0, 1.03])[None, None, :]
    hgt = hgt * (1.0 - 0.5 * wet)
    # dark stains
    sn = fbm(807, 5.0, 5.0, 3)
    stain = smoothstep(1.2, 1.6, sn)
    col = mix(col, np.array([0.085, 0.065, 0.06])[None, None, :] * (0.85 + 0.3 * grit[..., None]), stain * 0.8)
    # dark, wet joints with a bevel
    t = smoothstep(0.8, 3.2, dist)
    col = mix(np.broadcast_to(np.array([0.045, 0.047, 0.052]), col.shape), col, t)
    hgt = hgt * 0.7 + 2.6 * smoothstep(0.8, 5.0, dist)
    # drain grooves: short curved channels
    rng2 = np.random.RandomState(808)
    groove = Layer()
    for _ in range(5):
        x, y = rng2.uniform(0, N), rng2.uniform(0, N)
        ang = rng2.uniform(0, 2 * np.pi)
        curve = rng2.uniform(-0.08, 0.08)
        length = rng2.uniform(70, 150)
        pts = []
        for tt in np.linspace(0.0, 1.0, 12):
            a = ang + curve * tt * length * 0.1
            pts.append((x + np.cos(a) * length * tt, y + np.sin(a) * length * tt))
        groove.line(pts, rng2.uniform(4.0, 6.0), 255)
    gm = np.clip(blur(groove.result(), 0.9), 0.0, 1.0)
    col = mix(col, np.array([0.04, 0.042, 0.048])[None, None, :], gm * 0.85)
    hgt = hgt - 3.0 * gm
    # iron grates: dark recess with raised bars
    back = Layer()
    bars = Layer()
    for _ in range(3):
        cx, cy = rng2.uniform(0, N), rng2.uniform(0, N)
        w, h = 46, 30
        back.polygon([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2),
                      (cx - w / 2, cy + h / 2)], 255)
        for k in range(7):
            bx = cx - w / 2 + 4 + k * (w - 8) / 6.0
            bars.line([(bx, cy - h / 2 + 2), (bx, cy + h / 2 - 2)], 3.0, 255)
    bm = np.clip(back.result(), 0.0, 1.0)
    brm = np.clip(bars.result(), 0.0, 1.0)
    col = mix(col, np.array([0.03, 0.03, 0.034])[None, None, :], bm * 0.92)
    col = mix(col, np.array([0.16, 0.13, 0.11])[None, None, :] * (0.8 + 0.4 * grit[..., None]), brm * 0.9)
    hgt = hgt - 3.2 * bm + 3.6 * brm
    return col, hgt


WORKSHOP_PLANK = np.array([0.262, 0.205, 0.176])
IRON = np.array([0.135, 0.13, 0.13])
RUST_ORANGE = np.array([0.30, 0.15, 0.08])


def workshop_field():
    pid, dist, count = row_layout(901, 8, 210, 340, 3.5, 902)
    rng = np.random.RandomState(903)
    tone = rng.uniform(0.80, 1.18, count)[pid]
    hue = rng.uniform(-0.02, 0.02, count)[pid]
    grain = fbm(904, 4.0, 110.0, 3)
    grit = fbm(905, 150.0, 150.0, 2)
    col = WORKSHOP_PLANK[None, None, :] * tone[..., None] + np.stack([hue, hue * 0.4, -hue * 0.5], -1) * 0.5
    col = col * (1.0 + 0.12 * grain + 0.05 * grit)[..., None]
    hgt = 0.45 * grain + 0.25 * grit
    # soot: dark, slightly cool darkening in broad patches
    soot = smoothstep(-0.2, 1.4, fbm(906, 3.5, 3.5, 3))
    col = col * (1.0 - 0.30 * soot)[..., None] * np.array([1.0, 0.98, 0.96])[None, None, :]
    # dark joints
    t = smoothstep(0.6, 2.6, dist)
    col = mix(np.broadcast_to(np.array([0.03, 0.025, 0.024]), col.shape), col, t)
    col = col * (0.85 + 0.15 * smoothstep(1.0, 5.0, dist))[..., None]
    hgt = hgt + 2.0 * smoothstep(0.6, 4.0, dist)
    # oil: dark bluish-black blotches
    oil = smoothstep(1.35, 1.65, fbm(907, 6.5, 6.5, 3))
    col = mix(col, np.array([0.045, 0.045, 0.055])[None, None, :], oil * 0.85)
    hgt = hgt - 0.6 * oil
    # rust spots: small orange-brown flecks
    rust = smoothstep(1.5, 2.1, fbm(908, 26.0, 26.0, 2)) * smoothstep(0.0, 1.2, fbm(909, 4.0, 4.0, 2))
    col = mix(col, RUST_ORANGE[None, None, :] * (0.8 + 0.4 * grit[..., None]), rust * 0.6)
    # iron plates with rivets
    plates = Layer()
    rivets = Layer()
    for (cx, cy, w, h) in ((96, 120, 100, 60), (330, 290, 80, 100), (150, 430, 110, 52)):
        plates.polygon([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2),
                        (cx - w / 2, cy + h / 2)], 255)
        for sx in (-1, 1):
            for sy in (-1, 1):
                rivets.ellipse(cx + sx * (w / 2 - 7), cy + sy * (h / 2 - 7), 3.2, 3.2, 0.0, 255)
    pm = np.clip(plates.result(), 0.0, 1.0)
    edge = np.clip(pm - blur(pm, 2.5), 0.0, 1.0)
    rv = np.clip(blur(rivets.result(), 0.6) * 1.3, 0.0, 1.0)
    plate_col = IRON[None, None, :] * (0.85 + 0.35 * (grit[..., None] * 0.5 + 0.5)) * (1.0 - 0.3 * soot)[..., None]
    col = mix(col, plate_col, pm)
    plate_rust = pm * smoothstep(1.1, 1.7, fbm(911, 10.0, 10.0, 3)) * 0.55
    col = mix(col, RUST_ORANGE[None, None, :], plate_rust)
    col = mix(col, col * 1.5, rv * 0.7)
    col = col * (1.0 - 0.6 * edge)[..., None]
    hgt = hgt + 3.0 * pm + 2.5 * rv - 1.2 * edge
    return col, hgt


# ---------------------------------------------------------------------------------------------------------------
# portal, portal wave (F2 batch 5): every layer is truly periodic; the wooden bridge atlas follows below

PORTAL_STONE = np.array([0.182, 0.172, 0.208])
WAVE_STONE = np.array([0.165, 0.212, 0.222])


def rune_layer(seed, count, glyph, width):
    """Hairline rune glyphs: a stem plus a few short straight strokes (horizontal, vertical, diagonal) inside a
    small box."""
    rng = np.random.RandomState(seed)
    layer = Layer()
    for _ in range(count):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        half = glyph * rng.uniform(0.7, 1.1)
        pts = [(rng.randint(0, 3) - 1, rng.randint(0, 3) - 1) for _ in range(rng.randint(3, 6))]
        if rng.randint(0, 2) == 0:
            layer.line([(cx, cy - half), (cx, cy + half)], width, 255)
        else:
            layer.line([(cx - half, cy), (cx + half, cy)], width, 255)
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            if a == b:
                continue
            layer.line([(cx + a[0] * half, cy + a[1] * half), (cx + b[0] * half, cy + b[1] * half)], width, 255)
    return layer.result()


def portal_field():
    pid, dist, count = row_layout(1001, 3, 150, 270, 6.0, 1002)
    rng = np.random.RandomState(1003)
    tone = rng.uniform(0.84, 1.16, count)[pid]
    hue = rng.uniform(-0.02, 0.02, count)[pid]
    mottle = fbm(1004, 12.0, 12.0, 3)
    grit = fbm(1005, 160.0, 160.0, 2)
    col = PORTAL_STONE[None, None, :] * tone[..., None] + np.stack([hue * 0.6, -hue * 0.3, hue * 0.8], -1) * 0.4
    col = col * (1.0 + 0.10 * mottle + 0.07 * grit)[..., None]
    hgt = 0.5 * mottle + 0.4 * grit
    # worn, smoother patches where the stone is walked
    worn = smoothstep(0.3, 1.5, fbm(1006, 3.0, 3.0, 2))
    col = col * (1.0 + 0.10 * worn)[..., None]
    hgt = hgt * (1.0 - 0.4 * worn)
    # dark grimy joints with a bevel
    t = smoothstep(0.8, 3.0, dist)
    col = mix(np.broadcast_to(np.array([0.045, 0.042, 0.058]), col.shape), col, t)
    col = col * (0.86 + 0.14 * smoothstep(1.0, 6.0, dist))[..., None]
    hgt = hgt * 0.7 + 2.4 * smoothstep(0.8, 5.0, dist)
    # faint violet bloom in some patches
    bloom = smoothstep(0.6, 1.8, fbm(1007, 4.5, 4.5, 3))
    col = mix(col, col * np.array([1.08, 0.96, 1.22])[None, None, :], bloom * 0.6)
    # hairline rune grooves: glyphs plus a few thin groove lines
    runes = np.clip(blur(rune_layer(1008, 30, 13, 1.3), 0.5) * 1.4, 0.0, 1.0)
    rng2 = np.random.RandomState(1009)
    lines = Layer()
    for _ in range(7):
        x, y = rng2.uniform(0, N), rng2.uniform(0, N)
        ang = rng2.choice([0.0, np.pi / 2, np.pi / 4, -np.pi / 4]) + rng2.uniform(-0.04, 0.04)
        length = rng2.uniform(60, 140)
        lines.line([(x, y), (x + np.cos(ang) * length, y + np.sin(ang) * length)], 1.2, 255)
    lm = np.clip(blur(lines.result(), 0.5) * 1.4, 0.0, 1.0)
    groove = np.clip(runes + lm * 0.8, 0.0, 1.0)
    col = mix(col, np.array([0.06, 0.045, 0.085])[None, None, :], groove * 0.75)
    col = mix(col, col * np.array([1.0, 0.95, 1.35])[None, None, :], blur(groove, 1.6) * 0.35)
    hgt = hgt - 2.6 * groove
    return col, hgt


def portal_wave_field():
    pid, dist, count = row_layout(1101, 7, 70, 150, 3.0, 1102)
    rng = np.random.RandomState(1103)
    tone = rng.uniform(0.80, 1.18, count)[pid]
    hue = rng.uniform(-0.02, 0.02, count)[pid]
    mottle = fbm(1104, 16.0, 16.0, 3)
    grit = fbm(1105, 190.0, 190.0, 2)
    col = WAVE_STONE[None, None, :] * tone[..., None] + np.stack([-hue * 0.5, hue * 0.2, hue * 0.6], -1) * 0.4
    col = col * (1.0 + 0.11 * mottle + 0.08 * grit)[..., None]
    hgt = 0.55 * mottle + 0.4 * grit
    # damp, cooler patches
    damp = smoothstep(0.2, 1.4, fbm(1106, 3.5, 3.5, 3))
    col = col * (1.0 - 0.15 * damp)[..., None] * np.array([0.97, 1.0, 1.05])[None, None, :]
    # dark joints
    t = smoothstep(0.7, 2.8, dist)
    col = mix(np.broadcast_to(np.array([0.035, 0.042, 0.055]), col.shape), col, t)
    col = col * (0.85 + 0.15 * smoothstep(1.0, 5.0, dist))[..., None]
    hgt = hgt * 0.7 + 2.2 * smoothstep(0.7, 4.5, dist)
    # concentric wave grooves around the tile centre (distance on the torus, so the pattern is periodic), warped
    # by noise and broken into arcs
    dx = wrap_dist(_XX + 0.0, N / 2.0)
    dy = wrap_dist(_YY + 0.0, N / 2.0)
    radius = np.sqrt(dx ** 2 + dy ** 2) + 3.0 * fbm(1107, 3.0, 3.0, 2)
    phase = radius / 32.0
    ring = np.abs(phase - np.round(phase)) * 32.0
    groove = 1.0 - smoothstep(0.8, 2.6, ring)
    arcs = smoothstep(-0.4, 0.5, fbm(1108, 2.5, 2.5, 2))
    groove = np.clip(groove * arcs, 0.0, 1.0)
    col = mix(col, np.array([0.05, 0.065, 0.095])[None, None, :], groove * 0.8)
    col = mix(col, col * np.array([0.95, 1.05, 1.30])[None, None, :], blur(groove, 2.0) * 0.30)
    hgt = hgt - 2.0 * groove
    return col, hgt


# wooden bridge atlas -------------------------------------------------------------------------------------------

def mesh_uv_triangles(mesh_path):
    """Texture coordinates and triangle list of models/WoodBridge.mesh (OGRE binary mesh v1.8, one sub mesh, 48
    byte vertices with the texture coordinates at offset 24, 16 bit indices)."""
    import struct
    with open(mesh_path, 'rb') as f:
        data = f.read()
    found = {}

    def walk(pos, end):
        end = min(end, len(data))  # the length of the mesh chunk is a little too large in this file
        while pos + 6 <= end:
            cid, ln = struct.unpack_from('<HI', data, pos)
            body = pos + 6
            if cid == 0x3000:
                walk(body + 1, pos + ln)
            elif cid == 0x5000:
                found['count'], = struct.unpack_from('<I', data, body)
                walk(body + 4, pos + ln)
            elif cid == 0x5200:
                walk(body + 4, pos + ln)
            elif cid == 0x5210:
                found['verts'] = np.frombuffer(data[body:body + found['count'] * 48], dtype='<f4').reshape(-1, 12)
            elif cid == 0x4000:
                e = data.index(b'\n', body) + 1
                icount, = struct.unpack_from('<I', data, e + 1)
                found['idx'] = np.frombuffer(data[e + 6:e + 6 + icount * 2], dtype='<u2').reshape(-1, 3)
            pos += ln

    walk(24, len(data))
    return found['verts'][:, 6:8].astype(float), found['idx']


def id_map_grow(ids, steps):
    """Fills the pixels with id 0 around the painted ones with the neighbouring id (steps pixels wide)."""
    out = ids.copy()
    for _ in range(steps):
        empty = out == 0
        pad = np.pad(out, 1)
        best = np.zeros_like(out)
        for oy in (0, 1, 2):
            for ox in (0, 1, 2):
                nb = pad[oy:oy + N, ox:ox + N]
                best = np.where((best == 0) & (nb != 0), nb, best)
        out = np.where(empty, best, out)
    return out


def bridge_atlas(mesh_path):
    """Repaints the UV atlas of the wooden bridge. Every quad (two triangles) of the mesh is one plank; the
    planks are painted on the pixels of the mesh UVs plus a 14 px padding (no texture filtering bleed), the rest
    of the atlas is a neutral flat colour. Returns colour, height, painted zone and the pixels used by the UVs."""
    uv, tris = mesh_uv_triangles(mesh_path)
    ids_img = Image.new('I', (N, N), 0)
    draw = ImageDraw.Draw(ids_img)
    count = len(tris) // 2
    boxes = np.zeros((count + 1, 4))
    for i in range(count):
        pts = uv[np.concatenate([tris[2 * i], tris[2 * i + 1]])] * N
        boxes[i + 1] = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
        for tri in (tris[2 * i], tris[2 * i + 1]):
            draw.polygon([(uv[k, 0] * N, uv[k, 1] * N) for k in tri], fill=i + 1)
    ids = np.asarray(ids_img).astype(int)
    covered = ids != 0
    ids = id_map_grow(ids, 14)
    zone = ids != 0
    rng = np.random.RandomState(1201)
    tone = rng.uniform(0.84, 1.16, count + 1)
    hue = rng.uniform(-0.03, 0.03, count + 1)
    off_y = rng.randint(0, N, count + 1)
    off_x = rng.randint(0, N, count + 1)
    yy = (_YY + off_y[ids]) % N
    xx = (_XX + off_x[ids]) % N
    ga = fbm(1202, 3.0, 70.0, 3)[yy, xx]
    gb = fbm(1203, 2.0, 22.0, 3)[yy, xx]
    grit = fbm(1204, 150.0, 150.0, 2)
    base = np.array([0.435, 0.348, 0.283])
    col = base[None, None, :] * tone[ids][..., None] + np.stack([hue[ids] * 0.6, hue[ids] * 0.2, -hue[ids] * 0.5], -1) * 0.5
    # weathering: silvery grey streaks along the grain
    silver = smoothstep(0.3, 1.6, gb)
    col = mix(col, np.array([0.40, 0.375, 0.345])[None, None, :] * tone[ids][..., None], silver * 0.45)
    col = col * (1.0 + 0.12 * ga + 0.05 * grit)[..., None]
    hgt = 0.6 * ga + 0.3 * gb + 0.25 * grit
    # dark joints at the plank border (bounding box of the quad)
    edge = np.minimum(np.minimum(_YY - boxes[ids, 1], boxes[ids, 3] - _YY),
                      np.minimum(_XX - boxes[ids, 0], boxes[ids, 2] - _XX))
    t = smoothstep(0.2, 2.2, edge)
    col = mix(np.broadcast_to(np.array([0.045, 0.036, 0.030]), col.shape), col, t)
    col = col * (0.78 + 0.22 * smoothstep(1.0, 7.0, edge))[..., None]
    hgt = hgt * 0.7 + 2.0 * smoothstep(0.2, 4.0, edge)
    # dirt: dark brown blotches, more along the joints
    dirt = smoothstep(0.2, 1.7, fbm(1205, 5.0, 5.0, 3)) * 0.5 + (1.0 - smoothstep(2.0, 10.0, edge)) * 0.35
    col = mix(col, np.array([0.135, 0.105, 0.075])[None, None, :], np.clip(dirt, 0.0, 0.8) * 0.6)
    # cracks along the grain
    rng2 = np.random.RandomState(1206)
    cracks = Layer()
    for _ in range(40):
        x, y = rng2.uniform(0, N), rng2.uniform(0, N)
        length = rng2.uniform(30, 90)
        cracks.line([(x, y), (x + length, y + rng2.uniform(-2, 2))], 1.2, 255)
    cm = np.clip(blur(cracks.result(), 0.5) * 1.4, 0.0, 1.0) * 0.8
    col = mix(col, np.array([0.08, 0.06, 0.045])[None, None, :], cm)
    hgt = hgt - 1.5 * cm
    # nail heads near both ends of the wide planks, with a rust streak running down
    nails = Layer()
    streak = Layer()
    for i in range(1, count + 1):
        w = boxes[i, 2] - boxes[i, 0]
        h = boxes[i, 3] - boxes[i, 1]
        if w < 60 or h < 14:
            continue
        sy = (boxes[i, 1] + boxes[i, 3]) * 0.5 + rng2.uniform(-h * 0.22, h * 0.22)
        for sx in (boxes[i, 0] + 11.0, boxes[i, 2] - 11.0):
            nails.ellipse(sx, sy, 2.6, 2.6, 0.0, 255)
            streak.line([(sx, sy), (sx + rng2.uniform(-0.5, 0.5), sy + rng2.uniform(5, 11))], 1.6, 255)
    nm = np.clip(blur(nails.result(), 0.5) * 1.4, 0.0, 1.0)
    sm = np.clip(blur(streak.result(), 0.8) * 1.4, 0.0, 1.0)
    rim = np.clip(blur(nm, 1.6) - nm, 0.0, 1.0)
    col = mix(col, np.array([0.30, 0.24, 0.19])[None, None, :], np.clip(rim * 1.2, 0.0, 0.5))
    col = mix(col, np.array([0.11, 0.07, 0.05])[None, None, :], sm * 0.45)
    col = mix(col, np.array([0.055, 0.050, 0.048])[None, None, :], nm * 0.95)
    hgt = hgt + 2.2 * nm - 0.6 * sm
    # outside the painted zone: neutral dark grey-brown, flat normal
    col = np.where(zone[..., None], col, np.array([0.20, 0.17, 0.15])[None, None, :])
    hgt = np.where(zone, hgt, 0.0)
    return col, hgt, zone, covered


# ---------------------------------------------------------------------------------------------------------------

ROOMS = {
    'dormitory': {
        'field': dormitory_field, 'band': dormitory_band, 'strength': 1.4,
        # file name -> (exposed sides, normal map name)
        'pieces': {'Dormitory1111': ('', 'Dormitory1111Normal'), 'Dormitory1011': ('B', 'Dormitory1011Normal'),
                   'Dormitory1100': ('TR', 'Dormitory1100Normal'), 'Dormitory': ('', 'DormitoryNormal')},
    },
    'library': {
        'field': library_field, 'band': library_band, 'strength': 1.3,
        'pieces': {'Library0000': ('TBLR', 'Library0000Normal'), 'Library0001': ('TBL', 'Library0001Normal'),
                   'Library0101': ('TB', 'Library0101Normal'), 'Library1011': ('T', 'Library1011Normal'),
                   'Library0011': ('TL', 'Library1100Normal'), 'Library1111': ('', 'Library1111Normal')},
    },
    'hatchery': {
        'field': hatchery_field, 'band': hatchery_band, 'strength': 1.15, 'rot_invariant': False,
        'pieces': {'Farm0000': ('TBLR', 'Farm0000Normal'), 'Farm1000': ('TBL', 'Farm1000Normal'),
                   'Farm1010': ('TB', 'Farm1010Normal'), 'Farm1011': ('T', 'Farm1011Normal'),
                   'Farm1100': ('TL', 'Farm1100Normal'), 'Farm': ('', 'FarmNormal')},
    },
    'dungeonTemple': {
        'field': temple_field, 'band': None, 'strength': 1.3, 'rot_invariant': True,
        'pieces': {'DungeonTempleFloor': ('', 'DungeonTempleFloorNormal')},
    },
    'treasury': {
        'field': treasury_field, 'band': None, 'strength': 1.3, 'rot_invariant': True,
        'pieces': {'Treasury': ('', 'TreasuryNormal')},
    },
    'crypt': {
        # the existing CryptNormal.png is kept
        'field': crypt_field, 'band': None, 'strength': 0.0,
        'pieces': {'Crypt': ('', None)},
    },
    'trainingHall': {
        'field': training_hall_field, 'band': None, 'strength': 1.2,
        'pieces': {'TrainingHallFloor': ('', 'TrainingHallFloorNormal')},
    },
    'casino': {
        'field': casino_field, 'band': None, 'strength': 1.3,
        'pieces': {'CasinoFloor': ('', 'CasinoFloorNormal')},
    },
    'prison': {
        # the existing PrisonNormal.png is kept
        'field': prison_field, 'band': None, 'strength': 0.0,
        'pieces': {'Prison': ('', None)},
    },
    'arena': {
        # Arena.png is repainted in place: the pit meshes (ArenaLowered, ArenaFallOf) use the material Arena
        'field': arena_field, 'band': None, 'strength': 1.3,
        'pieces': {'Arena': ('', 'ArenaNormal')},
    },
    'torture': {
        'field': torture_field, 'band': None, 'strength': 1.3,
        'pieces': {'TortureFloor': ('', 'TortureFloorNormal')},
    },
    'workshop': {
        'field': workshop_field, 'band': None, 'strength': 1.3,
        'pieces': {'WorkshopFloor': ('', 'WorkshopFloorNormal')},
    },
    'portal': {
        # own file, Claimed.png / ClaimedMask.png (claimed ground, seat colour emblem mask) stay untouched
        'field': portal_field, 'band': None, 'strength': 1.3,
        'pieces': {'PortalFloor': ('', 'PortalFloorNormal')},
    },
    'portalWave': {
        'field': portal_wave_field, 'band': None, 'strength': 1.3,
        'pieces': {'PortalWaveFloor': ('', 'PortalWaveFloorNormal')},
    },
}


def build(room):
    spec = ROOMS[room]
    field_col, field_hgt = spec['field']()
    result = {}
    for name, (sides, normal_name) in spec['pieces'].items():
        col, hgt = field_col.copy(), (field_hgt.copy() if field_hgt is not None else None)
        for side in sides:
            col, hgt = spec['band'](col, hgt, side)
        result[name] = (col, hgt, normal_name, sides)
    return result, spec['strength']


def border_check(result):
    """Field borders must be mirror and transpose symmetric; opposite open sides of a piece must agree."""
    worst = 0.0
    for name, (col, hgt, _, sides) in result.items():
        if not sides:
            top, left = col[0], col[:, 0]
            worst = max(worst, np.abs(top - top[::-1]).max(), np.abs(top - left).max(),
                        np.abs(top - col[N - 1]).max(), np.abs(left - col[:, N - 1]).max())
        else:
            for a, b, la, lb in (('T', 'B', col[0], col[N - 1]), ('L', 'R', col[:, 0], col[:, N - 1])):
                if a not in sides and b not in sides:
                    worst = max(worst, np.abs(la - lb).max())
    return worst


def wrap_check(result):
    """Periodicity: the jump across the tile wrap-around divided by the typical jump between neighbouring
    pixels (about 1 or less when there is no seam). Also: the sides of a piece that are not exposed must equal
    the base piece (far away from the exposed sides)."""
    worst = 0.0
    base = None
    for name, (col, hgt, _, sides) in result.items():
        if not sides:
            base = col
    for name, (col, hgt, _, sides) in result.items():
        for axis, ends in ((0, 'TB'), (1, 'LR')):
            if any(e in sides for e in ends):
                continue  # a wall fringe on an exposed side is meant to end there
            typical = np.abs(np.diff(col, axis=axis)).mean()
            jump = np.abs(np.take(col, 0, axis=axis) - np.take(col, N - 1, axis=axis)).mean()
            worst = max(worst, jump / (typical + 1e-9))
        if sides and base is not None:
            for side, sl in (('T', (slice(0, 3), slice(200, N - 200))), ('B', (slice(N - 3, N), slice(200, N - 200))),
                             ('L', (slice(200, N - 200), slice(0, 3))), ('R', (slice(200, N - 200), slice(N - 3, N)))):
                if side not in sides:
                    diff = np.abs(col[sl] - base[sl]).max()
                    if diff > 0.02:
                        print(name, 'side', side, 'differs from the base tile by', diff)
    return worst


def seam_image(result):
    """The open floor piece rolled by half a tile in x and y (the former borders cross the middle), tiled 2x2."""
    for col, _, _, sides in result.values():
        if not sides:
            return to_image(np.tile(np.roll(col, (N // 2, N // 2), (0, 1)), (2, 2, 1)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'materials',
                                            'textures')
    seam_dir = None
    for a in sys.argv[1:]:
        if a.startswith('--seamcheck='):
            seam_dir = a.split('=', 1)[1]
    seam_rooms = ('hatchery', 'dungeonTemple', 'trainingHall', 'casino', 'prison', 'arena', 'torture', 'workshop', 'portal',
                  'portalWave') if seam_dir else ()
    for room in ROOMS:
        result, strength = build(room)
        if '--check' in sys.argv and ROOMS[room].get('rot_invariant', room in ('hatchery', 'dormitory', 'library')):
            print(room, 'max asymmetry on open borders (0..1): %.3f' % border_check(result))
        if '--check' in sys.argv and room in ('hatchery', 'trainingHall', 'casino', 'prison', 'arena', 'torture', 'workshop',
                                                          'portal', 'portalWave'):
            print(room, 'wrap seam ratio (about 1 or less = no seam): %.2f' % wrap_check(result))
        if room in seam_rooms:
            seam_image(result).save(os.path.join(seam_dir, 'f2-%s-seamcheck.png' % room.lower()))
        for name, (col, hgt, normal_name, _) in result.items():
            to_image(col).save(os.path.join(out, name + '.png'), optimize=True)
            if normal_name is not None:
                to_image(normal_map(hgt, strength)).save(os.path.join(out, normal_name + '.png'), optimize=True)
            print(name, 'mean RGB', (col.reshape(-1, 3).mean(0) * 255).round().astype(int))
    # wooden bridge atlas (repainted in place, the UV layout comes from the mesh)
    col, hgt, zone, covered = bridge_atlas(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                                                        'models', 'WoodBridge.mesh'))
    if '--check' in sys.argv:
        print('WoodBridge painted zone %.1f %% of the atlas, mesh UV pixels %.1f %%' % (zone.mean() * 100, covered.mean() * 100))
    to_image(col).convert('RGBA').save(os.path.join(out, 'WoodBridge.png'), optimize=True)
    to_image(normal_map(hgt, 1.3)).convert('RGBA').save(os.path.join(out, 'WoodBridgeNormal.png'), optimize=True)
    print('WoodBridge mean RGB of the UV pixels', (col[covered].mean(0) * 255).round().astype(int))


if __name__ == '__main__':
    main()
