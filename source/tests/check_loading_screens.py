#!/usr/bin/env python3
"""Check the complete loading-picture set against the production selector."""
from pathlib import Path
import re
import struct


# Read JPEG frame dimensions without requiring an optional image package.
def jpeg_dimensions(path):
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        raise AssertionError(f"not a JPEG: {path}")
    offset = 2
    while offset < len(data):
        if data[offset] != 0xFF:
            raise AssertionError(f"invalid JPEG marker: {path}")
        while data[offset] == 0xFF:
            offset += 1
        marker = data[offset]
        offset += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        length = struct.unpack_from(">H", data, offset)[0]
        if marker in (0xC0, 0xC1, 0xC2):
            height, width = struct.unpack_from(">HH", data, offset + 3)
            return width, height
        offset += length
    raise AssertionError(f"missing JPEG dimensions: {path}")


# Verify every named selector entry, every asset and the requested total size limit.
def main():
    root = Path(__file__).resolve().parents[2]
    source = (root / "source/render/LoadingScreen.cpp").read_text(encoding="utf-8")
    table = source.split("const char* const LOADING_TEXTURES[] = {", 1)[1].split("};", 1)[0]
    names = re.findall(r'"(loading_\d{2}\.jpg)"', table)
    expected = [f"loading_{number:02d}.jpg" for number in range(1, 26)]
    assert names == expected, "selector must reference exactly the 25 loading pictures"
    folder = root / "materials/textures/loading"
    assert sorted(path.name for path in folder.glob("*.jpg")) == expected, "loading picture set is incomplete"
    total = 0
    for name in names:
        path = folder / name
        assert jpeg_dimensions(path) == (1920, 1080), f"wrong dimensions: {name}"
        total += path.stat().st_size
    assert total < 25_000_000, f"loading picture set exceeds 25 MB: {total}"
    resources = (root / "cmake/config/resources.cfg.in").read_text(encoding="utf-8")
    assert "FileSystem=materials/textures/loading" in resources, "loading images must be discoverable by Ogre"
    application = (root / "source/ODApplication.cpp").read_text(encoding="utf-8")
    startup = application.index("LoadingScreen startupLoading(*renderWindow, overlaySystem);")
    assert application.index('misc["hidden"] = "true";') < startup, "native window must start hidden"
    resources = application.index("resMgr.setupOgreResources(")
    shaders = application.index("if (!Ogre::RTShader::ShaderGenerator::initialize())")
    shown = application.index("renderWindow->setHidden(false);")
    assert startup < shown < resources < shaders, "show the first picture before full resource setup and RTSS"
    assert application.index('"materials/textures/loading", "FileSystem", "StartupLoading"') < startup, "register only the picture folder before drawing"
    assert startup < application.index("renderWindow->setVisible(true);", startup), "present the loading picture before showing the native window"
    constructor = source.split("LoadingScreen::LoadingScreen(Ogre::RenderWindow& window, Ogre::OverlaySystem& overlaySystem)", 1)[1].split("void LoadingScreen::presentStartup()", 1)[0]
    assert "selectLoadingImage();" in constructor and "update();" in constructor and "window.update();" in constructor, "startup must present the shared picture mechanism"
    assert "ShaderGenerator" not in constructor, "the first picture must not depend on RTSS"
    for token in ('addRenderQueueListener(&overlaySystem)', 'createLoadingText("StartupLoadingFont", "StartupLoading")', 'createLoadingRing(*startupScene, "StartupLoading")', "ringPass->setFragmentProgram("):
        assert token in constructor, f"missing startup loading text or ring: {token}"
    text = source.split("void createLoadingText(", 1)[1].split("void destroyLoadingIndicator(", 1)[0]
    for token in ('setCaption("Loading...")', "loadingOverlay->show()", "GMM_RELATIVE", "setCharHeight(LOADING_TEXT_HEIGHT)"):
        assert token in text, f"missing overlay text setup: {token}"
    height = float(re.search(r"LOADING_TEXT_HEIGHT = ([0-9.]+)f", source).group(1))
    assert height >= 0.06, "the loading text must be at least 6 percent of the window height (65 px at 1080p, 130 px at 4K)"
    fonts = re.findall(r"setTrueTypeSize\((\d+)\)", source)
    assert fonts and all(int(size) >= 96 for size in fonts), "the font bitmap must stay sharp when the text is scaled up"
    # The ember ring: material, rotation by time, creation on the startup path and on every later path, cleanup.
    assert 'createTextureUnitState("loading_ring.png")' in source and "SBT_TRANSPARENT_ALPHA" in source, "ring material missing"
    ring = source.split("void fitLoadingRing(", 1)[1].split("void createLoadingRing(", 1)[0]
    assert "steady_clock" in ring and "LOADING_RING_SECONDS" in ring and "setUVs(" in ring, "the ring must turn with time"
    later_construct = source.split("LoadingScreen::LoadingScreen(CEGUI::Window* existingStatus)", 1)[1].split("catch(...)", 1)[0]
    assert 'createLoadingRing(*RenderManager::getSingleton().getSceneManager(), "Graphics")' in later_construct and "createLoadingText(LOADING_FONT_NAME" in later_construct, "later load paths must create ring and text"
    assert source.count("fitLoadingRing(*ringRectangle") == 2, "startup present and update() must both advance the ring"
    assert 'destroyLoadingIndicator("StartupLoading")' in source and 'destroyLoadingIndicator("Graphics")' in source, "ring and text must be released on both paths"
    assert "loadingText->setAlpha(0.0f);" in source, "the small widget text must not draw over the large text"
    ring_png = (root / "materials/textures/loading/loading_ring.png").read_bytes()
    assert ring_png[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack_from(">II", ring_png, 16) == (256, 256), "ring texture missing or wrong size"
    for token in ('"StartupLoadingVertex"', '"StartupLoadingFragment"', "vertex->setSource(", "fragment->setSource(", 'setNamedConstant("picture", 0)'):
        assert token in constructor, f"missing standalone startup shader setup: {token}"
    present = source.split("void LoadingScreen::presentStartup()", 1)[1].split("void LoadingScreen::scriptParseEnded", 1)[0]
    for token in ("messagePump();", "_updateViewport(STARTUP_VIEWPORT_ORDER)", "swapBuffers();"):
        assert token in present, f"startup must pump and present only its own viewport: {token}"
    assert "window.update()" not in present, "do not render a partially initialized menu"
    assert "presentStartup();" in source.split("void LoadingScreen::scriptParseEnded", 1)[1].split("void LoadingScreen::finishStartup", 1)[0], "resource initialization must refresh the picture"
    for stage in ("resMgr.setupOgreResources(", "Ogre::ResourceGroupManager::getSingletonPtr()->initialiseAllResourceGroups();", "SoundEffectsManager soundEffectsManager;", "pybind11::gil_scoped_release pythonMainThreadRelease;", "Gui gui("):
        start = application.index("\n    " + stage, startup)
        following = application[start:].splitlines()[2].strip()
        assert following == "LoadingScreen::presentStartup();", f"missing startup present after {stage}"
    groups = (root / "source/renderscene/RenderSceneGroup.cpp").read_text(encoding="utf-8")
    reset = groups.split("void RenderSceneGroup::reset(", 1)[1].split("void RenderSceneGroup::freeGroup(", 1)[0]
    assert reset.index("scene->activate(") < reset.index("LoadingScreen::presentStartup();") < reset.index("++mIndexScene;"), "refresh between synchronous menu commands"
    update = source.split("void LoadingScreen::update()", 1)[1]
    fallback = update.split("if(loadingText == nullptr)", 1)[1].split("previousRootAlpha", 1)[0]
    assert 'createWindow("OD/StaticText")' in fallback and 'setText("Loading...")' in fallback, "missing fallback loading text"
    assert "root->addChild(temporaryLoadingText);" in fallback and "loadingText = temporaryLoadingText;" in fallback, "fallback text must be attached and shown"
    restore = source.split("void restoreLoadingInterface()", 1)[1].split("bool loadingRootDestroyed", 1)[0]
    assert "destroyWindow(temporaryLoadingText);" in restore, "temporary loading text must be removed"
    destroyed = source.split("bool loadingRootDestroyed", 1)[1].split("void fitLoadingImage", 1)[0]
    assert "temporaryLoadingText = nullptr;" in destroyed, "root destruction must clear the temporary text pointer"
    finish = source.split("void LoadingScreen::finish()", 1)[1].split("void LoadingScreen::update()", 1)[0]
    for cleanup in ("removeViewport(STARTUP_VIEWPORT_ORDER)", "destroySceneManager(startupScene)", 'destroyResourceGroup("StartupLoading")'):
        assert cleanup in finish, f"missing startup resource cleanup: {cleanup}"
    destructor = source.split("LoadingScreen::~LoadingScreen()", 1)[1].split("void LoadingScreen::continueLoading()", 1)[0]
    assert "if(mStartup)" in destructor and "finishStartup();" in destructor, "startup guard must not finish later load stages"
    listener = (root / "source/render/ODFrameListener.cpp").read_text(encoding="utf-8")
    menu = listener.split("void ODFrameListener::createMainMenuScene()", 1)[1].split("void ODFrameListener::freeMainMenuScene()", 1)[0]
    assert menu.index("resetMenu(") < menu.index("LoadingScreen::finishStartup();"), "keep the startup picture until menu creation finishes"
    # Every later load path constructs the screen and so reaches update(), whose fallback covers a root without a text.
    sites = {}
    for path in (root / "source").rglob("*.cpp"):
        if path.name == "LoadingScreen.cpp":
            continue
        found = re.findall(r"(?m)^\s*LoadingScreen \w+[;(]", path.read_text(encoding="utf-8", errors="replace"))
        if found:
            sites[path.name] = len(found)
    expected_sites = {"EditorMode.cpp": 2, "MenuModeConfigureSeats.cpp": 1, "MenuModeEditorNew.cpp": 1, "ODClient.cpp": 3, "ODServer.cpp": 1, "ODApplication.cpp": 1}
    assert sites == expected_sites, "review the loading text of a changed load path: " + str(sites)
    later = source.split("LoadingScreen::LoadingScreen(CEGUI::Window* existingStatus)", 1)[1].split("catch(...)", 1)[0]
    assert "update();" in later and "getRenderWindow()->update();" in later, "every later load path must show its text at once"
    assert "statusOverride != nullptr ? statusOverride : findLoadingText(root);" in source, "the text must come from the override or the sheet before the fallback"
    print(f"OK: 25 referenced loading pictures, 1920x1080, {total} bytes; startup order and cleanup; {sum(sites.values())} load paths show their text")


if __name__ == "__main__":
    main()
