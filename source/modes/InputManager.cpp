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

#include "InputManager.h"

#include "gamemap/SelectionEntityWanted.h"
#include "modes/AbstractApplicationMode.h"
#include "modes/PointerMapping.h"
#include "render/Gui.h"
#include "modes/SFMLToOISListener.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"

#include <OISMouse.h>
#include <OISKeyboard.h>

#include <OISInputManager.h>
#include <OgreRenderWindow.h>
#include <CEGUI/System.h>
#include <CEGUI/GUIContext.h>
#include <algorithm>
#include <exception>

#if defined OIS_WIN32_PLATFORM && !defined OD_USE_SFML_WINDOW
#include <windows.h>
#endif

InputManager::InputManager(Ogre::RenderWindow* renderWindow):
    mInputManager(nullptr),
    mKeyboard(nullptr),
    mLMouseDown(false),
    mRMouseDown(false),
    mMMouseDown(false),
    mMouseDownOnCEGUIWindow(false),
    mMouseDownOnDraggableTileContainer(false),
    mKeeperHandPos(Ogre::Vector3::ZERO),
    mKeeperHandPosOverBlock(Ogre::Vector3::ZERO),   
    mXPos(0),
    mYPos(0),
    mLStartDragX(0),
    mLStartDragY(0),
    mRStartDragX(0),
    mRStartDragY(0),
    mSeatIdSelected(0),
    offsetDraggableTileContainer(Ogre::Vector2(Ogre::Vector2::ZERO)),
    mCommandState(InputCommandState::infoOnly),
    mMouse(nullptr),
    mCurrentAMode(nullptr),
    mHighlightedCreature(nullptr),
    mCreatureTypeForOutliner(SelectionEntityWanted::creatureAliveAllied),
    mRenderWindow(renderWindow),
    mMouseGrab(false),
    mKeyboardGrab(false)
#if defined OIS_WIN32_PLATFORM && !defined OD_USE_SFML_WINDOW
    ,
    mPointerForwarder(*this),
    mWasForeground(true),
    mCursorHidden(false),
    mCursorClipped(false),
    mHasPendingPosition(false),
    mPendingX(0),
    mPendingY(0),
    mLastPointerX(0),
    mLastPointerY(0)
#endif
#ifdef OD_USE_SFML_WINDOW
    ,
    mListener(Utils::make_unique<SFMLToOISListener>(mCurrentAMode, renderWindow->getWidth(), renderWindow->getHeight()))
#endif
{
    OD_LOG_INF("*** Initializing OIS - Input Manager ***");

    for (int i = 0; i < 10; ++i)
    {
        mHotkeyLocationIsValid[i] = false;
        mHotkeyLocation[i].vv = Ogre::Vector3::ZERO;
        mHotkeyLocation[i].qq = Ogre::Quaternion::IDENTITY;
    }

    ConfigManager& config = ConfigManager::getSingleton();
    createInputDevices(config.getInputValue(Config::MOUSE_GRAB, "No", false) == "Yes",
                       config.getInputValue(Config::KEYBOARD_GRAB, "No", false) == "Yes");
}

