"""Static check of the Dungeonbook after owner check build 0.7.3.41 (decision 710, finding 1). No game, no compiler.

Targets: book-variant-2.png and book-switch-variant-1.png in G:/Moreya-Internal/medien/ingame-qs-8/m1/.

Cause of the finding "every post shows the same crossed-swords placeholder": the posts of the owner's game were all
fight posts ("Intruders at the door. Rude.", "Swinging at things again.", "#fight"), and postPictureName gave every
fight post the one HUD icon OpenDungeonsIcons/FighterButton (crossed swords). The icon was drawn as a small square
(AspectMode Shrink, AspectRatio 1) in the middle of a wide empty strip, so it looked like a placeholder; every other
post kind also had only one small HUD icon instead of a picture of what happened.

1. Every post kind (PostCategory except Nb) has a painted scene DungeonbookIcons/Post*; work, training and wish posts
   take the scene of their room. The kinds of the concepts get their scene (fight, level up, hunger, digging, gold).
   No HUD icon (OpenDungeonsIcons, FighterButton) is used for a post any more.
2. The scenes are in gui/DungeonbookIcons.png as 2:1 pictures, painted (not empty, not flat) and all different.
3. The feed pictures (start page and feed of one creature) and the six profile post pictures fill their frame with
   the scene, cropped like the concept: Picture/Clip/Image, AspectMode Expand, AspectRatio 2, clipped by the frame.
4. The book has an ornate iron frame (riveted, rusty edges) and the large centred title "Dungeonbook" of the concepts.
5. No other window changes: the frame and title images, the caption formatting and the titlebar height of the shared
   looks OD/FrameWindow and OD/GameTitlebar come from properties whose defaults are exactly what the looks drew before,
   and only WindowSocial.layout sets them.
"""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image

repo = Path(__file__).resolve().parents[2]
social = (repo / 'source/render/SocialWindow.cpp').read_text(encoding='utf-8')
layout_text = (repo / 'gui/WindowSocial.layout').read_text(encoding='utf-8')
book = ET.fromstring(layout_text).find('Window')
imageset = ET.parse(repo / 'gui/DungeonbookIcons.imageset').getroot()
images = {i.get('name'): tuple(int(i.get(k)) for k in ('xPos', 'yPos', 'width', 'height'))
          for i in imageset.findall('Image')}
atlas = Image.open(repo / 'gui' / imageset.get('imagefile')).convert('RGBA')


def function_body(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start)]


# 1. A scene per post kind
picture = function_body(social, 'std::string postPictureName(const social::Post& post)')
rooms_fn = function_body(social, 'std::string roomPictureName(int32_t roomType)')
enum = (repo / 'source/social/PostLog.h').read_text(encoding='utf-8').split('enum class PostCategory')[1].split('};')[0]
categories = [c for c in re.findall(r'^\s+(\w+),?\s*$', enum, re.M) if c != 'Nb']
assert len(categories) > 40, categories
cases = re.findall(r'case PostCategory::(\w+):', picture)
assert sorted(cases) == sorted(categories), ('every post kind has exactly one scene',
                                             set(categories) ^ set(cases))
room_enum = (repo / 'source/rooms/RoomType.h').read_text(encoding='utf-8')
room_enum = room_enum.split('enum class RoomType')[1].split('};')[0]
room_types = [r for r in re.findall(r'^\s+(\w+)', room_enum, re.M) if r not in ('nullRoomType', 'nbRooms')]
room_cases = re.findall(r'case RoomType::(\w+):', rooms_fn)
assert sorted(room_cases) == sorted(room_types), ('every room has a scene', set(room_types) ^ set(room_cases))
names = set(re.findall(r'"(\w+)"', picture + rooms_fn))
assert names and all(n.startswith('Post') for n in names), names
for name in names:
    assert name in images, name + ' is not in DungeonbookIcons.imageset'
assert len(names) >= 20, ('the post kinds need many different scenes', len(names))


