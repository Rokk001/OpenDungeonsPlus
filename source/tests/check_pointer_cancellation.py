"""Exercise production game/editor pointer cancellation without issuing world actions."""
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def function(relative_path, signature):
    """Read the complete production method, retaining its implementation unchanged."""
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    start = source.index(signature)
    end = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


PREAMBLE = r'''
#include <cassert>
#include <vector>

enum class SelectedAction { none, selectTile, buildRoom };
enum class InputCommandState { infoOnly, building, validated };

//! Records held shared input without relying on a renderer or network client.
struct InputState
{
    bool left = true, right = true, middle = true;
    bool gui = true, tileContainer = true;
    InputCommandState command = InputCommandState::building;
};

//! Represents tool selection independently of the transient world selection.
struct Selection
{
    SelectedAction action = SelectedAction::selectTile;
    SelectedAction getCurrentAction() const { return action; }
    void setCurrentAction(SelectedAction value) { action = value; }
};

//! Records camera cleanup commands, allowing fixed axis/value assertions.
struct CameraManager
{
    enum Direction { zeroRandomRotateX, zeroRandomRotateY };
};

//! Provides the production cancellation method's camera-command dependency.
struct ODFrameListener
{
    std::vector<CameraManager::Direction> axes;
    std::vector<double> values;
    static ODFrameListener& getSingleton()
    {
        static ODFrameListener listener;
        return listener;
    }
    void moveCamera(CameraManager::Direction axis, double value)
    {
        axes.push_back(axis);
        values.push_back(value);
    }
};

//! Models base cleanup; real CEGUI capture cleanup is checked by the Win32 probe.
struct AbstractApplicationMode
{
    InputState input;
    int baseCancels = 0, releases = 0, worldCommands = 0;
    void cancelMouseInput()
    {
        ++baseCancels;
        input.left = input.right = input.middle = false;
        input.gui = input.tileContainer = false;
        input.command = InputCommandState::infoOnly;
    }
    void mouseReleased() { ++releases; }
    void checkInputCommand() { ++worldCommands; }
};

//! Supplies game state touched by the unchanged production cancellation method.
struct GameMode : AbstractApplicationMode
{
    bool mPendingHandDrop = true;
    float mMiddleDragDistance = 12.0f;
    Selection mPlayerSelection;
    int selectedTiles = 8, clears = 0;
    void unselectAllTiles() { selectedTiles = 0; ++clears; }
    void cancelMouseInput();
};

//! Supplies editor state touched by the unchanged production cancellation method.
struct EditorMode : AbstractApplicationMode
{
    struct Marker { bool isExtensible = true; } mTileMarker;
    Selection mPlayerSelection;
    int selectedTiles = 8, clears = 0;
    void unselectAllTiles() { selectedTiles = 0; ++clears; }
    void cancelMouseInput();
};

//! Checks that cancellation cleans up shared state without release validation.
void checkShared(const AbstractApplicationMode& mode)
{
    assert(!mode.input.left && !mode.input.right && !mode.input.middle);
    assert(!mode.input.gui && !mode.input.tileContainer);
    assert(mode.input.command == InputCommandState::infoOnly);
    assert(mode.baseCancels == 1);
    assert(mode.releases == 0 && mode.worldCommands == 0);
}
'''

MAIN = r'''
//! Checks cancellation of transient selections, persistent tools and repeated losses.
int main()
{
    GameMode game;
    game.cancelMouseInput();
    checkShared(game);
    assert(!game.mPendingHandDrop && game.mMiddleDragDistance == 0.0f);
    assert(game.mPlayerSelection.action == SelectedAction::none);
    assert(game.selectedTiles == 0 && game.clears == 1);
    ODFrameListener& listener = ODFrameListener::getSingleton();
    assert(listener.axes.size() == 2 && listener.values.size() == 2);
    assert(listener.axes[0] == CameraManager::zeroRandomRotateX);
    assert(listener.axes[1] == CameraManager::zeroRandomRotateY);
    assert(listener.values[0] == 0.0 && listener.values[1] == 0.0);

    GameMode gameTool;
    gameTool.mPlayerSelection.action = SelectedAction::buildRoom;
    gameTool.cancelMouseInput();
    checkShared(gameTool);
    assert(gameTool.mPlayerSelection.action == SelectedAction::buildRoom);
    assert(gameTool.selectedTiles == 0 && !gameTool.mPendingHandDrop);
    gameTool.cancelMouseInput();
    assert(gameTool.mPlayerSelection.action == SelectedAction::buildRoom);
    assert(gameTool.worldCommands == 0 && gameTool.releases == 0);

    EditorMode editor;
    editor.cancelMouseInput();
    checkShared(editor);
    assert(!editor.mTileMarker.isExtensible);
    assert(editor.mPlayerSelection.action == SelectedAction::none);
    assert(editor.selectedTiles == 0 && editor.clears == 1);

    EditorMode editorTool;
    editorTool.mPlayerSelection.action = SelectedAction::buildRoom;
    editorTool.cancelMouseInput();
    checkShared(editorTool);
    assert(editorTool.mPlayerSelection.action == SelectedAction::buildRoom);
    assert(!editorTool.mTileMarker.isExtensible && editorTool.selectedTiles == 0);
    editorTool.cancelMouseInput();
    assert(editorTool.worldCommands == 0 && editorTool.releases == 0);
}
'''


def main():
    """Compile and execute the focused probe using the configured Windows compiler."""
    production = function("source/modes/GameMode.cpp", "void GameMode::cancelMouseInput()")
    production += "\n" + function("source/modes/EditorMode.cpp", "void EditorMode::cancelMouseInput()")
    vcvars = Path("C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/VC/Auxiliary/Build/vcvars64.bat")
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        cpp = directory / "probe.cpp"
        cpp.write_text(PREAMBLE + production + MAIN, encoding="utf-8")
        batch = directory / "run.cmd"
        batch.write_text(
            f'@echo off\ncall "{vcvars}" >nul\n'
            f'cl /nologo /EHsc /std:c++14 "{cpp}" /Fe:"{directory / "probe.exe"}" '
            f'/Fo:"{directory / "probe.obj"}"\n'
            'if errorlevel 1 exit /b 1\n'
            f'"{directory / "probe.exe"}"\nexit /b %errorlevel%\n',
            encoding="utf-8",
        )
        subprocess.run(["cmd", "/d", "/c", str(batch)], cwd=directory, check=True)
    print("production game/editor pointer cancellation probe passed")


if __name__ == "__main__":
    main()
