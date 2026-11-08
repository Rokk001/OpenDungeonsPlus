"""Trap delivery point and 20 s transfer check (decision 845 item 5). Compiles nothing.

The ghost cauldron has a delivery point for ghost traps, the trap socket over the middle of its mouth
(RoomGhostRoom::getTrapSocketPosition, 1.574 above the floor = the top of the socket glow of models/GhostCauldron.mesh).
A hunter at its cauldron sets the trap into the socket: the ghost is teleported there and flows visibly into the
cauldron for GhostTransferSeconds (20, config/rooms.cfg with its doc line), the same for every hunter; it replaces the
GhostEmptyTurns emptying and its one-second Empty clip. Hunter efficiency no longer shortens it; the room's CatchTime
research (which shortened the emptying) now shortens the transfer of a researched keeper (16 s, 13.3 s). The phase clock mTurns is
saved, so a loaded game resumes the remaining time. The client shows the open, shining trap on the socket and the ghost
rising out of it, spiralling down and sinking into the ectoplasm for the whole 20 s (a model of GhostEntity::updateLook
runs over the full transfer). No other clip or capture duration changes (fixed config values).
Owner decision 865 moves the delivery point: no longer the socket over the middle of the cauldron's top, but a delivery
device on the cauldron's rim directly beside the hunter, within reach of his hand (RoomGhostRoom::getTrapSocketPosition
for the anchor and the standing tile: GhostDeliveryHandReach 0.55 from the middle of his tile towards the cauldron, its
top at GhostDeliveryHeight 1.1). The hunter takes the shut trap in his hand and puts it in with a visible put-in motion
(once, the one-second Empty clip; the client moves the trap from his hand into the device over GhostPutInSeconds while
the device swings out from the rim), the trap stays shut, then the ghost rises out of the device, glides over the rim
and spirals down into the mouth. The transfer keeps 20/16/13.3 s by the CatchTime research only, the put-in included.
These parts fail on base 6c97ae45c (socket over the middle of the mouth at 1.574, the open trap standing in it, the
Empty clip looping for the whole transfer).
Owner decision 894 replaces the dynamic device beside the hunter by the permanent trap seat of the rebuilt cauldron
(models/GhostCauldron.mesh, bone DeliverySocket): RoomGhostRoom::getTrapSocketPosition(anchor) is the middle of the 2x2
block plus the offset (0.5, 0.82, 1.1); the hunter stands on RoomGhostRoom::getTrapStandingTile, the tile on the +Y side
0.68 from the seat, and faces -Y; reserveCauldron sends him to that one tile. No device, hinge or arm is built any more.
"""
from pathlib import Path
import math
import re
import struct

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


