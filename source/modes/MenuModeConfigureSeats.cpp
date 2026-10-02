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

#include "gamemap/GameMap.h"

#include "ai/KeeperAIType.h"
#include "entities/CreatureDefinition.h"
#include "game/Seat.h"
#include "game/SkillType.h"
#include "modes/MenuModeConfigureSeats.h"
#include "modes/ModeManager.h"
#include "network/ChatEventMessage.h"
#include "network/ODServer.h"
#include "network/ODClient.h"
#include "render/Gui.h"
#include "render/ODFrameListener.h"
#include "sound/MusicPlayer.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/Helper.h"

#include <CEGUI/CEGUI.h>

#include <boost/filesystem.hpp>

const std::string TEXT_SEAT_ID_PREFIX = "TextSeat";
const std::string COMBOBOX_TEAM_ID_PREFIX = "ComboTeam";
const std::string COMBOBOX_PLAYER_FACTION_PREFIX = "ComboPlayerFactionSeat";
const std::string COMBOBOX_PLAYER_PREFIX = "ComboPlayerSeat";
const std::string COMBOBOX_GOLD_DENSITY = "ComboGoldDensity";
const std::string COMBOBOX_MANA_REGENERATION = "ComboManaRegeneration";
const std::string COMBOBOX_HEART_DESTROYED = "ComboHeartDestroyed";
const std::string COMBOBOX_FOG_OF_WAR = "ComboFogOfWar";
const std::string SPINNER_MAX_CREATURES = "SpinMaxCreatures";
const std::string SPINNER_GAME_SPEED = "SpinGameSpeed";
const std::string SPINNER_GAME_DURATION = "SpinGameDuration";

namespace
{
const std::string SETTINGS_WINDOW = "GameSettingsWindow";
const std::string SETTINGS_TABS = "SettingsTabs";

//! \brief Height of one line on the creature, room, spell, trap and door pages, in layout pixels
const float SETTING_LINE_HEIGHT = 34.0f;

//! \brief The text on the button of a room, spell, trap or door
std::string itemStateText(uint32_t state)
{
    switch(static_cast<GameMap::SkirmishItemState>(state))
    {
        case GameMap::SkirmishItemState::notAvailable:
            return "Not available";
        case GameMap::SkirmishItemState::availableAtStart:
            return "Available at start";
        default:
            return "Needs research";
    }
}

//! \brief The name of the page where the skill is shown or an empty string if it has none
std::string itemPageName(SkillType type)
{
    const std::string name = Skills::toString(type);
    if(name.compare(0, 4, "room") == 0)
        return "Rooms";
    if(name.compare(0, 5, "spell") == 0)
        return "Spells";
    if(name.compare(0, 8, "trapDoor") == 0)
        return "Doors";
    if(name.compare(0, 4, "trap") == 0)
        return "Traps";

    return "";
}

uint32_t getSpinnerValue(CEGUI::Window* page, const std::string& spinnerName)
{
    return static_cast<uint32_t>(static_cast<CEGUI::Spinner*>(page->getChild(spinnerName))->getCurrentValue());
}

CEGUI::Window* getSettingsWindow(CEGUI::Window* sheet)
{
    return sheet->getChild(SETTINGS_WINDOW);
}

//! \brief The page "General" of the Game settings window
CEGUI::Window* getGeneralPage(CEGUI::Window* sheet)
{
    return getSettingsWindow(sheet)->getChild(SETTINGS_TABS + "/General");
}

void addSettingItem(CEGUI::Combobox* combo, const std::string& text, uint32_t value)
{
    const CEGUI::Image* selImg = &CEGUI::ImageManager::getSingleton().get("OpenDungeonsSkin/SelectionBrush");
    CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(text, value);
    item->setSelectionBrushImage(selImg);
    combo->addItem(item);
}

//! \brief Returns the id of the selected item or defaultValue if nothing is selected
uint32_t getSettingValue(CEGUI::Window* playersWin, const std::string& comboName, uint32_t defaultValue)
{
    CEGUI::Combobox* combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(comboName));
    CEGUI::ListboxItem* selItem = combo->getSelectedItem();
    if(selItem == nullptr)
        return defaultValue;

    return selItem->getID();
}

void selectSettingValue(CEGUI::Window* playersWin, const std::string& comboName, uint32_t value)
{
    CEGUI::Combobox* combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(comboName));
    CEGUI::ListboxItem* selItem = nullptr;
    for(uint32_t i = 0; i < combo->getItemCount(); ++i)
    {
        CEGUI::ListboxItem* item = combo->getListboxItemFromIndex(i);
        if(item->getID() == value)
            selItem = item;

        combo->setItemSelectState(item, false);
    }
    if(selItem != nullptr)
    {
        combo->setText(selItem->getText());
        combo->setItemSelectState(selItem, true);
    }
}
}

