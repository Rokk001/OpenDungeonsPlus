#!/usr/bin/env python3
"""Paints the floor dirt decals and the toilet seat texture and writes their material scripts.

    python tools/gen_dirt_decals.py [output folder]

Writes
    materials/textures/DirtStage1.png   256 x 256 RGBA, a few stains
    materials/textures/DirtStage2.png   256 x 256 RGBA, stains with litter (bone chips, scraps, straw)
    materials/textures/DirtStage3.png   256 x 256 RGBA, a dark layer of filth with wet puddles
    materials/textures/ToiletSeat.png   128 x 128 RGB, the left half (u < 0.5) is stone, the right half is wood
    materials/scripts/DirtStage.material   materials DirtStage1, DirtStage2, DirtStage3 (alpha blended decals)
    materials/scripts/ToiletSeat.material  material ToiletSeat (opaque)

The decal meshes (models/DirtStage1.mesh ...) cover one tile and use the material of the same name; the seat mesh
(models/ToiletSeat.mesh) maps the stone seat to the left half of its UV space and the wooden lid to the right half.
The decals fade to nothing at the border, so neighbouring tiles blend without a seam. Original work of the project,
everything is procedural with fixed seeds, so a second run gives byte-identical files. Needs numpy and Pillow.
"""

import os
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw

from gen_pile_textures import fbm, smoothstep, to_image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECAL_SIZE = 256
SEAT_SIZE = 128
SUPER = 2

STAIN_RGB = (74, 52, 34)
FILTH_RGB = (38, 30, 24)
PUDDLE_RGB = (72, 70, 56)
LITTER_RGBS = ((222, 214, 190), (150, 120, 78), (196, 168, 104), (110, 92, 70))
STONE_RGB = (134, 130, 124)
WOOD_RGB = (128, 84, 46)


def seeded(name):
    """A random state seeded by the texture name."""
    return np.random.RandomState(zlib.crc32(name.encode('ascii')))


def edge_fade(size):
    """Alpha factor that is 1 inside and falls to 0 at the border of the decal (so tiles blend without a seam)."""
    idx = np.arange(size)
    edge = np.minimum(idx, size - 1 - idx).astype(float)
    ramp = smoothstep(2.0, size * 0.16, edge)
    return ramp[:, None] * ramp[None, :]


def stain_alpha(rng, size, threshold, softness):
    """Alpha of blotches: noise above a threshold, with a soft edge."""
    n = fbm(rng, size, 6.0, 3)
    return smoothstep(threshold, threshold + softness, n)


def litter_layer(rng, count):
    """Returns an RGBA float image of small bits (bone chips, scraps, straw) scattered at random places."""
    big = Image.new('RGBA', (DECAL_SIZE * SUPER, DECAL_SIZE * SUPER), (0, 0, 0, 0))
    draw = ImageDraw.Draw(big)
    margin = DECAL_SIZE * 0.2
    for _ in range(count):
        cx = rng.uniform(margin, DECAL_SIZE - margin) * SUPER
        cy = rng.uniform(margin, DECAL_SIZE - margin) * SUPER
        ang = rng.uniform(0.0, np.pi)
        length = rng.uniform(5.0, 14.0) * SUPER
        width = rng.uniform(1.6, 3.4) * SUPER
        rgb = LITTER_RGBS[rng.randint(0, len(LITTER_RGBS))]
        dx, dy = np.cos(ang) * length / 2.0, np.sin(ang) * length / 2.0
        draw.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=rgb + (255,), width=int(width))
    small = big.resize((DECAL_SIZE, DECAL_SIZE), Image.BOX)
    return np.asarray(small).astype(float) / 255.0


