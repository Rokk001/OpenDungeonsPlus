"""Guard conservative view culling, deferred construction and observed suppression counters.

This is a non-compiling contract check; engine draw counts and performance require release evidence.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


# Reject loss of the early culling gate, fallback or source-submission accounting.
def verify(source):
    add = body(source, 'void TerrainDrawBatch::add(')
    assert 'mBounds.merge(entity->getWorldBoundingBox(true))' in add
    build = body(source, 'void TerrainDrawBatch::preUpdateSceneGraph(')
    gate = build.index('if(!camera->isVisible(cell.mBounds))')
    assert gate < build.index('cell.mDirty = false') < build.index('createStaticGeometry')
    assert 'continue;' in build[gate:build.index('cell.mDirty = false')]
    view = body(source, 'void TerrainDrawBatch::preFindVisibleObjects(')
    assert 'cell.mSuppressed = 0' in view
    assert 'cell.mEnabled = false' in view
    gate = view.index('!viewport->getCamera()->isVisible(cell.mBounds)')
    assert gate < view.index('cell.mDecided = true') < view.index('cell.canBatch()')
    assert 'setVisible(enabled)' in view
    assert 'entity->setVisible' not in source
    submit = body(source, 'bool TerrainDrawBatch::Cell::objectRendering(')
    assert submit.index('if(!canBatch())') < submit.index('return true;') < submit.index('++mSuppressed')
    report = body(source, 'void TerrainDrawBatch::postFindVisibleObjects(')
    assert 'stage != Ogre::SceneManager::IRS_NONE || !viewport->getOverlaysEnabled()' in report
    assert report.index('if(now < mNextReport)') < report.index('mCells.begin()')
    assert 'std::chrono::seconds(60)' in report
    for field in ('candidateSources=', 'suppressedSourceCallbacks=', 'culled=', 'fallback='):
        assert field in report


# Check fixed union/frustum fixtures: rejecting the union cannot reject any intersecting member.
def check_bounds():
    boxes = [(-8, -4, -7, -3), (-7, -4, -6, -3), (-8, -3, -7, -2)]
    bounds = (-8, -4, -6, -2)
    views = [(-9, -5, -5, -1), (-7.5, -3.5, -7, -3), (0, 0, 4, 4), (-6, -2, -5, -1)]
    expected = [True, True, False, True]
    for view, visible in zip(views, expected):
        intersects = lambda box: box[0] <= view[2] and box[2] >= view[0] and box[1] <= view[3] and box[3] >= view[1]
        assert intersects(bounds) == visible
        assert intersects(bounds) or not any(intersects(box) for box in boxes)
    # Removing a member leaves a conservative superset; stale bounds only reduce batching opportunities.
    assert all(bounds[0] <= box[0] <= box[2] <= bounds[2] and bounds[1] <= box[1] <= box[3] <= bounds[3]
               for box in boxes[1:])


# Run contracts plus independent mutations, keeping expected fixture counts fixed.
def main():
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text()
    verify(source)
    mutations = [
        ('if(!camera->isVisible(cell.mBounds))', 'if(false)'),
        ('!viewport->getCamera()->isVisible(cell.mBounds)', 'false'),
        ('cell.mDecided = true;', 'cell.mDecided = false;'),
        ('++mSuppressed;', ';'),
        ('cell->mBounds.merge(entity->getWorldBoundingBox(true));', ';'),
    ]
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    check_bounds()
    print('terrain batch view cost: 4 bound fixtures, 5 rejected mutations; runtime coverage still required')


if __name__ == '__main__':
    main()
