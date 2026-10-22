"""Compile the actual research rules, Seat methods and packet/save paths.

Run in the maintained Windows developer environment; no game is launched.
World/UI services are fixtures; research methods and wire codec are production code.
"""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
prefix = Path(os.environ["CMAKE_PREFIX_PATH"])


def function(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


seat = (root / "source/game/Seat.cpp").read_text(encoding="utf-8")
manager = (root / "source/game/SkillManager.cpp").read_text(encoding="utf-8")
skill = (root / "source/game/Skill.cpp").read_text(encoding="utf-8")
client = (root / "source/network/ODClient.cpp").read_text(encoding="utf-8")
server = (root / "source/network/ODServer.cpp").read_text(encoding="utf-8")
BRIEF = chr(92) + "brief"
tab_prefix = manager[manager.index("//! " + BRIEF + " Path prefix of the research buttons of the Rooms tab"):
                     manager.index("//! " + BRIEF + " Titles of the tabs")]
no_parents = "static const std::vector<SkillType> NO_PARENTS;"
assert no_parents in manager
seat_levels = seat[seat.index("//! " + BRIEF + " Highest research level of a skill"):seat.index("const std::string Seat::PLAYER_TYPE_HUMAN")]
definitions = tab_prefix + "\n" + no_parents + "\n" + function(manager, "SkillTab getTabOfPrefix(") + "\n" + seat_levels + "\n"
definitions += skill[skill.index("Skill::Skill("):]
definitions += "\n" + "\n".join(function(manager, signature) for signature in [
    "static Skill* createSkill(", "static void registerSkillDef(",
    "SkillManager::SkillManager()", "const Skill* SkillManager::getSkill(",
    "SkillTab SkillManager::getSkillTab(", "void SkillManager::listTabSkills(",
    "bool SkillManager::isAllSkillsDoneForSeat(",
    "double SkillManager::getResearchValue(const Seat*", "double SkillManager::getResearchValue(SkillType",
    "void SkillManager::buildRandomPendingSkillsForSeat("])
definitions += "\n" + "\n".join(function(seat, signature) for signature in [
    "bool Seat::addSkill(", "bool Seat::isSkillDone(", "uint32_t Seat::getSkillLevel(",
    "void Seat::setResearchLevels(", "void Seat::completeResearch(", "void Seat::addSkillPoints(",
    "void Seat::setNextSkill(", "void Seat::setSkillsDone(", "void Seat::setSkillTree(",
    "bool Seat::isSkillNotAllowed(", "uint32_t Seat::getQueuedSkillLevel(",
    "std::vector<std::pair<SkillType, int> > Seat::getQueuedLevels(", "const char* Seat::getResearchGateFailure(",
    "bool Seat::canResearchLevel(", "void Seat::addFreeLevelOneSkills("])
load = seat[seat.index("    uint32_t nbSkill =", seat.index("bool Seat::importSeatFromStream")):
            seat.index("    // Note: At this point, we are reading seats")]
save_start = seat.index('    os << "[SkillDone]"')
save = seat[save_start:seat.index("    // In editor mode, we don't save tile states", save_start)]
decode = function(client, "case ServerNotificationType::skillsDone:")
decode = decode[decode.index("{") + 1:-1].replace("            break;", "            return true;")
request = function(server, "case ClientNotificationType::askSetSkillTree:")
request = request[request.index("{") + 1:-1].replace("            break;", "            return true;")

probe = r'''
#include "game/Skill.h"
#include "game/SkillType.h"
#include "rooms/RoomType.h"
#include "traps/TrapType.h"
#include "spells/SpellType.h"
#include "network/ODPacket.h"
#include "utils/NameAliases.h"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#define OD_LOG_INF(x) ((void)0)
#define OD_LOG_ERR(x) ((void)0)
#define OD_LOG_WRN(x) ((void)0)
#define OD_ASSERT_TRUE(x) do {if(!(x)) return false;} while(0)
namespace Random {template<typename RandomIt> void shuffle(RandomIt first,RandomIt last){static std::mt19937 generator(1);std::shuffle(first,last,generator);}
 unsigned int Uint(unsigned int low,unsigned int high){static std::mt19937 generator(1);return std::uniform_int_distribution<unsigned int>(low,high)(generator);}}
namespace Helper {std::string toString(int value){return std::to_string(value);} template<class T> std::string toString(T value){std::ostringstream s;s<<value;return s.str();}}
class ConfigManager {
public:
    std::map<std::string,int> points;
    std::set<std::string> freeLevelOne;
    static ConfigManager& getSingleton(){static ConfigManager c;return c;}
    int getSkillPoints(const std::string& key) const {return points.at(key);}
    bool isSkillFreeLevelOne(const std::string& key) const {return freeLevelOne.count(key)>0;}
};
enum class SkillFamily {rooms,traps,spells,keeper,nb};
enum class SkillTab {rooms,traps,spells,nb};
SkillTab getTabOfPrefix(const std::string& skillFamily);
struct SkillDef {
    const Skill* mSkill;const uint32_t mTier;const SkillTab mTab;
    SkillDef(const std::string& family,const Skill* s,uint32_t tier):mSkill(s),mTier(tier),mTab(getTabOfPrefix(family)){}
    void mapSkill(std::vector<std::vector<SkillType>>&){ }
};
struct SkillDefRoom:SkillDef {SkillDefRoom(const std::string& f,const char*,const Skill* s,uint32_t t,RoomType):SkillDef(f,s,t){}};
struct SkillDefTrap:SkillDef {SkillDefTrap(const std::string& f,const char*,const Skill* s,uint32_t t,TrapType):SkillDef(f,s,t){}};
struct SkillDefSpell:SkillDef {SkillDefSpell(const std::string& f,const char*,const Skill* s,uint32_t t,SpellType):SkillDef(f,s,t){}};
struct SkillDefKeeper:SkillDef {SkillDefKeeper(const std::string& f,const char*,const Skill* s,uint32_t t):SkillDef(f,s,t){}};
struct Seat;
struct SkillManager {
    std::vector<const SkillDef*> mSkills;
    std::vector<std::vector<SkillType>> mTabSkills;
    std::vector<std::vector<SkillType>> mSkillsFamily;
    SkillManager();
    static const Skill* getSkill(SkillType);
    static SkillTab getSkillTab(SkillType);
    static void listTabSkills(SkillTab,std::vector<SkillType>&);
    static bool isAllSkillsDoneForSeat(const Seat*);
    static double getResearchValue(SkillType,uint32_t,double,bool=false);
    static double getResearchValue(const Seat*,SkillType,double,bool=false);
    static void buildRandomPendingSkillsForSeat(std::vector<SkillType>&,const Seat*);
};
SkillManager& getSkillManager(){static SkillManager m;return m;}
struct GameMap {bool server=true;bool isServerGameMap()const{return server;}};
struct Player {
    Seat* seat=nullptr;int warnings=0;
    Seat* getSeat()const{return seat;}
    bool getIsHuman()const{return true;}
    bool getHasLost()const{return false;}
    void notifyNoSkillInQueue(){++warnings;}
};
enum class ServerNotificationType {skillsDone,skillTree,chatServer};
enum class EventShortNoticeType {aboutSkills};
ODPacket& operator<<(ODPacket& packet,EventShortNoticeType type){return packet<<static_cast<int>(type);}
struct ServerNotification {
    ServerNotificationType type; ODPacket mPacket;
    ServerNotification(ServerNotificationType t,Player*):type(t){}
};
struct ODServer {
    std::vector<std::unique_ptr<ServerNotification>> sent;
    static ODServer& getSingleton(){static ODServer s;return s;}
    void queueServerNotification(ServerNotification* n){sent.emplace_back(n);}
};
GIFTBOXENUM
struct Seat {
    GameMap world;GameMap* mGameMap=&world;Player player;
    bool mHadLibrary=false;
    std::vector<std::pair<int32_t,uint32_t>> mStoredSpecialBoxes;
    void addStoredSpecial(GiftBoxType type,uint32_t amount){mStoredSpecialBoxes.push_back(std::pair<int32_t,uint32_t>(static_cast<int32_t>(type),amount));}
    int32_t mSkillPoints=0;const Skill* mCurrentSkill=nullptr;
    SkillType mCurrentSkillType=SkillType::nullSkillType;float mCurrentSkillProgress=0;
    bool mGuiSkillNeedsRefresh=false;
    std::vector<SkillType> mSkillDone,mSkillPending,mSkillNotAllowed;
    //! \brief Fixture list for the optional arrival history that the seat load and save paths handle.
    std::vector<std::string> mAnnouncedCreatureClasses;
    std::map<SkillType,uint32_t> mResearchLevels;
    Seat(){player.seat=this;}
    Player* getPlayer() {return &player;}
    bool isSkilling()const{return mCurrentSkill!=nullptr;}
    uint32_t getNbRooms(RoomType)const{return 1;}
    const std::vector<SkillType>& getSkillDone()const{return mSkillDone;}
    const std::vector<SkillType>& getSkillPending()const{return mSkillPending;}
    const std::vector<SkillType>& getSkillNotAllowed()const{return mSkillNotAllowed;}
    bool addSkill(SkillType,bool=true);bool isSkillDone(SkillType)const;uint32_t getSkillLevel(SkillType)const;
    bool isSkillNotAllowed(SkillType)const;
    uint32_t getQueuedSkillLevel(SkillType,const std::vector<std::pair<SkillType,int> >&)const;
    std::vector<std::pair<SkillType,int> > getQueuedLevels(const std::vector<SkillType>&)const;
    const char* getResearchGateFailure(SkillType,int,const std::vector<std::pair<SkillType,int> >&)const;
    bool canResearchLevel(SkillType,int,const std::vector<std::pair<SkillType,int> >&)const;
    void addFreeLevelOneSkills(std::vector<SkillType>&)const;
    void setResearchLevels(const std::map<SkillType,uint32_t>&);
    void completeResearch(SkillType);void addSkillPoints(int32_t);void setNextSkill(SkillType);
    void setSkillsDone(const std::vector<SkillType>&);void setSkillTree(const std::vector<SkillType>&);
    bool load(std::istream& is);void save(std::ostream& os)const;
};
DEFINITIONS
bool Seat::load(std::istream& is){std::string str;LOAD return true;}
void Seat::save(std::ostream& os)const{SAVE}
Player* activePlayer;
Player* getPlayer(){return activePlayer;}
bool decodeSkills(ODPacket& packetReceived){DECODE}
struct ClientSocket {Player* getPlayer(){return activePlayer;}};
bool requestSkills(ODPacket& packetReceived){ClientSocket socket;ClientSocket* clientSocket=&socket;REQUEST}
int checks=0;
void check(bool value,const std::string& name){++checks;if(!value)throw std::runtime_error(name);}
void near(double a,double b,const std::string& name){check(std::abs(a-b)<1e-7,name);}
int main(int argc,char** argv){try {
    std::ifstream config(argv[1]);std::string line;bool inFree=false;
    while(std::getline(config,line)){line=line.substr(0,line.find('#'));std::istringstream row(line);std::string key;int points;
        if(line.find("[FreeLevelOne]")!=std::string::npos){inFree=true;continue;}
        if(line.find("[/FreeLevelOne]")!=std::string::npos){inFree=false;continue;}
        if(inFree){if(row>>key)ConfigManager::getSingleton().freeLevelOne.insert(key);continue;}
        if(row>>key>>points && key[0]!='#')ConfigManager::getSingleton().points[key]=points;}
    std::vector<SkillType> all;
    for(uint32_t i=1;i<static_cast<uint32_t>(SkillType::countSkill);++i)
        if(!Skills::isRewardSkill(static_cast<SkillType>(i)))all.push_back(static_cast<SkillType>(i));
    check(all.size()==53,"all 53 research entries");
    check(ConfigManager::getSingleton().freeLevelOne.size()==5,"five free level one entries in skills.cfg");
    const std::vector<std::pair<SkillType,int> > none;
    // The research tree: tabs, tiers and parents of the production constructor
    check(SkillManager::getSkillTab(SkillType::roomTreasury)==SkillTab::rooms&&SkillManager::getSkillTab(SkillType::keeperDominion)==SkillTab::rooms,"Dominion stands in the Rooms tab");
    check(SkillManager::getSkillTab(SkillType::trapDoorWooden)==SkillTab::traps&&SkillManager::getSkillTab(SkillType::keeperHeartMending)==SkillTab::traps,"Heart Mending stands in the Traps tab");
    check(SkillManager::getSkillTab(SkillType::spellSummonWorker)==SkillTab::spells&&SkillManager::getSkillTab(SkillType::keeperManaFlow)==SkillTab::spells,"Mana Flow stands in the Spells tab");
    {std::vector<SkillType> rooms,traps,spells;SkillManager::listTabSkills(SkillTab::rooms,rooms);SkillManager::listTabSkills(SkillTab::traps,traps);SkillManager::listTabSkills(SkillTab::spells,spells);
     check(rooms.size()==16&&traps.size()==19&&spells.size()==18,"16 + 19 + 18 entries in the three tabs");}
    {const Skill* mending=SkillManager::getSkill(SkillType::keeperHeartMending);
     check(mending->getDependencies().size()==1&&mending->getDependencies()[0]->getType()==SkillType::keeperHeartFortitude,"Heart Mending needs only Heart Fortitude");
     const Skill* banner=SkillManager::getSkill(SkillType::trapWatchBanner);
     check(banner->getDependencies().size()==2&&banner->getDependencies()[0]->getType()==SkillType::trapAlarm&&banner->getDependencies()[1]->getType()==SkillType::roomGuardRoom,"Watch Banner needs Alarm Trap and Guard Room");}
    {Seat reward;reward.setSkillTree({SkillType::spellSummonChampion});check(reward.mSkillPending.empty(),"the reward skill cannot be researched");}
    for(SkillType type:all){
        const Skill* skill=SkillManager::getSkill(type);check(skill!=nullptr,"catalog completeness");
        const int anchor=ConfigManager::getSingleton().points.at(Skills::toString(type));
        check(skill->getNeededSkillPoints()==(ConfigManager::getSingleton().isSkillFreeLevelOne(Skills::toString(type))?0:anchor),"level I costs the tier cost, 0 for a free level one entry");
        check(skill->getNeededSkillPoints(2)==2*anchor,"level II cost");
        check(skill->getNeededSkillPoints(3)==4*anchor,"level III cost");
        Seat s;s.setSkillsDone(all);check(s.getSkillLevel(type)==1,"legacy unlock means I");
        s.setSkillTree({type});s.addSkillPoints(2*anchor-1);
        check(s.getSkillLevel(type)==1 && s.mSkillPoints==2*anchor-1,"no premature upgrade");
        s.addSkillPoints(1);check(s.getSkillLevel(type)==2 && s.mSkillPoints==0 && s.mSkillPending.empty(),"II charged once and consumed");
        s.setSkillTree({type});s.addSkillPoints(4*anchor+13);
        check(s.getSkillLevel(type)==3 && s.mSkillPoints==13 && s.mSkillPending.empty(),"III and surplus points");
        s.setSkillTree({type});check(s.mSkillPending.empty(),"cap rejects fourth level");
        check(!s.addSkill(type) && s.getSkillLevel(type)==3,"gift unlock cannot alter upgrade");
        std::stringstream saved;s.save(saved);Seat loaded;
        check(loaded.load(saved) && loaded.getSkillLevel(type)==3 && loaded.mSkillPoints==13,"level and points save roundtrip");
    }
    // A new seat starts with the free level one entries (the seat start applies them the same way)
    std::vector<SkillType> startSkills;Seat probeSeat;probeSeat.addFreeLevelOneSkills(startSkills);
    check(startSkills.size()==5,"five entries are free at level I");
    {Seat sandboxLike;sandboxLike.mSkillNotAllowed={SkillType::roomLibrary};std::vector<SkillType> list;sandboxLike.addFreeLevelOneSkills(list);
     check(list.size()==4&&std::find(list.begin(),list.end(),SkillType::roomLibrary)==list.end(),"the level can forbid a free level one entry");}
    Seat fresh;fresh.setSkillsDone(startSkills);
    check(fresh.getSkillLevel(SkillType::roomTreasury)==1&&fresh.getSkillLevel(SkillType::spellSummonWorker)==1,"free entries are at level I at the start");
    Seat gifted;gifted.setSkillsDone(startSkills);gifted.setSkillTree({SkillType::roomTrainingHall});
    gifted.addSkill(SkillType::roomTrainingHall);gifted.addSkillPoints(1000);
    check(gifted.getSkillLevel(SkillType::roomTrainingHall)==1 && gifted.mSkillPending.empty(),"gift cannot silently start an unselected upgrade");
    fresh.setSkillTree({SkillType::roomTrainingHall});fresh.addSkillPoints(250);
    check(fresh.getSkillLevel(SkillType::roomTrainingHall)==1,"actual first unlock");
    fresh.setSkillTree({SkillType::roomWorkshop,SkillType::roomWorkshop});
    check(fresh.mSkillPending.size()==1&&fresh.mSkillPending[0]==SkillType::roomWorkshop,"only the duplicate entry is dropped, the valid one stays");
    fresh.mSkillNotAllowed={SkillType::roomTrainingHall};fresh.setSkillTree({SkillType::roomTrainingHall});
    check(fresh.mSkillPending.empty(),"map-disabled upgrade rejected");
    fresh.mSkillNotAllowed.clear();fresh.setSkillTree({SkillType::trapBoulder});
    check(fresh.mSkillPending.empty(),"locked dependencies rejected");
    // Levels I: a parent counts when it is done or queued earlier, or when the level does not allow it
    {Seat g;g.setSkillsDone(startSkills);
     g.setSkillTree({SkillType::roomArena});check(g.mSkillPending.empty(),"Arena without Training Hall is dropped");
     g.setSkillTree({SkillType::roomArena,SkillType::roomTrainingHall});check(g.mSkillPending.size()==1&&g.mSkillPending[0]==SkillType::roomTrainingHall,"a parent queued later does not count, the valid entry stays");
     g.setSkillTree({SkillType::roomTrainingHall,SkillType::roomArena,SkillType::keeperDominion});check(g.mSkillPending.size()==3,"parents queued earlier count");
     Seat denied;denied.setSkillsDone(startSkills);denied.mSkillNotAllowed={SkillType::roomTrainingHall};
     denied.setSkillTree({SkillType::roomArena});check(denied.mSkillPending.size()==1,"a parent the level does not allow counts as fulfilled");
     std::vector<SkillType> chain;SkillManager::getSkill(SkillType::roomArena)->buildDependencies(startSkills,denied.mSkillNotAllowed,chain);
     check(chain.size()==1&&chain[0]==SkillType::roomArena,"the dependency chain skips a parent the level does not allow");
     check(SkillManager::getSkill(SkillType::roomArena)->canBeSkilled(startSkills,denied.mSkillNotAllowed)&&!SkillManager::getSkill(SkillType::roomArena)->canBeSkilled(startSkills,{}),"canBeSkilled honours the allowed list");}
    // Levels II and III: half (rounded up) and all of the allowed entries of the tab need level I
    {Seat g;g.setSkillsDone(startSkills);
     check(!g.canResearchLevel(SkillType::roomTreasury,2,none),"level II waits for 8 of 16 rooms at level I (4 present)");
     std::vector<std::pair<SkillType,int> > four={{SkillType::roomTrainingHall,1},{SkillType::roomWorkshop,1},{SkillType::roomBridgeWooden,1},{SkillType::roomGuardRoom,1}};
     check(g.canResearchLevel(SkillType::roomTreasury,2,four),"level II opens with 8 of 16 rooms (queued entries count)");
     std::vector<std::pair<SkillType,int> > three(four.begin(),four.begin()+3);
     check(!g.canResearchLevel(SkillType::roomTreasury,2,three),"7 of 16 rooms are not enough");
     g.setSkillTree({SkillType::roomTrainingHall,SkillType::roomWorkshop,SkillType::roomBridgeWooden,SkillType::roomTreasury});
     check(g.mSkillPending.size()==3,"the queue drops only the level II entry that has no gate yet");
     g.setSkillTree({SkillType::roomTrainingHall,SkillType::roomWorkshop,SkillType::roomBridgeWooden,SkillType::roomGuardRoom,SkillType::roomTreasury});
     check(g.mSkillPending.size()==5,"the queue accepts level II once 8 entries are done or queued");
     check(!g.canResearchLevel(SkillType::roomTreasury,3,four),"level III needs the entry at level II");
     Seat done;done.setSkillsDone(startSkills);
     std::vector<SkillType> allRooms;SkillManager::listTabSkills(SkillTab::rooms,allRooms);
     std::vector<SkillType> doneList=startSkills;for(SkillType t:allRooms)if(std::find(doneList.begin(),doneList.end(),t)==doneList.end())doneList.push_back(t);
     done.setSkillsDone(doneList);done.mResearchLevels[SkillType::roomTreasury]=2;
     check(done.canResearchLevel(SkillType::roomTreasury,3,none),"level III opens when every room has level I");
     done.mSkillDone.erase(std::find(done.mSkillDone.begin(),done.mSkillDone.end(),SkillType::keeperDominion));
     check(!done.canResearchLevel(SkillType::roomTreasury,3,none),"level III waits for the last room");
     done.mSkillNotAllowed={SkillType::keeperDominion};
     check(done.canResearchLevel(SkillType::roomTreasury,3,none),"an entry the level does not allow is not counted");
     check(!done.canResearchLevel(SkillType::keeperDominion,1,none)&&!done.canResearchLevel(SkillType::spellSummonChampion,1,none),"not allowed and reward skills cannot be queued");}
    std::vector<SkillType> automatic;SkillManager::buildRandomPendingSkillsForSeat(automatic,&fresh);
    fresh.setSkillTree(automatic);check(fresh.mSkillPending==automatic && !automatic.empty(),"autofill includes legal unlocks and upgrades");
    fresh.addSkillPoints(100000);check(fresh.mSkillPending.empty(),"large book surplus drains full selected queue");
    check(fresh.getSkillLevel(SkillType::roomTrainingHall)==2,"autofill upgrades unlocked item only once");
    Seat resumed;resumed.setSkillsDone(all);resumed.setSkillTree({SkillType::trapCannon,SkillType::trapSpike});resumed.addSkillPoints(125);
    check(resumed.mSkillPoints==125,"partial progress of the first upgrade is kept");
    std::stringstream saved;resumed.save(saved);Seat loaded;check(loaded.load(saved),"pending upgrade save loads");
    std::vector<SkillType> pending=loaded.mSkillPending;loaded.setSkillTree(pending);loaded.addSkillPoints(75);
    check(loaded.getSkillLevel(SkillType::trapCannon)==2 && loaded.mSkillPending==std::vector<SkillType>{SkillType::trapSpike},"resume partial upgrade with order retained");
    std::stringstream old("[SkillDone] roomLibrary [/SkillDone] [SkillNotAllowed] [/SkillNotAllowed] [SkillPending] roomTrainingHall [/SkillPending]");
    Seat legacy;check(legacy.load(old) && legacy.getSkillLevel(SkillType::roomLibrary)==1 && legacy.mSkillPoints==0,"old save without extension");
    check(!legacy.mHadLibrary && legacy.mStoredSpecialBoxes.empty(),"old save has no lost library and no stored specials");
    {Seat keeper;keeper.setSkillsDone(all);keeper.mHadLibrary=true;
     keeper.addStoredSpecial(GiftBoxType::mana,50000);keeper.addStoredSpecial(GiftBoxType::healAll,0);keeper.addStoredSpecial(GiftBoxType::mana,7);
     std::stringstream kept;keeper.save(kept);Seat restored;
     check(restored.load(kept) && restored.mHadLibrary,"the lost library state survives a save and load");
     check(restored.mStoredSpecialBoxes==keeper.mStoredSpecialBoxes && restored.mStoredSpecialBoxes.size()==3,"stored specials survive a save and load in order");
     std::stringstream nothing;Seat plain;plain.setSkillsDone(all);plain.save(nothing);Seat plainLoaded;
     check(plainLoaded.load(nothing) && !plainLoaded.mHadLibrary && plainLoaded.mStoredSpecialBoxes.empty(),"a seat without them saves no block");
     for(const std::string& block:{"[StoredSpecials] 1 0 5 [/StoredSpecials]", "[StoredSpecials] 1 13 5 [/StoredSpecials]", "[StoredSpecials] 2 1 5 [/StoredSpecials]"}){
      std::stringstream badSpecial("[SkillDone] roomLibrary [/SkillDone] "+block+" [SkillNotAllowed] [/SkillNotAllowed] [SkillPending] [/SkillPending]");
      Seat rejected;check(!rejected.load(badSpecial),"malformed stored special rejected");}}
    for(const std::string& block:{"-1 0", "0 1 roomLibrary 4", "0 1 trapCannon 2", "0 2 roomLibrary 2 roomLibrary 3"}){
        std::stringstream bad("[SkillDone] roomLibrary [/SkillDone] [ResearchProgress] "+block+" [/ResearchProgress] [SkillNotAllowed] [/SkillNotAllowed] [SkillPending] [/SkillPending]");
        Seat rejected;check(!rejected.load(bad),"malformed save rejected");
    }
    Seat receiver;receiver.world.server=false;activePlayer=&receiver.player;
    ODPacket packet;packet<<uint32_t(2)<<SkillType::trapCannon<<uint32_t(3)<<SkillType::roomLibrary<<uint32_t(2);
    check(decodeSkills(packet) && receiver.getSkillLevel(SkillType::trapCannon)==3 && receiver.getSkillLevel(SkillType::roomLibrary)==2,"actual client packet parser");
    ODPacket bad;bad<<uint32_t(1)<<SkillType::trapCannon<<uint32_t(4);check(!decodeSkills(bad),"invalid network level rejected");
    ODPacket truncated;truncated<<uint32_t(1)<<SkillType::trapCannon;check(!decodeSkills(truncated),"truncated level packet rejected");
    Seat host;host.setSkillsDone(all);activePlayer=&host.player;
    ODPacket request;request<<uint32_t(1)<<SkillType::trapCannon<<uint32_t(2);
    check(requestSkills(request) && host.mSkillPending==std::vector<SkillType>{SkillType::trapCannon},"actual server accepts II request");
    host.addSkillPoints(200);ODPacket stale;stale<<uint32_t(1)<<SkillType::trapCannon<<uint32_t(2);
    check(requestSkills(stale) && host.mSkillPending.empty(),"stale II request cannot silently queue III");
    using T=SkillType;
    struct Effect{T type;double base,second,third;bool secondary;};
    const Effect effects[]={
        {T::roomTreasury,1000,1250,1500,false},{T::roomHatchery,15,12,10,false},
        {T::roomDormitory,1.5,1.8,2.1,false},{T::roomLibrary,5,6,7,false},
        {T::roomTrainingHall,5,6,7,false},{T::roomWorkshop,5,6,7,false},
        {T::roomBridgeWooden,1,1.25,1.5,false},{T::roomBridgeStone,1,1.5,2,false},
        {T::roomCrypt,30,24,20,false},{T::roomPrison,1,2,3,false},
        {T::roomArena,20,25,30,false},{T::roomCasino,.1,.12,.14,false},{T::roomTorture,.1,.12,.14,false},
        {T::trapCannon,10,12,14,false},{T::trapCannon,15,18,21,true},
        {T::trapSpike,10,13,16,false},{T::trapSpike,15,20,24,true},
        {T::trapBoulder,100,120,140,false},{T::trapBoulder,120,144,168,true},
        {T::trapDoorWooden,10,15,20,false},{T::spellSummonWorker,1500,1350,1200,false},
        {T::spellCallToWar,50,65,80,false},{T::spellCreatureDefense,5,6,7,false},
        {T::spellCreatureExplosion,14,17,20,false},{T::spellCreatureHaste,1.5,1.65,1.8,false},
        {T::spellCreatureHeal,5,6,7,false},{T::spellCreatureSlow,.5,.45,.4,false},
        {T::spellCreatureStrength,1.1,1.15,1.2,false},{T::spellCreatureWeak,.9,.85,.8,false},
        {T::spellEyeEvil,10,15,20,false}};
    for(const auto& effect:effects){
        near(SkillManager::getResearchValue(effect.type,0,effect.base,effect.secondary),effect.base,"preplaced baseline");
        near(SkillManager::getResearchValue(effect.type,1,effect.base,effect.secondary),effect.base,"I unchanged");
        near(SkillManager::getResearchValue(effect.type,2,effect.base,effect.secondary),effect.second,"approved II effect");
        near(SkillManager::getResearchValue(effect.type,3,effect.base,effect.secondary),effect.third,"approved III effect");
    }
    std::cout<<"CHECKS="<<checks<<" FAILURES=0\n";
}catch(const std::exception& e){std::cerr<<"CHECK "<<checks<<": "<<e.what()<<"\n";return 1;}}
'''
gift_header = (root / "source/entities/GiftBoxEntity.h").read_text(encoding="utf-8")
gift_enum = gift_header[gift_header.index("enum class GiftBoxType"):]
gift_enum = gift_enum[:gift_enum.index("};") + 2]
for key, value in {"GIFTBOXENUM": gift_enum, "DEFINITIONS": definitions, "LOAD": load, "SAVE": save,
                   "DECODE": decode, "REQUEST": request}.items():
    probe = probe.replace(key, value)

with tempfile.TemporaryDirectory(prefix="research-progression-") as directory:
    work = Path(directory)
    cpp = work / "check.cpp"
    cpp.write_text(probe, encoding="utf-8")
    executable = work / "check.exe"
    subprocess.run([
        "cl", "/nologo", "/EHsc", "/MD", "/std:c++17",
        f"/I{root / 'source'}", f"/I{prefix / 'include'}", f"/I{prefix / 'include/OGRE'}",
        str(cpp), str(root / "source/network/ODPacket.cpp"), str(root / "source/game/SkillType.cpp"), str(root / "source/utils/NameAliases.cpp"),
        f"/Fe:{executable}", "/link", f"/LIBPATH:{prefix / 'lib'}",
        "OgreMain.lib", "sfml-network.lib", "sfml-system.lib"
    ], cwd=work, check=True)
    subprocess.run([str(executable), str(root / "config/skills.cfg")], cwd=work, check=True)
