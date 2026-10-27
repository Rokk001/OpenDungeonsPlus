"""Check heart source/configuration; --probe exercises protection, damage, death and saves."""
from pathlib import Path
import subprocess
import sys
from combat_heart_checks import check_heart_configuration, configure_heart_probe
import tempfile

repo = Path(__file__).resolve().parents[2]
source = (repo / 'source/rooms/RoomDungeonTemple.cpp').read_text()
header = (repo / 'source/rooms/RoomDungeonTemple.h').read_text()


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


probe = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <sstream>
#include <string>
#include <vector>
#define OD_LOG_ERR(x)
#define OD_LOG_INF(x)
namespace Ogre {typedef double Real;struct Vector3{Real x,y,z;Vector3(Real a,Real b,Real c):x(a),y(b),z(c){}};}
struct TileData {virtual ~TileData()=default;};
struct RoomTreasuryTileData:TileData {double mGoldInTile=0;std::string mMeshOfTile;};
struct Tile{int getX()const{return 3;}int getY()const{return 4;}};
struct Player {bool human=true;bool lost=false;int conqueror=-1,heartX=-1,heartY=-1,recorded=0;bool getIsHuman()const{return human;}bool getHasLost()const{return lost;}
 void recordHeartDestroyed(int c,int x,int y){conqueror=c;heartX=x;heartY=y;++recorded;}};
struct SeatStatistics {unsigned mKeepersDefeated=0;};
enum class SkillType {nullSkillType};
namespace Skills {std::string toString(SkillType){return "";}}
namespace Helper {std::string toString(int value){return std::to_string(value);}}
struct Seat {int team;Player* player=nullptr;int id=0;SeatStatistics stats;SeatStatistics& getStatistics(){return stats;}Player* getPlayer(){return player;}int getId()const{return id;}bool isAlliedSeat(Seat* s){return s&&team==s->team;}
 bool isRogueSeat()const{return false;}double getMana()const{return 0;}void revealMapPermanently(){}std::vector<SkillType> getSkillDone()const{return {};}bool addSkill(SkillType){return true;}};
enum class ServerNotificationType {chatServer};
enum class EventShortNoticeType {majorGameEvent};
struct ODPacket {std::vector<std::string> texts;int majorEvents=0;
 ODPacket& operator<<(const std::string& t){texts.push_back(t);return *this;}
 ODPacket& operator<<(EventShortNoticeType){++majorEvents;return *this;}};
struct ServerNotification {ServerNotificationType type;Player* player;ODPacket mPacket;
 ServerNotification(ServerNotificationType t,Player* p):type(t),player(p){}};
struct ODServer {std::vector<ServerNotification*> queue;
 static ODServer& getSingleton(){static ODServer server;return server;}
 void queueServerNotification(ServerNotification* n){queue.push_back(n);}};
enum class GameEntityType {creature, other};
struct CreatureDefinition {bool worker=false;bool isWorker()const{return worker;}};
struct GameEntity {Seat* seat;int deaths=0;GameEntity(Seat* s=nullptr):seat(s){}
 virtual GameEntityType getObjectType()const{return GameEntityType::other;}
 Seat* getSeat(){return seat;}void setSeat(Seat* s){seat=s;}void fireEntityDead(){++deaths;}
 virtual bool isAttackable(Tile*,Seat*)const{return false;}virtual double getHP(Tile*)const{return 0;}
 virtual double takeDamage(GameEntity*,double,double,double,double,Tile*,bool){return 0;}};
struct Creature:GameEntity {CreatureDefinition definition;Creature(Seat* s,bool worker):GameEntity(s){definition.worker=worker;}
 GameEntityType getObjectType()const override{return GameEntityType::creature;}
 const CreatureDefinition* getDefinition()const{return &definition;}};
struct GameMap {bool editor=false;int fights=0;
 bool isInEditorMode(){return editor;}void playerIsFighting(Player*,Tile*){++fights;}
 void addManaToSeat(int,int){}uint32_t getHeartDestroyedReward()const{return 0;}
 static const uint32_t SKIRMISH_HEART_REWARD_SPECIALS=1;static const uint32_t SKIRMISH_HEART_REWARD_ROOMS_AND_LAND=2;};
