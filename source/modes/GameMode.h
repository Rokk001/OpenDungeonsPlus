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

#ifndef GAMEMODE_H
#define GAMEMODE_H

#include "GameEditorModeBase.h"

#include "modes/DebriefingTable.h"
#include "modes/DefeatHeartBurst.h"
#include "modes/DefeatSequence.h"
#include "modes/InputCommand.h"
#include "modes/InputBridge.h"
#include "modes/SettingsWindow.h"
#include "game/CreaturePanelData.h"
#include "game/TrapProductionData.h"

#include "utils/ConfigManager.h"
#include <CEGUI/EventArgs.h>
#include <map>
#include <chrono>
#include <cstdint>
#include <memory>
#include <set>
#include <vector>

namespace CEGUI
{
class Window;
}

class Creature;
class CreaturePanel;
class GameEntity;
class MiniMapDrawnFull;
class MenuModeLoad;
class SocialWindow;

enum class SpellType;
enum class SkillType;

//! \brief utility class to store and display the current skill completion. To make clearer
//! if it fills up or down, we fill it smoothly each time the player opens the skill tree
class SkillCurrentCompletion
{
public:
    SkillCurrentCompletion()
    {
        resetValue();
    }

    void resetValue()
    {
        mProgressBar = nullptr;
        mCompleteness = 0;
        mCompletenessDisplayed = 0;
    }

    void setValue(CEGUI::ProgressBar* progressBar, float completeness)
    {
        mProgressBar = progressBar;
        mCompleteness = completeness;
        mCompletenessDisplayed = 0;
    }

    //! \brief The progressbar to update at each frame update
    CEGUI::ProgressBar* mProgressBar;
    //! \brief The completeness
    float mCompleteness;
    //! \brief Value currently displayed [0-completeness]
    float mCompletenessDisplayed;
};



class GameMode final : public GameEditorModeBase, public InputCommand
{
 public:
    //! \brief Connects the in-game controls and existing objectives window to the mode manager.
    GameMode(ModeManager*);

    virtual ~GameMode();

    /*! \brief Process the mouse movement event.
     *
     * The function uses ground targeting for room construction and surface targeting
     * for other actions to handle dragging selections and selecting creatures.
     */
    virtual bool mouseMoved     (const OIS::MouseEvent &arg) override;

    /*! \brief Handle mouse clicks.
     *
     * This function uses the current action target to determine whether a creature
     * or a selection of eligible tiles is being dragged.
     */
    virtual bool mousePressed   (const OIS::MouseEvent &arg, OIS::MouseButtonID id) override;

    /*! \brief Handle mouse button releases.
     *
     * Finalize the selection of tiles or drop a creature when the user releases the mouse button.
     */
    virtual bool mouseReleased  (const OIS::MouseEvent &arg, OIS::MouseButtonID id) override;

    //! \brief Handle the keyboard input.
    virtual bool keyPressed     (const OIS::KeyEvent &arg) override;

    /*! \brief Process the key up event.
     *
     * When a key is released during normal gamplay the camera movement may need to be stopped.
     */
    virtual bool keyReleased    (const OIS::KeyEvent &arg) override;

    /*! \brief defines what the hotkeys do
     *
     * currently the only thing the hotkeys do is moving the camera around.
     * If the shift key is pressed we store this hotkey location
     * otherwise we fly the camera to a stored position.
     */
    virtual void handleHotkeys  (OIS::KeyCode keycode) override;

    void onFrameStarted(const Ogre::FrameEvent& evt) override;
    void onFrameEnded(const Ogre::FrameEvent& evt) override;
    void receiveEventShortNotice(EventMessage* event) override;

    //! \brief Called when the game mode is activated
    //! Used to call the corresponding Gui Sheet.
    void activate() override;
    void deactivate() override;

    //! \brief Called when exit button is pressed
    void popupExit(bool pause);

    virtual void notifyGuiAction(GuiAction guiAction) override;

    //! \brief Shows/hides/toggles the help window
    bool showHelpWindow(const CEGUI::EventArgs& = {});
    bool hideHelpWindow(const CEGUI::EventArgs& = {});
    bool toggleHelpWindow(const CEGUI::EventArgs& = {});