MenuModeConfigureSeats::MenuModeConfigureSeats(ModeManager* modeManager):
    AbstractApplicationMode(modeManager, ModeManager::MENU_CONFIGURE_SEATS),
    mIsActivePlayerConfig(false),
    mSettingsReceived(false),
    mIsRefreshing(false)
{
    CEGUI::Window* window = modeManager->getGui().getGuiSheet(Gui::guiSheet::configureSeats);
    addEventConnection(
        window->getChild("ListPlayers/LaunchGameButton")->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::launchSelectedButtonPressed, this)
        )
    );
    addEventConnection(
        window->getChild("ListPlayers/BackButton")->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::goBack, this)
        )
    );

    addEventConnection(
        window->getChild("ListPlayers")->subscribeEvent(
            CEGUI::FrameWindow::EventCloseClicked,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::goBack, this)
        )
    );

    addEventConnection(
        window->getChild("ListPlayers/GameSettingsButton")->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::openGameSettings, this)
        )
    );
    addEventConnection(
        getSettingsWindow(window)->getChild("CloseSettingsButton")->subscribeEvent(
            CEGUI::PushButton::EventClicked,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::closeGameSettings, this)
        )
    );
    addEventConnection(
        getSettingsWindow(window)->subscribeEvent(
            CEGUI::FrameWindow::EventCloseClicked,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::closeGameSettings, this)
        )
    );

    initSettingCombos();
    initSettingPages();

    addEventConnection(
        window->getChild("ListPlayers/GameChatEditBox")->subscribeEvent(
            CEGUI::Editbox::EventTextAccepted,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::chatText, this)
        )
    );
}

MenuModeConfigureSeats::~MenuModeConfigureSeats()
{
    CEGUI::Window* tmpWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
    for(int seatId : mSeatIds)
    {
        std::string name;
        name = TEXT_SEAT_ID_PREFIX + Helper::toString(seatId);
        tmpWin->destroyChild(name);
        name = COMBOBOX_PLAYER_FACTION_PREFIX + Helper::toString(seatId);
        tmpWin->destroyChild(name);
        name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seatId);
        tmpWin->destroyChild(name);
        name = COMBOBOX_TEAM_ID_PREFIX + Helper::toString(seatId);
        tmpWin->destroyChild(name);
    }
}

void MenuModeConfigureSeats::initSettingCombos()
{
    CEGUI::Window* generalPage = getGeneralPage(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats));
    uint32_t percents[] = {50, 100, 400};
    const std::string percentCombos[] = {COMBOBOX_GOLD_DENSITY, COMBOBOX_MANA_REGENERATION};
    for(const std::string& comboName : percentCombos)
    {
        CEGUI::Combobox* combo = static_cast<CEGUI::Combobox*>(generalPage->getChild(comboName));
        combo->resetList();
        combo->setReadOnly(true);
        combo->setEnabled(false);
        mHostSettingWindows.push_back(combo);
        for(uint32_t percent : percents)
            addSettingItem(combo, Helper::toString(percent) + "%", percent);

        selectSettingValue(generalPage, comboName, 100);
        addEventConnection(
            combo->subscribeEvent(CEGUI::Combobox::EventListSelectionAccepted,
                CEGUI::Event::Subscriber(&MenuModeConfigureSeats::comboChanged, this))
        );
    }

    // What the keeper that destroys a dungeon heart receives
    CEGUI::Combobox* combo = static_cast<CEGUI::Combobox*>(generalPage->getChild(COMBOBOX_HEART_DESTROYED));
    combo->resetList();
    combo->setReadOnly(true);
    combo->setEnabled(false);
    mHostSettingWindows.push_back(combo);
    addSettingItem(combo, "Gain mana", 0);
    addSettingItem(combo, "Gain mana and a special", 1);
    addSettingItem(combo, "Gain mana, rooms and land", 2);
    selectSettingValue(generalPage, COMBOBOX_HEART_DESTROYED, 0);
    addEventConnection(
        combo->subscribeEvent(CEGUI::Combobox::EventListSelectionAccepted,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::comboChanged, this))
    );

    combo = static_cast<CEGUI::Combobox*>(generalPage->getChild(COMBOBOX_FOG_OF_WAR));
    combo->resetList();
    combo->setReadOnly(true);
    combo->setEnabled(false);
    mHostSettingWindows.push_back(combo);
    addSettingItem(combo, "On", 1);
    addSettingItem(combo, "Off", 0);
    selectSettingValue(generalPage, COMBOBOX_FOG_OF_WAR, 1);
    addEventConnection(
        combo->subscribeEvent(CEGUI::Combobox::EventListSelectionAccepted,
            CEGUI::Event::Subscriber(&MenuModeConfigureSeats::comboChanged, this))
    );

    // The spinners: maximum number of creatures, game speed and game duration
    struct SpinnerSetting
    {
        const std::string* name;
        double minimum;
        double maximum;
        double step;
        double initial;
    };
    const double maxCreaturesAbsolute = ConfigManager::getSingleton().getMaxCreaturesPerSeatAbsolute();
    const double maxCreaturesDefault = ConfigManager::getSingleton().getMaxCreaturesPerSeatDefault();
    const SpinnerSetting spinners[] = {
        {&SPINNER_MAX_CREATURES, 1.0, maxCreaturesAbsolute, 1.0, maxCreaturesDefault},
        {&SPINNER_GAME_SPEED, 25.0, 400.0, 25.0, 100.0},
        {&SPINNER_GAME_DURATION, 0.0, 9999.0, 1.0, 0.0}
    };
    for(const SpinnerSetting& setting : spinners)
    {
        CEGUI::Spinner* spinner = static_cast<CEGUI::Spinner*>(generalPage->getChild(*setting.name));
        spinner->setTextInputMode(CEGUI::Spinner::Integer);
        spinner->setMinimumValue(setting.minimum);
        spinner->setMaximumValue(setting.maximum);
        spinner->setStepSize(setting.step);
        spinner->setCurrentValue(setting.initial);
        spinner->setEnabled(false);
        mHostSettingWindows.push_back(spinner);
        addEventConnection(
            spinner->subscribeEvent(CEGUI::Spinner::EventValueChanged,
                CEGUI::Event::Subscriber(&MenuModeConfigureSeats::settingChanged, this))
        );
    }
}

