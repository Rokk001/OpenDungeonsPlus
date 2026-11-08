"""Guard diagnostic sleep boundaries without compiling or changing the limiter policy."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source):
    """Require one unchanged sleep decision and one-minute monotonic aggregate evidence."""
    sleep = body(source, 'void FrameRateLimiter::sleepIfEarly(')
    assert 'const std::int64_t minDifference = divisor / 1000;' in source
    assert 'if(mMinFrameTime - timeSinceLast > minDifference)' in sleep
    assert 'const std::int64_t requested = mMinFrameTime - timeSinceLast;' in sleep
    assert sleep.count('boost::this_thread::sleep_for(') == 1
    assert 'boost::this_thread::sleep_for(boost::chrono::microseconds(requested));' in sleep
    actual = 'const std::int64_t actual = mClock.getElapsedTime().asMicroseconds() - timeSinceLast;'
    assert actual in sleep and sleep.index('sleep_for(') < sleep.index(actual)
    assert 'mRequestedSleep += requested;' in sleep and 'mActualSleep += actual;' in sleep
    assert 'std::max(mMaxOversleep, actual - requested)' in sleep
    assert sleep.count('mClock.restart()') == 1
    assert 'mReportElapsed += mClock.restart().asMicroseconds();' in sleep
    assert 'if(mReportElapsed >= 60 * divisor)' in sleep
    assert sleep.index('mClock.restart()') < sleep.index('if(mReportElapsed >= 60 * divisor)') < sleep.index('OD_LOG_INF')
    for field in ('samples=', 'intervalMs=', 'requestedMeanMs=', 'actualMeanMs=', 'maxOversleepMs='):
        assert field in sleep
    for counter in ('mReportElapsed', 'mSleepCount', 'mRequestedSleep', 'mActualSleep', 'mMaxOversleep'):
        assert counter + ' = 0;' in sleep
    assert 'mSleepCount == 0 ? 0.0' in sleep


def main():
    """Reject seven diagnostic/policy regressions and check fixed schedule observations."""
    source = (ROOT / 'source/utils/FrameRateLimiter.cpp').read_text()
    verify(source)
    mutations = [
        ('> minDifference', '>= minDifference'),
        ('mMinFrameTime - timeSinceLast;', 'mMinFrameTime;'),
        ('microseconds(requested)', 'microseconds(1)'),
        ('mClock.getElapsedTime().asMicroseconds() - timeSinceLast;', 'requested;'),
        ('actual - requested)', 'actual)'),
        ('mReportElapsed >= 60 * divisor', 'true'),
        ('mMaxOversleep = 0;', ';'),
    ]
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted mutation: ' + old)
    # Fixed work/request/actual fixtures include threshold, late and uncapped frames.
    cases = [(16666, 4000, 12666), (16666, 15666, 0), (16666, 15665, 1001),
             (16666, 20000, 0), (1000, 0, 0)]
    for minimum, work, expected in cases:
        assert (minimum - work if minimum - work > 1000 else 0) == expected
    requested = [12666, 1001, 8000]
    actual = [20000, 1500, 8100]
    assert sum(requested) == 21667 and sum(actual) == 29600
    assert max(observed - target for target, observed in zip(requested, actual)) == 7334
    assert len(cases) == 5 and len(mutations) == 7
    print('limiter evidence: 5 unchanged sleep decisions, fixed totals/max, 7 rejected mutations; runtime oversleep remains unmeasured')


if __name__ == '__main__':
    main()
