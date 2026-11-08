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
export = body(action, 'void CreatureActionHuntGhost::exportToStream(')
assert "<< mState << ' ' << (mTarget.empty()?\"none\":mTarget) << ' '" in export and "<< mTurns <<" in export, 'clock saved'
has(body(action, 'bool CreatureActionHuntGhost::isTransferring() const'), 'at the cauldron',
    'mState==6 && !mGhosts.empty() && mDestination!=nullptr', '!mCreature.isMoving() && mCreature.getPositionTile()==mDestination')
has(body(action, 'uint32_t CreatureActionHuntGhost::getBoxVisualState() const'), 'visual state 5', 'if(isTransferring()) return 5u;')
has(body(action, 'std::string CreatureActionHuntGhost::getThrowGhostName() const'), 'transferred ghost',
    'if(isTransferring()) return mGhosts.front();')
has(header, 'declarations', 'uint32_t getBoxVisualState() const;', 'double getTransferTurns() const;', 'bool isTransferring() const;')

# 3. The delivery point is the top of the socket glow of the cauldron mesh
room = read('source/rooms/RoomGhostRoom.cpp')
has(body(room, 'Ogre::Vector3 RoomGhostRoom::getTrapSocketPosition(const Tile& anchor)'), 'socket on the mesh',
    'static const float TRAP_SOCKET_HEIGHT=1.574f;', 'return Ogre::Vector3(anchor.getX()+0.5f,anchor.getY()+0.5f,TRAP_SOCKET_HEIGHT);')
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
has(visuals, 'trap open on the socket', 'const bool lyingBox=mGhostBoxMode==1 || mGhostBoxMode==3 || mGhostBoxMode==4 || mGhostBoxMode==5;',
    'else if(mGhostBoxMode==5)', 'position=ghost->getPosition();',
    'const double poured=mGhostTransferShown*config.getRoomConfigDouble("GhostTransferSeconds");',
    'lidTarget=std::min(1.0,poured/config.getRoomConfigDouble("GhostLidOpenSeconds"));', 'trapLight=mGhostLidShown;',
    'ghost->setTransferProgress(mGhostBoxMode==5?mGhostTransferShown:0.0);', 'mGhostHeldBox->setVisible(mGhostBoxMode==2);')
has(body(creature, 'void Creature::clearGhostHuntVisuals()'), 'reset', 'ghost->setTransferProgress(0.0);', 'mGhostTransferShown=0.0;')
ghost = read('source/entities/GhostEntity.cpp')
look = body(ghost, 'void GhostEntity::updateLook()')
has(look, 'transfer look', 'if(mState == GhostState::boxed && transfer > 0.0)', 'const double rise = std::min(1.0, transfer / 0.1);',
    'const double spiral = std::max(0.0, std::min(1.0, (transfer - 0.1) / 0.8));',
    'const double fade = std::max(0.0, std::min(1.0, (transfer - 0.9) / 0.1));',
    'const double angle = spiral * 5.0 * 2.0 * Ogre::Math::PI;',
    'const double radius = 0.42 * std::sin(spiral * Ogre::Math::PI) + 0.1 * (1.0 - spiral);',
    'static const double TRANSFER_RISE = 0.45;', 'const double lift = TRANSFER_RISE * rise - (TRANSFER_RISE + 0.40) * spiral - 0.2 * fade;',
    'alpha = 0.45f * static_cast<float>(rise * (1.0 - fade));', 'node->setVisible(true);')
assert look.index('if(mState == GhostState::boxed && transfer > 0.0)') < look.index('setMeshOpacity(alpha);')


# 5. Model of the timeline: 20 s at 1.4 turns per second; visible for the whole transfer, inside the mouth, ends in the
# ectoplasm; the trap lid is open after GhostLidOpenSeconds
def ghost_at(share):
    rise = min(1.0, share / 0.1)
    spiral = max(0.0, min(1.0, (share - 0.1) / 0.8))
    fade = max(0.0, min(1.0, (share - 0.9) / 0.1))
    radius = 0.42 * math.sin(spiral * math.pi) + 0.1 * (1.0 - spiral)
    lift = 0.45 * rise - (0.45 + 0.40) * spiral - 0.2 * fade
    return 0.45 * rise * (1.0 - fade), radius, lift


turns_per_second = float(re.search(r'double ODApplication::turnsPerSecond = ([\d.]+);', read('source/ODApplication.cpp')).group(1))
duration = transfer_seconds * turns_per_second
assert abs(duration - 28.0) < 1e-9, duration
socket, surface = 1.574, 1.17
for step in range(1, 1000):
    alpha, radius, lift = ghost_at(step / 1000.0)
    assert alpha > 0.0, ('ghost visible during the whole transfer', step)
    assert radius <= 0.53, ('inside the cauldron mouth', step, radius)
end = ghost_at(1.0)
assert end[0] < 1e-9 and socket + end[2] < surface, ('ends faded in the ectoplasm', end)
assert ghost_at(0.9)[2] < ghost_at(0.5)[2] < ghost_at(0.1)[2] and socket + ghost_at(0.95)[2] < surface + 0.05
assert min(1.0, (2.0 / transfer_seconds) * transfer_seconds / lid_open) == 1.0, 'lid open after two seconds'

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
print('ghost transfer: delivery point, 20 s, visible, resumed, CatchTime only (not efficiency): ok')
