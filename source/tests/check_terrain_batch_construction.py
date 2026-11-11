"""Guard deferred light-compatible construction and exhausted-cell cleanup without compiling.

The eligibility hint is learned after transforms update, never used to suppress a draw.
Current-view fallback, real construction cost and appearance still need engine validation.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source):
    """Reject premature light queries, construction without a hint and retained empty cells."""
    build = body(source, 'void TerrainDrawBatch::preUpdateSceneGraph(')
    assert 'queryLights()' not in build
    gate = build.index('if(!cell.mBuildAllowed)')
    assert gate < build.index('cell.mDirty = false') < build.index('createStaticGeometry')
    assert 'continue;' in build[gate:build.index('cell.mDirty = false')]
    view = body(source, 'void TerrainDrawBatch::preFindVisibleObjects(')
    assert 'if(!cell.mDecided && cell.mDirty && cell.mEntities.size() >= 2)' in view
    assert 'if(!entity->isAttached())' in view
    assert 'else if(lights != firstLights)' in view
    assert view.count('cell.mBuildAllowed = false;') == 2
    assert view.index('entity->queryLights()') < view.index('cell.canBatch()')
    decision = body(source, 'bool TerrainDrawBatch::Cell::canBatch(')
    assert 'mBuildAllowed' not in decision
    assert 'if(mDirty || mGeometry == nullptr' in decision
    assert decision.index('lights != mLights') < decision.index('mEnabled = true;')
    invalidation = body(source, 'void TerrainDrawBatch::invalidate(')
    assert 'cell.mBuildAllowed = false;' in invalidation
    removal = body(source, 'void TerrainDrawBatch::remove(')
    assert removal.index('setListener(nullptr)') < removal.index('mEntities.erase')
    assert removal.index('mMembers.erase(member)') < removal.index('if(cell.mEntities.empty())')
    assert 'if(it->second.get() != &cell)' in removal
    assert 'mCells.erase(it);' in removal


def main():
    """Reject six independent regressions to construction, fallback and cleanup."""
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text()
    verify(source)
    mutations = [
        ('if(!cell.mBuildAllowed)', 'if(false)'),
        ('else if(lights != firstLights)', 'else if(false)'),
        ('cell.mBuildAllowed = false;', ';'),
        ('if(!cell.mDecided && cell.mDirty && cell.mEntities.size() >= 2)', 'if(cell.mDirty)'),
        ('mCells.erase(it);', ';'),
        ('lights != mLights', 'false'),
    ]
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    print('terrain construction: six mutations rejected; runtime cost remains unverified')


if __name__ == '__main__':
    main()
