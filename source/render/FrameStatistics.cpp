#include "render/FrameStatistics.h"

#include "utils/LogManager.h"

#include <iomanip>
#include <sstream>

//! \brief Uses a monotonic clock rather than Ogre's smoothed animation delta.
double FrameStatistics::now()
{
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
}

//! \brief Emits a permanent statistics line, including empty intervals crossed by a long stall.
void FrameStatistics::log(const char* label, const MenuFlightFrameStats& frames)
{
    std::ostringstream line;
    line << std::fixed << std::setprecision(2) << label << ": frames=" << frames.getFrames()
        << " meanMs=" << frames.getMeanMilliseconds()
        << " p95Ms=" << frames.getP95Milliseconds()
        << " maxMs=" << frames.getMaxMilliseconds()
        << " framesOver33Ms=" << frames.getSlowFrames();
    OD_LOG_INF(line.str());
}

//! \brief Keeps pointer intervals separate while allowing them to overlap a drag or game minute.
void FrameStatistics::pointerMoved(int x, int y, PointerArea area)
{
    if(mHavePosition && x == mX && y == mY)
        return;
    mHavePosition = true;
    mX = x;
    mY = y;
    // Any real movement, also outside a window, extends an active line: it ends
    // only after one second without movement, not when the hand leaves its area.
    const double time = now();
    extendMovement(mMenuMovement, "Menu hand movement", time);
    extendMovement(mWindowMovement, "Game window hand movement", time);
    if(area == Outside)
        return;
    Movement& movement = area == Menu ? mMenuMovement : mWindowMovement;
    movement.mActive = true;
    movement.mLastMovement = time;
}

//! \brief Queues a line ended by a one-second pause, otherwise moves its pause start to this movement.
void FrameStatistics::extendMovement(Movement& movement, const char* label, double time)
{
    if(!movement.mActive)
        return;
    if(time - movement.mLastMovement >= 1.0)
    {
        mCompleted.push_back(Completed{label, movement.mFrames});
        movement.mFrames.reset();
        movement.mActive = false;
        return;
    }
    movement.mLastMovement = time;
}

//! \brief Starts only accepted drags; ordinary button presses do not produce drag lines.
void FrameStatistics::beginDrag()
{
    if(mDragging)
        return;
    mDragFrames.reset();
    mDragging = true;
}

//! \brief Ends the press-to-release interval without counting an extra input-event sample.
void FrameStatistics::endDrag()
{
    if(!mDragging)
        return;
    mCompleted.push_back(Completed{"Window drag", mDragFrames});
    mDragFrames.reset();
    mDragging = false;
}

//! \brief Logs and releases the samples of a pointer interval that has ended.
void FrameStatistics::finishMovement(Movement& movement, const char* label)
{
    if(!movement.mActive)
        return;
    log(label, movement.mFrames);
    movement.mFrames.reset();
    movement.mActive = false;
}

//! \brief Counts every render interval once in each active series, including a frame crossing its end.
float FrameStatistics::sampleFrame(bool inGame)
{
    const double time = now();
    const float seconds = mPreviousFrame == 0.0 ? 0.0f : static_cast<float>(time - mPreviousFrame);
    mPreviousFrame = time;
    // Input may be delivered before frameStarted (SFML) or after it (OIS). Defer
    // ended intervals so both paths retain their last intersecting render frame.
    for(Completed& completed : mCompleted)
    {
        completed.mFrames.addFrame(seconds);
        log(completed.mLabel, completed.mFrames);
    }
    mCompleted.clear();
    if(mMenuMovement.mActive)
    {
        mMenuMovement.mFrames.addFrame(seconds);
        if(time - mMenuMovement.mLastMovement >= 1.0 || inGame)
            finishMovement(mMenuMovement, "Menu hand movement");
    }
    if(mWindowMovement.mActive)
    {
        mWindowMovement.mFrames.addFrame(seconds);
        if(time - mWindowMovement.mLastMovement >= 1.0 || !inGame)
            finishMovement(mWindowMovement, "Game window hand movement");
    }
    if(mDragging)
        mDragFrames.addFrame(seconds);
    if(inGame && !mInGame)
    {
        mGameFrames.reset();
        mNextMinute = time + 60.0;
    }
    if(mInGame)
    {
        mGameFrames.addFrame(seconds);
        while(time >= mNextMinute)
        {
            log("Game minute", mGameFrames);
            mGameFrames.reset();
            mNextMinute += 60.0;
        }
        if(!inGame)
        {
            log("Game minute interrupted", mGameFrames);
            mGameFrames.reset();
            if(mDragging)
            {
                log("Window drag interrupted", mDragFrames);
                mDragFrames.reset();
                mDragging = false;
            }
        }
    }
    mInGame = inGame;
    return seconds;
}

//! \brief Preserves the last partial intervals on a normal shutdown.
void FrameStatistics::finish()
{
    finishMovement(mMenuMovement, "Menu hand movement interrupted");
    finishMovement(mWindowMovement, "Game window hand movement interrupted");
    endDrag();
    for(const Completed& completed : mCompleted)
        log(completed.mLabel, completed.mFrames);
    mCompleted.clear();
    if(mInGame)
        log("Game minute interrupted", mGameFrames);
    mGameFrames.reset();
    mInGame = false;
}
