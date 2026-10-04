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
MAX_TRIANGLES_PER_PILE = 150
MAX_TRIANGLES_PER_HEAP = 150
MAX_TRIANGLES_PER_SACK = 400
MAX_TRIANGLES_100_TILE_ROOM = 15000
# Draw calls: settled piles are drawn by one static batch per room and patch of tiles (two materials per batch)
MAX_DRAW_CALLS_100_TILE_ROOM = 18
MAX_DRAW_CALLS_400_TILE_ROOM = 40
MATERIALS_FULL = 2
MATERIALS_REDUCED = 1
# Gold elsewhere adds no particle system and no per-frame work on the CPU
MAX_NEW_PARTICLE_SYSTEMS = 0
# Effects one room may show at once (splash + dust + sparkle/sliding/rolling coins), and glow lights per patch
MAX_ROOM_EFFECTS = 16


def read(path):
    with open(os.path.join(REPO, path), encoding='utf-8') as handle:
        return handle.read()


def constant(text, name):
    match = re.search(r'\b' + name + r'\s*=\s*(\d+)\s*;', text)
    if match is None:
        raise SystemExit('constant not found: ' + name)
    return int(match.group(1))


def worst_patches(width, chunk):
    """Patches a room of the given width can touch along one axis, worst case alignment."""
    return (width - 1 + chunk - 1) // chunk + 1


def main():
    pile = read('source/render/TreasuryGoldMesh.cpp')
    loose = read('source/render/LooseGoldMesh.cpp')

    full_divisions = int(re.search(r'reduced \? (\d+) : (\d+)', pile).group(2))
    reduced_divisions = int(re.search(r'reduced \? (\d+) : (\d+)', pile).group(1))
    heap_rings = constant(loose, 'HeapRings')
    heap_sectors = constant(loose, 'HeapSectors')
    sack_sectors = constant(loose, 'SackSectors')
    profile_count = constant(loose, 'ProfileCount')

    layer = read('source/rooms/TreasuryGoldLayer.h')
    coin_sides = constant(pile, 'CoinSides')
    spill_sides = constant(pile, 'SpillSides')
    gem_faces = constant(pile, 'GemFaces')
    max_top_coins = constant(layer, 'maxTopCoins')
    max_gems = constant(layer, 'maxGems')
    max_spill_coins = constant(layer, 'maxSpillCoins')
    scatter_coins = constant(layer, 'scatterCoins')

    # Coins on top, gems and spilled coins lie in a second section (a second draw call) of the full pile mesh
    detail_tris = max_top_coins * coin_sides + max_gems * gem_faces + max_spill_coins * spill_sides
    detail_verts = max_top_coins * (coin_sides + 1) + max_gems * 6 + max_spill_coins * (spill_sides + 1)
    scatter_tris = scatter_coins * coin_sides

    pile_tris = {'full': 2 * full_divisions ** 2 + detail_tris, 'reduced': 2 * reduced_divisions ** 2}
    pile_verts = {'full': (full_divisions + 1) ** 2 + detail_verts, 'reduced': (reduced_divisions + 1) ** 2}
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
    limit(scatter_tris <= MAX_TRIANGLES_PER_PILE, 'floor scatter too heavy: %d triangles' % scatter_tris)
    limit(100 * pile_tris['full'] <= MAX_TRIANGLES_100_TILE_ROOM,
          'a 100 tile treasury costs %d triangles' % (100 * pile_tris['full']))

    # Particle systems: none of the gold visuals of this part may add one
    new_particles = 0
    for name in ('source/render/LooseGoldMesh.cpp', 'materials/scripts/GoldSack.material'):
        new_particles += len(re.findall(r'ParticleSystem|particle_system', read(name)))
    limit(new_particles <= MAX_NEW_PARTICLE_SYSTEMS, 'gold elsewhere added %d particle systems' % new_particles)

    rules = read('source/render/TreasuryCreatureRules.h')
    chunk = constant(rules, 'batchChunkSize')
    splash = int(re.search(r'splashBudget.*?Detail::full:\s*return (\d+);', rules, re.S).group(1))
    dust = int(re.search(r'dustBudget.*?Detail::full:\s*return (\d+);', rules, re.S).group(1))
    ambient = constant(rules, 'ambientBudgetFull')
    limit(splash + dust + ambient <= MAX_ROOM_EFFECTS,
          'a room may show %d effects at once' % (splash + dust + ambient))

    print('mesh                 triangles  vertices')
    print('pile (full)          %9d  %8d  (of that %d triangles of coins and gems in a second section)' % (
        pile_tris['full'], pile_verts['full'], detail_tris))
    print('empty tile scatter   %9d' % scatter_tris)
    print('pile (reduced)       %9d  %8d' % (pile_tris['reduced'], pile_verts['reduced']))
    print('floor heap           %9d  %8d' % (heap_tris, heap_verts))
    print('carried sack         %9d  %8d' % (sack_tris, sack_verts))
    print()
    print('draw calls per room (a square room; before = one object per tile with a pile section and a coin/gem')
    print('section, after = one static batch per room and %dx%d tile patch, worst case alignment)' % (chunk, chunk))
    print('room tiles   draw calls before (full/reduced)   draw calls after (full/reduced)   triangles (full)   triangles (reduced)')
    calls = {}
    for tiles in (10, 25, 50, 100, 400):
        side = int(round(tiles ** 0.5))
        patches = min(tiles, worst_patches(side, chunk) ** 2)
        before = (tiles * MATERIALS_FULL, tiles * MATERIALS_REDUCED)
        after = (patches * MATERIALS_FULL, patches * MATERIALS_REDUCED)
        calls[tiles] = after
        print('%10d %17d / %-17d %17d / %-14d %18d %21d' % (tiles, before[0], before[1], after[0], after[1],
                                                           tiles * pile_tris['full'], tiles * pile_tris['reduced']))
        limit(after[0] <= before[0] and after[1] <= before[1], 'batching adds draw calls for %d tiles' % tiles)
    limit(calls[100][0] <= MAX_DRAW_CALLS_100_TILE_ROOM, 'a 100 tile treasury costs %d draw calls' % calls[100][0])
    limit(calls[400][0] <= MAX_DRAW_CALLS_400_TILE_ROOM, 'a 400 tile treasury costs %d draw calls' % calls[400][0])
    print()
    print('effects per room at once (full): %d splash + %d dust + %d sparkle/slide/roll = %d (budget %d)' % (
        splash, dust, ambient, splash + dust + ambient, MAX_ROOM_EFFECTS))
    print('glow: one light per 3x3 patch of tiles with rich piles, none at detail off')
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
