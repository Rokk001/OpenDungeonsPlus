"""Static checks for actual job-pause reporting through the existing ring; no compilation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# Isolate one production function for source-contract checks.
def function(path, signature):
    source = (ROOT / path).read_text(encoding="utf-8")
    block = source[source.index(signature):]
    return block[:block.index("\n}\n")]


packet = function("source/entities/Creature.cpp", "void Creature::exportProgressToPacket(")
assert 'CreatureAction::isRoomWorkAction(getActivity().action)' in packet
assert 'mJobCooldown > 0 && mJobCooldownDuration > 0' in packet
assert 'working ? static_cast<double>(mJobCooldown) : mAttackRecoveryTurns' in packet
assert 'working ? static_cast<double>(mJobCooldownDuration) : mAttackRecoveryDuration' in packet
assert 'os << getExperienceProgress() << remaining << duration << mAttackRecoverySerial;' in packet
setup = function("source/entities/Creature.cpp", "void Creature::setJobCooldown(")
assert setup.index('if(hasSlapEffect())') < setup.index('mJobCooldown = val;')
assert 'mJobCooldownDuration = static_cast<uint32_t>(std::max(0, val));' in setup
assert '++mAttackRecoverySerial;' in setup and 'mNeedFireRefresh = true;' in setup
header = (ROOT / "source/entities/Creature.h").read_text(encoding="utf-8")
decrement = header[header.index('inline bool decreaseJobCooldown()'):header.index('void setJobCooldown(')]
assert decrement.index('--mJobCooldown;') < decrement.index('mNeedFireRefresh = true;')
assert decrement.count('--mJobCooldown;') == 1
room = function("source/creatureaction/CreatureActionUseRoom.cpp", "bool CreatureActionUseRoom::handleJob(")
assert 'if(!creature.decreaseJobCooldown())' in room
fixture = (ROOT / "source/tests/check_creature_progress.py").read_text(encoding="utf-8")
assert 'actual job pause round trip and end' in fixture
assert 'job display keeps existing packet alignment' in fixture
assert 'interrupted work does not display an unrelated old job pause' in fixture
print("Actual room-work pauses use the unchanged recovery payload; gameplay cooldown decrement remains authoritative: PASS (static only)")
