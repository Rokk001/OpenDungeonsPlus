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
             'WorkerCarryFrameNormal', 'WorkerCarryFrameSelected', 'WorkersHudNormal', 'WorkersHudHover', 'WorkersHudPressed'):
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

# --- HUD button (D9, D10)
hud = ET.parse(repo / 'gui/ModeGame.layout').getroot()
imports = [n.get('filename') for n in hud.iter('LayoutImport')]
assert 'WindowWorkers.layout' in imports
button = None
for node in hud.iter('Window'):
    if node.get('name') == 'WorkersButton':
        button = node
assert button is not None, 'HUD button WorkersButton is missing'
button_props = props(button)
assert button_props['TooltipText'] == 'Workers (J)'
assert button_props['Text'] == 'Workers'
assert button_props['NormalImage'] == 'OpenDungeonsIcons/WorkersHudNormal'
assert button_props['HoverImage'] == 'OpenDungeonsIcons/WorkersHudHover'
assert button_props['PushedImage'] == 'OpenDungeonsIcons/WorkersHudPressed'
button_area = udims(button_props['Area'])
assert button_area[1][0] == 1 and button_area[3][0] == 1, 'the button sits in the bottom bar'

# --- key J, help line, seat handling, Esc (D9, D10)
game = read('source/modes/GameMode.cpp')
assert re.search(r'case OIS::KC_J:\s*mWorkersWindow->toggle\(\);\s*break;', game), 'key J toggles the window'
for path in sorted((repo / 'source').rglob('*.cpp')):
    if path.name == 'GameMode.cpp':
        continue
    assert 'KC_J' not in path.read_text(encoding='utf-8', errors='replace'), 'key J is used elsewhere: ' + str(path)
assert game.count('OIS::KC_J') == 1
assert ('"  - J opens the workers window: fixed workers per job, free workers, priority and carry order."' in game)
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
assert code.count('WorkerJobSettings next = seat->getWorkerJobSettings();') >= 7
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
released = code[code.index('bool WorkersWindow::onTabletReleased'):code.index('bool WorkersWindow::onPriorityArrowClicked')]
assert 'next.freeMode != static_cast<uint32_t>(WorkerFreeMode::priority)' in released
refresh = code[code.index('void WorkersWindow::refresh()'):]
assert 'mSelectedJob = -1;' in refresh and 'WorkerArrow' in code and 'Disabled' in code
mode = code[code.index('bool WorkersWindow::onModeClicked'):code.index('int32_t WorkersWindow::getSlotId')]
assert 'mSelectedJob = -1;' in mode, 'a switch of the mode clears the selection'

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
