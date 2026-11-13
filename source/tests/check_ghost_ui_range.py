"""Check complete ghost/merchant controls over the continuous display/scale range.

Fixed scope: 7 ghost-room windows, 10 merchant windows and 10 HUD row icons.
Supplements the existing look, icon and general window checks; runs no compiler.
No screenshot/runtime claim: Pillow measures the shipped font, not GPU output.

For every width >=640, height >=480 and user scale in [.8,1.2], layout
scale s=min(w/1024,h/768)*user is >=.5. Both centred frames fit without
shrinking even at 120%. Font scale/s is always 1.28. The shared frame
images have native 3840x2160 scaling without user scale, so their size/s
is at most 1/(2.8125*.8), less than one. Title padding is 12 physical
pixels, hence at most 24*s. Bounding client rectangles in design units
therefore proves containment, separation and caption fit between sampled
resolutions too. Child edges are affine in client width/height; test the
four independent endpoint combinations, not just matching aspect ratios.
"""

from itertools import combinations, product
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import ImageFont


REPO = Path(__file__).resolve().parents[2]
SCREENS = ((640, 480), (640, 4320), (800, 600), (1024, 768), (1280, 720),
           (1366, 768), (1920, 1080), (2560, 1440), (3440, 1440),
           (3840, 2160), (7680, 480), (7680, 4320))
SCALES = (.8, .9, 1., 1.1, 1.2)
CHILDREN = {
    'GhostRoom': {'GhostInfoPanel', 'GhostBarText', 'GhostExplainText',
                  'GhostProductButton', 'GhostReviveButton', 'CloseButton'},
    'Merchant': {'StockList', 'EmptyText', 'MarginLabel', 'MarginSlider', 'ModeButton',
                 'HistoryPanel', 'HistoryText', 'BuyButton', 'CloseButton'},
}
# Exact counts include the root frame: 7 and 10 windows respectively.
WINDOW_COUNTS = {'GhostRoom': 7, 'Merchant': 10}
FRAME_SIZES = {'GhostRoom': (560., 420.), 'Merchant': (780., 520.)}
ROW_X = {'GoalsButton': 4, 'ResearchButton': 52, 'ProductionButton': 100,
         'SocialButton': 148, 'WorkersButton': 196, 'InfirmaryButton': 244,
         'MerchantButton': 292, 'GhostHuntersButton': 340, 'LabButton': 388,
         'SandboxButton': 436}
CAPTIONS = {
    'GhostBarText': ('Ectoplasm: 0.0 / 10.0 ghost levels',
                     'Ectoplasm: 100.0 / 100.0 ghost levels'),
    'GhostProductButton': ('Apparatus: Mana still', 'Apparatus: Ghost press', 'Apparatus: Soul forge'),
    'GhostReviveButton': ('Revive own: On', 'Revive own: Off'),
    'MarginLabel': ('Margin: 0 %', 'Margin: 50 %'),
    'ModeButton': ('Fair', 'Profit'),
    'BuyButton': ('Buy', 'Buy (100000)'),
    'CloseButton': ('Close',),
}


def read(path):
    """Read tracked production input without depending on the current directory."""
    return (REPO / path).read_text(encoding='utf-8')


def props(node):
    """Return explicit CEGUI properties."""
    return {p.get('name'): p.get('value') for p in node.findall('Property')}


def area(node):
    """Parse the four relative/offset pairs of a CEGUI rectangle."""
    pairs = re.findall(r'\{(-?[\d.]+),(-?[\d.]+)\}', props(node)['Area'])
    assert len(pairs) == 4, node.get('name')
    return tuple((float(a), float(b)) for a, b in pairs)


def rectangle(node, width, height, scale=1.):
    """Resolve a rectangle against its parent's client area."""
    return tuple(a * (width if i % 2 == 0 else height) + b * scale
                 for i, (a, b) in enumerate(area(node)))


def inside(inner, outer):
    """Require positive dimensions and full containment without clipping allowances."""
    return (outer[0] <= inner[0] < inner[2] <= outer[2]
            and outer[1] <= inner[1] < inner[3] <= outer[3])


def apart(first, second):
    """Check that two controls cannot cover one another's hit area."""
    return (first[2] <= second[0] or second[2] <= first[0]
            or first[3] <= second[1] or second[3] <= first[1])


