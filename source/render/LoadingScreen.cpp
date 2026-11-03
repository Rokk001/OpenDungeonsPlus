#include "render/LoadingScreen.h"

#include "render/ODFrameListener.h"
#include "render/RenderManager.h"
#include "utils/LogManager.h"

#include <OgreCamera.h>
#include <OgreHighLevelGpuProgramManager.h>
#include <OgreHighLevelGpuProgram.h>
#include <Bites/OgreWindowEventUtilities.h>
#include <OgreRoot.h>
#include <OgreViewport.h>
#include <OgreColourValue.h>
#include <OgreMaterial.h>
#include <OgreMaterialManager.h>
#include <OgrePass.h>
#include <OgreTechnique.h>
#include <OgreRectangle2D.h>
#include <OgreRenderQueue.h>
#include <OgreVector2.h>
#include <OgreRenderWindow.h>
#include <OgreSceneManager.h>
#include <OgreSceneNode.h>
#include <OgreTextureManager.h>
#include <OgreTextureUnitState.h>
#include <Overlay/OgreOverlaySystem.h>
#include <Overlay/OgreOverlayManager.h>
#include <Overlay/OgreOverlay.h>
#include <Overlay/OgreOverlayContainer.h>
#include <Overlay/OgreTextAreaOverlayElement.h>
#include <Overlay/OgreFontManager.h>
#include <Overlay/OgreFont.h>

#include <CEGUI/Event.h>
#include <CEGUI/String.h>
#include <CEGUI/System.h>
#include <CEGUI/GUIContext.h>
#include <CEGUI/Window.h>
#include <CEGUI/WindowManager.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>
#include <string>
#include <utility>
#include <vector>

