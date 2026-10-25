"""Update the heart badge with the real CEGUI Ogre renderer and read back what the badge image shows.

The heart ring in the top left corner did not move when the heart was hit. The badge image
(OpenDungeonsIcons/ManaBadge) refers to the CEGUI texture "ManaBadge"; a window caches its geometry
together with the Ogre texture it had when it was drawn (CEGUI's OgreGeometryBuffer::appendGeometry
stores getOgreTexture() in the batch). OgreTexture::loadFromMemory makes a new Ogre texture on every call,
so the redrawn ring went into a texture the badge never showed again.

This check links OgreMain and the CEGUI Ogre renderer, opens a hidden window, bootstraps CEGUI, creates
the badge texture the way Gui.cpp does, and then:
- reproduces the cause: loadFromMemory replaces the Ogre texture;
- runs the real Gui::updateHeartBadge, drawBadgePixels and painted composition, cut out of Gui.cpp by signature, and checks
  that the Ogre texture stays the same and that its pixels, read back from the texture, are the ring of
  the new health (and differ from the full ring).
"""
from pathlib import Path
import argparse
import os
import shutil
import re
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--loading-screens', action='store_true', help='Also render the production loading material at both requested ratios')
parser.add_argument('--loading-output', type=Path, help='Private destination for generated loading-screen renders')
parser.add_argument('--menu-scene', action='store_true', help='Also render the configured menu scene at 1920x1080')
parser.add_argument('--menu-output', type=Path, help='Private destination for the menu scene and comparison images')
parser.add_argument('--menu-reference', type=Path, help='Reference image placed beside the menu scene render')
args = parser.parse_args()
if args.loading_screens and args.loading_output is None:
    parser.error('--loading-screens requires --loading-output')
if args.menu_scene:
    if args.menu_output is None or args.menu_reference is None:
        parser.error('--menu-scene requires --menu-output and --menu-reference')
    if not args.menu_reference.is_file():
        parser.error('--menu-reference must name an existing image')
    if any((args.menu_output / name).exists() for name in ('menu-scene-1920x1080.png', 'menu-scene-compare.png')):
        parser.error('--menu-output already contains a menu render; select a fresh private directory')
# Both optional renders read the repository and output folder from the same probe arguments
if args.loading_screens and args.menu_scene:
    parser.error('--loading-screens and --menu-scene render in separate runs; pass only one of them')

repo = Path(__file__).resolve().parents[2]
deps = Path(os.environ.get('OD_DEPS_ROOT', str(Path.home() / 'od-deps')))
gui = (repo / 'source/render/Gui.cpp').read_text()
rules = repo / 'source/game/HeartHealthRing.h'


# Extract one complete production function for the existing native probe.
def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


update = function(gui, 'void Gui::updateHeartBadge(').replace('void Gui::updateHeartBadge(', 'void updateHeartBadge(')
badge_helpers = ('float badgeClamp(', 'void badgeMix(', 'void badgeSet(', 'float badgeNoise(', 'float badgeSmoothstep(', 'float badgeSmoothMin(',
                 'float badgeHash(', 'float badgeValueNoise(', 'float badgeFbm(', 'float badgeCircle(', 'float badgeTaper(', 'float badgeBox(',
                 'float badgeRound(', 'float badgeHeartDistance(', 'float badgeHeartVeins(', 'float badgeHeartHeight(', 'float badgeSkullDistance(',
                 'float badgeCoinHeight(', 'void badgeNormal(', 'float badgeDiffuse(', 'float badgeHalfway(', 'float badgeCavity(', 'void badgeFrame(', 'void badgeGemRing(', 'void badgeBeadRing(',
                 'void badgeHeartWell(', 'void badgeCoinWell(', 'void drawBadgePixels(')
painted_constants = gui[gui.index('//! Painted navigation atlas coordinates,'):gui.index('// Layout of the room, trap and spell buttons')]
badge_code = (painted_constants + 'const int BADGE_SIZE = 128;\n'
              + '\n'.join(function(gui, signature) for signature in badge_helpers)
              + '\n' + function(gui, 'void copyPaintedNavigationPixels(')
              + '\n' + function(gui, 'void applyPaintedBadgePixels(') + '\n')