void InputManager::createInputDevices(bool mouseGrab, bool keyboardGrab)
{
#ifndef OD_USE_SFML_WINDOW

    // Get the Window attribute for OIS.
    size_t windowHnd = 0;
    mRenderWindow->getCustomAttribute("WINDOW", &windowHnd);
    std::ostringstream windowHndStr;
    windowHndStr << windowHnd;

    //setup parameter list for OIS
    OIS::ParamList paramList;
    paramList.insert(std::make_pair(std::string("WINDOW"), windowHndStr.str()));
#if defined OIS_WIN32_PLATFORM
    paramList.insert(std::make_pair(std::string("w32_mouse"), std::string("DISCL_FOREGROUND" )));
    // The pointer position is the Windows pointer position, so the mouse is never exclusive.
    // Mouse grab is done by clipping and hiding the Windows pointer (see updateCursorGrab).
    paramList.insert(std::make_pair(std::string("w32_mouse"), std::string("DISCL_NONEXCLUSIVE")));
    paramList.insert(std::make_pair(std::string("w32_keyboard"), std::string("DISCL_FOREGROUND")));
    paramList.insert(std::make_pair(std::string("w32_keyboard"), std::string(keyboardGrab ? "DISCL_EXCLUSIVE" : "DISCL_NONEXCLUSIVE")));
#elif defined OIS_LINUX_PLATFORM
    paramList.insert(std::make_pair(std::string("x11_mouse_grab"), std::string(mouseGrab ? "true" : "false")));
    // When grabbing, OIS tracks the pointer by accumulating relative motion and warps
    // the real pointer back to the window centre near the edges. Leaving the system
    // cursor visible then shows it drifting away from the one CEGUI draws, so hide it.
    paramList.insert(std::make_pair(std::string("x11_mouse_hide"), std::string(mouseGrab ? "true" : "false")));
    paramList.insert(std::make_pair(std::string("x11_keyboard_grab"), std::string(keyboardGrab ? "true" : "false")));
    paramList.insert(std::make_pair(std::string("XAutoRepeatOn"), std::string("true")));
#endif

    //setup InputManager
    mInputManager = OIS::InputManager::createInputSystem(paramList);

    //setup Keyboard
    OIS::Keyboard* oisKeyboard = static_cast<OIS::Keyboard*>(mInputManager->createInputObject(OIS::OISKeyboard, true));

    oisKeyboard->setTextTranslation(OIS::Keyboard::Unicode);

    mKeyboard.reset(new Keyboard(oisKeyboard));

    //setup Mouse
    mMouse = static_cast<OIS::Mouse*>(mInputManager->createInputObject(OIS::OISMouse, true));
#if defined OIS_WIN32_PLATFORM
    hookWindowWheel();
#endif
#else
    mKeyboard.reset(new Keyboard());
#endif
    mMouseGrab = mouseGrab;
    mKeyboardGrab = keyboardGrab;
    setWidthAndHeight(mRenderWindow->getWidth(), mRenderWindow->getHeight());
    if(mCurrentAMode != nullptr)
        setCurrentAMode(*mCurrentAMode);
}

template<> InputManager* Ogre::Singleton<InputManager>::msSingleton = nullptr;


InputManager::~InputManager()
{
    OD_LOG_INF("*** Destroying Input Manager ***");
    destroyInputDevices();
}

void InputManager::destroyInputDevices()
{
#ifndef OD_USE_SFML_WINDOW
#if defined OIS_WIN32_PLATFORM
    updateCursorGrab(false);
    unhookWindowWheel();
#endif
    if(mInputManager != nullptr)
    {
        if(mMouse != nullptr)
            mInputManager->destroyInputObject(mMouse);
        if(mKeyboard != nullptr)
            mInputManager->destroyInputObject(mKeyboard->getKeyboard());
        OIS::InputManager::destroyInputSystem(mInputManager);
    }
    mInputManager = nullptr;
    mMouse = nullptr;
#endif
    mKeyboard.reset();
}

void InputManager::refreshSettings()
{
    // Called before capturing input, never from inside an OIS callback.
    ConfigManager& config = ConfigManager::getSingleton();
    const bool mouseGrab = config.getInputValue(Config::MOUSE_GRAB, "No", false) == "Yes";
    const bool keyboardGrab = config.getInputValue(Config::KEYBOARD_GRAB, "No", false) == "Yes";
    if(mouseGrab == mMouseGrab && keyboardGrab == mKeyboardGrab)
        return;

    const bool previousMouseGrab = mMouseGrab;
    const bool previousKeyboardGrab = mKeyboardGrab;
    destroyInputDevices();
    try
    {
        createInputDevices(mouseGrab, keyboardGrab);
    }
    catch(const std::exception& error)
    {
        OD_LOG_ERR("Could not apply input capture settings: " + std::string(error.what()));
        destroyInputDevices();
        config.setInputValue(Config::MOUSE_GRAB, previousMouseGrab ? "Yes" : "No");
        config.setInputValue(Config::KEYBOARD_GRAB, previousKeyboardGrab ? "Yes" : "No");
        config.saveUserConfig();
        createInputDevices(previousMouseGrab, previousKeyboardGrab);
    }
    mLMouseDown = mRMouseDown = mMMouseDown = false;
}

