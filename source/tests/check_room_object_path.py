"""Compile and exercise the production furniture route geometry without a game."""
from pathlib import Path
import os
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])
probe = r'''
#include "gamemap/RoomObjectPath.h"
#include <OgreQuaternion.h>
#include <iostream>
#include <chrono>
using namespace RoomObjectPath;
int checks=0,failures=0;
void check(bool ok,const char* reason){++checks;if(!ok){++failures;std::cout<<"FAIL "<<reason<<'\n';}}
Obstacle box(float x,float y,float angle=0){return {{-.403275f,-.6f},{.996725f,.6f},{x,y},std::cos(angle),std::sin(angle)};}
int main(){
 const TerrainSegment floor=[](const Ogre::Vector2& a,const Ogre::Vector2& b){return a.x>=0&&a.y>=0&&b.x>=0&&b.y>=0&&a.x<=12&&a.y<=12&&b.x<=12&&b.y<=12;};
 for(float angle:{0.f,.5235988f,1.5707963f,3.1415927f}){
  std::vector<Obstacle> obstacles{box(5,5,angle)};
  for(const auto& start:{Ogre::Vector2(2,5),Ogre::Vector2(5,2),Ogre::Vector2(2,2)}){
   const auto goal=Ogre::Vector2(10,10)-start;
   std::vector<Ogre::Vector2> path;
   check(route(start,goal,obstacles,0,0,12,12,floor,path),"route exists around rotated coop");
   auto previous=start;
   for(const auto& p:path){check(clearPoint(obstacles,p),"waypoint clears furniture");check(clearSegment(obstacles,previous,p),"entire leg clears furniture");previous=p;}
   check(!path.empty()&&path.back()==goal,"precise endpoint retained");
  }
 }
 std::vector<Obstacle> thin{{{-.01f,-1.f},{.01f,1.f},{5,5},1,0}};
 check(!clearSegment(thin,{4,5},{6,5}),"thin object blocks crossing with both endpoints outside");
 check(clearSegment(thin,{4,6},{6,6}),"tangency outside interior stays open");
 check(!clearSegment(thin,{5,5},{6,5}),"ordinary movement cannot start in furniture");
 check(clearSegment(thin,{5,5},{6,5},true),"legacy overlap can exit");
 check(!clearSegment(thin,{4,5},{5,5},true),"exit permission never admits a blocked destination");
 std::vector<Obstacle> furniture{box(5,5),box(7,5),box(5,8),box(7,8)};
 std::vector<Ogre::Vector2> path;
 check(route({2,5},{10,5},furniture,0,0,12,12,floor,path),"multiple furniture objects can be bypassed");
 auto previous=Ogre::Vector2(2,5);
 for(const auto& p:path){check(clearSegment(furniture,previous,p),"no corner cutting between adjacent objects");previous=p;}
 check(!route({2,5},{5,5},furniture,0,0,12,12,floor,path)&&path.empty(),"unusable furniture endpoint fails without a partial unsafe route");
 check(route({5,5},{2,5},furniture,0,0,12,12,floor,path),"creature already inside coop can escape");
 previous={5,5};bool first=true;
 for(const auto& p:path){check(clearSegment(furniture,previous,p,first),"escape never re-enters furniture");previous=p;first=false;}
 const TerrainSegment closedDoor=[](const Ogre::Vector2& a,const Ogre::Vector2& b){return !(std::min(a.x,b.x)<6&&std::max(a.x,b.x)>=6);};
 check(!route({2,5},{10,5},furniture,0,0,12,12,closedDoor,path),"no route crosses a closed door");
 const TerrainSegment gap=[](const Ogre::Vector2& a,const Ogre::Vector2& b){
  for(int i=0;i<=20;++i){const auto p=a+(b-a)*(i/20.f);if(p.x>5.8f&&p.x<6.2f&&p.y<9)return false;}return true;
 };
 check(route({2,5},{10,5},furniture,0,0,12,12,gap,path),"terrain detour is retained while avoiding furniture");
 previous={2,5};for(const auto& p:path){check(gap(previous,p),"every routed leg respects terrain");previous=p;}
 check(route({1.13f,1.27f},{3.71f,2.12f},{},0,0,12,12,floor,path)&&path.size()==1&&path.back()==Ogre::Vector2(3.71f,2.12f),"unobstructed precise movement is unchanged");
 // Check the body transform independently with Ogre's rotation of native -Y,
 // including an asymmetric forward weapon and rotated furniture.
 for(float rotation:{0.f,.5235988f,1.5707963f})for(int dy=-1;dy<=1;++dy)for(int dx=-1;dx<=1;++dx){
  if(dx==0&&dy==0)continue;
  const auto heading=Ogre::Vector2(float(dx),float(dy)).normalisedCopy();
  Obstacle obstacle=box(5,5,rotation);obstacle.bodyMinimum={-.2f,-.9f};obstacle.bodyMaximum={.3f,.4f};
  const Ogre::Quaternion orientation(Ogre::Radian(std::atan2(heading.x,-heading.y)),Ogre::Vector3::UNIT_Z);
  const auto overlaps=[&](const Ogre::Vector2& point){
   Ogre::Vector2 low(std::numeric_limits<float>::infinity()),high(-std::numeric_limits<float>::infinity());
   for(float x:{-.2f,.3f})for(float y:{-.9f,.4f}){
    const auto world=orientation*Ogre::Vector3(x,y,0);
    const auto local=obstacle.local(point+Ogre::Vector2(world.x,world.y));low.makeFloor(local);high.makeCeil(local);
   }
   return high.x>obstacle.minimum.x&&low.x<obstacle.maximum.x&&high.y>obstacle.minimum.y&&low.y<obstacle.maximum.y;
  };
  for(int y=0;y<11;++y)for(int x=0;x<11;++x){
   const Ogre::Vector2 point(2.13f+x*.57f,2.27f+y*.51f);
   check(obstacle.contains(point,heading)==overlaps(point),"directional body clearance matches Ogre-rotated envelope");
  }
  const auto from=Ogre::Vector2(5,5)-heading*3, to=Ogre::Vector2(5,5)+heading*3;
  check(obstacle.intersects(from,to),"directional full segment cannot tunnel through furniture");
 }
 // A valid terrain tile can be enclosed by furniture: the original tile
 // pathfinder still reaches it, but the body-aware path must reject it cheaply.
 std::vector<Obstacle> enclosed{
  {{-1,-.05f},{1,.05f},{100,99},1,0},{{-1,-.05f},{1,.05f},{100,101},1,0},
  {{-.05f,-1},{.05f,1},{99,100},1,0},{{-.05f,-1},{.05f,1},{101,100},1,0}};
 for(auto& obstacle:enclosed){obstacle.bodyMinimum={-.2f,-.3f};obstacle.bodyMaximum={.2f,.3f};}
 int terrainChecks=0;
 const TerrainSegment openFloor=[&](const Ogre::Vector2&,const Ogre::Vector2&){++terrainChecks;return true;};
 const auto began=std::chrono::steady_clock::now();
 check(!route({10,10},{100,100},enclosed,0,0,127,127,openFloor,path)&&path.empty(),"furniture-enclosed destination fails without an unsafe route");
 check(terrainChecks<1000,"enclosed destination rejection does not explore the entire map");
 std::cout<<"ENCLOSED_GOAL_MS="<<std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-began).count()<<'\n';
 terrainChecks=0;
 check(!route({100,100},{10,10},enclosed,0,0,127,127,openFloor,path)&&path.empty(),"furniture-enclosed start fails without searching the remote open component");
 check(terrainChecks<1000,"enclosed start rejection does not explore the entire map");
 // Reverse expansion must query forward terrain edges, not assume symmetry.
 const TerrainSegment oneWay=[](const Ogre::Vector2& a,const Ogre::Vector2& b){return b.x>=a.x;};
 check(route({2,5},{10,5},furniture,0,0,12,12,oneWay,path),"bidirectional search preserves a forward-only detour");
 previous={2,5};for(const auto& p:path){check(oneWay(previous,p)&&clearSegment(furniture,previous,p),"each reconstructed edge keeps its forward terrain and obstacle direction");previous=p;}
 check(!route({10,5},{2,5},furniture,0,0,12,12,oneWay,path),"reverse search cannot reverse one-way terrain permissions");
 size_t chosen=0;
 const std::vector<Ogre::Vector2> foodGoals{{100,100},{11,12}};
 check(routeToAny({10,10},foodGoals,enclosed,0,0,127,127,openFloor,path,chosen)&&chosen==1&&path.back()==foodGoals[chosen],"an enclosed food candidate does not hide another reachable approach");
 const std::vector<Ogre::Vector2> detourGoals{{5,5},{10,5},{9,5}};
 check(routeToAny({2,5},detourGoals,furniture,0,0,12,12,floor,path,chosen)&&chosen>0&&path.back()==detourGoals[chosen],"shared search reconstructs the selected food approach after a detour");
 previous={2,5};for(const auto& p:path){check(clearSegment(furniture,previous,p)&&floor(previous,p),"shared-search route does not cut through furniture or terrain");previous=p;}
 check(!routeToAny({10,10},{{100,100},{100.1f,100.1f}},enclosed,0,0,127,127,openFloor,path,chosen)&&path.empty(),"all enclosed food candidates fail in one shared search");
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}
'''
with tempfile.TemporaryDirectory(prefix='odp-room-path-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/O2', '/std:c++14', f'/I{repo / "source"}',
                    f'/I{prefix / "include/OGRE"}', 'check.cpp', '/Fecheck.exe', '/link',
                    f'/LIBPATH:{prefix / "lib"}', 'OgreMain.lib'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
