"""Guard the limiter's sleep decision, its precise Windows wait and the per-minute evidence, without compiling.

Tilda F1 runtime evidence (build 52, 8bb3464ce, P1 settings): the plain boost sleep woke on average
7.3 ms late in the menu (requestedMeanMs 12.39, actualMeanMs 19.70) and 7.7 ms late in the P1 game
(2.29 / 9.97), max 24.5 ms. The limiter now waits on a high-resolution waitable timer and keeps the
boost sleep only as fallback. The sleep decision (60 fps minimum frame time, 1 ms threshold) is unchanged.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source, header):
    """Require one unchanged sleep decision, one precise wait and one-minute monotonic aggregate evidence."""
    sleep = body(source, 'void FrameRateLimiter::sleepIfEarly(')
    assert 'const std::int64_t minDifference = divisor / 1000;' in source
    assert 'if(mMinFrameTime - timeSinceLast > minDifference)' in sleep
    assert 'const std::int64_t requested = mMinFrameTime - timeSinceLast;' in sleep
    assert sleep.count('waitFor(') == 1 and 'waitFor(requested);' in sleep
    assert 'sleep_for(' not in sleep
    actual = 'const std::int64_t actual = mClock.getElapsedTime().asMicroseconds() - timeSinceLast;'
    assert actual in sleep and sleep.index('waitFor(') < sleep.index(actual)
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

    # Precise wait: a high-resolution timer, relative due time in 100 ns units, one wait, boost fallback.
    wait = body(source, 'void FrameRateLimiter::waitFor(')
    assert '#ifdef _WIN32' in wait and 'if(mWaitTimer != nullptr)' in wait
    assert 'due.QuadPart = -microseconds * 10;' in wait
    assert 'if(SetWaitableTimer(mWaitTimer, &due, 0, nullptr, nullptr, FALSE))' in wait
    assert wait.count('WaitForSingleObject(mWaitTimer, INFINITE);') == 1
    assert wait.index('WaitForSingleObject') < wait.index('return;') < wait.index('#endif')
    assert wait.count('boost::this_thread::sleep_for(boost::chrono::microseconds(microseconds));') == 1
    assert wait.index('#endif') < wait.index('boost::this_thread::sleep_for(')
    assert 'Sleep(' not in wait and 'timeBeginPeriod' not in source, 'no global timer resolution change'
    constructor = body(source, 'FrameRateLimiter::FrameRateLimiter(')
    assert 'CreateWaitableTimerExW(nullptr, nullptr, CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, TIMER_ALL_ACCESS)' in constructor
    assert 'mWaitTimer(nullptr)' in source.split('FrameRateLimiter::FrameRateLimiter(', 1)[1].split('{', 1)[0]
    assert '#define CREATE_WAITABLE_TIMER_HIGH_RESOLUTION 0x00000002' in source
    destructor = body(source, 'FrameRateLimiter::~FrameRateLimiter(')
    assert 'if(mWaitTimer != nullptr)' in destructor and 'CloseHandle(mWaitTimer);' in destructor
    # One owner of the handle: copying the limiter would close it twice.
    assert 'FrameRateLimiter(const FrameRateLimiter&) = delete;' in header
    assert 'FrameRateLimiter& operator=(const FrameRateLimiter&) = delete;' in header
    assert 'void* mWaitTimer;' in header
    assert header.index('std::int64_t mMinFrameTime;') < header.index('void* mWaitTimer;') < header.index('sf::Clock mClock;')


def main():
    """Reject decision, wait and diagnostic regressions and check fixed schedule observations."""
    source = (ROOT / 'source/utils/FrameRateLimiter.cpp').read_text()
    header = (ROOT / 'source/utils/FrameRateLimiter.h').read_text()
    verify(source, header)
    mutations = [
        ('> minDifference', '>= minDifference'),
        ('mMinFrameTime - timeSinceLast;', 'mMinFrameTime;'),
        ('waitFor(requested);', 'waitFor(1);'),
        ('mClock.getElapsedTime().asMicroseconds() - timeSinceLast;', 'requested;'),
        ('actual - requested)', 'actual)'),
        ('mReportElapsed >= 60 * divisor', 'true'),
        ('mMaxOversleep = 0;', ';'),
        ('due.QuadPart = -microseconds * 10;', 'due.QuadPart = microseconds * 10;'),
        ('due.QuadPart = -microseconds * 10;', 'due.QuadPart = -microseconds;'),
        ('            return;\n', ''),
        ('CREATE_WAITABLE_TIMER_HIGH_RESOLUTION, TIMER_ALL_ACCESS', '0, TIMER_ALL_ACCESS'),
        ('        CloseHandle(mWaitTimer);', '        ;'),
        ('    boost::this_thread::sleep_for(boost::chrono::microseconds(microseconds));\n', ''),
    ]
    for old, new in mutations:
        assert old in source, old
        try:
            verify(source.replace(old, new, 1), header)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted mutation: ' + old)
    header_mutations = [('    FrameRateLimiter(const FrameRateLimiter&) = delete;\n', '')]
    for old, new in header_mutations:
        assert old in header
        try:
            verify(source, header.replace(old, new, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted header mutation: ' + old)
    # Fixed work/request fixtures include threshold, late and uncapped frames (60 fps: 16666 us).
    cases = [(16666, 4000, 12666), (16666, 15666, 0), (16666, 15665, 1001),
             (16666, 20000, 0), (1000, 0, 0)]
    for minimum, work, expected in cases:
        assert (minimum - work if minimum - work > 1000 else 0) == expected
    # Due time: 12666 us relative -> -126660 units of 100 ns.
    assert -12666 * 10 == -126660
    # Measured build-52 shares of the plain sleep's late wake (menu, P1 game minute 1).
    menu_late = 2322 * (19.7023 - 12.3928) / 60015.0
    game_late = 904 * (9.97468 - 2.29395) / 60011.1
    assert 0.28 < menu_late < 0.29 and 0.11 < game_late < 0.12
    total = len(mutations) + len(header_mutations)
    print('limiter: 5 unchanged sleep decisions, precise high-resolution wait with boost fallback, '
          'measured late wake %.1f%% menu / %.1f%% game, %d rejected mutations' % (100 * menu_late, 100 * game_late, total))


if __name__ == '__main__':
    main()
