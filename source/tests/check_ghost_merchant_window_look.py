"""Room Manager look check: the embedded ghost and merchant pages use the shared Dungeonbook frame and
their texts stay inside the page from 640x480 to 8K at UI scale 80 to 120 %.

Game look: the same frame and title band as Dungeonbook, MedievalSharp fonts on every text and button,
gold value texts and dark framed panels. The common frame owns the close control. The merchant page has an empty-state text that
says why the stock is empty and what to do, and the client code shows it exactly when no goods are listed.

Fit: the windows are designed in 1024x768 pixels; Gui scales offsets by min(w/1024, h/768) * UI scale (and shrinks a
window to the screen), fonts by min(w/800, h/600) * UI scale. Text size is estimated with fixed font metrics of the
SourceSerif4 face behind the MedievalSharp fonts (pixel size = points * 4/3, average glyph width 0.52 em, line
height 1.35 em, 15 % word-wrap slack); every text box must hold its text (longest value the code writes) at every
tested resolution and scale.
"""
from pathlib import Path
import math
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]

FRAME_SIDE = 36.0       # BookFrameLeft/Right width and BookFrameBottom height (DungeonbookIcons.imageset)
TITLE_PADDING = 12.0    # FontDim padding of the title bar (OD.looknfeel)
RESOLUTIONS = [(640, 480), (800, 600), (1024, 768), (1280, 720), (1366, 768), (1920, 1080), (2560, 1440),
               (3440, 1440), (3840, 2160), (7680, 4320)]
SCALES = [0.8, 0.9, 1.0, 1.1, 1.2]


def props(node):
    return {p.get('name'): p.get('value') for p in node.findall('Property')}


def udims(area):
    numbers = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', area)]
    assert len(numbers) == 8, area
    return numbers


def font_points(name):
    return float(name.rsplit('-', 1)[1])


def text_fits(text, font, width, height, font_scale):
    px = font_points(font) * 4.0 / 3.0 * font_scale
    lines = 0
    for paragraph in text.split('\n'):
        lines += max(1, math.ceil(len(paragraph) * 0.52 * px * 1.15 / width))
    return lines * 1.35 * px <= height, lines


