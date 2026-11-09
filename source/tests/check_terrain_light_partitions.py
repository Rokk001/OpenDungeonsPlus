"""Guard compatible light subsets without relaxing current-view terrain validation.

Noncompiling contracts and fixed fixtures do not measure GPU draw savings.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source):
    """Require exact ordered lights, complete ownership transfers and deferred construction."""
    partition = body(source, 'void TerrainDrawBatch::partitionByLights(')
    assert 'if(!cell.mDirty || cell.mGeometry != nullptr)' in partition
    assert 'if(!entity->isAttached())\n            return;' in partition
    assert 'lights[group] != current' in partition
    assert 'current = entity->queryLights()' in partition
    assert 'groups[group].push_back(entity);' in partition
    assert 'if(groups.size() < 2)' in partition
    assert 'if(groups[largest].size() < 2)' in partition
    assert 'if(group == largest)\n            continue;' in partition
    assert 'subset->mMaterial = cell.mMaterial;' in partition
    assert 'subset->mEntities.swap(groups[group]);' in partition
    assert 'subset->mBuildAllowed = subset->mEntities.size() >= 2;' in partition
    assert 'subset->mBounds.merge(entity->getWorldBoundingBox(true));' in partition
    assert 'entity->setListener(subset.get());' in partition
    assert 'mMembers[entity->getName()] = subset.get();' in partition
    assert 'mCells[key.str()] = std::move(subset);' in partition
    assert 'cell.mEntities.swap(groups[largest]);' in partition
    assert 'createStaticGeometry' not in partition
    assert 'setVisible' not in partition
    view = body(source, 'void TerrainDrawBatch::preFindVisibleObjects(')
    assert 'if(!cell.mBuildAllowed)\n                partitionByLights(cell);' in view
    assert view.index('if(now < cell.mNextBuildProbe)') < view.index('partitionByLights(cell)')
    gate = body(source, 'bool TerrainDrawBatch::Cell::canBatch(')
    for required in ('if(mDirty || mGeometry == nullptr', 'lights != mLights',
                     '_getFullTransform() != mTransforms[i]', 'getSubEntity(0)->getMaterial() != mMaterial'):
        assert required in gate


def groups_for(entries):
    """Model partition membership by exact sequence, preserving every original identity."""
    groups = []
    for identity, lights in entries:
        for group in groups:
            if group[0][1] == lights:
                group.append((identity, lights))
                break
        else:
            groups.append([(identity, lights)])
    if len(groups) < 2 or max(map(len, groups)) < 2:
        return [entries]
    return groups


def main():
    """Check five fixed lighting fixtures and reject nine independent source regressions."""
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text()
    verify(source)
    fixtures = [
        ([(0, (1, 2)), (1, (1, 2)), (2, (2, 1)), (3, (2, 1))], [2, 2]),
        ([(0, (1, 2)), (1, (2, 1)), (2, (3,))], [3]),
        ([(0, ()), (1, ()), (2, (1,))], [2, 1]),
        ([(0, (1,)), (1, (1,)), (2, (1,))], [3]),
        ([(0, (1, 2)), (1, (1, 2)), (2, (1, 2, 3)), (3, (1, 2, 3)), (4, ())], [2, 2, 1]),
    ]
    for entries, expected in fixtures:
        groups = groups_for(entries)
        assert list(map(len, groups)) == expected
        assert sorted(identity for group in groups for identity, _ in group) == list(range(len(entries)))
        if len(groups) > 1:
            assert all(all(lights == group[0][1] for _, lights in group) for group in groups)
    mutations = [
        ('lights[group] != current', 'false'),
        ('if(groups[largest].size() < 2)', 'if(false)'),
        ('if(group == largest)', 'if(false)'),
        ('subset->mMaterial = cell.mMaterial;', ';'),
        ('subset->mBounds.merge(entity->getWorldBoundingBox(true));', ';'),
        ('entity->setListener(subset.get());', ';'),
        ('mMembers[entity->getName()] = subset.get();', ';'),
        ('cell.mEntities.swap(groups[largest]);', ';'),
        ('lights != mLights', 'false'),
    ]
    assert len(fixtures) == 5 and len(mutations) == 9
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    print('terrain light partitions: 5 fixtures, 9 mutations rejected; runtime savings unverified')


if __name__ == '__main__':
    main()
