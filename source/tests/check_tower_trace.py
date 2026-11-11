"""Check the diagnostic patch without compiling or launching the renderer."""
from pathlib import Path
import argparse
import re
import runpy
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'scripts/win32/patches/ogre14-tower-trace.patch'
MAIN = 'OgreMain/src/OgreSceneManager.cpp'
HEADER = 'OgreMain/src/OgreODTowerTrace.h'


def verify(main, header):
    """Guard post-submission placement, isolation, bounded output and buffer reads."""
    body = main.split('void SceneManager::issueRenderWithLights(', 1)[1]
    assert body.index('_issueRenderOp(rend, pass);') < body.index('traceODTower(')
    assert main.count('traceODTower(') == 1
    assert 'std::getenv("OD_TOWER_TRACE")' in header
    assert 'path == nullptr || *path == \'\\0\'' in header
    assert header.index('if(mStopped || pass == nullptr)') < header.index('dynamic_cast<const SubEntity*>')
    assert 'getName() != "MenuGreenTower.mesh"' in header
    assert 'if(frame < 120)' in header and 'if(mFrames == 3)' in header
    assert 'if(mDraws == 4096)' in header
    assert all(word in header for word in ('COMPLETE frames=3', 'INCOMPLETE frames=', 'TRUNCATED draw_cap=4096'))
    assert 'const GpuProgramParameters& params' in header
    assert 'count > (params.getConstantList().size() - definition.physicalIndex) / width' in header
    for token in ('getFloatPointer', 'getDoublePointer', 'getIntPointer', 'getUnsignedIntPointer',
                  'getPreprocessorDefines', 'getSource()', 'getAutoConstantList', 'getMaterialName',
                  'getTextureName', 'getPowerScale', 'getAttenuationQuadric', 'getCurrentCamera'):
        assert token in header
    assert not re.search(r'^\s*auto\s+\w+\s*[=:]', header, re.MULTILINE)
    # Do not evaluate lazy source light getters, force auto updates, or alter a rendering value.
    for forbidden in ('source->getLight', '_updateAutoParams', 'setCurrent', 'setNamed',
                      'invalidateViewSpaceLights', 'getLightPositionViewSpaceArray'):
        assert forbidden not in header


def main():
    """Apply/reverse fixtures and optionally check the exact pinned source without modifying it."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ogre-source', type=Path)
    args = parser.parse_args()
    patch = PATCH.read_text()
    preimages = runpy.run_path(str(ROOT / 'source/tests/check_gl3plus_exact_uniform_cache.py'))['preimages']
    before = preimages(patch)[MAIN]
    if args.ogre_source:
        result = subprocess.run(['git', '-C', str(args.ogre_source), 'show',
                                 'f906880885f6014ca9b5bd8aaa09b399394d5676:' + MAIN],
                                capture_output=True, text=True, check=True)
        before = result.stdout
    with tempfile.TemporaryDirectory(prefix='tower-trace-') as temporary:
        fixture = Path(temporary)
        target = fixture / MAIN
        target.parent.mkdir(parents=True)
        target.write_text(before, newline='\n')
        for flags in ([], ['--recount']):
            subprocess.run(['git', 'apply', *flags, str(PATCH)], cwd=fixture, check=True,
                           capture_output=True, text=True)
            after = target.read_text()
            header = (fixture / HEADER).read_text()
            verify(after, header)
            mutations = [
                ('if(mDraws == 4096)', 'if(false)'),
                ('if(mFrames == 3)', 'if(false)'),
                ('getName() != "MenuGreenTower.mesh"', 'getName().empty()'),
                ('std::getenv("OD_TOWER_TRACE")', '"always-on.txt"'),
                ('const GpuProgramParameters& params', 'GpuProgramParameters& params'),
                ('getCurrentCamera()', 'getLightPositionViewSpaceArray(1)'),
            ]
            for old, new in mutations:
                assert old in header
                try:
                    verify(after, header.replace(old, new, 1))
                except AssertionError:
                    continue
                raise AssertionError('accepted trace regression: ' + old)
            wrong_order = after.replace('_issueRenderOp(rend, pass);', '', 1)
            wrong_order = wrong_order.replace('traceODTower(rend, pass, pLightListToUse, mAutoParamDataSource.get());',
                'traceODTower(rend, pass, pLightListToUse, mAutoParamDataSource.get());\n_issueRenderOp(rend, pass);', 1)
            try:
                verify(wrong_order, header)
            except AssertionError:
                pass
            else:
                raise AssertionError('accepted pre-update uniform snapshot')
            subprocess.run(['git', 'apply', *flags, '--reverse', str(PATCH)], cwd=fixture,
                           check=True, capture_output=True, text=True)
            assert target.read_text() == before and not (fixture / HEADER).exists()
    install = (ROOT / 'scripts/win32/install-ogre-prereq.ps1').read_text()
    assert 'apply --recount $taskTowerTracePatch' in install
    assert install.index('apply --recount $taskTowerTracePatch') < install.index('$taskPatchHashes = Get-OgrePrereqPatchHashes')
    assert PATCH.name in (ROOT / 'scripts/win32/ogre-prereq-provenance.ps1').read_text()
    print('tower trace: plain/recount apply and reverse; seven mutations rejected; compile/runtime deferred')


if __name__ == '__main__':
    main()