def font_metrics(name):
    """Measure the shipped font in layout design units, including the 1.28 ratio."""
    spec = ET.parse(REPO / 'gui/fonts' / (name + '.font')).getroot()
    assert spec.get('filename') == 'SourceSerif4-Semibold.ttf'
    face = ImageFont.truetype(str(REPO / 'gui/fonts' / spec.get('filename')), 1024)
    factor = float(spec.get('size')) * (4. / 3.) * 1.28 / 1024.
    return face, factor


def caption_fits(text, font, width, height, wrap):
    """Measure word wrapping and full line boxes with the actual shipped face."""
    face, factor = font_metrics(font)
    lines = []
    for paragraph in text.split('\n'):
        current = ''
        for word in paragraph.split():
            trial = (current + ' ' + word).strip()
            if wrap and current and face.getlength(trial) * factor > width:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    assert max(face.getlength(line) * factor for line in lines) <= width, text
    assert len(lines) * sum(face.getmetrics()) * factor <= height, (text, height)


def scaling_contract():
    """Pin production assumptions used by the continuous geometric bounds."""
    gui = read('source/render/Gui.cpp')
    for key, expected in (('LAYOUT_DESIGN_WIDTH', '1024.0'), ('LAYOUT_DESIGN_HEIGHT', '768.0'),
                          ('FONT_DESIGN_WIDTH', '800.0'), ('FONT_DESIGN_HEIGHT', '600.0')):
        assert re.search(key + r' = ' + re.escape(expected) + r'f;', gui), key
    for fragment in ('layoutScale * getWindowFitFactor(window)',
                     'scaleRect(data.area, scale)', 'const float scale = resolutionScale * mUserScale;',
                     'FONT_DESIGN_WIDTH / mUserScale', 'FONT_DESIGN_HEIGHT / mUserScale',
                     'setAutoScaled(CEGUI::ASM_Min)'):
        assert fragment in gui, fragment
    # Shared frame images are deliberately outside the dynamically scaled families.
    scaling = gui[gui.index('bool shouldScaleImage('):gui.index('std::string scaleFormattedImageSizes(')]
    assert 'OpenDungeonsGameWindow/' not in scaling
    images = ET.parse(REPO / 'gui/ODGameWindow.imageset').getroot()
    assert (images.get('autoScaled'), images.get('nativeHorzRes'), images.get('nativeVertRes')) == ('true', '3840', '2160')
    sizes = {i.get('name'): (i.get('width'), i.get('height')) for i in images.findall('Image')}
    assert sizes['FrameLeft'] == sizes['FrameRight'] == ('16', '128')
    assert sizes['FrameBottom'] == ('128', '16')
    look = ET.parse(REPO / 'gui/OD.looknfeel').getroot().find("WidgetLook[@name='OD/FrameWindow']")
    title = look.find("Child[@nameSuffix='__auto_titlebar__']")
    assert title.find('.//FontDim').attrib == {'widget': '__auto_titlebar__', 'padding': '12', 'type': 'LineSpacing'}
    assert look.find("PropertyLinkDefinition[@name='TitlebarFont']").get('initialValue') == 'MedievalSharp-10'


