"""Compile production progress, packet and clock methods; never launch a game."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
prefix = Path(os.environ['CMAKE_PREFIX_PATH'])


def function(path, signature):
    text = (root / path).read_text()
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


creature = 'source/entities/Creature.cpp'
methods = '\n'.join(function(creature, sig) for sig in (
    'double Creature::getExperienceProgress()', 'void Creature::exportProgressToPacket(',
    'void Creature::importProgressFromPacket(', 'void Creature::receiveExp(',
    'void Creature::recordWorkerStepRecovery('))
clock = function('source/render/CreatureOverlayStatus.cpp', 'void CreatureOverlayStatus::updateProgress(')
source = (root / creature).read_text()
for sig in ('void Creature::exportToPacket(', 'void Creature::exportToPacketForUpdate('):
    assert 'exportProgressToPacket(os, seat);' in function(creature, sig)
for sig in ('void Creature::importFromPacket(', 'void Creature::updateFromPacket('):
    assert 'importProgressFromPacket(is);' in function(creature, sig)
assert 'mAttackRecoveryTurns = std::max(0.0, mAttackRecoveryTurns - 1.0);' in source
overlay_source = (root / 'source/render/CreatureOverlayStatus.cpp').read_text().replace('\r\n', '\n')
# Mana ring layers: backing disc and frame from the health picture set, arc from the plain progress atlas, no spokes
assert 'MANA_RING_BACKING_MATERIAL = "CreatureOverlay7"' in overlay_source
assert 'MANA_RING_BASE_MATERIAL = "CreatureExperience"' in overlay_source
assert 'rrBuildTintedMaterial(\n        MANA_RING_BACKING_MATERIAL, mSeat->getColorValue())' in overlay_source
assert '"CreatureOverlay0"' not in overlay_source.split('CreatureOverlayStatus::CreatureOverlayStatus(')[1]
assert 'mAttackRecoveryDuration = std::max(static_cast<double>(skillData.mWarmup), skillData.mCooldown)' in source
server = (root / 'source/network/ODServer.cpp').read_text()
assert server.count('packetSend << clientSocket->supportsCreatureProgress();') == 1
assert server.count('packetSend << client->supportsCreatureProgress();') == 1
client = (root / 'source/network/ODClient.cpp').read_text()
assert 'if(!packetReceived.endOfPacket())\n                OD_ASSERT_TRUE(packetReceived >> creatureProgress);' in client
assert 'mSupportsCreatureProgress = false;' in (root / 'source/network/ODSocketClient.cpp').read_text()

probe = r'''
#include "network/ODPacket.h"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <limits>
#include <string>
#include <vector>
#define OD_LOG_ERR(x) ((void)0)
#define OD_ASSERT_TRUE(x) do { if(!(x)) return; } while(0)
constexpr unsigned MAX_LEVEL = 30;
struct Player {};
struct Seat {Player player; Player* getPlayer() const {return const_cast<Player*>(&player);}};
struct ODServer {bool enabled=true;static ODServer& getSingleton(){static ODServer s;return s;}bool supportsCreatureProgress(Player*){return enabled;}};
struct ODClient {bool enabled=true;static ODClient& getSingleton(){static ODClient s;return s;}bool supportsCreatureProgress(){return enabled;}};
struct Definition {double needed=100;double getXPNeededWhenLevel(unsigned)const{return needed;}bool isWorker()const{return false;}};
struct GameMap {double getGameSpeedFactor()const{return 1.0;}};
//! \brief Minimal action identifiers used by the production packet selector.
enum class CreatureActionType {nb, useRoom, crackBox, harvestHerbs, brewPotion};
//! \brief Runs the production room-work selector for all work actions.
struct CreatureAction {static bool isRoomWorkAction(CreatureActionType actionType);};
ACTION_SELECTOR
//! \brief Minimal current-action snapshot for the production packet selector.
struct CreatureActivity {CreatureActionType action=CreatureActionType::nb;};
//! \brief Holds only the fields required by extracted production progress methods.
struct Creature {
 GameMap map;GameMap* getGameMap()const{return const_cast<GameMap*>(&map);}
 bool server=true,mHasProgressInformation=false,mNeedFireRefresh=false;unsigned mLevel=1;
 double mExp=0,mExperienceProgress=0;Definition def;Definition* mDefinition=&def;
 double mAttackRecoveryTurns=0,mAttackRecoveryDuration=0;uint32_t mAttackRecoverySerial=0;
 int mJobCooldown=0;uint32_t mJobCooldownDuration=0;bool working=false;
 //! \brief Reports the mocked current activity for the production progress packet.
 CreatureActivity getActivity() const {CreatureActivity activity;if(working)activity.action=CreatureActionType::useRoom;return activity;}

 //! \brief Supplies a controlled Trainer value to the actual experience formula.
 double trainer=0;
 //! \brief Returns the controlled Trainer effect for the actual experience formula.
 double getItemEffect(const std::string& name)const{return name=="Trainer"?trainer:0;}
 bool getIsOnServerMap()const{return server;}std::string getName()const{return "probe";}
 //! \brief Records the real one-turn interval using the production method below.
 void recordWorkerStepRecovery();
 double getExperienceProgress()const;void receiveExp(double);
 void exportProgressToPacket(ODPacket&,const Seat*)const;void importProgressFromPacket(ODPacket&);
 bool hasProgressInformation()const{return mHasProgressInformation;}
 double getAttackRecoveryTurns()const{return mAttackRecoveryTurns;}
 double getAttackRecoveryDuration()const{return mAttackRecoveryDuration;}
 uint32_t getAttackRecoverySerial()const{return mAttackRecoverySerial;}
 Definition* getDefinition()const{return mDefinition;}
 //! \brief Mocked mana pool of the creature, shown by the mana ring.
 static constexpr uint32_t MANA_RING_STEPS=63;double mMana=0,mMaxMana=0;
 double getMaxMana()const{return mMaxMana;}double getCurrentMana()const{return mMana;}
};
METHODS
namespace Ogre {using Real=float;}
struct ODApplication {static double turnsPerSecond;};double ODApplication::turnsPerSecond=1.4;
//! \brief Inactive level test, as in a normal game.
struct RunLevelTest {static bool isActive(){return false;}static void onRecoveryFrame(bool,uint32_t){}};
enum class CreatureOverlays {health,experience,recovery,status,mana};
const uint32_t PROGRESS_ATLAS_COLUMNS=8;
const uint32_t PROGRESS_ATLAS_LAST_FRAME=PROGRESS_ATLAS_COLUMNS*PROGRESS_ATLAS_COLUMNS-1;
struct MovableTextOverlay {
 unsigned frames[5]={};bool shown[5]={};
 void displayOverlay(uint32_t id,int t){shown[id]=t!=0;}
 void setAtlasFrame(uint32_t id,uint32_t frame,uint32_t cols){if(cols!=8||frame>63)throw 1;frames[id]=frame;}
};
struct CreatureOverlayStatus {
 Creature* mCreature;MovableTextOverlay* mMovableTextOverlay;std::vector<uint32_t> mOverlayIds{0,1,2,3,4};
 double mRecoveryTurns=0;uint32_t mRecoverySerial=0;float mRecoveryElapsed=0;
 void updateProgress(float);
};
CLOCK
//! \brief Checks progress packets and the unchanged clock for attacks, room pauses and worker steps.
int main(){int checks=0,failures=0;auto check=[&](bool ok,const char* why){++checks;if(!ok){++failures;std::cerr<<"FAIL "<<why<<'\n';}};
 Seat seat;Creature a,b;b.server=false;
 for(unsigned level=1;level<=30;++level)for(double xp:{0.,25.,100.,150.}){
  a.mLevel=level;a.mExp=xp;a.mAttackRecoveryDuration=8;a.mAttackRecoveryTurns=5;a.mAttackRecoverySerial=42;
  ODPacket packet;a.exportProgressToPacket(packet,&seat);packet<<uint32_t(0x12345678);b.importProgressFromPacket(packet);
  check(b.mHasProgressInformation&&b.getExperienceProgress()==(level==30?1.:std::min(1.,xp/100.)),"experience round trip and cap");
  check(b.mAttackRecoveryTurns==5&&b.mAttackRecoveryDuration==8&&b.mAttackRecoverySerial==42,"recovery round trip");
  uint32_t sentinel=0;packet>>sentinel;check(sentinel==0x12345678&&packet.endOfPacket(),"concatenated payload remains aligned");
 }
 ODServer::getSingleton().enabled=false;ODPacket legacy;a.exportProgressToPacket(legacy,&seat);legacy<<uint32_t(27);
 ODClient::getSingleton().enabled=false;b.importProgressFromPacket(legacy);uint32_t sentinel=0;legacy>>sentinel;
 check(!b.mHasProgressInformation&&sentinel==27,"old client/server payload untouched");
 ODClient::getSingleton().enabled=true;ODServer::getSingleton().enabled=true;
 for(double invalid:{-.1,1.1,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()}){
  ODPacket packet;packet<<invalid<<0.0<<0.0<<uint32_t(0);b.importProgressFromPacket(packet);check(!b.mHasProgressInformation,"invalid XP rejected");
 }
 ODPacket bad;bad<<.5<<8.0<<2.0<<uint32_t(1);b.importProgressFromPacket(bad);check(!b.mHasProgressInformation,"invalid recovery rejected");
 ODPacket shortPacket;shortPacket<<.5;b.importProgressFromPacket(shortPacket);check(!b.mHasProgressInformation,"truncated payload rejected");
 a.mLevel=1;a.mExp=0;a.receiveExp(-1);check(a.mExp==0,"negative gain rejected");a.receiveExp(20);check(a.mExp==20&&a.mNeedFireRefresh,"XP changes schedule replication");
 a.trainer=25;a.mExp=0;a.receiveExp(20);check(a.mExp==25,"Trainer multiplies earned experience without rounding");a.trainer=0;
 a.working=true;a.mAttackRecoveryTurns=0;a.mAttackRecoveryDuration=0;a.mAttackRecoverySerial=101;
 for(unsigned remaining:{5u,4u,1u,0u}){
  a.mJobCooldown=remaining;a.mJobCooldownDuration=5;
  ODPacket packet;a.exportProgressToPacket(packet,&seat);packet<<uint32_t(0x76543210);b.importProgressFromPacket(packet);
  check(b.mAttackRecoveryTurns==remaining&&b.mAttackRecoveryDuration==(remaining?5u:0u),"actual job pause round trip and end");
  uint32_t tail=0;packet>>tail;check(tail==0x76543210&&packet.endOfPacket(),"job display keeps existing packet alignment");
 }
 a.working=false;a.mJobCooldown=4;a.mJobCooldownDuration=5;
 ODPacket interrupted;a.exportProgressToPacket(interrupted,&seat);b.importProgressFromPacket(interrupted);
 check(b.mAttackRecoveryTurns==0,"interrupted work does not display an unrelated old job pause");
 MovableTextOverlay overlay;CreatureOverlayStatus status{&b,&overlay};b.mHasProgressInformation=true;b.mExperienceProgress=.5;b.mAttackRecoveryDuration=4;b.mAttackRecoveryTurns=4;b.mAttackRecoverySerial=1;
 status.updateProgress(0);check(overlay.frames[1]==31&&overlay.frames[2]==1,"half XP and fresh attack");
 status.updateProgress(.35f);check(overlay.frames[2]>1,"recovery sweeps between turns");auto frozen=overlay.frames[2];
 for(int i=0;i<100;++i)status.updateProgress(0);check(overlay.frames[2]==frozen,"pause freezes clock");
 status.updateProgress(1000);check(overlay.frames[2]<17,"missing server tick cannot fake readiness");
 b.mAttackRecoveryTurns=1;status.updateProgress(0);check(overlay.frames[2]==47,"server corrects recovery");
 b.mAttackRecoveryTurns=0;status.updateProgress(0);check(overlay.frames[2]==0,"ready hides clock");
 a.mAttackRecoveryDuration=2.35;a.mAttackRecoveryTurns=0.35;ODPacket fractional;a.exportProgressToPacket(fractional,&seat);b.importProgressFromPacket(fractional);
 check(b.mAttackRecoveryTurns==0.35&&b.mAttackRecoveryDuration==2.35,"fractional recovery round trip");
 b.mAttackRecoveryDuration=2.35;b.mAttackRecoveryTurns=0.35;++b.mAttackRecoverySerial;status.updateProgress(0);status.updateProgress(1000);
 check(overlay.frames[2]>0&&overlay.frames[2]<=63,"fractional remainder keeps the clock inside the ring");b.mAttackRecoveryDuration=4;
 b.mAttackRecoveryTurns=4;++b.mAttackRecoverySerial;status.updateProgress(0);check(overlay.frames[2]==1,"repeated attack resets clock");
 a.working=false;a.mAttackRecoverySerial=150;
 for(unsigned step=1;step<=3;++step){
  a.mNeedFireRefresh=false;a.recordWorkerStepRecovery();
  ODPacket packet;a.exportProgressToPacket(packet,&seat);b.importProgressFromPacket(packet);
  check(b.mAttackRecoveryTurns==1&&b.mAttackRecoveryDuration==1&&b.mAttackRecoverySerial==150+step&&a.mNeedFireRefresh,"worker step reports actual upkeep interval");
  status.updateProgress(0);check(overlay.frames[2]==1,"each worker step restarts the existing ring");
  status.updateProgress(.35f);check(overlay.frames[2]>1&&overlay.frames[2]<63,"worker interval sweeps within the server turn");
  unsigned paused=overlay.frames[2];status.updateProgress(0);check(overlay.frames[2]==paused,"worker recovery freezes while paused");
 }
 b.mMaxMana=40;for(double mana:{0.,20.,40.,60.,-5.}){b.mMana=mana;status.updateProgress(0);
  check(overlay.frames[4]==(mana<=0?0u:mana>=40?63u:unsigned(mana/40*63)),"mana ring follows current mana, clamped to the ring");}
 b.mMaxMana=0;b.mMana=10;status.updateProgress(0);check(overlay.frames[4]==0,"no mana pool shows an empty ring");
 b.mHasProgressInformation=false;status.updateProgress(0);check(!overlay.shown[1]&&overlay.frames[2]==0,"legacy replay does not invent progress");
 std::cout<<"CHECKS="<<checks<<" FAILURES="<<failures<<'\n';return failures?1:0;
}
'''.replace('ACTION_SELECTOR', function('source/creatureaction/CreatureAction.cpp', 'bool CreatureAction::isRoomWorkAction(')).replace('METHODS', methods).replace('CLOCK', clock)
with tempfile.TemporaryDirectory(prefix='odp-progress-') as directory:
    work = Path(directory)
    (work / 'probe.cpp').write_text(probe)
    subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++17', f'/I{root / "source"}',
                    f'/I{prefix / "include"}', f'/I{prefix / "include/OGRE"}', 'probe.cpp',
                    str(root / 'source/network/ODPacket.cpp'), '/Feprobe.exe', '/link',
                    f'/LIBPATH:{prefix / "lib"}', 'sfml-network.lib', 'sfml-system.lib', 'OgreMain.lib'], cwd=work, check=True)
    subprocess.run([str(work / 'probe.exe')], cwd=work, check=True)
