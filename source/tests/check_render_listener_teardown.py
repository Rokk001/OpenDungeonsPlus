"""Guard callback removal before their owners die; this does not prove a clean native exit."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(renderer, listener, application):
    """Require removal of all four callbacks while their Ogre registries still exist."""
    shutdown = body(renderer, 'RenderManager::~RenderManager(')
    assert 'mSceneManager->addListener(&ddd);' in renderer
    assert 'mRenderTarget->addListener(this);' in renderer
    assert shutdown.index('mSceneManager->removeListener(&ddd);') < shutdown.index('clearCreatureDecay(')
    assert 'if(mRenderTarget != nullptr)\n        mRenderTarget->removeListener(this);' in shutdown
    shutdown = body(listener, 'ODFrameListener::~ODFrameListener(')
    assert 'addRenderQueueListener(this);' in listener
    assert shutdown.index('removeRenderQueueListener(this);') < shutdown.index('exitApplication();')
    assert application.index('removeListener(sgListener);') < application.index('delete sgListener;')
    assert application.index('delete sgListener;') < application.index('Ogre::RTShader::ShaderGenerator::destroy();')


def main():
    """Reject removal of any of the four independent callback detachments."""
    sources = [(ROOT / path).read_text() for path in (
        'source/render/RenderManager.cpp', 'source/render/ODFrameListener.cpp', 'source/ODApplication.cpp')]
    verify(*sources)
    mutations = [(0, 'mSceneManager->removeListener(&ddd);'),
                 (0, 'mRenderTarget->removeListener(this);'),
                 (1, 'mRenderManager->getSceneManager()->removeRenderQueueListener(this);'),
                 (2, 'Ogre::MaterialManager::getSingleton().removeListener(sgListener);')]
    for index, removal in mutations:
        mutated = list(sources)
        assert removal in mutated[index]
        mutated[index] = mutated[index].replace(removal, ';', 1)
        try:
            verify(*mutated)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted dangling callback: ' + removal)
    print('render callback lifetime: four mutations rejected; native exit requires matching runtime')


if __name__ == '__main__':
    main()
