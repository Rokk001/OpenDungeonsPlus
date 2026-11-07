"""Check the fix of the particle billboard buffer wait. It does not start a game.

Cause 2 of the slow frames: BillboardParticleRenderer::_updateRenderQueue -> BillboardSet::beginBillboards ->
HardwareBuffer::lock waited for the GPU in every frame (17 % of the menu frame, GPU 3D engine only 16 to 18 % busy).
OGRE already locks the dynamic billboard buffer with HBL_DISCARD, but GL3PlusHardwareBuffer::lockImpl orphans the
buffer with glBufferData(NULL) and then maps it synchronised, and the Intel Arc driver waits anyway. The fix is an
OGRE patch that maps the orphaned storage with GL_MAP_UNSYNCHRONIZED_BIT. The look is the same: the same bytes
reach the GPU, only the wait is gone. The patch is applied by install-ogre-prereq.ps1 and needs a rebuild of OGRE.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
patch = (repo / 'scripts/win32/patches/ogre14-discard-lock-unsynchronized.patch').read_text(encoding='utf-8')
install = (repo / 'scripts/win32/install-ogre-prereq.ps1').read_text(encoding='utf-8')

diff = patch[patch.index('diff --git'):]
assert diff.count('diff --git') == 1 and 'RenderSystems/GL3Plus/src/OgreGL3PlusHardwareBuffer.cpp' in diff
added = [line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')]
removed = [line[1:] for line in diff.splitlines() if line.startswith('-') and not line.startswith('---')]
# only the DISCARD branch gets the unsynchronised flag; the orphaning call stays in front of it
assert any('glBufferData(mTarget, mSizeInBytes, NULL, getGLUsage(mUsage))' in line for line in added)
assert any('access |= GL_MAP_UNSYNCHRONIZED_BIT;' in line for line in added)
assert not any('GL_MAP_READ_BIT' in line for line in added + removed), 'reads must keep their synchronisation'
assert len(added) <= 10 and len(removed) <= 4, 'the patch must stay a small change of the discard branch'
order = [line.strip() for line in added]
assert order.index('OGRE_CHECK_GL_ERROR(glBufferData(mTarget, mSizeInBytes, NULL, getGLUsage(mUsage)));') < order.index('access |= GL_MAP_UNSYNCHRONIZED_BIT;')

# the install script applies it like the other OGRE patches
assert "patches/ogre14-discard-lock-unsynchronized.patch" in install
assert 'apply --recount --reverse --check $taskDiscardLockPatch' in install
assert 'apply --recount $taskDiscardLockPatch' in install
assert install.index('$taskDiscardLockPatch') < install.index('$taskOptions'), 'the patch must be applied before OGRE is configured and built'

# the particle scripts and the game code are not part of this cause: the look stays as it is
assert 'billboard_type' in (repo / 'particles/MenuScene.particle').read_text(encoding='utf-8')
print('ok')