void MenuModeConfigureSeats::initSettingPages()
{
    CEGUI::WindowManager& winMgr = CEGUI::WindowManager::getSingleton();
    CEGUI::Window* settingsWin = getSettingsWindow(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats));

    // One line per fighter creature class, with the maximum number a keeper may have
    float lineY = 10.0f;
    for(const std::pair<const std::string, CreatureDefinition*>& def : ConfigManager::getSingleton().getCreatureDefinitions())
    {
        if(def.second->isWorker())
            continue;

        CEGUI::Window* pane = settingsWin->getChild(SETTINGS_TABS + "/Creatures/CreaturesSP");
        CEGUI::Window* label = winMgr.createWindow("OD/StaticText", "Label" + def.first);
        label->setArea(CEGUI::UDim(0, 16), CEGUI::UDim(0, lineY), CEGUI::UDim(0, 330), CEGUI::UDim(0, lineY + 28));
        label->setText(def.first);
        label->setProperty("FrameEnabled", "False");
        label->setProperty("BackgroundEnabled", "False");
        pane->addChild(label);

        CEGUI::Spinner* spinner = static_cast<CEGUI::Spinner*>(winMgr.createWindow("OD/Spinner", "Limit" + def.first));
        spinner->setArea(CEGUI::UDim(0, 350), CEGUI::UDim(0, lineY), CEGUI::UDim(0, 470), CEGUI::UDim(0, lineY + 28));
        spinner->setTooltipText("Most creatures of this type a keeper may have. 32 means no limit.");
        pane->addChild(spinner);
        spinner->setTextInputMode(CEGUI::Spinner::Integer);
        spinner->setMinimumValue(0.0);
        spinner->setMaximumValue(static_cast<double>(GameMap::SKIRMISH_CREATURE_LIMIT_NONE));
        spinner->setStepSize(1.0);
        spinner->setCurrentValue(static_cast<double>(GameMap::SKIRMISH_CREATURE_LIMIT_NONE));
        spinner->setEnabled(false);
        mHostSettingWindows.push_back(spinner);
        mLimitSpinners[def.first] = spinner;
        addEventConnection(
            spinner->subscribeEvent(CEGUI::Spinner::EventValueChanged,
                CEGUI::Event::Subscriber(&MenuModeConfigureSeats::settingChanged, this))
        );
        lineY += SETTING_LINE_HEIGHT;
    }

    // One line per room, spell, trap and door, with a button that cycles its availability
    mItemStates.assign(static_cast<uint32_t>(SkillType::countSkill),
        static_cast<uint32_t>(GameMap::SkirmishItemState::needsResearch));
    std::map<std::string, float> pageLineY;
    for(uint32_t i = 1; i < static_cast<uint32_t>(SkillType::countSkill); ++i)
    {
        SkillType skillType = static_cast<SkillType>(i);
        const std::string pageName = itemPageName(skillType);
        if(pageName.empty())
            continue;

        CEGUI::Window* pane = settingsWin->getChild(SETTINGS_TABS + "/" + pageName + "/" + pageName + "SP");
        std::map<std::string, float>::iterator itY = pageLineY.find(pageName);
        if(itY == pageLineY.end())
            itY = pageLineY.insert(std::pair<std::string, float>(pageName, 10.0f)).first;

        const float y = itY->second;
        CEGUI::Window* label = winMgr.createWindow("OD/StaticText", "ItemLabel" + Helper::toString(i));
        label->setArea(CEGUI::UDim(0, 16), CEGUI::UDim(0, y), CEGUI::UDim(0, 330), CEGUI::UDim(0, y + 28));
        label->setText(Skills::skillTypeToPlayerVisibleString(skillType));
        label->setProperty("FrameEnabled", "False");
        label->setProperty("BackgroundEnabled", "False");
        pane->addChild(label);

        CEGUI::Window* button = winMgr.createWindow("OD/Button", "ItemButton" + Helper::toString(i));
        button->setArea(CEGUI::UDim(0, 350), CEGUI::UDim(0, y), CEGUI::UDim(0, 540), CEGUI::UDim(0, y + 28));
        button->setText(itemStateText(mItemStates[i]));
        button->setID(i);
        button->setEnabled(false);
        pane->addChild(button);
        mHostSettingWindows.push_back(button);
        mItemButtons[i] = button;
        addEventConnection(
            button->subscribeEvent(CEGUI::PushButton::EventClicked,
                CEGUI::Event::Subscriber(&MenuModeConfigureSeats::itemStateClicked, this))
        );
        itY->second += SETTING_LINE_HEIGHT;
    }
}

bool MenuModeConfigureSeats::openGameSettings(const CEGUI::EventArgs&)
{
    CEGUI::Window* settingsWin = getSettingsWindow(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats));
    settingsWin->setVisible(true);
    settingsWin->moveToFront();
    return true;
}

