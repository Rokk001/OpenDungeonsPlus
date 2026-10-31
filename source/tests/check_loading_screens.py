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
    startup = application.index("LoadingScreen startupLoading(*renderWindow);")
    assert application.index('misc["hidden"] = "true";') < startup, "native window must start hidden"
    resources = application.index("resMgr.setupOgreResources(")
    shaders = application.index("if (!Ogre::RTShader::ShaderGenerator::initialize())")
    shown = application.index("renderWindow->setHidden(false);")
    assert startup < shown < resources < shaders, "show the first picture before full resource setup and RTSS"
    assert application.index('"materials/textures/loading", "FileSystem", "StartupLoading"') < startup, "register only the picture folder before drawing"
    assert startup < application.index("renderWindow->setVisible(true);", startup), "present the loading picture before showing the native window"
    constructor = source.split("LoadingScreen::LoadingScreen(Ogre::RenderWindow& window)", 1)[1].split("void LoadingScreen::presentStartup()", 1)[0]
    assert "selectLoadingImage();" in constructor and "update();" in constructor and "window.update();" in constructor, "startup must present the shared picture mechanism"
    assert "ShaderGenerator" not in constructor, "the first picture must not depend on RTSS"
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
    finish = source.split("void LoadingScreen::finish()", 1)[1].split("void LoadingScreen::update()", 1)[0]
    for cleanup in ("removeViewport(STARTUP_VIEWPORT_ORDER)", "destroySceneManager(startupScene)", 'destroyResourceGroup("StartupLoading")'):
        assert cleanup in finish, f"missing startup resource cleanup: {cleanup}"
    destructor = source.split("LoadingScreen::~LoadingScreen()", 1)[1].split("void LoadingScreen::continueLoading()", 1)[0]
    assert "if(mStartup)" in destructor and "finishStartup();" in destructor, "startup guard must not finish later load stages"
    listener = (root / "source/render/ODFrameListener.cpp").read_text(encoding="utf-8")
    menu = listener.split("void ODFrameListener::createMainMenuScene()", 1)[1].split("void ODFrameListener::freeMainMenuScene()", 1)[0]
    assert menu.index("resetMenu(") < menu.index("LoadingScreen::finishStartup();"), "keep the startup picture until menu creation finishes"
    print(f"OK: 25 referenced loading pictures, 1920x1080, {total} bytes; startup order and cleanup")


if __name__ == "__main__":
    main()
