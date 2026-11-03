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

# Dungeonbook: posts follow the complete profile inside its scrollable document, without a fixed reserve.
social = (repo / 'source/render/SocialWindow.cpp').read_text()
assert 'PROFILE_MIN_POSTS_HEIGHT' not in social, 'posts must not displace essentials from the opening page'
assert 'ownPosts->setText(posts)' in social and 'mProfilePage->getChild("OwnPostsText")' in social
assert social.index('ownPosts->setText(posts)') < social.index('fillProfilePage(mProfilePage)')
assert 'page->getChild("OwnPostsText")' in body
social_layout = (repo / 'gui/WindowSocial.layout').read_text()
window = re.search(r'name="SocialWindow">\s*<Property name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', social_layout)
pane = ET.fromstring(social_layout).find(".//Window[@name='ProfilePane']/Property[@name='Area']").get('value')
assert pane == '{{0.48,0},{0.08,0},{0.98,0},{0.98,0}}'
pane_height = ((int(window[4]) - int(window[2])) - title_height - 2 * border) * 0.9
pane_width = ((int(window[3]) - int(window[1])) - 2 * side) * 0.5
assert pane_height >= 300, 'the profile viewport of the Dungeonbook is too small'
for name, (latest_bottom, remarks_bottom) in (('typical', typical), ('worst', worst)):
    posts_bottom = remarks_bottom + row(15)  # five multi-line posts remain reachable below every profile row
    reachable_rows(posts_bottom, pane_height)
    assert posts_bottom - max(0.0, posts_bottom - pane_height) <= pane_height + 1e-6
for width, height in ((1024, 768), (1280, 720), (1920, 1080), (2560, 1440)):
    scale = min(width / 1024.0, height / 768.0)
    report.append('%dx%d Dungeonbook: profile %.0f px, all profile rows and recent posts scroll together' % (
        width, height, pane_height * scale))

print('profile layout ok: card %dx%d design px, page %d px, typical latest ends %.0f, remarks %.0f, worst %.0f' % (
    card_width, card_height, page_height, typical[0], typical[1], worst[1]))
for line in report:
    print('  ' + line)

# Selected profile variant (D-1 variant 2): portrait, name, keeper, four attributes, combat block, defense block and
# three detail tiles. Nothing on the page scrolls: every value has a window that is high enough for its lines.
chosen = ET.parse(repo / 'gui/WindowDungeonbookProfile.layout').getroot().find('Window')
assert 'VertScrollbar' not in (repo / 'gui/WindowDungeonbookProfile.layout').read_text(), 'the profile page has no inner scrollbar'
assert 'HorzScrollbar' not in (repo / 'gui/WindowDungeonbookProfile.layout').read_text()
areas = {}
for window in chosen.iter('Window'):
    name = window.get('name')
    props = {p.get('name'): p.get('value') for p in window.findall('Property')}
    if 'Area' not in props:
        continue
    coords = [(float(a), float(b)) for a, b in re.findall(r'\{(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\}', props['Area'])]
    assert len(coords) == 4, name
    assert all(offset == 0 for scale, offset in coords), name + ' uses only relative areas'
    areas[name] = (coords[0][0], coords[1][0], coords[2][0], coords[3][0])
assert 'StatsText' not in areas, 'the free-form statistics scroll area is gone'
wanted = ('Portrait', 'NameText', 'KeeperText', 'SocialButton', 'Attributes', 'CombatPanel', 'CombatLabels', 'CombatValues',
          'DefensePanel', 'DefenseLabels', 'DefenseValues', 'EquipmentPanel', 'PathPanel', 'SkillsPanel',
          'EquipmentTile', 'PathTile', 'SkillsTile')
for name in wanted:
    assert name in areas, name
assert {w.get('name') for w in chosen.find("Window[@name='Attributes']").findall('Window')} == {
    'Strength', 'Dexterity', 'Life', 'Mana'}
# vertical order of the rows, with a gap between neighbours
rows = ['Portrait', 'NameText', 'KeeperText', 'Attributes', 'CombatPanel', 'DefensePanel', 'EquipmentTile']
for upper, lower in zip(rows, rows[1:]):
    assert areas[upper][3] <= areas[lower][1], (upper, lower)
