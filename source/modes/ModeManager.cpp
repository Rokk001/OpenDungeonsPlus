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

#include "modes/ModeManager.h"

#include "modes/InputManager.h"
#include "modes/AdvertMode.h"
#include "modes/MenuModeMain.h"
#include "modes/MenuModeConfigureSeats.h"
#include "modes/MenuModeCampaign.h"
#include "modes/MenuModeSkirmish.h"
#include "modes/MenuModeMasterServerJoin.h"
#include "modes/MenuModeMultiplayerClient.h"
#include "modes/MenuModeMultiplayerServer.h"
#include "modes/MenuModeEditorNew.h"
#include "modes/MenuModeEditorLoad.h"
#include "modes/MenuModeReplay.h"
#include "modes/MenuModeLoad.h"
#include "modes/GameMode.h"
#include "modes/EditorMode.h"
#include "utils/MakeUnique.h"
#include "render/Gui.h"
#include "render/ODFrameListener.h"

#include <CEGUI/Window.h>
#include <CEGUI/GUIContext.h>
#include <CEGUI/System.h>

namespace
{
//! Configured scene destinations used by menu return and campaign arrival.
static const std::string PLACE_OVERVIEW = "overview";
static const std::string PLACE_CAMPAIGN = "campaign";
}

ModeManager::ModeManager(Ogre::RenderWindow* renderWindow, Gui* gui) :
    mInputManager(renderWindow),
    mGui(gui),
    mRequestedMode(ModeType::MENU_MAIN),
    mStoreCurrentModeAtChange(true)
{
}

ModeManager::~ModeManager()
{
}

AbstractApplicationMode* ModeManager::getCurrentMode()
{
    return mCurrentApplicationMode.get();
}

ModeManager::ModeType ModeManager::getCurrentModeType() const
{
    return mCurrentApplicationMode->getModeType();
}

//! \brief Requests the previous mode once, without consuming history during a menu flight.
void ModeManager::requestPreviousMode()
{
    ODFrameListener& listener = ODFrameListener::getSingleton();
    if(mMainMenuReturnPending || !mMenuArrivalPlace.empty() || listener.isMainMenuFlightActive() ||
       (mRequestedMode == MENU_MAIN && mCurrentApplicationMode != nullptr &&
        mCurrentApplicationMode->getModeType() != MENU_MAIN))
        return;
    if (mPreviousModeTypes.empty())
    {
        mRequestedMode = MENU_MAIN;
        return;
    }

    mRequestedMode = mPreviousModeTypes.back();
    mPreviousModeTypes.pop_back();

    // Don't store current mode when changing it
    // Otherwise, we could loop between two modes
    // when going backward more than one time.
    mStoreCurrentModeAtChange = false;
}

void ModeManager::requestSavedGame(const std::string& filename)
{
    mRequestedSavedGame = filename;
    requestMode(MENU_LOAD_SAVEDGAME, false);
}

//! \brief Hides the current menu sheet while the camera returns or enters a destination.
void ModeManager::hideMenuForFlight()
{
    if(mFlightHiddenWindow != nullptr)
        return;
    mFlightHiddenWindow = CEGUI::System::getSingleton().getDefaultGUIContext().getRootWindow();
    if(mFlightHiddenWindow != nullptr)
        mFlightHiddenWindow->hide();
}

//! \brief Restores a hidden sheet before it is reused or replaced by another existing pane.
void ModeManager::restoreMenuAfterFlight()
{
    if(mFlightHiddenWindow != nullptr)
        mFlightHiddenWindow->show();
    mFlightHiddenWindow = nullptr;
}

//! \brief Reveals the returning campaign pane after the arrival and table flight finish.
bool ModeManager::updateMenuArrival()
{
    if(mMenuArrivalPlace.empty())
        return false;
    ODFrameListener& listener = ODFrameListener::getSingleton();
    if(listener.isMainMenuFlightActive())
        return true;
    if(listener.getMainMenuPlace() != mMenuArrivalPlace)
    {
        listener.flyMainMenuTo(mMenuArrivalPlace);
        return true;
    }
    mMenuArrivalPlace.clear();
    restoreMenuAfterFlight();
    return false;
}

