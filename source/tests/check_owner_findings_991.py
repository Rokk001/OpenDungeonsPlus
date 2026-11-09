#!/usr/bin/env python3
"""Check the three owner findings of decision 991 without launching the game.

1. A worker pulls a body right behind itself: the pulled body follows the worker that really pulls it, not the
   slower placeholder worker type, so it never falls behind on a long way to the crypt (replay of the follow).
2. A creature that is knocked out or lies dying when the game is saved lies again at once after loading: the
   knockout is saved, and the production load branch (compiled) sets the death clip at its last frame.
3. An own merchant room (and every other room) keeps its owner on a human client: no room flashes in the changing
   colours of an unowned room on the minimap (replay of the production owner switches over every room visual).

Fixed values of this branch: 24 room visuals; Kobold and DwarfWorker GroundMoveSpeed 1.35 and GroundSpeed/Level
0.01815; placeholder worker GroundMoveSpeed 1.0; DormitoryWoundedDragWorkerSpeedFactor 0.6,
DormitoryWoundedDragFollowSpeedFactor 1.3, DormitoryWoundedDragGap 0.9; CreatureGetUpSeconds 6; 1.4 turns per second.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def body(source, signature):
    """Returns the braces body of the first function that starts with the signature."""
    start = source.index(signature)
    open_brace = source.index('{', start)
    depth = 0
    for index in range(open_brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[open_brace:index + 1]
    raise AssertionError('no end of ' + signature)


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def config_value(text, key):
    match = re.search(r'^\s*' + re.escape(key) + r'\s+(\S+)', text, re.M)
    assert match, key
    return float(match.group(1))


def creature_block(text, name):
    start = text.index('    Name\t' + name)
    return text[start:text.index('[/Creature]', start)]


creature = read('source/entities/Creature.cpp')
rooms_cfg = read('config/rooms.cfg')
creatures_cfg = read('config/creatures.cfg')

# ---------------------------------------------------------------------------------------------------------------
# 1. The pulled body keeps right behind the worker
# ---------------------------------------------------------------------------------------------------------------
speed = strip_comments(body(creature, 'double Creature::getMoveSpeed(Tile* tile) const'))
dragged = speed[speed.index('clip == EntityAnimation::dragged_anim'):]
dragged = dragged[:dragged.index('return ')] + dragged[dragged.index('return '):].split(';', 1)[0]
assert 'getCreatureDefinitionDefaultWorker()' in dragged, 'the placeholder type stays the lower bound'
assert 'getGameMap()->getCreature(mDragWorkerName)' in dragged, 'the worker that really pulls is looked up'
assert re.search(r'workerSpeed\s*=\s*std::max\(workerSpeed,\s*worker->getMoveSpeedGround\(\)\)', dragged), \
    'the body follows the faster of the placeholder type and the real worker'
assert 'getDragWorkerSpeedFactor()' in dragged and 'DormitoryWoundedDragFollowSpeedFactor' in dragged

placeholder = re.search(r'double\s+moveSpeedGround\s*=\s*([\d.]+)', read('source/entities/CreatureDefinition.h'))
assert placeholder and float(placeholder.group(1)) == 1.0, 'placeholder worker ground speed'
drag_factor = config_value(rooms_cfg, 'DormitoryWoundedDragWorkerSpeedFactor')
follow_factor = config_value(rooms_cfg, 'DormitoryWoundedDragFollowSpeedFactor')
gap = config_value(rooms_cfg, 'DormitoryWoundedDragGap')
assert (drag_factor, follow_factor, gap) == (0.6, 1.3, 0.9), (drag_factor, follow_factor, gap)
workers = {}
for name in ('Kobold', 'DwarfWorker'):
    block = creature_block(creatures_cfg, name)
    workers[name] = (config_value(block, 'GroundMoveSpeed'), config_value(block, 'GroundSpeed/Level'))
    assert workers[name] == (1.35, 0.01815), (name, workers[name])


def trailing_distance(worker_ground, body_ground, path_tiles=20.0, step=0.05):
    """Replays CreatureActionCarryEntity: the worker walks the path with the Drag clip, the body is sent up to the
    trail length minus the gap each turn and slides there at its own speed. Returns the largest distance on the
    trail between worker and body while the worker walks."""
    worker_speed = worker_ground * drag_factor
    body_speed = body_ground * drag_factor * follow_factor
    worker_arc = 0.0
    body_arc = 0.0
    largest = 0.0
    while worker_arc < path_tiles:
        worker_arc = min(path_tiles, worker_arc + worker_speed * step)
        target = max(0.0, worker_arc - gap)
        body_arc = min(target, body_arc + body_speed * step)
        largest = max(largest, worker_arc - body_arc)
    return largest


for name, (ground, per_level) in workers.items():
    for level in range(1, 31):
        worker_ground = ground + per_level * (level - 1)
        fixed = trailing_distance(worker_ground, max(1.0, worker_ground))
        assert fixed <= gap + 0.06, (name, level, fixed)
# Before the fix the body slid at the placeholder speed (1.0): a level 10 Kobold left it 3.7 tiles behind after a
# way of 20 tiles, the three tiles the owner saw; the fixed follow keeps it at the gap
old = trailing_distance(workers['Kobold'][0] + workers['Kobold'][1] * 9, 1.0)
assert old > 3.0, old

# The animated hand contact of the pulled body stays (decision 892 follow-up): leg in the worker's hand
render = read('source/render/RenderManager.cpp')
contact = body(render, 'void RenderManager::rrApplyDragContact(')
assert 'Hand.R' in contact and 'Foot.R' in contact and 'hand - ankle' in contact

# ---------------------------------------------------------------------------------------------------------------
# 2. A knocked-out or dying creature lies right after loading
# ---------------------------------------------------------------------------------------------------------------
export = creature[creature.index('void Creature::exportToStream'):creature.index('Creature::importFromStream')]
assert re.search(r'if\(mArenaKnockOut \|\| mKoTurnCounter != 0\)\s*\n\s*os << "\\t" << KO_SAVE_OPEN', export), \
    'every knockout is saved, a temporary one too'
restore = body(creature, 'void Creature::restoreEntityState()')
assert re.search(r'getAnimationStateName\(\) == EntityAnimation::die_anim &&\s*getAnimationTime\(\) >= '
                 r'LOADED_LYING_CLIP_SECONDS\)\s*RenderManager::getSingleton\(\)\.rrSettleCreatureFall\(this\);', restore)
assert re.search(r'static const double LOADED_LYING_CLIP_SECONDS = 1000\.0;', creature)
assert config_value(rooms_cfg, 'CreatureGetUpSeconds') == 6.0
turns = re.search(r'double ODApplication::turnsPerSecond = ([\d.]+);', read('source/ODApplication.cpp'))
assert turns and float(turns.group(1)) == 1.4

setup = body(creature, 'void Creature::setupDefinition(')
branch = setup[setup.index('if(!isAlive() && mDeathCounter != 0)'):setup.index('// The mana comes from the save')]
settle = body(render, 'void RenderManager::rrSettleCreatureFall(')

probe = r'''
#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <string>
#include <vector>
namespace Ogre { struct Vector3 { static const Vector3 ZERO; }; const Vector3 Vector3::ZERO = {}; typedef float Real; }
namespace EntityAnimation { const std::string die_anim = "Die", rot_anim = "Rot", getup_anim = "GetUp", idle_anim = "Idle"; }
namespace ODApplication { double turnsPerSecond = 1.4; }
struct ConfigManager
{
    static ConfigManager& getSingleton() { static ConfigManager c; return c; }
    double getRoomConfigDouble(const std::string& key) { assert(key == "CreatureGetUpSeconds"); return 6.0; }
};
static const double LOADED_LYING_CLIP_SECONDS = 1000.0;
struct Loaded
{
    double mHp = 1.0, mDeathCounter = 0.0, mDecayTurns = -1.0, mKoTurnCounter = 0.0;
    bool mArenaKnockOut = false;
    std::string mClip = "Idle", mDestinationClip;
    double mClipTime = 0.0;
    bool isAlive() const { return mHp > 0.0; }
    void clearDestinations(const std::string& clip, bool, bool) { mDestinationClip = clip; }
    void setAnimationState(const std::string& clip, bool, const Ogre::Vector3&, bool) { mClip = clip; mClipTime = 0.0; }
    void setAnimationTime(double time) { mClipTime = std::max(0.0, time); }
    void restore()
    {
BRANCH
    }
};
struct Creature {};
struct CreatureDropAnimation { Creature* mCreature; Ogre::Real mElapsed; };
struct CreatureDeathVariant { Creature* mCreature; Ogre::Real mElapsed; Ogre::Real mDuration; };
const Ogre::Real CREATURE_DROP_ANIMATION_DURATION = 0.35f;
struct Render
{
    std::vector<CreatureDropAnimation> mCreatureDropAnimations;
    std::vector<CreatureDeathVariant> mCreatureDeathVariants;
    void rrSettleCreatureFall(const Creature* creature)
SETTLE
};
static Loaded load(double hp, double koTurns, bool arena, double deathCounter = 0.0, double decay = -1.0)
{
    Loaded c;
    c.mHp = hp; c.mKoTurnCounter = koTurns; c.mArenaKnockOut = arena; c.mDeathCounter = deathCounter; c.mDecayTurns = decay;
    c.restore();
    return c;
}
int main()
{
    // Dying (death knockout, counter below 0): lies in the last frame of the death clip
    Loaded dying = load(5.0, -12.0, false);
    assert(dying.mClip == "Die" && dying.mDestinationClip == "Die" && dying.mClipTime >= 1000.0);
    // Temporary knockout (tavern, stun): lies too
    Loaded stunned = load(5.0, 20.0, false);
    assert(stunned.mClip == "Die" && stunned.mClipTime >= 1000.0);
    // Arena loser still lying (counter above the 9 get-up turns): lies
    Loaded arenaLying = load(5.0, 30.0, true);
    assert(arenaLying.mClip == "Die" && arenaLying.mClipTime >= 1000.0);
    // Arena loser already getting up (9 or fewer turns left): goes on getting up
    Loaded arenaUp = load(5.0, 9.0, true);
    assert(arenaUp.mClip == "GetUp" && arenaUp.mClipTime == 0.0);
    // Healthy creature: unchanged
    Loaded healthy = load(5.0, 0.0, false);
    assert(healthy.mClip == "Idle" && healthy.mDestinationClip.empty());
    // Dead body: lies at once; a decaying body keeps the decay clip that seeks its own time
    Loaded body = load(0.0, 0.0, false, 40.0);
    assert(body.mClip == "Die" && body.mClipTime >= 1000.0);
    Loaded decaying = load(0.0, 0.0, false, 40.0, 3.0);
    assert(decaying.mClip == "Rot" && decaying.mClipTime == 0.0);

    // The procedural falls of only that creature end at once
    Creature a, b;
    Render render;
    render.mCreatureDropAnimations = {{&a, 0.0f}, {&b, 0.1f}};
    render.mCreatureDeathVariants = {{&a, 0.0f, 1.6f}, {&b, 0.2f, 1.6f}};
    render.rrSettleCreatureFall(&a);
    assert(render.mCreatureDropAnimations[0].mElapsed >= CREATURE_DROP_ANIMATION_DURATION);
    assert(render.mCreatureDropAnimations[1].mElapsed == 0.1f);
    assert(render.mCreatureDeathVariants[0].mElapsed >= 1.6f);
    assert(render.mCreatureDeathVariants[1].mElapsed == 0.2f);
    std::cout << "load lying probe ok" << std::endl;
    return 0;
}
'''.replace('BRANCH', branch).replace('SETTLE', settle)


def run_probe(source_text):
    compiler = shutil.which('cl')
    assert compiler, 'cl (MSVC) is needed for the compiled probe; run from a Developer prompt (vcvars64)'
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        (work / 'probe.cpp').write_text(source_text, encoding='utf-8')
        subprocess.run([compiler, '/nologo', '/EHsc', '/MD', '/std:c++17', 'probe.cpp', '/Feprobe.exe'],
                       cwd=work, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([str(work / 'probe.exe')], cwd=work, check=True)


run_probe(probe)

# ---------------------------------------------------------------------------------------------------------------
# 3. Every own room keeps its owner on a human client
# ---------------------------------------------------------------------------------------------------------------
tile_h = read('source/entities/Tile.h')
enum = tile_h[tile_h.index('enum class TileVisual'):]
enum = enum[:enum.index('};')]
room_visuals = sorted(set(re.findall(r'\b([a-zA-Z]+Room)\b', strip_comments(enum))))
assert len(room_visuals) == 24, room_visuals

seat = strip_comments(read('source/game/Seat.cpp'))


def case_blocks(switch_text):
    """Splits a switch into (labels, statements) groups: consecutive case labels share the statements after them."""
    groups = []
    pending = []
    for part in re.split(r'(case TileVisual::\w+:|default:)', switch_text)[1:]:
        label = re.match(r'case TileVisual::(\w+):$', part)
        if label:
            pending.append(label.group(1))
        elif part == 'default:':
            pending.append('default')
        elif part.strip():
            groups.append((pending, part))
            pending = []
    return groups


def switch_of(function_body, head):
    start = function_body.index(head)
    return body(function_body[start:], head)


update = body(seat, 'void Seat::updateTileStateForSeat(')
remembered = {}
for labels, statements in case_blocks(switch_of(update, 'switch(jj->second.mTileVisual)')):
    for label in labels:
        remembered[label] = statements
exported = {}
export_tile = body(seat, 'void Seat::exportTileToPacket(')
for labels, statements in case_blocks(switch_of(export_tile, 'switch(tileState.mTileVisual)')):
    for label in labels:
        exported[label] = statements

for visual in room_visuals:
    statements = remembered.get(visual)
    assert statements is not None, visual + ': the owner of the room is not remembered'
    assert 'jj->second.mSeatIdOwner = tile->getSeat()->getId();' in statements, visual
    assert 'getIsHuman' not in statements, visual + ': the owner is remembered for human keepers too'
    sent = exported.get(visual)
    assert sent is not None and 'tileSeatId = tileState.mSeatIdOwner;' in sent, visual + ': the owner is sent'

# A state stored before the owner was remembered for humans (-1) still sends the keeper's own new rooms
for visual in ('merchantRoom', 'herbGardenRoom', 'alchemyLabRoom', 'infirmaryRoom'):
    assert 'if(tileSeatId == -1 && tile->getSeat() == this && tile->getTileVisual() == tileState.mTileVisual)' \
        in exported[visual], visual
    assert 'tileSeatId = getId();' in exported[visual], visual

# The minimap flashes a room only while its owner is unknown (the colours of an unowned room)
minimap = strip_comments(read('source/gamemap/MiniMap.cpp'))
colour = body(minimap, 'MiniMap::TileColour MiniMap::colourFromTile(')
assert 'if(room && (owner == nullptr || owner->isRogueSeat()))' in colour and 'result.animated = true;' in colour
print('owner findings 991 ok')
