"""Static regression guard for recovery countdown during possession; no compilation or game launch."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "source/entities/Creature.cpp").read_text(encoding="utf-8")
upkeep = source[source.index("void Creature::doUpkeep()") :]
upkeep = upkeep[:upkeep.index("\n}\n")]
countdown = upkeep.index("if(mAttackRecoveryTurns > 0)")
possessed = upkeep.index("// If a player controls the creature, its other actions are paused.")
assert upkeep.count("--mAttackRecoveryTurns;") == 1
assert upkeep.index("if(isFrozen())") < countdown < possessed
assert upkeep.index("if(isHexenHen())") < countdown
assert 'mNeedFireRefresh = true;' in upkeep[countdown:possessed]
assert upkeep.index('--skillData.mCooldown;', possessed) > countdown
assert upkeep.index('possessedFunc();', possessed) > countdown
assert 'working ? static_cast<uint32_t>(mJobCooldown) : mAttackRecoveryTurns' in source
assert 'os << getExperienceProgress() << remaining << duration << mAttackRecoverySerial;' in source
print("Recovery countdown updates exactly once before possessed and AI actions, retaining existing packet fields: PASS (static only)")