bool MenuModeConfigureSeats::closeGameSettings(const CEGUI::EventArgs&)
{
    getSettingsWindow(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats))->setVisible(false);
    return true;
}

bool MenuModeConfigureSeats::settingChanged(const CEGUI::EventArgs&)
{
    if(!mIsRefreshing)
        fireSeatConfigurationToServer();

    return true;
}

bool MenuModeConfigureSeats::itemStateClicked(const CEGUI::EventArgs& ea)
{
    CEGUI::Window* button = static_cast<const CEGUI::WindowEventArgs&>(ea).window;
    const uint32_t skill = button->getID();
    if(skill >= mItemStates.size())
        return true;

    // Not available, available at start, needs research, then it starts again
    mItemStates[skill] = (mItemStates[skill] + 1) % (static_cast<uint32_t>(GameMap::SkirmishItemState::needsResearch) + 1);
    button->setText(itemStateText(mItemStates[skill]));
    fireSeatConfigurationToServer();
    return true;
}

void MenuModeConfigureSeats::activate()
{
    // Loads the corresponding Gui sheet.
    getModeManager().getGui().loadGuiSheet(Gui::guiSheet::configureSeats);

    giveFocus();

    // Play the main menu music
    MusicPlayer::getSingleton().play(ConfigManager::getSingleton().getMainMenuMusic());

    // We use the client game map to allow everybody to see how the server is configuring seats
    GameMap* gameMap = ODFrameListener::getSingleton().getClientGameMap();
    gameMap->setGamePaused(true);

    // The Game settings window is closed and only the host may change it. It shows the values from the server
    mSettingsReceived = false;
    getSettingsWindow(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats))->setVisible(false);
    for(CEGUI::Window* settingWindow : mHostSettingWindows)
        settingWindow->setEnabled(false);

    CEGUI::WindowManager& winMgr = CEGUI::WindowManager::getSingleton();
    CEGUI::Window* tmpWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
    CEGUI::Window* msgWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("LoadingText");
    msgWin->setText("Loading...");
    msgWin->setVisible(false);

    tmpWin->setText(reinterpret_cast<const CEGUI::utf8*>(std::string("Configure map : " + gameMap->getLevelName()).c_str()));

    // Reset the chat
    CEGUI::Window* chatWin = tmpWin->getChild("GameChatText");
    chatWin->setText("");
    CEGUI::Window* chatEdit = tmpWin->getChild("GameChatEditBox");
    chatEdit->setText("");

    const std::vector<std::string>& factions = ConfigManager::getSingleton().getFactions();
    const CEGUI::Image* selImg = &CEGUI::ImageManager::getSingleton().get("OpenDungeonsSkin/SelectionBrush");
    const std::vector<Seat*>& seats = gameMap->getSeats();

    int offset = 0;
    bool enabled = false;

    for(Seat* seat : seats)
    {
        // We do not add the rogue creatures seat
        if(seat->isRogueSeat())
            continue;

        mSeatIds.push_back(seat->getId());
        std::string name;
        CEGUI::Combobox* combo;

        name = TEXT_SEAT_ID_PREFIX + Helper::toString(seat->getId());
        CEGUI::DefaultWindow* textSeatId = static_cast<CEGUI::DefaultWindow*>(winMgr.createWindow("OD/StaticText", name));
        tmpWin->addChild(textSeatId);
        Ogre::ColourValue seatColor = seat->getColorValue();
        seatColor.a = 1.0f; // Restore the color opacity
        textSeatId->setArea(CEGUI::UDim(0.3,10), CEGUI::UDim(0,65 + offset), CEGUI::UDim(0,60), CEGUI::UDim(0,30));
        textSeatId->setText("[colour='" + Helper::getCEGUIColorFromOgreColourValue(seatColor) + "']Seat "  + Helper::toString(seat->getId()));
        textSeatId->setProperty("FrameEnabled", "False");
        textSeatId->setProperty("BackgroundEnabled", "False");

        name = COMBOBOX_PLAYER_FACTION_PREFIX + Helper::toString(seat->getId());
        combo = static_cast<CEGUI::Combobox*>(winMgr.createWindow("OD/Combobox", name));
        tmpWin->addChild(combo);
        combo->setArea(CEGUI::UDim(0.3,80), CEGUI::UDim(0,70 + offset), CEGUI::UDim(0.2,0), CEGUI::UDim(0,150));
        combo->setReadOnly(true);
        combo->setEnabled(enabled);
        combo->setSortingEnabled(true);
        if(seat->getFaction().compare(Seat::PLAYER_FACTION_CHOICE) == 0)
        {
            uint32_t cptFaction = 0;
            for(const std::string& faction : factions)
            {
                CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(faction, cptFaction);
                item->setSelectionBrushImage(selImg);
                combo->addItem(item);
                // We set nothing in the combos. They will be refreshed by the server
                ++cptFaction;
            }
        }
        else
        {
            uint32_t cptFaction = 0;
            for(const std::string& faction : factions)
            {
                if(seat->getFaction().compare(faction) == 0)
                    break;

                ++cptFaction;
            }
            // If the faction is not found, we set it to the first defined
            if(cptFaction >= factions.size())
                cptFaction = 0;

            CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(factions[cptFaction], cptFaction);
            item->setSelectionBrushImage(selImg);
            combo->addItem(item);
            combo->setText(item->getText());
            combo->setEnabled(false);
        }
        combo->subscribeEvent(CEGUI::Combobox::EventListSelectionAccepted, CEGUI::SubscriberSlot(&MenuModeConfigureSeats::comboChanged, this));

        name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seat->getId());
        combo = static_cast<CEGUI::Combobox*>(winMgr.createWindow("OD/Combobox", name));
        tmpWin->addChild(combo);
        combo->setArea(CEGUI::UDim(0.7,-90), CEGUI::UDim(0,70 + offset), CEGUI::UDim(0.3,0), CEGUI::UDim(0,150));
        combo->setReadOnly(true);
        combo->setEnabled(enabled);
        combo->setSortingEnabled(true);
        if(seat->getPlayerType().compare(Seat::PLAYER_TYPE_INACTIVE) == 0)
        {
            CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(Seat::PLAYER_TYPE_INACTIVE, Seat::PLAYER_TYPE_INACTIVE_ID);
            item->setSelectionBrushImage(selImg);
            combo->addItem(item);
            combo->setText(item->getText());
            combo->setEnabled(false);
        }
        else if(seat->getPlayerType().compare(Seat::PLAYER_TYPE_AI) == 0)
        {
            for(uint32_t i = 0; i < static_cast<uint32_t>(KeeperAIType::nbAI); ++i)
            {
                KeeperAIType type = static_cast<KeeperAIType>(i);
                int32_t id = Seat::aITypeToPlayerId(type);
                CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(KeeperAITypes::toDisplayableString(type), id);
                item->setSelectionBrushImage(selImg);
                combo->addItem(item);
            }
        }
        else if(seat->getPlayerType().compare(Seat::PLAYER_TYPE_CHOICE) == 0)
        {
            for(uint32_t i = 0; i < static_cast<uint32_t>(KeeperAIType::nbAI); ++i)
            {
                KeeperAIType type = static_cast<KeeperAIType>(i);
                int32_t id = Seat::aITypeToPlayerId(type);
                CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(KeeperAITypes::toDisplayableString(type), id);
                item->setSelectionBrushImage(selImg);
                combo->addItem(item);
            }
        }
        combo->subscribeEvent(CEGUI::Combobox::EventListSelectionAccepted, CEGUI::SubscriberSlot(&MenuModeConfigureSeats::comboChanged, this));

        name = COMBOBOX_TEAM_ID_PREFIX + Helper::toString(seat->getId());
        combo = static_cast<CEGUI::Combobox*>(winMgr.createWindow("OD/Combobox", name));
        tmpWin->addChild(combo);
        combo->setArea(CEGUI::UDim(1,-80), CEGUI::UDim(0,70 + offset), CEGUI::UDim(0,60), CEGUI::UDim(0,150));
        combo->setReadOnly(true);
        combo->setEnabled(enabled);
        combo->setSortingEnabled(true);
        const std::vector<int>& availableTeamIds = seat->getAvailableTeamIds();
        OD_ASSERT_TRUE_MSG(!availableTeamIds.empty(), "Empty availableTeamIds for seat id="
            + Helper::toString(seat->getId()));
        if(availableTeamIds.size() > 1)
        {
            for(int teamId : availableTeamIds)
            {
                CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(Helper::toString(teamId), teamId);
                item->setSelectionBrushImage(selImg);
                combo->addItem(item);
                // We do not select anything by default. The server will refresh what needs to be
            }
        }
        else if(!availableTeamIds.empty())
        {
            int teamId = availableTeamIds[0];
            CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(Helper::toString(teamId), teamId);
            item->setSelectionBrushImage(selImg);
            combo->addItem(item);
            combo->setText(item->getText());
            combo->setEnabled(false);
        }
        combo->subscribeEvent(CEGUI::Combobox::EventListSelectionAccepted, CEGUI::SubscriberSlot(&MenuModeConfigureSeats::comboChanged, this));

        offset += 30;
    }

    getModeManager().getGui().registerWindowHierarchy(tmpWin);
    getModeManager().getGui().registerWindowHierarchy(
        getSettingsWindow(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)));

    tmpWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers/LaunchGameButton");
    tmpWin->setEnabled(enabled);

    // We notify the server we are ready to receive players and configure them
    ODClient::getSingleton().queueClientNotification(ClientNotificationType::readyForSeatConfiguration);
}

