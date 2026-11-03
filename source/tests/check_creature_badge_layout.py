"""Check the creature badge: one flower, red health above blue mana, original sizes. No compile, no game."""
from pathlib import Path
import re
from PIL import Image

root = Path(__file__).resolve().parents[2]
textures = root / 'materials/textures'
source = (root / 'source/render/CreatureOverlayStatus.cpp').read_text(encoding='utf-8').replace('\r\n', '\n')
overlay_cpp = (root / 'source/render/MovableTextOverlay.cpp').read_text(encoding='utf-8')
overlay_h = (root / 'source/render/MovableTextOverlay.h').read_text(encoding='utf-8')

# The sizes of the badge parts are the original ones again; the thin mana ring is gone.
for setting in ('HEALTH_BADGE_SIZE = 64;', 'STATUS_ICON_SIZE = 30;', 'CROWN_SIZE = 64;',
                'LEVEL_CAPTION_SIZE_ONE_DIGIT = 32;', 'LEVEL_CAPTION_SIZE_TWO_DIGITS = 26;'):
    assert setting in source, setting
assert 'forceTextArea(healthId, HEALTH_BADGE_SIZE, HEALTH_BADGE_SIZE)' in source
assert 'forceTextArea(manaId, HEALTH_BADGE_SIZE, HEALTH_BADGE_SIZE)' in source
assert 'forceTextArea(statusId, STATUS_ICON_SIZE, STATUS_ICON_SIZE)' in source
assert 'MANA_RING' not in source and 'ManaRing' not in source and 'setOffset(manaId' not in source
assert 'MANA_FLOWER_SHARE = 1.0f / 3.0f;' in source
assert 'BADGE_FLOWER_MATERIAL = "CreatureOverlay0";' in source

# The mana part of the flower is drawn under the rings and the level, so it is created before the experience ring.
constructor = source[source.index('CreatureOverlayStatus::CreatureOverlayStatus('):]
assert constructor.index('CreatureOverlays::mana') < constructor.index('CreatureOverlays::experience')
assert constructor.index('CreatureOverlays::health') < constructor.index('CreatureOverlays::mana')

# Cutting the picture: update() shrinks and moves the panel to the band and the picture shows the same band.
assert 'void setVerticalBand(uint32_t childOverlayId, Ogre::Real top, Ogre::Real bottom);' in overlay_h
assert 'setUV(0.0f, top, 1.0f, bottom)' in overlay_cpp
assert '+ relTextHeight * childOverlay.mBandTop' in overlay_cpp
assert 'relTextHeight * (childOverlay.mBandBottom - childOverlay.mBandTop)' in overlay_cpp


def bands(health, mana, has_mana):
    """Mirror updateProgress: health band and mana band as fractions of the flower height (top, bottom)."""
    bottom = 2 / 3 if has_mana else 1.0
    return (bottom * (1 - health), bottom), (bottom + (1 / 3) * (1 - mana), 1.0)


# Full health and mana: upper 2/3 health, lower 1/3 mana.
h, m = bands(1, 1, True)
assert h == (0.0, 2 / 3) and abs(m[0] - 2 / 3) < 1e-9 and m[1] == 1.0
# Both drain from the top and keep their lower edge, and stay inside their own part.
for share in (0.75, 0.5, 0.25, 0.0):
    h, m = bands(share, share, True)
    assert abs(h[1] - 2 / 3) < 1e-9 and abs((h[1] - h[0]) - share * 2 / 3) < 1e-9
    assert m[1] == 1.0 and abs((m[1] - m[0]) - share / 3) < 1e-9 and m[0] >= h[1]
# Without mana the whole flower is health.
assert bands(1, 0, False)[0] == (0.0, 1.0) and abs(bands(0.5, 0, False)[0][0] - 0.5) < 1e-9

# The flower picture has solid pixels in both parts, so both stay readable.
alpha = Image.open(textures / 'CreatureOverlay0.png').convert('RGBA').getchannel('A')
width, height = alpha.size
upper = sum(1 for y in range(int(height * 2 / 3)) for x in range(width) if alpha.getpixel((x, y)) >= 128)
lower = sum(1 for y in range(int(height * 2 / 3), height) for x in range(width) if alpha.getpixel((x, y)) >= 128)
assert upper > 0 and lower > 0

material = (root / 'materials/scripts/CreatureOverlay.material').read_text(encoding='utf-8')
assert re.search(r'material CreatureOverlay0\b', material)
print('creature badge flower, bands and sizes pass the checks')
