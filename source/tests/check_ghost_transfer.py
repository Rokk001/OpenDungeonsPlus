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
# Decision 865: the delivery device beside the hunter and the put-in, each key under a documentation line
rows = rooms.splitlines()
for key, value in (('GhostDeliveryHandReach', '0.55'), ('GhostDeliveryHeight', '1.1'), ('GhostPutInSeconds', '1')):
    assert values.get(key) == value, (key, values.get(key), value)
    index = next(i for i, row in enumerate(rows) if row.split()[:1] == [key])
    above = index - 1
    while not rows[above].lstrip().startswith('#'):
        assert rows[above].split()[0].startswith('Ghost'), (key, 'documented block')
        above -= 1
    assert 'decision 865' in rows[above - 1] + rows[above] or key == 'GhostPutInSeconds', (key, 'doc line names the decision')
put_in_row = next(i for i, row in enumerate(rows) if row.split()[:1] == ['GhostPutInSeconds'])
put_in_doc = ' '.join(rows[put_in_row - 2:put_in_row])
assert all(row.startswith('#') for row in rows[put_in_row - 2:put_in_row]), 'two documentation lines over GhostPutInSeconds'
assert all(word in put_in_doc for word in ('put-in', 'Empty clip', 'shut', 'swings out')), 'the put-in doc lines describe the motion'
hand_reach = float(values['GhostDeliveryHandReach'])
device_height = float(values['GhostDeliveryHeight'])
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
has(state6, 'transfer at the delivery point', 'const Ogre::Vector3 socket=RoomGhostRoom::getTrapSocketPosition(*mEmptyAnchor,*mDestination);',
    'if(poured!=nullptr && poured->getPosition()!=socket) poured->teleport(socket);', 'const double duration=getTransferTurns();',
    'while(!mGhosts.empty() && mTurns>=duration)', 'if(ghost!=nullptr) empty->emptyGhost(mCreature,*ghost);',
    'if(mEmptyAnchor==nullptr) { interrupt();return false; }')
for removed in ('GhostEmptyTurns', 'getEfficiency'):
    assert removed not in state6, ('the old emptying is replaced', removed)
# Decision 865: the put-in motion plays once on arrival (the Empty clip, not looped), facing the device
has(state6, 'the put-in motion once', 'if(!mPutIn) { mCreature.setAnimationState(EntityAnimation::empty_anim,false,socket-mCreature.getPosition(),true);mPutIn=true; }')
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

# 3. Decision 865: the delivery point is the top of the device beside the hunter, not the middle of the cauldron's top
room = read('source/rooms/RoomGhostRoom.cpp')
socket_body = body(room, 'Ogre::Vector3 RoomGhostRoom::getTrapSocketPosition(const Tile& anchor, const Tile& standing)')
has(socket_body, 'device beside the hunter towards the cauldron',
    'const float centreX=anchor.getX()+0.5f,centreY=anchor.getY()+0.5f;',
    'const float towardsX=centreX-static_cast<float>(standing.getX()),towardsY=centreY-static_cast<float>(standing.getY());',
    'const float distance=std::sqrt(towardsX*towardsX+towardsY*towardsY);',
    'const float reach=std::min(static_cast<float>(config.getRoomConfigDouble("GhostDeliveryHandReach")),distance);',
    'return Ogre::Vector3(static_cast<float>(standing.getX())+towardsX*reach/distance,',
    'static_cast<float>(standing.getY())+towardsY*reach/distance,static_cast<float>(config.getRoomConfigDouble("GhostDeliveryHeight")));')
for old in ('TRAP_SOCKET_HEIGHT', '1.574'):
    assert old not in socket_body, ('no socket over the middle of the mouth', old)
has(read('source/rooms/RoomGhostRoom.h'), 'declarations', 'static Ogre::Vector3 getTrapSocketPosition(const Tile& anchor, const Tile& standing);',
    'static Ogre::Vector3 getCauldronMouthPosition(const Ogre::Vector3& cauldron);', 'static float getCauldronRimRadius();')
has(body(room, 'Ogre::Vector3 RoomGhostRoom::getCauldronMouthPosition('), 'mouth on the mesh', 'static const float ECTOPLASM_SURFACE_HEIGHT=1.17f;')
has(body(room, 'float RoomGhostRoom::getCauldronRimRadius()'), 'rim on the mesh', 'static const float RIM_RADIUS=0.66f;')
rim_radius, rim_top, surface_height = 0.66, 1.24, 1.17


# Model of getTrapSocketPosition for every tile a hunter may stand on (reserveCauldron: the ring round the 2x2 block)
def device_for(stand_x, stand_y):
    centre_x, centre_y = 0.5, 0.5
    towards_x, towards_y = centre_x - stand_x, centre_y - stand_y
    distance = math.hypot(towards_x, towards_y)
    reach = min(hand_reach, distance)
    return stand_x + towards_x * reach / distance, stand_y + towards_y * reach / distance, device_height