bool MenuModeConfigureSeats::launchSelectedButtonPressed(const CEGUI::EventArgs&)
{
    // We send to the server the associations faction/seat/player
    // It will be responsible to disconnect the unselected players
    if(!mIsActivePlayerConfig)
        return true;

    ClientNotification* notif = new ClientNotification(ClientNotificationType::seatConfigurationSet);
    ODClient::getSingleton().queueClientNotification(notif);
    return true;
}

bool MenuModeConfigureSeats::goBack(const CEGUI::EventArgs&)
{
    // We disconnect client and, if we are server, the server
    ODClient::getSingleton().disconnect();
    if(ODServer::getSingleton().isConnected())
    {
        ODServer::getSingleton().stopServer();
    }

    getModeManager().requestPreviousMode();
    return true;
}

bool MenuModeConfigureSeats::comboChanged(const CEGUI::EventArgs& ea)
{
    // If the combo changed is a player and he was already in another combo, we remove him from the combo
    CEGUI::Combobox* comboSel = static_cast<CEGUI::Combobox*>(static_cast<const CEGUI::WindowEventArgs&>(ea).window);
    CEGUI::ListboxItem* selItem = comboSel->getSelectedItem();
    if((selItem != nullptr) &&
       (comboSel->getName().compare(0, COMBOBOX_PLAYER_PREFIX.length(), COMBOBOX_PLAYER_PREFIX) == 0) &&
       (static_cast<int32_t>(selItem->getID()) >= Seat::PLAYER_ID_HUMAN_MIN) && // Can be several AI players
       (static_cast<int32_t>(selItem->getID()) != Seat::PLAYER_TYPE_INACTIVE_ID)) // Can be several inactive players
    {
        GameMap* gameMap = ODFrameListener::getSingleton().getClientGameMap();
        CEGUI::Window* playersWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
        for(int seatId : mSeatIds)
        {
            Seat* seat = gameMap->getSeatById(seatId);
            if(seat->getPlayerType().compare(Seat::PLAYER_TYPE_INACTIVE) == 0)
                continue;

            std::string name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seatId);
            CEGUI::Combobox* combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
            if(combo == comboSel)
                continue;

            CEGUI::ListboxItem* item = combo->getSelectedItem();
            if(item == nullptr)
                continue;

            if(item->getID() != selItem->getID())
                continue;

            combo->setText("");
            combo->setItemSelectState(item, false);
        }
    }

    fireSeatConfigurationToServer();
    return true;
}

