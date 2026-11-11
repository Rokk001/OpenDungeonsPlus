/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "modes/MenuModeLoad.h"
#include "modes/MenuModeReplay.h"
#include "modes/LoadGameFilter.h"

#include "utils/Helper.h"
#include "render/Gui.h"
#include "modes/ModeManager.h"
#include "sound/MusicPlayer.h"
#include "gamemap/GameMap.h"
#include "render/ODFrameListener.h"
#include "network/ODServer.h"
#include "network/ODClient.h"
#include "network/ServerMode.h"
#include "network/ServerNotification.h"
#include "utils/LogManager.h"
#include "gamemap/MapHandler.h"
#include "utils/ConfigManager.h"
#include "utils/ResourceManager.h"

#include <CEGUI/CEGUI.h>
#include <CEGUI/widgets/Scrollbar.h>
#include <algorithm>
#include <ctime>
#include "boost/filesystem.hpp"

const std::string SAVEGAME_EXTENSION = ".level";

//! \brief Collects every loadable saved game (not multiplayer) and replay with its kind.
static std::vector<LoadEntry> collectLoadEntries()
{
    std::vector<LoadEntry> entries;
    std::vector<std::string> saves;
    std::vector<std::string> replays;
    Helper::fillFilesList(ResourceManager::getSingleton().getSaveGamePath(), saves, SAVEGAME_EXTENSION);
    Helper::fillFilesList(ResourceManager::getSingleton().getReplayDataPath(), replays, ".odr");
    for(const std::string& file : saves)
    {
        LevelInfo info;
        bool valid = MapHandler::getMapInfo(file, info);
        int kind = classifyLoadSave(boost::filesystem::path(file).filename().string(), valid, info, Campaign::getSingleton());
        if(kind >= 0)
            entries.push_back({file, boost::filesystem::last_write_time(file), kind});
    }
    for(const std::string& file : replays)
        entries.push_back({file, boost::filesystem::last_write_time(file), 3});
    return entries;
}

//! \brief Sets up the unified save and replay browser.
MenuModeLoad::MenuModeLoad(ModeManager *modeManager, bool inGame, const std::string& savedGame):
    AbstractApplicationMode(modeManager, ModeManager::MENU_LOAD_SAVEDGAME),
    mInGame(inGame),
    mSavedGame(savedGame)
{
    CEGUI::Window* window = modeManager->getGui().getGuiSheet(Gui::guiSheet::loadSavedGameMenu);
    CEGUI::Combobox* filter = static_cast<CEGUI::Combobox*>(window->getChild("LevelWindowFrame/KindFilter"));
    filter->resetList();
    const char* names[] = {"Campaign", "Skirmish", "Sandbox", "Replays"};
    for(size_t i = 0; i < 4; ++i)
    {
        CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(names[i]);
        item->setSelectionBrushImage("OpenDungeonsSkin/SelectionBrush");
        filter->addItem(item);
    }
    addEventConnection(filter->subscribeEvent(CEGUI::Combobox::EventListSelectionAccepted,
        CEGUI::Event::Subscriber(&MenuModeLoad::updateFilesList, this)));
    addEventConnection(
        window->getChild("LevelWindowFrame/BackButton")->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeLoad::closeBrowser, this)
        )
    );
    addEventConnection(
        window->getChild("LevelWindowFrame/LaunchButton")->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeLoad::launchSelectedButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild("LevelWindowFrame/DeleteButton")->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeLoad::deleteSelectedButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild("LevelWindowFrame/SaveGameSelect")->subscribeEvent(
            CEGUI::Listbox::EventMouseClick,
            CEGUI::Event::Subscriber(&MenuModeLoad::updateDescription, this)
        )
    );
    addEventConnection(
        window->getChild("LevelWindowFrame/SaveGameSelect")->subscribeEvent(
            CEGUI::Listbox::EventMouseDoubleClick,
            CEGUI::Event::Subscriber(&MenuModeLoad::launchSelectedButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild("LevelWindowFrame")->subscribeEvent(
            CEGUI::FrameWindow::EventCloseClicked,
            CEGUI::Event::Subscriber(&MenuModeLoad::closeBrowser, this)
        )
    );
}

MenuModeLoad::~MenuModeLoad()
{
    if(isOpenInGame())
        closeBrowser();
}

bool MenuModeLoad::closeBrowser(const CEGUI::EventArgs&)
{
    if(!mInGame)
        return goBack();
    mOpen = false;
    ODFrameListener::getSingleton().getClientGameMap()->setGamePaused(mWasPaused);
    getModeManager().getGui().loadGuiSheet(Gui::inGameMenu);
    getModeManager().getCurrentMode()->giveFocus();
    return true;
}

//! \brief Closes the in-game browser on Escape and otherwise uses menu input.
bool MenuModeLoad::keyPressed(const OIS::KeyEvent& arg)
{
    if(mInGame && arg.key == OIS::KC_ESCAPE)
        return closeBrowser();
    return AbstractApplicationMode::keyPressed(arg);
}

//! \brief Opens the save browser with current campaign eligibility available to its file list.
void MenuModeLoad::activate()
{
    MapHandler::loadCampaignProgress();
    // Loads the corresponding Gui sheet.
    getModeManager().getGui().loadGuiSheet(Gui::guiSheet::loadSavedGameMenu);

    GameMap* gameMap = ODFrameListener::getSingleton().getClientGameMap();
    CEGUI::Window* sheet = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu);
    sheet->getChild("WelcomeBanner")->hide();
    sheet->getChild("VersionText")->setVisible(!mInGame);
    sheet->getChild("LevelWindowFrame")->setLookNFeel(
        mInGame ? "OD/GameSettingsWindow" : "OD/MenuPageWindow");
    sheet->getChild("LoadingText")->setAlwaysOnTop(true);
    sheet->getChild("LoadingText")->moveToFront();
    if(mInGame)
    {
        if(!mOpen)
            mWasPaused = gameMap->getGamePaused();
        mOpen = true;
        gameMap->setGamePaused(true);
        giveFocus();
    }
    else
    {
        giveFocus();
        MusicPlayer::getSingleton().play(ConfigManager::getSingleton().getMainMenuMusic());
        gameMap->clearAll();
        gameMap->setGamePaused(true);
        if(!mSavedGame.empty())
        {
            ODFrameListener::getSingleton().stopGameRenderer();
            ODFrameListener::getSingleton().createMainMenuScene();
        }
    }

    CEGUI::Combobox* filter = static_cast<CEGUI::Combobox*>(sheet->getChild("LevelWindowFrame/KindFilter"));
    size_t newestKind = static_cast<size_t>(openingLoadKind(collectLoadEntries()));
    filter->setItemSelectState(newestKind, true);
    filter->setText(filter->getListboxItemFromIndex(newestKind)->getText());
    updateFilesList();
    if(!mSavedGame.empty())
    {
        const std::string filename = mSavedGame;
        mSavedGame.clear();
        if(boost::filesystem::path(filename).extension().string() == ".odr")
        {
            if(!ODClient::getSingleton().replay(filename))
            {
                sheet->getChild("LoadingText")->setText("Error: Couldn't launch replay!");
                sheet->getChild("LoadingText")->show();
            }
        }
        else
            launchSavedGame(filename);
    }

}

