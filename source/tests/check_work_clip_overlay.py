#!/usr/bin/env python3
"""Pure check (nothing compiled, nothing started): a WhileWorking reaction can lay a named clip over the running work
clip, the work clip keeps running through complementary blend weights (restored afterwards), and the exhaustion and trap reload events are
hooked up to their clips. A creature that carries something walks with the clip CarryWalk (when the skeleton
has it) instead of Walk, with the same speed factors."""
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
cpp = (root / 'source' / 'render' / 'CreatureReactions.cpp').read_text(encoding='utf-8')
cfg = (root / 'config' / 'creatureReactions.cfg').read_text(encoding='utf-8')

# The gate in front of startClip: dying events never, WhileWorking events only when the variant names a clip
assert re.search(r'clipAllowed\s*=\s*!event\.mDying\s*&&\s*\(!event\.mWhileWorking\s*\|\|\s*!variant\.mClip\.empty\(\)\)', cpp)
assert 'clipAllowed && startClip(reaction, creature, variant)' in cpp
# No mActivity change, no refresh in the clip code
start = cpp.index('bool CreatureReactions::startClip')
end = cpp.index('bool CreatureReactions::addParticles')
clip_code = cpp[start:end]
start_code = clip_code[:clip_code.index('void CreatureReactions::stopClip')]
stop_code = clip_code[clip_code.index('void CreatureReactions::stopClip'):]
assert 'mActivity' not in clip_code and 'fireCreatureRefreshIfNeeded' not in clip_code
# The running work clip is retained for the entry blend and restored when the overlay ends.
assert 'base->setEnabled(false)' not in clip_code
assert 'base->setWeight(1.0f);' in start_code and 'base->setWeight(1.0f);' in stop_code
assert 'animState->setWeight(0.0f);' in start_code
update_start = cpp.index('bool CreatureReactions::updateReaction')
update_end = cpp.index('\n}', update_start) + 2
update_code = cpp[update_start:update_end]
assert 'animState->setWeight(static_cast<Ogre::Real>(weight));' in update_code
assert 'base->setWeight(static_cast<Ogre::Real>(1.0 - weight));' in update_code
assert 'base->setTimePosition(' not in clip_code and 'base->addTime(' not in update_code
# Priority rule for a WhileWorking event stays
assert 'event->mWhileWorking &&' in cpp and 'ReactionPriority::none' in cpp

events = {}
for match in re.finditer(r'\[Event\](.*?)\[/Event\]', cfg, re.S):
    body = match.group(1)
    name = re.search(r'Name\s+(\S+)', body).group(1)
    events[name] = body

# Read the configured named overlays without changing their event ordering.
def variant_clips(name):
    return re.findall(r'^\s*Clip\s+(\S+)', events[name], re.M)

for name, clips in (('DigExhausted', ('WipeBrow', 'Pant')), ('TrapReload', ('TrapReload',))):
    assert re.search(r'^\s*WhileWorking\s+yes', events[name], re.M), name
    assert variant_clips(name) == list(clips), (name, variant_clips(name))
    # The old effect and emote parts stay
    assert re.search(r'^\s*(Emote|Effect)\s', events[name], re.M), name


# Carrying walk: the clip is chosen where the Walk clip is applied, by the client side carry state
render = (root / 'source' / 'render' / 'RenderManager.cpp').read_text(encoding='utf-8')
client = (root / 'source' / 'network' / 'ODClient.cpp').read_text(encoding='utf-8')
movable_h = (root / 'source' / 'entities' / 'MovableGameEntity.h').read_text(encoding='utf-8')
creature_h = (root / 'source' / 'entities' / 'Creature.h').read_text(encoding='utf-8')
assert 'carry_walk_anim = "CarryWalk"' in movable_h
assert 'getClientCarrying()' in creature_h and 'setClientCarrying(bool carrying)' in creature_h
choice = re.search(r'\(anim == EntityAnimation::walk_anim\) && dropCreature->getClientCarrying\(\) &&\s+'
                   r'objectEntity->getSkeleton\(\)->hasAnimation\(EntityAnimation::carry_walk_anim\)', render)
assert choice, 'CarryWalk is chosen only for Walk, only when carrying and only when the skeleton has it'
# The drag clip is chosen before and is never replaced; the entity state (and so the speed factors) stays Walk
assert render.index('chooseDragClip(objectEntity') < choice.start()
assert 'carry_walk_anim' not in (root / 'source' / 'entities' / 'Creature.cpp').read_text(encoding='utf-8')
assert 'carry_walk_anim' not in (root / 'source' / 'entities' / 'MovableGameEntity.cpp').read_text(encoding='utf-8')
assert 'setClientCarrying(true);' in client and 'setClientCarrying(false);' in client
assert client.index('setClientCarrying(true);') < client.index('rrCarryEntity(carrier, carried)')
assert client.index('setClientCarrying(false);') < client.index('rrReleaseCarriedEntity(carrier, carried)')
# A carrier that already walks switches clips when it picks up or puts down
assert render.count('rrSetObjectAnimationState(carrier, EntityAnimation::walk_anim, true);') == 2

print('work clip overlay: ok')
