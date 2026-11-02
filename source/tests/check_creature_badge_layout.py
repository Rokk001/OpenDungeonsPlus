"""Check that the solid portions of the centred badge layers stay distinct without compiling the game."""
from pathlib import Path
import re
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
textures = root / 'materials/textures'
source = (root / 'source/render/CreatureOverlayStatus.cpp').read_text(encoding='utf-8')
for setting in ('HEALTH_BADGE_SIZE = 112;', 'MANA_RING_SIZE = 64;', 'STATUS_ICON_SIZE = 28;',
                'CROWN_SIZE = 28;', 'LEVEL_CAPTION_SIZE_ONE_DIGIT = 30;',
                'LEVEL_CAPTION_SIZE_TWO_DIGITS = 18;'):
    assert setting in source, setting
assert 'forceTextArea(healthId, HEALTH_BADGE_SIZE, HEALTH_BADGE_SIZE)' in source
assert 'forceTextArea(statusId, STATUS_ICON_SIZE, STATUS_ICON_SIZE)' in source
assert 'setOffset(manaId' not in source


def solid_pixels(image, size):
    """Place a scaled overlay in badge coordinates and return pixels at least half opaque."""
    alpha = image.convert('RGBA').resize((size, size), Image.Resampling.BILINEAR).getchannel('A')
    offset = (112 - size) // 2
    return {(x + offset, y + offset) for y in range(size) for x in range(size) if alpha.getpixel((x, y)) >= 128}


mana = set().union(*(solid_pixels(Image.open(textures / ('ManaRing%d.png' % n)), 64) for n in range(1, 9)))
backing = solid_pixels(Image.open(textures / 'CreatureOverlay7.png'), 112)
for n in range(8):
    petals = solid_pixels(Image.open(textures / ('CreatureOverlay%d.png' % n)), 112) - backing
    assert not mana & petals, 'mana covers health segments %d' % n
for atlas_name in ('CreatureExperience.png', 'CreatureRecovery.png'):
    atlas = Image.open(textures / atlas_name)
    for frame in range(64):
        x, y = (frame % 8) * 128, (frame // 8) * 128
        assert not mana & solid_pixels(atlas.crop((x, y, x + 128, y + 128)), 64), (atlas_name, frame)
material = (root / 'materials/scripts/CreatureOverlayStatus.material').read_text(encoding='utf-8')
for name in re.findall(r'texture\s+(\S+)', material):
    assert not mana & solid_pixels(Image.open(textures / name), 28), name
assert not mana & solid_pixels(Image.open(textures / 'ChampionCrown.png'), 28), 'champion crown'
# Approximate the centred font and its one-pixel outline; the in-game renderer remains a visual check.
for level in range(1, 31):
    size = 30 if level < 10 else 18
    font = ImageFont.truetype(str(root / 'gui/fonts/MedievalSharp-Bold.ttf'), size)
    canvas = Image.new('L', (112, 112), 0)
    draw = ImageDraw.Draw(canvas)
    label = str(level)
    box = draw.textbbox((0, 0), label, font=font)
    x = (112 - (box[2] - box[0])) / 2 - box[0] - 1
    y = (112 - (box[3] - box[1])) / 2 - box[1] + 2
    draw.text((x, y), label, font=font, fill=255, stroke_width=1)
    text_pixels = {(x, y) for y in range(112) for x in range(112) if canvas.getpixel((x, y)) >= 128}
    assert not mana & text_pixels, 'level %d overlaps mana' % level
print('centred badge layers remain distinct in pixel checks')