void MenuModeConfigureSeats::addPlayer(const std::string& nick, int32_t id)
{
    const CEGUI::Image* selImg = &CEGUI::ImageManager::getSingleton().get("OpenDungeonsSkin/SelectionBrush");
    CEGUI::Window* playersWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");

    GameMap* gameMap = ODFrameListener::getSingleton().getClientGameMap();
    mPlayers.push_back(std::pair<std::string, int32_t>(nick, id));
    for(int seatId : mSeatIds)
    {
        Seat* seat = gameMap->getSeatById(seatId);
        if(seat->getPlayerType().compare(Seat::PLAYER_TYPE_INACTIVE) == 0)
            continue;

        if(seat->getPlayerType().compare(Seat::PLAYER_TYPE_AI) == 0)
            continue;

        std::string name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seatId);
        CEGUI::Combobox* combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
        CEGUI::ListboxTextItem* item = new CEGUI::ListboxTextItem(reinterpret_cast<const CEGUI::utf8*>(nick.c_str()), id);
        item->setSelectionBrushImage(selImg);
        combo->addItem(item);
    }
}

void MenuModeConfigureSeats::removePlayer(int32_t id)
{
    CEGUI::Window* playersWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
    for(std::vector<std::pair<std::string, int32_t> >::iterator it = mPlayers.begin(); it != mPlayers.end();)
    {
        std::pair<std::string, int32_t>& player = *it;
        if(player.second != id)
        {
            ++it;
            continue;
        }

        mPlayers.erase(it);
        for(int seatId : mSeatIds)
        {
            std::string name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seatId);
            CEGUI::Combobox* combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
            for(uint32_t i = 0; i < combo->getItemCount();)
            {
                CEGUI::ListboxItem* selItem = combo->getListboxItemFromIndex(i);
                if(selItem->getID() == static_cast<CEGUI::uint>(id))
                {
                    if(selItem->isSelected())
                        combo->setText("");

                    combo->removeItem(selItem);
                }
                else
                    ++i;
            }
        }
        break;
    }
}

void MenuModeConfigureSeats::fireSeatConfigurationToServer()
{
    CEGUI::Window* playersWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");

    ClientNotification* notif = new ClientNotification(ClientNotificationType::seatConfigurationRefresh);

    for(int seatId : mSeatIds)
    {
        CEGUI::Combobox* combo;
        CEGUI::ListboxItem* selItem;
        std::string name;
        notif->mPacket << seatId;
        name = COMBOBOX_PLAYER_FACTION_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
        selItem = combo->getSelectedItem();
        if(selItem != nullptr)
        {
            int32_t factionIndex = static_cast<int32_t>(selItem->getID());
            notif->mPacket << true << factionIndex;
        }
        else
        {
            notif->mPacket << false;
        }

        name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
        selItem = combo->getSelectedItem();
        if(selItem != nullptr)
        {
            int32_t playerId = selItem->getID();
            notif->mPacket << true << playerId;
        }
        else
        {
            notif->mPacket << false;
        }

        name = COMBOBOX_TEAM_ID_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
        selItem = combo->getSelectedItem();
        if(selItem != nullptr)
        {
            int32_t teamId = selItem->getID();
            notif->mPacket << true << teamId;
        }
        else
        {
            notif->mPacket << false;
        }
    }

    // Until the server has sent its values, the window shows the defaults and none of its values is chosen
    CEGUI::Window* generalPage = getGeneralPage(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats));
    const uint32_t notChosen = GameMap::SKIRMISH_SETTING_UNCHOSEN;
    notif->mPacket << getSettingValue(generalPage, COMBOBOX_GOLD_DENSITY, notChosen);
    notif->mPacket << getSettingValue(generalPage, COMBOBOX_MANA_REGENERATION, notChosen);
    notif->mPacket << (mSettingsReceived ? getSpinnerValue(generalPage, SPINNER_MAX_CREATURES) : notChosen);
    notif->mPacket << (mSettingsReceived ? getSpinnerValue(generalPage, SPINNER_GAME_SPEED) : notChosen);
    notif->mPacket << (mSettingsReceived ? getSpinnerValue(generalPage, SPINNER_GAME_DURATION) : notChosen);
    notif->mPacket << getSettingValue(generalPage, COMBOBOX_FOG_OF_WAR, notChosen);
    notif->mPacket << getSettingValue(generalPage, COMBOBOX_HEART_DESTROYED, notChosen);

    uint32_t nbCreatureLimits = mSettingsReceived ? static_cast<uint32_t>(mLimitSpinners.size()) : 0;
    notif->mPacket << nbCreatureLimits;
    if(mSettingsReceived)
    {
        for(const std::pair<const std::string, CEGUI::Spinner*>& limit : mLimitSpinners)
            notif->mPacket << limit.first << static_cast<uint32_t>(limit.second->getCurrentValue());
    }

    uint32_t nbSkillStates = mSettingsReceived ? static_cast<uint32_t>(mItemButtons.size()) : 0;
    notif->mPacket << nbSkillStates;
    if(mSettingsReceived)
    {
        for(const std::pair<const uint32_t, CEGUI::Window*>& item : mItemButtons)
            notif->mPacket << item.first << mItemStates[item.first];
    }
    ODClient::getSingleton().queueClientNotification(notif);
}