bool InputManager::setRenderWindow(Ogre::RenderWindow* renderWindow)
{
    if(renderWindow == mRenderWindow)
        return true;

#ifdef OD_USE_SFML_WINDOW
    return false;
#else
    Ogre::RenderWindow* previousWindow = mRenderWindow;
    destroyInputDevices();
    mRenderWindow = renderWindow;
    try
    {
        createInputDevices(mMouseGrab, mKeyboardGrab);
    }
    catch(const std::exception& error)
    {
        OD_LOG_ERR("Could not move input to the new render window: " + std::string(error.what()));
        destroyInputDevices();
        mRenderWindow = previousWindow;
        createInputDevices(mMouseGrab, mKeyboardGrab);
        return false;
    }
    mLMouseDown = mRMouseDown = mMMouseDown = false;
    return true;
#endif
}

void InputManager::setWidthAndHeight(int width, int height)
{
#ifndef OD_USE_SFML_WINDOW
    const OIS::MouseState& ms = mMouse->getMouseState();
    ms.width = width;
    ms.height = height;
#endif
}

void InputManager::setMousePosition(int x, int y)
{
#ifndef OD_USE_SFML_WINDOW
    if(mMouse == nullptr)
        return;

    OIS::MouseState& state = const_cast<OIS::MouseState&>(mMouse->getMouseState());
    x = (std::max)(0, (std::min)(x, state.width - 1));
    y = (std::max)(0, (std::min)(y, state.height - 1));
#if defined OIS_WIN32_PLATFORM
    size_t windowHandle = 0;
    mRenderWindow->getCustomAttribute("WINDOW", &windowHandle);
    const HWND window = reinterpret_cast<HWND>(windowHandle);
    if(GetForegroundWindow() == window)
    {
        moveSystemPointer(x, y);
        mHasPendingPosition = false;
    }
    else
    {
        // A position set in the background wins when the window returns to the foreground
        mHasPendingPosition = true;
        mPendingX = x;
        mPendingY = y;
    }
    mLastPointerX = x;
    mLastPointerY = y;
#else
    if(!mMouseGrab)
        return;
#endif
    // Discard motion accumulated during loading without dispatching input.
    OIS::MouseListener* listener = mMouse->getEventCallback();
    mMouse->setEventCallback(nullptr);
    mMouse->capture();
    mMouse->setEventCallback(listener);
    state.X.abs = x;
    state.Y.abs = y;
    state.X.rel = state.Y.rel = state.Z.rel = 0;
    CEGUI::System::getSingleton().getDefaultGUIContext().injectMousePosition(
        static_cast<float>(x), static_cast<float>(y));
#endif
}

void InputManager::setCurrentAMode(AbstractApplicationMode& mode)
{
    mCurrentAMode = &mode;
#ifndef OD_USE_SFML_WINDOW
#if defined OIS_WIN32_PLATFORM
    mMouse->setEventCallback(&mPointerForwarder);
#else
    mMouse->setEventCallback(&mode);
#endif
    mKeyboard->getKeyboard()->setEventCallback(&mode);
#else
    mListener->setReceiver(&mode);
#endif
}

void InputManager::handleSFMLEvent(const sf::Event& evt)
{
#ifdef OD_USE_SFML_WINDOW
    mListener->handleEvent(evt);
#else
    OD_LOG_ERR("TRIED TO USE SFML EVENTS BUT THEY ARE DISABLED!");
#endif
}

