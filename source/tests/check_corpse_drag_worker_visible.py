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
print('ok')
