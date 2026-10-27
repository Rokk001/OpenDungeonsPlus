"""Compile extracted production infirmary rules against controlled fixtures; never launch the game.

This check deliberately requires the maintained developer compiler environment. It is not a
static check and must be scheduled only after implementation is complete.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]

# Read production source without depending on the current working directory.
def read(path):
    return (repo / path).read_text(encoding="utf-8")

# Extract a complete production function, keeping its actual body unchanged.
def function(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]

# Build and execute one self-contained production-code probe with bounded child lifetimes.
def run_probe(name, code):
    with tempfile.TemporaryDirectory(prefix=name + "-") as directory:
        work = Path(directory)
        source, binary = work / "check.cpp", work / "check.exe"
        source.write_text(code, encoding="utf-8")
        subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++17", str(source),
            "/Fe:" + str(binary)], cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=180)
        subprocess.run([str(binary)], cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=180)

# Use the actual cot/patient records so stream or field changes cannot silently evade the fixtures.
def records():
    header = read("source/rooms/RoomInfirmary.h")
    return header[header.index("    struct CotInfo"):header.index("    //! " + chr(92) + "brief Creates an empty infirmary.")]

PRELUDE = r"""
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <queue>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>
//! \brief Fails a named production-behaviour assertion.
void check(bool result,const char* name){if(!result)throw std::runtime_error(name);}
//! \brief Compares fractional values without rounding their production storage.
void near(double result,double expected,const char* name){check(std::abs(result-expected)<1e-8,name);}
//! \brief Declares creatures referenced by fixture rooms and actions.
struct Creature;
//! \brief Declares rooms referenced by fixture tiles.
struct Room;
//! \brief Declares infirmaries referenced by fixture rest and carry actions.
struct RoomInfirmary;
//! \brief Identifies the room kinds required by admission and bed redirection fixtures.
enum class RoomType{infirmary,dormitory,other};
//! \brief Provides only the vectors required by cot geometry and saved shaman positions.
namespace Ogre {
//! \brief Stores the position coordinates used by the production room methods.
struct Vector3{float x,y,z;
 //! \brief Initializes the fixture position from its three coordinates.
 Vector3(float a=0,float b=0,float c=0):x(a),y(b),z(c){}
};
//! \brief Stores the two saved shaman position coordinates.
struct Vector2{float x=0,y=0;};using Real=float;}
//! \brief Supplies the current figure position to the real room stream writer.
struct InfirmaryShamanEntity{Ogre::Vector3 position;
 //! \brief Returns the position written by the real shaman stream codec.
 const Ogre::Vector3& getPosition()const{return position;}
};
//! \brief Supplies declared room parameters independently of production code.
struct ConfigManager {
 //! \brief Returns the fixture's shared configuration service.
 static ConfigManager& getSingleton(){static ConfigManager config;return config;}
 //! \brief Returns the independently specified value for the requested room key.
 double getRoomConfigDouble(const std::string& name){
  const std::map<std::string,double> values={{"InfirmaryAdmissionWageShare",.3},{"InfirmaryManaPerWage",2},
   {"InfirmaryFullHealSeconds",60},{"DormitoryFullHealSeconds",150},{"InfirmaryMoodWageShare",.3},
   {"InfirmaryMoodDefaultTurns",30},{"InfirmaryHealGlowTurns",7},{"InfirmaryCotShareSmall",12},
   {"InfirmaryCotShareMedium",17},{"InfirmaryCotShareLarge",6},{"InfirmaryMinRoomSide",4},
   {"InfirmaryDischargeMinPercent",40},{"InfirmaryDischargeMaxPercent",100},
   {"InfirmaryDischargeStepPercent",10},{"InfirmaryDischargeDefaultPercent",100},
   {"DormitoryWoundedCarryHpPercent",35},{"InfirmaryDirtPerTreatment",15.6}};
  return values.at(name);}
 //! \brief Returns a signed integer room parameter from the fixture configuration.
 int getRoomConfigInt32(const std::string& name){return int(getRoomConfigDouble(name));}
 //! \brief Returns an unsigned integer room parameter from the fixture configuration.
 uint32_t getRoomConfigUInt32(const std::string& name){return uint32_t(getRoomConfigDouble(name));}
 //! \brief Returns the full death countdown used for manually admitted patients.
 int getNbTurnsKoCreatureAttacked(){return 120;}
};
//! \brief Captures room shortage messages while preserving human-player routing.
struct Player{bool human=true;int notices=0;
 //! \brief Reports whether the fixture keeper is human.
 bool getIsHuman()const{return human;}
 //! \brief Counts shortage notices only for human keepers.
 void notifyInfirmaryEvent(){if(human)++notices;}
};
//! \brief Represents the keeper resource and setting services used by the real room.
struct Seat{Player player;double mana=10000;int payer=0,threshold=100;bool heal=true;
 //! \brief Returns the keeper whose notices the fixture records.
 Player* getPlayer(){return &player;}
 //! \brief Returns the keeper for const admission checks.
 const Player* getPlayer()const{return &player;}
 //! \brief Returns the keeper identifier used by admission gold transfers.
 int getId()const{return 1;}
 //! \brief Returns the selected admission payer.
 int getInfirmaryPayer()const{return payer;}
 //! \brief Returns the selected discharge health percentage.
 int getInfirmaryThreshold()const{return threshold;}
 //! \brief Reports whether healing may spend mana.
 bool getInfirmaryHealOn()const{return heal;}
 //! \brief Takes the exact requested mana only when the complete amount is available.
 bool takeMana(double amount){if(mana<amount)return false;mana-=amount;return true;}
 //! \brief Identifies this fixture as an owned keeper seat.
 bool isRogueSeat()const{return false;}
 //! \brief Returns the keeper faction accepted by infirmary admission rules.
 std::string getFaction()const{return "Keeper";}
};
//! \brief Identifies fixture entities to the actual carry and admission methods.
enum class GameEntityType{creature,room,other};
//! \brief Supplies the real carry-entry type and ownership contract.
struct GameEntity{Seat* owner=nullptr;
 //! \brief Allows fixture creatures to be destroyed through their entity interface.
 virtual ~GameEntity(){}
 //! \brief Identifies this fixture entity as a creature for carrying checks.
 virtual GameEntityType getObjectType()const{return GameEntityType::creature;}
 //! \brief Supplies carry listener attachment without changing fixture state.
 void addGameEntityListener(void*){}
 //! \brief Supplies the production carry-lock service without changing eligibility.
 void setCarryLock(Creature&,bool){}
 //! \brief Supplies non-drag pickup notification to the actual constructor.
 void notifyEntityCarryOn(Creature*){}
 //! \brief Returns the owner used by carry eligibility.
 Seat* getSeat()const{return owner;}
 //! \brief Requires a stable name for saved entity rebinding.
 virtual const std::string& getName()const=0;
};
//! \brief Exposes the tile geometry used by the actual layout and minimum-square methods.
struct Tile{int x,y;bool full=true;Room* room=nullptr;std::vector<Tile*> neighbors;
 //! \brief Returns the fixture tile's horizontal coordinate.
 int getX()const{return x;}
 //! \brief Returns the fixture tile's vertical coordinate.
 int getY()const{return y;}
 //! \brief Reports whether the tile blocks an infirmary entrance.
 bool isFullTile()const{return full;}
 //! \brief Returns the room used by joined-floor and own-bed checks.
 Room* getCoveringRoom(){return room;}
 //! \brief Returns the registered neighbors used by the minimum-square rule.
 const std::vector<Tile*>& getAllNeighbors(){return neighbors;}
 //! \brief Supplies admission dirt handling without changing the geometry fixture.
 void addDirt(double){}
};
//! \brief Holds fixed fixture terrain, production room membership and precise treasury transfers.
struct GameMap{std::map<std::pair<int,int>,Tile> tiles;std::vector<Room*> rooms;std::map<std::string,Creature*> creatures;int64_t turn=0;double treasury=1000,credited=0;
 //! \brief Finds a fixture tile without creating terrain outside the registered map.
 Tile* getTile(int x,int y){const std::pair<int,int> cell(x,y);return tiles.count(cell)?&tiles.at(cell):nullptr;}
 //! \brief Returns the physical rooms whose gold can pay an admission.
 const std::vector<Room*>& getRooms(){return rooms;}
 //! \brief Returns the controlled turn used by shortage and glow checks.
 int64_t getTurnNumber(){return turn;}
 //! \brief Withdraws a complete fractional admission without partially charging a refusal.
 bool withdrawFromTreasuries(double amount,Seat*){if(treasury<amount)return false;treasury-=amount;return true;}
 //! \brief Records gold transferred from a creature purse to its keeper.
 void addGoldToSeat(double amount,int){credited+=amount;}
 //! \brief Resolves saved patient and carrier names to the registered fixture creatures.
 Creature* getCreature(const std::string& name){return creatures.count(name)?creatures.at(name):nullptr;}
};
//! \brief Represents just the inherited services invoked by the selected production methods.
struct Room{GameMap* map;Seat* seat;std::vector<Tile*> mCoveredTiles;double gold=1000;RoomType type=RoomType::infirmary;Tile* delivery=nullptr;
 //! \brief Attaches the fixture room to its terrain and owning keeper.
 Room(GameMap* m=nullptr,Seat* s=nullptr):map(m),seat(s){}
 //! \brief Supports destruction through the inherited room interface.
 virtual ~Room(){}
 //! \brief Returns the room owner used by admission and joined-floor checks.
 Seat* getSeat()const{return seat;}
 //! \brief Returns the fixture map supplying tiles, entities and resources.
 GameMap* getGameMap()const{return map;}
 //! \brief Returns the room kind used by cot and bed redirection rules.
 RoomType getType()const{return type;}
 //! \brief Identifies rooms to the actual carry constructor.
 GameEntityType getObjectType()const{return GameEntityType::room;}
 //! \brief Supplies the fixture destination selected after a carry redirects to a bed.
 virtual Tile* askSpotForCarriedEntity(GameEntity*){return delivery;}
 //! \brief Supplies listener detachment without changing fixture ownership.
 void removeGameEntityListener(void*){}
 //! \brief Supplies listener attachment without changing fixture ownership.
 void addGameEntityListener(void*){}
 //! \brief Returns the number of room tiles available to minimum-square checks.
 unsigned numCoveredTiles()const{return unsigned(mCoveredTiles.size());}
 //! \brief Returns a covered tile in the fixture's registered order.
 Tile* getCoveredTile(unsigned i){return mCoveredTiles.at(i);}
 //! \brief Returns physical room gold used by the actual admission preflight.
 double getTotalGoldStored()const{return gold;}
 //! \brief Supplies cot object removal without invoking rendering services.
 void removeBuildingObject(Tile*){}
 //! \brief Omits inherited room data so the probe isolates the infirmary save payload.
 void exportToStream(std::ostream&)const{}
 //! \brief Accepts inherited room data already supplied by the fixture.
 bool importFromStream(std::istream&){return true;}
 //! \brief Supplies room audio without playing a sound during the rule probe.
 void fireRoomSound(Tile&,const char*){}
 //! \brief Supplies unrelated room dirt handling without changing rule inputs.
 static void addUseDirt(const Creature&,Tile*,const std::string&){}
 //! \brief Supplies the inherited restore hook before the actual infirmary restoration.
 void restoreInitialEntityState(){}
};
//! \brief Models the fee and optional mood definitions read by production admission logic.
struct CreatureMood{
 //! \brief Supports the production mood casts through the fixture base interface.
 virtual ~CreatureMood(){}
};
//! \brief Supplies the independently specified fee mood modifier.
struct CreatureMoodFee:CreatureMood{
 //! \brief Returns the fee modifier scaled by the production admission mood rule.
 double getMoodModifier()const{return -120;}
};
//! \brief Supplies the configured rested lifetime used by admission moods.
struct CreatureMoodRested:CreatureMood{
 //! \brief Returns the rested lifetime used by the production mood initializer.
 double getTurnsMax()const{return 30;}
};
//! \brief Holds controlled creature fee, eligibility, bed size and mood definitions.
struct Definition{double fee=58,sleepHeal=2.05;std::vector<const CreatureMood*> moods;bool worker=false,champion=false;int width=1,height=1;
 //! \brief Returns the wage used for proportional admission and mana costs.
 double getFee(int)const{return fee;}
 //! \brief Returns the retained legacy flag controlling zero bed healing.
 double getSleepHeal()const{return sleepHeal;}
 //! \brief Returns optional fee and rested definitions for the actual mood initializer.
 const std::vector<const CreatureMood*>& getCreatureMoods()const{return moods;}
 //! \brief Reports the worker exclusion used by admission checks.
 bool isWorker()const{return worker;}
 //! \brief Reports the champion exclusion used by admission checks.
 bool isChampion()const{return champion;}
 //! \brief Returns the first bed dimension used to select the matching cot size.
 int getBedDim1()const{return width;}
 //! \brief Returns the second bed dimension used to select the matching cot size.
 int getBedDim2()const{return height;}
};
//! \brief Records action transitions without reimplementing their production decisions.
struct CreatureActionSleep{
 //! \brief Represents the production transition to an own-bed sleep action.
 CreatureActionSleep(Creature&){}
};
//! \brief Represents a newly created infirmary rest action without animation services.
struct CreatureActionInfirmaryRest{
 //! \brief Accepts the creature and room passed by actual admission and restoration.
 CreatureActionInfirmaryRest(Creature&,RoomInfirmary&){}
};
//! \brief Provides the owning creature reference used by the actual carry constructor.
struct CreatureAction{Creature& mCreature;
 //! \brief Retains the owning creature for the actual carry constructor.
 CreatureAction(Creature& creature):mCreature(creature){}
};
using Building=Room;
//! \brief Declares the actual carry constructor state while excluding unrelated rendering and path services.
struct CreatureActionCarryEntity:CreatureAction{
 GameEntity* mEntityToCarry=nullptr;Tile* mTileDest=nullptr;Building* mBuildingDest=nullptr;
 bool mIsDrag=false;int mDragPhase=0,mDragLayTurns=0;double mDragFollowArc=0;
 //! \brief Executes the production room-delivery constructor supplied by the streams probe.
 CreatureActionCarryEntity(Creature&,GameEntity&,Building&);
 //! \brief Uses the production own-seat living-creature drag selection.
 static bool isPulledOverGround(const Creature&,GameEntity&);
 //! \brief Supplies drag attachment without changing the saved knockout countdown.
 void startDrag(){}
};
namespace Utils{
//! \brief Constructs the fixture action requested by an extracted production method.
template<class T,class... A>std::unique_ptr<T> make_unique(A&&... a){return std::unique_ptr<T>(new T(std::forward<A>(a)...));}}
namespace EntityAnimation{const char* sleep_anim="sleep";const char* die_anim="die";const char* idle_anim="idle";}
//! \brief Identifies the action states used by the actual attack behaviour.
enum class CreatureActionType{fight,flee,sleep,infirmaryRest};
//! \brief Supplies the mood states handled by the actual attack behaviour.
enum class CreatureMoodLevel{Happy,Angry,Furious};
namespace Random{
//! \brief Supplies a deterministic non-flee result for the production attack behaviour.
int Int(int,int){return 0;}}
//! \brief Supplies mutable resources and records actual admission, healing and action effects.
struct Creature:GameEntity{Definition definition;double hp=1,maximum=100,gold=100,mInfirmaryMood=0,mInfirmaryMoodTurns=0;
 double counter=-73;int glows=0,popped=0,sleeps=0;std::string name="patient";Tile* home=nullptr;Tile* tile=nullptr;
 Tile* resumedCarryTarget=nullptr;double resumedCarryCounter=0;bool resumedCarryIsDrag=false;
 //! \brief Returns mutable creature definitions for the actual treatment methods.
 Definition* getDefinition(){return &definition;}
 //! \brief Returns creature definitions during const admission checks.
 const Definition* getDefinition()const{return &definition;}
 //! \brief Returns the fixture level used when the production methods request a wage.
 int getLevel()const{return 1;}
 //! \brief Returns the precise purse balance used by admission checks.
 double getGoldCarried()const{return gold;}
 //! \brief Applies an exact fractional change to the fixture purse.
 void addGoldCarried(double v){gold+=v;}
 //! \brief Returns the current health used by treatment and lying rules.
 double getHP()const{return hp;}
 //! \brief Returns the controlled maximum health used by proportional healing.
 double getMaxHp()const{return maximum;}
 //! \brief Records the health change produced by the actual healing rule.
 void setHP(double v){hp=v;}
 //! \brief Returns the signed remaining knockout countdown.
 double getKoTurnCounter()const{return counter;}
 //! \brief Restores the exact saved knockout countdown.
 void setKoTurnCounter(double v){counter=v;}
 //! \brief Stops the knockout countdown after a paid admission.
 void resetKoTurns(){counter=0;}
 //! \brief Returns the stable entity name used by reservations and saves.
 const std::string& getName()const{return name;}
 //! \brief Applies the extracted production admission mood initializer.
 void setInfirmaryAdmissionMood(bool);
 //! \brief Reports whether the fixture creature is alive for admission and dragging.
 bool isAlive()const{return hp>0;}
 //! \brief Identifies the fixture as an eligible creature outside prison.
 bool isInPrison()const{return false;}
 std::set<CreatureActionType> actions;std::vector<int> enemies;int fights=0,flees=0;
 //! \brief Reports the action states consumed by the actual attack behaviour.
 bool isActionInList(CreatureActionType action)const{return actions.count(action)>0;}
 //! \brief Returns the controlled visible-enemy list for combat decisions.
 const std::vector<int>& getVisibleEnemyObjects()const{return enemies;}
 //! \brief Supplies a happy mood so combat boundary checks do not randomly flee.
 CreatureMoodLevel getMoodValue()const{return CreatureMoodLevel::Happy;}
 //! \brief Records the attack behaviour's decision to fight.
 void fight(){++fights;}
 //! \brief Records the attack behaviour's decision to flee.
 void flee(){++flees;}
 //! \brief Counts healing glow requests without invoking the renderer.
 void addParticleEffect(const char*,uint32_t){++glows;}
 //! \brief Returns the tile used by admission arrival and audio checks.
 Tile* getPositionTile(){return tile;}
 //! \brief Returns the own bed used after refusal or partial discharge.
 Tile* getHomeTile(){return home;}
 //! \brief Supplies queue cleanup without altering the controlled fixture actions.
 void clearActionQueue(){}
 //! \brief Supplies animation destination cleanup without invoking pathfinding.
 void clearDestinations(const char*,bool,bool){}
 //! \brief Supplies patient placement without changing the fixture's explicit tile binding.
 void setPosition(const Ogre::Vector3&){}
 //! \brief Supplies ordinary attachment for the real carry constructor's non-drag branch.
 void carryEntity(GameEntity*){}
 //! \brief Records the actual constructor's resumed destination and countdown for assertions.
 void pushAction(std::unique_ptr<CreatureActionCarryEntity>);
 //! \brief Counts non-carry action transitions requested by production methods.
 template<class T>void pushAction(std::unique_ptr<T>){++sleeps;}
 //! \brief Counts action completions requested by production methods.
 void popAction(){++popped;}
};
//! \brief Executes the actual attack behaviour with controlled visible-enemy inputs.
struct CreatureBehaviourAttackEnemy{
 //! \brief Executes the extracted production attack decision for the supplied creature.
 bool processBehaviour(Creature&)const;
};
namespace SkillType{const int roomInfirmary=1,roomDormitory=2;}
namespace ResearchEffect{const char* SleepRecovery="SleepRecovery";const char* HealTime="HealTime";}
namespace SkillManager{double factor=1;
 //! \brief Supplies only the independent research multiplier selected by each fixture case.
 double getResearchValue(const Seat*,int,double base,const std::string&){return base*factor;}}
