"""Check that the shadow texture pass visits only shadow casters, without compiling or starting a game.

Removed cause: shadows (17.72% of the P1 frame in build 52; the shadow camera's scene traversal alone
took 10.78%, the shadow draws 4.59%). Ogre's traversal processes every shadow receiver in that pass,
mostly the terrain tiles, only to collect receiver bounds. ShadowCasterSceneManager hands only casters
to the render queue. This check verifies the source contract, that the game reads none of the skipped
bounds, models Ogre's per-object rule on fixed fixtures and rejects source regressions. The runtime
saving still needs the release build.
"""
from pathlib import Path
import itertools
import os
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source, header, render, cmake):
    """Require Ogre's path for normal views, the caster-only shadow traversal and its registration."""
    find = body(source, 'void ShadowCasterSceneManager::_findVisibleObjects(')
    assert find.index('if(!onlyShadowCasters)') < find.index(
        'Ogre::SceneManager::_findVisibleObjects(cam, visibleBounds, onlyShadowCasters);') < find.index('return;')
    assert 'findShadowCasters(getRootSceneNode(), cam, visibleBounds);' in find
    visit = body(source, 'void ShadowCasterSceneManager::findShadowCasters(')
    cull = 'if(!cam->isVisible(node->_getWorldAABB()))\n        return;'
    assert visit.index(cull) < visit.index('node->getAttachedObjects()')
    guard = 'if(object->getCastShadows())\n            queue->processVisibleObject(object, cam, true, visibleBounds);'
    assert guard in visit
    assert visit.count('queue->processVisibleObject(') == 1
    assert 'findShadowCasters(static_cast<Ogre::SceneNode*>(child), cam, visibleBounds);' in visit
    assert visit.index('node->getChildren()') < visit.index('getDebugDrawer()->drawSceneNode(node);')
    assert 'const Ogre::String ShadowCasterSceneManager::TYPE_NAME = "ShadowCasterSceneManager";' in source
    assert 'return OGRE_NEW ShadowCasterSceneManager(instanceName);' in source
    assert 'return ShadowCasterSceneManager::TYPE_NAME;' in source
    registration = body(source, 'const Ogre::String& ShadowCasterSceneManager::registerFactory(')
    assert 'static ShadowCasterSceneManagerFactory factory;' in registration
    assert registration.index('if(!registered)') < registration.index('addSceneManagerFactory(&factory);')
    assert 'removeSceneManagerFactory' not in source
    assert 'class ShadowCasterSceneManager : public Ogre::SceneManager' in header
    assert 'bool onlyShadowCasters) override;' in header
    assert 'createSceneManager(ShadowCasterSceneManager::registerFactory(), "SceneManager")' in render
    assert '#include "render/ShadowCasterSceneManager.h"' in render
    assert '${SRC}/render/ShadowCasterSceneManager.cpp' in cmake


