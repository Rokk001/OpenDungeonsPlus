"""Guard retryable RTSS material creation without compiling or starting the engine.

This checks the failure branch and assignment ordering, not generated shaders or runtime cost.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source):
    """Require failed clones to leave both caches before an unchanged entity is returned."""
    helper = body(source, 'bool RenderManager::useShaderSkinning(')
    failure = body(helper, 'if(!mShaderGenerator->createShaderBasedTechnique(*copy,')
    cleanup = failure.index('mShaderGenerator->removeAllShaderBasedTechniques(*copy);')
    eviction = failure.index('Ogre::MaterialManager::getSingleton().remove(copy->getHandle());')
    assert cleanup < eviction < failure.index('return false;')
    assert 'setMaterial(' not in failure
    assert 'removeAllShaderBasedTechniques(*material)' not in helper
    assert 'remove(material->getHandle())' not in helper
    assert helper.index('if(!copy)') < helper.index('material->clone(copyName)')
    assert helper.index(failure) < helper.index('addTemplateSubRenderState(')
    assert helper.index('addTemplateSubRenderState(') < helper.index('setMaterial(skinned[index])')
    assert helper.index('setMaterial(skinned[index])') < helper.index('prepareEntityForSkinning(entity)')


def main():
    """Reject four cache/assignment regressions in the failed-creation path."""
    source = (ROOT / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
    verify(source)
    mutations = [
        ('mShaderGenerator->removeAllShaderBasedTechniques(*copy);', ';'),
        ('Ogre::MaterialManager::getSingleton().remove(copy->getHandle());', ';'),
        ('mShaderGenerator->removeAllShaderBasedTechniques(*copy);',
         'mShaderGenerator->removeAllShaderBasedTechniques(*material);'),
        ('Ogre::MaterialManager::getSingleton().remove(copy->getHandle());',
         'entity->getSubEntity(0)->setMaterial(copy);'),
    ]
    assert len(mutations) == 4
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    print('skinning copy retry: four mutations rejected; engine shader generation remains unverified')


if __name__ == '__main__':
    main()