def windows():
    """Cover every child, dynamic caption, click target and intentional panel overlay."""
    title_face, title_factor = font_metrics('MedievalSharp-10')
    title_line = sum(title_face.getmetrics()) * title_factor
    for name in ('GhostRoom', 'Merchant'):
        root = ET.parse(REPO / 'gui' / ('Window' + name + '.layout')).getroot().find('Window')
        nodes = {n.get('name'): n for n in root.findall('Window')}
        assert set(nodes) == CHILDREN[name], (name, set(nodes))
        assert len(list(root.iter('Window'))) == WINDOW_COUNTS[name]
        assert root.get('type') == 'OD/FrameWindow'
        assert props(root)['SizingEnabled'] == 'False'
        assert not any(key.startswith('Frame') and key.endswith('Image') for key in props(root))
        assert 'TitlebarFont' not in props(root) and root.find('AutoWindow') is None
        width, height = FRAME_SIZES[name]
        assert area(root) == ((.5, -width / 2), (.5, -height / 2), (.5, width / 2), (.5, height / 2))
        # These strict inequalities prove no fit-factor breakpoint anywhere in the range.
        assert width * 1.2 < 1024 and height * 1.2 < 768
        caption_fits(props(root)['Text'], 'MedievalSharp-10', width - 2 * (title_line + 24.), title_line, False)
        for screen, user in product(SCREENS, SCALES):
            scale = min(screen[0] / 1024., screen[1] / 768.) * user
            assert scale >= .5
            assert inside(rectangle(root, *screen, scale), (0, 0, *screen))
        # Independent conservative extrema contain every physical client rectangle / s.
        for cw, ch in product((width - 32., width),
                              (height - title_line - 24. - 16., height - title_line)):
            rectangles = {key: rectangle(node, cw, ch) for key, node in nodes.items()}
            for key, rect in rectangles.items():
                assert inside(rect, (0, 0, cw, ch)), (name, key, rect)
                p = props(nodes[key])
                if nodes[key].get('type') == 'OD/Button':
                    assert min(rect[2] - rect[0], rect[3] - rect[1]) * .5 >= 16, key
                texts = CAPTIONS.get(key, (p.get('Text', ''),))
                for text in texts:
                    if text:
                        caption_fits(text, p['Font'], rect[2] - rect[0] - 12., rect[3] - rect[1],
                                     'WordWrap' in p.get('HorzFormatting', ''))
            controls = [key for key, node in nodes.items() if node.get('type') in
                        ('OD/Button', 'OD/SettingsSlider', 'OD/MultiColumnList')]
            for first, second in combinations(controls, 2):
                assert apart(rectangles[first], rectangles[second]), (first, second)
            if name == 'GhostRoom':
                assert props(nodes['GhostInfoPanel'])['MousePassThroughEnabled'] == 'True'
                for key in ('GhostBarText', 'GhostExplainText'):
                    assert inside(rectangles[key], rectangles['GhostInfoPanel']), key
                assert apart(rectangles['GhostBarText'], rectangles['GhostExplainText'])
                for key in ('GhostProductButton', 'GhostReviveButton', 'CloseButton'):
                    assert apart(rectangles['GhostInfoPanel'], rectangles[key]), key
            else:
                assert props(nodes['EmptyText'])['MousePassThroughEnabled'] == 'True'
                assert inside(rectangles['EmptyText'], rectangles['StockList'])
                assert inside(rectangles['HistoryText'], rectangles['HistoryPanel'])
                assert props(nodes['HistoryText'])['VertScrollbar'] == 'True'
                assert props(nodes['HistoryText'])['HorzFormatting'] == 'WordWrapLeftAligned'
                for key in controls + ['MarginLabel', 'StockList']:
                    assert apart(rectangles['HistoryPanel'], rectangles[key]), key


def hud():
    """Check all ten HUD slots, including both icons moved for the ghost button."""
    root = ET.parse(REPO / 'gui/ModeGame.layout').getroot()
    nodes = {n.get('name'): n for n in root.iter('Window')}
    for name, x in ROW_X.items():
        assert area(nodes[name]) == ((0, x), (1, -224), (0, x + 40), (1, -184)), name
    # Fixed lower-strip geometry proves vertical separation for every positive s.
    obstacles = {
        'MiniMap': ((0, 8), (1, -184), (0, 184), (1, -8)),
        'MainTabControl': ((0, 188), (1, -184), (1, 0), (1, 0)),
        'PanelToggleButton': ((0, 400), (1, -184), (0, 432), (1, -132)),
        'MessageQueue': ((0, 436), (1, -184), (1, 0), (1, -132)),
    }
    for name, expected in obstacles.items():
        assert area(nodes[name]) == expected, name
    # Entire row fits continuously: s/w <=1.2/1024; s/h <=1.2/768.
    assert 476 * 1.2 < 1024 and 224 * 1.2 < 768
    assert 40 * .5 == 20  # fixed minimum hit target at 640x480 / 80%
    for screen, user in product(SCREENS, SCALES):
        s = min(screen[0] / 1024., screen[1] / 768.) * user
        row = {name: rectangle(nodes[name], *screen, s) for name in ROW_X}
        for name, rect in row.items():
            assert inside(rect, (0, 0, *screen)), name
            for obstacle in ('MiniMap', 'MainTabControl', 'PanelToggleButton', 'MessageQueue'):
                assert apart(rect, rectangle(nodes[obstacle], *screen, s)), (name, obstacle)
        for first, second in combinations(row, 2):
            assert apart(row[first], row[second]), (first, second)


