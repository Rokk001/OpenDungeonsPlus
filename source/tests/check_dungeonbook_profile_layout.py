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
page_layout_text = page
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
# Owner decision 732: names and post texts are never shortened with "..." but word wrap; owner decision 830: the game
# values are rounded to at most two decimals (no raw float sums); the longest name, post, nick and value the game can
# produce are measured here.
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
             'EquipmentTile', 'EquipmentTitle', 'PathTile', 'PathTitle', 'SkillsTile', 'SkillsTitle', 'Portrait/Image',
             'Portrait/Frame'):
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

# Code: real game data only, every value of today kept, rounded to at most two decimals (owner decision 830: no raw
# float sums such as 51.59700000000005), and the slots filled by the creature code
for label in ('"Experience"', '"HP"', '"Gold"', '"Sight radius"', '"Potions"', '"Inventory"', '"Raw damage per second"',
              '"Skill points earned / spent"'):
    assert label in social, label
assert 'findStatisticsValue(entry.stats, line.label)' in social
for field in ('critical', 'attackRating', 'defenseRating', 'physicalDefense', 'magicalDefense', 'elementDefense'):
    assert 'formatProfileValue(entry.%s)' % field in social, field
assert 'formatProfileValue(values[i])' in social


def function_of(text, signature):
    body = text[text.index(signature):]
    return body[:body.index('\n}\n')]


# The book rounds in ONE place, the creature code: its value text is the rounded text with the thousands grouped
for rounding in ('setprecision', 'std::fixed', 'std::round', 'lround', 'std::trunc', 'std::ceil'):
    assert rounding not in social, 'the Dungeonbook rounds through Creature::formatRoundedNumber only: ' + rounding
profile_value = function_of(social, 'std::string formatProfileValue(double value)')
assert 'return groupThousands(Creature::formatRoundedNumber(value));' in profile_value, profile_value
statistics_numbers = function_of(social, 'std::string formatStatisticsNumbers(')
assert 'formatProfileValue(number)' in statistics_numbers and 'groupThousands(parts[i])' not in statistics_numbers, \
    'the statistics values are rounded as well, also a raw sum an older server wrote'
assert 'parser.imbue(std::locale::classic());' in statistics_numbers
group = function_of(social, 'std::string groupThousands(const std::string& number)')
assert 'THOUSANDS_GROUP = 3;' in social and 'result.insert(comma - THOUSANDS_GROUP, ",")' in group
# The rounded number text of the creature code: two decimals at most, zeros at the end dropped, exponent from 1e15 on
creature_header = (repo / 'source/entities/Creature.h').read_text()
assert 'static std::string formatRoundedNumber(double value);' in creature_header
creature_cpp = (repo / 'source/entities/Creature.cpp').read_text()
assert 'formatExactNumber' not in creature_cpp + creature_header + social, 'the raw exact number text is gone'
rounded = function_of(creature_cpp, 'std::string Creature::formatRoundedNumber(double value)')
for fragment in ('stream << std::fixed;', 'stream << std::scientific;', 'if(std::fabs(value) >= ROUNDED_FIXED_MAX)',
                 'stream << std::setprecision(ROUNDED_DECIMALS) << value;', 'std::locale::classic()',
                 "while(!mantissa.empty() && (mantissa[mantissa.size() - 1] == '0'))",
                 "if(!mantissa.empty() && (mantissa[mantissa.size() - 1] == '.'))", 'if(mantissa == "-0")',
                 'return mantissa + suffix;'):
    assert fragment in rounded, fragment
assert re.search(r'ROUNDED_DECIMALS = 2;', creature_cpp) and re.search(r'ROUNDED_FIXED_MAX = 1e15;', creature_cpp)
stats_text = function_of(creature_cpp, 'std::string Creature::getStatsText(const Seat* viewer)')
for fragment in ('"Experience: " << formatRoundedNumber(mExp)',
                 '"HP: " << formatRoundedNumber(getHP()) << " / " << formatRoundedNumber(mMaxHP)',
                 '"Gold: " << formatRoundedNumber(mGoldCarried)'):
    assert fragment in stats_text, fragment
