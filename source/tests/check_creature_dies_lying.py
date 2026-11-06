"""Wiring check (X1 rework, decisions 664/687): a knocked-out creature that dies dies where it lies, and a dead creature
lies still (no compiler needed)."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


render = read('source/render/RenderManager.cpp')
header = read('source/render/RenderManager.h')
movable = read('source/entities/MovableGameEntity.cpp')

# (c) the death clip does not start again for a body that already lies in its death pose
assert 'bool rrIsCreatureDown(const Creature* creature) const;' in header
down = render.split('bool RenderManager::rrIsCreatureDown')[1].split('void RenderManager::rrRefreshCreatureGoldSack')[0]
assert 'EntityAnimation::die_anim' in down and 'mCreatureGroundPoses' in down and 'mLieOnGround' in down
clip = movable.split('void MovableGameEntity::startAnimationClip()')[1].split('//! \brief Checks the actual strike phase')[0]
assert 'rrIsCreatureDown' in clip and clip.index('rrIsCreatureDown') < clip.index('rrSetObjectAnimationState')
assert 'mPrevAnimationState == EntityAnimation::die_anim' in clip

# (g) a dead body never loops a clip and no clip but the death and decay clips advances
ground = render.split('void RenderManager::setCreatureDropGroundAnimation')[1].split('void RenderManager::rrCreateCreatureCombatImpact')[0]
assert 'animation, false);' in ground and 'animation == EntityAnimation::idle_anim' not in ground
update = movable.split('void MovableGameEntity::update(Ogre::Real timeSinceLastFrame)')[1].split('if (mWalkQueue.empty())')[0]
assert 'deadBodyHolds' in update and 'isAlive()' in update and '"CorpseDecay"' in update and '!deadBodyHolds &&' in update
print('ok')
