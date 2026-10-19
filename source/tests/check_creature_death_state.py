"""Static regression for late-visible corpses retaining death state; no compilation or game launch."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# Isolate one production function without executing C++.
def function(path, signature):
    source = (ROOT / path).read_text(encoding="utf-8")
    block = source[source.index(signature):]
    return block[:block.index("\n}\n")]


death = function("source/entities/Creature.cpp", "void Creature::dropCarriedEquipment()")
assert death.index("clearDestinations(EntityAnimation::die_anim, false, false)") < death.index(
    "setAnimationState(EntityAnimation::die_anim, false, Ogre::Vector3::ZERO, false)")
assert death.index("clearActionQueue();") < death.index("setAnimationState(EntityAnimation::die_anim")
state = function("source/entities/MovableGameEntity.cpp", "void MovableGameEntity::setAnimationState(")
assert "mPrevAnimationState = state;" in state and "mPrevAnimationStateLoop = loop;" in state
packet = function("source/entities/MovableGameEntity.cpp", "void MovableGameEntity::exportToPacket(")
assert "os << mPrevAnimationState;" in packet and "os << mPrevAnimationStateLoop;" in packet
restore = function("source/entities/MovableGameEntity.cpp", "void MovableGameEntity::restoreEntityState()")
assert "rrSetObjectAnimationState(this, mPrevAnimationState, mPrevAnimationStateLoop)" in restore
print("Death pose is retained in authoritative state and initial corpse packets, without idle reset: PASS (static only)")

# Lethal knockouts use the same retained lying pose, while remaining non-attackable.
damage = function("source/entities/Creature.cpp", "double Creature::takeDamage(")
knockout = damage[damage.index("else if(ko && !getDefinition()->isWorker())"):]
assert knockout.index("mHp = 1.0;") < knockout.index("dropCarriedEquipment();")
assert knockout.index("mKoTurnCounter = -") < knockout.index("dropCarriedEquipment();")
assert 'recordScriptEvent(*this, "incapacitated")' in knockout
attackable = function("source/entities/Creature.cpp", "bool Creature::isAttackable(")
assert "if(mKoTurnCounter < 0)" in attackable
assert "return false;" in attackable[attackable.index("if(mKoTurnCounter < 0)"):]
print("Lethal knockouts share the retained lying pose and remain non-attackable: PASS (static only)")