server_text = (repo / 'source/network/ODServer.cpp').read_text()
for getter in ('getAttackRating', 'getDefenseRating', 'getRawDamagePerSecond'):
    assert 'Creature::formatRoundedNumber(creature->%s())' % getter in server_text, getter
    assert 'Helper::toString(creature->%s())' % getter not in server_text, getter + ' is written with six digits'


def rounded_number(value):
    """Python replica of Creature::formatRoundedNumber: two decimals, zeros at the end dropped, exponent from 1e15."""
    text = ('%.2e' if abs(value) >= 1e15 else '%.2f') % value
    mantissa, sep, exponent = text.partition('e')
    mantissa = mantissa.rstrip('0').rstrip('.')
    if mantissa == '-0':
        mantissa = '0'
    return mantissa + sep + exponent


def group_thousands(number):
    """Python replica of groupThousands in SocialWindow.cpp."""
    if any(c in number for c in 'eEin'):
        return number
    sign = 1 if number.startswith('-') else 0
    whole = number.find('.') if '.' in number else len(number)
    while whole > sign + 3:
        number = number[:whole - 3] + ',' + number[whole - 3:]
        whole -= 3
    return number


# Rounded means: at most two decimals, no zero at the end, the nearest such number (the owner's raw sums included)
for value, text in ((51.59700000000005, '51.6'), (56.51100000000007, '56.51'), (14.8, '14.8'), (42600.0, '42,600'),
                    (41.666666666666664, '41.67'), (0.1 + 0.2, '0.3'), (12.0, '12'), (-1234567.25, '-1,234,567.25'),
                    (3e-05, '0'), (-0.004, '0'), (4.5864, '4.59'), (5e20 / 7, '7.14e+19')):
    assert group_thousands(rounded_number(value)) == text, (value, group_thousands(rounded_number(value)))
for value in (1.0 / 3, 2.0 / 3 * 100, 1e-7 / 3, 123456789.123, 0.001, 999999999999999.9, 51.59700000000005):
    shown = rounded_number(value)
    assert abs(float(shown) - value) <= 0.005 + abs(value) * 1e-15, (value, shown)
    assert '.' not in shown or len(shown.split('.')[1]) <= 2, shown
# The widest value text the book can show: every magnitude and form, negative
WORST_NUMBERS = tuple(sorted({group_thousands(rounded_number(float('-9.8765432109876543e%d' % e))) for e in range(-320, 308)},
                       key=lambda n: (text_width('MedievalSharp-8', n), n))[-12:])
assert all(len(n) >= 10 for n in WORST_NUMBERS) and '-987,654,321,098,765.38' in WORST_NUMBERS, WORST_NUMBERS
# Every magnitude and form (and the round values like 1.0000000000000002), for the attribute cells whose line breaks
# depend on where the commas, points and exponent lie
ALL_NUMBERS = tuple(sorted({group_thousands(rounded_number(float(m % e))) for m in ('-9.8765432109876543e%d',
                            '-1.0000000000000002e%d', '9.8765432109876543e%d', '1.2345e%d') for e in range(-320, 308)}))
assert len(ALL_NUMBERS) > 1000 and set(WORST_NUMBERS) <= set(ALL_NUMBERS), len(ALL_NUMBERS)
# Owner decision 816: Strength, Dexterity, Life and Mana side by side in ONE row (book-variant-2), label on top, the
# rounded value below it; a long value is broken into lines of ATTRIBUTE_LINE_CHARS characters (breakAttributeValue)
ATTRIBUTES = ('Strength', 'Dexterity', 'Life', 'Mana')
LINE_CHARS = int(re.search(r'ATTRIBUTE_LINE_CHARS = (\d+);', social)[1])
break_value = function_of(social, 'std::string breakAttributeValue(const std::string& value)')
for fragment in ('while(rest.size() > ATTRIBUTE_LINE_CHARS)', 'std::string::size_type cut = ATTRIBUTE_LINE_CHARS;',
                 'for(std::string::size_type i = ATTRIBUTE_LINE_CHARS; i >= ATTRIBUTE_LINE_CHARS / 2; --i)',
                 "if(rest[i - 1] == ',' || rest[i - 1] == '.' || rest[i] == 'e' || rest[i] == 'E')",
                 'result += rest.substr(0, cut) + "\\n";', 'rest = rest.substr(cut);', 'return result + rest;'):
    assert fragment in break_value, fragment
