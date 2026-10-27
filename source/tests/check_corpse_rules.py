"""Compile the real death-phase branch and FIFO crypt/revival production bodies."""
from check_ghost_rules import PRELUDE, GHOST_WORLD, function, read, run_probe

# Extend controlled services with corpse observations; no phase or FIFO algorithms live in mocks.
def corpse_fixture():
    additions = r'''
 unsigned int mDeathCounter=0;double hp=100,mCorpseTurns=0,mDecayTurns=-1,mMaxHP=100,mHunger=0,mWakefulness=0,mThirst=0,mSpecialMood=0;bool mIsCarried=false,mNeedFireRefresh=false,mGhostRevived=false,server=true;std::string mCorpseCarrierName,animation;int drops=0,dirtyCalls=0,queueClears=0,koResets=0;
 //! \brief Reports corpse authority.
 bool getIsOnServerMap()const{return server;}
 //! \brief Returns the controlled world.
 GameMap* getGameMap()const{return map;}
 //! \brief Returns the actual carry marker.
 bool isCorpseCarried()const{return mIsCarried;}
 //! \brief Restores tile registration before life is restored.
 void addEntityToPositionTile(){check(!alive,"crypt release precedes revival");onMap=true;}
 //! \brief Observes the unchanged equipment drop.
 void dropCarriedEquipment(){++drops;}
 //! \brief Observes ordinary corpse dirt without fabricating terminal dirt.
 void dirtyTileByCorpse(){++dirtyCalls;}
 //! \brief Returns the original death placement.
 Ogre::Vector3 getPosition()const{return Ogre::Vector3(tile?tile->x:0,tile?tile->y:0,0);}
 //! \brief Captures decay clip selection.
 void clearDestinations(const std::string& value,bool,bool){animation=value;}
 //! \brief Captures decay or restored idle animation.
 void setAnimationState(const std::string& value,bool,const Ogre::Vector3&,bool){animation=value;}
 //! \brief Destroys the previous action ownership at revival.
 void clearActionQueue(){++queueClears;}
 //! \brief Clears fatal knockout and item-loss state through the required existing API.
 void resetKoTurns(){++koResets;ko=false;}
 //! \brief Restores the requested exact health share.
 void setHP(double value){alive=value>0;hp=value;}
 //! \brief Supplies an independent observable happy mood.
 void removeAnnoyance(){mSpecialMood=37.25;}
 //! \brief Observes ordinary mood recomputation.
 void computeMood(){}
 //! \brief Observes ordinary overlay recomputation.
 void computeCreatureOverlayMoodValue(){}
 //! \brief Returns current health for the real carrying guard.
 double getHP()const{return alive?hp:0;}
 //! \brief Runs the exact worker and dead-body carrying branches.
 EntityCarryType carryDead()const;
 //! \brief Runs only the original death branch.
 void corpseTick();
 //! \brief Runs the original Raise Dead reservation guard.
 bool takeCorpse();
 //! \brief Runs the original revival sequence.
 bool reviveFromCorpse(double hpShare);
'''
    world = GHOST_WORLD
    world = world.replace(' bool getIsOnServerMap()const{return server;}', r'''
 //! \brief Initializes an actual non-worker death ghost and records its creation.
 GhostEntity(GameMap* value,const Creature& corpse):map(value),seat(corpse.seat){mCreatureName=corpse.name;}
 //! \brief Initializes an independent fixture ghost.
 GhostEntity()=default;
 //! \brief Registers a ghost created by the production death branch.
 void addToGameMap(){map->ghosts.push_back(this);}
 //! \brief Receives normal ghost mesh initialization.
 void createMesh(){}
 //! \brief Receives the ghost's original corpse placement.
 void setPosition(const Ogre::Vector3& value){mPosition=value;}
 bool getIsOnServerMap()const{return server;}
''')
    base = PRELUDE.replace(' size_t getMaxCreaturesPerSeatAbsolute()const{return 20;}', r'''
 //! \brief Returns the decided revival tiredness threshold.
 double getTiredWakefulness()const{return 20;}
 size_t getMaxCreaturesPerSeatAbsolute()const{return 20;}
''')
    world = world.replace(' RoomType getType()const{return type;}', r'''
 //! \brief Supplies the unchanged room save prefix.
 void exportToStream(std::ostream&)const{}
 //! \brief Supplies the unchanged room save reader prefix.
 bool importFromStream(std::istream&){return true;}
 RoomType getType()const{return type;}
''')
    world = world.replace(' Creature()=default;', additions+' Creature()=default;')
    declarations = r'''
//! \brief Captures blood creation at first death only.
namespace DirtPileKind{const int blood=0;}
//! \brief Observes the blood side effect.
struct DirtPileEntity{static int count;
 //! \brief Counts actual death blood calls.
 static void createOnTile(GameMap*,Tile*,int,const std::string&){++count;}
};int DirtPileEntity::count=0;
//! \brief Captures worker vanish and revival spell events.
struct Spell{static int vanish,revivals;
 //! \brief Records only the prescribed production event calls.
 static void fireSpellEffect(Tile&,const std::string& event,const std::string& sound){check(sound.empty(),"event sound namespace");if(event=="WorkerVanish")++vanish;if(event=="GhostRevive")++revivals;}
};int Spell::vanish=0;int Spell::revivals=0;
//! \brief Retains production grave occupancy and FIFO storage.
struct RoomCrypt:Room{GameMap* map=nullptr;std::map<Tile*,Creature*> mRottingCreatures;std::vector<unsigned int> mCorpseLevels;std::map<std::pair<int,int>,std::string> mCorpseSpotNames;
 //! \brief Returns the controlled world.
 GameMap* getGameMap(){return map;}
 //! \brief Finds a delivered corpse using the actual production checks.
 Tile* getCorpseSpot(const Creature&)const;
 //! \brief Removes actual crypt reservations before revival.
 void removeCorpse(Creature&);
 //! \brief Runs the actual FIFO spawn algorithm.
 void notifyCorpseDecayed(Creature&);
 //! \brief Runs the actual crypt writer.
 void exportToStream(std::ostream&)const;
 //! \brief Runs the actual optional crypt reader.
 bool importFromStream(std::istream&);
};
'''
    base += '\nenum class EntityCarryType{corpse,notCarryable};\n'
    source = read('source/entities/Creature.cpp')
    death = function(function(source,'void Creature::doUpkeep('),'    if (!isAlive())')
    carry = function(source,'EntityCarryType Creature::getEntityCarryType(')
    carry_body = carry[carry.index('    if(getDefinition()->isWorker())'):carry.index('    // A creature knocked')]
    dead_guard = carry[carry.index('    if(getHP() <= 0.0)'):carry.index('    // A hurt creature')]
    carry_code = '\nEntityCarryType Creature::carryDead()const{'+carry_body+dead_guard+'return EntityCarryType::notCarryable;}\n'
    crypt = read('source/rooms/RoomCrypt.cpp')
    return base+world+declarations+''.join(function(crypt,sig) for sig in
        ['Tile* RoomCrypt::getCorpseSpot(', 'void RoomCrypt::removeCorpse(', 'void RoomCrypt::notifyCorpseDecayed('])+\
        carry_code+'\nvoid Creature::corpseTick(){'+death+'}\n'+function(source,'bool Creature::takeCorpse(')+function(source,'bool Creature::reviveFromCorpse(')