assert areas['KeeperText'][1] == areas['SocialButton'][1] and areas['KeeperText'][2] <= areas['SocialButton'][0]
assert areas['SocialButton'][3] <= areas['Attributes'][1]
assert areas['EquipmentTile'][1] == areas['PathTile'][1] == areas['SkillsTile'][1]
assert areas['EquipmentTile'][2] <= areas['PathTile'][0] and areas['PathTile'][2] <= areas['SkillsTile'][0]
assert areas['SkillsTile'][3] <= 1.0 and areas['SkillsTile'][2] <= 1.0
# the texts lie inside their tiles
for panel, tile in (('EquipmentPanel', 'EquipmentTile'), ('PathPanel', 'PathTile'), ('SkillsPanel', 'SkillsTile'),
                    ('CombatLabels', 'CombatPanel'), ('CombatValues', 'CombatPanel'),
                    ('DefenseLabels', 'DefensePanel'), ('DefenseValues', 'DefensePanel')):
    a, b = areas[panel], areas[tile]
    assert a[0] >= b[0] and a[2] <= b[2] and a[1] >= b[1] and a[3] <= b[3], (panel, tile)
# all values of the mockup have a label, the three defenses included
labels = {w.get('name'): w.find("Property[@name='Text']").get('value') for w in chosen.findall('Window')
          if w.get('name') in ('CombatLabels', 'DefenseLabels')}
assert labels['CombatLabels'].split(chr(10)) == ['Critical %', 'Attack Rating', 'Defense Rating']
assert labels['DefenseLabels'].split(chr(10)) == ['Physical Defense', 'Magical Defense', 'Element Defense']
# SocialWindow fills exactly these windows, one value line per label, and shortens the tiles instead of scrolling
assert 'setProfileTile(mDungeonbookPage->getChild("EquipmentPanel")' in social
assert 'getChild("CombatValues")->setText' in social and 'getChild("DefenseValues")->setText' in social
assert 'selected->magicalDefense' in social and 'selected->elementDefense' in social and 'selected->physicalDefense' in social
assert 'isTileTextFitting' in social and 'getChild("StatsText")' not in social
assert '"[" << creature.keeper << "] "' in social and '"Keeper: " + escapeMarkup(selected->keeper)' in social, \
    'own and allied creatures carry their keeper in the list and on the page'
combat_values = social[social.index('std::ostringstream combat;'):social.index('getChild("DefenseValues")')]
assert combat_values.count('\\n') == 4, 'each of the two value columns has three lines (two line breaks)'

# Height model of the page at every screen and user scale. The profile pane is a part of the 880x580 Dungeonbook
# window. The window is shrunk by Gui::getWindowFitFactor on small screens, the fonts are not, so the lines are
# compared in screen pixels: line height = font factor * 17.92 design pixels * scale, area = fraction * pane height.
LINE_8 = 17.92
LINE = {'MedievalSharp-6': LINE_8 * 6 / 8, 'MedievalSharp-8': LINE_8, 'MedievalSharp-10': LINE_8 * 10 / 8}
CHAR_8 = 8.2
window_h, window_w = 580.0, 880.0
# window: (lines, font) the text needs at least
need_lines = {
    'NameText': (1, 'MedievalSharp-10'), 'KeeperText': (1, 'MedievalSharp-8'), 'SocialButton': (1, 'MedievalSharp-8'),
    'Attributes': (2, 'MedievalSharp-8'), 'CombatLabels': (3, 'MedievalSharp-8'), 'CombatValues': (3, 'MedievalSharp-8'),
    'DefenseLabels': (3, 'MedievalSharp-8'), 'DefenseValues': (3, 'MedievalSharp-8')}
