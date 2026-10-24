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
assert rows == ['StatusText', 'LatestText', 'QuirksText'], rows
# The loop bounds must match the lengths of the two row lists
before_rows = [r for r in before.split(',') if r.strip()]
assert 'i < ' + str(len(before_rows)) + ';' in body and 'i < 3;' in body, 'row counts do not match the row lists'

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
holder = re.search(r'name="ProfilePage" >\s*<Property name="Area" value="\{\{0\.0,0\},\{0\.0,(\d+)\},\{1\.0,0\},\{1\.0,(-\d+)\}\}"', layout)
page_height = card_height - int(holder[1]) + int(holder[2])
text_width = card_width - 32

LINE, PAD, GAP, TOP = 18.0, 4.0, 4.0, 174.0
# attributes, equipment, path and skills: four one line rows above the bio
ATTRIBUTE_ROWS = 4
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

# Dungeonbook: the profile gets the pane minus the room kept for the recent posts
social = (repo / 'source/render/SocialWindow.cpp').read_text()
minimum = float(re.search(r'PROFILE_MIN_POSTS_HEIGHT = ([0-9.]+)f', social)[1])
gap = float(re.search(r'OWN_POSTS_GAP = ([0-9.]+)f', social)[1])
assert 'UDim(1, -PROFILE_MIN_POSTS_HEIGHT)' in social, 'the profile holder must leave the room for the posts'
assert social.index('UDim(1, -PROFILE_MIN_POSTS_HEIGHT)') < social.index('fillProfilePage(mProfilePage)'), 'the holder is set after the fill'
social_layout = (repo / 'gui/WindowSocial.layout').read_text()
window = re.search(r'name="SocialWindow">\s*<Property name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', social_layout)
pane = re.search(r'name="ProfilePane">\s*<Property name="Area" value="\{\{0,(\d+)\},\{0,(\d+)\},\{1,(-\d+)\},\{1,(-\d+)\}\}"', social_layout)
pane_height = (int(window[4]) - int(window[2])) - int(pane[2]) + int(pane[4])
pane_width = (int(window[3]) - int(window[1])) - int(pane[1]) + int(pane[3])
dungeonbook_viewport = pane_height - minimum
posts_height = pane_height - (dungeonbook_viewport + gap)
assert posts_height >= minimum - gap > 0, 'the recent posts keep no room'
assert dungeonbook_viewport >= 300, 'the profile viewport of the Dungeonbook is too small'
# the profile of the Dungeonbook scrolls as well: all rows are reachable also in the smaller viewport
for name, (latest_bottom, remarks_bottom) in (('typical', typical), ('worst', worst)):
    reachable_rows(remarks_bottom, dungeonbook_viewport)
# worst case: the profile scrolls, the posts keep their height
for name, (latest_bottom, remarks_bottom) in (('typical', typical), ('worst', worst)):
    shown = min(remarks_bottom, dungeonbook_viewport)
    assert pane_height - (shown + gap) >= minimum - gap, name
for width, height in ((1024, 768), (1280, 720), (1920, 1080), (2560, 1440)):
    scale = min(width / 1024.0, height / 768.0)
    report.append('%dx%d Dungeonbook: pane %.0f px, profile %.0f px (typical %.0f, worst %.0f design px of content), posts at least %.0f px' % (
        width, height, pane_height * scale, dungeonbook_viewport * scale, typical[1], worst[1], (minimum - gap) * scale))

print('profile layout ok: card %dx%d design px, page %d px, typical latest ends %.0f, remarks %.0f, worst %.0f' % (
    card_width, card_height, page_height, typical[0], typical[1], worst[1]))
for line in report:
    print('  ' + line)
