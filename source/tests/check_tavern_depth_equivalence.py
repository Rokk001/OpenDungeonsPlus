"""Keep dense tavern furniture measurements exact when reducing temporary arrays."""
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import author_tavern_seats as seats


# Preserve the former stacked reduction as an independent numerical reference.
def reference(points, size, whole_bench, selected=None):
    if selected is not None:
        points = points[:, selected, :]
    world = points * size
    x, y, z = world[:, :, 0], world[:, :, 1], world[:, :, 2]
    worst = np.zeros(points.shape[:2])
    places = (-0.328, 0.328) if whole_bench else (-1.5 * 0.328, -0.5 * 0.328, 0.5 * 0.328, 1.5 * 0.328)
    for place in places:
        along = np.abs(x + place)
        inside = (z > 0.37) & (z < 0.4425) & (along < 0.26 + 0.328) & (y > -0.735)
        worst = np.maximum(worst, np.where(inside, -0.0882 - y, 0.0))
        for middle in (-0.328, 0.328):
            beside = np.abs(x + place - middle)
            worst = np.maximum(worst, np.minimum.reduce([0.193 - beside, y + 0.605, -0.219 - y, z, 0.38 - z]))
        worst = np.maximum(worst, np.minimum.reduce([2.0 * 0.328 - along, y + 0.088, 0.087 - y, z - 0.202,
                                                     0.2575 - 0.015 - z]))
        worst = np.maximum(worst, np.minimum.reduce([along - (0.187 + 0.328), (0.26 + 0.328) - along,
                                                     0.042 - np.abs(y), z, 0.21 - z]))
    return np.maximum(0.0, worst.max(axis=1)) / size


# Check fixed furniture penetrations independently of the reference reduction.
def check_contacts(function):
    points = np.array([[[0.0, -0.1, 0.4]], [[0.492, -0.4, 0.2]],
                       [[0.0, 0.0, 0.22]], [[0.7, 0.0, 0.1]], [[0.0, 1.0, 1.0]]])
    seats.SCENE.update(size=1.0, whole_bench=False)
    np.testing.assert_allclose(function(points), [0.0118, 0.18, 0.018, 0.021, 0.0], rtol=0.0, atol=1e-15)


# Compare isolated boundary contacts, late entry, exterior vertices and nonfinite inputs.
def check_filter(function):
    boundaries = []
    for y in (-0.735, -0.605, -0.219, -0.0882, -0.088, -0.042, 0.042, 0.087):
        for side in (-np.inf, y, np.inf):
            value = y if side == y else np.nextafter(y, side)
            for z in (0.1, 0.22, 0.3, 0.4):
                boundaries.append([[0.492, value, z]])
    for z in (0.0, 0.202, 0.21, 0.2575 - 0.015, 0.37, 0.38, 0.4425):
        for side in (-np.inf, z, np.inf):
            value = z if side == z else np.nextafter(z, side)
            for y in (-0.4, 0.0):
                boundaries.append([[0.492, y, value]])
    boundary_points = np.array(boundaries)
    mover = np.full((385, 1, 3), 2.0)
    mover[-1, 0] = [0.492, -0.4, 0.2]
    outside = np.full((385, 3, 3), 2.0)
    invalid = np.array([[[np.nan, 2.0, 2.0]], [[2.0, np.nan, 2.0]], [[2.0, 2.0, np.nan]],
                        [[np.inf, 2.0, 2.0]], [[2.0, -np.inf, 2.0]]])
    for whole_bench in (False, True):
        for size in (1.0, 1.1):
            seats.SCENE.update(size=size, whole_bench=whole_bench)
            for data in (boundary_points, mover, outside, invalid):
                np.testing.assert_array_equal(function(data), reference(data, size, whole_bench))


# Exercise all 385 frames, both scales/seat sets, selection and noncontiguous input.
def verify(function):
    check_contacts(function)
    check_filter(function)
    rng = np.random.default_rng(9341)
    points = rng.uniform([-1.2, -0.9, -0.1], [1.2, 0.2, 0.6], (385, 129, 3))
    # Include the exact boundaries and their adjacent representable coordinates.
    for axis, boundaries in enumerate(([-0.588, 0.0, 0.588], [-0.735, -0.605, -0.219, -0.088, 0.087],
                                       [0.0, 0.202, 0.21, 0.2425, 0.37, 0.38, 0.4425])):
        for index, boundary in enumerate(boundaries):
            points[:, index * 3, axis] = boundary
            points[:, index * 3 + 1, axis] = np.nextafter(boundary, -np.inf)
            points[:, index * 3 + 2, axis] = np.nextafter(boundary, np.inf)
    original = points.copy()
    cases = 0
    for whole_bench in (False, True):
        for size in (1.0, 1.1):
            seats.SCENE.update(size=size, whole_bench=whole_bench)
            for data in (points, points[:, ::2, :]):
                for selected in (None, [0, 3, 7, 11, 31]):
                    # The reference freezes the old constants; binary-identical arithmetic is required.
                    np.testing.assert_array_equal(function(data, selected), reference(data, size, whole_bench, selected))
                    cases += 1
    np.testing.assert_array_equal(points, original)
    assert cases == 16, cases
    # Empty inputs retain the original error instead of passing as zero penetration.
    for data, selected in ((np.empty((385, 0, 3)), None), (points, [])):
        for measured in (function, seats.frame_depths):
            try:
                measured(data, selected)
            except ValueError:
                pass
            else:
                raise AssertionError('empty furniture input must fail')


# Reject omitted collision components and a missing face in the optimized calculation.
def check_mutations():
    source = (ROOT / 'tools/author_tavern_seats.py').read_text(encoding='utf-8')
    body = source.split('def frame_depths(', 1)[1].split('\n\n# Measure how far', 1)[0]
    body = 'def frame_depths(' + body
    mutations = [('TABLE_NEAR_EDGE - y', 'np.zeros_like(y)'),
                 ('half - beside', '-np.ones_like(beside)'),
                 ('LONG_BENCH_HALF_LENGTH - along', '-np.ones_like(along)'),
                 ('along - LONG_BENCH_LEG_X[0]', '-np.ones_like(along)'),
                 ('high - BENCH_SINK - z', 'high - z'),
                 ('candidate.any(axis=0)', 'candidate[0]'),
                 (' | (~np.isfinite(world)).any(axis=(0, 2))', '')]
    rejected = 0
    for before, after in mutations:
        assert body.count(before) == 1, before
        namespace = dict(vars(seats))
        exec(body.replace(before, after), namespace)
        try:
            verify(namespace['frame_depths'])
        except AssertionError:
            rejected += 1
        else:
            raise AssertionError(('mutation survived', before))
    assert rejected == 7, rejected


# Preserve module state when this numerical check is imported by another check.
def main():
    saved = dict(seats.SCENE)
    try:
        verify(seats.frame_depths)
        check_mutations()
    finally:
        seats.SCENE.clear()
        seats.SCENE.update(saved)
    print('tavern furniture depth: 16 dense cases, five fixed contacts, boundary/filter cases, seven mutations rejected')


if __name__ == '__main__':
    main()
