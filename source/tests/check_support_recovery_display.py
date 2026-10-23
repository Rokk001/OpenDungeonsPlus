"""Check successful self-cast recovery reporting without compiling or starting the game."""
from pathlib import Path

source = (Path(__file__).resolve().parents[2] / "source/entities/Creature.cpp").read_text(encoding="utf-8")


# Verify that both successful support paths report the real timers after their failure guard.
def check(text):
    for signature in ("void Creature::doUpkeep()", "void Creature::possessedUseSkill("):
        block = text[text.index(signature):]
        block = block[:block.index("\n}\n")]
        start = block.index("if(!skillData.mSkill->tryUseSupport(")
        report = block[start:]
        report = report[:report.index("mNeedFireRefresh = true;") + len("mNeedFireRefresh = true;")]
        guard = "continue;" if "doUpkeep" in signature else "return;"
        statements = (
            guard,
            "skillData.mCooldown += skillData.mSkill->getCooldownNbTurns();",
            "skillData.mWarmup += skillData.mSkill->getWarmupNbTurns();",
            "mAttackRecoveryDuration = std::max(static_cast<double>(skillData.mWarmup), skillData.mCooldown);",
            "mAttackRecoveryTurns = mAttackRecoveryDuration;",
            "++mAttackRecoverySerial;",
            "mNeedFireRefresh = true;",
        )
        positions = [report.index(statement) for statement in statements]
        assert positions == sorted(positions)
        assert report.count("++mAttackRecoverySerial;") == 1


check(source)
try:
    check(source.replace("mAttackRecoveryTurns = mAttackRecoveryDuration;", "", 1))
except (ValueError, AssertionError):
    pass
else:
    raise AssertionError("Missing AI recovery report was not detected")
# Removing both report sites must also expose the possessed-path regression.
try:
    check(source.replace("++mAttackRecoverySerial;", ""))
except (ValueError, AssertionError):
    pass
else:
    raise AssertionError("Missing cast refresh sequence was not detected")
print("AI and possessed self-casts report actual recovery only after success: PASS (source contract, not runtime)")
