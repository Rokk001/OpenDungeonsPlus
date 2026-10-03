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
const std::string CMP_BUTTON_DIFFICULTY = "CampaignWindowFrame/DifficultyButton";
const std::string CMP_CHECK_RELATIONSHIPS = "CampaignWindowFrame/RelationshipsCheckbox";
const std::string CMP_BUTTON_BACK = "CampaignWindowFrame/BackButton";
const std::string CMP_MAP = "CampaignWindowFrame/CampaignMap";
const std::string CMP_TEXT_DESCRIPTION = "CampaignWindowFrame/DescriptionText";

// Territory tints on the campaign map (ARGB). They are multiplied with a white
// image and are translucent, so the map image stays visible below them
const std::string COLOUR_LOCKED = "A0100C08";
const std::string COLOUR_AVAILABLE = "A0B07A2A";
const std::string COLOUR_COMPLETED = "A038603C";
const std::string COLOUR_HOVER = "D8F0B848";
} // namespace

MenuModeCampaign::MenuModeCampaign(ModeManager* modeManager):
    AbstractApplicationMode(modeManager, ModeManager::MENU_CAMPAIGN),
    mHoveredLevel(0)
{
    CEGUI::Window* window = modeManager->getGui().getGuiSheet(Gui::guiSheet::campaignMenu);

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
    if(playedLevel < campaign.getNumLevels())
    {
        const CampaignLevel& level = campaign.getLevel(playedLevel);
        if(campaign.getPlayedLevelWon())
        {
            mResultText = "Debriefing - " + level.mTitle + "\n\n" + level.mDebriefing + "\n\n";
            if(level.mBonus)
            {
                mResultText += "You have cleared the hidden land.";
            }
            else if(campaign.isFinished())
                mResultText += "You have completed the campaign.";
            else
                mResultText += "The next level is unlocked.";

            // The numbers of the level, as sent by the server when it was won
            std::string summary = campaign.getLevelSummary();
            if(!summary.empty())
                mResultText += "\n\n" + summary;
        }
        else
        {
            mResultText = "You did not complete this level. You can try again.";
        }
        campaign.clearPlayedLevel();
    }

    mHoveredLevel = campaign.getNumLevels();
    clearMap();
    if(campaign.getNumLevels() == 0)
        return;

    fillMap();
    showDescription(campaign.getNumLevels());
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

void MenuModeCampaign::clearMap()
{
    CEGUI::WindowManager& windowManager = CEGUI::WindowManager::getSingleton();
    for(std::vector<CEGUI::Window*>::iterator it = mTerritoryWindows.begin(); it != mTerritoryWindows.end(); ++it)
        windowManager.destroyWindow(*it);
    mTerritoryWindows.clear();
}

void MenuModeCampaign::fillMap()
{
    Campaign& campaign = Campaign::getSingleton();
    CEGUI::WindowManager& windowManager = CEGUI::WindowManager::getSingleton();
    CEGUI::Window* window = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Window* map = window->getChild(CMP_MAP);

    for(size_t i = 0; i < campaign.getNumLevels(); ++i)
    {
        const CampaignLevel& level = campaign.getLevel(i);
        // A bonus level stays hidden until it is found
        if(level.mBonus && !campaign.isUnlocked(i))
            continue;

        bool startable = campaign.isUnlocked(i);
        std::vector<CampaignMapBlock> blocks = campaign.getMapBlocks(i);
        for(size_t j = 0; j < blocks.size(); ++j)
        {
            const CampaignMapBlock& block = blocks[j];
            std::string name = "Territory_" + Helper::toString(static_cast<int>(i)) + "_"
                + Helper::toString(static_cast<int>(j));
            CEGUI::Window* territory = windowManager.createWindow("OD/StaticImage", name);
            territory->setProperty("FrameEnabled", "True");
            territory->setProperty("BackgroundEnabled", "False");
            territory->setProperty("Image", "OpenDungeonsIcons/CampaignSolid");
            // The area is position and size, the block holds the size and not the far corner
            territory->setArea(CEGUI::UDim(block.mX / 100.0f, 0), CEGUI::UDim(block.mY / 100.0f, 0),
                CEGUI::UDim(block.mWidth / 100.0f, 0), CEGUI::UDim(block.mHeight / 100.0f, 0));
            territory->setID(static_cast<CEGUI::uint>(i));
            if(j == 0)
            {
                // A static image cannot show text: the title is a child that lets the mouse through
                CEGUI::Window* label = windowManager.createWindow("OD/StaticText", name + "_Label");
                label->setProperty("FrameEnabled", "False");
                label->setProperty("BackgroundEnabled", "False");
                label->setProperty("HorzFormatting", "WordWrapCentred");
                label->setProperty("VertFormatting", "CentreAligned");
                label->setProperty("Font", "MedievalSharp-12");
                label->setArea(CEGUI::UDim(0, 0), CEGUI::UDim(0, 0), CEGUI::UDim(1, 0), CEGUI::UDim(1, 0));
                label->setMousePassThroughEnabled(true);
                label->setText(reinterpret_cast<const CEGUI::utf8*>(level.mTitle.c_str()));
                territory->addChild(label);
            }

            // Levels that cannot be started do not react to the mouse
            if(startable)
            {
                addEventConnection(
                    territory->subscribeEvent(
                        CEGUI::Window::EventMouseEntersArea,
                        CEGUI::Event::Subscriber(&MenuModeCampaign::territoryEntered, this)
                    )
                );
                addEventConnection(
                    territory->subscribeEvent(
                        CEGUI::Window::EventMouseLeavesArea,
                        CEGUI::Event::Subscriber(&MenuModeCampaign::territoryLeft, this)
                    )
                );
                addEventConnection(
                    territory->subscribeEvent(
                        CEGUI::Window::EventMouseClick,
                        CEGUI::Event::Subscriber(&MenuModeCampaign::territoryClicked, this)
                    )
                );
            }
            else
            {
                territory->setMousePassThroughEnabled(true);
            }

            map->addChild(territory);
            mTerritoryWindows.push_back(territory);
            updateTerritoryColour(territory);
        }
    }
}

void MenuModeCampaign::updateTerritoryColour(CEGUI::Window* block)
{
    Campaign& campaign = Campaign::getSingleton();
    size_t index = static_cast<size_t>(block->getID());
    const std::string* colour = &COLOUR_AVAILABLE;
    if(!campaign.isUnlocked(index))
        colour = &COLOUR_LOCKED;
    else if(index == mHoveredLevel)
        colour = &COLOUR_HOVER;
    else if(campaign.isCompleted(index))
        colour = &COLOUR_COMPLETED;
    block->setProperty("ImageColours", *colour);
}

bool MenuModeCampaign::territoryEntered(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    mHoveredLevel = static_cast<size_t>(args.window->getID());
    for(std::vector<CEGUI::Window*>::iterator it = mTerritoryWindows.begin(); it != mTerritoryWindows.end(); ++it)
        updateTerritoryColour(*it);
    showDescription(mHoveredLevel);
    return true;
}

bool MenuModeCampaign::territoryLeft(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    if(mHoveredLevel != static_cast<size_t>(args.window->getID()))
        return true;

    mHoveredLevel = Campaign::getSingleton().getNumLevels();
    for(std::vector<CEGUI::Window*>::iterator it = mTerritoryWindows.begin(); it != mTerritoryWindows.end(); ++it)
        updateTerritoryColour(*it);
    showDescription(mHoveredLevel);
    return true;
}

bool MenuModeCampaign::territoryClicked(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    startLevel(static_cast<size_t>(args.window->getID()));
    return true;
}

void MenuModeCampaign::startLevel(size_t index)
{
    Campaign& campaign = Campaign::getSingleton();
    CEGUI::Window* mainWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Window* statusText = mainWin->getChild(CMP_TEXT_LOADING);

    if(!campaign.isUnlocked(index))
    {
        statusText->setText("This level is locked. Complete the previous levels first.");
        return;
    }

    std::string level = ResourceManager::getSingleton().getGameDataPath() + "levels/"
        + campaign.getLevel(index).mFile;
    if(!boost::filesystem::exists(boost::filesystem::path(level)))
    {
        OD_LOG_ERR("Campaign level not found: " + level);
        statusText->setText("ERROR: Campaign level file not found.");
        return;
    }

    statusText->setText("Loading...");

    // In single player mode, we act as a server
    campaign.startLevel(index);
    const std::string& nickname = ODFrameListener::getSingleton().getClientGameMap()->getLocalPlayerNick();
    CEGUI::ToggleButton* relationshipsCheckbox = static_cast<CEGUI::ToggleButton*>(
        mainWin->getChild(CMP_CHECK_RELATIONSHIPS));
    if(!ODServer::getSingleton().startServer(nickname, level, ServerMode::ModeGameSinglePlayer, false,
        relationshipsCheckbox->isSelected()))
    {
        OD_LOG_ERR("Could not start server for campaign game !!!");
        statusText->setText("ERROR: Could not start server for campaign game !!!");
        campaign.stopCampaign();
        return;
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
        return;
    }
}

bool MenuModeCampaign::backButtonPressed(const CEGUI::EventArgs&)
{
    Campaign::getSingleton().stopCampaign();
    getModeManager().requestMode(AbstractModeManager::MENU_MAIN);
    return true;
}

void MenuModeCampaign::showDescription(size_t index)
{
    Campaign& campaign = Campaign::getSingleton();
    CEGUI::Window* mainWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::campaignMenu);
    CEGUI::Window* descTxt = mainWin->getChild(CMP_TEXT_DESCRIPTION);

    std::string description;
    if(index < campaign.getNumLevels())
    {
        const CampaignLevel& level = campaign.getLevel(index);
        description = "Briefing - " + level.mTitle + "\n\n" + level.mBriefing;
    }
    else
    {
        // Nothing under the mouse: the debriefing of the level played last
        if(!mResultText.empty())
            description = mResultText;
        else
            description = "Move the mouse over a land and click it to start the level.";
    }

    size_t talismanTotal = campaign.getTalismanTotal();
    if(talismanTotal > 0)
    {
        description += "\n\nTalisman: " + Helper::toString(static_cast<int>(campaign.getTalismanPieces()))
            + " of " + Helper::toString(static_cast<int>(talismanTotal)) + " pieces found.";
    }
    descTxt->setText(reinterpret_cast<const CEGUI::utf8*>(description.c_str()));
}
