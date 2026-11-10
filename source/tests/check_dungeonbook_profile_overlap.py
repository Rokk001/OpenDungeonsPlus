"""Check that nothing overlaps on the profile page of the Dungeonbook (owner decision 830, finding d).

Static check, no game needed. The owner saw the Health bar run into the handle line "@bodge... - Worker - Level 1":
the bar row was 20 design pixels high with a 4 pixel gap above the handle line, and the "Health" label (42 design
pixels of text) had a 48 pixel box right up to the bar. The page measured here:

1. The Dungeonbook profile page (gui/WindowSocial.layout): portrait, info text, name, keeper line, the holder of the
   shared profile page, the column rule and the posts column do not overlap (texts that replace each other aside).
2. The shared profile page (gui/WindowCreatureProfilePage.layout, flowed by Gui::layoutCreatureProfilePage) in the
   holder of the book (compact, the rows start at the top) and on the creature card: the bar row is one label line
   high, its bars sit inside it, the labels hold their text and end before their bars, the experience bar ends before
   the scrollbar, and the handle line (word wrapped, the widest handle the names can give) starts PROFILE_BAR_ROW_GAP
   below the bar row. Every pair of these windows is free of overlap.

Measured with the shipped font at 640x480 to 7680x4320 (ten screens) and every UI scale from 80 to 120 percent.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from PIL import ImageFont

repo = Path(__file__).resolve().parents[2]
gui = (repo / 'source/render/Gui.cpp').read_text()
body = gui[gui.index('float Gui::layoutCreatureProfilePage'):]
body = body[:body.index('\nvoid Gui::applyProfileScroll')]


def constant(name):
    return float(re.search(r'const float %s = ([0-9.]+)f;' % name, gui)[1])


ROW_GAP, PAD = constant('PROFILE_ROW_GAP'), constant('PROFILE_LINE_PADDING')
SIDE, RIGHT, INSET = constant('PROFILE_SIDE_MARGIN'), constant('PROFILE_RIGHT_MARGIN'), constant('PROFILE_ROW_INSET_TOTAL')
BAR_H, BAR_ROW_MIN, BAR_GAP = (constant('PROFILE_BAR_HEIGHT'), constant('PROFILE_BAR_ROW_MIN_HEIGHT'),
                               constant('PROFILE_BAR_ROW_GAP'))
FLOW_TOP = constant('PROFILE_FLOW_TOP')
assert BAR_GAP >= 2 * ROW_GAP, 'the bars keep a clear gap to the handle line'
# The flow of the bar row as the replica below does it
for fragment in ('const float barRowHeight = std::max(PROFILE_BAR_ROW_MIN_HEIGHT,\n'
                 '        getProfileLinesHeight(page->getChild("HealthLabel"), 1, scale));',
                 'const float barTop = (barRowHeight - PROFILE_BAR_HEIGHT) / 2.0f;',
                 'area.d_min.d_y = CEGUI::UDim(0, y + ((i % 2 == 0) ? 0.0f : barTop));',
                 'area.d_max.d_y = CEGUI::UDim(0, y + ((i % 2 == 0) ? barRowHeight : barTop + PROFILE_BAR_HEIGHT));',
                 'y += barRowHeight + PROFILE_BAR_ROW_GAP;',
                 'const char* const personalRows[] = {"HandleText", "AgeText", "RelationText", "FromText", "JobText"};',
                 'float y = compact ? PROFILE_ROW_GAP : std::max(PROFILE_FLOW_TOP, 34.0f + equipmentHeight + PROFILE_ROW_GAP);'):
    assert fragment in body, fragment
assert body.index('const char* const barNames') < body.index('y += barRowHeight') < body.index('personalRows[i]')
assert 'CEGUI::URect area = mScaledWindows.find(child)->second.area;' in body, 'the bars keep their layout columns'
row_fn = gui[gui.index('float Gui::layoutProfileTextRow('):]
row_fn = row_fn[:row_fn.index('\n}\n')]
assert 'width = parent->getPixelSize().d_width - PROFILE_ROW_INSET_TOTAL * scale;' in row_fn
assert 'return y + height + PROFILE_ROW_GAP;' in row_fn
assert 'return font->getLineSpacing() * static_cast<float>(lines) / scale + PROFILE_LINE_PADDING;' in gui

# Shipped font, in design pixels (fonts scale like the layout)
spec = ET.parse(repo / 'gui/fonts/MedievalSharp-8.font').getroot()
face = ImageFont.truetype(str(repo / 'gui/fonts' / spec.get('filename')), 1024)
FACTOR = float(spec.get('size')) * (96.0 / 72.0) * (1024.0 / 800.0) / 1024.0
LINE = sum(face.getmetrics()) * FACTOR


def text_width(text):
    return face.getlength(text) * FACTOR


def wrapped_lines(text, width):
    lines, current = 1, ''
    for word in text.split(' '):
        trial = (current + ' ' + word).strip()
        if current and text_width(trial) > width:
            lines += 1
            current = word
        else:
            current = trial
    return lines


# The columns of the bar row in the shared page
page_root = ET.parse(repo / 'gui/WindowCreatureProfilePage.layout').getroot().find('Window')
columns = {}
for window in page_root.findall('Window'):
    area = window.find("Property[@name='Area']").get('value')
    dims = [(float(a), float(b)) for a, b in re.findall(r'\{(-?[0-9.]+),(-?[0-9.]+)\}', area)]
    columns[window.get('name')] = (dims[0], dims[2])
for name in ('HealthLabel', 'ExperienceLabel'):
    label = page_root.find("Window[@name='%s']" % name)
    assert label.find("Property[@name='Font']").get('value') == 'MedievalSharp-8', name
    assert label.find("Property[@name='VertFormatting']").get('value') == 'CentreAligned', name
    assert label.find("Property[@name='FrameEnabled']").get('value') == 'False', name + ' has no frame padding'
creature_cpp = (repo / 'source/entities/Creature.cpp').read_text()
assert 'page->getChild("HealthLabel")->setText("Health");' in creature_cpp
assert 'page->getChild("ExperienceLabel")->setText("XP");' in creature_cpp
LABEL_TEXT = {'HealthLabel': 'Health', 'ExperienceLabel': 'XP'}

# The widest handle line: "@" + the widest given name in small letters + the largest number, the class and level 30
handle_fn = creature_cpp[creature_cpp.index('std::string makeProfileHandle('):]
handle_fn = handle_fn[:handle_fn.index('\n}\n')]
assert 'std::string handle = "@";' in handle_fn and 'PROFILE_HANDLE_MIN_NUMBER' in handle_fn
numbers = {m[0]: int(m[1]) for m in re.findall(r'(PROFILE_HANDLE_(?:MIN_NUMBER|NUMBER_COUNT)) = (\d+);', creature_cpp)}
largest_number = str(numbers['PROFILE_HANDLE_MIN_NUMBER'] + numbers['PROFILE_HANDLE_NUMBER_COUNT'] - 1)
assert '" - Level " + Helper::toString(getLevel())' in creature_cpp and '(definition->isWorker() ? "Worker" : "Fighter")' in creature_cpp
given = []
for line in (repo / 'config/social-names.cfg').read_text().split('\n'):
    cells = line.split('\t')
    if cells[0] == 'Given':
        given += [c for c in cells[2:] if c]
assert len(given) > 100
handles = sorted({'@' + ''.join(c for c in g.lower() if c.isascii() and c.isalnum()) + largest_number for g in given},
                 key=lambda h: -text_width(h))[:3]
HANDLE_TEXTS = [h + ' - ' + kind + ' - Level 30' for h in handles for kind in ('Worker', 'Fighter')] + [
    '@bodge' + largest_number + ' - Worker - Level 1']
OTHER_ROWS = ('Age 2147483647 - Female', 'Relationship: It is complicated', 'From: Mudcrest')


def overlap(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def flow(page_w, scale, compact):
    """The rectangles (design pixels of the page) of the bar row and the first rows, as layoutCreatureProfilePage
    places them. scale only matters through the line heights, which are the same in design pixels at every size."""
    y = ROW_GAP if compact else FLOW_TOP + LINE + PAD + ROW_GAP  # the card has the attributes line above the bars
    rects = {}
    row_h = max(BAR_ROW_MIN, LINE + PAD)
    bar_top = (row_h - BAR_H) / 2.0
    for name in ('HealthLabel', 'HealthBar', 'ExperienceLabel', 'ExperienceBar'):
        (lx, lo), (rx, ro) = columns[name]
        left, right = lx * page_w + lo, rx * page_w + ro
        top, bottom = (y, y + row_h) if name.endswith('Label') else (y + bar_top, y + bar_top + BAR_H)
        rects[name] = (left, top, right, bottom)
    bar_row_bottom = y + row_h
    y += row_h + BAR_GAP
    width = page_w - INSET
    for name, texts in (('HandleText', HANDLE_TEXTS), ('AgeText', OTHER_ROWS[:1]), ('RelationText', OTHER_ROWS[1:2]),
                        ('FromText', OTHER_ROWS[2:])):
        lines = max(wrapped_lines(t, width) for t in texts)
        height = lines * LINE + PAD
        rects[name] = (SIDE, y, page_w - RIGHT, y + height)
        y += height + ROW_GAP
    (lx, lo), (rx, ro) = columns['ProfileScrollbar']
    rects['ProfileScrollbar'] = (lx * page_w + lo, 0.0, rx * page_w + ro, y + 1000.0)
    return rects, bar_row_bottom


# 1. The book's profile page (WindowSocial.layout), boxes as fractions of the frame client
social_layout = (repo / 'gui/WindowSocial.layout').read_text()
book = ET.fromstring(social_layout).find('Window')
size = re.search(r'name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', social_layout)
book_w, book_h = int(size[3]) - int(size[1]), int(size[4]) - int(size[2])
profile = book.find("Window[@name='ProfilePage']")


def fractions(element):
    value = element.find("Property[@name='Area']").get('value')
    dims = [(float(a), float(b)) for a, b in re.findall(r'\{(-?[0-9.]+),(-?[0-9.]+)\}', value)]
    assert all(offset == 0 for _, offset in dims), element.get('name') + ' scales with its parent'
    return tuple(d[0] for d in dims)


page_box = fractions(profile)
book_boxes = {w.get('name'): fractions(w) for w in profile.findall('Window')}
# Windows that are shown instead of each other: the fallback text instead of the holder, "Nothing posted yet."
# instead of the post pictures
alternatives = {frozenset(('SocialHolder', 'SocialText'))} | {
    frozenset(('PostsEmpty', 'PostThumb%d' % i)) for i in range(6)}
names = sorted(book_boxes)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        if frozenset((a, b)) not in alternatives:
            assert not overlap(book_boxes[a], book_boxes[b]), ('the profile page of the book overlaps', a, b)
holder = book_boxes['SocialHolder']
assert book_boxes['KeeperText'][3] <= holder[1] and book_boxes['NameText'][3] <= book_boxes['KeeperText'][1]
assert book_boxes['Portrait'][2] <= holder[0] and book_boxes['ColumnRule'][2] <= holder[0]

# 2. The shared page in the book (compact) and on the card, on every screen and UI scale
skin = ET.parse(repo / 'gui/ODSkin.imageset').getroot()
side = float(skin.find("Image[@name='WindowLeftEdge']").get('width')) / 4.0
book_images = ET.parse(repo / 'gui/DungeonbookIcons.imageset').getroot()
FRAME_PX = max(float(book_images.find("Image[@name='BookFrame%s']" % n).get(d))
               for n, d in (('Left', 'width'), ('Right', 'width'), ('Bottom', 'height')))
card_layout = (repo / 'gui/WindowCreatureProfile.layout').read_text()
card = re.search(r'name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', card_layout)
card_w, card_h = int(card[3]) - int(card[1]), int(card[4]) - int(card[2])
design = re.search(r'LAYOUT_DESIGN_WIDTH = ([0-9.]+)f', gui), re.search(r'LAYOUT_DESIGN_HEIGHT = ([0-9.]+)f', gui)
design_w, design_h = float(design[0][1]), float(design[1][1])
SCREENS = ((640, 480), (800, 600), (1024, 768), (1280, 720), (1366, 768), (1920, 1080), (1920, 1200), (2560, 1440),
           (3840, 2160), (7680, 4320))
checked = 0
narrowest = {}
smallest_gap = 1e9
for screen_w, screen_h in SCREENS:
    for percent in range(80, 121):
        scale = min(screen_w / design_w, screen_h / design_h) * percent / 100.0
        book_fit = min(1.0, screen_w / (book_w * scale), screen_h / (book_h * scale))
        frame = FRAME_PX * min(screen_w / 3840.0, screen_h / 2160.0) / scale
        book_page_w = (book_w * book_fit - 2 * frame) * (page_box[2] - page_box[0]) * (holder[2] - holder[0])
        card_fit = min(1.0, screen_w / (card_w * scale), screen_h / (card_h * scale))
        card_page_w = card_w * card_fit - 2 * side
        for owner, page_w, compact in (('Dungeonbook', book_page_w, True), ('card', card_page_w, False)):
            rects, bar_row_bottom = flow(page_w, scale, compact)
            for label, bar in (('HealthLabel', 'HealthBar'), ('ExperienceLabel', 'ExperienceBar')):
                l, b = rects[label], rects[bar]
                # the label holds its word on one line, vertically inside its box, and ends before its bar
                assert text_width(LABEL_TEXT[label]) <= l[2] - l[0], (owner, label, 'text wider than its box')
                assert LINE <= l[3] - l[1] + 1e-6, (owner, label, 'text higher than its box')
                assert l[2] + 4.0 <= b[0], (owner, label, 'runs into its bar')
                # the bar lies inside the row and is wide enough to be read
                assert l[1] <= b[1] and b[3] <= l[3], (owner, bar, 'leaves the bar row')
                assert b[2] - b[0] >= 40.0, (owner, bar, screen_w, screen_h, percent, round(b[2] - b[0], 1))
                narrowest[owner] = min(narrowest.get(owner, 1e9), b[2] - b[0])
            assert rects['HealthBar'][2] + 4.0 <= rects['ExperienceLabel'][0], (owner, 'Health bar runs into XP')
            assert rects['ExperienceBar'][2] <= rects['ProfileScrollbar'][0], (owner, 'XP bar under the scrollbar')
            # the handle line starts a clear gap below the whole bar row, also in screen pixels
            gap = rects['HandleText'][1] - bar_row_bottom
            assert gap >= BAR_GAP - 1e-6 and gap * scale >= 4.0, (owner, screen_w, screen_h, percent, gap)
            smallest_gap = min(smallest_gap, gap * scale)
            names = [n for n in rects if n != 'ProfileScrollbar']
            for i, a in enumerate(names):
                for b in names[i + 1:]:
                    assert not overlap(rects[a], rects[b]), (owner, screen_w, screen_h, percent, a, b)
                    checked += 1
            for name in ('HandleText', 'AgeText', 'RelationText', 'FromText'):
                assert not overlap(rects[name], rects['ProfileScrollbar']), (owner, name, 'under the scrollbar')

print('profile overlap ok: bar row %.1f design px (labels one line of %.1f), gap %.0f to the handle line, smallest gap '
      '%.1f screen px; narrowest bar %.0f (book) / %.0f (card) design px; %d window pairs at %d screens x 41 UI scales'
      % (max(BAR_ROW_MIN, LINE + PAD), LINE, BAR_GAP, smallest_gap, narrowest['Dungeonbook'], narrowest['card'],
         checked, len(SCREENS)))
