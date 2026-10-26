"""Exercise the defeat follow-ups without a game: menu flight timing, its use by the main menu, camera symbol, stone imagery.

MenuFlight.h is compiled as it is. MenuModeMain::onFrameStarted and the hand-over functions of ModeManager.h are cut out of
the production sources and compiled against small mocks. The image names used by the layout and by GameMode.cpp are checked
against the real imagesets and the icon picture.
"""
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ElementTree

from PIL import Image

repo = Path(__file__).resolve().parents[2]
game_mode = (repo / 'source/modes/GameMode.cpp').read_text()
mode_manager = (repo / 'source/modes/ModeManager.h').read_text()
menu_main = (repo / 'source/modes/MenuModeMain.cpp').read_text()
menu_scene = (repo / 'source/renderscene/RenderSceneMenu.cpp').read_text()
flight_header = (repo / 'source/render/MenuFlight.h').read_text()
gui = repo / 'gui'


# Extract one complete production function for the isolated probe.
def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def imagesets():
    """Every image of the real imagesets as 'Set/Image': (picture file, x, y, width, height)."""
    found = {}
    for path in sorted(gui.glob('*.imageset')):
        root = ElementTree.parse(path).getroot()
        for image in root.findall('Image'):
            found[root.get('name') + '/' + image.get('name')] = (
                gui / root.get('imagefile'), int(image.get('xPos')), int(image.get('yPos')),
                int(image.get('width')), int(image.get('height')))
    return found


images = imagesets()