ring = [(x, y) for y in range(-1, 3) for x in range(-1, 3) if not (0 <= x < 2 and 0 <= y < 2)]
assert len(ring) == 12
for x, y in ring:
    dx, dy, dz = device_for(x, y)
    # Within reach of the hand: GhostDeliveryHandReach from the middle of the hunter's tile, between him and the cauldron
    assert abs(math.hypot(dx - x, dy - y) - hand_reach) < 1e-9, (x, y)
    assert (dx - x) * (0.5 - x) + (dy - y) * (0.5 - y) > 0, ('towards the cauldron', x, y)
    assert abs((dx - x) * (0.5 - y) - (dy - y) * (0.5 - x)) < 1e-9, ('on the line to the middle', x, y)
    # Not over the middle of the cauldron's top: outside its rim, on the hunter's side
    assert math.hypot(dx - 0.5, dy - 0.5) > rim_radius + 0.3, ('beside the cauldron, not on its top', x, y)
    # At hand height: under the rim's top, above the cauldron's belly hoop
    assert 0.9 <= dz <= rim_top, dz
assert hand_reach <= 0.6, 'the hand reaches the device without a step'
# The trap (models/GhostBox.mesh 0.13 x 0.11 x 0.12) fits into the cradle and its top shows above it
creature = read('source/entities/Creature.cpp')
half_x, half_y, depth = (float(re.search(r'static const Ogre::Real %s=([\d.]+)f;' % name, creature).group(1))
                         for name in ('GHOST_DEVICE_HALF_X', 'GHOST_DEVICE_HALF_Y', 'GHOST_DEVICE_DEPTH'))
assert 0.13 / 2 < half_x and 0.11 / 2 < half_y and depth < 0.12, (half_x, half_y, depth)
has(body(room, 'void RoomGhostRoom::createCauldronObjects()'), 'cauldron centred on its block', 'tile->getX()+0.5f,tile->getY()+0.5f,0.0f,0.0f,false);')
generator = read('assets-src/rooms/ghostroom/create_models.py')
assert "rod('Trap socket glow',(0,0,1.385),(0,0,1.405),.165,'GhostEctoplasm',24)" in generator
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
ordered_parts = ('const Ogre::Vector3 device=ghost->getPosition();',
    'const double putIn=config.getRoomConfigDouble("GhostPutInSeconds");',
    'const double transferSeconds=SkillManager::getResearchValue(getSeat(),SkillType::roomGhostRoom,',
    'config.getRoomConfigDouble("GhostTransferSeconds"),"CatchTime");',
    'mGhostDeliveryClock=mGhostThrowTurns*transferSeconds>=putIn?putIn:0.0;',
    'mGhostDeliveryMouth=ghostCauldronMouthNear(*getGameMap(),device);',
    'buildGhostDeliveryDevice(*mGhostDeliveryDevice,arm);',
    'else mGhostDeliveryClock+=seconds*getGameMap()->getGameSpeedFactor();',
    'const double swing=putIn>0.0?std::min(1.0,mGhostDeliveryClock/(0.4*putIn)):1.0;',
    'const float inserted=static_cast<float>(putIn>0.0?std::max(0.0,std::min(1.0,(mGhostDeliveryClock-0.4*putIn)/(0.6*putIn))):1.0);',
    'const Ogre::Vector3 seat=device-Ogre::Vector3(0.0f,0.0f,GHOST_DEVICE_DEPTH);',
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
for removed in ('lidTarget', 'poured', 'GhostLidOpenSeconds'):
    assert removed not in delivery, ('the trap no longer opens in the device', removed)
has(visuals, 'the device leaves with the delivery', 'destroyGhostDelivery(scene,mGhostDeliveryHinge,mGhostDeliveryNode,mGhostDeliveryDevice);')
assert visuals.index('if(mGhostBoxMode!=5)') < visuals.index('destroyGhostDelivery(')
device_body = body(creature, 'static void buildGhostDeliveryDevice(')
for material in ('"GhostBrass"', '"GhostIron"', '"GhostEctoplasm"'):
    assert material in device_body, ('the device has its cradle, arm and intake', material)
assert device_body.count('object.begin(') == device_body.count('object.end();') == 3
mouth_body = body(creature, 'static Ogre::Vector3 ghostCauldronMouthNear(')
has(mouth_body, 'the ghost flows into the nearest cauldron', 'entity->getMeshName()!="GhostCauldron"',
    'RoomGhostRoom::getCauldronMouthPosition(best->getPosition())')
has(body(creature, 'void Creature::clearGhostHuntVisuals()'), 'reset', 'ghost->setTransferProgress(0.0);', 'mGhostTransferShown=0.0;',
    'destroyGhostDelivery(scene,mGhostDeliveryHinge,mGhostDeliveryNode,mGhostDeliveryDevice);')
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
for x, y in ring:
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
        swing = min(1.0, t_now / (0.4 * put_in))
        inserted = max(0.0, min(1.0, (t_now - 0.4 * put_in) / (0.6 * put_in)))
        share = 0.0 if inserted < 1.0 else max(0.0, (t_now - put_in) / (seconds - put_in))
        if t_now < put_in:
            assert share == 0.0, ('the ghost waits in the shut trap until it is put in', t_now)
        if t_now < 0.4 * put_in:
            assert inserted == 0.0 and swing < 1.0, ('the device swings out before the trap goes in', t_now)
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
print('ghost transfer: delivery device beside the hunter, put-in, trap shut, 20 s, visible, resumed, CatchTime only: ok')
