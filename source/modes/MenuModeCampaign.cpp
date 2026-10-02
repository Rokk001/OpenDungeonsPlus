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

#include "modes/MenuModeCampaign.h"

#include "ai/KeeperAIType.h"
#include "game/Campaign.h"
#include "gamemap/GameMap.h"
#include "modes/ModeManager.h"
#include "network/ODClient.h"
#include "network/ODServer.h"
#include "network/ServerMode.h"
#include "render/Gui.h"
#include "render/ODFrameListener.h"
#include "sound/MusicPlayer.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/ResourceManager.h"

#include <CEGUI/CEGUI.h>
#include "boost/filesystem.hpp"

#include <cctype>
#include <fstream>

namespace
{
const std::string CAMPAIGN_DEFINITION_FILE = "levels/campaign/Campaign.cfg";
const std::string CAMPAIGN_PROGRESS_FILE = "campaign.progress";

const std::string CMP_FRAME = "CampaignWindowFrame";
const std::string CMP_TEXT_LOADING = "LoadingText";
const std::string CMP_BUTTON_LAUNCH = "CampaignWindowFrame/LaunchGameButton";
const std::string CMP_BUTTON_DIFFICULTY = "CampaignWindowFrame/DifficultyButton";
const std::string CMP_BUTTON_BACK = "CampaignWindowFrame/BackButton";
const std::string CMP_LIST_LEVELS = "CampaignWindowFrame/LevelSelect";
const std::string CMP_TEXT_DESCRIPTION = "CampaignWindowFrame/DescriptionText";
} // namespace