probe = r'''
#include <cmath>
#include <iostream>
#include <string>
#include "render/MenuFlight.h"

int gChecks = 0, gFailures = 0;
//! \brief Records an assertion without stopping the remaining regression checks.
void check(bool ok, const char* msg) {++gChecks;if(!ok){++gFailures;std::cout << "FAIL " << msg << '\n';}}

namespace Ogre {struct FrameEvent {};}
namespace CEGUI {struct EventArgs {};}
struct AbstractModeManager {enum ModeType {NONE, MENU_MAIN, MENU_REPLAY, ADVERTISMENT};};
const std::string WINDOW_SKIRMISH = "SkirmishSubMenuWindow";
int gToggles = 0;
int gShown = 0;
int gChanged = 0;
bool gButtonsVisible = false;
int gOverviewReveals = 0;
std::string gToggled;
MenuFlight gFlight;
struct ODFrameListener
{
    //! \brief Returns the isolated listener sharing the production flight timer.
    static ODFrameListener& getSingleton() {static ODFrameListener listener;return listener;}
    //! \brief Reports whether the current arrival or destination timer is advancing.
    bool isMainMenuFlightActive() const {return gFlight.isActive();}
};

struct ModeManager
{
    enum ModeType {MENU_MAIN = 2};
    bool mOpenSkirmishSubMenu = false;
    bool mMainMenuArrivalRequested = false;
    //! \brief Accepts the original hand-over request without a full application mode switch.
    void requestMode(ModeType, bool = true) {}
@@REQUESTMAINMENU@@
@@CONSUMEREQUEST@@
@@CONSUMEARRIVAL@@
};

class MenuModeMain
{
public:
    void onFrameStarted(const Ogre::FrameEvent& evt);
    //! \brief Represents the second leg to the cave, retaining its delayed pane reveal.
    bool toggleSubMenu(const std::string& name)
    {++gToggles;gToggled = name;mPendingSubMenu = name;return gFlight.start();}
    //! \brief Records an existing pane becoming visible after arrival.
    void showSubMenu(const std::string& name) {++gShown;gToggled = name;}
    //! \brief Records overview visibility at the same production arrival boundary.
    void showMainMenuButtons(bool visible) {gButtonsVisible = visible;if(visible) ++gOverviewReveals;}
    //! \brief Records a deferred mode request once its flight completes.
    bool changeModeEvent(AbstractModeManager::ModeType, const CEGUI::EventArgs&) {++gChanged;return true;}
    bool mSkirmishSubMenuPending = false;
    bool mOverviewPending = false;
    std::string mPendingSubMenu;
    AbstractModeManager::ModeType mPendingMode = AbstractModeManager::NONE;
};
@@FRAME@@

namespace S = MenuFlightSettings;

//! \brief Exercises three-dimensional flight timing and the two-leg defeat menu hand-over.
int main()
{
    // Pure timing and path functions
    check(MenuFlight::progressAt(-1.0f) == 0.0f && MenuFlight::progressAt(0.0f) == 0.0f, "progress: before and at the start is 0");
    check(MenuFlight::progressAt(S::DURATION * 0.5f) == 0.5f, "progress: halfway");
    check(MenuFlight::progressAt(S::DURATION) == 1.0f && MenuFlight::progressAt(100.0f) == 1.0f, "progress: at and after the end is 1");
    check(S::DURATION >= 1.5f && S::DURATION <= 2.5f, "the flight lasts between 1.5 and 2.5 seconds");
    check(MenuFlight::easedProgressAt(0.0f) == 0.0f && MenuFlight::easedProgressAt(-5.0f) == 0.0f, "ease: starts at zero");
    check(MenuFlight::easedProgressAt(S::DURATION) == 1.0f && MenuFlight::easedProgressAt(S::DURATION + 10.0f) == 1.0f, "ease: ends exactly at the configured endpoint");
    bool monotonic = true;
    float last = MenuFlight::easedProgressAt(0.0f);
    for(int i = 1; i <= 300; ++i)
    {
        const float progress = MenuFlight::easedProgressAt(S::DURATION * i / 300.0f);
        monotonic = monotonic && progress >= last && progress >= 0.0f && progress <= 1.0f;
        last = progress;
    }
    check(monotonic, "ease: advances monotonically without overshooting");
    check(MenuFlight::easedProgressAt(S::DURATION * 0.01f) < 0.001f &&
        1.0f - MenuFlight::easedProgressAt(S::DURATION * 0.99f) < 0.001f, "ease: slows at both endpoints");

    // The state
    MenuFlight flight;
    check(!flight.isActive() && flight.getProgress() == 0.0f, "idle: no active path");
    check(!flight.advance(1.0f) && flight.getProgress() == 0.0f && !flight.isActive(), "idle: advancing does nothing");
    check(!flight.start(0.0f) && !flight.start(-1.0f), "start: rejects nonpositive durations");
    check(flight.start() && flight.isActive() && flight.getProgress() == 0.0f, "start: active at the first pose");
    check(!flight.start(), "start: a second start while running is refused");
    check(!flight.advance(S::MAX_STEP * 4.0f) && flight.isActive(), "one slow frame is clamped and does not end the flight");
    check(flight.getProgress() > 0.0f && flight.getProgress() < 1.0f, "in the middle the camera is between its endpoints");
    check(!flight.advance(-1.0f) && flight.isActive(), "a negative step does nothing");
    int steps = 0;
    bool ended = false;
    while(!ended && steps < 1000)
    {
        ended = flight.advance(0.1f);
        ++steps;
    }
    check(ended && !flight.isActive() && flight.getProgress() == 1.0f, "the flight reaches its exact endpoint");
    check(steps >= 15 && steps <= 25, "configured duration is respected after a clamped slow frame");
    check(!flight.advance(0.1f), "the end is reported once");
    check(flight.start(), "a new request may start a new flight after the end");
    flight.reset();
    check(!flight.isActive() && flight.getProgress() == 0.0f, "reset stops the flight");

    // The hand-over flag works exactly once and the sub-menu waits for the end of the flight
    ModeManager manager;
    check(!manager.consumeSkirmishSubMenuRequest(), "no request: nothing to consume");
    manager.requestMainMenuWithSkirmishSubMenu();
    check(manager.consumeSkirmishSubMenuRequest() && !manager.consumeSkirmishSubMenuRequest(), "the hand-over is consumed exactly once");
    manager.mMainMenuArrivalRequested = true;
    check(manager.consumeMainMenuArrivalRequest() && !manager.consumeMainMenuArrivalRequest(), "normal game-return arrival is consumed exactly once");

    MenuModeMain menu;
    Ogre::FrameEvent event;
    menu.onFrameStarted(event);
    check(gToggles == 0, "without a pending request the frame hook never shows a sub-menu");
    menu.mSkirmishSubMenuPending = true;
    gFlight.start();
    for(int i = 0; i < 100 && gFlight.isActive(); ++i)
    {
        menu.onFrameStarted(event);
        gFlight.advance(0.1f);
    }
    check(gToggles == 0 && menu.mSkirmishSubMenuPending && !gButtonsVisible, "during the flight the sub-menu and overview entries stay hidden");
    menu.onFrameStarted(event);
    check(gToggles == 1 && gToggled == WINDOW_SKIRMISH && !menu.mSkirmishSubMenuPending && gShown == 0 && gFlight.isActive(), "after arrival the cave flight starts before showing the skirmish pane");
    for(int i = 0; i < 100 && gFlight.isActive(); ++i)
    {
        menu.onFrameStarted(event);
        gFlight.advance(0.1f);
    }
    check(gShown == 0, "during the cave flight the skirmish pane remains hidden");
    menu.onFrameStarted(event);
    menu.onFrameStarted(event);
    check(gToggles == 1 && gShown == 1 && gOverviewReveals == 0, "the pane is revealed exactly once after both flights without flashing overview entries");
    menu.mOverviewPending = true;
    gFlight.start();
    menu.onFrameStarted(event);
    check(menu.mOverviewPending && !gButtonsVisible, "overview entries remain hidden during the return flight");
    while(gFlight.isActive())
        gFlight.advance(0.1f);
    menu.onFrameStarted(event);
    menu.onFrameStarted(event);
    check(!menu.mOverviewPending && gButtonsVisible && gOverviewReveals == 1, "overview entries reappear exactly once on return arrival");
    menu.mPendingMode = AbstractModeManager::MENU_REPLAY;
    gFlight.start();
    menu.onFrameStarted(event);
    check(gChanged == 0, "the replay mode waits during the archive flight");
    while(gFlight.isActive())
        gFlight.advance(0.1f);
    menu.onFrameStarted(event);
    menu.onFrameStarted(event);
    check(gChanged == 1, "the replay pane opens exactly once at arrival");

    std::cout << "CHECKS=" << gChecks << " FAILURES=" << gFailures << '\n';
    return gFailures ? 1 : 0;
}
'''
probe = probe.replace('@@REQUESTMAINMENU@@', function(mode_manager, 'void requestMainMenuWithSkirmishSubMenu('))
probe = probe.replace('@@CONSUMEREQUEST@@', function(mode_manager, 'bool consumeSkirmishSubMenuRequest('))
probe = probe.replace('@@CONSUMEARRIVAL@@', function(mode_manager, 'bool consumeMainMenuArrivalRequest('))
probe = probe.replace('@@FRAME@@', function(menu_main, 'void MenuModeMain::onFrameStarted('))
assert '@@' not in probe