probe = r'''
#include <cmath>
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <map>
#include <Ogre.h>
#include <OgreRectangle2D.h>
#include <OgreHardwarePixelBuffer.h>
#include <OgreRenderTexture.h>
#include <OgrePixelFormat.h>
#include <CEGUI/CEGUI.h>
#include <CEGUI/RendererModules/Ogre/Renderer.h>
#include <CEGUI/RendererModules/Ogre/Texture.h>
#include <OgreParticleSystem.h>
#include <RTShaderSystem/OgreShaderGenerator.h>
#include <Bites/OgreSGTechniqueResolverListener.h>
#include "RULES_HEADER"

BADGE_CODE
UPDATE
LOADING_HELPERS
//! \brief Records each assertion from the badge and optional menu probes.
void check(bool ok, const std::string& msg);
MENU_HELPERS

int gChecks = 0, gFailures = 0;
void check(bool ok, const std::string& msg) {++gChecks;if(!ok){++gFailures;std::cout << "FAIL " << msg << '\n';}}

//! \brief Reads the actual painted-size badge pixels from the existing Ogre texture.
std::vector<unsigned char> readBack(CEGUI::Texture& texture)
{
    Ogre::TexturePtr ogreTexture = static_cast<CEGUI::OgreTexture&>(texture).getOgreTexture();
    std::vector<unsigned char> pixels(PAINTED_BADGE_SIZE * PAINTED_BADGE_SIZE * 4);
    Ogre::PixelBox box(PAINTED_BADGE_SIZE, PAINTED_BADGE_SIZE, 1, ogreTexture->getFormat(), pixels.data());
    ogreTexture->getBuffer()->blitToMemory(box);
    return pixels;
}

// Is the ring pixel at an angle (degrees clockwise from the top) green? Spokes are grey, the groove is dark.
//! \brief Samples the unchanged health annulus in the composited 256-pixel badge.
bool ringGreen(const std::vector<unsigned char>& pixels, float angle)
{
    const float radians = angle * 3.14159265f / 180.0f;
    const int x = static_cast<int>((23.0f * std::sin(radians) + 32.0f) * PAINTED_BADGE_SIZE / 64.0f);
    const int y = static_cast<int>((-23.0f * std::cos(radians) + 32.0f) * PAINTED_BADGE_SIZE / 64.0f);
    const int i = (y * PAINTED_BADGE_SIZE + x) * 4;
    return pixels[i + 1] - pixels[i] > 40;
}

//! \brief Checks the real badge texture and optionally renders the production loading screen or the configured menu assets.
int main(int argc, char** argv)
{
    try
    {
    const std::string prefix = argv[1];
    Ogre::LogManager* logs = new Ogre::LogManager();
    logs->createLog("badge-Ogre.log", true, false, false);
    Ogre::Root* root = new Ogre::Root("", "", "");
    root->loadPlugin(prefix + "/bin/RenderSystem_GL3Plus");
    LOADING_CODEC
    MENU_PLUGINS
    root->setRenderSystem(root->getAvailableRenderers().front());
    root->initialise(false);
    Ogre::NameValuePairList options;
    options["hidden"] = "true";
    Ogre::RenderWindow* window = root->createRenderWindow("Badge", 256, 256, false, &options);
    // As the game: the shader generator supplies the GPU programs the GL3+ renderer needs
    Ogre::ResourceGroupManager& resources = Ogre::ResourceGroupManager::getSingleton();
    resources.addResourceLocation(prefix + "/Media/Main", "FileSystem", "OgreInternal");
    resources.addResourceLocation(prefix + "/Media/RTShaderLib", "FileSystem", "General");
    resources.addResourceLocation(std::string(argv[2]) + "/gui", "FileSystem", "General");
    resources.initialiseAllResourceGroups();
    paintedNavigationAtlas.load(PAINTED_NAVIGATION_ATLAS, Ogre::ResourceGroupManager::AUTODETECT_RESOURCE_GROUP_NAME);
    Ogre::RTShader::ShaderGenerator::initialize();
    Ogre::RTShader::ShaderGenerator* shaders = Ogre::RTShader::ShaderGenerator::getSingletonPtr();
    OgreBites::SGTechniqueResolverListener listener(shaders);
    Ogre::MaterialManager::getSingleton().addListener(&listener);
    Ogre::SceneManager* scene = root->createSceneManager("DefaultSceneManager");
    shaders->addSceneManager(scene);
    Ogre::MaterialManager::getSingleton().setActiveScheme(Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME);
    Ogre::Camera* camera = scene->createCamera("Camera");
    scene->getRootSceneNode()->createChildSceneNode()->attachObject(camera);
    window->addViewport(camera);
    CEGUI::OgreRenderer& renderer = CEGUI::OgreRenderer::bootstrapSystem(*window);

    // As Gui.cpp at start: the full ring, loaded once
    std::vector<unsigned char> full;
    drawBadgePixels(full, 0, 1.0f, false);
    applyPaintedBadgePixels(full, 0, false);
    CEGUI::Texture& badge = renderer.createTexture("ManaBadge");
    badge.loadFromMemory(full.data(), CEGUI::Sizef(PAINTED_BADGE_SIZE, PAINTED_BADGE_SIZE), CEGUI::Texture::PF_RGBA);
    const Ogre::TexturePtr shown = static_cast<CEGUI::OgreTexture&>(badge).getOgreTexture();
    check(readBack(badge) == full, "the full ring is in the badge texture");

    // The cause: loading again makes a new Ogre texture; a window that cached the first one keeps showing it
    {
        CEGUI::Texture& probe = renderer.createTexture("Probe");
        probe.loadFromMemory(full.data(), CEGUI::Sizef(PAINTED_BADGE_SIZE, PAINTED_BADGE_SIZE), CEGUI::Texture::PF_RGBA);
        const Ogre::Texture* first = static_cast<CEGUI::OgreTexture&>(probe).getOgreTexture().get();
        probe.loadFromMemory(full.data(), CEGUI::Sizef(PAINTED_BADGE_SIZE, PAINTED_BADGE_SIZE), CEGUI::Texture::PF_RGBA);
        const Ogre::Texture* second = static_cast<CEGUI::OgreTexture&>(probe).getOgreTexture().get();
        check(first != second, "reproduced: loadFromMemory replaces the Ogre texture the badge window had cached");
        renderer.destroyTexture("Probe");
    }

    // The production update after a hit: the same Ogre texture now holds the smaller ring
    updateHeartBadge(0.4f, true);
    std::vector<unsigned char> expected;
    drawBadgePixels(expected, 0, 0.4f, true);
    applyPaintedBadgePixels(expected, 0, true);
    check(static_cast<CEGUI::OgreTexture&>(badge).getOgreTexture().get() == shown.get(),
        "updateHeartBadge keeps the Ogre texture the badge window shows");
    const std::vector<unsigned char> after = readBack(badge);
    check(after == expected, "the shown texture holds the ring of the new health");
    check(after != full, "the shown ring is no longer the full ring");
    std::vector<unsigned char> peaceful;
    drawBadgePixels(peaceful, 0, 0.4f, false);
    applyPaintedBadgePixels(peaceful, 0, false);
    check(after != peaceful, "the painted badge retains the attack-colour change at the same health");
    updateHeartBadge(0.0f, false);
    std::vector<unsigned char> empty;
    drawBadgePixels(empty, 0, 0.0f, false);
    applyPaintedBadgePixels(empty, 0, false);
    check(readBack(badge) == empty && static_cast<CEGUI::OgreTexture&>(badge).getOgreTexture().get() == shown.get(),
        "a destroyed heart empties the shown ring");

    // Six segments: 0, 17, 50 and 100 percent and a partly filled segment, read back from the shown texture
    const float mids[6] = {30.0f, 90.0f, 150.0f, 210.0f, 270.0f, 330.0f};
    const float fractions[5] = {0.0f, 0.17f, 0.5f, 1.0f, 0.22f};
    const int expectedSegments[5] = {0, 1, 3, 6, 1};
    for(int f = 0; f < 5; ++f)
    {
        updateHeartBadge(fractions[f], false);
        const std::vector<unsigned char> shownPixels = readBack(badge);
        int green = 0;
        for(int k = 0; k < 6; ++k)
            green += ringGreen(shownPixels, mids[k]) ? 1 : 0;
        check(green == expectedSegments[f], "the shown ring has the whole segments of " + std::to_string(fractions[f]));
        check(!ringGreen(shownPixels, 0.0f) && !ringGreen(shownPixels, 60.0f) && !ringGreen(shownPixels, 180.0f),
            "the spokes of the shown ring are not green");
        if(f == 4)
            check(ringGreen(shownPixels, 75.0f) && !ringGreen(shownPixels, 110.0f),
                "the shown ring fills a partly covered segment only in part");
    }

    LOADING_RENDER
    MENU_RENDER
    CEGUI::OgreRenderer::destroySystem();
    Ogre::MaterialManager::getSingleton().removeListener(&listener);
    shaders->removeSceneManager(scene);
    Ogre::RTShader::ShaderGenerator::destroy();
    // The Ogre root is not deleted: its teardown after the CEGUI renderer crashes in this bare setup,
    // and the process ends here anyway
    }
    catch(const std::exception& e)
    {
        std::cout << "EXCEPTION " << e.what() << '\n';
        return 1;
    }
    std::cout << "CHECKS=" << gChecks << " FAILURES=" << gFailures << '\n';
    return gFailures ? 1 : 0;
}
'''
# Reuse the production background-rectangle material and fitting code in this existing GL3Plus/CEGUI probe.
loading_helpers = ''
loading_render = ''
if args.loading_screens:
    loading_source = (repo / 'source/render/LoadingScreen.cpp').read_text(encoding='utf-8')
    loading_helpers = function(loading_source, 'void fitLoadingImage(') + '\n' + function(loading_source, 'Ogre::MaterialPtr createLoadingMaterial(')
    loading_render = r'''
    const std::string repository = argv[2];
    const std::string output = argv[3];
    resources.createResourceGroup("Graphics");
    resources.addResourceLocation(repository + "/materials/textures/loading", "FileSystem", "Graphics");
    resources.initialiseResourceGroup("Graphics");
    resources.createResourceGroup("GUI");
    resources.addResourceLocation(repository + "/gui", "FileSystem", "GUI");
    resources.addResourceLocation(repository + "/gui/fonts", "FileSystem", "GUI");
    resources.addResourceLocation(repository + "/gui/schemas", "FileSystem", "GUI");
    resources.initialiseResourceGroup("GUI");
    CEGUI::ImageManager::setImagesetDefaultResourceGroup("GUI");
    CEGUI::Font::setDefaultResourceGroup("GUI");
    CEGUI::Scheme::setDefaultResourceGroup("GUI");
    CEGUI::WidgetLookManager::setDefaultResourceGroup("GUI");
    CEGUI::WindowManager::setDefaultResourceGroup("GUI");
    CEGUI::SchemeManager::getSingleton().createFromFile("ODSkin.scheme");
    CEGUI::Window* layout = CEGUI::WindowManager::getSingleton().loadLayoutFromFile("MenuSkirmish.layout");
    CEGUI::System::getSingleton().getDefaultGUIContext().setRootWindow(layout);
    CEGUI::Window* label = layout->getChild("LoadingText");
    layout->setAlpha(0.0f);
    layout->setEnabled(false);
    label->setInheritsAlpha(false);
    label->setAlpha(1.0f);
    renderer.setFrameControlExecutionEnabled(false);
    Ogre::MaterialPtr loading = createLoadingMaterial("loading_01.jpg");
    Ogre::Rectangle2D rectangle("LoadingPreview", true);
    rectangle.setMaterial(loading);
    rectangle.setBoundingBox(Ogre::AxisAlignedBox::BOX_INFINITE);
    Ogre::SceneNode* background = scene->getRootSceneNode()->createChildSceneNode();
    background->attachObject(&rectangle);
    const unsigned int heights[2] = {1080, 1200};
    for(unsigned int height : heights)
    {
        fitLoadingImage(rectangle, 1920, height);
        CEGUI::System::getSingleton().notifyDisplaySizeChanged(CEGUI::Sizef(1920, static_cast<float>(height)));
        Ogre::TexturePtr rendered = Ogre::TextureManager::getSingleton().createManual("LoadingPreviewTarget", "General",
            Ogre::TEX_TYPE_2D, 1920, height, 0, Ogre::PF_BYTE_RGBA, Ogre::TU_RENDERTARGET);
        Ogre::RenderTexture* target = rendered->getBuffer()->getRenderTarget();
        target->setAutoUpdated(false);
        target->addViewport(camera)->setBackgroundColour(Ogre::ColourValue::Red);
        renderer.setDefaultRootRenderTarget(*target);
        target->update(false);
        CEGUI::System::getSingleton().renderAllGUIContexts();
        target->writeContentsToFile(output + "/loading-screen-1920x" + std::to_string(height) + ".png");
        std::vector<unsigned char> pixels(1920 * height * 4);
        Ogre::PixelBox box(1920, height, 1, Ogre::PF_BYTE_RGBA, pixels.data());
        target->copyContentsToMemory(Ogre::Box(0, 0, 1920, height), box);
        const unsigned int edge = (height == 1200 ? 10 * 1920 + 960 : (height / 2) * 1920 + 960) * 4;
        if(height == 1200)
            check(pixels[edge] < 3 && pixels[edge + 1] < 3 && pixels[edge + 2] < 3,
                "loading image has black margins on the taller viewport");
        else
            check(pixels[edge] + pixels[edge + 1] + pixels[edge + 2] > 0,
                "loading image fills the 16:9 viewport");
        renderer.setDefaultRootRenderTarget(*window);
        target->removeAllViewports();
        Ogre::TextureManager::getSingleton().remove(rendered->getHandle());
    }
    background->detachObject(&rectangle);
    scene->destroySceneNode(background);
    CEGUI::System::getSingleton().getDefaultGUIContext().setRootWindow(nullptr);
    CEGUI::WindowManager::getSingleton().destroyWindow(layout);
'''
probe = probe.replace('LOADING_HELPERS', loading_helpers).replace('LOADING_RENDER', loading_render)
probe = probe.replace('LOADING_CODEC', 'root->loadPlugin(prefix + "/bin/Codec_STBI");')

