"""Cursor trigger check (decision 845 item 1): the mouse cursor vanished during play.

The keeper hand is the only visible pointer: the system cursor is hidden for the whole game window and the CEGUI
arrow image is transparent. The trigger was the F9 key, which toggled the hand off with nothing that brought it back
(F9 sits between F8 load and F10 options). Windows, the Dungeonbook, pick-up, menus and camera moves never hide the
hand; only F9 and the defeat sequence call the toggle. This check pins that list (counted once on the branch: five
calls in GameMode.cpp, one in RenderSceneMenu.cpp, none elsewhere) and that F9 can only
restore the hand, and that the game mode gives the hand and the pointer back every frame outside the defeat sequence.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
source = repo / 'source'

# Every caller of the hand toggle, outside its definition in RenderManager.cpp
expected = {'modes/GameMode.cpp': 5, 'renderscene/RenderSceneMenu.cpp': 1}
found = {}
for path in source.rglob('*.cpp'):
    if 'tests' in path.parts:
        continue
    text = path.read_text(encoding='utf-8', errors='replace')
    count = text.count('rrToggleHandSelectorVisibility();')
    if count:
        found[path.relative_to(source).as_posix()] = count
assert found == expected, 'unexpected hand toggle callers: %r' % found

game = (source / 'modes/GameMode.cpp').read_text(encoding='utf-8')

# Trigger: F9 may only bring a hidden hand back, never hide it
f9 = game.split('case OIS::KC_F9:')[1].split('break;')[0]
assert 'if(!RenderManager::getSingleton().isKeeperHandVisible() && !mDefeatSequence.isStarted())' in f9, \
    'F9 still hides the keeper hand (the cursor of the game)'

# Every other GameMode call belongs to the defeat sequence (hide, restore on its end and when the game is left)
heads = [(m.start(), m.group(1)) for m in re.finditer(r'^(?![\s/#])[^\n]*?GameMode::(~?\w+)\(', game, re.M)]
owners = []
for m in re.finditer(r'rrToggleHandSelectorVisibility\(\);', game):
    owners.append([name for start, name in heads if start < m.start()][-1])
assert sorted(owners) == sorted(['~GameMode', 'keyPressedNormal', 'startDefeatSequence', 'showDefeatDebriefing',
                                 'refreshActionFeedback']), 'hand toggled in %r' % owners

# The system cursor stays hidden on purpose: the hand is the pointer
app = (source / 'ODApplication.cpp').read_text(encoding='utf-8')
assert 'sfmlWindow.setMouseCursorVisible(false);' in app

# Restored every frame outside the defeat sequence
feedback = game.split('void GameMode::refreshActionFeedback(float elapsed)')[1].split('\nvoid GameMode::resetIdleHand()')[0]
assert ('if(!mDefeatSequence.isStarted() && !RenderManager::getSingleton().isKeeperHandVisible())\n'
        '        RenderManager::getSingleton().rrToggleHandSelectorVisibility();') in feedback
assert 'getMouseCursor().setVisible(!mDefeatSequence.isStarted())' in feedback
print('ok')