void InputManager::capturePointer()
{
#if defined OIS_WIN32_PLATFORM && !defined OD_USE_SFML_WINDOW
    if(mMouse == nullptr)
        return;

    size_t windowHandle = 0;
    mRenderWindow->getCustomAttribute("WINDOW", &windowHandle);
    const HWND window = reinterpret_cast<HWND>(windowHandle);
    const bool foreground = (window != nullptr) && (GetForegroundWindow() == window) && !IsIconic(window);
    OIS::MouseListener* listener = mMouse->getEventCallback();

    if(!foreground)
    {
        // No mouse input while the window is not in the foreground, the pointer is free
        if(mWasForeground)
        {
            updateCursorGrab(false);
            mLMouseDown = mRMouseDown = mMMouseDown = false;
            mWasForeground = false;
        }
        mMouse->setEventCallback(nullptr);
        mMouse->capture();
        mMouse->setEventCallback(listener);
        mWheel.clear();
        return;
    }

    if(!mWasForeground)
    {
        // Back in the foreground: drop the input of the background, then follow the Windows pointer at once
        mWasForeground = true;
        mWheel.clear();
        mMouse->setEventCallback(nullptr);
        mMouse->capture();
        mMouse->setEventCallback(listener);
        if(mHasPendingPosition)
        {
            moveSystemPointer(mPendingX, mPendingY);
            mHasPendingPosition = false;
        }
        int returnX = 0;
        int returnY = 0;
        bool returnInside = true;
        if(readSystemPointer(returnX, returnY, returnInside))
        {
            // Outside the window: bring the Windows pointer to the nearest point inside
            if(!returnInside)
                moveSystemPointer(returnX, returnY);
            mLastPointerX = returnX;
            mLastPointerY = returnY;
            applyPointerToState(returnX, returnY);
            // Input dropped above must not show up as motion or wheel
            OIS::MouseState& returnState = const_cast<OIS::MouseState&>(mMouse->getMouseState());
            returnState.X.rel = returnState.Y.rel = returnState.Z.rel = 0;
            if(mCurrentAMode != nullptr)
                mCurrentAMode->mouseMoved(OIS::MouseEvent(mMouse, returnState));
        }
    }

    updateCursorGrab(mMouseGrab);
    mMouse->capture();

    // The pointer can move without OIS reporting it (remote desktop), follow the Windows pointer anyway
    int x = 0;
    int y = 0;
    bool inside = true;
    if(readSystemPointer(x, y, inside) && (x != mLastPointerX || y != mLastPointerY))
    {
        mLastPointerX = x;
        mLastPointerY = y;
        applyPointerToState(x, y);
        OIS::MouseState& state = const_cast<OIS::MouseState&>(mMouse->getMouseState());
        state.X.rel = state.Y.rel = state.Z.rel = 0;
        if(mCurrentAMode != nullptr)
            mCurrentAMode->mouseMoved(OIS::MouseEvent(mMouse, state));
    }

    // The wheel, one event per frame with the collected movement (OIS units, 120 per notch)
    const int wheel = mWheel.take();
    if(wheel != 0 && mCurrentAMode != nullptr)
    {
        if(readSystemPointer(x, y, inside))
        {
            mLastPointerX = x;
            mLastPointerY = y;
            applyPointerToState(x, y);
        }
        OIS::MouseState& state = const_cast<OIS::MouseState&>(mMouse->getMouseState());
        state.X.rel = state.Y.rel = 0;
        state.Z.rel = wheel;
        mCurrentAMode->mouseMoved(OIS::MouseEvent(mMouse, state));
        state.Z.rel = 0;
    }
#else
    if(mMouse != nullptr)
        mMouse->capture();
#endif
}

