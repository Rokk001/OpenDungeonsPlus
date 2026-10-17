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
    'overlay': 'source/render/CreatureOverlayStatus.cpp',
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
    activate = body(sources['reactions'], 'bool CreatureReactions::startReaction(')
    reaction = body(sources['reactions'], 'bool CreatureReactions::updateReaction(')
    motion = body(sources['reactions'], 'void CreatureReactions::clearMotion(')
    scan = body(sources['rooms'], 'void RoomAmbience::scan()')
    events = body(sources['rooms'], 'void RoomAmbience::scanCreatureEvents()')
    ambient = body(sources['rooms'], 'bool RoomAmbience::playCreatureClip(')
    movable = body(sources['movable'], 'void MovableGameEntity::update(')
    mount = body(sources['chicken'], 'void ChickenEntity::mountHen(')
    contact = body(sources['movable'], 'bool MovableGameEntity::hasReachedAnimationContact(')
    hits = body(sources['combat'], 'void CreatureCombatReactions::processHits(')
    schedule = body(sources['combat'], 'void CreatureCombatReactions::scheduleHit(')
    request = body(sources['movable'], 'void MovableGameEntity::setAnimationState(')
    wake = body(sources['render'], 'bool RenderManager::startCreatureWakeAnimation(')
    select = body(sources['render'], 'void RenderManager::rrSetObjectAnimationState(')
    overlay = body(sources['overlay'], 'void CreatureOverlayStatus::update(')
    emote = body(sources['overlay'], 'void CreatureOverlayStatus::showEmote(')
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
        ('native wake blend', 'sleeping.mWakeFromAnimation = previousAnimation;' in wake and
         'sleeping.mWakeFromAnimation->setWeight(1.0f - weight);' in render and
         'sleeping.mWakeFromAnimation->setEnabled(false);' in render),
        ('articulated motion', 'if(!reaction.mArticulatedMotion)' in activate and
         'reaction.mArticulatedMotion = true;' in start),
        ('rest strength', 'getArticulatedRestTime(position / animState->getLength(), reaction.mClipWeight)' in reaction and
         'position = std::min(end, reaction.mElapsed * speed);' in reaction),
        ('queued contact', '!mWalkQueue.empty()' in contact and 'mDestinationAnimationState.find("Attack")' in contact),
        ('hit request identity', 'it->mAnimationSequence != attacker->getAnimationSequence()' in hits and
         'hit.mAnimationSequence == animationSequence' in schedule and '++mAnimationSequence;' in request),
        ('impact separation', 'hit.mAttacker == attackerName' in schedule),
        ('rest duration', 'getLength() / variant.mMotion.mDuration' in start and
         'reaction.mArticulatedMotion ? reaction.mClipSpeed :' in reaction),
        ('explicit rest priority', '(sitting || lying) && variant.mClip.empty() && variant.mFallbackClip.empty()' in start),
        ('emote clock', 'mEmoteRemaining -= timeSincelastFrame * static_cast<Ogre::Real>(mCreature->getGameMap()->getGameSpeedFactor());' in overlay and
         'mMovableTextOverlay->update(timeSincelastFrame);' in overlay and
         'timeToDisplay > 0.0f ? -1.0f : timeToDisplay' in emote),
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
        ('render', 'sleeping.mWakeFromAnimation = previousAnimation;', '', 'native wake blend'),
        ('reactions', 'if(!reaction.mArticulatedMotion)', 'if(true)', 'articulated motion'),
        ('reactions', 'getArticulatedRestTime(position / animState->getLength(), reaction.mClipWeight)',
         'getArticulatedRestTime(position / animState->getLength(), 1.0)', 'rest strength'),
        ('movable', 'mDestinationAnimationState.find("Attack")', 'std::string().find("Attack")', 'queued contact'),
        ('combat', 'it->mAnimationSequence != attacker->getAnimationSequence()', 'false', 'hit request identity'),
        ('combat', 'hit.mAttacker == attackerName', 'true', 'impact separation'),
        ('reactions', 'reaction.mArticulatedMotion ? reaction.mClipSpeed :',
         'false ? reaction.mClipSpeed :', 'rest duration'),
        ('reactions', '(sitting || lying) && variant.mClip.empty() && variant.mFallbackClip.empty()',
         '(sitting || lying)', 'explicit rest priority'),
        ('overlay', 'mEmoteRemaining -= timeSincelastFrame * static_cast<Ogre::Real>(mCreature->getGameMap()->getGameSpeedFactor());',
         'mEmoteRemaining -= timeSincelastFrame;', 'emote clock'),
    ]
    for key, old, new, label in mutations:
        changed = dict(sources)
        assert old in changed[key], (label, 'mutation did not match')
        changed[key] = changed[key].replace(old, new, 1)
        assert label in violations(changed), (label, 'negative control was accepted')
    print('Animation contracts: 25 protections and 25 negative controls passed; no compilation or game execution.')


if __name__ == '__main__':
    main()