# Keep the existing native asset setup while exercising production camera and menu navigation below.
menu_render = ''
menu_helpers = ''
if args.menu_scene:
    menu_helpers = r'''
#include "renderscene/RenderSceneMenu.h"
#include <OgreRectangle2D.h>
#include <CEGUI/widgets/ButtonBase.h>
#include <CEGUI/widgets/FrameWindow.h>

//! Sampling limits and tolerances for the authored zero-phase left firelight.
static const Ogre::Real PROBE_FIRE_AMPLITUDE = 0.18f;
static const Ogre::Real PROBE_FIRST_FIRE_STEP = 0.11f;
static const Ogre::Real PROBE_SECOND_FIRE_STEP = 0.13f;
static const Ogre::Real PROBE_FIRE_STEP = 0.05f;
static const Ogre::Real PROBE_COLOUR_EPSILON = 0.00001f;
static const unsigned int PROBE_FIRE_SAMPLES = 80;

//! \brief Exposes the real probe camera hierarchy to the extracted production menu functions.
class CameraManager
{
public:
    enum Direction {fullStop};
    Ogre::Camera* mActiveCamera = nullptr;
    Ogre::SceneNode* mActiveCameraNode = nullptr;
    Ogre::Viewport* mViewport = nullptr;
    bool mMainMenuProjection = true;
    Ogre::Radian mMainMenuBaseFovY = Ogre::Degree(45.0f);
    //! \brief Returns the attached native camera.
    Ogre::Camera* getActiveCamera() {return mActiveCamera;}
    //! \brief Returns the native position node used by production path sampling.
    Ogre::SceneNode* getActiveCameraNode() const {return mActiveCameraNode;}
    //! \brief Returns the native render viewport.
    Ogre::Viewport* getViewport() {return mViewport;}
    //! \brief Stops gameplay movement, which the isolated native camera does not use.
    void move(Direction) {}
    //! \brief Keeps the production projection function in this probe.
    void setViewportSize(unsigned int width, unsigned int height);
};

//! \brief Supplies native scene ownership and unchanged hand hooks to the menu code.
class RenderManager
{
public:
    Ogre::SceneManager* mSceneManager = nullptr;
    bool mHandVisible = true;
    //! \brief Returns the same native scene that owns the probe entities and lights.
    Ogre::SceneManager* getSceneManager() {return mSceneManager;}
    //! \brief Reports the native menu's hand visibility state.
    bool isKeeperHandVisible() const {return mHandVisible;}
    //! \brief Retains the production menu's hand-visibility lifecycle.
    void rrToggleHandSelectorVisibility() {mHandVisible = !mHandVisible;}
    //! \brief Leaves hand mesh animation outside the isolated camera/navigation checks.
    void rrSetHandPose(bool, bool) {}
};

//! \brief The existing asset loader owns render commands; these adapters delimit their parsed groups.
class RenderSceneGroup
{
public:
    //! \brief Reads one native scene group, already instantiated by the original asset probe below.
    static RenderSceneGroup* load(std::istream& input)
    {
        std::string line;
        if(!std::getline(input, line))
            return nullptr;
        while(std::getline(input, line))
            if(line == "[/RenderSceneGroup]")
                return new RenderSceneGroup();
        return nullptr;
    }
    //! \brief Leaves original native asset setup in the existing menu probe.
    void reset(CameraManager&, RenderManager&) {}
    //! \brief Leaves original native asset cleanup in the existing menu probe.
    void freeGroup(CameraManager&, RenderManager&) {}
    //! \brief Keeps independently sampled particles and banners outside camera state assertions.
    void update(CameraManager&, RenderManager&, Ogre::Real) {}
    //! \brief Accepts the real listener relationship without mocking camera paths.
    void setRenderSceneListener(RenderSceneListener*) {}
    //! \brief Accepts native synchronization unrelated to the menu's camera paths.
    void notifySyncPost(const std::string&) {}
};

namespace Helper
{
//! \brief Reads the actual configuration while removing its comment-only lines.
bool readFile(const std::string& name, std::stringstream& output, bool)
{
    std::ifstream input(name);
    std::string line;
    while(std::getline(input, line))
    {
        const std::size_t comment = line.find('#');
        if(comment != std::string::npos)
            line.erase(comment);
        if(line.find_first_not_of(" \t\r") != std::string::npos)
            output << line << '\n';
    }
    return !input.bad() && input.is_open();
}
//! \brief Reads a nonempty trimmed configuration command.
bool readNextLineNotEmpty(std::istream& input, std::string& line)
{
    while(std::getline(input, line))
    {
        const std::size_t first = line.find_first_not_of(" \t\r");
        if(first == std::string::npos)
            continue;
        line = line.substr(first, line.find_last_not_of(" \t\r") - first + 1);
        return true;
    }
    return false;
}
}
#define OD_LOG_ERR(message) throw std::runtime_error(message)
#define OD_LOG_WRN(message) throw std::runtime_error(message)
PRODUCTION_MENU_CODE
PRODUCTION_PROJECTION

//! \brief Existing menu destinations used by the extracted callbacks.
struct AbstractModeManager {enum ModeType {NONE, MENU_MAIN, MENU_REPLAY, ADVERTISMENT};};
//! \brief Supplies only the existing menu-sheet lookup used by the real callbacks.
class Gui
{
public:
    enum GuiSheet {mainMenu};
    CEGUI::Window* mRoot = nullptr;
    //! \brief Returns the same native CEGUI sheet throughout the flight.
    CEGUI::Window* getGuiSheet(GuiSheet) {return mRoot;}
};
//! \brief Records a child mode for the production back-history guard.
class AbstractApplicationMode
{
public:
    AbstractModeManager::ModeType mMode = AbstractModeManager::MENU_REPLAY;
    //! \brief Returns the current child mode while its root is hidden during return.
    AbstractModeManager::ModeType getModeType() const {return mMode;}
};
//! \brief Connects production menu navigation with the production three-dimensional scene.
class ODFrameListener
{
public:
    RenderSceneMenu* mMenu = nullptr;
    CameraManager* mCamera = nullptr;
    //! \brief Returns the fixture listener owning the real camera path state.
    static ODFrameListener& getSingleton() {static ODFrameListener listener;return listener;}
    //! \brief Reads the production path timer.
    bool isMainMenuFlightActive() const {return mMenu->isFlightActive();}
    //! \brief Requests a production configured destination.
    bool flyMainMenuTo(const std::string& name) {return mMenu->flyTo(*mCamera, name);}
    //! \brief Reads the destination published only at actual arrival.
    const std::string& getMainMenuPlace() const {return mMenu->getCurrentPlace();}
};
//! \brief Provides the exact history members needed by the extracted previous-mode guard.
class ModeManager : public AbstractModeManager
{
public:
    Gui mGui;
    bool mMainMenuReturnPending = false;
    std::string mMenuArrivalPlace;
    ModeType mRequestedMode = NONE;
    AbstractApplicationMode* mCurrentApplicationMode = nullptr;
    std::vector<ModeType> mPreviousModeTypes;
    bool mStoreCurrentModeAtChange = true;
    //! \brief Returns the real CEGUI sheet adapter.
    Gui& getGui() {return mGui;}
    //! \brief Keeps the production back-history guard in the native menu probe.
    void requestPreviousMode();
};
#define OD_ASSERT_TRUE(condition) do {if(!(condition)) throw std::runtime_error("menu assertion");} while(false)
NAV_CONSTANTS
//! \brief Hosts unchanged callback bodies against native CEGUI windows and the production scene.
class MenuModeMain
{
public:
    ModeManager mManager;
    bool mSkirmishSubMenuPending = false;
    std::string mPendingSubMenu;
    AbstractModeManager::ModeType mPendingMode = AbstractModeManager::NONE;
    AbstractModeManager::ModeType mLastMode = AbstractModeManager::NONE;
    //! \brief Returns the same manager used by all extracted callbacks.
    ModeManager& getModeManager() {return mManager;}
    //! \brief Records the original target action rather than replacing it with a new pane.
    bool changeModeEvent(AbstractModeManager::ModeType mode, const CEGUI::EventArgs&) {mLastMode = mode;return true;}
    //! \brief Leaves campaign confirmation controls unchanged outside the tested navigation.
    void showNewCampaignConfirm(bool) {}
    //! \brief Runs the production delayed-pane completion callback.
    void onFrameStarted(const Ogre::FrameEvent&);
    //! \brief Runs production immediate Quit or delayed Replay navigation.
    bool changeModeAfterFlight(AbstractModeManager::ModeType, const CEGUI::EventArgs&);
    //! \brief Starts the production submenu destination request.
    bool toggleSubMenu(const std::string&);
    //! \brief Reveals the existing submenu through its production callback.
    void showSubMenu(const std::string&);
    //! \brief Applies the unchanged production button visibility rule.
    void showMainMenuButtons(bool);
    //! \brief Runs the production submenu Back/Escape return request.
    bool goBack(const CEGUI::EventArgs& e = {});
};
PRODUCTION_NAVIGATION

//! \brief Advances production camera and menu timing with a bounded number of ordinary frames.
void finishMenuFlight(RenderSceneMenu& menu, CameraManager& camera, RenderManager& render, MenuModeMain& navigation)
{
    Ogre::FrameEvent frame;
    frame.timeSinceLastFrame = 0.05f;
    frame.timeSinceLastEvent = 0.05f;
    unsigned int frames = 0;
    while(menu.isFlightActive() && frames < 200)
    {
        navigation.onFrameStarted(frame);
        menu.updateMenu(camera, render, frame.timeSinceLastFrame);
        ++frames;
    }
    check(frames < 200 && !menu.isFlightActive(), "the configured menu flight terminates");
    navigation.onFrameStarted(frame);
}

//! \brief Checks a settled camera against the actual authored endpoint and orientation.
void checkMenuPose(RenderSceneMenu& menu, CameraManager& camera, const std::string& name)
{
    Ogre::Vector3 position = Ogre::Vector3::ZERO;
    Ogre::Quaternion orientation = Ogre::Quaternion::IDENTITY;
    check(menu.getCameraPose(name, position, orientation), "configured endpoint exists: " + name);
    check(camera.getActiveCamera()->getDerivedPosition().positionEquals(position, 0.001f), "camera reaches endpoint: " + name);
    check(std::abs(camera.getActiveCamera()->getDerivedOrientation().Dot(orientation)) > 0.99999f,
        "camera reaches endpoint orientation: " + name);
    check(menu.getCurrentPlace() == name, "settled menu place matches: " + name);
}
'''
    menu_render = r'''
    const std::string repository = argv[2];
    const std::string output = argv[3];
    resources.createResourceGroup("Graphics");
    for(const char* folder : {"models", "materials/scripts", "materials/textures", "particles", "shaders"})
        resources.addResourceLocation(repository + "/" + folder, "FileSystem", "Graphics", true);
    resources.initialiseResourceGroup("Graphics");
    scene->setAmbientLight(Ogre::ColourValue(0.3f, 0.3f, 0.3f));
    Ogre::ParticleSystem::setDefaultNonVisibleUpdateTimeout(5);
    Ogre::SceneNode* entities = scene->getRootSceneNode()->createChildSceneNode("MenuProbeEntities");
    camera->getParentSceneNode()->detachObject(camera);
    Ogre::SceneNode* cameraPosition = scene->getRootSceneNode()->createChildSceneNode("MenuProbeCamera");
    Ogre::SceneNode* cameraRotation = cameraPosition->createChildSceneNode();
    cameraRotation->attachObject(camera);
    camera->setNearClipDistance(0.02f);
    camera->setFarClipDistance(300.0f);
    camera->setAspectRatio(1920.0f / 1080.0f);
    std::ifstream definition(repository + "/config/mainmenuscene.cfg");
    if(!definition)
        throw std::runtime_error("cannot open menu scene configuration");
    unsigned int entityCount = 0, lightCount = 0, particleCount = 0, animationCount = 0, cameraCount = 0;
    std::string line;
    bool sceneMetadata = false;
    while(std::getline(definition, line))
    {
        std::istringstream command(line);
        std::string type;
        command >> type;
        if(type == "[MenuCamera]" || type == "[/MenuCamera]" ||
            type == "[MenuFireLights]" || type == "[/MenuFireLights]")
        {
            sceneMetadata = (type == "[MenuCamera]" || type == "[MenuFireLights]");
            continue;
        }
        if(sceneMetadata)
            continue;
        if(type.empty() || type[0] == '#' || type == "[RenderSceneGroup]" || type == "[/RenderSceneGroup]")
            continue;
        if(type == "CameraMove")
        {
            Ogre::Vector3 position = Ogre::Vector3::ZERO, rotation = Ogre::Vector3::ZERO;
            if(!(command >> position.x >> position.y >> position.z >> rotation.x >> rotation.y >> rotation.z))
                throw std::runtime_error("invalid menu camera command");
            cameraPosition->setPosition(position);
            cameraRotation->resetOrientation();
            cameraRotation->pitch(Ogre::Degree(rotation.x), Ogre::Node::TS_LOCAL);
            cameraRotation->yaw(Ogre::Degree(rotation.y), Ogre::Node::TS_LOCAL);
            cameraRotation->roll(Ogre::Degree(rotation.z), Ogre::Node::TS_LOCAL);
            ++cameraCount;
        }
        else if(type == "AddEntity")
        {
            std::string name, meshName;
            Ogre::Vector3 position = Ogre::Vector3::ZERO;
            if(!(command >> name >> meshName >> position.x >> position.y >> position.z))
                throw std::runtime_error("invalid menu entity command");
            Ogre::MeshPtr mesh = Ogre::MeshManager::getSingleton().load(meshName, "Graphics");
            unsigned short source = 0;
            if(!mesh->suggestTangentVectorBuildParams(source))
                mesh->buildTangentVectors(source);
            Ogre::Entity* entity = scene->createEntity(name, mesh);
            entities->createChildSceneNode(name + "_node", position)->attachObject(entity);
            ++entityCount;
        }
        else if(type == "AddPointLight")
        {
            std::string name;
            Ogre::Vector3 position = Ogre::Vector3::ZERO;
            Ogre::ColourValue diffuse = Ogre::ColourValue::Black, specular = Ogre::ColourValue::Black;
            Ogre::Real range = 0, constant = 0, linear = 0, quadratic = 0;
            if(!(command >> name >> position.x >> position.y >> position.z >> diffuse.r >> diffuse.g >> diffuse.b
                >> specular.r >> specular.g >> specular.b >> range >> constant >> linear >> quadratic))
                throw std::runtime_error("invalid menu point light command");
            Ogre::Light* light = scene->createLight(name);
            scene->getRootSceneNode()->createChildSceneNode("PointLightMenuSceneNode_" + name, position)->attachObject(light);
            light->setType(Ogre::Light::LT_POINT);
            light->setDiffuseColour(diffuse);
            light->setSpecularColour(specular);
            light->setAttenuation(range, constant, linear, quadratic);
            ++lightCount;
        }
        else if(type == "AddParticleEffect")
        {
            std::string name, script;
            if(!(command >> name >> script))
                throw std::runtime_error("invalid menu particle command");
            Ogre::ParticleSystem* particles = scene->createParticleSystem(name + "_particles_" + std::to_string(particleCount), script);
            scene->getSceneNode(name + "_node")->attachObject(particles);
            particles->fastForward(4.0f);
            ++particleCount;
        }
        else if(type == "AnimationTime")
        {
            std::string name, clip;
            Ogre::Real duration = 0;
            if(!(command >> name >> clip >> duration))
                throw std::runtime_error("invalid menu animation command");
            Ogre::AnimationState* animation = scene->getEntity(name)->getAnimationState(clip);
            animation->setEnabled(true);
            animation->setLoop(true);
            animation->setTimePosition(duration < 0 ? 1.0f : std::min(1.0f, duration));
            ++animationCount;
        }
        else
            throw std::runtime_error("unsupported menu scene command: " + type);
    }
    check(entityCount > 0 && lightCount > 1 && particleCount > 0 && animationCount > 0 && cameraCount == 1,
        "the configured menu has entities, independent lights, particles, animation and one overview camera");
    std::cout << "MENU entities=" << entityCount << " lights=" << lightCount << " particles=" << particleCount
        << " animations=" << animationCount << '\n';
    Ogre::TexturePtr rendered = Ogre::TextureManager::getSingleton().createManual("MenuScenePreview", "General",
        Ogre::TEX_TYPE_2D, 1920, 1080, 0, Ogre::PF_BYTE_RGBA, Ogre::TU_RENDERTARGET);
    Ogre::RenderTexture* target = rendered->getBuffer()->getRenderTarget();
    target->setAutoUpdated(false);
    Ogre::Viewport* viewport = target->addViewport(camera);
    viewport->setMaterialScheme(Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME);
    viewport->setBackgroundColour(Ogre::ColourValue::Black);
    // The original native setup supplies render objects; all camera/navigation state below is production code.
    Ogre::Rectangle2D* background = new Ogre::Rectangle2D("MenuProbeBackground", true);
    background->setMaterial(Ogre::MaterialManager::getSingleton().getByName("Background", "Graphics"));
    scene->getRootSceneNode()->createChildSceneNode("Background")->attachObject(background);
    CameraManager menuCamera;
    menuCamera.mActiveCamera = camera;
    menuCamera.mActiveCameraNode = cameraPosition;
    menuCamera.mViewport = viewport;
    menuCamera.setViewportSize(1920, 1080);
    RenderManager menuRenderer;
    menuRenderer.mSceneManager = scene;
    const Ogre::ColourValue savedAmbient = scene->getAmbientLight();
    const Ogre::ColourValue authoredFire = scene->getLight("LeftFire")->getDiffuseColour();
    const Ogre::ColourValue authoredFireSpecular = scene->getLight("LeftFire")->getSpecularColour();
    const Ogre::ColourValue steadyGreen = scene->getLight("SpireLight")->getDiffuseColour();
    RenderSceneMenu menuScene;
    menuScene.readSceneMenu(repository + "/config/mainmenuscene.cfg");
    menuScene.resetMenu(menuCamera, menuRenderer);
    check(!background->isVisible() && scene->getAmbientLight() == Ogre::ColourValue::Black,
        "production menu activation hides the world rectangle and disables uniform ambient lighting");
    checkMenuPose(menuScene, menuCamera, "overview");

    // The production menu updates fire colours from authored baselines even without a camera flight.
    check(scene->getLight("LeftFire")->getDiffuseColour() == authoredFire,
        "zero-phase fire starts at its authored intensity");
    menuScene.updateMenu(menuCamera, menuRenderer, PROBE_FIRST_FIRE_STEP);
    const Ogre::ColourValue firstFlicker = scene->getLight("LeftFire")->getDiffuseColour();
    menuScene.updateMenu(menuCamera, menuRenderer, PROBE_SECOND_FIRE_STEP);
    const Ogre::ColourValue secondFlicker = scene->getLight("LeftFire")->getDiffuseColour();
    check(firstFlicker != authoredFire && secondFlicker != firstFlicker,
        "the configured firelight changes continuously while the camera is settled");
    check(scene->getLight("SpireLight")->getDiffuseColour() == steadyGreen,
        "fire flicker never changes the green tower light");
    for(unsigned int sample = 0; sample < PROBE_FIRE_SAMPLES; ++sample)
    {
        menuScene.updateMenu(menuCamera, menuRenderer, PROBE_FIRE_STEP);
        const Ogre::ColourValue flicker = scene->getLight("LeftFire")->getDiffuseColour();
        const Ogre::Real scale = flicker.r / authoredFire.r;
        check(scale >= 1.0f - PROBE_FIRE_AMPLITUDE && scale <= 1.0f + PROBE_FIRE_AMPLITUDE &&
            std::abs(flicker.g - authoredFire.g * scale) < PROBE_COLOUR_EPSILON &&
            std::abs(flicker.b - authoredFire.b * scale) < PROBE_COLOUR_EPSILON,
            "configured fire intensity stays bounded and retains its authored warm colour");
        const Ogre::ColourValue specular = scene->getLight("LeftFire")->getSpecularColour();
        check(std::abs(specular.r - authoredFireSpecular.r * scale) < PROBE_COLOUR_EPSILON,
            "fire reflections use the same nonaccumulating intensity as diffuse lighting");
    }

    CEGUI::WindowManager& windows = CEGUI::WindowManager::getSingleton();
    CEGUI::Window* menuRoot = windows.createWindow("DefaultWindow", "MenuProbeRoot");
    CEGUI::System::getSingleton().getDefaultGUIContext().setRootWindow(menuRoot);
    for(const std::string& name : {WINDOW_CAMPAIGN, WINDOW_SKIRMISH, WINDOW_MULTIPLAYER, WINDOW_EDITOR, WINDOW_SETTINGS,
        BUTTON_START_CAMPAIGN, BUTTON_SKIRMISH, BUTTON_MULTIPLAYER, BUTTON_START_REPLAY, BUTTON_MAPEDITOR,
        BUTTON_SETTINGS, BUTTON_QUIT})
        menuRoot->addChild(windows.createWindow("DefaultWindow", name));
    for(const std::string& name : {WINDOW_CAMPAIGN, WINDOW_SKIRMISH, WINDOW_MULTIPLAYER, WINDOW_EDITOR, WINDOW_SETTINGS})
        menuRoot->getChild(name)->hide();
    MenuModeMain navigation;
    navigation.mManager.mGui.mRoot = menuRoot;
    ODFrameListener::getSingleton().mMenu = &menuScene;
    ODFrameListener::getSingleton().mCamera = &menuCamera;
    const std::string paneNames[] = {WINDOW_CAMPAIGN, WINDOW_SKIRMISH, WINDOW_MULTIPLAYER, WINDOW_EDITOR, WINDOW_SETTINGS};
    const std::string placeNames[] = {PLACE_CAMPAIGN, PLACE_SKIRMISH, PLACE_MULTIPLAYER, PLACE_EDITOR, PLACE_SETTINGS};
    for(unsigned int index = 0; index < 5; ++index)
    {
        navigation.toggleSubMenu(paneNames[index]);
        check(menuScene.isFlightActive() && !menuRoot->getChild(paneNames[index])->isVisible(),
            "submenu remains hidden while flying: " + placeNames[index]);
        check(!menuScene.flyTo(menuCamera, "settings"), "a second destination is rejected during a flight");
        finishMenuFlight(menuScene, menuCamera, menuRenderer, navigation);
        checkMenuPose(menuScene, menuCamera, placeNames[index]);
        check(menuRoot->getChild(paneNames[index])->isVisible(), "existing submenu is visible at arrival: " + placeNames[index]);
        navigation.goBack();
        check(menuScene.isFlightActive() && !menuRoot->getChild(paneNames[index])->isVisible(),
            "Back hides the submenu and starts its return route");
        finishMenuFlight(menuScene, menuCamera, menuRenderer, navigation);
        checkMenuPose(menuScene, menuCamera, "overview");
    }
    navigation.changeModeAfterFlight(AbstractModeManager::MENU_REPLAY, CEGUI::EventArgs());
    check(navigation.mLastMode == AbstractModeManager::NONE && menuScene.isFlightActive(), "replay mode waits for its archive flight");
    finishMenuFlight(menuScene, menuCamera, menuRenderer, navigation);
    checkMenuPose(menuScene, menuCamera, "replay");
    check(navigation.mLastMode == AbstractModeManager::MENU_REPLAY, "replay pane is requested at archive arrival");
    AbstractApplicationMode replayMode;
    navigation.mManager.mCurrentApplicationMode = &replayMode;
    navigation.mManager.mPreviousModeTypes.push_back(AbstractModeManager::MENU_MAIN);
    navigation.mManager.mPreviousModeTypes.push_back(AbstractModeManager::MENU_MAIN);
    navigation.mManager.requestPreviousMode();
    check(navigation.mManager.mRequestedMode == AbstractModeManager::MENU_MAIN &&
        navigation.mManager.mPreviousModeTypes.size() == 1, "child Back consumes exactly one history entry");
    navigation.mManager.requestPreviousMode();
    check(navigation.mManager.mPreviousModeTypes.size() == 1, "repeated Escape cannot consume return history twice");
    check(menuScene.flyTo(menuCamera, "overview"), "the replay pane can return through its authored overview route");
    finishMenuFlight(menuScene, menuCamera, menuRenderer, navigation);
    checkMenuPose(menuScene, menuCamera, "overview");

    navigation.mLastMode = AbstractModeManager::NONE;
    navigation.toggleSubMenu(WINDOW_CAMPAIGN);
    navigation.changeModeAfterFlight(AbstractModeManager::ADVERTISMENT, CEGUI::EventArgs());
    check(navigation.mLastMode == AbstractModeManager::ADVERTISMENT && menuScene.isFlightActive(),
        "Quit keeps its original immediate action during a flight");
    check(navigation.mPendingSubMenu.empty() && navigation.mPendingMode == AbstractModeManager::NONE &&
        !navigation.mSkirmishSubMenuPending, "Quit clears deferred actions that could replace it");
    finishMenuFlight(menuScene, menuCamera, menuRenderer, navigation);
    check(navigation.mLastMode == AbstractModeManager::ADVERTISMENT && !menuRoot->getChild(WINDOW_CAMPAIGN)->isVisible(),
        "completed flight cannot overwrite Quit or reveal its canceled pane");
    check(menuScene.flyTo(menuCamera, "overview"), "restore overview after the Quit timing assertion");
    finishMenuFlight(menuScene, menuCamera, menuRenderer, navigation);
    check(menuScene.startFlight(menuCamera), "the configured outside arrival starts");
    check(!menuScene.startFlight(menuCamera), "a second outside arrival is rejected");
    finishMenuFlight(menuScene, menuCamera, menuRenderer, navigation);
    checkMenuPose(menuScene, menuCamera, "overview");

    const unsigned int widths[] = {1920, 1440, 2520};
    const float referenceTangent = std::tan(Ogre::Degree(45.0f).valueRadians() * 0.5f);
    for(unsigned int index = 0; index < 3; ++index)
    {
        menuCamera.setViewportSize(widths[index], 1080);
        const float verticalTangent = std::tan(camera->getFOVy().valueRadians() * 0.5f);
        check(verticalTangent + 0.00001f >= referenceTangent &&
            verticalTangent * camera->getAspectRatio() + 0.00001f >= referenceTangent * 16.0f / 9.0f,
            "production projection preserves both dimensions of the authored overview");
    }
    menuCamera.setViewportSize(1920, 1080);
    target->update(false);
    target->update(false);
    target->writeContentsToFile(output + "/menu-scene-1920x1080.png");
    menuScene.freeMenu(menuCamera, menuRenderer);
    check(scene->getLight("LeftFire")->getDiffuseColour() == authoredFire &&
        scene->getLight("LeftFire")->getSpecularColour() == authoredFireSpecular,
        "menu teardown restores authored fire colours before releasing native lights");
    check(background->isVisible() && background->getMaterial() ==
        Ogre::MaterialManager::getSingleton().getByName("Background", "Graphics") && scene->getAmbientLight() == savedAmbient,
        "production teardown restores the world background and previous ambient lighting");
    menuScene.resetMenu(menuCamera, menuRenderer);
    checkMenuPose(menuScene, menuCamera, "overview");
    check(scene->getLight("LeftFire")->getDiffuseColour() == authoredFire,
        "re-entering the menu resets fire time without multiplying its old intensity");
    menuScene.freeMenu(menuCamera, menuRenderer);
    CEGUI::System::getSingleton().getDefaultGUIContext().setRootWindow(nullptr);
    windows.destroyWindow(menuRoot);
    background->getParentSceneNode()->detachObject(background);
    delete background;
    target->removeAllViewports();
    Ogre::TextureManager::getSingleton().remove(rendered->getHandle());
'''
    menu_source = (repo / 'source/renderscene/RenderSceneMenu.cpp').read_text()
    menu_source = re.sub(r'^#include[^\n]*\n', '', menu_source, flags=re.MULTILINE)
    camera_source = (repo / 'source/camera/CameraManager.cpp').read_text()
    projection_constants = '\n'.join(re.findall(r'^const (?:Ogre::Real MAIN_MENU_REFERENCE_ASPECT_RATIO|float MAIN_MENU_DEFAULT_FOV_Y_DEGREES) = [^;]+;', camera_source, re.MULTILINE))
    projection = projection_constants + '\n' + function(camera_source, 'void CameraManager::setViewportSize(')
    navigation_source = (repo / 'source/modes/MenuModeMain.cpp').read_text()
    navigation_constants = '\n'.join(re.findall(r'^(?:static )?const std::string [^;]+;', navigation_source, re.MULTILINE))
    navigation_functions = '\n'.join(function(navigation_source, signature) for signature in (
        'void MenuModeMain::onFrameStarted(', 'bool MenuModeMain::changeModeAfterFlight(',
        'bool MenuModeMain::toggleSubMenu(', 'void MenuModeMain::showSubMenu(',
        'void MenuModeMain::showMainMenuButtons(', 'bool MenuModeMain::goBack('))
    navigation_functions += '\n' + function((repo / 'source/modes/ModeManager.cpp').read_text(), 'void ModeManager::requestPreviousMode(')
    menu_helpers = menu_helpers.replace('PRODUCTION_MENU_CODE', menu_source).replace('PRODUCTION_PROJECTION', projection)
    menu_helpers = menu_helpers.replace('NAV_CONSTANTS', navigation_constants).replace('PRODUCTION_NAVIGATION', navigation_functions)
