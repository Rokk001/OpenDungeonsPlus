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

#ifndef INPUTMANAGER_H
#define INPUTMANAGER_H

#include <OgreVector.h>
#include <OgreSingleton.h>
#include <OISMouse.h>
#include "modes/WheelAccumulator.h"

#include <memory>


#include "modes/Keyboard.h"

namespace OIS
{
    class InputManager;
    class Keyboard;
    class Mouse;
}

namespace Ogre
{
    class RenderWindow;
}

namespace sf
{
    class Event;
}

class AbstractApplicationMode;
class SFMLToOISListener;

enum class InputCommandState
{
    infoOnly, // When the player is only moving mouse (but not building)
    building, // When the player is building (but has not validated he build)
    validated, // When the player is happy with the build and wants to build
};

enum class SelectionEntityWanted;

class Creature;

class InputManager: public Ogre::Singleton<InputManager>
{
public:

    struct PosWithOrient
    {
        Ogre::Vector3 vv;
        Ogre::Quaternion qq;
        Ogre::Quaternion qq2;
    };

    
    InputManager(Ogre::RenderWindow* renderWindow);
    ~InputManager();

    void setWidthAndHeight(int width, int height);
    //! \brief Moves the system cursor, the OIS mouse state and the GUI cursor to the given
    //! window position (clamped to the window) and drops motion accumulated before the call.
    void setMousePosition(int x, int y);
    void setCurrentAMode(AbstractApplicationMode& mode);
    //! \brief Captures the mouse. On Windows (OIS/DirectInput) the game pointer is the position of the
    //! Windows pointer inside the game window (1:1, also over remote desktop) and no mouse input is
    //! processed while the window is not in the foreground. Elsewhere it only captures the OIS mouse.
    void capturePointer();
    void handleSFMLEvent(const sf::Event& evt);
    //! \brief Recreates the input devices if the mouse or keyboard capture setting changed.
    //! Must not be called from an input callback.
    void refreshSettings();
    //! \brief Moves the input devices to another render window. Returns false (and keeps the old window)
    //! if the devices could not be created for the new one.
    bool setRenderWindow(Ogre::RenderWindow* renderWindow);

    OIS::InputManager*  mInputManager;


    bool                mHotkeyLocationIsValid[10];
    PosWithOrient       mHotkeyLocation[10];
    std::unique_ptr<Keyboard>           mKeyboard;

    //! \brief mouse handling related member
    bool                mLMouseDown, mRMouseDown, mMMouseDown;
    bool                mMouseDownOnCEGUIWindow;

    bool                mMouseDownOnDraggableTileContainer;
    Ogre::Vector3       mKeeperHandPos;
    Ogre::Vector3       mKeeperHandPosOverBlock;
    int                 mXPos, mYPos;
    int                 mLStartDragX, mLStartDragY;
    int                 mRStartDragX, mRStartDragY;
    //! \brief In editor mode, it contains the selected seat Id. In gamemode, it is not used
    int                 mSeatIdSelected;
    Ogre::Vector2       offsetDraggableTileContainer;
    InputCommandState   mCommandState;
    OIS::Mouse*         mMouse;
    Creature*           mHighlightedCreature;
    SelectionEntityWanted mCreatureTypeForOutliner;

    
    private:
    AbstractApplicationMode* mCurrentAMode;
    //! \brief The render window the input devices are bound to
    Ogre::RenderWindow* mRenderWindow;
    //! \brief Whether the input devices were created with mouse capture
    bool mMouseGrab;
    //! \brief Whether the input devices were created with keyboard capture
    bool mKeyboardGrab;
    //! \brief Creates the mouse and keyboard for mRenderWindow
    void createInputDevices(bool mouseGrab, bool keyboardGrab);
    //! \brief Destroys the mouse and keyboard; safe to call when they do not exist
    void destroyInputDevices();
#if defined OIS_WIN32_PLATFORM && !defined OD_USE_SFML_WINDOW
    //! \brief Hands the OIS mouse events to the current mode with the position of the Windows pointer
    class PointerForwarder: public OIS::MouseListener
    {
    public:
        PointerForwarder(InputManager& inputManager): mInputManager(inputManager) {}
        virtual bool mouseMoved(const OIS::MouseEvent& arg) override;
        virtual bool mousePressed(const OIS::MouseEvent& arg, OIS::MouseButtonID id) override;
        virtual bool mouseReleased(const OIS::MouseEvent& arg, OIS::MouseButtonID id) override;
    private:
        InputManager& mInputManager;
    };
    friend class PointerForwarder;
    //! \brief Reads the Windows pointer as game pointer position. Returns false if not possible.
    bool readSystemPointer(int& x, int& y, bool& inside);
    //! \brief Writes the game pointer position to the OIS state and the GUI
    void applyPointerToState(int x, int y);
    //! \brief Clips and hides the Windows pointer (mouse grab) or frees it
    void updateCursorGrab(bool grab);
    //! \brief Moves the Windows pointer to the given game pointer position (clamped)
    void moveSystemPointer(int x, int y);
    PointerForwarder mPointerForwarder;
    bool mWasForeground;
    bool mCursorHidden;
    bool mCursorClipped;
    //! \brief Position set by the game while the window was in the background
    bool mHasPendingPosition;
    int mPendingX, mPendingY;
    int mLastPointerX, mLastPointerY;
    //! rief Wheel movement taken from the window messages (see WheelAccumulator)
    WheelAccumulator mWheel;
    //! rief Window procedure that was replaced to see the wheel messages, and its window
    void* mOldWindowProc = nullptr;
    void* mHookedWindow = nullptr;
    void hookWindowWheel();
    void unhookWindowWheel();
    static void* sWheelOwner;
    static long long __stdcall wheelWindowProc(void* window, unsigned int message, unsigned long long wParam, long long lParam);
#endif
#ifdef OD_USE_SFML_WINDOW
    std::unique_ptr<SFMLToOISListener> mListener;
#endif
};

#endif // INPUTMANAGER_H
