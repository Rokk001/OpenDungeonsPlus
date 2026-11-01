#!/usr/bin/env python3
"""Paints the textures of the dirt piles and the blood stain and writes the material script that uses them.

    python tools/gen_pile_textures.py [output folder] [--check]

Writes, for every creature type of config/creatures.cfg:
    materials/textures/Pile_<Type>.png   64 x 64, colours fixed per type (table PILES below)
and
    materials/textures/BloodStain.png    128 x 128 with alpha (flat red decal)
    materials/scripts/DirtPiles.material the shared material DirtPiles, one material Pile_<Type> per type that
                                         inherits from it and only sets its texture, and the material BloodStain.

The pile meshes (models/Pile_<Type>.mesh) use the material named Pile_<Type>, the blood mesh (models/BloodStain.mesh)
the material BloodStain. The textures have no fixed UV layout: every pixel is painted from periodic noise, so any
UV unwrap looks right. Original work of the project, everything is procedural and seeded by the type name, so a
second run gives byte-identical files. Needs numpy and Pillow.

With --check nothing is written; the script only tests that the table covers exactly the creature types of
config/creatures.cfg and prints the result.
"""

import os
import re
import sys
import zlib

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILE_SIZE = 64
BLOOD_SIZE = 128

# Per creature type: base colour, accent colour (RGB 0-255) and the painting style (see paint_pile).
PILES = {
    'Kobold': ((150, 104, 60), (200, 60, 50), 'speckle'),
    'DwarfWorker': ((128, 92, 58), (80, 70, 64), 'speckle'),
    'Dwarf1': ((140, 98, 50), (245, 235, 200), 'speckle'),
    'Dwarf2': ((124, 88, 56), (90, 90, 96), 'speckle'),
    'RunelordDwarf': ((110, 82, 62), (90, 200, 255), 'sparkle'),
    'Orc': ((84, 100, 56), (235, 226, 200), 'speckle'),
    'Troll': ((92, 76, 60), (120, 170, 80), 'speckle'),
    'Goblin': ((96, 112, 50), (150, 160, 70), 'coil'),
    'PitDemon': ((60, 40, 38), (255, 120, 30), 'embers'),
    'LavaSpawn': ((58, 44, 44), (255, 150, 40), 'cracks'),
    'Rat': ((70, 56, 50), (110, 90, 80), 'speckle'),
    'Roach': ((88, 56, 32), (210, 190, 140), 'speckle'),
    'Spider': ((190, 190, 180), (120, 120, 115), 'coil'),
    'CaveHornet': ((214, 160, 40), (255, 214, 100), 'glossy'),
    'Slime': ((70, 190, 80), (190, 255, 190), 'glossy'),
    'Scarab': ((96, 70, 36), (60, 44, 24), 'heap'),
    'TentacleAlbine': ((214, 204, 190), (236, 170, 170), 'coil'),
    'TentacleGreen': ((70, 150, 70), (150, 210, 110), 'coil'),
    'Wyvern': ((100, 86, 64), (70, 140, 180), 'speckle'),
    'Dragon': ((40, 34, 34), (200, 90, 30), 'embers'),
    'Kreatur': ((40, 30, 46), (240, 230, 120), 'speckle'),
    'LizardMan': ((90, 104, 60), (200, 190, 120), 'speckle'),
    'Lich': ((140, 140, 146), (200, 200, 210), 'dust'),
    'Skeleton': ((232, 226, 208), (250, 246, 232), 'dust'),
    'Cultist': ((84, 56, 60), (180, 40, 50), 'coil'),
    'Wizard': ((110, 60, 150), (230, 200, 255), 'sparkle'),
    'Gnome': ((122, 86, 52), (200, 50, 50), 'speckle'),
    'Adventurer': ((130, 96, 64), (80, 150, 60), 'speckle'),
    'Monk': ((132, 98, 66), (235, 235, 235), 'speckle'),
    'Knight': ((118, 90, 66), (190, 50, 50), 'speckle'),
    'Defender': ((126, 100, 76), (150, 140, 130), 'heap'),
    'Elf': ((110, 110, 60), (240, 150, 190), 'speckle'),
    'DarkElf': ((44, 36, 48), (90, 70, 110), 'speckle'),
    'NatureMonster': ((66, 52, 34), (100, 200, 70), 'speckle'),
    'Champion': ((210, 170, 60), (255, 230, 120), 'sparkle'),
}