namespace ODApplication{const double turnsPerSecond=1.4;}
const size_t noCot=std::numeric_limits<size_t>::max();
"""

# Assemble the room declaration with actual state records and the methods under test.
def room_declaration():
    return "//! \\brief Declares the infirmary state and production methods exercised by the probes.\nstruct RoomInfirmary:Room {\n" + records() + r"""
 //! \brief Inherits fixture construction with an explicit map and keeper.
 using Room::Room;
 std::map<size_t,CotInfo> mCots;std::map<size_t,PatientInfo> mPatients;std::map<size_t,Tile*> mCotObjects;
 std::vector<Tile*> mAccessoryTiles;size_t mNextCotId=0;bool mLoadedCots=false;
 bool mManaShortageNotified=false,mHealingTurnFailed=false;int64_t mHealingTurn=-1;
 //! \brief Tests the production admission preflight without spending resources.
 bool canPayAdmission(const Creature&,bool)const;
 //! \brief Executes production admission charging and reports the amount and payer.
 bool payAdmission(Creature&,bool,double&,int&);
 //! \brief Executes one production treatment turn for the supplied patient.
 bool healPatient(Creature&);
 //! \brief Returns the shared keeper discharge threshold through the production method.
 int getDischargeThreshold()const;
 //! \brief Executes production admission onto a specified cot.
 bool admit(size_t,Creature&,bool);
 //! \brief Finds the actual active admission for the supplied creature.
 PatientInfo* getPatient(Creature&);
 //! \brief Executes production treatment interruption cleanup.
 void releasePatient(Creature&);
 //! \brief Executes production healing and threshold discharge for an admitted creature.
 bool restPatient(Creature&);
 //! \brief Restores the saved death countdown for one abandoned admission.
 void abandon(size_t);
 //! \brief Executes production abandonment for every patient and reservation.
 void abandonAll();
 //! \brief Executes the production deterministic cot placement algorithm.
 void layoutCots();
 //! \brief Executes production validation of the joined floor's minimum build square.
 static bool containsMinimumBlock(GameMap&,Seat*,const std::vector<Tile*>&);
 //! \brief Maps the production creature bed footprint to its required cot size.
 static int cotSize(const Creature&);
 //! \brief Executes production matching-cot selection with the requested manual policy.
 size_t findCot(const Creature&,bool)const;
 //! \brief Executes actual carrying eligibility and admission preflight.
 bool hasCarryEntitySpot(GameEntity*);
 //! \brief Executes the actual cot reservation or saved-reservation reuse path.
 Tile* reserveCot(Creature&,Creature&);
 //! \brief Returns the delivery tile owned by the creature's actual reservation.
 Tile* askSpotForCarriedEntity(GameEntity*);
 //! \brief Executes production reservation cleanup when a worker stops carrying.
 void cancelReservation(Creature&);
 //! \brief Executes production admission handling when a carrier reaches its destination.
 void notifyCarryingStateChanged(Creature*,GameEntity*);
 //! \brief Executes the actual manual-drop eligibility and keeper-payment rule.
 void creatureDropped(Creature&);
 //! \brief Records a cot's tile without creating a rendered building object.
 void createCotObject(size_t id){mCotObjects[id]=getGameMap()->getTile(mCots.at(id).x,mCots.at(id).y);}
 //! \brief Executes production rebinding of saved patients and reserved carries.
 void restoreInitialEntityState();
 //! \brief Invokes actual layout at the fixture's initial entity-creation stage.
 void updateActiveSpots(){layoutCots();}
 //! \brief Rebinds the saved figure position without creating renderer resources.
 void updateShaman(){if(mHasLoadedShamanPosition){static InfirmaryShamanEntity figure;figure.position=Ogre::Vector3(mLoadedShamanPosition.x,mLoadedShamanPosition.y,0);mShaman=&figure;}}
 //! \brief Writes the actual infirmary room save payload.
 void exportToStream(std::ostream&)const;
 //! \brief Reads the actual optional infirmary room save tags.
 bool importFromStream(std::istream&);
 InfirmaryShamanEntity* mShaman=nullptr;bool mHasLoadedShamanPosition=false;Ogre::Vector2 mLoadedShamanPosition;
 //! \brief Writes the actual optional shaman position record.
 void exportShamanToStream(std::ostream&)const;
 //! \brief Reads the actual optional shaman position without consuming later room tags.
 bool importShamanFromStream(std::istream&);
};
"""

# Exercise production fees, treatment, discharge, cooldown restoration and mood initialization.
def main():
    economy = re.sub(r'^#include[^\n]*\n', '', read("source/rooms/RoomInfirmaryEconomy.cpp"), flags=re.M)
    core = read("source/rooms/RoomInfirmary.cpp")
    code = PRELUDE + room_declaration() + economy
    for signature in ("bool RoomInfirmary::admit(", "RoomInfirmary::PatientInfo* RoomInfirmary::getPatient(",
            "void RoomInfirmary::releasePatient(", "bool RoomInfirmary::restPatient(",
            "void RoomInfirmary::abandon(", "void RoomInfirmary::abandonAll(",
            "int RoomInfirmary::cotSize(", "size_t RoomInfirmary::findCot(",
            "bool RoomInfirmary::hasCarryEntitySpot(", "Tile* RoomInfirmary::reserveCot(",
            "Tile* RoomInfirmary::askSpotForCarriedEntity(", "void RoomInfirmary::cancelReservation(",
            "void RoomInfirmary::notifyCarryingStateChanged(", "void RoomInfirmary::creatureDropped("):
        code += function(core, signature) + "\n"
    code += function(read("source/entities/Creature.cpp"), "void Creature::setInfirmaryAdmissionMood(")
    code += function(read("source/creaturebehaviour/CreatureBehaviourAttackEnemy.cpp"),
        "bool CreatureBehaviourAttackEnemy::processBehaviour(")
    expiry = function(read("source/entities/Creature.cpp"), "    if(mInfirmaryMoodTurns > 0.0)")
    code += "\n//! \\brief Executes the production per-turn admission mood expiration block.\nvoid expireMood(Creature& creature){" + expiry.replace("mInfirmaryMood", "creature.mInfirmaryMood") + "}\n"
    sleep = read("source/creatureaction/CreatureActionSleep.cpp")
    start = sleep.index("        creature.setHP(")
    bed = sleep[start:sleep.index(";", start)+1]
    code += "\n//! \\brief Executes the production bed-healing expression with explicit research and dirt inputs.\nvoid bedHeal(Creature& creature,Seat* sleepingSeat,double dirtOutputFactor){" + bed + "}\n"
    # Keep cross-component gates tied to the actual paths rather than a second invented admission model.
    for path, needle in (("source/creaturebehaviour/CreatureBehaviourAttackEnemy.cpp", "DormitoryWoundedCarryHpPercent"),
            ("source/creatureaction/CreatureActionCarryEntity.cpp", "RoomType::infirmary"),
            ("source/creatureaction/CreatureActionSearchEntityToCarry.cpp", "std::stable_partition")):
        assert needle in read(path), (path, needle)
    assert "manual ? ConfigManager::getSingleton().getNbTurnsKoCreatureAttacked()" in core
    assert "cancelReservation(*carrier)" in function(core,"void RoomInfirmary::notifyCarryingStateChanged(")
    assert "mRoom.releasePatient(mCreature);" in function(read("source/creatureaction/CreatureActionInfirmaryRest.cpp"),
        "CreatureActionInfirmaryRest::~CreatureActionInfirmaryRest(")
    redirect = function(read("source/creatureaction/CreatureActionCarryEntity.cpp"),
        "    if(mBuildingDest->getObjectType() == GameEntityType::room && static_cast<Room*>(mBuildingDest)->getType() == RoomType::infirmary)")
    code += r"""
