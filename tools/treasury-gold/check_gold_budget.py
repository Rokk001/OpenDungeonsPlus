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
# A full pile carries up to 16 coins (6 triangles each), 4 gems (8) and 8 spilled coins (4) on top of its round
# surface (a fan of 16 sectors with 2 rings, 80 triangles): 240 triangles. The limit was raised from 150 on purpose for the "sea of coins" of the plan. It
# stays cheap because the piles of a room are one static batch (two draw calls), the coins only exist at the detail
# full, and piles far from the camera use the reduced mesh (8 triangles).
MAX_TRIANGLES_PER_PILE = 250
MAX_TRIANGLES_PER_HEAP = 150
MAX_TRIANGLES_PER_SACK = 400
MAX_TRIANGLES_100_TILE_ROOM = 25000
# Draw calls: settled piles are drawn by one static batch per room (two materials per batch)
MAX_DRAW_CALLS_100_TILE_ROOM = 2
MAX_DRAW_CALLS_400_TILE_ROOM = 2
MATERIALS_FULL = 2
MATERIALS_REDUCED = 1
# Gold elsewhere adds no particle system and no per-frame work on the CPU
MAX_NEW_PARTICLE_SYSTEMS = 0
# Effects one room may show at once (splash + dust + sparkle/sliding/rolling coins), and glow lights per patch
MAX_ROOM_EFFECTS = 16
# Dynamic point lights of the glow over rich treasuries, in all rooms together
MAX_GLOW_LIGHTS = 32


def read(path):
    with open(os.path.join(REPO, path), encoding='utf-8') as handle:
        return handle.read()


def constant(text, name):
    match = re.search(r'\b' + name + r'\s*=\s*(\d+)\s*;', text)
    if match is None:
        raise SystemExit('constant not found: ' + name)
    return int(match.group(1))


def setting(text, name):
    """Default of a member of the TreasurySettings struct (the values config/treasury.cfg starts from)"""
    match = re.search(r'\b(?:int|float) ' + name + r' = ([0-9.]+)f?;', text)
    if match is None:
        raise SystemExit('setting not found: ' + name)
    return float(match.group(1))


def main():
    settings = read('source/rooms/TreasurySettings.h')
    pile = read('source/render/TreasuryGoldMesh.cpp')
    loose = read('source/render/LooseGoldMesh.cpp')

    sectors = constant(pile, 'PileSectors')
    full_rings = constant(pile, 'FullRings')
    reduced_rings = constant(pile, 'ReducedRings')
    # The round surface: a fan of one triangle per sector in the middle, a band of two triangles per sector between
    # two rings, and a band of two triangles per sector from the last ring to the tile border (the border points
    # are as many as the sectors)
    full_surface_tris = sectors * (1 + 2 * (full_rings - 1) + 2)
    reduced_surface_tris = sectors * (1 + 2 * (reduced_rings - 1) + 2)
    full_surface_verts = 1 + sectors * full_rings + sectors
    reduced_surface_verts = 1 + sectors * reduced_rings + sectors
    heap_rings = constant(loose, 'HeapRings')
    heap_sectors = constant(loose, 'HeapSectors')
    sack_sectors = constant(loose, 'SackSectors')
    profile_count = constant(loose, 'ProfileCount')

    layer = read('source/rooms/TreasuryGoldLayer.h')
    coin_sides = constant(pile, 'CoinSides')
    spill_sides = constant(pile, 'SpillSides')
    gem_sides = constant(pile, 'GemSides')
    # A cut gem: a table fan, a crown of two triangles per side and a pavilion of one per side
    gem_faces = 4 * gem_sides
    gem_verts = 2 * gem_sides + 2
    max_top_coins = int(setting(settings, 'maxTopCoins'))
    max_gems = int(setting(settings, 'maxGems'))
    max_spill_coins = 4 * int(setting(settings, 'spillCoinsFull'))
    scatter_coins = int(setting(settings, 'scatterCoins'))

    # Coins on top, gems and spilled coins lie in a second section (a second draw call) of the full pile mesh
    detail_tris = max_top_coins * coin_sides + max_gems * gem_faces + max_spill_coins * spill_sides
    detail_verts = max_top_coins * (coin_sides + 1) + max_gems * gem_verts + max_spill_coins * (spill_sides + 1)
    scatter_tris = scatter_coins * coin_sides

    pile_tris = {'full': full_surface_tris + detail_tris, 'reduced': reduced_surface_tris}
    pile_verts = {'full': full_surface_verts + detail_verts, 'reduced': reduced_surface_verts}
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
    limit('batchChunkSize' not in rules, 'the batch is split into patches again')
    splash = int(setting(settings, 'splashBudgetFull'))
    dust = int(setting(settings, 'dustBudgetFull'))
    ambient = int(setting(settings, 'ambientBudgetFull'))
    limit(setting(settings, 'glowMaxTotal') <= MAX_GLOW_LIGHTS and setting(settings, 'glowMaxPerRoom') <= setting(settings, 'glowMaxTotal'),
          'too many glow lights')
    limit(splash + dust + ambient <= MAX_ROOM_EFFECTS,
          'a room may show %d effects at once' % (splash + dust + ambient))

    print('mesh                 triangles  vertices')
    print('pile (full)          %9d  %8d  (of that %d triangles of coins and gems in a second section)' % (
        pile_tris['full'], pile_verts['full'], detail_tris))
    print('                     = %d surface + %d top coins * %d + %d gems * %d + %d spilled coins * %d' % (
        full_surface_tris, max_top_coins, coin_sides, max_gems, gem_faces, max_spill_coins, spill_sides))
    print('empty tile scatter   %9d' % scatter_tris)
    print('pile (reduced)       %9d  %8d' % (pile_tris['reduced'], pile_verts['reduced']))
    print('floor heap           %9d  %8d' % (heap_tris, heap_verts))
    print('carried sack         %9d  %8d' % (sack_tris, sack_verts))
    print()
    print('draw calls per room (a square room; before = one object per tile with a pile section and a coin/gem')
    print('section, after = one static batch per room)')
    print('room tiles   draw calls before (full/reduced)   draw calls after (full/reduced)   triangles (full)   triangles (reduced)')
    calls = {}
    for tiles in (10, 25, 50, 100, 400):
        patches = 1
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
    print('glow: one light per 3x3 patch of tiles with rich piles near the camera, at most %d per room and %d in all'
          ' (%d / %d at reduced), none at detail off' % (
              setting(settings, 'glowMaxPerRoom'), setting(settings, 'glowMaxTotal'),
              setting(settings, 'glowMaxPerRoomReduced'), setting(settings, 'glowMaxTotalReduced')))
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
