"""Compile the real pointer dispatcher with stubs and exercise event ordering."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / 'source/modes/InputManager.cpp').read_text(encoding='utf-8')
start = source.index('void InputManager::dispatchPointerEvents()')
end = source.index('bool InputManager::readSystemPointer', start)
function = source[start:end]
preamble = r"""
#include <vector>
#include <cassert>
#define WM_LBUTTONDOWN 1
#define WM_LBUTTONDBLCLK 2
#define WM_LBUTTONUP 3
#define WM_RBUTTONDOWN 4
#define WM_RBUTTONDBLCLK 5
#define WM_RBUTTONUP 6
#define WM_MBUTTONDOWN 7
#define WM_MBUTTONDBLCLK 8
#define WM_MBUTTONUP 9
#define WM_XBUTTONDOWN 10
#define WM_XBUTTONDBLCLK 11
#define WM_XBUTTONUP 12
#define WM_MOUSEMOVE 13
#define WM_MOUSEWHEEL 14
#define XBUTTON1 1
#define XBUTTON2 2
struct RECT {int left, top, right, bottom;};
typedef void* HWND;
bool GetClientRect(HWND, RECT* r) {*r = {0,0,1000,1000}; return true;}
namespace OIS {
enum MouseButtonID {MB_Left, MB_Right, MB_Middle, MB_Button3, MB_Button4};
struct Axis {int abs = 0, rel = 0;};
struct MouseState {Axis X,Y,Z; int buttons = 0;};
struct Mouse {MouseState state; const MouseState& getMouseState() {return state;}};
struct MouseEvent {MouseEvent(Mouse*, const MouseState& s): state(s) {} const MouseState& state;};
}
namespace PointerMapping {
struct Point {int mX, mY;};
Point clientToGamePointer(int x, int y, int, int, int, int, int) {return {x,y};}
}
namespace Gui {int getConfiguredUiScalePercent() {return 100;}}
struct Window {int getWidth() {return 1000;} int getHeight() {return 1000;}};
struct Mode {
 struct Record {char kind; int x,y,buttons,wheel;};
 std::vector<Record> records;
 void mouseMoved(const OIS::MouseEvent& e) {records.push_back({'m',e.state.X.abs,e.state.Y.abs,e.state.buttons,e.state.Z.rel});}
 void mousePressed(const OIS::MouseEvent& e, OIS::MouseButtonID) {records.push_back({'d',e.state.X.abs,e.state.Y.abs,e.state.buttons,e.state.Z.rel});}
 void mouseReleased(const OIS::MouseEvent& e, OIS::MouseButtonID) {records.push_back({'u',e.state.X.abs,e.state.Y.abs,e.state.buttons,e.state.Z.rel});}
};
struct InputManager {
 struct PointerEvent {unsigned int mMessage; int mX,mY,mWheel;};
 std::vector<PointerEvent> mPointerEvents;
 OIS::Mouse mouse; OIS::Mouse* mMouse = &mouse;
 HWND mHookedWindow = reinterpret_cast<HWND>(1);
 Window window; Window* mRenderWindow = &window;
 Mode mode; Mode* mCurrentAMode = &mode;
 int mLastPointerX = 0, mLastPointerY = 0, mPointerButtons = 0;
 void applyPointerToState(int x, int y) {mouse.state.X.abs=x; mouse.state.Y.abs=y;}
 void dispatchPointerEvents();
};
"""
main = r"""
int main() {
 InputManager p;
 // The release must be delivered before a later move, avoiding a dragged jump.
 p.mPointerEvents = {{WM_LBUTTONDOWN,10,10,0},{WM_MOUSEMOVE,10,20,0},{WM_LBUTTONUP,10,20,0},{WM_MOUSEMOVE,900,900,0},{WM_MOUSEWHEEL,900,900,120}};
 p.dispatchPointerEvents();
 assert(p.mode.records.size()==5);
 assert(p.mode.records[0].kind=='d' && p.mode.records[0].buttons==1);
 assert(p.mode.records[1].kind=='m' && p.mode.records[1].buttons==1 && p.mode.records[1].y==20);
 assert(p.mode.records[2].kind=='u' && p.mode.records[2].buttons==0 && p.mode.records[2].y==20);
 assert(p.mode.records[3].kind=='m' && p.mode.records[3].buttons==0 && p.mode.records[3].y==900);
 assert(p.mode.records[4].wheel==120 && p.mouse.state.Z.rel==0);
 // A double click is a second press; auxiliary buttons keep their own state.
 p.mode.records.clear();
 p.mPointerEvents = {{WM_LBUTTONDBLCLK,5,5,0},{WM_XBUTTONDOWN,5,5,1},{WM_LBUTTONUP,5,5,0},{WM_XBUTTONUP,5,5,1}};
 p.dispatchPointerEvents();
 assert(p.mode.records.size()==4 && p.mode.records[0].buttons==1 && p.mode.records[1].buttons==9);
 assert(p.mode.records[2].buttons==8 && p.mode.records[3].buttons==0);
}
"""
with tempfile.TemporaryDirectory() as directory:
    directory = pathlib.Path(directory)
    cpp = directory / 'probe.cpp'
    cpp.write_text(preamble + function + main, encoding='utf-8')
    vcvars = r'C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
    command = f'call "{vcvars}" >nul && cl /nologo /EHsc /std:c++14 "{cpp}" /Fe:"{directory / "probe.exe"}" /Fo:"{directory / "probe.obj"}" && "{directory / "probe.exe"}"'
    batch = directory / 'run.bat'
    batch.write_text('@echo off\n' + command + '\n', encoding='utf-8')
    subprocess.run(['cmd', '/d', '/c', str(batch)], cwd=directory, check=True)
print('ordered pointer dispatcher probe passed')