    //! \brief Shows/hides/toggles the objectives window
    bool showObjectivesWindow(const CEGUI::EventArgs& = {});
    bool hideObjectivesWindow(const CEGUI::EventArgs& = {});
    bool toggleObjectivesWindow(const CEGUI::EventArgs& = {});

    //! \brief Shows/toggles the Dungeonbook (creature list and post feed) and closes it again
    bool toggleSocialWindow(const CEGUI::EventArgs& = {});
    //! \brief Shows the Dungeonbook above the other windows with the creature selected, used by the
    //! creature card (the card stays open)
    void showSocialWindow(const std::string& selectedCreature);
    //! \brief Sandbox panel: toggles the window, changes the level of the heroes (left click up,
    //! right click down), takes a hero in the hand and starts hero invasions
    bool toggleSandboxWindow(const CEGUI::EventArgs& = {});
    bool hideSandboxWindow(const CEGUI::EventArgs& = {});
    bool onSandboxHeroLevelClicked(const CEGUI::EventArgs& e);
    bool takeSandboxHero(const CEGUI::EventArgs& = {});
    bool startSandboxSingleInvasion(const CEGUI::EventArgs& = {});
    bool startSandboxContinualInvasion(const CEGUI::EventArgs& = {});
    //! \brief Shows the score and the room timer the server sent (on the HUD and in the sandbox window) and
    //! opens the prompt when the server tells that the realm is complete
    void updateSandboxStatus();
    //! \brief The prompt after a completed realm: leave for the next realm, or stay in this one
    bool onSandboxNextRealm(const CEGUI::EventArgs& = {});
    bool onSandboxStay(const CEGUI::EventArgs& = {});

    //! \brief Shows/hides/toggles the player settings window
    //! \brief Casino payout control, opened by clicking on one of the player's casinos
    void showCasinoPayoutWindow(Tile* tile);
    bool hideCasinoPayoutWindow(const CEGUI::EventArgs& = {});
    bool cycleCasinoPayout(const CEGUI::EventArgs& = {});
    //! \brief Called when the server tells the payout level of a casino. It is only shown if
    //! it is the casino the window is open for.
    void setCasinoPayoutShown(int tileX, int tileY, uint32_t level);

    bool showPlayerSettingsWindow(const CEGUI::EventArgs& = {});
    bool togglePlayerSettingsWindow(const CEGUI::EventArgs& = {});
    bool cancelPlayerSettings(const CEGUI::EventArgs& = {});
    bool applyPlayerSettings(const CEGUI::EventArgs& = {});
    //! \brief Synchronize settings displayed in the menu with settings in the seat
    void syncPlayerSettings();

    //! \brief Shows/hides/toggles the Skill window
    bool showSkillWindow(const CEGUI::EventArgs& = {});
    bool hideSkillWindow(const CEGUI::EventArgs& = {});
    bool toggleSkillWindow(const CEGUI::EventArgs& = {});
    bool applySkillWindow(const CEGUI::EventArgs& = {});
    bool unselectAllSkillWindow(const CEGUI::EventArgs& = {});
    bool autoFillSkillWindow(const CEGUI::EventArgs& = {});
    void closeSkillWindow(bool saveSkill);
    //! \brief Shows the data received from the server in the production window and keeps
    //! the selected order selected.
    void refreshTrapProductionQueue(const TrapProductionData& data);

    //! \brief Entry point of the defeat sequence, called once when the server reports that the local
    //! player lost. conquerorSeatId is the seat that destroyed the heart (-1 if unknown); the heart tile
    //! is the centre tile of the destroyed heart (-1/-1 if unknown).
    void startDefeatSequence(int32_t conquerorSeatId, int32_t heartTileX, int32_t heartTileY);

    //! \brief Called once when the defeat sequence has run to its end (the screen is black).
    //! Opens the debriefing window on the black screen.
    void onDefeatSequenceFinished();

    //! \brief Shows the victory result after the server saved campaign progress.
    void showCampaignVictory(const std::string& goalsDisplay);

