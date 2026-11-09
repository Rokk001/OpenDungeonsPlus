"""Static check: the back arrow and the previous and next arrows of a Dungeonbook creature page take the click (owner
decision 921). No game and no compiler needed.

Cause found in the CEGUI 0.8 source: the pages (HomePage .. InventoryPage) cover the head of the book, and a left click
anywhere on a page raises that page above its siblings (Window::onMouseButtonDown -> moveToFront_impl(true), rise on
click). After the first click on a page the page lay over the head, and CEGUI hit testing (front window first) gave
the click on an arrow to the page. The head and the navigation bar are now always on top of the pages.
Checked here:
1. Header and NavBar are AlwaysOnTop children of the book, the pages are not; the pages do overlap the head.
2. A model of CEGUI drawing order and hit testing: after a click on every page the centre of each arrow still hits the
   arrow (without the fix the raised page takes it).
3. The arrows are connected: back shows the start page, previous and next step through the listed creatures with wrap.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
book = ET.fromstring((repo / 'gui/WindowSocial.layout').read_text(encoding='utf-8')).find('Window')
social = (repo / 'source/render/SocialWindow.cpp').read_text(encoding='utf-8')

PAGES = ('HomePage', 'FeedPage', 'ProfilePage', 'ValuesPage', 'InventoryPage')
ARROWS = ('BackButton', 'PrevButton', 'NextButton')


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


def inside(point, box):
    return box[0] <= point[0] < box[2] and box[1] <= point[1] < box[3]


def function_of(text, signature):
    body = text[text.index(signature):]
    return body[:body.index('\n}\n')]


client = (0.0, 0.0, 1.0, 1.0)
children = book.findall('Window')
header = child(book, 'Header')
header_box = area(header, client)

# 1. Layout
for name in ('Header', 'NavBar'):
    assert props(child(book, name)).get('AlwaysOnTop') == 'True', name + ' must stay on top of the pages'
for name in PAGES:
    page = child(book, name)
    assert props(page).get('AlwaysOnTop') != 'True', name
    assert props(page).get('MousePassThroughEnabled') != 'True', 'the page takes the clicks on its free space'
    box = area(page, client)
    assert box[1] < header_box[3], name + ' overlaps the head; without AlwaysOnTop a raised page covers the arrows'

# 2. Drawing order and hit testing with rise on click (CEGUI Window::addWindowToDrawList)
def build_order(use_layout_flags):
    order = []
    for window in children:
        top = use_layout_flags and props(window).get('AlwaysOnTop') == 'True'
        insert_order(order, (window.get('name'), top))
    return order


def insert_order(order, entry):
    if entry[1]:
        order.append(entry)
    else:
        order.insert(len([1 for _, t in order if not t]), entry)


def click(order, name):
    entry = [e for e in order if e[0] == name][0]
    order.remove(entry)
    insert_order(order, entry)


def hit(order, point, shown):
    for name, _ in reversed(order):
        if name in shown and inside(point, area(child(book, name), client)):
            return name
    return None


for fixed in (False, True):
    for page in PAGES[1:]:
        order = build_order(fixed)
        click(order, page)
        for arrow in ARROWS:
            box = area(child(header, arrow), header_box)
            centre = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            target = hit(order, centre, {page, 'Header', 'NavBar'})
            if fixed:
                assert target == 'Header', '%s after a click on %s: %s takes the click' % (arrow, page, target)
            else:
                assert target == page, 'the model shows the reported fault for %s on %s' % (arrow, page)

# 3. The handlers
constructor = function_of(social, 'SocialWindow::SocialWindow(')
for arrow, handler in (('BackButton', 'onBackClicked'), ('PrevButton', 'onPreviousClicked'),
                       ('NextButton', 'onNextClicked')):
    assert re.search(r'connect\(mWindow->getChild\("Header/%s"\), CEGUI::PushButton::EventClicked,\s*'
                     r'CEGUI::Event::Subscriber\(&SocialWindow::%s, this\)\);' % (arrow, handler), constructor), arrow
assert 'showPage(Page::Home);' in function_of(social, 'bool SocialWindow::onBackClicked(')
assert 'stepCreature(-1);' in function_of(social, 'bool SocialWindow::onPreviousClicked(')
assert 'stepCreature(1);' in function_of(social, 'bool SocialWindow::onNextClicked(')
step = function_of(social, 'void SocialWindow::stepCreature(int direction)')
assert '% count;' in step and 'mSelectedCreature = mListedCreatures[index];' in step and 'showPage(mPage);' in step


def step_model(index, count, direction):
    return (index + count + (count - 1 if direction < 0 else 1)) % count


assert [step_model(i, 3, 1) for i in range(3)] == [1, 2, 0]
assert [step_model(i, 3, -1) for i in range(3)] == [2, 0, 1]

print('check_dungeonbook_header_clicks_921: OK')
