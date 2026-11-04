"""Check the Workers window (key J, HUD button) without a running game and without compiling.

Pins the acceptance cases that can be read from the files: the window and every part of it are in the
layout, the painted pictures exist in the icon atlas, the six tablets fall in size from rank I to VI, the
window fits the screen at 640x480, 1024x768, 1920x1200 and 7680x4320 with UI scale 80 and 120 percent and
uses relative areas inside, key J and the help line, the HUD button with its tooltip, the handling of a
client without a keeper seat, Esc and the close button, the mode Automatic taking its order from
WorkerDefaultPriority, the ordering rules (arrows, drag, plus and minus, carry order) and the release note.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True


def read(path):
    """Return the text of a tracked file."""
    return (repo / path).read_text(encoding='utf-8')


NUMBER = r'(-?\d+(?:\.\d+)?)'
UDIM = r'\{' + NUMBER + ',' + NUMBER + r'\}'


def udims(value):
    """Return the (scale, offset) pairs of a CEGUI property value."""
    return [(float(a), float(b)) for a, b in re.findall(UDIM, value)]


def props(window):
    """The properties of a layout window as a dictionary."""
    return {p.get('name'): p.get('value') for p in window.findall('Property')}


layout_root = ET.fromstring(read('gui/WindowWorkers.layout'))
window = layout_root.find('Window')
assert window is not None and window.get('name') == 'WorkersWindow' and window.get('type') == 'OD/FrameWindow'
assert props(window)['Text'] == 'Workers', 'the window title is "Workers"'
assert props(window)['Visible'] == 'False', 'the window starts closed'


def child(parent, name):
    """The direct child window of the given name, which must exist."""
    for node in parent.findall('Window'):
        if node.get('name') == name:
            return node
    raise AssertionError('missing part ' + name + ' in ' + parent.get('name'))


# --- all parts are present (D1, D2, D6, D7)
for name in ('FreePanel', 'FreePortrait', 'FreeLabel', 'FreeCount', 'ModeAutomatic', 'ModePriority', 'PriorityPanel',
             'PriorityLabel', 'PriorityUp', 'PriorityDown', 'DragHand', 'DragHint', 'CarryTitle', 'CarryUp',
             'CarryDown', 'GoldPanel', 'GoldCoins', 'GoldLabel', 'GoldCheck'):
    child(window, name)
for mode in ('ModeAutomatic', 'ModePriority'):
    for part in ('Hand', 'Label'):
        child(child(window, mode), part)
for rank in range(6):
    tablet = child(window, 'Rank%d' % rank)
    for part in ('Frame', 'Numeral', 'Figure', 'Name', 'Minus', 'Count', 'Plus'):
        child(tablet, part)
    assert props(child(tablet, 'Minus'))['Text'] == '-' and props(child(tablet, 'Plus'))['Text'] == '+'
    child(window, 'Working%d' % rank)
for entry in range(7):
    frame = child(window, 'Carry%d' % entry)
    for part in ('Frame', 'Number', 'Picture', 'Name'):
        child(frame, part)
texts = {'FreeLabel': 'Free workers', 'PriorityLabel': 'Priority order', 'DragHint': 'Drag to reorder',
         'CarryTitle': 'Carry order', 'GoldLabel': 'Gold first (for digging)'}
for name, text in texts.items():
    assert props(child(window, name))['Text'] == text, name
assert props(child(child(window, 'ModeAutomatic'), 'Label'))['Text'] == 'Automatic'
assert props(child(child(window, 'ModePriority'), 'Label'))['Text'] == 'Priority list'

# --- the pictures exist in the icon atlas (images)
imageset = ET.parse(repo / 'gui/ODIcons.imageset').getroot()
atlas = {image.get('name') for image in imageset.findall('Image')}
code = read('source/render/WorkersWindow.cpp')
used = set(re.findall(r'OpenDungeonsIcons/(Worker\w+)', code + read('gui/WindowWorkers.layout') + read('gui/ModeGame.layout')))
assert used, 'the window uses no painted pictures'
# The arrow pictures are composed in the code from the direction and the state
if 'WorkerArrow' in used:
    used.discard('WorkerArrow')
    used.update('WorkerArrow' + d + st for d in ('Up', 'Down') for st in ('Normal', 'Hover', 'Pressed', 'Disabled'))
missing = sorted(name for name in used if name not in atlas)
assert not missing, 'pictures not in the atlas: %s' % missing
for name in ('WorkerJobDig', 'WorkerJobClaimGround', 'WorkerJobClaimWall', 'WorkerJobCarry', 'WorkerJobClean',
             'WorkerJobReload', 'WorkerFreePortrait', 'WorkerCarryOwn', 'WorkerCarryEnemy', 'WorkerCarryCorpses',
             'WorkerCarryGold', 'WorkerCarryItems', 'WorkerCarryGift', 'WorkerCarryTrapsDoors', 'WorkerHandInactive',
             'WorkerHandActive', 'WorkerHandDrag', 'WorkerArrowUpNormal', 'WorkerArrowDownDisabled',
             'WorkerCheckboxEmpty', 'WorkerCheckboxChecked', 'WorkerTabletNormal', 'WorkerTabletSelected',
             'WorkerCarryFrameNormal', 'WorkerCarryFrameSelected', 'WorkersButton'):
    assert name in used, 'picture not used: ' + name

# --- tablets fall in size from rank I to VI (D2)
widths = []
heights = []
for rank in range(6):
    v = udims(props(child(window, 'Rank%d' % rank))['Area'])
    widths.append(v[2][0] - v[0][0])
    heights.append(v[3][0] - v[1][0])
assert all(widths[i] > widths[i + 1] for i in range(5)), widths
assert all(heights[i] > heights[i + 1] for i in range(5)), heights
lefts = [udims(props(child(window, 'Rank%d' % r))['Area'])[0][0] for r in range(6)]
assert lefts == sorted(lefts), 'ranks run from left to right'
for rank in range(5):
    a = udims(props(child(window, 'Rank%d' % rank))['Area'])
    b = udims(props(child(window, 'Rank%d' % (rank + 1)))['Area'])
    assert a[2][0] <= b[0][0], 'tablets do not overlap'
carry_lefts = [udims(props(child(window, 'Carry%d' % e))['Area'])[0][0] for e in range(7)]
assert carry_lefts == sorted(carry_lefts), 'carry entries run from left to right'

# --- the window fits the screen at every size and the content uses relative areas only (fit_screen)
DESIGN_W, DESIGN_H = 1024.0, 768.0
area = udims(props(window)['Area'])
rel_w, off_w = area[2][0] - area[0][0], area[2][1] - area[0][1]
rel_h, off_h = area[3][0] - area[1][0], area[3][1] - area[1][1]
gui_cpp = read('source/render/Gui.cpp')
assert 'layoutScale * getWindowFitFactor(window)' in gui_cpp
for screen_w, screen_h in ((640, 480), (1024, 768), (1920, 1200), (7680, 4320)):
    for user in (0.8, 1.0, 1.2):
        scale = min(screen_w / DESIGN_W, screen_h / DESIGN_H) * user
        factor = 1.0
        if off_w * scale > 0 and rel_w < 1.0:
            factor = min(factor, max(0.0, (1.0 - rel_w) * screen_w) / (off_w * scale))
        if off_h * scale > 0 and rel_h < 1.0:
            factor = min(factor, max(0.0, (1.0 - rel_h) * screen_h) / (off_h * scale))
        width = rel_w * screen_w + off_w * scale * factor
        height = rel_h * screen_h + off_h * scale * factor
        assert width <= screen_w + 0.5 and height <= screen_h + 0.5, (screen_w, screen_h, user, width, height)
        # The window is not shrunk by the fit factor, so its text keeps the size it was made for
        assert factor >= 0.999, ('window shrinks below its text at', screen_w, screen_h, user)
for node in window.iter('Window'):
    if node is window:
        continue
    for name, value in props(node).items():
        if name == 'Area':
            assert all(offset == 0 for _s, offset in udims(value)), node.get('name') + ' uses a fixed pixel area'
        if name == 'Font':
            size = int(value.rsplit('-', 1)[1])
            assert size >= 8, node.get('name') + ' has a font too small to read'

# --- HUD button (D9, D10): a painted icon of its own in the icon row above the minimap, like the other icon buttons
hud = ET.parse(repo / 'gui/ModeGame.layout').getroot()
imports = [n.get('filename') for n in hud.iter('LayoutImport')]
assert 'WindowWorkers.layout' in imports
button = None
icon_row = {}
for node in hud.iter('Window'):
    if node.get('name') == 'WorkersButton':
        button = node
    if node.get('name') in ('SocialButton', 'InfirmaryButton', 'MerchantButton'):
        icon_row[node.get('name')] = node
assert button is not None, 'HUD button WorkersButton is missing'
assert button.get('type') == 'OD/GameTabButton', 'the HUD button is an icon button like the others'
button_props = props(button)
assert button_props['TooltipText'] == 'Workers (J)'
assert button_props['NormalImage'] == 'OpenDungeonsIcons/WorkersButton'
assert 'HoverImage' not in button_props and 'PushedImage' not in button_props and 'Text' not in button_props,     'the icon button draws no text and no old hud pictures'
assert button_props.get('NavigationFrame') == 'True' and button_props.get('AlwaysOnTop') == 'True'
assert 'J' in button_props.get('ContextHelp', '') or 'ContextHelp' in {u.get('name') for u in button.findall('UserString')}
button_area = udims(button_props['Area'])
assert button_area[1][0] == 1 and button_area[3][0] == 1, 'the button sits in the bottom bar'
button_box = (button_area[0][1], button_area[1][1], button_area[2][1], button_area[3][1])
assert button_box[2] - button_box[0] == 40 and button_box[3] - button_box[1] == 40, 'the same 40 pixel icon size as its row'
for other_name, other in icon_row.items():
    other_area = udims(props(other)['Area'])
    other_box = (other_area[0][1], other_area[1][1], other_area[2][1], other_area[3][1])
    assert (other_box[3] - other_box[1]) == 40
    assert other_box[1] == button_box[1], 'the Workers icon is in the same row as ' + other_name
    assert other_box[2] <= button_box[0] or button_box[2] <= other_box[0], 'the Workers icon covers ' + other_name
for atlas_name in ('WorkersButton',):
    assert atlas_name in atlas
# The old text button pictures are no longer used by any layout or by the window code
assert 'WorkersHud' not in read('gui/ModeGame.layout') + read('gui/WindowWorkers.layout') + code, 'old text button pictures'

# --- key J, help line, seat handling, Esc (D9, D10)
game = read('source/modes/GameMode.cpp')
assert re.search(r'case OIS::KC_J:\s*mWorkersWindow->toggle\(\);\s*break;', game), 'key J toggles the window'
for path in sorted((repo / 'source').rglob('*.cpp')):
    if path.name == 'GameMode.cpp':
        continue
    assert 'KC_J' not in path.read_text(encoding='utf-8', errors='replace'), 'key J is used elsewhere: ' + str(path)
assert game.count('OIS::KC_J') == 1
assert ('"  - J or the workers icon above the minimap opens the workers window: fixed workers per job, free workers, priority and carry order."' in game)
assert 'guiSheet->getChild("WorkersButton")->hide();' in game and 'mWorkersWindow->hide();' in game
assert 'mWorkersWindow->update();' in game
assert 'mWorkersWindow.reset(new WorkersWindow(mRootWindow, *mGameMap));' in game
assert 'WorkersWindow.cpp' in read('CMakeLists.txt')
show = code[code.index('void WorkersWindow::show()'):code.index('void WorkersWindow::hide()')]
assert 'getSeat() == nullptr' in show and show.index('getSeat() == nullptr') < show.index('mWindow->show()'), \
    'a client without a seat gets no window'
update = code[code.index('void WorkersWindow::update()'):code.index('bool WorkersWindow::onCloseClicked')]
assert 'mButton->setVisible(keeper)' in update and 'keeper = (getSeat() != nullptr)' in update
seat = code[code.index('Seat* WorkersWindow::getSeat() const'):code.index('void WorkersWindow::show()')]
assert 'getLocalPlayer()' in seat and 'player == nullptr' in seat and 'player->getSeat()' in seat
assert 'CEGUI::FrameWindow::EventCloseClicked' in code
close = code[code.index('bool WorkersWindow::onCloseClicked'):code.index('bool WorkersWindow::onButtonClicked')]
assert 'hide();' in close and 'return true;' in close, 'Esc and the close button close the window'

# --- every change is sent as the complete settings; the window shows only what the server stored (D8)
assert 'setWorkerJobSettings' not in code and 'setWorkerJobCounts' not in code, 'the window never stores settings itself'
assert 'sendWorkerJobSettings(settings)' in code and 'validWorkerJobSettings(settings)' in code
assert code.count('WorkerJobSettings next = seat->getWorkerJobSettings();') >= 6
plus = code[code.index('bool WorkersWindow::onFixedClicked'):code.index('bool WorkersWindow::onCarryPressed')]
assert 'seat->getFreeWorkers() == 0' in plus and '++next.fixed[job]' in plus, '"+" needs a free worker'
assert 'next.fixed[job] == 0' in plus and '--next.fixed[job]' in plus, '"-" stops at 0'
assert 'next.goldFirst = (next.goldFirst == 0) ? 1 : 0;' in code
assert 'seat->getWorkerJobCounts()' in code and '"Working: "' in code
assert 'seat->getFreeWorkers()' in code

# --- Automatic takes its order from WorkerDefaultPriority (D3)
config = read('config/global.cfg')
line = re.search(r'^\s*WorkerDefaultPriority\s+(.+)$', config, re.M).group(1).split()
job_ids = {'dig': 0, 'claimGround': 1, 'claimWall': 2, 'carry': 3, 'clean': 4, 'reload': 5}
default_priority = [job_ids[name] for name in line]
assert default_priority == [3, 0, 1, 2, 4, 5], default_priority
header = read('source/game/WorkerJobs.h')
assert 'enum class WorkerJob : uint32_t { dig, claimGround, claimWall, carry, clean, reload, none };' in header
assert 'enum class WorkerFreeMode : uint32_t { automatic, priority };' in header
order_code = code[code.index('WorkersWindow::getDisplayOrder'):code.index('const char* WorkersWindow::getRankNumeral')]
assert 'settings.priority' in order_code and 'return defaults.priority;' in order_code
assert 'getDefaultWorkerJobSettings()' in code
manager = read('source/utils/ConfigManager.cpp')
assert 'mWorkerJobDefaults.priority' in manager and '"WorkerDefaultPriority"' in manager
job_names = re.findall(r'"([A-Z][a-z]+(?: [a-z]+)?)"', code[code.index('JOB_NAMES'):code.index('JOB_IMAGES')])
assert job_names == ['Dig', 'Claim ground', 'Claim wall', 'Carry', 'Clean', 'Reload'], job_names
carry_names = re.findall(r'"([A-Z][a-z]+(?: [a-z]+)*)"', code[code.index('CARRY_NAMES'):code.index('CARRY_IMAGES')])
assert carry_names == ['Own knocked out', 'Enemy knocked out', 'Corpses', 'Gold', 'Items', 'Gift boxes', 'Traps and doors'], carry_names
assert re.findall(r'"([IV]+)"', code[code.index('RANK_NUMERALS'):code.index('CARRY_NAMES')]) == ['I', 'II', 'III', 'IV', 'V', 'VI']
assert 'enum class WorkerCarryEntry : uint32_t { ownKnockedOut, enemyKnockedOut, corpse, gold, items, giftBoxes, trapsDoors, none };' in header


def display_order(free_mode, priority):
    """Mirror of WorkersWindow::getDisplayOrder."""
    return list(priority) if free_mode == 1 else list(default_priority)


def move_entry(order, source, target):
    """Mirror of WorkersWindow::moveOrderEntry."""
    if source >= len(order) or target >= len(order) or source == target:
        return False
    value = order[source]
    if source < target:
        for i in range(source, target):
            order[i] = order[i + 1]
    else:
        for i in range(source, target, -1):
            order[i] = order[i - 1]
    order[target] = value
    return True


mover = read('source/render/WorkersWindow.h')
mover = mover[mover.index('static bool moveOrderEntry'):mover.index('static const char* getRankNumeral')]
for fragment in ('from >= N || to >= N || from == to', 'order[i] = order[i + 1];', 'order[i] = order[i - 1];', 'order[to] = value;'):
    assert fragment in mover, fragment
DIG, CLAIM_GROUND, CLAIM_WALL, CARRY, CLEAN, RELOAD = range(6)
keeper_list = [DIG, CARRY, CLEAN, RELOAD, CLAIM_GROUND, CLAIM_WALL]
# automatic_view: the keeper's own list is kept but the tablets follow the predefined priority
assert display_order(0, keeper_list) == [CARRY, DIG, CLAIM_GROUND, CLAIM_WALL, CLEAN, RELOAD]
assert display_order(1, keeper_list) == [DIG, CARRY, CLEAN, RELOAD, CLAIM_GROUND, CLAIM_WALL]
# move_up: Clean (III) up gives Clean on II and Carry on III
moved = list(keeper_list)
assert move_entry(moved, 2, 1) and moved == [DIG, CLEAN, CARRY, RELOAD, CLAIM_GROUND, CLAIM_WALL]
# drag_tablet: Claim wall (VI) onto I
moved = list(keeper_list)
assert move_entry(moved, 5, 0) and moved == [CLAIM_WALL, DIG, CARRY, CLEAN, RELOAD, CLAIM_GROUND]
# rank_edges: nothing moves beyond the ends
assert 'if(up && place == 0)' in code and 'if(!up && place + 1 >= JOB_COUNT)' in code
assert 'if(!up && place + 1 >= CARRY_COUNT)' in code
# carry_move: Gold (4) up twice, then Items dragged onto 1
carry = [0, 1, 2, 3, 4, 5, 6]
assert move_entry(carry, 3, 2) and move_entry(carry, 2, 1) and carry[1] == 3
assert move_entry(carry, carry.index(4), 0) and carry == [4, 0, 3, 1, 2, 5, 6], carry
# Automatic: no arrows, no drag, no selection
assert code.count('WorkerFreeMode::priority') >= 5
pressed = code[code.index('bool WorkersWindow::onTabletPressed'):code.index('bool WorkersWindow::onTabletReleased')]
assert 'settings.freeMode != static_cast<uint32_t>(WorkerFreeMode::priority)' in pressed and 'return true;' in pressed
finish = code[code.index('void WorkersWindow::finishDrag()'):code.index('bool WorkersWindow::onPriorityArrowClicked')]
assert 'next.freeMode == static_cast<uint32_t>(WorkerFreeMode::priority)' in finish, 'a tablet drag works in Priority list only'
refresh = code[code.index('void WorkersWindow::refresh()'):]
assert 'mSelectedJob = -1;' in refresh and 'WorkerArrow' in code and 'Disabled' in code
mode = code[code.index('bool WorkersWindow::onModeClicked'):code.index('int32_t WorkersWindow::getSlotId')]
assert 'mSelectedJob = -1;' in mode, 'a switch of the mode clears the selection'

# --- every text is fully readable at every screen size and UI scale (R2): measured with the font of the game
from PIL import ImageFont

FONT_FILE = str(repo / 'gui/fonts/SourceSerif4-Semibold.ttf')
FONT_DESIGN_W, FONT_DESIGN_H = 800.0, 600.0
# Frame of the window in layout pixels at the design size: left, top, right, bottom (measured in the game)
FRAME = (34.0, 32.0, 34.0, 36.0)
_fonts = {}


def text_font(size_px):
    """The font of the game at a pixel size."""
    key = round(size_px * 4)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_FILE, max(1.0, key / 4.0))
    return _fonts[key]


def wrap_lines(text, font, width):
    """Greedy word wrap like the CEGUI word wrap formatting; returns the lines."""
    lines = []
    current = ''
    for word in text.split(' '):
        trial = word if not current else current + ' ' + word
        if current and font.getlength(trial) > width:
            lines.append(current)
            current = word
        else:
            current = trial
    lines.append(current)
    return lines


def child_rect(node, parent_rect, scale):
    """Pixel rectangle (x, y, w, h) of a layout window inside its parent rectangle, with the aspect mode Shrink."""
    values = udims(props(node)['Area'])
    px, py, pw, ph = parent_rect
    left = px + values[0][0] * pw + values[0][1] * scale
    top = py + values[1][0] * ph + values[1][1] * scale
    width = (values[2][0] - values[0][0]) * pw + (values[2][1] - values[0][1]) * scale
    height = (values[3][0] - values[1][0]) * ph + (values[3][1] - values[1][1]) * scale
    p = props(node)
    if p.get('AspectMode') == 'Shrink':
        ratio = float(p['AspectRatio'])
        if width / height > ratio:
            width = height * ratio
        else:
            height = width / ratio
    return (left, top, width, height)


def window_rect(screen_w, screen_h, user):
    """Client rectangle of the Workers window and the layout scale for a screen and a UI scale."""
    scale = min(screen_w / DESIGN_W, screen_h / DESIGN_H) * user
    outer = udims(props(window)['Area'])
    width = (outer[2][0] - outer[0][0]) * screen_w + (outer[2][1] - outer[0][1]) * scale
    height = (outer[3][0] - outer[1][0]) * screen_h + (outer[3][1] - outer[1][1]) * scale
    left = outer[0][0] * screen_w + outer[0][1] * scale
    top = outer[1][0] * screen_h + outer[1][1] * scale
    left_edge, top_edge, right_edge, bottom_edge = (v * scale for v in FRAME)
    return (left + left_edge, top + top_edge, width - left_edge - right_edge, height - top_edge - bottom_edge), scale


def font_pixels(node, screen_w, screen_h, user):
    """Pixel size of the font of a layout window (size in points at 96 dpi, scaled like the game scales fonts)."""
    size = int(props(node)['Font'].rsplit('-', 1)[1])
    return size * 96.0 / 72.0 * min(screen_w / FONT_DESIGN_W, screen_h / FONT_DESIGN_H) * user


def check_text(node, text, rect, screen_w, screen_h, user, what):
    """The text must fit the window: wrapped texts in their height, every line in the width."""
    p = props(node)
    if p.get('Font') is None or not text:
        return
    font = text_font(font_pixels(node, screen_w, screen_h, user))
    ascent, descent = font.getmetrics()
    line_height = ascent + descent
    width = rect[2] * 0.94
    if 'WordWrap' in p.get('HorzFormatting', ''):
        lines = wrap_lines(text, font, width)
    else:
        lines = [text]
    for line in lines:
        assert font.getlength(line) <= width, ('text too wide', what, text, line, screen_w, screen_h, user,
                                               round(font.getlength(line)), round(width))
    # What is painted: the lines one below the other, the last one as high as its ink (the glyphs, not the line box)
    ink = max(font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines)
    painted = (len(lines) - 1) * line_height + ink
    assert painted <= rect[3] * 0.98, ('text too high', what, text, len(lines), screen_w, screen_h, user,
                                       round(painted), round(rect[3]))


def check_tree(node, rect, scale, screen_w, screen_h, user, texts):
    """Check the texts of all windows below a node; texts maps a window name to the list of possible texts."""
    for sub in node.findall('Window'):
        sub_rect = child_rect(sub, rect, scale)
        name = sub.get('name')
        possible = texts.get(name)
        if possible is None:
            own = props(sub).get('Text')
            possible = [own] if own else []
        if sub.get('type') == 'OD/StaticText' or name in ('Minus', 'Plus'):
            for text in possible:
                check_text(sub, text, sub_rect, screen_w, screen_h, user, name)
        check_tree(sub, sub_rect, scale, screen_w, screen_h, user, texts)


for screen_w, screen_h in ((640, 480), (800, 600), (1024, 768), (1366, 768), (1920, 1200), (7680, 4320)):
    for user in (0.8, 1.0, 1.2):
        client, scale = window_rect(screen_w, screen_h, user)
        assert client[0] >= 0 and client[1] >= 0 and client[0] + client[2] <= screen_w + 0.5 and \
            client[1] + client[3] <= screen_h + 0.5, 'window outside the screen'
        for rank in range(6):
            tablet = child(window, 'Rank%d' % rank)
            rect = child_rect(tablet, client, scale)
            local = {'Name': job_names, 'Count': ['0', '12', '99'], 'Numeral': ['I', 'II', 'III', 'IV', 'V', 'VI'][rank:rank + 1]}
            check_tree(tablet, rect, scale, screen_w, screen_h, user, local)
            working = child(window, 'Working%d' % rank)
            check_text(working, 'Working: 99', child_rect(working, client, scale), screen_w, screen_h, user, 'Working')
        for entry in range(7):
            frame = child(window, 'Carry%d' % entry)
            rect = child_rect(frame, client, scale)
            check_tree(frame, rect, scale, screen_w, screen_h, user, {'Name': carry_names, 'Number': [str(entry + 1)]})
        for node in window.findall('Window'):
            name = node.get('name')
            if (name.startswith(('Rank', 'Carry')) and name not in ('CarryTitle', 'CarryUp', 'CarryDown')) or \
                    name.startswith('Working'):
                continue
            rect = child_rect(node, client, scale)
            texts = {'FreeCount': ['0', '12', '99']}.get(name, [props(node).get('Text')] if props(node).get('Text') else [])
            if node.get('type') == 'OD/StaticText':
                for text in texts:
                    check_text(node, text, rect, screen_w, screen_h, user, name)
            if name in ('ModeAutomatic', 'ModePriority'):
                check_tree(node, rect, scale, screen_w, screen_h, user, {})

# --- the icon sits in the icon row directly above the minimap, next to the other icons (owner check of build 28)
row_boxes = {}
for node in hud.iter('Window'):
    node_props = props(node)
    if node.get('type') == 'OD/GameTabButton' and 'Area' in node_props:
        box = udims(node_props['Area'])
        if box[1][0] == 1 and box[1][1] == -224:
            row_boxes[node.get('name')] = box[0][1]
assert button_box[0] == row_boxes['WorkersButton'] and button_box[1] == -224
# The icons of the row stand on a 48 unit grid starting at the minimap edge; every slot is used once
assert sorted(row_boxes.values()) == list(range(4, 4 + 48 * len(row_boxes), 48)), row_boxes
assert len(set(row_boxes.values())) == len(row_boxes), 'two icons share a slot'
# The icons that are always there (goals, skill, production, dungeonbook) come first and the Workers icon is the next one, so it
# is never separated from them by free slots; icons that only show up later (room buttons, sandbox) follow behind it
always = [row_boxes[n] for n in ('GoalsButton', 'ResearchButton', 'ProductionButton', 'SocialButton')]
assert sorted(always) == [4, 52, 100, 148], always
assert row_boxes['WorkersButton'] == 196, 'the Workers icon is the first one after the always visible icons'
assert all(row_boxes[n] > 196 for n in ('MerchantButton', 'LabButton', 'SandboxButton', 'InfirmaryButton'))
# It stays left of the control panel toggle that ends the row and well inside the minimap column of the bottom bar
assert button_box[2] <= 400, 'the Workers icon is not floating towards the middle of the screen'

# --- pictures dominate, texts stay small (owner check of build 29): measured at every screen size and UI scale
for screen_w, screen_h in ((640, 480), (1024, 768), (1920, 1200), (7680, 4320)):
    for user in (0.8, 1.0, 1.2):
        client, scale = window_rect(screen_w, screen_h, user)
        for rank in range(6):
            tablet = child(window, 'Rank%d' % rank)
            t_rect = child_rect(tablet, client, scale)
            fig = child_rect(child(tablet, 'Figure'), t_rect, scale)
            figure_side = min(fig[2], fig[3])
            assert figure_side >= 0.80 * t_rect[2], ('the worker figure fills the tablet width', rank, figure_side, t_rect[2])
            assert figure_side >= 0.42 * t_rect[3], ('the worker figure fills the tablet height', rank, figure_side, t_rect[3])
            name_px = font_pixels(child(tablet, 'Name'), screen_w, screen_h, user)
            assert figure_side >= 4.0 * name_px, ('the job name is small below the figure', rank, figure_side, name_px)
            assert props(child(tablet, 'Name'))['Font'] == 'MedievalSharp-10', 'the job name is the second text size'
            assert udims(props(child(tablet, 'Name'))['Area'])[3][0] > udims(props(child(tablet, 'Figure'))['Area'])[1][0], \
                'the job name stands below the top of the figure'
            assert props(child(tablet, 'Name'))['VertFormatting'] == 'BottomAligned', 'the name sits right above the buttons'
        for entry in range(7):
            frame = child(window, 'Carry%d' % entry)
            c_rect = child_rect(frame, client, scale)
            pic = child_rect(child(frame, 'Picture'), c_rect, scale)
            picture_side = min(pic[2], pic[3])
            assert picture_side >= 0.75 * c_rect[2], ('the carry picture fills its entry', entry, picture_side, c_rect[2])
            assert picture_side >= 0.40 * c_rect[3], ('the carry picture fills its entry height', entry, picture_side, c_rect[3])
            name_px = font_pixels(child(frame, 'Name'), screen_w, screen_h, user)
            assert picture_side >= 5.0 * name_px, ('the carry name is small below the picture', entry, picture_side, name_px)
# Window texts: no text is larger than in the mockup (small names and labels, the count of free workers the largest)
text_limits = {'FreeCount': 13, 'CarryTitle': 12, 'FreeLabel': 10, 'PriorityLabel': 10, 'GoldLabel': 8, 'DragHint': 8}
for node in window.findall('Window'):
    name = node.get('name')
    if name in text_limits:
        assert int(props(node)['Font'].rsplit('-', 1)[1]) <= text_limits[name], (name, props(node)['Font'])
    if name.startswith('Working'):
        assert props(node)['Font'] == 'MedievalSharp-8', name + ' is a small text'
    if name.startswith('Carry') and name[5:].isdigit():
        assert props(child(node, 'Name'))['Font'] == 'MedievalSharp-8', 'the carry names are the small text size'
for name in ('ModeAutomatic', 'ModePriority'):
    assert props(child(child(window, name), 'Label'))['Font'] == 'MedievalSharp-10'
for node in window.iter('Window'):
    if 'Font' in props(node):
        assert int(props(node)['Font'].rsplit('-', 1)[1]) <= 13, (node.get('name'), 'text larger than the mockup')

# --- binding target sizes at 1920x1200 (owner decision 610, mockup variant-b-worker-colour.png), tolerance 10 percent
from PIL import Image


def visible_box(png):
    """Width and height of the visible (not transparent) part of a 256 pixel picture, as fractions of the picture."""
    image = Image.open(repo / 'assets-src/gui/icons/tiles' / (png + '.png')).convert('RGBA')
    box = image.split()[3].point(lambda v: 255 if v > 40 else 0).getbbox()
    return (box[2] - box[0]) / image.width, (box[3] - box[1]) / image.height


def cap_height(node, screen_w, screen_h, user):
    """Pixel height of a capital letter of the font of a layout window."""
    font = text_font(font_pixels(node, screen_w, screen_h, user))
    box = font.getbbox('H')
    return box[3] - box[1]


TARGET_TOLERANCE = 0.10
target_rows = []


def target(item, expected, computed):
    """Record an item and require every number of it to be within the tolerance of its target."""
    target_rows.append((item, expected, computed))
    for want, got in zip(expected, computed):
        assert abs(got - want) <= TARGET_TOLERANCE * want, ('target missed', item, expected, computed)


client, scale = window_rect(1920, 1200, 1.0)
outer = udims(props(window)['Area'])
outer_w = (outer[2][0] - outer[0][0]) * 1920 + (outer[2][1] - outer[0][1]) * scale
outer_h = (outer[3][0] - outer[1][0]) * 1200 + (outer[3][1] - outer[1][1]) * scale
outer_x = outer[0][0] * 1920 + outer[0][1] * scale
outer_y = outer[1][0] * 1200 + outer[1][1] * scale
target('window', (1480, 940), (outer_w, outer_h))
assert abs(outer_x + outer_w / 2 - 960) < 1 and abs(outer_y + outer_h / 2 - 600) < 1, 'the window is centred'
tablet_names = ['I', 'II', 'III', 'IV', 'V', 'VI']
tablet_targets = [(266, 387), (222, 345), (194, 313), (176, 290), (165, 270), (157, 254)]
tablet_sizes = []
for rank in range(6):
    t_rect = child_rect(child(window, 'Rank%d' % rank), client, scale)
    tablet_sizes.append((t_rect[2], t_rect[3]))
    target('tablet ' + tablet_names[rank] + (' (rank in between)' if 0 < rank < 5 else ''), tablet_targets[rank], tablet_sizes[rank])
for rank in range(5):
    assert tablet_sizes[rank][0] > tablet_sizes[rank + 1][0] and tablet_sizes[rank][1] > tablet_sizes[rank + 1][1], 'falls by rank'
# The worker figure: the visible part of its picture fills about 70 percent of the width of its tablet
job_pictures = ['WorkerJobDig', 'WorkerJobClaimGround', 'WorkerJobClaimWall', 'WorkerJobCarry', 'WorkerJobClean', 'WorkerJobReload']
visible_w = sum(visible_box(name)[0] for name in job_pictures) / len(job_pictures)
fill = []
for rank in range(6):
    tablet = child(window, 'Rank%d' % rank)
    t_rect = child_rect(tablet, client, scale)
    fig = child_rect(child(tablet, 'Figure'), t_rect, scale)
    fill.append(min(fig[2], fig[3]) * visible_w / t_rect[2])
target('worker figure width / tablet width, rank I', (0.70,), (fill[0],))
target('worker figure width / tablet width, rank VI', (0.70,), (fill[5],))
assert all(abs(v - 0.70) <= 0.07 for v in fill), fill
carry_pictures = ['WorkerCarryOwn', 'WorkerCarryEnemy', 'WorkerCarryCorpses', 'WorkerCarryGold', 'WorkerCarryItems',
                  'WorkerCarryGift', 'WorkerCarryTrapsDoors']
c_rect = child_rect(child(window, 'Carry0'), client, scale)
target('carry entry', (169, 188), (c_rect[2], c_rect[3]))
for entry in range(7):
    entry_rect = child_rect(child(window, 'Carry%d' % entry), client, scale)
    assert abs(entry_rect[2] - c_rect[2]) < 0.5 and abs(entry_rect[3] - c_rect[3]) < 0.5, 'all carry entries are equally large'
pic = child_rect(child(child(window, 'Carry0'), 'Picture'), c_rect, scale)
side = min(pic[2], pic[3])
mean_w = sum(visible_box(name)[0] for name in carry_pictures) / len(carry_pictures)
mean_h = sum(visible_box(name)[1] for name in carry_pictures) / len(carry_pictures)
target('carry picture (mean visible part of the seven)', (110, 60), (side * mean_w, side * mean_h))
job_cap = cap_height(child(child(window, 'Rank0'), 'Name'), 1920, 1200, 1.0)
carry_cap = cap_height(child(child(window, 'Carry0'), 'Name'), 1920, 1200, 1.0)
target('job name cap height', (17,), (job_cap,))
target('carry name cap height', (15,), (carry_cap,))
for name in ('FreeLabel', 'PriorityLabel', 'DragHint', 'GoldLabel', 'CarryTitle', 'FreeCount'):
    assert cap_height(child(window, name), 1920, 1200, 1.0) <= 23, (name, 'window text larger than in the mockup')
assert cap_height(child(window, 'Working0'), 1920, 1200, 1.0) <= carry_cap + 1, 'the Working line is in the small text size'
# The Working line sits below its tablet, centred under it
for rank in range(6):
    t_rect = child_rect(child(window, 'Rank%d' % rank), client, scale)
    w_rect = child_rect(child(window, 'Working%d' % rank), client, scale)
    assert w_rect[1] >= t_rect[1] + t_rect[3] - 1, 'Working line below its tablet'
    assert abs((w_rect[0] + w_rect[2] / 2) - (t_rect[0] + t_rect[2] / 2)) < 2, 'Working line centred under its tablet'
if '--table' in sys.argv:
    for item, expected, computed in target_rows:
        print('| %s | %s | %s |' % (item, ' x '.join('%g' % v for v in expected), ' x '.join('%.1f' % v for v in computed)))

# --- the tick box "Gold first" is large and its ticked state differs clearly from the empty one (R3)
for name in ('WorkerCheckboxEmpty', 'WorkerCheckboxChecked'):
    assert imageset.find("Image[@name='%s']" % name).get('width') == '256', name + ' is the large picture'
gold_check = child(window, 'GoldCheck')
check_props = props(gold_check)
assert check_props['NormalImage'].endswith('WorkerCheckboxEmpty')
client, scale = window_rect(1024, 768, 1.0)
box = child_rect(gold_check, client, scale)
assert min(box[2], box[3]) >= 44, ('the tick box is too small', box)
client, scale = window_rect(640, 480, 0.8)
box = child_rect(gold_check, client, scale)
assert min(box[2], box[3]) >= 20, ('the tick box is too small at 640x480', box)
assert 'check->setProperty("NormalImage", checkImage);' in code and 'WorkerCheckboxChecked' in code
assert 'getChild("GoldLabel")->setProperty("TextColours", settings.goldFirst != 0 ? COLOUR_LIT : COLOUR_NORMAL)' in code, \
    'the ticked state also lights the label'
for tile in ('WorkerCheckboxEmpty', 'WorkerCheckboxChecked'):
    assert (repo / 'assets-src/gui/icons/tiles' / (tile + '.png')).exists()

# --- dragging tablets and carry entries (R4): the event wiring, the layout properties and the drop mapping
down_up = re.findall(r'subscribeEvent\(CEGUI::Window::EventMouseButton(Down|Up),\s*CEGUI::Event::Subscriber\(&WorkersWindow::(\w+), this\)\)',
                     code)
assert ('Down', 'onTabletPressed') in down_up and ('Down', 'onCarryPressed') in down_up
assert down_up.count(('Up', 'onDragReleased')) == 3, 'the window, the tablets and the carry entries end a drag'
assert 'mWindow->subscribeEvent(CEGUI::Window::EventMouseButtonUp' in code, 'a drag ending beside every slot still ends'
# The release reads the pointer of the GUI context, not the position of the event
drag = code[code.index('void WorkersWindow::finishDrag()'):code.index('bool WorkersWindow::onPriorityArrowClicked')]
assert 'getDefaultGUIContext().getMouseCursor().getPosition()' in drag and 'mouse.position' not in drag
assert 'mDragTablet = -1;' in drag and 'mDragCarry = -1;' in drag, 'a drag ends once'
assert 'findSlotAt("Rank", JOB_COUNT' in drag and 'findSlotAt("Carry", CARRY_COUNT' in drag
# Slots are buttons (they hold the pointer while pressed) and everything painted on them lets the pointer through
for slots, parts in (('Rank', ('Frame', 'Numeral', 'Figure', 'Name', 'Count')), ('Carry', ('Frame', 'Number', 'Picture', 'Name'))):
    for index in range(6 if slots == 'Rank' else 7):
        slot = child(window, '%s%d' % (slots, index))
        assert slot.get('type') == 'OD/InvisibleButton', 'a slot is a button that holds the pointer'
        assert 'MousePassThroughEnabled' not in props(slot) and props(slot).get('Enabled', 'True') == 'True'
        for part in parts:
            assert props(child(slot, part)).get('MousePassThroughEnabled') == 'True', (slots, index, part)
for name in ('FreePanel', 'PriorityPanel', 'GoldPanel', 'GoldCoins', 'GoldLabel', 'DragHand', 'DragHint', 'CarryTitle'):
    assert props(child(window, name)).get('MousePassThroughEnabled') == 'True', name + ' must not cover a slot'
for index in range(6):
    assert props(child(window, 'Working%d' % index)).get('MousePassThroughEnabled') == 'True'


def drop_slot(rects, x, y):
    """Mirror of WorkersWindow::getDropSlot."""
    if not rects:
        return -1
    top = min(r[1] for r in rects)
    bottom = max(r[3] for r in rects)
    tolerance = (bottom - top) * 0.25
    if y < top - tolerance or y > bottom + tolerance:
        return -1
    for i, r in enumerate(rects):
        left = r[0] - (r[2] - r[0]) * 0.5 if i == 0 else (rects[i - 1][2] + r[0]) * 0.5
        right = r[2] + (r[2] - r[0]) * 0.5 if i + 1 == len(rects) else (r[2] + rects[i + 1][0]) * 0.5
        if left <= x < right:
            return i
    return -1


for fragment in ('const float tolerance = (bottom - top) * 0.25f;', 'if(y < top - tolerance || y > bottom + tolerance)',
                 '(rects[i - 1][2] + rects[i][0]) * 0.5f', '(rects[i][2] + rects[i + 1][0]) * 0.5f',
                 'if(x >= left && x < right)'):
    assert fragment in code, fragment

for screen_w, screen_h, user in ((640, 480, 0.8), (1024, 768, 1.0), (1920, 1200, 1.2), (7680, 4320, 0.8)):
    client, scale = window_rect(screen_w, screen_h, user)
    for slots, count, order in (('Rank', 6, [DIG, CARRY, CLEAN, RELOAD, CLAIM_GROUND, CLAIM_WALL]),
                                ('Carry', 7, [0, 1, 2, 3, 4, 5, 6])):
        rects = []
        for index in range(count):
            x, y, w, h = child_rect(child(window, '%s%d' % (slots, index)), client, scale)
            rects.append((x, y, x + w, y + h))
        for source in range(count):
            for target in range(count):
                # release in the middle of the target and near its edges, still inside its column
                for fx, fy in ((0.5, 0.5), (0.1, 0.1), (0.9, 0.9), (0.5, 1.15), (0.5, -0.15)):
                    r = rects[target]
                    px = r[0] + (r[2] - r[0]) * fx
                    py = r[1] + (r[3] - r[1]) * fy
                    assert drop_slot(rects, px, py) == target, (slots, source, target, fx, fy)
                dragged = list(order)
                moved = move_entry(dragged, source, drop_slot(rects, (rects[target][0] + rects[target][2]) / 2,
                                                              (rects[target][1] + rects[target][3]) / 2))
                assert moved == (source != target)
                if source != target:
                    assert dragged[target] == order[source], 'the dragged entry takes the place it is dropped on'
        # between two slots a drop belongs to one of the two neighbours; far away it belongs to none
        for index in range(count - 1):
            gap = (rects[index][2] + rects[index + 1][0]) / 2
            assert drop_slot(rects, gap - 0.01, (rects[index][1] + rects[index][3]) / 2) == index
            assert drop_slot(rects, gap + 0.01, (rects[index][1] + rects[index][3]) / 2) == index + 1
        row_top = min(r[1] for r in rects)
        row_bottom = max(r[3] for r in rects)
        assert drop_slot(rects, rects[0][0] + 1, row_top - (row_bottom - row_top)) == -1
        assert drop_slot(rects, rects[0][0] + 1, row_bottom + (row_bottom - row_top)) == -1
        assert drop_slot(rects, rects[-1][2] + (rects[-1][2] - rects[-1][0]), (row_top + row_bottom) / 2) == -1
    # drag_tablet end to end: Claim wall (VI) dragged onto I
    tablet_rects = []
    for index in range(6):
        x, y, w, h = child_rect(child(window, 'Rank%d' % index), client, scale)
        tablet_rects.append((x, y, x + w, y + h))
    start = list(keeper_list)
    assert move_entry(start, 5, drop_slot(tablet_rects, (tablet_rects[0][0] + tablet_rects[0][2]) / 2,
                                          (tablet_rects[0][1] + tablet_rects[0][3]) / 2))
    assert start == [CLAIM_WALL, DIG, CARRY, CLEAN, RELOAD, CLAIM_GROUND]

# --- release note (Global Constraint 15)
notes = read('RELEASE-NOTES.md')
unreleased = notes[notes.index('### Unreleased'):]
following = unreleased.find('\n### ', 5)
if following >= 0:
    unreleased = unreleased[:following]
bullet = ('* Workers window (key J or the HUD button): set the fixed workers per job, the mode for free workers, the priority '
          'and carry order and "gold first"; every job shows its target and the workers on it.')
assert bullet in unreleased.splitlines(), 'release note is missing under "### Unreleased"'

print('workers window check ok')