//! \brief Exercises the actual same-carry infirmary-to-bed redirection fragment.
struct CarryRedirect{Creature& mCreature;Room* mBuildingDest;Tile* mTileDest;int mDragPhase=2,mDragLayTurns=8;bool stopped=false;
 //! \brief Records that actual carry redirection had to stop the transport.
 bool stopDragging(bool){stopped=true;return false;}
 //! \brief Executes the actual infirmary-to-bed redirection fragment.
 bool redirect(Creature* dragged){REDIRECT return true;}
};
//! \brief Executes the production rest-action cleanup independently of rendering and animation services.
struct RestLifecycle{Creature& mCreature;RoomInfirmary& mRoom;
 //! \brief Executes the actual rest-action destructor to release its patient's cot.
 ~RestLifecycle();
};
""".replace("REDIRECT", redirect)
    code += function(read("source/creatureaction/CreatureActionInfirmaryRest.cpp"),
        "CreatureActionInfirmaryRest::~CreatureActionInfirmaryRest(").replace("CreatureActionInfirmaryRest", "RestLifecycle")
    code += r"""
//! \brief Runs treatment, admission, carry, combat and resource regression cases.
int main(){try{
 GameMap map;Seat seat;Room treasury(&map,&seat);map.rooms.push_back(&treasury);RoomInfirmary room(&map,&seat);
 Creature creature;CreatureMoodFee fee;CreatureMoodRested rested;creature.definition.moods={&fee,&rested};
 double amount=0;int payer=-1;
 check(room.payAdmission(creature,false,amount,payer),"keeper admission accepted");near(amount,17.4,"fractional admission");
 near(map.treasury,982.6,"keeper exact charge");near(creature.mInfirmaryMood,36,"keeper fee mood");near(creature.mInfirmaryMoodTurns,30,"rested lifetime");
 seat.payer=1;check(room.payAdmission(creature,false,amount,payer),"creature admission accepted");
 near(creature.gold,82.6,"purse exact charge");near(map.credited,17.4,"purse admission credited");near(creature.mInfirmaryMood,-36,"creature fee mood");
 check(room.payAdmission(creature,true,amount,payer)&&payer==0,"manual drop forces keeper");near(creature.gold,82.6,"manual leaves purse");
 seat.player.human=false;check(room.payAdmission(creature,false,amount,payer)&&payer==0,"AI forces keeper");seat.player.human=true;
 creature.gold=17.3;double before=map.credited;check(!room.payAdmission(creature,false,amount,payer),"insufficient purse refuses");near(map.credited,before,"refusal no partial charge");
 seat.payer=0;treasury.gold=17.3;before=map.treasury;check(!room.payAdmission(creature,false,amount,payer),"insufficient treasury refuses");near(map.treasury,before,"keeper refusal no partial charge");treasury.gold=1000;
 for(double wage:{58.0,2320.0})for(double maximum:{100.0,1703.0})for(double factor:{1.0,.8,.667}){
  creature.definition.fee=wage;creature.maximum=maximum;creature.hp=0;seat.mana=10000;SkillManager::factor=factor;map.turn+=1;
  check(room.healPatient(creature),"heals at research speed");near(maximum/creature.hp,84*factor,"infirmary turns");
  const double initial=10000;while(creature.hp<maximum-1e-9){++map.turn;check(room.healPatient(creature),"full treatment");}
  near(initial-seat.mana,2*wage,"exact mana per full treatment including final partial turn");
 }
 creature.definition.fee=58;
 for(double factor:{1.0,1.2,1.4}){SkillManager::factor=factor;creature.maximum=1000;creature.hp=0;
  bedHeal(creature,&seat,1);near(1000/creature.hp,210/factor,"bed full-heal turns");}
 creature.definition.sleepHeal=0;creature.hp=1;bedHeal(creature,&seat,1);near(creature.hp,1,"zero bed healing remains zero");
 SkillManager::factor=1;creature.hp=10;seat.mana=0;creature.counter=0;++map.turn;int notices=seat.player.notices;
 check(!room.healPatient(creature),"mana shortage pauses");near(creature.hp,10,"shortage no HP");check(creature.counter==0,"paused death counter stopped");
 check(!room.healPatient(creature)&&seat.player.notices==notices+1,"notice collected per room");
 ++map.turn;check(!room.healPatient(creature)&&seat.player.notices==notices+1,"shortage does not spam across turns");
 seat.heal=false;seat.mana=10000;before=seat.mana;++map.turn;check(!room.healPatient(creature),"healing switched off");near(seat.mana,before,"off spends no mana");
 seat.heal=true;++map.turn;check(room.healPatient(creature),"successful turn resumes");++map.turn;seat.mana=0;room.healPatient(creature);check(seat.player.notices==notices+2,"successful turn rearms notice");
 seat.mana=10000;map.turn=140;creature.hp=10;int glows=creature.glows;room.healPatient(creature);check(creature.glows==glows+1,"seventh turn glow");
 RoomInfirmary::CotInfo cot={};cot.size=1;cot.width=1;cot.height=1;room.mCots[0]=cot;
 creature.counter=-73;check(room.admit(0,creature,false),"carried admission");check(creature.counter==0&&room.mPatients[0].storedCounter==73,"admission stores counter");room.abandon(0);check(creature.counter==-73,"loss restores remaining counter");
 creature.counter=-73.375;check(room.admit(0,creature,false),"fractional carried admission");check(creature.counter==0&&room.mPatients[0].storedCounter==73.375,"admission preserves fractional death time");room.abandon(0);check(creature.counter==-73.375,"loss restores exact fractional death time");
 check(room.admit(0,creature,true),"manual admission");room.abandon(0);check(creature.counter==-120,"manual loss restores full counter");
 Tile home={0,0};creature.home=&home;creature.hp=500;seat.threshold=40;seat.heal=false;room.mPatients[0].creature=&creature;
 check(room.restPatient(creature),"switched-off threshold does not discharge");seat.heal=true;int sleeps=creature.sleeps;
 check(!room.restPatient(creature)&&creature.sleeps==sleeps+1,"partial discharge goes to own bed");
 creature.hp=creature.maximum;room.mPatients[0].creature=&creature;sleeps=creature.sleeps;
 check(!room.restPatient(creature)&&creature.sleeps==sleeps,"full discharge returns to normal");
 creature.setInfirmaryAdmissionMood(true);for(int i=0;i<29;++i)expireMood(creature);near(creature.mInfirmaryMood,-36,"mood retained for 29 turns");expireMood(creature);near(creature.mInfirmaryMood,0,"mood expires on turn 30");
 creature.definition.moods.clear();creature.setInfirmaryAdmissionMood(true);near(creature.mInfirmaryMood,0,"no Fee means no admission mood");near(creature.mInfirmaryMoodTurns,30,"missing Rested uses configured duration");
 CreatureBehaviourAttackEnemy attack;creature.enemies={1};creature.maximum=100;creature.hp=34;creature.actions={CreatureActionType::infirmaryRest};
 attack.processBehaviour(creature);check(creature.fights==0&&creature.flees==0,"patient below 35 percent remains lying");
 creature.actions={CreatureActionType::sleep};attack.processBehaviour(creature);check(creature.fights==0,"sleeper below 35 percent remains lying");
 creature.hp=35;creature.actions={CreatureActionType::infirmaryRest};room.mPatients[0].creature=&creature;
 {RestLifecycle rest{creature,room};attack.processBehaviour(creature);check(creature.fights==1,"patient at 35 percent can fight");}
 check(room.getPatient(creature)==nullptr,"ending the rest action releases treatment");
 room.mPatients.clear();map.tiles[{0,0}]={0,0};Creature incoming,carrier,other;incoming.name="incoming";carrier.name="carrier";other.name="other";
 incoming.owner=&seat;other.owner=&seat;incoming.hp=10;incoming.counter=-51;incoming.home=&home;carrier.tile=map.getTile(0,0);
 check(room.reserveCot(incoming,carrier)==map.getTile(0,0),"available cot reserved");check(room.askSpotForCarriedEntity(&incoming)==map.getTile(0,0),"reservation returns delivery tile");
 check(!room.hasCarryEntitySpot(&other),"another creature cannot take reservation");room.cancelReservation(carrier);check(room.mPatients.empty(),"interrupted carry releases reservation");
 room.reserveCot(incoming,carrier);before=map.treasury;room.notifyCarryingStateChanged(&carrier,&incoming);
 check(room.mPatients.at(0).creature==&incoming&&incoming.counter==0,"reserved arrival becomes patient");near(before-map.treasury,17.4,"arrival charges once");room.abandonAll();check(incoming.counter==-51,"abandon all restores admitted counter");
 incoming.counter=-51.625;room.reserveCot(incoming,carrier);room.notifyCarryingStateChanged(&carrier,&incoming);check(room.mPatients.at(0).storedCounter==51.625&&incoming.counter==0,"carried arrival preserves fractional death time");room.abandonAll();check(incoming.counter==-51.625,"abandon all restores exact fractional arrival counter");
 incoming.counter=-51;room.reserveCot(incoming,carrier);seat.payer=1;creature.owner=&seat;creature.hp=10;creature.home=&home;before=map.treasury;
 room.creatureDropped(creature);check(room.mPatients.at(0).creature==&creature&&room.mPatients.at(0).manual&&room.mPatients.at(0).payer==0,"manual drop overrides reservation and forces keeper");near(before-map.treasury,17.4,"manual keeper charge");
 before=map.treasury;room.notifyCarryingStateChanged(&carrier,&incoming);near(map.treasury,before,"cot taken at arrival never charges carried creature");
 check(room.mPatients.at(0).creature==&creature,"stale arrival preserves manual patient");
 Room dormitory(&map,&seat);dormitory.type=RoomType::dormitory;dormitory.delivery=&home;home.room=&dormitory;
 CarryRedirect taken{carrier,&room,map.getTile(0,0)};check(taken.redirect(&incoming)&&taken.mBuildingDest==&dormitory&&taken.mTileDest==&home,"taken cot redirects same carry to own bed");
 check(taken.mDragPhase==0&&taken.mDragLayTurns==0&&!taken.stopped,"same carry restarts final approach");
 room.abandonAll();seat.payer=0;incoming.counter=-51;room.reserveCot(incoming,carrier);treasury.gold=0;
 CarryRedirect unpaid{carrier,&room,map.getTile(0,0)};check(unpaid.redirect(&incoming)&&unpaid.mBuildingDest==&dormitory,"unpaid admission redirects to own bed");check(room.mPatients.empty(),"unpaid redirection frees reservation");
 incoming.home=nullptr;CarryRedirect homeless{carrier,&room,map.getTile(0,0)};check(!homeless.redirect(&incoming)&&homeless.stopped,"failed admission without own bed stops safely");
 room.abandonAll();treasury.gold=0;sleeps=creature.sleeps;room.creatureDropped(creature);check(room.mPatients.empty()&&creature.sleeps==sleeps+1,"manual refusal goes to own bed");
 std::cout<<"infirmary rules: ok\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
"""
    run_probe("infirmary-rules", code)

if __name__ == "__main__":
    main()
