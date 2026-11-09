"""Check the fix of the particle billboard buffer wait. It does not start a game.

Cause 2 of the slow frames: BillboardParticleRenderer::_updateRenderQueue -> BillboardSet::beginBillboards ->
HardwareBuffer::lock waited for the GPU in every frame (17 % of the menu frame, GPU 3D engine only 16 to 18 % busy).
OGRE already locks the dynamic billboard buffer with HBL_DISCARD, but GL3PlusHardwareBuffer::lockImpl orphans the
buffer with glBufferData(NULL) and then maps it synchronised, and the Intel Arc driver waits anyway. The fix is an
OGRE patch that maps the orphaned storage with GL_MAP_UNSYNCHRONIZED_BIT. The look is the same: the same bytes
reach the GPU, only the wait is gone. The patch is applied by install-ogre-prereq.ps1 and needs a rebuild of OGRE.
"""
from pathlib import Path
import base64
import hashlib
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
patch_path = repo / 'scripts/win32/patches/ogre14-discard-lock-unsynchronized.patch'
install = (repo / 'scripts/win32/install-ogre-prereq.ps1').read_text(encoding='utf-8')
fixture = base64.b64decode((repo / 'source/tests/fixtures/ogre/OgreGL3PlusHardwareBuffer.cpp.b64').read_bytes())

# This fixed upstream file and expected result bind the test to the validated OGRE revision.
assert hashlib.sha256(fixture).hexdigest() == '5d7008cc6c339ecbe4a960a373d800d0b196b34702eb277efdb35ed5b0b559c4'
old = b"""            if(options == HBL_DISCARD)
                OGRE_CHECK_GL_ERROR(glBufferData(mTarget, mSizeInBytes, NULL, getGLUsage(mUsage)));
""" + b" \n" + b"""            access |= GL_MAP_WRITE_BIT;
"""
new = b"""            if(options == HBL_DISCARD)
            {
                OGRE_CHECK_GL_ERROR(glBufferData(mTarget, mSizeInBytes, NULL, getGLUsage(mUsage)));
                // The storage was just orphaned: no queued command reads it, so no wait is needed
                access |= GL_MAP_UNSYNCHRONIZED_BIT;
            }

            access |= GL_MAP_WRITE_BIT;
"""
assert fixture.count(old) == 1
expected = fixture.replace(old, new, 1)
assert hashlib.sha256(expected).hexdigest() == 'af23bfbc9b53a78048dd5cf6fbcf31aa6b20a48725d92a419b7df9f867165d6a'

# Exercise both common checkout line-ending configurations using the installer options.
patch = patch_path.read_bytes()
assert patch.count(b'diff --git ') == 1
assert patch.startswith(b'diff --git a/RenderSystems/GL3Plus/src/OgreGL3PlusHardwareBuffer.cpp b/RenderSystems/GL3Plus/src/OgreGL3PlusHardwareBuffer.cpp\n')
for autocrlf in ('false', 'true'):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / 'RenderSystems/GL3Plus/src/OgreGL3PlusHardwareBuffer.cpp'
        target.parent.mkdir(parents=True)
        line_ending = b'\r\n' if autocrlf == 'true' else b'\n'
        original = fixture.replace(b'\n', line_ending)
        patched = expected.replace(b'\n', line_ending)
        target.write_bytes(original)
        def apply(*args):
            """Run the same Git apply options as the prerequisite installer."""
            subprocess.run(['git', '-c', 'core.autocrlf=' + autocrlf, 'apply', '--recount', *args, str(patch_path)], cwd=root, check=True)
        apply('--check')
        apply()
        assert target.read_bytes() == patched, 'only the intended discard branch may change'
        apply('--reverse', '--check')
        apply('--reverse')
        assert target.read_bytes() == original, 'reverse must reproduce the upstream file byte for byte'

# the install script applies it like the other OGRE patches
assert "patches/ogre14-discard-lock-unsynchronized.patch" in install
assert 'apply --recount --reverse --check $taskDiscardLockPatch' in install
assert 'apply --recount $taskDiscardLockPatch' in install
assert install.index('$taskDiscardLockPatch') < install.index('$taskOptions'), 'the patch must be applied before OGRE is configured and built'

# the particle scripts and the game code are not part of this cause: the look stays as it is
assert 'billboard_type' in (repo / 'particles/MenuScene.particle').read_text(encoding='utf-8')
print('ok')
