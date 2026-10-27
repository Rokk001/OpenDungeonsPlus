"""Compile real ghost, box, corpse, crypt, hunter and seat save/packet bodies.

Execution is compiler-gated; optional-block and malformed-record assertions are never skipped.
"""
from check_ghost_rules import function, read, run_probe
from check_corpse_rules import corpse_fixture

# Build the real codecs around independent identity and storage services.
def stream_fixture():
    code = corpse_fixture()
    code = code.replace('static const Vector3 ZERO;', 'Vector3 operator-(const Vector3& other)const{return Vector3(x-other.x,y-other.y,z-other.z);}static const Vector3 ZERO;')
    code = code.replace('rot_anim="Rot";', 'rot_anim="Rot",beam_anim="Beam",throw_anim="Throw",empty_anim="Empty";')
    code = code.replace('std::vector<Seat*> seats;', 'std::vector<Seat*> seats;std::vector<Room*> rooms;')
    code = code.replace(' int getMapSizeY()const{return 8;}', 'int getMapSizeY()const{return 8;}std::vector<Room*> getRoomsByType(RoomType type){std::vector<Room*> result;for(Room* room:rooms)if(room->type==type)result.push_back(room);return result;}')
    code = code.replace('RoomType type=RoomType::other;Seat* seat=nullptr;', 'RoomType type=RoomType::other;Seat* seat=nullptr;std::string name;')
    code = code.replace(' RoomType getType()const{return type;}', 'const std::string& getName()const{return name;}RoomType getType()const{return type;}')
    code = code.replace(' Creature()=default;', r'''
 std::deque<Ogre::Vector2> savedPath;
 //! \brief Receives the real restored walk path and selected pose.
 void setWalkPath(const std::string& value,const std::string&,bool,bool,const std::vector<Ogre::Vector2>& path,bool,bool){animation=value;savedPath.assign(path.begin(),path.end());}
 //! \brief Observes restored public hunter appearance refresh.
 void refreshGhostHuntVisuals(){}
 //! \brief Exposes the exact path written by the production hunter codec.
 const std::deque<Ogre::Vector2>& getWalkQueue()const{return savedPath;}
 Creature()=default;
''')
    ghost = read('source/entities/GhostEntity.cpp')
    for sig in ['    const char* stateName(', '    bool readState(', 'void GhostEntity::exportToStream(',
            'bool GhostEntity::importFromStream(', 'void GhostEntity::exportToPacket(', 'void GhostEntity::importFromPacket(',
            'void GhostEntity::exportToPacketForUpdate(', 'void GhostEntity::updateFromPacket(']:
        code += function(ghost, sig)
    crypt = read('source/rooms/RoomCrypt.cpp')
    code += function(crypt,'void RoomCrypt::exportToStream(')+function(crypt,'bool RoomCrypt::importFromStream(')
    code += r'''
//! \brief Retains only the real box continuation fields and unchanged base codec services.
struct GhostBoxEntity:RenderedMovableEntity{GameMap* map=nullptr;Seat* seat=nullptr;bool server=true,onMap=true,deleted=false;std::string mName="box",mAssignedHunter;double mOpenTurns=0;Ogre::Vector3 mPosition;std::vector<std::string> mGhostNames;
 //! \brief Returns box authority.
 bool getIsOnServerMap()const{return server;}
 //! \brief Returns whether the box is lying on the map.
 bool getIsOnMap()const{return onMap;}
 //! \brief Returns its controlled world.
 GameMap* getGameMap()const{return map;}
 //! \brief Returns its keeper.
 Seat* getSeat()const{return seat;}
 //! \brief Restores its keeper.
 void setSeat(Seat* value){seat=value;}
 //! \brief Returns its exact identity.
 const std::string& getName()const{return mName;}
 //! \brief Returns its exact position.
 const Ogre::Vector3& getPosition()const{return mPosition;}
 //! \brief Returns its tile.
 Tile* getPositionTile(){return map->getTile(int(mPosition.x),int(mPosition.y));}
 //! \brief Records removal without invalidating observations.
 void removeFromGameMap(){onMap=false;}
 //! \brief Records deferred deletion.
 void deleteYourself(){deleted=true;}
 //! \brief Runs the actual box opening code.
 void doUpkeep();
 //! \brief Runs the actual box save writer.
 void exportToStream(std::ostream&)const;
 //! \brief Runs the actual box save reader.
 bool importFromStream(std::istream&);
 //! \brief Runs the actual box creation writer.
 void exportToPacket(ODPacket&,const Seat*)const;
 //! \brief Runs the actual box creation reader.
 void importFromPacket(ODPacket&);
 //! \brief Runs the actual box update writer.
 void exportToPacketForUpdate(ODPacket&,Seat*);
 //! \brief Runs the actual box update reader.
 void updateFromPacket(ODPacket&);
};
//! \brief Supplies the actual saved hook-slot lookup contract.
struct RoomGhostRoom:Room{size_t restoredSlot=0;Tile* standing=nullptr;Tile* anchor=nullptr;
 //! \brief Returns a controlled reserved hook index.
 size_t getHunterHookSlot(const Creature&)const{return 7;}
 //! \brief Records the exact restored hook slot and equipment state.
 void restoreHunter(Creature&,Tile*,bool,size_t slot){restoredSlot=slot;}
 //! \brief Records exact restored standing tile and occupied cauldron anchor.
 void restoreCauldron(Creature&,Tile* stand,Tile* at,bool){standing=stand;anchor=at;}
};
//! \brief Stores every hunter continuation field used by the real codec.
struct CreatureActionHuntGhost{Creature& mCreature;uint32_t mState=0;std::string mTarget,mHookRoom,mReviveTarget,mEmptyRoom;int mHookX=0,mHookY=0;double mTurns=0,mRepathTurns=0;size_t mHookSlot=0;bool mEquipped=false,mRestoring=false,mRegistered=false,interrupted=false;std::string mBeamTarget;RoomGhostRoom* equipment=nullptr;std::vector<std::string> mGhosts,mReviveGhosts;std::vector<Ogre::Vector2> mLoadedPath;Tile* mDestination=nullptr;Tile* mEmptyAnchor=nullptr;
 //! \brief Binds this saved action to its owner.
 CreatureActionHuntGhost(Creature& creature):mCreature(creature){}
 //! \brief Uses the saved exact hook slot in an unbound continuation.
 RoomGhostRoom* hookRoom()const{return equipment;}
 //! \brief Observes an impossible loaded equipment continuation.
 void interrupt(){interrupted=true;}
 //! \brief Executes original loaded walk and Beam/Throw/Empty restoration.
 void restore();
 //! \brief Executes the original full hunter writer.
 void exportToStream(std::ostream&)const;
 //! \brief Executes the original full hunter reader.
 bool importFromStream(std::istream&);
};
'''
    box = read('source/entities/GhostBoxEntity.cpp')
    for sig in ['void GhostBoxEntity::doUpkeep(', 'void GhostBoxEntity::exportToStream(', 'bool GhostBoxEntity::importFromStream(',
            'void GhostBoxEntity::exportToPacket(', 'void GhostBoxEntity::importFromPacket(',
            'void GhostBoxEntity::exportToPacketForUpdate(', 'void GhostBoxEntity::updateFromPacket(']:
        code += function(box,sig)
    hunter = read('source/creatureaction/CreatureActionHuntGhost.cpp')
    code += function(hunter,'void CreatureActionHuntGhost::exportToStream(')+function(hunter,'bool CreatureActionHuntGhost::importFromStream(')
    code += function(hunter,'GhostEntity* ghostNamed(')+function(hunter,'RoomGhostRoom* roomNamed(')+function(hunter,'void CreatureActionHuntGhost::restore(')
    seat = read('source/game/Seat.cpp')
    seat_import = function(seat,'    if(str == "[GhostBells]")')+function(seat,'    if(str == "[GhostRoom]")')
    seat_start = seat.index('    os << "[GhostBells]')
    seat_end = seat.index('    os << "[Merchant]',seat_start)
    seat_save = seat[seat_start:seat_end]
    creature = read('source/entities/Creature.cpp')
    corpse_import = ''.join(function(creature,sig) for sig in ['        if(appearanceToken.compare(0, CORPSE_CARRIER_SAVE_LABEL.size()',
        '        if(appearanceToken == "CorpseDeathPending=1")','        if(appearanceToken == "CorpseConsumed=1")',
        '        if(appearanceToken == "[GhostRevival]")','        if(appearanceToken == "[Corpse]")'])
    final_start = creature.index('    // Apply last so arbitrary tag order')
    final_end = creature.index('    return true;',final_start)
    corpse_final = creature[final_start:final_end]
    save_start = creature.index('    if(!isAlive())', creature.index('void Creature::exportToStream('))
    save_end = creature.index('    for(const std::unique_ptr<CreatureAction>& action',save_start)
    corpse_save = creature[save_start:save_end]
    code += r'''
//! \brief Supplies strict numeric conversion to the real corpse block.
namespace Helper{
 //! \brief Reads the original HP string value.
 double toDouble(const std::string& value){return std::stod(value);}}
const std::string CORPSE_CARRIER_SAVE_LABEL="CorpseCarrier=";const double THIRST_STATE_MAX=100;
//! \brief Runs only the real optional seat blocks with legacy defaults and unrelated-tag preservation.
struct SeatRecord{double mEctoplasmLevels=0;GhostProduct mGhostProduct=GhostProduct::research;bool mGhostRevive=true;std::set<std::string> mGhostBellTargets;
 //! \brief Writes both real seat optional blocks at full precision.
 void save(std::ostream& os)const{os<<std::setprecision(17);SEAT_SAVE}
 //! \brief Reads the actual optional blocks in either order.
 bool load(std::istream& is){std::string str;if(!(is>>str))return false;while(true){SEAT_IMPORT
  if(str=="[GhostRoom]"||str=="[GhostBells]")continue;
  if(str=="[Other]"){if(!(is>>str)||str!="[/Other]"||!(is>>str))return false;continue;}return str=="EndSeat";}}
};
//! \brief Retains exact corpse clocks, transient markers and the fading revival mood.
struct CorpseRecord{double mCorpseTurns=0,mDecayTurns=-1,mSpecialMood=0,mThirst=0,mSavedRevivalThirst=0;unsigned int mDeathCounter=1;bool mIsCarried=false,mGhostRevived=false,mRevivalThirstFromSave=false;std::string mHpString="0",mCorpseCarrierName;
 //! \brief Reports the dead saved record to the real writer.
 bool isAlive()const{return mHpString=="max"||std::stod(mHpString)>0;}
 //! \brief Writes original corpse and revival blocks at full precision.
 void save(std::ostream& os)const{os<<std::setprecision(17);CORPSE_SAVE}
 //! \brief Reads actual optional tags and applies original transient-state precedence.
 bool load(std::istream& is){bool corpseConsumed=false,corpseDeathPending=false;std::string appearanceToken;
  while(is>>appearanceToken){CORPSE_IMPORT
   if(appearanceToken=="[Other]"){if(!(is>>appearanceToken)||appearanceToken!="[/Other]")return false;continue;}
   if(appearanceToken!="EndCreature")return false;break;}CORPSE_FINAL return true;}
};
'''.replace('SEAT_SAVE',seat_save).replace('SEAT_IMPORT',seat_import).replace('CORPSE_SAVE',corpse_save).replace('CORPSE_IMPORT',corpse_import).replace('CORPSE_FINAL',corpse_final)
    return code