probe = probe.replace('MENU_PLUGINS', 'root->loadPlugin(prefix + "/bin/Plugin_ParticleFX");' if args.menu_scene else '')
probe = probe.replace('MENU_HELPERS', menu_helpers)
probe = probe.replace('MENU_RENDER', menu_render)
# Style of the fixture itself (the extracted production code is compiled as it is)
assert re.search(r'\bauto\b', probe) is None and '[&]' not in probe
probe = probe.replace('RULES_HEADER', rules.as_posix()).replace('BADGE_CODE', badge_code).replace('UPDATE', update)
assert '.loadFromMemory(' not in update and '.blitFromMemory(' in update, 'the update must not replace the texture the badge shows'
print('STATIC OK: updateHeartBadge writes into the existing texture')
for path in (Path(__file__), repo / 'source/render/Gui.cpp'):
    assert not [b for b in path.read_bytes() if b < 32 and b not in (9, 10, 13)], path

with tempfile.TemporaryDirectory(prefix='odp-heart-badge-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    if args.loading_screens:
        args.loading_output.mkdir(parents=True, exist_ok=True)
    if args.menu_scene:
        args.menu_output.mkdir(parents=True, exist_ok=True)
    include = deps / 'install/include'
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++17', '/W1', '/I', str(include / 'OGRE'),
                    '/I', str(include / 'OGRE/RTShaderSystem'), '/I', str(include / 'cegui-0'), '/I', str(repo / 'source'), 'check.cpp', '/Fecheck.exe', '/link',
                    '/LIBPATH:' + str(deps / 'install/lib'), 'OgreMain.lib', 'OgreRTShaderSystem.lib', 'OgreBites.lib', 'CEGUIBase-0.lib',
                    'CEGUIOgreRenderer-0.lib'],
                   cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=120)
    environment = dict(os.environ)
    environment['PATH'] = str(deps / 'install/bin') + os.pathsep + environment.get('PATH', '')
    # Windows may block a freshly compiled executable (WinError 4551) for a moment
    for attempt in range(4):
        try:
            command = [str(work / 'check.exe'), (deps / 'install').as_posix(), repo.as_posix()]
            if args.loading_screens:
                command.append(args.loading_output.resolve().as_posix())
            if args.menu_scene:
                command.append(args.menu_output.resolve().as_posix())
            subprocess.run(command, cwd=work, check=True, env=environment, stdin=subprocess.DEVNULL, timeout=180)
            break
        except OSError as error:
            if attempt == 3:
                raise
            print('retrying after', error)
            time.sleep(2)

if args.loading_screens:
    destination = repo / 'build/reference-audit'
    destination.mkdir(parents=True, exist_ok=True)
    for height in (1080, 1200):
        filename = f'loading-screen-1920x{height}.png'
        shutil.copyfile(args.loading_output / filename, destination / filename)

if args.menu_scene:
    from PIL import Image

    with Image.open(args.menu_reference) as reference, Image.open(args.menu_output / 'menu-scene-1920x1080.png') as rendered:
        reference = reference.convert('RGB').resize((1920, 1080), Image.Resampling.LANCZOS)
        comparison = Image.new('RGB', (3840, 1080))
        comparison.paste(reference, (0, 0))
        comparison.paste(rendered.convert('RGB'), (1920, 0))
        comparison.save(args.menu_output / 'menu-scene-compare.png')