def scene_of(category):
    """The scene returned for a category: the first return after its case label (for a room post its default)."""
    rest = picture[picture.index('case PostCategory::%s:' % category):]
    found = re.search(r'return (?:room\.empty\(\) \? "(\w+)" : room|"(\w+)");', rest)
    return found[1] or found[2]


expected = {'Fight': 'PostFight', 'LevelUp': 'PostLevelUp', 'Eat': 'PostFood', 'ComplainHungry': 'PostFood',
            'Work': 'PostDig', 'Payday': 'PostGold', 'Sleep': 'PostSleep', 'Drank': 'PostTavern',
            'GhostScared': 'PostGhost', 'Relaxed': 'PostSpa', 'Bought': 'PostMerchant', 'Arrived': 'PostPortal'}
for category, scene in expected.items():
    assert scene_of(category) == scene, (category, scene_of(category), scene)
assert 'RoomType::trainingHall: return "PostTrain";' in rooms_fn and 'RoomType::library: return "PostLibrary";' in rooms_fn
finder = function_body(social, 'const CEGUI::Image* SocialWindow::findPostPicture(const social::Post& post) const')
assert 'images.isDefined("DungeonbookIcons/" + name)' in finder and 'OpenDungeonsIcons' not in finder
assert 'FighterButton' not in picture + rooms_fn + finder, 'the crossed-swords HUD icon is not a post picture'
print('1. %d post kinds and %d rooms mapped to %d painted scenes (fight, level up, food, dig, gold, ...)' % (
    len(categories), len(room_types), len(names)))

# 2. The scenes are real, distinct 2:1 paintings
pixels = {}
for name in sorted(names):
    x, y, w, h = images[name]
    assert w == 2 * h and h >= 192, (name, w, h)
    assert x + w <= atlas.size[0] and y + h <= atlas.size[1], name + ' lies outside the png'
    crop = np.asarray(atlas.crop((x, y, x + w, y + h)), np.float32)
    assert crop[..., 3].min() == 255, name + ' has transparent pixels'
    assert crop[..., :3].std() > 25, name + ' is flat, not a painting'
    pixels[name] = crop[::4, ::4, :3]
ordered = sorted(pixels)
for i, a in enumerate(ordered):
    for b in ordered[i + 1:]:
        assert np.abs(pixels[a] - pixels[b]).mean() > 12, ('two scenes are the same picture', a, b)
print('2. %d scenes are distinct 2:1 paintings in %s' % (len(names), imageset.get('imagefile')))


# 3. The pictures fill their frame
def props(element):
    return {p.get('name'): p.get('value') for p in element.findall('Property')}


def find(path):
    element = book
    for part in path.split('/'):
        element = element.find("Window[@name='%s']" % part)
        assert element is not None, path
    return element


frames = ['%s/FeedRows/Row%d/Picture' % (page, row) for page in ('HomePage', 'FeedPage') for row in range(3)]
frames += ['ProfilePage/PostThumb%d' % i for i in range(6)]
for path in frames:
    clip = find(path + '/Clip')
    image = props(find(path + '/Clip/Image'))
    assert clip.get('type') == 'DefaultWindow' and image.get('ClippedByParent', 'True') == 'True', path
    assert (image['AspectMode'], image['AspectRatio']) == ('Expand', '2'), (path, 'the scene fills its frame')
    assert image['Area'] == '{{0,0},{0,0},{1,0},{1,0}}' and image.get('HorizontalAlignment') == 'Centre', path
    area = [float(v) for v in re.findall(r'\{(-?[0-9.]+),0\}', props(clip)['Area'])]
    assert 0 < area[0] < 0.05 and 0.95 < area[2] < 1, (path, 'the scene stays inside the frame line')
    assert find(path).find("Window[@name='Image']") is None, path + ' still has the old small icon window'
assert 'setImage(picture->getChild("Clip/Image"), findPostPicture(post));' in social
assert 'setImage(thumb->getChild("Clip/Image"), findPostPicture(*it));' in social
print('3. %d post pictures fill their frame (Clip, Expand 2:1, centred)' % len(frames))

