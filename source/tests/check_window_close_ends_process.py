"""Wiring check (decision 841): closing the window with the X button ends the render loop and runs the shutdown;
no frame is rendered after the window close handler dropped the mode manager."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
app = (repo / 'source/ODApplication.cpp').read_text(encoding='utf-8')
listener = (repo / 'source/render/ODFrameListener.cpp').read_text(encoding='utf-8')

loop = app.split('#ifdef OD_USE_SFML_WINDOW\n    bool running = true;')[1].split('#else /* OD_USE_SFML_WINDOW */')[0]
closed = loop.split('sf::Event::Closed>())')[1].split('else')[0]
assert 'frameListener.requestExit();' in closed and 'running = false;' in closed and 'break;' in closed
guard = 'if(!running || frameListener.isExitRequested())\n            break;'
assert guard in loop and loop.index(guard) < loop.index('ogreRoot.renderOneFrame()')

for name in ('frameStarted', 'frameEnded'):
    body = listener.split('bool ODFrameListener::%s(' % name)[1].split('{', 1)[1][:200]
    assert 'if(!mModeManager)' in body, name
assert 'mWindow->isClosed() || !mModeManager' in listener
print('ok')
