"""Exercise production pointer methods with real User32 messages and CEGUI widgets.

OIS/Ogre devices are doubles. Subclassing, message delivery, capture, coordinate
conversion and GUI drag use real libraries. Foreground and pointer sampling have
deterministic seams, avoiding changes to the desktop focus or user's cursor.
"""
import os
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / 'source/modes/InputManager.cpp').read_text(encoding='utf-8')
mode_source = (root / 'source/modes/AbstractApplicationMode.cpp').read_text(encoding='utf-8')


def method(text, signature):
    """Extract a production method intact, including its preprocessor branches."""
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'


preamble = r'''
#define NOMINMAX
#define OIS_WIN32_PLATFORM
#include <windows.h>
#include <algorithm>
#include <cassert>
#include <functional>
#include <iostream>
#include <vector>
#include <CEGUI/System.h>
#include <CEGUI/GUIContext.h>
#include <CEGUI/SystemKeys.h>
#include <CEGUI/MouseCursor.h>
#include <CEGUI/Window.h>
#include <CEGUI/ImageCodec.h>
#include <CEGUI/widgets/FrameWindow.h>
#include <CEGUI/widgets/Titlebar.h>
#include <CEGUI/RendererModules/Null/Renderer.h>
#include "modes/PointerMapping.h"
#define OD_LOG_ERR(message) ((void)0)
static HWND foregroundWindow = nullptr;
static bool failHook = false;
//! Selects foreground deterministically without activating a window.
HWND probeForegroundWindow() { return foregroundWindow; }
//! Forces one hook failure while otherwise using actual subclass installation.
LONG_PTR probeSetWindowLongPtrW(HWND hwnd, int index, LONG_PTR value)
{
    if(failHook) { SetLastError(ERROR_ACCESS_DENIED); return 0; }
    return SetWindowLongPtrW(hwnd, index, value);
}
#define GetForegroundWindow probeForegroundWindow
#define SetWindowLongPtrW probeSetWindowLongPtrW
namespace OIS
{
enum MouseButtonID { MB_Left, MB_Right, MB_Middle, MB_Button3, MB_Button4 };
struct Axis { int abs = 0, rel = 0; };
struct MouseState { Axis X,Y,Z; int buttons = 0; mutable int width = 1000, height = 1000; };
struct Mouse;
struct MouseEvent { MouseEvent(Mouse*, const MouseState& value): state(value) {} const MouseState& state; };
struct MouseListener
{
    virtual bool mouseMoved(const MouseEvent&) = 0;
    virtual bool mousePressed(const MouseEvent&, MouseButtonID) = 0;
    virtual bool mouseReleased(const MouseEvent&, MouseButtonID) = 0;
};
struct Mouse
{
    MouseState state;
    MouseListener* callback = nullptr;
    std::function<void()> captured;
    const MouseState& getMouseState() { return state; }
    MouseListener* getEventCallback() { return callback; }
    void setEventCallback(MouseListener* value) { callback = value; }
    void capture() { if(captured) captured(); }
};
struct Keyboard { void setEventCallback(void*) {} };
}
namespace Gui
{
int getConfiguredUiScalePercent() { return 100; }
CEGUI::MouseButton convertButton(OIS::MouseButtonID button)
{
    const CEGUI::MouseButton buttons[] = {CEGUI::LeftButton, CEGUI::RightButton,
        CEGUI::MiddleButton, CEGUI::X1Button, CEGUI::X2Button};
    return buttons[button];
}
}
enum class InputCommandState { infoOnly, building, validated };
struct InputManager;
struct ModeManager { InputManager* manager = nullptr; InputManager& getInputManager() { return *manager; } };
struct Statistics { void endDrag() {} };
struct ODFrameListener
{
    static ODFrameListener& getSingleton() { static ODFrameListener listener; return listener; }
    Statistics& getFrameStatistics() { return statistics; }
    Statistics statistics;
};
struct AbstractApplicationMode: OIS::MouseListener
{
    struct Record { char kind; int x,y,buttons,wheel,dx,dy; };
    std::vector<Record> records;
    ModeManager manager;
    ModeManager* mModeManager = &manager;
    std::function<void()> pressed;
    bool mouseMoved(const OIS::MouseEvent& event)
    {
        records.push_back({'m',event.state.X.abs,event.state.Y.abs,event.state.buttons,event.state.Z.rel,event.state.X.rel,event.state.Y.rel});
        CEGUI::GUIContext& context = CEGUI::System::getSingleton().getDefaultGUIContext();
        context.injectMousePosition(float(event.state.X.abs), float(event.state.Y.abs));
        if(event.state.Z.rel) context.injectMouseWheelChange(float(event.state.Z.rel) / 120.0f);
        return true;
    }
    bool mousePressed(const OIS::MouseEvent& event, OIS::MouseButtonID button)
    {
        records.push_back({'d',event.state.X.abs,event.state.Y.abs,event.state.buttons,event.state.Z.rel,event.state.X.rel,event.state.Y.rel});
        CEGUI::System::getSingleton().getDefaultGUIContext().injectMouseButtonDown(Gui::convertButton(button));
        if(pressed) pressed();
        return true;
    }
    bool mouseReleased(const OIS::MouseEvent& event, OIS::MouseButtonID button)
    {
        records.push_back({'u',event.state.X.abs,event.state.Y.abs,event.state.buttons,event.state.Z.rel,event.state.X.rel,event.state.Y.rel});
        return CEGUI::System::getSingleton().getDefaultGUIContext().injectMouseButtonUp(Gui::convertButton(button));
    }
    void cancelMouseInput();
};
struct Keyboard { OIS::Keyboard keyboard; OIS::Keyboard* getKeyboard() { return &keyboard; } };
struct Window
{
    HWND handle = nullptr;
    int getWidth() { return 1000; }
    int getHeight() { return 1000; }
    void getCustomAttribute(const char*, size_t* value) { *value = reinterpret_cast<size_t>(handle); }
};
struct InputManager: OIS::MouseListener
{
    struct PointerEvent { unsigned int mMessage; int mX,mY,mWheel; };
    std::vector<PointerEvent> mPointerEvents;
    unsigned int mPointerEpoch = 0;
    int mPointerButtons = 0, mCapturedButtons = 0;
    bool mLMouseDown = false, mRMouseDown = false, mMMouseDown = false;
    bool mMouseDownOnCEGUIWindow = false, mMouseDownOnDraggableTileContainer = false;
    InputCommandState mCommandState = InputCommandState::infoOnly;
    OIS::Mouse mouse; OIS::Mouse* mMouse = &mouse;
    Keyboard keyboard; Keyboard* mKeyboard = &keyboard;
    Window window; Window* mRenderWindow = &window;
    AbstractApplicationMode mode; AbstractApplicationMode* mCurrentAMode = &mode;
    bool mWasForeground = true, mMouseGrab = false, mHasPendingPosition = false;
    int mPendingX = 0, mPendingY = 0, mLastPointerX = 0, mLastPointerY = 0;
    void* mHookedWindow = nullptr;
    void* mOldWindowProc = nullptr;
    static void* sWheelOwner;
    int sampleX = 0, sampleY = 0;
    bool sampleInside = true;
    InputManager() { mode.manager.manager = this; }
    bool readSystemPointer(int& x, int& y, bool& inside) { x=sampleX; y=sampleY; inside=sampleInside; return true; }
    void moveSystemPointer(int x, int y) { sampleX=x; sampleY=y; }
    void updateCursorGrab(bool) {}
    void applyPointerToState(int x, int y);
    void dispatchPointerEvents();
    void cancelPointerInput();
    bool prepareFallbackPointer();
    bool mouseMoved(const OIS::MouseEvent&) override;
    bool mousePressed(const OIS::MouseEvent&, OIS::MouseButtonID) override;
    bool mouseReleased(const OIS::MouseEvent&, OIS::MouseButtonID) override;
    void setMousePosition(int x, int y);
    void setCurrentAMode(AbstractApplicationMode& mode);
    void capturePointer();
    void hookWindowWheel();
    void unhookWindowWheel();
    static long long __stdcall wheelWindowProc(void*, unsigned int, unsigned long long, long long);
};
void* InputManager::sWheelOwner = nullptr;
//! Supplies an unused image codec so this probe never loads artwork.
struct Codec: CEGUI::ImageCodec
{
    Codec(): ImageCodec("probe") {}
    CEGUI::Texture* load(const CEGUI::RawDataContainer&, CEGUI::Texture* texture) { return texture; }
};
'''