# 4. Ornate iron frame and large centred title of the concepts, only for the book
FRAME_PARTS = ('TopLeft', 'TopRight', 'BottomLeft', 'BottomRight', 'Top', 'Left', 'Right', 'Bottom')
TITLE_PARTS = ('TopLeft', 'TopRight', 'Top', 'Left', 'Right')
root = props(book)
assert root['Text'] == 'Dungeonbook'
for part in FRAME_PARTS:
    assert root['Frame%sImage' % part] == 'DungeonbookIcons/BookFrame' + part, part
    assert 'BookFrame' + part in images, part
titlebar_window = book.find("AutoWindow[@namePath='__auto_titlebar__']")
assert titlebar_window is not None, 'the title band of the book is set through its titlebar'
title = props(titlebar_window)
for part in TITLE_PARTS:
    assert title['Title%sImage' % part] == 'DungeonbookIcons/BookFrame' + part, part
assert title['TitleRuleImage'] == 'DungeonbookIcons/BookTitleRule' and 'BookTitleRule' in images
assert title['CaptionHorzFormatting'] == 'CentreAligned' and title['CaptionCentred'] == 'True', 'centred title'
scheme = (repo / 'gui/ODSkin.scheme').read_text(encoding='utf-8')
assert root['TitlebarFont'] == 'MedievalSharp-20' and 'name="MedievalSharp-20"' in scheme, 'large title font'
assert layout_text.index('name="TitlebarFont"') < layout_text.index('name="Area"'), \
    'the title font is set before the area, so the first layout already has the tall title band'
T = images['BookFrameLeft'][2]
assert images['BookFrameRight'][2] == T and images['BookFrameTop'][3] == T and images['BookFrameBottom'][3] == T
assert images['BookFrameLeft'][3] >= 128 and images['BookFrameTop'][2] >= 128, 'edges tile along the window'
for corner in ('TopLeft', 'TopRight', 'BottomLeft', 'BottomRight'):
    x, y, w, h = images['BookFrame' + corner]
    assert w == h and w >= T, corner
assert (imageset.get('autoScaled'), imageset.get('nativeHorzRes'), imageset.get('nativeVertRes')) == \
    ('min', '3840', '2160'), 'the frame scales with the display like the shared frame (3840x2160)'
assert T * min(1920 / 3840.0, 1200 / 2160.0) >= 16, 'the iron frame is visible at 1920x1200 (at least 16 px)'
x, y, w, h = images['BookFrameTop']
band = np.asarray(atlas.crop((x, y, x + w, y + h)), np.float32)[..., :3]
luma = band @ np.array([0.299, 0.587, 0.114])
rusty = (band[..., 0] > band[..., 1] + 25) & (band[..., 0] > 80)
assert luma.mean() < 80, 'dark iron'
assert rusty[:3].mean() > 0.5 and rusty.mean() > 0.08, 'rusty edges'
bright = luma > luma.mean() + 30   # decision 830 e: matte black iron, no shiny highlights, rivets stay visible
assert bright.any() and luma.max() < 110, 'rivets and bevel stay visible but matte'
print('4. ornate iron frame (%d px edges at 2160, riveted, rusty) and centred 20 pt title on the book only' % T)

# 5. Every other window keeps its frame and title
skin = ET.parse(repo / 'gui/OD.looknfeel').getroot()
frame_look = skin.find("WidgetLook[@name='OD/FrameWindow']")
title_look = skin.find("WidgetLook[@name='OD/GameTitlebar']")


def definitions(look):
    return {d.get('name'): d for d in look.findall('PropertyDefinition')}


fdefs, tdefs = definitions(frame_look), definitions(title_look)
for part in FRAME_PARTS:
    d = fdefs['Frame%sImage' % part]
    assert (d.get('type'), d.get('initialValue')) == ('Image', 'OpenDungeonsGameWindow/Frame' + part), part