def stock_contract():
    """Keep product names/icons, scaled stock rows, full tooltips and history scrolling."""
    merchant = read('source/modes/GameModeMerchant.cpp')
    for fragment in ('ICON_DESIGN_SIZE = 64.0f;', 'STOCK_DESIGN_WIDTH = 716.0f;',
                     'getOwnerWindow()->getPixelSize().d_width / STOCK_DESIGN_WIDTH',
                     'list->getPixelSize().d_width / STOCK_DESIGN_WIDTH',
                     'ICON_DESIGN_SIZE * iconScale', 'new MerchantImageItem(item, entry.first)',
                     'image->setTooltipText(tooltip);', 'cell->setTooltipText(tooltip);',
                     'item.getDisplayName(mGameMap)', 'mRootWindow->getChild("MerchantWindow/HistoryText")->setText(history);'):
        assert fragment in merchant, fragment
    columns = re.findall(r'list->addColumn\("([^"]+)", (\d), CEGUI::UDim\(([^,]+), ([^)]+)\)\);', merchant)
    assert columns == [('Image', '0', '0.0f', 'ICON_DESIGN_SIZE'), ('Name', '1', '0.25f', '0'),
                       ('Quality', '2', '0.11f', '0'), ('Price', '3', '0.11f', '0'), ('Bonuses', '4', '0.40f', '0')]
    assert 64. + (.25 + .11 + .11 + .40) * 716. < 716.
    for label in ('Soul crystal', 'Mana crystal', 'Research book', 'Ectoplasm'):
        assert 'return "' + label + '";' in read('source/entities/ItemInstance.cpp')
        caption_fits(label, 'MedievalSharp-10', .25 * 716. - 12., 64., False)
    assert 'if(mSoulCrystal || mGhostItem != GhostItem::none) return "soul_crystal";' in read('source/entities/ItemInstance.cpp')
    images = ET.parse(REPO / 'gui/Items.imageset').getroot()
    assert images.find("Image[@name='soul_crystal']") is not None


def captions_and_tooltips():
    """Bind dynamic fixtures to production labels and bound all affected tooltips."""
    game = read('source/modes/GameMode.cpp')
    start = game.index('void GameMode::refreshGhostRoomWindow()')
    refresh = game[start:game.index('\n}', start)]
    assert set(re.findall(r'"(Apparatus: [^"]+)"', refresh)) == set(CAPTIONS['GhostProductButton'])
    for label in CAPTIONS['GhostReviveButton']:
        assert '"' + label + '"' in refresh
    assert 'std::setprecision(1)' in refresh and 'std::fmod(seat->getEctoplasmLevels(), perEctoplasm)' in refresh
    assert '"Ectoplasm: " << progress << " / " << perEctoplasm << " ghost levels"' in refresh
    tooltips = []
    for layout in ('WindowGhostRoom.layout', 'WindowMerchant.layout', 'ModeGame.layout'):
        root = ET.parse(REPO / 'gui' / layout).getroot()
        for node in root.iter('Window'):
            if layout == 'ModeGame.layout' and node.get('name') not in ROW_X:
                continue
            if 'TooltipText' in props(node):
                tooltips.append(props(node)['TooltipText'])
    # min(screen width/s) = 1024/1.2; height/s = 768/1.2.
    # Reserve 32 design pixels for the two tooltip borders (conservative).
    for text in tooltips + ['Soul crystal\nLevel 1', 'Mana crystal\nLevel 1',
                            'Research book\nLevel 1', 'Ectoplasm\nLevel 1']:
        caption_fits(text, 'LiberationSans-10', 1024. / 1.2 - 32., 768. / 1.2 - 32., False)
    gui = read('source/render/Gui.cpp')
    for fragment in ('x = std::max(0.0f, std::min(x, screen.d_width - bounds.getWidth()));',
                     'y = std::max(0.0f, std::min(y, screen.d_height - bounds.getHeight()));'):
        assert fragment in gui


def main():
    """Run fixed-scope coverage alongside the existing text/look and icon checks."""
    scaling_contract()
    windows()
    hud()
    stock_contract()
    captions_and_tooltips()
    print('ghost UI: 7 ghost windows, 10 merchant windows, 10 HUD slots; continuous bounds and 60 display/scale cases: ok')


if __name__ == '__main__':
    main()