# The camera symbol: an image window with an image that exists and is not empty
create = function(game_mode, 'void GameMode::createDefeatWindows(')
assert 'createWindow("OD/StaticImage", "DefeatCameraMarker")' in create
assert 'setText("CAM")' not in create
marker = re.search(r'^const std::string DEFEAT_CAMERA_MARKER_IMAGE = "([^"]+)";$', game_mode, re.MULTILINE)
assert marker and 'setProperty("Image", DEFEAT_CAMERA_MARKER_IMAGE)' in create
assert marker.group(1) in images, marker.group(1)
picture, x, y, width, height = images[marker.group(1)]
pixels = Image.open(picture).convert('RGBA')
assert x + width <= pixels.width and y + height <= pixels.height
assert pixels.crop((x, y, x + width, y + height)).getchannel('A').getbbox() is not None, 'the camera icon is empty'
for name, (other, ox, oy, ow, oh) in images.items():
    if name != marker.group(1) and other == picture:
        assert x + width <= ox or ox + ow <= x or y + height <= oy or oy + oh <= y, 'overlaps ' + name
print('CAMERA OK: the marker is an image window with', marker.group(1), 'and that image is a non-empty cell that overlaps no other image')

# The layout only names images the imagesets have, and uses the stone surface
layout = ElementTree.parse(gui / 'WindowDefeatDebriefing.layout').getroot()
used = []
for window in layout.iter('Window'):
    for prop in window.findall('Property'):
        if prop.get('name') in ('Image', 'NormalImage', 'HoverImage', 'PushedImage'):
            used.append(prop.get('value'))
