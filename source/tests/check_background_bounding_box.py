"""Check that the bounding box of the background node is not drawn. It does not start a game.

The camera manager switched on the bounding box of the "Background" scene node. Its box is set to +-100000 units,
far beyond the far clip distance of the game camera (300), so it was never seen, but the debug drawer rebuilt
its lines and waited for the GPU on their buffer in every frame. No scene node may show its bounding box.
The background itself (rectangle, material, render queue and box size) stays as it was.
"""
from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[2]
manager = (repo / 'source/camera/CameraManager.cpp').read_text(encoding='utf-8')

source_files = sorted(list((repo / 'source').rglob('*.cpp')) + list((repo / 'source').rglob('*.h')))
shown = []
for path in source_files:
    if 'tests' in path.relative_to(repo / 'source').parts:
        continue
    text = path.read_text(encoding='utf-8', errors='replace')
    if 'showBoundingBox(true)' in text or 'setShowBoundingBoxes(true)' in text:
        shown.append(str(path.relative_to(repo)))
assert shown == [], 'bounding boxes are switched on in %s' % shown

assert manager.count('createChildSceneNode("Background")') == 1, 'the background node is missing'
assert 'node->attachObject(rect);' in manager, 'the background rectangle is not attached'
assert 'rect->setMaterial(mat);' in manager, 'the background material changed'
assert 'rect->setRenderQueueGroup(Ogre::RenderQueueGroupID::RENDER_QUEUE_SKIES_EARLY);' in manager
assert 'Ogre::AxisAlignedBox(-100000.0*Ogre::Vector3::UNIT_SCALE, 100000.0*Ogre::Vector3::UNIT_SCALE)' in manager
assert 'createCamera("RTS", 0.02, 300.0);' in manager, 'the far clip distance of the game camera changed'

print('background bounding box ok: not shown, background unchanged')
sys.exit(0)
