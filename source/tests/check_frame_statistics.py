"""Non-compiling contracts for permanent rendered-frame statistics and Release symbols.

Checks the production sampling and input paths, idle/minute boundaries, overlapping
series, unclamped arithmetic and nearest-rank percentile against fixed fixtures.
It does not establish C++ compilation or game runtime correctness.
"""
from pathlib import Path
import math
import re

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    """Read production text without launching the game or a compiler."""
    return (ROOT / path).read_text(encoding="utf-8")


def function(text, signature):
    """Extract one complete function, including nested conditions."""
    start = text.index(signature)
    end = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


stats = read("source/render/FrameStatistics.cpp")
header = read("source/render/FrameStatistics.h")
listener = read("source/render/ODFrameListener.cpp")
base = read("source/modes/AbstractApplicationMode.cpp")
game = read("source/modes/GameMode.cpp")
workers = read("source/render/WorkersWindow.cpp")
scene = read("source/renderscene/RenderSceneMenu.cpp")
flight = read("source/render/MenuFlight.h")
cmake = read("CMakeLists.txt")

# Exactly one call samples all series. Repeated game mode callbacks never sample.
frame = function(listener, "bool ODFrameListener::frameStarted(")
assert listener.count("mFrameStatistics.sampleFrame(") == 1
assert "sampleFrame(" not in game and "addFrame(" not in base + workers
assert frame.index("mFrameStatistics.sampleFrame(inGame)") < frame.index("currentMode->onFrameStarted(evt)")
assert "ModeManager::GAME && mGameMap->getTurnNumber() != -1" in frame
sample = function(stats, "float FrameStatistics::sampleFrame(")
assert "steady_clock::now()" in function(stats, "double FrameStatistics::now(")
assert "time - mPreviousFrame" in sample
assert not re.search(r"getGamePaused|getGameSpeed|timeSinceLastFrame|std::min|MAX_STEP", sample)
for series in ("mMenuMovement.mFrames", "mWindowMovement.mFrames", "mDragFrames", "mGameFrames"):
    assert sample.count(series + ".addFrame(seconds);") == 1, series
# Independent if blocks allow the same frame in movement, drag and game minute.
assert "if(mMenuMovement.mActive)" in sample and "if(mWindowMovement.mActive)" in sample
assert "if(mDragging)" in sample and "if(mInGame)" in sample
assert "else if" not in sample
assert sample.index("mGameFrames.addFrame(seconds)") < sample.index("while(time >= mNextMinute)")
assert "mNextMinute = time + 60.0;" in sample and "mNextMinute += 60.0;" in sample
assert "mGameFrames.reset();" in sample and "mInGame = inGame;" in sample
assert "endDrag();" not in sample, "an interruption already sampled must not queue another frame"
assert "completed.mFrames.addFrame(seconds);" in sample and "mCompleted.clear();" in sample
assert "mFrameStatistics.finish();" in function(listener, "void ODFrameListener::exitApplication(")

# Real pointer moves, not wheel events or repeated coordinates, extend the one-second interval.
move = function(base, "bool AbstractApplicationMode::mouseMoved(")
assert move.index("mouseMovedN(") < move.index("getWindowContainingMouse()")
assert "if(arg.state.Z.rel == 0 || arg.state.X.rel != 0 || arg.state.Y.rel != 0)" in move
assert "window != context.getRootWindow()" in move and "FrameStatistics::GameWindow" in move
assert "FrameStatistics::Menu" in move and "mModeType == ModeManager::GAME" in move
pointer = function(stats, "void FrameStatistics::pointerMoved(")
assert "mHavePosition && x == mX && y == mY" in pointer
assert "if(area == Outside)" in pointer
assert "movement.mLastMovement = time;" in pointer
assert "time - movement.mLastMovement >= 1.0" in pointer
for series in ("mMenuMovement", "mWindowMovement"):
    assert f"time - {series}.mLastMovement >= 1.0" in sample
    assert sample.index(series + ".mFrames.addFrame(seconds)") < sample.index(f"time - {series}.mLastMovement >= 1.0")