    //! \brief Returns to the campaign map after the player acknowledges victory.
    bool onClickCampaignVictoryConfirm(const CEGUI::EventArgs&);

    //! \brief Shows/hides/toggles the options window
    bool showOptionsWindow(const CEGUI::EventArgs& = {});
    bool hideOptionsWindow(const CEGUI::EventArgs& = {});
    bool toggleOptionsWindow(const CEGUI::EventArgs& = {});
    bool closeOptionsWindow(const CEGUI::EventArgs& = {});
    bool showEndGameFromOptions(const CEGUI::EventArgs& = {});
    void setOptionsPage(bool endGame);
    bool toggleControlPanel(const CEGUI::EventArgs& = {});

    void toggleAllowTileDebugWindow(){ showTileDebugWindow = !showTileDebugWindow ;};
    //! \brief Refreshes the player current goals.
    void refreshPlayerGoals(const std::string& goalsDisplayString);

    //! \brief Refreshed the main ui data, such as mana, gold, ...
    void refreshMainUI();
    //! \brief Passes the latest creature counts received from the server to the creature panel
    void refreshCreaturePanel(const CreaturePanelData& data);

    void selectSquaredTiles(int tileX1, int tileY1, int tileX2, int tileY2) override;
    void selectTiles(const std::vector<Tile*> tiles) override;
    void unselectAllTiles() override;

    void displayText(const Ogre::ColourValue& txtColour, const std::string& txt) override;
    void displayPointerText(const Ogre::ColourValue& txtColour, const std::string& txt) override;

    //! \brief Called when the skill window is displayed. This function will call the Seat to get
    //! the current skill tree and update it as the player clicks on the skill buttons by calling
    //! skillButtonTreeClicked
    void resetSkillTree();
    //! \brief Called when the player clicks a skill in the skill tree. Note that resetSkillTree
    //! should be called before calling skillButtonTreeClicked
    //! Returns true if the pending list have been changed and false otherwise
    bool skillButtonTreeClicked(SkillType type);
    //! \brief Called when the player closes the skill tree. If apply is true, the changes
    //! should be sent to the server. If false, the changes should be canceled.
    void endSkillTree(bool apply);

    //! \brief Called at each frame. It checks if the Gui should be refreshed (for example,
    //! if a skill is done) and, if yes, refreshes accordingly.
    //! \param forceRefresh Refresh the gui even if no changes was declared by the local player Seat.
    void refreshGuiSkill(bool forceRefresh = false);

    //! \brief Lays out the research nodes in rows by prerequisite depth and draws the paths
    //! from each prerequisite to the skills that need it, coloured by whether they are done.
    //! Called when the research is refreshed and when the size of the window changes.
    void refreshSkillConnections();

    //! \brief Called at each frame. Updates spell cooldowns.
    void refreshSpellButtonCoolDowns();

    //! \brief Refresh the selected action, target preview and resource/cooldown feedback without executing it.
    void refreshActionFeedback(float elapsed);

    Creature* getClosestCreature(Tile*);

    //! \brief Called on client side when the local player takes control of a creature (possession)
    void notifyPossessionStarted();

    //! \brief Called on client side when the local player is no longer in control of a creature
    void notifyPossessionEnded();

protected:
    bool onClickYesQuitMenu(const CEGUI::EventArgs& /*arg*/);

    //! \brief The different Game Options Menu handlers
    bool showQuitMenuFromOptions(const CEGUI::EventArgs& e = {});
    //! \brief Options menu handler that marks the exit as a level restart (not a quit) and opens the exit confirmation popup
    //! \param e CEGUI event arguments, not used
    //! \return true, the event was handled
    bool showRestartLevelFromOptions(const CEGUI::EventArgs& e = {});
    bool showExitApplicationFromOptions(const CEGUI::EventArgs& e = {});
    bool showObjectivesFromOptions(const CEGUI::EventArgs& e = {});
    bool showSkillFromOptions(const CEGUI::EventArgs& e = {});
    bool saveGame(const CEGUI::EventArgs& e = {});
    //! \brief Opens the saved game browser on top of the running game.
    bool loadGame(const CEGUI::EventArgs& e = {});
    bool showSettingsFromOptions(const CEGUI::EventArgs& e = {});
    void initializeSettingsNavigation();

