"""Check the painted icon atlas gui/ODIcons.png and the iron skin of gui/ODSkin.png.

Every icon named in the layouts must exist in the imageset inside the atlas, be opaque where it
has a body, and retain its own painted source motif. Frost, stone and creature emblems need
their approved material colours rather than the previous uniformly warm procedural palette.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

repo = Path(__file__).resolve().parents[2]
text = (repo / 'gui/ODIcons.imageset').read_text()
icon_images = ET.fromstring(text)
rects = {node.get('name'): tuple(int(node.get(key)) for key in ('xPos', 'yPos', 'width', 'height'))
         for node in icon_images.findall('Image')}
assert len(rects) == len(icon_images.findall('Image')), 'unique image names'
atlas = np.array(Image.open(repo / 'gui/ODIcons.png').convert('RGBA'), dtype=np.float32)
used = set()
for layout in (repo / 'gui').glob('*.layout'):
    used |= set(re.findall(r'OpenDungeonsIcons/([A-Za-z0-9_]+)', layout.read_text()))
runtime = {'GoldBadge', 'ManaBadge', 'NavHelp', 'NavSell', 'NavOptions', 'MapZoom', 'MiniMapRim', 'MiniMapNorth', 'CampaignMap'}
runtime |= {n for n in used if n.startswith('MiniMapCorner')}
for name in sorted(used - runtime):
    assert name in rects, 'missing in imageset: ' + name
for name in ('NavigationCreatures', 'NavigationRooms', 'NavigationSpells', 'NavigationWorkshop', 'NavigationPanel',
             'NavigationObjectives', 'NavigationMessages', 'NavigationMessagesRead', 'MenuReturn',
             'HourglassIcon', 'CogIcon', 'HammerAnvilIcon', 'PlayIcon', 'CameraIcon'):
    assert name in rects, name
# Every name has an emblem of its own: no two names may share a cell, and no two cells may hold the same pixels
# (the research tree and the HUD show one emblem per trap, door, spell and room).
cells = {}
for name, rect in rects.items():
    assert rect not in cells, '%s and %s share one cell of the atlas' % (name, cells[rect])
    cells[rect] = name
names = sorted(rects)
for i, first in enumerate(names):
    x, y, w, h = rects[first]
    for second in names[i + 1:]:
        x2, y2, w2, h2 = rects[second]
        if (w, h) == (w2, h2):
            assert np.abs(atlas[y:y + h, x:x + w] - atlas[y2:y2 + h, x2:x2 + w]).max() > 0, '%s and %s show the same picture' % (first, second)
checked = 0
for name, (x, y, w, h) in rects.items():
    assert x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= atlas.shape[1] and y + h <= atlas.shape[0], name
    tile = atlas[y:y + h, x:x + w]
    opaque = tile[..., 3] > 200
    assert opaque.sum() > w * h * 0.04, name + ' has no body'
    source_image = Image.open(repo / 'assets-src/gui/icons/tiles' / (name + '.png')).convert('RGBA')
    if source_image.size == (2 * w, 2 * h):
        # A cell that shows its painted source at half size (the ghost room button) holds the downscaled motif;
        # a wrong motif differs by tens of levels on average, the downscale by well under one.
        reduced = np.array(source_image.resize((w, h), Image.LANCZOS), dtype=np.float32)
        assert np.abs(reduced - tile).mean() < 2.0, name + ' does not contain its painted source motif'
    else:
        source = np.array(source_image)
        assert np.array_equal(tile, source), name + ' does not contain its painted source motif'
    checked += 1
# Large room/spell/trap slots retain square painted plates with visible central motifs. Small
# status emblems are isolated transparent sprites. Chipped edges replace procedural corners.
sys.path.insert(0, str(repo / 'tools'))
import forged_motifs as fm
squares = [n for n, spec in fm.ICONS.items() if spec['kind'] is not None and rects[n][2:] == (256, 256)]
assert len(squares) >= 36, len(squares)
for name in squares:
    x, y, w, h = rects[name]
    a = atlas[y:y + h, x:x + w, 3]
    assert (w, h) == (256, 256) and (a > 200).mean() > 0.6, name + ' has no painted square body'
    inner = atlas[y + h // 4:y + 3 * h // 4, x + w // 4:x + 3 * w // 4, :3]
    assert inner.std(axis=(0, 1)).max() > 12, name + ' has no motif in the tile'
skin = np.array(Image.open(repo / 'gui/ODSkin.png').convert('RGBA'), dtype=np.float32)
skin_set = (repo / 'gui/ODSkin.imageset').read_text()
skin_images = ET.fromstring(skin_set)
skin_rects = {node.get('name'): tuple(int(node.get(key)) for key in ('xPos', 'yPos', 'width', 'height'))
              for node in skin_images.findall('Image')}
x, y, w, h = skin_rects['ForgedBar']
bar = skin[y:y + h, x:x + w]
assert (bar[..., 3] > 200).mean() > 0.6 and bar[..., :3].std() > 2, 'painted iron bar has a textured body'
game = (repo / 'gui/ModeGame.layout').read_text()
assert game.count('OpenDungeonsSkin/ForgedBar') == 2 and 'FFB98B56' not in game
# The approved bar is a chipped painted iron edge, replacing the old repeated vent segments.
bar_source = Image.open(repo / 'assets-src/gui/skin/frame-0-0.png').convert('RGBA')
assert np.array_equal(bar, np.array(bar_source.crop((0, 0, 512, 88)).resize((w, h), Image.Resampling.LANCZOS)))
# Research tiles: material states instead of flat colour squares.
# Return the actual registered skin rectangle, independent of XML attribute order.
def tile(name):
    x, y, tw, th = skin_rects[name]
    return skin[y:y + th, x:x + tw]
locked, learned, working, queued, focus = (tile('ResearchTile' + n) for n in ('Locked', 'Learned', 'Working', 'Queued', 'Focus'))
for name, t in (('Locked', locked), ('Learned', learned), ('Working', working), ('Queued', queued)):
    opaque = t[..., 3] > 200
    assert opaque.any() and t[opaque][:, :3].std() > 2, 'research tile %s has no painted frame' % name
for i, first in enumerate((locked, learned, working, queued)):
    for second in (locked, learned, working, queued)[i + 1:]:
        assert not np.array_equal(first, second), 'research states need distinct painted frames'
assert focus[focus.shape[0] // 2, focus.shape[1] // 2, 3] < 40 and (focus[..., 3] > 200).any(), 'focus is a rim with a clear centre'
# Stretched centres now use seamless cracked stone instead of the old low-noise flat colour and gutter.
for name in ('StaticBackdrop', 'EditBoxMiddle', 'ComboboxEditBackground', 'MenuMiddle', 'MultiListMiddle', 'TooltipMiddle',
             'ComboboxListBackdrop', 'VerticalSliderMiddle', 'HorizontalSliderMiddle', 'TabContentPaneMiddle'):
    x, y, tw, th = skin_rects[name]
    inner = skin[y:y + th, x:x + tw, :3]
    assert inner.std() > 2, name + ' has no painted stone texture'
    assert np.array_equal(inner[0], inner[-1]) and np.array_equal(inner[:, 0], inner[:, -1]), name + ' has a centre-tile seam'
    assert skin[y:y + th, x:x + tw, 3].min() == 255, name + ' centre is not opaque'
# Layout and look'n'feel wiring of the states
look = (repo / 'gui/OD.looknfeel').read_text()
scheme = (repo / 'gui/ODSkin.scheme').read_text()
game_code = (repo / 'source/modes/GameMode.cpp').read_text()
assert 'ResearchBackgroundColour' not in look and 'ResearchBackgroundColour' not in game_code
for n in ('Locked', 'Learned', 'Working', 'Queued'):
    assert 'OpenDungeonsSkin/ResearchTile' + n in game_code, n
assert 'ResearchTileFocus' in look and 'OD/EventPanel' in scheme
for f in ('WindowGameEvent.layout', 'WindowEvent.layout'):
    assert 'type="OD/EventPanel" name="GameEventText"' in (repo / 'gui' / f).read_text(), f
sym = look[look.index('<WidgetLook name="OD/MenuSymbolButton"'):]
sym = sym[:sym.index('</WidgetLook>')]
assert all(s in sym for s in ('plate_normal', 'plate_hover', 'plate_pushed', 'ButtonTopLeftHighlight', 'ButtonTopLeftPushed')),     'symbol buttons sit on forged plates with hover and pressed'
tree = (repo / 'gui/WindowSkillTree.layout').read_text()
assert 'FrameColours' not in tree and 'SelectionBrush' not in tree, 'skill tree columns use no flat tints'
material = (repo / 'materials/scripts/SquareSelector.material').read_text()
assert 'material SquareSelector' in material and 'emissive 1.0 0.70' in material
assert 'setMaterialName("SquareSelector")' in (repo / 'source/render/RenderManager.cpp').read_text()
# Third pass: one symbol style for every close and confirm button, iron scrollbars and list frames in the menus, warm text.
for layout in (repo / 'gui').glob('*.layout'):
    body = layout.read_text()
    assert 'OpenDungeonsSkin/CloseButton' not in body, layout.name + ' still uses the old close button image with its own frame'
    for button in re.finditer(r'<Window type="OD/MenuSymbolButton"[^>]*>(.*?)</Window>', body, re.S):
        assert set(re.findall(r'OpenDungeonsSkin/', button[1])) == set(), layout.name + ': symbol buttons use icon atlas images'
# Return a shared widget look to check its frame and text bindings.
def look_block(name):
    a = look.index('<WidgetLook name="%s"' % name)
    end = look.find('</WidgetLook>', a)
    return look[a:] if end < 0 else look[a:end]
thumb = look_block('OD/MenuScrollbarThumb')
assert 'SelectionBrush' not in thumb and 'inherits="OD/VerticalScrollbarThumb"' in thumb, 'menu scrollbar thumb is the forged iron thumb'
for name in ('OD/MenuListbox', 'OD/MenuMultiColumnList'):
    block = look_block(name)
    assert 'section="main"' in block, name + ' has the forged inset frame'
assert 'FFE8DCC0' in look_block('OD/StaticText') and 'FFFFFFFF' not in look_block('OD/Tooltip').split('name="label"')[1].split('</TextComponent>')[0],     'labels and tooltips use the warm bone text colour'
for f in ('source/entities/Creature.cpp', 'source/entities/Tile.cpp', 'source/gamemap/GameMap.cpp', 'source/modes/GameMode.cpp',
          'source/network/ChatEventMessage.cpp'):
    code = (repo / f).read_text()
    assert 'CCBBBBFF' not in code and "colour='FFFFFFFF'" not in code, f + ' has a cold or hard white text colour'
print('FORGED ICONS OK: %d icons checked, %d square tiles' % (checked, len(squares)))
