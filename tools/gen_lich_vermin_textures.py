# Paints the three textures of the 3D grave vermin (LichVerminShell, LichVerminMaggot, LichVerminWorm) into
# materials/textures. Procedural: mottled noise, chitin ribs, body rings. Usage: python gen_lich_vermin_textures.py <textures dir>
import math
import sys

import numpy as np
from PIL import Image

SIZE = 256
rng = np.random.default_rng(1207)


def noise(scale, seed):
    """Smooth tileable value noise in 0..1 with the given number of cells."""
    local = np.random.default_rng(seed)
    grid = local.random((scale, scale))
    ys = np.linspace(0, scale, SIZE, endpoint=False)
    xs = np.linspace(0, scale, SIZE, endpoint=False)
    y0 = ys.astype(int)[:, None]
    x0 = xs.astype(int)[None, :]
    fy = (ys - y0[:, 0])[:, None]
    fx = (xs - x0[0, :])[None, :]
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    y1 = (y0 + 1) % scale
    x1 = (x0 + 1) % scale
    top = grid[y0, x0] * (1 - fx) + grid[y0, x1] * fx
    bottom = grid[y1, x0] * (1 - fx) + grid[y1, x1] * fx
    return top * (1 - fy) + bottom * fy


def fbm(seed):
    return 0.55 * noise(4, seed) + 0.3 * noise(8, seed + 1) + 0.15 * noise(16, seed + 2)


def save(name, rgb, folder):
    image = np.clip(rgb, 0, 1)
    Image.fromarray((image * 255).astype(np.uint8), "RGB").save("%s/%s.png" % (folder, name))


def shell(folder):
    """Dark chitin: split line down the middle, ribbed wing covers, warm sheen, speckles."""
    v, u = np.meshgrid(np.linspace(0, 1, SIZE), np.linspace(0, 1, SIZE), indexing="ij")
    n = fbm(11)
    base = np.stack([0.11 + 0.10 * n, 0.065 + 0.06 * n, 0.04 + 0.03 * n], axis=2)
    ribs = 0.5 + 0.5 * np.cos((u - 0.5) * 2 * math.pi * 7)
    sheen = (ribs ** 3)[..., None] * np.array([0.22, 0.11, 0.035])
    base = base + sheen * (0.5 + 0.8 * n[..., None])
    split = np.exp(-((u - 0.5) / 0.012) ** 2)[..., None]
    base = base * (1 - 0.8 * split)
    speck = (rng.random((SIZE, SIZE)) > 0.985)[..., None] * 0.05
    save("LichVerminShell", base + speck, folder)


def rings(folder, name, count, light, dark, head_tint, seed):
    """Segmented soft body: pale rings with darker grooves and mottling; the front (v near 1) is darker."""
    v, u = np.meshgrid(np.linspace(0, 1, SIZE), np.linspace(0, 1, SIZE), indexing="ij")
    n = fbm(seed)
    wave = 0.5 + 0.5 * np.cos(v * 2 * math.pi * count)
    mix = (0.35 + 0.65 * wave ** 0.7)[..., None]
    rgb = np.array(dark)[None, None, :] * (1 - mix) + np.array(light)[None, None, :] * mix
    rgb = rgb * (0.82 + 0.3 * n[..., None])
    head = np.clip((v - 0.86) / 0.1, 0, 1)[..., None]
    rgb = rgb * (1 - head) + np.array(head_tint)[None, None, :] * head
    save(name, rgb, folder)


folder = sys.argv[1]
shell(folder)
rings(folder, "LichVerminMaggot", 7, (0.80, 0.70, 0.47), (0.50, 0.40, 0.22), (0.20, 0.13, 0.07), 31)
rings(folder, "LichVerminWorm", 14, (0.55, 0.22, 0.16), (0.27, 0.09, 0.07), (0.16, 0.06, 0.05), 47)
