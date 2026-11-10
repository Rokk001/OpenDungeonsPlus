"""T-C1 runtime integration probe for production Room Manager window methods.

Compiles the actual GameModeRoomManager.cpp method bodies with small GUI/event
and game-state stubs. No game build or display is required. Page/network entry
points record invocations; navigation, ownership, tile lookup, rendering and
event dispatch all execute the production code.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/modes/GameModeRoomManager.cpp').read_text(encoding='utf-8')
production = re.sub(r'^#include[^\n]*\n', '', source, flags=re.M)

STUBS = r'''
#include "rooms/RoomManagerNavigation.h"
#include "rooms/RoomManagerStatus.h"
#include <cstdlib>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace Helper {
template<class T> std::string toString(T value) { std::ostringstream out; out << value; return out.str(); }
}
namespace CEGUI {
struct EventArgs { virtual ~EventArgs() {} };
class Window;
struct WindowEventArgs : EventArgs { Window* window; explicit WindowEventArgs(Window* w) : window(w) {} };
struct UDim { float d_scale, d_offset; UDim(float scale=0, float offset=0) : d_scale(scale), d_offset(offset) {} };
struct USize { UDim d_width, d_height; USize() : d_width(0, 200), d_height(0, 66) {} };
struct Event {
    struct Subscriber {
        std::function<bool(const EventArgs&)> callback;
        template<class T> Subscriber(bool(T::*method)(const EventArgs&), T* owner) :
            callback([owner,method](const EventArgs& args) { return (owner->*method)(args); }) {}
    };
};
class Window {
public:
    enum { EventHidden=1, EventMouseClick=2 };
    bool visible;
    unsigned id;
    UDim y;
    USize size;
    std::string text;
    std::map<std::string,std::string> properties;
    std::map<std::string,std::unique_ptr<Window> > children;
    std::map<int,std::vector<std::function<bool(const EventArgs&)> > > events;
    Window() : visible(false), id(0) {}
    Window* ensure(const std::string& path) {
        const std::size_t slash = path.find('/');
        const std::string name = path.substr(0,slash);
        if(!children.count(name)) children[name].reset(new Window());
        Window* child = children[name].get();
        return slash == std::string::npos ? child : child->ensure(path.substr(slash+1));
    }
    Window* getChild(const std::string& path) {
        const std::size_t slash=path.find('/');
        const std::string name=path.substr(0,slash);
        if(!children.count(name)) throw std::runtime_error("unexpected GUI path: "+path);
        Window* child=children[name].get();
        return slash==std::string::npos ? child : child->getChild(path.substr(slash+1));
    }
    int subscribeEvent(int event, const Event::Subscriber& subscriber) {
        events[event].push_back(subscriber.callback); return 1;
    }
    void fire(int event) {
        WindowEventArgs args(this);
        for(const std::function<bool(const EventArgs&)>& callback : events[event]) callback(args);
    }
    void setVisible(bool value) {
        const bool hidden=visible && !value; visible=value;
        if(hidden) fire(EventHidden);
    }
    void show() { setVisible(true); }
    void hide() { setVisible(false); }
    bool isVisible() const { return visible; }
    void moveToFront() {}
    void setID(unsigned value) { id=value; }
    unsigned getID() const { return id; }
    void setProperty(const std::string& name,const std::string& value) { properties[name]=value; }
    void setText(const std::string& value) { text=value; }
    void setYPosition(UDim value) { y=value; }
    USize getSize() const { return size; }
};
struct FrameWindow { enum { EventCloseClicked=3 }; };
struct PushButton { enum { EventClicked=4 }; };
}

enum class TileVisual { nullTileVisual, ghostRoom, merchantRoom, tavernRoom, spaRoom,
    infirmaryRoom, alchemyLabRoom, casinoRoom, workshopRoom };
struct Seat {
    std::array<RoomManagerEntry,8> entries;
    Seat() : entries(emptyRoomManagerEntries()) {}
    uint32_t getNbRooms(RoomType type) const {
        for(const RoomManagerEntry& entry : entries) if(entry.type==type) return entry.count;
        return 0;
    }
    const std::array<RoomManagerEntry,8>& getRoomManagerEntries() const { return entries; }
};
struct Player { Seat* seat; explicit Player(Seat* s) : seat(s) {} Seat* getSeat() const { return seat; } };
// Client tiles intentionally provide no covering Room API: only ownership and visuals exist here.
struct Tile {
    Seat* seat; TileVisual visual; int x,y;
    Tile(Seat* s=nullptr,TileVisual v=TileVisual::nullTileVisual,int xx=0,int yy=0) : seat(s),visual(v),x(xx),y(yy) {}
    Seat* getSeat() const { return seat; }
    TileVisual getTileVisual() const { return visual; }
    int getX() const { return x; } int getY() const { return y; }
};
struct GameMap {
    Player* player; std::vector<Tile> tiles;
    explicit GameMap(Player* p) : player(p) {
        for(int x=0;x<16;++x) tiles.push_back(Tile(nullptr,TileVisual::nullTileVisual,x,0));
    }
    Player* getLocalPlayer() { return player; }
    int getMapSizeX() const { return 16; } int getMapSizeY() const { return 1; }
    Tile* getTile(int x,int y) { return x>=0 && x<16 && y==0 ? &tiles[x] : nullptr; }
};
struct RoomManager {
    static std::string getRoomReadableName(RoomType type) { return "Room"+Helper::toString(static_cast<int>(type)); }
};

class GameMode {
public:
    CEGUI::Window* mRootWindow;
    GameMap* mGameMap;
    RoomManagerNavigation mRoomManagerNavigation;
    RoomType mRoomManagerPageType;
    int mTavernX,mTavernY,mSpaX,mSpaY,mCasinoX,mCasinoY;
    int starts[8], releases[8], connections, closes;
    bool otherWindow;
    GameMode(CEGUI::Window* root,GameMap* map) : mRootWindow(root),mGameMap(map),
        mRoomManagerPageType(RoomType::nullRoomType),mTavernX(-1),mTavernY(-1),mSpaX(-1),mSpaY(-1),
        mCasinoX(-1),mCasinoY(-1),connections(0),closes(0),otherWindow(false) {
        for(int index=0;index<8;++index) { starts[index]=0; releases[index]=0; }
    }
    void addEventConnection(int) { ++connections; }
    void initializeRoomManager(); void refreshRoomManager();
    bool toggleRoomManager(const CEGUI::EventArgs& = CEGUI::EventArgs());
    bool selectRoomManagerType(RoomType,bool=false,bool=true);
    bool selectRoomManagerRow(const CEGUI::EventArgs&);
    bool closeRoomManager(const CEGUI::EventArgs& = CEGUI::EventArgs());
    void closeAllTopWindows() { ++closes; otherWindow=false; closeRoomManager(); }
    void hideMerchantWindow() { ++releases[1]; }
    void hideInfirmaryWindow() { ++releases[4]; }
    void hideAlchemyLabWindow(const CEGUI::EventArgs&) { ++releases[5]; }
    void hideGhostRoomWindow() { ++releases[0]; }
    void hideTavernWindow() { ++releases[2]; mTavernX=mTavernY=-1; }
    void hideSpaWindow() { ++releases[3]; mSpaX=mSpaY=-1; }
    void hideCasinoPayoutWindow() { ++releases[6]; mCasinoX=mCasinoY=-1; }
    void closeTrapProductionQueue() { ++releases[7]; }
    void showGhostRoomWindow(Tile* tile) { if(tile) ++starts[0]; }
    void showMerchantPage() { ++starts[1]; }
    void showTavernWindow(Tile* tile) { ++starts[2]; mTavernX=tile->x; mTavernY=tile->y; }
    void showSpaWindow(Tile* tile) { ++starts[3]; mSpaX=tile->x; mSpaY=tile->y; }
    void showInfirmaryWindow() { ++starts[4]; }
    void showAlchemyLabWindow() { ++starts[5]; }
    void showCasinoPayoutWindow(Tile* tile) { ++starts[6]; mCasinoX=tile->x; mCasinoY=tile->y; }
    void requestTrapProductionQueue() { ++starts[7]; }
};
'''

CASES = r'''
//! \brief Reports one failed production-window acceptance case.
void expect(bool condition,const char* message) {
    if(!condition) { std::cerr<<message<<std::endl; std::exit(1); }
}
//! \brief Exercises GUI events and production transitions with authoritative owned counts.
int main() {
    CEGUI::Window root;
    root.ensure("RoomManagerButton/Dot");
    root.ensure("RoomManagerWindow/RoomsLabel");
    for(unsigned index=0;index<8;++index) {
        for(const char* part : {"Button","Name","Icon","Highlight","Dot"})
            root.ensure("RoomManagerWindow/Rows/Row"+Helper::toString(index)+"/"+part);
        root.ensure(std::string("RoomManagerWindow/Pages/")+PAGE_NAMES[index]);
    }
    Seat seat,enemy; Player player(&seat); GameMap map(&player); GameMode game(&root,&map);
    CEGUI::Window* frame=root.getChild("RoomManagerWindow");
    CEGUI::Window* hud=root.getChild("RoomManagerButton");
    game.initializeRoomManager();
    expect(game.connections==11,"HUD,close,hidden and eight row events connected");
    game.refreshRoomManager();
    expect(!hud->visible && !frame->visible,"no owned rooms hides button and frame");
    game.otherWindow=true;
    game.selectRoomManagerType(RoomType::workshop,true);
    expect(game.otherWindow && game.closes==0,"unowned options target preserves other windows");
    game.selectRoomManagerType(RoomType::infirmary);
    expect(!frame->visible && game.otherWindow,"unowned key is inert");

    seat.entries[1].count=3; seat.entries[4].count=2; seat.entries[5].count=1;
    game.refreshRoomManager();
    expect(hud->visible && !frame->visible,"ownership shows button without opening frame");
    hud->fire(CEGUI::PushButton::EventClicked);
    expect(frame->visible && !game.otherWindow && game.closes==1,"HUD opens manager and closes other windows");
    expect(game.mRoomManagerNavigation.selected()==RoomType::merchant,"HUD selects first owned row");
    expect(frame->getChild("RoomsLabel")->text=="Rooms (3)","heading counts three types not six rooms");
    expect(!frame->getChild("Rows/Row0")->visible && frame->getChild("Rows/Row1")->visible,"only owned rows visible");
    expect(frame->getChild("Rows/Row1")->y.d_offset==0 && frame->getChild("Rows/Row4")->y.d_offset==66 &&
        frame->getChild("Rows/Row5")->y.d_offset==132,"owned rows close up in fixed order");
    expect(!frame->getChild("Rows/Row1/Dot")->visible,"merchant has no dot");
    expect(frame->getChild("Pages/MerchantPage")->visible && !frame->getChild("Pages/InfirmaryPage")->visible,"only selected page visible");
    expect(game.starts[1]==1,"merchant starts once on page entry");
    game.refreshRoomManager(); game.refreshRoomManager();
    expect(game.starts[1]==1,"refresh does not repeat page subscriptions");
    game.otherWindow=true;
    game.selectRoomManagerType(RoomType::infirmary);
    expect(game.otherWindow && game.closes==1,"I target preserves other windows");
    expect(game.starts[4]==1 && game.releases[1]==2,"switch releases previous page before opening infirmary");
    expect(frame->getChild("Rows/Row4/Highlight")->visible,"selection highlight follows key");
    game.selectRoomManagerType(RoomType::infirmary);
    expect(!frame->visible && game.otherWindow,"same I target toggles closed without closing other windows");
    game.selectRoomManagerType(RoomType::alchemyLab);
    expect(frame->visible && game.otherWindow && game.starts[5]==1,"L opens lab and preserves other windows");
    CEGUI::Window* row=frame->getChild("Rows/Row1/Button");
    row->fire(CEGUI::Window::EventMouseClick);
    expect(frame->getChild("Pages/MerchantPage")->visible,"row event selects merchant");
    row->fire(CEGUI::Window::EventMouseClick);
    expect(frame->visible,"selected row click stays open");
    hud->fire(CEGUI::PushButton::EventClicked);
    expect(!frame->visible && !game.otherWindow,"HUD toggles closed and closes other windows");

    seat.entries[7].count=1;
    game.otherWindow=true; game.selectRoomManagerType(RoomType::workshop,true);
    expect(frame->visible && !game.otherWindow && game.starts[7]==1,"options opens workshop and closes other windows");
    game.otherWindow=true; game.selectRoomManagerType(RoomType::workshop,true);
    expect(!frame->visible && !game.otherWindow,"options toggles workshop closed");
    game.selectRoomManagerType(RoomType::merchant);
    const int merchantBefore=game.starts[1];
    seat.entries[1].count=2; game.refreshRoomManager();
    expect(game.mRoomManagerNavigation.selected()==RoomType::merchant && game.starts[1]==merchantBefore,"non-last loss preserves page subscription");
    seat.entries[1].count=0; game.refreshRoomManager();
    expect(game.mRoomManagerNavigation.selected()==RoomType::infirmary,"last selected room loss selects first remaining row");
    expect(!frame->getChild("Rows/Row1")->visible && frame->getChild("Rows/Row4")->y.d_offset==0,"lost row disappears and remaining rows close up");
    for(RoomManagerEntry& entry : seat.entries) entry.count=0;
    game.refreshRoomManager();
    expect(!frame->visible && !hud->visible,"last managed room loss closes and hides button");

    // Dot colors are rendered from server snapshots immediately, with red ahead of yellow.
    seat.entries[4].count=1; seat.entries[5].count=1; seat.entries[5].dot=RoomManagerDot::yellow;
    game.selectRoomManagerType(RoomType::alchemyLab);
    expect(hud->getChild("Dot")->properties["TextColours"]=="FFFFD040","yellow button dot");
    seat.entries[4].dot=RoomManagerDot::red; game.refreshRoomManager();
    expect(hud->getChild("Dot")->properties["TextColours"]=="FFFF4040","red overrides yellow");
    expect(frame->getChild("Rows/Row4/Dot")->properties["TextColours"]=="FFFF4040","row immediately renders red");
    seat.entries[4].dot=RoomManagerDot::green; seat.entries[5].dot=RoomManagerDot::green;
    game.refreshRoomManager();
    expect(hud->getChild("Dot")->properties["TextColours"]=="FF50D050","button returns green");

    // Each client-visual page skips enemy tiles and rebinds when its old owned target is lost.
    const unsigned tileIndices[3]={2,3,6};
    const TileVisual visuals[3]={TileVisual::tavernRoom,TileVisual::spaRoom,TileVisual::casinoRoom};
    for(unsigned test=0;test<3;++test) {
        const unsigned index=tileIndices[test];
        for(RoomManagerEntry& entry : seat.entries) entry.count=0;
        seat.entries[index].count=2;
        map.tiles[0].seat=&enemy; map.tiles[0].visual=visuals[test];
        map.tiles[3].seat=&seat; map.tiles[3].visual=visuals[test];
        map.tiles[7].seat=&seat; map.tiles[7].visual=visuals[test];
        game.closeRoomManager(); game.selectRoomManagerType(RoomManagerNavigation::order()[index]);
        const int originalStarts=game.starts[index];
        const int chosen=test==0?game.mTavernX:test==1?game.mSpaX:game.mCasinoX;
        expect(chosen==3,"client visual lookup finds owned room without Room objects");
        map.tiles[3].seat=&enemy;
        game.refreshRoomManager();
        const int rebound=test==0?game.mTavernX:test==1?game.mSpaX:game.mCasinoX;
        expect(rebound==7 && game.starts[index]==originalStarts+1,"lost setting target rebinds to another owned room");
        game.refreshRoomManager();
        expect(game.starts[index]==originalStarts+1,"stable target does not resubscribe");
        map.tiles[7].visual=TileVisual::nullTileVisual;
        map.tiles[10].seat=&seat; map.tiles[10].visual=visuals[test];
        game.refreshRoomManager();
        const int replaced=test==0?game.mTavernX:test==1?game.mSpaX:game.mCasinoX;
        expect(replaced==10,"sold/replaced client tile rebinds by visual");
        map.tiles[10].visual=TileVisual::nullTileVisual;
    }
    frame->fire(CEGUI::FrameWindow::EventCloseClicked);
    expect(!frame->visible && !game.mRoomManagerNavigation.isOpen(),"title close event closes navigation");
    game.selectRoomManagerType(RoomType::casino);
    frame->hide();
    expect(!game.mRoomManagerNavigation.isOpen(),"generic hidden event releases manager state");
    map.player=nullptr; game.refreshRoomManager();
    expect(!hud->visible && !frame->visible,"missing player safely clears manager");
    std::cout<<"Room Manager production window runtime passed"<<std::endl;
}
'''

with tempfile.TemporaryDirectory(prefix='odp-room-manager-window-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(STUBS + production + CASES, encoding='utf-8')
    args = ['cl', '/nologo', '/EHsc', '/MD', '/O2', '/W3', '/I' + str(ROOT / 'source'), 'check.cpp', '/Fecheck.exe']
    if shutil.which('cl'):
        subprocess.run(args, cwd=work, check=True)
    else:
        vcvars = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio/18/BuildTools/VC/Auxiliary/Build/vcvars64.bat'
        batch = work / 'compile.cmd'
        batch.write_text('@echo off\ncall "' + str(vcvars) + '" >nul\n' + subprocess.list2cmdline(args) +
                         '\nexit /b %errorlevel%\n', encoding='utf-8')
        subprocess.run(['cmd', '/d', '/c', str(batch)], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