    //! \brief Handle the keyboard input in normal mode
    virtual bool keyPressedNormal   (const OIS::KeyEvent &arg);

    //! \brief Handle the keyboard input when chat is activated
    virtual bool keyPressedChat     (const OIS::KeyEvent &arg);

    //! \brief Handle the keyboard input in normal mode
    virtual bool keyReleasedNormal  (const OIS::KeyEvent &arg);

private:
    //! \brief The population panel in the creatures tab
    std::unique_ptr<CreaturePanel> mCreaturePanel;
    std::unique_ptr<SocialWindow> mSocialWindow;
    std::vector<CEGUI::Window*> mHeldCreatureIcons;
    void refreshHeldCreatureIcons();
    //! \brief Label next to the hand showing the width x height of the area being dragged
    CEGUI::Window* mSelectionSizeLabel = nullptr;
    void refreshSelectionSizeLabel();
    bool shouldExpireEventMessages() const override { return false; }
    void showEventMessages();
    void showEventMessage(EventMessage* message, bool raiseWindow);
    void dismissEventMessage(EventMessage* message);
    bool onEventMessagesClicked(const CEGUI::EventArgs& arg);
    void updateEventMessageIndicator(float elapsed);
    struct MessageTab
    {
        EventMessage* message;
        CEGUI::Window* window;
        bool read;
        float position;
    };
    std::vector<MessageTab> mMessageTabs;
    EventMessage* mSelectedEventMessage = nullptr;
    float mEventMessageFlashTime = 0.0f;

    //! \brief The saved game browser shown on top of the game, created on first use.
    std::unique_ptr<MenuModeLoad> mLoadMenu;
    //! \brief Whether the pending exit confirmation should leave to the desktop
    //! rather than back to the main menu. Set by the button that opened the
    //! confirmation popup.
    bool mExitToDesktop = false;

    //! \brief Whether the pending confirmation popup restarts the level rather than
    //! leaving the game. Set by the button that opened the confirmation popup.
    bool mRestartLevel = false;
    //! \brief Seconds of the time limit countdown that is shown on the HUD, -1 while it is hidden
    int32_t mTimeLimitShown = -1;
    //! \brief Seconds of the wave countdown that is shown on the HUD, -1 while it is hidden
    int32_t mWaveCountdownShown = -1;

    //! \brief Sets whether a tile must marked or unmarked for digging.
    //! this value is based on the first marked flag tile selected.
    bool mDigSetBool;

    std::string mActionTargetText;
    bool mActionTargetValid = false;
    std::vector<Tile*> mPreviewTiles;
    std::vector<Tile*> mSelectedTiles;

    //! \brief Index of the event in the game event queue (for zooming automatically)
    uint32_t mIndexEvent;

    //! \brief The settings window.
    SettingsWindow mSettings;
    bool mReturningToSettingsNavigation = false;

    //! \brief The level of the heroes taken from the sandbox hero toolbox
    uint32_t mSandboxHeroLevel;
    //! \brief The level file of the next realm offered by the open prompt
    std::string mSandboxNextLevel;
    //! \brief What the sandbox score and room timer of the HUD show, to set the text only on a change
    std::string mSandboxScoreShown;
    std::string mSandboxRoomShown;

    //! \brief Skills pending (Client side). This is copied from the seat for temporary changes while the
    //! player clicks on the skill tree window
    std::vector<SkillType> mSkillPending;
    std::map<SkillType, uint32_t> mSkillEditLevels;

    SkillCurrentCompletion mSkillCurrentCompletion;

    bool mIsSkillWindowOpen;

    //! \brief Whether the spell buttons were last shown locked because the library was lost
    bool mIsLibraryLostShown;

    SkillType mCurrentSkillType;
    float mCurrentSkillProgress;

    //! \brief Seats playing the game
    std::vector<int> mSeatIds;

    MouseMoveEvent mPreviousMousePosition;

    //! \brief Pointer movement in pixels since the middle button was pressed. A middle click that moved
    //! is a camera rotation and must not open a stats window.
    float mMiddleDragDistance;
    float mMiddlePressX;
    float mMiddlePressY;