//! \brief Changes modes after any required overview return while preserving existing mode history.
void ModeManager::checkModeChange()
{
    if (mRequestedMode == NONE)
        return;

    ODFrameListener& listener = ODFrameListener::getSingleton();
    if(!mMenuArrivalPlace.empty())
    {
        mMenuArrivalPlace.clear();
        restoreMenuAfterFlight();
    }
    if(mMainMenuReturnPending)
    {
        if(mRequestedMode == MENU_MAIN && listener.isMainMenuFlightActive())
            return;
        mMainMenuReturnPending = false;
        restoreMenuAfterFlight();
    }
    if(mRequestedMode == MENU_MAIN && mCurrentApplicationMode != nullptr &&
       mCurrentApplicationMode->getModeType() != MENU_MAIN &&
       mCurrentApplicationMode->getModeType() != GAME &&
       mCurrentApplicationMode->getModeType() != EDITOR && listener.getIsMainMenuCreated() &&
       listener.getMainMenuPlace() != PLACE_OVERVIEW)
    {
        if(listener.isMainMenuFlightActive())
            return;
        if(listener.flyMainMenuTo(PLACE_OVERVIEW))
        {
            mMainMenuReturnPending = true;
            hideMenuForFlight();
            return;
        }
    }

    const bool initialMode = mCurrentApplicationMode == nullptr;
    ModeType previousMode = NONE;
    if(mCurrentApplicationMode != nullptr)
    {
        if (mCurrentApplicationMode->getModeType() == mRequestedMode)
            return;

        // Keep the previous mode in mind.
        previousMode = mCurrentApplicationMode->getModeType();

        if(mRequestedMode == MENU_MAIN && (previousMode == GAME || previousMode == EDITOR))
            mMainMenuArrivalRequested = true;

        mCurrentApplicationMode->deactivate();
        mCurrentApplicationMode = nullptr;
    }

    switch(mRequestedMode)
    {
    case MENU_MAIN:
        mCurrentApplicationMode = Utils::make_unique<MenuModeMain>(this);
        // In that case, we are at the root menu and should ensure to have
        // a clean mode type history
        mPreviousModeTypes.clear();
        previousMode = NONE;
        break;
    case MENU_SKIRMISH:
        mCurrentApplicationMode = Utils::make_unique<MenuModeSkirmish>(this);
        break;
    case MENU_REPLAY:
        mCurrentApplicationMode = Utils::make_unique<MenuModeReplay>(this);
        break;
    case MENU_MULTIPLAYER_CLIENT:
        mCurrentApplicationMode = Utils::make_unique<MenuModeMultiplayerClient>(this);
        break;
    case MENU_MULTIPLAYER_SERVER:
        mCurrentApplicationMode = Utils::make_unique<MenuModeMultiplayerServer>(this, false);
        break;
    case MENU_EDITOR_NEW:
        mCurrentApplicationMode = Utils::make_unique<MenuModeEditorNew>(this);
        break;
    case MENU_EDITOR_LOAD:
        mCurrentApplicationMode = Utils::make_unique<MenuModeEditorLoad>(this);
        break;
    case MENU_CONFIGURE_SEATS:
        mCurrentApplicationMode = Utils::make_unique<MenuModeConfigureSeats>(this);
        break;
    case GAME:
        mCurrentApplicationMode = Utils::make_unique<GameMode>(this);
        break;
    case EDITOR:
        mCurrentApplicationMode = Utils::make_unique<EditorMode>(this);
        break;
    case MENU_LOAD_SAVEDGAME:
        mCurrentApplicationMode = Utils::make_unique<MenuModeLoad>(this, false, mRequestedSavedGame);
        mRequestedSavedGame.clear();
        if(previousMode == GAME)
            mPreviousModeTypes.clear();
        break;
    case MENU_CAMPAIGN:
        mCurrentApplicationMode = Utils::make_unique<MenuModeCampaign>(this);
        break;
    case MENU_MASTERSERVER_HOST:
        mCurrentApplicationMode = Utils::make_unique<MenuModeMultiplayerServer>(this, true);
        break;
    case MENU_MASTERSERVER_JOIN:
        mCurrentApplicationMode = Utils::make_unique<MenuModeMasterServerJoin>(this);
        break;
    case ADVERTISMENT:
        mCurrentApplicationMode = Utils::make_unique<AdvertMode>(this);
    default:
        break;
    }

    const bool campaignArrival = mRequestedMode == MENU_CAMPAIGN &&
        (previousMode == GAME || previousMode == EDITOR);
    mCurrentApplicationMode->activate();
    if(campaignArrival)
    {
        listener.startMainMenuFlight();
        mMenuArrivalPlace = PLACE_CAMPAIGN;
        hideMenuForFlight();
    }

    if((initialMode && mRequestedMode == MENU_MAIN) || mRequestedMode == GAME)
    {
        CEGUI::Window* navigation = mRequestedMode == GAME
            ? mGui->getGuiSheet(Gui::inGameMenu)->getChild(Gui::MAIN_TABCONTROL)
            : mGui->getGuiSheet(Gui::mainMenu)->getChild("StartSkirmishButton");
        const CEGUI::Rectf area = navigation->getUnclippedOuterRect().get();
        mInputManager.setMousePosition(static_cast<int>((area.left() + area.right()) * 0.5f),
                                       static_cast<int>((area.top() + area.bottom()) * 0.5f));
    }

    // Add the previous mode to mode types history when relevant.
    if (previousMode != NONE && mStoreCurrentModeAtChange)
        mPreviousModeTypes.push_back(previousMode);

    mRequestedMode = NONE;
}

//! \brief Advances mode changes and keeps a returning campaign pane hidden until arrival.
void ModeManager::update(const Ogre::FrameEvent& evt)
{
    checkModeChange();
    mInputManager.refreshSettings();

    // We update the current mode
    AbstractApplicationMode* currentMode = getCurrentMode();

#ifndef OD_USE_SFML_WINDOW
    mInputManager.mMouse->capture();
    mInputManager.mKeyboard->getKeyboard()->capture();
#endif
    //currentMode->mouseMoved(OIS::MouseEvent(nullptr, currentMode->getMouse()->getMouseState()));

    currentMode->updateCameraControls(evt.timeSinceLastFrame);
    if(updateMenuArrival())
        return;
    currentMode->onFrameStarted(evt);
}
