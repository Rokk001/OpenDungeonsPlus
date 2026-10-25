"""Check that no window of the gui layouts is larger than the screen at any UI scale.

Gui::applyScale scales the absolute part of every window area with min(width / 1024, height / 768)
times the UI scale, so a tall window (for example the 700 high skill tree) grows beyond the screen at
120 percent or on a small screen. Gui::getWindowFitFactor limits the window (and its children) to the
screen size. This check reads the window sizes from the layout files, resolves relative areas against
the screen (a window is a layout window that sits in a container filling the whole screen), applies the
same formula as the code, including the limit if the code has it, and fails for every window that is
still larger than the screen at 640x480, 1024x768, 1920x1200 and 7680x4320 with UI scale 80 and 120 percent.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]
gui_cpp = (repo / 'source/render/Gui.cpp').read_text(encoding='utf-8', errors='replace')
has_fit = 'getWindowFitFactor' in gui_cpp and 'layoutScale * getWindowFitFactor(window)' in gui_cpp

DESIGN_W, DESIGN_H = 1024.0, 768.0
SCREENS = [(640, 480), (1024, 768), (1920, 1200), (7680, 4320)]
USER_SCALES = [0.8, 1.2]
NUMBER = r'(-?\d+(?:\.\d+)?)'
UDIM = r'\{' + NUMBER + ',' + NUMBER + r'\}'


def udims(value):
    """Return the (scale, offset) pairs of a CEGUI property value like {{0.5,-380},{0.5,350}}."""
    return [(float(a), float(b)) for a, b in re.findall(UDIM, value)]


def window_extent(element):
    """Return ((rel_w, off_w), (rel_h, off_h)) of a window from its Area or Size property, or None."""
    props = {p.get('name'): p.get('value') for p in element.findall('Property')}
    if 'Area' in props:
        v = udims(props['Area'])
        if len(v) == 4:
            return (v[2][0] - v[0][0], v[2][1] - v[0][1]), (v[3][0] - v[1][0], v[3][1] - v[1][1])
    if 'Size' in props:
        v = udims(props['Size'])
        if len(v) == 2:
            return v[0], v[1]
    return None


def fills_parent(element):
    """True if the window has the area {{0,0},{0,0},{1,0},{1,0}} (it is as large as its parent)."""
    for p in element.findall('Property'):
        if p.get('name') == 'Area':
            v = udims(p.get('value'))
            return v == [(0, 0), (0, 0), (1, 0), (1, 0)]
    return False


def collect(path, windows, seen):
    """Collect the windows of a layout file that sit directly in a screen-sized container.

    Windows that fill their parent completely and the imported layouts are walked through; the first
    window below them that does not fill the parent is a window to check, its children are not.
    """
    root = ET.parse(repo / 'gui' / path).getroot()
    for window in root.findall('Window'):
        walk(window, path, windows, seen)


def walk(window, path, windows, seen):
    """Check one window in a screen-sized container, or walk into it if it fills the container."""
    if fills_parent(window):
        for child in window:
            if child.tag == 'Window':
                walk(child, path, windows, seen)
            elif child.tag == 'LayoutImport':
                imported = child.get('filename')
                if imported not in seen and (repo / 'gui' / imported).exists():
                    collect(imported, windows, seen | {imported})
        return
    extent = window_extent(window)
    if extent is not None:
        windows.append((path, window.get('name'), extent))


def fit_factor(extent, screen_w, screen_h, scale):
    """The factor of Gui::getWindowFitFactor, 1.0 if the code has no limit."""
    if not has_fit:
        return 1.0
    (rel_w, off_w), (rel_h, off_h) = extent
    factor = 1.0
    if off_w * scale > 0 and rel_w < 1.0:
        factor = min(factor, max(0.0, (1.0 - rel_w) * screen_w) / (off_w * scale))
    if off_h * scale > 0 and rel_h < 1.0:
        factor = min(factor, max(0.0, (1.0 - rel_h) * screen_h) / (off_h * scale))
    return factor


windows = []
for layout in sorted((repo / 'gui').glob('*.layout')):
    collect(layout.name, windows, {layout.name})
# The same window can be reached through several layouts (imports); report it once
windows = sorted(set((p, n, e) for p, n, e in windows))
assert windows, 'no windows found in the layouts'

# The existing Game/Editor quit confirmation stays centred and uses the opaque reskin panel.
quit_window = ET.parse(repo / 'gui' / 'WindowQuit.layout').getroot().find('Window')
quit_properties = {p.get('name'): p.get('value') for p in quit_window.findall('Property')}
quit_area = udims(quit_properties['Area'])
assert quit_window.get('type') == 'OD/FrameWindow'
assert float(quit_properties['Alpha']) == 1.0, 'quit confirmation must be opaque'
assert len(quit_area) == 4
assert all(abs(quit_area[axis][0] + quit_area[axis + 2][0] - 1.0) < 0.00001
           and quit_area[axis][1] == -quit_area[axis + 2][1] for axis in (0, 1)), 'quit confirmation must be centred'
assert {child.get('name') for child in quit_window.findall('Window')} == {'YesOption', 'NoOption', 'SaveReplayCheckbox'}

too_large = []
for screen_w, screen_h in SCREENS:
    for user_scale in USER_SCALES:
        scale = min(screen_w / DESIGN_W, screen_h / DESIGN_H) * user_scale
        for path, name, ((rel_w, off_w), (rel_h, off_h)) in windows:
            eff = scale * fit_factor(((rel_w, off_w), (rel_h, off_h)), screen_w, screen_h, scale)
            width = rel_w * screen_w + off_w * eff
            height = rel_h * screen_h + off_h * eff
            # A window as large as the screen plus a few pixels (relative size 1) is a deliberate bleed
            too_wide = width > screen_w + 0.5 and rel_w < 1.0
            too_high = height > screen_h + 0.5 and rel_h < 1.0
            if too_wide or too_high:
                too_large.append('%s %s: %.0fx%.0f on %dx%d at %d%%' % (
                    path, name, width, height, screen_w, screen_h, round(user_scale * 100)))

for line in too_large:
    print('larger than the screen:', line)
assert has_fit, 'Gui.cpp does not limit windows to the screen (getWindowFitFactor is missing)'
assert not too_large, '%d window sizes are larger than the screen' % len(too_large)
print('window fit screen check ok (%d windows, %d screen/scale combinations)' % (
    len(windows), len(SCREENS) * len(USER_SCALES)))

# Shared reskin title/close sizing and framed content must use the same usable rectangle.
skin = ET.parse(repo / 'gui/OD.looknfeel').getroot()
frame = skin.find("WidgetLook[@name='OD/FrameWindow']")
assert frame.find("PropertyLinkDefinition[@name='TitlebarFont']").get('initialValue') == 'MedievalSharp-10'
client = frame.find("NamedArea[@name='ClientWithTitleWithFrame']/Area")
assert len(client.findall('Dim')) == 4, 'frame contents need a clipped inner rectangle'
close = frame.find("Child[@nameSuffix='__auto_closebutton__']/Area")
for dimension in ('Width', 'Height'):
    node = close.find("Dim[@type='%s']/WidgetDim" % dimension)
    assert node is not None and node.get('widget') == '__auto_titlebar__' and node.get('dimension') == 'Height'
listbox = skin.find("WidgetLook[@name='OD/Listbox']")
for name in ('ItemRenderingArea', 'ItemRenderingAreaHScroll', 'ItemRenderingAreaVScroll', 'ItemRenderingAreaHVScroll'):
    for edge in ('LeftEdge', 'TopEdge'):
        dim = listbox.find("NamedArea[@name='%s']/Area/Dim[@type='%s']" % (name, edge))
        assert len(dim) == 1 and len(dim[0]) == 2, 'the frame and list padding must be summed inside one operator'
hud = ET.parse(repo / 'gui/ModeGame.layout').getroot()
assert hud.find(".//Window[@name='ObjectivesButton']") is None, 'the duplicate eye button is removed'
assert hud.find(".//Window[@name='GoalsButton']") is not None, 'the scroll goals button remains'
assert 'guiSheet->getChild("ObjectivesButton")' not in (repo / 'source/modes/GameMode.cpp').read_text()
notice = ET.parse(repo / 'gui/WindowGameEvent.layout').getroot().find('Window')
message = udims(notice.find("Window[@name='Message']/Property[@name='Area']").get('value'))
assert abs(message[0][0] - (1 - message[2][0])) < 1e-9, 'message margins are equal'
notice_extent = window_extent(notice)
notice_height = notice_extent[1][1]
atlas = ET.parse(repo / 'gui/ODSkin.imageset').getroot()
border_height = float(atlas.find("Image[@name='WindowTopEdge']").get('height')) / 4
for name in ('Message', 'Dismiss', 'Close'):
    area = udims(notice.find("Window[@name='%s']/Property[@name='Area']" % name).get('value'))
    # Derive the content bounds from the existing scaled atlas border and actual panel height.
    assert area[1][0] * notice_height >= border_height and area[3][0] * notice_height <= notice_height - border_height, name
print('shared title, close button, list insets, event field and single goals entry verified')
