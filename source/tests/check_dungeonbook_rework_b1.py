"""Static check of the Dungeonbook rework after owner check build 0.7.3.37 (decision 664, package B1).

No game and no compiler needed. Targets: book-variant-2.png (pages of one creature) and book-switch-variant-1.png (start
page) in G:/Moreya-Internal/medien/ingame-qs-8/m1/.

1. Whole book: start page with the creature list left and the all-creature feed right, the pages of one creature with
   the bottom navigation; framed panels with the thin rust frame of the concepts.
2. Profile: portrait left, data in the middle, posts right. The portrait lies over nothing: the build 37 portrait
   used HorizontalAlignment Centre, a window alignment in CEGUI, so it was centred in the page and covered the name,
   the health and XP bars and the handle. The boxes below are computed WITH the CEGUI alignment rules.
   The left column holds only the portrait and the info text.
3. Inventory: no slot (Left Hand and Armour included) touches the portrait.
4. Feed: every post row of both feeds has a picture, filled with a real game picture (room or thing of the post from
   the shipped OpenDungeonsIcons imageset) or else the portrait of the creature.
5. Sizes: pictures, post thumbnails and portraits keep a readable size at 640x480, 1920x1200 and 7680x4320 with the UI
   scale 80 % and 120 % (check_dungeonbook_profile_layout.py measures the texts of all pages at the same sizes).
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
layout_text = (repo / 'gui/WindowSocial.layout').read_text()
book = ET.fromstring(layout_text).find('Window')
social = (repo / 'source/render/SocialWindow.cpp').read_text()
header = (repo / 'source/render/SocialWindow.h').read_text()


def props(element):
    return {p.get('name'): p.get('value') for p in element.findall('Property')}


def collect(element, box, path, out):
    """Absolute boxes (fractions of the frame client) with the CEGUI rules for HorizontalAlignment and
    VerticalAlignment: Centre puts the window in the middle of its parent, the area position is an offset from there."""
    for child in element.findall('Window'):
        p = props(child)
        dims = [float(a) for a, _ in re.findall(r'\{(-?[0-9.]+),(-?[0-9.]+)\}', p['Area'])]
        x0, y0, x1, y1 = dims
        width, height = box[2] - box[0], box[3] - box[1]
        w, h = (x1 - x0) * width, (y1 - y0) * height
        left = box[0] + x0 * width
        top = box[1] + y0 * height
        if p.get('HorizontalAlignment') == 'Centre':
            left = box[0] + (width - w) / 2 + x0 * width
        if p.get('VerticalAlignment') == 'Centre':
            top = box[1] + (height - h) / 2 + y0 * height
        absolute = (left, top, left + w, top + h)
        name = (path + '/' if path else '') + child.get('name')
        out[name] = (absolute, child)
        collect(child, absolute, name, out)


boxes = {}
collect(book, (0.0, 0.0, 1.0, 1.0), '', boxes)


def overlaps(a, b):
    return a[0] < b[2] - 1e-9 and b[0] < a[2] - 1e-9 and a[1] < b[3] - 1e-9 and b[1] < a[3] - 1e-9


RUST = 'tl:FF6E4A2C tr:FF6E4A2C bl:FF6E4A2C br:FF6E4A2C'


def framed(name):
    p = props(boxes[name][1])
    return p.get('FrameEnabled') == 'True' and p.get('FrameColours') == RUST


# 1. Whole book
home = 'HomePage'
assert boxes['HomePage/ListRows'][0][2] <= boxes['HomePage/FeedRows'][0][0], 'start page: list left, feed right'
assert props(boxes['HomePage/FeedTitle'][1])['Text'] == 'All-Creature Feed'
assert framed('HomePage/ListPanel') and framed('HomePage/FeedPanel'), 'list and feed sit in framed panels'
assert boxes['HomePage/ListPanel'][0][2] <= boxes['HomePage/FeedPanel'][0][0], 'the two panels do not overlap'
for row in range(7):
    assert framed('HomePage/ListRows/Row%d/PortraitFrame' % row), 'list portraits are framed'
nav = boxes['NavBar'][0]
for page in ('HomePage', 'FeedPage', 'ProfilePage', 'ValuesPage', 'InventoryPage'):
    assert boxes[page][0][3] <= nav[1] + 1e-6, page + ' ends above the bottom navigation (variant 2)'
assert props(boxes['FeedPage/FeedTitle'][1])['Text'] == 'Feed'
print('1. whole book: start page list left / feed right in framed panels, bottom navigation on every page')

# 2. Profile: portrait left, data middle, posts right; the portrait covers nothing
portrait = boxes['ProfilePage/Portrait']
pp = props(portrait[1])
assert 'HorizontalAlignment' not in pp and 'VerticalAlignment' not in pp, \
    'the portrait frame must be placed at its area, not centred in the page (build 37 bug)'
assert framed('ProfilePage/Portrait')
clip = boxes['ProfilePage/Portrait/Clip']
image = props(boxes['ProfilePage/Portrait/Clip/Image'][1])
assert clip[1].get('type') == 'DefaultWindow' and image.get('ClippedByParent', 'True') == 'True', \
    'the picture is clipped by the frame, nothing of it reaches the text'
assert image['AspectMode'] == 'Expand' and image['AspectRatio'] == '1', 'square portrait, filled like the concept'
assert 'page->getChild("Portrait/Clip/Image")' in social
middle = ('NameText', 'KeeperText', 'SocialHolder', 'SocialText')
right = ['PostsTitle', 'PostsEmpty'] + ['PostThumb%d' % i for i in range(6)]
for name in middle + tuple(right):
    assert not overlaps(portrait[0], boxes['ProfilePage/' + name][0]), ('the portrait lies over', name)
    assert boxes['ProfilePage/' + name][0][0] >= portrait[0][2] - 1e-9, name + ' is right of the portrait'
for name in middle:
    assert boxes['ProfilePage/' + name][0][2] <= boxes['ProfilePage/ColumnRule'][0][0] + 1e-9, name + ' in the middle'
for name in right:
    assert boxes['ProfilePage/' + name][0][0] >= boxes['ProfilePage/ColumnRule'][0][2] - 1e-9, name + ' right'
# The health and XP bars and the handle are rows of the shared page inside SocialHolder: they stay clear as well
assert 'mProfilePage = gui.createCreatureProfilePage(holder)' in social
# The left column holds only the portrait and the info text (class, level, mood); nothing else is drawn there
left_column = [n for n in boxes if n.startswith('ProfilePage/') and n.count('/') == 1
               and boxes[n][0][0] < portrait[0][2] - 1e-9]
assert sorted(left_column) == ['ProfilePage/InfoText', 'ProfilePage/Portrait'], left_column
assert boxes['ProfilePage/InfoText'][0][1] >= portrait[0][3] - 1e-9, 'the info text sits below the portrait'
# Posts as pictures in two columns, three rows (book-variant-2)
thumbs = [boxes['ProfilePage/PostThumb%d' % i][0] for i in range(6)]
for i, a in enumerate(thumbs):
    assert framed('ProfilePage/PostThumb%d' % i) and 'ProfilePage/PostThumb%d/Image' % i in boxes
    for b in thumbs[i + 1:]:
        assert not overlaps(a, b), 'post pictures overlap'
assert abs(thumbs[0][1] - thumbs[1][1]) < 1e-9 and thumbs[0][2] <= thumbs[1][0], 'two pictures per row'
assert 'MAX_OWN_POSTS = 6' in social
posts = social[social.index('// The posts of the creature'):social.index('//! \\brief Fills the values sheet')]
for fragment in ('findPostPicture(*it)', 'thumb->setTooltipText(text', '->setVisible(false)', '"PostsEmpty"',
                 '"Posts (" + std::to_string(count) + ")"'):
    assert fragment in posts, fragment
print('2. profile: portrait left without window centring, data middle, six post pictures right; left column clean')

# 3. Inventory: the slots stay right of the portrait
inv = boxes['InventoryPage/Portrait']
ip = props(inv[1])
assert 'HorizontalAlignment' not in ip and 'VerticalAlignment' not in ip, 'inventory portrait centred in the page'
assert 'page->getChild("Portrait/Clip/Image")' in social[social.index('void SocialWindow::refreshInventory'):]
for i in range(13):
    slot = boxes['InventoryPage/SlotBox%d' % i]
    assert not overlaps(inv[0], slot[0]), ('slot over the portrait', props(boxes['InventoryPage/SlotBox%d/Label' % i][1])['Text'])
    assert slot[0][0] >= inv[0][2], 'every slot is right of the portrait'
for name in ('HintText', 'PotionsLabel', 'InventoryLabel'):
    assert not overlaps(inv[0], boxes['InventoryPage/' + name][0]), name
# head above left hand / armour / right hand, boots and ring below (book-variant-2)
head, right_hand, left_hand, armour, boots, ring = (boxes['InventoryPage/SlotBox%d' % i][0] for i in (2, 0, 1, 3, 4, 5))
assert head[3] <= armour[1] and abs(head[0] - armour[0]) < 1e-9
assert left_hand[2] <= armour[0] and armour[2] <= right_hand[0] and abs(left_hand[1] - right_hand[1]) < 1e-9
assert armour[3] <= boots[1] and boots[2] <= ring[0]
print('3. inventory: Left Hand, Armour and all other slots right of the portrait, variant 2 arrangement')

# 4. Feed: every post has a picture
for page in ('HomePage', 'FeedPage'):
    for row in range(3):
        base = '%s/FeedRows/Row%d' % (page, row)
        picture = boxes[base + '/Picture']
        assert framed(base + '/Picture') and base + '/Picture/Image' in boxes, base
        assert picture[0][1] >= boxes[base + '/Text'][0][3] - 1e-9, 'the picture sits below the text'
        assert not overlaps(picture[0], boxes[base + '/Portrait'][0]), 'the picture leaves the portrait free'
        assert picture[0][3] <= boxes[base][0][3] + 1e-9, 'the picture stays inside its row'
feed = social[social.index('void SocialWindow::rebuildFeed'):social.index('void SocialWindow::refreshPage')]
assert 'setImage(picture->getChild("Image"), findPostPicture(post));' in feed
assert 'const CEGUI::Image* findPostPicture(const social::Post& post) const;' in header
finder = social[social.index('const CEGUI::Image* SocialWindow::findPostPicture'):]
finder = finder[:finder.index('\n}\n')]
assert 'return findPortrait(post.mCreature, post.mClassName, post.mIsWorker, false);' in finder, \
    'a post without a room or thing shows the portrait of the creature'
assert 'images.isDefined("OpenDungeonsIcons/" + name)' in finder, 'only shipped pictures are used'
icons = {i.get('name') for i in ET.parse(repo / 'gui/ODIcons.imageset').getroot().findall('Image')}
pictures = social[social.index('std::string roomPictureName('):social.index('//! \\brief The text shortened')]
used = set(re.findall(r'return "(\w+)";', pictures)) | set(re.findall(r'\? "(\w+)"', pictures))
assert used, 'no pictures found'
for name in used:
    assert name in icons, name + ' is not a picture of the game'
categories = set(re.findall(r'^\s+(\w+),', (repo / 'source/social/PostLog.h').read_text().split('enum class PostCategory')[1]
                            .split('};')[0], re.M))
for category in re.findall(r'PostCategory::(\w+):', pictures):
    assert category in categories, category
rooms = (repo / 'source/rooms/RoomType.h').read_text()
for room in re.findall(r'RoomType::(\w+):', pictures):
    assert re.search(r'\b%s\b' % room, rooms), room
print('4. feed: every post row of both feeds has a picture (%d game pictures, portrait otherwise)' % len(used))

# 5. Sizes at 640x480, 1920x1200 and 8K, UI 80 % and 120 % (the window is 860x620 design pixels, fitted to the screen)
size = re.search(r'name="Area" value="\{\{0\.5,(-?\d+)\},\{0\.5,(-?\d+)\},\{0\.5,(\d+)\},\{0\.5,(\d+)\}\}"', layout_text)
book_w, book_h = int(size[3]) - int(size[1]), int(size[4]) - int(size[2])
CLIENT_W, CLIENT_H = book_w - 32.0, book_h - 52.0
for screen_w, screen_h in ((640, 480), (1920, 1200), (7680, 4320)):
    for user in (0.8, 1.2):
        scale = min(screen_w / 1024.0, screen_h / 768.0) * user
        fit = min(1.0, screen_w / (book_w * scale), screen_h / (book_h * scale))
        px = scale * fit

        def edge(name):
            b = boxes[name][0]
            return min((b[2] - b[0]) * CLIENT_W, (b[3] - b[1]) * CLIENT_H) * px

        smallest = {
            'feed picture': min(edge('%s/FeedRows/Row%d/Picture' % (p, r)) for p in ('HomePage', 'FeedPage') for r in range(3)),
            'post thumbnail': min(edge('ProfilePage/PostThumb%d' % i) for i in range(6)),
            'portrait': min(edge('ProfilePage/Portrait'), edge('InventoryPage/Portrait')),
        }
        limits = {'feed picture': 28.0, 'post thumbnail': 40.0, 'portrait': 100.0}
        for name, value in smallest.items():
            assert value >= limits[name], (name, screen_w, screen_h, user, round(value))
        assert book_w * fit * scale <= screen_w + 1e-6 and book_h * fit * scale <= screen_h + 1e-6
        print('  %dx%d UI %d%%: book %dx%d px, smallest feed picture %d px, post picture %d px, portrait %d px' % (
            screen_w, screen_h, round(user * 100), round(book_w * px), round(book_h * px),
            smallest['feed picture'], smallest['post thumbnail'], smallest['portrait']))
print('5. sizes: pictures and portraits readable from 640x480 to 8K at UI 80 and 120 percent')
