#!/usr/bin/env python3
"""Pure check (nothing compiled), decision 1048: a dead creature that a worker pulls jumped back and forth.
Cause: rrApplyDragContact sampled the animated hand bone of the Drag clip (and the ankle bone of the body) every
frame, so the body followed the swing of the arm. Fix: both points are sampled once per pull and kept in the node
local space, the body hangs at a fixed grip. Also reads decision 991 point 2 (knocked-out creature restored lying)."""
import math
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
render = (root / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
header = (root / 'source/render/RenderManager.h').read_text(encoding='utf-8')
creature = (root / 'source/entities/Creature.cpp').read_text(encoding='utf-8')


def body(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start)]


contact = body(render, 'void RenderManager::rrApplyDragContact(')
# the bones are only sampled while the grip is not valid yet; the position uses the stored local points
sample, use = contact.split('grip.mUsed = true;')
assert 'if(!grip.mValid || grip.mWorkerName != worker.getName())' in sample
assert sample.count('dragBonePoint(') == 2
assert 'dragBonePoint(' not in use
assert 'convertWorldToLocalPosition(sampledHand)' in sample and 'convertWorldToLocalPosition(sampledAnkle)' in sample
assert 'workerNode->convertLocalToWorldPosition(grip.mHand)' in use
assert 'bodyNode->convertLocalToWorldPosition(grip.mAnkle)' in use
assert 'contactPosition = bodyNode->_getDerivedPosition() + hand - ankle;' in use
# the grip lives as long as the pull: dropped when unused for a frame and when the creature is destroyed
assert 'struct DragGrip' in header and 'std::map<Creature*, DragGrip> mDragContactGrips;' in header
reset = body(render, 'void RenderManager::rrResetDragContacts()')
assert 'mDragContactGrips.erase(grip)' in reset and 'mUsed = false' in reset
assert 'mDragContactGrips.erase(curCreature);' in body(render, 'void RenderManager::rrDestroyCreature(')

# Numeric model: the worker walks backwards at constant speed, the hand swings with the clip.
SPEED, DT, SWING = 0.9, 1 / 60, 0.25


def hand_local(t):
    return 0.5 + SWING * math.sin(2 * math.pi * 1.2 * t)  # along the walking axis in worker space


def positions(grip_fixed):
    ankle_local = 0.2  # frozen lying pose: constant
    grip = hand_local(0.0)
    out = []
    for i in range(600):
        t = i * DT
        worker = -SPEED * t
        hand = worker + (grip if grip_fixed else hand_local(t))
        out.append(hand - ankle_local)  # body position = hand - ankle
    return out


# the body travels away from the start (negative direction); a step in the other direction is a jump back
def backward_steps(series):
    return sum(1 for i in range(len(series) - 1) if series[i + 1] - series[i] > 1e-9)


assert backward_steps(positions(False)) > 50, 'old contact: the swing pushes the body back and forth'
assert backward_steps(positions(True)) == 0, 'fixed grip: the body only moves with the worker'
steps = [positions(True)[i] - positions(True)[i + 1] for i in range(599)]
assert max(steps) - min(steps) < 1e-9, 'constant speed, no jitter'

# Decision 991 point 2, by reading: a knocked-out or dying creature is restored lying (not standing)
assert re.search(r'else if\(isAlive\(\) && \(mKoTurnCounter != 0\)\)', creature)
branch = creature[creature.index('else if(isAlive() && (mKoTurnCounter != 0))'):]
branch = branch[:branch.index('// The mana comes from the save')]
assert 'EntityAnimation::die_anim' in branch and 'setAnimationTime(LOADED_LYING_CLIP_SECONDS)' in branch
restore = body(creature, 'void Creature::restoreEntityState()')
assert 'rrSettleCreatureFall(this)' in restore and 'LOADED_LYING_CLIP_SECONDS' in restore
assert 'KO_SAVE_OPEN << " " << mKoTurnCounter' in creature
print('dragged corpse stable grip: ok')