# Exercise exact clock edges, carry pause, death idempotence, FIFO levels, caps and revival.
def main():
    code = corpse_fixture()+r'''
//! \brief Runs original corpse and crypt code against independent expected results.
int main(){
 GameMap map;Seat seat;Tile& tile=map.tiles[{0,0}];tile.x=tile.y=0;
 Creature corpse;corpse.map=&map;corpse.seat=&seat;corpse.tile=&tile;corpse.alive=false;map.creatures.push_back(&corpse);
 corpse.corpseTick();check(map.ghosts.size()==1&&corpse.drops==1&&seat.player.deaths==1&&DirtPileEntity::count==1,"one complete original death event");
 corpse.corpseTick();check(map.ghosts.size()==1&&corpse.drops==1,"death events are not repeated");
 corpse.mCorpseTurns=167;corpse.mIsCarried=true;int dirt=corpse.dirtyCalls;corpse.corpseTick();near(corpse.mCorpseTurns,167,"carried lie time pauses");near(corpse.mDecayTurns,-1,"carried body does not start decay");check(corpse.dirtyCalls==dirt,"carrier tile stays clean");
 corpse.mIsCarried=false;corpse.corpseTick();near(corpse.mCorpseTurns,168,"120 seconds converted to 168 turns");near(corpse.mDecayTurns,1,"threshold tick advances decay once");check(corpse.animation=="Rot","decay animation outside crypt");check(!corpse.takeCorpse(),"Raise Dead refuses decaying corpse");check(corpse.carryDead()==EntityCarryType::notCarryable,"decaying body cannot be carried");
 corpse.mDecayTurns=334;corpse.corpseTick();check(!corpse.deleted,"body survives until 336 decay turns");corpse.corpseTick();check(corpse.deleted&&tile.dirt==100,"outside crypt vanishes with MAX_DIRT");
 Creature worker;worker.map=&map;worker.seat=&seat;worker.tile=&tile;worker.alive=false;worker.definition.worker=true;size_t ghosts=map.ghosts.size();worker.corpseTick();check(worker.deleted&&map.ghosts.size()==ghosts&&Spell::vanish==1,"worker vanishes in original death turn without ghost");
 Creature consumed;consumed.map=&map;consumed.seat=&seat;consumed.tile=&tile;consumed.alive=false;consumed.mDeathCounter=1;check(consumed.takeCorpse(),"intact body can be reserved");check(!consumed.takeCorpse(),"consumed body cannot be reused");consumed.corpseTick();check(consumed.deleted&&consumed.drops==0&&map.ghosts.size()==ghosts,"consumed body has no death reward");
 for(int tier=1;tier<=3;++tier){seat.tier=tier;RoomCrypt crypt;crypt.map=&map;crypt.seat=&seat;crypt.type=RoomType::crypt;tile.room=&crypt;tile.dirt=0;map.creatures.clear();
  Creature body;body.map=&map;body.seat=&seat;body.tile=&tile;body.alive=false;body.mDeathCounter=1;body.mCorpseTurns=50.125;body.onMap=false;crypt.mRottingCreatures[&tile]=&body;body.corpseTick();near(body.mCorpseTurns,51.125,"delivered off-map body retains fractional lie remainder");near(body.mDecayTurns,-1,"crypt delivery does not start decay");
  const int threshold=tier==1?10:tier==2?8:6;for(int i=0;i<threshold-1;++i)crypt.mCorpseLevels.push_back(i==0?1:7);body.level=9;body.mDecayTurns=335;body.corpseTick();check(body.deleted&&tile.dirt==0,"crypt decay credits without terminal dirt");check(map.creatures.size()==1&&crypt.mCorpseLevels.empty(),"complete FIFO group spawns one lich");unsigned int expected=unsigned(std::floor((1.0+7*(threshold-2)+9)/threshold))+tier-1;check(map.creatures.front()->level==expected,"floor average then exact tier bonus");
  map.creatures.clear();crypt.mCorpseLevels.assign(threshold-1,30);body.deleted=false;body.level=30;crypt.mRottingCreatures[&tile]=&body;crypt.notifyCorpseDecayed(body);check(map.creatures.front()->level==30,"lich level cap 30");
  map.creatures.clear();std::vector<Creature> population(20);for(Creature& member:population){member.seat=&seat;map.creatures.push_back(&member);}crypt.mCorpseLevels.assign(threshold-1,4);crypt.mRottingCreatures[&tile]=&body;crypt.notifyCorpseDecayed(body);check(crypt.mCorpseLevels.size()==size_t(threshold)&&map.creatures.size()==20,"population cap retains FIFO levels");map.creatures.clear();crypt.mRottingCreatures[&tile]=&body;crypt.notifyCorpseDecayed(body);check(map.creatures.size()==1&&crypt.mCorpseLevels.size()==1,"later decay retries retained FIFO group");
 }
 seat.tier=1;RoomCrypt crypt;crypt.map=&map;crypt.seat=&seat;crypt.type=RoomType::crypt;tile.room=&crypt;Creature revived;revived.map=&map;revived.seat=&seat;revived.tile=&tile;revived.alive=false;revived.mDeathCounter=1;revived.mDecayTurns=250.125;revived.mCorpseTurns=418.125;revived.onMap=false;revived.level=17;revived.exp=12.25;crypt.mRottingCreatures[&tile]=&revived;
 check(revived.reviveFromCorpse(.35),"delivered decaying body can revive");near(revived.hp,35,"35 percent health");near(revived.exp,12.25,"revival retains old XP");check(revived.level==17&&revived.onMap&&crypt.mRottingCreatures[&tile]==nullptr,"revival retains level and releases grave");near(revived.mThirst,80,"revival direct thirst applies even to non-thirsty classes");near(revived.mHunger,80,"revival hungry");near(revived.mWakefulness,20,"revival tired");check(revived.koResets==1&&revived.queueClears==1&&revived.mDecayTurns==-1&&revived.mDeathCounter==0,"revival clears fatal and corpse state");
 check(!revived.reviveFromCorpse(.35),"living creature cannot revive again");revived.alive=false;revived.mDeathCounter=1;revived.mIsCarried=true;check(!revived.reviveFromCorpse(.35),"carried body cannot revive");
 std::cout<<"corpse clocks, FIFO crypt and revival: ok\n";
}
'''
    run_probe('corpse-rules', code)

if __name__ == '__main__':
    main()
