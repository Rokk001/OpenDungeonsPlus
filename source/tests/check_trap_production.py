"""Compile actual reorder and packet code against the installed Windows libraries.

Run after scripts/win32/Enter-OpenDungeonsPlus.ps1. Does not launch the game.
World ownership/order is simulated; packet encoding uses the real ODPacket.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
prefix = Path(os.environ["CMAKE_PREFIX_PATH"])
source = (root / "source/gamemap/GameMap.cpp").read_text(encoding="utf-8")
start = source.index("bool GameMap::moveTrapProductionOrder(")
end = source.index("\nvoid GameMap::removeTrap(", start)
reorder = source[start:end]
probe = r'''
#include "game/TrapProductionData.h"
#include "network/ODPacket.h"
#include <algorithm>
#include <iostream>
#include <stdexcept>
struct Seat {};
struct Trap {
    std::string name; Seat* seat; int needed;
    const std::string& getName() const {return name;}
    Seat* getSeat() const {return seat;}
    int getNbNeededCraftedTrap() const {return needed;}
};
struct GameMap {
    std::vector<Trap*> mTraps;
    bool server=true,editor=false;
    bool isServerGameMap() const {return server;}
    bool isInEditorMode() const {return editor;}
    bool moveTrapProductionOrder(Seat*,const std::string&,bool);
};
REORDER
int checks=0;
void check(bool ok,const char* name) {++checks;if(!ok)throw std::runtime_error(name);}
int main() {
    try {
        Seat own,enemy;
        Trap first{"first",&own,1},foreign{"foreign",&enemy,1},done{"done",&own,0},last{"last",&own,2};
        GameMap map;map.mTraps={&first,&foreign,&done,&last};
        check(map.moveTrapProductionOrder(&own,"last",true),"move earlier accepted");
        check(map.mTraps==std::vector<Trap*>{&last,&foreign,&done,&first},"only adjacent pending owned slots swap");
        check(!map.moveTrapProductionOrder(&own,"last",true),"first order cannot move earlier");
        check(map.moveTrapProductionOrder(&own,"last",false),"move later accepted");
        check(!map.moveTrapProductionOrder(&own,"last",false),"last order cannot move later");
        for(const auto& name:{"foreign","done","missing"})
            check(!map.moveTrapProductionOrder(&own,name,true),"foreign completed and stale targets rejected");
        check(!map.moveTrapProductionOrder(nullptr,"last",true),"missing owner rejected");
        map.server=false;check(!map.moveTrapProductionOrder(&own,"last",true),"client cannot mutate order");
        map.server=true;map.editor=true;check(!map.moveTrapProductionOrder(&own,"last",true),"editor cannot mutate gameplay order");
        map.editor=false;map.mTraps.clear();check(!map.moveTrapProductionOrder(&own,"last",true),"empty queue safe");

        using T=TrapType;
        TrapProductionData original;
        original.orders={{"first",T::cannon,2},{"last",T::doorWooden,1}};
        original.workshops={{"forge",T::cannon,40,100},{"idle",T::nullTrapType,10,0}};
        ODPacket encoded;exportTrapProductionData(encoded,original);
        TrapProductionData decoded;
        check(importTrapProductionData(encoded,decoded),"real packet roundtrip");
        check(decoded.orders.size()==2 && decoded.orders[0].name=="first" && decoded.orders[1].type==T::doorWooden,"wire preserves order and types");
        check(decoded.workshops.size()==2 && decoded.workshops[0].points==40 && decoded.workshops[0].required==100 && decoded.workshops[1].type==T::nullTrapType,"wire preserves current and idle workshops");
        ODPacket empty;exportTrapProductionData(empty,TrapProductionData{});
        check(importTrapProductionData(empty,decoded) && decoded.orders.empty() && decoded.workshops.empty(),"empty snapshot clears view");
        auto reject=[&](const TrapProductionData& bad){
            ODPacket packet;exportTrapProductionData(packet,bad);decoded=original;
            check(!importTrapProductionData(packet,decoded),"invalid snapshot rejected");
            check(decoded.orders.size()==2 && decoded.orders[0].name=="first","failed parse preserves previous snapshot");
        };
        auto bad=original;bad.orders[1].name="first";reject(bad);
        bad=original;bad.orders[0].type=T::nullTrapType;reject(bad);
        bad=original;bad.orders[0].type=T::nbTraps;reject(bad);
        bad=original;bad.orders[0].needed=0;reject(bad);
        bad=original;bad.orders[0].name.clear();reject(bad);
        bad=original;bad.workshops[1].name="forge";reject(bad);
        bad=original;bad.workshops[0].points=-1;reject(bad);
        bad=original;bad.workshops[0].required=-1;reject(bad);
        bad=original;bad.workshops[0].type=T::nbTraps;reject(bad);
        ODPacket truncated;truncated<<uint32_t(1)<<std::string("unfinished");
        check(!importTrapProductionData(truncated,decoded),"truncated real packet rejected");
        std::cout<<"CHECKS="<<checks<<" FAILURES=0\n";
    }catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}
}
'''.replace("REORDER", reorder)

with tempfile.TemporaryDirectory(prefix="trap-production-") as directory:
    work = Path(directory)
    cpp = work / "check.cpp"
    cpp.write_text(probe, encoding="utf-8")
    executable = work / "check.exe"
    subprocess.run([
        "cl", "/nologo", "/EHsc", "/MD", "/std:c++14",
        f"/I{root / 'source'}", f"/I{prefix / 'include'}", f"/I{prefix / 'include/OGRE'}",
        str(cpp), str(root / "source/game/TrapProductionData.cpp"),
        str(root / "source/network/ODPacket.cpp"), str(root / "source/traps/TrapType.cpp"),
        f"/Fe:{executable}", "/link", f"/LIBPATH:{prefix / 'lib'}",
        "OgreMain.lib", "sfml-network.lib", "sfml-system.lib"
    ], cwd=work, check=True)
    subprocess.run([str(executable)], cwd=work, check=True)