namespace
{
//! The complete loading-picture set; this generator is independent of gameplay randomness.
const char* const LOADING_TEXTURES[] = {
    "loading_01.jpg", "loading_02.jpg", "loading_03.jpg", "loading_04.jpg", "loading_05.jpg",
    "loading_06.jpg", "loading_07.jpg", "loading_08.jpg", "loading_09.jpg", "loading_10.jpg",
    "loading_11.jpg", "loading_12.jpg", "loading_13.jpg", "loading_14.jpg", "loading_15.jpg",
    "loading_16.jpg", "loading_17.jpg", "loading_18.jpg", "loading_19.jpg", "loading_20.jpg",
    "loading_21.jpg", "loading_22.jpg", "loading_23.jpg", "loading_24.jpg", "loading_25.jpg"
};
Ogre::Rectangle2D* loadingRectangle = nullptr;
Ogre::SceneManager* startupScene = nullptr;
Ogre::RenderWindow* startupWindow = nullptr;
//! The ember ring sits below the text and is drawn on top of the picture in every loading path.
Ogre::Rectangle2D* ringRectangle = nullptr;
Ogre::MaterialPtr ringMaterial;
Ogre::Overlay* loadingOverlay = nullptr;
Ogre::OverlayContainer* loadingTextPanel = nullptr;
Ogre::TextAreaOverlayElement* loadingTextArea = nullptr;
//! Text height as a fraction of the window height; relative metrics make it scale with every resolution.
const float LOADING_TEXT_HEIGHT = 0.075f;
//! Top of the text as a fraction of the window height.
const float LOADING_TEXT_TOP = 0.34f;
//! Vertical centre of the ring as a fraction of the window height.
const float LOADING_RING_CENTER = 0.60f;
//! Ring radius as a fraction of the window height.
const float LOADING_RING_RADIUS = 0.11f;
//! Seconds of one full clockwise turn.
const float LOADING_RING_SECONDS = 2.0f;
//! Name of the overlay font created for the loading paths after startup.
const char* const LOADING_FONT_NAME = "LoadingScreenFont";
//! Startup sits above the normal viewport until the first menu scene is ready.
const int STARTUP_VIEWPORT_ORDER = 1;
Ogre::MaterialPtr previousMaterial;
Ogre::MaterialPtr loadingMaterial;
Ogre::uint8 previousQueue = Ogre::RENDER_QUEUE_SKIES_EARLY;
//! Rectangle visibility restored after a load returns to the same menu scene.
bool previousRectangleVisible = true;
int previousImage = -1;
CEGUI::Window* hiddenRoot = nullptr;
CEGUI::Window* loadingText = nullptr;
CEGUI::Window* temporaryLoadingText = nullptr;
float previousRootAlpha = 1.0f;
bool previousRootEnabled = true;
float previousTextAlpha = 1.0f;
bool previousTextInheritsAlpha = true;
CEGUI::Window* statusOverride = nullptr;
CEGUI::String previousStatusText;
CEGUI::String deferredStatusText;
bool hasDeferredStatus = false;
CEGUI::Event::Connection rootDestruction;
std::vector<std::pair<CEGUI::Window*, bool> > previousVisibility;
std::vector<CEGUI::Window*> independentAlpha;

//! \brief Finds the existing loading text without creating a new widget or changing a layout.
CEGUI::Window* findLoadingText(CEGUI::Window* window)
{
    if(window->getName() == "LoadingText" ||
       (window->getName() == "LevelTypeText" && window->getText() == "Loading..."))
        return window;
    if(!window->isVisible())
        return nullptr;
    for(size_t i = 0; i < window->getChildCount(); ++i)
    {
        CEGUI::Window* found = findLoadingText(window->getChildAtIdx(i));
        if(found != nullptr)
            return found;
    }
    return nullptr;
}

//! \brief Makes existing independent-alpha widgets follow the hidden root while loading.
void inheritLoadingAlpha(CEGUI::Window* window)
{
    for(size_t i = 0; i < window->getChildCount(); ++i)
    {
        CEGUI::Window* child = window->getChildAtIdx(i);
        if(!child->inheritsAlpha())
        {
            independentAlpha.push_back(child);
            child->setInheritsAlpha(true);
        }
        inheritLoadingAlpha(child);
    }
}

//! \brief Restores the temporary opacity and input state of the existing loading interface.
void restoreLoadingInterface()
{
    if(hiddenRoot == nullptr)
        return;
    if(rootDestruction.isValid())
        rootDestruction->disconnect();
    hiddenRoot->setAlpha(previousRootAlpha);
    hiddenRoot->setEnabled(previousRootEnabled);
    for(CEGUI::Window* window : independentAlpha)
        window->setInheritsAlpha(false);
    independentAlpha.clear();
    if(loadingText != nullptr)
    {
        loadingText->setAlpha(previousTextAlpha);
        loadingText->setInheritsAlpha(previousTextInheritsAlpha);
        if(hasDeferredStatus && loadingText->getText() == "Loading...")
            loadingText->setText(deferredStatusText);
    }
    if(statusOverride != nullptr)
    {
        statusOverride->setText(previousStatusText);
        statusOverride = nullptr;
    }
    for(const std::pair<CEGUI::Window*, bool>& saved : previousVisibility)
        saved.first->setVisible(saved.second);
    previousVisibility.clear();
    if(temporaryLoadingText != nullptr)
    {
        CEGUI::WindowManager::getSingleton().destroyWindow(temporaryLoadingText);
        temporaryLoadingText = nullptr;
    }
    hasDeferredStatus = false;
    hiddenRoot = nullptr;
    loadingText = nullptr;
}

//! \brief Drops references before a loading layout is destroyed during a mode change.
bool loadingRootDestroyed(const CEGUI::EventArgs&)
{
    hasDeferredStatus = false;
    hiddenRoot = nullptr;
    loadingText = nullptr;
    temporaryLoadingText = nullptr;
    statusOverride = nullptr;
    previousVisibility.clear();
    independentAlpha.clear();
    return true;
}

//! \brief Fits a full-screen background rectangle using black texture-border margins.
void fitLoadingImage(Ogre::Rectangle2D& rectangle, unsigned int width, unsigned int height)
{
    const float imageAspect = 16.0f / 9.0f;
    const float viewportAspect = static_cast<float>(width) / std::max(1u, height);
    const float u = std::max(1.0f, viewportAspect / imageAspect) * 0.5f;
    const float v = std::max(1.0f, imageAspect / viewportAspect) * 0.5f;
    rectangle.setCorners(-1.0f, 1.0f, 1.0f, -1.0f);
    rectangle.setUVs(Ogre::Vector2(0.5f - u, 0.5f - v), Ogre::Vector2(0.5f - u, 0.5f + v),
        Ogre::Vector2(0.5f + u, 0.5f - v), Ogre::Vector2(0.5f + u, 0.5f + v));
}

//! \brief Makes an unlit loading material whose out-of-image texture coordinates are black.
Ogre::MaterialPtr createLoadingMaterial(const std::string& texture, const std::string& group = "Graphics")
{
    Ogre::MaterialPtr material = Ogre::MaterialManager::getSingleton().create("LoadingScreen", group);
    Ogre::Pass* pass = material->getTechnique(0)->getPass(0);
    pass->setLightingEnabled(false);
    pass->setDepthCheckEnabled(false);
    pass->setDepthWriteEnabled(false);
    Ogre::TextureUnitState* image = pass->createTextureUnitState(texture);
    image->setTextureAddressingMode(Ogre::TAM_BORDER);
    image->setTextureBorderColour(Ogre::ColourValue::Black);
    image->setTextureFiltering(Ogre::TFO_BILINEAR);
    return material;
}

//! \brief Makes the unlit alpha-blended material of the ember ring with a transparent texture border.
Ogre::MaterialPtr createRingMaterial(const std::string& group)
{
    Ogre::MaterialPtr material = Ogre::MaterialManager::getSingleton().create("LoadingRing", group);
    Ogre::Pass* pass = material->getTechnique(0)->getPass(0);
    pass->setLightingEnabled(false);
    pass->setDepthCheckEnabled(false);
    pass->setDepthWriteEnabled(false);
    pass->setSceneBlending(Ogre::SBT_TRANSPARENT_ALPHA);
    Ogre::TextureUnitState* image = pass->createTextureUnitState("loading_ring.png");
    image->setTextureAddressingMode(Ogre::TAM_BORDER);
    image->setTextureBorderColour(Ogre::ColourValue(0.0f, 0.0f, 0.0f, 0.0f));
    image->setTextureFiltering(Ogre::TFO_BILINEAR);
    return material;
}

//! \brief Places the ring below the text and turns it clockwise by the elapsed time.
void fitLoadingRing(Ogre::Rectangle2D& rectangle, unsigned int width, unsigned int height)
{
    static const std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();
    const float seconds = std::chrono::duration<float>(std::chrono::steady_clock::now() - begin).count();
    const float angle = 6.2831853f * std::fmod(seconds, LOADING_RING_SECONDS) / LOADING_RING_SECONDS;
    const float c = std::cos(angle);
    const float s = std::sin(angle);
    const float halfHeight = LOADING_RING_RADIUS * 2.0f;
    const float halfWidth = halfHeight * static_cast<float>(height) / static_cast<float>(std::max(1u, width));
    const float centerY = 1.0f - 2.0f * LOADING_RING_CENTER;
    rectangle.setCorners(-halfWidth, centerY + halfHeight, halfWidth, centerY - halfHeight);
    // Rotating the sampled coordinates by -angle turns the picture clockwise (v points down).
    const auto turned = [c, s](float x, float y) -> Ogre::Vector2
    {
        const float dx = x - 0.5f;
        const float dy = y - 0.5f;
        return Ogre::Vector2(0.5f + dx * c + dy * s, 0.5f - dx * s + dy * c);
    };
    rectangle.setUVs(turned(0.0f, 0.0f), turned(0.0f, 1.0f), turned(1.0f, 0.0f), turned(1.0f, 1.0f));
}

//! \brief Creates the ring rectangle above the picture in the given scene.
void createLoadingRing(Ogre::SceneManager& scene, const std::string& group)
{
    ringMaterial = createRingMaterial(group);
    Ogre::TextureManager::getSingleton().load("loading_ring.png", group);
    ringRectangle = new Ogre::Rectangle2D(Ogre::String("LoadingScreenRing"), true);
    ringRectangle->setBoundingBox(Ogre::AxisAlignedBox::BOX_INFINITE);
    ringRectangle->setMaterial(ringMaterial);
    ringRectangle->setRenderQueueGroup(RenderManager::OD_RENDER_QUEUE_ID_GUI);
    scene.getRootSceneNode()->attachObject(ringRectangle);
}

//! \brief Creates the large centred loading text as an overlay with the given font.
void createLoadingText(const std::string& fontName, const std::string& fontGroup)
{
    Ogre::OverlayManager& overlays = Ogre::OverlayManager::getSingleton();
    loadingOverlay = overlays.create("LoadingScreenOverlay");
    loadingTextPanel = static_cast<Ogre::OverlayContainer*>(overlays.createOverlayElement("Panel", "LoadingScreenPanel"));
    loadingTextPanel->setDimensions(1, 1);
    loadingOverlay->add2D(loadingTextPanel);
    loadingTextArea = static_cast<Ogre::TextAreaOverlayElement*>(overlays.createOverlayElement("TextArea", "LoadingScreenText"));
    loadingTextArea->setFontName(fontName, fontGroup);
    loadingTextArea->setMetricsMode(Ogre::GMM_RELATIVE);
    loadingTextArea->setPosition(0.5f, LOADING_TEXT_TOP);
    loadingTextArea->setCharHeight(LOADING_TEXT_HEIGHT);
    loadingTextArea->setAlignment(Ogre::TextAreaOverlayElement::Center);
    loadingTextArea->setColour(Ogre::ColourValue(0.86f, 0.82f, 0.76f));
    loadingTextArea->setCaption("Loading...");
    loadingTextPanel->addChild(loadingTextArea);
    loadingOverlay->show();
}

//! \brief Removes the ring rectangle, its material and the overlay text of the current loading path.
void destroyLoadingIndicator(const std::string& group)
{
    if(ringRectangle != nullptr)
    {
        ringRectangle->detachFromParent();
        delete ringRectangle;
        ringRectangle = nullptr;
    }
    if(ringMaterial)
    {
        ringMaterial.reset();
        Ogre::MaterialManager::getSingleton().remove("LoadingRing", group);
    }
    Ogre::OverlayManager& overlays = Ogre::OverlayManager::getSingleton();
    if(loadingOverlay != nullptr)
        overlays.destroy(loadingOverlay);
    if(loadingTextArea != nullptr)
        overlays.destroyOverlayElement(loadingTextArea);
    if(loadingTextPanel != nullptr)
        overlays.destroyOverlayElement(loadingTextPanel);
    loadingOverlay = nullptr;
    loadingTextArea = nullptr;
    loadingTextPanel = nullptr;
}

//! \brief Selects and loads one picture for both startup and every existing loading path.
void selectLoadingImage()
{
    static std::mt19937 generator(std::random_device{}());
    std::uniform_int_distribution<int> distribution(0, previousImage < 0 ? 24 : 23);
    int image = distribution(generator);
    if(previousImage >= 0 && image >= previousImage)
        ++image;
    const std::string group = startupScene != nullptr ? "StartupLoading" : "Graphics";
    Ogre::TextureManager::getSingleton().load(LOADING_TEXTURES[image], group);
    loadingMaterial = createLoadingMaterial(LOADING_TEXTURES[image], group);
    previousImage = image;
}
}