main = r'''
//! Counts one kind of delivered event independently of intermediate motion callbacks.
int count(const AbstractApplicationMode& mode, char kind)
{
    int result = 0;
    for(std::vector<AbstractApplicationMode::Record>::const_iterator it=mode.records.begin(); it!=mode.records.end(); ++it)
        if(it->kind == kind) ++result;
    return result;
}
//! Preserves normal Windows processing beneath the production subclass.
LRESULT CALLBACK baseWindowProc(HWND hwnd, UINT message, WPARAM wParam, LPARAM lParam)
{
    return DefWindowProcW(hwnd, message, wParam, lParam);
}
//! Uses real Win32 messages, actual subclass/capture and the actual CEGUI titlebar.
int main()
{
    CEGUI::NullRenderer& renderer = CEGUI::NullRenderer::create();
    renderer.setDisplaySize(CEGUI::Sizef(1000,1000));
    Codec codec;
    CEGUI::System::create(renderer, nullptr, nullptr, &codec);
    CEGUI::GUIContext& context = CEGUI::System::getSingleton().getDefaultGUIContext();
    CEGUI::Window* root = new CEGUI::Window("DefaultWindow", "root");
    CEGUI::FrameWindow* frame = new CEGUI::FrameWindow("CEGUI/FrameWindow", "frame");
    CEGUI::Titlebar* title = new CEGUI::Titlebar("CEGUI/Titlebar", "__auto_titlebar__");
    root->setSize(CEGUI::USize(CEGUI::UDim(1,0),CEGUI::UDim(1,0)));
    frame->setSize(CEGUI::USize(CEGUI::UDim(0,300),CEGUI::UDim(0,300)));
    title->setSize(CEGUI::USize(CEGUI::UDim(1,0),CEGUI::UDim(0,30)));
    root->addChild(frame); frame->addChild(title); context.setRootWindow(root);
    WNDCLASSW windowClass = {};
    windowClass.lpfnWndProc = baseWindowProc;
    windowClass.hInstance = GetModuleHandleW(nullptr);
    windowClass.lpszClassName = L"OdpPointerProbe";
    assert(RegisterClassW(&windowClass));
    HWND hwnd = CreateWindowExW(0,windowClass.lpszClassName,L"pointer probe",WS_POPUP,0,0,1000,1000,nullptr,nullptr,windowClass.hInstance,nullptr);
    assert(hwnd != nullptr);
    foregroundWindow = hwnd;
    InputManager p;
    p.window.handle = hwnd;
    p.hookWindowWheel();
    assert(p.mHookedWindow == hwnd && p.mOldWindowProc != nullptr);
    p.setCurrentAMode(p.mode);
    assert(p.mouse.getEventCallback() == nullptr);

    // A real titlebar follows the held move and stops before the later free move.
    SendMessageW(hwnd,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(10,10));
    assert(GetCapture() == hwnd);
    SetCapture(hwnd);
    assert(GetCapture() == hwnd && p.mCapturedButtons == 1);
    SendMessageW(hwnd,WM_MOUSEMOVE,MK_LBUTTON,MAKELPARAM(10,20));
    SendMessageW(hwnd,WM_LBUTTONUP,0,MAKELPARAM(10,20));
    SendMessageW(hwnd,WM_MOUSEMOVE,0,MAKELPARAM(900,900));
    POINT wheelPoint = {900,900}; ClientToScreen(hwnd,&wheelPoint);
    SendMessageW(hwnd,WM_MOUSEWHEEL,MAKEWPARAM(0,120),MAKELPARAM(wheelPoint.x,wheelPoint.y));
    p.dispatchPointerEvents();
    assert(count(p.mode,'d') == 1 && count(p.mode,'u') == 1);
    assert(frame->getPosition().d_y.d_offset == 10.0f && !title->isDragged());
    assert(p.mode.records.back().wheel == 120 && p.mouse.state.Z.rel == 0);
    assert(GetCapture() == nullptr);

    // Double clicks and auxiliary buttons retain separate held states.
    p.mode.records.clear();
    SendMessageW(hwnd,WM_LBUTTONDBLCLK,MK_LBUTTON,MAKELPARAM(500,500));
    SendMessageW(hwnd,WM_XBUTTONDOWN,MAKEWPARAM(MK_XBUTTON1,XBUTTON1),MAKELPARAM(500,500));
    SendMessageW(hwnd,WM_LBUTTONUP,0,MAKELPARAM(500,500));
    SendMessageW(hwnd,WM_XBUTTONUP,MAKEWPARAM(0,XBUTTON1),MAKELPARAM(500,500));
    p.dispatchPointerEvents();
    assert(count(p.mode,'d') == 2 && count(p.mode,'u') == 2 && p.mPointerButtons == 0);

    // Real capture loss cancels a drag without producing a normal release.
    frame->setPosition(CEGUI::UVector2(CEGUI::UDim(0,0),CEGUI::UDim(0,0)));
    p.mode.records.clear();
    SendMessageW(hwnd,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(10,10));
    p.dispatchPointerEvents();
    assert(title->isDragged());
    ReleaseCapture();
    p.dispatchPointerEvents();
    assert(!title->isDragged() && context.getInputCaptureWindow() == nullptr);
    assert(count(p.mode,'u') == 0 && p.mPointerButtons == 0);
    assert(!context.getSystemKeys().isPressed(CEGUI::SystemKeys::LeftMouse));
    SendMessageW(hwnd,WM_LBUTTONUP,0,MAKELPARAM(10,10));
    p.dispatchPointerEvents();
    assert(count(p.mode,'u') == 0);

    // Cancellation drains the real RestoreOldCapture chain instead of restoring it.
    assert(frame->captureInput());
    title->setRestoreOldCapture(true);
    assert(title->captureInput());
    assert(context.getInputCaptureWindow() == title);
    p.cancelPointerInput();
    assert(context.getInputCaptureWindow() == nullptr);
    title->setRestoreOldCapture(false);

    // Focus lost between frames cancels even if the foreground already returned.
    p.mode.records.clear();
    SendMessageW(hwnd,WM_RBUTTONDOWN,MK_RBUTTON,MAKELPARAM(500,500));
    p.dispatchPointerEvents();
    SendMessageW(hwnd,WM_KILLFOCUS,0,0);
    p.dispatchPointerEvents();
    assert(count(p.mode,'u') == 0 && p.mPointerButtons == 0 && GetCapture() == nullptr);

    // Reset before dispatch drops old buttons/wheel/motion and positions the GUI.
    SendMessageW(hwnd,WM_LBUTTONDOWN,MK_LBUTTON,MAKELPARAM(10,10));
    SendMessageW(hwnd,WM_MOUSEWHEEL,MAKEWPARAM(0,120),MAKELPARAM(wheelPoint.x,wheelPoint.y));
    p.mode.records.clear();
    p.setMousePosition(700,600);
    p.dispatchPointerEvents();
    assert(count(p.mode,'d') == 0 && p.mouse.state.X.abs == 700 && p.mouse.state.Y.abs == 600);
    assert(context.getMouseCursor().getPosition().d_x == 700);

    // Reset inside a callback invalidates the old in-flight batch including wheel.
    p.mode.pressed = [&p]() { p.setMousePosition(600,700); };
    p.mPointerEvents = {{WM_LBUTTONDOWN,500,500,0},{WM_LBUTTONUP,500,500,0},{WM_MOUSEWHEEL,500,500,120},{WM_MOUSEMOVE,900,900,0}};
    p.mode.records.clear();
    p.dispatchPointerEvents();
    p.mode.pressed = nullptr;
    assert(count(p.mode,'d') == 1 && count(p.mode,'u') == 0);
    assert(p.mouse.state.X.abs == 600 && p.mouse.state.Y.abs == 700 && p.mouse.state.Z.rel == 0);

    // The final system sample follows ordered release and does not replay wheel.
    p.mode.records.clear();
    p.mPointerEvents = {{WM_LBUTTONDOWN,500,500,0},{WM_LBUTTONUP,500,510,0},{WM_MOUSEWHEEL,500,510,120}};
    p.sampleX=900; p.sampleY=800;
    p.capturePointer();
    assert(count(p.mode,'u') == 1 && p.mode.records.back().wheel == 0);
    assert(p.mode.records.back().x == 900 && p.mode.records.back().y == 800);
    assert(p.mode.records.back().dx == 400 && p.mode.records.back().dy == 290);
    int wheelEvents = 0;
    for(std::vector<AbstractApplicationMode::Record>::const_iterator it=p.mode.records.begin(); it!=p.mode.records.end(); ++it)
        if(it->wheel) { assert(it->wheel == 120); ++wheelEvents; }
    assert(wheelEvents == 1);

    // A position requested in the background wins on reactivation.
    foregroundWindow = nullptr;
    p.capturePointer();
    p.setMousePosition(321,654);
    assert(p.mHasPendingPosition);
    foregroundWindow = hwnd;
    p.capturePointer();
    assert(!p.mHasPendingPosition && p.mouse.state.X.abs == 321 && p.mouse.state.Y.abs == 654);

    // Forced hook failure retains OIS input with absolute Windows coordinates.
    p.unhookWindowWheel();
    failHook = true;
    p.hookWindowWheel();
    failHook = false;
    assert(p.mHookedWindow == nullptr && p.mOldWindowProc == nullptr);
    p.setCurrentAMode(p.mode);
    assert(p.mouse.getEventCallback() != nullptr);
    p.mode.records.clear();
    p.sampleX = 345; p.sampleY = 456;
    p.mouse.state.X.abs = 999; p.mouse.state.Y.abs = 999;
    p.mouse.state.Z.rel = -120;
    p.mouse.getEventCallback()->mouseMoved(OIS::MouseEvent(&p.mouse,p.mouse.state));
    assert(p.mode.records.back().x == 345 && p.mode.records.back().y == 456 && p.mode.records.back().wheel == -120);
    p.mouse.getEventCallback()->mousePressed(OIS::MouseEvent(&p.mouse,p.mouse.state),OIS::MB_Right);
    p.mouse.getEventCallback()->mouseReleased(OIS::MouseEvent(&p.mouse,p.mouse.state),OIS::MB_Right);
    assert(count(p.mode,'d') == 1 && count(p.mode,'u') == 1);
    assert(p.mouse.state.Z.rel == -120);
    p.mouse.getEventCallback()->mouseMoved(OIS::MouseEvent(&p.mouse,p.mouse.state));
    assert(p.mode.records.back().wheel == -120);
    foregroundWindow = nullptr;
    p.mouse.getEventCallback()->mousePressed(OIS::MouseEvent(&p.mouse,p.mouse.state),OIS::MB_Left);
    assert(count(p.mode,'d') == 1);

    p.unhookWindowWheel(); DestroyWindow(hwnd);
    context.setRootWindow(nullptr); delete root;
    CEGUI::System::destroy(); CEGUI::NullRenderer::destroy(renderer);
    std::cout << "Win32 hook, cancellation, reset, fallback, wheel and real CEGUI drag checks passed\n";
}
'''