# Both real input paths use the same GUI injection; accepted titlebar and Workers drags only.
press = function(base, "bool AbstractApplicationMode::mousePressed(")
release = function(base, "bool AbstractApplicationMode::mouseReleased(")
assert "dynamic_cast<CEGUI::Titlebar*>" in press and "titlebar->isDragged()" in press
assert press.index("injectMouseButtonDown") < press.index("beginDrag()")
assert "id == OIS::MB_Left" in press and "id == OIS::MB_Left" in release
assert release.index("endDrag()") < release.index("injectMouseButtonUp")
for method, injection in (("mousePressed", "injectMouseButtonDown"), ("mouseReleased", "injectMouseButtonUp")):
    body = function(game, f"bool GameMode::{method}(")
    assert body.count(f"AbstractApplicationMode::{method}(arg, id)") == 2
    assert injection not in body
assert "AbstractApplicationMode::mouseMoved(arg)" in function(game, "bool GameMode::mouseMoved(")
for method, guard in (("onTabletPressed", "settings.freeMode"), ("onCarryPressed", "seat == nullptr")):
    body = function(workers, f"bool WorkersWindow::{method}(")
    assert body.index(guard) < body.index("beginDrag()")
assert "endDrag()" in function(workers, "void WorkersWindow::finishDrag(")

# Each log has every requested field, including the retained flight lines.
for body in (function(stats, "void FrameStatistics::log("), function(scene, "void RenderSceneMenu::logFlightFrames(")):
    for field in ("frames=", "meanMs=", "p95Ms=", "maxMs=", "framesOver33Ms="):
        assert field in body, field
assert scene.count("mFlightFrames.addFrame(") == 1
assert "recordFrameStatistics(frameSeconds)" in frame
assert "mActive && mFlight.isActive()" in function(scene, "void RenderSceneMenu::recordFrameStatistics(")

# Exercise the actual percentile rank expression against fixed, unsorted frame-time fixtures.
p95 = function(flight, "double getP95Milliseconds(")
assert "std::sort(sorted.begin(), sorted.end())" in p95
assert "return sorted[rank - 1] * 1000.0;" in p95 and "if(mSamples.empty())" in p95
rank_expression = re.search(r"rank = (.*);", p95).group(1).replace("sorted.size()", "size").replace("/", "//")
for samples, expected in (([0.020], 20.0), ([0.100] + [0.010] * 19, 10.0), ([0.100] + [0.010] * 18, 100.0), ([0.200, 0.040, 0.010], 200.0)):
    rank = eval(rank_expression, {"__builtins__": {}}, {"size": len(samples)})
    assert math.isclose(sorted(samples)[rank - 1] * 1000.0, expected)
add = function(flight, "void addFrame(")
assert "!std::isfinite(seconds) || seconds <= 0.0f" in add
assert "mSamples.push_back(seconds)" in add and "mTotal += seconds" in add
assert "seconds > MenuFlightSettings::SMOOTH_FRAME_LIMIT" in add
assert "const float SMOOTH_FRAME_LIMIT = 0.033f;" in flight
assert "mFrames == 0 ? 0.0 : mTotal * 1000.0 / mFrames" in flight
assert "mLongest = std::max(mLongest, seconds)" in add

# Compiler and linker must emit full Release symbols to the executable's directory.
assert 'set(CMAKE_CXX_FLAGS_RELEASE "/MD /O2 /Zi")' in cmake
assert 'LINK_FLAGS_RELEASE " /DEBUG:FULL"' in cmake
assert 'PDB_OUTPUT_DIRECTORY_RELEASE "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}"' in cmake
assert 'PDB_NAME_RELEASE "${PROJECT_BINARY_NAME}"' in cmake
assert cmake.count("${SRC}/render/FrameStatistics.cpp") == 1
assert "MenuFlightFrameStats mDragFrames" in header and "MenuFlightFrameStats mGameFrames" in header
print("Frame statistics contracts passed; percentile fixtures=4; no compilation or game launch")
