"""Guard pointer alignment without software vertex uploads in an inactive window.

The CPU skeleton must still supply the current fingertip and tool transforms.
This source check does not establish native bone parity or runtime stall removal.
"""
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parents[2]
block = runpy.run_path(str(ROOT / 'source/tests/check_minimap_inactive_window_upload.py'))['block']


def verify(source):
    """Require both upload guards and the CPU pose before each alignment query."""
    assert '#include <OgreRenderWindow.h>' in source
    source = re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S)
    body = block(source, 'void alignKeeperHandPointer(')[0]
    assert 'const Ogre::RenderWindow* window = ODFrameListener::getSingleton().getRenderWindow();' in body
    assert 'const bool windowDrawn = window == nullptr || window->isActive();' in body
    assert body.count('hand->_updateAnimation();') == 2
    assert body.count('if(windowDrawn)\n            hand->_updateAnimation();') == 1
    assert body.count('if(windowDrawn)\n        hand->_updateAnimation();') == 1
    tool = block(body, 'if(tool != nullptr)')[0]
    assert tool.index('skeleton->reset();') < tool.index('pose->apply(skeleton, 0);')
    assert tool.index('pose->apply(skeleton, 0);') < tool.index('skeleton->_updateTransforms();')
    assert tool.index('skeleton->_updateTransforms();') < tool.index('grip->_getFullLocalTransform() * point;')
    assert tool.index('model->setPosition(') < tool.index('skeleton->setAnimationState(*hand->getAllAnimationStates());')
    assert tool.index('skeleton->setAnimationState(') < tool.rindex('skeleton->_updateTransforms();')
    assert tool.rindex('skeleton->_updateTransforms();') < tool.index('if(windowDrawn)')
    fallback = block(body, 'else\n    {')[0]
    assert fallback.strip() == 'hand->_updateSkeleton();\n        hand->getSkeleton()->_updateTransforms();'
    assert body.index('hand->_updateSkeleton();') < body.index('getBone("Index3")')
    assert 'const Ogre::Vector3 tipLocal(-0.000284253f, 0.0155774f, 0.000218656f);' in body
    assert 'index->_getDerivedOrientation() * (index->_getDerivedScale() * tipLocal)' in body
    assert 'model->setPosition(-(model->getOrientation() * tip) * weight);' in body
    assert 'model->setPosition(-(model->getOrientation() * (model->getScale() * face)));' in body
    assert body.count('return;') == 2, 'do not skip pointer alignment while inactive'


def main():
    """Check the alignment contract and reject eight independently broken variants."""
    source = (ROOT / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
    verify(source)
    mutations = (
        ('window == nullptr || window->isActive()', 'true'),
        ('window == nullptr || window->isActive()', 'window == nullptr || window->isVisible()'),
        ('if(windowDrawn)\n            hand->_updateAnimation();', 'hand->_updateAnimation();'),
        ('if(windowDrawn)\n        hand->_updateAnimation();', 'hand->_updateAnimation();'),
        ('hand->_updateSkeleton();', ';'),
        ('hand->getSkeleton()->_updateTransforms();', ';'),
        ('skeleton->setAnimationState(*hand->getAllAnimationStates());', ';'),
        ('const bool windowDrawn =', 'if(!window->isActive()) return;\n    const bool windowDrawn ='),
    )
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    print('hand inactive window: both uploads gated, CPU pointer/tool poses retained, 8 mutations rejected')


if __name__ == '__main__':
    main()
