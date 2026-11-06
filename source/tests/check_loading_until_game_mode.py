"""Wiring check (X1 rework, decision 664 d): the loading screen of a map load lasts until the game or editor mode is
open, so the configure-map dialog is not shown again after the loading screen (no compiler needed)."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


client = read('source/network/ODClient.cpp')
start = client.split('case ServerNotificationType::startGameMode:')[1].split('case ServerNotificationType::chat:')[0]
game = start.split('requestMode(AbstractModeManager::GAME);')[1].split('break;')[0]
editor = start.split('requestMode(AbstractModeManager::EDITOR);')[1].split('break;')[0]
assert 'loading.continueLoading();' in game and 'loading.continueLoading();' in editor

modes = read('source/modes/ModeManager.cpp')
assert '#include "render/LoadingScreen.h"' in modes
change = modes.split('void ModeManager::checkModeChange()')[1].split('void ModeManager::update')[0]
# ends after the new mode object exists and before it opens (no frame is drawn in between), and also when the mode is
# already the requested one
assert change.count('LoadingScreen::finish();') == 2
assert change.index('LoadingScreen::finish();', change.index('case GAME:')) < change.index('mCurrentApplicationMode->activate();')
print('ok')