#if defined OIS_WIN32_PLATFORM && !defined OD_USE_SFML_WINDOW
bool InputManager::PointerForwarder::mouseMoved(const OIS::MouseEvent& arg)
{
    if(mInputManager.mCurrentAMode == nullptr)
        return true;
    // The wheel comes from the window messages (see capturePointer); the DirectInput wheel is dropped
    const_cast<OIS::MouseState&>(arg.state).Z.rel = 0;
    int x = 0;
    int y = 0;
    bool inside = true;
    if(mInputManager.readSystemPointer(x, y, inside))
    {
        mInputManager.mLastPointerX = x;
        mInputManager.mLastPointerY = y;
        mInputManager.applyPointerToState(x, y);
    }
    return mInputManager.mCurrentAMode->mouseMoved(arg);
}

bool InputManager::PointerForwarder::mousePressed(const OIS::MouseEvent& arg, OIS::MouseButtonID id)
{
    if(mInputManager.mCurrentAMode == nullptr)
        return true;
    int x = 0;
    int y = 0;
    bool inside = true;
    if(mInputManager.readSystemPointer(x, y, inside))
    {
        mInputManager.mLastPointerX = x;
        mInputManager.mLastPointerY = y;
        mInputManager.applyPointerToState(x, y);
    }
    return mInputManager.mCurrentAMode->mousePressed(arg, id);
}

bool InputManager::PointerForwarder::mouseReleased(const OIS::MouseEvent& arg, OIS::MouseButtonID id)
{
    if(mInputManager.mCurrentAMode == nullptr)
        return true;
    int x = 0;
    int y = 0;
    bool inside = true;
    if(mInputManager.readSystemPointer(x, y, inside))
    {
        mInputManager.mLastPointerX = x;
        mInputManager.mLastPointerY = y;
        mInputManager.applyPointerToState(x, y);
    }
    return mInputManager.mCurrentAMode->mouseReleased(arg, id);
}

bool InputManager::readSystemPointer(int& x, int& y, bool& inside)
{
    size_t windowHandle = 0;
    mRenderWindow->getCustomAttribute("WINDOW", &windowHandle);
    const HWND window = reinterpret_cast<HWND>(windowHandle);
    POINT point;
    RECT client;
    if(window == nullptr || !GetCursorPos(&point) || !ScreenToClient(window, &point) || !GetClientRect(window, &client))
        return false;

    const int clientWidth = client.right - client.left;
    const int clientHeight = client.bottom - client.top;
    inside = point.x >= 0 && point.y >= 0 && point.x < clientWidth && point.y < clientHeight;
    // The UI scale changes the interface size, not the pointer pixels; it is passed for completeness
    const int uiScale = static_cast<int>(Gui::getConfiguredUiScalePercent());
    PointerMapping::Point mapped = PointerMapping::clientToGamePointer(point.x, point.y, clientWidth, clientHeight,
        static_cast<int>(mRenderWindow->getWidth()), static_cast<int>(mRenderWindow->getHeight()), uiScale);
    x = mapped.mX;
    y = mapped.mY;
    return true;
}

void InputManager::applyPointerToState(int x, int y)
{
    OIS::MouseState& state = const_cast<OIS::MouseState&>(mMouse->getMouseState());
    state.X.abs = x;
    state.Y.abs = y;
    CEGUI::System::getSingleton().getDefaultGUIContext().injectMousePosition(
        static_cast<float>(x), static_cast<float>(y));
}

void InputManager::moveSystemPointer(int x, int y)
{
    size_t windowHandle = 0;
    mRenderWindow->getCustomAttribute("WINDOW", &windowHandle);
    const HWND window = reinterpret_cast<HWND>(windowHandle);
    RECT client;
    if(window == nullptr || !GetClientRect(window, &client))
        return;
    const int clientWidth = client.right - client.left;
    const int clientHeight = client.bottom - client.top;
    const int gameWidth = static_cast<int>(mRenderWindow->getWidth());
    const int gameHeight = static_cast<int>(mRenderWindow->getHeight());
    // Game pointer position to client position (inverse of the proportional mapping)
    POINT point;
    point.x = PointerMapping::clampToSize(gameWidth > 0 ? static_cast<int>(static_cast<long long>(x) * clientWidth / gameWidth) : x, clientWidth);
    point.y = PointerMapping::clampToSize(gameHeight > 0 ? static_cast<int>(static_cast<long long>(y) * clientHeight / gameHeight) : y, clientHeight);
    if(ClientToScreen(window, &point))
        SetCursorPos(point.x, point.y);
}

