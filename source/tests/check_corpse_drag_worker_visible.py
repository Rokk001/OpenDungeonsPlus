#!/usr/bin/env python3
"""Pure check (nothing compiled): the worker that pulls a corpse to the crypt (or a prisoner to the cell) plays the Drag
clip like the worker that pulls a wounded creature to its bed, and nothing in the dead-body hold hides or freezes
the carrier (X1 rework 2)."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
action = (root / 'source/creatureaction/CreatureActionCarryEntity.cpp').read_text(encoding='utf-8')
movable = (root / 'source/entities/MovableGameEntity.cpp').read_text(encoding='utf-8')
render = (root / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')

drag = action.split('bool CreatureActionCarryEntity::handleDragCreature()')[1].split('void CreatureActionCarryEntity::releaseEntity')[0]
external = drag.split('if(mExternalDrag)')[1].split('// A cot taken by hand')[0]
# the external pull (corpse to crypt) walks the worker with the Drag clip, never with the plain Walk clip
assert 'mCreature.setDragDestination(mTileDest)' in external
assert 'mCreature.setDestination(' not in external

# the Drag clip exists for the worker skeletons and is chosen for a worker that pulls (not for the pulled body)
for name in ('Kobold', 'Dwarf1'):
    assert b'Drag' in (root / 'models' / (name + '.skeleton')).read_bytes(), name
assert 'EntityAnimation::drag_anim' in render.split('std::string chooseDragClip')[1].split('freezeOnLastFrame = false')[1][:400]

# the hold of dead bodies only applies to creatures that are not alive, a living carrier keeps its clip running
hold = movable.split('bool deadBodyHolds = false;')[1].split('if (!deadBodyHolds')[0]
assert '!static_cast<Creature*>(this)->isAlive()' in hold
# the early return for creatures that lie down needs the death clip as the requested clip, the drag clip is not it
clip = movable.split('void MovableGameEntity::startAnimationClip()')[1].split('rrSetObjectAnimationState')[0]
assert 'mPrevAnimationState == EntityAnimation::die_anim' in clip
# nothing hides a carrier worker: a pulled body is never attached to the worker node
assert 'mIsDrag' in action and 'if(mIsDrag)' in action.split('CreatureActionCarryEntity::CreatureActionCarryEntity(Creature& creature, GameEntity& entityToCarry, Building& buildingDest')[1][:1800]

# X1 rework 3 (decision 710): the worker was still invisible and the corpse floated.
# (a) The corpse got the Dragged clip, a pose for a living, hurt creature pulled by the legs (the standing-ish pose of
#     the skeleton and the Troll hangs up to 0.9 above the ground). A dead body that already lies keeps its lying pose.
start = movable.split('void MovableGameEntity::startAnimationClip()')[1].split('void MovableGameEntity::')[0]
assert 'mPrevAnimationState == EntityAnimation::dragged_anim' in start and '!static_cast<Creature*>(this)->isAlive()' in start
assert start.index('dragged_anim') < start.index('rrSetObjectAnimationState')
down = render.split('bool RenderManager::rrIsCreatureDown')[1].split('void RenderManager::rrRefreshCreatureGoldSack')[0]
assert '"CorpseDecay"' in down
# (b) The corpse was pulled at the configured gap of 0.9 tiles, less than the half length of a lying Troll or Dragon
#     plus the worker: the body lay over the small worker (Kobold, 0.3 high) and hid it. The gap now covers both bodies.
assert 'double dragGap(Creature& worker, Creature& dragged)' in action
creature = (root / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
gap = creature.split('double Creature::getDragGap')[1].split(chr(10) + '}' + chr(10))[0]
assert 'RoomObjectNavigation::clearance(worker) + RoomObjectNavigation::clearance(dragged)' in gap
assert 'getRoomConfigDoubleOrDefault("DormitoryWoundedDragGap"' in gap
assert 'Creature::getDragGap(worker, dragged)' in action.split('double dragGap')[1].split(chr(10) + '}' + chr(10))[0]
assert action.count('dragGap(mCreature, *dragged)') == 2
# (decision 892) the corpse stays at the hands of the worker the whole way: a client sets the pulled dead body every
# frame on the way the worker walked, one gap behind it, instead of letting its own queued walk fall behind
assert 'updateDragTether();' in creature.split('void Creature::update(Ogre::Real timeSinceLastFrame)')[1].split(chr(10) + '}' + chr(10))[0]
tether = creature.split('void Creature::updateDragTether()')[1].split(chr(10) + '}' + chr(10))[0]
assert '!getIsOnServerMap()' in tether and 'mDragWorkerName.empty()' in tether
assert 'getCreature(mDragWorkerName)' in tether
assert 'getCreatures()' not in tether
assert creature.count('os << mDragWorkerName;') == 2
assert creature.count('is >> mDragWorkerName') == 2
assert 'mDragWorkerName = worker.getName();' in creature
assert 'mDragWorkerName.clear();' in creature
assert 'getDragGap(*worker, *this)' in tether and 'setPosition(' in tether
# the gap works for big bodies too (same function for small and big)
# the lying body of the biggest creatures needs more than the old gap of 0.9
import re
bounds = (root / 'source/gamemap/RoomObjectBounds.h').read_text(encoding='utf-8')
radii = dict(re.findall(r'\{"(\w+)\.mesh", (\.\d+)f, -', bounds.split('walkingRadii[]')[1]))
kobold = float(radii['Kobold'])
for big in ('Troll', 'Dragon', 'PitDemon', 'LavaSpawn', 'Kreatur'):
    assert float(radii[big]) + kobold + 0.1 > 0.9, big
print('ok')