//! \brief Shows only the selected kind, ordered by modification time, newest first.
bool MenuModeLoad::updateFilesList(const CEGUI::EventArgs&)
{
    CEGUI::Window* sheet = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu);
    CEGUI::Combobox* filter = static_cast<CEGUI::Combobox*>(sheet->getChild("LevelWindowFrame/KindFilter"));
    if(!filter->getSelectedItem())
        return true;
    size_t kind = filter->getItemIndex(filter->getSelectedItem());
    CEGUI::Listbox* list = static_cast<CEGUI::Listbox*>(sheet->getChild("LevelWindowFrame/SaveGameSelect"));
    list->resetList();
    mFilesList.clear();
    sheet->getChild("LevelWindowFrame/MapDescriptionText")->setText("");
    sheet->getChild("LoadingText")->hide();
    for(const LoadEntry& entry : visibleLoadEntries(collectLoadEntries(), static_cast<int>(kind)))
        mFilesList.push_back(entry.mPath);
    for(size_t i = 0; i < mFilesList.size(); ++i)
    {
        CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(boost::filesystem::path(mFilesList[i]).filename().string());
        item->setID(static_cast<uint32_t>(i));
        item->setSelectionBrushImage("OpenDungeonsSkin/SelectionBrush");
        list->addItem(item);
    }
    return true;
}

