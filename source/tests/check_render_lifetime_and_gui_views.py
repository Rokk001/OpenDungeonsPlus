"""Guard GL owner lifetimes and scene-only GUI exclusion without compiling or launching the game."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
application = (repo / 'source/ODApplication.cpp').read_text(encoding='utf-8')
listener = (repo / 'source/render/ODFrameListener.cpp').read_text(encoding='utf-8')
renderer = (repo / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')


def check_shutdown(source):
    """Release visual owners before RTSS and preserve the primary context for Root's resource teardown."""
    source = source.split('void ODApplication::startClient()', 1)[1]
    start = source.index('// Keep the GL context and shader generator alive')
    opening = source.index('{', start)
    depth = 0
    closing = None
    for match in re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}]', source[opening:], re.S):
        token = match.group()
        if token == '{':
            depth += 1
        elif token == '}':
            depth -= 1
            if depth == 0:
                closing = opening + match.start()
                break
    assert closing is not None
    owners = source[opening:closing]
    for declaration in ('RenderManager renderManager(', 'Gui gui(', 'TextRenderer textRenderer;', 'ODFrameListener frameListener('):
        assert declaration in owners
    assert owners.index('client.disconnect();') < owners.index('server.stopServer();')
    assert owners.index('ogreRoot.removeFrameListener(&frameListener);') < owners.index('frameListener.prepareRenderWindowShutdown();')
    assert source.index('Ogre::Root ogreRoot(') < opening
    assert source.index('Ogre::RTShader::ShaderGenerator::destroy();', opening) > closing
    # A completed owner scope is insufficient: Root still has mesh/texture hardware resources.
    # Ogre documents that the primary window's context must survive until its own shutdown.
    assert not re.search(r'ogreRoot\s*\.\s*destroyRenderTarget\s*\(\s*renderWindow\s*\)', source)
    assert not re.search(r'renderWindow\s*->\s*destroy\s*\(', source)
    assert not re.search(r'ogreRoot\s*\.\s*shutdown\s*\(', source)


def check_gui(source):
    """Require the GUI draw itself to be guarded by the current viewport and shadow stage."""
    callback = source.split('void ODFrameListener::renderQueueStarted(', 1)[1].split('bool ODFrameListener::quit(', 1)[0]
    condition = callback.split('if(', 1)[1].split('\n    {', 1)[0]
    for required in ('queueGroupId == RenderManager::OD_RENDER_QUEUE_ID_GUI',
                     'scene->_getCurrentRenderStage() != Ogre::SceneManager::IRS_RENDER_TO_TEXTURE',
                     'viewport != nullptr && viewport->getOverlaysEnabled()'):
        assert required in condition
    assert 'Ogre::Viewport* viewport = scene->getCurrentViewport();' in callback
    body = callback.split('\n    {', 1)[1].split('\n    }', 1)[0]
    assert 'CEGUI::System::getSingleton().renderAllGUIContexts();' in body
    assert 'setScissorTest(false)' in body


check_shutdown(application)
check_gui(listener)
# The smoke capture explicitly requests a scene without overlays and still updates every frame.
assert 'tmpViewport->setOverlaysEnabled(false);' in renderer
assert 'mRenderManager->mRenderTarget->update();' in listener
# Independent regressions must be rejected rather than merely checking function existence.
mutations = [
    (check_shutdown, application.replace('    Ogre::RTShader::ShaderGenerator::destroy();', '', 1).replace('    frameListener.prepareRenderWindowShutdown();', '    Ogre::RTShader::ShaderGenerator::destroy();\n    frameListener.prepareRenderWindowShutdown();', 1)),
    (check_shutdown, application.replace('    frameListener.prepareRenderWindowShutdown();', '    ogreRoot.destroyRenderTarget(renderWindow);\n    frameListener.prepareRenderWindowShutdown();', 1)),
    (check_shutdown, application.replace('    Ogre::RTShader::ShaderGenerator::destroy();', '    Ogre::RTShader::ShaderGenerator::destroy();\n    ogreRoot.destroyRenderTarget(renderWindow);', 1)),
    (check_shutdown, application.replace('    Ogre::RTShader::ShaderGenerator::destroy();', '    Ogre::RTShader::ShaderGenerator::destroy();\n    renderWindow->destroy();', 1)),
    (check_shutdown, application.replace('    frameListener.prepareRenderWindowShutdown();', '    ogreRoot.shutdown();\n    frameListener.prepareRenderWindowShutdown();', 1)),
    (check_gui, listener.replace('viewport != nullptr && viewport->getOverlaysEnabled()', 'viewport != nullptr', 1)),
    (check_gui, listener.replace('scene->_getCurrentRenderStage() != Ogre::SceneManager::IRS_RENDER_TO_TEXTURE', 'true', 1)),
]
for check, mutated in mutations:
    try:
        check(mutated)
    except (AssertionError, ValueError):
        continue
    raise AssertionError('unsafe lifetime or GUI mutation was accepted')
print('ok: visual owners released before RTSS; primary context retained for Root; scene-only views skip GUI; seven mutations rejected')