    //! \brief Opens the stats window of the entity under the pointer (or the tile debug window if enabled)
    void openStatsWindowUnderPointer(const OIS::MouseEvent& arg);

    //! \brief Set the help window (quite long) text.
    void setHelpWindowText();

    //! \brief Picks room floors through walls and uses normal surface picking for other actions.
    //! While dragging, any tile (also a wall) may end the drag so the valid floors inside are built.
    bool findActionTilePositionFromMouse(const OIS::MouseEvent& arg, Ogre::Vector3& position, bool dragging);

    //! \brief A sub-function called by mouseMoved()
    //! It will handle the potential mouse wheel logic
    void handleMouseWheel(const MouseWheelEvent& arg);

    //! \brief Set the state of the given skill button accordingly to the skill type given.
    //! \note: Called by refreshGuiSkill() for each skillType.
    void refreshSkillButtonState(const std::string& skillButton, const std::string& castButton,
        const std::string& skillProgressBar, SkillType resType);

    //! \brief Tells whether the latest mouse click was made on a relevant CEGUI widget,
    //! and thus, the game should ignore it.
    bool isMouseDownOnCEGUIWindow();
    bool isMouseWheelOnCEGUIWindow();

    //! \brief Reads the held camera keys and the mouse position (edge scrolling) once per frame
    //! and hands them to the camera. Adjusts the user view while the user camera window is open.
    void updateCameraControls(float elapsed) override;

    //! \brief Opens the window to define a user camera.
    bool showUserCameras(const CEGUI::EventArgs& = {});

    //! \brief Closes the window to define a user camera.
    bool closeUserCameras(const CEGUI::EventArgs& = {});

    //! \brief Selects the user camera whose button was clicked and shows its stored view.
    bool selectUserCamera(const CEGUI::EventArgs&);

    //! \brief Stores the current view in the selected user camera.
    bool storeUserCamera(const CEGUI::EventArgs&);
    //! \brief The player pressed the button of a stored special: asks the server to use it
    bool useSpecial(const CEGUI::EventArgs& args);
    //! \brief Shows the buttons of the specials the local player has stored
    void refreshSpecialButtons();
    //! \brief The number of stored specials the buttons show, indexed by gift box type
    std::vector<uint32_t> mSpecialCountsShown;
    //! \brief The user camera (0 to 2) the window to define user cameras edits.
    unsigned int mUserCameraSlot = 0;

    //! Restarts the inactivity timer and stops a running idle hand effect; called on every input event.
    void resetIdleHand();
    //! Counts inactivity while the hand may idle (when eligible is true) and starts an idle hand effect once
    //! the delay has passed; held keys and ineligible frames reset the timer.
    void updateIdleHand(float elapsed, bool eligible);
    //! Seconds since the last input while the hand was eligible to idle.
    float mIdleHandElapsed = 0.0f;
    //! Keys currently held down, so that a held key counts as input even without repeat events.
    std::set<OIS::KeyCode> mIdleHandKeys;

    //! \brief Closes every open GUI layer, topmost first.
    void closeAllTopWindows();
    bool showTrapProductionQueue(const CEGUI::EventArgs& = {});
    bool closeTrapProductionQueue(const CEGUI::EventArgs& = {});
    //! \brief Enables the move buttons according to the selected order.
    bool updateTrapProductionButtons(const CEGUI::EventArgs& = {});
    //! \brief Asks the server to move the selected order one place earlier or later.
    bool moveTrapProductionOrder(bool earlier);
    //! \brief Button handlers: ask the server to move the selected order before or after its neighbour.
    bool moveTrapProductionOrderEarlier(const CEGUI::EventArgs&);
    bool moveTrapProductionOrderLater(const CEGUI::EventArgs&);
    //! \brief Asks the server for the production data, unless a request is still open.
    void requestTrapProductionQueue();
    //! The last data received from the server. The ids of the list items in the window
    //! are indices into mTrapProductionData.orders.
    TrapProductionData mTrapProductionData;
    //! Seconds since the last request while the production window is open.
    float mProductionRefreshElapsed = 0.0f;
    //! True from sending a request until the server answer is shown.
    bool mProductionRequestPending = false;