void MenuModeConfigureSeats::activatePlayerConfig()
{
    mIsActivePlayerConfig = true;
    GameMap* gameMap = ODFrameListener::getSingleton().getClientGameMap();
    CEGUI::Window* listPlayersWindow = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
    listPlayersWindow->setText("Please configure map : " + gameMap->getLevelName());
    bool enabled = true;

    for(int seatId : mSeatIds)
    {
        Seat* seat = gameMap->getSeatById(seatId);

        std::string name;
        CEGUI::Combobox* combo;

        name = COMBOBOX_PLAYER_FACTION_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(listPlayersWindow->getChild(name));
        if(combo->getItemCount() > 1)
            combo->setEnabled(enabled);

        name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(listPlayersWindow->getChild(name));
        if(enabled)
        {
            if(seat->getPlayerType().compare(Seat::PLAYER_TYPE_INACTIVE) != 0)
                combo->setEnabled(enabled);
        }
        else
            combo->setEnabled(enabled);

        name = COMBOBOX_TEAM_ID_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(listPlayersWindow->getChild(name));
        if(combo->getItemCount() > 1)
            combo->setEnabled(enabled);
    }

    for(CEGUI::Window* settingWindow : mHostSettingWindows)
        settingWindow->setEnabled(enabled);

    CEGUI::Window* startButton = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers/LaunchGameButton");
    startButton->setEnabled(enabled);
}