assert used and all(name in images for name in used), [name for name in used if name not in images]
assert 'ODHudSurface/Stone' in used and 'OpenDungeonsIcons/CheckIcon' in used
types = {window.get('name'): window.get('type') for window in layout.iter('Window')}
assert types['Background'] == 'OD/StaticImage' and types['Panel'] == 'OD/StaticImage'
scheme = (gui / 'ODSkin.scheme').read_text()
assert 'windowType="OD/StaticImage"' in scheme and 'ODHudSurface.imageset' in scheme
for needed in ('Panel/Title', 'Panel/PlayerName', 'Panel/Outcome', 'Panel/Elapsed', 'Panel/StatisticsArea', 'Panel/ConfirmButton'):
    node = layout.find('Window')
    for part in needed.split('/'):
        found = [child for child in node.findall('Window') if child.get('name') == part]
        assert found, needed
        node = found[0]
print('LAYOUT OK: every image name exists in the imagesets, the stone surface backs the screen and the panel, the table area and button remain')

# Wiring of the flight
activate = function(menu_main, 'void MenuModeMain::activate(')
assert activate.index('showMainMenuButtons(true);') < activate.index('consumeSkirmishSubMenuRequest()') < activate.index('createMainMenuScene();') < activate.index('startMainMenuFlight();')
assert 'toggleSubMenu(WINDOW_SKIRMISH)' not in activate
assert 'consumeMainMenuArrivalRequest() || mSkirmishSubMenuPending' in activate
assert 'mSkirmishSubMenuPending = false;' in activate
update = function(menu_scene, 'void RenderSceneMenu::updateMenu(')
assert 'mFlight.advance(timeSinceLastFrame)' in update and 'samplePath(' in update
assert 'flightScale' not in update
assert 'mFlight.reset();' in function(menu_scene, 'void RenderSceneMenu::freeMenu(')
assert 'MenuFlight' in (repo / 'source/renderscene/RenderSceneMenu.h').read_text()
print('WIRING OK: configured 3D flights replace the picture zoom and the defeat pane waits for arrival and the cave destination')

assert re.search(r'\bauto\b', probe) is None and re.search(r'\bauto\b', flight_header) is None
assert re.search(r'\bauto\b', function(menu_main, 'void MenuModeMain::onFrameStarted(')) is None
print('STYLE OK: no auto in the new code or in the fixture')
for path in (Path(__file__), repo / 'source/render/MenuFlight.h', repo / 'source/renderscene/RenderSceneMenu.cpp', repo / 'source/renderscene/RenderSceneMenu.h',
             repo / 'source/render/ODFrameListener.cpp', repo / 'source/render/ODFrameListener.h', repo / 'source/modes/MenuModeMain.cpp',
             repo / 'source/modes/MenuModeMain.h', repo / 'source/modes/GameMode.cpp', repo / 'gui/WindowDefeatDebriefing.layout',
             repo / 'gui/ODIcons.imageset'):
    bad = [b for b in path.read_bytes() if b < 32 and b not in (9, 10, 13)]
    assert not bad, path
print('BYTES OK: no stray control characters')

with tempfile.TemporaryDirectory(prefix='odp-defeat-menu-flight-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++17', '/I', str(repo / 'source'), 'check.cpp', '/Fecheck.exe'],
                   cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=120)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=30)
