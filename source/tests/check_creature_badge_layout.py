"""Check the creature badge: outer ring life, inner ring mana, original sizes. No compile, no game."""
from pathlib import Path
import re
from PIL import Image

root = Path(__file__).resolve().parents[2]
textures = root / 'materials/textures'
source = (root / 'source/render/CreatureOverlayStatus.cpp').read_text(encoding='utf-8').replace('\r\n', '\n')
overlay_cpp = (root / 'source/render/MovableTextOverlay.cpp').read_text(encoding='utf-8')
overlay_h = (root / 'source/render/MovableTextOverlay.h').read_text(encoding='utf-8')

for setting in ('HEALTH_BADGE_SIZE = 64;', 'STATUS_ICON_SIZE = 30;', 'CROWN_SIZE = 64;',
                'LEVEL_CAPTION_SIZE_ONE_DIGIT = 32;', 'LEVEL_CAPTION_SIZE_TWO_DIGITS = 26;',
                'BADGE_FLOWER_MATERIAL = "CreatureOverlay0";',
                'BADGE_OUTER_RING_MATERIAL = "CreatureOverlayHealthOuter";',
                'BADGE_INNER_RING_MATERIAL = "CreatureOverlayManaInner";'):
    assert setting in source, setting
assert 'forceTextArea(healthId, HEALTH_BADGE_SIZE, HEALTH_BADGE_SIZE)' in source
assert 'forceTextArea(manaId, HEALTH_BADGE_SIZE, HEALTH_BADGE_SIZE)' in source
assert 'forceTextArea(statusId, STATUS_ICON_SIZE, STATUS_ICON_SIZE)' in source
# The old split into an upper red and a lower blue part is gone.
assert 'MANA_FLOWER_SHARE' not in source and 'healthBottom' not in source and 'MANA_RING' not in source

# The mana ring (blue, inner picture) lies over the health ring and under the experience ring.
constructor = source[source.index('CreatureOverlayStatus::CreatureOverlayStatus('):]
assert constructor.index('CreatureOverlays::health') < constructor.index('CreatureOverlays::mana')
assert constructor.index('CreatureOverlays::mana') < constructor.index('CreatureOverlays::experience')
assert 'BADGE_INNER_RING_MATERIAL, getManaColour()' in constructor
# A creature with mana gets the outer ring picture as health ring, one without mana the whole flower.
assert 'hasMana ? BADGE_OUTER_RING_MATERIAL : BADGE_FLOWER_MATERIAL' in source
assert '(mHasMana != hasMana)' in source

# Both rings shrink proportionally to their value and keep their lower edge.
progress = source[source.index('void CreatureOverlayStatus::updateProgress('):]
assert 'setVerticalBand(healthId, static_cast<Ogre::Real>(1.0 - healthShare), 1.0f)' in progress
assert 'setVerticalBand(manaId, static_cast<Ogre::Real>(1.0 - manaShare), 1.0f)' in progress
assert 'void setVerticalBand(uint32_t childOverlayId, Ogre::Real top, Ogre::Real bottom);' in overlay_h
assert 'setUV(0.0f, top, 1.0f, bottom)' in overlay_cpp

# The ring pictures: inner is the middle of the flower, outer the rest; together they are the flower.
flower = Image.open(textures / 'CreatureOverlay0.png').convert('RGBA').getchannel('A')
inner = Image.open(textures / 'CreatureOverlayManaInner.png').convert('RGBA').getchannel('A')
outer = Image.open(textures / 'CreatureOverlayHealthOuter.png').convert('RGBA').getchannel('A')
assert flower.size == inner.size == outer.size
centre = flower.size[0] / 2
solid_inner = solid_outer = 0
for y in range(flower.size[1]):
    for x in range(flower.size[0]):
        f, i, o = flower.getpixel((x, y)), inner.getpixel((x, y)), outer.getpixel((x, y))
        assert max(i, o) == f and min(i, o) == 0, (x, y)
        radius = ((x + 0.5 - centre) ** 2 + (y + 0.5 - centre) ** 2) ** 0.5
        if i >= 128:
            solid_inner += 1
            assert radius <= 32
        if o >= 128:
            solid_outer += 1
            assert radius > 30
assert solid_inner > 500 and solid_outer > 500

material = (root / 'materials/scripts/CreatureOverlay.material').read_text(encoding='utf-8')
for name, texture in (('CreatureOverlay0', 'CreatureOverlay0.png'),
                      ('CreatureOverlayHealthOuter', 'CreatureOverlayHealthOuter.png'),
                      ('CreatureOverlayManaInner', 'CreatureOverlayManaInner.png')):
    assert re.search(r'material ' + name + r'\s*\{[^}]*?texture ' + re.escape(texture), material, re.S), name
print('creature badge rings (blue inner mana, outer life), shrinking and sizes pass the checks')