    //! \brief Opens the full map window, or closes it when it is already open.
    bool toggleMap(const CEGUI::EventArgs& = {});
    //! \brief Closes the full map window and restores the regular minimap.
    bool closeMap(const CEGUI::EventArgs& = {});
    //! \brief Left click on the full map moves the camera there, right click closes the map.
    bool clickMap(const CEGUI::EventArgs&);
    //! \brief Left click on the minimap zoom button zooms in, right click zooms out.
    bool zoomMiniMap(const CEGUI::EventArgs&);
    bool clickHeartBadge(const CEGUI::EventArgs&);
    //! \brief Sets the tooltip of the time limit display: a script countdown or a time limit
    void updateTimeLimitTooltip(bool isCountdown);
    //! \brief Shows a detail view of the map area under the mouse cursor while the full map is open.
    void updateMapDetail();
    //! \brief Moves the camera to a room of the given type owned by the local player.
    void focusRoom(RoomType type);
    //! \brief The full map shown while the map window is open, nullptr otherwise.
    std::unique_ptr<MiniMapDrawnFull> mFullMap;
    //! \brief Zoom level of the minimap before the map window was opened.
    int mSavedMiniMapZoom = 0;
    std::map<RoomType, size_t> mRoomFocusIndices;
    //! \brief True while the map key is held, so that key repeat does not toggle the map again.
    bool mMapKeyDown = false;


    //! \brief Tile of the casino whose payout window is open and the payout level shown
    int mCasinoX;
    int mCasinoY;
    uint32_t mCasinoPayout;

    //! \brief whether to allow showing the window with debug Tile info under middlemouse button click
    bool showTileDebugWindow;
    
    const ConfigManager &config;
    
    //! \brief Whether the local player controls a creature (possession)
    bool isLocalPlayerPossessing();

    //! \brief Handles a key press or release while the player controls a creature. Returns
    //! true if the key was used and should not be handled as a normal game key.
    bool handlePossessionKey(OIS::KeyCode key, bool pressed);

    //! \brief Called at each frame while possessing. Sends the walk direction to the server
    //! when it changed.
    void updatePossessionInput(float timeSinceLastFrame);

    //! \brief The direction the possessed creature looks at (unit vector on the ground plane)
    Ogre::Vector2 getPossessionAim();

    //! \brief Sends the possession attack request (left mouse button) to the server
    void sendPossessionAttack();

    //! \brief Sends the request to use the creature skill of the given slot (keys 1 to 4)
    void sendPossessionSkill(uint32_t slot);

    //! \brief Sends the possession exit request to the server
    void sendPossessionExit();

    //! \brief The movement keys held down while possessing
    bool mPossessKeyForward = false;
    bool mPossessKeyBackward = false;
    bool mPossessKeyLeft = false;
    bool mPossessKeyRight = false;

    //! \brief The last walk direction sent to the server while possessing and the time since it was sent
    Ogre::Vector2 mPossessLastDirection = Ogre::Vector2::ZERO;
    float mPossessTimeSinceSent = 0.0f;

    //! \brief Called when there is a mouse input change
    void checkInputCommand();
    void handlePlayerActionNone();
    void handlePlayerActionSelectTile();
    //! \brief Button handler: switches the query mode (SelectedAction::queryEntity) on or off.
    //! While it is on, the next click shows information about the pointed entity instead of
    //! selecting tiles. Does nothing when not connected or while the game is paused.
    bool toggleQuery(const CEGUI::EventArgs& e);
    //! \brief Returns the entity on the given tile that can show a stats window and is nearest to
    //! the keeper hand position, or nullptr if there is none (or the tile is null).
    //! Used by the query mode and by the middle mouse button.
    GameEntity* getQueryTarget(Tile* tile) const;
    //! \brief Handles the query mode in checkInputCommand(): shows the name of the entity under the
    //! pointer and, once the click is validated, opens its stats window.
    void handlePlayerActionQuery();
    bool toggleSell(const CEGUI::EventArgs& e);
    void handlePlayerActionSell();
    //! \brief Draws eligible selection borders without including invalid room tiles.
    void updateSelectedTiles();

