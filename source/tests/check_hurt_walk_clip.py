#!/usr/bin/env python3
"""Pure check (nothing compiled, nothing started): a badly hurt creature walks with the clip WalkHurt when the
skeleton has it (else Walk), CarryWalk wins over it, the entity state stays Walk (same speed factors), the clip is
switched when the health stage crosses the threshold, and the E15 HurtWalk reaction adds no second limp on top."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]

def read(path):
    return (root / path).read_text(encoding='utf-8').replace('\r\n', '\n')

movable_h = read('source/entities/MovableGameEntity.h')
creature_h = read('source/entities/Creature.h')
creature = read('source/entities/Creature.cpp')
render = read('source/render/RenderManager.cpp')
reactions = read('source/render/CreatureReactions.cpp')
cfg = read('config/creatureReactions.cfg')

assert 'walk_hurt_anim = "WalkHurt"' in movable_h

# One stage test shared by the walk factor and the clip choice (16a condition and threshold)
assert 'static bool isLowHealthWalkStage(uint32_t healthStage);' in creature_h
assert 'isLowHealthWalkStage(mOverlayHealthValue)' in creature_h
stage = creature[creature.index('bool Creature::isLowHealthWalkStage'):creature.index('double Creature::getLowHealthWalkFactor')]
assert 'getLowHealthWalkThresholdPercent()' in stage and 'NB_OVERLAY_HEALTH_VALUES - 2' in stage
factor = creature[creature.index('double Creature::getLowHealthWalkFactor'):creature.index('double Creature::getClientPoseSpeedFactor')]
assert 'if(!isLowHealthWalking())' in factor and 'return 1.0;' in factor
assert 'getLowHealthWalkSpeedFactor()' in factor

# Clip choice: after the CarryWalk block (priority below it), only for Walk, only if the skeleton has it
carry = render.index('anim = EntityAnimation::carry_walk_anim;')
hurt = render.index('anim = EntityAnimation::walk_hurt_anim;')
assert carry < hurt
block = render[carry:hurt]
assert 'else if' in block and '(anim == EntityAnimation::walk_anim)' in block
assert 'dropCreature->isLowHealthWalking()' in block
assert 'hasAnimation(EntityAnimation::walk_hurt_anim)' in block
# The existing missing-clip loop still runs afterwards (Walk is never replaced because the skeleton is checked)
assert render.index('while (!objectEntity->getSkeleton()->hasAnimation(anim))') > hurt

# Speed: the entity state stays Walk, the clip time uses the Walk factors, nothing is added for WalkHurt
movable = read('source/entities/MovableGameEntity.cpp')
assert 'walk_hurt_anim' not in movable
assert 'walk_hurt_anim' not in creature.replace('EntityAnimation::walk_anim', '')

# The clip is switched when the health stage crosses the threshold while walking
update = creature[creature.index('void Creature::updateFromPacket'):]
assert 'isLowHealthWalkStage(oldHealthValue) != isLowHealthWalking()' in update
assert 'rrSetObjectAnimationState(this, EntityAnimation::walk_anim, true)' in update

# E15 HurtWalk: the limp motion is skipped while WalkHurt plays, the emote stays, the event is unchanged
assert '(event.mName == "HurtWalk")' in reactions
assert 'walk_hurt_anim' in reactions and '!playsHurtWalk' in reactions
event = re.search(r'Name\s+HurtWalk\b(.*?)\[/Event\]', cfg, re.S).group(1)
assert re.search(r'Emote\s+Sweat', event) and re.search(r'Motion\s+shake', event) and re.search(r'Motion\s+hop', event)
assert 'Clip ' not in event
print('check_hurt_walk_clip: ok')
