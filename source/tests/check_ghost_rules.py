"""Compile extracted production ghost rules against controlled world services.

This script invokes the developer compiler and must only run after the whole-plan
completion gate. Importing its extraction helpers does not compile or run a probe.
"""
from pathlib import Path
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]

# Read production text independently of the working directory.
def read(path):
    return (repo / path).read_text(encoding='utf-8')

# Extract a complete brace-delimited production body without rewriting its statements.
def function(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

# Compile and execute the actual extracted bodies with bounded closed-input children.
def run_probe(name, code):
    with tempfile.TemporaryDirectory(prefix=name+'-') as directory:
        work = Path(directory)
        source, binary = work/'check.cpp', work/'check.exe'
        source.write_text(code, encoding='utf-8')
        subprocess.run(['cl','/nologo','/EHsc','/MD','/std:c++17',str(source),'/Fe:'+str(binary)],
            cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=180)
        subprocess.run([str(binary)], cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=180)

PRELUDE = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <deque>
#include <iomanip>
#include <iostream>
#include <limits>
#include <list>
#include <map>
#include <memory>
#include <queue>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#define OD_LOG_INF(x) ((void)0)
#define OD_LOG_ERR(x) ((void)0)
#define OD_ASSERT_TRUE(x) check(bool(x),"packet read")
const unsigned int MAX_LEVEL=30;
//! \brief Rejects a failed independent expected result.
void check(bool result,const char* label){if(!result)throw std::runtime_error(label);}
//! \brief Compares fractional counters without rounding them.
void near(double result,double expected,const char* label){check(std::abs(result-expected)<1e-8,label);}
//! \brief Provides fixed real-time conversion for probe expectations.
namespace ODApplication{const double turnsPerSecond=1.4;}
//! \brief Supplies the vector coordinates used by world and codec bodies.
namespace Ogre{
//! \brief Stores an unrounded two-dimensional position.
struct Vector2{float x=0,y=0;
 //! \brief Initializes a world position.
 Vector2(float a=0,float b=0):x(a),y(b){}
};
//! \brief Stores an unrounded three-dimensional position.
struct Vector3{float x=0,y=0,z=0;
 //! \brief Initializes a world position.
 Vector3(float a=0,float b=0,float c=0):x(a),y(b),z(c){}
 static const Vector3 ZERO;
};const Vector3 Vector3::ZERO;using Real=float;}
//! \brief Supplies animation names used by the production state transitions.
namespace EntityAnimation{const std::string idle_anim="Idle",walk_anim="Walk",rot_anim="Rot";}
//! \brief Captures serialized values and allows a speculative packet copy without advancing its parent.
struct ODPacket{std::vector<std::string> tokens;size_t cursor=0;bool valid=true;
 //! \brief Writes one value into a distinct packet token.
 template<class T> ODPacket& operator<<(const T& value){std::ostringstream out;out<<std::setprecision(17)<<value;tokens.push_back(out.str());return *this;}
 //! \brief Reads exactly one typed packet token.
 template<class T> ODPacket& operator>>(T& value){if(cursor>=tokens.size()){valid=false;return *this;}std::istringstream in(tokens[cursor++]);if(!(in>>value))valid=false;return *this;}
 //! \brief Reads a complete string token including an empty string.
 ODPacket& operator>>(std::string& value){if(cursor>=tokens.size()){valid=false;return *this;}value=tokens[cursor++];return *this;}
 //! \brief Reports whether every requested token was present.
 explicit operator bool()const{return valid;}
};
//! \brief Declares the controlled world interfaces.
struct Tile;struct Creature;struct Room;struct GameMap;struct GhostEntity;
//! \brief Exposes the production entity identifiers used by the probes.
enum class GameEntityType{creature,ghostEntity,ghostBoxEntity,other};
//! \brief Exposes the production room identifiers used by the probes.
enum class RoomType{crypt,ghostRoom,other};
//! \brief Exposes the research identifiers used by the probes.
enum class SkillType{roomCrypt,roomGhostRoom,roomTrainingHall};
//! \brief Exposes the selected ectoplasm products.
enum class GhostProduct{research,mana,crystal};
//! \brief Exposes the saved ghost phases.
enum class GhostState{rising,floating,beamed,boxed,dissolving};
//! \brief Exposes action eligibility flags.
enum class CreatureActionType{flee,fight,buyItem};
//! \brief Supplies keeper-notification eligibility.
struct Player{bool human=true;int deaths=0;
 //! \brief Reports whether this keeper is human.
 bool getIsHuman()const{return human;}
 //! \brief Counts the original death notice.
 void notifyCreatureKilled(Creature&){++deaths;}
};
//! \brief Supplies ownership, visibility and configurable research levels.
struct Seat{int id=1,tier=1;double mana=100000,bar=0,points=0;bool revive=true;GhostProduct product=GhostProduct::research;Player player;std::set<Tile*> seen;
 //! \brief Returns this keeper's stable identifier.
 int getId()const{return id;}
 //! \brief Returns the notification recipient.
 Player* getPlayer(){return &player;}
 //! \brief Reports allied ownership.
 bool isAlliedSeat(const Seat* other)const{return other==this;}
 //! \brief Reports prior exploration.
 bool hasSeenTile(Tile* tile)const{return seen.count(tile)!=0;}
 //! \brief Reports the revival switch.
 bool getGhostRevive()const{return revive;}
 //! \brief Returns stored mana.
 double getMana()const{return mana;}
 //! \brief Returns the ectoplasm balance.
 double getEctoplasmLevels()const{return bar;}
 //! \brief Retains the full fractional ectoplasm balance.
 void setEctoplasmLevels(double value){bar=value;}
 //! \brief Returns the selected product.
 GhostProduct getGhostProduct()const{return product;}
 //! \brief Adds mana with the actual public capacity contract.
 void addMana(double value){mana=std::min(200000.0,mana+value);}
 //! \brief Adds research points without discarding fractions.
 void addSkillPoints(double value){points+=value;}
 //! \brief Counts an actual lich arrival.
 void notifyCreatureArrival(const std::string&){}
};
//! \brief Supplies the decided values independently of extracted production formulas.
struct ConfigManager{
 //! \brief Returns the fixture configuration.
 static ConfigManager& getSingleton(){static ConfigManager config;return config;}
 //! \brief Returns named room values required by these bodies.
 double getRoomConfigDouble(const std::string& key)const{const std::map<std::string,double> values={{"GhostRiseSeconds",1.5},{"GhostDissolveSeconds",1.5},{"GhostHowlMinSeconds",10},{"GhostHowlMaxSeconds",20},{"GhostBoxOpenSeconds",120},{"GhostRoomMinSide",4},{"GhostHuntersPerCauldron",3},{"GhostLevelsPerEctoplasm",10},{"GhostEctoplasmMana",10000},{"GhostEctoplasmResearchPoints",2000},{"CryptCorpsesPerLich",10},{"CryptLichLevelBonus",0},{"GhostBeamRange",1},{"GhostReviveMana",14000},{"TrainHallXpPerAttack",5},{"TrainHallCooldownHitMin",3},{"TrainHallCooldownHitMax",6}};return values.at(key);}
 //! \brief Reads an integer room setting.
 int getRoomConfigInt32(const std::string& key)const{return int(getRoomConfigDouble(key));}
 //! \brief Reads an unsigned room setting.
 uint32_t getRoomConfigUInt32(const std::string& key)const{return uint32_t(getRoomConfigDouble(key));}
 //! \brief Returns the canonical corpse lying duration.
 double getCorpseLieSeconds()const{return 120;}
 //! \brief Returns the decided wander search radius.
 unsigned int getGhostWanderRadius()const{return 8;}
 //! \brief Returns the canonical corpse decay duration.
 double getCorpseDecaySeconds()const{return 240;}
 //! \brief Returns the shared trap fear radius.
 uint32_t getTrapConfigUInt32(const std::string&)const{return 3;}
 //! \brief Returns the shared trap flee duration.
 double getTrapConfigDouble(const std::string&)const{return 20;}
 //! \brief Returns the independent reveal lifetime.
 int getSpellConfigInt32(const std::string&)const{return 10;}
 //! \brief Returns the independent population limit.
 size_t getMaxCreaturesPerSeatAbsolute()const{return 20;}
 //! \brief Returns the canonical lich class.
 const std::string& getRoomConfigString(const std::string&)const{static const std::string value="Lich";return value;}
};
//! \brief Supplies the exact research results independently of the production consumers.
struct SkillManager{
 //! \brief Returns configured tier values without duplicating consumer algorithms.
 static double getResearchValue(const Seat* seat,SkillType,double base,const std::string& effect){const size_t tier=seat->tier-1;if(effect=="LichLevel")return tier;if(effect=="LichCorpses"||effect=="EctoplasmLevels"){const double factors[]={1,.8,.6};return base*factors[tier];}if(effect=="BeamRange"||effect=="BoxCapacity")return base+tier;if(effect=="CatchTime"){const double factors[]={1,.8,.667};return base*factors[tier];}if(effect=="RevivePrice")return base-2000*tier;if(effect=="XpPerHit"){const double factors[]={1,1.2,1.4};return base*factors[tier];}return base;}
};
//! \brief Supplies deterministic random choices while allowing boundary selection.
namespace Random{unsigned int choice=0;
 //! \brief Chooses a bounded controlled integer.
 unsigned int Uint(unsigned int low,unsigned int high){return low+choice%(high-low+1);}
 //! \brief Returns the midpoint of a look-only random range.
 double Double(double low,double high){return (low+high)/2;}}
'''

GHOST_WORLD = r'''
//! \brief Supplies room identity to tiles and crypt placement checks.
struct Room{RoomType type=RoomType::other;Seat* seat=nullptr;std::vector<Tile*> floor;
 //! \brief Returns the fixture room type.
 RoomType getType()const{return type;}
 //! \brief Returns the fixture room owner.
 Seat* getSeat()const{return seat;}
 //! \brief Returns the complete room floor.
 const std::vector<Tile*>& getCoveredTiles()const{return floor;}
};
//! \brief Stores real topology, visibility and territory independently of rule bodies.
struct Tile{int x=0,y=0;bool full=false;Seat* owner=nullptr;Room* room=nullptr;double dirt=0;std::vector<Tile*> neighbors;std::vector<Seat*> vision;
 static constexpr double MAX_DIRT=100;
 //! \brief Returns the tile column.
 int getX()const{return x;}
 //! \brief Returns the tile row.
 int getY()const{return y;}
 //! \brief Reports solid terrain; doors intentionally do not become full terrain.
 bool isFullTile()const{return full;}
 //! \brief Reports keeper territory.
 bool isClaimedForSeat(const Seat* seat)const{return owner==seat;}
 //! \brief Returns the covering room.
 Room* getCoveringRoom(){return room;}
 //! \brief Returns adjacent topology.
 const std::vector<Tile*>& getAllNeighbors()const{return neighbors;}
 //! \brief Returns observing keepers.
 const std::vector<Seat*>& getSeatsWithVision()const{return vision;}
 //! \brief Records dirt emitted by the actual corpse branch.
 void addDirt(double value){dirt=std::min(MAX_DIRT,dirt+value);}
};
//! \brief Supplies creature-definition facts used by fear and creation.
struct CreatureDefinition{bool worker=false,afraid=false;std::string name="Rat";
 //! \brief Reports worker identity.
 bool isWorker()const{return worker;}
 //! \brief Reports the optional fear flag.
 bool isAfraidOfGhosts()const{return afraid;}
 //! \brief Returns the declared creature class.
 const std::string& getClassName()const{return name;}
 //! \brief Returns the class mesh identity.
 std::string getMeshName()const{return name+".mesh";}
};
//! \brief Supplies only the world lookups and independent visibility list consumed by ghosts.
struct GameMap{std::map<std::pair<int,int>,Tile> tiles;std::vector<Creature*> creatures;std::vector<GhostEntity*> ghosts;std::vector<Seat*> seats;std::vector<Tile*> visible;CreatureDefinition definition;int turn=0;
 //! \brief Returns an existing tile without inventing map geometry.
 Tile* getTile(int x,int y){std::map<std::pair<int,int>,Tile>::iterator it=tiles.find({x,y});return it==tiles.end()?nullptr:&it->second;}
 //! \brief Returns the controlled line-of-sight result.
 std::vector<Tile*> visibleTiles(int,int,uint32_t){return visible;}
 //! \brief Returns creatures present in the controlled world.
 const std::vector<Creature*>& getCreatures()const{return creatures;}
 //! \brief Resolves a stable creature name.
 Creature* getCreature(const std::string& name);
 //! \brief Resolves typed ghosts without conflating boxes.
 GhostEntity* getEntityFromTypeAndName(GameEntityType,const std::string& name);
 //! \brief Returns the current world turn.
 int getTurnNumber()const{return turn;}
 //! \brief Returns the declared class.
 const CreatureDefinition* getClassDescription(const std::string&){return &definition;}
 //! \brief Resolves a saved keeper.
 Seat* getSeatById(int id){for(Seat* seat:seats)if(seat->id==id)return seat;return nullptr;}
 //! \brief Returns living population after a corpse has left the map.
 std::vector<Creature*> getCreaturesBySeat(Seat* seat);
 //! \brief Returns the fixed map width used by reveal probes.
 int getMapSizeX()const{return 8;}
 //! \brief Returns the fixed map height used by reveal probes.
 int getMapSizeY()const{return 8;}
};
//! \brief Records fear, death and placement effects without implementing their rules.
struct Creature{GameMap* map=nullptr;Seat* seat=nullptr;Tile* tile=nullptr;CreatureDefinition definition;std::string name="victim";bool alive=true,ko=false,onMap=true,prison=false,flee=false,deleted=false;unsigned int level=1;int flees=0,interrupts=0;double exp=0;
 //! \brief Initializes a plain controlled creature.
 Creature()=default;
 //! \brief Initializes a spawned lich in the actual production constructor call.
 Creature(GameMap* world,const CreatureDefinition*,Seat* owner):map(world),seat(owner){}
 //! \brief Returns the stable creature name.
 const std::string& getName()const{return name;}
 //! \brief Returns class flags.
 const CreatureDefinition* getDefinition()const{return &definition;}
 //! \brief Reports health eligibility.
 bool isAlive()const{return alive;}
 //! \brief Reports knockout eligibility.
 bool isKo()const{return ko;}
 //! \brief Reports hand/map eligibility.
 bool getIsOnMap()const{return onMap;}
 //! \brief Reports prison eligibility.
 bool isInPrison()const{return prison;}
 //! \brief Reports an existing flee action.
 bool isActionInList(CreatureActionType)const{return flee;}
 //! \brief Returns the current tile.
 Tile* getPositionTile()const{return tile;}
 //! \brief Applies the observed production fear effect.
 void fleeFromTile(Tile*,double turns,bool scared){check(turns==20&&scared,"canonical fear effect");flee=true;++flees;}
 //! \brief Returns the saved level.
 unsigned int getLevel()const{return level;}
 //! \brief Initializes the spawned lich level.
 void setLevel(unsigned int value){level=value;}
 //! \brief Returns the keeper.
 Seat* getSeat()const{return seat;}
 //! \brief Removes this exact corpse from population.
 void removeFromGameMap(){onMap=false;if(map!=nullptr)map->creatures.erase(std::remove(map->creatures.begin(),map->creatures.end(),this),map->creatures.end());}
 //! \brief Records deferred destruction without invalidating assertions.
 void deleteYourself(){deleted=true;}
 //! \brief Registers an actual spawned lich.
 void addToGameMap(){map->creatures.push_back(this);}
 //! \brief Records production spawn placement.
 void setPosition(const Ogre::Vector3& position){tile=map->getTile(int(position.x),int(position.y));}
 //! \brief Leaves renderer creation outside the behavioral fixture.
 void createMesh(){}
 //! \brief Records reservation invalidation caused by floor removal.
 void interruptGhostHunt(){++interrupts;}
};
//! \brief Resolves actual fixture creature identities.
Creature* GameMap::getCreature(const std::string& name){for(Creature* creature:creatures)if(creature->name==name)return creature;return nullptr;}
//! \brief Returns the population of the requested keeper.
std::vector<Creature*> GameMap::getCreaturesBySeat(Seat* seat){std::vector<Creature*> result;for(Creature* creature:creatures)if(creature->seat==seat)result.push_back(creature);return result;}
//! \brief Supplies particle expiry counters used by the actual upkeep body.
struct EntityParticleEffect{int mNbTurnsEffect=10;
 //! \brief Initializes a continuation particle.
 EntityParticleEffect(const std::string&,const std::string&,int turns):mNbTurnsEffect(turns){}
};
//! \brief Supplies transparent base codec services rather than ghost rule implementations.
struct RenderedMovableEntity{
 //! \brief Supplies the unchanged creation packet prefix.
 void exportToPacket(ODPacket&,const Seat*)const{}
 //! \brief Supplies the unchanged creation packet reader prefix.
 void importFromPacket(ODPacket&){}
 //! \brief Supplies the unchanged update packet prefix.
 void exportToPacketForUpdate(ODPacket&,Seat*){}
 //! \brief Supplies the unchanged update reader prefix.
 void updateFromPacket(ODPacket&){}
};using GameEntity=RenderedMovableEntity;
//! \brief Captures positional sounds without running a network server.
struct ServerNotification{ODPacket mPacket;
 //! \brief Creates a captured message.
 ServerNotification(int,Player*){}
};
//! \brief Provides the one notification kind used by actual upkeep.
namespace ServerNotificationType{const int playSpatialSound=1;}
//! \brief Counts routed server messages.
struct ODServer{int notices=0;
 //! \brief Returns the controlled server.
 static ODServer& getSingleton(){static ODServer value;return value;}
 //! \brief Releases captured notifications.
 void queueServerNotification(ServerNotification* notice){++notices;delete notice;}
};
//! \brief Records the exact published social call.
namespace social{enum class PostCategory{GhostScared};
//! \brief Counts actual ghost scare posts.
struct PostLog{int posts=0;
 //! \brief Returns the controlled social service.
 static PostLog& getSingleton(){static PostLog value;return value;}
 //! \brief Records a real emitted post.
 void addPost(int,const std::string&,const std::string&,bool,PostCategory,int){++posts;}
};}
//! \brief Holds the actual fields consumed by extracted ghost methods.
struct GhostEntity:RenderedMovableEntity{GameMap* map=nullptr;Seat* seat=nullptr;std::string mName="ghost",mClassName="Rat",mCreatureName="victim",mAssignedHunter,mPrevAnimationState;bool mPrevAnimationStateLoop=true,server=true,deleted=false,moving=false;unsigned int mLevel=5;double mLifeLeft=17.25,mStateTurns=0,mHowlTurns=100;GhostState mState=GhostState::floating;Ogre::Vector3 mPosition;std::set<std::string> mScaredCreatures;std::deque<Ogre::Vector2> mWalkQueue;std::vector<EntityParticleEffect*> mEntityParticleEffects;std::vector<Seat*> mSeatsWithVisionNotified;
 //! \brief Returns authority status.
 bool getIsOnServerMap()const{return server;}
 //! \brief Returns the fixture map.
 GameMap* getGameMap()const{return map;}
 //! \brief Returns the ghost tile.
 Tile* getPositionTile(){return map->getTile(int(mPosition.x),int(mPosition.y));}
 //! \brief Returns the identity used by save records.
 const std::string& getName()const{return mName;}
 //! \brief Returns the original keeper.
 Seat* getSeat()const{return seat;}
 //! \brief Restores the original keeper.
 void setSeat(Seat* value){seat=value;}
 //! \brief Accepts the production mesh binding.
 void setMeshName(const std::string&){}
 //! \brief Supplies a deterministic particle name.
 std::string nextParticleSystemsName(){return "particle";}
 //! \brief Records production phase changes without supplying lifetime behavior.
 void setState(GhostState value){mState=value;mStateTurns=0;}
 //! \brief Records production hunter release.
 void setAssignedHunter(const std::string& value){mAssignedHunter=value;}
 //! \brief Returns the saved phase.
 GhostState getState()const{return mState;}
 //! \brief Returns hunter ownership.
 const std::string& getAssignedHunter()const{return mAssignedHunter;}
 //! \brief Returns the original creature identity.
 const std::string& getCreatureName()const{return mCreatureName;}
 //! \brief Returns the original level.
 unsigned int getLevel()const{return mLevel;}
 //! \brief Records the exact teleport endpoint.
 void teleport(const Ogre::Vector3& value){mPosition=value;}
 //! \brief Returns the saved placement.
 const Ogre::Vector3& getPosition()const{return mPosition;}
 //! \brief Records removal.
 void removeFromGameMap(){deleted=true;}
 //! \brief Records deferred destruction.
 void deleteYourself(){deleted=true;}
 //! \brief Reports whether the controlled movement queue is active.
 bool isMoving()const{return moving;}
 //! \brief Receives an actual production flight path.
 void setWalkPath(const std::string&,const std::string&,bool,bool,const std::vector<Ogre::Vector2>& path,bool,bool){mWalkQueue.assign(path.begin(),path.end());moving=!path.empty();}
 //! \brief Receives a production refresh.
 void refresh(){}
 //! \brief Executes the production lifetime state machine.
 void doUpkeep();
 //! \brief Executes the production terrain search.
 void wander();
 //! \brief Executes the production visibility and fear gates.
 void scareCreatures();
 //! \brief Executes the production ghost save writer.
 void exportToStream(std::ostream&)const;
 //! \brief Executes the production ghost save reader.
 bool importFromStream(std::istream&);
 //! \brief Executes the production creation codec.
 void exportToPacket(ODPacket&,const Seat*)const;
 //! \brief Executes the production creation decoder.
 void importFromPacket(ODPacket&);
 //! \brief Executes the production update codec.
 void exportToPacketForUpdate(ODPacket&,Seat*);
 //! \brief Executes the production update decoder.
 void updateFromPacket(ODPacket&);
 //! \brief Receives a client appearance refresh.
 void updateLook(){}
};
//! \brief Resolves only exact typed ghost identities.
GhostEntity* GameMap::getEntityFromTypeAndName(GameEntityType type,const std::string& name){if(type!=GameEntityType::ghostEntity)return nullptr;for(GhostEntity* ghost:ghosts)if(ghost->mName==name)return ghost;return nullptr;}
'''

# Assemble the common ghost fixture with unchanged production lifetime, fear and movement bodies.
def ghost_fixture():
    source = read('source/entities/GhostEntity.cpp')
    return PRELUDE + GHOST_WORLD + ''.join(function(source,signature) for signature in
        ['void GhostEntity::doUpkeep(', 'void GhostEntity::wander(', 'void GhostEntity::scareCreatures('])

# Exercise lifetime phases, fear exclusions and actual graph search over controlled topology.
def main():
    code = ghost_fixture() + r'''
//! \brief Runs independent phase, visibility, immunity and terrain boundary cases.
int main(){
 GameMap map;Seat seat;map.seats.push_back(&seat);
 for(int y=0;y<7;++y)for(int x=0;x<7;++x){Tile& tile=map.tiles[{x,y}];tile.x=x;tile.y=y;tile.owner=&seat;}
 GhostEntity ghost;ghost.map=&map;ghost.seat=&seat;ghost.mPosition=Ogre::Vector3(3,3,0);
 for(GhostState state:{GhostState::rising,GhostState::floating,GhostState::beamed}){ghost.mState=state;ghost.mLifeLeft=8.125;ghost.doUpkeep();near(ghost.mLifeLeft,7.125,"active lifetime keeps fraction");}
 ghost.mState=GhostState::boxed;ghost.mLifeLeft=8.125;ghost.doUpkeep();near(ghost.mLifeLeft,8.125,"boxed lifetime pauses");
 ghost.mState=GhostState::beamed;ghost.mLifeLeft=.25;ghost.doUpkeep();check(ghost.mState==GhostState::dissolving,"zero lifetime dissolves");near(ghost.mLifeLeft,0,"life clamps at zero");
 ghost.mStateTurns=2.09;ghost.doUpkeep();check(!ghost.deleted,"dissolve animation not cut short");ghost.mStateTurns=2.1;ghost.doUpkeep();check(ghost.deleted,"dissolve completes");
 Creature creatures[9];for(int i=0;i<9;++i){creatures[i].name="c"+std::to_string(i);creatures[i].tile=map.getTile(3,4);creatures[i].definition.afraid=true;map.creatures.push_back(&creatures[i]);}
 creatures[1].definition.worker=true;creatures[2].definition.afraid=false;creatures[3].alive=false;creatures[4].ko=true;creatures[5].onMap=false;creatures[6].prison=true;creatures[7].flee=true;creatures[8].tile=map.getTile(0,0);
 map.visible.push_back(map.getTile(3,4));ghost.scareCreatures();check(creatures[0].flees==1,"visible flagged creature flees");for(int i=1;i<9;++i)check(creatures[i].flees==0,"fear excludes immune or invisible creature");
 ghost.scareCreatures();check(creatures[0].flees==1,"one scare during flight");creatures[0].flee=false;ghost.scareCreatures();check(creatures[0].flees==2,"scare available after flight ends");
 map.creatures.clear();ghost.mState=GhostState::floating;ghost.moving=false;map.getTile(4,3)->full=true;map.getTile(3,4)->full=true;
 for(unsigned int choice=0;choice<45;++choice){Random::choice=choice;ghost.wander();for(const Ogre::Vector2& step:ghost.mWalkQueue)check(!map.getTile(int(step.x),int(step.y))->full,"flight never crosses solid terrain");}
 // A locked door remains non-full; the production search has no owner, lock or ground restriction.
 for(std::pair<const std::pair<int,int>,Tile>& entry:map.tiles)entry.second.full=true;
 map.getTile(3,3)->full=false;map.getTile(4,3)->full=false;map.getTile(4,3)->owner=nullptr;ghost.wander();check(ghost.mWalkQueue.size()==1&&ghost.mWalkQueue.front().x==4,"non-full foreign locked door remains traversable");
 map.getTile(4,3)->full=true;ghost.mWalkQueue.clear();ghost.wander();check(ghost.mWalkQueue.empty(),"isolated ghost has no invented route");
 std::cout<<"ghost lifetime, fear and terrain: ok\n";
}
'''
    run_probe('ghost-rules', code)


# Assemble actual hunt branches, assignment and product code with controlled navigation and economy services.
def hunt_fixture():
    base = PRELUDE.replace('#include <vector>', '#include <vector>\n#include <tuple>\n#include <functional>')
    base = base.replace('flee,fight,buyItem', 'flee,fight,buyItem,huntGhost,fightFriendly')
    base = base.replace('const std::string idle_anim="Idle",walk_anim="Walk",rot_anim="Rot";', 'const std::string idle_anim="Idle",walk_anim="Walk",rot_anim="Rot",beam_anim="Beam",throw_anim="Throw",empty_anim="Empty";')
    base = base.replace(' static const Vector3 ZERO;', r'''
 //! \brief Returns an endpoint direction for production pose calls.
 Vector3 operator-(const Vector3& other)const{return Vector3(x-other.x,y-other.y,z-other.z);}
 static const Vector3 ZERO;''')
    base = base.replace('GhostState{rising', 'GhostState{rising')
    base = base.replace('std::set<Tile*> seen;', 'std::set<Tile*> seen;std::set<std::string> announced;')
    base = base.replace(' Player* getPlayer()', r'''
 //! \brief Deduplicates actual target bell identities.
 bool announceGhostTarget(const std::string& name){return announced.insert(name).second;}
 //! \brief Takes exact revival mana only when available.
 bool takeMana(double amount){if(mana<amount)return false;mana-=amount;return true;}
 Player* getPlayer()''')
    base = base.replace('{"GhostRiseSeconds",1.5}', '{"GhostBeamTurns",5.5},{"GhostEmptyTurns",5.5},{"GhostBoxCapacity",1},{"GhostRepathTurns",5},{"GhostBoxThrowSeconds",.5},{"GhostReviveHpShare",.35},{"GhostRiseSeconds",1.5}')
    code = r'''
//! \brief Supplies declared hunter efficiency independently of timing code.
struct CreatureRoomAffinity{double efficiency=3;
 //! \brief Returns the configured hunting job.
 RoomType getRoomType()const{return RoomType::ghostRoom;}
 //! \brief Returns the configured job efficiency.
 double getEfficiency()const{return efficiency;}
};
//! \brief Supplies job and worker flags to the actual assignment predicate.
struct CreatureDefinition{bool worker=false;std::vector<CreatureRoomAffinity> jobs{{3}};
 //! \brief Reports worker identity.
 bool isWorker()const{return worker;}
 //! \brief Returns all configured jobs.
 const std::vector<CreatureRoomAffinity>& getRoomAffinity()const{return jobs;}
 //! \brief Returns the configured hunter efficiency.
 const CreatureRoomAffinity& getRoomAffinity(RoomType)const{return jobs.front();}
 //! \brief Returns the social post class.
 std::string getClassName()const{return "PitDemon";}
};
//! \brief Stores actual territory and terrain facts for navigation and reveal.
struct Tile{int x=0,y=0;bool reachable=true;Seat* owner=nullptr;Room* room=nullptr;
 //! \brief Returns the tile column.
 int getX()const{return x;}
 //! \brief Returns the tile row.
 int getY()const{return y;}
 //! \brief Reports keeper ownership.
 bool isClaimedForSeat(const Seat* value)const{return owner==value;}
 //! \brief Returns its room.
 Room* getCoveringRoom()const{return room;}
};
//! \brief Supplies room type, ownership and floor to actual dispatch.
struct Room{RoomType type=RoomType::other;Seat* seat=nullptr;std::string name;std::vector<Tile*> floor;
 //! \brief Returns room identity.
 RoomType getType()const{return type;}
 //! \brief Returns room ownership.
 Seat* getSeat()const{return seat;}
 //! \brief Returns its stable name.
 const std::string& getName()const{return name;}
 //! \brief Returns its covered tiles.
 const std::vector<Tile*>& getCoveredTiles()const{return floor;}
};
//! \brief Supplies polymorphic target facts without implementing hunt decisions.
struct GameEntity{GameEntityType type=GameEntityType::other;Seat* seat=nullptr;std::string name;Tile* tile=nullptr;bool deleted=false;
 //! \brief Allows safe fixture destruction through target storage.
 virtual ~GameEntity(){}
 //! \brief Returns the concrete target type.
 GameEntityType getObjectType()const{return type;}
 //! \brief Returns target ownership.
 Seat* getSeat()const{return seat;}
 //! \brief Returns the target identity.
 const std::string& getName()const{return name;}
 //! \brief Returns target placement.
 Tile* getPositionTile()const{return tile;}
 //! \brief Returns exact world placement.
 Ogre::Vector3 getPosition()const{return Ogre::Vector3(tile?tile->x:0,tile?tile->y:0,0);}
 //! \brief Records removal without invalidating assertions.
 void removeFromGameMap(){deleted=true;}
 //! \brief Records deferred destruction.
 void deleteYourself(){deleted=true;}
};using RenderedMovableEntity=GameEntity;
//! \brief Stores ghost identity and phase for the actual hunter branches.
struct GhostEntity:GameEntity{GhostState state=GhostState::floating;std::string assigned,creatureName;unsigned int level=1;
 //! \brief Initializes its concrete target type.
 GhostEntity(){type=GameEntityType::ghostEntity;}
 //! \brief Returns the actual capture phase.
 GhostState getState()const{return state;}
 //! \brief Receives actual capture transitions.
 void setState(GhostState value){state=value;}
 //! \brief Returns assignment ownership.
 const std::string& getAssignedHunter()const{return assigned;}
 //! \brief Receives assignment ownership.
 void setAssignedHunter(const std::string& value){assigned=value;}
 //! \brief Returns the corpse name used by revival.
 const std::string& getCreatureName()const{return creatureName;}
 //! \brief Returns the level contribution to ectoplasm.
 unsigned int getLevel()const{return level;}
};
//! \brief Stores closed-box contents independently of hunter capacity checks.
struct GhostBoxEntity:GameEntity{std::string assigned;std::vector<std::string> contents;static int dropped;static Ogre::Vector3 droppedPosition;
 //! \brief Initializes an independent closed box.
 GhostBoxEntity(){type=GameEntityType::ghostBoxEntity;}
 //! \brief Initializes a box actually dropped by interruption.
 GhostBoxEntity(GameMap*,const std::vector<std::string>& names):contents(names){type=GameEntityType::ghostBoxEntity;}
 //! \brief Returns box assignment ownership.
 const std::string& getAssignedHunter()const{return assigned;}
 //! \brief Receives assignment ownership.
 void setAssignedHunter(const std::string& value){assigned=value;}
 //! \brief Transfers every captured identity without clipping capacity.
 std::vector<std::string> takeGhostNames(){std::vector<std::string> result;result.swap(contents);return result;}
 //! \brief Receives owner initialization for a dropped box.
 void setSeat(Seat* value){seat=value;}
 //! \brief Receives interruption's exact last position.
 void setPosition(const Ogre::Vector3& value){droppedPosition=value;}
 //! \brief Records normal world registration.
 void addToGameMap(){++dropped;}
 //! \brief Leaves rendering outside this rule probe.
 void createMesh(){}
};
int GhostBoxEntity::dropped=0;Ogre::Vector3 GhostBoxEntity::droppedPosition;
//! \brief Supplies independent navigation and typed world lookups.
struct GameMap{std::map<std::pair<int,int>,Tile> tiles;std::vector<Room*> rooms;std::vector<Creature*> creatures;std::vector<GameEntity*> entities;int turn=0;
 //! \brief Returns exact fixture geometry.
 Tile* getTile(int x,int y){std::map<std::pair<int,int>,Tile>::iterator it=tiles.find({x,y});return it==tiles.end()?nullptr:&it->second;}
 //! \brief Returns current world turn.
 int getTurnNumber()const{return turn;}
 //! \brief Returns map width for reveal candidates.
 int getMapSizeX()const{return 8;}
 //! \brief Returns map height for reveal candidates.
 int getMapSizeY()const{return 8;}
 //! \brief Filters rooms by actual type and owner.
 std::vector<Room*> getRoomsByTypeAndSeat(RoomType type,const Seat* owner){std::vector<Room*> result;for(Room* room:rooms)if(room->type==type&&room->seat==owner)result.push_back(room);return result;}
 //! \brief Filters rooms by actual type.
 std::vector<Room*> getRoomsByType(RoomType type){std::vector<Room*> result;for(Room* room:rooms)if(room->type==type)result.push_back(room);return result;}
 //! \brief Returns exact rendered targets.
 const std::vector<GameEntity*>& getRenderedMovableEntities()const{return entities;}
 //! \brief Resolves both type and identity.
 GameEntity* getEntityFromTypeAndName(GameEntityType type,const std::string& name){for(GameEntity* entity:entities)if(entity->type==type&&entity->name==name)return entity;return nullptr;}
 //! \brief Resolves a corpse identity.
 Creature* getCreature(const std::string& name);
 //! \brief Returns eligible owner population without supplying eligibility logic.
 std::vector<Creature*> getCreaturesBySeat(Seat* owner);
 //! \brief Supplies independent path reachability and exact distance for ordering tests.
 std::list<Tile*> path(Tile* from,Tile* to,Creature*,Seat*){std::list<Tile*> result;if(from==nullptr||to==nullptr||!to->reachable)return result;int length=std::max(std::abs(from->x-to->x),std::abs(from->y-to->y))+1;while(length-->0)result.push_back(to);return result;}
 //! \brief Supplies an ordinary creature route.
 std::list<Tile*> path(Creature*,Tile* to){return to==nullptr?std::list<Tile*>():std::list<Tile*>{to};}
};
//! \brief Observes creature actions, experience and poses used by actual hunt branches.
struct Creature:GameEntity{GameMap* map=nullptr;CreatureDefinition definition;bool alive=true,ko=false,onMap=true,moving=false;Seat* prison=nullptr;std::set<CreatureActionType> actions;double xp=0;int clears=0,pops=0,assigned=0,revivals=0;std::string animation;
 //! \brief Initializes concrete creature identity.
 Creature(){type=GameEntityType::creature;}
 //! \brief Returns its world.
 GameMap* getGameMap()const{return map;}
 //! \brief Returns its definition.
 CreatureDefinition* getDefinition(){return &definition;}
 //! \brief Returns its definition for const consumers.
 const CreatureDefinition* getDefinition()const{return &definition;}
 //! \brief Reports health.
 bool isAlive()const{return alive;}
 //! \brief Reports knockout.
 bool isKo()const{return ko;}
 //! \brief Reports hand placement.
 bool getIsOnMap()const{return onMap;}
 //! \brief Reports server authority.
 bool getIsOnServerMap()const{return true;}
 //! \brief Reports imprisonment.
 Seat* getSeatPrison()const{return prison;}
 //! \brief Reports current action flags.
 bool isActionInList(CreatureActionType type)const{return actions.count(type)!=0;}
 //! \brief Records removal of the prior job.
 void clearActionQueue(){++clears;actions.clear();}
 //! \brief Observes the new hunt action.
 template<class T> void pushAction(std::unique_ptr<T>){++assigned;actions.insert(CreatureActionType::huntGhost);}
 //! \brief Observes normal action completion.
 void popAction(){++pops;}
 //! \brief Observes normal movement/pose setup.
 void clearDestinations(const std::string& value,bool,bool){moving=false;animation=value;}
 //! \brief Reports movement state.
 bool isMoving()const{return moving;}
 //! \brief Observes production pose changes.
 void setAnimationState(const std::string& value,bool,const Ogre::Vector3&,bool){animation=value;}
 //! \brief Returns current animation identity.
 const std::string& getAnimationStateName()const{return animation;}
 //! \brief Observes visual refresh.
 void refreshGhostHuntVisuals(){}
 //! \brief Retains exact training-derived experience.
 void receiveExp(double value){xp+=value;}
 //! \brief Supplies the existing revival service; corpse-rule probe checks its full actual body.
 bool reviveFromCorpse(double share){check(share==.35,"revival exact HP share");alive=true;++revivals;return true;}
};
//! \brief Resolves exact corpse identities.
Creature* GameMap::getCreature(const std::string& name){for(Creature* creature:creatures)if(creature->name==name)return creature;return nullptr;}
//! \brief Filters population ownership for actual assignment.
std::vector<Creature*> GameMap::getCreaturesBySeat(Seat* owner){std::vector<Creature*> result;for(Creature* creature:creatures)if(creature->seat==owner)result.push_back(creature);return result;}
//! \brief Supplies delivered-body membership to hunt decisions.
struct RoomCrypt:Room{std::set<Creature*> delivered;
 //! \brief Returns an actual recorded delivered corpse, with decay intentionally unrestricted.
 Tile* getCorpseSpot(Creature& corpse){return delivered.count(&corpse)?corpse.tile:nullptr;}
};
//! \brief Supplies the central item factory contract; the crystal probe checks its actual codec and identity.
struct ItemInstance{
 //! \brief Creates one crystal factory result.
 static std::unique_ptr<ItemInstance> createSoulCrystal(){return std::unique_ptr<ItemInstance>(new ItemInstance);}
};
//! \brief Counts real product calls without duplicating their conditions.
struct ItemBagEntity{static int crystals;
 //! \brief Observes central crystal factory delivery.
 ItemBagEntity(GameMap*,std::unique_ptr<ItemInstance>){++crystals;}
 //! \brief Receives keeper ownership.
 void setSeat(Seat*){}
 //! \brief Receives the original bowl tile placement.
 void setPosition(const Ogre::Vector3&){}
 //! \brief Receives normal map registration.
 void addToGameMap(){}
 //! \brief Receives normal mesh creation.
 void createMesh(){}
};int ItemBagEntity::crystals=0;
//! \brief Records free reveal candidates and exact unresearched duration.
struct SpellEyeEvil{static std::vector<Tile*> reveals;
 //! \brief Observes free reveals chosen by the original product body.
 static void spawnFree(GameMap*,Seat*,Tile* tile,int turns){check(turns==10,"base free reveal duration");reveals.push_back(tile);}
};std::vector<Tile*> SpellEyeEvil::reveals;
//! \brief Observes ectoplasm feedback calls.
struct Spell{
 //! \brief Requires the proper independent effect namespace.
 static void fireSpellEffect(Tile&,const std::string& event,const std::string& family){check(event=="EctoplasmBurst"&&family.empty(),"ectoplasm event");}
};
//! \brief Counts per-product AI decisions without choosing human switches.
struct KeeperAI{static int updates;
 //! \brief Observes one policy call for every produced ectoplasm.
 static void updateGhostRoomSettings(Seat&){++updates;}
};int KeeperAI::updates=0;
//! \brief Supplies existing unique ownership construction for actual assignment code.
namespace Utils{
 //! \brief Allocates the requested owned action with explicit types.
 template<class T,class... A>std::unique_ptr<T> make_unique(A&&... args){return std::unique_ptr<T>(new T(std::forward<A>(args)...));}}
//! \brief Observes actual social catch posts.
namespace social{enum class PostCategory{GhostHunted};
//! \brief Counts actual caught-ghost posts.
struct PostLog{int posts=0;
 //! \brief Returns the controlled post service.
 static PostLog& getSingleton(){static PostLog value;return value;}
 //! \brief Records the original catch post call.
 void addPost(int,const std::string&,const std::string&,bool,PostCategory,int){++posts;}
};}
//! \brief Supplies floor, hook and cauldron services while retaining actual product logic.
struct RoomGhostRoom:Room{GameMap* map=nullptr;Tile* mBowl=nullptr;int backpacks=3,bells=0,emptied=0;std::vector<GhostEntity*> emptiedGhosts;
 //! \brief Stores actual emptying reservation identity.
 struct Cauldron{Tile* anchor;Creature* hunter;};std::vector<Cauldron> mCauldrons;
 //! \brief Returns controlled world.
 GameMap* getGameMap(){return map;}
 //! \brief Returns independent supply for assignment-limit tests.
 uint32_t getBackpackCount()const{return backpacks;}
 //! \brief Records bell routing.
 void ringBell(){++bells;}
 //! \brief Returns a real controlled hook tile.
 Tile* reserveHook(Creature&){return floor.empty()?nullptr:floor.front();}
 //! \brief Returns stable hook identity.
 size_t getHunterHookSlot(const Creature&)const{return 2;}
 //! \brief Records equipment return.
 void releaseHunter(Creature&){}
 //! \brief Returns the configured standing place.
 Tile* reserveCauldron(Creature&){return floor.empty()?nullptr:floor.front();}
 //! \brief Returns the actual reserved cauldron anchor.
 Tile* getHunterCauldron(const Creature&)const{return floor.empty()?nullptr:floor.back();}
 //! \brief Records release after emptying.
 void releaseCauldron(Creature&){}
 //! \brief Records normal layout refresh.
 void updateActiveSpots(){}
 //! \brief Runs the actual research threshold consumer.
 static double getLevelsPerEctoplasm(const Seat&);
 //! \brief Runs the full actual reveal/bar/product body.
 void emptyGhost(Creature&,GhostEntity&);
};
//! \brief Stores the exact timed hunt continuation used by real branches.
struct CreatureActionHuntGhost{Creature& mCreature;std::string mTarget,mBeamTarget,mReviveTarget,mEmptyRoom,mHookRoom;std::vector<std::string> mGhosts,mReviveGhosts;uint32_t mState=2;double mTurns=0,mRepathTurns=0;int mLastTimedTurn=-1,mHookX=0,mHookY=0;size_t mHookSlot=0;bool mInterrupted=false,mRegistered=true,mEquipped=true,next=false;Ogre::Vector3 mLastPosition;Tile* mDestination=nullptr;Tile* mEmptyAnchor=nullptr;RoomGhostRoom* equipment=nullptr;
 //! \brief Initializes an independent actual assignment continuation.
 CreatureActionHuntGhost(Creature& creature,const std::string& target=""):mCreature(creature),mTarget(target){}
 //! \brief Returns the selected equipment room.
 RoomGhostRoom* hookRoom()const{return equipment;}
 //! \brief Runs the original research lookup.
 double researched(const std::string&,const std::string&)const;
 //! \brief Observes target release without implementing hunt transitions.
 void releaseTarget();
 //! \brief Supplies the controlled result of finding another target.
 bool nextTarget(){return next;}
 //! \brief Supplies controlled navigation success and placement.
 bool moveTo(Tile* tile){mDestination=tile;return tile!=nullptr&&tile->reachable;}
 //! \brief Observes interruption.
 void interrupt();
 //! \brief Captures original sound requests.
 static void playSound(GameMap&,Tile&,const std::string&){}
 //! \brief Runs the original assignment algorithm.
 static void assignHunters(GameMap&,Seat&);
 //! \brief Runs the original XP and interruption upkeep.
 void upkeep();
 //! \brief Runs the original revival selection.
 bool selectRevival();
 //! \brief Runs complete original timed capture, capacity, revival and empty branches.
 bool step();
};
'''
    action = read('source/creatureaction/CreatureActionHuntGhost.cpp')
    room = read('source/rooms/RoomGhostRoom.cpp')
    code += ''.join(function(action,sig) for sig in ['GhostEntity* ghostNamed(', 'RoomGhostRoom* roomNamed(', 'bool eligible(',
        'size_t pathLength(', 'Tile* targetEndpoint(', 'double CreatureActionHuntGhost::researched(',
        'void CreatureActionHuntGhost::releaseTarget(', 'void CreatureActionHuntGhost::interrupt(',
        'void CreatureActionHuntGhost::assignHunters(', 'void CreatureActionHuntGhost::upkeep(', 'bool CreatureActionHuntGhost::selectRevival('])
    code += function(room,'double RoomGhostRoom::getLevelsPerEctoplasm(')+function(room,'void RoomGhostRoom::emptyGhost(')
    branches = ''.join(function(action, sig) for sig in ['    if(mState==2 || mState==3)', '    if(mState==4)',
        '    if(mState==5)', '    if(mState==6)'])
    code += '\nbool CreatureActionHuntGhost::step(){GameMap& map=*mCreature.getGameMap();ConfigManager& config=ConfigManager::getSingleton();'+branches+'return false;}\n'
    return base+code

# Exercise assignment limits, real endpoint routing, fractional timing, revival recheck and product/reveal loops.
def hunt_checks():
    code = hunt_fixture()+r'''
//! \brief Runs original hunt decisions with independent expected timing and economy results.
int main(){
 GameMap map;Seat seat,enemy;enemy.id=2;for(int y=0;y<8;++y)for(int x=0;x<8;++x){Tile& tile=map.tiles[{x,y}];tile.x=x;tile.y=y;tile.owner=&seat;}
 RoomGhostRoom room;room.map=&map;room.type=RoomType::ghostRoom;room.seat=&seat;room.name="press";room.floor={map.getTile(1,1),map.getTile(2,2)};room.mBowl=map.getTile(1,2);map.rooms.push_back(&room);
 Creature hunter;hunter.name="hunter";hunter.map=&map;hunter.seat=&seat;hunter.tile=map.getTile(2,2);map.creatures.push_back(&hunter);
 GhostEntity ghost;ghost.name="target";ghost.seat=&enemy;ghost.tile=map.getTile(3,2);map.entities.push_back(&ghost);
 check(eligible(ghost,seat),"own-territory ghost eligible");ghost.tile->owner=&enemy;check(!eligible(ghost,seat),"foreign territory not hunted");ghost.tile->owner=&seat;ghost.state=GhostState::rising;check(!eligible(ghost,seat),"rising ghost not assigned");ghost.state=GhostState::floating;ghost.assigned="other";check(!eligible(ghost,seat),"assigned ghost not stolen");ghost.assigned.clear();
 ghost.tile->reachable=false;check(targetEndpoint(map,hunter,hunter.tile,ghost)!=nullptr,"hunter reaches adjacent endpoint when ghost tile inaccessible");
 for(int tier=1;tier<=3;++tier){seat.tier=tier;for(double efficiency:{3.0,1.5,.5}){hunter.definition.jobs.front().efficiency=efficiency;ghost.state=GhostState::floating;ghost.assigned.clear();CreatureActionHuntGhost action(hunter,"target");action.equipment=&room;action.mState=2;const double factors[]={1,.8,.667};const double beam=5.5*factors[tier-1]/efficiency;const int ticks=int(std::ceil(beam+.7));for(int turn=0;turn<ticks;++turn){map.turn=turn;action.step();double before=action.mTurns;action.step();near(action.mTurns,before,"one timed tick per world turn");}check(ghost.state==GhostState::boxed&&action.mGhosts.size()==1,"beam and throw complete");near(action.mTurns,ticks-beam-.7,"beam and throw keep fractional remainder");}
  hunter.definition.jobs.front().efficiency=1.5;CreatureActionHuntGhost action(hunter);action.equipment=&room;double before=hunter.xp;action.upkeep();near(hunter.xp-before,(tier==1?5:tier==2?6:7)/5.5,"XP follows actual training research without cap");
  action.mState=4;action.next=true;action.mGhosts.assign(tier-1,"held");check(action.step()&&action.mState==1,"research capacity permits next catch");action.mState=4;action.mGhosts.assign(tier,"held");action.step();check(action.mState==5,"research capacity stops additional catch");
 }

 // Actual emptying consumes fractional per-ghost durations and refuses remote work.
 hunter.definition.jobs.front().efficiency=3;seat.tier=1;seat.product=GhostProduct::research;seat.bar=0;
 GhostEntity extra1,extra2;extra1.name="extra1";extra2.name="extra2";extra1.seat=extra2.seat=&seat;extra1.tile=extra2.tile=ghost.tile;map.entities.push_back(&extra1);map.entities.push_back(&extra2);
 CreatureActionHuntGhost empty(hunter);empty.mState=6;empty.mDestination=hunter.tile;empty.mEmptyRoom="press";empty.mGhosts={"target","extra1","extra2"};room.mCauldrons={{room.floor.back(),&hunter}};
 for(int tick=0;tick<6;++tick){map.turn=100+tick;empty.step();double before=empty.mTurns;empty.step();near(empty.mTurns,before,"empty clock increments once per world turn");}
 check(empty.mGhosts.empty()&&empty.mState==7,"three ghosts emptied at efficiency three");near(empty.mTurns,.5,"emptying keeps fractional remainder");
 empty.mState=6;empty.mDestination=map.getTile(0,0);empty.mGhosts={"extra1"};double bar=seat.bar;empty.step();near(seat.bar,bar,"saved hunter cannot empty remotely");check(empty.mDestination==nullptr,"remote standing destination re-reserved");
 map.entities.resize(1);
 seat.tier=1;hunter.definition.jobs.front().efficiency=3;hunter.actions.clear();ghost.state=GhostState::floating;ghost.assigned.clear();room.backpacks=0;CreatureActionHuntGhost::assignHunters(map,seat);check(hunter.assigned==0,"zero backpacks prevents assignment");room.backpacks=1;CreatureActionHuntGhost::assignHunters(map,seat);check(hunter.assigned==1&&ghost.assigned==hunter.name,"one backpack assigns one nearest hunter");int bells=room.bells;CreatureActionHuntGhost::assignHunters(map,seat);check(room.bells==bells,"target bell fires once");
 // Each separate eligibility failure must prevent a new assignment.
 for(int failure=0;failure<7;++failure){hunter.actions.clear();hunter.alive=true;hunter.ko=false;hunter.onMap=true;hunter.prison=nullptr;hunter.definition.worker=false;hunter.definition.jobs={{3}};ghost.assigned.clear();if(failure==0)hunter.alive=false;if(failure==1)hunter.ko=true;if(failure==2)hunter.onMap=false;if(failure==3)hunter.prison=&enemy;if(failure==4)hunter.definition.worker=true;if(failure==5)hunter.actions.insert(CreatureActionType::fight);if(failure==6)hunter.actions.insert(CreatureActionType::flee);int assigned=hunter.assigned;CreatureActionHuntGhost::assignHunters(map,seat);check(hunter.assigned==assigned,"ineligible hunter remains at ordinary job");}
 hunter.actions.clear();hunter.alive=true;hunter.ko=false;hunter.onMap=true;hunter.prison=nullptr;hunter.definition.worker=false;hunter.definition.jobs={{3}};
 RoomCrypt crypt;crypt.type=RoomType::crypt;crypt.seat=&seat;Tile* grave=map.getTile(4,4);grave->room=&crypt;Creature corpse;corpse.name="body";corpse.map=&map;corpse.seat=&seat;corpse.tile=grave;corpse.alive=false;map.creatures.push_back(&corpse);crypt.delivered.insert(&corpse);ghost.seat=&seat;ghost.creatureName="body";ghost.state=GhostState::boxed;
 for(int tier=1;tier<=3;++tier){seat.tier=tier;CreatureActionHuntGhost action(hunter);action.mReviveGhosts={"target"};seat.mana=14000-2000*(tier-1);check(action.selectRevival(),"exact researched revival price is sufficient");seat.mana-=.125;action.mReviveTarget.clear();check(!action.selectRevival(),"fraction below revival price rejected");}
 seat.tier=1;seat.mana=14000;CreatureActionHuntGhost trip(hunter);trip.mState=5;trip.mReviveGhosts={"target"};trip.mGhosts={"target"};hunter.tile=grave;trip.step();check(corpse.revivals==1&&seat.mana==0&&ghost.deleted,"arrival revival pays exact price and removes ghost");corpse.alive=false;ghost.deleted=false;seat.mana=14000;trip.mReviveTarget="target";trip.mReviveGhosts={"target"};seat.mana=13999.875;trip.step();check(corpse.revivals==1&&!ghost.deleted,"arrival rechecks changed mana");
 hunter.tile=room.floor.front();room.mCauldrons={{room.floor.back(),&hunter}};ghost.seat=&enemy;ghost.deleted=false;ghost.level=1;ghost.tile=map.getTile(3,2);for(std::pair<const std::pair<int,int>,Tile>& entry:map.tiles)entry.second.owner=&seat;Tile* seen=map.getTile(6,6);Tile* unseen=map.getTile(7,7);seen->owner=unseen->owner=&enemy;seat.seen.insert(seen);
 for(int tier=1;tier<=3;++tier){seat.tier=tier;const double threshold=tier==1?10:tier==2?8:6;for(GhostProduct product:{GhostProduct::mana,GhostProduct::research,GhostProduct::crystal}){seat.product=product;seat.bar=threshold*2-.625;seat.mana=1000;seat.points=0;int crystals=ItemBagEntity::crystals;int policies=KeeperAI::updates;room.emptyGhost(hunter,ghost);near(seat.bar,.375,"product loop retains fractional bar");if(product==GhostProduct::mana)near(seat.mana,21000,"two products give exact mana");if(product==GhostProduct::research)near(seat.points,4000,"two products give exact research");if(product==GhostProduct::crystal)check(ItemBagEntity::crystals==crystals+2,"one factory crystal per ectoplasm");check(KeeperAI::updates==policies+2,"AI evaluated before each product");check(SpellEyeEvil::reveals.back()==unseen,"enemy reveal chooses unseen territory first");}}
 seat.tier=1;seat.product=GhostProduct::crystal;seat.bar=9.375;room.mBowl=nullptr;int crystals=ItemBagEntity::crystals;room.emptyGhost(hunter,ghost);near(seat.bar,10.375,"known no-bowl gap retains pending bar without consuming it");check(ItemBagEntity::crystals==crystals,"no invented crystal bowl");
 seat.seen.insert(unseen);room.mBowl=map.getTile(1,2);seat.product=GhostProduct::research;seat.bar=0;room.emptyGhost(hunter,ghost);check(SpellEyeEvil::reveals.back()==seen||SpellEyeEvil::reveals.back()==unseen,"seen territory fallback");size_t reveals=SpellEyeEvil::reveals.size();ghost.seat=&seat;room.emptyGhost(hunter,ghost);check(SpellEyeEvil::reveals.size()==reveals,"own ghost never reveals");
 CreatureActionHuntGhost interrupted(hunter,"target");interrupted.equipment=&room;interrupted.mGhosts={"extra1","extra2"};interrupted.mLastPosition=Ogre::Vector3(2.125f,3.875f,.5f);hunter.onMap=false;ghost.state=GhostState::beamed;ghost.assigned=hunter.name;int drops=GhostBoxEntity::dropped,pops=hunter.pops;interrupted.interrupt();interrupted.interrupt();check(GhostBoxEntity::dropped==drops+1&&interrupted.mGhosts.empty()&&!interrupted.mEquipped,"interruption drops full box exactly once");near(GhostBoxEntity::droppedPosition.x,2.125,"hand interruption uses saved last world X");near(GhostBoxEntity::droppedPosition.y,3.875,"hand interruption uses saved last world Y");check(hunter.pops==pops&&ghost.state==GhostState::floating&&ghost.assigned.empty(),"interruption releases target without queue reentrancy");
 CreatureActionHuntGhost incomplete(hunter);incomplete.mRegistered=false;incomplete.mGhosts={"extra1"};incomplete.interrupt();check(GhostBoxEntity::dropped==drops+1,"incomplete imported action cannot manufacture a dropped box");
 std::cout<<"hunt timing, assignment, revival, products and reveal: ok\n";
}
'''
    run_probe('ghost-hunts',code)

if __name__ == '__main__':
    main()
    hunt_checks()