def check_consumers():
    """The skipped receiver bounds have no reader: no depth range parameter and only the ground setup."""
    readers = []
    for folder, pattern in (('materials', '*.material'), ('shaders', '*'), ('source', '*.cpp'), ('source', '*.h')):
        for path in (ROOT / folder).rglob(pattern):
            if 'tests' in path.parts or not path.is_file():
                continue
            text = path.read_text(encoding='utf-8', errors='replace')
            for token in ('scene_depth_range', 'getVisibleObjectsBoundsInfo', 'getShadowCasterBoundsInfo',
                          'FocusedShadowCameraSetup', 'PSSMShadowCameraSetup', 'new Ogre::LiSPSMShadowCameraSetup'):
                if token in text:
                    readers.append((path.name, token))
    assert not readers, readers
    render = (ROOT / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
    assert render.count('setShadowCameraSetup(') == 1
    assert 'setShadowCameraSetup(Ogre::ShadowCameraSetupPtr(new GroundShadowCameraSetup()));' in render
    ground = (ROOT / 'source/render/GroundShadowCameraSetup.h').read_text(encoding='utf-8')
    assert 'Ogre::PlaneOptimalShadowCameraSetup setup(&mGroundPlane);' in ground
    assert 'VisibleObjectsBoundsInfo' not in ground


def ogre_process(cast, receive, visible):
    """Model of Ogre 14's RenderQueue::processVisibleObject in the shadow texture pass."""
    if not cast and not receive:
        return False, None
    if not visible:
        return False, None
    if cast:
        return True, 'caster'
    return False, 'receiver'


def game_process(cast, receive, visible):
    """Model of ShadowCasterSceneManager: non-casters never reach processVisibleObject."""
    if not cast:
        return False, None
    return ogre_process(cast, receive, visible)


def check_model():
    """Queued objects and caster bounds are identical; only receiver-only bounds are no longer collected."""
    fixtures = 0
    for cast, receive, visible in itertools.product((False, True), repeat=3):
        ogre_queued, ogre_bounds = ogre_process(cast, receive, visible)
        game_queued, game_bounds = game_process(cast, receive, visible)
        assert ogre_queued == game_queued
        assert game_bounds == (ogre_bounds if ogre_bounds != 'receiver' else None)
        fixtures += 1
    assert fixtures == 8
    return fixtures


def check_pinned_ogre():
    """When the pinned Ogre source is present, confirm the modelled rule against it."""
    deps = Path(os.environ.get('BUILD_DEPS_ROOT', Path(os.environ.get('USERPROFILE', '')) / 'build-deps'))
    queue = deps / 'src/ogre/OgreMain/src/OgreRenderQueue.cpp'
    if not queue.is_file():
        return 'pinned Ogre source absent, model only'
    text = queue.read_text(encoding='utf-8', errors='replace')
    start = text.index('void RenderQueue::processVisibleObject(')
    process = text[start:text.index('\n    }\n', start)]
    assert 'if(onlyShadowCasters && !mo->getCastShadows() && !receiveShadows)\n            return;' in process
    assert 'if (!onlyShadowCasters || mo->getCastShadows())' in process
    assert 'mo->_updateRenderQueue(this);' in process
    tail = process[process.index('else if (receiveShadows)'):]
    assert 'visibleBounds->mergeNonRenderedButInFrustum(bbox, bsphere, cam);' in tail
    assert '_updateRenderQueue' not in tail
    node = (deps / 'src/ogre/OgreMain/src/OgreSceneNode.cpp').read_text(encoding='utf-8', errors='replace')
    assert 'if (!cam->isVisible(mWorldAABB))' in node and 'getDebugDrawer()->drawSceneNode(this);' in node
    return 'pinned Ogre source confirmed'


def main():
    """Run the source, consumer, model and Ogre checks and reject six source regressions."""
    source = (ROOT / 'source/render/ShadowCasterSceneManager.cpp').read_text(encoding='utf-8')
    header = (ROOT / 'source/render/ShadowCasterSceneManager.h').read_text(encoding='utf-8')
    render = (ROOT / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
    cmake = (ROOT / 'CMakeLists.txt').read_text(encoding='utf-8')
    verify(source, header, render, cmake)
    check_consumers()
    fixtures = check_model()
    ogre = check_pinned_ogre()
    mutations = [
        ('if(object->getCastShadows())\n            queue', 'if(true)\n            queue'),
        ('findShadowCasters(getRootSceneNode(), cam, visibleBounds);',
         'Ogre::SceneManager::_findVisibleObjects(cam, visibleBounds, false);'),
        ('    if(!cam->isVisible(node->_getWorldAABB()))\n        return;\n', ''),
        ('findShadowCasters(static_cast<Ogre::SceneNode*>(child), cam, visibleBounds);', ';'),
        ('static ShadowCasterSceneManagerFactory factory;', 'ShadowCasterSceneManagerFactory factory;'),
        ('queue->processVisibleObject(object, cam, true, visibleBounds);',
         'queue->processVisibleObject(object, cam, false, visibleBounds);'),
    ]
    for old, new in mutations:
        assert old in source, old
        try:
            verify(source.replace(old, new), header, render, cmake)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('regression accepted: ' + old)
    assert len(mutations) == 6
    try:
        verify(source, header, render.replace('ShadowCasterSceneManager::registerFactory()', '"DefaultSceneManager"'), cmake)
    except AssertionError:
        pass
    else:
        raise AssertionError('regression accepted: default scene manager')
    print(f'check_shadow_caster_pass ok: {fixtures} object fixtures, {ogre}, {len(mutations) + 1} rejected '
          'mutations; runtime shadow saving unverified')


if __name__ == '__main__':
    main()
