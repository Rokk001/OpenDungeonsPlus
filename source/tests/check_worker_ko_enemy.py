"""Check that workers claim, dig and carry in both free-worker modes while a knocked-out enemy lies near the heart.

Owner decision 791 (build 45, map [Test] Ghosts): 15 free workers did nothing for about 95 s, the Workers window showed
'Claim ground: Working 14'. The cause was not the ghost room code: GameMap::updateSeatHeartDefense counted an enemy that
was knocked out to death (it stays alive with mKoTurnCounter < 0 until it dies) within the heart defence range as a live
threat, so the heart defence stayed on, every worker (a heart defence runner) dropped its job for goDefendHeart, and
WorkerAllocation::countedWorkers left all of them out of the job allocation. The same stall is in the log of a build
before 44, so it is older than the build-45 ghost commits.

The static part (always run, also with --static-only during the plan) pins this chain in the source. Without
--static-only a probe compiles the production updateSeatHeartDefense and the real WorkerAllocation.h and runs a seat of
15 workers with a knocked-out enemy six tiles from the heart in mode Automatic and in mode Priority list: the defence
stays off, the workers are counted, and dig, claim ground and carry each get workers and are chosen by idle workers.
Both parts fail on base 89fbc6bd7 (the defence ignores the knock-out)."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]


# Read a tracked source file.
def read(path):
    return (root / path).read_text(encoding='utf-8')


# Return the complete brace-delimited body that starts at the signature.
def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


game_map = read('source/gamemap/GameMap.cpp')
defence = function(game_map, 'void GameMap::updateSeatHeartDefense(')
constants = function(game_map, 'int heartDefenceRangeSquared(')
allocation = read('source/game/WorkerAllocation.cpp')
creature = read('source/entities/Creature.cpp')

# 1. The heart defence skips an enemy that is knocked out to death or imprisoned before it can become the nearest enemy.
loop = defence[defence.index('for (Creature* creature : getCreatures())'):defence.index('if (nearestEnemyTile == nullptr)')]
skip = loop.index('if (creature->isKoDeath() || creature->isInContainment())\n            continue;')
assert skip < loop.index('squaredDistanceTile(*heartTile, *creatureTile)'), 'the knock-out is checked before the distance'
assert 'if (nearestEnemyTile == nullptr)' in defence and 'seat->mHeartDefenceActive = false;' in defence, \
    'without a threatening enemy in range the defence ends'
assert 'isKoDeath() const;' in read('source/entities/Creature.h'), 'the server knock-out test exists'
assert re.search(r'bool Creature::isKoDeath\(\) const\s*\{\s*if\(getIsOnServerMap\(\)\)\s*return mKoTurnCounter < 0;', creature), \
    'on the server a creature knocked out to death has a negative knock-out counter'

# 2. Why it stopped all work: the defence takes every worker off its job and out of the allocation.
heart = function(creature, 'void Creature::handleHeartDefence()')
assert 'getHeartDefenceActive()' in heart and 'clearActionQueue();' in heart and 'CreatureActionGoDefendHeart' in heart
counted = function(allocation, 'std::vector<Creature*> countedWorkers(Seat& seat)')
assert 'creature->isActionInList(CreatureActionType::goDefendHeart)' in counted, 'defending workers are not allocated'

# 3. Both modes reach the same job pushes: the mode only switches freeTargets between even spread and priority list.
choose = function(allocation, 'WorkerJob chooseForIdle(Seat& seat, Creature& creature, const std::array<bool, 6>& available)')
assert 'settings.freeMode == static_cast<uint32_t>(WorkerFreeMode::priority)' in choose
assert 'enum class WorkerFreeMode : uint32_t { automatic, priority };' in read('source/game/WorkerJobs.h')
idle = function(creature, 'bool Creature::handleIdleAction()')
for job, action in (('dig', 'CreatureActionSearchTileToDig'), ('claimGround', 'CreatureActionSearchGroundTileToClaim'),
                    ('carry', 'CreatureActionSearchEntityToCarry')):
    case = idle[idle.index('case WorkerJob::' + job + ':'):]
    assert case.index('pushAction(Utils::make_unique<' + action + '>') < case.index('return true;'), (job, action)
print('worker heart defence wiring: ok')

if '--static-only' in sys.argv:
    sys.exit(0)

probe = r'''
#include "game/WorkerAllocation.h"
#include <iostream>
#include <string>
#include <vector>
enum class RoomType {dungeonTemple, other};
struct Tile {int x=0,y=0;Tile(int xi,int yi):x(xi),y(yi){} int getX()const{return x;} int getY()const{return y;}};
namespace Pathfinding { template <typename T> int squaredDistanceTile(const T& a,const T& b)
 {int dx=a.getX()-b.getX(),dy=a.getY()-b.getY();return dx*dx+dy*dy;} }
namespace SoundRelativeKeeperStatements { const std::string WeAreUnderAttack = "Keeper/WeAreUnderAttack"; }
struct ConfigManager { static ConfigManager& getSingleton(){static ConfigManager m;return m;}
 double getRoomConfigDouble(const std::string&)const{return 7.0;} };
struct Player { bool getIsHuman()const{return true;} bool getHasLost()const{return false;} };
struct Seat { int team;Player* player=nullptr;bool mHeartDefenceActive=false;bool mHeartDefenceHeartDamaged=false;
 Seat(int t):team(t){} Player* getPlayer()const{return player;}
 bool isAlliedSeat(const Seat* o)const{return o!=nullptr&&(o==this||o->team==team);} };
struct Creature { Seat* seat;Tile* tile;bool alive=true;int koCounter=0;bool defending=false;
 Creature(Seat* s,Tile* t):seat(s),tile(t){} Seat* getSeat()const{return seat;} bool isAlive()const{return alive;}
 bool getIsOnMap()const{return true;} Tile* getPositionTile()const{return tile;}
 bool isKoDeath()const{return koCounter<0;} bool isInContainment()const{return false;} };
struct Room { Seat* seat;Room(Seat* s):seat(s){} virtual ~Room()=default; Seat* getSeat()const{return seat;}
 virtual RoomType getType()const{return RoomType::other;} virtual double getHP(Tile*)const{return 1.0;} };
struct RoomDungeonTemple:Room { Tile* heart;RoomDungeonTemple(Seat* s,Tile* h):Room(s),heart(h){}
 RoomType getType()const override{return RoomType::dungeonTemple;} double getHP(Tile*)const override{return 10000.0;}
 Tile* getHeartTile()const{return heart;} double getHeartMaxHP()const{return 10000.0;} };
struct GameMap { std::vector<Room*> mRooms;std::vector<Creature*> mCreatures;
 std::vector<Room*>& getRooms(){return mRooms;} std::vector<Creature*>& getCreatures(){return mCreatures;}
 void fireRelativeSound(const std::vector<Seat*>&,const std::string&){}
 void updateSeatHeartDefense(Seat* seat); };
CONSTANTS
DEFENCE
int failures=0;
void check(bool ok,const char* what){if(!ok){++failures;std::cout<<"FAIL "<<what<<"\n";}}
int main(){
 using A=WorkerAllocation::Counts;
 GameMap map;Player human;Seat owner(1),enemySeat(2);owner.player=&human;
 Tile heartTile(0,0),near(6,0),home(3,3);
 RoomDungeonTemple temple(&owner,&heartTile);map.mRooms.push_back(&temple);
 Creature enemy(&enemySeat,&near);enemy.koCounter=-30;map.mCreatures.push_back(&enemy);
 std::vector<Creature> workers(15,Creature(&owner,&home));
 for(Creature& worker : workers) map.mCreatures.push_back(&worker);
 // Open work on the map: 40 tiles to dig, 60 to claim, 12 objects to carry, nothing else.
 const A caps{{40,60,0,12,0,0}},order{{0,1,2,3,4,5}},parts{{6,5,4,3,2,1}};
 for(int mode=0;mode<2;++mode){
  map.updateSeatHeartDefense(&owner);
  check(!owner.mHeartDefenceActive,"the knocked-out enemy six tiles from the heart does not start the defence");
  // Creature::handleHeartDefence: a worker drops its job for goDefendHeart only while the defence is on;
  // WorkerAllocation::countedWorkers leaves defending workers out.
  uint32_t counted=0;
  for(Creature& worker : workers){worker.defending=owner.mHeartDefenceActive;if(!worker.defending) ++counted;}
  check(counted==15,"all 15 workers take part in the job allocation");
  const A targets=WorkerAllocation::freeTargets(counted,caps,mode==1,order,parts);
  check(targets[0]>0&&targets[1]>0&&targets[3]>0,"dig, claim ground and carry all get workers");
  check(targets[0]+targets[1]+targets[3]==15,"every worker has work");
  const std::array<bool,6> available{{true,true,true,true,true,true}};
  A counts{{0,0,0,0,0,0}};
  for(uint32_t i=0;i<counted;++i){
   const uint32_t job=WorkerAllocation::chooseFreeJob(6,counts,targets,available);
   check(job<6,"an idle worker gets a job");
   if(job<6) ++counts[job];
  }
  check(counts[0]>0&&counts[1]>0&&counts[3]>0,"idle workers start digging, claiming and carrying");
 }
 // A standing enemy in range still calls the workers to the heart.
 enemy.koCounter=0;map.updateSeatHeartDefense(&owner);
 check(owner.mHeartDefenceActive,"a standing enemy in range starts the defence");
 enemy.koCounter=-30;map.updateSeatHeartDefense(&owner);
 check(!owner.mHeartDefenceActive,"the defence ends once that enemy is knocked out to death");
 std::cout<<"FAILURES="<<failures<<"\n";return failures?1:0;
}
'''
probe = probe.replace('CONSTANTS', 'namespace {\n' + constants + '\n}').replace('DEFENCE', defence)
with tempfile.TemporaryDirectory(prefix='odp-worker-ko-') as directory:
    work = Path(directory)
    (work / 'probe.cpp').write_text(probe, encoding='utf-8')
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++17', '/I' + str(root / 'source'), 'probe.cpp', '/Fe:probe.exe'],
                   cwd=work, check=True)
    subprocess.run([str(work / 'probe.exe')], cwd=work, check=True)
print('workers claim, dig and carry in both modes with a knocked-out enemy near the heart: ok')
