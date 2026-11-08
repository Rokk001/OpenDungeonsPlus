"""Check GL3Plus program-cache teardown ordering without compiling Ogre."""
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'scripts/win32/patches/ogre14-gl3plus-program-shutdown.patch'
INSTALL = ROOT / 'scripts/win32/install-ogre-prereq.ps1'
PROVENANCE = ROOT / 'scripts/win32/ogre-prereq-provenance.ps1'
SOURCE = Path('RenderSystems/GL3Plus/src/OgreGL3PlusRenderSystem.cpp')
FIXTURE = """namespace Ogre {
    void GL3PlusRenderSystem::shutdown(void)
    {
        RenderSystem::shutdown();

        // Remove from manager safely
    }
}
"""


def verify(source):
    """Require guarded cache destruction before any render targets are shut down."""
    body = source.split('void GL3PlusRenderSystem::shutdown(void)', 1)[1].split(
        '// Remove from manager safely', 1)[0]
    expected = ('if (mProgramManager)\n'
                '            mProgramManager->destroyAllPrograms();\n\n'
                '        RenderSystem::shutdown();')
    comment = '//! Releases cached programs while the manager and GL context are still alive.\n    void GL3PlusRenderSystem::shutdown(void)'
    return comment in source and body.count('destroyAllPrograms()') == 1 and expected in body


def main():
    """Apply the patch to a source fixture and reject unsafe ordering mutations."""
    patch = PATCH.read_text(encoding='utf-8')
    name = PATCH.name
    install = INSTALL.read_text(encoding='utf-8')
    provenance = PROVENANCE.read_text(encoding='utf-8')
    assert name in provenance
    assert 'patches/' + name in install
    assert 'apply --recount --reverse --check $taskProgramShutdownPatch' in install
    assert 'apply --recount $taskProgramShutdownPatch' in install
    assert install.index('apply --recount $taskProgramShutdownPatch') < install.index('$taskPatchHashes = Get-OgrePrereqPatchHashes')
    with tempfile.TemporaryDirectory(prefix='ogre-shutdown-') as temporary:
        fixture = Path(temporary)
        target = fixture / SOURCE
        target.parent.mkdir(parents=True)
        target.write_text(FIXTURE, encoding='utf-8')
        assert not verify(FIXTURE)
        result = subprocess.run(['git', 'apply', str(PATCH)], cwd=fixture,
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        fixed = target.read_text(encoding='utf-8')
        assert verify(fixed)
        block = ('if (mProgramManager)\n'
                 '            mProgramManager->destroyAllPrograms();\n\n'
                 '        RenderSystem::shutdown();')
        mutations = [
            fixed.replace('//! Releases cached programs while the manager and GL context are still alive.\n    ', ''),
            fixed.replace('mProgramManager->destroyAllPrograms();', ''),
            fixed.replace('if (mProgramManager)', 'if (!mProgramManager)'),
            fixed.replace('if (mProgramManager)\n            ', ''),
            fixed.replace(block, 'RenderSystem::shutdown();\n        if (mProgramManager)\n            mProgramManager->destroyAllPrograms();'),
            fixed.replace('mProgramManager->destroyAllPrograms();', 'mProgramManager->destroyAllPrograms();\n            mProgramManager->destroyAllPrograms();'),
        ]
        assert all(not verify(candidate) for candidate in mutations)
        reverse = subprocess.run(['git', 'apply', '--reverse', '--check', str(PATCH)],
                                 cwd=fixture, capture_output=True, text=True)
        assert reverse.returncode == 0, reverse.stderr
    print('GL3Plus shutdown patch: fixture applied and six unsafe mutations rejected')


if __name__ == '__main__':
    main()
