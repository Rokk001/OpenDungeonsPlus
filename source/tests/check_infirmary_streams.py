"""Compile actual room, seat and creature save fragments and test old and resumed saves."""
import re
from check_infirmary_rules import PRELUDE, function, read, room_declaration, run_probe

# Exercise production save bodies and the real resumed-carry constructor with controlled world services.
def main():
    room = read("source/rooms/RoomInfirmaryStreams.cpp")
    code = PRELUDE + room_declaration() + re.sub(r'^#include[^\n]*\n', '', room, flags=re.M)
    shaman = read("source/rooms/RoomInfirmaryShaman.cpp")
    for signature in ("void RoomInfirmary::exportShamanToStream(", "bool RoomInfirmary::importShamanFromStream("):
        code += function(shaman, signature)
    core = read("source/rooms/RoomInfirmary.cpp")
    code += function(core, "void RoomInfirmary::layoutCots(")
    code += function(core, "void RoomInfirmary::restoreInitialEntityState(")
    for signature in ("int RoomInfirmary::cotSize(", "size_t RoomInfirmary::findCot(",
            "bool RoomInfirmary::hasCarryEntitySpot(", "Tile* RoomInfirmary::reserveCot(",
            "Tile* RoomInfirmary::askSpotForCarriedEntity("):
        code += function(core, signature)
    code += function(read("source/rooms/RoomInfirmaryEconomy.cpp"), "bool RoomInfirmary::canPayAdmission(")
    carry = read("source/creatureaction/CreatureActionCarryEntity.cpp")
    code += "\n#define OD_LOG_INF(message) ((void)0)\n"
    code += function(carry, "CreatureActionCarryEntity::CreatureActionCarryEntity(Creature& creature, GameEntity& entityToCarry, Building& buildingDest)")
    code += function(carry, "bool CreatureActionCarryEntity::isPulledOverGround(")
    code += r"""
//! \brief Captures the destination selected by the actual constructor and its actual knockout counter.
void Creature::pushAction(std::unique_ptr<CreatureActionCarryEntity> action){
 ++sleeps;resumedCarryTarget=action->mTileDest;resumedCarryIsDrag=action->mIsDrag;
 resumedCarryCounter=static_cast<Creature*>(action->mEntityToCarry)->getKoTurnCounter();
}
"""
    seat = read("source/game/Seat.cpp")
    creature = read("source/entities/Creature.cpp")
    seat_import = function(seat, '    if(str == "[Infirmary]")')
    seat_save_start = seat.index('    os << "[Infirmary]')
    seat_save = seat[seat_save_start:seat.index(";", seat_save_start)+1]
    creature_import = function(creature, '        if(appearanceToken == "[Infirmary]")')
    creature_save_start = creature.index('    os << "\\t[Infirmary]')
    creature_save = creature[creature_save_start:creature.index(";", creature_save_start)+1]
    threshold = function(read("source/game/SeatData.cpp"), "void SeatData::setInfirmaryThreshold(")
    code += r"""
//! \brief Retains the production optional seat block and threshold validator.
struct SeatData{int32_t mInfirmaryPayer=0,mInfirmaryThreshold=100;bool mInfirmaryHealOn=true;
 //! \brief Returns the payer serialized by the actual seat save fragment.
 int getInfirmaryPayer()const{return mInfirmaryPayer;}
 //! \brief Accepts only the two production admission payer choices.
 void setInfirmaryPayer(int32_t value){if(value==0||value==1)mInfirmaryPayer=value;}
 //! \brief Executes the actual configured discharge-threshold validator.
 void setInfirmaryThreshold(int32_t);
 //! \brief Restores the healing switch used by the actual seat load fragment.
 void setInfirmaryHealOn(bool value){mInfirmaryHealOn=value;}
 //! \brief Writes the extracted production infirmary seat block.
 void save(std::ostream& os)const{SEAT_SAVE}
 //! \brief Reads the production seat block while preserving ownership of the next tag.
 bool load(std::istream& is){std::string str;if(!(is>>str))return false;while(true){SEAT_IMPORT
  if(str=="[Other]"){std::string payload,close;if(!(is>>payload>>close>>str)||close!="[/Other]")return false;continue;}
  return str=="EndSeat";}return true;}
};
//! \brief Retains the production optional creature mood block, including old-save defaults.
struct MoodRecord{double mInfirmaryMood=0,mInfirmaryMoodTurns=0;
 //! \brief Writes the production mood block with enough precision for an exact round-trip.
 void save(std::ostream& os)const{os<<std::setprecision(std::numeric_limits<double>::max_digits10);CREATURE_SAVE}
 //! \brief Reads the production mood block alongside unrelated optional creature tags.
 bool load(std::istream& is){std::string appearanceToken;while(is>>appearanceToken){CREATURE_IMPORT
  if(appearanceToken=="[Other]"){std::string payload,close;if(!(is>>payload>>close)||close!="[/Other]")return false;continue;}
  return appearanceToken=="EndCreature";}return true;}
};
""".replace("SEAT_SAVE",seat_save).replace("SEAT_IMPORT",seat_import).replace("CREATURE_SAVE",creature_save).replace("CREATURE_IMPORT",creature_import)
    code += threshold
    # The production reader must initialize old-save moods before optional trailing tokens.
    assert re.search(r'mInfirmaryMood\s*\(0\.0\)', creature)
    assert re.search(r'mInfirmaryMoodTurns\s*\(0\.0\)', creature)
    assert 'str == "[Infirmary]"' in seat[seat.index("// Optional seat blocks"):seat.index('    if(str == "[Infirmary]")')]
    rebind = function(read("source/rooms/RoomInfirmary.cpp"), "void RoomInfirmary::restoreInitialEntityState(")
    for needle in ("getCreature(patient.creatureName)", "getCreature(patient.reservedByName)", "CreatureActionCarryEntity"):
        assert needle in rebind, needle
    code += r"""
//! \brief Runs room, reservation, seat and creature save compatibility regression cases.
int main(){try{
 // Keep integer countdown regressions and also preserve fractional waiting, dragging and admitted death times.
 for(double remaining:{-47.0,-29.0,-47.25,-29.5})for(double paidCounter:{73.0,73.375}){
 GameMap map;Seat seat;RoomInfirmary original(&map,&seat);
 map.rooms.push_back(&original);
 for(int x=0;x<8;++x)for(int y=0;y<8;++y)map.tiles[{x,y}]={x,y};
 RoomInfirmary::CotInfo small={};small.size=1;small.x=1;small.y=2;small.width=1;small.height=1;
 RoomInfirmary::CotInfo medium=small;medium.size=2;medium.x=3;medium.width=2;medium.rotation=90;
 original.mCots[7]=small;original.mCots[91]=medium;original.mCots[120]=small;original.mCots[120].x=6;
 Creature patient,carrier,originalIncoming;carrier.name="carrier";carrier.owner=&seat;
 originalIncoming.name="incoming";originalIncoming.owner=&seat;originalIncoming.definition.height=2;originalIncoming.counter=-80;
 map.creatures["incoming"]=&originalIncoming;
 RoomInfirmary::PatientInfo admission;admission.creature=&patient;admission.admissionPaid=17.400000000000002;admission.payer=1;admission.storedCounter=paidCounter;admission.manual=false;
 original.mPatients[7]=admission;
 check(original.reserveCot(originalIncoming,carrier)==map.getTile(3,2),"initial reservation uses actual eligibility and cot-size gate");
 original.mPatients.at(91).storedCounter=-80;originalIncoming.counter=remaining;
 InfirmaryShamanEntity figure;figure.position=Ogre::Vector3(2.25,3.75,0);original.mShaman=&figure;
 std::ostringstream saved;saved.precision(6);original.exportToStream(saved);check(saved.precision()==6,"room restores caller precision");
 std::istringstream input(saved.str()+"NextRoom");RoomInfirmary loaded(&map,&seat);
 check(loaded.importFromStream(input),"mid-treatment room load");check(loaded.mCots.size()==3&&loaded.mPatients.size()==2,"cots and patients resumed");
 check(loaded.mPatients.at(0).creatureName=="patient","noncontiguous cot id remapped");
 check(loaded.mPatients.at(1).creatureName=="incoming"&&loaded.mPatients.at(1).reservedByName=="carrier","running reservation names preserved");
 check(loaded.mPatients.at(1).storedCounter==remaining,"reservation saves current signed countdown rather than stale record");
 check(loaded.mPatients.at(0).admissionPaid==admission.admissionPaid,"admission fraction exact");
 check(loaded.mPatients.at(0).payer==1&&loaded.mPatients.at(0).storedCounter==paidCounter&&!loaded.mPatients.at(0).manual,"paid state preserved");
 check(loaded.mCots.at(1).width==2&&loaded.mCots.at(1).height==1&&loaded.mCots.at(1).rotation==90,"rotated cot footprint restored");
 std::string next;input>>next;check(next=="NextRoom","reader leaves next room unread");
 check(loaded.mHasLoadedShamanPosition,"shaman position tag restored");near(loaded.mLoadedShamanPosition.x,2.25,"shaman x");near(loaded.mLoadedShamanPosition.y,3.75,"shaman y");
 Creature incoming;incoming.name="incoming";incoming.owner=&seat;incoming.definition.height=2;incoming.counter=0;
 map.creatures["patient"]=&patient;map.creatures["carrier"]=&carrier;map.creatures["incoming"]=&incoming;
 check(!loaded.hasCarryEntitySpot(&incoming),"freshly loaded zero-countdown creature cannot bypass the production eligibility gate");
 const double savedSeatGold=5000;map.rooms.clear();map.rooms.push_back(&loaded);loaded.gold=savedSeatGold;
 Creature unreserved;unreserved.name="new-patient";unreserved.owner=&seat;
 check(loaded.hasCarryEntitySpot(&unreserved),"new patient has a free matching cot before the treasury load-order case");
 // Entity creation resumes carries before the saved keeper balance is redistributed into room tiles.
 loaded.gold=0;map.treasury=0;
 const std::map<size_t,RoomInfirmary::CotInfo> cotSnapshot=loaded.mCots;
 loaded.updateActiveSpots();loaded.restoreInitialEntityState();
 check(loaded.mCots.size()==cotSnapshot.size(),"initial entity restoration retains occupied, reserved and empty saved cots");
 for(const std::pair<const size_t,RoomInfirmary::CotInfo>& entry:cotSnapshot){check(loaded.mCots.count(entry.first),"saved cot identity retained");const RoomInfirmary::CotInfo& actual=loaded.mCots.at(entry.first);check(actual.x==entry.second.x&&actual.y==entry.second.y&&actual.rotation==entry.second.rotation,"saved cot placement retained");}
 check(loaded.mPatients.at(0).creature==&patient&&loaded.mPatients.at(1).reservedBy==&carrier,"actual restore rebinds treatment and reservation");
 check(incoming.counter==remaining&&carrier.resumedCarryCounter==remaining,"exact saved countdown restored before the real carry constructor");
 check(carrier.resumedCarryTarget==map.getTile(3,2)&&carrier.resumedCarryIsDrag,"actual constructor resumes dragging to the original reserved cot");
 check(loaded.askSpotForCarriedEntity(&incoming)==carrier.resumedCarryTarget,"resumed reservation remains owned by its incoming creature");
 check(!loaded.canPayAdmission(incoming,false),"existing reservation resumes before physical treasury refill");
 check(!loaded.hasCarryEntitySpot(&unreserved)&&loaded.reserveCot(unreserved,carrier)==nullptr,"new unreserved admission still requires physical treasury funds");
 loaded.gold=savedSeatGold;map.treasury=savedSeatGold;
 check(loaded.hasCarryEntitySpot(&unreserved),"new admissions become eligible only after saved treasury funds are redistributed");
 std::ostringstream again;loaded.exportToStream(again);check(again.str()==saved.str(),"complete room restoration round-trip lossless");
 std::istringstream old("NextRoom");RoomInfirmary oldRoom(&map,&seat);check(oldRoom.importFromStream(old)&&oldRoom.mCots.empty()&&oldRoom.mPatients.empty(),"old room without tags loads");old>>next;check(next=="NextRoom","old reader retains next token");
 std::istringstream reordered("InfirmaryPatients 1 0 patient none 17.4 0 51 1 InfirmaryShaman 1.5 2.5 InfirmaryCots 1 1 2 2 0 NextRoom");
 RoomInfirmary mixed(&map,&seat);check(mixed.importFromStream(reordered)&&mixed.mPatients.at(0).manual&&mixed.mPatients.at(0).storedCounter==51,"optional room tags in any order");
 for(const char* invalid:{"InfirmaryCots 1 4 0 0 0","InfirmaryCots 1 1 99 99 0","InfirmaryPatients 1 0 patient"}){
  std::istringstream bad(invalid);RoomInfirmary room(&map,&seat);check(!room.importFromStream(bad),"malformed room state rejected");}
 SeatData settings;settings.mInfirmaryPayer=1;settings.mInfirmaryThreshold=70;settings.mInfirmaryHealOn=false;
 std::ostringstream settingsText;settings.save(settingsText);
 for(const std::string& text:{settingsText.str()+" [Other] payload [/Other] EndSeat",std::string("[Other] payload [/Other] ")+settingsText.str()+" EndSeat"}){
  SeatData copy;std::istringstream stream(text);check(copy.load(stream)&&copy.mInfirmaryPayer==1&&copy.mInfirmaryThreshold==70&&!copy.mInfirmaryHealOn,"seat settings round-trip amid optional blocks");}
 SeatData oldSettings;std::istringstream oldSeat("EndSeat");check(oldSettings.load(oldSeat)&&oldSettings.mInfirmaryPayer==0&&oldSettings.mInfirmaryThreshold==100&&oldSettings.mInfirmaryHealOn,"old seat defaults");
 for(int threshold=40;threshold<=100;threshold+=10){settings.setInfirmaryThreshold(threshold);check(settings.mInfirmaryThreshold==threshold,"valid threshold accepted");}
 for(int threshold:{-1,0,39,41,55,99,101}){settings.setInfirmaryThreshold(threshold);check(settings.mInfirmaryThreshold==100,"invalid threshold refused");}
 MoodRecord mood;mood.mInfirmaryMood=-36.123456789012345;mood.mInfirmaryMoodTurns=12.5;std::ostringstream moodText;mood.save(moodText);
 for(const std::string& text:{moodText.str()+" [Other] payload [/Other] EndCreature",std::string("[Other] payload [/Other] ")+moodText.str()+" EndCreature"}){
  MoodRecord copy;std::istringstream stream(text);check(copy.load(stream)&&copy.mInfirmaryMood==mood.mInfirmaryMood&&copy.mInfirmaryMoodTurns==12.5,"creature mood exact round-trip amid optional tags");}
 MoodRecord oldMood;std::istringstream oldCreature("EndCreature");check(oldMood.load(oldCreature)&&oldMood.mInfirmaryMood==0&&oldMood.mInfirmaryMoodTurns==0,"old creature defaults");
 }
 std::cout<<"infirmary streams: ok\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
"""
    run_probe("infirmary-streams", code)

if __name__ == "__main__":
    main()