values_fill = function_of(social, 'void SocialWindow::refreshValues(')
assert 'const char* names[] = {"Strength", "Dexterity", "Life", "Mana"};' in values_fill
assert ('text << names[i] << "\\n" << (known ? breakAttributeValue(formatProfileValue(values[i])) : std::string("-"));'
        in values_fill), 'the attribute cells show label and rounded value, broken into the lines of the cell'


def break_attribute_value(value):
    """Python replica of breakAttributeValue in SocialWindow.cpp."""
    lines = []
    while len(value) > LINE_CHARS:
        cut = LINE_CHARS
        for i in range(LINE_CHARS, LINE_CHARS // 2 - 1, -1):
            if value[i - 1] in ',.' or value[i] in 'eE':
                cut = i
                break
        lines.append(value[:cut])
        value = value[cut:]
    return lines + [value]


for value in ALL_NUMBERS + ('11', '-', '42,600', '41.666666666666664'):
    assert ''.join(break_attribute_value(value)) == value, ('a character of the value is lost', value)
    assert all(0 < len(part) <= LINE_CHARS for part in break_attribute_value(value)), value
assert LINE_CHARS == 14, 'the expected breaks below are written for 14 characters per line'
for value, expected in (('14', ['14']), ('42,600', ['42,600']), ('41.666666666666664', ['41.66666666666', '6664']),
                        ('-9.876543210987655e+280', ['-9.87654321098', '7655e+280']),
                        ('-987,654,321,098,765.4', ['-987,654,321,', '098,765.4']),
                        ('-1.0000000000000002e-05', ['-1.00000000000', '00002e-05'])):
    assert break_attribute_value(value) == expected, (value, break_attribute_value(value))
ATTRIBUTE_TEXTS = {name: tuple(name + '\n' + '\n'.join(break_attribute_value(n)) for n in ALL_NUMBERS + ('-', '0'))
                   for name in ATTRIBUTES}
ATTRIBUTE_LINES = max(t.count('\n') + 1 for texts in ATTRIBUTE_TEXTS.values() for t in texts)
cells = [boxes['ValuesPage/' + name][0] for name in ATTRIBUTES]
for cell in cells[1:]:
    assert abs(cell[1] - cells[0][1]) < 1e-9 and abs(cell[3] - cells[0][3]) < 1e-9, 'the four attributes share ONE row'
    assert abs((cell[2] - cell[0]) - (cells[0][2] - cells[0][0])) < 1e-3, 'the four attribute cells are equally wide'
for left, right in zip(cells, cells[1:]):
    assert left[2] < right[0], 'Strength, Dexterity, Life, Mana from left to right without overlap'
combat_panel = boxes['ValuesPage/CombatPanel'][0]
assert abs(cells[0][0] - combat_panel[0]) < 1e-9 and abs(cells[-1][2] - combat_panel[2]) < 1e-9, \
    'the attribute row spans the right column like the combat block below it'
assert boxes['ValuesPage/Portrait'][0][3] <= cells[0][1] + 1e-9 and cells[0][3] <= combat_panel[1] + 1e-9, \
    'the attribute row lies between the portrait ring and the combat block'
for name in ATTRIBUTES:
    cell = {p.get('name'): p.get('value') for p in boxes['ValuesPage/' + name][1].findall('Property')}
    assert cell['Font'] == 'MedievalSharp-8' and cell['HorzFormatting'] == 'CentreAligned', name
    assert cell['BackgroundEnabled'] == 'True' and 'Text' not in cell, name
assert not any(re.fullmatch(r'ValuesPage/(Strength|Dexterity|Life|Mana)\w+', n) for n in boxes), 'one window per attribute'
# The Equipment, Path and Skills tiles show symbol and title (book-variant-2); their whole text is in the tooltip and
# in the path and skills rows of the profile page, which word wrap and scroll (first part of this check)
assert 'entry.equipment, entry.path, entry.skills' in social and 'fitTextToWindow' not in social
tiles = function_of(social, 'void SocialWindow::refreshValues(')
for fragment in ('const std::string tooltip = std::string(tiles[i]) + ": " + value;',
                 'page->getChild(std::string(tiles[i]) + "Tile")->setTooltipText(tooltip);',
                 'page->getChild(std::string(tiles[i]) + "Title")->setTooltipText(tooltip);'):
    assert fragment in tiles, fragment
for name in ('Equipment', 'Path', 'Skills'):
    assert 'ValuesPage/%sValue' % name not in boxes, name + ' tile shows a shortened text'
    tile = boxes['ValuesPage/%sTile' % name][1].find("Property[@name='MousePassThroughEnabled']")
    assert tile is not None and tile.get('value') == 'False', name + ' tile must show its tooltip'
shared_page = (repo / 'gui/WindowCreatureProfilePage.layout').read_text()
assert 'name="PathText"' in shared_page and 'name="SkillsText"' in shared_page
for row in ('PathText', 'SkillsText'):
    assert re.search(r'name="%s"\s*>(?:(?!</Window>).)*WordWrapLeftAligned' % row, shared_page, re.S), row + ' word wraps'
assert re.search(r'textRows(?:Before|After)\[\] = \{[^}]*"SkillsText"', body), 'the skills row flows and scrolls'
assert 'page->getChild("PathText")->setText("Path: " + getSkillPathText());' in creature_cpp
assert 'page->getChild("SkillsText")->setText("Skills: " + getSkillListText());' in creature_cpp
# Out of sight the fallback profile holds equipment, path and skills in full and scrolls when it is longer
fallback = social[social.index('// Out of sight the profile'):social.index('// The posts of the creature')]
assert '"\\nEquipment: " + entry.equipment + "\\nPath: " + entry.path + "\\nSkills: " + entry.skills' in fallback
assert 'fallback->setText(escapeMarkup(text));' in fallback
social_text = boxes['ProfilePage/SocialText'][1]
assert social_text.find("Property[@name='VertScrollbar']").get('value') == 'True', 'the fallback profile scrolls'
assert social_text.find("Property[@name='HorzFormatting']").get('value').startswith('WordWrap')
# No text of the book ends in "..." (decision 732): no shortening helper, no dots, the whole text is set
for gone in ('elideToWidth', 'setElidedText', 'fitTextToWindow', 'isTileTextFitting', '"..."', "'...'", '+ "..'):
    assert gone not in social, gone + ' shortens a text of the Dungeonbook'
assert 'void setFullText(CEGUI::Window* window, const std::string& text)' in social
assert 'window->setText(escapeMarkup(text));' in function_of(social, 'void setFullText(')
for call in ('setFullText(home->getChild("CreaturesLabel"), label.str());',
             'setFullText(row->getChild("Name"), profile.getFullName());',
             'setFullText(header->getChild("NameText"), profile.getFullName());',
             'setFullText(page->getChild("NameText"), profile.getFullName());',
             'setFullText(page->getChild("KeeperText"), "Keeper: " + entry.keeper);',
             'head->setText(std::string(FEED_NAME_COLOUR) + escapeMarkup(profile.getFullName()) + FEED_TIME_COLOUR',
             'textWindow->setText(std::string(FEED_TEXT_COLOUR) + escapeMarkup(text));'):
    assert call in social, call
profile_fill = function_of(creature_cpp, 'float Creature::fillProfilePage(CEGUI::Window* page)')
assert '"..."' not in profile_fill and 'std::string("nothing to say")' in profile_fill, 'the profile status ends in "..."'
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


def require(name, font, lines=1, texts=(), pad_w=6.0, pad_h=0.0, wrap=False):
    """A window and the texts it must show in full. A wrapped window word wraps every text with the shipped font at its
    width (as CEGUI does, at the spaces) and must be high enough for all its lines and wide enough for its widest word;
    lines is the least number of lines it has room for."""
    if wrap:
        formatting = boxes[name][1].find("Property[@name='HorzFormatting']")
        assert formatting is not None and formatting.get('value').startswith('WordWrap'), name + ' must word wrap'
    need[name] = (font, lines, texts, pad_w, pad_h, wrap)


def wrap_lines(font, text, width):
    """Lines of the text word wrapped at the spaces to the width (CEGUI word wrap); a word never splits."""
    lines = []
    for paragraph in text.split('\n'):
        current = ''
        for word in paragraph.split(' '):
            trial = word if not current else current + ' ' + word
            if current and text_width(font, trial) > width + 1e-6:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    return lines


# The longest texts the book can show (owner decision 732: names and post texts in full, word wrapped). Names: every
# given name with every surname and epithet of config/social-names.cfg (CreatureProfile::getFullName). Posts: every
# post template of config/social-texts.cfg with each slot filled by its widest values (names, hometowns, jobs, likes,
# dislikes, quirks, rooms of CreaturePosts::getRoomName, item names of items.cfg and potions.cfg, level 30).
name_groups = []
for line in (repo / 'config/social-names.cfg').read_text().split('\n'):
    cells = line.split('\t')
    if cells[0] == '[NameGroup]':
        name_groups.append({'given': [], 'last': [], 'home': []})
    elif cells[0] == 'Given':
        name_groups[-1]['given'] += [c for c in cells[2:] if c]
    elif cells[0] in ('Surname', 'Title'):
        name_groups[-1]['last'] += [c for c in cells[1:] if c]
    elif cells[0] == 'Hometown':
        name_groups[-1]['home'] += [c for c in cells[1:] if c]
full_names = [g + ((' ' + s) if s else '') for group in name_groups for g in group['given'] for s in [''] + group['last']]
assert len(full_names) > 5000 and 'CreatureProfile' in (repo / 'source/social/CreatureProfile.h').read_text()


def widest(pool, font='MedievalSharp-8', count=3):
    return sorted(set(pool), key=lambda t: -text_width(font, t))[:count]


WIDEST_NAMES_8 = widest(full_names) + sorted(full_names, key=len)[-1:]
WIDEST_NAMES_10 = widest(full_names, 'MedievalSharp-10') + sorted(full_names, key=len)[-1:]
pools = {'job': [], 'like': [], 'dislike': [], 'quirk': []}
templates = []
for line in (repo / 'config/social-texts.cfg').read_text().split('\n'):
    cells = line.split('\t')
    if cells[0].lower() in pools:
        pools[cells[0].lower()].append(cells[-1])
    elif cells[0] == 'Post':
        templates.append(cells[-1])
assert len(templates) > 300 and all(pools.values()), 'post templates and slot pools are read'
items = ['Soul crystal', 'Ectoplasm', 'Mana crystal', 'Research book']
for cfg in ('items.cfg', 'potions.cfg'):
    items += re.findall(r'^\s*Display\s+(.+?)\s*$', (repo / 'config' / cfg).read_text(), re.M)
posts_source = (repo / 'source/social/CreaturePosts.cpp').read_text()
rooms = re.findall(r'return "([a-z ]+)";', posts_source[posts_source.index('CreaturePosts::getRoomName'):][:3000])
assert len(items) > 50 and len(rooms) > 15, (len(items), len(rooms))
slot_values = {'name': WIDEST_NAMES_8, 'friend': WIDEST_NAMES_8, 'hometown': widest([h for g in name_groups for h in g['home']]),
               'job': widest(pools['job']), 'like': widest(pools['like']), 'dislike': widest(pools['dislike']),
               'quirk': widest(pools['quirk']), 'level': ['30'], 'room': widest(rooms), 'item': widest(items)}
import itertools
WORST_POSTS = []
for template in templates:
    slots = sorted(set(re.findall(r'\{(\w+)\}', template)))
    for choice in itertools.product(*(slot_values.get(s, ['']) for s in slots)):
        values = dict(zip(slots, choice))
        WORST_POSTS.append(re.sub(r'\{(\w+)\}', lambda m: values.get(m[1], ''), template))
# The age of a post (formatAge) and the level or crown (about two letters wide) after the name in the feed head
AGES = ('just now', '59 sec ago', '59 min ago', '2147483 h ago')
HEADS = [n + '   ' + level + age for n in WIDEST_NAMES_8 for level in ('', 'Lv. 30 - ', 'WW - ') for age in AGES]
LINK_LEFT = float(re.search(r'PROFILE_LINK_LEFT = ([0-9.]+)f', gui)[1])
for link in ('FriendLink0', 'FriendLink1', 'FoeLink'):
    assert re.search(r'name="%s"\s*>\s*<Property name="Area" value="\{\{0\.0,%d\},' % (link, LINK_LEFT), page_layout_text), link
NICK = 'W' * 20  # the nick of a keeper has at most 20 characters (MenuModeMultiplayerServer)
assert 'nickCeguiStr.length() > 20' in (repo / 'source/modes/MenuModeMultiplayerServer.cpp').read_text()

require('HomePage/CreaturesLabel', 'MedievalSharp-10', texts=('Known creatures (999 of 999)',), wrap=True)
for f, text in zip(filters, ('[ All ]', '[ Workers ]', '[ Fighters ]', '[ Unhappy ]')):
    require(f, 'MedievalSharp-8', texts=(text,), pad_w=14.0, pad_h=6.0)
require('HomePage/FeedTitle', 'MedievalSharp-10', texts=('All-Creature Feed',))
for row in list_rows:
    require(row + '/Name', 'MedievalSharp-8', lines=2, texts=WIDEST_NAMES_8, wrap=True)
    require(row + '/Level', 'MedievalSharp-8', texts=('Lv. 30',))
    require(row + '/Mood', 'MedievalSharp-8', texts=('Furious', 'Content', 'Neutral', 'Unhappy', 'Hungry'), wrap=True)
for page in ('HomePage', 'FeedPage'):
    for i in range(3):
        require('%s/FeedRows/Row%d/Head' % (page, i), 'MedievalSharp-8', texts=HEADS, wrap=True)
        require('%s/FeedRows/Row%d/Text' % (page, i), 'MedievalSharp-8', lines=2, texts=WORST_POSTS, wrap=True)
    require(page + '/FeedEmpty', 'MedievalSharp-8', lines=2)
require('FeedPage/FeedTitle', 'MedievalSharp-10', texts=('Feed',))
require('Header/NameText', 'MedievalSharp-10', texts=WIDEST_NAMES_10, wrap=True)
for n in nav:
    require(n + '/Label', 'MedievalSharp-10', texts=(boxes[n + '/Label'][1].find("Property[@name='Text']").get('value'),))
require('ProfilePage/NameText', 'MedievalSharp-10', texts=WIDEST_NAMES_10, wrap=True)
require('ProfilePage/KeeperText', 'MedievalSharp-8', texts=('Keeper: ' + NICK, 'Keeper: Player 1'), wrap=True)
require('ProfilePage/InfoText', 'MedievalSharp-8', lines=4, texts=('Mood: Furious', 'Level 30'))
require('ProfilePage/PostsTitle', 'MedievalSharp-10', texts=('Posts (200)',))
require('ProfilePage/SocialHolder', 'MedievalSharp-8', lines=6)
require('ProfilePage/PostsEmpty', 'MedievalSharp-8', lines=2, texts=('Nothing posted yet.',))
# Values: rounded numbers (two decimals at most, every magnitude); a pair "a / b" wraps after the slash
pairs = tuple(a + ' / ' + b for a in WORST_NUMBERS[-3:] for b in WORST_NUMBERS[-3:])
for name, label in (('Experience', 'Experience:'), ('HitPoints', 'Hit points:'), ('Gold', 'Gold:'),
                    ('SightRadius', 'Sight radius:'), ('Potions', 'Potions:'), ('Inventory', 'Inventory:'),
                    ('DamagePerSecond', 'Damage per second:'), ('SkillPoints', 'Skill points:')):
    require('ValuesPage/%sLabel' % name, 'MedievalSharp-8', texts=(label,), pad_w=4.0)
    require('ValuesPage/%sValue' % name, 'MedievalSharp-8', lines=2, texts=WORST_NUMBERS + pairs + ('-',), pad_w=4.0,
            wrap=True)
# The attribute cells of the one row: label and every value line of every magnitude, whole (decision 816)
assert ATTRIBUTE_LINES == 3, ATTRIBUTE_LINES
for name in ATTRIBUTES:
    require('ValuesPage/' + name, 'MedievalSharp-8', lines=ATTRIBUTE_LINES, texts=ATTRIBUTE_TEXTS[name])
require('ValuesPage/CombatLabels', 'MedievalSharp-8', lines=3, texts=('Critical %', 'Attack Rating', 'Defense Rating'))
require('ValuesPage/DefenseLabels', 'MedievalSharp-8', lines=3, texts=('Physical Defense', 'Magical Defense', 'Element Defense'))
require('ValuesPage/CombatValues', 'MedievalSharp-8', lines=3, texts=tuple(n + '%' for n in WORST_NUMBERS) + WORST_NUMBERS)
require('ValuesPage/DefenseValues', 'MedievalSharp-8', lines=3, texts=WORST_NUMBERS)
for name in ('Equipment', 'Path', 'Skills'):
    require('ValuesPage/%sTitle' % name, 'MedievalSharp-8', texts=(name,), pad_w=2.0)
for i, label in enumerate(labels):
    require('InventoryPage/SlotBox%d/Label' % i, 'MedievalSharp-6', texts=(label,), pad_w=2.0)
require('InventoryPage/PotionsLabel', 'MedievalSharp-8', texts=('Potions',))
require('InventoryPage/InventoryLabel', 'MedievalSharp-8', texts=('Inventory',))
require('InventoryPage/HintText', 'MedievalSharp-8', lines=4)
for name in need:
    assert name in boxes, name

state_lines = []
wrapped_lines = {}
narrowest_link = 1e9
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
        for name, (font, lines, texts, pad_w, pad_h, wrap) in need.items():
            box = boxes[name][0]
            width = (box[2] - box[0]) * client_w
            height = (box[3] - box[1]) * client_h
            if wrap:
                # every text in full: all its wrapped lines in the height, its widest word in the width
                wrapped = [wrap_lines(font, t, width - pad_w) for t in texts]
                lines = max([lines] + [len(w) for w in wrapped])
                words = [word for t in texts for word in t.replace('\n', ' ').split(' ')]
                wanted_w = max([text_width(font, word) + pad_w for word in words] + [0.0])
                assert all(text_width(font, part) + pad_w <= width + 1e-6 for w in wrapped for part in w), name
                wrapped_lines[name] = max(wrapped_lines.get(name, 0), lines)
            else:
                wanted_w = max([text_width(font, part) + pad_w for t in texts for part in t.split('\n')] + [0.0])
            wanted_h = lines * line_height(font) + pad_h
            assert height + 1e-6 >= wanted_h, ('text too high for its window', name, screen_w, screen_h, user,
                                               round(height, 1), round(wanted_h, 1))
            assert width + 1e-6 >= wanted_w, ('text too wide for its window', name, screen_w, screen_h, user,
                                              round(width, 1), round(wanted_w, 1))
            page = name.split('/')[0]
            ratio = max(wanted_h / height, wanted_w / width)
            if ratio > tightest.get(page, (0.0, ''))[0]:
                tightest[page] = (ratio, name)
        # The friend and foe names of the shared profile page are one-line buttons from PROFILE_LINK_LEFT to the right
        # margin of the holder (Gui::layoutCreatureProfilePage): the widest name must fit whole
        holder = boxes['ProfilePage/SocialHolder'][0]
        link_width = (holder[2] - holder[0]) * client_w - LINK_LEFT - 32.0
        assert link_width >= max(text_width('MedievalSharp-8', n) for n in WIDEST_NAMES_8) + 2.0,             ('a friend name is wider than its link', screen_w, screen_h, user, round(link_width, 1))
        narrowest_link = min(narrowest_link, link_width)
        # the slot pictures stay squares of at least 24 screen pixels, the portraits at least 40
        for i in range(13):
            slot = boxes['InventoryPage/SlotBox%d/Slot%d' % (i, i)][0]
            edge = min((slot[2] - slot[0]) * client_w, (slot[3] - slot[1]) * client_h) * scale
            assert edge >= 12.0, ('slot too small', screen_w, screen_h, user, edge)
        # the one attribute row: each cell in screen pixels and the room its widest and highest text takes
        cell = boxes['ValuesPage/Strength'][0]
        cell_w, cell_h = (cell[2] - cell[0]) * client_w, (cell[3] - cell[1]) * client_h
        attribute_w = max(text_width('MedievalSharp-8', part) + 6.0 for name in ATTRIBUTES
                          for t in ATTRIBUTE_TEXTS[name] for part in t.split('\n'))
        state_lines.append('%dx%d UI %d%%: attribute row 4 cells of %dx%d px, widest line %.0f%% of the width, '
                           'label + %d value lines %.0f%% of the height' % (
                               screen_w, screen_h, round(user * 100), round(cell_w * scale), round(cell_h * scale),
                               attribute_w / cell_w * 100, ATTRIBUTE_LINES - 1,
                               ATTRIBUTE_LINES * line_height('MedievalSharp-8') / cell_h * 100))
        state_lines.append('%dx%d UI %d%%: book %dx%d px (fit %.2f); tightest text per page: %s' % (
            screen_w, screen_h, round(user * 100), round(win_w * scale), round(win_h * scale), fit,
            ', '.join('%s %s %.0f%%' % (p.replace('Page', ''), tightest[p][1].split('/')[-1], tightest[p][0] * 100)
                      for p in ('HomePage', 'Header', 'FeedPage', 'ProfilePage', 'ValuesPage', 'InventoryPage', 'NavBar')
                      if p in tightest)))
print('Dungeonbook pages verified: start page, head with back/previous/next arrows, bottom navigation, feed, profile, '
      'values sheet and 13-slot inventory fit 640x480 to 8K at 80 to 120 percent')
for line in state_lines:
    print('  ' + line)
print('Full texts (decision 732), most wrapped lines at any size: list name %d, feed head %d, post text %d (%d posts), '
      'head name %d, profile name %d, keeper %d, value %d; widest value %s; narrowest friend link %.0f of %.0f design px' % (
          wrapped_lines['HomePage/ListRows/Row0/Name'], wrapped_lines['HomePage/FeedRows/Row0/Head'],
          wrapped_lines['HomePage/FeedRows/Row0/Text'], len(WORST_POSTS), wrapped_lines['Header/NameText'],
          wrapped_lines['ProfilePage/NameText'], wrapped_lines['ProfilePage/KeeperText'],
          wrapped_lines['ValuesPage/HitPointsValue'], WORST_NUMBERS[-1], narrowest_link,
          max(text_width('MedievalSharp-8', n) for n in WIDEST_NAMES_8)))
