from pathlib import Path
import math
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
layout = ET.parse(root / 'gui/ModeEditor.layout').getroot()
editor = layout.find('Window')
bar = editor.find("Window[@name='MainTabControl']")
assert bar.find("Property[@name='Area']").get('value') == '{{0,0},{1,-133},{1,-200},{1,0}}'
assert bar.find("Property[@name='TabHeight']").get('value') == '{0,35}'
source = (root / 'source/render/Gui.cpp').read_text(encoding='utf-8')
assert 'arrangeEditorActionButtons(editorSheet->second)' in source
assert '(buttons.size() + 1) / 2' in source
assert '(width - 8.0f) / static_cast<float>(columns) - 4.0f' in source
assert '(height - 12.0f) / 2.0f' in source
for page, expected in [('Rooms', 27), ('Traps', 18), ('Spells', 18)]:
    node = ET.parse(root / ('gui/WindowTab' + page + '.layout')).getroot().find('Window')
    buttons = [child for child in node.findall('Window') if child.get('type') == 'OD/GameTabButton']
    assert len(buttons) == expected
    for w, h in [(640, 480), (1920, 1200), (7680, 4320)]:
        for user in (0.8, 1.0, 1.2):
            scale = min(w / 1024, h / 768) * user
            width, height = (w - 200 * scale) / scale, 133 - 35
            columns = (expected + 1) // 2
            side = max(0, min(52, (width - 8) / columns - 4, (height - 12) / 2))
            assert side > 0
            rects = [(4 + (i // 2) * (side + 4), 4 + (i % 2) * (side + 4)) for i in range(expected)]
            for x, y in rects:
                assert x >= 0 and y >= 0 and x + side <= width and y + side <= height
            assert len(set(rects)) == expected
pipe = editor.find("Window[@name='HorizontalPipe']")
gold = pipe.find("Window[@name='GoldDensityDisplay']")
assert pipe.find("Property[@name='Area']").get('value') == '{{0,0},{1,-143},{1,0},{1,-133}}'
assert gold.find("Property[@name='Area']").get('value') == '{{0,210},{0,-3.5},{0,405},{0,28.5}}'
assert gold.find("Property[@name='MaxSize']") is None
assert gold.find("Property[@name='VerticalAlignment']").get('value') == 'Centre'
for scale in (0.8, 1.0, 1.2):
    # CEGUI centres the 32-pixel label in the 10-pixel bar, then applies its offset.
    top = (10 * scale - 32 * scale) / 2 - 3.5 * scale
    assert math.isclose(top / scale, -14.5)
    assert math.isclose((top + 16 * scale) / scale, 1.5)
print('Editor construction positions and gold label scaling: OK')
