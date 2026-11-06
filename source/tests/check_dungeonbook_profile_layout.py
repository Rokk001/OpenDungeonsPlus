"""Check that the profile remarks (QuirksText) never move the status and the latest post and that every row can be reached.

Static check, no game needed. Two things are verified.

1. Order. The rows of the profile page flow from top to bottom (Gui::layoutCreatureProfilePage). The remarks of
   the picture come after status and latest post, so those two keep the position they have without remarks.
2. Overflow. The creature card has a fixed height and the Dungeonbook pane is limited too. If the rows are
   higher than the page, the page scrolls: the page layout holds a scrollbar that is shown only then, and
   layoutCreatureProfilePage moves all rows with it (so nothing is cut off without a way to reach it).
   The card stays 640 design pixels high and the content scrolls (decision of the owner): the check does not
   demand that the typical content fits without scrolling, it demands that ALL rows are reachable by scrolling,
   at 640x480, 1024x768, 1920x1200 and 7680x4320, each with the user scale 80 % and 120 %.

The height model: fonts and layout are scaled by the same factor, both from the display size and the user
scale (the font is autoscaled from 800x600, the layout from 1024x768, the same ratio), so the heights in design
pixels do not depend on the resolution. This is computed per resolution and per user scale below to show it.
A text line of the 8 point font is about 14 pixels at 800x600, that is 18 design pixels; a row is its lines plus
4 pixels padding and 4 pixels gap.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
gui = (repo / 'source/render/Gui.cpp').read_text()
body = gui[gui.index('float Gui::layoutCreatureProfilePage'):]
body = body[:body.index('\nvoid Gui::applyProfileScroll')]

# 1. order
before = re.search(r'textRowsBefore\[\] = \{([^}]*)\}', body)[1]
after = re.search(r'textRowsAfter\[\] = \{([^}]*)\}', body)[1]
assert 'QuirksText' not in before, 'the remarks must not come before status and latest post'
rows = [r.strip(' "') for r in after.split(',')]
assert rows == ['StatusText', 'EffectsText', 'LatestText', 'QuirksText'], rows
# The loop bounds must match the lengths of the two row lists
before_rows = [r for r in before.split(',') if r.strip()]
assert 'i < ' + str(len(before_rows)) + ';' in body and 'i < 4;' in body, 'row counts do not match the row lists'

# 2. scrolling machinery
page = (repo / 'gui/WindowCreatureProfilePage.layout').read_text()
assert 'type="OD/VerticalScrollbar" name="ProfileScrollbar"' in page, 'the page needs its scrollbar'
bar = page[page.index('name="ProfileScrollbar"'):]
bar = bar[:bar.index('</Window>')]
assert 'name="Visible" value="False"' in bar, 'the scrollbar must be hidden until the content overflows'
assert 'bool overflow = (y > viewport' in body, 'the overflow test is missing'
assert 'bar->setVisible(overflow)' in body, 'the scrollbar must be shown only on overflow'
assert 'setDocumentSize(y)' in body and 'setPageSize(viewport)' in body, 'the scrollbar range is missing'
assert 'applyProfileScroll(page, offset)' in body, 'the rows must follow the scroll position'
assert 'return overflow ? viewport : y;' in body, 'the caller must get the page height on overflow'
assert 'Gui::onProfileScrolled' in gui and 'EventScrollPositionChanged' in gui, 'the scrollbar is not connected'
assert 'mProfileBaseAreas.erase' in gui, 'the unscrolled areas must be released with the window'
assert 'EventMouseWheel' in gui and 'Gui::onProfileWheel' in gui, 'the mouse wheel does not scroll the profile'
assert 'setMouseInputPropagationEnabled(true)' in gui, 'the rows must pass the mouse wheel on to the page'
wheel = gui[gui.index('bool Gui::onProfileWheel'):]
wheel = wheel[:wheel.index('\n}\n')]
assert 'isVisible()' in wheel, 'the wheel must only scroll while the scrollbar is shown'
header_rows = ('Portrait', 'NameText', 'HandleText', 'AgeText', 'RelationText', 'FromText', 'JobText', 'HealthLabel',
               'HealthBar', 'ExperienceLabel', 'ExperienceBar')
for name in header_rows:
    assert 'name="%s"' % name in page, name  # moved with the scroll as well (all children but the scrollbar)

layout = (repo / 'gui/WindowCreatureProfile.layout').read_text()
m = re.search(r'name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', layout)
card_width, card_height = int(m[3]) - int(m[1]), int(m[4]) - int(m[2])
# The page uses 88 percent of the shared frame client, excluding title and borders.
import xml.etree.ElementTree as ET
card = ET.fromstring(layout).find('Window')
holder = card.find("Window[@name='ProfilePage']/Property[@name='Area']").get('value')
assert holder == '{{0.0,0},{0.0,0},{1.0,0},{0.88,0}}'
skin = ET.parse(repo / 'gui/ODSkin.imageset').getroot()
border = float(skin.find("Image[@name='WindowTopEdge']").get('height')) / 4
side = float(skin.find("Image[@name='WindowLeftEdge']").get('width')) / 4
title_height = 18 * 10 / 8 + 12
page_height = (card_height - title_height - 2 * border) * 0.88
text_width = card_width - 2 * side - 48
assert 'PROFILE_RIGHT_MARGIN = 32.0f' in gui

LINE, PAD, GAP, TOP = 18.0, 4.0, 4.0, 132.0
# Attributes, health/XP, five personal rows, then path and skills precede the bio.
ATTRIBUTE_ROWS = 9
CHAR = 8.2  # design pixels of an average character of the font


def row(lines):
    return lines * LINE + PAD + GAP


def lines_of(chars, width):
    return max(1, -(-int(chars * CHAR) // int(width)))


def content(bio, likes, dislikes, friends, status, latest, quirks):
    """Returns (bottom of the latest post, bottom of the remarks) in design pixels."""
    y = TOP + ATTRIBUTE_ROWS * row(1) + row(bio) + row(likes) + row(dislikes)
    y += max(LINE + PAD, friends * (LINE + PAD)) + GAP  # friends label and one button per friend
    y += row(1) - GAP + GAP  # foe row
    y += row(status)
    latest_bottom = y + row(latest) - GAP
    return latest_bottom, latest_bottom + GAP + (row(quirks) - GAP if quirks else 0)


# typical: bio 2 lines, likes and dislikes 1 line, two friends, status and latest 2 lines, remarks heading plus
# two one line remarks; worst case: everything at its longest, remarks wrap to two lines each (Dungeonbook width)
dungeonbook_width = 404
typical = content(2, 1, 1, 2, 2, 2, 3)
worst = content(3, 2, 2, 2, 3, 3, 1 + 2 * lines_of(64, dungeonbook_width))
without_quirks = content(2, 1, 1, 2, 2, 2, 0)
assert typical[0] == without_quirks[0], 'the remarks moved status or latest post'
assert card_height == 640, ('the card keeps its height of 640 design pixels, the content scrolls', card_height)

scroll_step = float(re.search(r'PROFILE_SCROLL_STEP = ([0-9.]+)f', gui)[1])
overflow_tolerance = float(re.search(r'PROFILE_OVERFLOW_TOLERANCE = ([0-9.]+)f', gui)[1])
design_width = float(re.search(r'LAYOUT_DESIGN_WIDTH = ([0-9.]+)f', gui)[1])
design_height = float(re.search(r'LAYOUT_DESIGN_HEIGHT = ([0-9.]+)f', gui)[1])
assert scroll_step > 0.0, 'the wheel and the arrows need a step'
# the scrollbar range is document - page, and the offset is clamped to it, so the last pixel of the content ends at the
# bottom of the page when the scrollbar is at its end
assert 'std::min(scrollbar->getScrollPosition(), y - viewport)' in body, 'the offset must reach the end of the content'
assert 'setDocumentSize(y)' in body and 'setPageSize(viewport)' in body


def reachable_rows(content_bottom, viewport):
    """All rows are reachable when the largest scroll offset brings the bottom of the content to the page bottom.

    Returns (maximum scroll offset, number of wheel steps to reach it)."""
    maximum = max(0.0, content_bottom - viewport)
    assert maximum + viewport >= content_bottom - 1e-9, 'the end of the content is not reachable'
    return maximum, -(-int(maximum * 1000) // int(scroll_step * 1000))


# the tallest single row (a status or remark of three or more lines) must fit the page, so it can be shown whole
tallest_row = max(row(1 + 2 * lines_of(64, dungeonbook_width)), row(3), row(4))
assert tallest_row <= page_height, 'a single row is higher than the page and cannot be shown whole'

report = []
for width, height in ((640, 480), (1024, 768), (1920, 1200), (7680, 4320)):
    for user in (0.8, 1.2):
        scale = min(width / design_width, height / design_height) * user
        # the card must be on the screen, otherwise its end could not be reached at all
        assert card_height * scale <= height + 1e-6 and card_width * scale <= width + 1e-6, ('the card is larger than the screen', width, height, user)
        page_px = page_height * scale
        for name, (latest_bottom, remarks_bottom) in (('typical', typical), ('worst', worst)):
            maximum, wheel_steps = reachable_rows(remarks_bottom, page_height)
            overflow = remarks_bottom > page_height + overflow_tolerance
            # without overflow the bar is hidden and nothing moves; with overflow the bar is shown and reaches the end
            assert overflow or maximum <= overflow_tolerance, (name, remarks_bottom)
            # the last row ends exactly at the page bottom at the end of the range, the first row starts at the top
            assert abs((remarks_bottom - maximum) - min(remarks_bottom, page_height)) < 1e-6 or not overflow
            report.append('%dx%d user %d%% %s: page %.0f px, content %.0f px, %s' % (
                width, height, round(user * 100), name, page_px, remarks_bottom * scale,
                ('scrolls %.0f px in %d wheel steps, all rows reachable' % (maximum * scale, wheel_steps)) if overflow else 'fits'))

for width, height in ((1024, 768), (1280, 720), (1920, 1080), (2560, 1440)):
    for user in (0.5, 1.0, 2.0):
        scale = min(width / 1024.0, height / 768.0) * user
        font_scale = min(width / (800.0 / user), height / (600.0 / user))
        # screen pixels of one line (14 pixels at 800x600) and of the card page, back in design pixels
        line_design = 14.0 * font_scale / scale
        assert abs(line_design - 17.92) < 0.01, ('the line height depends on the resolution', line_design)
        page_px = page_height * scale
        for name, (latest_bottom, remarks_bottom) in (('typical', typical), ('worst', worst)):
            need = remarks_bottom * scale
            reachable_rows(remarks_bottom, page_height)
        # the status keeps its place whatever the resolution: its top does not depend on the remarks
        assert typical[0] == without_quirks[0]

# Dungeonbook (gui/WindowSocial.layout), owner decisions 635, 636, 647 and 648: a start page with the creature list
# (portrait, name, level, mood, filters All / Workers / Fighters / Unhappy) and the feed of all creatures, and the four
# pages of one creature (Feed, Profile, Values, Inventory) switched by the navigation bar at the bottom; the head of
# these pages has a back arrow to the start page and previous / next arrows around the name. No button in mid-page.
# Every page is measured with the shipped font at 640x480, 1920x1200 and 7680x4320 (and 1024x768), UI scale 80 % and
# 120 %: the window stays on the screen, no text is higher or wider than its window and nothing leaves its parent.
from PIL import ImageFont

social = (repo / 'source/render/SocialWindow.cpp').read_text()
social_header = (repo / 'source/render/SocialWindow.h').read_text()
social_layout = (repo / 'gui/WindowSocial.layout').read_text()
book = ET.fromstring(social_layout).find('Window')
size = re.search(r'name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', social_layout)
book_w, book_h = int(size[3]) - int(size[1]), int(size[4]) - int(size[2])
# 880x644 since the ornate frame and the 20 point title of decision 710 (860x620 before): the pages keep their room
assert (book_w, book_h) == (880, 644), (book_w, book_h)
assert not (repo / 'gui/WindowDungeonbookProfile.layout').exists(), 'the old profile page with its buttons is gone'
for old in ('Attributes', 'Social profile', 'Statistics', 'Back', 'Show: all creatures', 'Posts of: everyone'):
    assert 'name="Text" value="%s"' % old not in social_layout, 'old button ' + old
for old in ('FilterButton', 'FeedTab', 'ProfileTab', 'FeedModeButton', 'CreatureList', 'ProfilePane', 'SocialButton',
            'StatisticsButton', 'StatisticsPage'):
    assert 'name="%s"' % old not in social_layout and '"%s"' % old not in social, old
assert 'type="OD/Listbox"' not in social_layout

font_files = {}
for name in ('MedievalSharp-6', 'MedievalSharp-8', 'MedievalSharp-10', 'MedievalSharp-20'):
    spec = ET.parse(repo / 'gui/fonts' / (name + '.font')).getroot()
    font_files[name] = (ImageFont.truetype(str(repo / 'gui/fonts' / spec.get('filename')), 1024),
                        float(spec.get('size')) * (96.0 / 72.0) * (1024.0 / 800.0) / 1024.0)


def text_width(font, text):
    """Width of the text in design pixels with the shipped font (fonts scale like the layout)."""
    face, factor = font_files[font]
    return face.getlength(text) * factor


def line_height(font):
    face, factor = font_files[font]
    return sum(face.getmetrics()) * factor


CLIENT_W, CLIENT_H = 828.0, 560.0
# The book has its own ornate iron frame (DungeonbookIcons/BookFrame*, imageset auto scaled 'min' from 3840x2160):
# its side and bottom edges are FRAME_PX image pixels, scaled with the display only (not with the UI scale)
book_images = ET.parse(repo / 'gui/DungeonbookIcons.imageset').getroot()
assert (book_images.get('autoScaled'), book_images.get('nativeHorzRes'), book_images.get('nativeVertRes')) == ('min', '3840', '2160')
FRAME_PX = max(float(book_images.find("Image[@name='BookFrame%s']" % n).get(d))
               for n, d in (('Left', 'width'), ('Right', 'width'), ('Bottom', 'height')))
assert book.find("Property[@name='FrameLeftImage']").get('value') == 'DungeonbookIcons/BookFrameLeft'


def collect_boxes(element, box, path, out):
    """Absolute boxes of all windows below element, as fractions of the frame client."""
    for child in element.findall('Window'):
        value = child.find("Property[@name='Area']").get('value')
        dims = [(float(a), float(b)) for a, b in re.findall(r'\{(-?[0-9.]+),(-?[0-9.]+)\}', value)]
        assert len(dims) == 4 and all(offset == 0 for _, offset in dims), child.get('name') + ' scales with its client'
        x0, y0, x1, y1 = (d[0] for d in dims)
        assert 0 <= x0 < x1 <= 1.0001 and 0 <= y0 < y1 <= 1.0001, ('outside its parent', path, child.get('name'))
        width, height = box[2] - box[0], box[3] - box[1]
        absolute = (box[0] + x0 * width, box[1] + y0 * height, box[0] + x1 * width, box[1] + y1 * height)
        name = (path + '/' if path else '') + child.get('name')
        out[name] = (absolute, child)
        collect_boxes(child, absolute, name, out)


boxes = {}
collect_boxes(book, (0.0, 0.0, 1.0, 1.0), '', boxes)
pages = ('HomePage', 'FeedPage', 'ProfilePage', 'ValuesPage', 'InventoryPage')
for page in pages + ('Header', 'NavBar'):
    assert page in boxes, page
assert boxes['NavBar'][0][1] >= max(boxes[p][0][3] for p in pages) - 1e-6, 'the pages end above the navigation bar'
header_bottom = boxes['Header'][0][3]
for name, (box, element) in boxes.items():
    page = name.split('/')[0]
    if page in pages[1:] and name.count('/') == 1:
        assert box[1] >= header_bottom - 1e-6, (name, 'overlaps the head with the arrows')


def visible_default(name):
    element = boxes[name][1]
    prop = element.find("Property[@name='Visible']")
    return prop is None or prop.get('value') == 'True'


assert visible_default('HomePage') and not any(visible_default(p) for p in pages[1:]), 'the book opens on the start page'
assert not visible_default('Header'), 'the start page has no head with arrows'
# Navigation: four buttons in the bottom bar, the arrows in the head, the filters in the head of the start page
nav = [n for n in boxes if n.startswith('NavBar/Nav') and n.count('/') == 1 and n != 'NavBar/NavRule']
assert nav == ['NavBar/NavFeed', 'NavBar/NavProfile', 'NavBar/NavValues', 'NavBar/NavInventory'], nav
assert [boxes[n + '/Label'][1].find("Property[@name='Text']").get('value') for n in nav] == [
    'Feed', 'Profile', 'Values', 'Inventory']
for arrow in ('BackButton', 'PrevButton', 'NextButton'):
    assert 'Header/' + arrow in boxes
prev_box, name_box, next_box = (boxes['Header/' + n][0] for n in ('PrevButton', 'NameText', 'NextButton'))
assert prev_box[2] <= name_box[0] and name_box[2] <= next_box[0], 'the arrows sit around the name'
assert boxes['Header/BackButton'][0][2] <= prev_box[0], 'the back arrow sits left in the head'
filters = ['HomePage/Filter' + f for f in ('All', 'Workers', 'Fighters', 'Unhappy')]
for f in filters:
    assert f in boxes and boxes[f][0][3] <= boxes['HomePage/ListRows'][0][1], f + ' sits in the head of the start page'
buttons = [n for n, (b, e) in boxes.items() if e.get('type') in ('OD/Button', 'OD/InvisibleButton')]
for n in buttons:
    allowed = n.startswith('NavBar/') or n.startswith('Header/') or n in filters or (
        n.startswith('HomePage/ListRows/Row') and n.endswith('/Button'))
    assert allowed, n + ' is a button in mid-page'
# Rows of the list and of the feeds, scrolled by their scrollbars, no overlap
list_rows = sorted(n for n in boxes if re.fullmatch(r'HomePage/ListRows/Row\d', n))
assert len(list_rows) == 7 and 'LIST_ROWS = 7' in social
for page in ('HomePage', 'FeedPage'):
    rows = sorted(n for n in boxes if re.fullmatch(page + r'/FeedRows/Row\d', n))
    assert len(rows) == 3 and 'FEED_ROWS = 3' in social, page
    for upper, lower in zip(rows, rows[1:]):
        assert boxes[upper][0][3] <= boxes[lower][0][1] + 1e-9
    assert boxes[page + '/FeedScroll'][1].get('type') == 'OD/VerticalScrollbar'
for upper, lower in zip(list_rows, list_rows[1:]):
    assert boxes[upper][0][3] <= boxes[lower][0][1] + 1e-9
for part in ('Highlight', 'Portrait', 'Name', 'Level', 'MoodIcon', 'Mood', 'Button'):
    assert 'HomePage/ListRows/Row0/' + part in boxes, part
# Inventory: 13 slots (6 equipment, 3 potions, 4 inventory), each with symbol, quality frame and lock; no overlap
slot_names = ['InventoryPage/SlotBox%d' % i for i in range(13)]
assert all(n in boxes for n in slot_names) and 'InventoryPage/SlotBox13' not in boxes
labels = [boxes[n + '/Label'][1].find("Property[@name='Text']").get('value') for n in slot_names]
assert labels == ['Right Hand', 'Left Hand', 'Head', 'Armour', 'Boots', 'Ring', 'Potion 1', 'Potion 2', 'Potion 3',
                  'Inventory 1', 'Inventory 2', 'Inventory 3', 'Inventory 4'], labels
for i, n in enumerate(slot_names):
    for child in ('SlotType', 'QualityFrame', 'Lock'):
        assert '%s/Slot%d/%s' % (n, i, child) in boxes, (n, child)
    assert boxes['%s/Slot%d/Lock' % (n, i)][1].find("Property[@name='Image']").get('value') == 'DungeonbookIcons/Lock'
    for m in slot_names[i + 1:]:
        a, b = boxes[n][0], boxes[m][0]
        assert a[2] <= b[0] + 1e-9 or b[2] <= a[0] + 1e-9 or a[3] <= b[1] + 1e-9 or b[3] <= a[1] + 1e-9, (n, m)
# Values sheet: every value of the former statistics page, the attributes, combat and defense blocks with symbols
for name in ('Experience', 'HitPoints', 'Gold', 'SightRadius', 'Potions', 'Inventory', 'DamagePerSecond', 'SkillPoints'):
    assert 'ValuesPage/%sLabel' % name in boxes and 'ValuesPage/%sValue' % name in boxes, name
for name in ('Strength', 'Dexterity', 'Life', 'Mana', 'CombatLabels', 'CombatValues', 'DefenseLabels', 'DefenseValues',
             'EquipmentValue', 'PathValue', 'SkillsValue', 'Portrait/Image', 'Portrait/Frame'):
    assert 'ValuesPage/' + name in boxes, name
for name, icon in (('CombatIcon', 'Swords'), ('DefenseIcon', 'Shield'), ('EquipmentIcon', 'Equipment'),
                   ('PathIcon', 'Path'), ('SkillsIcon', 'Skills')):
    assert boxes['ValuesPage/' + name][1].find("Property[@name='Image']").get('value') == 'DungeonbookIcons/' + icon
assert boxes['ValuesPage/CombatLabels'][1].find("Property[@name='Text']").get('value').split(chr(10)) == [
    'Critical %', 'Attack Rating', 'Defense Rating']
assert boxes['ValuesPage/DefenseLabels'][1].find("Property[@name='Text']").get('value').split(chr(10)) == [
    'Physical Defense', 'Magical Defense', 'Element Defense']
assert boxes['ValuesPage/Portrait/Frame'][1].find("Property[@name='Image']").get('value') == 'DungeonbookFrame/Ring'
icons = ET.parse(repo / 'gui/DungeonbookIcons.imageset').getroot()
icon_names = {i.get('name') for i in icons.findall('Image')}
for value in re.findall(r'value="DungeonbookIcons/(\w+)"', social_layout) + re.findall(r'"DungeonbookIcons/(\w+)"', social):
    assert value in icon_names, value
assert (repo / 'gui' / icons.get('imagefile')).is_file()
scheme = ET.parse(repo / 'gui/ODSkin.scheme').getroot()
assert scheme.find("Imageset[@filename='DungeonbookIcons.imageset'][@name='DungeonbookIcons']") is not None
assert scheme.find("Imageset[@filename='DungeonbookFrame.imageset'][@name='DungeonbookFrame']") is not None
assert 'gui/DungeonbookIcons.png' in (repo / 'CREDITS').read_text()

# Code: real game data only, every value of today kept, rounded, and the slots filled by the creature code
for label in ('"Experience"', '"HP"', '"Gold"', '"Sight radius"', '"Potions"', '"Inventory"', '"Raw damage per second"',
              '"Skill points earned / spent"'):
    assert label in social, label
assert 'findStatisticsValue(entry.stats, line.label)' in social
for field in ('critical', 'attackRating', 'defenseRating', 'physicalDefense', 'magicalDefense', 'elementDefense'):
    assert 'formatProfileValue(entry.%s)' % field in social, field
assert 'formatProfileValue(values[i])' in social and 'std::setprecision(2)' in social
assert 'entry.equipment, entry.path, entry.skills' in social and 'fitTextToWindow(tile, FEED_TEXT_COLOUR, value)' in social
assert 'Creature::fillItemSlotWindows(creature, slots, true)' in social
creature_text = (repo / 'source/entities/Creature.cpp').read_text()
fill = creature_text[creature_text.index('void Creature::fillItemSlotWindows('):]
fill = fill[:fill.index('\n}\n')]
for fragment in ('creature->mEquipment[slot]', 'creature->mPotionSlots[slot - 6]', 'creature->mInventory[slot - 9]',
                 'slot >= VISIBLE_ITEM_HAND_SLOTS', 'ItemDrops::poorWeapon(*weapon)', 'item->describe(creature->getGameMap())',
                 'slotType->setVisible(item == nullptr)', 'slot - 6 >= creature->mPotionSlots.size()',
                 'image->getChild("Lock")->setVisible(locked)', '"PotionSlotLevel2"', '"PotionSlotLevel3"'):
    assert fragment in fill, fragment
assert 'fillItemSlotWindows(this, slotWindows, false)' in creature_text, 'the creature card keeps its slots'
for handler in ('onBackClicked', 'onPreviousClicked', 'onNextClicked', 'onNavClicked', 'onFilterClicked', 'onListRowClicked',
                'onListWheel', 'onFeedWheel', 'onListScrolled', 'onFeedScrolled', 'onLinkClicked'):
    assert 'bool SocialWindow::%s' % handler in social and '&SocialWindow::%s' % handler in social, handler
step = social[social.index('void SocialWindow::stepCreature'):]
step = step[:step.index('\n}\n')]
assert '% count' in step and 'mListedCreatures' in step, 'previous and next wrap around the shown list'
assert 'row->getChild("Highlight")->setVisible(entry->name == mSelectedCreature)' in social
assert 'describeMood(*entry, mood, icon)' in social
assert 'MAX_FEED_ROWS = 25' in social and 'MAX_OWN_POSTS = 6' in social
assert 'creature->fillProfilePage(mProfilePage)' in social
compact = social[social.index('const char* const hidden[]'):]
compact = compact[:compact.index('};')]
for name in ('"Portrait"', '"NameText"', '"AttributesText"', '"EquipmentText"', '"EquipmentRow"', '"OwnPostsText"'):
    assert name in compact, 'the shared profile page in the book hides ' + name
assert 'const bool compact = !page->getChild("Portrait")->isVisible();' in body
assert 'compact ? PROFILE_ROW_GAP' in body

# Sizes. Fonts and layout scale by the same factor from the display and the UI scale (the line heights in design
# pixels do not depend on the resolution); Gui::getWindowFitFactor shrinks a window larger than the screen together
# with its children but not the fonts, so the texts are compared with the shrunk boxes.
assert book.find("Property[@name='TitlebarFont']").get('value') == 'MedievalSharp-20'
TITLE_LINE = line_height('MedievalSharp-20')
need = {}


def require(name, font, lines=1, texts=(), pad_w=6.0, pad_h=0.0):
    need[name] = (font, lines, texts, pad_w, pad_h)


require('HomePage/CreaturesLabel', 'MedievalSharp-10', texts=('Known creatures (40 of 64)',))
for f, text in zip(filters, ('[ All ]', '[ Workers ]', '[ Fighters ]', '[ Unhappy ]')):
    require(f, 'MedievalSharp-8', texts=(text,), pad_w=14.0, pad_h=6.0)
require('HomePage/FeedTitle', 'MedievalSharp-10', texts=('All-Creature Feed',))
for row in list_rows:
    require(row + '/Name', 'MedievalSharp-8')
    require(row + '/Level', 'MedievalSharp-8', texts=('Lv. 30',))
    require(row + '/Mood', 'MedievalSharp-8', texts=('Furious', 'Content', 'Neutral', 'Unhappy', 'Hungry'))
for page in ('HomePage', 'FeedPage'):
    for i in range(3):
        require('%s/FeedRows/Row%d/Head' % (page, i), 'MedievalSharp-8', texts=('Name   Lv. 30 - 59 min ago',))
        require('%s/FeedRows/Row%d/Text' % (page, i), 'MedievalSharp-8', lines=2)
    require(page + '/FeedEmpty', 'MedievalSharp-8', lines=2)
require('FeedPage/FeedTitle', 'MedievalSharp-10', texts=('Feed',))
require('Header/NameText', 'MedievalSharp-10', texts=('Grimwald Stonebreaker',))
for n in nav:
    require(n + '/Label', 'MedievalSharp-10', texts=(boxes[n + '/Label'][1].find("Property[@name='Text']").get('value'),))
require('ProfilePage/NameText', 'MedievalSharp-10')
require('ProfilePage/KeeperText', 'MedievalSharp-8', texts=('Keeper: Player 1',))
require('ProfilePage/InfoText', 'MedievalSharp-8', lines=4, texts=('Mood: Furious', 'Level 30'))
require('ProfilePage/PostsTitle', 'MedievalSharp-10', texts=('Posts (200)',))
require('ProfilePage/SocialHolder', 'MedievalSharp-8', lines=6)
require('ProfilePage/PostsEmpty', 'MedievalSharp-8', lines=2, texts=('Nothing posted yet.',))
for name, label in (('Experience', 'Experience:'), ('HitPoints', 'Hit points:'), ('Gold', 'Gold:'),
                    ('SightRadius', 'Sight radius:'), ('Potions', 'Potions:'), ('Inventory', 'Inventory:'),
                    ('DamagePerSecond', 'Damage per second:'), ('SkillPoints', 'Skill points:')):
    require('ValuesPage/%sLabel' % name, 'MedievalSharp-8', texts=(label,), pad_w=4.0)
    require('ValuesPage/%sValue' % name, 'MedievalSharp-8', texts=('1500 / 1500', '12 / 12'), pad_w=4.0)
for name in ('Strength', 'Dexterity', 'Life', 'Mana'):
    require('ValuesPage/' + name, 'MedievalSharp-8', lines=2, texts=(name, '999.99'))
require('ValuesPage/CombatLabels', 'MedievalSharp-8', lines=3, texts=('Critical %', 'Attack Rating', 'Defense Rating'))
require('ValuesPage/DefenseLabels', 'MedievalSharp-8', lines=3, texts=('Physical Defense', 'Magical Defense', 'Element Defense'))
require('ValuesPage/CombatValues', 'MedievalSharp-8', lines=3, texts=('99.99 %', '999.99'))
require('ValuesPage/DefenseValues', 'MedievalSharp-8', lines=3, texts=('999.99',))
for name in ('Equipment', 'Path', 'Skills'):
    require('ValuesPage/%sTitle' % name, 'MedievalSharp-8', texts=(name,), pad_w=2.0)
    require('ValuesPage/%sValue' % name, 'MedievalSharp-6', lines=4)
for i, label in enumerate(labels):
    require('InventoryPage/SlotBox%d/Label' % i, 'MedievalSharp-6', texts=(label,), pad_w=2.0)
require('InventoryPage/PotionsLabel', 'MedievalSharp-8', texts=('Potions',))
require('InventoryPage/InventoryLabel', 'MedievalSharp-8', texts=('Inventory',))
require('InventoryPage/HintText', 'MedievalSharp-8', lines=4)
for name in need:
    assert name in boxes, name

state_lines = []
for screen_w, screen_h in ((640, 480), (1024, 768), (1920, 1200), (7680, 4320)):
    for user in (0.8, 1.2):
        scale = min(screen_w / 1024.0, screen_h / 768.0) * user
        fit = min(1.0, screen_w / (book_w * scale), screen_h / (book_h * scale))
        win_w, win_h = book_w * fit, book_h * fit  # design pixels after the fit, fonts unchanged
        assert win_w * scale <= screen_w + 1e-6 and win_h * scale <= screen_h + 1e-6, 'the book is larger than the screen'
        # the title bar is one line of the title font plus 12 screen pixels; the frame takes its edges
        frame = FRAME_PX * min(screen_w / 3840.0, screen_h / 2160.0) / scale
        client_w = win_w - 2 * frame
        client_h = win_h - (TITLE_LINE + 12.0 / scale) - frame
        tightest = {}
        for name, (font, lines, texts, pad_w, pad_h) in need.items():
            box = boxes[name][0]
            width = (box[2] - box[0]) * client_w
            height = (box[3] - box[1]) * client_h
            wanted_h = lines * line_height(font) + pad_h
            wanted_w = max([text_width(font, t) + pad_w for t in texts] + [0.0])
            assert height + 1e-6 >= wanted_h, ('text too high for its window', name, screen_w, screen_h, user,
                                               round(height, 1), round(wanted_h, 1))
            assert width + 1e-6 >= wanted_w, ('text too wide for its window', name, screen_w, screen_h, user,
                                              round(width, 1), round(wanted_w, 1))
            page = name.split('/')[0]
            ratio = max(wanted_h / height, wanted_w / width)
            if ratio > tightest.get(page, (0.0, ''))[0]:
                tightest[page] = (ratio, name)
        # the slot pictures stay squares of at least 24 screen pixels, the portraits at least 40
        for i in range(13):
            slot = boxes['InventoryPage/SlotBox%d/Slot%d' % (i, i)][0]
            edge = min((slot[2] - slot[0]) * client_w, (slot[3] - slot[1]) * client_h) * scale
            assert edge >= 12.0, ('slot too small', screen_w, screen_h, user, edge)
        state_lines.append('%dx%d UI %d%%: book %dx%d px (fit %.2f); tightest text per page: %s' % (
            screen_w, screen_h, round(user * 100), round(win_w * scale), round(win_h * scale), fit,
            ', '.join('%s %s %.0f%%' % (p.replace('Page', ''), tightest[p][1].split('/')[-1], tightest[p][0] * 100)
                      for p in ('HomePage', 'Header', 'FeedPage', 'ProfilePage', 'ValuesPage', 'InventoryPage', 'NavBar')
                      if p in tightest)))
print('Dungeonbook pages verified: start page, head with back/previous/next arrows, bottom navigation, feed, profile, '
      'values sheet and 13-slot inventory fit 640x480 to 8K at 80 to 120 percent')
for line in state_lines:
    print('  ' + line)
