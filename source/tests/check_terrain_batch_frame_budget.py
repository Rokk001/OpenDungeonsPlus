"""Guard the one-cell Ogre-frame construction budget without compiling or running the game."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source, header):
    """Require a shared frame stamp, one construction, and ordinary dirty-cell fallback."""
    assert '#include <OgreRoot.h>' in source
    assert 'unsigned long mLastBuildFrame;' in header and 'bool mHasBuildFrame;' in header
    constructor = source.split('TerrainDrawBatch::TerrainDrawBatch()', 1)[1].split('{', 1)[0]
    assert 'mLastBuildFrame(0)' in constructor and 'mHasBuildFrame(false)' in constructor
    build = body(source, 'void TerrainDrawBatch::preUpdateSceneGraph(')
    assert 'const unsigned long frame = Ogre::Root::getSingleton().getNextFrameNumber();' in build
    guard = 'if(mHasBuildFrame && mLastBuildFrame == frame)\n        return;'
    assert guard in build
    assert build.index(guard) < build.index('for(std::map')
    allowed = build.index('if(!cell.mBuildAllowed)')
    stamp = build.index('mLastBuildFrame = frame;')
    used = build.index('mHasBuildFrame = true;')
    dirty = build.index('cell.mDirty = false;')
    assert allowed < stamp < used < dirty < build.index('createStaticGeometry')
    assert 'continue;' in build[allowed:stamp]
    assert 'return;' in build[build.index('region->second->setListener(&cell);'):]
    assert 'mHasBuildFrame' not in body(source, 'void TerrainDrawBatch::clear(')
    decision = body(source, 'bool TerrainDrawBatch::Cell::canBatch(')
    assert 'if(mDirty || mGeometry == nullptr' in decision
    callback = body(source, 'bool TerrainDrawBatch::Cell::objectRendering(')
    assert 'if(!canBatch())\n        return true;' in callback


def simulate(callbacks):
    """Model a single shared frame budget; rejected candidates stay dirty."""
    dirty = set(range(4))
    last_frame = None
    built = []
    for frame, candidates in callbacks:
        if last_frame == frame:
            continue
        for cell, eligible in candidates:
            if cell not in dirty or not eligible:
                continue
            last_frame = frame
            dirty.remove(cell)
            built.append((frame, cell))
            break
    return built, dirty


def main():
    """Check same-frame views, next-frame progress and seven independent mutations."""
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text(encoding='utf-8')
    header = (ROOT / 'source/render/TerrainDrawBatch.h').read_text(encoding='utf-8')
    verify(source, header)
    callbacks = [(10, [(0, False), (1, True), (2, True)]),
                 (10, [(0, True), (2, True)]), (11, [(0, True), (2, True)]),
                 (11, [(2, True)]), (12, [(2, True)])]
    assert simulate(callbacks) == ([(10, 1), (11, 0), (12, 2)], {3})
    changes = [
        ('getNextFrameNumber()', 'getNextFrameNumber() + 1'),
        ('if(mHasBuildFrame && mLastBuildFrame == frame)', 'if(false)'),
        ('mLastBuildFrame = frame;', ';'),
        ('mHasBuildFrame = true;', ';'),
        ('mHasBuildFrame(false)', 'mHasBuildFrame(true)'),
        ('region->second->setListener(&cell);\n        }\n        return;', 'region->second->setListener(&cell);\n        }'),
        ('if(mDirty || mGeometry == nullptr', 'if(false && mGeometry == nullptr'),
    ]
    assert len(changes) == 7
    for old, new in changes:
        assert old in source
        try:
            verify(source.replace(old, new, 1), header)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    print('terrain frame budget: fixed one-cell fixtures and seven mutations passed; runtime performance unverified')


if __name__ == '__main__':
    main()
