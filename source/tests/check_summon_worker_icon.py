"""Check the summon worker icon: shared binding and the painted worker source in its doubled atlas slot."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

repo = Path(__file__).resolve().parents[2]
gui = (repo / 'source/render/Gui.cpp').read_text()
game = (repo / 'source/modes/GameMode.cpp').read_text()


# Return a complete function body to check the existing spell-image binding.
def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


refresh = function(game, 'void GameMode::refreshSkillButtonState(')
assert 'getCreatureHandIconImage' not in refresh
assert 'getWorkerClassToSpawn' not in refresh
assert 'mRootWindow->getChild(button)->getProperty("NormalImage")' in game
for filename, prop in [('WindowTabSpells.layout', 'NormalImage'), ('WindowSkillTree.layout', 'ButtonImage')]:
    button = ET.parse(repo / 'gui' / filename).find('.//Window[@name="SummonWorkerButton"]')
    assert button.find(f'Property[@name="{prop}"]').get('value') == 'OpenDungeonsIcons/SummonWorkerButton'
assert 'createSummonWorkerIcon' not in gui and 'colourNavigationAtlas' not in gui
images = ET.parse(repo / 'gui/ODIcons.imageset').findall('Image[@name="SummonWorkerButton"]')
assert len(images) == 1, 'one registered summon worker icon'
x, y, w, h = (int(images[0].get(key)) for key in ('xPos', 'yPos', 'width', 'height'))
tile = np.array(Image.open(repo / 'gui/ODIcons.png').convert('RGBA'), dtype=np.float32)[y:y + h, x:x + w]
opaque = tile[..., 3] > 200
assert (x, y, w, h) == (1536, 1280, 256, 256), 'same logical slot at double source resolution'
assert opaque.sum() > 0.6 * w * h, 'painted worker tile has a visible body'
source = np.array(Image.open(repo / 'assets-src/gui/icons/tiles/SummonWorkerButton.png').convert('RGBA'))
assert np.array_equal(tile, source), 'registered slot contains the painted worker, not a different emblem'
centre = tile[h // 4:3 * h // 4, w // 4:3 * w // 4, :3]
assert centre.std(axis=(0, 1)).max() > 12, 'worker motif remains visible at the centre'
print('SUMMON ICON OK')