void InputManager::updateCursorGrab(bool grab)
{
    if(grab)
    {
        size_t windowHandle = 0;
        mRenderWindow->getCustomAttribute("WINDOW", &windowHandle);
        const HWND window = reinterpret_cast<HWND>(windowHandle);
        RECT client;
        POINT topLeft = {0, 0};
        if(window != nullptr && GetClientRect(window, &client) && ClientToScreen(window, &topLeft))
        {
            // Re-applied every frame so that it follows resizing and moving of the window
            RECT clip;
            clip.left = topLeft.x;
            clip.top = topLeft.y;
            clip.right = topLeft.x + (client.right - client.left);
            clip.bottom = topLeft.y + (client.bottom - client.top);
            ClipCursor(&clip);
            mCursorClipped = true;
        }
        if(!mCursorHidden)
        {
            ShowCursor(FALSE);
            mCursorHidden = true;
        }
    }
    else
    {
        if(mCursorClipped)
        {
            ClipCursor(nullptr);
            mCursorClipped = false;
        }
        if(mCursorHidden)
        {
            ShowCursor(TRUE);
            mCursorHidden = false;
        }
    }
}

void* InputManager::sWheelOwner = nullptr;

long long __stdcall InputManager::wheelWindowProc(void* window, unsigned int message, unsigned long long wParam, long long lParam)
{
    InputManager* owner = static_cast<InputManager*>(sWheelOwner);
    if(owner == nullptr || owner->mOldWindowProc == nullptr)
        return DefWindowProcW(static_cast<HWND>(window), message, wParam, lParam);
    if(message == WM_MOUSEWHEEL)
    {
        const HWND hwnd = static_cast<HWND>(window);
        owner->mWheel.add(static_cast<int>(GET_WHEEL_DELTA_WPARAM(wParam)),
            GetForegroundWindow() == hwnd && !IsIconic(hwnd));
    }
    return CallWindowProcW(reinterpret_cast<WNDPROC>(owner->mOldWindowProc), static_cast<HWND>(window),
        message, wParam, lParam);
}

void InputManager::hookWindowWheel()
{
    unhookWindowWheel();
    size_t windowHandle = 0;
    mRenderWindow->getCustomAttribute("WINDOW", &windowHandle);
    const HWND window = reinterpret_cast<HWND>(windowHandle);
    if(window == nullptr)
        return;
    mWheel.clear();
    sWheelOwner = this;
    LONG_PTR old = SetWindowLongPtrW(window, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(&InputManager::wheelWindowProc));
    if(old == 0)
    {
        sWheelOwner = nullptr;
        return;
    }
    mOldWindowProc = reinterpret_cast<void*>(old);
    mHookedWindow = window;
}

void InputManager::unhookWindowWheel()
{
    if(mOldWindowProc != nullptr && mHookedWindow != nullptr)
    {
        const HWND window = static_cast<HWND>(mHookedWindow);
        if(IsWindow(window) && GetWindowLongPtrW(window, GWLP_WNDPROC) == reinterpret_cast<LONG_PTR>(&InputManager::wheelWindowProc))
            SetWindowLongPtrW(window, GWLP_WNDPROC, reinterpret_cast<LONG_PTR>(mOldWindowProc));
    }
    if(sWheelOwner == this)
        sWheelOwner = nullptr;
    mOldWindowProc = nullptr;
    mHookedWindow = nullptr;
}
#endif
