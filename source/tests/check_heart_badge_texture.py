"""Update the heart badge with the real CEGUI Ogre renderer and read back what the badge image shows.

The heart ring in the top left corner did not move when the heart was hit. The badge image
(OpenDungeonsIcons/ManaBadge) refers to the CEGUI texture "ManaBadge"; a window caches its geometry
together with the Ogre texture it had when it was drawn (CEGUI's OgreGeometryBuffer::appendGeometry
stores getOgreTexture() in the batch). OgreTexture::loadFromMemory makes a new Ogre texture on every call,
so the redrawn ring went into a texture the badge never showed again.

This check links OgreMain and the CEGUI Ogre renderer, opens a hidden window, bootstraps CEGUI, creates
the badge texture the way Gui.cpp does, and then:
- reproduces the cause: loadFromMemory replaces the Ogre texture;
- runs the real Gui::updateHeartBadge and drawBadgePixels, cut out of Gui.cpp by signature, and checks
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
args = parser.parse_args()
if args.loading_screens and args.loading_output is None:
    parser.error('--loading-screens requires --loading-output')
repo = Path(__file__).resolve().parents[2]
deps = Path(os.environ.get('OD_DEPS_ROOT', str(Path.home() / 'od-deps')))
gui = (repo / 'source/render/Gui.cpp').read_text()
rules = repo / 'source/game/HeartHealthRing.h'


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
badge_code = 'const int BADGE_SIZE = 128;\n' + '\n'.join(function(gui, signature) for signature in badge_helpers) + '\n'

probe = r'''
#include <cmath>
#include <iostream>
#include <string>
#include <vector>
#include <Ogre.h>
#include <OgreRectangle2D.h>
#include <OgreHardwarePixelBuffer.h>
#include <OgreRenderTexture.h>
#include <OgrePixelFormat.h>
#include <algorithm>
#include <CEGUI/CEGUI.h>
#include <CEGUI/RendererModules/Ogre/Renderer.h>
#include <CEGUI/RendererModules/Ogre/Texture.h>
#include <RTShaderSystem/OgreShaderGenerator.h>
#include <Bites/OgreSGTechniqueResolverListener.h>
#include "RULES_HEADER"

BADGE_CODE
UPDATE
LOADING_HELPERS

int gChecks = 0, gFailures = 0;
void check(bool ok, const std::string& msg) {++gChecks;if(!ok){++gFailures;std::cout << "FAIL " << msg << '\n';}}

std::vector<unsigned char> readBack(CEGUI::Texture& texture)
{
    Ogre::TexturePtr ogreTexture = static_cast<CEGUI::OgreTexture&>(texture).getOgreTexture();
    std::vector<unsigned char> pixels(BADGE_SIZE * BADGE_SIZE * 4);
    Ogre::PixelBox box(BADGE_SIZE, BADGE_SIZE, 1, ogreTexture->getFormat(), pixels.data());
    ogreTexture->getBuffer()->blitToMemory(box);
    return pixels;
}

// Is the ring pixel at an angle (degrees clockwise from the top) green? Spokes are grey, the groove is dark.
bool ringGreen(const std::vector<unsigned char>& pixels, float angle)
{
    const float radians = angle * 3.14159265f / 180.0f;
    const int x = static_cast<int>((23.0f * std::sin(radians) + 32.0f) * BADGE_SIZE / 64.0f);
    const int y = static_cast<int>((-23.0f * std::cos(radians) + 32.0f) * BADGE_SIZE / 64.0f);
    const int i = (y * BADGE_SIZE + x) * 4;
    return pixels[i + 1] - pixels[i] > 40;
}

//! \brief Checks the live badge texture and optionally renders the production loading screen.
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
    root->setRenderSystem(root->getAvailableRenderers().front());
    root->initialise(false);
    Ogre::NameValuePairList options;
    options["hidden"] = "true";
    Ogre::RenderWindow* window = root->createRenderWindow("Badge", 256, 256, false, &options);
    // As the game: the shader generator supplies the GPU programs the GL3+ renderer needs
    Ogre::ResourceGroupManager& resources = Ogre::ResourceGroupManager::getSingleton();
    resources.addResourceLocation(prefix + "/Media/Main", "FileSystem", "OgreInternal");
    resources.addResourceLocation(prefix + "/Media/RTShaderLib", "FileSystem", "General");
    resources.initialiseAllResourceGroups();
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
    CEGUI::Texture& badge = renderer.createTexture("ManaBadge");
    badge.loadFromMemory(full.data(), CEGUI::Sizef(BADGE_SIZE, BADGE_SIZE), CEGUI::Texture::PF_RGBA);
    const Ogre::TexturePtr shown = static_cast<CEGUI::OgreTexture&>(badge).getOgreTexture();
    check(readBack(badge) == full, "the full ring is in the badge texture");

    // The cause: loading again makes a new Ogre texture; a window that cached the first one keeps showing it
    {
        CEGUI::Texture& probe = renderer.createTexture("Probe");
        probe.loadFromMemory(full.data(), CEGUI::Sizef(BADGE_SIZE, BADGE_SIZE), CEGUI::Texture::PF_RGBA);
        const Ogre::Texture* first = static_cast<CEGUI::OgreTexture&>(probe).getOgreTexture().get();
        probe.loadFromMemory(full.data(), CEGUI::Sizef(BADGE_SIZE, BADGE_SIZE), CEGUI::Texture::PF_RGBA);
        const Ogre::Texture* second = static_cast<CEGUI::OgreTexture&>(probe).getOgreTexture().get();
        check(first != second, "reproduced: loadFromMemory replaces the Ogre texture the badge window had cached");
        renderer.destroyTexture("Probe");
    }

    // The production update after a hit: the same Ogre texture now holds the smaller ring
    updateHeartBadge(0.4f, true);
    std::vector<unsigned char> expected;
    drawBadgePixels(expected, 0, 0.4f, true);
    check(static_cast<CEGUI::OgreTexture&>(badge).getOgreTexture().get() == shown.get(),
        "updateHeartBadge keeps the Ogre texture the badge window shows");
    const std::vector<unsigned char> after = readBack(badge);
    check(after == expected, "the shown texture holds the ring of the new health");
    check(after != full, "the shown ring is no longer the full ring");
    updateHeartBadge(0.0f, false);
    std::vector<unsigned char> empty;
    drawBadgePixels(empty, 0, 0.0f, false);
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
probe = probe.replace('LOADING_CODEC', 'root->loadPlugin(prefix + "/bin/Codec_STBI");' if args.loading_screens else '')

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
    include = deps / 'install/include'
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++17', '/W1', '/I', str(include / 'OGRE'),
                    '/I', str(include / 'OGRE/RTShaderSystem'), '/I', str(include / 'cegui-0'), 'check.cpp', '/Fecheck.exe', '/link',
                    '/LIBPATH:' + str(deps / 'install/lib'), 'OgreMain.lib', 'OgreRTShaderSystem.lib', 'OgreBites.lib', 'CEGUIBase-0.lib',
                    'CEGUIOgreRenderer-0.lib'],
                   cwd=work, check=True)
    environment = dict(os.environ)
    environment['PATH'] = str(deps / 'install/bin') + os.pathsep + environment.get('PATH', '')
    # Windows may block a freshly compiled executable (WinError 4551) for a moment
    for attempt in range(4):
        try:
            command = [str(work / 'check.exe'), str(deps / 'install').as_posix()]
            if args.loading_screens:
                command.extend([repo.as_posix(), args.loading_output.resolve().as_posix()])
            subprocess.run(command, cwd=work, check=True, env=environment)
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
