"""Execute production room availability and aggregation rules against controlled owner fixtures."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def body(path, signature):
    """Extract the unchanged production function including its signature."""
    source = (ROOT / path).read_text(encoding="utf-8")
    start = source.index(signature)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    """Compile actual rule bodies and verify red, yellow, green and reserved-place transitions."""
    header = (ROOT / "source/rooms/RoomManagerStatus.h").read_text(encoding="utf-8")
    header = header.replace('#include "rooms/RoomType.h"',
        (ROOT / "source/rooms/RoomType.h").read_text(encoding="utf-8"))
    spa = (ROOT / "source/rooms/RoomSpaLayout.h").read_text(encoding="utf-8")
    code = r'''
#include <algorithm>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>
#include <vector>
#include <string>
void check(bool ok,const char* name){if(!ok)throw std::runtime_error(name);}
'''+header+spa+r'''
struct Seat { int mode=0;int getLabMode()const{return mode;} };
struct Creature {std::string name="guest";uint32_t places=1;const std::string& getName()const{return name;}Seat* seat=nullptr;uint32_t level=1;bool alive=true;
 Seat* getSeat()const{return seat;}bool isAlive()const{return alive;}uint32_t getLevel()const{return level;} };
struct PotionDefinition {std::string id="heal",kind="HealPercent",size="Small";uint32_t level=1;std::map<std::string,uint32_t> herbs{{"mint",1}};
 const std::string& getId()const{return id;}const std::string& getKind()const{return kind;}
 const std::string& getSize()const{return size;}uint32_t getLevelMin()const{return level;}
 const std::map<std::string,uint32_t>& getHerbs()const{return herbs;} };
struct ConfigManager {std::vector<PotionDefinition> potions{PotionDefinition()};
 static ConfigManager& getSingleton(){static ConfigManager instance;return instance;}
 const std::vector<PotionDefinition>& getPotions()const{return potions;}
 uint32_t getRoomConfigUInt32(const char*)const{return 3;}
 double getRoomConfigDoubleOrDefault(const std::string&,double value)const{return value;} };
struct RoomMerchant {static uint32_t countPotion(...){return 0;}static uint32_t recentPotionSales(...){return 0;}};
enum class GameEntityType {craftedTrap,giftBoxEntity};
enum class GiftBoxType {item};
struct GameEntity {virtual ~GameEntity(){};virtual GameEntityType getObjectType()const{return GameEntityType::giftBoxEntity;}};
struct GiftBoxEntity:GameEntity {GiftBoxType getGiftBoxType()const{return GiftBoxType::item;}};
struct GiftBoxItem:GiftBoxEntity {bool canCrack(const Seat&)const{return true;}};
struct Trap {Seat* seat=nullptr;int needed=1;Seat* getSeat()const{return seat;}int getNbNeededCraftedTrap()const{return needed;}};
enum class TrapType {nullTrapType,ordered};
struct Tile {std::vector<GameEntity*> entities;const std::vector<GameEntity*>& getEntitiesInTile()const{return entities;}uint32_t finished=0;uint32_t countEntitiesOnTile(GameEntityType)const{return finished;}};
struct Room {RoomType type;Seat* seat;virtual ~Room(){};};
struct GameMap {std::vector<Trap*> traps;const std::vector<Trap*>& getTraps()const{return traps;}std::vector<Creature*> creatures;std::vector<Room*> rooms;
 const std::vector<Creature*>& getCreatures()const{return creatures;}
 std::vector<Room*> getRoomsByTypeAndSeat(RoomType type,Seat* seat){std::vector<Room*> result;for(Room* room:rooms)if(room->type==type&&room->seat==seat)result.push_back(room);return result;} };
struct TileData {virtual ~TileData(){}};
struct AlchemyLabTileData:TileData {bool mReserved=false;};
struct RoomAlchemyLab:Room {std::map<Tile*,TileData*> mTileData;std::map<std::string,uint32_t> mHerbs;
 std::vector<std::pair<std::string,double>> mPausedBatches;uint32_t finished=0;GameMap* map;
 GameMap* getGameMap()const{return map;}Seat* getSeat()const{return seat;}
 uint32_t finishedCount()const{return finished;}
 static uint32_t countWaitingPotion(...){return 0;}
 bool canBrew(const PotionDefinition&)const;const PotionDefinition* choosePotion()const;
 RoomManagerDot getRoomManagerDot()const;
};
struct RoomCasinoGameCreatureInfo {Creature* mCreature=nullptr;};
struct RoomCasinoGame {RoomCasinoGameCreatureInfo mCreature1,mCreature2;};
struct RoomCasino:Room {std::map<Tile*,RoomCasinoGame> mCreaturesSpots;bool hasRoomManagerPlace()const;};
struct RoomInfirmary:Room {struct CotInfo{};struct PatientInfo{Creature* creature=nullptr;Creature* reservedBy=nullptr;};
 std::map<size_t,CotInfo> mCots;std::map<size_t,PatientInfo> mPatients;bool hasRoomManagerPlace()const;};
struct RoomSpaBather {SpaBlock mBlock;};
struct RoomSpaPendingBather {SpaBlock mBlock;};
struct Attendant {bool getPlace(int32_t&,int32_t&)const{return false;}};
struct RoomSpa:Room {SpaTileSet pool;std::vector<RoomSpaBather> mBathers;std::map<std::string,RoomSpaPendingBather> mPendingBathers;
 Attendant* mAttendant=nullptr;SpaTileSet getPoolSet()const{return pool;}SpaTileSet getTakenSet()const;bool hasRoomManagerPlace()const;};
const uint32_t TAVERN_SEATS_PER_TABLE=8,TAVERN_PLACES_PER_TABLE=10,TAVERN_SEATS_PER_BENCH=4;
struct RoomTavernSeat {Tile* mTable;uint32_t mIndex;RoomTavernSeat(Tile* tile,uint32_t index):mTable(tile),mIndex(index){}
 bool operator<(const RoomTavernSeat& other)const{return mTable!=other.mTable?mTable<other.mTable:mIndex<other.mIndex;}
 bool operator==(const RoomTavernSeat& other)const{return mTable==other.mTable&&mIndex==other.mIndex;}};
struct RoomTavernSpot{uint32_t mPlaces=1;};
struct RoomTavernPendingSpot{RoomTavernSeat mSeat;RoomTavernPendingSpot():mSeat(nullptr,0){}};
bool hasTavernBlock(const std::vector<Tile*>& tiles){return !tiles.empty();}
struct RoomTavern:Room {GameMap* map=nullptr;std::vector<Tile*> mCoveredTiles;
 std::map<RoomTavernSeat,RoomTavernSpot> mSpots;std::map<std::string,RoomTavernPendingSpot> mPendingSpots;
 GameMap* getGameMap()const{return map;}std::vector<Tile*> getTableTiles()const{return mCoveredTiles;}
 bool isFreeSeat(const RoomTavernSeat&,uint32_t)const;bool isFreeStool(const Creature&,const RoomTavernSeat&)const{return false;}
 bool isBenchBlocked(Tile*,uint32_t)const{return false;}bool isPlaceBlockedByStool(const RoomTavernSeat&,uint32_t)const{return false;}
 static uint32_t getPlacesOf(const Creature& creature){return creature.places;}bool hasRoomManagerPlace()const;
};
struct RoomWorkshop:Room {GameMap* map=nullptr;GameMap* getGameMap()const{return map;}Seat* getSeat()const{return seat;}std::vector<Tile*> mCoveredTiles,mUnusedSpots;std::map<Creature*,Tile*> mCreaturesSpots;
 TrapType mTrapType=TrapType::nullTrapType;void* mCrackBox=nullptr;uint32_t places=3;
 uint32_t getNumActiveSpots()const{return places;}RoomManagerDot getRoomManagerDot()const;};
'''
    for path, signature in [
        ("source/rooms/RoomAlchemyLab.cpp", "bool usableSize("),
        ("source/rooms/RoomAlchemyLab.cpp", "bool RoomAlchemyLab::canBrew("),
        ("source/rooms/RoomAlchemyLab.cpp", "const PotionDefinition* RoomAlchemyLab::choosePotion("),
        ("source/rooms/RoomAlchemyLab.cpp", "RoomManagerDot RoomAlchemyLab::getRoomManagerDot("),
        ("source/rooms/RoomTavern.cpp", "bool RoomTavern::isFreeSeat("),
        ("source/rooms/RoomTavern.cpp", "bool RoomTavern::hasRoomManagerPlace("),
        ("source/rooms/RoomCasino.cpp", "bool RoomCasino::hasRoomManagerPlace("),
        ("source/rooms/RoomInfirmary.cpp", "bool RoomInfirmary::hasRoomManagerPlace("),
        ("source/rooms/RoomSpa.cpp", "SpaTileSet RoomSpa::getTakenSet("),
        ("source/rooms/RoomSpa.cpp", "bool RoomSpa::hasRoomManagerPlace("),
        ("source/rooms/RoomWorkshop.cpp", "RoomManagerDot RoomWorkshop::getRoomManagerDot("),
        ("source/network/ODServer.cpp", "    std::array<RoomManagerEntry, 8> countRoomManagerEntries(")]:
        code += body(path, signature) + "\n"
    code += r'''
int main(){
 Seat owner,other;Creature creature;creature.seat=&owner;GameMap map;map.creatures.push_back(&creature);
 Tile tile;AlchemyLabTileData cauldron;RoomAlchemyLab lab;lab.type=RoomType::alchemyLab;lab.seat=&owner;lab.map=&map;lab.mTileData[&tile]=&cauldron;
 check(lab.getRoomManagerDot()==RoomManagerDot::red,"empty idle lab red");
 lab.mHerbs["mint"]=2;check(lab.getRoomManagerDot()==RoomManagerDot::green,"usable stored recipe green");
 lab.mHerbs["mint"]=0;cauldron.mReserved=true;check(lab.getRoomManagerDot()==RoomManagerDot::yellow,"last potion brewing yellow, herbs already consumed");
 check(lab.getRoomManagerDot()==RoomManagerDot::yellow,"reserved unstaffed paused cauldron still brewing");
 cauldron.mReserved=false;lab.mPausedBatches.push_back(std::make_pair("heal",2.0));check(lab.getRoomManagerDot()==RoomManagerDot::yellow,"displaced paused batch brewing");
 lab.mPausedBatches.clear();lab.mHerbs["mint"]=2;owner.mode=2;check(lab.getRoomManagerDot()==RoomManagerDot::red,"mode excludes stored recipe red");
 owner.mode=0;ConfigManager::getSingleton().potions[0].level=5;check(lab.getRoomManagerDot()==RoomManagerDot::red,"herbs only for unusable level red");
 creature.level=5;check(lab.getRoomManagerDot()==RoomManagerDot::green,"level permits recipe green");
 lab.finished=3;check(lab.getRoomManagerDot()==RoomManagerDot::red,"finished potion capacity red");
 lab.finished=2;check(lab.getRoomManagerDot()==RoomManagerDot::green,"one potion place free green");
 RoomCasino casino;casino.type=RoomType::casino;casino.seat=&owner;check(!casino.hasRoomManagerPlace(),"casino without furniture red");
 casino.mCreaturesSpots[&tile]=RoomCasinoGame();check(casino.hasRoomManagerPlace(),"casino free place green regardless money setting");
 casino.mCreaturesSpots[&tile].mCreature1.mCreature=&creature;casino.mCreaturesSpots[&tile].mCreature2.mCreature=&creature;
 check(!casino.hasRoomManagerPlace(),"full casino red regardless payout");
 RoomInfirmary first,second;first.type=second.type=RoomType::infirmary;first.seat=second.seat=&owner;
 check(!first.hasRoomManagerPlace(),"infirmary no places red");first.mCots[1]=RoomInfirmary::CotInfo();check(first.hasRoomManagerPlace(),"cot any size free green");
 first.mPatients[1].reservedBy=&creature;check(!first.hasRoomManagerPlace(),"carried patient reservation taken");
 first.mPatients[1].creature=&creature;check(!first.hasRoomManagerPlace(),"patient taken even healing paused");
 second.mCots[2]=RoomInfirmary::CotInfo();map.rooms={&first,&second};check(countRoomManagerEntries(&map,&owner)[4].dot==RoomManagerDot::green,"one full and one free infirmary green");
 second.mPatients[2]=RoomInfirmary::PatientInfo();check(countRoomManagerEntries(&map,&owner)[4].dot==RoomManagerDot::red,"every infirmary full red");
 RoomSpa spa;spa.type=RoomType::spa;spa.seat=&owner;check(!spa.hasRoomManagerPlace(),"spa no bath places red");spa.pool.insert({0,0});check(spa.hasRoomManagerPlace(),"small free bath place green");
 spa.mPendingBathers["saved"]=RoomSpaPendingBather();check(!spa.hasRoomManagerPlace(),"saved bath reservation taken");spa.mPendingBathers.clear();spa.mBathers.push_back(RoomSpaBather());check(!spa.hasRoomManagerPlace(),"arriving bath reservation taken");
 RoomWorkshop workshop;workshop.type=RoomType::workshop;workshop.seat=&owner;workshop.map=&map;workshop.mCoveredTiles.push_back(&tile);workshop.mUnusedSpots.push_back(&tile);tile.finished=3;
 check(workshop.getRoomManagerDot()==RoomManagerDot::green,"workshop no order green even full");
 Trap queued;queued.seat=&owner;map.traps.push_back(&queued);check(workshop.getRoomManagerDot()==RoomManagerDot::red,"queued order before assignment red");map.traps.clear();
 GiftBoxItem queuedBox;tile.entities.push_back(&queuedBox);check(workshop.getRoomManagerDot()==RoomManagerDot::red,"delivered box before assignment red");tile.entities.clear();workshop.mTrapType=TrapType::ordered;check(workshop.getRoomManagerDot()==RoomManagerDot::red,"trap order with full output red");
 tile.finished=2;check(workshop.getRoomManagerDot()==RoomManagerDot::green,"workshop output space green");workshop.mTrapType=TrapType::nullTrapType;workshop.mCrackBox=&tile;check(workshop.getRoomManagerDot()==RoomManagerDot::green,"box cracking without trap orders green with space");
 tile.finished=3;check(workshop.getRoomManagerDot()==RoomManagerDot::red,"box work full finished trap output red");workshop.mUnusedSpots.clear();check(workshop.getRoomManagerDot()==RoomManagerDot::green,"workshop without work places green");
 RoomTavern tavern;tavern.type=RoomType::tavern;tavern.seat=&owner;tavern.map=&map;map.rooms={&tavern};check(countRoomManagerEntries(&map,&owner)[2].dot==RoomManagerDot::red,"full tavern red with no beer research");tavern.mCoveredTiles.push_back(&tile);check(countRoomManagerEntries(&map,&owner)[2].dot==RoomManagerDot::green,"free tavern green with no beer research");
 for(uint32_t index=0;index<8;++index)tavern.mSpots[RoomTavernSeat(&tile,index)]=RoomTavernSpot();
 check(!tavern.hasRoomManagerPlace(),"every tavern seat taken red");tavern.mSpots.erase(RoomTavernSeat(&tile,7));check(tavern.hasRoomManagerPlace(),"one tavern seat free green");
 tavern.mPendingSpots["guest"].mSeat=RoomTavernSeat(&tile,7);check(!tavern.hasRoomManagerPlace(),"saved tavern reservation taken");tavern.mPendingSpots.clear();
 Room ghost,merchant;ghost.type=RoomType::ghostRoom;ghost.seat=&owner;merchant.type=RoomType::merchant;merchant.seat=&owner;map.rooms={&ghost,&merchant};
 std::array<RoomManagerEntry,8> entries=countRoomManagerEntries(&map,&owner);check(entries[0].dot==RoomManagerDot::green,"ghost always green independently of loose ectoplasm");check(entries[1].dot==RoomManagerDot::none,"merchant no dot");
 check(entries[0].count==1&&entries[1].count==1&&entries[2].count==0,"owned type counts");check(roomManagerButtonDot(entries)==RoomManagerDot::green,"absent red rows ignored");
 entries[5].count=1;entries[5].dot=RoomManagerDot::yellow;check(roomManagerButtonDot(entries)==RoomManagerDot::yellow,"yellow button if no red");entries[4].count=1;entries[4].dot=RoomManagerDot::red;check(roomManagerButtonDot(entries)==RoomManagerDot::red,"red button precedes yellow");
 map.rooms={&ghost,&merchant,&tavern,&spa,&first,&second,&lab,&casino,&workshop};entries=countRoomManagerEntries(&map,&owner);for(const RoomManagerEntry& entry:entries)check(entry.type==RoomType::alchemyLab||entry.dot!=RoomManagerDot::yellow,"yellow lab only");
 check(countRoomManagerEntries(&map,&other)[4].count==0,"foreign rooms never exposed");
 std::cout<<"Room Manager status production rules: OK\n";
}
'''
    # The probe uses real room rules with controlled services and never links or starts the game.
    with tempfile.TemporaryDirectory(prefix="room-manager-status-") as directory:
        work = Path(directory)
        source, binary = work / "check.cpp", work / "check.exe"
        source.write_text(code, encoding="utf-8")
        subprocess.run(["cl", "/nologo", "/EHsc", "/MD", str(source), "/Fe:" + str(binary)],
            cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=180)
        subprocess.run([str(binary)], cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=180)


if __name__ == "__main__":
    main()
