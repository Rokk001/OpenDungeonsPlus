"""Check badge segment stages and textures without compiling or starting the game."""
from pathlib import Path
import re
from PIL import Image

root = Path(__file__).resolve().parents[2]
textures = root / 'materials/textures'
source = (root / 'source/render/CreatureOverlayStatus.cpp').read_text(encoding='utf-8')
creature = (root / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
material = (root / 'materials/scripts/CreatureOverlay.material').read_text(encoding='utf-8')
assert 'NB_OVERLAY_HEALTH_VALUES = 8;' in creature
assert 'HEALTH_BADGE_SIZE = 64;' in source
assert 'forceTextArea(healthId, HEALTH_BADGE_SIZE, HEALTH_BADGE_SIZE)' in source
assert 'forceTextArea(manaId, HEALTH_BADGE_SIZE, HEALTH_BADGE_SIZE)' in source
assert 'BADGE_OUTER_RING_MATERIAL = "CreatureOverlayHealthStage";' in source
assert 'BADGE_INNER_RING_MATERIAL = "CreatureOverlayManaStage";' in source
assert '(hasMana ? BADGE_OUTER_RING_MATERIAL : BADGE_FLOWER_MATERIAL) + Helper::toString(mHealthValue)' in source
assert 'BADGE_INNER_RING_MATERIAL + Helper::toString(manaStage)' in source
assert 'setVerticalBand(' not in source
assert 'if(manaShare > 0.0)' in source and 'if(manaShare >= threshold)' in source
assert 'threshold -= 1.0 / static_cast<double>(steps);' in source
assert 'displayOverlay(manaId, hasMana ? -1 : 0)' in source

# Match the same descending threshold loop as Creature::computeCreatureOverlayHealthValue.
def stage(share):
    if share <= 0:
        return 7
    threshold = 1.0
    for value in range(6):
        if share >= threshold:
            return value
        threshold -= 1.0 / 6
    return 6

for fraction, expected in [(1, 0), (0.9, 1), (0.7, 2), (0.5, 4), (0.3, 5), (0.2, 5), (0.001, 6), (0, 7)]:
    # The comparisons follow repeated subtraction, including floating-point threshold rounding.
    assert stage(fraction) == expected, (fraction, stage(fraction), expected)
for i in range(6):
    threshold = 1.0
    for unused in range(i):
        threshold -= 1.0 / 6
    assert stage(threshold) == i
    if i:
        assert stage(threshold + 1e-9) == i
    assert stage(threshold - 1e-9) == i + 1

for stage_index in range(8):
    original = Image.open(textures / f'CreatureOverlay{stage_index}.png').convert('RGBA')
    outer = Image.open(textures / f'CreatureOverlayHealthStage{stage_index}.png').convert('RGBA')
    inner = Image.open(textures / f'CreatureOverlayManaStage{stage_index}.png').convert('RGBA')
    assert original.size == outer.size == inner.size == (128, 128)
    for y in range(128):
        for x in range(128):
            pixel = original.getpixel((x, y))
            a, b = outer.getpixel((x, y)), inner.getpixel((x, y))
            assert (a == pixel and b[3] == 0) or (b == pixel and a[3] == 0), (stage_index, x, y)
    for kind in ('Health', 'Mana'):
        name = f'CreatureOverlay{kind}Stage{stage_index}'
        assert re.search(r'material ' + name + r'\s*\{[^}]*?texture ' + name + r'\.png', material, re.S), name
print('creature badge segment stages and textures: ok')