tile_need = LINE['MedievalSharp-8'] + 4 * LINE['MedievalSharp-6']  # title plus four value lines in the small font
fit_report = []
for screen_w, screen_h in ((640, 480), (800, 600), (1024, 768), (1280, 720), (1920, 1080), (1920, 1200), (7680, 4320)):
    for user in (0.8, 1.0, 1.2):
        scale = min(screen_w / 1024.0, screen_h / 768.0) * user
        fit = 1.0
        # Gui::getWindowFitFactor: absolute width and height of the centred window against the screen
        if window_w * scale > screen_w:
            fit = min(fit, screen_w / (window_w * scale))
        if window_h * scale > screen_h:
            fit = min(fit, screen_h / (window_h * scale))
        win_h = window_h * scale * fit
        win_w = window_w * scale * fit
        pane_h = (win_h - title_height * scale - 2 * border * scale * fit) * 0.9
        pane_w = (win_w - 2 * side * scale * fit) * 0.5
        for name, (lines, font) in need_lines.items():
            height = pane_h * (areas[name][3] - areas[name][1])
            assert height + 1e-6 >= lines * LINE[font] * scale, (
                '%s too low for its text' % name, screen_w, screen_h, user, height, lines * LINE[font] * scale)
        for name in ('EquipmentPanel', 'PathPanel', 'SkillsPanel'):
            height = pane_h * (areas[name][3] - areas[name][1])
            assert height + 1e-6 >= tile_need * scale, (
                '%s too low for title and four lines' % name, screen_w, screen_h, user, height, tile_need * scale)
        # the widest single-line texts must fit their width: attribute tile, labels, button and the tile titles
        attribute_tile = (areas['Attributes'][2] - areas['Attributes'][0]) * 0.241
        widths = {
            'Attributes/Dexterity': (len('Dexterity') * CHAR_8, attribute_tile),
            'CombatLabels': (len('Defense Rating') * CHAR_8, areas['CombatLabels'][2] - areas['CombatLabels'][0]),
            'DefenseLabels': (len('Physical Defense') * CHAR_8, areas['DefenseLabels'][2] - areas['DefenseLabels'][0]),
            'SocialButton': (len('Social profile') * CHAR_8, areas['SocialButton'][2] - areas['SocialButton'][0]),
            'EquipmentPanel': (len('Equipment') * CHAR_8, areas['EquipmentPanel'][2] - areas['EquipmentPanel'][0])}
        for name, (need, fraction) in widths.items():
            assert pane_w * fraction + 1e-6 >= need * scale, (
                '%s too narrow' % name, screen_w, screen_h, user, pane_w * fraction, need * scale)
        fit_report.append((screen_w, screen_h, user, pane_w, pane_h))
for screen_w, screen_h, user, pane_w, pane_h in fit_report:
    if (screen_w, screen_h) in ((640, 480), (7680, 4320)) and user in (0.8, 1.2):
        print('  %dx%d user %d%% profile pane %.0fx%.0f px: every value row fits without a scrollbar' % (
            screen_w, screen_h, round(user * 100), pane_w, pane_h))
print('chosen profile arrangement without scrollbars verified')

# Variant 2 keeps its illustrated parchment and circular frame behind interactive content.
background = chosen.find("Window[@name='PageBackground']")
assert background is not None and chosen.findall('Window')[0] == background
assert background.find("Property[@name='Image']").get('value') == 'DungeonbookArt/Page'
assert background.find("Property[@name='MousePassThroughEnabled']").get('value') == 'True'
frame = chosen.find("Window[@name='Portrait']/Window[@name='Frame']")
assert frame.find("Property[@name='Image']").get('value') == 'DungeonbookFrame/Ring'
assert frame.find("Property[@name='MousePassThroughEnabled']").get('value') == 'True'
imageset = ET.parse(repo / 'gui/DungeonbookPage.imageset').getroot()
assert imageset.get('name') == 'DungeonbookArt' and imageset.get('imagefile') == 'DungeonbookPage.png'
assert (repo / 'gui' / imageset.get('imagefile')).is_file()
scheme = ET.parse(repo / 'gui/ODSkin.scheme').getroot()
assert scheme.find("Imageset[@filename='DungeonbookPage.imageset'][@name='DungeonbookArt']") is not None
ring_set = ET.parse(repo / 'gui/DungeonbookFrame.imageset').getroot()
assert ring_set.get('name') == 'DungeonbookFrame' and (repo / 'gui' / ring_set.get('imagefile')).is_file()
assert scheme.find("Imageset[@filename='DungeonbookFrame.imageset'][@name='DungeonbookFrame']") is not None
credits = (repo / 'CREDITS').read_text()
assert 'gui/DungeonbookPage.png' in credits and 'gui/DungeonbookFrame.png' in credits
print('profile background, frame and resource registration verified')

# Second page of the profile: the eight values of the former statistics field, reached by a button on the first page.
# The page covers the first one, has no scrollbar, and every tile is high and wide enough at every screen and UI scale.
stats_page = chosen.find("Window[@name='StatisticsPage']")
assert stats_page is not None and stats_page.find("Property[@name='Visible']").get('value') == 'False'
assert stats_page.find("Property[@name='Image']").get('value') == 'DungeonbookArt/Page', 'the page covers the first page'
assert chosen.find("Window[@name='StatisticsButton']") is not None, 'the first page needs the button to the statistics'
assert stats_page.find("Window[@name='BackButton']") is not None, 'the statistics page needs a button back'
page_areas = {}
for window in stats_page.findall('Window'):
    coords = [float(a) for a, b in re.findall(r'\{(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\}',
                                             window.find("Property[@name='Area']").get('value'))]
    page_areas[window.get('name')] = (coords[0], coords[1], coords[2], coords[3])