void MenuModeConfigureSeats::refreshSeatConfiguration(ODPacket& packet)
{
    CEGUI::Window* playersWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
    for(int seatId : mSeatIds)
    {
        CEGUI::Combobox* combo;
        bool isSelected;
        int seatIdPacket;
        CEGUI::ListboxItem* selItem = nullptr;
        OD_ASSERT_TRUE(packet >> seatIdPacket);
        OD_ASSERT_TRUE_MSG(seatId == seatIdPacket, "seatId=" + Helper::toString(seatId) + ", seatIdPacket=" + Helper::toString(seatIdPacket));
        std::string name;
        name = COMBOBOX_PLAYER_FACTION_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
        OD_ASSERT_TRUE(packet >> isSelected);
        if(isSelected)
        {
            int32_t factionIndex = -1;
            OD_ASSERT_TRUE(packet >> factionIndex);
            uint32_t id = static_cast<uint32_t>(factionIndex);
            selItem = nullptr;
            for(uint32_t i = 0; i < combo->getItemCount(); ++i)
            {
                CEGUI::ListboxItem* item = combo->getListboxItemFromIndex(i);
                if(isSelected && item->getID() == id)
                    selItem = item;

                combo->setItemSelectState(item, false);
            }
            if(selItem != nullptr)
            {
                combo->setText(selItem->getText());
                combo->setItemSelectState(selItem, true);
            }
        }

        name = COMBOBOX_PLAYER_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
        OD_ASSERT_TRUE(packet >> isSelected);
        int32_t playerId = 0;
        if(isSelected)
        {
            OD_ASSERT_TRUE(packet >> playerId);
        }

        // Because of a bug in CEGUI::Combobox, the text is unset if we call setItemSelectState
        // on an unselected item that has the same text as the currently selected one. For
        // this reason, we start by unselecting everything and we will select after if
        // there is something to select
        selItem = nullptr;
        for(uint32_t i = 0; i < combo->getItemCount(); ++i)
        {
            CEGUI::ListboxItem* item = combo->getListboxItemFromIndex(i);
            if(isSelected && item->getID() == static_cast<uint32_t>(playerId))
                selItem = item;

            combo->setItemSelectState(item, false);
        }
        if(selItem != nullptr)
        {
            combo->setText(selItem->getText());
            combo->setItemSelectState(selItem, true);
        }

        name = COMBOBOX_TEAM_ID_PREFIX + Helper::toString(seatId);
        combo = static_cast<CEGUI::Combobox*>(playersWin->getChild(name));
        OD_ASSERT_TRUE(packet >> isSelected);
        int32_t teamId = 0;
        if(isSelected)
        {
            OD_ASSERT_TRUE(packet >> teamId);
        }
        selItem = nullptr;
        for(uint32_t i = 0; i < combo->getItemCount(); ++i)
        {
            CEGUI::ListboxItem* item = combo->getListboxItemFromIndex(i);
            if(isSelected && item->getID() == static_cast<uint32_t>(teamId))
                selItem = item;

            combo->setItemSelectState(item, false);
        }
        if(selItem != nullptr)
        {
            combo->setText(selItem->getText());
            combo->setItemSelectState(selItem, true);
        }
    }

    uint32_t goldDensityPercent;
    uint32_t manaRegenerationPercent;
    uint32_t maxCreaturesSetting;
    OD_ASSERT_TRUE(packet >> goldDensityPercent);
    OD_ASSERT_TRUE(packet >> manaRegenerationPercent);
    OD_ASSERT_TRUE(packet >> maxCreaturesSetting);
    uint32_t gameSpeedPercent;
    uint32_t gameDurationMinutes;
    uint32_t fogOfWar;
    uint32_t heartDestroyedReward;
    OD_ASSERT_TRUE(packet >> gameSpeedPercent);
    OD_ASSERT_TRUE(packet >> gameDurationMinutes);
    OD_ASSERT_TRUE(packet >> fogOfWar);
    OD_ASSERT_TRUE(packet >> heartDestroyedReward);

    // The window is changed to what the server says. This must not be sent back
    mIsRefreshing = true;
    CEGUI::Window* generalPage = getGeneralPage(getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats));
    selectSettingValue(generalPage, COMBOBOX_GOLD_DENSITY, goldDensityPercent);
    selectSettingValue(generalPage, COMBOBOX_MANA_REGENERATION, manaRegenerationPercent);
    selectSettingValue(generalPage, COMBOBOX_FOG_OF_WAR, fogOfWar);
    selectSettingValue(generalPage, COMBOBOX_HEART_DESTROYED, heartDestroyedReward);
    // 0 means that the default number of creatures is used
    if(maxCreaturesSetting == 0)
        maxCreaturesSetting = ConfigManager::getSingleton().getMaxCreaturesPerSeatDefault();
    static_cast<CEGUI::Spinner*>(generalPage->getChild(SPINNER_MAX_CREATURES))->setCurrentValue(maxCreaturesSetting);
    static_cast<CEGUI::Spinner*>(generalPage->getChild(SPINNER_GAME_SPEED))->setCurrentValue(gameSpeedPercent);
    static_cast<CEGUI::Spinner*>(generalPage->getChild(SPINNER_GAME_DURATION))->setCurrentValue(gameDurationMinutes);

    uint32_t nbCreatureLimits;
    OD_ASSERT_TRUE(packet >> nbCreatureLimits);
    for(uint32_t i = 0; i < nbCreatureLimits; ++i)
    {
        std::string className;
        uint32_t limit;
        OD_ASSERT_TRUE(packet >> className >> limit);
        std::map<std::string, CEGUI::Spinner*>::iterator itLimit = mLimitSpinners.find(className);
        if(itLimit != mLimitSpinners.end())
            itLimit->second->setCurrentValue(limit);
    }

    uint32_t nbSkillStates;
    OD_ASSERT_TRUE(packet >> nbSkillStates);
    for(uint32_t i = 0; i < nbSkillStates; ++i)
    {
        uint32_t skillType;
        uint32_t skillState;
        OD_ASSERT_TRUE(packet >> skillType >> skillState);
        std::map<uint32_t, CEGUI::Window*>::iterator itItem = mItemButtons.find(skillType);
        if(itItem == mItemButtons.end() || skillState > static_cast<uint32_t>(GameMap::SkirmishItemState::needsResearch))
            continue;

        mItemStates[skillType] = skillState;
        itItem->second->setText(itemStateText(skillState));
    }
    mIsRefreshing = false;
    mSettingsReceived = true;

    // The speed of the game is also needed to animate the game when it starts
    ODFrameListener::getSingleton().getClientGameMap()->setGameRules(gameSpeedPercent, gameDurationMinutes,
        fogOfWar != 0, heartDestroyedReward);
}

void MenuModeConfigureSeats::receiveChat(const ChatMessage& chat)
{
    CEGUI::Window* playersWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
    // Adds the message right away
    CEGUI::Window* chatWin = playersWin->getChild("GameChatText");
    chatWin->appendText(reinterpret_cast<const CEGUI::utf8*>(chat.getMessageAsString().c_str()));

    // Ensure the latest text is shown
    CEGUI::Scrollbar* scrollBar = reinterpret_cast<CEGUI::Scrollbar*>(chatWin->getChild("__auto_vscrollbar__"));
    scrollBar->setScrollPosition(scrollBar->getDocumentSize());
}

bool MenuModeConfigureSeats::chatText(const CEGUI::EventArgs& e)
{
    CEGUI::Window* playersWin = getModeManager().getGui().getGuiSheet(Gui::guiSheet::configureSeats)->getChild("ListPlayers");
    CEGUI::Editbox* chatEdit = static_cast<CEGUI::Editbox*>(playersWin->getChild("GameChatEditBox"));
    const std::string txt = chatEdit->getText().c_str();

    ODClient::getSingleton().queueClientNotification(ClientNotificationType::chat, txt);

    chatEdit->setText("");

    return true;
}
