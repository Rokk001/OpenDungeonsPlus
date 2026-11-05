#ifndef FRAMESTATISTICS_H
#define FRAMESTATISTICS_H

#include "render/MenuFlight.h"

#include <chrono>

//! \brief Collects overlapping pointer, drag and real-minute intervals at one render callback.
class FrameStatistics
{
public:
    //! \brief Identifies menu movement and movement over a game interface window.
    enum PointerArea { Outside, Menu, GameWindow };

    //! \brief Records actual position changes, independently of the number of input events.
    void pointerMoved(int x, int y, PointerArea area);
    //! \brief Starts a window or Workers entry drag at its accepted left-button press.
    void beginDrag();
    //! \brief Finishes a drag at release, even if the pointer has left the pressed window.
    void endDrag();
    //! \brief Samples once per rendered frame and returns its unsmoothed wall-clock duration.
    float sampleFrame(bool inGame);
    //! \brief Writes unfinished intervals before the render listener shuts down.
    void finish();

private:
    //! \brief A pointer interval remains active for one second after its last movement.
    struct Movement
    {
        bool mActive = false;
        double mLastMovement = 0.0;
        MenuFlightFrameStats mFrames;
    };

    //! \brief An input-ended interval waits for its last intersecting rendered frame.
    struct Completed
    {
        const char* mLabel;
        MenuFlightFrameStats mFrames;
    };

    //! \brief Returns monotonic seconds, unaffected by pause, game speed or system clock changes.
    static double now();
    //! \brief Writes all five frame statistics using the same fields as a menu flight.
    static void log(const char* label, const MenuFlightFrameStats& frames);
    //! \brief Closes an active pointer interval and clears its samples.
    static void finishMovement(Movement& movement, const char* label);

    Movement mMenuMovement;
    Movement mWindowMovement;
    std::vector<Completed> mCompleted;
    MenuFlightFrameStats mDragFrames;
    MenuFlightFrameStats mGameFrames;
    bool mDragging = false;
    bool mInGame = false;
    bool mHavePosition = false;
    int mX = 0;
    int mY = 0;
    double mPreviousFrame = 0.0;
    double mNextMinute = 0.0;
};

#endif // FRAMESTATISTICS_H