def paint_stage(stage):
    """Returns the RGBA float image of dirt stage 1, 2 or 3."""
    size = DECAL_SIZE
    rng = seeded('DirtStage%d' % stage)
    fade = edge_fade(size)
    rgb = np.array(STAIN_RGB if stage < 3 else FILTH_RGB) / 255.0
    tone = 0.85 + 0.2 * fbm(rng, size, 14.0, 2)
    col = rgb[None, None, :] * tone[..., None]
    if stage == 1:
        alpha = stain_alpha(rng, size, 1.15, 0.5) * 0.75
    elif stage == 2:
        alpha = np.maximum(stain_alpha(rng, size, 0.55, 0.6) * 0.8, 0.0)
        bits = litter_layer(rng, 46)
        col = col * (1.0 - bits[..., 3:4]) + bits[..., :3] * bits[..., 3:4]
        alpha = np.maximum(alpha, bits[..., 3])
    else:
        alpha = np.clip(0.55 + 0.35 * smoothstep(-0.8, 0.8, fbm(rng, size, 5.0, 3)), 0.0, 1.0)
        puddle = smoothstep(1.0, 1.4, fbm(rng, size, 7.0, 3))
        pud_rgb = np.array(PUDDLE_RGB) / 255.0
        col = col * (1.0 - puddle[..., None]) + pud_rgb[None, None, :] * (0.8 + 0.4 * tone[..., None]) * puddle[..., None]
        alpha = np.maximum(alpha, puddle * 0.9)
    return np.dstack([np.clip(col, 0.0, 1.0), np.clip(alpha * fade, 0.0, 1.0)])


def paint_seat():
    """Returns the 128 x 128 RGB float image of the seat: stone on the left half, wood on the right half."""
    size = SEAT_SIZE
    rng = seeded('ToiletSeat')
    stone = np.array(STONE_RGB) / 255.0
    wood = np.array(WOOD_RGB) / 255.0
    grit = fbm(rng, size, 30.0, 2)
    mottle = fbm(rng, size, 6.0, 3)
    left = stone[None, None, :] * (1.0 + 0.10 * mottle + 0.06 * grit)[..., None]
    yy = np.arange(size)[:, None].astype(float)
    xx = np.arange(size)[None, :].astype(float)
    planks = 0.5 + 0.5 * np.sin(2.0 * np.pi * (yy / (size / 4.0)) + 1.5 * fbm(rng, size, 4.0, 2))
    right = wood[None, None, :] * (0.8 + 0.3 * planks + 0.08 * grit)[..., None]
    seam = (np.abs(yy % (size / 4.0)) < 1.5).astype(float)
    right = right * (1.0 - 0.45 * seam[..., None])
    col = np.where(xx[..., None] < size / 2.0, left, right)
    return np.clip(col, 0.0, 1.0)


def decal_material(name):
    """Material text of one alpha blended decal."""
    return '\n'.join([
        'material %s' % name,
        '{',
        '    receive_shadows on',
        '',
        '    technique',
        '    {',
        '        pass',
        '        {',
        '            ambient 0.8 0.8 0.8 1.0',
        '            diffuse 0.7 0.7 0.7 1.0',
        '            specular 0.0 0.0 0.0 1.0 12.5',
        '            scene_blend alpha_blend',
        '            depth_write off',
        '            depth_bias 1',
        '            cull_hardware none',
        '',
        '            texture_unit',
        '            {',
        '                texture %s.png' % name,
        '                tex_address_mode clamp',
        '                filtering trilinear',
        '            }',
        '        }',
        '    }',
        '}',
        ''])


def seat_material():
    """Material text of the toilet seat (opaque, stone and wood in one texture)."""
    return '\n'.join([
        'material ToiletSeat',
        '{',
        '    receive_shadows on',
        '',
        '    technique',
        '    {',
        '        pass',
        '        {',
        '            ambient 0.8 0.8 0.8 1.0',
        '            diffuse 0.75 0.75 0.75 1.0',
        '            specular 0.05 0.05 0.05 1.0 12.5',
        '',
        '            texture_unit',
        '            {',
        '                texture ToiletSeat.png',
        '                tex_address_mode wrap',
        '                filtering trilinear',
        '            }',
        '        }',
        '    }',
        '}',
        ''])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else os.path.join(ROOT, 'materials', 'textures')
    scripts = os.path.join(ROOT, 'materials', 'scripts')
    texts = ['// Floor dirt decals, one per stage (textures made by tools/gen_dirt_decals.py)', '']
    for stage in (1, 2, 3):
        to_image(paint_stage(stage)).save(os.path.join(out, 'DirtStage%d.png' % stage), optimize=True)
        texts.append(decal_material('DirtStage%d' % stage))
    with open(os.path.join(scripts, 'DirtStage.material'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(texts))
    to_image(paint_seat()).save(os.path.join(out, 'ToiletSeat.png'), optimize=True)
    with open(os.path.join(scripts, 'ToiletSeat.material'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('// Toilet seat: stone seat (left half of the UV space) and wooden lid (right half)\n')
        handle.write(seat_material())
    print('wrote DirtStage1-3.png, ToiletSeat.png and their materials')
    return 0


if __name__ == '__main__':
    sys.exit(main())