//! \brief Uses the existing picture mechanism with only a camera and rectangle before full resource initialization.
LoadingScreen::LoadingScreen(Ogre::RenderWindow& window, Ogre::OverlaySystem& overlaySystem) : mContinueLoading(false), mStartup(true)
{
    try
    {
        startupWindow = &window;
        startupScene = Ogre::Root::getSingleton().createSceneManager("DefaultSceneManager", "LoadingScreenScene");
        startupScene->addRenderQueueListener(&overlaySystem);
        Ogre::Camera* camera = startupScene->createCamera("LoadingScreenCamera");
        window.addViewport(camera, STARTUP_VIEWPORT_ORDER);
        loadingRectangle = new Ogre::Rectangle2D(Ogre::String("LoadingScreenRectangle"), true);
        loadingRectangle->setBoundingBox(Ogre::AxisAlignedBox::BOX_INFINITE);
        startupScene->getRootSceneNode()->attachObject(loadingRectangle);
        selectLoadingImage();
        createLoadingRing(*startupScene, "StartupLoading");
        // The core OpenGL renderer needs shaders even before RTSS and its libraries exist.
        Ogre::HighLevelGpuProgramManager& programs = Ogre::HighLevelGpuProgramManager::getSingleton();
        Ogre::HighLevelGpuProgramPtr vertex = programs.createProgram("StartupLoadingVertex",
            "StartupLoading", "glsl", Ogre::GPT_VERTEX_PROGRAM);
        vertex->setSource("#version 150\nin vec4 vertex; in vec2 uv0; out vec2 pictureUV;"
            "void main(){gl_Position=vertex; pictureUV=uv0;}");
        vertex->load();
        Ogre::HighLevelGpuProgramPtr fragment = programs.createProgram("StartupLoadingFragment",
            "StartupLoading", "glsl", Ogre::GPT_FRAGMENT_PROGRAM);
        fragment->setSource("#version 150\nuniform sampler2D picture; in vec2 pictureUV; out vec4 colour;"
            "void main(){colour=texture(picture,pictureUV);}");
        fragment->load();
        Ogre::Pass* pass = loadingMaterial->getTechnique(0)->getPass(0);
        pass->setVertexProgram(vertex->getName());
        pass->setFragmentProgram(fragment->getName());
        pass->getFragmentProgramParameters()->setNamedConstant("picture", 0);
        Ogre::FontPtr font = Ogre::FontManager::getSingleton().create("StartupLoadingFont", "StartupLoading");
        font->setType(Ogre::FT_TRUETYPE);
        font->setSource("MedievalSharp-Bold.ttf");
        font->setTrueTypeSize(128);
        font->setTrueTypeResolution(72);
        font->addCodePointRange(Ogre::Font::CodePointRange(32, 126));
        font->load();
        Ogre::Pass* fontPass = font->getMaterial()->getTechnique(0)->getPass(0);
        fontPass->setVertexProgram(vertex->getName());
        fontPass->setFragmentProgram(fragment->getName());
        fontPass->getFragmentProgramParameters()->setNamedConstant("picture", 0);
        Ogre::Pass* ringPass = ringMaterial->getTechnique(0)->getPass(0);
        ringPass->setVertexProgram(vertex->getName());
        ringPass->setFragmentProgram(fragment->getName());
        ringPass->getFragmentProgramParameters()->setNamedConstant("picture", 0);
        createLoadingText("StartupLoadingFont", "StartupLoading");
        update();
        window.update();
        OD_LOG_INF("startup loading picture drawn");
        Ogre::ResourceGroupManager::getSingleton().addResourceGroupListener(this);
    }
    catch(...)
    {
        finish();
        throw;
    }
}

