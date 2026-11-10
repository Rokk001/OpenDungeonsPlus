"""Check that the content of every gui/*.layout window stays inside its window and that its fixed captions are not cut.

Static check, no game needed. It extends check_window_fit_screen.py (which only compares the window SIZE with the
screen) with the content of the windows. For every layout file, in the context it is loaded in (a layout that is
imported by another one is checked inside the importing window, with the inherited font), at

    640x480, 1024x768, 1920x1200 and 7680x4320 (8K), each with the user scale 80 % and 120 %

it computes the pixel rectangle of every window with the same formulas as Gui.cpp and verifies

1. Containment. Every child lies inside the client area of its parent. For a frame window the client area is the
   window without the title bar and without the frame edges, so content that would sit under the title or under the
   frame is found. The window itself is limited to the screen by Gui::getWindowFitFactor (same formula as there).
2. Text. Every window with a fixed caption (static text, label, button, check box, tab, menu entry, frame title)
   gets the text rectangle of its widget look and the caption is measured with the shipped font file (the same
   method as check_dungeonbook_profile_layout.py): a caption that does not wrap must not be wider than the box, a
   wrapped caption must not have a word wider than the box, and the glyph ink of the first and the last line, placed
   by the vertical format of the widget, must stay inside the box height (the window clips the glyphs, not the empty
   line space above and below them). Captions that the code fills in (empty Text in the layout) have no layout text and
   are measured by their own checks (check_workers_window.py, check_dungeonbook_profile_layout.py ...); a window
   whose font is not set inherits it from its parent as CEGUI does (default: the first font of the scheme).

The scale formulas (Gui::applyScale, Gui::applyScaleToWindow, Gui::updateResourceScaling):
* layout scale  = min(width / 1024, height / 768) * user scale; absolute (offset) parts of areas are multiplied by it
  and by the window fit factor of the top window; relative parts are fractions of the parent client area.
* font scale    = min(width / (800 / user), height / (600 / user)) of the font design size, that is the layout scale
  times 1024 / 800 in design pixels.
* images        = 'OpenDungeonsSkin/' etc. (shouldScaleImage) are scaled with the layout scale divided by their pixel
  density, all other images keep the scale mode of their imageset (native 3840x2160) (display only, not the user scale).
* alignment     = CEGUI reads only the word Centre as centred, so 'Center' and 'Centered' count as Top / Left.

Exclusions (each one is a documented limit of the game, not a layout fault, and is marked in the code):
* children of a scrollable pane (CEGUI shows its scrollbars as soon as the content is larger than the view),
* windows that explicitly set ClippedByParent False (badges and symbols that are meant to overhang their parent),
* progress bars (tinted overlays that the parent clips),
* list, combo box and multi column list contents (rows are filled and scrolled by the code); of a combo box only the
  closed box (1.5 line spacings) counts, the drop down list opens over the other windows,
* the room, trap and spell buttons of the game build bar (placed by Gui::arrangeActionButtons),
* KNOWN_LIMITS: the map editor build bar and the developer widget gallery, which are not in-game windows; their
  findings are counted and printed, not hidden.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from PIL import ImageFont

repo = Path(__file__).resolve().parents[2]
gui_dir = repo / 'gui'
gui_cpp = (repo / 'source/render/Gui.cpp').read_text(encoding='utf-8', errors='replace')
assert 'layoutScale * getWindowFitFactor(window)' in gui_cpp, 'Gui.cpp does not limit windows to the screen'

DESIGN_W, DESIGN_H = 1024.0, 768.0
FONT_W, FONT_H = 800.0, 600.0
SCREENS = [(640, 480), (1024, 768), (1920, 1200), (7680, 4320)]
USER_SCALES = [0.8, 1.2]
TOLERANCE = 0.75  # screen pixels: rounding of the renderer
NEWLINE = chr(10)
BACKSLASH_N = chr(92) + 'n'
NUMBER = r'(-?\d+(?:\.\d+)?)'
UDIM = r'\{' + NUMBER + ',' + NUMBER + r'\}'

# Gui.cpp image rules, read from the source so the check follows them
SCALED_PREFIXES = re.findall(r'startsWith\(name, "([A-Za-z]+/)"\)', gui_cpp[gui_cpp.index('bool shouldScaleImage'):][:600])
assert 'OpenDungeonsSkin/' in SCALED_PREFIXES and len(SCALED_PREFIXES) >= 5, SCALED_PREFIXES
DENSITY = {'OpenDungeonsSkin/': float(re.search(r'SKIN_IMAGE_PIXEL_DENSITY = ([0-9.]+)f', gui_cpp)[1]),
           'ODHudSurface/': float(re.search(r'HUD_SURFACE_IMAGE_PIXEL_DENSITY = ([0-9.]+)f', gui_cpp)[1]),
           'OpenDungeonsIcons/': float(re.search(r'ICON_IMAGE_PIXEL_DENSITY = ([0-9.]+)f', gui_cpp)[1]),
           'OpenDungeonsNavigation/': float(re.search(r'ICON_IMAGE_PIXEL_DENSITY = ([0-9.]+)f', gui_cpp)[1])}


def udims(value):
    """The (scale, offset) pairs of a CEGUI property value like {{0.5,-380},{0.5,350}}."""
    return [(float(a), float(b)) for a, b in re.findall(UDIM, value)]


# ---------------------------------------------------------------------------------------------------- fonts and images
fonts = {}
for font_file in sorted((gui_dir / 'fonts').glob('*.font')):
    spec = ET.parse(font_file).getroot()
    face = ImageFont.truetype(str(gui_dir / 'fonts' / spec.get('filename')), 1024)
    # points to pixels at 96 dpi on the 800x600 design size, per font unit of the 1024 pixel measurement
    fonts[spec.get('name')] = (face, float(spec.get('size')) * (96.0 / 72.0) / 1024.0)
DEFAULT_FONT = 'LiberationSans-10'  # the first font of ODSkin.scheme is the CEGUI default font
assert re.search(r'<Font filename="LiberationSans-10.font"', (gui_dir / 'ODSkin.scheme').read_text()), 'default font moved'
FRAME_TITLE_FONT = 'MedievalSharp-10'

imagesets = {}
for imageset_file in gui_dir.glob('*.imageset'):
    root = ET.parse(imageset_file).getroot()
    imagesets[root.get('name')] = (
        root.get('autoScaled'), float(root.get('nativeHorzRes', 0)), float(root.get('nativeVertRes', 0)),
        {i.get('name'): (float(i.get('width')), float(i.get('height'))) for i in root.findall('Image')})


def font_scale(screen, user):
    """Pixels per font pixel of the 800x600 design (Font::setNativeResolution(800 / user, 600 / user), ASM_Min)."""
    return min(screen[0] / (FONT_W / user), screen[1] / (FONT_H / user))


def text_size(font, text, screen, user):
    """Pixel width and line height of one line of text with the shipped font."""
    face, factor = fonts[font]
    scale = font_scale(screen, user)
    return face.getlength(text) * factor * scale, sum(face.getmetrics()) * factor * scale


def image_size(name, screen, user):
    """Pixel size of a named image after the scaling of Gui::updateResourceScaling."""
    imageset, _, image = name.partition('/')
    mode, native_w, native_h, images = imagesets[imageset]
    width, height = images[image]
    layout = min(screen[0] / DESIGN_W, screen[1] / DESIGN_H) * user
    for prefix in SCALED_PREFIXES:
        if name.startswith(prefix):
            density = DENSITY.get(prefix, 1.0)
            return width / density * layout, height / density * layout
    if mode in ('true', 'min') and native_w:
        factor = min(screen[0] / native_w, screen[1] / native_h)
        return width * factor, height * factor
    return width, height


# ---------------------------------------------------------------------------------------------------- layout tree
class Node:
    def __init__(self, element, parent, layout):
        self.parent = parent
        self.layout = layout
        self.type = element.get('type')
        self.name = element.get('name')
        self.props = {p.get('name'): p.get('value') for p in element.findall('Property')}
        self.children = []
        self.path = (parent.path + '/' if parent is not None else '') + (self.name or '?')

    def font(self):
        node = self
        while node is not None:
            if 'Font' in node.props:
                return node.props['Font']
            node = node.parent
        return DEFAULT_FONT

    def area(self):
        if 'Area' in self.props:
            value = udims(self.props['Area'])
            if len(value) == 4:
                return value
        return None


def build(layout_name, parent, seen):
    """Parse a layout file below the given parent node; layouts imported by it are built below their window."""
    root = ET.parse(gui_dir / layout_name).getroot()
    nodes = []
    for window in root.findall('Window'):
        nodes.append(build_window(window, parent, layout_name, seen))
    return nodes


def build_window(element, parent, layout_name, seen):
    node = Node(element, parent, layout_name)
    for child in element:
        if child.tag == 'Window':
            node.children.append(build_window(child, node, layout_name, seen))
        elif child.tag == 'LayoutImport':
            imported = child.get('filename')
            assert (gui_dir / imported).exists(), imported
            assert imported not in seen, 'layout import cycle ' + imported
            node.children.extend(build(imported, node, seen | {imported}))
    return node


layouts = sorted(p.name for p in gui_dir.glob('*.layout'))
imported_by_somebody = set()
for name in layouts:
    for entry in ET.parse(gui_dir / name).getroot().iter('LayoutImport'):
        imported_by_somebody.add(entry.get('filename'))
# Every layout that nobody imports is a root of its own: a sheet (Mode*, Menu*) or a window the code loads by name
sheets = []
for name in layouts:
    if name not in imported_by_somebody:
        sheets.extend(build(name, None, {name}))
assert sheets and layouts


def covered_layouts(nodes, out):
    for node in nodes:
        out.add(node.layout)
        covered_layouts(node.children, out)
    return out


covered = covered_layouts(sheets, set())
assert covered == set(layouts), ('layouts not checked', sorted(set(layouts) - covered))

# ---------------------------------------------------------------------------------------------------- geometry
FRAME_TYPES = ('OD/FrameWindow', 'OD/MenuFrameWindow', 'OD/MenuSelectionWindow')
SCROLL_TYPES = ('OD/ScrollablePane', 'OD/MenuScrollablePane')
# widgets whose rows are filled by the code and scrolled by their own scrollbar
LIST_TYPES = ('OD/Listbox', 'OD/MenuListbox', 'OD/MultiColumnList', 'OD/MenuMultiColumnList', 'OD/Combobox',
              'OD/PopupMenu', 'OD/Menubar', 'OD/MultiLineEditbox')


def is_fill(node):
    return node.area() == [(0, 0), (0, 0), (1, 0), (1, 0)]


def screen_sized_container(node):
    """Gui::isScreenSizedContainer: no parent, or a window that fills a screen sized parent."""
    return node is None or (is_fill(node) and screen_sized_container(node.parent))


def fit_factor(top, screen, user):
    """Gui::getWindowFitFactor for the window that sits directly in a screen sized container."""
    value = top.area()
    if value is None:
        return 1.0
    scale = min(screen[0] / DESIGN_W, screen[1] / DESIGN_H) * user
    rel_w, rel_h = value[2][0] - value[0][0], value[3][0] - value[1][0]
    off_w, off_h = (value[2][1] - value[0][1]) * scale, (value[3][1] - value[1][1]) * scale
    factor = 1.0
    if off_w > 0 and rel_w < 1.0:
        factor = min(factor, max(0.0, (1.0 - rel_w) * screen[0]) / off_w)
    if off_h > 0 and rel_h < 1.0:
        factor = min(factor, max(0.0, (1.0 - rel_h) * screen[1]) / off_h)
    return factor


def frame_images(node):
    defaults = {'FrameLeftImage': 'OpenDungeonsGameWindow/FrameLeft', 'FrameRightImage': 'OpenDungeonsGameWindow/FrameRight',
                'FrameBottomImage': 'OpenDungeonsGameWindow/FrameBottom', 'FrameTopImage': 'OpenDungeonsGameWindow/FrameTop'}
    return {key: node.props.get(key, default) for key, default in defaults.items()}


def title_height(node, screen, user):
    """The title bar is one line of its font plus 12 pixels (FontDim LineSpacing, padding 12)."""
    font = node.props.get('TitlebarFont', FRAME_TITLE_FONT)
    return text_size(font, 'Ag', screen, user)[1] + 12.0


def client_rect(node, rect, screen, user, s):
    """The rectangle the children of the node are laid out in (looknfeel NamedArea, CEGUI Window::getChildContentArea)."""
    x0, y0, x1, y1 = rect
    if node.type == 'OD/ScrollablePane' and node.path.endswith('/SocialWindow/ValuesPage'):
        # Gui::applyScale places these original columns in an 820x500 design-pixel scroll document.
        # Measure their captions in that document; check_dungeonbook_profile_layout also checks scroll reachability.
        assert 'const float documentWidth = 820.0f * scale;' in gui_cpp
        assert 'const float documentHeight = 500.0f * scale;' in gui_cpp
        document_scale = min(screen[0] / DESIGN_W, screen[1] / DESIGN_H) * user
        return x0, y0, x0 + 820.0 * document_scale, y0 + 500.0 * document_scale
    if node.type in ('OD/FrameWindow',):
        images = frame_images(node)
        return (x0 + image_size(images['FrameLeftImage'], screen, user)[0], y0 + title_height(node, screen, user),
                x1 - image_size(images['FrameRightImage'], screen, user)[0],
                y1 - image_size(images['FrameBottomImage'], screen, user)[1])
    if node.type in ('OD/MenuFrameWindow', 'OD/MenuSelectionWindow'):
        return (x0 + image_size('OpenDungeonsSkin/WindowLeftEdge', screen, user)[0], y0 + title_height(node, screen, user),
                x1 - image_size('OpenDungeonsSkin/WindowRightEdge', screen, user)[0],
                y1 - image_size('OpenDungeonsSkin/WindowBottomEdge', screen, user)[1])
    if node.type == 'OD/TabControl':
        value = udims(node.props.get('TabHeight', '{0,0}'))
        return x0, y0 + (value[0][1] * s if value else 0.0), x1, y1
    return rect


def child_rect(node, parent_client, s):
    """Pixel rectangle of a window from its Area (and the alignment properties) inside the parent client rectangle."""
    value = node.area()
    px0, py0, px1, py1 = parent_client
    pw, ph = px1 - px0, py1 - py0
    x0, y0 = px0 + value[0][0] * pw + value[0][1] * s, py0 + value[1][0] * ph + value[1][1] * s
    x1, y1 = px0 + value[2][0] * pw + value[2][1] * s, py0 + value[3][0] * ph + value[3][1] * s
    width, height = x1 - x0, y1 - y0
    horizontal = node.props.get('HorizontalAlignment', 'Left')
    vertical = node.props.get('VerticalAlignment', 'Top')
    shift_x = shift_y = 0.0
    if horizontal == 'Centre':  # CEGUI reads any other word than Centre / Right as Left
        shift_x = (pw - width) / 2.0
    elif horizontal == 'Right':
        shift_x = pw - width
    if vertical == 'Centre':  # 'Center' and 'Centered' are read as Top by CEGUI
        shift_y = (ph - height) / 2.0
    elif vertical == 'Bottom':
        shift_y = ph - height
    return x0 + shift_x, y0 + shift_y, x0 + shift_x + width, y0 + shift_y + height


# ---------------------------------------------------------------------------------------------------- text
TEXT_TYPES = {'OD/StaticText', 'OD/MenuTitle', 'OD/ResourceDisplay', 'OD/EventPanel', 'OD/MenuDescription',
              'OD/Button', 'OD/MainMenuButton', 'OD/InvisibleButton', 'OD/MenuTextButton', 'OD/Checkbox',
              'OD/RadioButton', 'OD/IconButton', 'OD/ImageButton', 'OD/ResearchButton', 'OD/TabButton',
              'OD/MenuItem', 'OD/MenuSymbolButton', 'OD/GameTabButton', 'OD/MiniMapCornerButton'}
STATIC_LIKE = {'OD/StaticText', 'OD/MenuTitle', 'OD/ResourceDisplay', 'OD/EventPanel', 'OD/MenuDescription'}


def strip_markup(text):
    """The visible characters of a CEGUI text: colour and font tags are not drawn, image tags are left out."""
    return re.sub(r'\[[^\[\]]*=[^\[\]]*\]', '', text)


def text_area(node, rect, screen, user, s):
    """The rectangle the look draws the caption in (TextComponent / WithFrameTextRenderArea of OD.looknfeel)."""
    x0, y0, x1, y1 = rect
    if node.type in STATIC_LIKE:
        if node.props.get('FrameEnabled', 'True') == 'True':
            left = image_size('OpenDungeonsSkin/StaticLeft', screen, user)[0]
            top = image_size('OpenDungeonsSkin/StaticTop', screen, user)[1]
            right = image_size('OpenDungeonsSkin/StaticRight', screen, user)[0]
            bottom = image_size('OpenDungeonsSkin/StaticBottom', screen, user)[1]
            return x0 + left, y0 + top, x1 - right, y1 - bottom
        return rect
    if node.type in ('OD/Checkbox', 'OD/RadioButton'):
        name = 'OpenDungeonsSkin/CheckboxNormal' if node.type == 'OD/Checkbox' else 'OpenDungeonsSkin/RadioButtonNormal'
        return x0 + image_size(name, screen, user)[0] + 3.0, y0, x1, y1
    if node.type == 'OD/IconButton':
        return x0 + 1.1 * (y1 - y0), y0, x1, y1
    if node.type == 'OD/ImageButton' or node.type == 'OD/ResearchButton':
        return x0 + 5.0, y0, x0 + 5.0 + 0.9 * (x1 - x0), y1
    return rect


def wrap_text(font, text, width, screen, user):
    """Lines of a caption that wraps at spaces (CEGUI word wrap); a word longer than the line stays on its own line."""
    lines = []
    widest_word = 0.0
    for paragraph in text.split(NEWLINE):
        current = ''
        for word in paragraph.split(' '):
            trial = word if not current else current + ' ' + word
            widest_word = max(widest_word, text_size(font, word, screen, user)[0])
            if current and text_size(font, trial, screen, user)[0] > width + 1e-6:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    return lines, widest_word


def ink_extent(font, line, screen, user):
    """Ink of one line relative to its baseline in pixels: (top, bottom), top is negative above the baseline."""
    face, factor = fonts[font]
    left, top, right, bottom = face.getbbox(line if line else 'x', anchor='ls')
    scale = factor * font_scale(screen, user)
    return top * scale, bottom * scale


def font_metrics(font, screen, user):
    """(ascent, descent) in pixels; the line box of CEGUI is ascent + descent high."""
    face, factor = fonts[font]
    ascent, descent = face.getmetrics()
    scale = factor * font_scale(screen, user)
    return ascent * scale, descent * scale


tightest = {}
captions = {}


def check_text(node, rect, screen, user, s, problems):
    caption = node.props.get('Text')
    if not caption or node.type not in TEXT_TYPES:
        return
    caption = strip_markup(caption.replace(BACKSLASH_N, NEWLINE))
    if not caption.strip():
        return
    horizontal = node.props.get('HorzFormatting', node.props.get('HorzLabelFormatting', 'LeftAligned'))
    wrap = horizontal.startswith('WordWrap')
    x0, y0, x1, y1 = text_area(node, rect, screen, user, s)
    width, height = x1 - x0, y1 - y0
    font = node.font()
    ascent, descent = font_metrics(font, screen, user)
    line = ascent + descent
    if wrap:
        lines, widest_word = wrap_text(font, caption, width, screen, user)
        if widest_word > width + TOLERANCE:
            problems.append((node, 'word wider than the box', widest_word, width))
    else:
        lines = caption.split(NEWLINE)
        longest = max(text_size(font, part, screen, user)[0] for part in lines)
        if longest > width + TOLERANCE:
            problems.append((node, 'text wider than the box', longest, width))
    # Vertical: the line boxes are placed by the vertical format, the glyph ink of the first and the last line must stay
    # inside the box (the window clips the glyphs; the empty space of the line box above and below the ink may overhang)
    block = len(lines) * line
    widest = max(text_size(font, part, screen, user)[0] for part in lines)
    ratio = widest / width if width > 0 else 9.9
    if node.layout not in tightest or ratio > tightest[node.layout][0]:
        tightest[node.layout] = (ratio, node.path)
    captions[node.layout] = captions.get(node.layout, 0) + 1
    vertical = node.props.get('VertFormatting', node.props.get('VertLabelFormatting', default_vertical(node)))
    if vertical.startswith('Cent'):
        block_top = y0 + (height - block) / 2.0
    elif vertical.startswith('Bottom'):
        block_top = y1 - block
    else:
        block_top = y0
    first_top = block_top + ascent + ink_extent(font, lines[0], screen, user)[0]
    last_bottom = block_top + (len(lines) - 1) * line + ascent + ink_extent(font, lines[-1], screen, user)[1]
    if first_top < y0 - TOLERANCE or last_bottom > y1 + TOLERANCE:
        problems.append((node, 'text higher than the box', last_bottom - first_top, height))


def default_vertical(node):
    """CEGUI default: static text is top aligned, buttons and check boxes centre their label."""
    return 'TopAligned' if node.type in STATIC_LIKE else 'CentreAligned'


def check_title(node, rect, screen, user, problems):
    if node.type not in FRAME_TYPES:
        return
    caption = node.props.get('Text')
    if not caption or not strip_markup(caption).strip():
        return
    font = node.props.get('TitlebarFont', FRAME_TITLE_FONT)
    left = image_size('OpenDungeonsSkin/TitleBarLeft', screen, user)[0] if node.type != 'OD/FrameWindow' else 0.0
    width = text_size(font, strip_markup(caption), screen, user)[0]
    # the title area is the width of the window minus 75 pixels (close button and corner), CEGUI offsets are pixels
    room = (rect[2] - rect[0]) - left - 75.0
    if width > room + TOLERANCE:
        problems.append((node, 'title wider than the title bar', width, room))


# ---------------------------------------------------------------------------------------------------- the check
CODE_ARRANGED_LAYOUTS = ('WindowTabRooms.layout', 'WindowTabTraps.layout', 'WindowTabSpells.layout')
CODE_ARRANGED_PAGES = ('/Rooms', '/Traps', '/Spells')


# Layouts and windows that are measured but whose findings are listed instead of failing the check. Each entry is a
# documented limit of a part of the game that is not an in-game window:
KNOWN_LIMITS = (
    # (layout file, path prefix or None for the whole layout, reason)
    ('WidgetsTest.layout', None,
     'developer widget gallery, no code loads it; its windows are test arrangements, not game windows'),
    ('WindowTabRooms.layout', 'EDITORGUI/MainTabControl/',
     'map editor build bar: fixed pixel positions designed for a 1024x768 bottom panel of 133 pixels, one row of buttons '
     'per page; the editor sheet is not an in-game window and has no arranging code (Gui::arrangeActionButtons is used on '
     'the game sheet only)'),
    ('ModeEditor.layout', 'EDITORGUI/HorizontalPipe/GoldDensityDisplay',
     'map editor status line: its area is pinned by check_world_balance_gold.py (editor, not an in-game window); at UI '
     'scale 120 % the text line is higher than the 25 design pixel box'),
    ('WindowTabTraps.layout', 'EDITORGUI/MainTabControl/', 'map editor build bar, see WindowTabRooms.layout'),
    ('WindowTabSpells.layout', 'EDITORGUI/MainTabControl/', 'map editor build bar, see WindowTabRooms.layout'),
)


def known_limit(layout, path):
    for known_layout, prefix, reason in KNOWN_LIMITS:
        if layout == known_layout and (prefix is None or path.startswith(prefix)):
            return reason
    return None


def overhang_allowed(node):
    """Documented exclusions of the containment test (see the module text)."""
    parent = node.parent
    if node.props.get('ClippedByParent') == 'False':
        return 'unclipped'
    if node.type in ('OD/ProgressBar', 'OD/AlternateProgressBar') and node.props.get('ClippedByParent') != 'False':
        # progress bars are tinted overlays of the tile or button they sit on (alpha 0.2 research / build progress);
        # the parent clips them, so a bar that is wider than its tile shows nothing outside the tile
        return 'overlay'
    if node.type == 'OD/GameTabButton' and node.layout in CODE_ARRANGED_LAYOUTS and node.parent.path.endswith(
            CODE_ARRANGED_PAGES) and 'Root/MainTabControl' in node.parent.path:
        # the room, trap and spell buttons of the game build bar are placed by Gui::arrangeRoomButtons /
        # arrangeTrapButtons / arrangeSpellButtons (arrangeActionButtons) from the visible buttons at every resolution,
        # the layout positions are only the defaults of the first frame
        return 'arranged by code'
    if parent is not None and parent.type in SCROLL_TYPES:
        # documented limit: a scrollable pane shows its own scrollbars as soon as the content is larger than the view
        # (and Gui::limitScrollingToVisibleControls sets its extent), so a longer content is reached by scrolling
        return 'scroll'
    if parent is not None and parent.type in LIST_TYPES:
        return 'list'
    return None


def walk(node, parent_client, parent_outer, screen, user, top_fit, problems, stats):
    if node.area() is None:
        return
    layout_scale = min(screen[0] / DESIGN_W, screen[1] / DESIGN_H) * user
    if screen_sized_container(node):
        fit = 1.0
    elif screen_sized_container(node.parent):
        fit = top_fit = fit_factor(node, screen, user)
    else:
        fit = top_fit
    s = layout_scale * fit
    non_client = node.props.get('NonClient') == 'True'
    rect = child_rect(node, parent_outer if non_client else parent_client, s)
    stats['windows'] += 1
    if node.type == 'OD/Combobox':
        # only the closed box counts (looknfeel: edit box = 1.5 line spacings); the drop down list opens over the other
        # windows and is never part of the layout rectangle
        ascent, descent = font_metrics(node.font(), screen, user)
        rect = (rect[0], rect[1], rect[2], min(rect[3], rect[1] + 1.5 * (ascent + descent)))
    skip = overhang_allowed(node)
    if node.parent is not None and not screen_sized_container(node.parent):
        pc = parent_outer if non_client else parent_client
        out = (rect[0] < pc[0] - TOLERANCE or rect[1] < pc[1] - TOLERANCE
               or rect[2] > pc[2] + TOLERANCE or rect[3] > pc[3] + TOLERANCE)
        if out and skip is None:
            problems.append((node, 'outside the client area of its parent',
                             tuple(round(v, 1) for v in rect), tuple(round(v, 1) for v in pc)))
    elif node.parent is not None and not screen_sized_container(node):
        # a window directly in a screen sized container: the fit factor keeps it on the screen
        if (rect[2] - rect[0] > screen[0] + TOLERANCE or rect[3] - rect[1] > screen[1] + TOLERANCE) \
                and not (node.area()[2][0] - node.area()[0][0] >= 1.0):
            problems.append((node, 'window larger than the screen', rect, (0, 0, screen[0], screen[1])))
    if node.type in LIST_TYPES:
        return
    check_text(node, rect, screen, user, s, problems)
    check_title(node, rect, screen, user, problems)
    client = client_rect(node, rect, screen, user, s)
    for child in node.children:
        walk(child, client, rect, screen, user, top_fit, problems, stats)


all_problems = {}
stats = {'windows': 0}
for screen in SCREENS:
    for user in USER_SCALES:
        for sheet in sheets:
            problems = []
            walk(sheet, (0.0, 0.0, float(screen[0]), float(screen[1])), (0.0, 0.0, float(screen[0]), float(screen[1])),
                 screen, user, 1.0, problems, stats)
            for node, kind, got, limit in problems:
                key = (node.layout, node.path, kind)
                all_problems.setdefault(key, []).append((screen, user, got, limit))

known = {key: cases for key, cases in all_problems.items() if known_limit(key[0], key[1])}
all_problems = {key: cases for key, cases in all_problems.items() if key not in known}
for layout, prefix, reason in KNOWN_LIMITS:
    count = sum(1 for key in known if key[0] == layout and (prefix is None or key[1].startswith(prefix)))
    print('known limit: %s %s: %d findings (%s)' % (layout, prefix or '(whole layout)', count, reason))
per_layout = {}
for (layout, path, kind), cases in sorted(all_problems.items()):
    per_layout.setdefault(layout, []).append((path, kind, cases))
for layout, entries in per_layout.items():
    for path, kind, cases in entries:
        screen, user, got, limit = cases[0]
        print('FAULT %s %s: %s (%d of %d cases, first %dx%d at %d%%: %s vs %s)' % (
            layout, path, kind, len(cases), len(SCREENS) * len(USER_SCALES), screen[0], screen[1],
            round(user * 100), got if isinstance(got, tuple) else round(got, 1),
            limit if isinstance(limit, tuple) else round(limit, 1)))
for layout in layouts:
    ratio, path = tightest.get(layout, (0.0, '-'))
    print('  %-34s %4d captions measured, tightest %3.0f%% of its box (%s)' % (
        layout, captions.get(layout, 0) // (len(SCREENS) * len(USER_SCALES)), ratio * 100, path.split('/')[-1]))
print('%d layouts, %d window evaluations, %d faults' % (len(layouts), stats['windows'], len(all_problems)))
if all_problems:
    sys.exit(1)
