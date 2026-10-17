"""Check animation clock and interruption contracts without compiling or starting the game.

Each regression also has a negative source mutation, so losing its protection must fail.
These source checks do not claim visible animation quality or C++ execution.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATHS = {
    'frame': 'source/render/ODFrameListener.cpp',
    'render': 'source/render/RenderManager.cpp',
    'reactions': 'source/render/CreatureReactions.cpp',
    'rooms': 'source/render/RoomAmbience.cpp',
    'movable': 'source/entities/MovableGameEntity.cpp',
    'chicken': 'source/entities/ChickenEntity.cpp',
    'combat': 'source/render/CreatureCombatReactions.cpp',
}


# Return a complete top-level C++ function, retaining its final closing brace.
def body(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2]


# Report missing protections for the original pause, timing, sleep and facing failures.
def violations(sources):
    render = body(sources['render'], 'void RenderManager::updateRenderAnimations(')
    frame = body(sources['frame'], 'void ODFrameListener::updateAnimations(')
    start = body(sources['reactions'], 'bool CreatureReactions::startClip(')
    reaction = body(sources['reactions'], 'bool CreatureReactions::updateReaction(')
    motion = body(sources['reactions'], 'void CreatureReactions::clearMotion(')
    scan = body(sources['rooms'], 'void RoomAmbience::scan()')
    events = body(sources['rooms'], 'void RoomAmbience::scanCreatureEvents()')
    ambient = body(sources['rooms'], 'bool RoomAmbience::playCreatureClip(')
    movable = body(sources['movable'], 'void MovableGameEntity::update(')
    mount = body(sources['chicken'], 'void ChickenEntity::mountHen(')
    contact = body(sources['movable'], 'bool MovableGameEntity::hasReachedAnimationContact(')
    hits = body(sources['combat'], 'void CreatureCombatReactions::processHits(')
    wake = body(sources['render'], 'bool RenderManager::startCreatureWakeAnimation(')
    select = body(sources['render'], 'void RenderManager::rrSetObjectAnimationState(')
    protections = [
        ('pause', 'if((mGameMap == nullptr) || mGameMap->getGamePaused() || (mGameMap->getTurnNumber() <= 0))' in render and
         render.index('if(mHandAnimationState != nullptr)') <
         render.index('mGameMap->getGamePaused()') <
         render.index('updateChickenLooks(timeSinceLastFrame)')),
        ('render speed', 'timeSinceLastFrame *= static_cast<Ogre::Real>(mGameMap->getGameSpeedFactor());' in render),
        ('reaction speed', 'mCreatureReactions->update(gameTime);' in frame and
         'mRoomAmbience->update(gameTime);' in frame and 'mGameMap->getGameSpeedFactor()' in frame),
        ('clip lifetime', 'reaction.mDuration' not in start and
         '(reaction.mElapsed >= reaction.mDuration) && reaction.mClip.empty()' in reaction and
         'return !reaction.mClip.empty() || (reaction.mElapsed < reaction.mDuration);' in reaction),
        ('motion clock', 'const double elapsed = reaction.mElapsed;' in motion and
         'reaction.mElapsed = elapsed;' in motion and
         motion.index('applyMotion(reaction, creature);') < motion.index('reaction.mElapsed = elapsed;')),
        ('sleep occupants', 'RenderManager::getSingleton().rrIsCreatureSleeping(creature)' in scan),
        ('sleep events', 'RenderManager::getSingleton().rrIsCreatureSleeping(creature)' in events),
        ('ambient priority', '!creature->isAlive()' in ambient and 'creature->isKo()' in ambient and
         'creature->getAnimationStateName() != EntityAnimation::idle_anim' in ambient),
        ('strike speed', 'mBlowStartDelay -= static_cast<double>(timeSinceLastFrame) * gameSpeedFactor;' in movable),
        ('mating facing', 'hen.setAnimationState(ChickenPose::cackle, true, direction, false);' in mount and
         'setAnimationState(ChickenPose::mount, true, direction, false);' in mount and
         mount.index('playPose(ChickenPose::mount, 3);') <
         mount.index('hen.setAnimationState(ChickenPose::cackle, true, direction, false);')),
        ('contact phase', 'if(mBlowStartDelay > 0.0)' in contact and
         'mAnimationState->getTimePosition() >= mAnimationState->getLength() * share' in contact),
        ('contact scheduling', '!attacker->hasReachedAnimationContact(HIT_SHARE_OF_CLIP)' in hits and
         hits.index('!attacker->hasReachedAnimationContact(') < hits.index('PendingHit hit = *it;')),
        ('particle clock', 'mSceneManager->getMovableObjects("ParticleSystem")' in render and
         '->setSpeedFactor(particleSpeed)' in render and
         'mGameMap->getGamePaused() ? 0.0f' in render),
        ('reaction blend', 'animState->setWeight(0.0f);' in start and
         'base->setWeight(static_cast<Ogre::Real>(1.0 - weight));' in reaction),
        ('wake continuity', 'sleeping.mWakeStartTime * (1.0f - progress)' in render and
         'const Ogre::Real previousTime = sleeping.mAnimation->getTimePosition();' in wake and
         '(clip == previousClip) ? previousTime' in wake),
        ('wake priority', '(anim == EntityAnimation::idle_anim) && startCreatureWakeAnimation' in select and
         select.index('startCreatureWakeAnimation(dropCreature, objectEntity)') <
         select.index('cancelCreatureSleepAnimation(dropCreature);')),
    ]
    return [name for name, protected in protections if not protected]


# Verify every protection and ensure a corresponding removed guard is detected.
def main():
    sources = {key: (ROOT / path).read_text(encoding='utf-8') for key, path in PATHS.items()}
    failures = violations(sources)
    assert not failures, failures
    mutations = [
        ('render', 'if((mGameMap == nullptr) || mGameMap->getGamePaused() || (mGameMap->getTurnNumber() <= 0))',
         'if(mGameMap == nullptr)', 'pause'),
        ('render', 'timeSinceLastFrame *= static_cast<Ogre::Real>(mGameMap->getGameSpeedFactor());', '', 'render speed'),
        ('frame', 'mCreatureReactions->update(gameTime);', 'mCreatureReactions->update(timeSinceLastFrame);', 'reaction speed'),
        ('reactions', '(reaction.mElapsed >= reaction.mDuration) && reaction.mClip.empty()',
         'reaction.mElapsed >= reaction.mDuration', 'clip lifetime'),
        ('reactions', 'reaction.mElapsed = elapsed;', '', 'motion clock'),
        ('rooms', 'RenderManager::getSingleton().rrIsCreatureSleeping(creature)', 'false', 'sleep occupants'),
        ('rooms', 'const bool sleeping = RenderManager::getSingleton().rrIsCreatureSleeping(creature);',
         'const bool sleeping = false;', 'sleep events'),
        ('rooms', 'creature->getAnimationStateName() != EntityAnimation::idle_anim', 'false', 'ambient priority'),
        ('movable', 'mBlowStartDelay -= static_cast<double>(timeSinceLastFrame) * gameSpeedFactor;',
         'mBlowStartDelay -= static_cast<double>(timeSinceLastFrame);', 'strike speed'),
        ('chicken', 'hen.setAnimationState(ChickenPose::cackle, true, direction, false);', '', 'mating facing'),
        ('movable', 'mAnimationState->getTimePosition() >= mAnimationState->getLength() * share',
         'true', 'contact phase'),
        ('combat', '!attacker->hasReachedAnimationContact(HIT_SHARE_OF_CLIP)', 'false', 'contact scheduling'),
        ('render', '->setSpeedFactor(particleSpeed)', '->setSpeedFactor(1.0f)', 'particle clock'),
        ('reactions', 'base->setWeight(static_cast<Ogre::Real>(1.0 - weight));', '', 'reaction blend'),
        ('render', '(clip == previousClip) ? previousTime', '(clip == previousClip) ? 0.0f', 'wake continuity'),
        ('render', '(anim == EntityAnimation::idle_anim) && startCreatureWakeAnimation',
         'startCreatureWakeAnimation', 'wake priority'),
    ]
    for key, old, new, label in mutations:
        changed = dict(sources)
        assert old in changed[key], (label, 'mutation did not match')
        changed[key] = changed[key].replace(old, new, 1)
        assert label in violations(changed), (label, 'negative control was accepted')
    print('Animation contracts: 16 protections and 16 negative controls passed; no compilation or game execution.')


if __name__ == '__main__':
    main()
