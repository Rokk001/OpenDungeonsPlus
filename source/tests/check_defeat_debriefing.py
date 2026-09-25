"""Exercise the defeat debriefing without a game: time text, input routing, one-shot opening, leaving to the menu.

DefeatSequence.h is compiled as it is. The GameMode functions that open the debriefing and handle its button, the
guard at the top of the input handlers and the two hand-over functions of ModeManager.h are cut out of the production
sources by signature and compiled against small mocks. The mocked window tree is generated from the real layout file.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ElementTree

repo = Path(__file__).resolve().parents[2]
game_mode = (repo / 'source/modes/GameMode.cpp').read_text()
sequence_header = (repo / 'source/modes/DefeatSequence.h').read_text()
mode_manager = (repo / 'source/modes/ModeManager.h').read_text()
menu_main = (repo / 'source/modes/MenuModeMain.cpp').read_text()
layout_path = repo / 'gui/WindowDefeatDebriefing.layout'


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def constant(name):
    match = re.search(r'^const std::string ' + name + r' = .*;$', game_mode, re.MULTILINE)
    assert match, name
    return match.group(0)


def handler_guard(signature):
    """The part of an input handler in front of its first game statement, ending in a sentinel return."""
    start = game_mode.index(signature)
    end = game_mode.index('    resetIdleHand();', start)
    return game_mode[start:end].replace('GameMode::', 'Probe::') + '    return false;\n}\n'


def layout_windows():
    """Paths (below the root window) of all windows of the real layout with their Visible property."""
    root = ElementTree.parse(layout_path).getroot().find('Window')
    found = []

    def walk(node, prefix):
        for child in node.findall('Window'):
            path = prefix + child.get('name')
            visible = True
            for prop in child.findall('Property'):
                if prop.get('name') == 'Visible':
                    visible = prop.get('value') != 'False'
            found.append((path, visible))
            walk(child, path + '/')

    walk(root, '')
    return found


windows = layout_windows()

probe = r'''
#include <cmath>
#include <cstdint>
#include <functional>
#include <iostream>
#include <map>
#include <string>
#include <vector>
#include "modes/DefeatSequence.h"

std::vector<std::string> gLog;
#define OD_LOG_INF(x) gLog.push_back(x)
int gMissing = 0, gLayoutLoads = 0, gMoveInjected = 0, gDownInjected = 0, gUpInjected = 0;
int gCursorShown = 0, gCursorHidden = 0, gModeRequests = 0;
int gLastMode = 0;
namespace OIS {struct MouseEvent {};struct KeyEvent {};enum MouseButtonID {MB_Left};}
namespace CEGUI
{
typedef unsigned char utf8;
struct EventArgs {};
struct PushButton {static const std::string EventClicked;};
const std::string PushButton::EventClicked = "Clicked";
namespace Event
{
struct Connection {};
template<typename T> struct Invoker
{
    bool (T::*function)(const EventArgs&);
    T* object;
    bool operator()() {EventArgs args;return (object->*function)(args);}
};
struct Subscriber
{
    std::function<bool()> handler;
    template<typename T> Subscriber(bool (T::*function)(const EventArgs&), T* object)
    {
        Invoker<T> invoker = {function, object};
        handler = invoker;
    }
};
}
struct Window
{
    bool visible = true;bool alwaysOnTop = false;std::string text;
    std::map<std::string, Window*> byPath;
    std::vector<Window*> children;
    std::function<bool()> onClick;
    void hide() {visible = false;}
    void setAlwaysOnTop(bool value) {alwaysOnTop = value;}
    void addChild(Window* child) {children.push_back(child);}
    void setText(const std::string& value) {text = value;}
    void setText(const utf8* value) {text = reinterpret_cast<const char*>(value);}
    Window* getChild(const std::string& path)
    {
        std::map<std::string, Window*>::iterator it = byPath.find(path);
        if(it == byPath.end()) {++gMissing;static Window dummy;return &dummy;}
        return it->second;
    }
    Event::Connection subscribeEvent(const std::string&, const Event::Subscriber& subscriber)
    {
        onClick = subscriber.handler;
        return Event::Connection();
    }
    void add(const std::string& path, bool isVisible)
    {
        Window* window = new Window();window->visible = isVisible;byPath[path] = window;
    }
};
struct WindowManager
{
    static WindowManager& getSingleton() {static WindowManager manager;return manager;}
    Window* loadLayoutFromFile(const std::string& name)
    {
        ++gLayoutLoads;
        if(name != "WindowDefeatDebriefing.layout") ++gMissing;
        Window* root = new Window();
@@TREE@@
        return root;
    }
};
struct MouseCursor {void setVisible(bool visible) {if(visible) ++gCursorShown; else ++gCursorHidden;}};
struct GUIContext
{
    MouseCursor cursor;
    MouseCursor& getMouseCursor() {return cursor;}
    bool injectMouseButtonDown(int) {++gDownInjected;return true;}
    bool injectMouseButtonUp(int) {++gUpInjected;return true;}
};
struct System
{
    GUIContext context;
    static System& getSingleton() {static System system;return system;}
    GUIContext& getDefaultGUIContext() {return context;}
};
}
namespace Gui {inline int convertButton(OIS::MouseButtonID) {return 0;}}
struct AbstractApplicationMode {bool mouseMoved(const OIS::MouseEvent&) {++gMoveInjected;return true;}};
struct ODApplication {static double turnsPerSecond;};
double ODApplication::turnsPerSecond = 1.4;
struct Player {std::string nick;const std::string& getNick() const {return nick;}};
struct GameMap
{
    Player player;int64_t turn = 0;
    Player* getLocalPlayer() {return &player;}
    int64_t getTurnNumber() const {return turn;}
};
struct ModeManager
{
    enum ModeType {NONE = 0, ADVERTISMENT = 1, MENU_MAIN};
    bool mOpenSkirmishSubMenu = false;
    void requestMode(ModeType mode, bool = true) {++gModeRequests;gLastMode = mode;}
@@REQUESTMAINMENU@@
@@CONSUMEREQUEST@@
};
@@CONSTANTS@@

class GameMode
{
public:
    GameMode():mRootWindow(&mRoot),mGameMap(&mMap),mModeManager(&mManager)
    {
        mDefeatSubtitle = &subtitle;mDefeatCameraMarker = &marker;
        mRoot.children.push_back(&subtitle);mRoot.children.push_back(&marker);
    }
    void addEventConnection(CEGUI::Event::Connection) {}
    void onDefeatSequenceFinished();
    void showDefeatDebriefing();
    bool onClickDefeatDebriefingConfirm(const CEGUI::EventArgs& arg);
    DefeatSequence mDefeatSequence;
    CEGUI::Window* mDefeatSubtitle = nullptr;
    CEGUI::Window* mDefeatCameraMarker = nullptr;
    CEGUI::Window* mDefeatDebriefing = nullptr;
    CEGUI::Window subtitle, marker, mRoot;
    CEGUI::Window* mRootWindow;
    GameMap mMap;
    GameMap* mGameMap;
    ModeManager mManager;
    ModeManager* mModeManager;
};
@@FINISHED@@
@@SHOW@@
@@CONFIRM@@

class Probe : public AbstractApplicationMode
{
public:
    DefeatSequence mDefeatSequence;
    bool mouseMoved(const OIS::MouseEvent &arg);
    bool mousePressed(const OIS::MouseEvent& arg, OIS::MouseButtonID id);
    bool mouseReleased(const OIS::MouseEvent &arg, OIS::MouseButtonID id);
    bool keyPressed(const OIS::KeyEvent& arg);
    bool keyReleased(const OIS::KeyEvent &arg);
};
@@MOVED@@
@@PRESSED@@
@@RELEASED@@
@@KEYDOWN@@
@@KEYUP@@

int gChecks = 0, gFailures = 0;
void check(bool ok, const char* msg) {++gChecks;if(!ok){++gFailures;std::cout << "FAIL " << msg << '\n';}}
typedef DefeatSequence DS;

struct Routing {bool moved, pressed, released, keyDown, keyUp;int moves, downs, ups;};
Routing route(Probe& probe)
{
    gMoveInjected = gDownInjected = gUpInjected = 0;
    OIS::MouseEvent mouse;OIS::KeyEvent key;
    Routing r;
    r.moved = probe.mouseMoved(mouse);
    r.pressed = probe.mousePressed(mouse, OIS::MB_Left);
    r.released = probe.mouseReleased(mouse, OIS::MB_Left);
    r.keyDown = probe.keyPressed(key);
    r.keyUp = probe.keyReleased(key);
    r.moves = gMoveInjected;r.downs = gDownInjected;r.ups = gUpInjected;
    return r;
}

void finish(DefeatSequence& sequence)
{
    sequence.start(1, 3, 4);
    while(!sequence.advance(0.25f)) {}
}

int main()
{
    // Elapsed time: turn number over turns per second, written as mm:ss
    check(debriefingElapsedSeconds(0, 1.4) == 0, "no turn yet: 0 s");
    check(debriefingElapsedSeconds(1, 1.4) == 0, "one turn is less than a second");
    check(debriefingElapsedSeconds(84, 1.4) == 60, "84 turns at 1.4 per second are 60 s");
    check(debriefingElapsedSeconds(-5, 1.4) == 0, "negative turn number: 0 s");
    check(debriefingElapsedSeconds(100, 0.0) == 0 && debriefingElapsedSeconds(100, -1.0) == 0, "no turn rate: 0 s");
    check(debriefingElapsedSeconds(100000, 1.4) == 71428, "large turn numbers do not overflow");
    check(formatDebriefingTime(0) == "00:00", "0 s");
    check(formatDebriefingTime(9) == "00:09", "single digit seconds are padded");
    check(formatDebriefingTime(59) == "00:59", "59 s");
    check(formatDebriefingTime(60) == "01:00", "60 s");
    check(formatDebriefingTime(600) == "10:00", "10 minutes");
    check(formatDebriefingTime(3599) == "59:59", "3599 s");
    check(formatDebriefingTime(3600) == "1:00:00", "one hour");
    check(formatDebriefingTime(3661) == "1:01:01", "over an hour");
    check(formatDebriefingTime(36000) == "10:00:00", "ten hours");
    check(formatDebriefingTime(-7) == "00:00", "negative seconds");

    // Timeline gate for the debriefing
    DefeatSequence gate;
    check(!gate.blocksInput() && !gate.allowsGuiInput() && !gate.isDebriefingOpen(), "not started: nothing blocked, no debriefing");
    check(!gate.openDebriefing() && !gate.confirmDebriefing(), "not started: neither open nor confirm work");
    gate.start(1, 3, 4);
    check(gate.blocksInput() && !gate.allowsGuiInput(), "started: game and interface blocked");
    check(!gate.openDebriefing() && !gate.allowsGuiInput(), "the debriefing cannot open before the end");
    check(!gate.confirmDebriefing(), "confirm before the debriefing does nothing");
    while(!gate.advance(0.25f)) {}
    check(gate.blocksInput() && !gate.allowsGuiInput(), "at the end but before the debriefing: still blocked");
    check(gate.openDebriefing() && gate.isDebriefingOpen() && gate.blocksInput() && gate.allowsGuiInput(), "the debriefing opens once: game blocked, interface reachable");
    check(!gate.openDebriefing(), "the debriefing does not open twice");
    check(gate.confirmDebriefing() && !gate.confirmDebriefing() && !gate.confirmDebriefing(), "confirm succeeds exactly once");

    // Input routing through the real handler guards
    {
        Probe probe;
        Routing r = route(probe);
        check(!r.moved && !r.pressed && !r.released && !r.keyDown && !r.keyUp && r.moves == 0 && r.downs == 0 && r.ups == 0, "before the sequence: everything reaches the game, nothing is injected here");
        probe.mDefeatSequence.start(1, 3, 4);
        r = route(probe);
        check(r.moved && r.pressed && r.released && r.keyDown && r.keyUp, "sequence running: all input is swallowed");
        check(r.moves == 0 && r.downs == 0 && r.ups == 0, "sequence running: nothing reaches the interface either");
        while(!probe.mDefeatSequence.advance(0.25f)) {}
        r = route(probe);
        check(r.moved && r.pressed && r.released && r.keyDown && r.keyUp && r.moves == 0 && r.downs == 0 && r.ups == 0, "black screen before the debriefing: still fully blocked");
        probe.mDefeatSequence.openDebriefing();
        r = route(probe);
        check(r.moved && r.pressed && r.released && r.keyDown && r.keyUp, "debriefing: the game gets no input (every handler returns before the game code)");
        check(r.moves == 1 && r.downs == 1 && r.ups == 1, "debriefing: mouse move, press and release reach the interface once each");
    }

    // The finished hook and the debriefing window
    {
        GameMode mode;
        mode.mMap.player.nick = "Keeper";
        mode.mMap.turn = 84;
        finish(mode.mDefeatSequence);
        gCursorShown = gCursorHidden = 0;
        mode.onDefeatSequenceFinished();
        check(gLayoutLoads == 1 && mode.mDefeatDebriefing != nullptr, "the hook loads the debriefing layout");
        check(mode.mRoot.children.size() == 3 && mode.mRoot.children[2] == mode.mDefeatDebriefing && mode.mDefeatDebriefing->alwaysOnTop, "the window is added to the game sheet, on top");
        check(!mode.subtitle.visible && !mode.marker.visible, "subtitle and camera marker make room");
        check(mode.mDefeatDebriefing->byPath["Panel/PlayerName"]->text == "Keeper", "player name shown");
        check(mode.mDefeatDebriefing->byPath["Panel/Outcome"]->text == "Level won: No", "outcome line");
        check(mode.mDefeatDebriefing->byPath["Panel/Elapsed"]->text == "Time elapsed: 01:00", "elapsed time line");
        check(mode.mDefeatDebriefing->byPath["Panel/StatisticsArea"]->visible == false, "the statistics area exists and stays hidden while empty");
        check(gCursorShown == 1 && gCursorHidden == 0, "the pointer is shown again");
        check(mode.mDefeatDebriefing->byPath["Panel/ConfirmButton"]->onClick != nullptr, "the confirm button is connected");
        mode.onDefeatSequenceFinished();
        mode.onDefeatSequenceFinished();
        check(gLayoutLoads == 1 && gCursorShown == 1, "calling the hook again changes nothing");
        check(gMissing == 0, "every window the code asks for exists in the layout");

        // Leaving: exactly one request for the main menu, with the sub-menu hand-over
        CEGUI::Window* button = mode.mDefeatDebriefing->byPath["Panel/ConfirmButton"];
        check(gModeRequests == 0 && !mode.mManager.mOpenSkirmishSubMenu, "nothing requested before the click");
        button->onClick();
        button->onClick();
        check(gModeRequests == 1 && gLastMode == ModeManager::MENU_MAIN, "two clicks request the main menu exactly once");
        check(mode.mManager.consumeSkirmishSubMenuRequest(), "the hand-over asks the menu to open the skirmish sub-menu");
        check(!mode.mManager.consumeSkirmishSubMenuRequest(), "the hand-over is consumed once");
    }
    {
        GameMode mode;
        gModeRequests = 0;
        CEGUI::EventArgs args;
        mode.mDefeatSequence.start(1, 3, 4);
        mode.onClickDefeatDebriefingConfirm(args);
        check(gModeRequests == 0 && !mode.mManager.mOpenSkirmishSubMenu, "a click without an open debriefing leaves nothing");
        GameMode early;
        early.onDefeatSequenceFinished();
        check(early.mDefeatDebriefing == nullptr && gLayoutLoads == 1, "the hook without a finished sequence opens nothing");
    }
    std::cout << "CHECKS=" << gChecks << " FAILURES=" << gFailures << '\n';
    return gFailures ? 1 : 0;
}
'''

tree = '\n'.join('        root->add("%s", %s);' % (path, 'true' if visible else 'false') for path, visible in windows)
constants = '\n'.join(constant(name) for name in ('DEFEAT_DEBRIEFING_OUTCOME', 'DEFEAT_DEBRIEFING_ELAPSED'))
for marker, text in (
        ('@@TREE@@', tree),
        ('@@CONSTANTS@@', constants),
        ('@@REQUESTMAINMENU@@', function(mode_manager, 'void requestMainMenuWithSkirmishSubMenu(')),
        ('@@CONSUMEREQUEST@@', function(mode_manager, 'bool consumeSkirmishSubMenuRequest(')),
        ('@@FINISHED@@', function(game_mode, 'void GameMode::onDefeatSequenceFinished(')),
        ('@@SHOW@@', function(game_mode, 'void GameMode::showDefeatDebriefing(')),
        ('@@CONFIRM@@', function(game_mode, 'bool GameMode::onClickDefeatDebriefingConfirm(')),
        ('@@MOVED@@', handler_guard('bool GameMode::mouseMoved(')),
        ('@@PRESSED@@', handler_guard('bool GameMode::mousePressed(')),
        ('@@RELEASED@@', handler_guard('bool GameMode::mouseReleased(')),
        ('@@KEYDOWN@@', handler_guard('bool GameMode::keyPressed(')),
        ('@@KEYUP@@', handler_guard('bool GameMode::keyReleased('))):
    assert marker in probe, marker
    probe = probe.replace(marker, text)

# Static wiring checks on the production sources.
for signature in ('bool GameMode::keyPressed(', 'bool GameMode::keyReleased('):
    body = function(game_mode, signature)
    assert body[body.index('{'):].startswith('{\n    if(mDefeatSequence.blocksInput())\n        return true;\n'), signature
for signature in ('bool GameMode::mouseMoved(', 'bool GameMode::mousePressed(', 'bool GameMode::mouseReleased('):
    body = function(game_mode, signature)
    assert body[body.index('{'):].startswith(
        '{\n    if(mDefeatSequence.blocksInput())\n    {\n        if(mDefeatSequence.allowsGuiInput())\n'), signature
print('WIRING OK: keys stay fully blocked, the mouse handlers inject into the interface only while the debriefing is open')
activate = function(menu_main, 'void MenuModeMain::activate(')
assert activate.index('showMainMenuButtons(true);') < activate.index('consumeSkirmishSubMenuRequest()') < activate.index('giveFocus();')
assert 'toggleSubMenu(WINDOW_SKIRMISH)' in activate
assert 'mDefeatDebriefing' in function(game_mode, 'void GameMode::destroyDefeatWindows(')
assert 'child == mDefeatDebriefing' in function(game_mode, 'void GameMode::hideInterfaceForDefeat(')
assert 'destroyDefeatWindows();' in function(game_mode, 'GameMode::~GameMode(')
print('WIRING OK: the main menu consumes the hand-over, the debriefing stays visible and is destroyed with the mode')
names = [path for path, _ in windows]
for needed in ('Panel/Title', 'Panel/PlayerName', 'Panel/Outcome', 'Panel/Elapsed', 'Panel/StatisticsArea', 'Panel/ConfirmButton'):
    assert needed in names, needed
assert 'OpenDungeonsIcons/CheckIcon' in layout_path.read_text()
assert re.search(r'\bauto\b', probe) is None and re.search(r'\bauto\b', sequence_header) is None
print('STYLE OK: no auto in the new code or in the fixture')
for path in (layout_path, Path(__file__), repo / 'source/modes/DefeatSequence.h', repo / 'source/modes/GameMode.cpp',
             repo / 'source/modes/GameMode.h', repo / 'source/modes/ModeManager.h', repo / 'source/modes/MenuModeMain.cpp'):
    bad = [b for b in path.read_bytes() if b < 32 and b not in (9, 10, 13)]
    assert not bad, path
print('BYTES OK: no stray control characters')

with tempfile.TemporaryDirectory(prefix='odp-defeat-debriefing-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', '/I', str(repo / 'source'), 'check.cpp', '/Fecheck.exe'],
                   cwd=work, check=True)
    # Windows may block a freshly compiled executable (WinError 4551) for a moment
    for attempt in range(4):
        try:
            subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
            break
        except OSError as error:
            if attempt == 3:
                raise
            print('retrying after', error)
            time.sleep(2)