struct TreasuryObject {TreasuryObject(GameMap*,int){}void addToGameMap(){}void createMesh(){}void setPosition(Ogre::Vector3){}};
struct BuildingObject:GameEntity {Tile* tile;BuildingObject(Tile* t):tile(t){}Tile* getPositionTile(){return tile;}bool notifyRemoveAsked(){return true;}};
struct ODApplication {static double turnsPerSecond;};double ODApplication::turnsPerSecond=1.4;
struct Building {double floorHP=250;double getHP(Tile*)const{return floorHP;}};
struct Room:Building {
 GameMap* map;Seat* seat;int dead=0,removed=0,upkeep=0,objectsRemoved=0;std::vector<Tile*> mCoveredTiles;std::map<Tile*,TileData*> mTileData;
 void removeAllBuildingObjects(){++objectsRemoved;}void removeBuildingObject(Tile*){}
 static Tile* nineTiles(){static Tile tiles[9];return tiles;}
 Room(GameMap* m,Seat* s):map(m),seat(s){for(int i=0;i<9;++i)mCoveredTiles.push_back(nineTiles()+i);}virtual ~Room()=default;
 unsigned numCoveredTiles()const{return static_cast<unsigned>(mCoveredTiles.size());}
 GameMap* getGameMap()const{return map;}Seat* getSeat()const{return seat;}
 double getPhysicalDefense(){return 1;}double getMagicalDefense(){return 2;}double getElementDefense(){return 3;}
 void fireEntityDead(){++dead;}
 virtual bool canSeatSellBuilding(Seat*)const{return true;}
 virtual bool isAttackable(Tile*,Seat*)const{return true;}
 virtual double takeDamage(GameEntity*,double,double,double,double,Tile*,bool){return 99;}
 virtual bool removeCoveredTile(Tile* tile){++removed;
  mCoveredTiles.erase(std::remove(mCoveredTiles.begin(),mCoveredTiles.end(),tile),mCoveredTiles.end());return true;}
 virtual void doUpkeep(){++upkeep;}void announceKeeperWealth(Tile*){}
 virtual void exportToStream(std::ostream& os)const{os<<floorHP<<'\n';}
 virtual bool importFromStream(std::istream& is){return bool(is>>floorHP);}
};
enum class HeartHealthTier {healthy,damaged,critical};
struct RoomDungeonTemple:Room {
 BuildingObject* mTempleObject=nullptr;double mHeartHP=-1;bool mCriticalWarningSent=false;bool mGoldChanged=false;
 HeartHealthTier mCurrentHeartTier=HeartHealthTier::healthy;int templeRebuilds=0;
 bool getIsOnServerMap()const{return true;}
 //! \brief Records the targeted replacement without removing any ring objects.
 void replaceBuildingObject(Tile*,BuildingObject*){++templeRebuilds;}
 //! \brief Supplies the mesh argument to the extracted tier-switch method.
 static const std::string& getMeshNameForHeartTier(HeartHealthTier){static const std::string mesh="fixture";return mesh;}
 double getHeartHealthFraction()const;HeartHealthTier computeHeartHealthTier()const;void checkHeartHealthTier();
 bool isTreasuryTile(Tile*)const;void updateTreasuryMeshesForTile(Tile*,RoomTreasuryTileData*);Tile* getHeartTile()const;
 RoomDungeonTemple(GameMap* m,Seat* s):Room(m,s){}
 INLINE_METHODS
 static const double HEART_CRITICAL_FRACTION;double mHeartHPFactor=1.0;double getHeartHPFactor()const;double getHeartMaxHP()const;
 bool canAttackHeart(Tile*,Seat*)const;double getHP(Tile*)const;
 double takeHeartDamage(GameEntity*,double,double,double,double,Tile*);
 bool removeCoveredTile(Tile*)override;void doUpkeep()override;
 void exportToStream(std::ostream&)const override;bool importFromStream(std::istream&)override;
};
struct PersistentObject:BuildingObject {
 PersistentObject(GameMap*,Room&,const std::string&,Tile* t,double,bool,float,const char*,bool):BuildingObject(t){}
};
HEART_REWARD
HEART_OBJECT;
METHODS
bool RoomDungeonTemple::isTreasuryTile(Tile*)const{return false;}
void RoomDungeonTemple::updateTreasuryMeshesForTile(Tile*,RoomTreasuryTileData*){}
Tile* RoomDungeonTemple::getHeartTile()const{return nullptr;}
int checks=0,failures=0;
void check(bool ok,const char* msg){++checks;if(!ok){++failures;std::cout<<"FAIL "<<msg<<'\n';}}
int main(){
 Player ownerPlayer;Seat owner{1,&ownerPlayer},ally{1},enemy{2,nullptr,5};Tile centre,floor;BuildingObject object{&centre};
 GameMap map;RoomDungeonTemple heart(&map,&owner);DungeonHeartObject core(&map,heart,&centre,"DungeonHeartObjectHealthy");
 heart.mTempleObject=&core;heart.mCoveredTiles={&centre,&floor};
 check(core.getSeat()==&owner,"heart entity carries room ownership");
 check(RoomDungeonTemple(&map,&owner).getHeartMaxHP()==15100&&heart.getHeartMaxHP()==15100,"the configured maximum is 15100, whatever the number of tiles");
 check(heart.getHP(nullptr)==15100&&heart.floorHP==250,"an undamaged heart has 15100, independent of the floor durability");
 for(Seat* seat:{&owner,&ally,&enemy,static_cast<Seat*>(nullptr)}){
  GameEntity attacker{seat};
  check(!heart.canSeatSellBuilding(seat),"no gameplay demolition permission");
  check(!heart.isAttackable(&floor,seat)&&!heart.isAttackable(&centre,seat),"room floor is not a combat target");
  check(heart.takeDamage(&attacker,999,999,999,999,&floor,false)==0,"direct floor damage rejected");
  check(!heart.canAttackHeart(&floor,seat),"outer floor is not the heart");
  check(heart.canAttackHeart(&centre,seat)==(seat==&enemy),"only enemies can attack the heart");
  if(seat!=&enemy)check(heart.takeHeartDamage(&attacker,999,999,999,999,&centre)==0,"friendly and unknown damage rejected");
 }
 check(!heart.removeCoveredTile(&floor)&&heart.removed==0,"server refuses floor removal");
 GameEntity attacker{&enemy};
 check(heart.takeHeartDamage(nullptr,99,0,0,0,&centre)==0,"unattributed damage rejected");
 check(heart.takeHeartDamage(&attacker,99,0,0,0,&floor)==0,"enemy cannot damage the floor");
 check(core.takeDamage(&attacker,4,5,6,7,&centre,false)==16,"actual heart entity receives damage");
 check(heart.getHP(nullptr)==15084&&heart.floorHP==250,"heart damage never reduces floor health");
 // The research of the heart: the maximum follows the heart health factor, the current health grows with it, the healing follows its own factor
 {RoomDungeonTemple h(&map,&owner);h.mHeartHP=5000;gResearchHeartHP=1.698;h.doUpkeep();
  check(std::abs(h.getHeartMaxHP()-15100.0*1.698)<1e-6,"the heart health research raises the maximum");
  check(std::abs(h.getHP(nullptr)-(5000*1.698+3.775/1.4))<1e-6,"the current health grows with the maximum when a level is reached");
  gResearchHeartHP=2.474;h.doUpkeep();
  check(std::abs(h.getHP(nullptr)-((5000*1.698+3.775/1.4)*2.474/1.698+3.775/1.4))<1e-6,"the next level scales by the ratio of the factors");
  gResearchHeartHP=1.0;
  RoomDungeonTemple fresh(&map,&owner);gResearchHeartHP=1.698;fresh.doUpkeep();
  check(std::abs(fresh.getHP(nullptr)-15100.0*1.698)<1e-6,"an undamaged heart is at the new maximum");
  gResearchHeartHP=1.0;
  RoomDungeonTemple mender(&map,&owner);mender.mHeartHP=1000;gResearchHeartHeal=2.0;mender.doUpkeep();
  check(std::abs(mender.getHP(nullptr)-(1000+2*3.775/1.4))<1e-9,"the heart healing research multiplies the healing per second");
  gResearchHeartHeal=1.0;}
 check(heart.dead==0&&map.fights==1,"nonlethal hit reports combat without death");
 heart.doUpkeep();check(heart.removed==0&&heart.upkeep==1,"living heart retains all floor tiles");
 check(std::abs(heart.getHP(nullptr)-(15084+3.775/1.4))<1e-9,"a living damaged heart heals 3.775 per second, per turn 3.775 / turnsPerSecond");
 heart.mHeartHP=15084;
 std::stringstream save;heart.exportToStream(save);save<<"[/Room]\n";
 RoomDungeonTemple loaded(&map,&owner);check(loaded.importFromStream(save)&&std::abs(loaded.getHP(nullptr)-15084)<1e-6,"damaged heart round trip by share");
 std::string next;save>>next;check(next=="[/Room]","save parser preserves room boundary");
 std::stringstream legacy("80\n[/Room]\n");RoomDungeonTemple old(&map,&owner);
 check(old.importFromStream(legacy)&&old.getHP(nullptr)==15100,"a heart without a health record starts undamaged");
 legacy>>next;check(next=="[/Room]","legacy boundary not consumed");
 check(save.str().find("HeartHealthShare ")!=std::string::npos&&save.str().find("HeartHealth10000")==std::string::npos,"the health is saved as the share HeartHealthShare of the maximum");
 // New saves: the share marker reads back to the same health, also with the heart health research
 {RoomDungeonTemple h(&map,&owner);h.mHeartHP=3775;std::stringstream s;h.exportToStream(s);s<<"[/Room]\n";
  check(s.str().find("HeartHealthShare 0.25\n")!=std::string::npos,"a quarter of 15100 is saved as the share 0.25");
  RoomDungeonTemple back(&map,&owner);check(back.importFromStream(s)&&back.getHP(nullptr)==3775,"a quarter heart round-trips its share");
  RoomDungeonTemple full(&map,&owner);std::stringstream f;full.exportToStream(f);f<<"[/Room]\n";
  check(f.str().find("HeartHealthShare 1\n")!=std::string::npos,"an undamaged heart is saved as the share 1");
  RoomDungeonTemple ruin(&map,&owner);ruin.mHeartHP=0;std::stringstream r;ruin.exportToStream(r);r<<"[/Room]\n";
  RoomDungeonTemple ruinBack(&map,&owner);check(r.str().find("HeartHealthShare 0\n")!=std::string::npos&&ruinBack.importFromStream(r)&&ruinBack.getHP(nullptr)==0,"a ruin is saved as the share 0 and stays a ruin");
  gResearchHeartHP=1.698;RoomDungeonTemple big(&map,&owner);big.mHeartHP=big.getHeartMaxHP()/2;std::stringstream b;big.exportToStream(b);b<<"[/Room]\n";
  RoomDungeonTemple bigBack(&map,&owner);check(bigBack.importFromStream(b)&&std::abs(bigBack.getHP(nullptr)-15100.0*1.698/2)<1e-6,"the share survives the heart health research");
  gResearchHeartHP=1.0;}
 {std::stringstream over("250\nHeartHealthShare 2\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(over)&&h.getHP(nullptr)==15100,"a share above 1 is limited to the full heart");}
 {std::stringstream shareHalf("250\nHeartHealthShare 0.5\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(shareHalf)&&h.getHP(nullptr)==7550,"a share of one half loads as 7550");}
 // Saves made with the former maximum of 10000: the share of that maximum is kept (divided by 10000 times the research factor)
 {std::stringstream full10("250\nHeartHealth10000 10000\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(full10)&&h.getHP(nullptr)==15100,"a full heart of an old save (HeartHealth10000 10000) loads as 15100");}
 {std::stringstream half10("250\nHeartHealth10000 5000\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(half10)&&h.getHP(nullptr)==7550,"a half heart of an old save loads as 7550");}
 {gResearchHeartHP=1.698;std::stringstream fort("250\nHeartHealth10000 8490\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(fort)&&std::abs(h.getHP(nullptr)-h.getHeartMaxHP()/2)<1e-6,"an old save with the heart health research keeps its share of 10000 times the factor");gResearchHeartHP=1.0;}
 // Saves from before the heart had its own health: HeartHP was measured against the floor durability (250 here)
 {std::stringstream full("250\nHeartHP 250\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(full)&&h.getHP(nullptr)==15100,"an old save with a full heart (HeartHP equal to the floor durability) loads full");}
 {std::stringstream half("250\nHeartHP 125\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(half)&&h.getHP(nullptr)==7550,"an old half damaged heart keeps its share of the health");}
 {std::stringstream ruin("250\nHeartHP 0\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(ruin)&&h.getHP(nullptr)==0,"an old destroyed heart stays destroyed");}
 {std::stringstream big("250\nHeartHealth10000 999999\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(big)&&h.getHP(nullptr)==15100,"a saved health above the maximum is limited to it");}
 // Saves from when the heart had 10000 health per room tile (90000 for the nine tiles of these fixtures)
 {std::stringstream full("250\nHeartHealth 90000\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(full)&&h.getHP(nullptr)==15100,"a full heart of the per-tile scale stays full");}
 {std::stringstream half("250\nHeartHealth 45000\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(half)&&h.getHP(nullptr)==7550,"a damaged heart of the per-tile scale keeps its share");}
 {std::stringstream ruin("250\nHeartHealth 0\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(ruin)&&h.getHP(nullptr)==0,"a ruin of the per-tile scale stays a ruin");}
 {std::stringstream big("250\nHeartHealth 999999\n[/Room]\n");RoomDungeonTemple h(&map,&owner);
  check(h.importFromStream(big)&&h.getHP(nullptr)==15100,"a per-tile value above its maximum is limited to the full heart");}
 for(const char* text:{"250\nHeartHP -1\n", "250\nHeartHP nan\n", "250\nHeartHP nope\n", "250\nHeartHealth -1\n", "250\nHeartHealth10000 -1\n", "250\nHeartHealthShare -1\n", "250\nHeartHealthShare nan\n", "250\nHeartSomething 5\n"}){
  std::stringstream bad(text);RoomDungeonTemple invalid(&map,&owner);check(!invalid.importFromStream(bad),"invalid health rejected");}
 {Creature worker(&enemy,true);Creature fighter(&enemy,false);
  check(heart.takeHeartDamage(&worker,999,999,999,999,&centre)==0&&heart.getHP(nullptr)==15084,"an enemy worker cannot damage the heart");
  check(heart.takeHeartDamage(&fighter,4,0,0,0,&centre)==4&&heart.getHP(nullptr)==15080,"an enemy fighter damages the heart");}
 check(core.takeDamage(&attacker,99999,0,0,0,&centre,false)==15080,"lethal damage clamped");
 check(core.deaths==1&&core.getHP(nullptr)==0,"object death listeners notified");
 check(heart.dead==1&&!heart.canAttackHeart(&centre,&enemy),"death fires once and disables targeting");
 check(ownerPlayer.recorded==1&&ownerPlayer.conqueror==5&&ownerPlayer.heartX==3&&ownerPlayer.heartY==4,"owner records conqueror seat and heart tile on death");
 check(heart.takeHeartDamage(&attacker,99999,0,0,0,&centre)==0&&heart.dead==1,"dead heart cannot be hit twice");
 check(ownerPlayer.recorded==1,"conqueror recorded only once");
 check(enemy.stats.mKeepersDefeated==1&&owner.stats.mKeepersDefeated==0,"final blow counts one defeated keeper for the attacker seat only, once");
 heart.doUpkeep();check(heart.removed==0&&heart.mCoveredTiles.size()==2&&heart.objectsRemoved==1&&heart.mTempleObject==nullptr,"heart death releases only the heart object and keeps the floor");
 heart.doUpkeep();check(heart.getHP(nullptr)==0,"a destroyed heart never heals");
 {RoomDungeonTemple h(&map,&owner);h.doUpkeep();check(h.getHP(nullptr)==15100,"an undamaged heart stays at the maximum");
  h.mHeartHP=15099.5;h.doUpkeep();check(h.getHP(nullptr)==15100,"healing stops at the maximum");
  h.mHeartHP=1;h.doUpkeep();h.doUpkeep();check(std::abs(h.getHP(nullptr)-(1+2*3.775/1.4))<1e-9,"healing adds up turn by turn");
  h.mCriticalWarningSent=true;h.mHeartHP=1657;h.doUpkeep();check(h.mCriticalWarningSent,"healing inside the critical range keeps the warning spent");
  h.mHeartHP=1660;h.doUpkeep();check(!h.mCriticalWarningSent,"healing above 11 % re-arms the critical warning");}
 // The heart object follows the health tier, but a destroyed heart is only released (never rebuilt)
 {BuildingObject obj{&centre};RoomDungeonTemple h(&map,&owner);h.mTempleObject=&obj;h.doUpkeep();
  check(h.templeRebuilds==0,"a healthy heart keeps its object");
  h.mHeartHP=5000;h.doUpkeep();check(h.templeRebuilds==1&&h.mTempleObject->getPositionTile()==&centre&&h.objectsRemoved==0,"a lower tier replaces only the heart on its existing tile");
  h.mHeartHP=0;h.doUpkeep();check(h.templeRebuilds==1,"a destroyed heart is not rebuilt as a critical one");}
 // Critical-health warning (threshold 11 % of 15100 = 1661)
 ODServer& server=ODServer::getSingleton();GameEntity hitter{&enemy};
 const char* warning="Your dungeon heart is in critical condition!";
 {server.queue.clear();BuildingObject obj{&centre};RoomDungeonTemple h(&map,&owner);h.mTempleObject=&obj;
  h.takeHeartDamage(&hitter,13300,0,0,0,&centre);
  h.takeHeartDamage(&hitter,138.9,0,0,0,&centre);
  check(server.queue.empty(),"no warning above 11 percent");
  h.takeHeartDamage(&hitter,0.2,0,0,0,&centre);
  check(server.queue.size()==1,"exactly one warning at the threshold");
  if(server.queue.size()==1){ServerNotification* n=server.queue[0];
   check(n->type==ServerNotificationType::chatServer&&n->player==&ownerPlayer,"warning goes to the owner only");
   check(n->mPacket.texts.size()==1&&n->mPacket.texts[0]==warning&&n->mPacket.majorEvents==1,"warning text and event type");}
  h.takeHeartDamage(&hitter,1,0,0,0,&centre);h.takeHeartDamage(&hitter,1,0,0,0,&centre);
  check(server.queue.size()==1,"no second warning on further hits");
  h.takeHeartDamage(&hitter,99999,0,0,0,&centre);
  check(h.dead==1&&server.queue.size()==1,"killing hit sends no extra warning");}
 {server.queue.clear();BuildingObject obj{&centre};RoomDungeonTemple h(&map,&owner);h.mTempleObject=&obj;h.mHeartHP=20;
  h.takeHeartDamage(&hitter,1,0,0,0,&centre);
  check(server.queue.size()==1,"first hit while already below the threshold warns once");
  h.takeHeartDamage(&hitter,1,0,0,0,&centre);
  check(server.queue.size()==1,"no repeat after a low first hit");}
 {server.queue.clear();BuildingObject obj{&centre};RoomDungeonTemple h(&map,&owner);h.mTempleObject=&obj;h.mHeartHP=20;
  h.takeHeartDamage(&hitter,999,0,0,0,&centre);
  check(h.dead==1&&server.queue.empty(),"killing hit from below the threshold sends no warning");}
 {server.queue.clear();BuildingObject obj{&centre};RoomDungeonTemple h(&map,&owner);h.mTempleObject=&obj;
  h.takeHeartDamage(&hitter,99999,0,0,0,&centre);
  check(h.dead==1&&server.queue.empty(),"one-blow kill from full health sends no warning");}
 {Player bot;bot.human=false;Player loser;loser.lost=true;Seat botSeat{1,&bot},lostSeat{1,&loser},emptySeat{1};
  for(Seat* seat:{&botSeat,&lostSeat,&emptySeat}){
   server.queue.clear();BuildingObject obj{&centre};RoomDungeonTemple h(&map,seat);h.mTempleObject=&obj;h.mHeartHP=20;
   h.takeHeartDamage(&hitter,1,0,0,0,&centre);
   check(server.queue.empty(),"no warning for a non-human, lost or absent owner");}}
 {server.queue.clear();map.editor=true;BuildingObject obj{&centre};RoomDungeonTemple h(&map,&owner);h.mTempleObject=&obj;h.mHeartHP=20;
  h.takeHeartDamage(&hitter,1,0,0,0,&centre);map.editor=false;
  check(server.queue.empty(),"no warning in editor mode");}
 {Player p;Seat s{1,&p};BuildingObject noTile{nullptr};RoomDungeonTemple h(&map,&s);h.mTempleObject=&noTile;
  h.takeHeartDamage(&hitter,99999,0,0,0,nullptr);check(p.recorded==1&&p.conqueror==5&&p.heartX==-1&&p.heartY==-1,"unknown centre tile is recorded as -1/-1");}
 map.editor=true;RoomDungeonTemple edit(&map,&owner);edit.mCoveredTiles={&floor};edit.mTileData[&floor]=new RoomTreasuryTileData;
 check(edit.removeCoveredTile(&floor),"editor editing preserved");
 std::stringstream level;edit.exportToStream(level);check(level.str().find("Heart")==std::string::npos,"editor maps do not persist combat damage");
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}
'''
inline = '\n'.join(function(header, sig) for sig in
                   ('bool canSeatSellBuilding(', 'bool isAttackable(', 'double takeDamage('))
methods = '\n'.join(function(source, sig) for sig in (
    'double RoomDungeonTemple::getHeartHealthFraction(', 'HeartHealthTier RoomDungeonTemple::computeHeartHealthTier(',
    'void RoomDungeonTemple::checkHeartHealthTier(',
    'double RoomDungeonTemple::getHP(', 'double RoomDungeonTemple::getHeartHPFactor(', 'double RoomDungeonTemple::getHeartMaxHP(', 'bool RoomDungeonTemple::canAttackHeart(',
    'double RoomDungeonTemple::takeHeartDamage(', 'bool RoomDungeonTemple::removeCoveredTile(',
    'void RoomDungeonTemple::doUpkeep(', 'void RoomDungeonTemple::exportToStream(',
    'bool RoomDungeonTemple::importFromStream('))
methods = source[source.index('const double RoomDungeonTemple::HEART_CRITICAL_FRACTION'):source.index('RoomDungeonTemple::RoomDungeonTemple(')] + methods
# The placeholders are whole lines, so that names that contain them (e.g. the skirmish reward constants) stay untouched
probe = probe.replace('\n INLINE_METHODS\n', '\n' + inline + '\n').replace('\nMETHODS\n', '\n' + methods + '\n')
probe = probe.replace('\nHEART_OBJECT;\n', '\n' + function(source, 'class DungeonHeartObject :') + ';\n')
# The reward for destroying a heart is a file-local helper called by takeHeartDamage
# (the special objects and the room hand over are checked in check_skirmish_settings.py)
reward = ('void placeHeartRewardSpecials(GameMap*, Seat*, Tile*) {}\n'
          'void giveHeartRewardRoomsAndLand(GameMap*, Seat*, Seat*) {}\n')
tier_source = (repo / 'source/rooms/HeartHealthTier.cpp').read_text()
tier = tier_source[tier_source.index('namespace'):] + '\n'
probe = probe.replace('\nHEART_REWARD\n', '\n' + tier + reward + function(source, 'void giveDestroyedHeartReward(') + '\n')
check_heart_configuration(repo)
if '--probe' not in sys.argv:
    print('Source checks passed; compiled probe requires --probe')
    raise SystemExit(0)
probe = configure_heart_probe(probe)

with tempfile.TemporaryDirectory(prefix='odp-heart-combat-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++17', 'check.cpp', '/Fecheck.exe'], cwd=work, check=True)
    subprocess.run([str(work / 'check.exe')], cwd=work, check=True)
