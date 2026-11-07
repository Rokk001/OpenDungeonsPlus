"""Owner screenshots of 2026-11-07 (decision 830 a): white rectangles at the edges of the dark pool block and white puffs on top
of it. The block is the lava spa (SpaMudPool and SpaPoolRim), not the crypt: every crypt texture and material exists.

1  The rectangles are the lava seam of SpaPoolRim (material SpaLavaGlow). A material with 'lighting off' ignores diffuse and
   emissive and paints an untextured surface white, so the colour has to come from a texture unit (colour_op_ex src_manual).
2  The puffs are SpaSteam: the emitter sat at the origin of the pool piece, inside the mud (top 0.28), so the lower half of each
   puff was cut off and the rest was a large opaque white blob. The emitter now starts above the mud and the puffs are thin.
3  The pool pieces stay out of the furniture list (isWalkableSpaMesh); graves (coffins) stay solid. Decision 837 makes the
   mud solid for the route search instead (RoomObjectNavigation::spaPoolObstacles, check_spa_owner_837.py).
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
material = (root / 'materials/scripts/Spa.material').read_text(encoding='utf-8')
glow = material[material.index('material SpaLavaGlow'):]
assert 'lighting off' in glow and 'emissive' in glow
assert re.search(r'texture_unit\s*\{\s*colour_op_ex source1 src_manual src_current 1\.0 0\.15 0\.015', glow), \
    'SpaLavaGlow must take its colour from a texture unit, or the lava seam is white'

particle = (root / 'particles/RoomAmbienceProduction.particle').read_text(encoding='utf-8')
steam = particle[particle.index('particle_system SpaSteam'):]
steam = steam[:steam.index('\n}\n')]
mud_top = 0.28
start = float(re.search(r'position\s+0 0 ([0-9.]+)', steam).group(1))
assert start > mud_top, 'the steam must start above the mud surface'
alpha = float(re.search(r'colour_range_start\s+\S+ \S+ \S+ ([0-9.]+)', steam).group(1))
assert alpha <= 0.35, 'the steam must be thin'
assert float(re.search(r'rate\s+([0-9.]+)', steam.split('affector Scaler')[1]).group(1)) <= 0.15

bounds = (root / 'source/gamemap/RoomObjectBounds.h').read_text(encoding='utf-8')
assert 'return name == SPA_POOL_MESH || name == SPA_RIM_MESH' in bounds
assert 'isSteppableMesh' in bounds and 'name == "KnightCoffin"' in bounds
print('check_spa_white_rim_steam_x1 ok')