MenuModeCampaign::MenuModeCampaign(ModeManager* modeManager):
    AbstractApplicationMode(modeManager, ModeManager::MENU_CAMPAIGN),
    mResultLevel(0)
{
    CEGUI::Window* window = modeManager->getGui().getGuiSheet(Gui::guiSheet::campaignMenu);

    addEventConnection(
        window->getChild(CMP_BUTTON_LAUNCH)->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeCampaign::launchSelectedButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild(CMP_LIST_LEVELS)->subscribeEvent(
            CEGUI::Listbox::EventMouseDoubleClick,
            CEGUI::Event::Subscriber(&MenuModeCampaign::launchSelectedButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild(CMP_LIST_LEVELS)->subscribeEvent(
            CEGUI::Listbox::EventMouseClick,
            CEGUI::Event::Subscriber(&MenuModeCampaign::updateDescription, this)
        )
    );
    addEventConnection(
        window->getChild(CMP_BUTTON_DIFFICULTY)->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeCampaign::difficultyButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild(CMP_BUTTON_BACK)->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeCampaign::backButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild(CMP_FRAME)->subscribeEvent(
            CEGUI::FrameWindow::EventCloseClicked,
            CEGUI::Event::Subscriber(&MenuModeCampaign::backButtonPressed, this)
        )
    );
}

bool MenuModeCampaign::loadCampaign()
{
    ResourceManager& resources = ResourceManager::getSingleton();
    Campaign& campaign = Campaign::getSingleton();

    std::ifstream definition((resources.getGameDataPath() + CAMPAIGN_DEFINITION_FILE).c_str());
    if(!definition.is_open() || !campaign.importDefinition(definition))
    {
        OD_LOG_ERR("Could not read the campaign definition " + CAMPAIGN_DEFINITION_FILE);
        return false;
    }

    std::string progressPath = resources.getUserDataPath() + CAMPAIGN_PROGRESS_FILE;
    campaign.setProgressPath(progressPath);
    std::ifstream progress(progressPath.c_str());
    if(progress.is_open())
        campaign.importProgress(progress);

    return true;
}

void MenuModeCampaign::activate()
{
    // Loads the corresponding Gui sheet.
    getModeManager().getGui().loadGuiSheet(Gui::guiSheet::campaignMenu);

    giveFocus();

    // Play the main menu music
    MusicPlayer::getSingleton().play(ConfigManager::getSingleton().getMainMenuMusic());

    // We may come from a finished game: show the menu scene and clean the map
    GameMap* gameMap = ODFrameListener::getSingleton().getClientGameMap();
    gameMap->clearAll();
    gameMap->setGamePaused(true);
    ODFrameListener::getSingleton().stopGameRenderer();
    ODFrameListener::getSingleton().createMainMenuScene();

    Campaign& campaign = Campaign::getSingleton();
    CEGUI::Window* window = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    window->getChild(CMP_TEXT_LOADING)->setText("");

    // Debriefing of the level that was played last
    mResultText.clear();
    size_t playedLevel = campaign.getPlayedLevel();
    size_t selected = campaign.getCurrentLevel();
    if(playedLevel < campaign.getNumLevels())
    {
        const CampaignLevel& level = campaign.getLevel(playedLevel);
        selected = playedLevel;
        if(campaign.getPlayedLevelWon())
        {
            mResultText = "Debriefing - " + level.mTitle + "\n\n" + level.mDebriefing + "\n\n";
            if(level.mBonus)
            {
                mResultText += "You have cleared the hidden land.";
                selected = campaign.getCurrentLevel();
            }
            else if(campaign.isFinished())
                mResultText += "You have completed the campaign.";
            else
            {
                mResultText += "The next level is unlocked.";
                selected = campaign.getCurrentLevel();
            }
        }
        else
        {
            mResultText = "You did not complete this level. You can try again.";
        }
        campaign.clearPlayedLevel();
    }

    if(campaign.getNumLevels() == 0)
        return;

    if(selected >= campaign.getNumLevels())
        selected = campaign.getNumLevels() - 1;

    // The debriefing is shown together with the briefing of the selected level
    mResultLevel = selected;

    fillLevelList();
    selectLevel(selected);
    updateDifficultyButton();
}

void MenuModeCampaign::updateDifficultyButton()
{
    Campaign& campaign = Campaign::getSingleton();
    CEGUI::Window* window = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Window* button = window->getChild(CMP_BUTTON_DIFFICULTY);
    KeeperAIType type = static_cast<KeeperAIType>(campaign.getDifficulty());
    std::string name = KeeperAITypes::toString(type);
    name[0] = static_cast<char>(std::toupper(static_cast<unsigned char>(name[0])));
    button->setText("Difficulty: " + name);
    // The difficulty is chosen when a new campaign is begun and then stays
    button->setEnabled(!campaign.hasProgress());
}

bool MenuModeCampaign::difficultyButtonPressed(const CEGUI::EventArgs&)
{
    Campaign& campaign = Campaign::getSingleton();
    if(campaign.hasProgress())
        return true;

    uint32_t next = (campaign.getDifficulty() + 1) % static_cast<uint32_t>(KeeperAIType::nbAI);
    campaign.setDifficulty(next);
    updateDifficultyButton();
    return true;
}

void MenuModeCampaign::fillLevelList()
{
    Campaign& campaign = Campaign::getSingleton();
    CEGUI::Window* window = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Listbox* levelList = static_cast<CEGUI::Listbox*>(window->getChild(CMP_LIST_LEVELS));
    levelList->resetList();

    for(size_t i = 0; i < campaign.getNumLevels(); ++i)
    {
        const CampaignLevel& level = campaign.getLevel(i);
        std::string text = Helper::toString(static_cast<int>(i + 1)) + ". ";
        if(level.mBonus && !campaign.isUnlocked(i))
            text += "(secret level)";
        else
            text += level.mTitle + (level.mBonus ? " (bonus)" : "");
        if(campaign.isCompleted(i))
            text += " (completed)";
        else if(!campaign.isUnlocked(i) && !level.mBonus)
            text += " (locked)";

        CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(text);
        item->setID(static_cast<CEGUI::uint>(i));
        item->setSelectionBrushImage("OpenDungeonsSkin/SelectionBrush");
        levelList->addItem(item);
    }
}

void MenuModeCampaign::selectLevel(size_t index)
{
    CEGUI::Window* window = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Listbox* levelList = static_cast<CEGUI::Listbox*>(window->getChild(CMP_LIST_LEVELS));
    levelList->clearAllSelections();
    CEGUI::ListboxItem* item = levelList->getListboxItemFromIndex(index);
    if(item != nullptr)
        levelList->setItemSelectState(item, true);

    updateDescription();
}

bool MenuModeCampaign::launchSelectedButtonPressed(const CEGUI::EventArgs&)
{
    Campaign& campaign = Campaign::getSingleton();
    CEGUI::Window* mainWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Listbox* levelList = static_cast<CEGUI::Listbox*>(mainWin->getChild(CMP_LIST_LEVELS));
    CEGUI::Window* statusText = mainWin->getChild(CMP_TEXT_LOADING);

    if(levelList->getSelectedCount() == 0)
    {
        statusText->setText("Please select a level first.");
        return true;
    }

    size_t index = static_cast<size_t>(levelList->getFirstSelectedItem()->getID());
    if(!campaign.isUnlocked(index))
    {
        statusText->setText("This level is locked. Complete the previous levels first.");
        return true;
    }

    std::string level = ResourceManager::getSingleton().getGameDataPath() + "levels/"
        + campaign.getLevel(index).mFile;
    if(!boost::filesystem::exists(boost::filesystem::path(level)))
    {
        OD_LOG_ERR("Campaign level not found: " + level);
        statusText->setText("ERROR: Campaign level file not found.");
        return true;
    }

    statusText->setText("Loading...");

    // In single player mode, we act as a server
    campaign.startLevel(index);
    const std::string& nickname = ODFrameListener::getSingleton().getClientGameMap()->getLocalPlayerNick();
    if(!ODServer::getSingleton().startServer(nickname, level, ServerMode::ModeGameSinglePlayer, false))
    {
        OD_LOG_ERR("Could not start server for campaign game !!!");
        statusText->setText("ERROR: Could not start server for campaign game !!!");
        campaign.stopCampaign();
        return true;
    }

    int port = ODServer::getSingleton().getNetworkPort();
    uint32_t timeout = ConfigManager::getSingleton().getClientConnectionTimeout();
    std::string replayFilename = ResourceManager::getSingleton().getReplayDataPath()
        + ResourceManager::getSingleton().buildReplayFilename();
    if(!ODClient::getSingleton().connect("localhost", port, timeout, replayFilename))
    {
        OD_LOG_ERR("Could not connect to server for campaign game !!!");
        statusText->setText("Error: Couldn't connect to local server!");
        campaign.stopCampaign();
        return true;
    }
    return true;
}

bool MenuModeCampaign::backButtonPressed(const CEGUI::EventArgs&)
{
    Campaign::getSingleton().stopCampaign();
    getModeManager().requestMode(AbstractModeManager::MENU_MAIN);
    return true;
}

bool MenuModeCampaign::updateDescription(const CEGUI::EventArgs&)
{
    Campaign& campaign = Campaign::getSingleton();
    CEGUI::Window* mainWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Listbox* levelList = static_cast<CEGUI::Listbox*>(mainWin->getChild(CMP_LIST_LEVELS));
    CEGUI::Window* descTxt = mainWin->getChild(CMP_TEXT_DESCRIPTION);

    if(levelList->getSelectedCount() == 0)
    {
        descTxt->setText("");
        return true;
    }

    size_t index = static_cast<size_t>(levelList->getFirstSelectedItem()->getID());
    const CampaignLevel& level = campaign.getLevel(index);

    std::string description;
    if(!mResultText.empty() && (index == mResultLevel))
        description = mResultText + "\n\n";

    if(level.mBonus && !campaign.isUnlocked(index))
        description += "This level is still hidden. Find it in the campaign levels.";
    else
        description += "Briefing - " + level.mTitle + "\n\n" + level.mBriefing;

    size_t talismanTotal = campaign.getTalismanTotal();
    if(talismanTotal > 0)
    {
        description += "\n\nTalisman: " + Helper::toString(static_cast<int>(campaign.getTalismanPieces()))
            + " of " + Helper::toString(static_cast<int>(talismanTotal)) + " pieces found.";
    }
    descTxt->setText(reinterpret_cast<const CEGUI::utf8*>(description.c_str()));
    return true;
}