def check_window(name, layout, texts, buttons):
    """Checks an embedded page and resolves text bounds through its actual shared frame."""
    root = ET.parse(repo / 'gui' / layout).getroot()
    window = root.find('Window')
    p = props(window)
    assert window.get('type') == 'DefaultWindow', name + ': page has no separate frame'
    assert window.find('AutoWindow') is None, name + ': title belongs to Room Manager'
    children = {c.get('name'): c for c in window.findall('Window')}
    assert 'CloseButton' not in children, name + ': common frame owns the close control'
    manager = ET.parse(repo / 'gui/WindowRoomManager.layout').getroot().find('Window')
    book = ET.parse(repo / 'gui/WindowSocial.layout').getroot().find('Window')
    frame_props = props(manager)
    for key, value in props(book).items():
        if key.startswith('Frame') and key.endswith('Image') or key == 'TitlebarFont':
            assert frame_props[key] == value, 'Room Manager shares Dungeonbook ' + key
    assert props(manager.find('AutoWindow')) == props(book.find('AutoWindow')), 'shared Dungeonbook title band'
    pages = next(c for c in manager.findall('Window') if c.get('name') == 'Pages')
    for child in children.values():
        q = props(child)
        if child.get('type') in ('OD/Button', 'OD/StaticText', 'OD/MultiColumnList') and q.get('Text', 'x') != '' \
                and 'Panel' not in child.get('name'):
            assert q.get('Font', '').startswith('MedievalSharp-'), '%s/%s: game font' % (name, child.get('name'))
        assert child.get('type') != 'OD/GameTabButton', '%s/%s: HUD tab button in a window' % (name, child.get('name'))
        if 'TooltipText' in q:
            assert len(q['TooltipText']) <= 100, '%s/%s: tooltip too long to stay on screen' % (name, child.get('name'))
    wx0, wy0, wx1, wy1 = udims(frame_props['Area'])[1::2]
    wwidth, wheight = wx1 - wx0, wy1 - wy0
    for w, h in RESOLUTIONS:
        for user in SCALES:
            layout_scale = min(w / 1024.0, h / 768.0) * user
            fit = min(1.0, w / (wwidth * layout_scale), h / (wheight * layout_scale))
            s = layout_scale * fit
            f = min(w / 800.0, h / 600.0) * user
            assert wwidth * s <= w + 0.5 and wheight * s <= h + 0.5, '%s larger than %dx%d' % (name, w, h)
            title_h = font_points('MedievalSharp-20') * 4.0 / 3.0 * 1.35 * f + TITLE_PADDING * s
            cw = (wwidth - 2 * FRAME_SIDE) * s
            ch = wheight * s - title_h - FRAME_SIDE * s
            assert ch > 0, name
            page_area = udims(props(pages)['Area'])
            cw = (page_area[4] - page_area[0]) * cw + (page_area[5] - page_area[1]) * s
            ch = (page_area[6] - page_area[2]) * ch + (page_area[7] - page_area[3]) * s
            embedded = udims(p['Area'])
            cw = (embedded[4] - embedded[0]) * cw + (embedded[5] - embedded[1]) * s
            ch = (embedded[6] - embedded[2]) * ch + (embedded[7] - embedded[3]) * s
            for child in children.values():
                bounds = udims(props(child)['Area'])
                left = bounds[0] * cw + bounds[1] * s
                top = bounds[2] * ch + bounds[3] * s
                right = bounds[4] * cw + bounds[5] * s
                bottom = bounds[6] * ch + bounds[7] * s
                assert 0 <= left < right <= cw + 0.5, (name, child.get('name'), 'horizontal page bounds', w, h, user)
                assert 0 <= top < bottom <= ch + 0.5, (name, child.get('name'), 'vertical page bounds', w, h, user)
            for child_name, text in list(texts.items()) + list(buttons.items()):
                q = props(children[child_name])
                a = udims(q['Area'])
                bw = (a[4] - a[0]) * cw + (a[5] - a[1]) * s
                bh = (a[6] - a[2]) * ch + (a[7] - a[3]) * s
                if child_name in buttons:
                    bw -= 12 * s  # text inset of buttons and one-line labels
                ok, lines = text_fits(text, q['Font'], bw, bh, f)
                assert ok, '%s/%s sticks out at %dx%d %d %%: %d lines in %.0fx%.0f px' % (
                    name, child_name, w, h, user * 100, lines, bw, bh)
                if child_name in buttons:
                    assert lines == 1, '%s/%s wraps at %dx%d %d %%' % (name, child_name, w, h, user * 100)
                else:
                    assert 'WordWrap' in q.get('HorzFormatting', ''), '%s/%s must wrap' % (name, child_name)
    return children


ghost_layout = ET.parse(repo / 'gui/RoomManagerGhostPage.layout').getroot().find('Window')
explain = props({c.get('name'): c for c in ghost_layout.findall('Window')}['GhostExplainText'])['Text']
assert 'cauldron' in explain and 'apparatus' in explain and 'Research unlocks' in explain
check_window('GhostPage', 'RoomManagerGhostPage.layout',
             {'GhostBarText': 'Ectoplasm: 100.0 / 100.0 ghost levels', 'GhostExplainText': explain},
             {'GhostProductButton': 'Apparatus: Ghost press', 'GhostReviveButton': 'Revive own: Off'})

merchant_layout = ET.parse(repo / 'gui/RoomManagerMerchantPage.layout').getroot().find('Window')
empty = props({c.get('name'): c for c in merchant_layout.findall('Window')}['EmptyText'])['Text']
assert empty.startswith('The tables are empty') and 'creatures sell items' in empty and 'workers bring item bags' in empty
assert 'buy it' in empty
check_window('MerchantPage', 'RoomManagerMerchantPage.layout',
             {'EmptyText': empty},
             {'MarginLabel': 'Margin: 50 %', 'ModeButton': 'Profit', 'BuyButton': 'Buy (100000)'})

# The client shows the empty-state text exactly when the stock list is empty
merchant = (repo / 'source/modes/GameModeMerchant.cpp').read_text(encoding='utf-8')
assert merchant.count('mRootWindow->getChild("RoomManagerWindow/Pages/MerchantPage/EmptyText")->setVisible(mMerchantItems.empty());') == 2
assert 'static const float STOCK_DESIGN_WIDTH = 485.12f;' in merchant

# The shared Room Manager close control closes the one common window.
game = (repo / 'source/modes/GameModeRoomManager.cpp').read_text(encoding='utf-8')
assert 'CEGUI::FrameWindow::EventCloseClicked' in game and '&GameMode::closeRoomManager' in game
print('Room Manager ghost and merchant look/fit passed')