def body(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def has(text, rule, *fragments):
    for fragment in fragments:
        assert fragment in text, (rule, fragment)


# 1. The config key with its doc line; the other durations stay as they were (fixed values)
rooms = read('config/rooms.cfg')
match = re.search(r'^(#[^\n]*\n)+GhostTransferSeconds 20\s*$', rooms, re.M)
assert match and 'delivery point' in match.group(0) and 'decision 845' in match.group(0), 'GhostTransferSeconds 20 with doc line'
values = dict(re.findall(r'^(Ghost\w+)\s+([-\d.]+)\s*$', rooms, re.M))
fixed = {'GhostBoxThrowSeconds': '2', 'GhostBeamSeconds': '16', 'GhostBoxSnapSeconds': '2', 'GhostRiseSeconds': '1.5',
         'GhostDissolveSeconds': '1.5', 'GhostTransferSeconds': '20'}
for key, value in fixed.items():
    assert values.get(key) == value, (key, values.get(key), value)
transfer_seconds = float(values['GhostTransferSeconds'])
lid_open = float(values['GhostLidOpenSeconds'])
# Decision 894: the put-in under a two-line documentation; the hand reach and height of the old device are gone
rows = rooms.splitlines()
assert values.get('GhostPutInSeconds') == '1'
assert 'GhostDeliveryHandReach' not in values and 'GhostDeliveryHeight' not in values, 'the old device keys are gone'
put_in_row = next(i for i, row in enumerate(rows) if row.split()[:1] == ['GhostPutInSeconds'])
put_in_doc = ' '.join(rows[put_in_row - 2:put_in_row])
assert all(row.startswith('#') for row in rows[put_in_row - 2:put_in_row]), 'two documentation lines over GhostPutInSeconds'
assert all(word in put_in_doc for word in ('put-in', 'Empty clip', 'shut', 'trap seat')), 'the put-in doc lines describe the motion'
put_in = float(values['GhostPutInSeconds'])

# 2. The server: fixed duration, teleport into the socket, saved clock
action = read('source/creatureaction/CreatureActionHuntGhost.cpp')
header = read('source/creatureaction/CreatureActionHuntGhost.h')
has(body(action, 'double CreatureActionHuntGhost::getTransferTurns() const'), '20 s for every hunter, the research shortens it',
    'return researched("GhostTransferSeconds","CatchTime")*ODApplication::turnsPerSecond;')
assert 'getEfficiency' not in body(action, 'double CreatureActionHuntGhost::getTransferTurns() const')
has(read('source/game/SkillManager.cpp'), 'research base: the transfer and the beam (decisions 855, 857)',
    '{SkillType::roomGhostRoom, "CatchTime", ResearchBaseSource::rooms, "GhostTransferSeconds", "GhostBeamSeconds"}')
# The hunter efficiency shortens only the beam (getBeamSeconds), never the transfer
assert 'getBeamSeconds' not in body(action, 'double CreatureActionHuntGhost::getTransferTurns() const')
assert 'GhostEmptyTurns' not in values, 'replaced by GhostTransferSeconds'
state6 = action[action.index('    if(mState==6)\n'):action.index('    if(mState==7)\n')]
has(state6, 'transfer at the delivery point', 'const Ogre::Vector3 socket=RoomGhostRoom::getTrapSocketPosition(*mEmptyAnchor);',
    'if(poured!=nullptr && poured->getPosition()!=socket) poured->teleport(socket);', 'const double duration=getTransferTurns();',
    'while(!mGhosts.empty() && mTurns>=duration)', 'if(ghost!=nullptr) empty->emptyGhost(mCreature,*ghost);',
    'if(mEmptyAnchor==nullptr) { interrupt();return false; }')
for removed in ('GhostEmptyTurns', 'getEfficiency'):
    assert removed not in state6, ('the old emptying is replaced', removed)
# Decision 865: the put-in motion plays once on arrival (the Empty clip, not looped), facing the device
has(state6, 'the put-in motion once', 'if(!mPutIn) { mCreature.setAnimationState(EntityAnimation::empty_anim,false,facing(mCreature,socket),true);mPutIn=true; }')
assert state6.index('getTrapSocketPosition') < state6.index('if(!mPutIn)') < state6.index('const double duration=getTransferTurns();')
assert 'empty_anim,true' not in action, 'the Empty clip no longer loops for the whole transfer'
assert action.count('EntityAnimation::empty_anim') == 1, 'the put-in is the only Empty clip of the hunt'
has(header, 'the put-in flag', 'bool mPutIn = false;')
restore = body(action, 'void CreatureActionHuntGhost::restore()')
has(restore, 'a loaded delivery past its put-in does not repeat it', 'if(mState==6 && isTransferring() &&',
    'mTurns>=ConfigManager::getSingleton().getRoomConfigDouble("GhostPutInSeconds")*ODApplication::turnsPerSecond)',
    'mPutIn=true;', 'mCreature.setAnimationState(EntityAnimation::idle_anim,true,Ogre::Vector3::ZERO,false);')
export = body(action, 'void CreatureActionHuntGhost::exportToStream(')
assert "<< mState << ' ' << (mTarget.empty()?\"none\":mTarget) << ' '" in export and "<< mTurns <<" in export, 'clock saved'
has(body(action, 'bool CreatureActionHuntGhost::isTransferring() const'), 'at the cauldron',
    'mState==6 && !mGhosts.empty() && mDestination!=nullptr', '!mCreature.isMoving() && mCreature.getPositionTile()==mDestination')
has(body(action, 'uint32_t CreatureActionHuntGhost::getBoxVisualState() const'), 'visual state 5', 'if(isTransferring()) return 5u;')
has(body(action, 'std::string CreatureActionHuntGhost::getThrowGhostName() const'), 'transferred ghost',
    'if(isTransferring()) return mGhosts.front();')
has(header, 'declarations', 'uint32_t getBoxVisualState() const;', 'double getTransferTurns() const;', 'bool isTransferring() const;')

# 3. Decision 894: the delivery point is the permanent trap seat of the cauldron, offset (0.5, 0.82, 1.1) from its middle
room = read('source/rooms/RoomGhostRoom.cpp')
socket_body = body(room, 'Ogre::Vector3 RoomGhostRoom::getTrapSocketPosition(const Tile& anchor)')
has(socket_body, 'the exact offset of the seat',
    'return Ogre::Vector3(static_cast<float>(anchor.getX())+0.5f+TRAP_SOCKET_OFFSET_X,',
    'static_cast<float>(anchor.getY())+0.5f+TRAP_SOCKET_OFFSET_Y,TRAP_SOCKET_OFFSET_Z);')
has(room, 'the measured offset', 'static const float TRAP_SOCKET_OFFSET_X=0.5f;', 'static const float TRAP_SOCKET_OFFSET_Y=0.82f;',
    'static const float TRAP_SOCKET_OFFSET_Z=1.1f;')
for old in ('TRAP_SOCKET_HEIGHT', '1.574', 'GhostDeliveryHandReach', 'GhostDeliveryHeight', 'standing.getX()'):
    assert old not in room, ('no socket over the middle of the mouth, no device beside the hunter', old)
standing_body = body(room, 'Tile* RoomGhostRoom::getTrapStandingTile(GameMap& map, const Tile& anchor)')
has(standing_body, 'the +Y side of the block', 'return map.getTile(anchor.getX()+1,anchor.getY()+2);')
reserve = body(room, 'Tile* RoomGhostRoom::reserveCauldron(Creature& hunter)')
has(reserve, 'the hunter walks to the one place beside the seat', 'Tile* best=getTrapStandingTile(*getGameMap(),*cauldron.anchor);')
assert 'for(int y=-1;y<=2;++y)' not in reserve, 'no choice of any ring tile any more'
has(read('source/rooms/RoomGhostRoom.h'), 'declarations', 'static Ogre::Vector3 getTrapSocketPosition(const Tile& anchor);',
    'static Tile* getTrapStandingTile(GameMap& map, const Tile& anchor);',
    'static Ogre::Vector3 getCauldronMouthPosition(const Ogre::Vector3& cauldron);', 'static float getCauldronRimRadius();')
# Measured once on the export of models/GhostCauldron.mesh (rim and top of the pot, ectoplasm top of the state file)
has(body(room, 'Ogre::Vector3 RoomGhostRoom::getCauldronMouthPosition('), 'mouth on the mesh', 'static const float ECTOPLASM_SURFACE_HEIGHT=1.049f;')
has(body(room, 'float RoomGhostRoom::getCauldronRimRadius()'), 'rim on the mesh', 'static const float RIM_RADIUS=0.68f;')
rim_radius, rim_top, surface_height = 0.68, 1.14, 1.049
seat_offset = (0.5, 0.82, 1.1)


# Model of getTrapSocketPosition and getTrapStandingTile for the block with its anchor in (0, 0); the middle of the block is (0.5, 0.5)
def device_for(anchor_x, anchor_y):
    return anchor_x + 0.5 + seat_offset[0], anchor_y + 0.5 + seat_offset[1], seat_offset[2]


stand = (1, 2)
hand_reach = math.hypot(device_for(0, 0)[0] - stand[0], device_for(0, 0)[1] - stand[1])
assert abs(hand_reach - 0.68) < 1e-9, hand_reach
assert abs(device_for(0, 0)[0] - stand[0]) < 1e-9 and device_for(0, 0)[1] < stand[1], 'the hunter faces -Y towards the seat'
assert 0 < hand_reach <= 0.7, 'the hand reaches the seat without a step'
dx, dy, dz = device_for(0, 0)
assert math.hypot(dx - 0.5, dy - 0.5) > rim_radius, 'the seat lies on the rim neck, outside the rolled rim, not over the mouth'
assert dz <= rim_top and dz >= 1.0, dz
assert stand not in [(x, y) for x in range(2) for y in range(2)], 'the standing tile lies outside the block'
has(body(room, 'void RoomGhostRoom::createCauldronObjects()'), 'cauldron centred on its block', 'tile->getX()+0.5f,tile->getY()+0.5f,0.0f,0.0f,false);')
assets = read('source/tests/check_ghost_assets.py')
has(assets, 'the seat marker of the export is checked there', 'zip(offset,(.5,.82,1.1))')
mesh = (repo / 'models/GhostCauldron.mesh').read_bytes()
assert b'GhostEctoplasm\n' in mesh

# 4. The client: the share is sent, the trap stands open and shines on the socket, the ghost gets the share
creature = read('source/entities/Creature.cpp')
refresh = body(creature, 'void Creature::refreshGhostHuntVisuals()')
has(refresh, 'transferred share sent', 'else if(boxMode==5)', 'const double transfer=hunt->getTransferTurns();',
    'turns=transfer>0.0?std::min(1.0,turns/transfer):1.0;', 'const double transfer=hunt->getTransferTurns();', '(boxMode==1 || boxMode==3 || boxMode==4 || boxMode==5) && turns!=mGhostThrowTurns')
visuals = body(creature, 'void Creature::updateGhostHuntVisuals(double seconds)')
has(visuals, 'the shut trap put into the device beside the hunter',
    'const bool lyingBox=mGhostBoxMode==1 || mGhostBoxMode==3 || mGhostBoxMode==4 || mGhostBoxMode==5 || mGhostBoxMode==6;',
    'ghost->setTransferProgress(mGhostBoxMode==5?mGhostTransferShown:0.0);', 'mGhostHeldBox->setVisible(mGhostBoxMode==2);')
delivery = visuals[visuals.index('else if(mGhostBoxMode==5)'):visuals.index('else if(mGhostBoxMode==6)')]
ordered_parts = ('const Ogre::Vector3 seat=ghost->getPosition();',
    'const double putIn=config.getRoomConfigDouble("GhostPutInSeconds");',
    'const double transferSeconds=SkillManager::getResearchValue(getSeat(),SkillType::roomGhostRoom,',
    'config.getRoomConfigDouble("GhostTransferSeconds"),"CatchTime");',
    'mGhostDeliveryClock=mGhostThrowTurns*transferSeconds>=putIn?putIn:0.0;',
    'mGhostDeliveryMouth=ghostCauldronMouthNear(*getGameMap(),seat);',
    'else mGhostDeliveryClock+=seconds*getGameMap()->getGameSpeedFactor();',
    'const float inserted=static_cast<float>(putIn>0.0?std::max(0.0,std::min(1.0,mGhostDeliveryClock/putIn)):1.0);',
    'position=hand+(seat-hand)*inserted;',
    'share=std::max(0.0,(mGhostThrowTurns*transferSeconds-putIn)/(transferSeconds-putIn));',
    'if(inserted<1.0f) share=0.0;',
    'mGhostTransferShown+=(share-mGhostTransferShown)*std::min(1.0,seconds*6.0);',
    'mGhostLidShown=0.0;', 'trapLight=inserted>=1.0f?1.0:0.0;', 'ghost->setTransferTarget(mGhostDeliveryMouth);')
position = -1
for part in ordered_parts:
    found = delivery.find(part, position + 1)
    assert found > position, ('put-in, then the flow, the trap stays shut', part)
    position = found
for removed in ('Hinge', 'buildGhostDeliveryDevice', 'swing', 'GHOST_DEVICE', 'yaw'):
    assert removed not in delivery, ('no device is built or swung any more', removed)
for removed in ('lidTarget', 'poured', 'GhostLidOpenSeconds'):
    assert removed not in delivery, ('the trap no longer opens in the device', removed)
for removed in ('destroyGhostDelivery', 'buildGhostDeliveryDevice', 'addGhostDeviceBox', 'mGhostDeliveryHinge', 'mGhostDeliveryNode', 'mGhostDeliveryDevice'):
    assert removed not in creature and removed not in read('source/entities/Creature.h'), ('the dynamic device is removed', removed)
mouth_body = body(creature, 'static Ogre::Vector3 ghostCauldronMouthNear(')
has(mouth_body, 'the ghost flows into the nearest cauldron', 'entity->getMeshName()!="GhostCauldron"',
    'RoomGhostRoom::getCauldronMouthPosition(best->getPosition())')
has(body(creature, 'void Creature::clearGhostHuntVisuals()'), 'reset', 'ghost->setTransferProgress(0.0);', 'mGhostTransferShown=0.0;',
    'mGhostDeliveryGhost.clear();mGhostDeliveryClock=0.0;')
ghost = read('source/entities/GhostEntity.cpp')
look = body(ghost, 'void GhostEntity::updateLook()')
has(look, 'transfer look', 'if(mState == GhostState::boxed && transfer > 0.0)', 'const double rise = std::min(1.0, transfer / 0.1);',
    'const Ogre::Vector3 mouth = mHasTransferTarget ? mTransferTarget : mPosition;',
    'const double spiral = std::max(0.0, std::min(1.0, (transfer - 0.1) / 0.8));',
    'const double fade = std::max(0.0, std::min(1.0, (transfer - 0.9) / 0.1));',
    'const double glide = std::min(1.0, spiral / 0.25);',
    'const double angle = spiral * 5.0 * 2.0 * Ogre::Math::PI;',
    'const double radius = 0.42 * std::sin(spiral * Ogre::Math::PI) + 0.1 * (1.0 - spiral);',
    'static const double TRANSFER_RISE = 0.45;', 'const double top = std::max(mPosition.z, mouth.z) + TRANSFER_RISE;',
    'const double lift = mPosition.z + (top - mPosition.z) * rise - (top - mouth.z) * spiral - 0.2 * fade;',
    'const double centreX = mPosition.x + (mouth.x - mPosition.x) * glide;',
    'const double centreY = mPosition.y + (mouth.y - mPosition.y) * glide;',
    'alpha = 0.45f * static_cast<float>(rise * (1.0 - fade));', 'node->setVisible(true);')
has(read('source/entities/GhostEntity.h'), 'the mouth the ghost flows into',
    'void setTransferTarget(const Ogre::Vector3& mouth) { mTransferTarget = mouth; mHasTransferTarget = true; }')
assert look.index('if(mState == GhostState::boxed && transfer > 0.0)') < look.index('setMeshOpacity(alpha);')


# 5. Model of the timeline: 20 s at 1.4 turns per second; the put-in first, then the ghost visible for the whole flow,
# out of the device beside the hunter over the rim into the mouth, ends in the ectoplasm; the trap stays shut
def ghost_at(share, device, mouth):
    rise = min(1.0, share / 0.1)
    spiral = max(0.0, min(1.0, (share - 0.1) / 0.8))
    fade = max(0.0, min(1.0, (share - 0.9) / 0.1))
    glide = min(1.0, spiral / 0.25)
    angle = spiral * 5.0 * 2.0 * math.pi
    radius = 0.42 * math.sin(spiral * math.pi) + 0.1 * (1.0 - spiral)
    top = max(device[2], mouth[2]) + 0.45
    lift = device[2] + (top - device[2]) * rise - (top - mouth[2]) * spiral - 0.2 * fade
    x = device[0] + (mouth[0] - device[0]) * glide + radius * math.cos(angle)
    y = device[1] + (mouth[1] - device[1]) * glide + radius * math.sin(angle)
    return 0.45 * rise * (1.0 - fade), x, y, lift, spiral


turns_per_second = float(re.search(r'double ODApplication::turnsPerSecond = ([\d.]+);', read('source/ODApplication.cpp')).group(1))
duration = transfer_seconds * turns_per_second
assert abs(duration - 28.0) < 1e-9, duration
surface = surface_height
mouth = (0.5, 0.5, surface)
for x, y in [(0, 0)]:
    device = device_for(x, y)
    for step in range(1, 1000):
        alpha, gx, gy, lift, spiral = ghost_at(step / 1000.0, device, mouth)
        assert alpha > 0.0, ('ghost visible during the whole flow', step)
        from_mouth = math.hypot(gx - 0.5, gy - 0.5)
        if spiral >= 0.25:
            assert from_mouth <= 0.53, ('inside the cauldron mouth once over it', x, y, step, from_mouth)
        if from_mouth > rim_radius:
            assert lift > rim_top or math.hypot(gx - device[0], gy - device[1]) <= 0.11, ('over the rim, not through it', x, y, step)
    start = ghost_at(0.001, device, mouth)
    assert math.hypot(start[1] - device[0], start[2] - device[1]) <= 0.11, ('it leaves the device', x, y)
    end = ghost_at(1.0, device, mouth)
    assert end[0] < 1e-9 and end[3] < surface and math.hypot(end[1] - 0.5, end[2] - 0.5) <= 0.11, ('ends faded in the ectoplasm', end)
    assert ghost_at(0.9, device, mouth)[3] < ghost_at(0.5, device, mouth)[3] < ghost_at(0.1, device, mouth)[3]
# The put-in comes first and the whole delivery keeps the transfer time: 20, 16 and 13.3 s by the research
for seconds in (20.0, 16.0, 20.0 * 0.667):
    for t_step in range(0, int(seconds * 100) + 1):
        t_now = t_step / 100.0
        inserted = max(0.0, min(1.0, t_now / put_in))
        share = 0.0 if inserted < 1.0 else max(0.0, (t_now - put_in) / (seconds - put_in))
        if t_now < put_in:
            assert share == 0.0, ('the ghost waits in the shut trap until it is put in', t_now)
        if t_now < put_in:
            assert inserted < 1.0, ('the trap goes into the seat over the put-in', t_now)
    # At the end of the transfer time (the server's clock) the ghost has fully flowed in, not before the put-in is over
    assert share == 1.0 and t_now == seconds or abs(t_now - seconds) < 0.01 and abs(share - 1.0) < 0.01 / (seconds - put_in), \
        ('the ghost has fully flowed in at the end of the transfer time', seconds, t_now, share)
    assert all(max(0.0, (k / 100.0 - put_in) / (seconds - put_in)) < 1.0 for k in range(0, int(seconds * 100) - 1)), \
        'not fully in before the transfer time is over'

# 6. A loaded game resumes the remaining time: the saved clock k leaves duration - k turns
for saved in (0.0, 7.0, 27.0):
    turns, left = saved, 0
    while turns < duration:
        turns += 1.0
        left += 1
    assert left == math.ceil(duration - saved), (saved, left)

# 7. Decisions 855 and 857: only the CatchTime research shortens the transfer (20 s, 16 s, 13.3 s); hunter efficiency
# does not. The transfer clock runs one turn per game turn for every hunter, nothing in its time reads an efficiency.
def code_only(text):
    return re.sub(r'//[^\n]*', '', text)


transfer_body = code_only(body(action, 'double CreatureActionHuntGhost::getTransferTurns() const'))
state6 = code_only(state6)
refresh = code_only(refresh)
for word in ('fficiency', 'getAffinity', 'getLevel', 'Speed'):
    assert word not in transfer_body, ('the transfer time does not depend on the hunter', word)
assert state6.count('mTurns+=') == 1 and 'if(mLastTimedTurn!=map.getTurnNumber()) { mTurns+=1.0;mLastTimedTurn=map.getTurnNumber(); }' in state6, \
    'the transfer clock gains exactly one turn per game turn'
for word in ('fficiency', 'getAffinity', 'Speed', 'getBeamSeconds'):
    assert word not in state6, ('the transfer phase does not read the hunter efficiency', word)
transfer_share = refresh[refresh.index('else if(boxMode==5)'):]
transfer_share = transfer_share[:transfer_share.index('break;')]
assert 'fficiency' not in transfer_share and 'getCaptureTurns' not in transfer_share, \
    'the client share of the transfer does not read the hunter efficiency or the beam time'
catch_time = re.search(r'^\s*roomGhostRoom\s+CatchTime\s+mul\s+(\S+)\s+(\S+)\s+(\S+)\s*$', read('config/skills.cfg'), re.M)
assert catch_time, 'CatchTime research line'
seconds_by_level = [transfer_seconds * float(f) for f in catch_time.groups()]
assert [round(s, 1) for s in seconds_by_level] == [20.0, 16.0, 13.3], seconds_by_level
print('ghost transfer: trap seat of the cauldron, hunter walks to its side, put-in, trap shut, 20 s, visible, resumed, CatchTime only: ok')