BLOOD_RGB = (150, 18, 20)


def fbm(rng, size, cells, octaves=3):
    """Periodic noise (zero mean, unit variance) on a size x size grid; cells = features per axis."""
    k = np.fft.fftfreq(size) * size
    total = np.zeros((size, size))
    for octave in range(octaves):
        white = rng.standard_normal((size, size))
        scale = 2.0 ** octave
        filt = np.exp(-(k[None, :] / (cells * scale)) ** 2 - (k[:, None] / (cells * scale)) ** 2)
        layer = np.fft.ifft2(np.fft.fft2(white) * filt).real
        layer /= layer.std() + 1e-9
        total += layer * 0.55 ** octave
    return total / (total.std() + 1e-9)


def smoothstep(a, b, x):
    """Smooth 0..1 ramp between a and b."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def paint_pile(name, base, accent, style):
    """Returns the 64 x 64 RGB texture (float 0..1) of one creature type; the style selects the accent pattern."""
    rng = np.random.RandomState(zlib.crc32(name.encode('ascii')))
    size = PILE_SIZE
    base_col = np.array(base) / 255.0
    acc_col = np.array(accent) / 255.0
    lumps = fbm(rng, size, 6.0)
    grain = fbm(rng, size, 18.0, 2)
    col = base_col[None, None, :] * (1.0 + 0.16 * lumps + 0.07 * grain)[..., None]
    detail = fbm(rng, size, 10.0)
    if style == 'speckle':
        mask = smoothstep(1.25, 1.6, detail)
        col = col * (1.0 - mask[..., None]) + acc_col[None, None, :] * mask[..., None]
    elif style == 'sparkle':
        mask = smoothstep(1.5, 1.9, fbm(rng, size, 22.0, 2))
        col = col * (1.0 - mask[..., None]) + acc_col[None, None, :] * mask[..., None]
    elif style == 'embers':
        mask = smoothstep(1.35, 1.8, fbm(rng, size, 16.0, 2))
        col = col * (1.0 - mask[..., None]) + acc_col[None, None, :] * mask[..., None]
    elif style == 'cracks':
        crack = 1.0 - smoothstep(0.0, 0.16, np.abs(fbm(rng, size, 7.0, 2)))
        col = col * (1.0 - crack[..., None]) + acc_col[None, None, :] * crack[..., None]
    elif style == 'coil':
        yy = np.arange(size)[:, None] / float(size)
        xx = np.arange(size)[None, :] / float(size)
        bands = 0.5 + 0.5 * np.sin(2.0 * np.pi * (3.0 * (xx + yy) + 0.12 * detail))
        mask = smoothstep(0.55, 0.9, bands)
        col = col * (1.0 - 0.7 * mask[..., None]) + acc_col[None, None, :] * (0.7 * mask[..., None])
    elif style == 'glossy':
        mask = smoothstep(1.1, 1.7, detail)
        col = col * (1.0 - 0.6 * mask[..., None]) + acc_col[None, None, :] * (0.6 * mask[..., None])
    elif style == 'dust':
        mask = smoothstep(0.4, 1.6, lumps)
        col = col * (1.0 - 0.5 * mask[..., None]) + acc_col[None, None, :] * (0.5 * mask[..., None])
    return np.clip(col, 0.0, 1.0)


def paint_blood():
    """Returns the 128 x 128 RGBA texture (float 0..1) of the blood stain: a dark red blotch with a ragged edge."""
    rng = np.random.RandomState(zlib.crc32(b'BloodStain'))
    size = BLOOD_SIZE
    yy, xx = np.mgrid[0:size, 0:size]
    dist = np.sqrt(((xx - size / 2.0) / (size / 2.0)) ** 2 + ((yy - size / 2.0) / (size / 2.0)) ** 2)
    edge = 0.62 + 0.14 * fbm(rng, size, 5.0, 3)
    alpha = 1.0 - smoothstep(edge - 0.06, edge + 0.04, dist)
    # a few detached droplets around the blotch
    drops = smoothstep(1.6, 2.2, fbm(rng, size, 14.0, 2)) * smoothstep(0.55, 0.75, dist) * (1.0 - smoothstep(0.85, 0.98, dist))
    alpha = np.clip(alpha + 0.9 * drops, 0.0, 1.0)
    shade = 0.55 + 0.25 * fbm(rng, size, 8.0, 2) + 0.2 * (1.0 - np.clip(dist, 0.0, 1.0))
    col = (np.array(BLOOD_RGB) / 255.0)[None, None, :] * np.clip(shade, 0.35, 1.3)[..., None]
    return np.dstack([np.clip(col, 0.0, 1.0), alpha])


def creature_names():
    """The creature type names listed in config/creatures.cfg (lines 'Name <type>' inside the definitions)."""
    names = []
    with open(os.path.join(ROOT, 'config', 'creatures.cfg'), encoding='utf-8') as handle:
        for line in handle:
            match = re.match(r'^\s+Name\s+(\S+)\s*$', line)
            if match:
                names.append(match.group(1))
    return names


def material_text():
    """The text of materials/scripts/DirtPiles.material: shared base, one child per type, the blood material."""
    lines = [
        '// Dirt piles and blood stains (textures made by tools/gen_pile_textures.py).',
        '// DirtPiles is the shared base; every Pile_<Type> only sets the texture of its creature type.',
        '',
        'material DirtPiles',
        '{',
        '    receive_shadows on',
        '',
        '    technique main',
        '    {',
        '        pass pile',
        '        {',
        '            ambient 0.8 0.8 0.8 1.0',
        '            diffuse 0.75 0.75 0.75 1.0',
        '            specular 0.0 0.0 0.0 1.0 12.5',
        '',
        '            texture_unit decalmap',
        '            {',
        '                texture White.png',
        '                tex_address_mode wrap',
        '                filtering trilinear',
        '            }',
        '        }',
        '    }',
        '}',
        '',
    ]
    for name in sorted(PILES):
        lines += [
            'material Pile_%s : DirtPiles' % name,
            '{',
            '    technique main',
            '    {',
            '        pass pile',
            '        {',
            '            texture_unit decalmap',
            '            {',
            '                texture Pile_%s.png' % name,
            '            }',
            '        }',
            '    }',
            '}',
            '',
        ]
    lines += [
        '// Flat red decal on the floor; lies a little above the tile and does not write depth',
        'material BloodStain',
        '{',
        '    receive_shadows on',
        '',
        '    technique',
        '    {',
        '        pass',
        '        {',
        '            ambient 0.8 0.8 0.8 1.0',
        '            diffuse 0.75 0.75 0.75 1.0',
        '            specular 0.2 0.1 0.1 1.0 24.0',
        '            scene_blend alpha_blend',
        '            depth_write off',
        '            depth_bias 2',
        '            cull_hardware none',
        '',
        '            texture_unit',
        '            {',
        '                texture BloodStain.png',
        '                tex_address_mode clamp',
        '                filtering trilinear',
        '            }',
        '        }',
        '    }',
        '}',
        '',
    ]
    return '\n'.join(lines)


def to_image(arr):
    """Converts a float 0..1 array (RGB or RGBA) to a Pillow image."""
    mode = 'RGBA' if arr.shape[-1] == 4 else 'RGB'
    return Image.fromarray((np.clip(arr, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), mode)


def main():
    names = creature_names()
    if sorted(names) != sorted(PILES):
        print('creature types and table differ: only in cfg', sorted(set(names) - set(PILES)),
              'only in table', sorted(set(PILES) - set(names)))
        return 1
    print('table covers all %d creature types' % len(names))
    if '--check' in sys.argv:
        return 0
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out = args[0] if args else os.path.join(ROOT, 'materials', 'textures')
    for name in sorted(PILES):
        base, accent, style = PILES[name]
        to_image(paint_pile(name, base, accent, style)).save(os.path.join(out, 'Pile_%s.png' % name), optimize=True)
    to_image(paint_blood()).save(os.path.join(out, 'BloodStain.png'), optimize=True)
    with open(os.path.join(ROOT, 'materials', 'scripts', 'DirtPiles.material'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(material_text())
    print('wrote %d pile textures, BloodStain.png and DirtPiles.material' % len(PILES))
    return 0


if __name__ == '__main__':
    sys.exit(main())
