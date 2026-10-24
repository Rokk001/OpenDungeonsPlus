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

#ifndef MODEMANAGER_H
#define MODEMANAGER_H

#include "modes/AbstractModeManager.h"

#include "modes/InputManager.h"

#include <vector>
#include <memory>
#include <string>

class AbstractApplicationMode;
class CameraManager;
class Gui;
namespace CEGUI
{
class Window;
}

namespace Ogre {
  class RenderWindow;
}

//! \brief Switches application modes and preserves scene flights between existing menu panes.
class ModeManager final : public AbstractModeManager
{
public:

    ModeManager(Ogre::RenderWindow* renderWindow, Gui* gui);
    virtual ~ModeManager();

    //! \brief Updates mouse event, checks for made changes, ...
    void update(const Ogre::FrameEvent& evt);

    AbstractApplicationMode* getCurrentMode();
    ModeType getCurrentModeType() const;

    //! \brief Request loading the given game mode
    void requestMode(ModeType mode, bool keepCurrentModeInHistory = true)
    {
        mRequestedMode = mode;
        mStoreCurrentModeAtChange = keepCurrentModeInHistory;
    }

    //! Request the main menu, opened with its skirmish sub-menu (used after the defeat debriefing)
    void requestMainMenuWithSkirmishSubMenu()
    {
        mOpenSkirmishSubMenu = true;
        requestMode(MENU_MAIN);
    }

    //! Returns true once if the main menu should open its skirmish sub-menu, then forgets it
    bool consumeSkirmishSubMenuRequest()
    {
        const bool requested = mOpenSkirmishSubMenu;
        mOpenSkirmishSubMenu = false;
        return requested;
    }

    //! \brief Consumes a request to fly into the main menu after returning from a game or editor.
    bool consumeMainMenuArrivalRequest()
    {
        const bool requested = mMainMenuArrivalRequested;
        mMainMenuArrivalRequested = false;
        return requested;
    }

    //! \brief Requests the previous mode once without consuming history during a menu flight.
    void requestPreviousMode();
    //! \brief Request to leave the current mode and launch the given saved game.
    void requestSavedGame(const std::string& filename);

    InputManager& getInputManager()
    { return mInputManager; }

    Gui& getGui()
    { return *mGui; }

    //! \brief The currently loaded mode.
    std::unique_ptr<AbstractApplicationMode> mCurrentApplicationMode;
    
private:
    //! \brief The common input manager instance
    InputManager mInputManager;

    //! \brief Pointer to the GUI instance
    Gui* mGui;



    //! \brief Stores the order of modes loaded. Useful when used to go back to the previous mode.
    std::vector<ModeType> mPreviousModeTypes;

    //! \brief Tells which new mode is requested.
    ModeManager::ModeType mRequestedMode;

    //! \brief Tells whether the current mode should be kept in history
    //! when changing from the current mode.
    bool mStoreCurrentModeAtChange;
    //! Set by requestMainMenuWithSkirmishSubMenu, consumed by the main menu when it is activated
    bool mOpenSkirmishSubMenu = false;
    //! Requests the configured outside-to-overview flight on the next main-menu activation.
    bool mMainMenuArrivalRequested = false;
    //! True while returning from another menu pane to the overview before activating the main menu.
    bool mMainMenuReturnPending = false;
    //! Menu pane temporarily hidden during an arrival or return flight; never owned here.
    CEGUI::Window* mFlightHiddenWindow = nullptr;
    //! Destination to reach after the arrival from a game, empty when no arrival is pending.
    std::string mMenuArrivalPlace = std::string();
    //! \brief Saved game that the next load menu launches right away, empty if none.
    std::string mRequestedSavedGame;

    //! \brief Actually change the mode if needed
    void checkModeChange();

    //! \brief Hides the current pane for a scene flight without changing its controls or contents.
    void hideMenuForFlight();
    //! \brief Restores the pane hidden by a completed or superseded menu flight.
    void restoreMenuAfterFlight();
    //! \brief Finishes a game-to-campaign arrival before revealing its existing pane.
    bool updateMenuArrival();
};

#endif // MODEMANAGER_H