# Exercise complete records, exact fractional counters, legacy boundaries and rejection paths.
def main():
    code = stream_fixture()+r'''
//! \brief Runs the real serializers with nondefault continuation data and old-save sentinels.
int main(){
 GameMap map;Seat seat;map.seats.push_back(&seat);for(int y=0;y<8;++y)for(int x=0;x<8;++x){Tile& tile=map.tiles[{x,y}];tile.x=x;tile.y=y;}
 for(GhostState phase:{GhostState::rising,GhostState::floating,GhostState::beamed,GhostState::boxed,GhostState::dissolving}){
  GhostEntity first;first.map=&map;first.seat=&seat;first.mState=phase;first.mLifeLeft=123.125;first.mStateTurns=.375;first.mHowlTurns=7.625;first.mAssignedHunter="hunter";first.mScaredCreatures={"scared1","scared2"};first.mPosition=Ogre::Vector3(2.25f,3.5f,0);first.mWalkQueue={Ogre::Vector2(3,3),Ogre::Vector2(4,3)};
  std::stringstream stream;first.exportToStream(stream);GhostEntity second;second.map=&map;check(second.importFromStream(stream),"ghost full save");near(second.mLifeLeft,123.125,"remaining life exact");near(second.mStateTurns,.375,"rise dissolve phase exact");near(second.mHowlTurns,7.625,"howl continuation exact");check(second.mState==phase&&second.mAssignedHunter=="hunter"&&second.mScaredCreatures==first.mScaredCreatures&&second.mWalkQueue.size()==2,"ghost states identities scared set and rest path");
  ODPacket packet;first.exportToPacket(packet,&seat);GhostEntity client;client.map=&map;client.importFromPacket(packet);check(packet.cursor==packet.tokens.size(),"ghost creation consumes symmetric fields");near(client.mHowlTurns,7.625,"ghost creation howl");first.mLifeLeft=75.875;first.mStateTurns=1.125;ODPacket update;first.exportToPacketForUpdate(update,&seat);client.updateFromPacket(update);near(client.mLifeLeft,75.875,"ghost update lifetime");near(client.mStateTurns,1.125,"ghost update phase");check(update.cursor==update.tokens.size(),"ghost update tail symmetry");
 }
 GhostEntity oldGhost;oldGhost.map=&map;std::stringstream old("1 old Rat victim 2 3 7 45.125 floating none");check(oldGhost.importFromStream(old)&&oldGhost.mHowlTurns==100,"legacy ghost without optional runtime");GhostEntity bad;bad.map=&map;std::stringstream badGhost("1 bad Rat victim 2 3 7 45.125 invalid none");check(!bad.importFromStream(badGhost),"invalid phase rejected");
 GhostEntity boxed;boxed.map=&map;boxed.seat=&seat;boxed.mName="inside";boxed.mState=GhostState::boxed;boxed.mLifeLeft=31.625;map.ghosts.push_back(&boxed);
 GhostBoxEntity box;box.map=&map;box.seat=&seat;box.mPosition=Ogre::Vector3(4,5,0);box.mOpenTurns=166.5;box.mAssignedHunter="hunter";box.mGhostNames={"inside","missing"};std::stringstream boxSave;box.exportToStream(boxSave);GhostBoxEntity loaded;loaded.map=&map;check(loaded.importFromStream(boxSave),"box complete save");near(loaded.mOpenTurns,166.5,"box fractional opening time");check(loaded.mGhostNames==box.mGhostNames&&loaded.mAssignedHunter=="hunter","box complete identities");
 loaded.doUpkeep();check(!loaded.deleted,"box before 168 turns");near(boxed.mLifeLeft,31.625,"boxed lifetime paused during lying-box countdown");loaded.doUpkeep();check(loaded.deleted&&boxed.mState==GhostState::floating&&boxed.mAssignedHunter.empty()&&boxed.mPosition.x==4,"expired box releases at exact box placement");near(boxed.mLifeLeft,31.625,"release retains catch lifetime");
 ODPacket bp;box.exportToPacket(bp,&seat);GhostBoxEntity bc;bc.map=&map;bc.importFromPacket(bp);check(bp.cursor==bp.tokens.size()&&bc.mGhostNames==box.mGhostNames,"box creation all names");ODPacket bu;box.exportToPacketForUpdate(bu,&seat);bc.updateFromPacket(bu);check(bu.cursor==bu.tokens.size()&&bc.mOpenTurns==166.5,"box update symmetry");
 RoomCrypt crypt;crypt.map=&map;crypt.seat=&seat;crypt.mCorpseLevels={2,19,7};Creature corpse;corpse.name="body";crypt.mRottingCreatures[map.getTile(1,2)]=&corpse;crypt.mRottingCreatures[map.getTile(2,2)]=nullptr;std::stringstream cs;crypt.exportToStream(cs);cs<<" EndRoom";RoomCrypt restored;restored.map=&map;check(restored.importFromStream(cs),"crypt complete tags");std::string token;cs>>token;check(token=="EndRoom"&&restored.mCorpseLevels==crypt.mCorpseLevels&&restored.mCorpseSpotNames[{1,2}]=="body"&&restored.mCorpseSpotNames[{2,2}]=="none","crypt FIFO names and following record");std::stringstream legacy("0 [/Room] [Room] 9 next");RoomCrypt oldCrypt;check(oldCrypt.importFromStream(legacy),"legacy trailing crypt zero");legacy>>token;check(token=="[/Room]","legacy crypt leaves following room intact");
 Creature hunter;hunter.map=&map;hunter.savedPath={Ogre::Vector2(2,3),Ogre::Vector2(3,3)};for(uint32_t state=0;state<=8;++state){CreatureActionHuntGhost action(hunter);action.mState=state;action.mTarget="target";action.mHookRoom="hooks";action.mHookX=2;action.mHookY=3;action.mTurns=1.125;action.mRepathTurns=3.875;action.mHookSlot=7;action.mEquipped=true;action.mGhosts={"a","b","c"};action.mReviveGhosts={"a","c"};action.mReviveTarget="a";action.mEmptyRoom="press";action.mDestination=map.getTile(3,4);action.mEmptyAnchor=map.getTile(4,4);std::stringstream hs;hs<<std::setprecision(17);action.exportToStream(hs);hs>>token;check(token=="[GhostHunt]","hunter opening tag");CreatureActionHuntGhost resumed(hunter);check(resumed.importFromStream(hs),"all nine hunt states roundtrip");near(resumed.mTurns,1.125,"hunter fractional step");near(resumed.mRepathTurns,3.875,"hunter fractional repath");check(resumed.mHookSlot==7&&resumed.mGhosts==action.mGhosts&&resumed.mReviveGhosts==action.mReviveGhosts&&resumed.mDestination==action.mDestination&&resumed.mEmptyAnchor==action.mEmptyAnchor&&resumed.mLoadedPath.size()==2,"exact hook cauldron stand path and revival candidates");}
 for(const std::string& malformed:{"9 none none 0 0 0 0 [/GhostHunt]","2 none none 0 0 -1 0 [/GhostHunt]","2 none none 0 0 1 1 [/GhostHunt]"}){CreatureActionHuntGhost action(hunter);std::stringstream stream(malformed);check(!action.importFromStream(stream),"malformed hunt rejected");}
 SeatRecord record;record.mEctoplasmLevels=8.875;record.mGhostProduct=GhostProduct::crystal;record.mGhostRevive=false;record.mGhostBellTargets={"a","b"};std::stringstream ss;record.save(ss);ss<<" EndSeat";SeatRecord rs;check(rs.load(ss)&&rs.mEctoplasmLevels==8.875&&rs.mGhostProduct==GhostProduct::crystal&&!rs.mGhostRevive&&rs.mGhostBellTargets==record.mGhostBellTargets,"seat bar switches and one-shot bells");std::stringstream emptySeat("[Other] [/Other] EndSeat");SeatRecord defaults;check(defaults.load(emptySeat)&&defaults.mEctoplasmLevels==0&&defaults.mGhostProduct==GhostProduct::research&&defaults.mGhostRevive,"old seat defaults");for(const std::string& text:{"[GhostRoom] -1 0 1 [/GhostRoom] EndSeat","[GhostRoom] 1 3 1 [/GhostRoom] EndSeat","[GhostRoom] 1 0 1 wrong EndSeat"}){SeatRecord broken;std::stringstream stream(text);check(!broken.load(stream),"invalid seat settings rejected");}
 CorpseRecord cr;cr.mCorpseTurns=88.125;cr.mDecayTurns=2.875;cr.mIsCarried=true;cr.mCorpseCarrierName="worker";cr.mDeathCounter=std::numeric_limits<unsigned int>::max();std::stringstream cps;cr.save(cps);cps<<" EndCreature";CorpseRecord rr;check(rr.load(cps)&&rr.mCorpseTurns==88.125&&rr.mDecayTurns==2.875&&rr.mDeathCounter==std::numeric_limits<unsigned int>::max()&&rr.mCorpseCarrierName=="worker","corpse exact counters and transient consumed/carrier");std::stringstream pending("CorpseDeathPending=1 [Corpse] 0 -1 [/Corpse] EndCreature");CorpseRecord pendingRecord;check(pendingRecord.load(pending)&&pendingRecord.mDeathCounter==0,"pending death survives arbitrary tag order");std::stringstream oldCorpse("[Other] [/Other] EndCreature");CorpseRecord oldRecord;check(oldRecord.load(oldCorpse)&&oldRecord.mCorpseTurns==0&&oldRecord.mDecayTurns==-1,"old corpse defaults");std::stringstream revival("[GhostRevival] 13.125 80 [/GhostRevival] EndCreature");CorpseRecord rev;check(rev.load(revival)&&rev.mSpecialMood==13.125&&rev.mSavedRevivalThirst==80&&rev.mRevivalThirstFromSave,"declining happy mood and direct thirst continuation");

 for(const std::string& invalid:{"[Corpse] -0.125 -1 [/Corpse] EndCreature","[Corpse] 1 -1.125 [/Corpse] EndCreature","[Corpse] 1 0 wrong EndCreature","[GhostRevival] 2 100.125 [/GhostRevival] EndCreature"}){CorpseRecord record;std::stringstream stream(invalid);check(!record.load(stream),"malformed corpse and revival optional blocks rejected");}
 for(const std::string& invalid:{"0 CorpseLevels 2 1","0 CryptSpots 1 2 3"}){RoomCrypt record;std::stringstream stream(invalid);check(!record.importFromStream(stream),"short crypt FIFO and spot records rejected");}
 GhostBoxEntity legacyBox;legacyBox.map=&map;std::stringstream oldBox("old 2 3 17.875 0");check(legacyBox.importFromStream(oldBox)&&legacyBox.mAssignedHunter.empty()&&legacyBox.mOpenTurns==17.875,"legacy box without runtime");
 CreatureActionHuntGhost legacyHunt(hunter);std::stringstream oldHunt("2 none none 1 2 1.375 1 inside [/GhostHunt] NEXT");check(legacyHunt.importFromStream(oldHunt)&&legacyHunt.mRestoring&&legacyHunt.mGhosts.size()==1,"old hunter without runtime");oldHunt>>token;check(token=="NEXT","old hunter preserves following tag");
 SeatRecord reordered;std::stringstream order("[GhostRoom] 1.125 1 0 [/GhostRoom] [GhostBells] 1 earlier [/GhostBells] EndSeat");check(reordered.load(order)&&reordered.mEctoplasmLevels==1.125&&reordered.mGhostBellTargets.count("earlier"),"seat optional blocks also load in reverse order");
 RoomGhostRoom restoredRoom;restoredRoom.type=RoomType::ghostRoom;restoredRoom.seat=&seat;restoredRoom.name="press";map.rooms.push_back(&restoredRoom);hunter.tile=map.getTile(2,2);
 for(uint32_t phase:{2u,3u,6u}){CreatureActionHuntGhost resumed(hunter);resumed.mState=phase;resumed.mRestoring=true;resumed.equipment=&restoredRoom;resumed.mHookSlot=7;resumed.mHookX=1;resumed.mHookY=2;resumed.mTarget="inside";resumed.mEmptyRoom="press";resumed.mDestination=map.getTile(3,4);resumed.mEmptyAnchor=map.getTile(4,4);resumed.mLoadedPath={Ogre::Vector2(3,3)};resumed.restore();check(resumed.mRegistered&&!resumed.mRestoring&&restoredRoom.restoredSlot==7,"load binds exact reserved hook slot before assignment");check(hunter.animation==(phase==2?"Beam":phase==3?"Throw":"Empty"),"load restores exact active phase pose");if(phase==6)check(restoredRoom.standing==resumed.mDestination&&restoredRoom.anchor==resumed.mEmptyAnchor,"load restores exact occupied cauldron and standing place");}
 std::cout<<"ghost streams and packets: ok\n";
}
'''
    run_probe('ghost-streams',code)


