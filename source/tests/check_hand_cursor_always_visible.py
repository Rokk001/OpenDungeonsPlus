"""Wiring check (decision 839): the keeper hand is the only visible mouse cursor, so no key may hide it and the
game mode restores it every frame (except during the defeat sequence, which hides and restores it itself)."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
game = (repo / 'source/modes/GameMode.cpp').read_text(encoding='utf-8')

f9 = game.split('case OIS::KC_F9:')[1].split('break;')[0]
assert 'isKeeperHandVisible()' in f9 and 'mDefeatSequence.isStarted()' in f9
assert 'rrToggleHandSelectorVisibility' in f9 and '!RenderManager::getSingleton().isKeeperHandVisible()' in f9

feedback = game.split('void GameMode::refreshActionFeedback(float elapsed)')[1].split('\nvoid GameMode::resetIdleHand()')[0]
restore = ('if(!mDefeatSequence.isStarted() && !RenderManager::getSingleton().isKeeperHandVisible())\n'
           '        RenderManager::getSingleton().rrToggleHandSelectorVisibility();')
assert restore in feedback
assert 'getMouseCursor().setVisible(!mDefeatSequence.isStarted())' in feedback
assert feedback.index(restore) < feedback.index('updateIdleHand(elapsed')
print('ok')