signatures = [
    'void InputManager::dispatchPointerEvents()',
    'void InputManager::cancelPointerInput()',
    'bool InputManager::prepareFallbackPointer()',
    'bool InputManager::mouseMoved(',
    'bool InputManager::mousePressed(',
    'bool InputManager::mouseReleased(',
    'void InputManager::applyPointerToState(',
    'void InputManager::setMousePosition(',
    'void InputManager::setCurrentAMode(',
    'void InputManager::capturePointer()',
    'long long __stdcall InputManager::wheelWindowProc(',
    'void InputManager::hookWindowWheel()',
    'void InputManager::unhookWindowWheel()',
]
functions = ''.join(method(source, signature) for signature in signatures)
functions += method(mode_source, 'void AbstractApplicationMode::cancelMouseInput()')
deps = pathlib.Path(os.environ.get('BUILD_DEPS_ROOT', pathlib.Path.home() / 'build-deps'))
cegui_source = deps / 'src/cegui/cegui'
with tempfile.TemporaryDirectory(prefix='odp-pointer-') as directory:
    directory = pathlib.Path(directory)
    cpp = directory / 'probe.cpp'
    cpp.write_text(preamble + functions + main, encoding='utf-8')
    vcvars = pathlib.Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio/18/BuildTools/VC/Auxiliary/Build/vcvars64.bat'
    null_sources = ' '.join('"' + str(cegui_source / 'src/RendererModules/Null' / name) + '"'
                            for name in ['Renderer.cpp', 'GeometryBuffer.cpp', 'Texture.cpp', 'TextureTarget.cpp'])
    command = (f'call "{vcvars}" >nul && cl /nologo /EHsc /MD /std:c++14 /DCEGUINULLRENDERER_EXPORTS '
               f'/I"{root / "source"}" /I"{deps / "install/include/cegui-0"}" '
               f'/I"{cegui_source / "include"}" "{cpp}" {null_sources} '
               f'/Fe:"{directory / "probe.exe"}" /link /LIBPATH:"{deps / "install/lib"}" CEGUIBase-0.lib user32.lib')
    batch = directory / 'run.bat'
    batch.write_text('@echo off\n' + command + '\nif errorlevel 1 exit /b %errorlevel%\n'
                     + f'set "PATH={deps / "install/bin"};%PATH%"\n"{directory / "probe.exe"}"\n', encoding='utf-8')
    subprocess.run(['cmd', '/d', '/c', str(batch)], cwd=directory, check=True)
