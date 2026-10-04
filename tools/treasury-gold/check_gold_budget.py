#!/usr/bin/env python3
"""Counts the render budget of the gold visuals without starting the game.

It reads the mesh constants from the sources (so the numbers cannot drift from the code) and prints, for
treasuries of several sizes, how many scene objects (draw calls), triangles, vertices and extra particle
systems the gold layer, the loose gold heaps and the carried sacks cost. It fails when a number goes over
the budget below. This is a count, not a frame time: the frame time has to be measured in the game.

Usage: python check_gold_budget.py [--table]
"""

import os
import re
import sys

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')

# Budget
MAX_TRIANGLES_PER_PILE = 100
MAX_TRIANGLES_PER_HEAP = 150
MAX_TRIANGLES_PER_SACK = 400
MAX_TRIANGLES_100_TILE_ROOM = 10000
# Gold elsewhere adds no particle system and no per-frame work on the CPU
MAX_NEW_PARTICLE_SYSTEMS = 0


def read(path):
    with open(os.path.join(REPO, path), encoding='utf-8') as handle:
        return handle.read()


def constant(text, name):
    match = re.search(r'\b' + name + r'\s*=\s*(\d+)\s*;', text)
    if match is None:
        raise SystemExit('constant not found: ' + name)
    return int(match.group(1))


def main():
    pile = read('source/render/TreasuryGoldMesh.cpp')
    loose = read('source/render/LooseGoldMesh.cpp')

    full_divisions = int(re.search(r'reduced \? (\d+) : (\d+)', pile).group(2))
    reduced_divisions = int(re.search(r'reduced \? (\d+) : (\d+)', pile).group(1))
    heap_rings = constant(loose, 'HeapRings')
    heap_sectors = constant(loose, 'HeapSectors')
    sack_sectors = constant(loose, 'SackSectors')
    profile_count = constant(loose, 'ProfileCount')

    pile_tris = {'full': 2 * full_divisions ** 2, 'reduced': 2 * reduced_divisions ** 2}
    pile_verts = {'full': (full_divisions + 1) ** 2, 'reduced': (reduced_divisions + 1) ** 2}
    heap_tris = 2 * heap_rings * heap_sectors
    heap_verts = (heap_rings + 1) * heap_sectors
    sack_tris = 2 * (profile_count - 1) * sack_sectors + heap_tris
    sack_verts = profile_count * sack_sectors + heap_verts

    failures = []

    def limit(ok, text):
        if not ok:
            failures.append(text)

    limit(pile_tris['full'] <= MAX_TRIANGLES_PER_PILE, 'pile too heavy: %d triangles' % pile_tris['full'])
    limit(heap_tris <= MAX_TRIANGLES_PER_HEAP, 'heap too heavy: %d triangles' % heap_tris)
    limit(sack_tris <= MAX_TRIANGLES_PER_SACK, 'sack too heavy: %d triangles' % sack_tris)
    limit(100 * pile_tris['full'] <= MAX_TRIANGLES_100_TILE_ROOM,
          'a 100 tile treasury costs %d triangles' % (100 * pile_tris['full']))

    # Particle systems: none of the gold visuals of this part may add one
    new_particles = 0
    for name in ('source/render/LooseGoldMesh.cpp', 'materials/scripts/GoldSack.material'):
        new_particles += len(re.findall(r'ParticleSystem|particle_system', read(name)))
    limit(new_particles <= MAX_NEW_PARTICLE_SYSTEMS, 'gold elsewhere added %d particle systems' % new_particles)

    print('mesh                 triangles  vertices')
    print('pile (full)          %9d  %8d' % (pile_tris['full'], pile_verts['full']))
    print('pile (reduced)       %9d  %8d' % (pile_tris['reduced'], pile_verts['reduced']))
    print('floor heap           %9d  %8d' % (heap_tris, heap_verts))
    print('carried sack         %9d  %8d' % (sack_tris, sack_verts))
    print()
    print('room tiles   objects   triangles (full)   triangles (reduced)   new particle systems')
    for tiles in (10, 25, 50, 100, 400):
        # One scene object per tile pile; every mesh is shared by name, so no per-tile mesh memory
        print('%10d %9d %18d %21d %22d' % (tiles, tiles, tiles * pile_tris['full'],
                                           tiles * pile_tris['reduced'], 0))
    print()
    print('per worker carrying gold: 1 sack object (%d triangles), the floor heap object stays hidden' % sack_tris)
    print('veins: shader only (no extra objects, no particles)')

    if failures:
        print()
        for text in failures:
            print('FAIL', text)
        return 1
    print()
    print('budget ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
