"""Guard failed build-probe throttling without caching any current-view draw decision."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source):
    """Require a 250 ms negative retry delay scoped to dirty-cell construction hints."""
    view = body(source, 'void TerrainDrawBatch::preFindVisibleObjects(')
    dirty = body(view, 'if(!cell.mDecided && cell.mDirty && cell.mEntities.size() >= 2)')
    assert dirty.index('if(now < cell.mNextBuildProbe)') < dirty.index('entity->queryLights()')
    assert 'continue;' in dirty[:dirty.index('cell.mBuildAllowed = true;')]
    failed = body(dirty, 'for(size_t i = 0; i < cell.mEntities.size(); ++i)')
    assert 'else if(lights != firstLights)' in failed
    assert 'if(!cell.mBuildAllowed)\n                cell.mNextBuildProbe = now + std::chrono::milliseconds(250);' in dirty
    assert view.index(dirty) < view.index('const bool enabled = cell.canBatch();')
    current = body(source, 'bool TerrainDrawBatch::Cell::canBatch(')
    assert 'mNextBuildProbe' not in current and 'chrono' not in current
    assert 'if(mDirty || mGeometry == nullptr' in current
    assert current.index('lights != mLights') < current.index('mEnabled = true;')
    reset = body(source, 'void TerrainDrawBatch::invalidate(')
    assert 'cell.mNextBuildProbe = std::chrono::steady_clock::time_point();' in reset


def main():
    """Reject five regressions of retry scope, expiry, reset and current lighting checks."""
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text()
    verify(source)
    mutations = [
        ('if(now < cell.mNextBuildProbe)', 'if(false)'),
        ('if(!cell.mBuildAllowed)\n                cell.mNextBuildProbe', 'if(true)\n                cell.mNextBuildProbe'),
        ('std::chrono::milliseconds(250)', 'std::chrono::milliseconds(0)'),
        ('cell.mNextBuildProbe = std::chrono::steady_clock::time_point();', ';'),
        ('lights != mLights', 'false'),
    ]
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    print('terrain retry: 250 ms failed-probe delay; five mutations rejected')


if __name__ == '__main__':
    main()