# Assemble the original creature/room presentation tails and free-reveal codecs.
def packet_fixture():
    from check_ghost_rules import PRELUDE
    code = PRELUDE+r'''
//! \brief Supplies transparent unchanged base packet and stream prefixes.
struct RenderedMovableEntity{
 //! \brief Supplies ordinary creation prefix.
 void exportToPacket(ODPacket&,const Seat*)const{}
 //! \brief Supplies ordinary creation reader prefix.
 void importFromPacket(ODPacket&){}
 //! \brief Supplies ordinary update prefix.
 void exportToPacketForUpdate(ODPacket&,Seat*){}
 //! \brief Supplies ordinary update reader prefix.
 void updateFromPacket(ODPacket&){}
};
//! \brief Retains actual furniture presentation state and merchant fields.
struct BuildingObject:RenderedMovableEntity{Ogre::Vector2 mFurnitureScale{.75f,1.25f};int32_t mItemBagQuality=2;bool mItemBagSealed=true;double mGhostFill=.625,mGhostAlarm=3.125;
 //! \brief Runs original furniture creation writer.
 void exportToPacket(ODPacket&,const Seat*)const;
 //! \brief Runs original furniture creation reader.
 void importFromPacket(ODPacket&);
 //! \brief Runs original furniture update writer.
 void exportToPacketForUpdate(ODPacket&,Seat*);
 //! \brief Runs original furniture update reader.
 void updateFromPacket(ODPacket&);
};
//! \brief Supplies unchanged ordinary-spell codec services to the free reveal extension.
struct Spell:RenderedMovableEntity{
 //! \brief Supplies ordinary spell stream prefix.
 void exportToStream(std::ostream&)const{}
 //! \brief Supplies ordinary spell stream reader prefix.
 bool importFromStream(std::istream&){return true;}
};
//! \brief Stores the actual reveal mode, base radius and remaining lifetime.
struct SpellEyeEvil:Spell{bool mFreeMode=false;uint32_t mFreeRadius=0;int32_t mFreeTurns=0;int duration=0;
 //! \brief Receives the exact restored free-spell duration.
 void setDuration(int value){duration=value;}
 //! \brief Runs original free-mode save writer.
 void exportToStream(std::ostream&)const;
 //! \brief Runs original free-mode save reader.
 bool importFromStream(std::istream&);
 //! \brief Runs original free-mode creation writer.
 void exportToPacket(ODPacket&,const Seat*)const;
 //! \brief Runs original free-mode creation reader.
 void importFromPacket(ODPacket&);
};
'''
    building = read('source/entities/BuildingObject.cpp')
    for sig in ['void BuildingObject::exportToPacket(', 'void BuildingObject::importFromPacket(',
            'void BuildingObject::exportToPacketForUpdate(', 'void BuildingObject::updateFromPacket(']:
        code += function(building,sig)
    eye = read('source/spells/SpellEyeEvil.cpp')
    for sig in ['void SpellEyeEvil::exportToStream(', 'bool SpellEyeEvil::importFromStream(',
            'void SpellEyeEvil::exportToPacket(', 'void SpellEyeEvil::importFromPacket(']:
        code += function(eye,sig)
    source = read('source/entities/Creature.cpp')
    writer = function(source,'void Creature::exportToPacket(')
    update = function(source,'void Creature::exportToPacketForUpdate(')
    reader = function(source,'void Creature::importFromPacket(')
    update_reader = function(source,'void Creature::updateFromPacket(')
    full_tail = writer[writer.index('    exportSkillBuildToPacket(os);'):writer.rindex('}')]
    update_tail = update[update.index('    exportSkillBuildToPacket(os);'):update.rindex('}')]
    read_start = reader.index('    importSkillBuildFromPacket(is);')
    read_end = reader.index('    setupDefinition(',read_start)
    full_read = reader[read_start:read_end]
    update_start = update_reader.index('    importSkillBuildFromPacket(is);')
    update_end = update_reader.index('    // The thief sack',update_start)
    update_read = update_reader[update_start:update_end]
    code += r'''
//! \brief Retains every field in the real existing item/needs/thirst/corpse/hunter packet tail.
struct CreatureTail{Seat* owner=nullptr;double mGoldCarried=12.25,mInfirmaryMood=7.5,mUrge=9.125,mCreatureDirt=2.75,mThirst=80,mTavernMood=-2.5,mDrunk=4.125,mHangoverTurns=3.375,mSpaMood=5.5,mRelaxTurns=6.25,mCorpseTurns=167.875,mDecayTurns=22.125,mGhostThrowTurns=.375,mGhostThrowClientTurns=0;bool mGhostBackpack=true;std::string mGhostBeamTarget="ghost",mGhostThrowTarget="target";uint32_t mGhostBoxMode=2;int skill=3,items=4;
 //! \brief Returns owner for exact existing visibility masks.
 Seat* getSeat()const{return owner;}
 //! \brief Supplies distinct unchanged skill-prefix tokens.
 void exportSkillBuildToPacket(ODPacket& os)const{os<<skill;}
 //! \brief Reads unchanged skill-prefix tokens.
 void importSkillBuildFromPacket(ODPacket& is){OD_ASSERT_TRUE(is>>skill);}
 //! \brief Supplies distinct unchanged item-prefix tokens.
 void exportItemsToPacket(ODPacket& os,const Seat*)const{os<<items;}
 //! \brief Reads unchanged item-prefix tokens.
 bool importItemsFromPacket(ODPacket& is){return bool(is>>items);}
 //! \brief Runs the real four-field thirst writer.
 void exportThirstStateToPacket(ODPacket&)const;
 //! \brief Runs the real four-field thirst reader.
 void importThirstStateFromPacket(ODPacket&);
 //! \brief Runs the real two-field lava spa writer.
 void exportSpaStateToPacket(ODPacket&)const;
 //! \brief Runs the real two-field lava spa reader.
 void importSpaStateFromPacket(ODPacket&);
 //! \brief Runs the unchanged complete creation tail.
 void full(ODPacket& os,const Seat* seat)const{FULL_WRITE}
 //! \brief Runs the unchanged complete update tail including owner masks.
 void update(ODPacket& os,Seat* seat){UPDATE_WRITE}
 //! \brief Runs the unchanged complete creation decoder tail.
 void readFull(ODPacket& is){FULL_READ}
 //! \brief Runs the unchanged complete update decoder tail.
 void readUpdate(ODPacket& is){UPDATE_READ}
};
'''.replace('FULL_WRITE',full_tail).replace('UPDATE_WRITE',update_tail).replace('FULL_READ',full_read).replace('UPDATE_READ',update_read)
    code += function(source,'void Creature::exportThirstStateToPacket(').replace('Creature::','CreatureTail::')
    code += function(source,'void Creature::importThirstStateFromPacket(').replace('Creature::','CreatureTail::')
    code += function(source,'void Creature::exportSpaStateToPacket(').replace('Creature::','CreatureTail::')
    code += function(source,'void Creature::importSpaStateFromPacket(').replace('Creature::','CreatureTail::')
    seat_source = read('source/game/SeatData.cpp')
    seat_writer = function(seat_source,'void SeatData::exportToPacketForUpdate(')
    seat_writer = seat_writer[seat_writer.index('    os << getInfirmaryPayer()'):seat_writer.rindex('}')]
    seat_reader = function(seat_source,'bool SeatData::importFromPacketForUpdate(')
    seat_reader = seat_reader[seat_reader.index('    int32_t payer = 0;'):seat_reader.rindex('}')]
    code += r'''
//! \brief Keeps the actual owner-only room setting codec tail and its old infirmary prefix.
struct SeatDataTail{int32_t payer=1,mInfirmaryThreshold=65;bool mInfirmaryHealOn=false,mGhostRevive=false;double mEctoplasmLevels=8.875;GhostProduct mGhostProduct=GhostProduct::crystal;
 //! \brief Returns the existing payer setting.
 int32_t getInfirmaryPayer()const{return payer;}
 //! \brief Receives the existing payer setting.
 void setInfirmaryPayer(int32_t value){payer=value;}
 //! \brief Receives the existing threshold setting.
 void setInfirmaryThreshold(int32_t value){mInfirmaryThreshold=value;}
 //! \brief Receives the existing healing switch.
 void setInfirmaryHealOn(bool value){mInfirmaryHealOn=value;}
 //! \brief Executes the original owner-only settings writer.
 void save(ODPacket& os)const{SEAT_WRITE}
 //! \brief Executes the original owner-only settings decoder and validation.
 bool load(ODPacket& is){SEAT_READ}
};
'''.replace('SEAT_WRITE',seat_writer).replace('SEAT_READ',seat_reader)
    return code

