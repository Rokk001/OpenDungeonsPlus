"""Static check: filled and empty Dungeonbook slots differ at a glance (owner decision 918). No game and no compiler
needed.

A filled slot shows the picture of its own item in full colour inside the frame of its quality (Poor grey, Common white,
Rare blue, Epic purple, config/items.cfg); an empty slot shows the placeholder with the slot symbol clearly dimmed.
Checked here:
1. Creature::fillItemSlotWindows (the book calls it with showLocks) colours an empty slot with EMPTY_ITEM_SLOT_COLOURS,
   at most half opaque, a filled one opaque white, a locked potion slot keeps its grey under the lock; the picture is
   the item picture and the quality frame is shown only for a filled slot.
2. The four quality frames exist in gui/ODIcons.imageset and config/items.cfg names their colours; with Pillow present
   the frame pictures are measured: Poor and Common grey to white, Rare blue, Epic purple.
3. Every inventory slot of the book has the picture, the symbol and the quality frame windows.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
creature = (repo / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
social = (repo / 'source/render/SocialWindow.cpp').read_text(encoding='utf-8')
items_cfg = (repo / 'config/items.cfg').read_text(encoding='utf-8')
imageset = (repo / 'gui/ODIcons.imageset').read_text(encoding='utf-8')
book = ET.fromstring((repo / 'gui/WindowSocial.layout').read_text(encoding='utf-8')).find('Window')


def function_of(text, signature):
    body = text[text.index(signature):]
    return body[:body.index('\n}\n')]


# 1. The colours of the slots
match = re.search(r'static const char\* const EMPTY_ITEM_SLOT_COLOURS = "([^"]+)";', creature)
assert match, 'the dimmed colour of an empty slot is a named constant'
colours = re.findall(r'(tl|tr|bl|br):([0-9A-F]{8})', match.group(1))
assert [c[0] for c in colours] == ['tl', 'tr', 'bl', 'br'] and len({c[1] for c in colours}) == 1
alpha = int(colours[0][1][:2], 16)
grey = max(int(colours[0][1][i:i + 2], 16) for i in (2, 4, 6))
assert alpha <= 0x80, 'an empty slot is clearly dimmed (at most half opaque)'
assert grey < 0xFF, 'and greyed'
fill = function_of(creature, 'void Creature::fillItemSlotWindows(')
assert re.search(r'const char\* const colours = locked \? "tl:FF606060 tr:FF606060 bl:FF606060 br:FF606060" :\s*'
                 r'\(item == nullptr \? EMPTY_ITEM_SLOT_COLOURS : "tl:FFFFFFFF tr:FFFFFFFF bl:FFFFFFFF br:FFFFFFFF"\);',
                 fill), 'empty dimmed, filled in full colour, locked grey'
assert 'image->setProperty("ImageColours", colours);' in fill and 'slotType->setProperty("ImageColours", colours);' in fill
assert fill.index('if(!showLocks)') < fill.index('image->setProperty("ImageColours", colours);'), \
    'only the book (showLocks) changes the colours; the creature card keeps its look'
assert '"ItemImages/" + item->getImageName()' in fill and 'slotType->setVisible(item == nullptr);' in fill
assert 'frame->setVisible(item != nullptr);' in fill
assert 'frame->setProperty("Image", "OpenDungeonsIcons/ItemFrame" + qualityName(item->mQuality));' in fill
assert 'Creature::fillItemSlotWindows(creature, slots, true);' in function_of(social, 'void SocialWindow::refreshInventory(')

# 2. The quality frames
assert 'Quality colours: Poor grey, Common white, Rare blue, Epic purple' in items_cfg
frames = {}
for quality in ('Poor', 'Common', 'Rare', 'Epic'):
    found = re.search(r'<Image height="(\d+)" name="ItemFrame%s" width="(\d+)" xPos="(\d+)" yPos="(\d+)" />' % quality,
                      imageset)
    assert found, 'ItemFrame' + quality
    frames[quality] = tuple(int(v) for v in found.groups())
try:
    from PIL import Image
except ImportError:
    Image = None
if Image is not None:
    atlas = Image.open(repo / 'gui/ODIcons.png').convert('RGBA')
    average = {}
    for quality, (height, width, x, y) in frames.items():
        pixels = [p for p in atlas.crop((x, y, x + width, y + height)).getdata() if p[3] > 200 and max(p[:3]) > 80]
        assert pixels, quality
        average[quality] = tuple(sum(p[i] for p in pixels) / len(pixels) for i in range(3))
    for quality in ('Poor', 'Common'):
        r, g, b = average[quality]
        assert max(r, g, b) - min(r, g, b) < 25, quality + ' frame is grey to white'
    assert average['Common'][0] > average['Poor'][0], 'Common is lighter than Poor'
    r, g, b = average['Rare']
    assert b > r + 40 and b > g + 30, 'Rare frame is blue'
    r, g, b = average['Epic']
    assert b > g + 30 and r > g + 20, 'Epic frame is purple'

# 3. The slot windows of the book
page = [w for w in book.findall('Window') if w.get('name') == 'InventoryPage'][0]
for slot in range(13):
    box = [w for w in page.findall('Window') if w.get('name') == 'SlotBox%d' % slot][0]
    picture = [w for w in box.findall('Window') if w.get('name') == 'Slot%d' % slot][0]
    names = [w.get('name') for w in picture.findall('Window')]
    assert 'SlotType' in names and 'QualityFrame' in names, slot

print('check_dungeonbook_slot_look_918: OK')