//! \brief Pumps events and redraws only the loading viewport, leaving partially built scenes untouched.
void LoadingScreen::presentStartup()
{
    if(startupWindow == nullptr || startupWindow->isClosed())
        return;
    Ogre::WindowEventUtilities::messagePump();
    if(startupWindow->isClosed())
        return;
    fitLoadingImage(*loadingRectangle, startupWindow->getWidth(), startupWindow->getHeight());
    if(ringRectangle != nullptr)
        fitLoadingRing(*ringRectangle, startupWindow->getWidth(), startupWindow->getHeight());
    startupWindow->_beginUpdate();
    startupWindow->_updateViewport(STARTUP_VIEWPORT_ORDER);
    startupWindow->_endUpdate();
    startupWindow->swapBuffers();
}

//! \brief Presents the startup picture after each synchronous resource script.
void LoadingScreen::scriptParseEnded(const Ogre::String&, bool)
{
    presentStartup();
}

//! \brief Presents the startup picture after each resource in a group load.
void LoadingScreen::resourceLoadEnded()
{
    presentStartup();
}

//! \brief Ends only startup loading, leaving every later load path under its existing ownership.
void LoadingScreen::finishStartup()
{
    if(startupScene != nullptr)
        finish();
}

//! \brief Saves the background visibility and immediately presents a uniformly selected nonrepeating picture.
LoadingScreen::LoadingScreen(CEGUI::Window* existingStatus) : mContinueLoading(false), mStartup(false)
{
    try
    {
        ODFrameListener* frame = ODFrameListener::getSingletonPtr();
        if(frame == nullptr || RenderManager::getSingletonPtr() == nullptr)
            return;
        if(loadingRectangle == nullptr)
        {
            loadingRectangle = static_cast<Ogre::Rectangle2D*>(RenderManager::getSingleton().getSceneManager()
                ->getSceneNode("Background")->getAttachedObject(0));
            previousMaterial = loadingRectangle->getMaterial();
            previousQueue = loadingRectangle->getRenderQueueGroup();
            previousRectangleVisible = loadingRectangle->isVisible();
            selectLoadingImage();
            createLoadingRing(*RenderManager::getSingleton().getSceneManager(), "Graphics");
            if(!Ogre::FontManager::getSingleton().getByName(LOADING_FONT_NAME, "GUI"))
            {
                Ogre::FontPtr font = Ogre::FontManager::getSingleton().create(LOADING_FONT_NAME, "GUI");
                font->setType(Ogre::FT_TRUETYPE);
                font->setSource("MedievalSharp-Bold.ttf");
                font->setTrueTypeSize(128);
                font->setTrueTypeResolution(72);
                font->addCodePointRange(Ogre::Font::CodePointRange(32, 126));
                font->load();
            }
            createLoadingText(LOADING_FONT_NAME, "GUI");
        }
        if(existingStatus != nullptr)
        {
            statusOverride = existingStatus;
            previousStatusText = existingStatus->getText();
            existingStatus->setText("Loading...");
        }
        update();
        // Updating only the render target avoids recursively processing input, sockets or mode changes.
        frame->getRenderWindow()->update();
    }
    catch(...)
    {
        finish();
        throw;
    }
}