//! \brief Starts the selected saved game or replay.
bool MenuModeLoad::launchSelectedButtonPressed(const CEGUI::EventArgs&)
{
    CEGUI::Window* tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LevelWindowFrame/SaveGameSelect");
    CEGUI::Listbox* levelSelectList = static_cast<CEGUI::Listbox*>(tmpWin);

    if(levelSelectList->getSelectedCount() == 0)
    {
        tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LoadingText");
        tmpWin->setText("Please select a saved game first.");
        tmpWin->show();
        return true;
    }

    const uint32_t id = levelSelectList->getFirstSelectedItem()->getID();
    if(id >= mFilesList.size())
        return true;
    const std::string level = mFilesList[id];
    CEGUI::Combobox* filter = static_cast<CEGUI::Combobox*>(getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LevelWindowFrame/KindFilter"));
    if(loadConfirmAction(static_cast<int>(filter->getItemIndex(filter->getSelectedItem())), true) == 2)
    {
        std::string description;
        std::string error;
        CEGUI::Window* loading = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LoadingText");
        if(!MenuModeReplay::checkReplayValid(level, description, error))
        {
            loading->setText("Error: Couldn't launch replay!");
            loading->show();
            return true;
        }
        if(mInGame)
        {
            getModeManager().requestSavedGame(level);
            return true;
        }
        if(!ODClient::getSingleton().replay(level))
        {
            loading->setText("Error: Couldn't launch replay!");
            loading->show();
        }
        return true;
    }
    if(mInGame)
    {
        getModeManager().requestSavedGame(level);
        return true;
    }
    return launchSavedGame(level);
}

//! \brief Starts the server with a saved game and shows the exact cause in the menu if loading fails.
bool MenuModeLoad::launchSavedGame(const std::string& level)
{
    std::string nickname = ConfigManager::getSingleton().getGameValue(Config::NICKNAME, std::string(), false);
    if(!nickname.empty())
        ODFrameListener::getSingleton().getClientGameMap()->setLocalPlayerNick(nickname);
    CEGUI::Window* tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LoadingText");
    tmpWin->setText("Loading...");
    tmpWin->show();

    // In single player mode, we act as a server
    if(!ODServer::getSingleton().startServer(nickname, level, ServerMode::ModeGameLoaded, false))
    {
        OD_LOG_ERR("Could not start server for single player game !!!");
        tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LoadingText");
        const std::string& cause = MapHandler::getLastLoadError();
        tmpWin->setText(cause.empty() ? std::string("ERROR: Could not start the saved game. See the log for details.")
                                      : "ERROR: This saved game can't be loaded. " + cause);
        tmpWin->show();
        return true;
    }

    int port = ODServer::getSingleton().getNetworkPort();
    uint32_t timeout = ConfigManager::getSingleton().getClientConnectionTimeout();
    std::string replayFilename = ResourceManager::getSingleton().getReplayDataPath()
        + ResourceManager::getSingleton().buildReplayFilename();
    if(!ODClient::getSingleton().connect("localhost", port, timeout, replayFilename))
    {
        ODServer::getSingleton().stopServer();
        OD_LOG_ERR("Could not connect to server for single player game !!!");
        tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LoadingText");
        tmpWin->setText("Error: Couldn't connect to local server!");
        tmpWin->show();
        return true;
    }
    return true;
}

//! \brief Deletes the selected file while retaining the current filter.
bool MenuModeLoad::deleteSelectedButtonPressed(const CEGUI::EventArgs&)
{
    CEGUI::Window* tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LevelWindowFrame/SaveGameSelect");
    CEGUI::Listbox* selectList = static_cast<CEGUI::Listbox*>(tmpWin);

    if(selectList->getSelectedCount() == 0)
    {
        tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LoadingText");
        tmpWin->setText("Please select a saved game first.");
        tmpWin->show();
        return true;
    }

    CEGUI::ListboxItem* selItem = selectList->getFirstSelectedItem();
    int id = selItem->getID();

    const std::string& levelFile = mFilesList[id];
    if(!boost::filesystem::remove(levelFile))
    {
        OD_LOG_ERR("Could not delete saved game !!!");
        tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LoadingText");
        tmpWin->setText("Error: Couldn't delete saved game!");
        tmpWin->show();
        return true;
    }

    updateFilesList();
    return true;
}

//! \brief Shows the selected save or replay description.
bool MenuModeLoad::updateDescription(const CEGUI::EventArgs&)
{
    // Get the level corresponding id
    CEGUI::Window* tmpWin = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LevelWindowFrame/SaveGameSelect");
    CEGUI::Listbox* levelSelectList = static_cast<CEGUI::Listbox*>(tmpWin);

    CEGUI::Window* descTxt = getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LevelWindowFrame/MapDescriptionText");

    if(levelSelectList->getSelectedCount() == 0)
    {
        descTxt->setText("");
        return true;
    }

    getModeManager().getGui().playButtonClickSound();

    CEGUI::ListboxItem* selItem = levelSelectList->getFirstSelectedItem();
    int id = selItem->getID();

    std::string filename = mFilesList[id];

    CEGUI::Combobox* filter = static_cast<CEGUI::Combobox*>(getModeManager().getGui().getGuiSheet(Gui::loadSavedGameMenu)->getChild("LevelWindowFrame/KindFilter"));
    if(filter->getItemIndex(filter->getSelectedItem()) == 3)
    {
        std::string description;
        std::string error;
        bool valid = MenuModeReplay::checkReplayValid(filename, description, error);
        descTxt->setText(reinterpret_cast<const CEGUI::utf8*>((valid ? description : error).c_str()));
        return true;
    }
    LevelInfo levelInfo;
    std::string mapDescription;
    if(MapHandler::getMapInfo(filename, levelInfo))
        mapDescription = levelInfo.mLevelDescription;
    else
        mapDescription = "invalid map";

    descTxt->setText(mapDescription);
    static_cast<CEGUI::Scrollbar*>(descTxt->getChild("__auto_vscrollbar__"))->setScrollPosition(0);

    return true;
}