title_defaults = {'TitleTopLeftImage': 'FrameTopLeft', 'TitleTopRightImage': 'FrameTopRight', 'TitleTopImage': 'FrameTop',
                  'TitleLeftImage': 'FrameLeft', 'TitleRightImage': 'FrameRight', 'TitleRuleImage': 'TitleRule'}
for name, part in title_defaults.items():
    assert (tdefs[name].get('type'), tdefs[name].get('initialValue')) == ('Image', 'OpenDungeonsGameWindow/' + part)
assert (tdefs['CaptionHorzFormatting'].get('initialValue'), tdefs['CaptionCentred'].get('initialValue')) == \
    ('LeftAligned', 'false'), 'other captions stay left aligned in their old area'
for look, defs in ((frame_look, fdefs), (title_look, tdefs)):
    for node in look.iter():
        if node.tag in ('ImageProperty', 'ImagePropertyDim', 'HorzFormatProperty', 'PropertyDim') and \
                node.get('name') not in ('HorzFormatting', 'VertFormatting'):
            assert node.get('name') in defs, (look.get('name'), node.tag, node.get('name'))
        if node.tag in ('Image', 'ImageDim'):
            assert 'ClientBrush' in node.get('name'), (look.get('name'), 'fixed image', node.get('name'))
# Titlebar height: the titlebar font is TitlebarFont, MedievalSharp-10 unless a layout sets it (as the fixed font before)
child = frame_look.find("Child[@nameSuffix='__auto_titlebar__']/Area/Dim[@type='Height']/FontDim")
assert child.get('widget') == '__auto_titlebar__' and child.get('font') is None and child.get('padding') == '12'
assert frame_look.find("PropertyLinkDefinition[@name='TitlebarFont']").get('initialValue') == 'MedievalSharp-10'
new_props = set(fdefs) | set(tdefs) | {'TitlebarFont'}
new_props -= {'CaptionColour'}
for other in sorted((repo / 'gui').glob('*.layout')):
    if other.name == 'WindowSocial.layout':
        continue
    text = other.read_text(encoding='utf-8', errors='replace')
    for name in new_props:
        assert 'name="%s"' % name not in text, (other.name, 'sets', name)


# The caption area: unchanged without CaptionCentred, symmetric with it (evaluated from the looknfeel)
def evaluate(node, width, top_left, centred):
    tag = node.tag
    if tag == 'UnifiedDim':
        return float(node.get('scale', '0')) * width + float(node.get('offset', '0'))
    if tag == 'AbsoluteDim':
        return float(node.get('value'))
    if tag == 'ImagePropertyDim':
        assert node.get('name') == 'TitleTopLeftImage'
        return top_left
    if tag == 'PropertyDim':
        assert node.get('name') == 'CaptionCentred'
        return 1.0 if centred else 0.0
    if tag == 'OperatorDim':
        a, b = (evaluate(n, width, top_left, centred) for n in node)
        return {'Add': lambda: a + b, 'Subtract': lambda: a - b, 'Multiply': lambda: a * b,
                'Divide': lambda: a / b}[node.get('op')]()
    raise AssertionError(tag)


area = title_look.find(".//ImagerySection[@name='caption']/TextComponent/Area")
assert title_look.find(".//ImagerySection[@name='caption']/TextComponent/HorzFormatProperty").get('name') == \
    'CaptionHorzFormatting'
for width in (400.0, 1100.0, 3960.0):
    for top_left in (10.0, 28.0):
        left = evaluate(area.find("Dim[@type='LeftEdge']")[0], width, top_left, False)
        plain = evaluate(area.find("Dim[@type='Width']")[0], width, top_left, False)
        assert (left, plain) == (top_left, width - 75), 'other windows keep their caption area'
        centred = evaluate(area.find("Dim[@type='Width']")[0], width, top_left, True)
        assert abs((width - (left + centred)) - left) < 1e-6, 'the centred title sits in the middle of the window'
print('5. other windows unchanged: shared looks default to their old images, caption area and title height')
print('check_dungeonbook_post_pictures ok')