//! \brief Restores the prior presentation when a synchronous stage fails or throws.
LoadingScreen::~LoadingScreen()
{
    if(mStartup)
        Ogre::ResourceGroupManager::getSingleton().removeResourceGroupListener(this);
    if(!mContinueLoading)
    {
        if(mStartup)
            finishStartup();
        else
            finish();
    }
}

//! \brief Leaves the picture visible while the client receives and creates the map.
void LoadingScreen::continueLoading()
{
    mContinueLoading = true;
}

//! \brief Releases startup resources or restores the game/menu material, rectangle and interface after loading.
void LoadingScreen::finish()
{
    if(loadingRectangle == nullptr && startupScene == nullptr)
        return;
    restoreLoadingInterface();
    if(startupScene != nullptr)
    {
        if(startupWindow->hasViewportWithZOrder(STARTUP_VIEWPORT_ORDER))
            startupWindow->removeViewport(STARTUP_VIEWPORT_ORDER);
        if(loadingRectangle != nullptr)
        {
            loadingRectangle->detachFromParent();
            delete loadingRectangle;
            loadingRectangle = nullptr;
        }
        destroyLoadingIndicator("StartupLoading");
        Ogre::Root::getSingleton().destroySceneManager(startupScene);
        startupScene = nullptr;
        startupWindow = nullptr;
        if(loadingMaterial)
        {
            loadingMaterial.reset();
            Ogre::MaterialManager::getSingleton().remove("LoadingScreen", "StartupLoading");
        }
        Ogre::ResourceGroupManager::getSingleton().destroyResourceGroup("StartupLoading");
        return;
    }
    ODFrameListener* frame = ODFrameListener::getSingletonPtr();
    Ogre::MaterialPtr material = frame != nullptr && frame->getIsMainMenuCreated() ? previousMaterial
        : Ogre::MaterialManager::getSingleton().getByName("Background", "Graphics");
    loadingRectangle->setMaterial(material);
    loadingRectangle->setRenderQueueGroup(previousQueue);
    loadingRectangle->setVisible(frame != nullptr && frame->getIsMainMenuCreated() ? previousRectangleVisible : true);
    loadingRectangle->setUVs(Ogre::Vector2(0, 0), Ogre::Vector2(0, 1), Ogre::Vector2(1, 0), Ogre::Vector2(1, 1));
    loadingRectangle->setCorners(-1, 1, 1, -1);
    loadingRectangle = nullptr;
    destroyLoadingIndicator("Graphics");
    previousMaterial.reset();
    loadingMaterial.reset();
    Ogre::MaterialManager::getSingleton().remove("LoadingScreen", "Graphics");
    if(frame != nullptr && frame->getIsMainMenuCreated())
        frame->updateMenuScene(0.0f);
}