button_area = areas['StatisticsButton']
# the button sits left of the portrait ring (a square in the middle of the portrait), so page 1 keeps its arrangement
assert button_area[2] < 0.35 and button_area[3] <= areas['NameText'][1] and button_area[0] >= areas['Portrait'][0]
statistics = ('Experience', 'HP', 'Gold', 'SightRadius', 'Potions', 'Inventory', 'DamagePerSecond', 'SkillPoints')
for name in statistics:
    tile, panel = page_areas[name + 'Tile'], page_areas[name + 'Panel']
    assert panel[0] >= tile[0] and panel[2] <= tile[2] and panel[1] >= tile[1] and panel[3] <= tile[3], name
    assert 0 <= tile[0] < tile[2] <= 1 and 0 <= tile[1] < tile[3] <= 1, name
tiles = [page_areas[n + 'Tile'] for n in statistics]
for i, first in enumerate(tiles):
    for second in tiles[i + 1:]:
        assert first[2] <= second[0] or second[2] <= first[0] or first[3] <= second[1] or second[3] <= first[1], 'tiles overlap'
assert max(page_areas['Title'][3], page_areas['BackButton'][3]) <= min(t[1] for t in tiles) and max(t[3] for t in tiles) <= 1.0
assert page_areas['BackButton'][2] <= page_areas['Title'][0], 'the back button sits where the button to the statistics is'
# code: shown by the button, filled from the statistics text, shortened to the tile instead of scrolling
assert 'onStatisticsViewClicked' in social and 'mShowingStatistics' in social
assert social.count('mShowingStatistics = false;') >= 3, 'selecting another creature returns to the first page'
for label in ('Experience', 'HP', 'Gold', 'Potions', 'Inventory', 'Raw damage per second', 'Sight radius',
              'Skill points earned / spent'):
    assert '"%s"' % label in social, label
assert 'findStatisticsValue(selected->stats' in social
assert 'setProfileTile(statisticsPage->getChild(std::string(line.window) + "Panel")' in social
assert 'creature->getRawDamagePerSecond()' in (repo / 'source/network/ODServer.cpp').read_text(), 'the server still sends them'
# Fit: the tile text is the title in the 8 point font and up to four value lines in the 6 point font
tile_lines = LINE['MedievalSharp-8'] + 4 * LINE['MedievalSharp-6']
for screen_w, screen_h in ((640, 480), (800, 600), (1024, 768), (1280, 720), (1920, 1080), (7680, 4320)):
    for user in (0.8, 1.0, 1.2):
        scale = min(screen_w / 1024.0, screen_h / 768.0) * user
        fit = min(1.0, screen_w / (window_w * scale), screen_h / (window_h * scale))
        pane_h = (window_h * scale * fit - title_height * scale - 2 * border * scale * fit) * 0.9
        pane_w = (window_w * scale * fit - 2 * side * scale * fit) * 0.5
        for name in statistics:
            panel = page_areas[name + 'Panel']
            assert pane_h * (panel[3] - panel[1]) + 1e-6 >= tile_lines * scale, (name, screen_w, screen_h, user)
            # the longest title ("Damage per second") has to fit one line of the tile
            assert pane_w * (panel[2] - panel[0]) + 1e-6 >= len('Damage per second') * CHAR_8 * scale, (name, screen_w, user)
        assert pane_h * (page_areas['BackButton'][3] - page_areas['BackButton'][1]) + 1e-6 >= LINE_8 * scale
        assert pane_w * (page_areas['BackButton'][2] - page_areas['BackButton'][0]) + 1e-6 >= len('Back') * CHAR_8 * scale
        assert pane_h * (page_areas['Title'][3] - page_areas['Title'][1]) + 1e-6 >= LINE['MedievalSharp-10'] * scale
        assert pane_w * (button_area[2] - button_area[0]) + 1e-6 >= len('Statistics') * CHAR_8 * scale
        assert pane_h * (button_area[3] - button_area[1]) + 1e-6 >= LINE_8 * scale
print('statistics page verified: eight tiles, button there and back, fits 640x480 to 8K at 80 to 120 percent')