# Check tail symmetry and preserved old fields as well as free reveal legacy boundaries.
def packet_checks():
    protocol = read('source/network/ODPacket.h')
    client = read('source/network/ODClient.cpp')
    server = read('source/network/ODServer.cpp')
    assert 'WIRE_SCHEMA_SUFFIX' in protocol
    assert 'NetworkProtocol::WIRE_SCHEMA_SUFFIX' in client and 'NetworkProtocol::WIRE_SCHEMA_SUFFIX' in server
    hello = server.index('NetworkProtocol::WIRE_SCHEMA_SUFFIX')
    assert hello < server.index('ServerNotificationType::loadLevel',hello), 'schema rejects before changed records'
    code = packet_fixture()+r'''
//! \brief Checks exact real packet tails and old ordinary-spell continuations.
int main(){
 Seat owner,other;CreatureTail first;first.owner=&owner;for(bool update:{false,true})for(Seat* viewer:{&owner,&other}){ODPacket packet;if(update)first.update(packet,viewer);else first.full(packet,viewer);CreatureTail second;if(update)second.readUpdate(packet);else second.readFull(packet);check(packet.cursor==packet.tokens.size(),"complete creature tail symmetry");near(second.mGoldCarried,12.25,"gold remains double");check(second.skill==3&&second.items==4,"old skill and item tails retained");near(second.mCorpseTurns,167.875,"corpse counter public exact");near(second.mDecayTurns,22.125,"decay counter public exact");check(second.mGhostBackpack&&second.mGhostBeamTarget=="ghost"&&second.mGhostBoxMode==2&&second.mGhostThrowTarget=="target","all hunter visual fields");near(second.mGhostThrowClientTurns,.375,"loaded throw phase exact");bool own=viewer==&owner;near(second.mInfirmaryMood,own?7.5:0,"existing infirmary owner mask");near(second.mUrge,update&&!own?0:9.125,"existing needs update mask");near(second.mThirst,update&&!own?0:80,"existing thirst update mask");near(second.mSpaMood,own?5.5:0,"lava spa owner mask");near(second.mHangoverTurns,update&&!own?0:3.375,"four thirst and two spa fields precede corpse doubles");near(second.mRelaxTurns,own?6.25:0,"relaxation owner mask");}
 BuildingObject firstObject,secondObject;ODPacket creation;firstObject.exportToPacket(creation,&owner);secondObject.importFromPacket(creation);check(creation.cursor==creation.tokens.size()&&secondObject.mFurnitureScale.x==.75f&&secondObject.mFurnitureScale.y==1.25f&&secondObject.mItemBagQuality==2&&secondObject.mItemBagSealed,"furniture old footprint and item fields preserved");near(secondObject.mGhostFill,.625,"furniture full fill");near(secondObject.mGhostAlarm,3.125,"furniture full alarm");firstObject.mGhostFill=.875;ODPacket update;firstObject.exportToPacketForUpdate(update,&owner);secondObject.updateFromPacket(update);check(update.cursor==update.tokens.size(),"furniture update symmetry");near(secondObject.mGhostFill,.875,"furniture update fill");
 SpellEyeEvil freeEye;freeEye.mFreeMode=true;freeEye.mFreeRadius=3;freeEye.mFreeTurns=7;std::stringstream stream;freeEye.exportToStream(stream);stream<<" EndSpell";SpellEyeEvil restored;check(restored.importFromStream(stream)&&restored.mFreeMode&&restored.mFreeRadius==3&&restored.mFreeTurns==7&&restored.duration==7,"free eye exact saved radius and remaining duration");std::string next;stream>>next;check(next=="EndSpell","free eye leaves following record");std::stringstream old("NextSpell");SpellEyeEvil ordinary;check(ordinary.importFromStream(old)&&!ordinary.mFreeMode,"old ordinary eye no free-mode research leak");old>>next;check(next=="NextSpell","old ordinary eye preserves next record");ODPacket eye;freeEye.exportToPacket(eye,&owner);SpellEyeEvil eyeClient;eyeClient.importFromPacket(eye);check(eye.cursor==eye.tokens.size()&&eyeClient.mFreeRadius==3&&eyeClient.duration==7,"free eye packet symmetry");
 SeatDataTail seatSource,seatResult;ODPacket seatPacket;seatSource.save(seatPacket);check(seatResult.load(seatPacket)&&seatPacket.cursor==seatPacket.tokens.size(),"owner-only seat settings symmetry");near(seatResult.mEctoplasmLevels,8.875,"owner seat bar exact");check(seatResult.mGhostProduct==GhostProduct::crystal&&!seatResult.mGhostRevive&&seatResult.payer==1&&seatResult.mInfirmaryThreshold==65&&!seatResult.mInfirmaryHealOn,"old infirmary and new ghost seat fields retained");
 for(uint32_t product:{3u,99u}){ODPacket invalid;invalid<<int32_t(1)<<int32_t(65)<<false<<1.25<<product<<true;SeatDataTail result;check(!result.load(invalid)&&result.mEctoplasmLevels==8.875,"invalid product cannot partially adopt ghost settings");}
 std::cout<<"creature furniture and free-eye tails: ok\n";
}
'''
    run_probe('ghost-packet-tails',code)

if __name__ == '__main__':
    main()
    packet_checks()