    //! \brief Asks the server to drop the pending hand entity on the pending tile or, if
    //! dropAllCreatures is set and every held creature can be dropped there, all held
    //! creatures at once. Falls back to the plain action when no request can be sent.
    void sendPendingHandDropRequest(bool dropAllCreatures);
    //! True while the right mouse button is held after a drop was started. The drop is
    //! sent on release, or for all creatures once the button is held long enough.
    bool mPendingHandDrop = false;
    //! Seconds the right mouse button has been held for the pending drop.
    float mPendingHandDropTime = 0.0f;
    //! Tile coordinates of the pending drop.
    int mPendingHandDropX = -1;
    int mPendingHandDropY = -1;
    //! Type (as GameEntityType) and name of the first held entity when the drop started.
    int32_t mPendingHandDropEntityType = 0;
    std::string mPendingHandDropEntityName;

    //! \brief Builds the player settings window
    void buildPlayerSettingsWindow();

    //! \brief Tracks the Alt keys and toggles the creature indicators on each new Alt press.
    //! Key repeats and overlapping left/right Alt presses count as one held interval.
    void updateCreatureIndicatorAlt(OIS::KeyCode key, bool pressed);
    //! \brief Whether the health and need indicators above the creatures are shown
    bool mCreatureIndicatorsVisible = true;
    //! \brief Whether the left Alt key is currently held, as far as the indicator toggle knows
    bool mIndicatorLeftAltDown = false;
    //! \brief Whether the right Alt key is currently held, as far as the indicator toggle knows
    bool mIndicatorRightAltDown = false;

    //! \brief Brings the defeat sequence to the wall-clock time now (does nothing before it starts)
    void updateDefeatSequence(std::chrono::steady_clock::time_point now);
    //! \brief Puts the camera on a low oblique view of the given floor position without a flight
    void cutCameraToHeart(const Ogre::Vector3& heartPosition);
    void createDefeatWindows();
    void destroyDefeatWindows();
    //! \brief Loads the defeat or campaign victory result (summary lines and confirm button) and shows the pointer.
    void showDefeatDebriefing();
    //! Fills the hidden statistics area of the debriefing with the rows and shows it (nothing for no rows)
    void fillDefeatStatistics(const std::vector<DebriefingTableRow>& rows);
    //! The confirm button of the debriefing: leaves to the main menu with the skirmish sub-menu open
    bool onClickDefeatDebriefingConfirm(const CEGUI::EventArgs& arg);
    //! \brief Hides every window of the game interface except the ones of the defeat sequence
    void hideInterfaceForDefeat();
    void startDefeatSwirl();
    //! The copy of the heart bursts: it is removed, the burst effects start (unless time is already past the
    //! explosion phase) and the rubble is created
    void startDefeatBurst(float time);
    //! Removes every scene object of the sequence (effects, copy of the heart, rubble); safe to call again
    void stopDefeatEffects();

    DefeatSequence mDefeatSequence;
    //! Position of the destroyed heart in the scene
    Ogre::Vector3 mDefeatHeartPosition = Ogre::Vector3::ZERO;
    //! Direction (horizontal, unit length) in which the swirl travels
    Ogre::Vector3 mDefeatSwirlDirection = Ogre::Vector3::ZERO;
    bool mDefeatExplosionEffectActive = false;
    bool mDefeatSwirlEffectActive = false;
    bool mDefeatSwirlDone = false;
    //! The client-only copy of the heart exists (from the start until the burst)
    bool mDefeatHeartShown = false;
    bool mDefeatBurstDone = false;
    //! The rubble exists (from the burst until the end of the sequence)
    bool mDefeatRubbleShown = false;
    std::vector<DefeatRubblePiece> mDefeatRubble;
    CEGUI::Window* mDefeatTint = nullptr;
    CEGUI::Window* mDefeatFade = nullptr;
    CEGUI::Window* mDefeatSubtitle = nullptr;
    CEGUI::Window* mDefeatCameraMarker = nullptr;
    CEGUI::Window* mDefeatDebriefing = nullptr;

};

#endif // GAMEMODE_H
