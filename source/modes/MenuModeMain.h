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

#ifndef MENUMODEMAIN_H
#define MENUMODEMAIN_H

#include "AbstractApplicationMode.h"

#include "modes/SettingsWindow.h"

#include <string>

//! \brief Shows the existing main-menu panes after their configured scene flights finish.
class MenuModeMain: public AbstractApplicationMode
{
public:
    //! \brief Connects the existing menu actions to their scene-flight timing.
    MenuModeMain(ModeManager*);

    virtual ~MenuModeMain()
    {}

    //! \brief Called when the game mode is activated
    //! Used to call the corresponding Gui Sheet, and to start a level again if a restart was requested
    //! from the game.
    void activate() final override;

    //! \brief Opens the overview or requested pane only after its flight reaches the configured destination.
    void onFrameStarted(const Ogre::FrameEvent& evt) override;

    //! \brief Defers replay navigation until arrival and keeps quitting immediate during a flight.
    bool changeModeAfterFlight(AbstractModeManager::ModeType mode, const CEGUI::EventArgs& e);

    //! \brief Hides the open submenu and restores overview entries only after the return flight.
    bool goBack(const CEGUI::EventArgs& e = {}) override;

private:
    //! \brief Starts the level again if the in-game "Restart Level" button asked for it
    void restartPendingLevel();

    //! \brief The Settings window
    SettingsWindow mSettings;
    //! \brief True while a settings page opened from the settings sub menu is shown,
    //! so that closing it shows the sub menu again.
    bool mSettingsPageOpen = false;
    //! True while the menu waits for the flight to end before it shows the skirmish sub-menu
    bool mSkirmishSubMenuPending = false;
    //! True while overview entries wait for the outside arrival or return flight to finish.
    bool mOverviewPending = false;
    //! Existing submenu waiting for its configured scene flight to finish.
    std::string mPendingSubMenu = std::string();
    //! Existing mode waiting for its configured scene flight to finish.
    AbstractModeManager::ModeType mPendingMode = AbstractModeManager::NONE;

    //! \brief Helper functions to connect a button to a mode change
    void connectModeChangeEvent(const std::string& buttonName, AbstractModeManager::ModeType mode);
    //! \brief Connects an existing mode-changing button through flight-aware navigation.
    void connectModeChangeEvent(CEGUI::Window* button, AbstractModeManager::ModeType mode);

    //! \brief Function triggered when pushing a button
    bool quitButtonPressed(const CEGUI::EventArgs&);
    //! \brief Flies to the right tower before showing the existing settings submenu.
    bool toggleSettings(const CEGUI::EventArgs&);
    //! \brief Hides the settings sub menu and shows the named settings page.
    bool openSettingsPage(const std::string& name);
    //! \brief Opens the settings page belonging to the clicked sub menu button.
    bool settingsPageButtonClicked(const CEGUI::EventArgs& e);
    //! \brief Shows the settings sub menu again after a settings page was closed.
    bool settingsPageClosed(const CEGUI::EventArgs&);
    //! \brief Shows or hides the main menu buttons behind the sub menus.
    void showMainMenuButtons(bool visible);
    //! \brief Flies to the named submenu's location before showing its existing controls.
    bool toggleSubMenu(const std::string& name);
    //! \brief Shows one existing submenu after arrival and hides its siblings.
    void showSubMenu(const std::string& name);

    //! \brief Sub menu button triggers
    //! \brief Shows or hides the campaign sub menu
    bool toggleCampaignSubMenu(const CEGUI::EventArgs&);
    //! \brief Starts a new campaign, after a confirmation when there is saved progress that it would replace
    bool newCampaignPressed(const CEGUI::EventArgs&);
    //! \brief Forgets the saved campaign progress and opens the campaign menu
    bool newCampaignConfirmed(const CEGUI::EventArgs&);

    //! \brief Shows or hides the question that asks whether the saved campaign progress
    //! may be replaced by a new campaign, in place of the two campaign buttons
    void showNewCampaignConfirm(bool visible);
    //! \brief Flies to the side cave before showing the existing skirmish submenu.
    bool toggleSkirmishSubMenu(const CEGUI::EventArgs&);
    //! \brief Flies to the left arcade before showing the existing multiplayer submenu.
    bool toggleMultiplayerSubMenu(const CEGUI::EventArgs&);
    //! \brief Flies to the workshop before showing the existing editor submenu.
    bool toggleEditorSubMenu(const CEGUI::EventArgs&);

    //! \brief Opens the level list with the sandbox levels
    bool sandboxButtonPressed(const CEGUI::EventArgs& e);
};

#endif // MENUMODEMAIN_H
