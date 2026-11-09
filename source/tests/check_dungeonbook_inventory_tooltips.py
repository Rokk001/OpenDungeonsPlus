"""Static check: every filled slot of the Dungeonbook inventory page shows the item tooltip on hover (decision 863,
finding 3). No game and no compiler needed.

On the book page a slot is a framed box (InventoryPage/SlotBoxN, OD/StaticText) with the item picture (SlotN) in its
middle and the slot name (Label) below. Creature::fillItemSlotWindows sets the item tooltip (item->describe) on the
picture only, which covers about a third of the box, and the label passes the mouse to the box, so hovering the frame or
the name showed nothing. Checked here:
1. CEGUI hit testing (deepest visible, non pass-through window under the mouse, later siblings first): the picture is a
   hit target, its overlays (SlotType, QualityFrame, Lock) and the label pass the mouse on, the box is the hit target
   around the picture, and no later window of the page, the header or the navigation bar lies over a slot box.
2. refreshInventory copies the tooltip of every picture to its box right after fillItemSlotWindows, so the whole box
   shows the item values (or the lock text of a locked potion slot) and an empty slot shows nothing.
3. fillItemSlotWindows still sets item->describe on the picture, and the creature card keeps its own slots and call.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
book = ET.fromstring((repo / 'gui/WindowSocial.layout').read_text()).find('Window')
social = (repo / 'source/render/SocialWindow.cpp').read_text()
creature = (repo / 'source/entities/Creature.cpp').read_text()
card = ET.fromstring((repo / 'gui/WindowCreatureProfilePage.layout').read_text())

SLOTS = 13


def props(element):
    return {p.get('name'): p.get('value') for p in element.findall('Property')}


def area(element, box):
    dims = [float(a) for a, _ in re.findall(r'\{(-?[0-9.]+),(-?[0-9.]+)\}', props(element)['Area'])]
    width, height = box[2] - box[0], box[3] - box[1]
    return (box[0] + dims[0] * width, box[1] + dims[1] * height, box[0] + dims[2] * width, box[1] + dims[3] * height)


def child(element, name):
    found = [c for c in element.findall('Window') if c.get('name') == name]
    assert len(found) == 1, name
    return found[0]


def passes(element):
    return props(element).get('MousePassThroughEnabled') == 'True'


def overlaps(a, b):
    return a[0] < b[2] - 1e-9 and b[0] < a[2] - 1e-9 and a[1] < b[3] - 1e-9 and b[1] < a[3] - 1e-9


def function_of(text, signature):
    body = text[text.index(signature):]
    return body[:body.index('\n}\n')]


# 1. Hit testing of the inventory page
client = (0.0, 0.0, 1.0, 1.0)
top = book.findall('Window')
names = [w.get('name') for w in top]
page = child(book, 'InventoryPage')
page_box = area(page, client)
page_children = page.findall('Window')
for i in range(SLOTS):
    box_window = child(page, 'SlotBox%d' % i)
    assert not passes(box_window), 'SlotBox%d must be the hit target around its picture' % i
    box = area(box_window, page_box)
    picture = child(box_window, 'Slot%d' % i)
    assert not passes(picture) and props(picture).get('Visible') != 'False', 'Slot%d must be hit' % i
    for overlay in picture.findall('Window'):
        assert passes(overlay), 'Slot%d/%s lies over the picture and must pass the mouse on' % (i, overlay.get('name'))
    label = child(box_window, 'Label')
    assert passes(label), 'SlotBox%d/Label must pass the mouse to the box' % i
    picture_box = area(picture, box)
    share = ((picture_box[2] - picture_box[0]) * (picture_box[3] - picture_box[1])) / ((box[2] - box[0]) * (box[3] - box[1]))
    assert share < 1.0, 'the picture covers only part of the box, so the box needs the tooltip too'
    # Later siblings are drawn and hit first
    for later in page_children[page_children.index(box_window) + 1:]:
        if not passes(later) and props(later).get('Visible') != 'False':
            assert not overlaps(area(later, page_box), box), '%s lies over SlotBox%d' % (later.get('name'), i)
    # Header and navigation bar come after the pages in the book
    for name in names[names.index('InventoryPage') + 1:]:
        sibling = child(book, name)
        if not passes(sibling):
            assert not overlaps(area(sibling, client), box), '%s lies over SlotBox%d' % (name, i)

# 2. The box repeats the tooltip of its picture
inventory = function_of(social, 'void SocialWindow::refreshInventory(')
fill_at = inventory.index('Creature::fillItemSlotWindows(creature, slots, true);')
copy = 'slot->getParent()->setTooltipText(slot->getTooltipText());'
assert copy in inventory and inventory.index(copy) > fill_at, 'the slot boxes take the tooltip after the slots are filled'
assert re.search(r'for\(CEGUI::Window\* slot : slots\)\s*\n\s*' + re.escape(copy), inventory), 'every slot box'
assert '"SlotBox" + std::to_string(slot) + "/Slot" + std::to_string(slot)' in inventory, 'the picture is a child of its box'

# 3. The shared fill and the creature card stay as they are
fill = function_of(creature, 'void Creature::fillItemSlotWindows(')
assert 'image->setTooltipText(item == nullptr ? "" : item->describe(creature->getGameMap(), heldWeapon));' in fill
assert 'image->setTooltipText("Potion slot locked: it opens at level "' in fill
assert 'getParent()' not in fill, 'the shared fill does not touch the parents of the card slots'
assert 'fillItemSlotWindows(this, slotWindows, false);' in creature, 'the creature card keeps its slots'
row = [w for w in card.iter('Window') if w.get('name') == 'EquipmentRow']
assert len(row) == 1
for i in range(SLOTS):
    slot = child(row[0], 'Slot%d' % i)
    assert not passes(slot), 'card Slot%d keeps its tooltip' % i
    for overlay in slot.findall('Window'):
        assert passes(overlay), 'card Slot%d/%s' % (i, overlay.get('name'))

print('dungeonbook inventory tooltips: %d slot boxes show the item tooltip of their picture, card unchanged' % SLOTS)
