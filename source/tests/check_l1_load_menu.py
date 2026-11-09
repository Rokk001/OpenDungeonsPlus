"""Check the sole saved-game entry, save restrictions and load-menu flights without compiling."""
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
def read(path):
    return (root / path).read_text(encoding="utf-8")
def names(path):
    return {node.get("name") for node in ET.parse(root / path).iter("Window")}
def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]

main = read("source/modes/MenuModeMain.cpp")
game = read("source/modes/GameMode.cpp")
manager = read("source/modes/ModeManager.cpp")
load = read("source/modes/MenuModeLoad.cpp")
assert "LoadGameButton" in names("gui/MenuMain.layout")
assert "StartReplayButton" not in names("gui/MenuMain.layout")
assert "LoadSkirmishButton" not in names("gui/WindowSkirmishSubMenu.layout")
assert "LoadGameButton" not in names("gui/WindowGameOptions.layout")
assert "SaveGameButton" in names("gui/WindowGameOptions.layout")
assert "KC_F8" not in game
keys = function(game, "bool GameMode::keyPressedNormal(")
assert "case OIS::KC_F5:" in keys and "saveGame();" in keys
page = function(game, "void GameMode::setOptionsPage(")
save = function(game, "bool GameMode::saveGame(")
assert "isConnected() &&" in page and "!= ServerMode::ModeGameMultiPlayer" in page
assert 'setVisible(!endGame && canSave)' in page and 'entries.erase(entries.begin() + 2)' in page
assert '!ODServer::getSingleton().isConnected() ||' in save
assert '== ServerMode::ModeGameMultiPlayer' in save
assert save.index('return true;') < save.index('hideOptionsWindow();') < save.index('askSaveMap')
assert 'ModeGameSinglePlayer' in read('source/modes/MenuModeSkirmish.cpp')
assert 'ModeGameMultiPlayer' in read('source/modes/MenuModeMultiplayerServer.cpp')
assert 'connectModeChangeEvent(BUTTON_LOAD_GAME, AbstractModeManager::ModeType::MENU_LOAD_SAVEDGAME)' in main
flight = function(main, 'bool MenuModeMain::changeModeAfterFlight(')
assert 'isMainMenuFlightActive()' in flight and 'MENU_LOAD_SAVEDGAME' in flight
assert 'flyMainMenuTo(PLACE_REPLAY)' in flight and 'showMainMenuButtons(false)' in flight and 'mPendingMode = mode' in flight
assert 'if(!mInGame)' in function(load, 'bool MenuModeLoad::closeBrowser(')
assert 'return goBack();' in function(load, 'bool MenuModeLoad::closeBrowser(')
assert 'flyMainMenuTo(PLACE_OVERVIEW)' in function(manager, 'void ModeManager::checkModeChange(')
print('OK: L1 menu entries, save guards and flight routing')