//! \brief Fits the loading picture and shows existing or temporary status text once the GUI exists.
void LoadingScreen::update()
{
    if(loadingRectangle == nullptr)
        return;
    ODFrameListener* frame = ODFrameListener::getSingletonPtr();
    Ogre::RenderWindow* window = startupWindow != nullptr ? startupWindow : frame->getRenderWindow();
    loadingRectangle->setMaterial(loadingMaterial);
    loadingRectangle->setVisible(true);
    loadingRectangle->setRenderQueueGroup(RenderManager::OD_RENDER_QUEUE_ID_GUI - 1);
    fitLoadingImage(*loadingRectangle, window->getWidth(), window->getHeight());
    if(ringRectangle != nullptr)
        fitLoadingRing(*ringRectangle, window->getWidth(), window->getHeight());
    if(CEGUI::System::getSingletonPtr() == nullptr)
        return;
    CEGUI::Window* root = CEGUI::System::getSingleton().getDefaultGUIContext().getRootWindow();
    if(root == hiddenRoot)
    {
        // Existing editor success messages are restored after the asynchronous load finishes.
        if(loadingText != nullptr && loadingText->getText() != "Loading...")
        {
            deferredStatusText = loadingText->getText();
            hasDeferredStatus = true;
            loadingText->setText("Loading...");
        }
        return;
    }
    restoreLoadingInterface();
    if(root == nullptr)
        return;
    hiddenRoot = root;
    loadingText = statusOverride != nullptr ? statusOverride : findLoadingText(root);
    if(loadingText == nullptr)
    {
        temporaryLoadingText = CEGUI::WindowManager::getSingleton().createWindow("OD/StaticText");
        temporaryLoadingText->setArea(CEGUI::URect(CEGUI::UDim(0, 0), CEGUI::UDim(0.8f, 0),
            CEGUI::UDim(1, 0), CEGUI::UDim(0.8f, 20)));
        temporaryLoadingText->setText("Loading...");
        temporaryLoadingText->setProperty("FrameEnabled", "False");
        temporaryLoadingText->setProperty("BackgroundEnabled", "False");
        temporaryLoadingText->setProperty("HorzFormatting", "CentreAligned");
        root->addChild(temporaryLoadingText);
        loadingText = temporaryLoadingText;
    }
    previousRootAlpha = root->getAlpha();
    previousRootEnabled = !root->isDisabled();
    if(loadingText != nullptr)
    {
        previousTextAlpha = loadingText->getAlpha();
        previousTextInheritsAlpha = loadingText->inheritsAlpha();
        for(CEGUI::Window* visible = loadingText; visible != nullptr && visible != root; visible = visible->getParent())
        {
            previousVisibility.push_back(std::make_pair(visible, visible->isVisible()));
            visible->setVisible(true);
        }
        // The large overlay text replaces the small widget text, which only carries the status logic.
        loadingText->setAlpha(0.0f);
    }
    inheritLoadingAlpha(root);
    if(loadingText != nullptr)
        loadingText->setInheritsAlpha(false);
    rootDestruction = root->subscribeEvent(CEGUI::Window::EventDestructionStarted,
        CEGUI::Event::Subscriber(&loadingRootDestroyed));
    root->setAlpha(0.0f);
    root->setEnabled(false);
}
